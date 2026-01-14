import re
import survey
import typing

# Route and border style sheet regexes. Note that the names that follow
# the . can contain spaces
_BorderStylePattern = re.compile(r'border(?:\.(.+))?')
_RouteStylePattern = re.compile(r'route(?:\.(.+))?')

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
