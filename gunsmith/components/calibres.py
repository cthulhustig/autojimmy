import common
import construction
import gunsmith
import typing

class ConventionalCalibre(gunsmith.WeaponComponentInterface):
    """
    For Rocket Propelled
    - Receiver Weight: -50% (Field Catalog p38)
    - Barrel Weight: -50% (Field Catalog p38)
    - Base Range: 250m
    - Base Ammo Cost: x2 Standard Base Ammo Cost
    - Ammo Capacity: -40%
    - Physical Signature: Normal
    - Recoil: -4 (From list on Field Catalogue p32)
    - Penetration: 0 (From Field Catalogue p40)
    - Trait: Zero-G
    - Trait: Inaccurate (-1)
    - Note: Damage is 1D at ranges < 10m
    """
    # NOTE: I've assumed the rocket weight and ammo capacity modifiers is in addition to the calibre
    # specific weight and capacity modifiers. This seems like it must be the case as there are some
    # non-rocket calibres that cause a larger reduction than that (e.g. Anti-Material).
    # NOTE: Barrel weight reduction for rockets is handled in the Barrel code
    # NOTE: I'm making a couple of assumptions regarding recoil. I'm assuming rockets are classed as
    # near-zero recoil accelerators and that the modifier for them is applied on top of any modifier
    # for the receiver type, the later seems sensible as having it instead of the normal receiver
    # recoil value would mean gauss longarm and support weapons would actually have worse recoil than
    # the non-gauss version
    # NOTE: The rules state that rocket propelled ammo starts with a Penetration of 0 but it can be
    # increased with specialist ammo or design choices. I assume the specialist ammo is just AP/AAP
    # ammo but I'm not sure what the design choices are.
    _RocketReceiverWeightModifierPercentage = common.ScalarCalculation(
        value=-50,
        name='Rocket Calibre Base Range')
    _RocketBaseRange = common.ScalarCalculation(
        value=250,
        name='Rocket Calibre Base Range')
    _RocketBasePhysicalSignature = gunsmith.Signature.Normal
    _RocketBasePenetration = common.ScalarCalculation(
        value=0,
        name='Rocket Calibre Base Penetration')
    _RocketAmmoCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Rocket Calibre Ammo Cost Multiplier')
    _RocketCapacityModifierPercentage = common.ScalarCalculation(
        value=-40,
        name='Rocket Calibre Ammo Capacity Percentage Modifier')
    _RocketRecoilModifier = common.ScalarCalculation(
        value=-4,
        name='Rocket Calibre Recoil Modifier')
    _RocketInaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Rocket Calibre Inaccurate Modifier')
    _RocketNote = 'Damage is 1D at ranges < 10m'

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, float, common.ScalarCalculation] = 0,
            baseDamageConstant: typing.Union[int, float, common.ScalarCalculation] = 0,
            baseAmmoCost: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            basePhysicalSignature: gunsmith.Signature = gunsmith.Signature.Normal,
            basePenetration: typing.Union[int, float, common.ScalarCalculation] = None,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            recoilModifier: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__()

        if not isinstance(baseRange, common.ScalarCalculation):
            baseRange = common.ScalarCalculation(
                value=baseRange,
                name=f'{componentString} Calibre Range')

        if not isinstance(baseDamageDiceCount, common.ScalarCalculation):
            baseDamageDiceCount = common.ScalarCalculation(
                value=baseDamageDiceCount,
                name=f'{componentString} Calibre Damage Dice Count')

        if not isinstance(baseDamageConstant, common.ScalarCalculation):
            baseDamageConstant = common.ScalarCalculation(
                value=baseDamageConstant,
                name=f'{componentString} Calibre Damage Constant')

        if baseAmmoCost != None and not isinstance(baseAmmoCost, common.ScalarCalculation):
            baseAmmoCost = common.ScalarCalculation(
                value=baseAmmoCost,
                name=f'{componentString} Calibre Ammo Cost Per 100 Rounds')

        if basePenetration != None and not isinstance(basePenetration, common.ScalarCalculation):
            basePenetration = common.ScalarCalculation(
                value=basePenetration,
                name=f'{componentString} Calibre Penetration')

        if weightModifierPercentage != None and not isinstance(weightModifierPercentage, common.ScalarCalculation):
            weightModifierPercentage = common.ScalarCalculation(
                value=weightModifierPercentage,
                name=f'{componentString} Calibre Receiver Weight Modifier Percentage')

        if costModifierPercentage != None and not isinstance(costModifierPercentage, common.ScalarCalculation):
            costModifierPercentage = common.ScalarCalculation(
                value=costModifierPercentage,
                name=f'{componentString} Calibre Receiver Cost Modifier Percentage')

        if capacityModifierPercentage != None and not isinstance(capacityModifierPercentage, common.ScalarCalculation):
            capacityModifierPercentage = common.ScalarCalculation(
                value=capacityModifierPercentage,
                name=f'{componentString} Calibre Ammo Capacity Modifier Percentage')

        if recoilModifier != None and not isinstance(recoilModifier, common.ScalarCalculation):
            recoilModifier = common.ScalarCalculation(
                value=recoilModifier,
                name=f'{componentString} Calibre Recoil Modifier')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._baseRange = baseRange
        self._baseAmmoCost = baseAmmoCost
        self._baseDamageDiceCount = baseDamageDiceCount
        self._baseDamageConstant = baseDamageConstant
        self._basePenetration = basePenetration
        self._basePhysicalSignature = basePhysicalSignature
        self._weightModifierPercentage = weightModifierPercentage
        self._costModifierPercentage = costModifierPercentage
        self._capacityModifierPercentage = capacityModifierPercentage
        self._recoilModifier = recoilModifier

        self._isRocketOption = construction.BooleanOption(
            id='Rocket',
            name='Rocket Accelerated',
            value=False,
            description='Specify if the weapon fires rocket accelerated ammunition.')
        
    def isHighVelocity(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ConventionalCalibre so must implement isHighVelocity') 

    def isRocket(self) -> bool:
        return self._isRocketOption.value()

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        instanceString = self.componentString()
        if self._isRocketOption.value():
            instanceString += ' (Rocket)'
        return instanceString

    def typeString(self) -> str:
        return 'Calibre'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel:
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._isRocketOption]

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        #
        # Basic Step
        #

        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

        #
        # Rocket Step
        #

        if not self.isRocket():
            return # Nothing more to do

        step = gunsmith.WeaponStep(
            name='Rocket Propelled Modification',
            type=self.typeString())

        step.setWeight(weight=construction.PercentageModifier(
            value=self._RocketReceiverWeightModifierPercentage))

        # Override the range and physical signature rather than modifying them as the rules
        # gives absolute value rather than a number of modification levels
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Range,
            value=self._RocketBaseRange))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
            value=self._RocketBasePhysicalSignature))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Penetration,
            value=self._RocketBasePenetration))

        # Modify existing weapon attributes
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=self._RocketCapacityModifierPercentage,
                roundDown=True)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCost,
            modifier=construction.MultiplierModifier(
                value=self._RocketAmmoCostMultiplier)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Recoil,
            modifier=construction.ConstantModifier(
                value=self._RocketRecoilModifier)))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.ZeroG))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._RocketInaccurateModifier)))

        step.addNote(note=self._RocketNote)

        context.applyStep(
            sequence=sequence,
            step=step)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = gunsmith.WeaponStep(
            name=self.componentString(), # Use base name as we don't want Rocket included, that's a separate step
            type=self.typeString())

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Range,
            value=self._baseRange))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Damage,
            value=common.DiceRoll(
                count=self._baseDamageDiceCount,
                type=common.DieType.D6,
                constant=self._baseDamageConstant)))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
            value=self._basePhysicalSignature))

        if self._baseAmmoCost:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCost,
                value=self._baseAmmoCost))

        if self._basePenetration:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Penetration,
                value=self._basePenetration))

        if self._weightModifierPercentage:
            step.setWeight(weight=construction.PercentageModifier(
                value=self._weightModifierPercentage))

        if self._costModifierPercentage:
            step.setCredits(credits=construction.PercentageModifier(
                value=self._costModifierPercentage))

        if self._capacityModifierPercentage:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
                modifier=construction.PercentageModifier(
                    value=self._capacityModifierPercentage,
                    roundDown=True)))

        if self._recoilModifier:
            recoilModifier = common.Calculator.add(
                lhs=self._baseDamageDiceCount,
                rhs=self._recoilModifier,
                name=f'{self.componentString()} Calibre Recoil Modifier')
        else:
            recoilModifier = common.Calculator.equals(
                value=self._baseDamageDiceCount,
                name=f'{self.componentString()} Calibre Recoil Modifier')
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Recoil,
            modifier=construction.ConstantModifier(
                value=recoilModifier)))

        return step

