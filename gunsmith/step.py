import construction
import typing

class WeaponCost(construction.ConstructionCost):
    Credits = 'Credit Cost'
    Weight = 'Weight Cost'

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

