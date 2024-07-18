import common
import construction
import gunsmith
import typing

class Barrel(gunsmith.WeaponComponentInterface):
    """
    All Barrels
    - Quickdraw: Base barrel Quickdraw modifier is not applied to Secondary Weapons (but modifier for a Heavy Barrel is)
    - Requirement: Not compatible with Projectors
    Heavy Barrel
    - Barrel Weight: x2 (Field Catalogue p43)
    - Barrel Cost: x2 (Field Catalogue p43)
    - Heat Dissipation: +2 (from table on Core rules p14, it's not in the Heavy Barrel description)
    - Heat Before Misshape: +100%
    - Quickdraw: -1
    Rocket Calibre
    - Barrel Weight: -50%
    - Range: Range modifier not applied for rocket ammo (Field Catalogue p40)
    - Penetration: Penetration modifier not applied for rocket ammo
    - Requirement: Not compatible with Energy Weapons
    Multi Barrel
    - Barrel Cost: Base barrel cost multiplied by number of barrels
    - Barrel Weight:
        - Complete Multi-Barrel: Base barrel weight + 50% base barrel weight for each additional barrel
        - Partial Multi-Barrel: Base barrel weight * Additional barrel count
    Energy Weapons
    - Note: If the max damage dice for the barrel is less than the damage of the weapon the excess power is
      wasted but the weapon is not damaged (Field Catalogue p64)
    """
    # NOTE: Heat isn't fully supported for weapons other than conventional firearms as I don't know
    # the base heat generation/dissipation values. However I've not made heavy barrel incompatible as
    # it allows a user add one if they're using homebrew rules for heat
    # NOTE: I've added the requirement that the Quickdraw modifier is not applied to secondary
    # weapons. It seems wrong that the only Quickdraw modifier that is applied for a secondary
    # weapon is -1 per additional barrel, for example if the barrel of the secondary weapon was
    # heavy or you added a suppressor to it you would expect those negative Quickdraw modifiers to
    # affect the Quickdraw of the weapon as a whole. To achieve this only some components apply the
    # Quickdraw modifiers to secondary weapons (generally the ones with negative modifiers), the
    # final Quickdraw of the secondary weapon is then applied as a modifier to the Quickdraw of the
    # primary weapon.
    # The Quickdraw modifiers for barrels are not applied as they're all positive modifier and
    # would result in a some barrels on a secondary weapon causing the weapon as a whole to have a
    # better Quickdraw score than it would if it didn't have the secondary weapon. As mentioned above
    # it still makes sense to apply the negative modifier for a heavy barrel on the secondary weapon
    # NOTE: The fact that the Penetration modifier is not implied from the working of description
    # (Field Catalogue p38 & 40) and the description of barrel range modifiers (Field Catalogue p42).
    # If the barrel length doesn't affect the range when using rocket propelled ammo it would imply
    # that it doesn't affect the amount of kinetic energy the round has when it exits the barrel and
    # therefore wouldn't affect the level of penetration it achieves.
    _HeavyWeightMultiplier = common.ScalarCalculation(
        value=2,
        name='Heavy Barrel Weight Multiplier')
    _HeavyCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Heavy Barrel Cost Multiplier')
    _HeavyQuickdrawModifier = common.ScalarCalculation(
        value=-1,
        name='Heavy Barrel Quickdraw Modifier')
    _HeavyHeatDissipationModifier = common.ScalarCalculation(
        value=+2,
        name='Heavy Barrel Heat Dissipation Modifier')
    _HeavyHeatMisshapeModifierPercentage = common.ScalarCalculation(
        value=+100,
        name='Heavy Barrel Heat Before Misshape Modifier Percentage')
    _RocketWeightModifierPercentage = common.ScalarCalculation(
        value=-50,
        name='Rocket Barrel Weight Modifier Percentage')
    _AdditionalCompleteBarrelWeightPercentage = common.ScalarCalculation(
        value=50,
        name='Additional Barrel Weight Percentage')

    def __init__(
            self,
            componentString: str,
            weightPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            costPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            rangeModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            penetrationModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            quickdrawModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            physicalSignatureModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            maxEnergyWeaponDamageDice: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__()

        if weightPercentage != None  and not isinstance(weightPercentage, common.ScalarCalculation):
            weightPercentage = common.ScalarCalculation(
                value=weightPercentage,
                name=f'{componentString} Barrel Weight Percentage')
        if costPercentage != None  and not isinstance(costPercentage, common.ScalarCalculation):
            costPercentage = common.ScalarCalculation(
                value=costPercentage,
                name=f'{componentString} Barrel Cost Percentage')
        if rangeModifierPercentage != None  and not isinstance(rangeModifierPercentage, common.ScalarCalculation):
            rangeModifierPercentage = common.ScalarCalculation(
                value=rangeModifierPercentage,
                name=f'{componentString} Barrel Range Modifier Percentage')
        if penetrationModifier != None  and not isinstance(penetrationModifier, common.ScalarCalculation):
            penetrationModifier = common.ScalarCalculation(
                value=penetrationModifier,
                name=f'{componentString} Barrel Penetration Modifier')
        if quickdrawModifier != None  and not isinstance(quickdrawModifier, common.ScalarCalculation):
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name=f'{componentString} Barrel Quickdraw Modifier')
        if physicalSignatureModifier != None  and not isinstance(physicalSignatureModifier, common.ScalarCalculation):
            physicalSignatureModifier = common.ScalarCalculation(
                value=physicalSignatureModifier,
                name=f'{componentString} Barrel Physical Signature Modifier')
        if maxEnergyWeaponDamageDice != None and not isinstance(maxEnergyWeaponDamageDice, common.ScalarCalculation):
            maxEnergyWeaponDamageDice = common.ScalarCalculation(
                value=maxEnergyWeaponDamageDice,
                name=f'{componentString} Barrel Max Damage Dice For Energy Weapon')

        self._componentString = componentString
        self._weightPercentage = weightPercentage
        self._costPercentage = costPercentage
        self._rangeModifierPercentage = rangeModifierPercentage
        self._penetrationModifier = penetrationModifier
        self._quickdrawModifier = quickdrawModifier
        self._physicalSignatureModifier = physicalSignatureModifier
        self._maxEnergyWeaponDamageDice = maxEnergyWeaponDamageDice

        self._isHeavyOption = construction.BooleanOption(
            id='Heavy',
            name='Heavy',
            value=False,
            description='Specify if the barrel is of heavy construction for improved heat dissipation.')

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        instanceString = self.componentString()
        if self._isHeavyOption.value():
            instanceString += ' (Heavy)'
        return instanceString

    def typeString(self) -> str:
        return 'Barrel'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Not compatible with projectors
        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Only compatible with weapons that have a receiver.
        return context.hasComponent(
            componentType=gunsmith.Receiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._isHeavyOption]

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        baseStep = self._createStep(sequence=sequence, context=context)
        context.applyStep(
            sequence=sequence,
            step=baseStep)

        # Generate additional steps for each additional barrel. These only
        # have cost & weight as we don't want the operations to be applied
        # for each barrel
        barrelCount = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.BarrelCount)
        assert(isinstance(barrelCount, common.ScalarCalculation)) # Construction logic should enforce this

        additionalBarrels = common.Calculator.subtract(
            lhs=barrelCount,
            rhs=common.ScalarCalculation(value=1),
            name=f'Additional Barrel Count')

        if additionalBarrels.value() <= 0:
            return # Nothing more to do

        barrelCost = baseStep.credits()
        additionalCost = common.Calculator.multiply(
            lhs=barrelCost.numericModifier(),
            rhs=additionalBarrels,
            name=f'Total Additional Barrel Cost')

        barrelWeight = baseStep.weight()
        if context.hasComponent(
                componentType=gunsmith.CompleteMultiBarrelSetup,
                sequence=sequence):
            additionalWeight = common.Calculator.takePercentage(
                value=barrelWeight.numericModifier(),
                percentage=self._AdditionalCompleteBarrelWeightPercentage)
        else:
            additionalWeight = barrelWeight.numericModifier()

        additionalWeight = common.Calculator.multiply(
            lhs=additionalWeight,
            rhs=additionalBarrels,
            name=f'Total Additional Barrel Weight')

        step = gunsmith.WeaponStep(
            name=f'Additional {self.instanceString()} Barrel x{additionalBarrels.value()}',
            type=self.typeString(),
            credits=construction.ConstantModifier(value=additionalCost),
            weight=construction.ConstantModifier(value=additionalWeight))
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

        isRocket = self._isRocket(sequence=sequence, context=context)

        weight = None
        if self._weightPercentage:
            weight = common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=sequence),
                percentage=self._weightPercentage,
                name=f'{self.componentString()} Barrel Weight')
        else:
            weight = common.ScalarCalculation(
                value=0,
                name=f'{self.componentString()} Barrel Weight')

        # Apply barrel weight reduction for using rocket propelled ammo
        if isRocket:
            weight = common.Calculator.applyPercentage(
                value=weight,
                percentage=self._RocketWeightModifierPercentage,
                name=f'Rocket {weight.name()}')

        if self._isHeavyOption.value():
            weight = common.Calculator.multiply(
                lhs=weight,
                rhs=self._HeavyWeightMultiplier,
                name=f'Heavy {weight.name()}')

        step.setWeight(weight=construction.ConstantModifier(value=weight))

        cost = None
        if self._costPercentage:
            cost = common.Calculator.takePercentage(
                value=context.receiverCredits(sequence=sequence),
                percentage=self._costPercentage,
                name=f'{self.componentString()} Barrel Cost')
        else:
            cost = common.ScalarCalculation(
                value=0,
                name=f'{self.componentString()} Barrel Cost')

        if self._isHeavyOption.value():
            cost = common.Calculator.multiply(
                lhs=cost,
                rhs=self._HeavyCostMultiplier,
                name=f'Heavy {cost.name()}')

        step.setCredits(credits=construction.ConstantModifier(value=cost))

        # Don't apply range modifier if using rocket propelled ammo
        if self._rangeModifierPercentage and not isRocket:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Range,
                modifier=construction.PercentageModifier(
                    value=self._rangeModifierPercentage)))

        # Don't apply penetration modifier if using rocket propelled ammo
        if self._penetrationModifier and not isRocket:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Penetration,
                modifier=construction.ConstantModifier(
                    value=self._penetrationModifier)))

        # Only apply barrel quickdraw modifier to primary weapon. Barrel quickdraw
        # modifiers are handled differently for secondary weapons
        if self._quickdrawModifier and context.isPrimary(sequence=sequence):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=self._quickdrawModifier)))

        if self._physicalSignatureModifier:
            # Only add signature modifier if weapon has a physical signature
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.PhysicalSignature,
                    modifier=construction.ConstantModifier(
                        value=self._physicalSignatureModifier)))

        # Apply barrel damage limit to for energy weapons if required
        isEnergyWeapon = context.hasComponent(
            componentType=gunsmith.PowerPackReceiver,
            sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence)
        if self._maxEnergyWeaponDamageDice and isEnergyWeapon:
            currentMaxDamageDice = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.MaxDamageDice)
            assert(isinstance(currentMaxDamageDice, common.ScalarCalculation)) # Construction logic should enforce this
            if self._maxEnergyWeaponDamageDice.value() < currentMaxDamageDice.value():
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.MaxDamageDice,
                    value=self._maxEnergyWeaponDamageDice))

            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.Damage)
            assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

            wastedDamage = common.Calculator.subtract(
                lhs=damageRoll.dieCount(),
                rhs=self._maxEnergyWeaponDamageDice)
            if wastedDamage.value() > 0:
                damageDiceModifier = common.Calculator.negate(
                    value=wastedDamage,
                    name=f'{self.componentString()} Barrel Damage Dice Wasted Due To Barrel Limit')
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.Damage,
                    modifier=construction.DiceRollModifier(
                        countModifier=damageDiceModifier)))

                step.addNote(
                    note=f'{self.componentString()} barrel has a max damage of {self._maxEnergyWeaponDamageDice.value()}D, each shot will waste {wastedDamage.value()} points of power')

        # Apply heavy barrel modifications
        if self._isHeavyOption.value():
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=self._HeavyQuickdrawModifier)))

            # Only update HeatDissipation if the weapon has the attribute. Not all weapons have it
            # as rules don't specify it
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.HeatDissipation):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.HeatDissipation,
                    modifier=construction.ConstantModifier(
                        value=self._HeavyHeatDissipationModifier)))

            # Only update OverheatThreshold if the weapon has the attribute. Not all weapons have it
            # as rules don't specify it
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.OverheatThreshold):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.OverheatThreshold,
                    modifier=construction.PercentageModifier(
                        value=self._HeavyHeatMisshapeModifierPercentage,
                        roundDown=True)))

            # Only update DangerHeatThreshold if the weapon has the attribute. Not all weapons have it
            # as rules don't specify it
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold,
                    modifier=construction.PercentageModifier(
                        value=self._HeavyHeatMisshapeModifierPercentage,
                        roundDown=True)))

            # Only update DisasterHeatThreshold if the weapon has the attribute. Not all weapons have it
            # as rules don't specify it
            if context.hasAttribute(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold):
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold,
                    modifier=construction.PercentageModifier(
                        value=self._HeavyHeatMisshapeModifierPercentage,
                        roundDown=True)))

        return step

    def _isRocket(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence barrel is part of
        return calibre.isRocket() if calibre else False

class MinimalBarrel(Barrel):
    """
    - Damage: All Damage Dice are converted to D3s rather than D6s. Also Reduce damage by 1 dice for
      high-velocity weapons (only for Conventional Weapons)
    - Range: 5m fixed
    - Quickdraw: +8
    - Penetration: -2
    - Physical Signature: Increased by 2 levels
    - Max Damage: 2D (for Energy Weapons, Field Catalogue p64)
    """
    # NOTE: The example laser pistol with a minimal barrel (Field Catalogue p114) has the barrel range
    # as 50m rather 5m. I've assumed this is a typo as, if it's not, it makes other longer barrels on
    # energy weapons pointless
    # NOTE: A Minimal barrel isn't really a sensible thing to put on a Launcher due to the 5m range
    # (See Launcher and Support Weapon section on p58 of the Field Catalogue). However it doesn't
    # say you CAN'T do it so I've not done anything to prevent it
    # NOTE: Damage dice reduction is only applied to conventional weapons as it's a result of the
    # reduction in projectile velocity caused by the reduction in barrel length (Field Catalogue p42).
    # The damage for launchers come from the payload and how the barrel affects damage of an energy
    # weapon is handled by the Max Damage.
    # NOTE: The damage reduction is applied to Gauss weapons as the rules (Field Catalogue p40) say
    # it's short barrels (and I assume ones longer than that) that don't affect the damage

    _FixedRange = common.ScalarCalculation(
        value=5,
        name='Minimal Barrel Max Range')
    _HighVelocityDamageDiceModifier = common.ScalarCalculation(
        value=-1,
        name='Minimal Barrel High Velocity Damage Dice Count Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Minimal',
            penetrationModifier=-2,
            quickdrawModifier=+8,
            physicalSignatureModifier=+2,
            maxEnergyWeaponDamageDice=2)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        isRocket = self._isRocket(sequence=sequence, context=context)

        # Don't apply range modifier if using rocket propelled ammo
        if not isRocket:
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Range,
                value=self._FixedRange))

        if context.hasComponent(
                componentType=gunsmith.ConventionalReceiver,
                sequence=sequence):
            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.Damage)
            assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

            damageDieCount = damageRoll.dieCount()

            calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
                componentType=gunsmith.ConventionalCalibre,
                sequence=sequence) # Only interested in calibre from sequence barrel is part of
            assert(calibre) # Construction order should prevent this
            if calibre.isHighVelocity():
                damageDieCount = common.Calculator.add(
                    lhs=damageDieCount,
                    rhs=self._HighVelocityDamageDiceModifier,
                    name='Minimal Barrel Damage Die Count')

            damageRoll = common.DiceRoll(
                count=damageDieCount,
                type=common.DieType.D3,
                constant=damageRoll.constant())
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                value=damageRoll))

        return step

