import common
import construction
import enum
import gunsmith
import typing

class ReceiverFeature(gunsmith.WeaponComponentInterface):
    def __init__(
            self,
            componentString: str,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            minTechLevel: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__()

        if weightModifierPercentage != None and not isinstance(weightModifierPercentage, common.ScalarCalculation):
            weightModifierPercentage = common.ScalarCalculation(
                value=weightModifierPercentage,
                name=f'{componentString} Receiver Weight Modifier Percentage')

        if costModifierPercentage != None and not isinstance(costModifierPercentage, common.ScalarCalculation):
            costModifierPercentage = common.ScalarCalculation(
                value=costModifierPercentage,
                name=f'{componentString} Receiver Cost Modifier Percentage')

        if minTechLevel != None and not isinstance(minTechLevel, common.ScalarCalculation):
            minTechLevel = common.ScalarCalculation(
                value=minTechLevel,
                name=f'{componentString} Minimum Tech Level')

        self._componentString = componentString
        self._weightModifierPercentage = weightModifierPercentage
        self._costModifierPercentage = costModifierPercentage
        self._minTechLevel = minTechLevel

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Receiver Feature'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Enforce minimum TL
        if self._minTechLevel and context.techLevel() < self._minTechLevel.value():
            return False

        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.Receiver,
                sequence=sequence):
            return False

        # Don't allow multiple features of the same type in this sequence
        return not context.hasComponent(
            componentType=type(self),
            sequence=sequence)

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

        if self._weightModifierPercentage:
            step.setWeight(weight=construction.PercentageModifier(
                value=self._weightModifierPercentage))
        if self._costModifierPercentage:
            step.setCredits(credits=construction.PercentageModifier(
                value=self._costModifierPercentage))

        return step

class AdvancedProjectileWeaponFeature(ReceiverFeature):
    """
    - Min TL: 9
    - Receiver Cost: +25%
    - Receiver Weight -10%
    - Physical Signature: One level lower
    - Range: +25%
    - Requirement: Only compatible with projectile weapons (i.e. Conventional Firearms and Launchers)
    """
    # NOTE: I added the requirement about only being compatible with Conventional Firearms and
    # Launchers as Projectors and Energy Weapons aren't projectile weapons
    _RangeModifierPercentage = common.ScalarCalculation(
        value=+25,
        name='Advanced Projectile Weapon Range Modifier Percentage')
    _PhysicalSignatureModifier = common.ScalarCalculation(
        value=-1,
        name='Advanced Projectile Weapon Physical Signature Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Advanced Projectile Weapon',
            minTechLevel=9,
            weightModifierPercentage=-10,
            costModifierPercentage=+25)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Only compatible with projectile weapons
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Range,
            modifier=construction.PercentageModifier(
                value=self._RangeModifierPercentage)))

        if not context.hasComponent(
                componentType=gunsmith.ArchaicCalibre,
                sequence=sequence):
            # Projectile weapons are always expected to have a physical signature
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
                modifier=construction.ConstantModifier(
                    value=self._PhysicalSignatureModifier)))

        return step

class AccurisedFeature(ReceiverFeature):
    """
    - Receiver Cost: +100%
    - Note: DM+1 to attack rolls at ranges >= 25m if aimed
    """
    _Note = 'DM+1 to attack rolls at ranges >= 25m if aimed'

    def __init__(self) -> None:
        super().__init__(
            componentString='Accurised',
            costModifierPercentage=+100)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._Note)
        return step

class BullpupFeature(ReceiverFeature):
    """
    - Receiver Cost: +25%
    - Quickdraw: +2 (Primary weapon only)
    - Note: Must be specified as left or right handed
    - Requirement: Must have a Full Stock
    - Requirement: Not compatible with Projectors
    """
    # NOTE: Requirement about having a Full Stock is handled in Stock code
    # NOTE: I've added the requirement about not being compatible with projectors as they don't
    # have an ammo feed to be moved or a stock to move it into
    # NOTE: I've added the requirement that the Quickdraw modifier is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # The Quickdraw modifier for the Bullpup feature is not applied as it's a positive modifier and
    # would result in a secondary weapon with the feature causing the weapon as a whole to have a
    # better Quickdraw score than it would if it didn't have the secondary weapon. It's still
    # desirable to allow the user to add Bullpup to a secondary weapon as some referees may rule
    # that both the primary and secondary weapon may require the feature (and therefore the cost
    # modifier) in order for the weapon as a whole to get the Quickdraw modifier.

    class _HandedSetup(enum.Enum):
        RightHanded = 'Right Handed'
        LeftHanded = 'Left Handed'

    _QuickdrawModifier = common.ScalarCalculation(
        value=+2,
        name='Bullpup Quickdraw Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Bullpup',
            costModifierPercentage=+25)

        self._setupOption = construction.EnumOption(
            id='Setup',
            name='Setup',
            type=BullpupFeature._HandedSetup,
            value=BullpupFeature._HandedSetup.RightHanded,
            description='Bullpup weapons must be set up for a left or right handed shooter.')

    def instanceString(self) -> str:
        setup = self._setupOption.value()
        assert(isinstance(setup, BullpupFeature._HandedSetup))
        return super().instanceString() + f' ({setup.value})'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.ProjectorReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._setupOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Quickdraw,
            modifier=construction.ConstantModifier(
                value=self._QuickdrawModifier)))

        setup = self._setupOption.value()
        assert(isinstance(setup, BullpupFeature._HandedSetup))
        step.addNote(note=f'Weapon can only be used {setup.value.lower()}')

        return step

class SizeReductionFeature(ReceiverFeature):
    """
    - Ammo Capacity: Capacity reduction doesn't apply to power pack energy weapons
    - Requirement: Not compatible with other size reduction features
    - Requirement: Not compatible with High Capacity
    - Requirement: Not compatible with Projectors
    - Requirement: Not compatible in cases where it would reduce ammo capacity below weapon minimum
    """
    # NOTE: I've added the caveat that the ammo capacity is handled differently for power pack
    # energy weapons as their "capacity" is determined by the power pack size
    # NOTE: I added the requirement about not being compatible with projectors as you can
    # just specify a lower propellant/fuel capacity to reduce the weight. In theory you could
    # have it reduce the structure weight but that would be complicated and isn't worth the
    # effort for now
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

    def __init__(
            self,
            componentString: str,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]],
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]],
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]]
            ) -> None:
        super().__init__(
            componentString=componentString,
            weightModifierPercentage=weightModifierPercentage,
            costModifierPercentage=costModifierPercentage)

        if not isinstance(capacityModifierPercentage, common.ScalarCalculation):
            capacityModifierPercentage = common.ScalarCalculation(
                value=capacityModifierPercentage,
                name=f'{componentString} Ammo Capacity Percentage Modifier')

        self._capacityModifierPercentage = capacityModifierPercentage

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with Projectors
        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Not compatible with other size reduction features, High Capacity
        if context.hasComponent(
                componentType=SizeReductionFeature,
                sequence=sequence) \
            or context.hasComponent(
                componentType=HighCapacityFeature,
                sequence=sequence):
            return False

        # Only compatible if the capacity reduction wouldn't reduce the weapons
        # capacity to below the allowed minimum
        return self._checkCapacityCompatibility(
            sequence=sequence,
            context=context)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Don't adjust ammo capacity for power pack energy weapons as their capacity
        # comes from the power pack size
        if not context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
                modifier=construction.PercentageModifier(
                    value=self._capacityModifierPercentage,
                    roundDown=True)))

        return step

    def _checkCapacityCompatibility(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence):
            # Capacity reduction isn't applied to power pack weapons so the feature is always
            # applied compatible with them
            return True

        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
        if not isinstance(ammoCapacity, common.ScalarCalculation):
            return False

        minCapacity = 1
        if context.hasComponent(
                componentType=gunsmith.CompleteMultiBarrelSetup,
                sequence=sequence):
            # The sequence has a complete multi barrel setup so the minimum capacity is
            # equal to the number of barrels
            barrelCount = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.BarrelCount)
            if not isinstance(ammoCapacity, common.ScalarCalculation):
                return False
            minCapacity = barrelCount.value()

        modifiedCapacity = common.Calculator.floor(
            value=common.Calculator.applyPercentage(
                value=ammoCapacity,
                percentage=self._capacityModifierPercentage))
        return modifiedCapacity.value() >= minCapacity

class CompactFeature(SizeReductionFeature):
    """
    - Receiver Cost: +25%
    - Receiver Weight: -10%
    - Ammo Capacity: -25% (except for Energy Weapons)
    - Requirement: Not compatible with Very Compact
    - Requirement: Not compatible with High Capacity
    - Requirement: Not compatible with Projectors
    """

    _CapacityModifierPercentage = common.ScalarCalculation(
        value=-25,
        name='Compact Ammo Capacity Modifier Percentage')

    def __init__(self) -> None:
        super().__init__(
            componentString='Compact',
            weightModifierPercentage=-10,
            costModifierPercentage=+25,
            capacityModifierPercentage=-25)

