import common
import construction
import gunsmith
import typing

class MultiBarrel(gunsmith.MultiBarrelInterface):
    """
    - Heat Dissipation: +1 for each additional barrel (table on p14 of Field Catalogue)
    - Requirement: Not compatible with projectors
    """
    # NOTE: I've added the requirement that you can't have multi-barrel projectors as (from
    # a rules point of view) they don't have barrels.

    _AdditionalBarrelHeatModifier = common.ScalarCalculation(
        value=+1,
        name='Multiple Barrel Heat Dissipation Modifier For Each Additional Barrel')

    _BarrelCountOptionDescription = \
        '<p>Specify the number of barrels the weapon has.</p>' \
        '<p>Note that this is for a receiver with multiple barrels such as double barrel ' \
        'shotguns or rotary barrel weapons. Cases where each barrel has a it\'s own receiver ' \
        'should be handled as a secondary weapon.</p>'

    def __init__(
            self,
            componentString: str
            ) -> None:
        super().__init__()

        self._componentString = componentString

        self._barrelCountOption = construction.IntegerComponentOption(
            id='Count',
            name='Count',
            value=2,
            minValue=2,
            description=MultiBarrel._BarrelCountOptionDescription)

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        return f'{self.componentString()} x{self._barrelCountOption.value()}'

    def typeString(self) -> str:
        return 'Multi-Barrel'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Not compatible with projects
        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Only compatible with weapons that have a receiver.
        return context.hasComponent(
            componentType=gunsmith.ReceiverInterface,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._barrelCountOption]

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        barrelCount = common.ScalarCalculation(
            value=self._barrelCountOption.value(),
            name='Specified Barrel Count')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.BarrelCount,
            value=barrelCount))

        if context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttribute.HeatDissipation):
            additionalBarrels = common.Calculator.subtract(
                lhs=barrelCount,
                rhs=common.ScalarCalculation(value=1),
                name='Additional Barrel Count')
            heatModifier = common.Calculator.multiply(
                lhs=self._AdditionalBarrelHeatModifier,
                rhs=additionalBarrels,
                name='Multiple Barrel Heat Dissipation Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatDissipation,
                modifier=construction.ConstantModifier(value=heatModifier)))

        return step

class CompleteMultiBarrelSetup(MultiBarrel):
    """
    - Receiver Weight: +10% for for each additional barrel (Field Catalogue p40)
    - Receiver Cost: +10% for for each additional barrel (Field Catalogue p40)
    - Barrel Cost: Each barrel has normal cost (Field Catalogue p40)
    - Barrel Weight: Each barrel after the first only adds 1/2 its weight (Field Catalogue p40)
    - Quickdraw: -1 for each additional barrel (Field Catalogue p40)
    - Heat Dissipation: +1 for each additional barrel (table on p14 of Field Catalogue)
    """
    # NOTE: The fact additional barrel weight is halved is handled in the barrel code
    # NOTE: This implementation doesn't handle complete multi-barrel setups with unmatched barrels.
    # It would be a LOT of effort for a minor feature. Users can achieve a very similar end result
    # with secondary weapons (although costs/weight may be different)

    _ReceiverWeightPercentageIncrement = common.ScalarCalculation(
        value=+10,
        name='Complete Multi-Barrel Setup Receiver Weight Percentage For Each Additional Barrel')
    _ReceiverCostPercentageIncrement = common.ScalarCalculation(
        value=+10,
        name='Complete Multi-Barrel Setup Receiver Cost Percentage For Each Additional Barrel')
    _AdditionalBarrelQuickdrawModifier = common.ScalarCalculation(
        value=-1,
        name='Multiple Barrel Quickdraw Modifier For Each Additional Barrel')

    def __init__(self) -> None:
        super().__init__(componentString='Complete Multi-Barrel')

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        barrelCount = common.ScalarCalculation(
            value=self._barrelCountOption.value(),
            name='Specified Barrel Count')
        additionalBarrels = common.Calculator.subtract(
            lhs=barrelCount,
            rhs=common.ScalarCalculation(value=1),
            name='Additional Barrel Count')

        quickdrawModifier = common.Calculator.multiply(
            lhs=self._AdditionalBarrelQuickdrawModifier,
            rhs=additionalBarrels,
            name=f'{self.componentString()} Quickdraw Modifier')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Quickdraw,
            modifier=construction.ConstantModifier(
                value=quickdrawModifier)))

        weightModifierPercentage = common.Calculator.multiply(
            lhs=self._ReceiverWeightPercentageIncrement,
            rhs=additionalBarrels,
            name=f'{self.componentString()} Setup Receiver Weight Modifier Percentage')
        step.setWeight(weight=construction.PercentageModifier(
            value=weightModifierPercentage))

        costModifierPercentage = common.Calculator.multiply(
            lhs=self._ReceiverCostPercentageIncrement,
            rhs=additionalBarrels,
            name=f'{self.componentString()} Setup Receiver Cost Modifier Percentage')
        step.setCredits(credits=construction.PercentageModifier(value=costModifierPercentage))

        return step

class PartialMultiBarrelSetup(MultiBarrel):
    """
    - Barrel Cost: Each barrel has normal cost (Field Catalogue p40)
    - Barrel Weight: Each barrel after the first only adds 1/2 its weight
    - Heat Dissipation: +1 for each additional barrel (table on p14 of Field Catalogue)
    """
    # NOTE: The Multi-Barrel section (Field Catalogue p40-41) reads like the Quickdraw -1 modifier
    # for each additional barrel only applies for Complete barrels and not Partial barrels. The
    # the example on p70 does have the -1 but the example on p79 doesn't. I've chosen to go with
    # the wording rather than the example.
    # NOTE: The description for Partial Multi-Barrel (Field Catalogue p40) doesn't say additional
    # barrels only add 1/2 the barrel weight, however the example on p70 does use half weight. The
    # example on p70 is no help as it has minimal barrels which have no weight. I've chosen to go
    # with the wording rather than the example.

    def __init__(self) -> None:
        super().__init__(componentString='Partial Multi-Barrel')