class HandgunCalibre(ConventionalCalibre):
    """
    Min TL: 5
    Penetration: 0 (For all handgun calibres)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # calibres become available. I've gone with TL 5 as that's the min TL for a Revolver in the Core
    # Rules p118

    def __init__(
            self,
            componentString: str,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseAmmoCost: typing.Union[int, float, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, common.ScalarCalculation] = 0,
            baseDamageConstant: typing.Union[int, common.ScalarCalculation] = 0,
            basePhysicalSignature: gunsmith.Signature = gunsmith.Signature.Normal,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__(
            minTechLevel=5,
            basePenetration=0,
            componentString=componentString,
            baseRange=baseRange,
            baseAmmoCost=baseAmmoCost,
            baseDamageDiceCount=baseDamageDiceCount,
            baseDamageConstant=baseDamageConstant,
            basePhysicalSignature=basePhysicalSignature,
            weightModifierPercentage=weightModifierPercentage,
            costModifierPercentage=costModifierPercentage,
            capacityModifierPercentage=capacityModifierPercentage)

    def isHighVelocity(self) -> bool:
        return False

class LightHandgunCalibre(HandgunCalibre):
    """
    - Receiver Cost: -20%
    - Receiver Weight: -25%
    - Ammo Capacity: +20%
    - Base Damage: 2D
    - Base Range: 40m
    - Base Ammo Cost: Cr60 per 100 rounds
    - Physical Signature: Low
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Light Handgun',
            baseRange=40,
            baseAmmoCost=60,
            baseDamageDiceCount=2,
            basePhysicalSignature=gunsmith.Signature.Low,
            weightModifierPercentage=-25,
            costModifierPercentage=-20,
            capacityModifierPercentage=+20)

