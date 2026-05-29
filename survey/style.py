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
            reporter.addMessage('Ignoring invalid Line Style "{string}"')
        return None
    return lower

def formatLineStyleString(
        style: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = style.lower()
    if lower not in _ValidLineStyles:
        if reporter:
            reporter.addMessage('Ignoring invalid Line Style "{string}"')
        return None
    return lower

def parseLabelSizeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = string.lower()
    if lower not in _ValidLabelSizes:
        if reporter:
            reporter.addMessage('Ignoring invalid Label Size "{string}"')
        return None
    return lower

def formatLineStyleString(
        style: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    lower = style.lower()
    if lower not in _ValidLabelSizes:
        if reporter:
            reporter.addMessage('Ignoring invalid Line Style "{string}"')
        return None
    return lower

def parseHtmlColourString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if not common.isValidHtmlColour(string):
        if reporter:
            reporter.addMessage('Ignoring invalid HTML Colour "{string}"')
        return None
    return string

def formatHtmlColourString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if not common.isValidHtmlColour(string):
        if reporter:
            reporter.addMessage('Ignoring invalid HTML Colour "{string}"')
        return None
    return string

def parseStyleSheet(
        content: str
        ) -> survey.RawStyleSheet:
    routeStyles: typing.List[survey.RawRouteStyle] = []
    borderStyles: typing.List[survey.RawBorderStyle] = []
    styles = survey.readCssContent(content)

    for styleKey, properties in styles.items():
        match = _BorderStylePattern.match(styleKey)
        if match:
            tag = match.group(1)
            colour = properties.get('color')
            style = properties.get('style')
            if colour is not None or style is not None:
                borderStyles.append(survey.RawBorderStyle(
                    tag=tag,
                    colour=colour,
                    style=style))

        match = _RouteStylePattern.match(styleKey)
        if match:
            tag = match.group(1)
            colour = properties.get('color')
            style = properties.get('style')
            width = properties.get('width')
            if width is not None:
                width = float(width)
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