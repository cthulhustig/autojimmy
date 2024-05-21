import common
import construction
import gunsmith
import typing

# The finalisation component is a hack to perform various modifications when the user specified
# portion of the weapon has been generated. When displaying the manifest the finalisation stages
# aren't shown so finalisation shouldn't do anything that affects the cost or weight of the weapon
class Finalisation(gunsmith.WeaponComponentInterface):
    _ProjectorMishapTechLevelDivisor = common.ScalarCalculation(
        value=2,
        name='Projector Weapon Mishap Threshold Tech Level Divisor')
    _GaussMishapTechLevelModifier = common.ScalarCalculation(
        value=4,
        name='Gauss Weapon Mishap Threshold Tech Level Modifier')
    _ProjectileMishapTechLevelModifier = common.ScalarCalculation(
        value=8,
        name='Projectile Weapon Mishap Threshold Tech Level Modifier')
    _SignatureDetectionModifierMap = {
        gunsmith.Signature.Minimal: common.ScalarCalculation(value=-6, name='Minimal Signature Detection Modifier'),
        gunsmith.Signature.Small: common.ScalarCalculation(value=-4, name='Small Signature Detection Modifier'),
        gunsmith.Signature.Low: common.ScalarCalculation(value=-2, name='Low Signature Detection Modifier'),
        gunsmith.Signature.Normal: common.ScalarCalculation(value=0, name='Normal Signature Detection Modifier'),
        gunsmith.Signature.High: common.ScalarCalculation(value=+2, name='High Signature Detection Modifier'),
        gunsmith.Signature.VeryHigh: common.ScalarCalculation(value=+4, name='Very High Signature Detection Modifier'),
        gunsmith.Signature.Extreme: common.ScalarCalculation(value=+6, name='Extreme Signature Detection Modifier')
    }
    _DistractionTargetNumberMap = {
        gunsmith.Distraction.Small: common.ScalarCalculation(value=4, name='Small Distraction Resistance Target Number'),
        gunsmith.Distraction.Minor: common.ScalarCalculation(value=6, name='Minor Distraction Resistance Target Number'),
        gunsmith.Distraction.Typical: common.ScalarCalculation(value=8, name='Typical Distraction Resistance Target Number'),
        gunsmith.Distraction.Potent: common.ScalarCalculation(value=10, name='Potent Distraction Resistance Target Number'),
        gunsmith.Distraction.Overwhelming: common.ScalarCalculation(value=12, name='Overwhelming Distraction Resistance Target Number')
    }

    def componentString(self) -> str:
        return 'Finalisation'

    def typeString(self) -> str:
        return 'Finalisation'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return True

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
        self._createHeavyHandgunCalibreStep(sequence=sequence, context=context)
        self._createRecoilModifierStep(sequence=sequence, context=context)
        self._createRangeModifierNotes(sequence=sequence, context=context)
        self._createAutoModifierNotes(sequence=sequence, context=context)
        self._createMalfunctionDMStep(sequence=sequence, context=context)
        self._createMishapThresholdStep(sequence=sequence, context=context)
        self._createPenetrationStep(sequence=sequence, context=context)
        self._createRemoveRedundantBulkyTrait(sequence=sequence, context=context) # Must be applied after heavy handgun calibre step
        self._createTraitNotes(sequence=sequence, context=context)
        self._createSpecificLocationNotes(sequence=sequence, context=context)

    """
    Heavy Handgun Calibre
    - Trait: Bulky (see note)
    """
    # NOTE: The wording rules say the following regarding the Bulky trait
    # "Heavy handguns gain the Bulky trait. Larger weapons using heavy handgun ammunition are Bulky
    # unless they weigh more than 2kg or are compensated in some manner."
    # I've taken compensation to be either RecoilCompensationFeature, StabilisationWeaponFeature but
    # not GraviticSystemAccessory. I don't think GraviticSystemAccessory would apply in this case as
    # it seems to be for compensating for weight not recoil (if anything reducing the weight to near
    # zero would make it harder to control the recoil).

    def _createHeavyHandgunCalibreStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        if not context.hasComponent(
                componentType=gunsmith.HeavyHandgunCalibre,
                sequence=sequence):
            return # Only applies to HeavyHandgunCalibre

        if context.hasComponent(
                componentType=gunsmith.RecoilCompensationFeature,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.StabilisationWeaponFeature,
                sequence=sequence):
            return # Bulky doesn't apply if weapon is compensated

        isBulky = False
        if context.hasComponent(
                componentType=gunsmith.HandgunReceiver,
                sequence=sequence):
            # Uncompensated handguns are always bulky
            isBulky = True
        elif context.totalWeight(sequence=None).value() <= 2: # Use whole weapon weight
            # Larger uncompensated weapons are only bulky if they don't weigh more than 2kg
            isBulky = True

        if not isBulky:
            return # Nothing to do

        step = gunsmith.WeaponStep(
            name=f'Uncompensated Heavy Handgun Calibre',
            type='Usability',
            factors=[construction.SetAttributeFactor(attributeId=gunsmith.WeaponAttributeId.Bulky)])
        context.applyStep(
            sequence=sequence,
            step=step)

    """
    Recoil Modifiers
    - Requirement: Only applies to weapons with a Recoil attribute
    - Note: DM-1 to Attack Rolls for every point the users gun skill is below the recoil level
    - Automatic Weapons
        - Auto Recoil: Recoil + Auto Score
    """
    # NOTE: The rules around recoil (Field Catalogue p32) seem brutal if you're untrained in Gun Combat. Your
    # bog standard light pistol has a recoil of 0. That means an untrained person (who's already at DM-3 for
    # being untrained) gets an additional DM-3 modifier for recoil (skill - weapon recoil)

    def _createRecoilModifierStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        recoil = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Recoil)
        if not isinstance(recoil, common.ScalarCalculation):
            return # Nothing to do

        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Auto)

        step = gunsmith.WeaponStep(
            name=f'Recoil ({recoil.value()})',
            type='Usability')

        step.addNote(
            note=f'{"When making a normal attack, if" if autoScore else "If"} the users Gun Combat skill is lower than {recoil.value()} then they suffer a negative DM equal to the difference between the values.')

        autoRecoil = None
        if isinstance(autoScore, common.ScalarCalculation):
            autoRecoil = common.Calculator.add(
                lhs=recoil,
                rhs=autoScore,
                name='Auto Recoil')
            step.addFactor(construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AutoRecoil,
                value=autoRecoil))

            step.addNote(
                note=f'When making a fully-automatic or burst fire attack, if the users Gun Combat skill is lower than {autoRecoil.value()} then they suffer a negative DM equal to the difference between the values.')

        context.applyStep(
            sequence=sequence,
            step=step)

    """
    Range Modifiers (Core Rules p73)
    - Note: Short Range = DM+1 when <= 1/4 range
    - Note: Long Range = DM-2 when > base range and < range x2
    - Note: Extreme Range = DM-4 when >= range x2 and < range x4
    - Note: Unless weapon has the Scope trait ranges > 100m are treated as extreme (300m in non-combat situation)
    """

    def _createRangeModifierNotes(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        baseRange = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Range)
        if not baseRange or not isinstance(baseRange, common.ScalarCalculation):
            return # Can't calculate range modifiers so nothing to do

        hasScope = context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Scope)

        noScopeShort, noScopeLong, noScopeExtreme = \
            Finalisation._generateRangeNotes(
                hasScope=False, # Generate ranges notes without a scope
                baseRange=baseRange.value())

        withScopeShort = None
        withScopeLong = None
        withScopeExtreme = None
        if hasScope:
            withScopeShort, withScopeLong, withScopeExtreme = \
                Finalisation._generateRangeNotes(
                    hasScope=True, # Generate ranges notes when using scope
                    baseRange=baseRange.value())
            if withScopeShort == noScopeShort:
                withScopeShort = None
            if withScopeLong == noScopeLong:
                withScopeLong = None
            if withScopeExtreme == noScopeExtreme:
                withScopeExtreme = None

        formatNoScopeSuffix = lambda hasAlt: ' (Without Scope)' if hasAlt else ' (With And Without Scope)' if hasScope else ''

        if noScopeShort:
            step = gunsmith.WeaponStep(
                name='Short' + formatNoScopeSuffix(hasAlt=withScopeShort != None),
                type='Range',
                notes=[noScopeShort])
            context.applyStep(
                sequence=sequence,
                step=step)

        if withScopeShort:
            step = gunsmith.WeaponStep(
                name='Short (With Scope)',
                type='Range',
                notes=[withScopeShort])
            context.applyStep(
                sequence=sequence,
                step=step)

        if noScopeLong:
            step = gunsmith.WeaponStep(
                name='Long' + formatNoScopeSuffix(hasAlt=withScopeLong != None),
                type='Range',
                notes=[noScopeLong])
            context.applyStep(
                sequence=sequence,
                step=step)

        if withScopeLong:
            step = gunsmith.WeaponStep(
                name='Long (With Scope)',
                type='Range',
                notes=[withScopeLong])
            context.applyStep(
                sequence=sequence,
                step=step)

        if noScopeExtreme:
            step = gunsmith.WeaponStep(
                name='Extreme' + formatNoScopeSuffix(hasAlt=withScopeExtreme != None),
                type='Range',
                notes=[noScopeExtreme])
            context.applyStep(
                sequence=sequence,
                step=step)

        if withScopeExtreme:
            step = gunsmith.WeaponStep(
                name='Extreme (With Scope)',
                type='Range',
                notes=[withScopeExtreme])
            context.applyStep(
                sequence=sequence,
                step=step)

    @staticmethod
    def _generateRangeNotes(
            hasScope: bool,
            baseRange: int,
            ) -> typing.Tuple[typing.Optional[str], typing.Optional[str], typing.Optional[str]]:
        _CombatRangeThreshold = 100
        _NonCombatRangeThreshold = 300

        shortRange = baseRange / 4
        extremeRange = baseRange * 2
        maxRange = baseRange * 4

        baseRangeString = common.formatNumber(number=baseRange)
        shortRangeString = common.formatNumber(number=shortRange)
        extremeRangeString = common.formatNumber(number=extremeRange)
        maxRangeString = common.formatNumber(number=maxRange)

        shortRangeNote = None
        if hasScope or shortRange < _CombatRangeThreshold:
            shortRangeNote = f'DM+1 to attack rolls at ranges <= {shortRangeString}m'
        elif shortRange >= _CombatRangeThreshold and shortRange < _NonCombatRangeThreshold:
            shortRangeNote = f'DM+1 to attack rolls at ranges <= {_CombatRangeThreshold}m in combat situations, or at ranges <= {shortRangeString}m in non-combat situations'
        else:
            shortRangeNote = f'DM+1 to attack rolls at ranges <= {_CombatRangeThreshold}m, or at ranges <= {_NonCombatRangeThreshold}m in non-combat situations'

        longRangeNote = None
        if hasScope or extremeRange <= _CombatRangeThreshold:
            longRangeNote = f'DM-2 to attack rolls at ranges > {baseRangeString}m and < {extremeRangeString}m'
        elif extremeRange >= _CombatRangeThreshold and extremeRange < _NonCombatRangeThreshold:
            if baseRange < _CombatRangeThreshold:
                longRangeNote = f'DM-2 to attack rolls at ranges > {baseRangeString}m and < {_CombatRangeThreshold}m in combat situations, or at ranges > {baseRangeString}m and < {extremeRangeString}m in non-combat situations'
            else:
                # The base range is over 100m so there is no long range modifier in combat
                # situations as everything is treated as extreme. There is however a long
                # range modifier in non-combat situations for ranges between the base and
                # extreme range
                longRangeNote = f'DM-2 to attack rolls at ranges > {baseRangeString}m and < {extremeRangeString}m in non-combat situations'
        elif baseRange < _CombatRangeThreshold:
            longRangeNote = f'DM-2 to attack rolls at ranges > {baseRangeString}m and < {_CombatRangeThreshold}m in combat situations, or at ranges > {baseRangeString}m and < {_NonCombatRangeThreshold}m in non-combat situations'
        elif baseRange < _NonCombatRangeThreshold:
            # The base range is over 100m so there is no long range modifier in combat
            # situations as everything is treated as extreme. There is however a long
            # range modifier in non-combat situations for ranges between the base range
            # and 300m
            longRangeNote = f'DM-2 to attack rolls at ranges > {baseRangeString}m and < {_NonCombatRangeThreshold}m in non-combat situations'
        else:
            # The base range of the weapon is over 300m so there is no long range modifier for combat or non-combat situations
            pass

        extremeRangeNote = None
        if hasScope or extremeRange <= _CombatRangeThreshold:
            extremeRangeNote = f'DM-4 to attack rolls at ranges >= {extremeRangeString}m and <= {maxRangeString}m'
        elif extremeRange < _NonCombatRangeThreshold:
            extremeRangeNote = f'DM-4 to attack rolls at ranges >= {_CombatRangeThreshold}m and <= {maxRangeString}m in combat situations, or at ranges >= {extremeRangeString}m and <= {maxRangeString}m in non-combat situations'
        else:
            extremeRangeNote = f'DM-4 to attack rolls at ranges >= {_CombatRangeThreshold}m and <= {maxRangeString}m in combat situations, or at ranges >= {_NonCombatRangeThreshold}m and <= {maxRangeString}m in non-combat situations'

        return (shortRangeNote, longRangeNote, extremeRangeNote)

    """
    Auto Fire Modifiers
    - Requirement: Only applies to weapons with an Auto score
    - Burst Attack (Core Rules p75)
        - Note: Add the Auto score to damage. This uses a number of rounds equal to the Auto score.
    - Full Auto Attack (Core Rules p75)
        - Requirement: Requires fully automatic or mechanical rotary mechanism
        - Note: Make a number of attacks equal to the Auto score. These attacks can be made against
          separate targets so long as they are all within six metres of one another. Full auto uses a
          number of rounds equal to three times the Auto score.
    - Generated Heat (Field Catalogue p13)
        - A weapon making autofire attacks or one that produces a great deal of thermal energy such as
          a plasma or fusion gun, generates an amount of Heat equal to its damage dice each round, plus
          its Auto score
    """
    # NOTE: I've added the requirement that full auto attack note requires the fully automatic or mechanical
    # rotary mechanism. The rules around auto attacks in the core rules say any weapon with an Auto score can
    # make burst or full auto attacks. Obviously that's not taking into account the new rules where you have
    # burst capable and fully automatic mechanism. On Field Catalogue p34 it says increasing the Auto score of
    # burst capable weapon doesn't allow it to fire full auto but it does allow it to increase the damage
    # modifier gained from firing a burst. The rules don't cover if weapon that gains the auto trait from a
    # mechanical rotary mechanism would allow full auto or not so I've included the note for them and it's up
    # to the user to decide.
    # NOTE: The rules for burst fire and full auto get a little weird if you have Auto 1. Technically this
    # can happen with a mechanical rotary mechanism and 2/3 barrels (and possibly other ways). With Auto 1
    # there is no reason not to fire every round as a burst as it gives +1 damage but still only uses a single
    # round. Conversely there is never a reason to use full auto as it uses 3 times the ammo for no extra attacks.
    # NOTE: The way the rules are worded (Field Catalogue p13) heat equal to damage dice + auto score is added
    # each _round_, this is important as it means when firing full auto the amount of heat does not go up by the
    # number of attacks being made.

    def _createAutoModifierNotes(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        autoScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Auto)
        if not isinstance(autoScore, common.ScalarCalculation):
            return
        autoScore = autoScore.value()

        heatGeneration = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.AutoHeatGeneration)
        if not isinstance(heatGeneration, common.ScalarCalculation):
            return
        heatGeneration = heatGeneration.value()

        burstFireNote = f'Firing a burst gives Damage +{autoScore}, uses {autoScore} rounds of ammunition and generates Heat +{heatGeneration}.'
        step = gunsmith.WeaponStep(
            name=f'Burst Fire',
            type='Auto Fire',
            notes=[burstFireNote])
        context.applyStep(
            sequence=sequence,
            step=step)

        if autoScore > 1:
            hasRequiredMechanism = context.hasComponent(
                componentType=gunsmith.FullyAutomaticMechanism,
                sequence=sequence) \
                or context.hasComponent(
                    componentType=gunsmith.MechanicalRotaryMechanism,
                    sequence=sequence)

            if hasRequiredMechanism:
                fullAutoNote = f'Firing full auto allows {autoScore} attacks to be made in a round, uses {autoScore * 3} rounds of ammunition and generates Heat +{heatGeneration}. ' + \
                    'These attacks can be made against separate targets so long as they are all within 6m of one another.'
                step = gunsmith.WeaponStep(
                    name=f'Full Auto',
                    type='Auto Fire',
                    notes=[fullAutoNote])
                context.applyStep(
                    sequence=sequence,
                    step=step)

    """
    Malfunction DM (Field Catalogue p8)
    - Plus any modifiers for Bulwarked and Rugged
    - Minus weapons damage
    - Minus any Hazardous and Ramshackle scores the weapon has
    """
    # NOTE: The list of modifiers to apply when rolling against the Malfunction table (Field
    # Catalogue p8) don't say to include Ramshackle, however the description for Ramshackle does
    # say that it's applied as a DM to the result of malfunction rolls. This is backed up by the
    # description for the low quality receiver feature (Field Catalogue p34) which say 1 point of
    # Ramshackle effectively adds a point if Inaccurate and and a point Hazardous, and the rules
    # are clear Hazardous is applied as a modifier when rolling against the Malfunction table.

    def _createMalfunctionDMStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        malfunctionModifiers = []

        bulwarked = context.findFirstComponent(
            componentType=gunsmith.BulwarkedFeature,
            sequence=sequence) # Only interested in the sequence being calculated
        if bulwarked:
            assert(isinstance(bulwarked, gunsmith.BulwarkedFeature))
            bulwarkedModifier = common.ScalarCalculation(
                value=bulwarked.levelCount(),
                name='Bulwarked Malfunction Modifier')
            malfunctionModifiers.append(bulwarkedModifier)

        if context.hasComponent(
                componentType=gunsmith.RuggedFeature,
                sequence=sequence):
            ruggedModifier = common.ScalarCalculation(
                value=+2,
                name='Rugged Malfunction Modifier')
            malfunctionModifiers.append(ruggedModifier)

        damage = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Damage)
        if damage:
            assert(isinstance(damage, common.DiceRoll))
            malfunctionModifiers.append(common.Calculator.negate(
                value=damage.dieCount()))

        hazardousScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Hazardous)
        if hazardousScore:
            assert(isinstance(hazardousScore, common.ScalarCalculation))
            malfunctionModifiers.append(hazardousScore)

        ramshackleScore = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Ramshackle)
        if ramshackleScore:
            assert(isinstance(ramshackleScore, common.ScalarCalculation))
            malfunctionModifiers.append(ramshackleScore)

        malfunctionDM = common.Calculator.sum(
            values=malfunctionModifiers,
            name='Malfunction DM')

        step = gunsmith.WeaponStep(
            name='Malfunction DM',
            type='Resilience',
            factors=[construction.SetAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.MalfunctionDM,
                value=malfunctionDM)])
        context.applyStep(
            sequence=sequence,
            step=step)

    """
    - Mishap Threshold (Field Catalogue p22)
        - TL / 2 for Flamethrowers and similar weapons containing hazardous substances
        - TL for Lasers and similarly complex weapons that require precise alignment
        - TL + 4 for Gauss, plasma, fusion and similar complex but robust weapons
        - TL + 8 Conventional firearms and similar strongly built mechanical devices
        - TL + 12 Hand weapons and similar strongly built items with few or no moving parts
    - Note: If the damage inflicted on the weapon in a single hit is greater than the mishap
    threshold then a Malfunction occurs
    - Note: If the damage inflicted on the weapon in a single hit is over 3 times the mishap
    threshold then the weapon is taken out of action and requires major repairs
    - Note: If the damage inflicted on the weapon in a single hit is over 10 times the mishap
    threshold then the weapon is completely destroyed
    """
    # NOTE: The rules covering mishaps (Field Catalogue p22) don't explicitly say how to work out
    # what happens if a mishap occurs (i.e. if the damage inflicted is over the mishap threshold
    # but less that 3 times the threshold). My reading of the mishap description and descriptions
    # for the Hazardous, Ramshackle & traits is, if a mishap occurs, then you roll against the
    # Malfunction table to determine the outcome.
    # NOTE: I've made some assumptions when it comes to mishap band different weapons should fall
    # into. I've assumed all projectors should have a value of TL/2, it's not clear if "hazardous
    # substances" only refers to when using a flammable contents fuel or if it's any projector due
    # to the use of a pressurised propellant. I'm treating launchers as conventional firearms and
    # giving them TL + 8 due to their construction being so similar. I've assumed "Hand weapons"
    # refers to things like swords rather than pistols.
    # NOTE: The mishap rules mention that armour can be used to make a weapon safer (Field
    # Catalogue p23). I assume it's talking about the armour receiver feature but it doesn't say how
    # the armour level affects the mishap threshold. The most obvious thing would be for it to be
    # added as a modifier so I've gone with that.

    def _createMishapThresholdStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        techLevel = common.ScalarCalculation(
            value=context.techLevel(),
            name='Weapon Construction Tech Level')

        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            mishapThreshold = common.Calculator.divideFloor(
                lhs=techLevel,
                rhs=self._ProjectorMishapTechLevelDivisor)
        elif context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.EnergyCartridgeReceiver,
                sequence=sequence):
            mishapThreshold = common.Calculator.equals(value=techLevel)
        elif context.hasComponent(
                componentType=gunsmith.GaussCalibre,
                sequence=sequence):
            mishapThreshold = common.Calculator.add(
                lhs=techLevel,
                rhs=self._GaussMishapTechLevelModifier)
        elif context.hasComponent(
                componentType=gunsmith.ConventionalReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence):
            mishapThreshold = common.Calculator.add(
                lhs=techLevel,
                rhs=self._ProjectileMishapTechLevelModifier)
        else:
            assert(False)

        armourLevel = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Armour)
        if isinstance(armourLevel, common.ScalarCalculation):
            mishapThreshold = common.Calculator.add(
                lhs=mishapThreshold,
                rhs=armourLevel)

        mishapThreshold = common.Calculator.rename(
            value=mishapThreshold,
            name='Mishap Threshold')
        outOfActionThreshold = common.Calculator.multiply(
            lhs=mishapThreshold,
            rhs=common.ScalarCalculation(value=3),
            name='Out Of Action Threshold')
        destroyedThreshold = common.Calculator.multiply(
            lhs=mishapThreshold,
            rhs=common.ScalarCalculation(value=10),
            name='Destroyed Threshold')

        step = gunsmith.WeaponStep(
            name=f'Mishap',
            type='Resilience',
            notes=[
                f'The weapon suffers a malfunction if it takes > {mishapThreshold.value()} and < {outOfActionThreshold.value()} points of damage in a single hit. Roll against the Malfunction table on p8 of the Field Catalogue.',
                f'The weapon is put out of action and requires major repairs if it takes >= {outOfActionThreshold.value()} and < {destroyedThreshold.value()} points of damage in a single hit.',
                f'The weapon is completely destroyed if it takes >= {destroyedThreshold.value()} points of damage in a single hit.',
            ])
        context.applyStep(
            sequence=sequence,
            step=step)

    """
    Penetration Modifiers
    - Requirement: Penetration based AP/LoPen modifier doesn't apply to Launchers or Projectors
    """
    # NOTE: I've added the requirement that Penetration doesn't affect Launchers/Projectors as their
    # damage comes from the grenade/fuel so there is no penetration as such. Those weapons will
    # still have a Penetration attribute as it's to much faff ot update stuff like the barrel code
    # to only set Penetration for some weapon types

    def _createPenetrationStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence) \
            or context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            # Penetration doesn't affect Launchers and Projectors
            return

        # Convert Penetration attribute to LoPen/AP trait (Field Catalogue p18)
        penetration = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Penetration)
        if not penetration:
            return # Nothing to do

        penetration = penetration.value()
        factors = []
        if penetration < 0:
            loPenModifier = None
            if penetration <= -4:
                loPenModifier = common.ScalarCalculation(
                    value=5,
                    name='Penetration <= -4 Lo-Pen Modifier')
            elif penetration == -3:
                loPenModifier = common.ScalarCalculation(
                    value=4,
                    name='Penetration -3 Lo-Pen Modifier')
            elif penetration == -2:
                loPenModifier = common.ScalarCalculation(
                    value=3,
                    name='Penetration -2 Lo-Pen Modifier')
            elif penetration == -1:
                loPenModifier = common.ScalarCalculation(
                    value=2,
                    name='Penetration -1 Lo-Pen Modifier')
            assert(loPenModifier)

            factors.append(construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.LoPen,
                modifier=construction.ConstantModifier(value=loPenModifier)))
        elif penetration > 0:
            damageRoll = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.Damage)
            assert(isinstance(damageRoll, common.DiceRoll)) # Construction logic should enforce this

            apModifier = None
            damageModifier = None
            if penetration == +1:
                # AP 1 per full dice of damage
                apModifier = common.Calculator.equals(
                    value=damageRoll.dieCount(),
                    name='Penetration +1 AP Modifier')
            elif penetration == +2:
                # AP 1 plus 1 per full dice of damage, -1 damage per 2 full dice of damage
                apModifier = common.Calculator.add(
                    lhs=common.ScalarCalculation(value=1),
                    rhs=damageRoll.dieCount(),
                    name='Penetration +2 AP Modifier')
                damageModifier = common.Calculator.multiply(
                    lhs=common.ScalarCalculation(
                        value=-1,
                        name='Penetration +2 Damage Modifier Per 2 Full Dice Of Damage'),
                    rhs=common.Calculator.divideFloor(
                        lhs=damageRoll.dieCount(),
                        rhs=common.ScalarCalculation(value=2)),
                    name='Penetration +2 Damage Modifier')
            elif penetration == +3:
                # AP 3 plus 3 per 2 full dice of damage, -2 damage per 3 full dice of damage
                apModifier = common.Calculator.add(
                    lhs=common.ScalarCalculation(value=3),
                    rhs=common.Calculator.multiply(
                        lhs=common.ScalarCalculation(
                            value=3,
                            name='Penetration +3 AP Modifier Per 2 Full Dice Of Damage'),
                        rhs=common.Calculator.divideFloor(
                            lhs=damageRoll.dieCount(),
                            rhs=common.ScalarCalculation(value=2))),
                    name='Penetration +3 AP Modifier')
                damageModifier = common.Calculator.multiply(
                    lhs=common.ScalarCalculation(
                        value=-2,
                        name='Penetration +3 Damage Modifier Per 3 Full Dice Of Damage'),
                    rhs=common.Calculator.divideFloor(
                        lhs=damageRoll.dieCount(),
                        rhs=common.ScalarCalculation(value=3)),
                    name='Penetration +3 Damage Modifier')
            elif penetration >= +4:
                # AP 5 plus 2 per full dice of damage, -1 damage per dice of damage
                apModifier = common.Calculator.add(
                    lhs=common.ScalarCalculation(value=5),
                    rhs=common.Calculator.multiply(
                        lhs=common.ScalarCalculation(
                            value=2,
                            name='Penetration +4 AP Modifier Per Full Dice Of Damage'),
                        rhs=damageRoll.dieCount()),
                    name='Penetration +4 AP Modifier')
                damageModifier = common.Calculator.multiply(
                    lhs=common.ScalarCalculation(
                        value=-1,
                        name='Penetration +4 Damage Modifier Per Full Dice Of Damage'),
                    rhs=damageRoll.dieCount(),
                    name='Penetration >= +4 Damage Modifier')

            if apModifier:
                factors.append(construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.AP,
                    modifier=construction.ConstantModifier(
                        value=apModifier)))

            if damageModifier:
                factors.append(construction.ModifyAttributeFactor(
                    attributeId=gunsmith.WeaponAttributeId.Damage,
                    modifier=construction.DiceRollModifier(
                        constantModifier=damageModifier)))

        if not factors:
            return

        step = gunsmith.WeaponStep(
            name=f'Penetration ({penetration})',
            type='Trait',
            factors=factors)
        context.applyStep(
            sequence=sequence,
            step=step)

    """
    Remove Redundant Bulky Trait
    - Trait: Bulky is redundant if weapon has Very Bulky
    """
    # NOTE: I've added a step that removes the Bulky trait if the weapon also has the Very Bulky trait. Based on
    # the descriptions of the gravitic system and stabilisation accessories they seem to be levels rather independent
    # traits.

    def _createRemoveRedundantBulkyTrait(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        if not context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.VeryBulky) or \
            not context.hasAttribute(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.Bulky):
            return # Nothing to do

        # The weapon has Bulky and Very Bulky, Bulky is redundant so remove it
        step = gunsmith.WeaponStep(
            name=f'Remove Redundant Bulky Trait',
            type='Trait',
            factors=[construction.DeleteAttributeFactor(attributeId=gunsmith.WeaponAttributeId.Bulky)])
        context.applyStep(
            sequence=sequence,
            step=step)

    def _createTraitNotes(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        for trait in gunsmith.TraitAttributeIds:
            if not context.hasAttribute(sequence=sequence, attributeId=trait):
                continue

            name = trait.value
            notes = []
            if trait == gunsmith.WeaponAttributeId.Bulky:
                notes.append('If the user has a STR less than 9, all attack rolls have a negative DM equal to their difference between their STR DM and +1.')
            elif trait == gunsmith.WeaponAttributeId.VeryBulky:
                notes.append('If the user has a STR less than 12, all attack rolls have a negative DM equal to the difference between their STR DM and +2.')
            elif trait == gunsmith.WeaponAttributeId.Scope:
                pass # This is handled by the range modifiers finalisation step
            elif trait == gunsmith.WeaponAttributeId.ZeroG:
                notes.append('The weapon can be used in zero gravity without requiring an Athletics (DEX) check.')
            elif trait == gunsmith.WeaponAttributeId.Corrosive:
                notes.append('Corrosive weapons inflict normal damage on the first round, then on each round after that another roll is made with the damage reduced by 1D. This stops when the number of damage dice reaches zero.')
                notes.append('Armour protects as normal against corrosive weapons. However corrosive materials destroy armour at a rate of 1 point per dice of damage for each round they\'re in contact.')
            elif trait == gunsmith.WeaponAttributeId.RF:
                pass # This is an internal trait so has no notes
            elif trait == gunsmith.WeaponAttributeId.VRF:
                pass # This is an internal trait so has no notes
            elif trait == gunsmith.WeaponAttributeId.Stun:
                notes.append('Damage from stun weapons is only deducted from END, taking into account any armour. If the targets END is reduced to 0 they will be incapacitated for a number of rounds equal to the amount the damage exceeded their END.')
                notes.append('Damage caused by stun weapons is completely healed by one hour of rest.')
            elif trait == gunsmith.WeaponAttributeId.Auto:
                pass # This is handled by the auto modifier finalisation step
            elif trait == gunsmith.WeaponAttributeId.Inaccurate:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'DM-{abs(value.value())} to attack rolls at ranges > 10m.')
            elif trait == gunsmith.WeaponAttributeId.Hazardous:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'DM-{abs(value.value())} when rolling against the Malfunction table on p8 of the Field Catalogue.')
            elif trait == gunsmith.WeaponAttributeId.Unreliable:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'When the weapon is used an additional 1D of a different colour is rolled. If it comes up <= {value.value()} a malfunction occurs and a roll must be made against the Malfunction table on p8 of the Field Catalogue.')
            elif trait == gunsmith.WeaponAttributeId.SlowLoader:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'The weapon takes {value.value()} minor actions to reload. The user can make an Average(8+) Gun Combat check to reduce the load time by a number of minor actions equal to the Effect of the roll.')
            elif trait == gunsmith.WeaponAttributeId.Ramshackle:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'DM-{abs(value.value())} to attack rolls.')
                notes.append(f'DM-{abs(value.value())} when rolling against the Malfunction table on p8 of the Field Catalogue.')
            elif trait == gunsmith.WeaponAttributeId.AP:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'Targets armour value is reduced by {value.value()}.')
            elif trait == gunsmith.WeaponAttributeId.LoPen:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'Targets armour value is multiplied by {value.value()}.')
            elif trait == gunsmith.WeaponAttributeId.Spread:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                range = context.attributeValue(
                    sequence=sequence,
                    attributeId=gunsmith.WeaponAttributeId.Range)
                assert(isinstance(range, common.ScalarCalculation))
                range = common.formatNumber(number=range.value())
                name += f' ({value.value()})'
                notes.append(f'DM+{value.value()} to attack rolls at ranges <= {range}m.')
            elif trait == gunsmith.WeaponAttributeId.Blast:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'Upon a successful attack, damage is rolled against all targets within {value.value()}m.')
                notes.append(f'A target cannot dodge a blast attack but they can dive for cover. Cover can be used if it lies between the target and the center of the blast radius.')
            elif trait == gunsmith.WeaponAttributeId.PulseIntensity:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation))
                name += f' ({value.value()})'
                notes.append(f'The EMP pulse will destroy unshielded systems with a TL < {value.value() - 2} and cause unshielded systems with a TL <= {value.value() + 2} to shut down for 1D minutes.')
                notes.append(f'The EMP pulse may disrupt shielded systems and systems with a TL > {value.value() + 2}. Roll 2D against the Disruption table on p26 of the Field Catalogue with a positive DM+1 for every TL above {value.value()} and an additional DM+2 if the systems are intended for military use.')
            elif trait == gunsmith.WeaponAttributeId.Incendiary:
                # Note this can be a scalar or dice roll
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation) or isinstance(value, common.DiceRoll))
                if isinstance(value, common.ScalarCalculation):
                    name += f' ({value.value()})'
                    notes.append(f'DM+{value.value()} when rolling against the Flammability table on p7 of the Field Catalogue.')
                else:
                    name += f' ({str(value)})'
                    notes.append(f'When rolling against the Flammability table on p7 of the Field Catalogue, roll {str(value)} and use the result as a positive modifier.')
            elif trait == gunsmith.WeaponAttributeId.Burn:
                # Note this can be a scalar or dice roll
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, common.ScalarCalculation) or isinstance(value, common.DiceRoll))
                rounds = value.value() if isinstance(value, common.ScalarCalculation) else str(value)
                name += f' ({rounds})'
                notes.append(f'After the initial attack, half the attack damage is applied each round for {rounds} rounds. Armour protects against this damage each round.')
            elif trait == gunsmith.WeaponAttributeId.EmissionsSignature:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, gunsmith.Signature))
                name += f' ({value.value})'
                modifier = Finalisation._SignatureDetectionModifierMap[value]
                modifier = common.formatNumber(number=modifier.value(), alwaysIncludeSign=True)
                notes.append(f'DM{modifier} modifier to checks to detect the firing of the weapon using sensors.')
            elif trait == gunsmith.WeaponAttributeId.PhysicalSignature:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, gunsmith.Signature))
                name += f' ({value.value})'
                modifier = Finalisation._SignatureDetectionModifierMap[value]
                modifier = common.formatNumber(number=modifier.value(), alwaysIncludeSign=True)
                notes.append(f'DM{modifier} modifier to checks to detect the firing of the weapon using physical means (e.g. audibly or visually).')
            elif trait == gunsmith.WeaponAttributeId.Distraction:
                value = context.attributeValue(sequence=sequence, attributeId=trait)
                assert(isinstance(value, gunsmith.Distraction))
                name += f' ({value.value})'
                target = Finalisation._DistractionTargetNumberMap[value]
                notes.append(f'Targets must make an END({target.value()}+) check or be unable to take their next set of actions.')

            if notes:
                step = gunsmith.WeaponStep(
                    name=name,
                    type='Trait',
                    notes=notes)
                context.applyStep(
                    sequence=sequence,
                    step=step)

    """
    Specific Location (Traveller Companion p52):
    - Attack DM: DM-2 for single shot, DM-6 for for automatic fire
    """
    # This covers the called Specific Location rules from p52 of the Traveller Companion rules

    def _createSpecificLocationNotes(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        hasAutoScore = context.hasAttribute(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.Auto)
        notes = []

        if hasAutoScore:
            notes.append('DM-2 to attack rolls when trying to hit a specific body part with a single shot.')
            notes.append('DM-6 to attack rolls when trying to hit a specific body part with auto fire.')
        else:
            notes.append('DM-2 to attack rolls when trying to hit a specific body part.')

        step = gunsmith.WeaponStep(
            name='Specific Location',
            type='Traveller Companion',
            notes=notes)
        context.applyStep(
            sequence=sequence,
            step=step)