class ShortBarrel(Barrel):
    """
    - Cost: 10% of Receiver Cost
    - Weight: 10% of Receiver Weight
    - Damage: Reduce damage by 1 dice for high-velocity weapons (only for non-Gauss Conventional
      Weapons, Field Catalogue p40)
    - Range: -90%
    - Quickdraw: +6
    - Penetration: -1
    - Physical Signature: Increased by 1 level
    - Max Damage: 3D (for Energy Weapons, Field Catalogue p64)
    """
    # NOTE: A Short barrel isn't really a sensible thing to put on a Launcher due to the short range
    # (See Launcher and Support Weapon section on p58 of the Field Catalogue). However it doesn't say
    # you CAN'T do it so I've not done anything to prevent it
    # NOTE: Damage dice reduction is only applied to conventional weapons as it's a result of the
    # reduction in projectile velocity caused by the reduction in barrel length (Field Catalogue p42).
    # The damage for launchers come from the payload and how the barrel affects damage of an energy
    # weapon is handled by the Max Damage.

    _HighVelocityDamageDiceModifier = common.ScalarCalculation(
        value=-1,
        name='Short Barrel High Velocity Damage Dice Count Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Short',
            weightPercentage=10,
            costPercentage=10,
            rangeModifierPercentage=-90,
            penetrationModifier=-1,
            quickdrawModifier=+6,
            physicalSignatureModifier=+1,
            maxEnergyWeaponDamageDice=3)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Apply damage reduction due to barrel length to conventional weapons firing high-velocity
        # non-gauss rounds
        calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence barrel is part of
        if calibre and calibre.isHighVelocity() and not isinstance(calibre, gunsmith.GaussCalibre):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    countModifier=self._HighVelocityDamageDiceModifier)))

        return step

