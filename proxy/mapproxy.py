import aiohttp.web
import asyncio
import app
import enum
import logging
import multiprocessing
import os
import proxy
import time
import travellermap
import threading
import typing

_MaxTileCacheBytes = 256 * 1024 * 1024 # 256MiB
_MapProxyDbFileName = 'map_proxy.db'

# NOTE: Changing the Server string like this doesn't work if an exception is
# thrown by the request handler. I can't see a way to do it without implementing
# my own code to generate HTTP error responses so it doesn't seem worth the
# effort
@aiohttp.web.middleware
async def _serverHeaderMiddlewareAsync(
        request: aiohttp.web.Request,
        handler: typing.Callable[[aiohttp.web.Request], aiohttp.web.Response]
        ):
    response: aiohttp.web.Response = await handler(request)
    response.headers['Server'] = f'{app.AppName} Map Proxy {app.AppVersion}'
    return response

class MapProxy(object):
    class ServerStatus(enum.Enum):
        Stopped = 0
        Starting = 1
        Started = 2
        Error = 3

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _listenPort = None
    _hostPoolSize = None
    _travellerMapUrl = None
    _installDir = None
    _appDir = None
    _mainsMilieu = None
    _logDir = None
    _logLevel = logging.INFO
    _service = None
    _shutdownEvent = None
    _status = ServerStatus.Stopped
    _mpContext = None # Multiprocessing context
    _messageQueue = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    # Setting up multiprocessing stuff should be protected by __main__ so
                    # shouldn't be done when initialising the rest of the static class
                    # variables. A context is used so we can force processes to be spawned,
                    # this keeps the behaviour the same on all OS and avoids issues with
                    # singletons when using fork
                    cls._mpContext = multiprocessing.get_context('spawn')
                    cls._shutdownEvent = cls._mpContext.Event()
                    cls._messageQueue = cls._mpContext.Queue()

                    cls._instance = cls.__new__(cls)
        return cls._instance

    @staticmethod
    def configure(
            listenPort: int,
            hostPoolSize: int,
            travellerMapUrl: str,
            installDir: str,
            appDir: str,
            mainsMilieu: travellermap.Milieu,
            logDir: str,
            logLevel: int
            ) -> None:
        if MapProxy._instance:
            raise RuntimeError('You can\'t configure map proxy after the singleton has been initialised')
        if MapProxy._listenPort == 0:
            raise RuntimeError('Map proxy listen port can\'t be 0')
        MapProxy._listenPort = listenPort
        MapProxy._hostPoolSize = hostPoolSize
        MapProxy._travellerMapUrl = travellerMapUrl
        MapProxy._installDir = installDir
        MapProxy._appDir = appDir
        MapProxy._mainsMilieu = mainsMilieu
        MapProxy._logDir = logDir
        MapProxy._logLevel = logLevel

    # NOTE: This blocks until the proxy has reached the started state
    def start(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        if self._service:
            self.shutdown()

        self._status = MapProxy.ServerStatus.Starting
        try:
            self._service = self._mpContext.Process(
                target=MapProxy._serviceCallback,
                args=[
                    self._listenPort,
                    self._hostPoolSize,
                    self._travellerMapUrl,
                    self._installDir,
                    self._appDir,
                    self._mainsMilieu,
                    self._logLevel,
                    self._shutdownEvent,
                    self._messageQueue])
            self._service.daemon = False
            self._service.start()

            # TODO: This needs a timeout
            while self._status == MapProxy.ServerStatus.Starting:
                time.sleep(0.1)
                while not self._messageQueue.empty():
                    message = self._messageQueue.get(block=False)
                    if not message:
                        continue
                    newStatus = message[0]

                    if newStatus == MapProxy.ServerStatus.Starting:
                        if progressCallback and len(message) == 4:
                            # Pass on the startup progress, adding 1 to account for the fact this function
                            # has an initial starting process stage that the process it's self knows nothing
                            # about
                            progressCallback(message[1], message[2] + 1, message[3] + 1)
                    elif newStatus == MapProxy.ServerStatus.Started:
                        self._status = MapProxy.ServerStatus.Started
                        break
                    elif newStatus == MapProxy.ServerStatus.Error:
                        if len(message) != 2:
                            raise RuntimeError('Map proxy failed to start (Unknown error)')
                        raise RuntimeError(f'Map proxy failed to start ({message[1]})')
                    elif newStatus == MapProxy.ServerStatus.Stopped:
                        raise RuntimeError(f'Map proxy stopped unexpectedly during startup')
        except:
            self._status = MapProxy.ServerStatus.Error
            raise

    def shutdown(self) -> None:
        if not self._service:
            return
        self._shutdownEvent.set()
        self._service.join()
        self._service = None
        self._shutdownEvent.clear()
        # Clear out message queue
        while not self._messageQueue.empty():
            self._messageQueue.get()
        self._status = MapProxy.ServerStatus.Stopped

    def status(self) -> 'MapProxy.ServerStatus':
        self._updateStatus()
        return self._status

    def _updateStatus(self) -> None:
        while not self._messageQueue.empty():
            message = self._messageQueue.get(block=False)
            if not message:
                continue

            status = message[0]
            assert(isinstance(status, MapProxy.ServerStatus))
            self._status = status

    # NOTE: This runs in a separate process
    @staticmethod
    def _serviceCallback(
            listenPort: int,
            hostPoolSize: int,
            travellerMapUrl: str,
            installDir: str,
            appDir: str,
            mainsMilieu: travellermap.Milieu,
            logLevel: int,
            shutdownEvent: multiprocessing.Event,
            messageQueue: multiprocessing.Queue
            ) -> None:
        try:
            app.setupLogger(
                logDir=os.path.join(appDir, 'logs'),
                logFile='mapproxy.log')
            app.setLogLevel(logLevel=logLevel)
        except Exception as ex:
            logging.error('Failed to set up map proxy logging', exc_info=ex)

        logging.info(f'Map Proxy {app.AppVersion}')

        dbPath=os.path.join(appDir, _MapProxyDbFileName)
        logging.info(f'Proxy Listen Port: {listenPort}')
        logging.info(f'Map Database Path: {dbPath}')        

        # This is a hack. The aiohttp server logs all requests at info level
        # where as I only want it logged at debug. The best way I can see to
        # achieve this is to set the server logging to a level that won't log
        # the request when the app log level is set to anything higher than
        # debug
        if logLevel > logging.DEBUG:
            logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

        database = None
        compositor = None
        tileCache = None
        requestHandler = None
        webApp = None
        try:
            installMapsDir = os.path.join(installDir, 'data', 'map')
            overlayMapsDir = os.path.join(appDir, 'map')
            customMapsDir = os.path.join(appDir, 'custom_map')
            travellermap.DataStore.setSectorDirs(
                installDir=installMapsDir,
                overlayDir=overlayMapsDir,
                customDir=customMapsDir)

            loop = asyncio.get_event_loop()

            #
            # Set up database
            #
            database = proxy.Database(filePath=dbPath)
            loop.run_until_complete(database.initAsync())            
            
            progressCallback = \
                lambda text, current, total: messageQueue.put((MapProxy.ServerStatus.Starting, text, current, total))

            #
            # Generate Mains
            #
            mainsData = None
            try:
                mainsGenerator = travellermap.MainsGenerator()
                mainsData = mainsGenerator.generate(
                    milieu=mainsMilieu,
                    progressCallback=progressCallback)
            except Exception as ex:
                logging.error(
                    f'An exception occurred while generating mains for {mainsMilieu.value}',
                    exc_info=ex)
                # Continue. Mains data will be pulled from Traveller Map, it just won't have
                # have custom sector data

            #
            # Set up compositor
            #
            compositor = proxy.Compositor(
                customMapsDir=customMapsDir,
                mapDatabase=database)
            loop.run_until_complete(compositor.initAsync(
                progressCallback=progressCallback))

            #
            # Set up tile cache 
            #
            tileCache = proxy.TileCache(
                mapDatabase=database,
                travellerMapUrl=travellerMapUrl,
                maxMemBytes=_MaxTileCacheBytes)
            loop.run_until_complete(tileCache.initAsync(
                progressCallback=progressCallback))             

            #
            # Start web server
            #
            progressCallback = \
                lambda current, total: messageQueue.put((MapProxy.ServerStatus.Starting, 'Starting Server', current, total))
            serverStageCount = 2 # TODO: Do something better than hard coding the stage count
            serverStageIndex = 0

            progressCallback(serverStageIndex, serverStageCount)
            serverStageIndex += 1
            requestHandler = proxy.RequestHandler(
                travellerMapUrl=travellerMapUrl,
                installDir=installDir,
                tileCache=tileCache,
                compositor=compositor,
                mainsMilieu=mainsMilieu)
            loop.run_until_complete(requestHandler.initAsync())
            if mainsData:
                # Add static route for mains data        
                requestHandler.addStaticRoute(
                    route='/res/mains.json',
                    data=mainsData,
                    mimeType='application/json')

            # Set up web server with all requests redirected to my handler
            webApp = aiohttp.web.Application(
                middlewares=[_serverHeaderMiddlewareAsync])
            webApp.router.add_route(
                method='*',
                path='/{path:.*?}',
                handler=requestHandler.handleRequestAsync)            
            
            # Only listen on loopback for security. Multiple loopback addresses
            # can be used to allow the client side to round robin requests to
            # different addresses in order to work around the hard coded limit
            # of 6 connections per host enforced by the Chromium browser used by
            # the map widgets.
            hosts = []
            if hostPoolSize:
                for index in range(1, hostPoolSize + 1):
                    hosts.append(f'127.0.0.{index}')
            else:
                hosts.append('127.0.0.1')

            progressCallback(serverStageIndex, serverStageCount)
            serverStageIndex += 1
            loop.run_until_complete(loop.create_server(
                protocol_factory=webApp.make_handler(),
                host=hosts,
                port=listenPort))  

            # Now that set up is finished clear out cached data from that data
            # store to keep the memory footprint down.
            travellermap.DataStore.instance().clearCachedData()

            # Run event loop until proxy is shut down
            messageQueue.put((MapProxy.ServerStatus.Started, )) # Trailing comma is important to keep as a tuple
            progressCallback(serverStageCount, serverStageCount)
            loop.run_until_complete(MapProxy._shutdownMonitorAsync(
                shutdownEvent=shutdownEvent,
                webApp=webApp,
                requestHandler=requestHandler,
                tileCache=tileCache,
                compositor=compositor))

            messageQueue.put((MapProxy.ServerStatus.Stopped, )) # Trailing comma is important to keep as a tuple
            logging.info('Map proxy shutdown complete')
        except Exception as ex:
            logging.error('Exception occurred while running map proxy', exc_info=ex)
            messageQueue.put((MapProxy.ServerStatus.Error, str(ex)))
            loop.run_until_complete(MapProxy._shutdownAsync(
                requestHandler=requestHandler,
                webApp=webApp,
                tileCache=tileCache,
                compositor=compositor))

    async def _shutdownAsync(
            webApp: aiohttp.web.Application,
            requestHandler: proxy.RequestHandler,
            tileCache: proxy.TileCache,
            compositor: proxy.Compositor
            ) -> None:
        # Disable aiohttp logging during shutdown as it can get quite noisy if requests
        # are in progress due. The errors that are generated are expected due to closing
        # the async session used for outgoing connections
        logging.getLogger('aiohttp').setLevel(logging.CRITICAL)

        if requestHandler:
            await requestHandler.shutdownAsync()

        if webApp:
            await webApp.shutdown()
            await webApp.cleanup()

        if tileCache:
            await tileCache.shutdownAsync()

        if compositor:
            await compositor.shutdownAsync()

    async def _shutdownMonitorAsync(
            shutdownEvent: multiprocessing.Event,
            webApp: aiohttp.web.Application,
            requestHandler: proxy.RequestHandler,
            tileCache: proxy.TileCache,
            compositor: proxy.Compositor
            ) -> None:
        while True:
            await asyncio.sleep(0.5)
            if shutdownEvent.is_set():
                await MapProxy._shutdownAsync(
                    requestHandler=requestHandler,
                    webApp=webApp,
                    tileCache=tileCache,
                    compositor=compositor)
                return
