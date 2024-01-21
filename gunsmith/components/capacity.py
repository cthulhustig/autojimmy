import common
import gunsmith
import typing

class CapacityModification(gunsmith.CapacityModificationInterface):
    """
    - Requirement: Not compatible with Single Shot Mechanisms
    - Requirement: Not compatible with Projectors or Power Pack Energy weapons
    """

    def __init__(
            self
            ) -> None:
        super().__init__()

    def typeString(self) -> str:
        return 'Capacity Modification'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.ReceiverInterface,
                sequence=sequence):
            return False

        return not context.hasComponent(
            componentType=gunsmith.PowerPackReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.SingleShotMechanism,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.LightSingleShotLauncherReceiver,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

class DesiredCapacityModification(CapacityModification):
    """
    - Note: Base Ammo Capacity can be lowered or raised in 10% increments
        - Min: 1 round, Max: 150% of base
    - Increase
        - Receiver Cost: +10% per 10% Ammo Capacity Increase
        - Receiver Weight: +5% per 10% Ammo Capacity Increase
    - Decrease
        - Receiver Cost: -5% per 10% Ammo Capacity Increase
        - Receiver Weight: -5% per 10% Ammo Capacity Increase
    - Requirement: Not compatible with Single Shot Mechanism
    """
    _MaxCapacityIncreasePercentage = common.ScalarCalculation(
        value=+50,
        name='Max Ammo Capacity Increase Percentage')

    _PerIncreaseLevelWeightPercentage = common.ScalarCalculation(
        value=5,
        name='Receiver Weight Increase Per 10% Ammo Capacity Increase')
    _PerIncreaseLevelCostPercentage = common.ScalarCalculation(
        value=10,
        name='Receiver Cost Increase Per 10% Ammo Capacity Increase')
    _PerDecreaseLevelWeightPercentage = common.ScalarCalculation(
        value=-5,
        name='Receiver Weight Decrease Per 10% Ammo Capacity Decrease')
    _PerDecreaseLevelCostPercentage = common.ScalarCalculation(
        value=-5,
        name='Receiver Cost Decrease Per 10% Ammo Capacity Decrease')

    _RequiredCapacityOptionDescription = \
        '<p>Specify the required ammunition capacity for the weapon.</p>' \
        '<p>Note that it may not be possible to get exactly the capacity requested.</p>'

    def __init__(self) -> None:
        super().__init__()

        self._requiredCapacityOption = gunsmith.IntegerComponentOption(
            id='Capacity',
            name='Required Capacity',
            value=1,
            minValue=1,
            description=DesiredCapacityModification._RequiredCapacityOptionDescription)

    def componentString(self) -> str:
        return 'Desired Capacity'

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._requiredCapacityOption)
        return options

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        currentCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCapacity)
        assert(isinstance(currentCapacity, common.ScalarCalculation)) # Construction logic should enforce this

        maxCapacity = common.Calculator.floor(
            value=common.Calculator.applyPercentage(
                value=currentCapacity,
                percentage=self._MaxCapacityIncreasePercentage))
        requiredCapacity = common.ScalarCalculation(
            value=self._requiredCapacityOption.value(),
            name='Specified Ammo Capacity')
        capacity = common.Calculator.min(
            lhs=requiredCapacity,
            rhs=maxCapacity,
            name='Allowed Ammo Capacity')

        capacityOffset = common.Calculator.subtract(
            lhs=capacity,
            rhs=currentCapacity,
            name='Required Ammo Capacity Offset')
        if int(capacityOffset.value()) == 0:
            return # Nothing to do

        offsetPercentage = common.Calculator.multiply(
            lhs=common.Calculator.divideFloat(
                lhs=capacityOffset,
                rhs=currentCapacity),
            rhs=common.ScalarCalculation(value=100),
            name='Required Ammo Capacity Percentage Offset')
        levelCount = common.Calculator.ceil(
            value=common.Calculator.divideFloat(
                lhs=common.Calculator.absolute(offsetPercentage),
                rhs=common.ScalarCalculation(value=10)),
            name='Required Ammo Capacity Offset Levels')

        if capacityOffset.value() > 0:
            weightModifierPercentage = common.Calculator.multiply(
                lhs=self._PerIncreaseLevelWeightPercentage,
                rhs=levelCount,
                name=f'Ammo Capacity Increase Level {levelCount.value()} Receiver Weight Modifier Percentage')
            costModifierPercentage = common.Calculator.multiply(
                lhs=self._PerIncreaseLevelCostPercentage,
                rhs=levelCount,
                name=f'Ammo Capacity Increase Level {levelCount.value()} Receiver Cost Modifier Percentage')
        else:
            weightModifierPercentage = common.Calculator.multiply(
                lhs=self._PerDecreaseLevelWeightPercentage,
                rhs=levelCount,
                name=f'Ammo Capacity Decrease Level {levelCount.value()} Receiver Weight Modifier Percentage')
            costModifierPercentage = common.Calculator.multiply(
                lhs=self._PerDecreaseLevelCostPercentage,
                rhs=levelCount,
                name=f'Ammo Capacity Decrease Level {levelCount.value()} Receiver Cost Modifier Percentage')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        step.setWeight(weight=gunsmith.PercentageModifier(
            value=weightModifierPercentage))

        step.setCredits(credits=gunsmith.PercentageModifier(
            value=costModifierPercentage))

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.AmmoCapacity,
            value=capacity))

        context.applyStep(
            sequence=sequence,
            step=step)

