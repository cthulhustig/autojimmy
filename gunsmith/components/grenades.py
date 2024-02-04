import common
import construction
import enum
import gunsmith
import typing

class _GrenadeImpl(object):
    """
    - All Cartridge Grenades (Field Catalogue p53)
        - Damage: A grenade that hits without detonating will do 2D damage (Field Catalogue p53)
            - Could use this a the base damage for a launcher
        - Cost: x2.5 the payload price plus any additional features
        - Weight: Same as a hand thrown grenade
        - Base Range: 200m
        - Requirement: Only compatible with Launcher Weapon
    - Rocket Assisted Multipurpose (RAM) Cartridge Grenades (Field Catalogue p53)
        - Min TL: 8
        - Damage: A grenade that hits without detonating will do 2D damage (Field Catalogue p53)
            - Could use this a the base damage for a launcher
        - Cost: x3 the payload price plus any additional features
        - Weight: Same as a hand thrown grenade
        - Base Range: 300m
        - Requirement: Only compatible with launchers
    - Advanced Fusing
        - Min TL: 9
        - Cost: +25%
    """
    # NOTE: The Range of launcher grenades is incredibly confusing. The Tube Launcher Receivers
    # (Field Catalogue p58) have a base range of 200m for Light Receivers and 300m for Standard
    # Receivers. However the Cartridge Grenade and RAM Grenade descriptions (Field Catalogue p53) give
    # the base range for Cartridge Grenades as 200m and RAM Grenades as 300m. Looking at the example
    # Light Launcher (Field Catalogue p120) and Standard Launcher (Field Catalogue p121) it looks like RAM
    # Grenades can only be used by Standard Launchers. From looking at the ordinance table for the
    # Standard Launcher (Field Catalogue p122), I __think__ how it works is Light Launchers have a base
    # range of 200m, the Standard Launcher has a range of 200m for Standard Grenades and 300m for
    # RAM Grenades. When it comes to how to actually handle this I think it's effectively setting
    # the weapon Range to the min of the range the barrel will allow and the range of the grenade.
    # NOTE: The wording around Advanced Fusing is a little ambiguous. It says it adds 25% to
    # the cost of the weapon. However, at that point it's talking about hand thrown grenades,
    # so I'm taking it to mean it adds 25% to the cost of the grenade

    _StandardCartridgeCostMultiplier = common.ScalarCalculation(
        value=2.5,
        name='Cartridge Grenade Payload Cost Multiplier')
    _StandardCartridgeBaseRange = common.ScalarCalculation(
        value=200,
        name='Cartridge Grenade Base Range')

    _RAMCartridgeMinTechLevel = common.ScalarCalculation(
        value=8,
        name='RAM Cartridge Grenade Minimum TL')
    _RAMCartridgeCostMultiplier = common.ScalarCalculation(
        value=3,
        name='RAM Cartridge Grenade Cost Multiplier')
    _RAMCartridgeBaseRange = common.ScalarCalculation(
        value=300,
        name='RAM Cartridge Grenade Base Range')

    _CartridgeGrenadeImpactDamageDice = common.ScalarCalculation(
        value=2,
        name='Cartridge Grenade Impact Damage')

    _AdvancedFusingMinTechLevel = common.ScalarCalculation(
        value=9,
        name='Advanced Fusing Minimum TL')
    _AdvancedFusingCostModifierPercentage = common.ScalarCalculation(
        value=+25,
        name='Advanced Fusing Cost Modifier Percentage')

    def __init__(
            self,
            componentString: str,
            minTechLevel: typing.Union[int, common.ScalarCalculation],
            isLauncherGrenade: bool,
            payloadWeight: typing.Union[int, float, common.ScalarCalculation],
            payloadCost: typing.Union[int, float, common.ScalarCalculation],
            damageDice: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            flagTraits: typing.Optional[typing.Iterable[gunsmith.WeaponAttribute]] = None,
            numericTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, typing.Union[int, common.ScalarCalculation]]] = None,
            enumTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, enum.Enum]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        if not isinstance(minTechLevel, common.ScalarCalculation):
            minTechLevel = common.ScalarCalculation(
                value=minTechLevel,
                name=f'{componentString} Cartridge Grenade Minimum Tech Level')

        if not isinstance(payloadWeight, common.ScalarCalculation):
            payloadWeight = common.ScalarCalculation(
                value=payloadWeight,
                name=f'{componentString} Payload Weight')

        if not isinstance(payloadCost, common.ScalarCalculation):
            payloadCost = common.ScalarCalculation(
                value=payloadCost,
                name=f'{componentString} Payload Cost')

        if damageDice != None and not isinstance(damageDice, common.ScalarCalculation):
            damageDice = common.ScalarCalculation(
                value=damageDice,
                name=f'{componentString} Cartridge Grenade Damage Dice')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._isLauncherGrenade = isLauncherGrenade
        self._payloadWeight = payloadWeight
        self._payloadCost = payloadCost
        self._damageDice = damageDice
        self._flagTraits = flagTraits if flagTraits else [] # Create empty list to make things easier for consumer
        self._enumTraits = enumTraits if enumTraits else {}
        self._notes = notes if notes else []

        self._numericTraits = {}
        if numericTraits:
            for trait, value in numericTraits.items():
                if not isinstance(value, common.ScalarCalculation):
                    value = common.ScalarCalculation(
                        value=value,
                        name=f'{componentString} Cartridge Grenade {trait.value} Modifier')
                self._numericTraits[trait] = value

        self._isAdvancedFusingOption = construction.BooleanComponentOption(
            id='AdvancedFusing',
            name='Advanced Fusing',
            value=isAdvancedFusing if isAdvancedFusing != None else False,
            description='Specify if the cartridge grenade has advanced fusing.',
            enabled=False) # Optional, enabled if supported in updateOptions

        self._isRAMOption = construction.BooleanComponentOption(
            id='RAM',
            name='RAM',
            value=isRAM if isRAM != None else False,
            description='Specify if the cartridge grenade is a RAM grenade.',
            enabled=False) # Optional, enabled if supported in updateOptions

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        modifiers = ''
        if self._isAdvancedFusingOption.isEnabled() and self._isAdvancedFusingOption.value():
            modifiers += 'Advanced Fusing'
        if self._isRAMOption.isEnabled() and self._isRAMOption.value():
            if modifiers:
                modifiers += ', '
            modifiers += 'RAM'
        instanceString = self.componentString()
        if modifiers:
            instanceString += f' ({modifiers})'
        return instanceString

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel.value():
            return False

        # Throwing grenades have no further requirements
        if not self._isLauncherGrenade:
            return True

        return context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = []

        if self._isAdvancedFusingOption.isEnabled():
            options.append(self._isAdvancedFusingOption)

        if self._isRAMOption.isEnabled():
            options.append(self._isRAMOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._isAdvancedFusingOption.setEnabled(self._isAdvancedFusingCompatible(
            sequence=sequence,
            context=context))
        self._isRAMOption.setEnabled(self._isRAMCompatible(
            sequence=sequence,
            context=context))

    def isRAM(self) -> bool:
        return self._isRAMOption.value()

    def isAdvancedFusing(self) -> bool:
        return self._isAdvancedFusingOption.value()

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfGrenades: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        isAdvancedFusing = self._isAdvancedFusingCompatible(sequence=sequence, context=context) \
            and self._isAdvancedFusingOption.value()
        isRAM = self._isRAMCompatible(sequence=sequence, context=context) \
            and self._isRAMOption.value()

        cost = self._payloadCost
        if isAdvancedFusing:
            cost = common.Calculator.applyPercentage(
                value=cost,
                percentage=self._AdvancedFusingCostModifierPercentage,
                name=f'Advanced Fusing {cost.name()}')

        if isRAM:
            cost = common.Calculator.multiply(
                lhs=cost,
                rhs=self._RAMCartridgeCostMultiplier,
                name=f'RAM {cost.name()} Cartridge Grenade Cost')

        totalCost = common.Calculator.multiply(
            lhs=cost,
            rhs=numberOfGrenades,
            name='Total Cartridge Grenade Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        cartridgeWeight = common.Calculator.equals(
            value=self._payloadWeight,
            name=f'{self.componentString()} Cartridge Grenade Weight')
        totalWeight = common.Calculator.multiply(
            lhs=cartridgeWeight,
            rhs=numberOfGrenades,
            name='Total Cartridge Grenade Weight')
        step.setWeight(weight=construction.ConstantModifier(value=totalWeight))

        factors = []

        if self._damageDice:
            # This sets the damage rather than modifying it as launchers only get their
            # damage from the grenade payload. Note that this ignores the damage that
            # is done by the physical projectile if it doesn't detonate
            factors.append(construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.Damage,
                value=common.DiceRoll(
                    count=self._damageDice,
                    type=common.DieType.D6)))

        for trait in self._flagTraits:
            factors.append(construction.SetAttributeFactor(attributeId=trait))

        for trait, value in self._enumTraits.items():
            factors.append(construction.SetAttributeFactor(
                attributeId=trait,
                value=value))

        for trait, value in self._numericTraits.items():
            factors.append(construction.ModifyAttributeFactor(
                attributeId=trait,
                modifier=construction.ConstantModifier(value=value)))

        if self._isLauncherGrenade:
            # Limit weapon range by the grenade range
            weaponRange = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttribute.Range)
            assert(isinstance(weaponRange, common.ScalarCalculation)) # Construction logic should enforce this

            if isRAM:
                weaponRange = common.Calculator.min(
                    lhs=weaponRange,
                    rhs=self._RAMCartridgeBaseRange,
                    name=f'Range With RAM {self.componentString()} Cartridge Grenade')
            else:
                weaponRange = common.Calculator.min(
                    lhs=weaponRange,
                    rhs=self._StandardCartridgeBaseRange,
                    name=f'Range With {self.componentString()} Cartridge Grenade')
            factors.append(construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.Range,
                value=weaponRange))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            for note in self._notes:
                step.addNote(note=note)

    def _isAdvancedFusingCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return context.techLevel() >= self._AdvancedFusingMinTechLevel.value()

    def _isRAMCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._isLauncherGrenade:
            return False
        return context.techLevel() >= self._RAMCartridgeMinTechLevel.value()