class VeryCompactFeature(SizeReductionFeature):
    """
    - Receiver Cost: +40%
    - Receiver Weight: -20%
    - Ammo Capacity: -50%
    - Requirement: Not compatible with Compact
    - Requirement: Not compatible with High Capacity
    - Requirement: Not compatible with Projectors
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Very Compact',
            weightModifierPercentage=-20,
            costModifierPercentage=+40,
            capacityModifierPercentage=-50)

class CoolingSystemFeature(ReceiverFeature):
    """
    - Basic:
        - Receiver Cost: +10%
        - Receiver Weight: +100%
        - Heat: -2 per round even when being fired
    - Advanced:
        - Receiver Cost: +50%
        - Receiver Weight: +20%
        - Heat: -5 per round even when being fired
    - Requirement: Only compatible with weapons that have a HeatDissipating attribute
    """
    # NOTE: I added the requirement about only being compatible with weapons that have a HeatDissipating
    # attribute in order to disable the feature for weapons with optional heat rules turned off. It's
    # important this check is made using HeatDissipating rather than HeatGeneration as most weapon types
    # don't have a HeatGeneration value until the fire rate is applied

    class _CoolingType(enum.Enum):
        Basic = 'Basic'
        Advanced = 'Advanced'

    _CoolingTypeCostWeightHeatModifierMap = {
        _CoolingType.Basic: (+10, +100, -2),
        _CoolingType.Advanced: (+50, +20, -5)
    }

    def __init__(self) -> None:
        super().__init__(componentString='Cooling System')

        self._coolingTypeOption = construction.EnumOption(
            id='CoolingType',
            name='Cooling Type',
            type=CoolingSystemFeature._CoolingType,
            value=CoolingSystemFeature._CoolingType.Basic,
            description='Specify the cooling system type.')

    def instanceString(self) -> str:
        coolingType: CoolingSystemFeature._CoolingType = self._coolingTypeOption.value()
        return f'{self.componentString()} ({coolingType.value})'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Only compatible with weapons that have the HeatDissipation attribute.
        return context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.HeatDissipation)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._coolingTypeOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        instanceString = self.instanceString()

        costModifier, weightModifier, heatModifier = \
            CoolingSystemFeature._CoolingTypeCostWeightHeatModifierMap.get(
                self._coolingTypeOption.value(),
                (None, None, None))

        assert(costModifier != None)
        costModifier = common.ScalarCalculation(
            value=costModifier,
            name=f'{instanceString} Receiver Cost Modifier Percentage')

        assert(weightModifier != None)
        weightModifier = common.ScalarCalculation(
            value=weightModifier,
            name=f'{instanceString} Receiver Weight Modifier Percentage')

        assert(heatModifier != None)
        heatModifier = common.ScalarCalculation(
            value=heatModifier,
            name=f'{instanceString} Heat Dissipation Modifier')

        step.setCredits(credits=construction.PercentageModifier(
            value=costModifier))
        step.setWeight(weight=construction.PercentageModifier(
            value=weightModifier))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.HeatDissipation,
            modifier=construction.ConstantModifier(value=heatModifier)))

        return step

class GuidanceSystemFeature(ReceiverFeature):
    """
    - Receiver Cost: +50%
    - Requirement: Only applicable on weapons that launch missiles
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Guidance System',
            costModifierPercentage=+50)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence)

class HighCapacityFeature(ReceiverFeature):
    """
    - Receiver Cost: +20%
    - Receiver Weight: +10%
    - Ammo Capacity: +20%
    - Requirement: Not compatible with Compact and Very Compact
    - Requirement: Not compatible with Single Shot Mechanism where Ammo Capacity is determined by number of barrels
    - Requirement: Not compatible with Projectors or Energy Weapons
    """
    # NOTE: I added the requirement about not being compatible with projectors or energy weapons as
    # their capacities are handled differently
    _CapacityModifierPercentage = common.ScalarCalculation(
        value=+20,
        name='High Capacity Ammo Capacity Modifier Percentage')

    def __init__(self) -> None:
        super().__init__(
            componentString='High Capacity',
            weightModifierPercentage=+10,
            costModifierPercentage=+20)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with Projectors
        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Not compatible with Single Shot Weapons
        if context.hasComponent(
                componentType=gunsmith.SingleShotMechanism,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LightSingleShotLauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence):
            return False

        return not context.hasComponent(
            componentType=CompactFeature,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=VeryCompactFeature,
                sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=HighCapacityFeature._CapacityModifierPercentage,
                roundDown=True)))

        return step

