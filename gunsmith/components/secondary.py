import common
import construction
import gunsmith
import typing

class SecondaryMount(gunsmith.WeaponComponentInterface):
    """
    - Cost: 10% of secondary weapon cost
    - Weight: 10% of secondary weapon weight
    - Quickdraw: -1 per barrel (see note)
    """
    # NOTE: It's not entirely clear what should be included in the secondary weapon cost/weight when
    # calculating the mount cost/weight. I've chosen to only include the receiver and barrel values
    # as those are the parts that are specific to the secondary weapon. Barrel accessories are not
    # included as it seems wrong that the cost/weight of the mount would take into account items that
    # can be added after the initial purchase. None of the accessories have a weight that is high
    # enough relative to the weight of the receiver and barrel that you would expect them to require
    # a heavier duty mount
    # NOTE: The rules don't seem to impose any limit of what can be a secondary weapon (Field
    # Guide p40). It would seem like there should be to prevent the rocket launcher as a secondary
    # on a pistol, but I guess it's just how you look at it, is it the pistol or the rocket launcher
    # that is actually the secondary. I'm leaving this for the user to deal with.
    # NOTE: It's not clear how secondary weapons affect Quickdraw. Part of this comes from the fact
    # it's not clear exactly how the Multi-Barrel Weapon section relates to Secondary Weapons (Field
    # Catalogue p40). As it's not clear I've added an option where the user can specify the modifier
    # they thing. I've defaulted it to -1 as that's the modifier an addition complete multi-barrel
    # setup would add so it seems like a secondary weapon would add at least that.
    # NOTE: In the Tube Launcher section (Field Catalogue p58) it says there is no cost to adding a
    # Launcher to a weapon if it has Modularisation. However that seems more aimed at a bolt on
    # accessory launcher rather than a complete secondary weapon.

    _MountWeightModifierPercentage = common.ScalarCalculation(
        value=10,
        name='Secondary Weapon Mounting Weight Percentage')
    _MountCostModifierPercentage = common.ScalarCalculation(
        value=10,
        name='Secondary Weapon Mounting Cost Percentage')

    _QuickdrawOptionDescription = \
        '<p>Specify the Quickdraw modifier for the Secondary Weapon</p>' \
        '<p>The description of Secondary Weapons on p40 of the Field Catalogue doesn\'t mention ' \
        'a Quickdraw modifier for mounting a Secondary Weapon but you would expect it would have ' \
        'one. The description of Complete Multi-Barrel setups just below it mentions a Quickdraw ' \
        '-1 per additional barrel, however it\'s not clear exactly how multi-barrel setups relate ' \
        'to Secondary Weapons. The description of Multi-Barrel setups seem conceptually different ' \
        'to a true Secondary Weapon where you might mount a shotgun and laser rifle in the same ' \
        'weapon. As such, a straight -1 modifier seems like it could be unrealistically low in some ' \
        'cases. This option allows you to specify a modifier based on how you and your Referee ' \
        'interpret the rules.</p>'

    def __init__(self) -> None:
        super().__init__()

        self._quickdrawModifierOption = construction.IntegerOption(
            id='QuickdrawModifier',
            name='Secondary Weapon Quickdraw Modifier',
            value=-1,
            maxValue=0,
            description=SecondaryMount._QuickdrawOptionDescription)

    def componentString(self) -> str:
        return f'Standard Mounting'

    def typeString(self) -> str:
        return 'Mounting'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Not compatible with primary weapon
        return not context.isPrimary(sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._quickdrawModifierOption]

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        secondaryWeight = common.Calculator.add(
            lhs=context.phaseWeight(
                phase=gunsmith.WeaponPhase.Receiver,
                sequence=sequence),
            rhs=context.phaseWeight(
                phase=gunsmith.WeaponPhase.Barrel,
                sequence=sequence),
            name='Secondary Weapon Weight')
        secondaryCost = common.Calculator.add(
            lhs=context.phaseCredits(
                phase=gunsmith.WeaponPhase.Receiver,
                sequence=sequence),
            rhs=context.phaseCredits(
                phase=gunsmith.WeaponPhase.Barrel,
                sequence=sequence),
            name='Secondary Weapon Cost')

        step.setCredits(credits=construction.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=secondaryCost,
                percentage=self._MountCostModifierPercentage,
                name='Secondary Weapon Mounting Cost')))

        step.setWeight(weight=construction.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=secondaryWeight,
                percentage=self._MountWeightModifierPercentage,
                name='Secondary Weapon Mounting Weight')))

        quickdrawModifier = self._quickdrawModifierOption.value()
        if quickdrawModifier < 0:
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name='Specified Secondary Weapon Quickdraw Modifier')

            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=quickdrawModifier)))

        context.applyStep(
            sequence=sequence,
            step=step)
