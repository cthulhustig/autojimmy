import common
import construction
import enum
import gunsmith
import typing

class FeedAssist(enum.Enum):
    Powered = 'Powered'
    VRF = 'VRF'

class Feed(gunsmith.FeedInterface):
    """
    - Powered Feed Assist
        - Receiver Cost: x3
        - Receiver Weight: x3
        - Requirement: Only feasible with Longarm, Light Support & Support receivers (Field Catalogue p32)
        - Requirement: Only compatible with Conventional Firearm
    - VRF Assist
        - Receiver Cost: x5
        - Receiver Weight x5
        - Trait: Very Bulky
        - Requirement: Only feasible with Longarm, Light Support & Support receivers
        - Requirement: Only compatible with Conventional Firearm
    - Energy Cartridges
        - Min TL: 9 (Based on point energy cartridges become available)
        - Trait: Hazardous -2 if non-ejecting (Field Catalogue p63)
    """
    # NOTE: The RF description is HORRIBLY ambiguous (Field Catalogue p32). I've assumed the x3
    # multiplier when using a powered/forced Feed is in addition to the base receiver weight/cost
    # increases. This seems logical, having it _instead_ of the base receiver weight/cost would
    # mean the auto score would only affect cost when not using a powered/forced feed which would
    # be odd.
    # NOTE: I've added the requirement that a VRF feed is only compatible with longarm receivers
    # and larger. It would seem odd if a powered feed had the requirement but a VRF feed didn't
    # NOTE: I've added the requirement that feed assist is only compatible with conventional
    # firearms.
    # The fact it says it's compatible with support receivers could mean it would be compatible with
    # support launchers, however I've made RF/VRF incompatible with launchers as there seems no point
    # as the Penetration and Damage bonuses they give wouldn't really apply to launchers (as how the
    # fast weapon fires wouldn't affect the damage or penetration of the payload)
    # You would have thought that feed assists could be used with cartridge energy weapons but it's
    # not obvious how longarm/light support/support would map onto the minimal/small/medium/large
    # energy weapon receivers.
    # NOTE: I've added an option to allow the user to specify if powered feeds give the weapon the
    # Bulky or Very Bulky trait. The VRF rules (Field Catalogue p32) specifically say that a VRF
    # feed gives the Very Bulky trait but the RF rules don't say the same thing about the powered
    # feed. They do say that the RF capability gives the Bulky trait but not specially when using
    # powered feed. This distinction is important because i'm treating the feed assist separately from
    # the rest of the RF/VRF implementation to work around other rule ambiguities.

    _PoweredAssistWeightMultiplier = common.ScalarCalculation(
        value=3,
        name='Powered Feed Receiver Weight Multiplier')
    _PoweredAssistCostMultiplier = common.ScalarCalculation(
        value=3,
        name='Powered Feed Receiver Cost Multiplier')
    _VRFAssistWeightMultiplier = common.ScalarCalculation(
        value=5,
        name='VRF Feed Receiver Weight Multiplier')
    _VRFAssistCostMultiplier = common.ScalarCalculation(
        value=5,
        name='VRF Feed Receiver Cost Multiplier')
    _NonEjectingEnergyCartridgeHazardousModifier = common.ScalarCalculation(
        value=-2,
        name='Non-Ejecting Cartridge Feed Hazardous Modifier')

    _FeedAssistTypeOptionDescription = \
        '<p>Specify if weapon has a feed assist and if so what type.</p>' \
        '<p>The rules regarding RF/VRF and powered/forced feeds on p32 of the Field Catalog ' \
        'are a bit unclear. It\'s not obvious if a non-multimount weapon must have some kind ' \
        'of feed assist to achieve RF/VRF or if that\'s just if a weapon is being "converted".' \
        'This allows you to choose if the weapon has a powered/forced feed based on what you ' \
        'want for your weapon and the interpretation of the rules you agree with your Referee. ' \
        'For maximum flexibility, a powered/forced feed is not a requirement to achieve RF/VRF ' \
        'in this implementation of the rules.</p>'
    _PoweredFeedAssistBulkLevelOptionDescription = \
        '<p>Specify if the powered feed gives the weapon the Bulky/Very Bulky Trait.</p>' \
        '<p>The rules regarding RF/VRF and powered/forced feeds on p32 of the Field Catalog ' \
        'are a bit unclear. They say that the RF capability gives the weapon the Bulky trait, ' \
        'however not specifically because it\'s using a powered feed. Conversely the description ' \
        'for VRF doesn\'t say the basic VRF capability gives a Bulky/Very Bulky trait, but it ' \
        'does say a VRF feed gives the Very Bulky trait. This allows you to specify a value based ' \
        'on how you and your Referee interpret the rules.</p>'
    _CartridgeEjectDescription = 'Specify if spent energy cartridges are automatically ' \
        'ejected after being fired or if they must be removed manually before reloading.'

    def __init__(
            self,
            componentString: str,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__()

        if weightModifierPercentage != None and not isinstance(weightModifierPercentage, common.ScalarCalculation):
            weightModifierPercentage = common.ScalarCalculation(
                value=weightModifierPercentage,
                name=f'{componentString} Feed Receiver Weight Modifier Percentage')

        if costModifierPercentage != None and not isinstance(costModifierPercentage, common.ScalarCalculation):
            costModifierPercentage = common.ScalarCalculation(
                value=costModifierPercentage,
                name=f'{componentString} Feed Receiver Cost Modifier Percentage')

        self._componentString = componentString
        self._weightModifierPercentage = weightModifierPercentage
        self._costModifierPercentage = costModifierPercentage

        self._feedAssistOption = construction.EnumComponentOption(
            id='FeedAssist',
            name='Feed Assist',
            type=FeedAssist,
            value=None,
            isOptional=True,
            description=Feed._FeedAssistTypeOptionDescription,
            enabled=False) # Optional, enabled if supported in updateOptions

        self._poweredFeedBulkLevelOption = construction.EnumComponentOption(
            id='PoweredFeedBulkLevel',
            name='Bulky/Very Bulky Trait',
            type=gunsmith.WeaponAttribute,
            value=None,
            isOptional=True,
            options=[gunsmith.WeaponAttribute.Bulky, gunsmith.WeaponAttribute.VeryBulky],
            description=Feed._PoweredFeedAssistBulkLevelOptionDescription,
            enabled=False) # Optional, enabled if supported in updateOptions

        self._cartridgeEjectOption = construction.BooleanComponentOption(
            id='CartridgeEject',
            name='Ejecting',
            value=True,
            description=self._CartridgeEjectDescription,
            enabled=False) # Optional, enabled if supported in updateOptions

    def feedAssist(self) -> FeedAssist:
        return self._feedAssistOption.value()

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Feed'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Only compatible with weapons that have a conventional, launcher or energy
        # cartridge receiver
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = []

        if self._feedAssistOption.isEnabled():
            options.append(self._feedAssistOption)
            if self._poweredFeedBulkLevelOption.isEnabled() and \
                    self._feedAssistOption.value() == FeedAssist.Powered:
                options.append(self._poweredFeedBulkLevelOption)

        if self._cartridgeEjectOption.isEnabled():
            options.append(self._cartridgeEjectOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        isFeedAssistCompatible = self._isFeedAssistCompatible(
            sequence=sequence,
            context=context)
        self._feedAssistOption.setEnabled(isFeedAssistCompatible)
        self._poweredFeedBulkLevelOption.setEnabled(isFeedAssistCompatible)

        isEnergyCartridgeWeapon = self._isEnergyCartridgeWeapon(
            sequence=sequence,
            context=context)
        self._cartridgeEjectOption.setEnabled(isEnergyCartridgeWeapon)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        #
        # Base Step
        #

        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

        #
        # Feed Assist Step
        #

        if self._isFeedAssistCompatible(sequence=sequence, context=context):
            step = None
            if self._feedAssistOption.value() == FeedAssist.Powered:
                bulkLevel = self._poweredFeedBulkLevelOption.value()
                factors = None
                if bulkLevel != None:
                    factors = [construction.SetAttributeFactor(attributeId=bulkLevel)]

                step = gunsmith.WeaponStep(
                    name=f'Powered Feed Assist',
                    type=self.typeString(),
                    credits=construction.MultiplierModifier(value=self._PoweredAssistCostMultiplier),
                    weight=construction.MultiplierModifier(value=self._PoweredAssistWeightMultiplier),
                    factors=factors)
            if self._feedAssistOption.value() == FeedAssist.VRF:
                step = gunsmith.WeaponStep(
                    name=f'VRF Feed Assist',
                    type=self.typeString(),
                    credits=construction.MultiplierModifier(value=self._VRFAssistCostMultiplier),
                    weight=construction.MultiplierModifier(value=self._VRFAssistWeightMultiplier),
                    factors=[construction.SetAttributeFactor(
                        attributeId=gunsmith.WeaponAttribute.VeryBulky)])

            if step:
                context.applyStep(
                    sequence=sequence,
                    step=step)

        #
        # Non-ejecting Cartridge Step
        #

        if self._isEnergyCartridgeWeapon(sequence=sequence, context=context) \
                and not self._cartridgeEjectOption.value():
            step = gunsmith.WeaponStep(
                name=f'Non-Ejecting Energy Cartridges',
                type=self.typeString())
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.Hazardous,
                modifier=construction.ConstantModifier(
                    value=self._NonEjectingEnergyCartridgeHazardousModifier)))
            context.applyStep(
                sequence=sequence,
                step=step)

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

    def _isFeedAssistCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Feed Assist is only compatible with Conventional Weapons
        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence feed is part of
        if not receiver:
            return False
        return isinstance(receiver, gunsmith.LongarmReceiver) or \
            isinstance(receiver, gunsmith.LightSupportReceiver) or \
            isinstance(receiver, gunsmith.HeavyWeaponReceiver)

    def _isEnergyCartridgeWeapon(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return context.hasComponent(
            componentType=gunsmith.EnergyCartridgeReceiver,
            sequence=sequence)

class RemovableMagazineFeed(Feed):
    """
    - Requirement: Large-calibre handguns cannot use any form of detachable magazine (Field Catalogue p36)
    - Requirement: Not compatible with single shot grenade launchers
    """
    # NOTE: The requirement about Large-calibre handguns is in the shotgun/smoothbore section so
    # I'm treating it as specific to that type of weapon. Text elsewhere in the same description
    # (Field Catalogue p37) suggests all smoothbore ammo is classes as large-calibre. The end
    # effect is removable magazines are incompatible with handguns using any smoothbore ammo

    def __init__(self) -> None:
        super().__init__(componentString='Removable Magazine')

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with smoothbore handguns
        isSmoothboreHandgun = context.hasComponent(
            componentType=gunsmith.HandgunReceiver,
            sequence=sequence) \
            and context.hasComponent(
                componentType=gunsmith.SmoothboreCalibre,
                sequence=sequence)
        if isSmoothboreHandgun:
            return False

        # Not compatible with single shot grenade launchers
        return not context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence)

