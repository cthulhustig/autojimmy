import cartographer
import multiverse
import re
import survey
import typing

# Useful Test Locations:
# - Sector: Tsebntsiatldlants
#   - There is a route that runs the length of it that should be dashed purple. The
#     colour and style come from it using the "Core Route" type which is the only
#     type defined in the otu css file that has a space in the name
# - Sector: Glimmerdrift Reaches (Judges Guild)
#   - A lot of the borders in this sector use a dashed salmon pink colour. They get
#     this from the default border colour in the metadata style sheet info (i.e.
#     not the otu css file)
#   - Some of the routes are extra chunky because they use the Special type which
#     has a custom width defined in the metadata style sheet info
# - Sector: Far Frontiers
#   - The routes for the worlds around Bestus should be grey, not green. They can
#     get go wrong if the order the style sheet groups are looked up are messed up
# -  Vanguard Reaches (Don McKinney 2015)
#   - There is a red route running vertically (e.g. through Cloister) that gets
#     its colour from the allegiance of Im on the route and the custom colour
#     specified for Im in the metadata style sheet info
#   - This is also a very colourful sector with lots of different borders and
#     regions
# - Sector: Far Home
#   - Routes in this sector have a custom default colour specified in the metadata
#     stylesheet info

# TODO: I think it might be possible to move all the processing this is
# used for to conversion time. It probably means allegiances in the DB
# need to store route/border colour/style info. I suspect I'll also need
# to have some kind of RouteType that is stored at the sector level in
# a similar way to allegiances to store the route/border colour/style info
# for the different route types styles stored in otu.css

class StyleStore(object):
    # Route and border style sheet regexes. Note that the names that follow
    # the . can contain spaces
    _BorderPattern = re.compile(r'border(?:\.(.+))?')
    _RoutePattern = re.compile(r'route(?:\.(.+))?')

    _DefaultStylePath = 'styles/otu.css'

    _StyleMap = {
        'solid': cartographer.LineStyle.Solid,
        'dashed': cartographer.LineStyle.Dash,
        'dotted': cartographer.LineStyle.Dot}

    def __init__(self):
        self._borderStyles: typing.Dict[
            typing.Optional[str], # Border group from CSS file or None for default values
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[cartographer.LineStyle] # Style
            ]] = {}
        self._routeStyles: typing.Dict[
            typing.Optional[str], # Route group from CSS file or None for default values
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[cartographer.LineStyle], # Style
                typing.Optional[float] # Width
            ]] = {}

        content = survey.readCssContent(
            multiverse.SnapshotManager.instance().loadTextResource(
                filePath=StyleStore._DefaultStylePath))
        for group, properties in content.items():
            match = StyleStore._BorderPattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleStore._StyleMap.get(style.lower())
                self._borderStyles[key] = (colour, style)

            match = StyleStore._RoutePattern.match(group)
            if match:
                key = match.group(1)
                colour = properties.get('color')
                style = properties.get('style')
                if style:
                    style = StyleStore._StyleMap.get(style.lower())
                width = properties.get('width')
                if width:
                    width = float(width)
                self._routeStyles[key] = (colour, style, width)

    def hasBorderStyle(self, key: typing.Optional[str]) -> bool:
        return key in self._borderStyles

    def borderStyle(self, key: typing.Optional[str]) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[cartographer.LineStyle]]:
        return self._borderStyles.get(key, (None, None))

    def hasRouteStyle(self, key: typing.Optional[str]) -> bool:
        return key in self._routeStyles

    def routeStyle(self, key: typing.Optional[str]) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[cartographer.LineStyle],
            typing.Optional[float]]: # Width
        return self._routeStyles.get(key, (None, None, None))
