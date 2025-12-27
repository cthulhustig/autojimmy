import re
import survey
import typing

# Route and border style sheet regexes. Note that the names that follow
# the . can contain spaces
_BorderStylePattern = re.compile(r'border(?:\.(.+))?')
_RouteStylePattern = re.compile(r'route(?:\.(.+))?')

def parseSectorStyleSheet(
        content: str
        ) -> typing.Tuple[
            # Border Styles
            typing.Dict[
                str, # Allegiance/Type
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str] # Style
                ]],
            # Route Styles
            typing.Dict[
                str, # Allegiance/Type
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str], # Style
                    typing.Optional[float] # Width
                ]]]:
    borderStyleMap: typing.Dict[
        str, # Allegiance/Type
        typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[str] # Style
        ]] = {}
    routeStyleMap: typing.Dict[
        str, # Allegiance/Type
        typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[str], # Style
            typing.Optional[float] # Width
        ]] = {}
    styles = survey.readCssContent(content)

    for styleKey, properties in styles.items():
        match = _BorderStylePattern.match(styleKey)
        if match:
            tag = match.group(1)
            colour = properties.get('color')
            style = properties.get('style')
            if colour or style:
                borderStyleMap[tag] = (colour, style)

        match = _RouteStylePattern.match(styleKey)
        if match:
            tag = match.group(1)
            colour = properties.get('color')
            style = properties.get('style')
            width = properties.get('width')
            if width:
                width = float(width)
            if colour or style or width:
                routeStyleMap[tag] = (colour, style, width)

    return (borderStyleMap, routeStyleMap)
