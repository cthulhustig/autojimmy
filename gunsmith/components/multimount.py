import common
import construction
import gunsmith
import typing

class MultiMount(gunsmith.MultiMountInterface):
    """
    Multi-Mount
    - Quickdraw: -1 per barrel
    - Trait: Auto +1 for each additional weapon over 2 (Field Catalogue p41)
    - Trait: RF Trait if Multi-Mount weapon has Auto 4+ (Field Catalogue p41)
    - Trait: VRF Trait if Multi-Mount weapon has Auto 6+ (Field Catalogue p41)
    - Trait: VRF Trait if weapon already has RF Trait (Field Catalogue p32)
    - Barrel Count: Multiplied by number of weapons
    RF Upgrade
    - Trait: VRF
    - Trait: AP (AP score equal to the base number of damage dice, calculated before additional rapid-fire damage is added)
    - Damage: 1 extra dice of damage per 3 full dice of damage of a automatic weapon of the same calibre
    - Heat Generation: Auto Score + (2 x Damage Dice)
    - Requirement: Not compatible with launchers or projects
    VRF Upgrade
    - Trait: VRF
    - Trait: AP (AP score equal to the base number of damage dice, calculated before additional rapid-fire damage is added)
    - Damage: 1 extra dice of damage per 2 full dice of damage of a automatic weapon of the same calibre
    - Heat Generation: Auto Score + (3 x Damage Dice)
    - Requirement: Not compatible with launchers or projects
    """
    # NOTE: The point multi-mount should be applied isn't obvious. It could be multiple receiver/barrel
    # setups with a single stock (i.e. something specifically made as a multi-mount) _or_ it could be
    # multiple full weapons jerry-rigged together. I've gone with the later based on this line from the
    # RF description on p32 of the Field Catalogue "A twin mount carrying identical weapons......". This
    # makes it sounds like this a mount you can place multiple weapons in.Based on that thinking it makes
    # conceptual sense for it to be applied after the weapon has been fully constructed as you're just
    # combining multiple independent weapons.
    # It's even less obvious if it should be applied before or after the weapon is loaded. This has a big
    # impact as it determines if damage modifiers for ammo type are taken into account when calculating
    # the AP and damage modifier for the weapon achieving RF/VRF through multi-mount. I think it makes the
    # most sense for it to be applied before the weapon is loaded to keep it consistent with the RF/VRF
    # fire rate (which doesn't take ammo type damage modifiers into account). However the big downside of
    # this is the cost and weight of the loaded magazine won't be multiplied by the number of multi-mount
    # weapons. To hack around this I've created the MultiMountLoaded component which is added by a stage
    # that occurs at the end of the loading phase.
    # NOTE: The multi-mount description (Field Catalogue p41) isn't clear exactly what it means by
    # a multi-mount weapon with a high enough Auto score can be "considered" as RF or VRF. I'm working
    # on the assumption that it means the weapon gets the same AP and damage bonuses but also suffer the
    # same increased heat generation. I thinks this make sense as the description for RF (Field Catalogue
    # p32) mentions weapons achieving RF through a twin-mount in the same paragraph as the increased heat
    # generation
    # NOTE: The multi-mount description (Field Catalogue p41) doesn't mention anything about a quickdraw
    # modifier but it would seem logical that bolting multiple weapons together would have some effect on
    # it. As it's so unclear I've added an option so the user can specify a value
    # NOTE: It's not clear what should happen if you Multi-Mount multiple weapons that already have
    # the VRF trait. Currently this will result in the VRF AP, damage and heat modifications being
    # applied again. This doesn't seem too unreasonable and seems similar to what happens when
    # multiple RF weapons combine to become a VRF weapon
    # NOTE: I've added the requirement that RF/VRF upgrade is incompatible with launchers and projectors
    # for the same reasoning as RFFireRate and VRFFireRate are incompatible. It should be noted it's only
    # the RF/VRF upgrade that's incompatible, creating multi-mount launchers/projectors is allowed

    _AdditionalBarrelQuickDrawModifier = common.ScalarCalculation(
        value=-1,
        name='Multi-Mount Quickdraw Modifier Each Additional Barrel')

    _RFMinAutoLevel = common.ScalarCalculation(
        value=4,
        name='RF Minimum Auto Level')
    _RFDamageDiceDivisor = common.ScalarCalculation(
        value=3,
        name='RF Whole Damage Dice For Additional Damage Die')
    _RFHeatMultiplier = common.ScalarCalculation(
        value=2,
        name='RF Heat Multiplier')

    _VRFMinAutoLevel = common.ScalarCalculation(
        value=6,
        name='VRF Minimum Auto Level')
    _VRFDamageDiceDivisor = common.ScalarCalculation(
        value=2,
        name='VRF Whole Damage Dice For Additional Damage Die')
    _VRFHeatMultiplier = common.ScalarCalculation(
        value=3,
        name='VRF Heat Multiplier')

    _QuickdrawOptionDescription = \
        '<p>Specify the Quickdraw modifier for the Multi-Mount Weapon</p>' \
        '<p>The description of Multi-Mount on p41 of the Field Catalogue doesn\'t mention ' \
        'a Quickdraw modifier for mounting a Multi-Mount Weapon but you would expect it would ' \
        'have one. The description of Complete Multi-Barrel setups on the previous page mentions ' \
        'a Quickdraw -1 per additional barrel, it Multi-Barrel seems conceptually different ' \
        'Multi-Mount. A straight -1 modifier also seems very low if you were mounting multiple ' \
        'larger weapons together. This option allows you to specify a modifier based on how you ' \
        'and your Referee interpret the rules.</p>'

    def __init__(
            self,
            weaponCount: typing.Union[int, common.ScalarCalculation] = 2
            ) -> None:
        super().__init__()

        if not isinstance(weaponCount, common.ScalarCalculation):
            weaponCount = common.ScalarCalculation(
                value=weaponCount,
                name='Multi-Mount Weapon Count')

        self._weaponCountOption = construction.IntegerOption(
            id='Count',
            name='Count',
            value=2,
            minValue=2,
            description='Specify the number of identical weapons that are used to create the multi-mount setup.')

        self._quickdrawModifierOption = construction.IntegerOption(
            id='QuickdrawModifier',
            name='Secondary Weapon Quickdraw Modifier',
            value=0,
            maxValue=0,
            description=MultiMount._QuickdrawOptionDescription)

    def weaponCount(self) -> int:
        return self._weaponCountOption.value()

    def instanceString(self) -> str:
        return f'{super().instanceString()} x{self._weaponCountOption.value()}'

    def componentString(self) -> str:
        return f'Multi-Mount'

    def typeString(self) -> str:
        return 'Multi-Mount'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Only compatible with weapons that have a receiver. All sequences are checked as it
        # should be enabled if any weapon has one
        return context.hasComponent(
            componentType=gunsmith.ReceiverInterface,
            sequence=None)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._weaponCountOption, self._quickdrawModifierOption]

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
        weaponCount = common.ScalarCalculation(
            value=self._weaponCountOption.value(),
            name='Specified Weapon Count')

        #
        # Basic Multi-Mount Step
        #

        step = gunsmith.WeaponStep(
            name=f'Weapon Count x{weaponCount.value()}',
            type=self.typeString())

        additionalWeapons = common.Calculator.subtract(
            lhs=weaponCount,
            rhs=common.ScalarCalculation(value=1),
            name=f'{self.componentString()} Additional Weapon Count')

        additionalWeight = common.Calculator.multiply(
            lhs=context.totalWeight(sequence=None), # Total weight at point multi-mount is applied
            rhs=additionalWeapons,
            name=f'{self.componentString()} Additional Weapon Weight')
        step.setWeight(weight=construction.ConstantModifier(value=additionalWeight))

        additionalCost = common.Calculator.multiply(
            lhs=context.totalCredits(sequence=None), # Total cost at point multi-mount is applied
            rhs=additionalWeapons,
            name=f'{self.componentString()} Additional Weapon Cost')
        step.setCredits(credits=construction.ConstantModifier(value=additionalCost))

        barrelCount = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.BarrelCount)
        assert(isinstance(barrelCount, common.ScalarCalculation)) # Construction logic should enforce this

        # Only apply quickdraw modifier to primary weapon as this is a common component so
        # the modifier should only be applied once
        quickdrawModifier = self._quickdrawModifierOption.value()
        if quickdrawModifier < 0 and context.isPrimary(sequence=sequence):
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name='Specified Secondary Weapon Quickdraw Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=quickdrawModifier)))

        # Apply Auto modifier
        autoModifier = common.Calculator.subtract(
            lhs=additionalWeapons,
            rhs=common.ScalarCalculation(value=1),
            name=f'{self.componentString()} Auto Modifier')

        if autoModifier.value() > 0:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Auto,
                modifier=construction.ConstantModifier(
                    value=autoModifier)))

        context.applyStep(
            sequence=sequence,
            step=step)

        #
        # RF/VRF Modification Step
        #

        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return # Launchers and projectors can't be upgrade to RF/VRF

        # Get the Auto score if the weapon has one (it may not). This will be the modified
        # value as the previous step has been applied
        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Auto)
        if not isinstance(autoScore, common.ScalarCalculation):
            return # Nothing to do

        # Handle RF/VRF upgrade
        fireRateTrait = None
        damageDiceDivisor = None
        heatMultiplier = None
        if autoScore.value() >= self._VRFMinAutoLevel.value() \
            or context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.RF):
            # Multi-Mount gives VRF
            fireRateTrait = gunsmith.WeaponAttributeId.VRF
            damageDiceDivisor = self._VRFDamageDiceDivisor
            heatMultiplier = self._VRFHeatMultiplier
        elif autoScore.value() >= self._RFMinAutoLevel.value():
            # Multi-Mount gives RF
            fireRateTrait = gunsmith.WeaponAttributeId.RF
            damageDiceDivisor = self._RFDamageDiceDivisor
            heatMultiplier = self._RFHeatMultiplier
        else:
            return # Multi-mount hasn't given an increase in fire rate

        step = gunsmith.WeaponStep(
            name=f'{fireRateTrait.value} Upgrade',
            type=self.typeString())

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        # AP modifier should be calculated before rapid fire damage dice are added as it's
        # based on the pre-modified number of dice
        apModifier = common.Calculator.equals(
            value=damageRoll.dieCount(),
            name=f'{fireRateTrait.value} {self.componentString()} AP Modifier')
        if apModifier.value() > 0:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AP,
                modifier=construction.ConstantModifier(
                    value=apModifier)))

        additionalDamageDice: common.ScalarCalculation = common.Calculator.divideFloor(
            lhs=damageRoll.dieCount(),
            rhs=damageDiceDivisor,
            name=f'{fireRateTrait.value} {self.componentString()} Additional Damage Dice')
        if additionalDamageDice.value() > 0:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    countModifier=additionalDamageDice)))

        # Only update AutoHeatGeneration if heat rules are enabled for the weapon
        if context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.HeatDissipation):
            totalDamageDice = common.Calculator.add(
                lhs=damageRoll.dieCount(),
                rhs=additionalDamageDice,
                name=f'{fireRateTrait.value} {self.componentString()} Total Damage Dice')
            heatGeneration = common.Calculator.add(
                lhs=autoScore,
                rhs=common.Calculator.multiply(
                    lhs=totalDamageDice,
                    rhs=heatMultiplier),
                name=f'{fireRateTrait.value} {self.componentString()} Heat Generation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AutoHeatGeneration,
                value=heatGeneration))

        step.addFactor(factor=construction.SetAttributeFactor(attributeId=fireRateTrait))

        context.applyStep(
            sequence=sequence,
            step=step)

