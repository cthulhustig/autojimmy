import common
import gunsmith
import typing

class FireRate(gunsmith.FireRateInterface):
    def typeString(self) -> str:
        return 'Fire Rate'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        # Only compatible with weapons that have a receiver.
        return context.hasComponent(
            componentType=gunsmith.ReceiverInterface,
            sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

# I've created the standard fire rate to allow the HeatGeneration attribute to be set
# for non-RF/VRF weapons
class StandardFireRate(FireRate):
    """
    Conventional, Energy Cartridge & Power Pack:
    - Heat Generation: Damage Dice
    Projectors & Launchers
    - Heat Generation: Heat Generation optionally specified at receiv
    All:
    - Auto Heat Generation: Heat Generation + Auto Score
    """
    # NOTE: The wording of the rules around overheating (Field Catalogue p13) seem to say that
    # (with the exception of plasma/fusion weapons) it's only auto fire weapons that can generate
    # enough heat to cause overheating. To allow the user to choose if their weapon generates heat
    # for single shots I've split this into two values, HeatGeneration and AutoHeatGeneration.
    # NOTE: In the case of launchers & projectors the HeatGeneration attribute can optionally be
    # specified when selecting the receiver

    def __init__(self) -> None:
        super().__init__()

    def componentString(self) -> str:
        return 'Standard'

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        if not context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.HeatDissipation):
            # Heat generation must be turned off for this weapon type so there are no modifiers to
            # apply, just add the step as it is and bail
            context.applyStep(
                sequence=sequence,
                step=step)
            return

        heatGeneration = None
        if context.hasComponent(
                componentType=gunsmith.ConventionalReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence):
            # For conventional, energy cartridge and power pack weapons, HeatGeneration is
            # calculated from damage
            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.Damage)
            if damageRoll:
                assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

                heatGeneration = common.Calculator.equals(
                    value=damageRoll.dieCount(),
                    name='Standard Fire Rate Heat Generation')

                step.addFactor(factor=gunsmith.SetAttributeFactor(
                    attributeId=gunsmith.AttributeId.HeatGeneration,
                    value=heatGeneration))
        else:
            # For launchers & projects HeatGeneration is optionally specified when configuring the
            # receiver
            heatGeneration = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.HeatGeneration)

        if heatGeneration:
            autoScore = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.Auto)
            if isinstance(autoScore, common.ScalarCalculation):
                autoHeatGeneration = common.Calculator.add(
                    lhs=heatGeneration,
                    rhs=autoScore,
                    name='Auto Heat Generation')

                step.addFactor(factor=gunsmith.SetAttributeFactor(
                    attributeId=gunsmith.AttributeId.AutoHeatGeneration,
                    value=autoHeatGeneration))

        context.applyStep(
            sequence=sequence,
            step=step)

