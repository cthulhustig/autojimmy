import common
import gunsmith
import typing

_BarrelSpreadValues = {
    gunsmith.MinimalBarrel: common.ScalarCalculation(value=6, name='Minimal Barrel Spread Modifier'),
    gunsmith.ShortBarrel: common.ScalarCalculation(value=5, name='Short Barrel Spread Modifier'),
    gunsmith.HandgunBarrel: common.ScalarCalculation(value=4, name='Handgun Barrel Spread Modifier'),
    gunsmith.AssaultBarrel: common.ScalarCalculation(value=3, name='Assault Barrel Spread Modifier'),
    gunsmith.CarbineBarrel: common.ScalarCalculation(value=2, name='Carbine Barrel Spread Modifier'),
    gunsmith.RifleBarrel: common.ScalarCalculation(value=2, name='Rifle Barrel Spread Modifier'),
    gunsmith.LongBarrel: common.ScalarCalculation(value=1, name='Long Barrel Spread Modifier'),
    # NOTE: The rules (Field Catalogue p51) don't give a spread for a very long barrel. The only
    # sensible value seems to be 1 (the same as a long barrel) all barrels will have some amount of
    # spread so it can't be 0
    gunsmith.VeryLongBarrel: common.ScalarCalculation(value=1, name='Very Long Barrel Spread Modifier')
}