class HighQualityFeature(ReceiverFeature):
    """
    - Receiver Cost: >= +50%
    - Requirement: Not compatible with Low Quality feature
    """
    # NOTE: From what I can tell this feature is intended to let you modify any weapon
    # attribute(s) for a cost agreed with the Referee. I've had to limit to avoid
    # cluttering the UI to much with options for different attributes. I've gone with
    # the subset of attributes I think users will most likely want to modify, generally
    # these are attributes that don't have other features that allow you to modify them
    # or where modification options are limited.

    def __init__(self) -> None:
        super().__init__(componentString='High Quality')

        self._rangeModifierOption = construction.IntegerOption(
            id='RangeModifier',
            name='Range Modifier',
            value=0,
            minValue=0,
            description='Specify the Range increase given by the High Quality feature.')

        self._costPercentageOption = construction.FloatOption(
            id='CostIncrease',
            name='Receiver Cost Increase (%)',
            value=50,
            minValue=50,
            description='Specify the amount to spend on the feature.')

        self._quickdrawModifierOption = construction.IntegerOption(
            id='QuickdrawModifier',
            name='Quickdraw Modifier',
            value=0,
            minValue=0,
            description='Specify the Quickdraw increase given by the High Quality feature.')

        self._damageDiceModifierOption = construction.IntegerOption(
            id='DamageDiceModifier',
            name='Damage Dice Modifier',
            value=0,
            minValue=0,
            description='Specify the Damage Dice increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._damageConstantModifierOption = construction.IntegerOption(
            id='DamageConstantModifier',
            name='Damage Constant Modifier',
            value=0,
            minValue=0,
            description='Specify the Constant Damage increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._recoilModifierOption = construction.IntegerOption(
            id='RecoilModifier',
            name='Recoil Modifier',
            value=0,
            maxValue=0,
            description='Specify the Recoil reduction given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._penetrationModifierOption = construction.IntegerOption(
            id='PenetrationModifier',
            name='Penetration Modifier',
            value=0,
            minValue=0,
            description='Specify the Penetration increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._heatDissipationModifierOption = construction.IntegerOption(
            id='HeatDissipationModifier',
            name='Heat Dissipation Modifier',
            value=0,
            minValue=0,
            description='Specify the Heat Dissipation increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._overheatThresholdModifierOption = construction.IntegerOption(
            id='OverheatThresholdModifier',
            name='Overheat Threshold Modifier',
            value=0,
            minValue=0,
            description='Specify the Overheat Threshold increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._dangerHeatThresholdModifierOption = construction.IntegerOption(
            id='DangerHeatThresholdModifier',
            name='Danger Heat Threshold Modifier',
            value=0,
            minValue=0,
            description='Specify the Danger Heat Threshold increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._disasterHeatThresholdModifierOption = construction.IntegerOption(
            id='DisasterHeatThresholdModifier',
            name='Disaster Heat Threshold Modifier',
            value=0,
            minValue=0,
            description='Specify the Disaster Heat Threshold increase given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._physicalSignatureModifierOption = construction.IntegerOption(
            id='PhysicalSignatureModifier',
            name='Physical Signature Modifier',
            value=0,
            maxValue=0,
            description='Specify the Physical Signature reduction given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._emissionsSignatureModifierOption = construction.IntegerOption(
            id='EmissionsSignatureModifier',
            name='Emission Signature Modifier',
            value=0,
            maxValue=0,
            description='Specify the Emissions Signature reduction given by the High Quality feature.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._noteOption = construction.StringOption(
            id='EffectNote',
            name='Effect Note',
            value='',
            description='Specify any other effects of the High Quality feature.')

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        return not context.hasComponent(
            componentType=LowQualityFeature,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()

        options.append(self._costPercentageOption)
        options.append(self._rangeModifierOption)
        options.append(self._quickdrawModifierOption)

        if self._damageDiceModifierOption.isEnabled():
            options.append(self._damageDiceModifierOption)

        if self._damageConstantModifierOption.isEnabled():
            options.append(self._damageConstantModifierOption)

        if self._recoilModifierOption.isEnabled():
            options.append(self._recoilModifierOption)

        if self._penetrationModifierOption.isEnabled():
            options.append(self._penetrationModifierOption)

        if self._heatDissipationModifierOption.isEnabled():
            options.append(self._heatDissipationModifierOption)

        if self._overheatThresholdModifierOption.isEnabled():
            options.append(self._overheatThresholdModifierOption)

        if self._dangerHeatThresholdModifierOption.isEnabled():
            options.append(self._dangerHeatThresholdModifierOption)

        if self._disasterHeatThresholdModifierOption.isEnabled():
            options.append(self._disasterHeatThresholdModifierOption)

        if self._physicalSignatureModifierOption.isEnabled():
            options.append(self._physicalSignatureModifierOption)

        if self._emissionsSignatureModifierOption.isEnabled():
            options.append(self._emissionsSignatureModifierOption)

        options.append(self._noteOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)

        allowDamageModifier = self._allowDamageModifier(
            sequence=sequence,
            context=context)
        self._damageDiceModifierOption.setEnabled(allowDamageModifier)
        self._damageConstantModifierOption.setEnabled(allowDamageModifier)

        allowRecoilModifier = self._allowRecoilModifier(
            sequence=sequence,
            context=context)
        self._recoilModifierOption.setEnabled(allowRecoilModifier)

        allowPenetrationModifier = self._allowPenetrationModifier(
            sequence=sequence,
            context=context)
        self._penetrationModifierOption.setEnabled(allowPenetrationModifier)

        allowHeatModifier = self._allowHeatModifier(
            sequence=sequence,
            context=context)
        self._heatDissipationModifierOption.setEnabled(allowHeatModifier)
        self._overheatThresholdModifierOption.setEnabled(allowHeatModifier)
        self._dangerHeatThresholdModifierOption.setEnabled(allowHeatModifier)
        self._disasterHeatThresholdModifierOption.setEnabled(allowHeatModifier)
        if allowHeatModifier:
            self._updateHeatThresholdOptions(
                sequence=sequence,
                context=context)

        allowPhysicalSignatureModifier = self._allowPhysicalSignatureModifier(
            sequence=sequence,
            context=context)
        self._physicalSignatureModifierOption.setEnabled(allowPhysicalSignatureModifier)

        allowEmissionsSignatureModifier = self._allowEmissionsSignatureModifier(
            sequence=sequence,
            context=context)
        self._emissionsSignatureModifierOption.setEnabled(allowEmissionsSignatureModifier)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        cost = common.ScalarCalculation(
            value=self._costPercentageOption.value(),
            name='Specified Receiver Cost Percentage')
        step.setCredits(credits=construction.PercentageModifier(value=cost))

        rangeModifier = self._rangeModifierOption.value()
        if rangeModifier > 0: # Range modifiers are positive
            rangeModifier = common.ScalarCalculation(
                value=rangeModifier,
                name='Specified Range Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Range,
                modifier=construction.ConstantModifier(value=rangeModifier)))

        quickdrawModifier = self._quickdrawModifierOption.value()
        if quickdrawModifier > 0: # Quickdraw modifiers are positive
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name='Specified Quickdraw Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(value=quickdrawModifier)))

        if self._allowDamageModifier(sequence=sequence, context=context):
            damageDiceModifier = self._damageDiceModifierOption.value()
            if damageDiceModifier > 0: # Damage dice modifiers are positive
                damageDiceModifier = common.ScalarCalculation(
                    value=damageDiceModifier,
                    name='Specified Damage Dice Modifier')
            else:
                damageDiceModifier = None

            damageConstantModifier = self._damageConstantModifierOption.value()
            if damageConstantModifier > 0: # Damage constant modifiers are positive
                damageConstantModifier = common.ScalarCalculation(
                    value=damageConstantModifier,
                    name='Specified Damage Constant Modifier')
            else:
                damageConstantModifier = None

            if damageDiceModifier or damageConstantModifier:
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.Damage,
                    modifier=construction.DiceRollModifier(
                        countModifier=damageDiceModifier,
                        constantModifier=damageConstantModifier)))

        if self._allowRecoilModifier(sequence=sequence, context=context):
            recoilModifier = self._recoilModifierOption.value()
            if recoilModifier < 0: # Recoil modifiers are negative
                recoilModifier = common.ScalarCalculation(
                    value=recoilModifier,
                    name='Specified Recoil Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.Recoil,
                    modifier=construction.ConstantModifier(value=recoilModifier)))

        if self._allowPenetrationModifier(sequence=sequence, context=context):
            penetrationModifier = self._penetrationModifierOption.value()
            if penetrationModifier > 0: # Penetration modifiers are positive
                penetrationModifier = common.ScalarCalculation(
                    value=penetrationModifier,
                    name='Specified Penetration Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.Penetration,
                    modifier=construction.ConstantModifier(value=penetrationModifier)))

        if self._allowHeatModifier(sequence=sequence, context=context):
            heatDissipationModifier = self._heatDissipationModifierOption.value()
            if heatDissipationModifier > 0: # Heat dissipation modifiers are positive
                heatDissipationModifier = common.ScalarCalculation(
                    value=heatDissipationModifier,
                    name='Specified Heat Dissipation Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.HeatDissipation,
                    modifier=construction.ConstantModifier(value=heatDissipationModifier)))

            overheatModifier = self._overheatThresholdModifierOption.value()
            if overheatModifier > 0: # Overheat threshold modifiers are positive
                overheatModifier = common.ScalarCalculation(
                    value=overheatModifier,
                    name='Specified Overheat Threshold Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.OverheatThreshold,
                    modifier=construction.ConstantModifier(value=overheatModifier)))

            dangerHeatModifier = self._dangerHeatThresholdModifierOption.value()
            if dangerHeatModifier > 0: # Overheat threshold modifiers are positive
                dangerHeatModifier = common.ScalarCalculation(
                    value=dangerHeatModifier,
                    name='Specified Danger Heat Threshold Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold,
                    modifier=construction.ConstantModifier(value=dangerHeatModifier)))

            disasterHeatModifier = self._disasterHeatThresholdModifierOption.value()
            if disasterHeatModifier > 0: # Overheat threshold modifiers are positive
                disasterHeatModifier = common.ScalarCalculation(
                    value=disasterHeatModifier,
                    name='Specified Disaster Heat Threshold Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold,
                    modifier=construction.ConstantModifier(value=disasterHeatModifier)))

        if self._allowPhysicalSignatureModifier(sequence=sequence, context=context):
            physicalSignatureModifier = self._physicalSignatureModifierOption.value()
            if physicalSignatureModifier < 0: # Signature modifiers are negative
                physicalSignatureModifier = common.ScalarCalculation(
                    value=physicalSignatureModifier,
                    name='Specified Physical Signature Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
                    modifier=construction.ConstantModifier(value=physicalSignatureModifier)))

        if self._allowEmissionsSignatureModifier(sequence=sequence, context=context):
            emissionsSignatureModifier = self._emissionsSignatureModifierOption.value()
            if emissionsSignatureModifier < 0: # Signature modifiers are negative
                emissionsSignatureModifier = common.ScalarCalculation(
                    value=emissionsSignatureModifier,
                    name='Specified Emissions Signature Modifier')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.EmissionsSignature,
                    modifier=construction.ConstantModifier(value=emissionsSignatureModifier)))

        effectNote = self._noteOption.value()
        if effectNote:
            step.addNote(note=effectNote)

        return step

    def _allowDamageModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Damage modifiers only make sense for conventional and energy weapons.
        # Damage for launchers and projectors comes from the payload/fuel so the
        # weapon giving a modifier doesn't make much sense.
        return not context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence)

    def _allowRecoilModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Recoil is only applied to conventional weapons
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def _allowPenetrationModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Penetration only applies to conventional and directed energy weapons
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence)

    def _allowHeatModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # It's important this check is made against HeatDissipating rather than HeatGeneration as
        # most weapon types don't have a HeatGeneration value until the fire rate is applied
        return context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.HeatDissipation)

    def _allowPhysicalSignatureModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Archaic weapons can't have their physical signature lowered
        return context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.PhysicalSignature) \
            and not context.hasComponent(
                componentType=gunsmith.ArchaicCalibre,
                sequence=sequence)

    def _allowEmissionsSignatureModifier(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Archaic weapons can't have their physical signature lowered
        return context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.EmissionsSignature)

    def _updateHeatThresholdOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        currentOverheatThreshold = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.OverheatThreshold)
        currentDangerThreshold = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold)
        currentDisasterThreshold = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold)
        if not isinstance(currentOverheatThreshold, common.ScalarCalculation) or \
                not isinstance(currentDangerThreshold, common.ScalarCalculation) or \
                not isinstance(currentDisasterThreshold, common.ScalarCalculation):
            return # Nothing to do
        currentOverheatThreshold = currentOverheatThreshold.value()
        currentDangerThreshold = currentDangerThreshold.value()
        currentDisasterThreshold = currentDisasterThreshold.value()

        # Force a danger threshold modifier large enough to keep the modified danger threshold
        # above the modified overheat threshold
        modifiedOverheatThreshold = currentOverheatThreshold + self._overheatThresholdModifierOption.value()
        minDangerThreshold = max(currentDangerThreshold, modifiedOverheatThreshold + 1)
        self._dangerHeatThresholdModifierOption.setMin(value=minDangerThreshold - currentDangerThreshold)

        # Force a disaster threshold modifier large enough to keep the modified disaster threshold
        # above the modified danger threshold. The danger threshold must be re-retrieved from the
        # option to take into account any modification from the previous steps
        modifiedDangerThreshold = currentDangerThreshold + self._dangerHeatThresholdModifierOption.value()
        minDisasterThreshold = max(currentDisasterThreshold, modifiedDangerThreshold + 1)
        self._disasterHeatThresholdModifierOption.setMin(value=minDisasterThreshold - currentDisasterThreshold)