class MediumHandgunCalibre(HandgunCalibre):
    """
    - Base Damage: 3D-3
    - Base Range: 50m
    - Base Ammo Cost: Cr75 per 100 rounds
    - Physical Signature: Normal
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Medium Handgun',
            baseRange=50,
            baseAmmoCost=75,
            baseDamageDiceCount=3,
            baseDamageConstant=-3)

class HeavyHandgunCalibre(HandgunCalibre):
    """
    - Receiver Cost: +20%
    - Receiver Weight: +15% (rules actually say -15% but I think that's a typo, see note)
    - Ammo Capacity: -20%
    - Base Damage: 3D-1
    - Base Range: 60m
    - Base Ammo Cost: Cr100 per 100 rounds
    - Physical Signature: Normal
    - Trait: Bulky (see note)
    """
    # NOTE: The wording rules say the following regarding the Bulky trait
    # "Heavy handguns gain the Bulky trait. Larger weapons using heavy handgun ammunition are Bulky
    # unless they weigh more than 2kg or are compensated in some manner."
    # This is handled in finalisation as it needs to know the final weapon weight. In theory the
    # handgun part could be handled here but I've chosen to keep the logic all in one place.
    # NOTE: I suspect the receiver weight modifier should be +15% rather than -15%. The rules say
    # -15% (Field Catalogue p36) but the example weapons (e.g. Field Catalogue p83) has +15%. It
    # being +15% would also be consistent with the rules for the other "heavy" calibres.

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy Handgun',
            baseRange=60,
            baseDamageDiceCount=3,
            baseDamageConstant=-1,
            baseAmmoCost=100,
            basePhysicalSignature=gunsmith.Signature.Normal,
            weightModifierPercentage=+15,
            costModifierPercentage=+20,
            capacityModifierPercentage=-20)

class SmoothboreCalibre(ConventionalCalibre):
    """
    - Min TL: 4
    - Receiver Cost: -25% (for all Smoothbore Calibres, Field Catalogue p37)
    - Base Range: 1/4 for pellet ammo
    - Base Penetration: -1 (for all Smoothbore Calibres, Field Catalogue p39)
    - Base Capacity: (Longarm=10, Assault=6, Handgun=4) + (Smoothbore size modifier) (Field Catalogue p36)
    - Physical Signature: High (Field Catalogue p39)
    - Trait: Inaccurate (-2) (Field Catalogue p39)
    - Core Rules Compatible:
        - Base Penetration: 0
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # calibres become available. I've gone with TL 4 as that's the min TL for a Shotgun in the Core
    # Rules p118
    # NOTE: There is a conflict in the Field Catalogue around the Inaccurate trait and Physical
    # Signature of Smoothbore calibres. The table on p39 has Inaccurate (-2) and Physical(high) for
    # all Smoothbore calibres however the example Shotgun on p70 only has Inaccurate (-1) and
    # Physical (normal). I've gone with the value in the table.
    # NOTE: In the smoothbore description where it gives the base capacities for longarm, assault
    # and handgun receivers (Field Catalogue p36), it doesn't mention light support or support
    # receivers so I've just left them using the capacity specified by the receiver
    # NOTE: When the CoreRulesCompatibility rule is applied smoothbore calibres have a base
    # penetration of 0 rather than -1. This is done so shotguns generated with the tool can be
    # dropped into games using the core rules without them being massively nerfed compared to the
    # example shotguns from the other rule books (Core, Central Supply etc).

    _SmoothboreStandardBasePenetration = common.ScalarCalculation(
        value=-1,
        name='Smoothbore Calibre Base Penetration')
    _SmoothboreCoreRulesCompatibilityBasePenetration = common.ScalarCalculation(
        value=0,
        name='Smoothbore Calibre Base Penetration With Core Rules Compatibility Enabled')

    _SmoothboreLongarmAmmoCapacity = common.ScalarCalculation(
        value=10,
        name='Smoothbore Calibre Longarm Ammo Capacity')
    _SmoothboreAssaultAmmoCapacity = common.ScalarCalculation(
        value=6,
        name='Smoothbore Calibre Assault Ammo Capacity')
    _SmoothboreHandgunAmmoCapacity = common.ScalarCalculation(
        value=4,
        name='Smoothbore Calibre Handgun Ammo Capacity')
    _SmoothboreInaccurateModifier = common.ScalarCalculation(
        value=-2,
        name='Smoothbore Calibre Inaccurate Modifier')
    _SmoothboreNote = 'Range is 1/4 for pellet ammo'

    def __init__(
            self,
            componentString: str,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseAmmoCost: typing.Union[int, float, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, common.ScalarCalculation] = 0,
            baseDamageConstant: typing.Union[int, common.ScalarCalculation] = 0,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__(
            minTechLevel=4,
            basePenetration=None, # SmoothboreCalibre handles its own base penetration
            basePhysicalSignature=gunsmith.Signature.High,
            costModifierPercentage=-25,
            capacityModifierPercentage=None, # SmoothboreCalibre handles its own ammo capacity
            componentString=componentString,
            baseRange=baseRange,
            baseAmmoCost=baseAmmoCost,
            baseDamageDiceCount=baseDamageDiceCount,
            baseDamageConstant=baseDamageConstant,
            weightModifierPercentage=weightModifierPercentage)

        if capacityModifierPercentage != None and not isinstance(capacityModifierPercentage, common.ScalarCalculation):
            capacityModifierPercentage = common.ScalarCalculation(
                value=capacityModifierPercentage,
                name=f'{componentString} Ammo Capacity Percentage ')

        # IMPORTANT: Don't use base classes _capacityModifierPercentage as it will cause base class
        # to generate the capacity modifier which will then be applied to the pre-modified capacity.
        self._smoothboreCapacityModifierPercentage = capacityModifierPercentage

    def isHighVelocity(self) -> bool:
        return False

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        basePenetration = \
            SmoothboreCalibre._SmoothboreCoreRulesCompatibilityBasePenetration \
            if context.isRuleEnabled(rule=gunsmith.RuleId.CoreRulesCompatible) else \
            SmoothboreCalibre._SmoothboreStandardBasePenetration
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Penetration,
            value=basePenetration))

        capacityOverride = None
        if context.hasComponent(
                componentType=gunsmith.LongarmReceiver,
                sequence=sequence):
            capacityOverride = self._SmoothboreLongarmAmmoCapacity
        elif context.hasComponent(
                componentType=gunsmith.AssaultReceiver,
                sequence=sequence):
            capacityOverride = self._SmoothboreAssaultAmmoCapacity
        elif context.hasComponent(
                componentType=gunsmith.HandgunReceiver,
                sequence=sequence):
            capacityOverride = self._SmoothboreHandgunAmmoCapacity

        if capacityOverride:
            # Override the current ammo capacity with the one for this type of smoothbore
            if self._smoothboreCapacityModifierPercentage:
                capacityOverride = common.Calculator.floor(
                    value=common.Calculator.applyPercentage(
                        value=capacityOverride,
                        percentage=self._smoothboreCapacityModifierPercentage),
                    name=f'{self.componentString()} Calibre Ammo Capacity')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
                value=capacityOverride))
        elif self._smoothboreCapacityModifierPercentage:
            # No capacity override so just modify the existing capacity
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
                modifier=construction.PercentageModifier(
                    value=self._smoothboreCapacityModifierPercentage,
                    roundDown=True)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._SmoothboreInaccurateModifier)))

        step.addNote(note=self._SmoothboreNote)

        return step