class AdvancedFireRate(FireRate):
    """
    - Requirement: Not compatible with launches or projectors
    """
    # NOTE: I've added the requirement that advanced fire rates aren't compatible with launchers
    # or projectors as it's really not clear how the AP and damage bonus would be calculated as they
    # don't have a base damage (and without the AP & damage bonuses there is no real point to RF/VRF)
    # NOTE: The rules aren't clear if a RF/VRF can be fired in single shot mode or not, and if it can
    # what its characteristics are (damage, heat etc). As I've split heat generation HeatGeneration and
    # AutoHeatGeneration, i've had to set a value for HeatGeneration otherwise it's just left at 0 and
    # looks odd. I've chosen to set it to the same value as StandardFireRate with the damage calculation
    # applied before the RF/VRF damage bonus is applied. This seems sensible as conceptually the damage
    # bonus is for the increased rate of fire which wouldn't apply if firing a single shot.

    def __init__(
            self,
            componentString: str,
            minAutoScore: typing.Union[int, common.ScalarCalculation],
            damageDiceDivisor: typing.Union[int, common.ScalarCalculation],
            heatMultiplier: typing.Union[int, common.ScalarCalculation]
            ) -> None:
        super().__init__()

        if not isinstance(minAutoScore, common.ScalarCalculation):
            minAutoScore = common.ScalarCalculation(
                value=minAutoScore,
                name=f'{componentString} Fire Rate Minimum Auto Trait Level')

        if not isinstance(damageDiceDivisor, common.ScalarCalculation):
            damageDiceDivisor = common.ScalarCalculation(
                value=damageDiceDivisor,
                name=f'{componentString} Fire Rate Whole Damage Dice For Additional Damage Die')

        if not isinstance(heatMultiplier, common.ScalarCalculation):
            heatMultiplier = common.ScalarCalculation(
                value=heatMultiplier,
                name=f'{componentString} Fire Rate Heat Multiplier')

        self._componentString = componentString
        self._minAutoScore = minAutoScore
        self._damageDiceDivisor = damageDiceDivisor
        self._heatMultiplier = heatMultiplier

    def componentString(self):
        return self._componentString

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with launchers or projectors
        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Only compatible with weapons that have a high enough auto score
        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Auto)
        if not autoScore or not isinstance(autoScore, common.ScalarCalculation):
            return False
        return autoScore.value() >= self._minAutoScore.value()

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.WeaponStep:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Auto)
        assert(isinstance(autoScore, common.ScalarCalculation)) # Construction logic should enforce this

        damageRoll = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage)
        assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

        # AP modifier should be calculated before rapid fire damage dice are added as it's
        # based on the pre-modified number of dice
        apModifier = common.Calculator.equals(
            value=damageRoll.dieCount(),
            name=f'{self.componentString()} Fire Rate AP Modifier')
        if apModifier.value() > 0:
            step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.AP,
                modifier=gunsmith.ConstantModifier(value=apModifier)))

        additionalDamageDice = common.Calculator.divideFloor(
            lhs=damageRoll.dieCount(),
            rhs=self._damageDiceDivisor,
            name=f'{self.componentString()} Fire Rate Additional Damage Dice')
        if additionalDamageDice.value() > 0:
            step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.Damage,
                modifier=gunsmith.DiceRollModifier(
                    countModifier=additionalDamageDice)))

        # Only update HeatGeneration and AutoHeatGeneration if heat rules are enabled for the
        # weapon. It's important that HeatDissipation is checked to determine if the rules are
        # enabled as weapons may not have a HeatGeneration value yet
        if context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.HeatDissipation):
            # Apply damage based HeatGeneration modifier in the same way as for StandardFireRate.
            # This is for when firing a single shot so uses the damage value without any modification
            # for RF/VRF file rate
            damageHeatGeneration = common.Calculator.equals(
                value=damageRoll.dieCount(),
                name='Standard Fire Rate Heat Generation')
            step.addFactor(factor=gunsmith.SetAttributeFactor(
                attributeId=gunsmith.AttributeId.HeatGeneration,
                value=damageHeatGeneration))

            # AutoHeatGeneration should be calculated after additional damage dice are added
            totalDamageDice = common.Calculator.add(
                lhs=damageRoll.dieCount(),
                rhs=additionalDamageDice,
                name=f'{self.componentString()} Fire Rate Total Damage Dice')
            autoHeatGeneration = common.Calculator.add(
                lhs=autoScore,
                rhs=common.Calculator.multiply(
                    lhs=totalDamageDice,
                    rhs=self._heatMultiplier),
                name=f'{self.componentString()} Fire Rate Heat Generation')

            step.addFactor(factor=gunsmith.SetAttributeFactor(
                attributeId=gunsmith.AttributeId.AutoHeatGeneration,
                value=autoHeatGeneration))

        return step

