import common
import construction
import gunsmith
import typing

class _FuelImpl(object):
    """
    Requirement: Only compatible with Projector Weapons
    """

    def __init__(
            self,
            componentString: str,
            minTechLevel: typing.Union[int, common.ScalarCalculation],
            costPerKg: typing.Union[int, float, common.ScalarCalculation],
            damageDice: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            traitMap: typing.Optional[typing.Mapping[gunsmith.WeaponAttributeId, typing.Union[int, common.ScalarCalculation, common.DiceRoll]]] = None,
            ) -> None:
        if not isinstance(minTechLevel, common.ScalarCalculation):
            minTechLevel = common.ScalarCalculation(
                value=minTechLevel,
                name=f'{componentString} Fuel Minimum Tech Level')

        if not isinstance(costPerKg, common.ScalarCalculation):
            costPerKg = common.ScalarCalculation(
                value=costPerKg,
                name=f'{componentString} Fuel Cost Per kg')

        if damageDice != None and not isinstance(damageDice, common.ScalarCalculation):
            damageDice = common.ScalarCalculation(
                value=damageDice,
                name=f'{componentString} Fuel Damage Dice Count')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._costPerKg = costPerKg
        self._damageDice = damageDice

        self._traitMap = {}
        if traitMap:
            for trait, value in traitMap.items():
                if not isinstance(value, common.ScalarCalculation) and \
                        not isinstance(value, common.DiceRoll):
                    value = common.ScalarCalculation(
                        value=value,
                        name=f'{componentString} Fuel Base {trait.value}')
                self._traitMap[trait] = value

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        return self.componentString()

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel.value():
            return False

        # Only compatible with projectors
        return context.hasComponent(
            componentType=gunsmith.ProjectorReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            fuelWeight: common.ScalarCalculation,
            includeWeight: bool,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        if includeWeight:
            step.setWeight(weight=construction.ConstantModifier(value=fuelWeight))

        totalCost = common.Calculator.multiply(
            lhs=self._costPerKg,
            rhs=fuelWeight,
            name='Total Fuel Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        factors = []

        if self._damageDice:
            # This sets the damage rather than modifying it as projectors don't have a damage
            # other than what comes from the fuel
            factors.append(construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                value=common.DiceRoll(
                    count=self._damageDice,
                    type=common.DieType.D6)))

        for trait, value in self._traitMap.items():
            # The fact that this is setting the value rather than modifying it is important. The
            # value may be a DiceRoll and using them as a modifier isn't supported
            factors.append(construction.SetAttributeFactor(
                attributeId=trait,
                value=value))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _LiquidFuelImpl(_FuelImpl):
    """
    - Min TL: 4
    - Cost: Cr25 Per kg
    - Damage: 3D
    - Trait: Incendiary 1
    - Trait: Burn 1
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Liquid',
            minTechLevel=4,
            costPerKg=25,
            damageDice=3,
            traitMap={
                gunsmith.WeaponAttributeId.Incendiary: 1,
                gunsmith.WeaponAttributeId.Burn: 1})

class _JelliedFuelImpl(_FuelImpl):
    """
    - Min TL: 5
    - Cost: Cr75 Per kg
    - Damage: 4D
    - Trait: Incendiary 1
    - Trait: Burn D3 + 1
    """
    _BurnTrait = common.DiceRoll(
        count=common.ScalarCalculation(
            value=1,
            name='Jellied Fuel Burn D3 Count'),
        type=common.DieType.D3,
        constant=common.ScalarCalculation(
            value=1,
            name='Jellied Fuel Burn Constant'))

    def __init__(self) -> None:
        super().__init__(
            componentString='Jellied',
            minTechLevel=5,
            costPerKg=75,
            damageDice=4,
            traitMap={
                gunsmith.WeaponAttributeId.Incendiary: 1,
                gunsmith.WeaponAttributeId.Burn: self._BurnTrait})

class _IrritantFuelImpl(_FuelImpl):
    """
    - Min TL: 6
    - Cost: Cr25 Per kg
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Irritant',
            minTechLevel=6,
            costPerKg=25)

class _VolatileIrritantFuelImpl(_FuelImpl):
    """
    - Min TL: 6
    - Cost: Cr60 Per kg
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Volatile Irritant',
            minTechLevel=6,
            costPerKg=60)

class _SuppressantFuelImpl(_FuelImpl):
    """
    - Min TL: 6
    - Cost: Cr25 Per kg
    - Damage: 2D
    - Range: Effective range is halved
    """
    _RangeModifierPercentage = common.ScalarCalculation(
        value=-50,
        name='Suppressant Fuel Range Modifier Percentage')

    def __init__(self) -> None:
        super().__init__(
            componentString='Suppressant',
            minTechLevel=6,
            costPerKg=25,
            damageDice=2)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            fuelWeight: common.ScalarCalculation,
            includeWeight: bool,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            fuelWeight=fuelWeight,
            includeWeight=includeWeight,
            applyModifiers=applyModifiers,
            step=step)

        factor = construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Range,
            modifier=construction.PercentageModifier(
                value=self._RangeModifierPercentage))
        if not applyModifiers:
            factor = construction.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

class _BattlechemFuelImpl(_FuelImpl):
    """
    - Min TL: 8
    - Cost: Cr300 Per kg
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Battlechem',
            minTechLevel=8,
            costPerKg=300)