class FixedMagazineFeed(Feed):
    """
    - Receiver Weight: -10% (Field Catalogue p45)
    - Receiver Cost: -10% (Field Catalogue p45)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Fixed Magazine',
            weightModifierPercentage=-10,
            costModifierPercentage=-10)

class FixedDrumMagazineFeed(Feed):
    """
    - Receiver Cost: +5%
    - Ammo Capacity: Up to x2.5
    - Trait: Inaccurate (-1)
    - Trait: Hazardous (-1)
    - Requirement: Not compatible with single shot grenade launchers
    """
    # NOTE: Detachable drums are handled in Accessories as in theory you can get them for any
    # detachable magazine weapon

    _InaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Fixed Drum Magazine Feed Inaccurate Modifier')
    _HazardousModifier = common.ScalarCalculation(
        value=-1,
        name='Fixed Drum Magazine Feed Hazardous Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString=f'Fixed Drum Magazine',
            costModifierPercentage=+5)

        self._capacityIncreaseOption = construction.FloatComponentOption(
            id='CapacityIncrease',
            name='Capacity Increase (%)',
            value=150,
            minValue=0,
            maxValue=150,
            description='Specify the percentage increase in ammunition capacity given by the fixed drum magazine.')

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with single shot grenade launchers
        return not context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityIncreaseOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Ammo Capacity Increase Percentage')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=capacityIncrease,
                roundDown=True)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._InaccurateModifier)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Hazardous,
            modifier=construction.ConstantModifier(
                value=self._HazardousModifier)))

        return step