class RFFireRate(AdvancedFireRate):
    """
    - Receiver Cost: x(Auto Score + 2)
    - Receiver Weight: x2
    - Trait: Bulky
    - Trait: AP (AP score equal to the base number of damage dice, calculated before additional rapid-fire damage is added)
    - Trait: RF
    - Damage: "RF weapons do an extra dice of damage per three full dice an automatic weapon of the same calibre would deliver"
    - Heat Generation: Auto Score + (2 x Damage Dice)
    - Requirement: Must have at least Auto 4
    - Powered/Forced Feed:
        - Receiver Cost: x3
        - Receiver Weight: x3
        - Requirement: Only feasible on Longarm, Light Support Weapon or Support Weapon
    """
    # NOTE: The rules around how a RF weapon is created (Field Catalogue p32) are incredibly confusing.
    # It's not clear if you MUST have a forced feed or if it's just enough to meet the minimum Auto score.
    # I've gone with the approach of not making a forced feed mandatory, the user can add on if they (or
    # their Referee) wants to
    # NOTE: I'm treating RF as a flag trait when actually it's a modifier on the Auto trait. The Rapid
    # Fire description (Field Catalogue p32) says "Rapid-fire capability is denoted by the RF
    # code after the weapon’s Auto score"
    # NOTE: It's not clear what exactly the RF description means by "RF weapons do an extra dice of damage
    # per three full dice an automatic weapon of the same calibre would deliver". It could mean that the
    # damage bonus is based purely on the base damage for the calibre, however that would seem odd as it
    # wouldn't take into account damage reduction from things like the barrel.
    # In reality the kinds of damage reduction introduced by components would be caused by a loss of energy
    # in the projectile or energy beam before it leaves the weapon. Logically this would suggest that any
    # bonus that comes from increasing the number of shots leaving the weapon would have to be based on the
    # damage value after those losses had been applied.
    # In the case of damage increases from the base calibre value (e.g. if High Quality is used) then it's
    # less clear how this would logically work, however it doesn't seem unreasonable that the RF/VRF modifiers
    # should include it (the user would have to pay for both after all).
    # It's even less clear if damage modifiers from ammunition type should be taken into account. The VRF
    # description says "...delivers an extra dice of damage per two full base dice indicated by ammunition type.
    # For example, a 5.56mm machinegun has Auto 3 and does 3D damageI've chosen". The fact that it mentions
    # ammo type then goes on to specify the calibre but no ammo type suggests they mean calibre rather than ammo
    # type. I've gone with NOT taking ammo type modifiers into account.
    # NOTE: Creating a RF weapon by mounting two regular weapons together is handled by the Multi-Mount code
    # NOTE: Multiplier for powered/forced feed is handled by Feed code

    _WeightMultiplier = common.ScalarCalculation(
        value=2,
        name='RF Receiver Weight Multiplier')
    _CostIncreaseConstant = common.ScalarCalculation(
        value=2,
        name='RF Receiver Cost Increase Constant')

    def __init__(self) -> None:
        super().__init__(
            componentString='RF',
            minAutoScore=4,
            damageDiceDivisor=3,
            heatMultiplier=2)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Auto)
        assert(isinstance(autoScore, common.ScalarCalculation)) # Construction logic should enforce this

        step.setWeight(weight=gunsmith.MultiplierModifier(
            value=self._WeightMultiplier))

        costMultiplier = common.Calculator.add(
            lhs=autoScore,
            rhs=self._CostIncreaseConstant,
            name=f'RF Receiver Cost Multiplier')
        step.setCredits(credits=gunsmith.MultiplierModifier(
            value=costMultiplier))

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.RF))

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.Bulky))

        return step