class _MiniGrenadeImpl(_GrenadeImpl):
    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            isLauncherGrenade: bool,
            payloadWeight: typing.Union[int, float, common.ScalarCalculation],
            payloadCost: typing.Union[int, float, common.ScalarCalculation],
            damageDice: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            flagTraits: typing.Optional[typing.Iterable[gunsmith.WeaponAttribute]] = None,
            numericTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, typing.Union[int, common.ScalarCalculation]]] = None,
            enumTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, enum.Enum]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            isLauncherGrenade=isLauncherGrenade,
            payloadWeight=payloadWeight,
            payloadCost=payloadCost,
            damageDice=damageDice,
            flagTraits=flagTraits,
            numericTraits=numericTraits,
            enumTraits=enumTraits,
            notes=notes,
            isAdvancedFusing=isAdvancedFusing)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Hand grenades have no further requirements
        if not self._isLauncherGrenade:
            return True

        return context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LightSemiAutomaticLauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LightSupportLauncherReceiver,
                sequence=sequence)

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)
        self._isRAMOption.setEnabled(False) # RAM isn't an option for mini grenades

class _FullGrenadeImpl(_GrenadeImpl):
    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            isLauncherGrenade: bool,
            payloadWeight: typing.Union[int, float, common.ScalarCalculation],
            payloadCost: typing.Union[int, float, common.ScalarCalculation],
            damageDice: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            flagTraits: typing.Optional[typing.Iterable[gunsmith.WeaponAttribute]] = None,
            numericTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, typing.Union[int, common.ScalarCalculation]]] = None,
            enumTraits: typing.Optional[typing.Mapping[gunsmith.WeaponAttribute, enum.Enum]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            isLauncherGrenade=isLauncherGrenade,
            payloadWeight=payloadWeight,
            payloadCost=payloadCost,
            damageDice=damageDice,
            flagTraits=flagTraits,
            numericTraits=numericTraits,
            enumTraits=enumTraits,
            notes=notes,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Hand grenades have no further requirements
        if not self._isLauncherGrenade:
            return True

        return context.hasComponent(
            componentType=gunsmith.StandardSingleShotLauncherReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.StandardSemiAutomaticLauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.StandardSupportLauncherReceiver,
                sequence=sequence)

class _MiniAntilaserAerosolGrenadeImpl(_MiniGrenadeImpl):
    """
    Aerosol, Antilaser (Field Catalogue p57):
    - Min TL: 11 (Full Grenade TL +2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr10 (Field Catalogue p57)
    - Trait: Blast 6 (Field Catalogue p57)
    - Note: Optical targeting suffers DM-2. (Field Catalogue p54)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Antilaser Aerosol',
            minTechLevel=11,
            payloadWeight=0.3,
            payloadCost=10,
            numericTraits={gunsmith.WeaponAttribute.Blast: 6},
            notes=['Optical targeting suffers DM-2'],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullAntilaserAerosolGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 9 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr15 (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    - Note: Optical targeting suffers DM-2. (Field Catalogue p54)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Anti-Laser Aerosol',
            minTechLevel=9,
            payloadWeight=0.5,
            payloadCost=15,
            numericTraits={gunsmith.WeaponAttribute.Blast: 9},
            notes=['Optical targeting suffers DM-2'],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullCorrosiveAerosolGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 10 (Field Catalogue p57)
    - Payload Weight: 0.75kg (Field Catalogue p57)
    - Payload Cost: Cr100 (Field Catalogue p57)
    - Damage: 3D (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    - Trait: Corrosive (Field Catalogue p57)
    """
    # NOTE: Mini Corrosive Aerosol cartridges are not available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Corrosive Aerosol',
            minTechLevel=10,
            payloadWeight=0.75,
            payloadCost=100,
            damageDice=3,
            numericTraits={gunsmith.WeaponAttribute.Blast: 9},
            flagTraits=[gunsmith.WeaponAttribute.Corrosive],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullAntiArmourGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 6 (Field Catalogue p57)
    - Payload Weight: 0.1kg (Field Catalogue p57)
    - Payload Cost: Cr50 (Field Catalogue p57)
    - Damage: 4D (Field Catalogue p57)
    - Trait: AP 8 (Field Catalogue p57)
    - Trait: Blast 1 (Field Catalogue p57)
    """
    # NOTE: Mini Anti-Armour cartridges are not available
    # NOTE: The weight of 0.1kg for Anti-Armour grenades seems REALLY low compared to other
    # grenade types but that's what it has in the rules. I suspect it's probably a typo and
    # should be 1kg which would be more in line with other similar grenade types.

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Anti-Armour',
            minTechLevel=6,
            payloadWeight=0.1,
            payloadCost=50,
            damageDice=4,
            numericTraits={
                gunsmith.WeaponAttribute.AP: 8,
                gunsmith.WeaponAttribute.Blast: 1},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniBatonGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 9 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr5 (Field Catalogue p57)
    - Damage: Stun 1D (Field Catalogue p57)
    - Trait: Stun
    - Note: Damage delivered is considered to be tripled when determining if a knockdown has occurred (Field Catalogue p54)
    - Note: Has no effect against rigid armour (Field Catalogue p54)
    - Requirement: Small-calibre baton rounds, when used as a cartridge grenade payload, are treated as mini-grenades. Full-calibre rounds are treated as standard grenades (Field Catalogue p54)
    """
    # NOTE: I've created the Stun trait to show the weapon is doing stun damage
    # NOTE: The description for baton grenades (Field Catalogue p54) says "Small-calibre baton
    # rounds, when used as a cartridge grenade payload, are treated as mini-grenades. Full-calibre
    # rounds are treated as standard grenades". This just seems to be restating the rules for
    # cartridge grenades (Field Catalogue p53) that describe the warhead as "any standard grenade or
    # mini-grenade type". However, the fact that description specifically says that when the
    # description of other grenade types don't, makes me think I'm maybe missing something. As I
    # can't see what that might be, I have to assume that it is just a simple restating of the
    # rules, perhaps due to the fact baton grenades are unique in only really making sense as in
    # cartridge grenade form.

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Baton',
            minTechLevel=9,
            payloadWeight=0.3,
            payloadCost=5,
            damageDice=1,
            notes=[
                'Damage delivered is considered to be tripled when determining if a knockdown has occurred',
                'Has no effect against rigid armour'],
            flagTraits=[gunsmith.WeaponAttribute.Stun],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullBatonGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 7 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr10 (Field Catalogue p57)
    - Damage: Stun 2D (Field Catalogue p57)
    - Trait: Stun
    - Note: Damage delivered is considered to be tripled when determining if a knockdown has occurred (Field Catalogue p54)
    - Note: Has no effect against rigid armour (Field Catalogue p54)
    - Requirement: Small-calibre baton rounds, when used as a cartridge grenade payload, are treated as mini-grenades. Full-calibre rounds are treated as standard grenades (Field Catalogue p54)
    """
    # NOTE: I've created the Stun trait to show the weapon is doing stun damage
    # NOTE: The description for baton grenades (Field Catalogue p54) says "Small-calibre baton
    # rounds, when used as a cartridge grenade payload, are treated as mini-grenades. Full-calibre
    # rounds are treated as standard grenades". This just seems to be restating the rules for
    # cartridge grenades (Field Catalogue p53) that describe the warhead as "any standard grenade or
    # mini-grenade type". However, the fact that description specifically says that when the
    # description of other grenade types don't, makes me think I'm maybe missing something. As I
    # can't see what that might be, I have to assume that it is just a simple restating of the
    # rules, perhaps due to the fact baton grenades are unique in only really making sense as in
    # cartridge grenade form.

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Baton',
            minTechLevel=7,
            payloadWeight=0.5,
            payloadCost=10,
            damageDice=2,
            notes=[
                'Damage delivered is considered to be tripled when determining if a knockdown has occurred',
                'Has no effect against rigid armour'],
            flagTraits=[gunsmith.WeaponAttribute.Stun],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniBattlechemGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 10 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr75 (Field Catalogue p57)
    - Trait: Blast 4 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Battlechem',
            minTechLevel=10,
            payloadWeight=0.3,
            payloadCost=75,
            numericTraits={gunsmith.WeaponAttribute.Blast: 4},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullBattlechemGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 8 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr125 (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Battlechem',
            minTechLevel=8,
            payloadWeight=0.5,
            payloadCost=125,
            numericTraits={gunsmith.WeaponAttribute.Blast: 9},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniBreacherGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 10 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr25 (Field Catalogue p57)
    - Damage: 2D (Field Catalogue p57)
    - Trait: Blast 1 (Field Catalogue p57)
    - Trait: AP 4 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Breacher',
            minTechLevel=10,
            payloadWeight=0.3,
            payloadCost=25,
            damageDice=2,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 1,
                gunsmith.WeaponAttribute.AP: 4},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullBreacherGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 8 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr60 (Field Catalogue p57)
    - Damage: 4D (Field Catalogue p57)
    - Trait: Blast 1 (Field Catalogue p57)
    - Trait: AP 12 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Breacher',
            minTechLevel=8,
            payloadWeight=0.5,
            payloadCost=60,
            damageDice=4,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 1,
                gunsmith.WeaponAttribute.AP: 12},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullCorrosiveGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 10 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr75 (Field Catalogue p57)
    - Damage: 2D (Field Catalogue p57)
    - Trait: Blast 4 (Field Catalogue p57)
    - Trait: Corrosive (Field Catalogue p57)
    """
    # NOTE: Mini Corrosive cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Corrosive',
            minTechLevel=10,
            payloadWeight=0.5,
            payloadCost=75,
            damageDice=2,
            numericTraits={gunsmith.WeaponAttribute.Blast: 4},
            flagTraits=[gunsmith.WeaponAttribute.Corrosive],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullCryogenicGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 14 (Field Catalogue p57)
    - Payload Weight: 0.6kg (Field Catalogue p57)
    - Payload Cost: Cr150 (Field Catalogue p57)
    - Damage: 5D (Field Catalogue p57)
    - Trait: Blast 5 (Field Catalogue p57)
    """
    # NOTE: Mini Cryogenic cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Cryogenic',
            minTechLevel=14,
            payloadWeight=0.6,
            payloadCost=150,
            damageDice=5,
            numericTraits={gunsmith.WeaponAttribute.Blast: 5},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniDistractionGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 9 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr25 (Field Catalogue p57)
    - Note: Typical Distraction (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Distraction',
            minTechLevel=9,
            payloadWeight=0.3,
            payloadCost=25,
            enumTraits={gunsmith.WeaponAttribute.Distraction: gunsmith.Distraction.Typical},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullDistractionGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 7 (Field Catalogue p57)
    - Payload Weight: 0.6kg (Field Catalogue p57)
    - Payload Cost: Cr60 (Field Catalogue p57)
    - Note: Potent Distraction (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Distraction',
            minTechLevel=7,
            payloadWeight=0.6,
            payloadCost=60,
            enumTraits={gunsmith.WeaponAttribute.Distraction: gunsmith.Distraction.Potent},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullEMPGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 9 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr100 (Field Catalogue p57)
    - Trait: Pulse Intensity 9 (Field Catalogue p57)
    """
    # NOTE: Mini Electromagnetic Pulse cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full EMP',
            minTechLevel=9,
            payloadWeight=0.5,
            payloadCost=100,
            numericTraits={gunsmith.WeaponAttribute.PulseIntensity: 9},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullAdvancedEMPGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 12 (Field Catalogue p57)
    - Payload Weight: 0.75kg (Field Catalogue p57)
    - Payload Cost: Cr150 (Field Catalogue p57)
    - Trait: Pulse Intensity 12 (Field Catalogue p57)
    """
    # NOTE: Mini Advanced Electromagnetic Pulse cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Advanced EMP',
            minTechLevel=12,
            payloadWeight=0.75,
            payloadCost=150,
            numericTraits={gunsmith.WeaponAttribute.PulseIntensity: 12},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniFireSuppressionGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 10 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.4kg (Field Catalogue p57)
    - Payload Cost: Cr10 (Field Catalogue p57)
    - Trait: Blast 2 (Field Catalogue p57)
    - Note: Can be used to provide a Small distraction (Field Catalogue p55)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Fire Suppression',
            minTechLevel=10,
            payloadWeight=0.4,
            payloadCost=10,
            numericTraits={gunsmith.WeaponAttribute.Blast: 2},
            enumTraits={gunsmith.WeaponAttribute.Distraction: gunsmith.Distraction.Small},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullFireSuppressionGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 8 (Field Catalogue p57)
    - Payload Weight: 0.8kg (Field Catalogue p57)
    - Payload Cost: Cr15 (Field Catalogue p57)
    - Trait: Blast 3 (Field Catalogue p57)
    - Note: Can be used to provide a Small distraction (Field Catalogue p55)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Fire Suppression',
            minTechLevel=8,
            payloadWeight=0.8,
            payloadCost=15,
            numericTraits={gunsmith.WeaponAttribute.Blast: 3},
            enumTraits={gunsmith.WeaponAttribute.Distraction: gunsmith.Distraction.Small},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniFragmentationGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 8 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.3kg (Field Catalogue p57)
    - Payload Cost: Cr20 (Field Catalogue p57)
    - Damage: 3D (Field Catalogue p57)
    - Trait: Blast 4 (Field Catalogue p57)
    - Trait: Lo-Pen 2 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Fragmentation',
            minTechLevel=8,
            payloadWeight=0.3,
            payloadCost=20,
            damageDice=3,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 4,
                gunsmith.WeaponAttribute.LoPen: 2},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullFragmentationGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 6 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr30 (Field Catalogue p57)
    - Damage: 5D (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    - Trait: Lo-Pen 2 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Fragmentation',
            minTechLevel=6,
            payloadWeight=0.5,
            payloadCost=30,
            damageDice=5,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 9,
                gunsmith.WeaponAttribute.LoPen: 2},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullIncapacitantGasGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 7 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr50 (Field Catalogue p57)
    - Trait: Blast 3 (Field Catalogue p57)
    """
    # NOTE: Mini Incapacitant Gas cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Incapacitant Gas',
            minTechLevel=7,
            payloadWeight=0.5,
            payloadCost=50,
            numericTraits={gunsmith.WeaponAttribute.Blast: 3},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullToxinGasGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 9 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr250 (Field Catalogue p57)
    - Trait: Blast 3 (Field Catalogue p57)
    """
    # NOTE: Mini Toxic Gas cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Toxin Gas',
            minTechLevel=9,
            payloadWeight=0.5,
            payloadCost=250,
            numericTraits={gunsmith.WeaponAttribute.Blast: 3},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullAntipersonnelIncendiaryGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 8 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr75 (Field Catalogue p57)
    - Damage: 2D (Field Catalogue p57)
    - Trait: Blast 15 (Field Catalogue p57)
    - Trait: Incendiary 1 (Field Catalogue p57)
    - Trait: Burn 2 (Field Catalogue p57)
    """
    # NOTE: Mini Antipersonnel Incendiary cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Antipersonnel Incendiary',
            minTechLevel=8,
            payloadWeight=0.5,
            payloadCost=75,
            damageDice=2,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 15,
                gunsmith.WeaponAttribute.Incendiary: 1,
                gunsmith.WeaponAttribute.Burn: 2},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniDemolitionIncendiaryGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 8 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.6kg (Field Catalogue p57)
    - Payload Cost: Cr50 (Field Catalogue p57)
    - Damage: 2D (Field Catalogue p57)
    - Trait: Blast 1 (Field Catalogue p57)
    - Trait: Incendiary 4 (Field Catalogue p57)
    - Trait: Burn 6 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Demolition Incendiary',
            minTechLevel=8,
            payloadWeight=0.6,
            payloadCost=50,
            damageDice=2,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 1,
                gunsmith.WeaponAttribute.Incendiary: 4,
                gunsmith.WeaponAttribute.Burn: 6},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullDemolitionIncendiaryGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 6 (Field Catalogue p57)
    - Payload Weight: 1.2kg (Field Catalogue p57)
    - Payload Cost: Cr80 (Field Catalogue p57)
    - Damage: 3D (Field Catalogue p57)
    - Trait: Blast 2 (Field Catalogue p57)
    - Trait: Incendiary 6 (Field Catalogue p57)
    - Trait: Burn 6 (Field Catalogue p57)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Demolition Incendiary',
            minTechLevel=6,
            payloadWeight=1.2,
            payloadCost=80,
            damageDice=3,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 2,
                gunsmith.WeaponAttribute.Incendiary: 6,
                gunsmith.WeaponAttribute.Burn: 6},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullMicrogrenadeGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 8 (Field Catalogue p57)
    - Payload Weight: 0.75kg (Field Catalogue p57)
    - Payload Cost: Cr150 (Field Catalogue p57)
    - Damage: 2D (Field Catalogue p57)
    - Trait: Blast 3 (Field Catalogue p57)
    - Trait: Lo-Pen 3 (Field Catalogue p57)
    """
    # NOTE: Mini Microgrenade cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Microgrenade',
            minTechLevel=8,
            payloadWeight=0.75,
            payloadCost=150,
            damageDice=2,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 3,
                gunsmith.WeaponAttribute.LoPen: 3},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _MiniMultipleProjectileGrenadeImpl(_MiniGrenadeImpl):
    """
    - Min TL: 8 (Standard TL + 2, Field Catalogue p53)
    - Payload Weight: 0.4kg (Field Catalogue p57)
    - Payload Cost: Cr10 (Field Catalogue p57)
    - Damage: 5D (Field Catalogue p57)
    - Trait: Lo-Pen 3 (Field Catalogue p57)
    - Trait: Spread 2 (Field Catalogue p57)
    - Note: Out to 10m, multiple projectile grenades do full damage after which it is halved to the maximum range of 25m, beyond which it is completely ineffective. (Field Catalogue p55)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Mini Multiple Projectile',
            minTechLevel=8,
            payloadWeight=0.4,
            payloadCost=10,
            damageDice=5,
            numericTraits={
                gunsmith.WeaponAttribute.LoPen: 3,
                gunsmith.WeaponAttribute.Spread: 2},
            notes=['Out to 10m, multiple projectile grenades do full damage after which it is halved to the maximum range of 25m, beyond which it is completely ineffective'],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing)