class _AmmoImpl(object):
    """
    - Smart
        - Min TL: 10
        - Cost: x6 Weapon Ammo Cost + Ammo Type Cost
        - Note: DM+1 at ranges >= 100m or DM+2 for TL13+ Intelligent Weapon
        - Requirement: Requires Intelligent Weapon (on Primary weapon)
    - Extreme Stealth
        - Cost: x20 Standard Cost
        - Signature: Physical and Emissions Signature +1 if weapon has Extreme Stealth feature and ammo isn't Extreme Stealth ammo
        - Requirement: Extreme Stealth feature
    """
    # NOTE: When it comes to applying ammo type, smart and extreme stealth multipliers my reading
    # of the rules is the following. The ammo type and smart multiplies are added together (Field
    # Guild p51). This is then multiplied by the ammo cost for the weapon to give the cost for
    # the smart/non-smart variant of that ammo. If it's the extreme stealth variant that cost is
    # then multiplied by 20 (Field Catalogue p35) to give the cost of the extreme stealth variant
    # smart/non-smart ammo
    # NOTE: I've added the requirement that extreme stealth ammo is only compatible with the Extreme
    # stealth feature. It's only ever mentioned in the section for that feature (Field Catalogue
    # p35). Having it incompatible with normal weapons also makes it easier to reduce the number of
    # options that will be listed in the ammo table when exporting pdfs
    # NOTE: I've made the intelligent weapon accessory something that is only compatible with the
    # primary weapon as it only really makes sense as something that is applied to the weapon as
    # a whole. That means when checking for Smart ammo compatibility it needs to be the primary
    # weapon that is checked

    _SmartMinTechLevel = 10
    _SmartCostMultiplier = common.ScalarCalculation(
        value=6,
        name='Smart Ammo Cost Multiplier')
    _LowTechSmartNote = 'DM+1 to attack rolls at ranges >= 100m'
    _HighTechSmartNote = 'DM+2 to attack rolls at ranges >= 100m'

    _ExtremeStealthAmmoCostMultiplier = common.ScalarCalculation(
        value=20,
        name='Extreme Stealth Ammo Cost Multiplier')
    _ExtremeStealthRegularAmmoSignatureModifier = common.ScalarCalculation(
        value=+1,
        name='Extreme Stealth Weapon Using Standard Ammo Signature Modifier')

    # Smart ammo is a mod on other ammo types
    def __init__(
            self,
            componentString: str,
            minTechLevel: typing.Optional[int] = None,
            costMultiplier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            penetrationModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__()

        if costMultiplier != None and not isinstance(costMultiplier, common.ScalarCalculation):
            costMultiplier = common.ScalarCalculation(
                value=costMultiplier,
                name=f'{componentString} Ammo Cost Multiplier')

        if penetrationModifier != None and not isinstance(penetrationModifier, common.ScalarCalculation):
            penetrationModifier = common.ScalarCalculation(
                value=penetrationModifier,
                name=f'{componentString} Ammo Penetration Modifier')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._costMultiplier = costMultiplier
        self._penetrationModifier = penetrationModifier

        self._isSmartOption = gunsmith.BooleanComponentOption(
            id='Smart',
            name='Smart',
            value=isSmart if isSmart != None else False,
            description='Specify if this is smart ammunition.',
            enabled=False) # Optional, enabled if supported in updateOptions
        self._isStealthOption = gunsmith.BooleanComponentOption(
            id='Stealth',
            name='Stealth',
            value=isStealth if isStealth != None else False,
            description='Specify if this is stealth ammunition.',
            enabled=False) # Optional, enabled if supported in updateOptions

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        modifiers = ''
        if self._isSmartOption.isEnabled() and self._isSmartOption.value():
            modifiers += 'Smart'
        if self._isStealthOption.isEnabled() and self._isStealthOption.value():
            if modifiers:
                modifiers += ', '
            modifiers += 'Stealth'
        instanceString = self.componentString()
        if modifiers:
            instanceString += f' ({modifiers})'
        return instanceString

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if self._minTechLevel != None:
            if context.techLevel() < self._minTechLevel:
                return False

        # Only compatible with conventional weapons
        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = []

        # Only include Smart option if weapon supports it.
        if self._isSmartOption.isEnabled():
            options.append(self._isSmartOption)

        # Only include Stealth option if weapon has one of the stealth features
        if self._isStealthOption.isEnabled():
            options.append(self._isStealthOption)

        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        self._isSmartOption.setEnabled(self._isSmartCompatible(
            sequence=sequence,
            context=context))
        self._isStealthOption.setEnabled(self._isStealthCompatible(
            sequence=sequence,
            context=context))

    def isSmart(self) -> bool:
        return self._isSmartOption.value()

    def isStealth(self) -> bool:
        return self._isStealthOption.value()

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        ammoCost = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCost)
        assert(isinstance(ammoCost, common.ScalarCalculation)) # Construction logic should enforce this

        costMultiplier = self._calculateCostMultiplier()
        if costMultiplier:
            ammoCost = common.Calculator.multiply(
                lhs=ammoCost,
                rhs=costMultiplier)
        ammoCost = common.Calculator.equals(
            value=ammoCost,
            name=f'{self.componentString()} Cost Per 100 Rounds')

        ammoCost = common.Calculator.divideFloat(
            lhs=ammoCost,
            rhs=common.ScalarCalculation(value=100))
        totalCost = common.Calculator.multiply(
            lhs=ammoCost,
            rhs=numberOfRounds,
            name=f'Total Ammo Cost')
        step.setCost(cost=gunsmith.ConstantModifier(value=totalCost))

        factors = []
        notes = []

        if costMultiplier:
            factors.append(gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.AmmoCost,
                modifier=gunsmith.MultiplierModifier(
                    value=costMultiplier)))

        if self._penetrationModifier:
            factors.append(gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.Penetration,
                modifier=gunsmith.ConstantModifier(
                    value=self._penetrationModifier)))

        if self._isSmartCompatible(sequence=sequence, context=context) \
                and self._isSmartOption.value():
            highTechComputer = context.hasComponent(
                componentType=gunsmith.HighIntelligentWeaponFeature,
                sequence=sequence)
            notes.append(
                self._HighTechSmartNote if highTechComputer else self._LowTechSmartNote)

        if self._isStealthCompatible(sequence=sequence, context=context) \
                and not self._isStealthOption.value():
            # Apply signature increase if an Extreme Stealth weapon is loaded with standard ammo. As
            # this is conventional ammo the weapon is expected to always have a physical signature
            factors.append(gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.PhysicalSignature,
                modifier=gunsmith.ConstantModifier(
                    value=self._ExtremeStealthRegularAmmoSignatureModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = gunsmith.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            for note in notes:
                step.addNote(note=note)

    # This needs to be a class method (rather than static) so Flechette ammo can override it
    def _isSmartCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if context.techLevel() < self._SmartMinTechLevel:
            return False

        return context.hasComponent(
            componentType=gunsmith.IntelligentWeaponFeature,
            sequence=sequence)

    def _isStealthCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        return context.hasComponent(
            componentType=gunsmith.ExtremeStealthFeature,
            sequence=sequence) # Only compatible if this sequence has the extreme stealth feature

    def _calculateCostMultiplier(self):
        costMultiplier = self._costMultiplier
        if self._isSmartOption.value():
            if costMultiplier:
                # Smart ammo multiplier is added to base multiplier for ammo type (Field
                # Catalogue p51)
                costMultiplier = common.Calculator.add(
                    lhs=costMultiplier,
                    rhs=self._SmartCostMultiplier)
            else:
                costMultiplier = self._SmartCostMultiplier
        if self._isStealthOption.value():
            if costMultiplier:
                # Stealth ammo multiplies the standard cost for that type of ammo (Field Catalogue
                # p35)
                costMultiplier = common.Calculator.multiply(
                    lhs=costMultiplier,
                    rhs=self._ExtremeStealthAmmoCostMultiplier)
            else:
                costMultiplier = self._ExtremeStealthAmmoCostMultiplier
        if costMultiplier:
            costMultiplier = common.Calculator.equals(
                value=costMultiplier,
                name=f'Total Cost Multiplier')
        return costMultiplier

class _BallAmmoImpl(_AmmoImpl):
    """
    - No modifiers
    """

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Ball',
            isSmart=isSmart,
            isStealth=isStealth)

class _ArmourPiercingAmmoImpl(_AmmoImpl):
    """
    - Min TL: 4
    - Cost: x2 Weapon Ammo Cost
    - Penetration: +1
    """

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Armour Piercing',
            minTechLevel=4,
            costMultiplier=2,
            penetrationModifier=+1,
            isSmart=isSmart,
            isStealth=isStealth)

