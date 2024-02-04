import common
import construction
import gunsmith
import typing

_SecondaryWeaponBaseQuickdraw = common.ScalarCalculation(
    value=0,
    name='Secondary Weapon Base Quickdraw')

_EnableBaseHeatOptionDescription = \
    '<p>Enable user specified base heat values.</p>' \
    '<p>The Field Catalogue isn\'t clear on the base heat related values for energy weapons and ' \
    'launchers or even if the heat rules apply to those types of weapons. This allows you to ' \
    'specify base values if you or your Referee require it.</p>'

_BaseHeatGenerationOptionDescription = \
    '<p>Specify the number of points of heat that are generated each time a <b>single ' \
    'shot</b> is fired.</p>' \
    '<p>The description on p13 and table on p14 don\'t specify how much heat launchers generate ' \
    'and it\'s not obvious that it should be tied to the damage of the weapon in the same way as ' \
    'conventional and energy weapons. This allows you to specify values that you agree with your ' \
    'Referee.</p>' \
    '<p>Note this is the heat generated each time a single shot is fired. Additional heat from Auto ' \
    'attacks will be calculated automatically.</p>'

_BaseHeatDissipationOptionDescription = \
    '<p>Specify the number of points of heat that the weapon dissipates each round it\'s ' \
    '<b>not</b> fired.</p>' \
    '<p>The description on p13 and table on p14 don\'t specify how much heat energy weapons and ' \
    'launchers dissipate each round they\'re not fired. This allows you to specify values that you ' \
    'agree with your Referee.</p>'

_BaseOverheatThresholdOptionDescription = \
    '<p>Specify the Base Overheat Threshold for the weapon.</p>' \
    '<p>The table description on p13 and table on p14 don\'t specify a Base Overheat Threshold for ' \
    'energy weapons and launchers. This allows you to specify values that you agree with your Referee.</p>'

_BaseDangerHeatThresholdOptionDescription = \
    '<p>Specify the Base Danger Heat Threshold for the weapon.</p>' \
    '<p>The table description on p13 and table on p14 don\'t specify a Base Danger Heat Threshold for ' \
    'energy weapons and launchers. This allows you to specify values that you agree with your Referee.</p>'

_BaseDisasterHeatThresholdOptionDescription = \
    '<p>Specify the Base Disaster Heat Threshold for the weapon.</p>' \
    '<p>The table description on p13 and table on p14 don\'t specify a Base Disaster Heat Threshold for ' \
    'energy weapons and launchers. This allows you to specify values that you agree with your Referee.</p>'


#   █████████                                                       █████     ███                                ████
#  ███░░░░░███                                                     ░░███     ░░░                                ░░███
# ███     ░░░   ██████  ████████   █████ █████  ██████  ████████   ███████   ████   ██████  ████████    ██████   ░███
#░███          ███░░███░░███░░███ ░░███ ░░███  ███░░███░░███░░███ ░░░███░   ░░███  ███░░███░░███░░███  ░░░░░███  ░███
#░███         ░███ ░███ ░███ ░███  ░███  ░███ ░███████  ░███ ░███   ░███     ░███ ░███ ░███ ░███ ░███   ███████  ░███
#░░███     ███░███ ░███ ░███ ░███  ░░███ ███  ░███░░░   ░███ ░███   ░███ ███ ░███ ░███ ░███ ░███ ░███  ███░░███  ░███
# ░░█████████ ░░██████  ████ █████  ░░█████   ░░██████  ████ █████  ░░█████  █████░░██████  ████ █████░░████████ █████
#  ░░░░░░░░░   ░░░░░░  ░░░░ ░░░░░    ░░░░░     ░░░░░░  ░░░░ ░░░░░    ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░ ░░░░░

class ConventionalReceiver(gunsmith.ReceiverInterface):
    """
    Min TL: 3
    Requirement: Base Quickdraw is not applied to Secondary Weapons
    """
    # NOTE: I can't find anything in the Field Catalogue that gives a min TL for conventional
    # receivers so I've just gone with the min TL for antique weapons from the Core Rules p118
    # NOTE: I've added the requirement that the base Quickdraw is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # It's not obvious exactly what should be done for the base Quickdraw of a secondary weapon.
    # It seems wrong to include it as it would mean adding a secondary weapon with a handgun
    # receiver to a weapon that has a heavy receiver will result in the weapon as a whole having
    # a better Quickdraw than it did if it didn't have a secondary weapon. On the flip side it
    # seems wrong to not include it as you get the opposite case where adding a secondary weapon
    # with a heavy receiver to a weapon with a handgun receiver would not result in any change in
    # the Quickdraw of the weapon as a whole (other than the -1 per additional barrel).
    # I've decided the best approach is to not include it and leave it up to the referee to all
    # foul if a player tries to add a sniper rifle as a secondary weapon to a pistol.
    # NOTE: The rules aren't clear around the emissions signature of conventional firearms. They
    # do mention conventional weapons with electric ignition (Field Catalogue p30), and says they
    # have a Minimal emissions signature. As it's unclear I've added an option so the user can
    # specify one if they want. Note that the physical signature isn't set until the calibre
    # selection, however I've added the physical signature here for consistency with where it's
    # specified for other types of weapon.

    _MinTechLevel = 3
    _BarrelCount = common.ScalarCalculation(
        value=1,
        name='Conventional Receiver Base Barrel Count')

    _BaseEmissionsSignatureOptionDescription = \
        '<p>Specify the Base Emissions Signature of the weapon.</p>' \
        '<p>On p30 of the Field Catalogue it says that some conventional weapons can have ' \
        'an Emissions Signature due to electric initiation. This allows you to specify a ' \
        'value if required.</p>'

    def __init__(
            self,
            componentString: str,
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseCapacity: typing.Union[int, float, common.ScalarCalculation],
            baseQuickdraw: typing.Union[int, common.ScalarCalculation],
            baseHeatDissipation: typing.Union[int, common.ScalarCalculation],
            baseOverheatThreshold: typing.Union[int, common.ScalarCalculation],
            baseDangerHeatThreshold: typing.Union[int, common.ScalarCalculation],
            baseDisasterHeatThreshold: typing.Union[int, common.ScalarCalculation],
            baseRecoil: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__()

        if not isinstance(baseWeight, common.ScalarCalculation):
            baseWeight = common.ScalarCalculation(
                value=baseWeight,
                name=f'{componentString} Receiver Base Weight')

        if not isinstance(baseCost, common.ScalarCalculation):
            baseCost = common.ScalarCalculation(
                value=baseCost,
                name=f'{componentString} Receiver Base Cost')

        if not isinstance(baseCapacity, common.ScalarCalculation):
            baseCapacity = common.ScalarCalculation(
                value=baseCapacity,
                name=f'{componentString} Receiver Base Ammo Capacity')

        if not isinstance(baseQuickdraw, common.ScalarCalculation):
            baseQuickdraw = common.ScalarCalculation(
                value=baseQuickdraw,
                name=f'{componentString} Receiver Base Quickdraw')

        if not isinstance(baseHeatDissipation, common.ScalarCalculation):
            baseHeatDissipation = common.ScalarCalculation(
                value=baseHeatDissipation,
                name=f'{componentString} Receiver Base Heat Dissipation')

        if not isinstance(baseOverheatThreshold, common.ScalarCalculation):
            baseOverheatThreshold = common.ScalarCalculation(
                value=baseOverheatThreshold,
                name=f'{componentString} Receiver Base Overheat Threshold')

        if not isinstance(baseDangerHeatThreshold, common.ScalarCalculation):
            baseDangerHeatThreshold = common.ScalarCalculation(
                value=baseDangerHeatThreshold,
                name=f'{componentString} Receiver Base Danger Heat Threshold')

        if not isinstance(baseDisasterHeatThreshold, common.ScalarCalculation):
            baseDisasterHeatThreshold = common.ScalarCalculation(
                value=baseDisasterHeatThreshold,
                name=f'{componentString} Receiver Base Disaster Heat Threshold')

        if baseRecoil != None and not isinstance(baseRecoil, common.ScalarCalculation):
            baseRecoil = common.ScalarCalculation(
                value=baseRecoil,
                name=f'{componentString} Receiver Base Recoil')

        self._componentString = componentString
        self._baseWeight = baseWeight
        self._baseCost = baseCost
        self._baseCapacity = baseCapacity
        self._baseQuickdraw = baseQuickdraw
        self._baseHeatDissipation = baseHeatDissipation
        self._baseOverheatThreshold = baseOverheatThreshold
        self._baseDangerHeatThreshold = baseDangerHeatThreshold
        self._baseDisasterHeatThreshold = baseDisasterHeatThreshold
        self._baseRecoil = baseRecoil

        self._baseEmissionsSignatureOption = construction.EnumComponentOption(
            id='EmissionsSignature',
            name='Base Emissions Signature',
            type=gunsmith.Signature,
            value=None, # The rules suggest only some conventional weapons have an emissions signature so default to None
            isOptional=True, # Allow it to be optional don't explicitly give one
            description=ConventionalReceiver._BaseEmissionsSignatureOptionDescription)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Receiver'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._MinTechLevel:
            return False

        return context.weaponType(sequence=sequence) == gunsmith.WeaponType.ConventionalWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._baseEmissionsSignatureOption]

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

        step.setWeight(weight=construction.ConstantModifier(value=self._baseWeight))
        step.setCredits(credits=construction.ConstantModifier(value=self._baseCost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
            value=self._baseCapacity))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Quickdraw,
            value=self._baseQuickdraw if context.isPrimary(sequence=sequence) else _SecondaryWeaponBaseQuickdraw))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.HeatDissipation,
            value=self._baseHeatDissipation))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.OverheatThreshold,
            value=self._baseOverheatThreshold))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.DangerHeatThreshold,
            value=self._baseDangerHeatThreshold))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.DisasterHeatThreshold,
            value=self._baseDisasterHeatThreshold))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.BarrelCount,
            value=self._BarrelCount))

        if self._baseRecoil:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.Recoil,
                value=self._baseRecoil))

        emissionsSignature = self._baseEmissionsSignatureOption.value()
        if emissionsSignature:
            assert(isinstance(emissionsSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.EmissionsSignature,
                value=emissionsSignature))

        return step