class _FullMultipleProjectileGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 6 (Field Catalogue p57)
    - Payload Weight: 0.9kg (Field Catalogue p57)
    - Payload Cost: Cr15 (Field Catalogue p57)
    - Damage: 6D (Field Catalogue p57)
    - Trait: Lo-Pen 3 (Field Catalogue p57)
    - Trait: Spread 4 (Field Catalogue p57)
    - Note: Out to 10m, multiple projectile grenades do full damage after which it is halved to the maximum range of 25m, beyond which it is completely ineffective. (Field Catalogue p55)
    """

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Multiple Projectile',
            minTechLevel=6,
            payloadWeight=0.9,
            payloadCost=15,
            damageDice=6,
            numericTraits={
                gunsmith.WeaponAttribute.LoPen: 3,
                gunsmith.WeaponAttribute.Spread: 4},
            notes=['Out to 10m, multiple projectile grenades do full damage after which it is halved to the maximum range of 25m, beyond which it is completely ineffective'],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullPlasmaGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 12 (Field Catalogue p57)
    - Payload Weight: 0.8kg (Field Catalogue p57)
    - Payload Cost: Cr200 (Field Catalogue p57)
    - Damage: 8D (Field Catalogue p57)
    - Trait: Blast 6 (Field Catalogue p57)
    - Trait: Lo-Pen 2 (Field Catalogue p57)
    - Trait: Incendiary 4 (Field Catalogue p57)
    """
    # NOTE: Mini Plasma cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Plasma',
            minTechLevel=12,
            payloadWeight=0.8,
            payloadCost=200,
            damageDice=8,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 6,
                gunsmith.WeaponAttribute.LoPen: 2,
                gunsmith.WeaponAttribute.Incendiary: 4},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullAntiArmourPlasmaGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 12 (Field Catalogue p57)
    - Payload Weight: 0.9kg (Field Catalogue p57)
    - Payload Cost: Cr250 (Field Catalogue p57)
    - Damage: 8D (Field Catalogue p57)
    - Trait: Blast 3 (Field Catalogue p57)
    - Trait: AP 6 (Field Catalogue p57)
    - Trait: Incendiary 4 (Field Catalogue p57)
    """
    # NOTE: Mini Plasma cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Anti-Armour Plasma',
            minTechLevel=12,
            payloadWeight=0.9,
            payloadCost=250,
            damageDice=8,
            numericTraits={
                gunsmith.WeaponAttribute.Blast: 3,
                gunsmith.WeaponAttribute.AP: 6,
                gunsmith.WeaponAttribute.Incendiary: 4},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullSmokeGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 6 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr15 (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    """
    # NOTE: Mini Plasma cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Smoke/Thermosmoke',
            minTechLevel=6,
            payloadWeight=0.5,
            payloadCost=15,
            numericTraits={gunsmith.WeaponAttribute.Blast: 9},
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)