class _AdvancedArmourPiercingAmmoImpl(_AmmoImpl):
    """
    - Min TL: 7
    - Cost: x4 Weapon Ammo Cost
    - Penetration: +2
    - Requirement: Not compatible with Handguns and Smoothbores
    """
    # NOTE: For the requirement I've taken Handguns to mean handgun receivers rather than handgun
    # calibre. This is based on the example weapon on p89 of the Field Catalogue, it has a Light
    # Handgun calibre but has an example of Advanced Armour Piercing in the ammo table on p90

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Advanced Armour Piercing',
            minTechLevel=7,
            costMultiplier=4,
            penetrationModifier=+2,
            isSmart=isSmart,
            isStealth=isStealth)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.HandgunReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.SmoothboreCalibre,
                sequence=sequence)

class _DistractionAmmoImpl(_AmmoImpl):
    """
    - Min TL: 5
    - Cost: x4 Weapon Ammo Cost
    - Trait: Minor or Small Distraction
    """
    # NOTE: The rules say distraction ammo can either provide a minor or small distraction (Field
    # Catalogue p53) but doesn't say what would make it one over the other. Possibly lower calibre
    # ammo would be minor with higher calibres being small. The only example with distraction ammo
    # in its ammo table is the LIberator on p79, it use heavy handgun ammo and the table gives the
    # distraction level as small. As it's not clear when one option should be chosen over the other
    # I've added an option that lets the user choose

    _DistractionOptionDescription = \
        '<p>Specify the level of Distraction the ammunition provides</p>' \
        '<p>The description of Distraction Ammunition on p53 of the Field Catalogue say it provides ' \
        'a Minor or Small Distraction but don\'t say what would determine which of those it would be. ' \
        'This allows you to select a value that you agree with your Referee.</p>'

    def __init__(
            self,
            distractionType: typing.Optional[gunsmith.Distraction] = None,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Distraction',
            minTechLevel=5,
            costMultiplier=4,
            isSmart=isSmart,
            isStealth=isStealth)

        self._distractionTypeOption = gunsmith.EnumComponentOption(
            id='DistractionType',
            name='Distraction Type',
            type=gunsmith.Distraction,
            value=distractionType if distractionType != None else gunsmith.Distraction.Minor, # Small distraction has such a low modifier it's effectively pointless
            options=[gunsmith.Distraction.Small, gunsmith.Distraction.Minor],
            isOptional=False,
            description=_DistractionAmmoImpl._DistractionOptionDescription)

    def distractionType(self) -> gunsmith.Distraction:
        return self._distractionTypeOption.value()

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._distractionTypeOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factor = gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Distraction,
            value=self._distractionTypeOption.value())
        if not applyModifiers:
            factor = gunsmith.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

        return step