class _AdvancedFuelImpl(_FuelImpl):
    """
    - Min TL: 9
    - Cost: Cr150 Per kg
    - Damage: 5D
    - Trait: Incendiary D3 + 1
    - Trait: Burn D3 + 1
    """
    _IncendiaryTrait = common.DiceRoll(
        count=common.ScalarCalculation(
            value=1,
            name='Advanced Fuel Incendiary D3 Count'),
        type=common.DieType.D3,
        constant=common.ScalarCalculation(
            value=1,
            name='Advanced Fuel Incendiary Constant'))

    _BurnTrait = common.DiceRoll(
        count=common.ScalarCalculation(
            value=1,
            name='Advanced Fuel Burn D3 Count'),
        type=common.DieType.D3,
        constant=common.ScalarCalculation(
            value=1,
            name='Advanced Fuel Burn Constant'))

    def __init__(self) -> None:
        super().__init__(
            componentString='Advanced',
            minTechLevel=9,
            costPerKg=150,
            damageDice=5,
            traitMap={
                gunsmith.WeaponAttributeId.Incendiary: self._IncendiaryTrait,
                gunsmith.WeaponAttributeId.Burn: self._BurnTrait})

class _CryogenicFuelImpl(_FuelImpl):
    """
    - Min TL: 10
    - Cost: Cr100 Per kg
    - Damage: 4D
    - Note: Target must make an Average(8+) STR check or be unable to move their limbs for 1D rounds
    """
    _CryogenicNote = 'Target must make an Average(8+) STR check or be unable to move their limbs for 1D rounds'

    def __init__(self) -> None:
        super().__init__(
            componentString='Cryogenic',
            minTechLevel=10,
            costPerKg=100,
            damageDice=4)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            fuelWeight: common.ScalarCalculation,
            includeWeight: bool,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            fuelWeight=fuelWeight,
            includeWeight=includeWeight,
            applyModifiers=applyModifiers,
            step=step)

        if applyModifiers:
            step.addNote(note=self._CryogenicNote)

class ProjectorFuelLoaded(gunsmith.AmmoLoaded):
    # NOTE: Weight of fuel isn't added to weapon weight if loaded is set as the Structure weight
    # is the fully loaded weight
    def __init__(
            self,
            impl: _FuelImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Fuel'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        #
        # Fuel Step
        #

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        fuelWeight = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.FuelWeight)
        assert(isinstance(fuelWeight, common.ScalarCalculation)) # Construction logic should enforce this
        self._impl.updateStep(
            sequence=sequence,
            context=context,
            fuelWeight=fuelWeight,
            includeWeight=False, # Don't include loaded fuel weight, it's included in structure weight
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

        #
        # Propellant Step
        #

        step = gunsmith.WeaponStep(
            name='Propellant',
            type=self.typeString())

        propellantWeight = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.PropellantWeight)
        assert(isinstance(propellantWeight, common.ScalarCalculation)) # Construction logic should enforce this
        propellantCostPerKg = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.PropellantCost)
        assert(isinstance(propellantCostPerKg, common.ScalarCalculation)) # Construction logic should enforce this
        propellantCost = common.Calculator.multiply(
            lhs=propellantCostPerKg,
            rhs=propellantWeight,
            name='Propellant Cost')
        step.setCredits(credits=construction.ConstantModifier(value=propellantCost))

        context.applyStep(
            sequence=sequence,
            step=step)

class LiquidProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_LiquidFuelImpl())

class JelliedProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_JelliedFuelImpl())

class IrritantProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_IrritantFuelImpl())

class VolatileIrritantProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_VolatileIrritantFuelImpl())

class SuppressantProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_SuppressantFuelImpl())

class BattlechemProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_BattlechemFuelImpl())

class AdvancedProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_AdvancedFuelImpl())

class CryogenicProjectorFuelLoaded(ProjectorFuelLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_CryogenicFuelImpl())


class ProjectorFuelQuantity(gunsmith.AmmoQuantity):
    def __init__(
            self,
            impl: _FuelImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._fuelWeightOption = construction.FloatOption(
            id='Weight',
            name='Weight',
            value=1.0,
            minValue=0.1,
            description='Specify the weight of fuel.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} ({common.formatNumber(number=self._fuelWeightOption.value())}kg)'

    def typeString(self) -> str:
        return 'Fuel Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._fuelWeightOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        fuelWeight = common.ScalarCalculation(
            value=self._fuelWeightOption.value(),
            name='Specified Fuel Weight')

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            fuelWeight=fuelWeight,
            includeWeight=True, # Include the weight for fuel quantities
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class LiquidProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_LiquidFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return LiquidProjectorFuelLoaded()

class JelliedProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_JelliedFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return JelliedProjectorFuelLoaded()

class IrritantProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_IrritantFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return IrritantProjectorFuelLoaded()

class VolatileIrritantProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_VolatileIrritantFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return VolatileIrritantProjectorFuelLoaded()

class SuppressantProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_SuppressantFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return SuppressantProjectorFuelLoaded()

class BattlechemProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BattlechemFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return BattlechemProjectorFuelLoaded()

class AdvancedProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_AdvancedFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return AdvancedProjectorFuelLoaded()

class CryogenicProjectorFuelQuantity(ProjectorFuelQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_CryogenicFuelImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoaded:
        return CryogenicProjectorFuelLoaded()