class LowQualityFeature(ReceiverFeature):
    """
    - Low:
        - Receiver Cost: -10%
        - Deficiency Points: 1
    - Very Low:
        - Receiver Cost: -20%
        - Deficiency Points: 2
    - Extremely Low
        - Receiver Cost: -40%
        - Deficiency Points: 3
    - Appalling
        - Receiver Cost: -60%
        - Deficiency Points: 5
    - Piece Of Junk
        - Receiver Cost: -80%
        - Deficiency Points: 8
    - Requirement: Not compatible with High Quality feature
    """
    # NOTE: So that the component is valid by default it initialises the number of
    # Inaccurate level to the required number of deficiency points

    class _QualityLevel(enum.Enum):
        Low = 'Low'
        VeryLow = 'Very Low'
        ExtremelyLow = 'Extremely Low'
        Appalling = 'Appalling'
        PieceOfJunk = 'Piece Of Junk'

    _QualityCostDeficiencyModifierMap = {
        _QualityLevel.Low: (-10, 1),
        _QualityLevel.VeryLow: (-20, 2),
        _QualityLevel.ExtremelyLow: (-40, 3),
        _QualityLevel.Appalling: (-60, 5),
        _QualityLevel.PieceOfJunk: (-80, 8)
    }

    _InaccurateDeficiencyMultiplier = 1
    _HazardousDeficiencyMultiplier = 1
    _RamshackleDeficiencyMultiplier = 2
    _UnreliableDeficiencyMultiplier = 3

    _TraitOptionDescriptionFormat = \
        '<p>Specify the number of points of the {trait} trait to give the weapon to ' \
        'offset the Reduced Quality deficiency points. Each point of {trait} offsets ' \
        '{offset} deficiency points.</p>'
    _InaccurateOptionDescription = _TraitOptionDescriptionFormat.format(trait='Inaccurate', offset=_InaccurateDeficiencyMultiplier)
    _HazardousOptionDescription = _TraitOptionDescriptionFormat.format(trait='Hazardous', offset=_HazardousDeficiencyMultiplier)
    _RamshackleOptionDescription = _TraitOptionDescriptionFormat.format(trait='Ramshackle', offset=_RamshackleDeficiencyMultiplier)
    _UnreliableOptionDescription = _TraitOptionDescriptionFormat.format(trait='Unreliable', offset=_UnreliableDeficiencyMultiplier)

    def __init__(self) -> None:
        super().__init__(componentString='Low Quality')

        self._qualityLevelOption = construction.EnumOption(
            id='QualityLevel',
            name='Quality Level',
            type=LowQualityFeature._QualityLevel,
            value=LowQualityFeature._QualityLevel.Low,
            description='Specify the quality level.')

        self._inaccurateLevelsOption = construction.IntegerOption(
            id='Inaccurate',
            name='Inaccurate Levels',
            value=1, # Required points for default of low quality
            minValue=0,
            description=LowQualityFeature._InaccurateOptionDescription)

        self._hazardousLevelsOption = construction.IntegerOption(
            id='Hazardous',
            name='Hazardous Levels',
            value=0,
            minValue=0,
            description=LowQualityFeature._HazardousOptionDescription)

        self._ramshackleLevelsOption = construction.IntegerOption(
            id='Ramshackle',
            name='Ramshackle Levels',
            value=0,
            minValue=0,
            description=LowQualityFeature._RamshackleOptionDescription)

        self._unreliableLevelsOption = construction.IntegerOption(
            id='Unreliable',
            name='Unreliable Levels',
            value=0,
            minValue=0,
            description=LowQualityFeature._UnreliableOptionDescription)

    def instanceString(self) -> str:
        qualityLevel: LowQualityFeature._QualityLevel = self._qualityLevelOption.value()
        return f'{self.componentString()} ({qualityLevel.value})'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=HighQualityFeature,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._qualityLevelOption)
        options.append(self._inaccurateLevelsOption)
        options.append(self._hazardousLevelsOption)
        options.append(self._ramshackleLevelsOption)
        options.append(self._unreliableLevelsOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        instanceString = self.instanceString()

        costModifier, requiredDeficiencyPoints = \
            LowQualityFeature._QualityCostDeficiencyModifierMap.get(
                self._qualityLevelOption.value(),
                (None, None))

        assert(costModifier != None)
        costModifier = common.ScalarCalculation(
            value=costModifier,
            name=f'{instanceString} Receiver Cost Modifier Percentage')

        requiredDeficiencyPoints = common.ScalarCalculation(
            value=requiredDeficiencyPoints,
            name=f'{instanceString} Required Deficiency Points')

        totalPoints = 0

        inaccurateLevels = common.ScalarCalculation(
            value=self._inaccurateLevelsOption.value(),
            name='Specified Inaccurate Levels')
        totalPoints += inaccurateLevels.value() * self._InaccurateDeficiencyMultiplier

        hazardousLevels = common.ScalarCalculation(
            value=self._hazardousLevelsOption.value(),
            name='Specified Hazardous Levels')
        totalPoints += hazardousLevels.value() * self._HazardousDeficiencyMultiplier

        ramshackleLevels = common.ScalarCalculation(
            value=self._ramshackleLevelsOption.value(),
            name='Specified Ramshackle Levels')
        totalPoints += ramshackleLevels.value() * self._RamshackleDeficiencyMultiplier

        unreliableLevels = common.ScalarCalculation(
            value=self._unreliableLevelsOption.value(),
            name='Specified Unreliable Levels')
        totalPoints += unreliableLevels.value() * self._UnreliableDeficiencyMultiplier

        if totalPoints < requiredDeficiencyPoints.value():
            # An insufficient number of deficiency points have been specified. Create a new step to
            # replace the one generated by the base class. This will have no cost or weight
            # reduction and a single note explaining what is going on
            step = gunsmith.WeaponStep(
                name=self.instanceString(),
                type=self.typeString(),
                factors=[construction.StringFactor(
                    string=f'WARNING: {requiredDeficiencyPoints.value()} deficiency points are required')],
                notes=[f'{self.componentString()} not applied as insufficient deficiency points were specified, {totalPoints} were specified when {requiredDeficiencyPoints.value()} are required'])
            return step # Return this step rather than the one created by the base class

        step.setCredits(credits=construction.PercentageModifier(
            value=costModifier))

        if totalPoints > requiredDeficiencyPoints.value():
            # Don't prevent more deficiency points than required being specified but warn about it
            step.addNote(
                note=f'More deficiency points than required specified for {self.componentString()}, {totalPoints} were specified when only {requiredDeficiencyPoints.value()} are required')

        if inaccurateLevels.value() > 0:
            inaccurateModifier = common.Calculator.negate(
                value=inaccurateLevels,
                name='Inaccurate Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Inaccurate,
                modifier=construction.ConstantModifier(value=inaccurateModifier)))

        if hazardousLevels.value() > 0:
            hazardousModifier = common.Calculator.negate(
                value=hazardousLevels,
                name='Hazardous Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Hazardous,
                modifier=construction.ConstantModifier(value=hazardousModifier)))

        if ramshackleLevels.value() > 0:
            ramshackleModifier = common.Calculator.negate(
                value=ramshackleLevels,
                name='Ramshackle Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Ramshackle,
                modifier=construction.ConstantModifier(value=ramshackleModifier)))

        if unreliableLevels.value() > 0:
            unreliableModifier = common.Calculator.equals(
                value=unreliableLevels,
                name='Unreliable Modifier')
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Unreliable,
                modifier=construction.ConstantModifier(value=unreliableModifier)))

        return step

class IncreasedFireRateFeature(ReceiverFeature):
    """
    - Receiver Cost/Weight:
        - Level 1: +10% / +5%
        - Level 2: +25% / +10%
        - Level 3: +50% / +20%
        - Level 4: +100% / +40%
        - Level 5: +200% / +60%
        - Level 6: +300% / +80%
    - Requirement: Only applicable with weapons that have a burst capable, fully automatic or
      mechanical rotary mechanism
    """
    # NOTE: I've expanded the requirement to also allow this with Mechanical Rotary Mechanisms.
    # If you don't do this the rules don't allow you to add RF to a mechanical rotary weapon with
    # less than 8 barrels (or less than 12 for VRF). This doesn't seem correct as I would assume a
    # modern day minigun would be counted as at least RF but it only has 6 barrels.

    # Mapping of auto increase to the percentage receiver cost and weight the add
    _AutoIncreaseCostWeightModifierMap = {
        1: (+10, +5),
        2: (+25, +10),
        3: (+50, +20),
        4: (+100, +40),
        5: (+200, +60),
        6: (+300, +80)
    }

    def __init__(self) -> None:
        super().__init__(componentString='Increased Fire Rate')

        self._autoIncreaseOption = construction.IntegerOption(
            id='AutoIncrease',
            name='Auto Increase',
            value=1,
            minValue=1,
            maxValue=6,
            description='Specify the increase in Auto Score.')

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._autoIncreaseOption.value()})'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Requires one of the auto mechanisms (burst capable, fully automatic or rotary)
        return context.hasComponent(
            componentType=gunsmith.AutoMechanism,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._autoIncreaseOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        instanceString = self.instanceString()

        autoIncrease = common.ScalarCalculation(
            value=self._autoIncreaseOption.value(),
            name='Specified Auto Increase')

        costModifier, weightModifier = IncreasedFireRateFeature._AutoIncreaseCostWeightModifierMap.get(
            autoIncrease.value(),
            (None, None))

        assert(costModifier != None)
        costModifier = common.ScalarCalculation(
            value=costModifier,
            name=f'{instanceString} Receiver Cost Modifier Percentage')

        assert(weightModifier != None)
        weightModifier = common.ScalarCalculation(
            value=weightModifier,
            name=f'{instanceString} Receiver Weight Modifier Percentage')

        step.setCredits(credits=construction.PercentageModifier(
            value=costModifier))
        step.setWeight(weight=construction.PercentageModifier(
            value=weightModifier))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Auto,
            modifier=construction.ConstantModifier(value=autoIncrease)))

        return step

