import logic
import typing

class TaggingColours(object):
    @typing.overload
    def __init__(
        self,
        desirableColour: str,
        warningColour: str,
        dangerColour: str
        ) -> None: ...

    @typing.overload
    def __init__(self, other: 'TaggingColours' ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, TaggingColours):
                raise TypeError('The other parameter must be an TaggingColours')
            self._colourMap = dict(other._colourMap)
        else:
            self._colourMap = {
                logic.TagLevel.Desirable: args[0] if len(args) > 0 else kwargs['desirableColour'],
                logic.TagLevel.Warning: args[1] if len(args) > 1 else kwargs['warningColour'],
                logic.TagLevel.Danger: args[2] if len(args) > 2 else kwargs['dangerColour']}

    def colour(self, level: logic.TagLevel) -> str:
        return self._colourMap[level]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaggingColours):
            return False
        return self._colourMap == other._colourMap