class _EnhancedWoundingAmmoImpl(_AmmoImpl):
    """
    - Min TL: 5
    - Cost: x2 Weapon Ammo Cost
    - Damage: +2 per Damage Dice
    - Penetration: -2
    """
    _DamageIncreaseIncrement = common.ScalarCalculation(
        value=+2,
        name='Enhanced Wounding Ammo Damage Increase Per Dice')

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Enhanced Wounding',
            minTechLevel=5,
            costMultiplier=2,
            penetrationModifier=-2,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        damageModifier = common.Calculator.multiply(
            lhs=self._DamageIncreaseIncrement,
            rhs=damageRoll.dieCount(),
            name='Enhanced Wounding Ammo Damage Modifier')
        factor = gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Damage,
            modifier=gunsmith.DiceRollModifier(
                constantModifier=damageModifier))
        if not applyModifiers:
            factor = gunsmith.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

class _ExplosiveAmmoImpl(_AmmoImpl):
    """
    - Min TL: 6
    - Cost: x6 Weapon Ammo Cost
    - Damage: +1D + (1D for each full 3D of Damage)
    - Penetration: -1
    - Physical Signature: Increased by 1 level
    """
    # NOTE: I've assumed small arms is anything other than a Handgun receiver
    # NOTE: The description (Field Catalogue p50) says explosive ammo doesn't give the Blast trait for
    # small arms. I'm taking this to cover any of the weapons this code is creating
    _PhysicalSignatureModifier = common.ScalarCalculation(
        value=+1,
        name='Explosive Ammo Physical Signature Modifier')
    _ConstantDamageDiceConstant = common.ScalarCalculation(
        value=+1,
        name='Explosive Ammo Constant Damage Dice Constant')
    _ConstantDamageDiceIncrement = common.ScalarCalculation(
        value=+1,
        name='Explosive Ammo Damage Dice Increase Per 3 Full Dice')

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Explosive',
            minTechLevel=6,
            costMultiplier=6,
            penetrationModifier=-1,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factors = []

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        damageDiceModifier = common.Calculator.multiply(
            lhs=self._ConstantDamageDiceIncrement,
            rhs=common.Calculator.divideFloor(
                lhs=damageRoll.dieCount(),
                rhs=common.ScalarCalculation(value=3)))
        damageDiceModifier = common.Calculator.add(
            lhs=damageDiceModifier,
            rhs=self._ConstantDamageDiceConstant,
            name='Explosive Ammo Damage Dice Modifier')
        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Damage,
            modifier=gunsmith.DiceRollModifier(
                countModifier=damageDiceModifier)))

        # As this is conventional ammo the weapon is expected to always have a physical signature
        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.PhysicalSignature,
            modifier=gunsmith.ConstantModifier(
                value=self._PhysicalSignatureModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = gunsmith.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _FlechetteAmmoImpl(_AmmoImpl):
    """
    - Min TL: 7
    - Cost: Standard Weapon Ammo Cost
    - Damage: All Damage Dice are reduced to D3s and any existing D3s are reduced to a single point
    - Range: 10 meters
    - Trait: Spread score determined by barrel (table on Field Catalogue p51)
    - Note: DM+4 to attack rolls at ranges <= 5m
    - Requirement: No smart variant
    """
    # NOTE: It's not clear what "...and any existing D3s are reduced to a single point" actually
    # means. I've taken it to mean if the weapon is currently using D3s then the dice count is added
    # to the constant damage and the dice count and sides is reduced to 0 (i.e. there is no dice
    # roll)
    # NOTE: The description for Flechette just says it grants the Spread trait but doesn't say which
    # level. From looking at the ammo tables that go with the weapon examples (e.g Field Catalogue
    # p74) it looks like it's using the same spread table as pellet ammo (p51)
    # NOTE: I've added the requirement that there is no smart variant of Flechette ammo as smart ammo
    # has no effect under 100m so it would be pointless
    _FixedRange = common.ScalarCalculation(
        value=10,
        name='Flechette Ammo Range')
    _Note = 'DM+4 to attack rolls at ranges <= 5m'

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Flechette',
            minTechLevel=7,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factors = []

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        if damageRoll.dieCount().value() == 0:
            pass # Nothing to do
        elif damageRoll.dieType() == common.DieType.D3:
            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.Damage)
            assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

            damageConstant = common.Calculator.equals(
                value=damageRoll.dieCount(),
                name='Flechette Ammo Damage Constant')
            damageRoll = common.DiceRoll(constant=damageConstant)

            factors.append(gunsmith.SetAttributeFactor(
                attributeId=gunsmith.AttributeId.Damage,
                value=damageRoll))
        elif damageRoll.dieType() == common.DieType.D6:
            damageRoll = common.DiceRoll(
                count=damageRoll.dieCount(),
                type=common.DieType.D3,
                constant=damageRoll.constant())
            factors.append(gunsmith.SetAttributeFactor(
                attributeId=gunsmith.AttributeId.Damage,
                value=damageRoll))
        else:
            assert(False) # This should never happen

        factors.append(gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Range,
            value=self._FixedRange))

        barrel = context.findFirstComponent(
            componentType=gunsmith.Barrel,
            sequence=sequence) # Only interested in barrel from sequence ammo is part of
        assert(isinstance(barrel, gunsmith.Barrel)) # Construction order should enforce this

        spreadModifier = _BarrelSpreadValues.get(type(barrel))
        assert(spreadModifier) # This should never happen

        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Spread,
            modifier=gunsmith.ConstantModifier(
                value=spreadModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = gunsmith.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._Note)

    def _isSmartCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        return False # No smart variant of Flechette ammo