class SmallSmoothboreCalibre(SmoothboreCalibre):
    """
    - Receiver Weight: -40% (Field Catalogue p39)
    - Receiver Cost: -25% (for all Smoothbore Calibres, Field Catalogue p37)
    - Ammo Capacity: +40% (Field Catalogue p37)
    - Base Damage: 3D-2 (Field Catalogue p39)
    - Base Range: 60m/15m for Pellet ammo (Field Catalogue p39)
    - Base Ammo Cost: Cr100 per 100 rounds (Field Catalogue p39)
    - Base Penetration: -1 (for all Smoothbore Calibres, Field Catalogue p39)
    - Physical Signature: High (Field Catalogue p39)
    - Trait: Inaccurate (-2) (Field Catalogue p39)
    - Trait: Bulky when used in Handgun Receiver (Field Catalogue p36)
    """
    # NOTE: The Pellet ammo range is being handled as a trait (added by the base class). It's 1/4
    # range for all Smoothbore calibres

    def __init__(self) -> None:
        super().__init__(
            componentString='Small Smoothbore',
            baseRange=60,
            baseDamageDiceCount=3,
            baseDamageConstant=-2,
            baseAmmoCost=100,
            weightModifierPercentage=-40,
            capacityModifierPercentage=+40)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        if context.hasComponent(
                componentType=gunsmith.HandgunReceiver,
                sequence=sequence):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Bulky))

        return step

class LightSmoothboreCalibre(SmoothboreCalibre):
    """
    - Receiver Weight: -20% (Field Catalogue p39)
    - Receiver Cost: -25% (for all Smoothbore Calibres, Field Catalogue p37)
    - Ammo Capacity: +20% (Field Catalogue p39)
    - Base Damage: 4D-4 (Field Catalogue p39)
    - Base Range: 80m/20m for Pellet ammo (Field Catalogue p39)
    - Base Ammo Cost: Cr125 per 100 rounds
    - Base Penetration: -1 (for all Smoothbore Calibres, Field Catalogue p39)
    - Physical Signature: High (Field Catalogue p39)
    - Trait: Inaccurate (-2) (Field Catalogue p39)
    - Trait: Very Bulky when used in Handgun Receiver (Field Catalogue p36)
    - Trait: Bulky when used in Assault Weapon Receiver (Field Catalogue p36)
    """
    # NOTE: The Pellet ammo range is being handled as a trait (added by the base class). It's 1/4
    # range for all Smoothbore calibres

    def __init__(self) -> None:
        super().__init__(
            componentString='Light Smoothbore',
            baseRange=80,
            baseDamageDiceCount=4,
            baseDamageConstant=-4,
            baseAmmoCost=125,
            weightModifierPercentage=-20,
            capacityModifierPercentage=+20)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence calibre is part of
        assert(receiver) # Construction order should prevent this
        if isinstance(receiver, gunsmith.HandgunReceiver):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.VeryBulky))
        elif isinstance(receiver, gunsmith.AssaultReceiver):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Bulky))

        return step

class StandardSmoothboreCalibre(SmoothboreCalibre):
    """
    - Receiver Cost: -25% (for all Smoothbore Calibres, Field Catalogue p37)
    - Base Damage: 4D  (Field Catalogue p39)
    - Base Range: 100m/25m for Pellet ammo (Field Catalogue p39)
    - Base Ammo Cost: Cr150 per 100 rounds (Field Catalogue p39)
    - Base Penetration: -1 (for all Smoothbore Calibres, Field Catalogue p39)
    - Physical Signature: High (Field Catalogue p39)
    - Trait: Inaccurate (-2) (Field Catalogue p39)
    - Trait: Very Bulky when used in Assault Weapon Receiver (Field Catalogue p36)
    - Trait: Bulky when used in Longarm Receiver (Field Catalogue p36)
    - Requirement: Not compatible with Handgun Receiver (Field Catalogue p36)
    """
    # NOTE: The Pellet ammo range is being handled as a trait (added by the base class). It's 1/4
    # range for all Smoothbore calibres

    def __init__(self) -> None:
        super().__init__(
            componentString='Standard Smoothbore',
            baseRange=100,
            baseDamageDiceCount=4,
            baseAmmoCost=150)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.HandgunReceiver,
            sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence calibre is part of
        assert(receiver) # Construction order should prevent this
        if isinstance(receiver, gunsmith.AssaultReceiver):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.VeryBulky))
        elif isinstance(receiver, gunsmith.LongarmReceiver):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Bulky))

        return step