class VRFFireRate(AdvancedFireRate):
    """
    - Trait: AP (AP score equal to the base number of damage dice, calculated before additional rapid-fire damage is added)
    - Trait: VRF
    - Damage: 1 extra dice of damage per 2 full dice of damage of pre-VRF weapon
    - Heat Generation: Auto Score + (3 x Damage Dice)
    - Requirement: Must have at least Auto 6
    - VRF Feed:
        - Receiver Cost: x5
        - Receiver Weight: x5
        - Trait: Very Bulky
        - Requirement: Only feasible on Longarm, Light Support Weapon or Support Weapon
    """
    # NOTE: In the same way as with RF, I'm not making a VRF feed mandatory
    # NOTE: In the same way as with RF, I'm treating VRF as a flag trait when it's actually a
    # modifier on the Auto trait
    # NOTE: The VRF description is HORRIBLY ambiguous (Field Catalogue p32). The description for RF
    # has an x(Auto Score + 2) cost and x2 weight modifiers along with the Bulky trait for just the
    # RF capability (independent of any cost/weight multipliers for a powered feed), however the VRF
    # description doesn't have an equivalent which seems strange. I've added options so the user can
    # specify values if they want to
    # NOTE: Creating a VRF weapon by mounting two RF weapons together is handled by the Multi-Mount code
    # NOTE: Multiplier for powered/forced feed is handled by Feed code

    _ApplyCostWeightOptionDescription = \
        '<p>Specify if the VRF capability applies a receiver cost and weight multiplier in ' \
        'the same way RF capability does. This is independent of any multipliers applied for ' \
        'powered or VRF feeds.</p>' \
        '<p>The rules regarding RF/VRF capability on p32 of the Field Catalog are a bit unclear. ' \
        'They say that the RF capability causes a x2 receiver weight and x(Auto Score + 2) ' \
        'receiver cost multiplier, this seems to be independent of the x3 cost & weight ' \
        'multipliers it specifies for using a powered feed. The VRF description has no equivalent ' \
        'cost/weight multiplier for the VRF capability, just the modifiers for using a VRF feed. ' \
        'It seems unusual that this this kind of modifier would be applied to RF but not VRF. This ' \
        'option allows you to choose to the cost and weight modifiers that are applied based  on ' \
        'how you and your Referee interpret the rules.</p>'

    _CostAutoModifierOptionDescription = \
        '<p>Specify the modifier that will be added to the weapons Auto Score in order to ' \
        'calculate the cost multiplier for VRF capability.</p>' \
        '<p>The rules regarding RF/VRF capability on p32 of the Field Catalog are a bit unclear. ' \
        'They say that RF capability causes an x(Auto Score + 2) receiver cost multiplier, ' \
        'however they don\'t have an equivalent for VRF capability. This option allows you to ' \
        'specify the modifier that will be added to the Auto Score when calculating the cost ' \
        'multiplier based on how you and your Referee interpret the rules.</p>'

    _WeightMultiplierOptionDescription = \
        '<p>Specify the receiver weight multiplier for VRF capability.</p>' \
        '<p>The rules regarding RF/VRF capability on p32 of the Field Catalog are a bit unclear. ' \
        'They say that RF capability causes an x2 receiver weight multiplier, however they ' \
        'don\'t have an equivalent for VRF capability. This option allows you to specify the ' \
        'receiver cost multiplier based on how you and your Referee interpret the rules.</p>'

    _BulkLevelOptionDescription = \
        '<p>Specify if the the VRF capability gives the weapon the Bulky/Very Bulky Trait.</p>' \
        '<p>The rules regarding RF/VRF and powered/forced feeds on p32 of the Field Catalog ' \
        'are a bit unclear. They say that the RF capability gives the weapon the Bulky trait,  ' \
        'and this seems to be regardless of if a powered feed is being used, however the VRF ' \
        'description only says the weapon gains the Very Bulky trait if a VRF feed is being ' \
        'used. This allows you to specify a value based on how you and your Referee interpret ' \
        'the rules.</p>'

    def __init__(self) -> None:
        super().__init__(
            componentString='VRF',
            minAutoScore=6,
            damageDiceDivisor=2,
            heatMultiplier=3)

        self._applyCostWeightOption = gunsmith.BooleanComponentOption(
            id='ApplyCostWeightModifiers',
            name='Apply Cost & Weight Modifiers',
            value=False,
            description=VRFFireRate._ApplyCostWeightOptionDescription)

        self._costAutoModifierOption = gunsmith.IntegerComponentOption(
            id='CostModifier',
            name='Receiver Cost Auto Modifier',
            value=2, # Default to RF value
            minValue=0,
            description=VRFFireRate._CostAutoModifierOptionDescription)

        self._weightMultiplierOption = gunsmith.FloatComponentOption(
            id='WeightMultiplier',
            name='Receiver Weight Multiplier',
            value=2.0, # Default to RF value
            minValue=1.0,
            description=VRFFireRate._WeightMultiplierOptionDescription)

        self._bulkLevelOption = gunsmith.EnumComponentOption(
            id='BulkLevel',
            name='Bulky/Very Bulky Trait',
            type=gunsmith.AttributeId,
            value=gunsmith.AttributeId.Bulky, # Default to Bulky as that's what the RF capability gives
            isOptional=True,
            options=[gunsmith.AttributeId.Bulky, gunsmith.AttributeId.VeryBulky],
            description=VRFFireRate._BulkLevelOptionDescription)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._applyCostWeightOption)
        if self._applyCostWeightOption.value():
            options.append(self._weightMultiplierOption)
            options.append(self._costAutoModifierOption)
        options.append(self._bulkLevelOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        if self._applyCostWeightOption.value():
            autoScore = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.AttributeId.Auto)
            assert(isinstance(autoScore, common.ScalarCalculation)) # Construction logic should enforce this

            weightMultiplier = common.ScalarCalculation(
                value=self._weightMultiplierOption.value(),
                name='Specified VRF Receiver Weight Multiplier')
            step.setWeight(weight=gunsmith.MultiplierModifier(value=weightMultiplier))

            costConstant = common.ScalarCalculation(
                value=self._costAutoModifierOption.value(),
                name='Specified VRF Receiver Cost Auto Modifier')
            costMultiplier = common.Calculator.add(
                lhs=autoScore,
                rhs=costConstant,
                name=f'VRF Receiver Cost Multiplier')
            step.setCredits(credits=gunsmith.MultiplierModifier(
                value=costMultiplier))

        step.addFactor(factor=gunsmith.SetAttributeFactor(
            attributeId=gunsmith.AttributeId.VRF))

        bulkLevel = self._bulkLevelOption.value()
        if bulkLevel:
            step.addFactor(factor=gunsmith.SetAttributeFactor(attributeId=bulkLevel))

        return step