class HandgunBarrel(Barrel):
    """
    - Cost: 15% of Receiver Cost
    - Weight: 20% of Receiver Weight
    - Damage: Reduce damage by 1 dice for high-velocity weapons (only for non-Gauss Conventional
      Weapons, Field Catalogue p40)
    - Range: -80% (except if ammo type is Rocket Projectiles)
    - Quickdraw: +4
    - Penetration: -1
    - Max Damage: 3D (for Energy Weapons, Field Catalogue p64)
    - Core Rules Compatible:
        - Penetration: Modifier not applied
    """
    # NOTE: A Handgun barrel isn't really a sensible thing to put on a Launcher due to the short range
    # (See Launcher and Support Weapon section on p58 of the Field Catalogue). However it doesn't say
    # you CAN'T do it so I've not done anything to prevent it
    # NOTE: Damage dice reduction is only applied to conventional weapons as it's a result of the
    # reduction in projectile velocity caused by the reduction in barrel length (Field Catalogue p42).
    # The damage for launchers come from the payload and how the barrel affects damage of an energy
    # weapon is handled by the Max Damage.
    # NOTE: When the CoreRulesCompatibility rule is applied handgun barrels don't apply a -1 Penetration
    # modifier. This is done so basic handguns generated with the tool can be dropped into games using
    # the core rules without them being massively nerfed compared to the example handguns from the other
    # rule books (Core, Central Supply etc).

    _HandgunBarrelPenetrationModifier = common.ScalarCalculation(
        value=-1,
        name='Handgun Barrel Penetration Modifier')
    _HighVelocityDamageDiceModifier = common.ScalarCalculation(
        value=-1,
        name='Handgun Barrel High Velocity Damage Dice Count Modifier')

    def __init__(self) -> None:
        # Note that range isn't handled by base class due to complex requirement
        super().__init__(
            componentString='Handgun',
            weightPercentage=20,
            costPercentage=15,
            rangeModifierPercentage=-80,
            penetrationModifier=None, # Penetration is handled locally for handgun barrels
            quickdrawModifier=+4,
            maxEnergyWeaponDamageDice=3)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Handgun barrel penetrator modifier is not applied if CoreRulesCompatible is enabled or the
        # weapon is using rocket propelled ammo
        if not context.isRuleEnabled(rule=gunsmith.RuleId.CoreRulesCompatible) and \
                not self._isRocket(sequence=sequence, context=context):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Penetration,
                modifier=construction.ConstantModifier(
                    value=HandgunBarrel._HandgunBarrelPenetrationModifier)))

        # Apply damage reduction due to barrel length to conventional weapons firing high-velocity
        # non-gauss rounds
        calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence barrel is part of
        if calibre and calibre.isHighVelocity() and not isinstance(calibre, gunsmith.GaussCalibre):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    countModifier=self._HighVelocityDamageDiceModifier)))

        return step