class HeavySmoothboreCalibre(SmoothboreCalibre):
    """
    - Receiver Weight: +20%  (Field Catalogue p39)
    - Receiver Cost: -25% (for all Smoothbore Calibres, Field Catalogue p37)
    - Ammo Capacity: -20%  (Field Catalogue p39)
    - Base Damage: 4D+4  (Field Catalogue p39)
    - Base Range: 120m/30m for Pellet ammo (Field Catalogue p39)
    - Base Ammo Cost: Cr175 per 100 rounds (Field Catalogue p39)
    - Base Penetration: -1 (for all Smoothbore Calibres, Field Catalogue p39)
    - Physical Signature: High (Field Catalogue p39)
    - Trait: Inaccurate (-2) (Field Catalogue p39)
    - Trait: Very Bulky when used in Longarm Receiver (Field Catalogue p36)
    - Requirement: Not compatible with Handgun Receiver (Field Catalogue p36)
    - Requirement: Not compatible with Assault Weapon Receiver (Field Catalogue p36)
    """
    # NOTE: The Pellet ammo range is being handled as a trait (added by the base class). It's 1/4
    # range for all Smoothbore calibres

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy Smoothbore',
            baseRange=120,
            baseDamageDiceCount=4,
            baseDamageConstant=4,
            baseAmmoCost=175,
            weightModifierPercentage=+20,
            capacityModifierPercentage=-20)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence calibre is part of
        if not receiver:
            return False
        return not isinstance(receiver, gunsmith.HandgunReceiver) and \
            not isinstance(receiver, gunsmith.AssaultReceiver)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        if context.hasComponent(
                componentType=gunsmith.LongarmReceiver,
                sequence=sequence):
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.VeryBulky))

        return step

class RifleCalibre(ConventionalCalibre):
    """
    Min TL: 5
    Base Penetration: 0 (For all rifle calibres)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # calibres become available. I've gone with TL 5 as that's the min TL for a Rifle in the Core
    # Rules p118

    def __init__(
            self,
            componentString: str,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseAmmoCost: typing.Union[int, float, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, common.ScalarCalculation] = 0,
            baseDamageConstant: typing.Union[int, common.ScalarCalculation] = 0,
            basePhysicalSignature: gunsmith.Signature = gunsmith.Signature.Normal,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__(
            minTechLevel=5,
            basePenetration=0,
            componentString=componentString,
            baseRange=baseRange,
            baseAmmoCost=baseAmmoCost,
            baseDamageDiceCount=baseDamageDiceCount,
            baseDamageConstant=baseDamageConstant,
            basePhysicalSignature=basePhysicalSignature,
            weightModifierPercentage=weightModifierPercentage,
            costModifierPercentage=costModifierPercentage,
            capacityModifierPercentage=capacityModifierPercentage)

    def isHighVelocity(self) -> bool:
        return True

class LightRifleCalibre(RifleCalibre):
    """
    - Receiver Weight: -40%
    - Ammo Capacity: +20%
    - Base Damage: 2D
    - Base Range: 150m
    - Base Ammo Cost: Cr40 per 100 rounds
    - Physical Signature: Low
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Light Rifle',
            baseRange=150,
            baseDamageDiceCount=2,
            baseAmmoCost=40,
            basePhysicalSignature=gunsmith.Signature.Low,
            weightModifierPercentage=-40,
            capacityModifierPercentage=+20)

class IntermediateRifleCalibre(RifleCalibre):
    """
    - Receiver Weight: -20%
    - Base Damage: 3D
    - Base Range: 250m
    - Base Ammo Cost: Cr50 per 100 rounds
    - Physical Signature: Normal
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Intermediate Rifle',
            baseRange=250,
            baseDamageDiceCount=3,
            baseAmmoCost=50,
            weightModifierPercentage=-20)

class BattleRifleCalibre(RifleCalibre):
    """
    - Ammo Capacity: -20%
    - Base Damage: 3D+3
    - Base Range: 300m
    - Base Ammo Cost: Cr100 per 100 rounds
    - Physical Signature: Normal
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Battle Rifle',
            baseRange=300,
            baseDamageDiceCount=3,
            baseDamageConstant=3,
            baseAmmoCost=100,
            capacityModifierPercentage=-20)

class HeavyRifleCalibre(RifleCalibre):
    """
    - Receiver Cost: +25%
    - Receiver Weight: +10%
    - Ammo Capacity: -40%
    - Base Damage: 4D
    - Base Range: 400m
    - Base Ammo Cost: Cr250 per 100 rounds
    - Physical Signature: High
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy Rifle',
            baseRange=400,
            baseDamageDiceCount=4,
            baseAmmoCost=250,
            basePhysicalSignature=gunsmith.Signature.High,
            weightModifierPercentage=+10,
            costModifierPercentage=+25,
            capacityModifierPercentage=-40)

class AntiMaterialRifleCalibre(RifleCalibre):
    """
    - Receiver Cost: +150%
    - Receiver Weight: +50%
    - Ammo Capacity: -60%
    - Base Damage: 5D
    - Base Range: 1000m
    - Base Ammo Cost: Cr1500 per 100 rounds
    - Physical Signature: Extreme
    - Trait: Bulky
    - Requirement: Requires Light Support Weapon or Heavy Weapon Receiver
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Anti-Material Rifle',
            baseRange=1000,
            baseDamageDiceCount=5,
            baseAmmoCost=1500,
            basePhysicalSignature=gunsmith.Signature.Extreme,
            weightModifierPercentage=+50,
            costModifierPercentage=+150,
            capacityModifierPercentage=-60)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence calibre is part of
        if not receiver:
            return False
        return isinstance(receiver, gunsmith.LightSupportReceiver) or \
            isinstance(receiver, gunsmith.HeavyWeaponReceiver)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Bulky))

        return step

