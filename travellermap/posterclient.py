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
            mapUrl: str,
            sectorData: str,
            sectorMetadata: typing.Optional[str] = None,
            style: travellermap.Style = travellermap.Style.Poster,
            options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
            compositing: bool = True
            ) -> None:
        self._mapUrl = mapUrl
        self._sectorData = sectorData
        self._metaData = sectorMetadata
        self._style = style
        self._options = options
        self._compositing = compositing

    def makePoster(
            self,
            linearScale: float # Pixels per parsec
            ) -> bytes:
        url = travellermap.formatPosterUrl(
            baseMapUrl=self._mapUrl,
            style=self._style,
            options=self._options,
            linearScale=linearScale,
            compositing=self._compositing,
            minimal=True)

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
