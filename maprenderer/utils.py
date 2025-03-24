import travellermap
import typing

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