class HeavyAntiMaterialRifleCalibre(RifleCalibre):
    """
    - Receiver Cost: +250%
    - Receiver Weight: +100%
    - Ammo Capacity: -80%
    - Base Damage: 6D
    - Base Range: 1200m
    - Base Ammo Cost: Cr3000 per 100 rounds
    - Physical Signature: Extreme
    - Trait: Very Bulky
    - Requirement: Requires Light Support Weapon or Heavy Weapon Receiver
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy Anti-Material Rifle',
            baseRange=1200,
            baseDamageDiceCount=6,
            baseAmmoCost=3000,
            basePhysicalSignature=gunsmith.Signature.Extreme,
            weightModifierPercentage=+100,
            costModifierPercentage=+250,
            capacityModifierPercentage=-80)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        receiver = context.findFirstComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence) # Only interested in receiver from sequence calibre is part of
        if not receiver:
            return False
        return isinstance(receiver, gunsmith.LightSupportReceiver) or \
            isinstance(receiver, gunsmith.HeavyWeaponReceiver)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.VeryBulky))

        return step

class ArchaicCalibre(ConventionalCalibre):
    """
    - Min TL: 3
    - Base Penetration: -2
    - Trait: Unreliable (2)
    - Trait: Inaccurate (-1)
    - Physical Signature: Very High (can't be reduced)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # calibres become available. I've gone with TL 3 as that's the min TL for a Antique weapons in
    # the Core Rules p118
    # NOTE: The description for Archaic Weapons (Field Catalogue p38) says most have the Inaccurate
    # trait but the table of calibres (p39) doesn't mention it. I've gone with a value of 1 based on
    # the value given for the example Archaic Rifle (p72)
    # NOTE: Enforcing that the Physical Signature can't be reduced is handled by components that
    # modify the Physical Signature
    _ArchaicCalibreUnreliableModifier = common.ScalarCalculation(
        value=2,
        name='Archaic Calibre Unreliable Modifier')
    _ArchaicCalibreInaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Archaic Calibre Inaccurate Modifier')
    _ArchaicCalibreNote = 'Physical Signature can\'t be reduced'

    def __init__(
            self,
            componentString: str,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseAmmoCost: typing.Union[int, float, common.ScalarCalculation],
            slowLoaderModifier: typing.Union[int, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, common.ScalarCalculation] = 0,
            baseDamageConstant: typing.Union[int, common.ScalarCalculation] = 0,
            weightModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__(
            minTechLevel=3,
            basePenetration=-2,
            basePhysicalSignature=gunsmith.Signature.VeryHigh,
            componentString=componentString,
            baseRange=baseRange,
            baseAmmoCost=baseAmmoCost,
            baseDamageDiceCount=baseDamageDiceCount,
            baseDamageConstant=baseDamageConstant,
            weightModifierPercentage=weightModifierPercentage,
            costModifierPercentage=costModifierPercentage,
            capacityModifierPercentage=capacityModifierPercentage)

        if not isinstance(slowLoaderModifier, common.ScalarCalculation):
            slowLoaderModifier = common.ScalarCalculation(
                value=slowLoaderModifier,
                name=f'{componentString} Slow Loader Modifier')

        self._slowLoaderModifier = slowLoaderModifier

    def isHighVelocity(self) -> bool:
        return False

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.SlowLoader,
            modifier=construction.ConstantModifier(value=self._slowLoaderModifier)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Unreliable,
            modifier=construction.ConstantModifier(value=self._ArchaicCalibreUnreliableModifier)))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(value=self._ArchaicCalibreInaccurateModifier)))

        return step