class _GasAmmoImpl(_AmmoImpl):
    """
    - Min TL: 7
    - Cost: x6 Weapon Ammo Cost
    - Damage: 1D for round its self
    - Note: Dependant on gas contained in round
    """
    _DamageDiceCount = common.ScalarCalculation(
        value=1,
        name='Gas Ammo Damage Dice')
    _Note = 'Effect is dependant of gas contained in round'

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Gas',
            minTechLevel=7,
            costMultiplier=6,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        damageRoll = common.DiceRoll(
            count=self._DamageDiceCount,
            type=damageRoll.dieType())

        factor = gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Damage,
            value=damageRoll)
        if not applyModifiers:
            factor = gunsmith.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._Note)


class _HEAPAmmoImpl(_AmmoImpl):
    """
    - Min TL: 8
    - Cost: x10 Weapon Ammo Cost
    - Penetration: +2
    - Physical Signature: Increased by 1 level
    - Requirement: Requires 10mm ammo and above
    """
    # NOTE: To implement the 10mm ammo and above I've gone with the example calibres on p36-37 of
    # the Field Catalogue. I've included MediumHandgun as it has a range of 9-10mm
    # NOTE: HEAP rounds don't give the Blast trait (Field Catalogue p51). They use directed explosion to
    # give higher penetration rather than a blast
    # NOTE: Ideally the >= 10mm requirement would be handled as a requirement but the exact calibre
    # isn't a parameter. Instead I've handled it as a note.
    _PhysicalSignatureModifier = common.ScalarCalculation(
        value=+1,
        name='HEAP Physical Signature Modifier')

    _Note = 'Requires a calibre >= 10mm'

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='HEAP',
            minTechLevel=8,
            costMultiplier=10,
            penetrationModifier=+2,
            isSmart=isSmart,
            isStealth=isStealth)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        calibre = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence ammo is part of
        if not calibre:
            return False
        return isinstance(calibre, gunsmith.MediumHandgunCalibre) or \
            isinstance(calibre, gunsmith.HeavyHandgunCalibre) or \
            isinstance(calibre, gunsmith.SmoothboreCalibre) or \
            isinstance(calibre, gunsmith.HeavyRifleCalibre) or \
            isinstance(calibre, gunsmith.AntiMaterialRifleCalibre) or \
            isinstance(calibre, gunsmith.HeavyAntiMaterialRifleCalibre)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        # As this is conventional ammo the weapon is expected to always have a physical signature
        factor = gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.PhysicalSignature,
            modifier=gunsmith.ConstantModifier(
                value=self._PhysicalSignatureModifier))
        if not applyModifiers:
            factor = gunsmith.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._Note)

