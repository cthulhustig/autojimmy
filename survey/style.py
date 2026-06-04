import common
import re
import survey
import typing

_ValidLineStyles = set(['solid', 'dashed', 'dotted'])
_ValidLabelSizes = set(['small', 'large'])

# Route and border style sheet regexes. Note that the names that follow
# the . can contain spaces
_BorderStylePattern = re.compile(r'border(?:\.(.+))?')
_RouteStylePattern = re.compile(r'route(?:\.(.+))?')

def parseLineStyleString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = string.lower()
    if lower not in _ValidLineStyles:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Line Style "{string}"')
        return None
    return lower

def formatLineStyleString(
        style: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = style.lower()
    if lower not in _ValidLineStyles:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Line Style "{style}"')
        return None
    return lower

def parseLineWidthString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[float]:
    try:
        width = float(string)
    except:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Line width "{string}"')
        return None

    if width < 0:
        if reporter:
            reporter.addMessage(f'Ignoring negative Line Width "{width}"')
        return None

    return width

def formatLineWidthString(
        width: float,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if width < 0:
        if reporter:
            reporter.addMessage(f'Ignoring negative Line Width "{width}"')
        return None

    return str(width)

def parseLabelSizeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = string.lower()
    if lower not in _ValidLabelSizes:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Label Size "{string}"')
        return None
    return lower

def formatLabelSizeString(
        size: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = size.lower()
    if lower not in _ValidLabelSizes:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Label Size "{size}"')
        return None
    return lower

def parseHtmlColourString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if not common.isValidHtmlColour(string):
        if reporter:
            reporter.addMessage(f'Ignoring invalid HTML Colour "{string}"')
        return None
    return string

def formatHtmlColourString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if not common.isValidHtmlColour(string):
        if reporter:
            reporter.addMessage(f'Ignoring invalid HTML Colour "{string}"')
        return None
    return string

def parseStyleSheet(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> survey.RawStyleSheet:
    routeStyles: typing.List[survey.RawRouteStyle] = []
    borderStyles: typing.List[survey.RawBorderStyle] = []
    styles = survey.readCssContent(content)

    for styleKey, properties in styles.items():
        match = _BorderStylePattern.match(styleKey)
        if match:
            tag = match.group(1)

            colour = properties.get('color')
            if colour is not None:
                colour = survey.parseHtmlColourString(
                    string=colour,
                    reporter=reporter)

            style = properties.get('style')
            if style is not None:
                style = survey.parseLineStyleString(
                    string=style,
                    reporter=reporter)

            if colour is not None or style is not None:
                borderStyles.append(survey.RawBorderStyle(
                    tag=tag,
                    colour=colour,
                    style=style))

        match = _RouteStylePattern.match(styleKey)
        if match:
            tag = match.group(1)

            colour = properties.get('color')
            if colour is not None:
                colour = survey.parseHtmlColourString(
                    string=colour,
                    reporter=reporter)

            style = properties.get('style')
            if style is not None:
                style = survey.parseLineStyleString(
                    string=style,
                    reporter=reporter)

            width = properties.get('width')
            if width is not None:
                width = survey.parseLineWidthString(
                    string=width,
                    reporter=reporter)

            if colour is not None or style is not None or width is not None:
                routeStyles.append(survey.RawRouteStyle(
                    tag=tag,
                    colour=colour,
                    style=style,
                    width=width))

    return survey.RawStyleSheet(
        routeStyles=routeStyles,
        borderStyles=borderStyles)

def validateMandatoryLineStyle(
        name: str,
        value: str
        ) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value.lower(),
        allowed=_ValidLineStyles)

def validateOptionalLineStyle(
        name: str,
        value: typing.Optional[str]
        ) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value.lower() if value is not None else None,
        allowed=_ValidLineStyles)

def validateMandatoryLineWidth(
        name: str,
        value: float
        ) -> float:
    return common.validateMandatoryFloat(
        name=name,
        value=value,
        min=0)

def validateOptionalLineWidth(
        name: str,
        value: typing.Optional[float]
        ) -> typing.Optional[float]:
    return common.validateOptionalFloat(
        name=name,
        value=value,
        min=0)

def validateMandatoryLabelSize(
        name: str,
        value: str
        ) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value.lower(),
        allowed=_ValidLabelSizes)

def validateOptionalLabelSize(
        name: str,
        value: typing.Optional[str]
        ) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value.lower() if value is not None else None,
        allowed=_ValidLabelSizes)

def validateMandatoryHtmlColour(
        name: str,
        value: str
        ) -> str:
    return common.validateMandatoryHtmlColour(
        name=name,
        value=value)

def validateOptionalHtmlColour(
        name: str,
        value: typing.Optional[str]
        ) -> typing.Optional[str]:
    return common.validateOptionalHtmlColour(
        name=name,
        value=value)