class _FullStunGrenadeImpl(_FullGrenadeImpl):
    """
    - Min TL: 7 (Field Catalogue p57)
    - Payload Weight: 0.5kg (Field Catalogue p57)
    - Payload Cost: Cr30 (Field Catalogue p57)
    - Damage: Stun 3D (Field Catalogue p57)
    - Trait: Blast 9 (Field Catalogue p57)
    - Trait: Stun
    """
    # NOTE: I've created the Stun trait to show the weapon is doing stun damage
    # NOTE: Mini Plasma cartridges aren't available

    def __init__(
            self,
            isLauncherGrenade: bool,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Full Stun',
            minTechLevel=7,
            payloadWeight=0.5,
            payloadCost=30,
            damageDice=3,
            numericTraits={gunsmith.WeaponAttribute.Blast: 9},
            flagTraits=[gunsmith.WeaponAttribute.Stun],
            isLauncherGrenade=isLauncherGrenade,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM)


# █████                                                █████
#░░███                                                ░░███
# ░███         ██████   █████ ████ ████████    ██████  ░███████    ██████  ████████
# ░███        ░░░░░███ ░░███ ░███ ░░███░░███  ███░░███ ░███░░███  ███░░███░░███░░███
# ░███         ███████  ░███ ░███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███████  ░███ ░░░
# ░███      █ ███░░███  ░███ ░███  ░███ ░███ ░███  ███ ░███ ░███ ░███░░░   ░███
# ███████████░░████████ ░░████████ ████ █████░░██████  ████ █████░░██████  █████
#░░░░░░░░░░░  ░░░░░░░░   ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░

