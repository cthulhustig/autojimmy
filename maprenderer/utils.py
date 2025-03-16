import math
import travellermap
import typing

def loadTabFile(path: str) -> typing.Tuple[
        typing.List[str], # Headers
        typing.List[typing.Dict[
            str, # Header
            str]]]: # Value
    with open(path, 'r', encoding='utf-8-sig') as file:
        header = None
        rows = []
        for line in file.readlines():
            if not line:
                continue
            if line.startswith('#'):
                continue
            tokens = [t.strip() for t in line.split('\t')]
            if not header:
                header = tokens
                continue

            rows.append({header[i]:t for i, t in enumerate(tokens)})
    return (header, rows)

def makeAlphaColor(
        alpha: typing.Union[float, int],
        color: str
        ) -> str:
    red, green, blue, _ = travellermap.parseHtmlColor(htmlColor=color)

    alpha = int(alpha)
    if alpha < 0:
        alpha = 0
    if alpha > 255:
        alpha =255

    return f'#{alpha:02X}{red:02X}{green:02X}{blue:02X}'