class HandgunReceiver(ConventionalReceiver):
    """
    - Base Cost: 175
    - Base Weight: 0.8
    - Base Ammo Capacity: 10
    - Base Quickdraw: +4
    - Base Heat Dissipation: 2 (From table on Field Catalogue p14)
    - Base Overheat Threshold: 10 (From table on Field Catalogue p14)
    - Base Danger Heat Threshold: 15 (From table on Field Catalogue p14)
    - Base Disaster Heat Threshold: 20 (From table on Field Catalogue p14)
    - Base Recoil: -2 (From list on Field Catalogue p32)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Handgun',
            baseWeight=0.8,
            baseCost=175,
            baseCapacity=10,
            baseQuickdraw=4,
            baseHeatDissipation=2,
            baseOverheatThreshold=10,
            baseDangerHeatThreshold=15,
            baseDisasterHeatThreshold=20,
            baseRecoil=-2)

class AssaultReceiver(ConventionalReceiver):
    """
    - Base Cost: 300
    - Base Weight: 2
    - Base Ammo Capacity: 20
    - Base Quickdraw: +2
    - Base Heat Dissipation: 4 (From table on Core rules p14)
    - Base Overheat Threshold: 15 (From table on Core rules p14)
    - Base Danger Heat Threshold: 30 (From table on Core rules p14)
    - Base Disaster Heat Threshold: 45 (From table on Core rules p14)
    - Base Recoil: -4 (From list on Field Catalogue p32)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Assault',
            baseWeight=2,
            baseCost=300,
            baseCapacity=20,
            baseQuickdraw=2,
            baseHeatDissipation=4,
            baseOverheatThreshold=15,
            baseDangerHeatThreshold=30,
            baseDisasterHeatThreshold=45,
            baseRecoil=-4)

class LongarmReceiver(ConventionalReceiver):
    """
    - Base Cost: 400
    - Base Weight: 2.5
    - Base Ammo Capacity: 30
    - Base Quickdraw: 0
    - Base Heat Dissipation: 6 (From table on Core rules p14)
    - Base Overheat Threshold: 20 (From table on Core rules p14)
    - Base Danger Heat Threshold: 40 (From table on Core rules p14)
    - Base Disaster Heat Threshold: 60 (From table on Core rules p14)
    - Base Recoil: -6 (From list on Field Catalogue p32)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Longarm',
            baseWeight=2.5,
            baseCost=400,
            baseCapacity=30,
            baseQuickdraw=0,
            baseHeatDissipation=6,
            baseOverheatThreshold=20,
            baseDangerHeatThreshold=40,
            baseDisasterHeatThreshold=60,
            baseRecoil=-6)

class LightSupportReceiver(ConventionalReceiver):
    """
    - Base Cost: 1500
    - Base Weight: 5
    - Base Ammo Capacity: 50
    - Base Quickdraw: -4
    - Base Heat Dissipation: 8 (From table on Core rules p14)
    - Base Overheat Threshold: 25 (From table on Core rules p14)
    - Base Danger Heat Threshold: 50 (From table on Core rules p14)
    - Base Disaster Heat Threshold: 75 (From table on Core rules p14)
    - Base Recoil: -8 (From list on Field Catalogue p32)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Light Support',
            baseWeight=5,
            baseCost=1500,
            baseCapacity=50,
            baseQuickdraw=-4,
            baseHeatDissipation=8,
            baseOverheatThreshold=25,
            baseDangerHeatThreshold=50,
            baseDisasterHeatThreshold=75,
            baseRecoil=-8)

class HeavyWeaponReceiver(ConventionalReceiver):
    """
    - Base Cost: 3000
    - Base Weight: 10
    - Base Ammo Capacity: 50
    - Base Quickdraw: -8
    - Base Heat Dissipation: 10 (From table on Core rules p14)
    - Base Overheat Threshold: 30 (From table on Core rules p14)
    - Base Danger Heat Threshold: 60 (From table on Core rules p14)
    - Base Disaster Heat Threshold: 90 (From table on Core rules p14)
    """
    # NOTE: The naming of this receiver seems to be inconsistent. In some places it's referred to as
    # a Heavy Weapon receiver (Field Catalogue p31) and other places it's referred to as a Support
    # Receiver (Heating Effects table Field Catalogue p14)
    # NOTE: There is no entry for the Support receiver in the list of recoils (Field Catalogue p32).
    # I've decided to let the user specify the value. I've gone with a default of -10 as that would
    # fit the pattern of recoils for other lighter receiver types
    # NOTE: Although the rule say a Heavy Weapon usually requires a support mount or emplacement
    # (Field Catalogue p31), I've not done anything to enforce it as the rules don't say you can't
    # mount a Gravitic System to it and run around like a lunatic (no idea if inertia comes into
    # play when using grav assist).
    _DefaultBaseRecoilValue = -10
    _MaxBaseRecoilValue = -6 # Can't be higher than Light Support Weapon
    _MinBaseRecoilValue = -20 # Arbitrary minimum value

    _BaseRecoilOptionDescription = \
        '<p>Specify the Base Recoil for the weapon.</p>' \
        '<p>The table of p32 of the Field Catalogue doesn\'t give a base recoil value for a Heavy ' \
        'Support Weapon. This allows you to specify a value that you agree with your Referee. The value ' \
        f'defaults to {_DefaultBaseRecoilValue} as that is the next logical progression based on ' \
        'the pattern of values in the table.</p>'

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy Weapon',
            baseWeight=10,
            baseCost=3000,
            baseCapacity=50,
            baseQuickdraw=-8,
            baseHeatDissipation=10,
            baseOverheatThreshold=30,
            baseDangerHeatThreshold=60,
            baseDisasterHeatThreshold=90)

        self._baseRecoilOption = construction.IntegerComponentOption(
            id='Recoil',
            name='Base Recoil',
            value=HeavyWeaponReceiver._DefaultBaseRecoilValue,
            maxValue=HeavyWeaponReceiver._MaxBaseRecoilValue,
            minValue=HeavyWeaponReceiver._MinBaseRecoilValue,
            description=HeavyWeaponReceiver._BaseRecoilOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._baseRecoilOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        baseRecoil = common.ScalarCalculation(
            value=self._baseRecoilOption.value(),
            name=f'Specified {self.componentString()} Receiver Base Recoil')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Recoil,
            value=baseRecoil))

        return step


