import logging
import time
import travellermap
import typing
import urllib.error
import urllib.parse
import urllib.request

class PosterClient(object):
    def __init__(
            self,
            mapBaseUrl: str,
            mapProxyPort: int,
            sectorData: str,
            metaData: typing.Optional[str] = None,
            style: travellermap.Style = travellermap.Style.Poster,
            options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
            compositing: bool = True
            ) -> None:
        self._mapBaseUrl = mapBaseUrl
        self._mapProxyPort = mapProxyPort
        self._sectorData = sectorData
        self._metaData = metaData
        self._style = style
        self._options = options
        self._compositing = compositing

    def makePoster(
            self,
            linearScale: float # Pixels per parsec
            ) -> bytes:
        # TODO: This logic is duplicated in a few places, should consolidate. I don't think
        # this actually needs both, could just have the required base url (proxy or direct)
        # passed in from a higher level
        if self._mapProxyPort:
            baseUrl = f'http://127.0.0.1:{self._mapProxyPort}'
        else:
            baseUrl = self._mapBaseUrl

        url = travellermap.formatPosterUrl(
            baseMapUrl=baseUrl,
            style=self._style,
            options=self._options,
            linearScale=linearScale,
            compositing=self._compositing)
        
        # Leave this enabled to catch bugs that are causing LOTS of requests
        logging.info(f'Requesting poster {url}')

        startTime = time.time()        
        
        data = {'data': self._sectorData}
        if self._metaData:
            data['metadata'] = self._metaData
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data).encode())
        
        try:
            with urllib.request.urlopen(request) as response:
                content = response.read()
        except urllib.error.HTTPError as ex:
            raise RuntimeError(f'Poster request failed for {url} ({ex.reason})') from ex
        except urllib.error.URLError as ex:
            if isinstance(ex.reason, TimeoutError):
                raise TimeoutError(f'Poster request timeout for {url}') from ex
            raise RuntimeError(f'Poster request failed for {url} ({ex.reason})') from ex
        except Exception as ex:
            raise RuntimeError(f'Poster request failed for {url} ({ex})') from ex
        
        downloadTime = time.time() - startTime
        logging.debug(f'Generation of poster {url} took {downloadTime}s')

        return content