class AssaultBarrel(Barrel):
    """
    - Cost: 20% of Receiver Cost
    - Weight: 30% of Receiver Weight
    - Damage: Reduce damage by 1 dice for high-velocity weapons (only for non-Gauss Conventional
      Weapons, Field Catalogue p40)
    - Range: -50%
    - Quickdraw: +2
    - Max Damage: 4D (for Energy Weapons, Field Catalogue p64)
    """
    # NOTE: Damage dice reduction is only applied to conventional weapons as it's a result of the
    # reduction in projectile velocity caused by the reduction in barrel length (Field Catalogue p42).
    # The damage for launchers come from the payload and how the barrel affects damage of an energy
    # weapon is handled by the Max Damage.

    _HighVelocityDamageDiceModifier = common.ScalarCalculation(
        value=-1,
        name='Assault Barrel High Velocity Damage Dice Count Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Assault',
            weightPercentage=30,
            costPercentage=20,
            rangeModifierPercentage=-50,
            quickdrawModifier=+2,
            maxEnergyWeaponDamageDice=4)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Apply damage reduction due to barrel length to conventional weapons firing high-velocity
        # non-gauss rounds
        calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence barrel is part of
        if calibre and calibre.isHighVelocity() and not isinstance(calibre, gunsmith.GaussCalibre):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    countModifier=self._HighVelocityDamageDiceModifier)))

        return step