# █████                                                █████
#░░███                                                ░░███
# ░███         ██████   █████ ████ ████████    ██████  ░███████    ██████  ████████
# ░███        ░░░░░███ ░░███ ░███ ░░███░░███  ███░░███ ░███░░███  ███░░███░░███░░███
# ░███         ███████  ░███ ░███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███████  ░███ ░░░
# ░███      █ ███░░███  ░███ ░███  ░███ ░███ ░███  ███ ░███ ░███ ░███░░░   ░███
# ███████████░░████████ ░░████████ ████ █████░░██████  ████ █████░░██████  █████
#░░░░░░░░░░░  ░░░░░░░░   ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░

class LauncherReceiver(gunsmith.ReceiverInterface):
    """
    - Quickdraw: -8 (Primary weapon only)
    """
    # NOTE: I can't find mention of what the base physical or emissions signature is for a launcher.
    # The rules say all firearms and energy weapons have a physical signature but it's not clear if
    # firearms include launchers (I assume it does). However there is no such comment regarding the
    # emissions signature. As it's so unclear I've added options so the user can specify the value
    # if they want to.
    # NOTE: I can't find the rule for the Quickdraw modifier in the Field Catalogue, however all the
    # example weapons on p118-120 have a base Quickdraw of -8
    # NOTE: I've added the requirement that the base Quickdraw is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # It's not obvious exactly what should be done for the base Quickdraw of a secondary weapon.
    # It seems wrong to include it as it would mean adding a secondary weapon with a handgun
    # receiver to a weapon that has a heavy receiver will result in the weapon as a whole having
    # a better Quickdraw than it did if it didn't have a secondary weapon. On the flip side it
    # seems wrong to not include it as you get the opposite case where adding a secondary weapon
    # with a heavy receiver to a weapon with a handgun receiver would not result in any change in
    # the Quickdraw of the weapon as a whole (other than the -1 per additional barrel).
    # I've decided the best approach is to not include it and leave it up to the referee to all
    # foul if a player tries to add a sniper rifle as a secondary weapon to a pistol.
    # NOTE: I've added options so the user can specify base heat dissipation and mishap thresholds
    # as the rules don't make it clear what they'd be for a launcher but you would expect it would
    # generate some heat. The values default to 0 and the user can just ignore them if they choose
    # the heat rules don't apply to launchers
    # NOTE: I've added an option so the user can specify base heat generation per attack as the
    # rules don't specify one. Other types of weapon use the number of damage dice but that doesn't
    # apply to launchers as their damage is determined by the payload of the grenade.

    _QuickdrawModifier = common.ScalarCalculation(
        value=-8,
        name='Launcher Receiver Base Quickdraw')
    _BarrelCount = common.ScalarCalculation(
        value=1,
        name='Launcher Receiver Base Barrel Count')

    _BasePhysicalSignatureOptionDescription = \
        '<p>Specify the Base Physical Signature of the weapon.</p>' \
        '<p>On p7 of the Field Catalogue it says all firearms and energy weapons have at least ' \
        'some Physical Signature, however the rules don\'t specify what that is for a launcher ' \
        'weapon. This allows you to specify a value that you agree with your Referee. It defaults ' \
        'to Normal as that is the base value used for the examples on p120 & p121.</p>'

    _BaseEmissionsSignatureOptionDescription = \
        '<p>Specify the Base Emissions Signature of the weapon.</p>' \
        '<p>The Field Catalogue doesn\'t make it clear if launcher weapons have an Emissions Signature. ' \
        'However it seems logical that they could have electric initiation in the same was as described ' \
        'for conventional weapons on p30. This allows you to specify a value if required.</p>'

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseRange: typing.Union[int, common.ScalarCalculation],
            baseCapacity: typing.Union[int, common.ScalarCalculation] = None,
            sizeTrait: typing.Optional[gunsmith.WeaponAttribute] = None
            ) -> None:
        super().__init__()

        if not isinstance(baseWeight, common.ScalarCalculation):
            baseWeight = common.ScalarCalculation(
                value=baseWeight,
                name=f'{componentString} Receiver Base Weight')

        if not isinstance(baseCost, common.ScalarCalculation):
            baseCost = common.ScalarCalculation(
                value=baseCost,
                name=f'{componentString} Receiver Base Cost')

        if not isinstance(baseRange, common.ScalarCalculation):
            baseRange = common.ScalarCalculation(
                value=baseRange,
                name=f'{componentString} Receiver Base Range')

        if baseCapacity != None and not isinstance(baseCapacity, common.ScalarCalculation):
            baseCapacity = common.ScalarCalculation(
                value=baseCapacity,
                name=f'{componentString} Receiver Base Ammo Capacity')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._baseWeight = baseWeight
        self._baseCost = baseCost
        self._baseRange = baseRange
        self._baseCapacity = baseCapacity
        self._sizeTrait = sizeTrait

        self._basePhysicalSignatureOption = construction.EnumComponentOption(
            id='PhysicalSignature',
            name='Base Physical Signature',
            type=gunsmith.Signature,
            value=gunsmith.Signature.Normal, # Default to normal as the rules suggest all weapon types have a physical signature
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=LauncherReceiver._BasePhysicalSignatureOptionDescription)

        self._baseEmissionsSignatureOption = construction.EnumComponentOption(
            id='EmissionsSignature',
            name='Base Emissions Signature',
            type=gunsmith.Signature,
            value=None, # It's not obvious launchers have an emission signature so default to None
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=LauncherReceiver._BaseEmissionsSignatureOptionDescription)

        self._enableHeatOption = construction.BooleanComponentOption(
            id='EnableBaseHeat',
            name='Specify Base Heat Values',
            value=False,
            description=_EnableBaseHeatOptionDescription)

        self._baseHeatGenerationOption = construction.IntegerComponentOption(
            id='HeatGeneration',
            name='Base Heat Per Attack',
            value=0,
            minValue=0,
            description=_BaseHeatGenerationOptionDescription)

        self._baseHeatDissipationOption = construction.IntegerComponentOption(
            id='HeatDissipation',
            name='Base Heat Dissipation',
            value=0,
            minValue=0,
            description=_BaseHeatDissipationOptionDescription)

        self._baseOverheatThresholdOption = construction.IntegerComponentOption(
            id='OverheatThreshold',
            name='Base Overheat Threshold',
            value=0,
            minValue=0,
            description=_BaseOverheatThresholdOptionDescription)

        self._baseDangerHeatThresholdOption = construction.IntegerComponentOption(
            id='DangerHeatThreshold',
            name='Base Danger Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDangerHeatThresholdOptionDescription)

        self._baseDisasterHeatThresholdOption = construction.IntegerComponentOption(
            id='DisasterHeatThreshold',
            name='Base Disaster Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDisasterHeatThresholdOptionDescription)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Receiver'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel:
            return False

        return context.weaponType(sequence=sequence) == gunsmith.WeaponType.GrenadeLauncherWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [
            self._basePhysicalSignatureOption,
            self._baseEmissionsSignatureOption,
            self._enableHeatOption
        ]

        if self._enableHeatOption.value():
            options.extend([
                self._baseHeatGenerationOption,
                self._baseHeatDissipationOption,
                self._baseOverheatThresholdOption,
                self._baseDangerHeatThresholdOption,
                self._baseDisasterHeatThresholdOption
            ])

        return options

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
            type=self.typeString(),
            credits=construction.ConstantModifier(value=self._baseCost),
            weight=construction.ConstantModifier(value=self._baseWeight))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Range,
            value=self._baseRange))

        if self._baseCapacity:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
                value=self._baseCapacity))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.BarrelCount,
            value=self._BarrelCount))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Quickdraw,
            value=self._QuickdrawModifier if context.isPrimary(sequence=sequence) else _SecondaryWeaponBaseQuickdraw))

        physicalSignature = self._basePhysicalSignatureOption.value()
        if physicalSignature:
            assert(isinstance(physicalSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.PhysicalSignature,
                value=physicalSignature))

        emissionsSignature = self._baseEmissionsSignatureOption.value()
        if emissionsSignature:
            assert(isinstance(emissionsSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.EmissionsSignature,
                value=emissionsSignature))

        if self._enableHeatOption.value():
            baseHeatGeneration = common.ScalarCalculation(
                value=self._baseHeatGenerationOption.value(),
                name='Specified Base Heat Generation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatGeneration,
                value=baseHeatGeneration))

            baseHeatDissipation = common.ScalarCalculation(
                value=self._baseHeatDissipationOption.value(),
                name='Specified Base Heat Dissipation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatDissipation,
                value=baseHeatDissipation))

            baseOverheatThreshold = common.ScalarCalculation(
                value=self._baseOverheatThresholdOption.value(),
                name='Specified Base Overheat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.OverheatThreshold,
                value=baseOverheatThreshold))

            baseDangerHeatThreshold = common.ScalarCalculation(
                value=self._baseDangerHeatThresholdOption.value(),
                name='Specified Base Danger Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DangerHeatThreshold,
                value=baseDangerHeatThreshold))

            baseDisasterHeaHeatThreshold = common.ScalarCalculation(
                value=self._baseDisasterHeatThresholdOption.value(),
                name='Specified Base Disaster Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DisasterHeatThreshold,
                value=baseDisasterHeaHeatThreshold))

        if self._sizeTrait:
            step.addFactor(factor=construction.SetAttributeFactor(attributeId=self._sizeTrait))

        return step