class MultiMountLoaded(gunsmith.MultiMountLoadedInterface):
    # NOTE: This component is a hack used to multiply the cost of the loaded magazine/ammo cost and
    # weight by the number of multi-mounted weapons
    def __init__(self) -> None:
        super().__init__()

    def componentString(self) -> str:
        return f'Loaded Munitions Multiplier'

    def typeString(self) -> str:
        return 'Multi-Mount'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not context.hasComponent(sequence=sequence, componentType=gunsmith.MultiMount):
            return False

        # Only compatible with weapons that have an magazine or ammunition loaded
        return context.hasComponent(
            sequence=sequence,
            componentType=gunsmith.MagazineLoadedInterface) \
            or \
            context.hasComponent(
                sequence=sequence,
                componentType=gunsmith.AmmoLoadedInterface)

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

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
        multiMount = context.findFirstComponent(
            sequence=sequence,
            componentType=gunsmith.MultiMountInterface)
        assert(isinstance(multiMount, gunsmith.MultiMountInterface))
        weaponCount = common.ScalarCalculation(
            value=multiMount.weaponCount(),
            name='Multi-Mount Weapon Count')

        step = gunsmith.WeaponStep(
            name=self.componentString(),
            type=self.typeString(),
            credits=construction.MultiplierModifier(value=weaponCount),
            weight=construction.MultiplierModifier(value=weaponCount))

        context.applyStep(
            sequence=sequence,
            step=step)
