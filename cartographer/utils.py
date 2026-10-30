import common
import re
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

# Pattern used by Traveller Map to replace white space with '\n' to do
# wrapping of basic labels and the labels used on borders and regions. It
# works by putting '\n' between words that start with upper case letters,
# e.g. "Hegemony of Lorean" becomes "Hegemony of\nLorean"
_TextWrapPattern = re.compile(r'\s+(?![a-z])')
def wrapLabelText(text: str) -> str:
    return _TextWrapPattern.sub('\n', text)