class ArchaicPistolCalibre(ArchaicCalibre):
    """
    - Base Damage: 2D-3
    - Base Range: 20m
    - Base Ammo Cost: Cr10 per 100 rounds
    - Base Penetration: -2
    - Trait: Slow Loader (6)
    - Trait: Unreliable (2)
    - Trait: Inaccurate (-1)
    - Physical Signature: Very High (can't be reduced)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Archaic Pistol',
            baseRange=20,
            baseDamageDiceCount=2,
            baseDamageConstant=-3,
            baseAmmoCost=10,
            slowLoaderModifier=6)

class ArchaicSmoothboreCalibre(ArchaicCalibre):
    """
    - Base Damage: 3D-3
    - Base Range: 40m (10m for Pellet ammo)
    - Base Ammo Cost: Cr25 per 100 rounds
    - Base Penetration: -2
    - Trait: Slow Loader (8)
    - Trait: Unreliable (2)
    - Trait: Inaccurate (-1)
    - Physical Signature: Very High (can't be reduced)
    """
    _ArchaicSmoothboreNote = 'Range is 1/4 when firing pellet ammo'

    def __init__(self) -> None:
        super().__init__(
            componentString='Archaic Smoothbore',
            baseRange=40,
            baseDamageDiceCount=3,
            baseDamageConstant=-3,
            baseAmmoCost=25,
            slowLoaderModifier=8)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._ArchaicSmoothboreNote)
        return step

class ArchaicRifleCalibre(ArchaicCalibre):
    """
    - Base Damage: 3D-3
    - Base Range: 150m
    - Base Ammo Cost: Cr25 per 100 rounds
    - Penetration: -2
    - Trait: Slow Loader (12)
    - Trait: Unreliable (2)
    - Trait: Inaccurate (1)
    - Physical Signature: Very High (can't be reduced)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Archaic Rifle',
            baseRange=150,
            baseDamageDiceCount=3,
            baseDamageConstant=-3,
            baseAmmoCost=25,
            slowLoaderModifier=12)

class LowRecoilCalibre(ConventionalCalibre):
    """
    - Min TL: 8
    - Base Damage: 3D-3
    - Base Range: 40m
    - Base Ammo Cost: Cr150 for 100 rounds (Table on Field Catalogue p39)
    - Ammo Capacity: -20%
    - Recoil: -2 (From list on Field Catalogue p32)
    - Penetration: -1
    - Physical Signature: Normal
    - Trait: Zero-G
    - Trait: Inaccurate (-2)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # calibres become available. I've gone with TL 8 as that's the min TL for a Snub pistol in
    # the Core Rules p118
    # NOTE: The rules gives two different values for the cost of ammo. In the Low Recoil description
    # (Field Catalogue p38) it says Cr200 and in the list of Ammo Types (Field Catalogue p39) it
    # says Cr150. I've chosen to go with the table
    # NOTE: When it comes to recoil I'm assuming the modifier is applied on top of the base recoil
    # value for the receiver type. This seems a safe assumption as, if it replaces the receiver type
    # value, then low-recoil would actually make recoil worse

    _InaccurateModifier = common.ScalarCalculation(
        value=-2,
        name='Low-Recoil Inaccurate Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Low-Recoil',
            minTechLevel=8,
            baseRange=40,
            baseDamageDiceCount=3,
            baseDamageConstant=-3,
            baseAmmoCost=150,
            basePenetration=-1,
            basePhysicalSignature=gunsmith.Signature.Normal,
            capacityModifierPercentage=-20,
            recoilModifier=-2)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.ZeroG))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(value=self._InaccurateModifier)))

        return step

    def isHighVelocity(self) -> bool:
        return False

class GaussCalibre(ConventionalCalibre):
    """
    - Receiver Cost: +100%
    - Receiver Weight: +25%
    - Physical Signature: Normal
    - Ammo Capacity: x3
    - Recoil: -1 (From list on Field Catalogue p32)
    - Penetration: +2
    - Requirement: Damage is not reduced by short barrels (Field Catalogue p40)
    """
    # NOTE: The rules don't give a Physical Signature for Gauss weapons however they do mention an
    # audible crack (Field Catalogue p19) and the physical signature description (Field Catalogue
    # p7) says all weapons have a physical signature and in many cases it's around that of a typical
    # handgun/rifle. It you take typical to mean a mid range handgun/rifle calibre then that would be
    # normal
    # NOTE: When it comes to recoil I'm assuming the modifier is applied on top of the base recoil
    # value for the receiver type. This seems a safe assumption as, if it replaces the receiver type
    # value, then Gauss weapons would have worse recoil then non-Gauss weapons
    # NOTE: The requirement that range is not reduced due to barrel length is handled in the Barrel
    # code

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            baseRange: typing.Union[int, float, common.ScalarCalculation],
            baseDamageDiceCount: typing.Union[int, common.ScalarCalculation],
            baseEmissionsSignature: gunsmith.Signature,
            baseDamageConstant: typing.Union[int, common.ScalarCalculation] = 0,
            baseAmmoCost: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            capacityModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__(
            basePenetration=+2,
            basePhysicalSignature=gunsmith.Signature.Normal,
            weightModifierPercentage=+25,
            costModifierPercentage=+100,
            recoilModifier=-1,
            minTechLevel=minTechLevel,
            componentString=componentString,
            baseRange=baseRange,
            baseDamageDiceCount=baseDamageDiceCount,
            baseDamageConstant=baseDamageConstant,
            baseAmmoCost=baseAmmoCost,
            capacityModifierPercentage=capacityModifierPercentage)

        self._baseEmissionsSignature = baseEmissionsSignature

    def isHighVelocity(self) -> bool:
        return True

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.EmissionsSignature,
            value=self._baseEmissionsSignature))

        return step

class SmallGaussCalibre(GaussCalibre):
    """
    - Min TL: 13
    - Receiver Cost: +100%
    - Receiver Weight: +25%
    - Base Damage: 3D
    - Base Range: 100m
    - Base Ammo Cost: Cr50 per 100 rounds
    - Ammo Capacity: x3 (From table on Field Catalogue p31)
    - Recoil: -1 (From list on Field Catalogue p32)
    - Penetration: +2
    - Emissions Signature: Low
    - Requirement: Damage is not reduced by short barrels (Field Catalogue p40)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Small Gauss',
            minTechLevel=13,
            baseRange=100,
            baseDamageDiceCount=3,
            baseEmissionsSignature=gunsmith.Signature.Low,
            baseAmmoCost=50,
            capacityModifierPercentage=+200)

class StandardGaussCalibre(GaussCalibre):
    """
    - Min TL: 12
    - Receiver Cost: +100%
    - Receiver Weight: +25%
    - Base Damage: 4D
    - Base Ammo Cost: Cr50 per 100 rounds
    - Base Range: 600m
    - Base Ammo Cost: Cr50 per 100 rounds
    - Ammo Capacity: x3 (From table on Field Catalogue p31)
    - Recoil: -1 (From list on Field Catalogue p32)
    - Penetration: +2
    - Emissions Signature: Normal
    - Requirement: Damage is not reduced by short barrels (Field Catalogue p40)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Standard Gauss',
            minTechLevel=12,
            baseRange=600,
            baseDamageDiceCount=4,
            baseEmissionsSignature=gunsmith.Signature.Normal,
            baseAmmoCost=50,
            capacityModifierPercentage=+200)

class EnhancedGaussCalibre(GaussCalibre):
    """
    - Min TL: 14
    - Receiver Cost: +100%
    - Receiver Weight: +25%
    - Base Damage: 5D
    - Base Ammo Cost: Cr50 per 100 rounds
    - Base Range: 650m
    - Base Ammo Cost: Cr50 per 100 rounds
    - Ammo Capacity: x3 (From table on Field Catalogue p31)
    - Recoil: -1 (From list on Field Catalogue p32)
    - Penetration: +2
    - Emissions Signature: High
    - Requirement: Damage is not reduced by short barrels (Field Catalogue p40)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Enhanced Gauss',
            minTechLevel=14,
            baseRange=650,
            baseDamageDiceCount=5,
            baseEmissionsSignature=gunsmith.Signature.High,
            baseAmmoCost=50,
            capacityModifierPercentage=+200)

