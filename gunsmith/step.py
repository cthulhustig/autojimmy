import construction
import typing

# NOTE: For display purposes the credit cost is just referred to as cost for
# consistency with the Field Catalogue. The enum is named credits to
# differentiate it from the more generic concept of a cost.
class WeaponCost(construction.ConstructionCost):
    Credits = 'Cost'
    Weight = 'Weight'

class WeaponStep(construction.ConstructionStep):
    def __init__(
            self,
            name: str,
            type: str,
            credits: typing.Optional[construction.NumericModifierInterface] = None,
            weight: typing.Optional[construction.NumericModifierInterface] = None,
            factors: typing.Optional[typing.Iterable[construction.FactorInterface]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            name=name,
            type=type,
            factors=factors,
            notes=notes)
        if credits:
            self.setCredits(credits=credits)
        if weight:
            self.setWeight(weight=weight)

    def credits(self) -> typing.Optional[construction.NumericModifierInterface]:
        return self.cost(costId=WeaponCost.Credits)

    def setCredits(
            self,
            credits: construction.NumericModifierInterface
            ) -> None:
        self.setCost(costId=WeaponCost.Credits, value=credits)

    def weight(self) -> typing.Optional[construction.NumericModifierInterface]:
        return self.cost(costId=WeaponCost.Weight)

    def setWeight(
            self,
            weight: construction.NumericModifierInterface
            ) -> None:
        self.setCost(costId=WeaponCost.Weight, value=weight)
