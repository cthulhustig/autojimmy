import maprenderer
import os
import re
import travellermap
import typing

class DefaultStyleCache(object):
    _BorderPattern = re.compile(r'border\.(\w+)')
    _RoutePattern = re.compile(r'route\.(\w+)')
    _DefaultStylePath = 'res/styles/otu.css'

    _StyleMap = {
        'solid': maprenderer.LineStyle.Solid,
        'dashed': maprenderer.LineStyle.Dash,
        'dotted': maprenderer.LineStyle.Dot}

    def __init__(self, basePath: str):
        self._borderStyles = {}
        self._routeStyles = {}

        content = travellermap.readCssFile(
            os.path.join(basePath, DefaultStyleCache._DefaultStylePath))
        for group, properties in content.items():
            match = DefaultStyleCache._BorderPattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._StyleMap.get(style.lower())
                self._borderStyles[key] = (color, style)

            match = DefaultStyleCache._RoutePattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._StyleMap.get(style.lower())
                width = properties.get('width')
                if width:
                    width = float(width)
                self._routeStyles[key] = (color, style, width)

    def defaultBorderStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[maprenderer.LineStyle]]:
        return self._borderStyles.get(key, (None, None))

    def defaultRouteStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[maprenderer.LineStyle],
            typing.Optional[float]]: # Width
        return self._routeStyles.get(key, (None, None, None))