class IncreaseCapacityModification(CapacityModification):
    """
    - Note: Base Ammo Capacity can be lowered or raised in 10% increments
        - Min: 1 round, Max: 150% of base
    - Increase
        - Receiver Cost: +10% per 10% Ammo Capacity Increase
        - Receiver Weight: +5% per 10% Ammo Capacity Increase
    - Requirement: Not compatible with Single Shot Mechanism
    """
    _PerIncreaseLevelWeightPercentage = common.ScalarCalculation(
        value=5,
        name='Receiver Weight Increase Per 10% Ammo Capacity Increase')
    _PerIncreaseLevelCostPercentage = common.ScalarCalculation(
        value=10,
        name='Receiver Cost Increase Per 10% Ammo Capacity Increase')

    def __init__(self) -> None:
        super().__init__()

        self._increaseLevelsOption = gunsmith.IntegerComponentOption(
            id='Levels',
            name='Increase Levels',
            value=1,
            minValue=1,
            maxValue=5,
            description='Specify the number of levels to increase ammunition capacity by.')

    def componentString(self) -> str:
        return 'Capacity Increase'

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._increaseLevelsOption)
        return options

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        increaseLevels = common.ScalarCalculation(
            value=self._increaseLevelsOption.value(),
            name='Specified Increase Levels')

        weightModifierPercentage = common.Calculator.multiply(
            lhs=self._PerIncreaseLevelWeightPercentage,
            rhs=increaseLevels,
            name=f'{self.componentString()} Receiver Weight Modifier Percentage')
        step.setWeight(weight=gunsmith.PercentageModifier(
            value=weightModifierPercentage))

        costModifierPercentage = common.Calculator.multiply(
            lhs=self._PerIncreaseLevelCostPercentage,
            rhs=increaseLevels,
            name=f'{self.componentString()} Receiver Cost Modifier Percentage')
        step.setCredits(credits=gunsmith.PercentageModifier(
            value=costModifierPercentage))

        capacityModifierPercentage = common.Calculator.multiply(
            lhs=increaseLevels,
            rhs=common.ScalarCalculation(value=10),
            name=f'{self.componentString()} Ammo Capacity Modifier Percentage')
        step.addFactor(factor=gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.AmmoCapacity,
            modifier=gunsmith.PercentageModifier(
                value=capacityModifierPercentage,
                roundDown=True)))

        context.applyStep(
            sequence=sequence,
            step=step)