class LightweightFeature(ReceiverFeature):
    """
    - Requirement: Not compatible with Projectors
    """
    # NOTE: I added the requirement about not being compatible with projectors as you can
    # just specify a lower propellant/fuel capacity to reduce the weight. In theory you could
    # have it reduce the structure weight but that would be complicated and isn't worth the
    # effort for now

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        return not context.hasComponent(
            componentType=LightweightFeature,
            sequence=sequence)

class LessDurableLightweightFeature(LightweightFeature):
    """
    - Receiver Weight: -20%
    - Trait: Hazardous (-1)
    - Requirement: Not compatible with other Lightweight or Lightweight, Extreme features
    """
    _HazardousModifier = common.ScalarCalculation(
        value=-1,
        name='Lightweight (Less Durable) Hazardous Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Lightweight (Less Durable)',
            weightModifierPercentage=-20)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Hazardous,
            modifier=construction.ConstantModifier(
                value=self._HazardousModifier)))

        return step

class BetterMaterialsLightweightFeature(LightweightFeature):
    """
    - Receiver Weight: -20%
    - Receiver Cost: +50%
    - Requirement: Not compatible with other Lightweight or Lightweight, Extreme features
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Lightweight (Better Materials)',
            weightModifierPercentage=-20,
            costModifierPercentage=+50)

class LessDurableExtremeLightweightFeature(LightweightFeature):
    """
    - Receiver Weight: -40%
    - Trait: Hazardous (-3)
    - Requirement: Not compatible with other Lightweight or Lightweight, Extreme features
    """
    _HazardousModifier = common.ScalarCalculation(
        value=-3,
        name='Extreme Lightweight (Less Durable) Hazardous Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Extreme Lightweight (Less Durable)',
            weightModifierPercentage=-40)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Hazardous,
            modifier=construction.ConstantModifier(
                value=self._HazardousModifier)))

        return step

class BetterMaterialsExtremeLightweightFeature(LightweightFeature):
    """
    - Receiver Weight: -40%
    - Receiver Cost: +200%
    - Requirement: Not compatible with other Lightweight or Lightweight, Extreme features
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Extreme Lightweight (Better Materials)',
            weightModifierPercentage=-40,
            costModifierPercentage=+200)

class QuickdrawFeature(ReceiverFeature):
    """
    - Receiver Cost: +20%
    - Quickdraw: +2 (Primary weapon only)
    - Note: DM+1 to attack rolls at ranges < 25m
    - Note: DM-1 to attack rolls at ranges >= 25m
    """
    # NOTE: I've added the requirement that the Quickdraw modifier is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # The Quickdraw modifier for the Quickdraw feature is not applied as it's a positive modifier and
    # would result in a secondary weapon with the feature causing the weapon as a whole to have a
    # better Quickdraw score than it would if it didn't have the secondary weapon. It's still
    # desirable to allow the user to add Quickdraw to a secondary weapon as some referees may rule
    # that both the primary and secondary weapon may require the feature (and therefore the cost
    # modifier) in order for the weapon as a whole to get the Quickdraw modifier.
    #
    _QuickdrawIncrease = common.ScalarCalculation(
        value=+2,
        name='Quickdraw Feature Quickdraw Modifier')
    _Notes = [
        'DM+1 to attack rolls at ranges < 25m',
        'DM-1 to attack rolls at ranges >= 25m'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Quickdraw',
            costModifierPercentage=+20)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Quickdraw,
            modifier=construction.ConstantModifier(
                value=self._QuickdrawIncrease)))

        for note in self._Notes:
            step.addNote(note=note)

        return step

class RecoilCompensationFeature(ReceiverFeature):
    """
    - Level 1:
        - Receiver Cost: +10%
        - Receiver Weight: +5%
        - Recoil: -1
        - Damage: -1
    - Level 2:
        - Receiver Cost: +20%
        - Receiver Weight: +10%
        - Recoil: -2
        - Damage: -3
    - Requirement: Only compatible with conventional weapons as only they have recoil
    """
    _CompensationLevelCostWeightDamageModifierMap = {
        1: (+10, +5, -1),
        2: (+20, +10, -3)
    }

    def __init__(self) -> None:
        super().__init__(componentString='Recoil Compensation')

        self._compensationLevelOption = construction.IntegerOption(
            id='CompensationLevel',
            name='Compensation Level',
            value=1,
            minValue=1,
            maxValue=2,
            description='Specify the level of recoil compensation.')

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._compensationLevelOption.value()})'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Only compatible with conventional weapons
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._compensationLevelOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        instanceString = self.instanceString()

        compensationLevel = common.ScalarCalculation(
            value=self._compensationLevelOption.value(),
            name='Specified Recoil Compensation Level')

        costModifier, weightModifier, damageModifier = \
            RecoilCompensationFeature._CompensationLevelCostWeightDamageModifierMap.get(
                compensationLevel.value(),
                (None, None, None))

        assert(costModifier != None)
        costModifier = common.ScalarCalculation(
            value=costModifier,
            name=f'{instanceString} Receiver Cost Modifier Percentage')

        assert(weightModifier != None)
        weightModifier = common.ScalarCalculation(
            value=weightModifier,
            name=f'{instanceString} Receiver Weight Modifier Percentage')

        assert(damageModifier != None)
        damageModifier = common.ScalarCalculation(
            value=damageModifier,
            name=f'{instanceString} Damage Modifier')

        recoilModifier = common.Calculator.negate(
            value=compensationLevel,
            name=f'{instanceString} Recoil Modifier')

        step.setCredits(credits=construction.PercentageModifier(
            value=costModifier))
        step.setWeight(weight=construction.PercentageModifier(
            value=weightModifier))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Damage,
            modifier=construction.DiceRollModifier(
                constantModifier=damageModifier)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Recoil,
            modifier=construction.ConstantModifier(
                value=recoilModifier)))

        return step

class RuggedFeature(ReceiverFeature):
    """
    - Receiver Cost: +30%
    - Receiver Weight: +10%
    - Note: DM+2 when rolling on Malfunction table
    """
    _MalfunctionNote = 'DM+2 when rolling against the Malfunction table on p8 of the Field Catalogue.'

    def __init__(self) -> None:
        super().__init__(
            componentString='Rugged',
            weightModifierPercentage=+10,
            costModifierPercentage=+30)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=RuggedFeature._MalfunctionNote)
        return step

class ArmouredFeature(ReceiverFeature):
    """
    - Levels: There doesn't seem to be a limit to the number of points of Armoured you can take
    - Receiver Cost: +10% per point of Armoured
    - Receiver Weight: +5% per point of Armoured
    """
    # NOTE: It's not clear what effect armour has on a weapon. There is mention of it in the
    # Breaking Weapon description (Field Catalogue 21-22) but it doesn't say how exactly it affects
    # the maths. I suspect the armour value is added to the Mishap Threshold of the weapon.

    _PerLevelReceiverWeightIncrease = common.ScalarCalculation(
        value=+5,
        name='Armoured Per Level Receiver Weight Increase')
    _PerLevelReceiverCostIncrease = common.ScalarCalculation(
        value=+10,
        name='Armoured Per Level Receiver Cost Increase')

    def __init__(self) -> None:
        super().__init__(componentString='Armoured')

        self._levelCountOption = construction.IntegerOption(
            id='Levels',
            name='Levels',
            value=1,
            minValue=1,
            description='Specify the number of points of armour required.')

    def componentString(self) -> str:
        return 'Armoured'

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._levelCountOption.value()})'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._levelCountOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        levelCount = common.ScalarCalculation(
            value=self._levelCountOption.value(),
            name='Specified Armour Levels')

        weightModifierPercentage = common.Calculator.multiply(
            lhs=self._PerLevelReceiverWeightIncrease,
            rhs=levelCount,
            name=f'Armoured Level {levelCount.value()} Receiver Weight Modifier Percentage')
        step.setWeight(weight=construction.PercentageModifier(value=weightModifierPercentage))

        costModifierPercentage = common.Calculator.multiply(
            lhs=self._PerLevelReceiverCostIncrease,
            rhs=levelCount,
            name=f'Armoured Level {levelCount.value()} Receiver Cost Modifier Percentage')
        step.setCredits(credits=construction.PercentageModifier(value=costModifierPercentage))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Armour,
            value=levelCount))

        return step

