import common
import gunsmith
import typing

class PropellantType(gunsmith.PropellantTypeInterface):
    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            attacksPerKg: typing.Union[int, common.ScalarCalculation],
            costPerKg: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__()

        if not isinstance(baseRange, common.ScalarCalculation):
            baseRange = common.ScalarCalculation(
                value=baseRange,
                name=f'{componentString} Propellant Base Range')

        if not isinstance(attacksPerKg, common.ScalarCalculation):
            attacksPerKg = common.ScalarCalculation(
                value=attacksPerKg,
                name=f'{componentString} Propellant Attacks Per kg')

        if not isinstance(costPerKg, common.ScalarCalculation):
            costPerKg = common.ScalarCalculation(
                value=costPerKg,
                name=f'{componentString} Propellant Cost Per kg')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._baseRange = baseRange
        self._attacksPerKg = attacksPerKg
        self._costPerKg = costPerKg

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Propellant Type'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if context.techLevel() < self._minTechLevel:
            return False

        return context.hasComponent(
            componentType=gunsmith.ProjectorReceiver,
            sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.ConstructionStep:
        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Range,
            value=self._baseRange))

        propellantWeight = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.PropellantWeight)
        assert(isinstance(propellantWeight, common.ScalarCalculation)) # Construction logic should enforce this

        attacksPerTank = common.Calculator.floor(
            value=common.Calculator.multiply(
                lhs=propellantWeight,
                rhs=self._attacksPerKg),
            name=f'Attacks With {propellantWeight.value()}kg of {self.componentString()} Propellant')
        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.AmmoCapacity,
            value=attacksPerTank))

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.PropellantCost,
            value=self._costPerKg))

        return step

class CompressedGasPropellantType(PropellantType):
    """
    - Min TL: 4
    - Range: 20m
    - Attacks: 4 Per kg
    - Cost: C100 per kg
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Compressed Gas',
            minTechLevel=4,
            baseRange=20,
            attacksPerKg=4,
            costPerKg=100)

class SupercompressedGasPropellantType(PropellantType):
    """
    - Min TL: 7
    - Range: 25m
    - Attacks: 6 Per kg
    - Cost: C250 per kg
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Supercompressed Gas',
            minTechLevel=7,
            baseRange=25,
            attacksPerKg=6,
            costPerKg=250)

class GeneratedGasPropellantType(PropellantType):
    """
    - Min TL: 9
    - Range: 30m
    - Attacks: 10 Per kg
    - Cost: Cr500 Per kg (machinery), Cr200 Per kg (reagent)
    """
    # NOTE: In the case of Generated Gas the reagent is the consumable and its cost is treated
    # as the propellant cost
    # NOTE: I think the way the machinery cost is meant to work is it's an additional cost
    # on the weapon for each kg of propellant weight. This matches up with the costs of the
    # example projector (Field Catalogue p111)
    _MachineryCostPerKg = common.ScalarCalculation(
        value=500,
        name='Generated Gas Machinery Cost Per kg Of Propellant')

    def __init__(self) -> None:
        super().__init__(
            componentString='Generated Gas',
            minTechLevel=9,
            baseRange=30,
            attacksPerKg=10,
            costPerKg=200)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.ConstructionStep:
        step = super()._createStep(sequence=sequence, context=context)

        propellantWeight = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.PropellantWeight)
        assert(isinstance(propellantWeight, common.ScalarCalculation)) # Construction logic should enforce this

        machineryCost = common.Calculator.multiply(
            lhs=propellantWeight,
            rhs=self._MachineryCostPerKg,
            name=f'Cost Of Generated Gas Machinery For {propellantWeight.value()}kg Of Propellant')
        step.setCost(cost=gunsmith.ConstantModifier(value=machineryCost))

        return step

class PropellantQuantity(gunsmith.ProjectorPropellantQuantityInterface):
    def __init__(
            self,
            componentString: str,
            minTechLevel: int
            ) -> None:
        super().__init__()

        self._componentString = componentString
        self._minTechLevel = minTechLevel

        self._propellantWeightOption = gunsmith.FloatComponentOption(
            id='Weight',
            name='Weight',
            value=1.0,
            minValue=0.1,
            description='Specify the weight of propellant.')

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        return f'{self.componentString()} ({common.formatNumber(number=self._propellantWeightOption.value())}kg)'

    def typeString(self) -> str:
        return 'Propellant Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if context.techLevel() < self._minTechLevel:
            return False

        return context.hasComponent(
            componentType=gunsmith.ProjectorReceiver,
            sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return [self._propellantWeightOption]

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        propellantCostPerKg = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.PropellantCost)
        assert(isinstance(propellantCostPerKg, common.ScalarCalculation)) # Construction logic should enforce this

        propellantWeight = common.ScalarCalculation(
            value=self._propellantWeightOption.value(),
            name='Specified Propellant Weight')
        propellantCost = common.Calculator.multiply(
            lhs=propellantWeight,
            rhs=propellantCostPerKg,
            name='Propellant Cost')

        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString(),
            cost=gunsmith.ConstantModifier(value=propellantCost),
            weight=gunsmith.ConstantModifier(value=propellantWeight))
        context.applyStep(
            sequence=sequence,
            step=step)

class CompressedGasPropellantQuantity(PropellantQuantity):
    """
    - Min TL: 4
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Compressed Gas',
            minTechLevel=4)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.CompressedGasPropellantType,
            sequence=sequence)

class SupercompressedGasPropellantQuantity(PropellantQuantity):
    """
    - Min TL: 7
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Supercompressed Gas',
            minTechLevel=7)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.SupercompressedGasPropellantType,
            sequence=sequence)

class GeneratedGasPropellantQuantity(PropellantQuantity):
    """
    - Min TL: 9
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Generated Gas Reagents',
            minTechLevel=9)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.GeneratedGasPropellantType,
            sequence=sequence)
