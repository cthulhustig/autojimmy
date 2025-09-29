import cartographer
import common
import multiverse
import typing

def makeAlphaColour(
        alpha: typing.Union[float, int],
        colour: str,
        isNormalised: bool = False
        ) -> str:
    red, green, blue, _ = common.parseHtmlColour(htmlColour=colour)

    if isNormalised:
        alpha *= 255

    alpha = int(round(alpha))
    if alpha < 0:
        alpha = 0
    if alpha > 255:
        alpha = 255

    return f'#{alpha:02X}{red:02X}{green:02X}{blue:02X}'