class DecreaseCapacityModification(CapacityModification):
    """
    - Note: Base Ammo Capacity can be lowered or raised in 10% increments
        - Min: 1 round, Max: 150% of base
    - Decrease
        - Receiver Cost: -5% per 10% Ammo Capacity Increase
        - Receiver Weight: -5% per 10% Ammo Capacity Increase
    - Requirement: Not compatible with Single Shot Mechanism
    - Requirement: Not compatible in cases where it would reduce ammo capacity below weapon minimum
    """
    # NOTE: I've added the requirement that this isn't compatible with weapons where it would reduce
    # the ammo capacity below the minimum for the weapon. This is based on the assumption that ammo
    # capacities should be rounded each time they're modified. In most cases the minimum capacity is
    # 1, the exception to this is weapons that have a complete multi-barrel set up. This is based on
    # my interpretation of the description of complete multi-barrel setups (Field Catalogue p40). The
    # rules are less clear when it comes to partial multi-barrel setups. It seems like it's probably
    # dependant on the type of partial multi-barrel setup the user is creating. For a pepperbox pistol
    # like the example in the rules then you would think capacity shouldn't be allowed to go bellow
    # the number of barrels. However, partial multi-barrel setups also seem like the obvious choice
    # for something like a gatling gun where the capacity is completely independent of the number of
    # barrels. As such I've not left the minimum capacity as 1 for partial multi-barrel setups and
    # it's up to the user to choose sensible values based on the weapon they're creating.

    _PerDecreaseLevelWeightPercentage = common.ScalarCalculation(
        value=-5,
        name='Receiver Weight Decrease Per 10% Ammo Capacity Decrease')
    _PerDecreaseLevelCostPercentage = common.ScalarCalculation(
        value=-5,
        name='Receiver Cost Decrease Per 10% Ammo Capacity Decrease')

    def __init__(
            self,
            decreaseLevels: typing.Union[int, common.ScalarCalculation] = None
            ) -> None:
        super().__init__()

        if decreaseLevels and not isinstance(decreaseLevels, common.ScalarCalculation):
            decreaseLevels = common.ScalarCalculation(
                value=decreaseLevels,
                name=f'Capacity Decrease levels')

        self._decreaseLevelsOption = gunsmith.IntegerComponentOption(
            id='Levels',
            name='Decrease Levels',
            value=1,
            minValue=1,
            maxValue=10,
            description='Specify the number of levels to reduce ammunition capacity by.')

    def componentString(self) -> str:
        return 'Capacity Decrease'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        return self._calculateMaxDecrease(
            sequence=sequence,
            context=context) > 0

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._decreaseLevelsOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)
        maxLevel = self._calculateMaxDecrease(
            sequence=sequence,
            context=context)
        if maxLevel > 0:
            self._decreaseLevelsOption.setMin(value=1)
            self._decreaseLevelsOption.setMax(value=maxLevel)
        else:
            self._decreaseLevelsOption.setMin(value=0)
            self._decreaseLevelsOption.setMax(value=0)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        decreaseLevels = common.ScalarCalculation(
            value=self._decreaseLevelsOption.value(),
            name='Specified Decrease Levels')

        weightModifierPercentage = common.Calculator.multiply(
            lhs=self._PerDecreaseLevelWeightPercentage,
            rhs=decreaseLevels,
            name=f'{self.componentString()} Receiver Weight Modifier Percentage')
        step.setWeight(weight=gunsmith.PercentageModifier(
            value=weightModifierPercentage))

        costModifierPercentage = common.Calculator.multiply(
            lhs=self._PerDecreaseLevelCostPercentage,
            rhs=decreaseLevels,
            name=f'{self.componentString()} Receiver Cost Modifier Percentage')
        step.setCredits(credits=gunsmith.PercentageModifier(
            value=costModifierPercentage))

        capacityModifierPercentage = common.Calculator.multiply(
            lhs=decreaseLevels,
            rhs=common.ScalarCalculation(value=-10),
            name=f'{self.componentString()} Ammo Capacity Modifier Percentage')
        step.addFactor(factor=gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.AmmoCapacity,
            modifier=gunsmith.PercentageModifier(
                value=capacityModifierPercentage,
                roundDown=True)))

        context.applyStep(
            sequence=sequence,
            step=step)

    # Calculate the max decrease that can be applied while still keeping the ammo capacity above zero
    def _calculateMaxDecrease(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> int:
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCapacity)
        if not isinstance(ammoCapacity, common.ScalarCalculation):
            return 0

        minCapacity = 1
        if context.hasComponent(
                componentType=gunsmith.CompleteMultiBarrelSetup,
                sequence=sequence):
            # The sequence has a complete multi barrel setup so the minimum capacity is
            # equal to the number of barrels
            barrelCount = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.BarrelCount)
            if not isinstance(ammoCapacity, common.ScalarCalculation):
                return 0
            minCapacity = barrelCount.value()

        for level in range(10, 0, -1):
            modifiedCapacity = common.Calculator.floor(
                value=common.Calculator.applyPercentage(
                    value=ammoCapacity,
                    percentage=common.ScalarCalculation(value=level * -10)))
            if modifiedCapacity.value() >= minCapacity:
                return level
        return 0