class LauncherAmmoLoaded(gunsmith.AmmoLoadedInterface):
    """
    Requirement: Weapons with a removable magazine must have one loaded
    """

    def __init__(
            self,
            impl: _GrenadeImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Grenades'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        # If the weapon uses a removable magazine it must have one loaded
        if context.hasComponent(
                componentType=gunsmith.RemovableMagazineFeed,
                sequence=sequence):
            return context.hasComponent(
                componentType=gunsmith.LauncherMagazineLoaded,
                sequence=sequence)

        return True # Compatible with all fixed magazine weapons

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
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity)
        assert(isinstance(ammoCapacity, common.ScalarCalculation)) # Construction logic should enforce this

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfGrenades=ammoCapacity,
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class MiniAntilaserAerosolLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniAntilaserAerosolGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullAntilaserAerosolLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullAntilaserAerosolGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullCorrosiveAerosolLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullCorrosiveAerosolGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullAntiArmourLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullAntiArmourGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniBatonLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniBatonGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullBatonLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullBatonGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniBattlechemLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniBattlechemGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullBattlechemLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullBattlechemGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniBreacherLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniBreacherGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullBreacherLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullBreacherGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullCorrosiveLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullCorrosiveGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullCryogenicLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullCryogenicGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniDistractionLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniDistractionGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullDistractionLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullDistractionGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullEMPLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullEMPGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullAdvancedEMPLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullAdvancedEMPGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniFireSuppressionLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniFireSuppressionGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullFireSuppressionLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullFireSuppressionGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniFragmentationLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniFragmentationGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullFragmentationLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullFragmentationGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullIncapacitantGasLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullIncapacitantGasGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullToxinGasLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullToxinGasGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullAntipersonnelIncendiaryLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullAntipersonnelIncendiaryGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniDemolitionIncendiaryLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniDemolitionIncendiaryGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullDemolitionIncendiaryLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullDemolitionIncendiaryGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullMicrogrenadeLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullMicrogrenadeGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class MiniMultipleProjectileLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_MiniMultipleProjectileGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing))

class FullMultipleProjectileLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullMultipleProjectileGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullPlasmaLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullPlasmaGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullAntiArmourPlasmaLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullAntiArmourPlasmaGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullSmokeLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullSmokeGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class FullStunLauncherAmmoLoaded(LauncherAmmoLoaded):
    def __init__(
            self,
            isAdvancedFusing: typing.Optional[bool] = None,
            isRAM: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FullStunGrenadeImpl(
            isLauncherGrenade=True,
            isAdvancedFusing=isAdvancedFusing,
            isRAM=isRAM))

class LauncherAmmoQuantity(gunsmith.AmmoQuantityInterface):
    def __init__(
            self,
            impl: _GrenadeImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfGrenadesOption = construction.IntegerComponentOption(
            id='Quantity',
            name='Grenades',
            value=1,
            minValue=1,
            description='Specify the number of cartridge grenades.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfGrenadesOption.value()}'

    def typeString(self) -> str:
        return 'Cartridge Grenade Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfGrenadesOption]
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
        numberOfGrenades = common.ScalarCalculation(
            value=self._numberOfGrenadesOption.value(),
            name='Specified Number Of Cartridge Grenades')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfGrenades=numberOfGrenades,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class MiniAntilaserAerosolLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniAntilaserAerosolGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniAntilaserAerosolLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullAntilaserAerosolLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntilaserAerosolGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullAntilaserAerosolLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullCorrosiveAerosolLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCorrosiveAerosolGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullCorrosiveAerosolLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullAntiArmourLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntiArmourGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullAntiArmourLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniBatonLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBatonGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniBatonLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullBatonLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBatonGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullBatonLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniBattlechemLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBattlechemGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniBattlechemLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullBattlechemLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBattlechemGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullBattlechemLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniBreacherLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBreacherGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniBreacherLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullBreacherLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBreacherGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullBreacherLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullCorrosiveLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCorrosiveGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullCorrosiveLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullCryogenicLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCryogenicGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullCryogenicLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniDistractionLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniDistractionGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniDistractionLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullDistractionLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullDistractionGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullDistractionLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullEMPLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullEMPGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullEMPLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullAdvancedEMPLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAdvancedEMPGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullAdvancedEMPLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniFireSuppressionLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniFireSuppressionGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniFireSuppressionLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullFireSuppressionLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullFireSuppressionGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullFireSuppressionLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniFragmentationLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniFragmentationGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniFragmentationLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullFragmentationLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullFragmentationGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullFragmentationLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullIncapacitantGasLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullIncapacitantGasGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullIncapacitantGasLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullToxinGasLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullToxinGasGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullToxinGasLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullAntipersonnelIncendiaryLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntipersonnelIncendiaryGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullAntipersonnelIncendiaryLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniDemolitionIncendiaryLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniDemolitionIncendiaryGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniDemolitionIncendiaryLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullDemolitionIncendiaryLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullDemolitionIncendiaryGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullDemolitionIncendiaryLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullMicrogrenadeLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullMicrogrenadeGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullMicrogrenadeLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class MiniMultipleProjectileLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniMultipleProjectileGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return MiniMultipleProjectileLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing())

class FullMultipleProjectileLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullMultipleProjectileGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullMultipleProjectileLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullPlasmaLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullPlasmaGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullPlasmaLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullAntiArmourPlasmaLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntiArmourPlasmaGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullAntiArmourPlasmaLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullSmokeLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullSmokeGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullSmokeLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())

