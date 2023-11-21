import aiohttp.web
import io
import logging
import multidict
import PIL.Image
import PIL.ImageDraw
import proxy
import travellermap
import urllib.error
import urllib.parse
import urllib.request
import typing

class RequestHandler(object):
    class _StaticRouteData(object):
        def __init__(
                self,
                route: str,
                data: typing.Union[str, bytes],
                mimeType: str
                ) -> None:
            self._route = route
            self._data = data
            self._mimeType = mimeType

        def route(self) -> str:
            return self._route
        
        def data(self) -> typing.Union[str, bytes]:
            return self._data
        
        def mimeType(self) -> str:
            return self._mimeType

    # By default the aiohttp ClientSession connection pool seems to keep connections alive for ~15 seconds.
    # I'm overriding this to make navigation of the map more responsive
    _ConnectionKeepAliveSeconds = 60

    def __init__(
            self,
            travellerMapUrl: str,
            tileCache: proxy.TileCache,
            compositor: typing.Optional[proxy.Compositor],
            mainsMilieu: typing.Optional[travellermap.Milieu]
            ) -> None:
        super().__init__()
        self._travellerMapUrl = travellerMapUrl
        self._tileCache = tileCache
        self._compositor = compositor
        self._mainsMilieu = mainsMilieu
        self._staticRoutes: typing.Dict[str, RequestHandler._StaticRouteData] = {}

        # As far as I can tell connection reuse requires HTTP/2 which in turns requires
        # SSL (https://caniuse.com/http2). I was seeing exceptions when using my local
        # Traveller Map over HTTP but not when accessing the main site over HTTPS.
        parsedUrl = urllib.parse.urlparse(travellerMapUrl)
        if parsedUrl.scheme.lower() == 'https':
            self._connector = aiohttp.TCPConnector(
                keepalive_timeout=RequestHandler._ConnectionKeepAliveSeconds)
        else:            
            self._connector = aiohttp.TCPConnector(force_close=True)

        self._session = aiohttp.ClientSession(connector=self._connector)

    def addStaticRoute(
            self,
            route: str,
            data: typing.Union[str, bytes],
            mimeType: typing.Optional[str] = None
            ) -> None:
        self._staticRoutes[route] = RequestHandler._StaticRouteData(
            route=route,
            data=data,
            mimeType=mimeType)        

    async def shutdownAsync(self) -> None:
        if self._session:
            await self._session.close()

    async def handleRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        # TODO: I should probably use the local copies of sophont and allegiance files for those requests
        if request.path in self._staticRoutes:
            return await self._handleStaticRouteRequestAsync(request)
        elif request.path == '/api/tile':
            return await self._handleTileRequestAsync(request)
        elif request.path == '/res/mains.json':
            return await self._handleMainsRequestAsync(request)
        else:
            # Act as a proxy for all other requests and just forward them to the
            # configured Traveller Map instance
            return await self._handleProxyRequestAsync(request)

    async def _handleStaticRouteRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        logging.debug(f'Serving static content for {request.path}')

        staticData = self._staticRoutes.get(request.path)
        if not staticData:
            raise RuntimeError(f'Failed to find static content for {request.path}')        

        body = staticData.data()
        contentType = staticData.mimeType()
        headers = {
            'Content-Length': str(len(body)),
            'Cache-Control': 'no-store, no-cache', # Don't cache locally served files
            'Content-Type': contentType}

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=body) 

    # NOTE: It's important that this function tries it's best to return something. If compositing
    # fails it should return the default tile
    async def _handleTileRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        tileImage = None
        try:
            tileImage = await self._tileCache.lookupAsync(tileQuery=request.query_string)
        except Exception as ex:
            # Log this at a low level as it could happen a LOT if something goes wrong
            # TODO: This should be logging at debug as it could get very spammy
            logging.info(
                f'Error occurred when looking up tile {request.query_string} in tile cache',
                exc_info=ex)
            # Continue so tile is still generated

        shouldCacheTile = True
        overlapType = None
        if tileImage:
            logging.debug(f'Serving cached response for tile {request.query_string}')
            tileBytes = tileImage.bytes()
            contentType = travellermap.mapFormatToMimeType(tileImage.format())
            shouldCacheTile = False # Already in the cache so no need to add
        else:
            logging.debug(f'Creating tile for {request.query_string}')

            tileX = float(request.query['x'])
            tileY = float(request.query['y'])
            tileScale = float(request.query['scale'])
            tileWidth = int(request.query.get('w', 256))
            tileHeight = int(request.query.get('h', 256))
            milieu = str(request.query.get('milieu', 'M1105'))
            style = str(request.query.get('style', 'poster'))
            if milieu.upper() in travellermap.Milieu.__members__:
                milieu = travellermap.Milieu.__members__[milieu]
            else:
                milieu = travellermap.Milieu.M1105

            if self._compositor:
                overlapType = self._compositor.overlapType(
                    tileX=tileX,
                    tileY=tileY,
                    tileScale=tileScale,
                    milieu=milieu)
            else:
                overlapType = proxy.Compositor.OverlapType.NoOverlap

            if overlapType != proxy.Compositor.OverlapType.CompleteOverlap:
                # Request the tile from Traveller Map. If it's a partial overlap request an SVG so
                # the text can be processed to avoid truncation by overlaid sectors
                tileBytes, contentType, sourceFormat = await self._makeTileRequestAsync(request)

                # Set the target format, by default the source format is used, this can be None if we
                # got something unexpected back from Traveller Map. In that case the tile will be
                # returned as is (using the content type string returned with the tile). If the tile
                # is an SVG set the target format to the best type for the style and update the content
                # type string to match
                targetFormat = sourceFormat
                if sourceFormat == travellermap.MapFormat.SVG:
                    targetFormat = travellermap.MapFormat.JPEG if style == 'candy' else travellermap.MapFormat.PNG
                    contentType = travellermap.mapFormatToMimeType(targetFormat)

                # No tile data shouldn't really happen and there's nothing we can do to return something
                # usable. Making this check is important as, if it was to happen, it prevents code later
                # from re-making the request
                if not tileBytes:
                    raise RuntimeError('Proxied tile request returned no data')
            else:
                # The tile is completely overlapped by a custom sector so there is no need to request the tile
                # from Traveller Map. This also means there is no source format. Set the target format to the
                # best type for the style and update the content string accordingly
                tileBytes = None
                sourceFormat = None
                targetFormat = travellermap.MapFormat.JPEG if style == 'candy' else travellermap.MapFormat.PNG
                contentType = travellermap.mapFormatToMimeType(targetFormat)

            if targetFormat and (overlapType != proxy.Compositor.OverlapType.NoOverlap):
                tileImage = None
                try:
                    if overlapType == proxy.Compositor.OverlapType.PartialOverlap:
                        tileImage = PIL.Image.open(io.BytesIO(tileBytes))
                        await self._compositor.partialOverlapAsync(
                            tileImage=tileImage,
                            tileX=tileX,
                            tileY=tileY,
                            tileWidth=tileWidth,
                            tileHeight=tileHeight,
                            tileScale=tileScale,
                            milieu=milieu)
                    else:
                        assert(overlapType == proxy.Compositor.OverlapType.CompleteOverlap)
                        tileImage = await self._compositor.fullOverlapAsync(
                            tileX=tileX,
                            tileY=tileY,
                            tileScale=tileScale,
                            milieu=milieu)

                    if tileImage != None:
                        if (targetFormat == travellermap.MapFormat.JPEG) and (tileImage.mode == 'RGBA'):
                            # JPEG doesn't support alpha and Image.save doesn't just ignore it :(
                            rgbImage = tileImage.convert('RGB')
                            del tileImage
                            tileImage = rgbImage

                        newBytes = io.BytesIO()
                        tileImage.save(newBytes, format=targetFormat.value)
                        newBytes.seek(0)
                        tileBytes = newBytes.read()
                except Exception as ex:
                    # Log this at a low level as it could happen a LOT if something goes wrong
                    # TODO: This should be logging at debug as it could get very spammy
                    logging.warning('Failed to composite tile', exc_info=ex)
                    shouldCacheTile = False # Don't cache tiles if they failed to generate
                finally:
                    if tileImage:
                        del tileImage
            else:
                logging.debug(f'Serving live response for tile {request.query_string}')

            if not tileBytes:
                # If we get to here with no tile bytes it means something wen't wrong performing a simple
                # copy. In this situation the only real option is to request the tile from Traveller Map and
                # return that
                logging.debug(f'Requesting fallback tile for {request.query_string}')
                tileBytes, contentType, targetFormat = await self._makeTileRequestAsync(request)
                shouldCacheTile = False # Don't cache tile when using a fallback tile
                if not tileBytes:
                    # We're having a bad day, something also wen't wrong getting the tile from Traveller
                    # Map. Not much to do apart from bail
                    raise RuntimeError(f'Proxied tile request returned no data for tile {request.query_string}')

            # Add the tile to the cache. Depending on the logic above this could either be a tile
            # as-is from Traveller Map or a composite tile
            if shouldCacheTile and tileBytes and targetFormat and overlapType:
                tileImage = travellermap.MapImage(
                    bytes=tileBytes,
                    format=targetFormat)
                await self._tileCache.addAsync(
                    tileQuery=request.query_string,
                    tileImage=tileImage,
                    overlapType=overlapType)

            # Enable this to add a red boundary to all tiles in order to highlight where they are
            # NOTE: This code should always be after tiles are added to the cache as we don't want
            # to write tiles with the border to the disk cache
            """
            if targetFormat:
                colour = 'red'
                with PIL.Image.open(tileBytes if isinstance(tileBytes, io.BytesIO) else io.BytesIO(tileBytes)) as image:
                    draw = PIL.ImageDraw.Draw(image)
                    draw.line([(0, 0), (0, image.height - 1)], fill=colour, width=0)
                    draw.line([(0, image.height - 1), (image.width - 1, image.height - 1)], fill=colour, width=0)
                    draw.line([(image.width - 1, image.height - 1), (image.width - 1, 0)], fill=colour, width=0)
                    draw.line([(image.width - 1, 0), (0, 0)], fill=colour, width=0)
                    tileBytes = io.BytesIO()
                    image.save(tileBytes, format=targetFormat.value)
                    tileBytes.seek(0)
                    tileBytes = tileBytes.read()
            """                

        headers = {
            'Content-Length': str(len(tileBytes) if tileBytes else 0),
            # Tell the client not to cache tiles. Assuming the browser respects the request, it
            # should prevent stale tiles being displayed if the user modifies data
            'Cache-Control': 'no-store, no-cache'}
        if contentType:
            headers['Content-Type'] = contentType

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=tileBytes)

    async def _handleMainsRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        mainsData = None
        if self._mainsMilieu:
            try:
                # TODO: Ideally this would be async
                mainsData = travellermap.DataStore.instance().mainsData(
                    milieu=self._mainsMilieu)
                if not mainsData:
                    raise RuntimeError('Empty mains data returned')
            except Exception as ex:
                logging.error(f'Failed to retrieve mains data from data store', exc_info=ex)
                # Continue to fall back to traveller map

        if not mainsData:
            return await self._handleProxyRequestAsync(
                request=request,
                # Allow browser to cache it for the session but not store it on disk
                forceCacheControl='no-store')
        mainsData = mainsData.encode()

        logging.debug(f'Serving local mains data')

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': str(len(mainsData)),
            # Tell the client not to cache tiles. Assuming the browser respects the request, it
            # should prevent stale tiles being displayed if the user modifies data
            'Cache-Control': 'no-store, no-cache'}

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=mainsData)        

    _ProxyRequestCopyHeaders = [
        'Content-Type',
        'Cache-Control'
    ]
    async def _handleProxyRequestAsync(
            self,
            request: aiohttp.web.Request,
            forceCacheControl: typing.Optional[str] = None
            ) -> aiohttp.web.Response:
        status, reason, headers, body = await self._makeProxyRequestAsync(request)

        responseHeaders = {'Content-Length': str(len(body))}
        for header in RequestHandler._ProxyRequestCopyHeaders:
            if header in headers:
                responseHeaders[header] = headers[header]

        if forceCacheControl: # if forceCacheControl is an empty string, don't add the header
            responseHeaders['Cache-Control'] = forceCacheControl            

        return aiohttp.web.Response(
            status=status,
            reason=reason,
            headers=responseHeaders,
            body=body)

    async def _makeTileRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> typing.Tuple[bytes, str, typing.Optional[travellermap.MapFormat]]:
        status, reason, headers, body = await self._makeProxyRequestAsync(request)
        if status != 200:
            raise RuntimeError(f'Request for tile {request.query_string} filed (status: {status}, reason: {reason})')

        contentType = headers.get('Content-Type')
        tileFormat = travellermap.mimeTypeToMapFormat(contentType)
        if not tileFormat:
            # Log this at debug as it could happen a lot if something goes wrong
            logging.debug(f'Request for tile {request.query_string} returned unexpected Content-Type {contentType}')

        return body, contentType, tileFormat

    async def _makeProxyRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> typing.Tuple[
                int, # Status code
                str, # Reason
                multidict.CIMultiDict, # Headers
                bytes: # Body
                ]:
        targetUrl = urllib.parse.urljoin(self._travellerMapUrl, request.path)
        query = request.query
        body = await request.read()

        # The headers from the incoming request are used as the headers for the outgoing request.
        # The Host header should be removed if present as, if it's passed on, Traveller Map doesn't
        # like the fact it's set to the address of the proxy
        headers = request.headers
        if 'Host' in headers:
            headers = headers.copy()
            del headers['Host']

        async with self._session.request(request.method, targetUrl, headers=headers, params=query, data=body) as response:
            body = await response.read()
            headers = response.headers.copy()
            if response.content_type:
                headers['Content-Type'] = response.content_type
            return (response.status, response.reason, headers, body)