class CarbineBarrel(Barrel):
    """
    - Cost: 25% of Receiver Cost
    - Weight: 40% of Receiver Weight
    - Damage: -1 for for every 2 full dice of base damage (only for non-Gauss Conventional Weapons,
      Field Catalogue p40)
    - Range: -10%
    - Max Damage: 4D (for Energy Weapons, Field Catalogue p64)
    """
    # NOTE: Damage dice reduction is only applied to conventional weapons as it's a result of the
    # reduction in projectile velocity caused by the reduction in barrel length (Field Catalogue p42).
    # The damage for launchers come from the payload and how the barrel affects damage of an energy
    # weapon is handled by the Max Damage.
    # NOTE: Unlike other barrels the rules don't say the damage reduction is only applied for high
    # velocity rounds (Field Catalogue p42). I'm not sure if this is intentional or not so have chosen
    # to go with the exact wording of the rules.

    _DamageReductionStep = common.ScalarCalculation(
        value=-1,
        name='Carbine Barrel Damage Modifier For Every 2 Whole Dice Of Damage')

    def __init__(self) -> None:
        super().__init__(
            componentString='Carbine',
            weightPercentage=40,
            costPercentage=25,
            rangeModifierPercentage=-10,
            maxEnergyWeaponDamageDice=4)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Apply damage reduction due to barrel length to conventional weapons firing non-gauss
        # rounds. Note that, unlike damage reductions for other barrels, this is applied for low
        # and high velocity rounds as per the rules. THe check that the calibre is not-null is
        # important to prevent the modifier being applied to non-conventional weapons
        calibre: typing.Optional[gunsmith.ConventionalCalibre] = context.findFirstComponent(
            componentType=gunsmith.ConventionalCalibre,
            sequence=sequence) # Only interested in calibre from sequence barrel is part of
        if calibre and not isinstance(calibre, gunsmith.GaussCalibre):
            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.Damage)
            assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

            damageModifier = common.Calculator.multiply(
                lhs=self._DamageReductionStep,
                rhs=common.Calculator.divideFloor(
                    lhs=damageRoll.dieCount(),
                    rhs=common.ScalarCalculation(value=2)),
                name='Carbine Barrel Damage Modifier')

            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Damage,
                modifier=construction.DiceRollModifier(
                    constantModifier=damageModifier)))

        return step

class RifleBarrel(Barrel):
    """
    - Cost: 30% of Receiver Cost
    - Weight: 50% of Receiver Weight
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Rifle',
            weightPercentage=50,
            costPercentage=30)

class LongBarrel(Barrel):
    """
    - Cost: 50% of Receiver Cost
    - Weight: 75% of Receiver Weight
    - Range: +10%
    - Note: Reduces any negative DM due to range by 1 if the firer is using a scope
    """
    _Note = 'Reduces any negative DM due to range by 1 if the firer is using a scope'

    def __init__(self) -> None:
        super().__init__(
            componentString='Long',
            weightPercentage=75,
            costPercentage=50,
            rangeModifierPercentage=+10)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._Note)
        return step

class VeryLongBarrel(Barrel):
    """
    - Cost: 100% of Receiver Cost
    - Weight: 100% of Receiver Weight
    - Range: +25%
    - Note: Reduces any negative DM due to range by 2 if the firer is using a scope
    """
    _Note = 'Reduces any negative DM due to range by 2 if the firer is using a scope'

    def __init__(self) -> None:
        super().__init__(
            componentString='Very Long',
            weightPercentage=100,
            costPercentage=100,
            rangeModifierPercentage=+25)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)
        step.addNote(note=self._Note)
        return step