class ShotgunGaussCalibre(GaussCalibre):
    """
    - Min TL: 13
    - Receiver Cost: +100%
    - Receiver Weight: +25%
    - Base Damage: 3D + 6
    - Base Range: 100m
    - Ammo Capacity: -25% (Base Capacity x3 for gauss ammo then -75% for shotgun gauss)
    - Recoil: -1 (From list on Field Catalogue p32)
    - Penetration: +2
    - Emissions Signature: Low
    - Requirement: Damage is not reduced by short barrels (Field Catalogue p40)
    """
    # NOTE: The Gauss Shotgun description (Field Catalogue p40) seem contradictory. It says
    # that they "hold the same amount of projectiles as an equivalent gauss weapon, but they
    # are packed into bundles of 16-24" but it also says "Ammunition capacity is effectively
    # reduced by 75%.". A standard gauss weapon with an assault receiver has a base ammo
    # capacity of 60 (20 for an assault receiver x 3 for gauss ammo). Even if this was split
    # into the smaller bundles of 16 and rounded favourably this would only allow for an
    # effective ammo capacity of 4 which is a capacity reduction of ~93%. For an effective
    # capacity reduction of 75% it would suggest gauss shotguns all fire bundles of 4 rounds.
    # It's possible the issue is with my interpretation of holding the same number of "the
    # same amount of projectiles as an equivalent gauss weapon". But if it's not Base Ammo
    # capacity of the receiver multiplied by 3 (Table on Field Catalogue p31) then I don't
    # know what it means.
    # NOTE: The Gauss Shotgun description (Field Catalogue p40) doesn't say what the ammo
    # cost of 100 gauss shotgun rounds is. It say they are based on small gauss rounds and
    # those have a base cost of Cr50. However it would seem logical that gauss shotgun
    # rounds would be more expensive as each one contains multiple darts. To allow for this
    # I've added an option so the user can specify
    # NOTE: The same description says the following about damage "Gauss shotguns use small gauss
    # ammunition but deliver +2 damage per dice; typically this is 3D+6". If it's using the same
    # stats as Small Gauss, I'm not sure when it __wouldn't__ be 3D+6. It's possible that this
    # is meant to be a modifier that's meant to be applied after modifiers for ammo type have
    # been applied but the wording doesn't say anything like that.

    # Precompute a multiplier that can be applied to the base receiver ammo capacity in order
    # to apply the x3 multiplier for gauss ammo and 75% reduction for gauss shotgun ammo in
    # a single step.
    _AmmoCapacityMultiplier = common.Calculator.applyPercentage(
        value=common.ScalarCalculation(
            value=3,
            name='Gauss Calibre Ammo Capacity Multiplier'),
        percentage=common.ScalarCalculation(
            value=-75,
            name='Gauss Shotgun Ammo Capacity Percentage Reduction'),
        name='Gauss Shotgun Final Ammo Capacity Multiplier')

    _AmmoCostOptionDescription = \
        '<p>Specify the cost of 100 rounds of gauss shotgun ammo.</p>' \
        '<p>The description of gauss shotguns on p40 says projectiles are fired in bundles of ' \
        '16-24 and that they use the small gauss ammunition as the projectiles. However it ' \
        'doesn\'t say how ammo cost is affected. The base cost of 100 rounds of small gauss ammo ' \
        'is Cr50, but it would seem logical that a bundle of 16-24 of them would cost more. This ' \
        'option allows you to specify the cost for 100 rounds based on how you and your Referee ' \
        'interpret the rules.</p>' \
        '<p><i>Note that when purchasing quantities of gauss shotgun ammunition later in weapon ' \
        'construction, you are purchasing complete multiple projectile rounds based on this price '\
        'rather than purchasing the individual projectiles tha make up the rounds. This means you ' \
        'don\'t need to worry about buying 16-24 times the number of projectiles in order to get ' \
        'the number of rounds you desire. Just buy the number of rounds for the number of shots ' \
        'you want to fire.</i></p>'

    def __init__(self) -> None:
        super().__init__(
            componentString='Shotgun Gauss',
            minTechLevel=13,
            baseRange=100,
            baseDamageDiceCount=3, # Same as small gauss ammo
            baseDamageConstant=+6, # +2 per damage dice
            baseEmissionsSignature=gunsmith.Signature.Low,
            capacityModifierPercentage=None) # Handle capacity modifier locally as it's using a multiplier rather than a percentage

        self._ammoCostOption = construction.IntegerOption(
            id='AmmoCost',
            name='Cost of 100 Rounds of Gauss Shotgun Ammo',
            value=50, # Default to base cost of small gauss ammo
            minValue=50,
            description=ShotgunGaussCalibre._AmmoCostOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._ammoCostOption]
        options.extend(super().options())
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.MultiplierModifier(
                value=ShotgunGaussCalibre._AmmoCapacityMultiplier,
                roundDown=True)))

        ammoCost = common.ScalarCalculation(
            value=self._ammoCostOption.value(),
            name='Specified Gauss Shotgun Base Ammo Cost')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCost,
            value=ammoCost))

        return step
