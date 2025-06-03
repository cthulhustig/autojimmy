import logic
import typing

class OutcomeColours(object):
    @typing.overload
    def __init__(
            self,
            averageCaseColour: str,
            worstCaseColour: str,
            bestCaseColour: str
            ) -> None: ...
    @typing.overload
    def __init__(self, other: 'OutcomeColours' ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, OutcomeColours):
                raise TypeError('The other parameter must be an RollOutcomeColours')
            self._colourMap = dict(other._colourMap)
        else:
            self._colourMap = {
                logic.RollOutcome.AverageCase: args[0] if len(args) > 0 else kwargs['averageCaseColour'],
                logic.RollOutcome.WorstCase: args[0] if len(args) > 0 else kwargs['worstCaseColour'],
                logic.RollOutcome.BestCase: args[0] if len(args) > 0 else kwargs['bestCaseColour']}

    def colour(self, outcome: logic.RollOutcome) -> str:
        return self._colourMap[outcome]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OutcomeColours):
            return False
        return self._colourMap == other._colourMap