class BulwarkedFeature(ReceiverFeature):
    """
    - Levels: There doesn't seem to be a limit to the number of points of Bulwarked you can take
    - Receiver Cost: +20% per point of Bulwarked
    - Receiver Weight: +10% per point of Bulwarked
    - Note: Positive DM modifier equal to the number of levels of Bulwarked when rolling against the Malfunction table
    """

    _PerLevelReceiverWeightIncrease = common.ScalarCalculation(
        value=+10,
        name='Bulwarked Per Level Receiver Weight Increase')
    _PerLevelReceiverCostIncrease = common.ScalarCalculation(
        value=+20,
        name='Bulwarked Per Level Receiver Cost Increase')

    def __init__(self) -> None:
        super().__init__(componentString='Bulwarked')

        self._levelCountOption = construction.IntegerOption(
            id='Levels',
            name='Levels',
            value=1,
            minValue=1,
            description='Specify the number of points of bulwarking.')

    def levelCount(self) -> int:
        return self._levelCountOption.value()

    def componentString(self) -> str:
        return 'Bulwarked'

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._levelCountOption.value()})'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._levelCountOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        levelCount = common.ScalarCalculation(
            value=self._levelCountOption.value(),
            name='Specified Bulwarked Levels')

        weightModifierPercentage = common.Calculator.multiply(
            lhs=self._PerLevelReceiverWeightIncrease,
            rhs=levelCount,
            name=f'Bulwarked Level {levelCount.value()} Receiver Weight Modifier Percentage')
        step.setWeight(weight=construction.PercentageModifier(value=weightModifierPercentage))

        costModifierPercentage = common.Calculator.multiply(
            lhs=self._PerLevelReceiverCostIncrease,
            rhs=levelCount,
            name=f'Bulwarked Level {levelCount.value()} Receiver Cost Modifier Percentage')
        step.setCredits(credits=construction.PercentageModifier(value=costModifierPercentage))

        step.addNote(note=f'DM+{self._levelCountOption.value()} when rolling against the Malfunction table on p8 of the Field Catalogue.')

        return step

class DisguisedFeature(ReceiverFeature):
    """
    - Receiver Cost
        - Level 1: +50%
        - Level 2: +100%
        - Level 3: +150%
        - Level 4: +200%
    - Note: DM-<Level> on attempts to detect, notice or recognise it
    - Requirement: Not compatible with other levels of Disguise
    """
    _DisguisedLevelCostModifierMap = {
        1: +50,
        2: +100,
        3: +150,
        4: +200
    }

    def __init__(self) -> None:
        super().__init__(componentString='Disguised')

        self._disguisedLevelOption = construction.IntegerOption(
            id='DisguisedLevel',
            name='Disguised Level',
            value=1,
            minValue=1,
            maxValue=4,
            description='Specify the level of disguise.')

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._disguisedLevelOption.value()})'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._disguisedLevelOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        disgustedLevel = common.ScalarCalculation(
            value=self._disguisedLevelOption.value(),
            name='Specified Disguised Level')

        costModifier = DisguisedFeature._DisguisedLevelCostModifierMap.get(
            disgustedLevel.value())

        assert(costModifier != None)
        costModifier = common.ScalarCalculation(
            value=costModifier,
            name=f'{self.instanceString()} Receiver Cost Modifier Percentage')

        step.setCredits(credits=construction.PercentageModifier(
            value=costModifier))

        step.addNote(note=f'DM-{disgustedLevel.value()} on attempts to detect, notice or recognise it')

        return step

class StealthFeature(ReceiverFeature):
    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        return not context.hasComponent(
            componentType=StealthFeature,
            sequence=sequence)

class BasicStealthFeature(StealthFeature):
    """
    - Physical Signature: Reduced by 1 level
    - Emissions Signature: Reduced by 1 level
    - Note: DM-2 on attempts to detect it using scanners, observation or a physical search
    - Receiver Cost: +50%
    - Requirement: Not compatible with Extreme Stealth
    """
    _PhysicalSignatureModifier = common.ScalarCalculation(
        value=-1,
        name='Basic Stealth Physical Signature Modifier')
    _EmissionsSignatureModifier = common.ScalarCalculation(
        value=-1,
        name='Basic Stealth Emissions Signature Modifier')
    _Note = 'DM-2 on attempts to detect weapon using scanners, observation or a physical search'

    def __init__(self) -> None:
        super().__init__(
            componentString='Stealth (Basic)',
            costModifierPercentage=+50)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addNote(note=self._Note)

        if not context.hasComponent(
                componentType=gunsmith.ArchaicCalibre,
                sequence=sequence):
            # Only add signature modifier if the weapon has a physical signature
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
                    modifier=construction.ConstantModifier(
                        value=self._PhysicalSignatureModifier)))
            # Only add signature modifier if the weapon has a emissions signature
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.EmissionsSignature):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.EmissionsSignature,
                    modifier=construction.ConstantModifier(
                        value=self._EmissionsSignatureModifier)))

        return step

class ExtremeStealthFeature(StealthFeature):
    """
    - Physical Signature: Reduced by 3 levels (or 2 levels if using standard ammunition)
    - Emissions Signature: Reduced by 3 levels (or 2 levels if using standard ammunition)
    - Receiver Cost: +250%
    - Requirement: Not compatible with Basic Stealth
    - Note: DM-6 on attempts to detect it using scanners, observation or a physical search (DM-4 if using standard ammunition)
    - Note: Extreme Stealth Ammo costs x20 standard ammo
    """
    # NOTE: Handling the Physical/Emissions Signature being 1 level higher when using standard Ammo
    # is handled in the Ammo code

    _PhysicalSignatureModifier = common.ScalarCalculation(
        value=-3,
        name='Extreme Stealth Physical Signature Modifier')
    _EmissionsSignatureModifier = common.ScalarCalculation(
        value=-3,
        name='Extreme Stealth Emissions Signature Modifier')
    _Notes = [
        'DM-6 on attempts to detect weapon using scanners, observation or a physical search (DM-4 if using standard ammunition)',
        'Physical and Emissions Signature are both +1 when using standard ammo'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Stealth (Extreme)',
            costModifierPercentage=+250)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        for note in self._Notes:
            step.addNote(note=note)

        if not context.hasComponent(
                componentType=gunsmith.ArchaicCalibre,
                sequence=sequence):
            # Only add signature modifier if the weapon has a physical signature
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
                    modifier=construction.ConstantModifier(
                        value=self._PhysicalSignatureModifier)))
            # Only add signature modifier if the weapon has a emissions signature
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.EmissionsSignature):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.EmissionsSignature,
                    modifier=construction.ConstantModifier(
                        value=self._EmissionsSignatureModifier)))

        return step

class VacuumFeature(ReceiverFeature):
    """
    - Receiver Cost: +20%
    - Note: Can operate in a vacuum
    - Requirement: Not compatible with Projectors
    """
    # NOTE: I added the requirement about not being compatible with Projectors as I don't think
    # they'd really make sense in a vacuum. Combustible fuel would need air to burn and anyone
    # you're firing at would be wearing a suit that protects them from the other kinds of "fuel"

    _Note = 'Weapon can operate in a vacuum'

    def __init__(self) -> None:
        super().__init__(
            componentString='Vacuum',
            costModifierPercentage=+20)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with projectors
        return not context.hasComponent(
            componentType=gunsmith.ProjectorReceiver,
            sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._Note)
        return step

class UnderwaterFeature(ReceiverFeature):
    """
    - Receiver Cost: +100%
    - Note: Underwater range 1/5th of normal range'
    """
    # NOTE: Underwater is modifier on the other receiver types so it seems more sensible to have it
    # as a receiver feature
    # NOTE: Underwater projectors and directed energy weapons don't seem sensible but nothing in the
    # rules say it's not allowed

    _Note = 'Underwater range 1/5th of normal range'

    def __init__(self) -> None:
        super().__init__(
            componentString='Underwater',
            costModifierPercentage=+100)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._Note)
        return step

class SlowLoaderFeature(ReceiverFeature):
    # NOTE: This feature is a bit of a hack to allow a weapon to be marked as a slow loader based on
    # the type of weapon being designed rather than purely rules based reasons. An example of this is
    # the Jimpy-G (Field Catalogue p110) which has a Slow Loader trait of 4 due to the length of time
    # it takes to change the belt.
    _SlowLoaderOptionDescription = \
        '<p>Specify the Slow Loader modifier to be applied.</p>' \
        '<p>The rules don\'t give much guidance on when weapons should have the Slow Loader ' \
        'trait. This allows you to give the weapon a Slow Loader modifier based on the weapon ' \
        'you\'re designing and how you and your Referee interpret the rules.</p>'

    def __init__(self) -> None:
        super().__init__(componentString='Slow Loader')

        self._slowLoaderOption = construction.IntegerOption(
            id='Score',
            name='Slow Loader Score',
            value=1,
            minValue=1,
            description=SlowLoaderFeature._SlowLoaderOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._slowLoaderOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        slowLoaderModifier = common.ScalarCalculation(
            value=self._slowLoaderOption.value(),
            name='Specified Slow Loader Modifier')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.SlowLoader,
            modifier=construction.ConstantModifier(value=slowLoaderModifier)))

        return step