class FullStunLauncherAmmoQuantity(LauncherAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullStunGrenadeImpl(isLauncherGrenade=True))

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FullStunLauncherAmmoLoaded(
            isAdvancedFusing=self._impl.isAdvancedFusing(),
            isRAM=self._impl.isRAM())


# █████   █████                          █████
#░░███   ░░███                          ░░███
# ░███    ░███   ██████   ████████    ███████
# ░███████████  ░░░░░███ ░░███░░███  ███░░███
# ░███░░░░░███   ███████  ░███ ░███ ░███ ░███
# ░███    ░███  ███░░███  ░███ ░███ ░███ ░███
# █████   █████░░████████ ████ █████░░████████
#░░░░░   ░░░░░  ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░░░

class HandGrenadeQuantity(gunsmith.HandGrenadeQuantityInterface):
    def __init__(
            self,
            impl: _GrenadeImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfGrenadesOption = construction.IntegerComponentOption(
            id='Quantity',
            name='Grenades',
            value=1,
            minValue=1,
            description='Specify the number of grenades.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfGrenadesOption.value()}'

    def typeString(self) -> str:
        return 'Hand Grenade Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfGrenadesOption]
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
        numberOfGrenades = common.ScalarCalculation(
            value=self._numberOfGrenadesOption.value(),
            name='Specified Number Of Grenades')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfGrenades=numberOfGrenades,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class MiniAntilaserAerosolHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniAntilaserAerosolGrenadeImpl(isLauncherGrenade=False))

class FullAntilaserAerosolHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntilaserAerosolGrenadeImpl(isLauncherGrenade=False))

class FullCorrosiveAerosolHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCorrosiveAerosolGrenadeImpl(isLauncherGrenade=False))

class FullAntiArmourHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntiArmourGrenadeImpl(isLauncherGrenade=False))

class MiniBatonHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBatonGrenadeImpl(isLauncherGrenade=False))

class FullBatonHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBatonGrenadeImpl(isLauncherGrenade=False))

class MiniBattlechemHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBattlechemGrenadeImpl(isLauncherGrenade=False))

class FullBattlechemHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBattlechemGrenadeImpl(isLauncherGrenade=False))

class MiniBreacherHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniBreacherGrenadeImpl(isLauncherGrenade=False))

class FullBreacherHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullBreacherGrenadeImpl(isLauncherGrenade=False))

class FullCorrosiveHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCorrosiveGrenadeImpl(isLauncherGrenade=False))

class FullCryogenicHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullCryogenicGrenadeImpl(isLauncherGrenade=False))

class MiniDistractionv(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniDistractionGrenadeImpl(isLauncherGrenade=False))

class FullDistractionHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullDistractionGrenadeImpl(isLauncherGrenade=False))

class FullEMPHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullEMPGrenadeImpl(isLauncherGrenade=False))

class FullAdvancedEMPHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAdvancedEMPGrenadeImpl(isLauncherGrenade=False))

class MiniFireSuppressionHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniFireSuppressionGrenadeImpl(isLauncherGrenade=False))

class FullFireSuppressionHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullFireSuppressionGrenadeImpl(isLauncherGrenade=False))

class MiniFragmentationHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniFragmentationGrenadeImpl(isLauncherGrenade=False))

class FullFragmentationHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullFragmentationGrenadeImpl(isLauncherGrenade=False))

class FullIncapacitantGasHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullIncapacitantGasGrenadeImpl(isLauncherGrenade=False))

class FullToxinGasHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullToxinGasGrenadeImpl(isLauncherGrenade=False))

class FullAntipersonnelIncendiaryHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntipersonnelIncendiaryGrenadeImpl(isLauncherGrenade=False))

class MiniDemolitionIncendiaryHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniDemolitionIncendiaryGrenadeImpl(isLauncherGrenade=False))

class FullDemolitionIncendiaryHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullDemolitionIncendiaryGrenadeImpl(isLauncherGrenade=False))

class FullMicrogrenadeHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullMicrogrenadeGrenadeImpl(isLauncherGrenade=False))

class MiniMultipleProjectileHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_MiniMultipleProjectileGrenadeImpl(isLauncherGrenade=False))

class FullMultipleProjectileHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullMultipleProjectileGrenadeImpl(isLauncherGrenade=False))

class FullPlasmaHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullPlasmaGrenadeImpl(isLauncherGrenade=False))

class FullAntiArmourPlasmaHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullAntiArmourPlasmaGrenadeImpl(isLauncherGrenade=False))

class FullSmokeHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullSmokeGrenadeImpl(isLauncherGrenade=False))

class FullStunHandGrenadeQuantity(HandGrenadeQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FullStunGrenadeImpl(isLauncherGrenade=False))