class _IncendiaryAmmoImpl(_AmmoImpl):
    """
    - Min TL: 6
    - Cost: x6 Weapon Ammo Cost
    - Trait: Incendiary 1
    - Note: An incendiary round that penetrates armour delivers half as much damage as got through armour again the
      following round, with the armour offering no protection
    """
    # NOTE: The description (Field Catalogue p51) just says Incendiary, I've assumed that means
    # Incendiary 1
    # NOTE: The description for incendiary rounds (Field Catalogue p51) says it delivers half damage
    # again the next round. This is more like the description for the Burn trait (Field Catalogue
    # p6) than the Incendiary trait (Field Catalogue p7) trait. It's also worth noting that the
    # fact armour offers no protection is also different from the description of incendiary and
    # flammable weapons (Field Catalogue p24), however that section is specifically for weapons
    # that don't penetrate armour.
    _IncendiaryTrait = common.ScalarCalculation(
        value=1,
        name='Incendiary Ammo Incendiary Modifier')
    _IncendiaryNote = 'An incendiary round that penetrates armour delivers half as much damage as got through armour again the following round, with the armour offering no protection'

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Incendiary',
            minTechLevel=6,
            costMultiplier=6,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factor = gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Incendiary,
            modifier=gunsmith.ConstantModifier(
                value=self._IncendiaryTrait))
        if not applyModifiers:
            factor = gunsmith.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._IncendiaryNote)

class _LowPenetrationAmmoImpl(_AmmoImpl):
    """
    - Min TL: 6
    - Cost: Standard Weapon Ammo Cost
    - Damage: All Damage Dice are reduced to D3s
    - Penetration: Normally -1 but can be any value from -1 to -4
    """

    def __init__(
            self,
            penetration: typing.Optional[int] = None,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Low Penetration',
            minTechLevel=6,
            isSmart=isSmart,
            isStealth=isStealth)

        self._penetrationOption = gunsmith.IntegerComponentOption(
            id='Penetration',
            name='Penetration Modifier',
            value=penetration if penetration != None else -1,
            maxValue=-1,
            minValue=-4,
            description='Specify the Penetration reduction provided by the ammunition.')

    def penetration(self) -> int:
        return self._penetrationOption.value()

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._penetrationOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factors = []

        penetrationModifier = common.ScalarCalculation(
            value=self._penetrationOption.value(),
            name='Specified Penetration Modifier')
        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Penetration,
            modifier=gunsmith.ConstantModifier(
                value=penetrationModifier)))

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        damageRoll = common.DiceRoll(
            count=damageRoll.dieCount(),
            type=common.DieType.D3,
            constant=damageRoll.constant())
        factors.append(gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Damage,
            value=damageRoll))

        for factor in factors:
            if not applyModifiers:
                factor = gunsmith.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _PelletAmmoImpl(_AmmoImpl):
    """
    - Min TL: 3
    - Cost: Standard Weapon Ammo Cost
    - Range: Range reduced by 75%
    - Trait: Spread score determined by barrel (table on Field Catalogue p51)
    - Penetration: Reduce Penetration by the weapon's Spread score for the barrel (Field Catalogue p51)
    """
    # NOTE: The reduction in range of 75% is based on the rules for shotguns (Field Catalogue p36).
    # The rules don't explicitly say that other weapons using pellet ammo suffer the same modifier,
    # however it seems logical they would. The description for pellet ammo (Field Catalogue p51)
    # only says pellet ammo is typically used by smoothbores, but it doesn't say exclusively.

    _PelletRangeModifier = common.ScalarCalculation(
        value=-75,
        name='Pellet Ammo Range Percentage Modifier')

    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None,
            ) -> None:
        super().__init__(
            componentString='Pellet',
            minTechLevel=3,
            isSmart=isSmart,
            isStealth=isStealth)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface,
            numberOfRounds: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.ConstructionStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=applyModifiers,
            step=step)

        factors = []

        barrel = context.findFirstComponent(
            componentType=gunsmith.Barrel,
            sequence=sequence) # Only interested in barrel from sequence ammo is part of
        assert(isinstance(barrel, gunsmith.Barrel)) # Construction order should enforce this

        spreadModifier = _BarrelSpreadValues.get(type(barrel))
        assert(spreadModifier) # This should never happen

        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Range,
            modifier=gunsmith.PercentageModifier(
                value=_PelletAmmoImpl._PelletRangeModifier)))
        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Spread,
            modifier=gunsmith.ConstantModifier(value=spreadModifier)))
        factors.append(gunsmith.ModifyAttributeFactor(
            attributeId=gunsmith.AttributeId.Penetration,
            modifier=gunsmith.ConstantModifier(
                value=common.Calculator.negate(
                    value=spreadModifier,
                    name='Pellet Ammo Minimal Barrel Penetration Modifier'))))

        for factor in factors:
            if not applyModifiers:
                factor = gunsmith.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class ConventionalAmmoLoaded(gunsmith.AmmoLoadedInterface):
    """
    Requirement: Weapons with a removable magazine must have one loaded
    """

    def __init__(
            self,
            impl: _AmmoImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Ammo'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        # If the sequence uses a removable magazine it must have one loaded
        if context.hasComponent(
                componentType=gunsmith.RemovableMagazineFeed,
                sequence=sequence):
            return context.hasComponent(
                componentType=gunsmith.ConventionalMagazineLoaded,
                sequence=sequence)

        return True # Compatible with all fixed magazine weapons

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCapacity)
        assert(isinstance(ammoCapacity, common.ScalarCalculation)) # Construction logic should enforce this

        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=ammoCapacity,
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class BallConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_BallAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class ArmourPiercingConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ArmourPiercingAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class AdvancedArmourPiercingConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_AdvancedArmourPiercingAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class DistractionConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            distractionType: typing.Optional[gunsmith.Distraction] = None,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_DistractionAmmoImpl(
            distractionType=distractionType,
            isSmart=isSmart,
            isStealth=isStealth))

class EnhancedWoundingConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_EnhancedWoundingAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class ExplosiveConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ExplosiveAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class FlechetteConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_FlechetteAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class GasConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_GasAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class HEAPConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_HEAPAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class IncendiaryConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_IncendiaryAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class LowPenetrationConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            penetration: typing.Optional[int] = None,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_LowPenetrationAmmoImpl(
            penetration=penetration,
            isSmart=isSmart,
            isStealth=isStealth))

class PelletConventionalAmmoLoaded(ConventionalAmmoLoaded):
    def __init__(
            self,
            isSmart: typing.Optional[bool] = None,
            isStealth: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_PelletAmmoImpl(
            isSmart=isSmart,
            isStealth=isStealth))

class ConventionalAmmoQuantity(gunsmith.AmmoQuantityInterface):
    def __init__(
            self,
            impl: _AmmoImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfRoundsOption = gunsmith.IntegerComponentOption(
            id='Quantity',
            name='Rounds',
            value=1,
            minValue=1,
            description='Specify the number of rounds of ammunition.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfRoundsOption.value()}'

    def typeString(self) -> str:
        return 'Ammo Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = [self._numberOfRoundsOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        numberOfRounds = common.ScalarCalculation(
            value=self._numberOfRoundsOption.value(),
            name='Specified Number Of Rounds')

        step = gunsmith.ConstructionStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfRounds=numberOfRounds,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class BallConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BallAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return BallConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class ArmourPiercingConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ArmourPiercingAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return ArmourPiercingConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class AdvancedArmourPiercingConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_AdvancedArmourPiercingAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return AdvancedArmourPiercingConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class DistractionConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_DistractionAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        assert(isinstance(self._impl, _DistractionAmmoImpl))
        return DistractionConventionalAmmoLoaded(
            distractionType=self._impl.distractionType(),
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class EnhancedWoundingConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_EnhancedWoundingAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return EnhancedWoundingConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class ExplosiveConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExplosiveAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return ExplosiveConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class FlechetteConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_FlechetteAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return FlechetteConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class GasConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_GasAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return GasConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class HEAPConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_HEAPAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return HEAPConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class IncendiaryConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_IncendiaryAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return IncendiaryConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class LowPenetrationConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_LowPenetrationAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        assert(isinstance(self._impl, _LowPenetrationAmmoImpl))
        return LowPenetrationConventionalAmmoLoaded(
            penetration=self._impl.penetration(),
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())

class PelletConventionalAmmoQuantity(ConventionalAmmoQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_PelletAmmoImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return PelletConventionalAmmoLoaded(
            isSmart=self._impl.isSmart(),
            isStealth=self._impl.isStealth())