# ██████████
#░░███░░░░░█
# ░███  █ ░  ████████    ██████  ████████   ███████ █████ ████
# ░██████   ░░███░░███  ███░░███░░███░░███ ███░░███░░███ ░███
# ░███░░█    ░███ ░███ ░███████  ░███ ░░░ ░███ ░███ ░███ ░███
# ░███ ░   █ ░███ ░███ ░███░░░   ░███     ░███ ░███ ░███ ░███
# ██████████ ████ █████░░██████  █████    ░░███████ ░░███████
#░░░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░░      ░░░░░███  ░░░░░███
#                                          ███ ░███  ███ ░███
#                                         ░░██████  ░░██████
#                                          ░░░░░░    ░░░░░░

class EnergyWeaponFeature(ReceiverFeature):
    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Only compatible with energy weapons
        return context.hasComponent(
            componentType=gunsmith.PowerPackReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence)

class EfficientBeamGeneratorFeature(EnergyWeaponFeature):
    """
    - Min TL: 11
    - Receiver Cost: +50%
    - Receiver Weight: -25%
    - Range: +25%
    - Requirement: Only compatible with Energy Weapons
    """
    _RangeModifierPercentage = common.ScalarCalculation(
        value=+25,
        name='Efficient Beam Generator Range Modifier Percentage')

    def __init__(self) -> None:
        super().__init__(
            componentString='Efficient Beam Generator',
            minTechLevel=11,
            costModifierPercentage=+50,
            weightModifierPercentage=-25)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Range,
            modifier=construction.PercentageModifier(
                value=self._RangeModifierPercentage)))

        return step

class ImprovedBeamFocusFeature(EnergyWeaponFeature):
    """
    - Min TL: 11
    - Receiver Cost: +25%
    - Damage: +3 to any energy weapon doing >= 2D damage
    - Requirement: Only compatible with Energy Weapons
    """
    _DamageConstantModifier = common.ScalarCalculation(
        value=+3,
        name='Improved Beam Focus Damage Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Improved Beam Focus',
            minTechLevel=11,
            costModifierPercentage=+25)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction order should enforce this

        if damageRoll.dieCount().value() >= 2:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    constantModifier=self._DamageConstantModifier)))

        return step

class IntensifiedPulseFeature(EnergyWeaponFeature):
    """
    - Min TL: 12
    - Receiver Cost: +25%
    - Receiver Weight: +10%
    - Penetration: +1
    - Requirement: Only compatible with Energy Weapons
    """
    _PenetrationModifier = common.ScalarCalculation(
        value=+1,
        name='Intensified Pulse Penetration Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Intensified Pulse',
            minTechLevel=12,
            costModifierPercentage=+25,
            weightModifierPercentage=+10)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Penetration,
            modifier=construction.ConstantModifier(
                value=self._PenetrationModifier)))

        return step

class VariableIntensityFeature(EnergyWeaponFeature):
    """
    - Min TL: 10
    - Receiver Cost: +15%
    - Receiver Weight: +10%
    - Damage: Can be set to anything up to the weapon max
    - Note: Powerpack weapons draw only enough power for the shot, but cartridges are fully expended even on a low power setting
    - Requirement: Only compatible with Energy Weapons
    """
    # NOTE: Ideally this would probably take the damage the user wants to set it to as an argument so it
    # could calculate the actual damage of the weapon at that point in time. However if I do that it
    # introduces an ordering dependency on ImprovedBeamFocusFeature as the +3 damage modifier it applies
    # is dependant on the number of damage dice. Instead I'm handling it as a note that is generated when
    # applying the component and gives the range the user can set it to.
    _PowerPackNote = 'Powerpack weapons draw only enough power for the shot'
    _CartridgeNote = 'Cartridges are fully expended even on a low power setting'

    def __init__(self) -> None:
        super().__init__(
            componentString='Variable Intensity',
            minTechLevel=10,
            costModifierPercentage=+25,
            weightModifierPercentage=+10)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        maxDamageDice = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.MaxDamageDice)
        assert(maxDamageDice) # Construction order should enforce this
        step.addNote(note=f'Damage can be set to value between 1D and {maxDamageDice.value()}D')

        typeNote = None
        if context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence):
            typeNote = self._PowerPackNote
        elif context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence):
            typeNote = self._CartridgeNote
        assert(typeNote) # CCompatibility check should enforce this
        step.addNote(note=typeNote)

        return step

class InternalPowerPackFeature(EnergyWeaponFeature):
    # NOTE: This feature is a hack added to make handling of internal power packs easier. The
    # weight of the power pack is specified as an option but not actually applied to the weapon
    # as that would affect the receiver weight calculation and the rules don't suggest it should.

    def __init__(self) -> None:
        super().__init__(componentString='Internal Power Pack')

        self._weightOption = construction.FloatOption(
            id='Weight',
            name='Weight',
            value=1,
            minValue=0.001, # Power density at higher TLs mean even very small power packs hold a decent number of shots
            description='Specify the weight of the internal power pack that can be inserted.')

    def packWeight(self) -> float:
        return self._weightOption.value()

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._weightOption.value()}kg)'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._weightOption]
        options.extend(super().options())
        return options


# █████   ███   █████
#░░███   ░███  ░░███
# ░███   ░███   ░███   ██████   ██████   ████████   ██████  ████████
# ░███   ░███   ░███  ███░░███ ░░░░░███ ░░███░░███ ███░░███░░███░░███
# ░░███  █████  ███  ░███████   ███████  ░███ ░███░███ ░███ ░███ ░███
#  ░░░█████░█████░   ░███░░░   ███░░███  ░███ ░███░███ ░███ ░███ ░███
#    ░░███ ░░███     ░░██████ ░░████████ ░███████ ░░██████  ████ █████
#     ░░░   ░░░       ░░░░░░   ░░░░░░░░  ░███░░░   ░░░░░░  ░░░░ ░░░░░
#                                        ░███
#                                        █████
#                                       ░░░░░

class WeaponFeature(gunsmith.WeaponComponentInterface):
    """
    - Requirement: Only compatible with primary weapon
    """
    # NOTE: Weapon features are features that are applied to the weapon as a whole. As such they are
    # only compatible with the primary weapon

    def __init__(
            self,
            componentString: str,
            minTechLevel: typing.Optional[int] = None
            ) -> None:
        super().__init__()

        self._componentString = componentString
        self._minTechLevel = minTechLevel

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Weapon Features'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if self._minTechLevel != None:
            if context.techLevel() < self._minTechLevel:
                return False

        # Only compatible with weapons that have a receiver. A whole weapon search is used as
        # it can be any of the weapon sequences.
        if not context.hasComponent(
                componentType=gunsmith.Receiver,
                sequence=None):
            return False

        # Don't allow multiple weapon features of the same type
        return not context.hasComponent(
            componentType=type(self),
            sequence=None) # Whole weapon search

class IntelligentWeaponFeature(WeaponFeature):
    """
    - Requirement: Not compatible with other intelligent weapon accessories
    """
    # NOTE: I've moved intelligent weapon from an accessory to a weapon feature as it's applied to
    # the weapon as a whole rather than being a primary/secondary thing. For this to work it needs
    # to be applied before the secondary weapon as it can affect what ammo types are compatible with
    # it
    # NOTE: There doesn't seem to be any direct benefit to adding Intelligent Weapon to anything
    # other than Conventional Weapons as only the get Smart ammo. However there could be some other
    # in game benefits so I'm not making it incompatible

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            fixedCost: typing.Union[int, common.ScalarCalculation],
            computerNote: str
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel)

        if not isinstance(fixedCost, common.ScalarCalculation):
            fixedCost = common.ScalarCalculation(
                value=fixedCost,
                name=f'{componentString} Cost')

        self._fixedCost = fixedCost
        self._computerNote = computerNote

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with other intelligent weapon accessories
        return not context.hasComponent(
            componentType=gunsmith.IntelligentWeaponFeature,
            sequence=None) # Whole weapon search

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=construction.ConstantModifier(self._fixedCost),
            notes=[self._computerNote])
        context.applyStep(
            sequence=sequence,
            step=step)

class LowIntelligentWeaponFeature(IntelligentWeaponFeature):
    """
    - Min TL: 11
    - Cost: Cr1000
    - Note: Computer/0
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Intelligent Weapon (TL 11-12)',
            minTechLevel=11,
            fixedCost=1000,
            computerNote='Computer/0')

class HighIntelligentWeaponFeature(IntelligentWeaponFeature):
    """
    - Min TL: 13
    - Cost: Cr5000
    - Note: Computer/1
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Intelligent Weapon (TL 13+)',
            minTechLevel=13,
            fixedCost=5000,
            computerNote='Computer/1')