class SingleShotLauncherReceiver(LauncherReceiver):
    """
    From Field Catalogue p58
    - Base Capacity: 1
    - Traits: Bulky
    """

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseRange: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            baseWeight=baseWeight,
            baseCost=baseCost,
            baseRange=baseRange,
            baseCapacity=1,
            sizeTrait=gunsmith.WeaponAttribute.Bulky)

class LightSingleShotLauncherReceiver(SingleShotLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 8
    - Weight: 1.5kg
    - Cost: Cr200
    - Base Range: 200m
    - Base Capacity: 1
    - Traits: Bulky
    - Physical Signature: Normal (All Tube Launchers)
    - Quickdraw: -8 (All Tube Launchers)
    """
    # NOTE: The min TL of 8 is based on the fact cartridge launchers become available at TL 6 and mini grenades become
    # available two TLs after the standard variants (Field Catalogue p53)

    def __init__(self) -> None:
        super().__init__(
            componentString='Single Shot Launcher (Light Grenade)',
            minTechLevel=8,
            baseWeight=1.5,
            baseCost=200,
            baseRange=200)

class StandardSingleShotLauncherReceiver(SingleShotLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 6
    - Weight: 2kg
    - Cost: Cr300
    - Base Range: 300m
    - Base Capacity: 1
    - Trait: Bulky
    - Physical Signature: Normal (All launchers)
    - Quickdraw: -8 (All launchers)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Single Shot Launcher (Standard Grenade)',
            minTechLevel=6,
            baseWeight=2,
            baseCost=300,
            baseRange=300)

class SemiAutomaticLauncherReceiver(LauncherReceiver):
    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseRange: typing.Union[int, common.ScalarCalculation],
            baseCapacity: typing.Union[int, common.ScalarCalculation] = None,
            sizeTrait: typing.Optional[gunsmith.WeaponAttribute] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            baseWeight=baseWeight,
            baseCost=baseCost,
            baseRange=baseRange,
            baseCapacity=baseCapacity,
            sizeTrait=sizeTrait)

class LightSemiAutomaticLauncherReceiver(SemiAutomaticLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 8
    - Weight: 2.5kg
    - Cost: Cr400
    - Base Range: 200m
    - Base Capacity: 3
    - Trait: Bulky
    - Physical Signature: Normal (All launchers)
    - Quickdraw: -8 (All launchers)
    """
    # NOTE: The min TL of 8 is based on the fact cartridge launchers become available at TL 6 and mini grenades become
    # available two TLs after the standard variants (Field Catalogue p53)

    def __init__(self) -> None:
        super().__init__(
            componentString='Semi-Automatic Launcher (Light Grenade)',
            minTechLevel=8,
            baseWeight=2.5,
            baseCost=400,
            baseRange=200,
            baseCapacity=3,
            sizeTrait=gunsmith.WeaponAttribute.Bulky)

class StandardSemiAutomaticLauncherReceiver(SemiAutomaticLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 6
    - Weight: 3.5kg
    - Cost: Cr500
    - Base Range: 300m
    - Base Capacity: 3
    - Trait: Very Bulky
    - Physical Signature: Normal (All launchers)
    - Quickdraw: -8 (All launchers)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Semi-Automatic Launcher (Standard Grenade)',
            minTechLevel=6,
            baseWeight=3.5,
            baseCost=500,
            baseRange=300,
            baseCapacity=3,
            sizeTrait=gunsmith.WeaponAttribute.VeryBulky)

class SupportLauncherReceiver(LauncherReceiver):
    _BaseCapacityOptionDescription = \
        '<p>Specify the Base Ammunition Capacity for the weapon</p>' \
        '<p>The table on p58 of the Field Catalogue specifies the Base Ammunition ' \
        'Capacity for Support Launchers as Varies, I assume this is because they\'re ' \
        'generally belt fed. This allows you to specify the value you require.</p>' \
        'If you\'re creating a belt fed weapon you can specify a value of 1, for the single ' \
        'round that is loaded at any one time, then specify the belt capacity when selecting ' \
        'a belt magazine.<br>' \
        'If you\'re creating a weapon that\'s fed by some other kind of magazine, you can ' \
        'specify a base capacity that you agree with your Referee for this kind of weapon.</p>'

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseRange: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            baseWeight=baseWeight,
            baseCost=baseCost,
            baseRange=baseRange)

        self._baseCapacityOption = construction.IntegerComponentOption(
            id='Capacity',
            name='Base Capacity',
            value=1,
            minValue=1,
            description=SupportLauncherReceiver._BaseCapacityOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._baseCapacityOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        baseCapacity = common.ScalarCalculation(
            value=self._baseCapacityOption.value(),
            name='Specified Base Capacity')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
            value=baseCapacity))

        return step

