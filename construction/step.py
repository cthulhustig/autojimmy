import common
import enum
import construction
import typing

# Construction implementations should create an enum derived from this class
# with entries for each of the costs that a component can have (e.g. credits,
# weight). The value of the entry should be the human readable name of the
# attribute to be displayed to the user
class ConstructionCost(enum.Enum):
    pass

class ConstructionStep(object):
    def __init__(
            self,
            name: str,
            type: str,
            costs: typing.Optional[typing.Mapping[ConstructionCost, construction.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[construction.FactorInterface]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        self._name = name
        self._type = type
        self._costs = dict(costs) if costs != None else {}
        self._factors = list(factors) if factors != None else []
        self._notes = list(notes) if notes != None else []

    def name(self) -> str:
        return self._name

    def type(self) -> str:
        return self._type

    def cost(
            self,
            costId: ConstructionCost
            ) -> typing.Optional[construction.NumericModifierInterface]:
        return self._costs.get(costId)

    def setCost(
            self,
            costId: ConstructionCost,
            value: construction.NumericModifierInterface
            ) -> None:
        self._costs[costId] = value

    def costs(self) -> typing.Mapping[ConstructionCost, construction.NumericModifierInterface]:
        return self._costs

    def factors(self) -> typing.Iterable[construction.FactorInterface]:
        return self._factors

    def addFactor(
            self,
            factor: construction.FactorInterface
            ) -> None:
        self._factors.append(factor)

    def notes(self) -> typing.Iterable[str]:
        return self._notes

    def addNote(
            self,
            note: str
            ) -> None:
        self._notes.append(note)

    @staticmethod
    def calculateSequenceCost(
            costId: ConstructionCost,
            steps: typing.Iterable['ConstructionStep']
            ) -> typing.Optional[common.ScalarCalculation]:
        total = construction.calculateNumericModifierSequence(
            modifiers=[step.cost(costId=costId) for step in steps if step.cost(costId=costId)])
        if not total:
            return None
        return common.Calculator.equals(
            value=total,
            name=f'Total {costId.value}')
