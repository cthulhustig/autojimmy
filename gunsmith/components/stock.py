import common
import gunsmith
import typing

_StocklessDmModifierNote = 'DM-2 to attack rolls for aimed fire at ranges > 25m'
_FoldingStockModifierNote = 'At ranges > 25m, DM-1 to attack rolls when stock deployed and DM-2 when not deployed'

# NOTE: I've separated stocks from other furniture as one always needs to be chosen (even if that
# is stockless).
class Stock(gunsmith.StockInterface):
    def typeString(self) -> str:
        return 'Stock'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        # Only compatible with weapons that have a receiver. A whole weapon search is used as
        # it can be any of the weapon sequences.
        return context.hasComponent(
            componentType=gunsmith.ReceiverInterface,
            sequence=None)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

class StocklessStock(Stock):
    """
    - Quickdraw: +2 for Longarm or Assault Weapons
    - Note: DM-2 to attack rolls for aimed fire at ranges > 25m
    - Requirement: Not compatible with Bullpup
    """
    _QuickdrawModifier = common.ScalarCalculation(
        value=2,
        name='Stockless Quickdraw Modifier for Assault or Longarm Weapons')

    _UseAttackModifierOptionDescription = \
        '<p>Select if the DM-2 attack modifier at ranges > 25m applies to this weapon.</p>' \
        '<p>This modifier seems a little harsh when applied to handguns or other similarly ' \
        'ranged weapons. At ranges > 25m most handguns will be at extreme range so will already ' \
        'have a DM-4 modifier. Applying an additional DM-2 at ranges > 25m means it\'s ' \
        'effectively impossible for someone with a low gun combat skill to get a lucky shot in ' \
        'without aiming. Although this would be difficult to do, it doesn\'t seem outwith the ' \
        'realms of possibility. This option allows you to turn the modifier on or off based on ' \
        'how you and your Referee interpret the rules. This doesn\'t affect calculated values as ' \
        'ranged dependant modifiers aren\'t applied in calculations, however it will affect the ' \
        'notes that are generated for the weapon</p>' \
        '<p><i>Disabling this modifier can also simplify using weapons created with the Field ' \
        'Catalogue rules in games that are mainly using the Core rules. By ignoring it for Field ' \
        'Catalogue weapons, it means players & referees who are more use to the Core rules don\'t ' \
        'need to remember to apply the modifier to their weapons in order to keep the game ' \
        'balanced.</i></p>'

    def __init__(self) -> None:
        super().__init__()

        self._useAttackModifierOption = gunsmith.BooleanComponentOption(
            id='UseAttackModifier',
            name='Use Attack Modifier',
            value=True,
            description=StocklessStock._UseAttackModifierOptionDescription)

    def componentString(self) -> str:
        return 'Stockless'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.BullpupFeature,
            sequence=None) # Incompatible if any weapon sequence has the bullpup feature

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = [self._useAttackModifierOption]
        options.extend(super().options())
        return options

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        if self._useAttackModifierOption.value():
            step.addNote(note=_StocklessDmModifierNote)

        # Modify Quickdraw for Conventional Assault and Longarm receivers. When checking for the
        # receiver types a whole weapon search is performed as the affect is global. This is only
        # done for the primary weapon as the modifier should only be applied once.
        if context.isPrimary(sequence=sequence):
            hasRequiredReceiver = \
                context.hasComponent(
                    componentType=gunsmith.AssaultReceiver,
                    sequence=None) \
                or context.hasComponent(
                    componentType=gunsmith.LongarmReceiver,
                    sequence=None)
            if hasRequiredReceiver:
                step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Quickdraw,
                    modifier=gunsmith.ConstantModifier(
                        value=self._QuickdrawModifier)))

        context.applyStep(
            sequence=sequence,
            step=step)

class FoldingStock(Stock):
    """
    - Cost: 15% of Receiver Cost
    - Weight: 5% of Receiver Weight
    - Note: At ranges > 25m, DM-1 to attack rolls when stock deployed and DM-2 when not deployed
    - Note: DM+2 to Quickdraw checks for longarm and assault weapons when stock not deployed
    - Requirement: Not compatible with Bullpup
    """
    # NOTE: The notes covering when the stock is not deployed are based on the fact the rules say
    # it's treated the same as stockless when not deployed
    _WeightPercentage = common.ScalarCalculation(
        value=5,
        name='Folding Stock Receiver Weight Percentage')
    _CostPercentage = common.ScalarCalculation(
        value=15,
        name='Folding Stock Receiver Cost Percentage')
    _QuickdrawNote = 'DM+2 to Quickdraw checks for longarm and assault weapons when stock not deployed'

    def componentString(self) -> str:
        return 'Folding'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.BullpupFeature,
            sequence=None) # Incompatible if any weapon sequence has the bullpup feature

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        step.setWeight(weight=gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=None), # Use weight of all receivers
                percentage=self._WeightPercentage,
                name='Folding Stock Weight')))

        step.setCost(cost=gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverCost(sequence=None), # Use cost of all receivers
                percentage=self._CostPercentage,
                name='Folding Stock Cost')))

        step.addNote(note=_FoldingStockModifierNote)

        # Add note regarding quickdraw modifier when stock not deployed. When checking for the
        # receiver types a whole weapon search is performed as the affect is global
        if context.hasComponent(
                componentType=gunsmith.AssaultReceiver,
                sequence=None) \
            or context.hasComponent(
                componentType=gunsmith.LongarmReceiver,
                sequence=None):
            step.addNote(note=self._QuickdrawNote)

        context.applyStep(
            sequence=sequence,
            step=step)

class FullStock(Stock):
    """
    - Cost: 10% of Receiver Cost
    - Weight: 10% of Receiver Weight
    - Requirement: Bullpup Weapons MUST have a Full Stock
    """
    # NOTE: Requirement is handled in code for other Stocks
    _WeightPercentage = common.ScalarCalculation(
        value=10,
        name='Full Stock Receiver Weight Percentage')
    _CostPercentage = common.ScalarCalculation(
        value=10,
        name='Full Stock Receiver Cost Percentage')

    def componentString(self) -> str:
        return 'Full'

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        step.setWeight(weight=gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=None), # Use weight of all receivers
                percentage=self._WeightPercentage,
                name='Full Stock Weight')))

        step.setCost(cost=gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverCost(sequence=None), # Use cost of all receivers
                percentage=self._CostPercentage,
                name='Full Stock Cost')))

        context.applyStep(
            sequence=sequence,
            step=step)

class SupportMountAccessory(Stock):
    """
    - Cost: 25% of Receiver Cost
    - Weight: 100% of Receiver Weight
    - Requirement: Not compatible with Bullpup
    """
    _ReceiverCostPercentage = common.ScalarCalculation(
        value=25,
        name='Support Mount Receiver Cost Percentage')
    _ReceiverWeightPercentage = common.ScalarCalculation(
        value=100,
        name='Support Mount Receiver Weight Percentage')

    def componentString(self) -> str:
        return 'Support Mount'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.BullpupFeature,
            sequence=None) # Incompatible if any weapon sequence has the bullpup feature

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        cost = gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverCost(sequence=None), # Use cost of all receivers
                percentage=self._ReceiverCostPercentage,
                name=f'Support Mount Cost'))

        weight = gunsmith.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=None), # Use weight of all receivers
                percentage=self._ReceiverWeightPercentage,
                name=f'Support Mount Weight'))

        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString(),
            cost=cost,
            weight=weight)
        context.applyStep(
            sequence=sequence,
            step=step)
