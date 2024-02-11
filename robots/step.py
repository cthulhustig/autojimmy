import construction
import typing

# NOTE: For display purposes the credit cost is just referred to as cost for
# consistency with the Field Catalogue. The enum is named credits to
# differentiate it from the more generic concept of a cost.
class RobotCost(construction.ConstructionCost):
    Credits = 'Cost'
    Slots = 'Slots'
    Bandwidth = 'Bandwidth'

class RobotStep(construction.ConstructionStep):
    def __init__(
            self,
            name: str,
            type: str,
            costs: typing.Optional[typing.Mapping[RobotCost, construction.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[construction.FactorInterface]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            name=name,
            type=type,
            costs=costs,
            factors=factors,
            notes=notes)