class ModularisationWeaponFeature(WeaponFeature):
    """
    - Cost: 20% of Receiver Cost
    - Weight: 10% of Receiver Weight
    """
    # NOTE: The description in the Field Catalogue (p43) says modularisation adds x% to the weapon
    # weight and cost. However looking at the example weapons (e.g p96) it's a percentage of the
    # receiver weight/cost

    _ReceiverWeightPercentage = common.ScalarCalculation(
        value=10,
        name='Modularisation Receiver Weight Percentage')
    _ReceiverCostPercentage = common.ScalarCalculation(
        value=20,
        name='Modularisation Receiver Cost Percentage')

    def __init__(self) -> None:
        super().__init__(componentString='Modularisation')

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=construction.ConstantModifier(
                value=common.Calculator.takePercentage(
                    value=context.receiverCredits(sequence=None), # Use cost of all receivers
                    percentage=self._ReceiverCostPercentage,
                    name=f'Modularisation Cost')),
            weight=construction.ConstantModifier(
                value=common.Calculator.takePercentage(
                    value=context.receiverWeight(sequence=None), # Use weight of all receivers
                    percentage=self._ReceiverWeightPercentage,
                    name=f'Modularisation Weight')))

        context.applyStep(
            sequence=sequence,
            step=step)

class SecureWeaponFeature(WeaponFeature):
    """
    - Min TL: 10
    - Cost: Cr100
    """
    # NOTE: I've made this a weapon feature rather than an accessory as it seems like something
    # that would be applied to the weapon as a whole (i.e. including secondary weapon). For it
    # to provide any real security it also seems like it would need to be more integrated into the
    # weapon rather than an aftermarket bolt-on (at least for non-energy weapons).

    _MinTechLevel = 10
    _FixedCost = common.ScalarCalculation(
        value=100,
        name='Secure Weapon Cost')

    def __init__(self) -> None:
        super().__init__(
            componentString='Secure Weapon',
            minTechLevel=self._MinTechLevel)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=construction.ConstantModifier(value=self._FixedCost))
        context.applyStep(
            sequence=sequence,
            step=step)

class StabilisationWeaponFeature(WeaponFeature):
    """
    - Min TL: 9
    - Cost: Cr300
    - Weight: 20% of Receiver Weight
    - Note: Offsets an aiming DM caused by movement or a poorly balanced weapon by up to -2
    - Note: If a weapon is Bulky or Very Bulky due to recoil (not actual weight or bulk), a gyrostabiliser reduces Very Bulky to Bulky and eliminates the Bulky trait entirely
    """
    # NOTE: I've added the requirement that this is only compatible with the primary weapon. As it
    # only really makes sense for it to be something applied to the weapon as a whole. This does
    # make the weight calculation slightly odd as it's based on the receiver weight of the primary
    # weapon only.
    # NOTE: I've been through all the components that give the Bulky or Very Bulky trait and in the
    # majority of cases it's clear that they are being given due to recoil so stabilisation would
    # have an affect.
    # One exception is RF/VRF (Field Catalogs p32) where it's not explicitly stated but seems most
    # likely its due to weight.
    # The other exception is launchers (Field Catalogue p58) where it's just not clear at all why
    # they are given the traits. The fact that the example on p118 weighs only 0.75kg but still has
    # the Bulky trait would suggest it's not due to weight so must be due to recoil.
    # To handle the cases where it's unclear I've added options to allow the user to choose.
    # NOTE: It's not obvious if this should be detachable or not. As I don't know it's better to
    # allow it

    _MinTechLevel = 9
    _FixedCost = common.ScalarCalculation(
        value=300,
        name='Stabilisation Cost')
    _ReceiverWeightPercentage = common.ScalarCalculation(
        value=20,
        name='Stabilisation Receiver Weight Percentage')
    _AimingModifierNote = 'Offsets an aiming DM caused by movement or a poorly balanced weapon by up to -2'

    _AffectsFireRateBulkLevelOptionDescription = \
        '<p>Specify if the stabilisation accessory affects Bulky and Very Bulky traits gained ' \
        'due to the weapon having RF or VRF fire rates or a powered or VRF feed.</p>' \
        '<p>The rules regarding RF/VRF capability on p32 of the Field Catalog don\'t make it ' \
        'clear if they give the Bulky/Very Bulky trait due to their weight or the recoil from ' \
        'such a rapid rate of fire. The wording in the rules would suggest it\'s due to weight, ' \
        'in which case stabilisation would have no effect, however it\'s not explicit. This ' \
        'option allows you to choose the behaviour based on how you and your Referee interpret ' \
        'the rules.</p>'
    _RemovesFireRateBulkLevelOptionDescription = \
        '<p>Specify if the stabilisation accessory affects Bulky and Very Bulky traits launcher ' \
        'weapons receive.</p>' \
        '<p>The rules covering launchers on p58 of the Field Catalog don\'t make it clear if' \
        'they\'re given the Bulky/Very Bulky trait due to their weight or recoil. The fact that ' \
        'the example on p118 has the Bulky trait and only weighs 0.75kg would suggest that it\'s ' \
        'not due to weight so must be due to recoil, in which case stabilisation would have an ' \
        'affect. It could be argued that the example is Bulky due to size, however the description ' \
        'of the Bulky trait on p75 of the Core Rules only says it can be gained due to weight or ' \
        'recoil, but doesn\'t mention size. This option allows you to choose the behaviour based ' \
        'on how you and your Referee interpret the rules.</p>'

    def __init__(self) -> None:
        super().__init__(
            componentString='Stabilisation',
            minTechLevel=self._MinTechLevel)

        self._affectsFireRateBulkLevelOption = construction.BooleanOption(
            id='AffectsFireRateBulkLevel',
            name='Affects Bulky & Very Bulky Traits For RF & VRF Weapons',
            value=False, # My reading of the rules is that it's due to weight so wouldn't be applied
            description=StabilisationWeaponFeature._AffectsFireRateBulkLevelOptionDescription)

        self._affectsLauncherBulkLevelOption = construction.BooleanOption(
            id='AffectsFireRateBulkLevel',
            name='Affects Bulky & Very Bulky Traits For Grenade Launchers',
            value=True, # My reading of the rules is that it's not due to weight so would be applied
            description=StabilisationWeaponFeature._RemovesFireRateBulkLevelOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()

        if self._affectsFireRateBulkLevelOption.isEnabled():
            options.append(self._affectsFireRateBulkLevelOption)

        if self._affectsLauncherBulkLevelOption.isEnabled():
            options.append(self._affectsLauncherBulkLevelOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)
        self._affectsFireRateBulkLevelOption.setEnabled(
            self._hasFireRateBulkModifier(
                context=context,
                sequence=None)) # Check entire weapon when enabling the option
        self._affectsLauncherBulkLevelOption.setEnabled(
            self._isLauncherWeapon(
                context=context,
                sequence=None)) # Check entire weapon when enabling the option

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=construction.ConstantModifier(value=self._FixedCost))

        step.setWeight(weight=construction.ConstantModifier(
            value=common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=None), # Use weight of all receivers
                percentage=self._ReceiverWeightPercentage,
                name=f'Stabilisation Weight')))

        modifyBulkLevel = True
        if self._hasFireRateBulkModifier(
                context=context,
                sequence=sequence): # Only check weapon sequence when checking if modifier should be applied
            modifyBulkLevel = self._affectsFireRateBulkLevelOption.value()
        if self._isLauncherWeapon(
                context=context,
                sequence=sequence): # Only check weapon sequence when checking if modifier should be applied
            modifyBulkLevel = self._affectsLauncherBulkLevelOption.value()

        if modifyBulkLevel:
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.VeryBulky):
                step.addFactor(factor=construction.DeleteAttributeFactor(attributeId=gunsmith.WeaponAttributeId.VeryBulky))
                step.addFactor(factor=construction.SetAttributeFactor(attributeId=gunsmith.WeaponAttributeId.Bulky))
            elif context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.Bulky):
                step.addFactor(factor=construction.DeleteAttributeFactor(attributeId=gunsmith.WeaponAttributeId.Bulky))

        step.addNote(note=StabilisationWeaponFeature._AimingModifierNote)

        context.applyStep(
            sequence=sequence,
            step=step)

    def _hasFireRateBulkModifier(
            self,
            context: gunsmith.WeaponContext,
            sequence: str
            ) -> bool:
        if context.hasComponent(
                componentType=gunsmith.AdvancedFireRate,
                sequence=sequence):
            return True

        feed = context.findFirstComponent(
            componentType=gunsmith.Feed,
            sequence=sequence)
        if not feed:
            return False
        assert(isinstance(feed, gunsmith.Feed))
        return feed.feedAssist() != None

    def _isLauncherWeapon(
            self,
            context: gunsmith.WeaponContext,
            sequence: str
            ) -> bool:
        return context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence)
