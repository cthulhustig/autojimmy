import astronomer
import common
import survey
import typing

class BorderLabel(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            worldX: float,
            worldY: float,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            text: typing.Optional[str] = None,
            show: bool = True,
            wrap: bool = False
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        common.validateObject(name='allegiance', value=allegiance, objectType=astronomer.Allegiance, allowNone=True)
        common.validateStr(name='text', value=text, allowEmpty=True, allowNone=True)
        common.validateBool(name='show', value=show)
        common.validateBool(name='wrap', value=wrap)

        self._worldX = worldX
        self._worldY = worldY
        self._allegiance = allegiance
        self._text = text
        self._show = show
        self._wrap = wrap

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def text(self) -> typing.Optional[str]:
        return self._text

    def show(self) -> bool:
        return self._show

    def wrap(self) -> bool:
        return self._wrap

class Border(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            labels: typing.Optional[typing.Collection[BorderLabel]] = None,
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateSequence(name='hexes', value=hexes, elementType=astronomer.HexPosition, allowEmpty=False)
        common.validateObject(name='allegiance', value=allegiance, objectType=astronomer.Allegiance, allowNone=True)
        common.validateObject(name='style', value=style, objectType=astronomer.LineStyle, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateCollection(name='labels', value=labels, elementType=BorderLabel, allowEmpty=True, allowNone=True)

        self._hexes = list(hexes)
        self._allegiance = allegiance
        self._style = style
        self._colour = colour
        self._labels = list(labels) if labels is not None else None
        self._outline: typing.Optional[typing.List[typing.Tuple[float, float]]] = None
        self._outlines: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

    def hexes(self) -> typing.Iterable[astronomer.HexPosition]:
        return self._hexes

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def labels(self) -> typing.Optional[typing.Collection[BorderLabel]]:
        return common.ConstCollectionRef(self._labels) if self._labels is not None else None

    def worldPath(self) -> typing.Iterable[typing.Tuple[float, float]]:
        if self._outline is not None:
            return common.ConstSequenceRef(self._outline)

        self._outline = astronomer.regionHexPathToWorldSpaceOutline(self._hexes)
        return common.ConstSequenceRef(self._outline)

    def worldOutlines(self) -> typing.Collection[typing.Sequence[astronomer.HexPosition]]:
        if self._outlines is not None:
            return common.ConstCollectionRef(self._outlines)

        hexCount = len(self._hexes)
        if hexCount > 1 and self._hexes[0] == self._hexes[-1]:
            # Ignore the last hex if it's just looping back to the original hex
            # as the algorithm does that automatically
            hexCount -= 1

        self._outlines = []

        if hexCount == 1:
            self._outlines.append(self.worldPath())
            return self._outlines

        outline, holes = astronomer.decomposeHexPath(self._hexes)

        self._outlines.append(astronomer.regionHexPathToWorldSpaceOutline(outline))

        if holes:
            for hole in holes:
                self._outlines.append(astronomer.regionHexPathToWorldSpaceOutline(hole))

        return self._outlines