class LightSupportLauncherReceiver(SupportLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 8
    - Weight: 10kg
    - Cost: Cr2000
    - Base Range: 200m
    - Base Capacity: Varies
    - Physical Signature: Normal (All launchers)
    - Quickdraw: -8 (All launchers)
    """
    # NOTE: The min TL of 8 is based on the fact cartridge launchers become available at TL 6 and
    # mini grenades become available two TLs after the standard variants (Field Catalogue p53)
    # NOTE: The rules have the base ammo capacity as 'Varies' for light and standard support
    # launchers (table on Field Catalogue p58) but doesn't give an indication of why that is or what
    # range it varies over. I suspect it's related to the fact the rules say these types of weapons
    # are generally belt fed (Field Catalogue p59). I've chosen to add an option so the user can
    # specify what the base capacity is.

    def __init__(self) -> None:
        super().__init__(
            componentString='Support Launcher (Light Grenade)',
            minTechLevel=8,
            baseWeight=10,
            baseCost=2000,
            baseRange=200)

class StandardSupportLauncherReceiver(SupportLauncherReceiver):
    """
    From Field Catalogue p58
    - Min TL: 6
    - Weight: 15kg
    - Cost: Cr2000
    - Base Range: 300m
    - Base Capacity: Varies
    - Physical Signature: Normal (All launchers)
    - Quickdraw: -8 (All launchers)
    """
    # NOTE: The rules have the base ammo capacity as 'Varies' for light and standard support
    # launchers (table on Field Catalogue p58) but doesn't give an indication of why that is
    # or what range it varies over. I suspect it's related to the fact the rules say these
    # types of weapons are generally belt fed (Field Catalogue p59). I've chosen to add an
    # option so the user can specify what the base capacity is.

    def __init__(self) -> None:
        super().__init__(
            componentString='Support Launcher (Standard Grenade)',
            minTechLevel=6,
            baseWeight=15,
            baseCost=2000,
            baseRange=300)


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

class _DirectedEnergyReceiverImpl(object):
    """
    Power Pack Weapons
    - Min TL: 8
    Energy Cartridge Weapons
    - Min TL: 9
    All Energy Weapons
    - Damage: Can be between 1 and max damage for receiver type
    - Power Per Shot: Equal to number of damage dice
    - Physical Signature: Normal
    - Emissions Signature: Normal
    - Base Penetration: -1
    - Trait: Zero-G
    - Requirement: Only compatible with energy weapons
    - Requirement: Base Quickdraw is only applied to Primary Weapons
    - Core Rules Compatible:
        - Base Penetration: 0
    """
    # NOTE: The min TL is based on the the fact power packs become available at TL 8, energy
    # cartridges aren't available until TL 9
    # NOTE: I can't find anything that explicitly gives the physical signature of a directed energy
    # weapon. The description of physical signature (Field Catalogue p7) says "All firearms and
    # energy weapons have at least some Physical Signature and in many cases this is about the same
    # as that of a typical handgun or rifle". IF we take "typical" to mean the mid range of those
    # calibres (i.e. Medium Handgun and Assault/Battle Rifle) then that would mean the signature is
    # Normal
    # NOTE: I can't find anything that explicitly gives the emissions signature fo a directed
    # energy weapon in the written rules, however the example laser pistol & rifle (Field Catalogue
    # p115-117) have a emissions signature of Normal
    # NOTE: I've added the requirement that the base Quickdraw is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # It's not obvious exactly what should be done for the base Quickdraw of a secondary weapon.
    # It seems wrong to include it as it would mean adding a secondary weapon with a handgun
    # receiver to a weapon that has a heavy receiver will result in the weapon as a whole having
    # a better Quickdraw than it did if it didn't have a secondary weapon. On the flip side it
    # seems wrong to not include it as you get the opposite case where adding a secondary weapon
    # with a heavy receiver to a weapon with a handgun receiver would not result in any change in
    # the Quickdraw of the weapon as a whole (other than the -1 per additional barrel).
    # I've decided the best approach is to not include it and leave it up to the referee to all
    # foul if a player tries to add a sniper rifle as a secondary weapon to a pistol.
    # NOTE: I can't figure out what the base ammo capacity of cartridge based energy weapons should
    # be so I've had to take it as a parameter.
    # NOTE: I've added options so the user can optionally specify base heat stats as the rules don't
    # make it clear what they'd be for a energy weapons but they do say they generate some.
    # NOTE: When the CoreRulesCompatibility rule is applied energy weapons have a base penetration
    # of 0  rather than -1. This is done so shotguns generated with the tool can be dropped into
    # games using the core rules without them being massively nerfed compared to the example energy
    # weapons from the other rule books (Core, Central Supply etc).

    _PowerPackWeaponMinTechLevel = 8
    _EnergyCartridgeWeaponMinTechLevel = 9
    _PhysicalSignature = gunsmith.Signature.Normal
    _EmissionsSignature = gunsmith.Signature.Normal
    _StandardPenetrationTrait = common.ScalarCalculation(
        value=-1,
        name='Directed Energy Weapon Receiver Base Penetration')
    _CoreRulesCompatibilityPenetrationTrait = common.ScalarCalculation(
        value=0,
        name='Directed Energy Weapon Receiver Base Penetration With Core Rules Compatibility Enabled')
    _BarrelCount = common.ScalarCalculation(
        value=1,
        name='Directed Energy Weapon Receiver Base Barrel Count')

    _BasePhysicalSignatureOptionDescription = \
        '<p>Specify the Base Physical Signature of the weapon.</p>' \
        '<p>On p7 of the Field Catalogue it says all firearms and energy weapons have at least ' \
        'some Physical Signature, however the rules don\'t specify what that is for a directed ' \
        'energy weapon. This allows you to specify a value that you agree with your Referee. It ' \
        'defaults to Normal as that seems the most obvious default.</p>' \
        '<p>It\'s worth noting that the examples on p114-117 have no Physical Signature. However that ' \
        'seems more likely to be an oversight when p7 says most energy weapons do have one.</p>'

    _BaseEmissionsSignatureOptionDescription = \
        '<p>Specify the Base Emissions Signature of the weapon.</p>' \
        '<p>Surprisingly the rules don\'t give a Base Emissions Signature for energy weapons. ' \
        'This allows you to specify a value you agree with your Referee. It defaults to Normal as ' \
        'the examples on p114-117 have a Normal Emissions Signature.</p>'

    def __init__(
            self,
            componentString: str,
            maxDamageDice: typing.Union[int, common.ScalarCalculation],
            baseWeight: typing.Union[int, float, common.ScalarCalculation],
            baseCost: typing.Union[int, float, common.ScalarCalculation],
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseQuickdraw: typing.Union[int, common.ScalarCalculation],
            ) -> None:
        super().__init__()

        if not isinstance(maxDamageDice, common.ScalarCalculation):
            maxDamageDice = common.ScalarCalculation(
                value=maxDamageDice,
                name=f'{componentString} Receiver Max Damage Dice')

        if not isinstance(baseWeight, common.ScalarCalculation):
            baseWeight = common.ScalarCalculation(
                value=baseWeight,
                name=f'{componentString} Receiver Base Weight')

        if not isinstance(baseCost, common.ScalarCalculation):
            baseCost = common.ScalarCalculation(
                value=baseCost,
                name=f'{componentString} Receiver Base Cost')

        if not isinstance(baseRange, common.ScalarCalculation):
            baseRange = common.ScalarCalculation(
                value=baseRange,
                name=f'{componentString} Receiver Base Range')

        if not isinstance(baseQuickdraw, common.ScalarCalculation):
            baseQuickdraw = common.ScalarCalculation(
                value=baseQuickdraw,
                name=f'{componentString} Receiver Base Quickdraw')

        self._componentString = componentString
        self._maxDamageDice = maxDamageDice
        self._baseWeight = baseWeight
        self._baseCost = baseCost
        self._baseRange = baseRange
        self._baseQuickdraw = baseQuickdraw

        self._baseDamageDiceOption = construction.IntegerComponentOption(
            id='DamageDice',
            name='Base Damage Dice',
            value=self._maxDamageDice.value(),
            minValue=1,
            maxValue=self._maxDamageDice.value(),
            description='Specify the Base Damage Dice for the weapon.')

        self._basePhysicalSignatureOption = construction.EnumComponentOption(
            id='PhysicalSignature',
            name='Base Physical Signature',
            type=gunsmith.Signature,
            value=gunsmith.Signature.Normal, # Default to normal as the rules suggest all weapon types have a physical signature
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=_DirectedEnergyReceiverImpl._BasePhysicalSignatureOptionDescription)

        self._baseEmissionsSignatureOption = construction.EnumComponentOption(
            id='EmissionsSignature',
            name='Base Emissions Signature',
            type=gunsmith.Signature,
            value=gunsmith.Signature.Normal, # Default to normal as all directed energy weapons have an emissions signature
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=_DirectedEnergyReceiverImpl._BaseEmissionsSignatureOptionDescription)

        self._enableHeatOption = construction.BooleanComponentOption(
            id='EnableBaseHeat',
            name='Specify Base Heat Values',
            value=False,
            description=_EnableBaseHeatOptionDescription)

        self._baseHeatDissipationOption = construction.IntegerComponentOption(
            id='HeatDissipation',
            name='Base Heat Dissipation',
            value=0,
            minValue=0,
            description=_BaseHeatDissipationOptionDescription)

        self._baseOverheatThresholdOption = construction.IntegerComponentOption(
            id='OverheatThreshold',
            name='Base Overheat Threshold',
            value=0,
            minValue=0,
            description=_BaseOverheatThresholdOptionDescription)

        self._baseDangerHeatThresholdOption = construction.IntegerComponentOption(
            id='DangerHeatThreshold',
            name='Base Danger Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDangerHeatThresholdOptionDescription)

        self._baseDisasterHeatThresholdOption = construction.IntegerComponentOption(
            id='DisasterHeatThreshold',
            name='Base Disaster Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDisasterHeatThresholdOptionDescription)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Receiver'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        weaponType = context.weaponType(sequence=sequence)
        if weaponType == gunsmith.WeaponType.PowerPackWeapon:
            return context.techLevel() >= _DirectedEnergyReceiverImpl._PowerPackWeaponMinTechLevel
        elif weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            return context.techLevel() >= _DirectedEnergyReceiverImpl._EnergyCartridgeWeaponMinTechLevel

        # Only compatible with energy weapons
        return False

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [
            self._baseDamageDiceOption,
            self._basePhysicalSignatureOption,
            self._baseEmissionsSignatureOption,
            self._enableHeatOption
            ]

        if self._enableHeatOption.value():
            options.extend([
                self._baseHeatDissipationOption,
                self._baseOverheatThresholdOption,
                self._baseDangerHeatThresholdOption,
                self._baseDisasterHeatThresholdOption])

        return options

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
            step: gunsmith.WeaponStep
            ) -> None:
        step.setWeight(weight=construction.ConstantModifier(value=self._baseWeight))
        step.setCredits(credits=construction.ConstantModifier(value=self._baseCost))

        damageDice = common.ScalarCalculation(
            value=self._baseDamageDiceOption.value(),
            name='Specified Receiver Damage Dice')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Damage,
            value=common.DiceRoll(
                count=damageDice,
                type=common.DieType.D6)))

        powerPerShot = common.Calculator.equals(
            value=damageDice,
            name=f'{self.componentString()} Receiver Power Per Shot')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.PowerPerShot,
            value=powerPerShot))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.MaxDamageDice,
            value=self._maxDamageDice))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Range,
            value=self._baseRange))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.BarrelCount,
            value=self._BarrelCount))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Quickdraw,
            value=self._baseQuickdraw if context.isPrimary(sequence=sequence) else _SecondaryWeaponBaseQuickdraw))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.ZeroG))

        basePenetration = \
            _DirectedEnergyReceiverImpl._CoreRulesCompatibilityPenetrationTrait \
            if context.isRuleEnabled(rule=gunsmith.RuleId.CoreRulesCompatible) else \
            _DirectedEnergyReceiverImpl._StandardPenetrationTrait
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Penetration,
            value=basePenetration))

        physicalSignature = self._basePhysicalSignatureOption.value()
        if physicalSignature:
            assert(isinstance(physicalSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.PhysicalSignature,
                value=physicalSignature))

        emissionsSignature = self._baseEmissionsSignatureOption.value()
        if emissionsSignature:
            assert(isinstance(emissionsSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.EmissionsSignature,
                value=emissionsSignature))

        if self._enableHeatOption.value():
            baseHeatDissipation = common.ScalarCalculation(
                value=self._baseHeatDissipationOption.value(),
                name='Specified Base Heat Dissipation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatDissipation,
                value=baseHeatDissipation))

            baseOverheatThreshold = common.ScalarCalculation(
                value=self._baseOverheatThresholdOption.value(),
                name='Specified Base Overheat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.OverheatThreshold,
                value=baseOverheatThreshold))

            baseDangerHeatThreshold = common.ScalarCalculation(
                value=self._baseDangerHeatThresholdOption.value(),
                name='Specified Base Danger Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DangerHeatThreshold,
                value=baseDangerHeatThreshold))

            baseDisasterHeaHeatThreshold = common.ScalarCalculation(
                value=self._baseDisasterHeatThresholdOption.value(),
                name='Specified Base Disaster Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DisasterHeatThreshold,
                value=baseDisasterHeaHeatThreshold))

class _MinimalDirectedEnergyReceiverImpl(_DirectedEnergyReceiverImpl):
    """
    - Base Weight: 0.5kg
    - Base Cost: Cr400
    - Base Range: 50m
    - Base Quickdraw: 4
    - Max Damage: 2D
    - Physical Signature: Normal (See note on base class)
    - Emissions Signature: Normal (See note on base class)
    - Trait: Zero-G
    - Trait: Penetration -1
    - Requirement: Only compatible with Energy Weapons
    """
    # NOTE: I can't find anything in the written rules that gives the base quickdraw for a directed
    # energy weapon receivers. The quickdraw of +4 is based on the example laser with a minimal
    # receiver (Field Catalogue p114)

    def __init__(self) -> None:
        super().__init__(
            componentString='Minimal',
            baseWeight=0.5,
            baseCost=400,
            baseRange=50,
            baseQuickdraw=4,
            maxDamageDice=2)

class _SmallDirectedEnergyReceiverImpl(_DirectedEnergyReceiverImpl):
    """
    - Base Weight: 1.5kg
    - Base Cost: Cr800
    - Base Range: 100m
    - Base Quickdraw: 4
    - Max Damage: 3D
    - Physical Signature: Normal (See note on base class)
    - Emissions Signature: Normal (See note on base class)
    - Trait: Zero-G
    - Trait: Penetration -1
    - Requirement: Only compatible with Energy Weapons
    """
    # NOTE: I can't find anything in the written rules that gives the base quickdraw for a directed
    # energy weapon receivers. The quickdraw of +4 is based on the example laser with a small
    # receiver (Field Catalogue p117)

    def __init__(self) -> None:
        super().__init__(
            componentString='Small',
            baseWeight=1.5,
            baseCost=800,
            baseRange=100,
            baseQuickdraw=4,
            maxDamageDice=3)

class _MediumDirectedEnergyReceiverImpl(_DirectedEnergyReceiverImpl):
    """
    - Base Weight: 3kg
    - Base Cost: Cr2500
    - Base Range: 200m
    - Base Quickdraw: 0
    - Max Damage: 5D
    - Physical Signature: Normal (See note on base class)
    - Emissions Signature: Normal (See note on base class)
    - Trait: Zero-G
    - Trait: Penetration -1
    - Requirement: Only compatible with Energy Weapons
    """
    # NOTE: I can't find anything in the written rules that gives the base quickdraw for a directed
    # energy weapon receivers. The quickdraw of +0 is based on the example laser with a medium
    # receiver (Field Catalogue p116)

    def __init__(self) -> None:
        super().__init__(
            componentString='Medium',
            baseWeight=3,
            baseCost=2500,
            baseRange=200,
            baseQuickdraw=0,
            maxDamageDice=5)

class _LargeDirectedEnergyReceiverImpl(_DirectedEnergyReceiverImpl):
    """
    - Base Weight: 8kg
    - Base Cost: Cr5000
    - Base Range: 500m
    - Base Quickdraw: -8
    - Max Damage: 8D
    - Physical Signature: Normal (See note on base class)
    - Emissions Signature: Normal (See note on base class)
    - Trait: Zero-G
    - Trait: Penetration -1
    - Requirement: Only compatible with Energy Weapons
    """
    # NOTE: I can't find anything in the written rules that gives the base quickdraw for a directed
    # energy weapon receivers. The quickdraw of -8 is based on the example laser with a large
    # receiver (Field Catalogue p146)

    def __init__(self) -> None:
        super().__init__(
            componentString='Large',
            baseWeight=8,
            baseCost=5000,
            baseRange=500,
            baseQuickdraw=-8,
            maxDamageDice=8)

class PowerPackReceiver(gunsmith.ReceiverInterface):
    def __init__(
            self,
            impl: _DirectedEnergyReceiverImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString() + ' Power Pack'

    def typeString(self) -> str:
        return self._impl.typeString()

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.weaponType(sequence=sequence) == gunsmith.WeaponType.PowerPackWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        return self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class MinimalPowerPackReceiver(PowerPackReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_MinimalDirectedEnergyReceiverImpl())

class SmallPowerPackReceiver(PowerPackReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_SmallDirectedEnergyReceiverImpl())

class MediumPowerPackReceiver(PowerPackReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_MediumDirectedEnergyReceiverImpl())

class LargePowerPackReceiver(PowerPackReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_LargeDirectedEnergyReceiverImpl())

class EnergyCartridgeReceiver(gunsmith.ReceiverInterface):
    _BaseCapacityOptionDescription = \
        '<p>Specify the Base Ammunition Capacity for the weapon</p>' \
        '<p>The Field Catalogue doesn\'t specify the Base Ammunition Capacity for ' \
        'energy cartridge weapons. This allows you to specify a value that you ' \
        'agree with you Referee.</p>'

    def __init__(
            self,
            impl: _DirectedEnergyReceiverImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._baseCapacityOption = construction.IntegerComponentOption(
            id='BaseCapacity',
            name='Base Capacity',
            value=1,
            minValue=1,
            description=EnergyCartridgeReceiver._BaseCapacityOptionDescription)

    def componentString(self) -> str:
        return self._impl.componentString() + ' Energy Cartridge'

    def typeString(self) -> str:
        return self._impl.typeString()

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.weaponType(sequence=sequence) == gunsmith.WeaponType.EnergyCartridgeWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._baseCapacityOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        return self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            step=step)

        baseCapacity = common.ScalarCalculation(
            value=self._baseCapacityOption.value(),
            name='Specified Receiver Base Capacity')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
            value=baseCapacity))

        context.applyStep(
            sequence=sequence,
            step=step)

class MinimalEnergyCartridgeReceiver(EnergyCartridgeReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_MinimalDirectedEnergyReceiverImpl())

class SmallEnergyCartridgeReceiver(EnergyCartridgeReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_SmallDirectedEnergyReceiverImpl())

class MediumEnergyCartridgeReceiver(EnergyCartridgeReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_MediumDirectedEnergyReceiverImpl())

class LargeEnergyCartridgeReceiver(EnergyCartridgeReceiver):
    def __init__(self) -> None:
        super().__init__(impl=_LargeDirectedEnergyReceiverImpl())


# ███████████                          ███                     █████
#░░███░░░░░███                        ░░░                     ░░███
# ░███    ░███ ████████   ██████      █████  ██████   ██████  ███████    ██████  ████████   █████
# ░██████████ ░░███░░███ ███░░███    ░░███  ███░░███ ███░░███░░░███░    ███░░███░░███░░███ ███░░
# ░███░░░░░░   ░███ ░░░ ░███ ░███     ░███ ░███████ ░███ ░░░   ░███    ░███ ░███ ░███ ░░░ ░░█████
# ░███         ░███     ░███ ░███     ░███ ░███░░░  ░███  ███  ░███ ███░███ ░███ ░███      ░░░░███
# █████        █████    ░░██████      ░███ ░░██████ ░░██████   ░░█████ ░░██████  █████     ██████
#░░░░░        ░░░░░      ░░░░░░       ░███  ░░░░░░   ░░░░░░     ░░░░░   ░░░░░░  ░░░░░     ░░░░░░
#                                 ███ ░███
#                                ░░██████
#                                 ░░░░░░

class ProjectorReceiver(gunsmith.ReceiverInterface):
    """
    - Min TL: 4
    - Trait: Hazardous -6
    - Note: DM-2 on all physical tasks for each additional multiple of the maximum payload weight
    - Requirement: Base Quickdraw is only applied to Primary Weapons
    """
    # NOTE: I can't find mention of what the base physical or emissions signature is for a projector.
    # The rules say all firearms and energy weapons have a physical signature. However there is no
    # such comment regarding the emissions signature. The description of the emissions signature trait
    # (Field Catalogue p6) gives flame and cryptogenic weapons as example of weapons that have an
    # emissions signature but not what it would be or if it applies to projectors using other fuel
    # types. As it's so unclear I've added options so the user can specify the value if they want to.
    # NOTE: I can't find anything in the Field Catalogue that explicitly gives the min TL of a
    # projector receivers. I've gone with TL 4 based on the Flamethrower from the Core Rules p124,
    # this is also whe the fuel for projectors starts to become available
    # NOTE: I've added the requirement that the base Quickdraw is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # It's not obvious exactly what should be done for the base Quickdraw of a secondary weapon.
    # It seems wrong to include it as it would mean adding a secondary weapon with a handgun
    # receiver to a weapon that has a heavy receiver will result in the weapon as a whole having
    # a better Quickdraw than it did if it didn't have a secondary weapon. On the flip side it
    # seems wrong to not include it as you get the opposite case where adding a secondary weapon
    # with a heavy receiver to a weapon with a handgun receiver would not result in any change in
    # the Quickdraw of the weapon as a whole (other than the -1 per additional barrel).
    # I've decided the best approach is to not include it and leave it up to the referee to all
    # foul if a player tries to add a sniper rifle as a secondary weapon to a pistol.
    # NOTE: The rules don't give details of heat generation/dissipation or malfunction thresholds
    # for projects. Unlike the other weapons types where this is the case I've not added options
    # fo the user to specify them. My thinking is that process of expelling compressed gas cools
    # the environment it so I don't think projectors would suffer from heat related failure in
    # the same way as other weapons.
    _MinTechLevel = 4
    _BarrelCount = common.ScalarCalculation(
        value=1,
        name='Projector Base Barrel Count')
    _HazardousTrait = common.ScalarCalculation(
        value=-6,
        name='Projector Base Hazardous Modifier')
    _UnwieldyModifier = common.ScalarCalculation(
        value=-2,
        name='Unwieldy Projector Physical Action Modifier')

    _BasePhysicalSignatureOptionDescription = \
        '<p>Specify the Base Physical Signature of the weapon.</p>' \
        '<p>On p7 of the Field Catalogue it says all firearms and energy weapons have at least ' \
        'some Physical Signature, however the rules don\'t specify what that is for a projected ' \
        'energy weapons. This allows you to specify a value that you agree with your Referee. It ' \
        'defaults to Normal as that seems the most obvious default.</p>' \
        '<p>It\'s worth noting that the examples on p111-113 have no Physical Signature. However that ' \
        'seems more likely to be an oversight when p7 says most energy weapons do have one.</p>'

    _BaseEmissionsSignatureOptionDescription = \
        '<p>Specify the Base Emissions Signature of the weapon.</p>' \
        '<p>The Field Catalogue doesn\'t specify a Base Emissions Signature for projected energy ' \
        'weapons. The Emissions Signature description on p6 does say flame and cryogenic weapons ' \
        'have one, which I assume would include flamethrowers and cryo projectors. However there\'s ' \
        'no indicate of a value or what other signature other types of projector would have. This ' \
        'allows you to specify a value you agree with your Referee. It defaults to Normal as that ' \
        'seems the most obvious default.</p>' \
        '<p>It\'s worth noting that the examples flamethrower on p111/112 has an Emissions Signature ' \
        'of Extreme, however the cryo projector on p112/113 has no Emissions Signature.</p>'

    def __init__(
            self,
            componentString: str,
            unwieldyThreshold: typing.Union[int, common.ScalarCalculation],
            payloadWeightPercentage: typing.Union[int, float, common.ScalarCalculation],
            costPerKg: typing.Union[int, float, common.ScalarCalculation],
            baseQuickdraw: typing.Union[int, common.ScalarCalculation],
            baseBlast: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__()

        if not isinstance(unwieldyThreshold, common.ScalarCalculation):
            unwieldyThreshold = common.ScalarCalculation(
                value=unwieldyThreshold,
                name=f'Payload Weight {componentString} Projector Becomes Unwieldy')

        if not isinstance(payloadWeightPercentage, common.ScalarCalculation):
            payloadWeightPercentage = common.ScalarCalculation(
                value=payloadWeightPercentage,
                name=f'{componentString} Structure Payload Weight Percentage')

        if not isinstance(costPerKg, common.ScalarCalculation):
            costPerKg = common.ScalarCalculation(
                value=costPerKg,
                name=f'{componentString} Structure Cost Per kg')

        if not isinstance(baseQuickdraw, common.ScalarCalculation):
            baseQuickdraw = common.ScalarCalculation(
                value=baseQuickdraw,
                name=f'{componentString} Structure Base Quickdraw Modifier')

        if not isinstance(baseBlast, common.ScalarCalculation):
            baseBlast = common.ScalarCalculation(
                value=baseBlast,
                name=f'{componentString} Structure Base Blast Modifier')

        self._componentString = componentString
        self._unwieldyThreshold = unwieldyThreshold
        self._payloadWeightPercentage = payloadWeightPercentage
        self._costPerKg = costPerKg
        self._baseQuickdraw = baseQuickdraw
        self._baseBlast = baseBlast

        self._fuelWeightOption = construction.FloatComponentOption(
            id='FuelWeight',
            name='Fuel Weight',
            value=1.0,
            minValue=0.1,
            description='Specify the weight of fuel the weapon can hold.')

        self._propellantWeightOption = construction.FloatComponentOption(
            id='PropellantWeight',
            name='Propellant Weight',
            value=1.0,
            minValue=0.1,
            description='Specify the weight of propellant the weapon can hold.')

        self._physicalSignatureOption = construction.EnumComponentOption(
            id='PhysicalSignature',
            name='Base Physical Signature',
            type=gunsmith.Signature,
            value=gunsmith.Signature.Normal, # Default to normal as the rules suggest all weapon types have a physical signature
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=ProjectorReceiver._BasePhysicalSignatureOptionDescription)

        self._emissionsSignatureOption = construction.EnumComponentOption(
            id='EmissionsSignature',
            name='Base Emissions Signature',
            type=gunsmith.Signature,
            value=gunsmith.Signature.Normal, # Default to normal as the rules suggest at least some types of projector have an emissions signature
            isOptional=True, # Allow it to be optional as the rules don't explicitly give values
            description=ProjectorReceiver._BaseEmissionsSignatureOptionDescription)

        self._enableHeatOption = construction.BooleanComponentOption(
            id='EnableBaseHeat',
            name='Specify Base Heat Values',
            value=False,
            description=_EnableBaseHeatOptionDescription)

        self._baseHeatGenerationOption = construction.IntegerComponentOption(
            id='HeatGeneration',
            name='Base Heat Per Attack',
            value=0,
            minValue=0,
            description=_BaseHeatGenerationOptionDescription)

        self._baseHeatDissipationOption = construction.IntegerComponentOption(
            id='HeatDissipation',
            name='Base Heat Dissipation',
            value=0,
            minValue=0,
            description=_BaseHeatDissipationOptionDescription)

        self._baseOverheatThresholdOption = construction.IntegerComponentOption(
            id='OverheatThreshold',
            name='Base Overheat Threshold',
            value=0,
            minValue=0,
            description=_BaseOverheatThresholdOptionDescription)

        self._baseDangerHeatThresholdOption = construction.IntegerComponentOption(
            id='DangerHeatThreshold',
            name='Base Danger Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDangerHeatThresholdOptionDescription)

        self._baseDisasterHeatThresholdOption = construction.IntegerComponentOption(
            id='DisasterHeatThreshold',
            name='Base Disaster Heat Threshold',
            value=0,
            minValue=0,
            description=_BaseDisasterHeatThresholdOptionDescription)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Structure'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._MinTechLevel:
            return False

        return context.weaponType(sequence=sequence) == gunsmith.WeaponType.ProjectorWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [
            self._fuelWeightOption,
            self._propellantWeightOption,
            self._physicalSignatureOption,
            self._emissionsSignatureOption,
            self._enableHeatOption
        ]

        if self._enableHeatOption.value():
            options.extend([
                self._baseHeatGenerationOption,
                self._baseHeatDissipationOption,
                self._baseOverheatThresholdOption,
                self._baseDangerHeatThresholdOption,
                self._baseDisasterHeatThresholdOption
            ])

        return options

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
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        propellantWeight = common.ScalarCalculation(
            value=self._propellantWeightOption.value(),
            name='Specified Propellant Weight')
        fuelWeight = common.ScalarCalculation(
            value=self._fuelWeightOption.value(),
            name='Specified Fuel Weight')

        payloadWeight = common.Calculator.add(
            lhs=propellantWeight,
            rhs=fuelWeight,
            name=f'{self.componentString()} Payload Weight')
        totalWeight = common.Calculator.applyPercentage(
            value=payloadWeight,
            percentage=self._payloadWeightPercentage,
            name=f'{self.componentString()} Structure Base Weight')
        step.setWeight(weight=construction.ConstantModifier(value=totalWeight))

        totalCost = common.Calculator.multiply(
            lhs=totalWeight,
            rhs=self._costPerKg,
            name=f'{self.componentString()} Structure Base Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.PropellantWeight,
            value=propellantWeight))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.FuelWeight,
            value=fuelWeight))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.BarrelCount,
            value=self._BarrelCount))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Quickdraw,
            value=self._baseQuickdraw if context.isPrimary(sequence=sequence) else _SecondaryWeaponBaseQuickdraw))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Blast,
            value=self._baseBlast))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Hazardous,
            value=self._HazardousTrait))

        physicalSignature = self._physicalSignatureOption.value()
        if physicalSignature:
            assert(isinstance(physicalSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.PhysicalSignature,
                value=physicalSignature))

        emissionsSignature = self._emissionsSignatureOption.value()
        if emissionsSignature:
            assert(isinstance(emissionsSignature, gunsmith.Signature))
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.EmissionsSignature,
                value=emissionsSignature))

        if self._enableHeatOption.value():
            baseHeatGeneration = common.ScalarCalculation(
                value=self._baseHeatGenerationOption.value(),
                name='Specified Base Heat Generation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatGeneration,
                value=baseHeatGeneration))

            baseHeatDissipation = common.ScalarCalculation(
                value=self._baseHeatDissipationOption.value(),
                name='Specified Base Heat Dissipation')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.HeatDissipation,
                value=baseHeatDissipation))

            baseOverheatThreshold = common.ScalarCalculation(
                value=self._baseOverheatThresholdOption.value(),
                name='Specified Base Overheat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.OverheatThreshold,
                value=baseOverheatThreshold))

            baseDangerHeatThreshold = common.ScalarCalculation(
                value=self._baseDangerHeatThresholdOption.value(),
                name='Specified Base Danger Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DangerHeatThreshold,
                value=baseDangerHeatThreshold))

            baseDisasterHeaHeatThreshold = common.ScalarCalculation(
                value=self._baseDisasterHeatThresholdOption.value(),
                name='Specified Base Disaster Heat Threshold')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.DisasterHeatThreshold,
                value=baseDisasterHeaHeatThreshold))

        loadWeight = propellantWeight.value() + fuelWeight.value()
        unwieldyMultiples = loadWeight // self._unwieldyThreshold.value()
        if unwieldyMultiples > 0:
            unwieldyModifier = unwieldyMultiples * self._UnwieldyModifier.value()
            step.addNote(
                note=f'DM{unwieldyModifier} on all physical tasks due to payload weight being over projector maximum')

        context.applyStep(
            sequence=sequence,
            step=step)

class LargeProjectorReceiver(ProjectorReceiver):
    """
    - Max Payload: 20kg
    - Weight: 30% of payload weight
    - Cost: Cr50 per kg of weapons total weight
    - Quickdraw: +2
    - Trait: Blast +3
    - Trait: Hazardous -6
    - Note: DM-2 on all physical tasks for each additional multiple of the maximum payload weight
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Large',
            unwieldyThreshold=20,
            payloadWeightPercentage=30,
            costPerKg=50,
            baseQuickdraw=2,
            baseBlast=3)

class CompactProjectorReceiver(ProjectorReceiver):
    """
    - Max Payload: 10kg before it becomes unwieldy
    - Weight: 20% of payload weight
    - Cost: Cr100 per Kg of weapons total weight
    - Quickdraw: 0
    - Trait: Blast +2
    - Trait: Hazardous -6
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Compact',
            unwieldyThreshold=10,
            payloadWeightPercentage=20,
            costPerKg=100,
            baseQuickdraw=0,
            baseBlast=2)

class HandProjectorReceiver(ProjectorReceiver):
    """
    - Max Payload: 2kg before it becomes unwieldy
    - Weight: 10% of payload weight
    - Cost: Cr25 per kg of weapons total weight
    - Quickdraw: +2
    - Trait: Blast +1
    - Trait: Hazardous -6
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Hand',
            unwieldyThreshold=2,
            payloadWeightPercentage=10,
            costPerKg=25,
            baseQuickdraw=2,
            baseBlast=1)
