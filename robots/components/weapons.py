import common
import construction
import enum
import robots
import traveller
import typing

class FireControlLevel(enum.Enum):
    Basic = 'Basic'
    Improved = 'Improved'
    Enhanced = 'Enhanced'
    Advanced = 'Advanced'


_SkillNameMap = {skill.name(): skill for skill in traveller.AllStandardSkills}

class _WeaponImpl(object):
    """
    - Option: Mount Size
        - Small
            - Slots: 1
            - Cost: 500
            - Note: A small weapon mount may hold any melee weapon useable with
            one hand, any pistol or equivalent single-handed ranged weapon, or
            an explosive charge or grenade of less than three kilograms
        - Medium
            - Slots: 2
            - Cost: 1000
            - Note: A medium weapon mount may hold any larger weapon usable by
            Melee or Gun Combat skills or an explosive of up to six kilograms
        - Heavy
            - Slots: 10
            - Cost: 5000
            - Note: A heavy mount may hold any weapon usable with Heavy
            Weapons (portable)
        - Vehicle
            - Slots: 15
            - Cost: 10000
            - Note: A vehicle mount may hold any weapon of mass 250 kilograms or
            less that requires Heavy Weapons (vehicle).
    - Option: Weapon
        - Requirement: Ability to select a weapon from a list with the list
        determined by the size of the mount
    - Option: Autoloader
        - Min TL: 6
        - Cost: Weapon magazine cost * Number of Magazines * 2
        - Slots: Doubles the slots used by the weapon/mount
        - Option: Number of magazines the Autoloader holds
    - Option: Linked Weapons
        - Requirement: Up to 4 weapons OF THE SAME TYPE can be linked to fire as
        a single attack. If the attack succeeds, only one damage roll is made
        and +1 PER DAMAGE DICE is added for each additional weapon (p61)
        - Requirement: Linked weapons require a Fire Control System (clarified
        by Geir)
        - Requirement: Hand held weapons can't be linked (clarified by Geir)
    - Option: Fire Control System
        - <All>
            - Slots: 1
            - Trait: Scope
            - Note: If the robot has a Laser Designator attacks get a DM+2 to
            attack targets that have been successfully illuminated (p37)
            - Note: When making attacks, the Fire Control Systems Weapon Skill
            DM can be used instead of the weapon skill for the mounted/held
            weapon (clarification by Geir Lanesskog)
        - Basic
            - Min TL: 6
            - Cost: 10000
            - Weapon Skill DM: +1
        - Improved
            - Min TL: 8
            - Cost: 25000
            - Weapon Skill DM: +2
        - Enhanced
            - Min TL: 10
            - Cost: 50000
            - Weapon Skill DM: +3
        - Advanced
            - Min TL: 12
            - Cost: 100000
            - Weapon Skill DM: +4
    """
    # NOTE: The rules around Fire Control Systems and linked weapons are
    # confusing. I got a chance to put some questions to Geir Lanesskog (the
    # author of the book) and he clarified some stuff.
    # https://forum.mongoosepublishing.com/threads/robot-tl-8-sentry-gun.124598/#post-973844
    # https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/
    #
    # Clarification 1: His intention was that only weapons held by or mounted
    # to a manipulators should get a DEX modifier for attack rolls and this
    # could be a negative modifier. He specifically said that you just don't
    # include it, you shouldn't count it a DEX of zero (i.e. it gives no DM
    # rather than a DM-3)
    # Although he doesn't explicitly state it this would imply a robot with no
    # manipulators has no DEX score.
    #
    # Clarification 2: "For finalisation purposes, Weapon Skill DM is treated as
    # the weapon skill of the robot with the integrated weapon" means the robot
    # robot effectively gets the combat skill appropriate for the mounted weapon
    # at a level equal to the Weapon Skill DM for the Fire Control System. The
    # important piece of logic that is missing is that, if the robot also takes
    # the actual skill at a higher level, that level is used instead.
    #
    # Clarification 3: The section covering the attack modifier for weapons held
    # by or mounted to a manipulator is worded incorrectly. Rather than you
    # taking the larger of the DEX modifier for the manipulator and the Weapon
    # Skill DM of the Fire Control system and and using it in addition to the
    # weapon skill for the weapon. It should have said to take the larger of the
    # weapon skill for the weapon and the Fire Control System and use it in
    # addition to the DEX modifier for the manipulator. His intention was it
    # should be treated in the same way the attack modifier for a player, they
    # get the modifier from a combat skill (which could be an actual skill or
    # provided by the Fire Control System) and they also get a modifier for the
    # DEX (of the manipulator)
    #
    # Clarification 4: Fire Control System can be used with hand held weapons
    #
    # Clarification 5: The way linked weapons work was intended to be based on
    # the Vehicle Handbook mount rules where multiple weapons can be linked but
    # only if they're on the same mount. For robots the "same mount" is classed
    # as all mounted to a single servo mount or all mounted to the same
    # manipulator. This is slightly different to what the rules say as they say
    # each weapon requires its own mount (p61). The important part is you can't
    # link weapons on different manipulators or servo and manipulator mounted
    # weapons.
    #
    # Clarification 6: Weapons held by a manipulator (rather than mounted to a
    # manipulator) can't be linked. This is a logical side effect of
    # Clarification 5 as it wouldn't make sense for one manipulator to hold
    # multiple weapons.
    # NOTE: The note about which weapons a mount of a given size can use is
    # handled in finalisation

    # Data Structure: Cost, Slots
    _MountSizeData = {
        traveller.WeaponSize.Small: (500, 1),
        traveller.WeaponSize.Medium: (1000, 2),
        traveller.WeaponSize.Heavy: (5000, 10),
        traveller.WeaponSize.Vehicle: (10000, 15)
    }

    _AutoloaderMinTL = common.ScalarCalculation(
        value=6,
        name='Autoloader Min TL')
    _AutoloaderMagazineCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Autoloader Magazine Cost Multiplier')
    _AutoloaderMinManipulatorSizeModifier = common.ScalarCalculation(
        value=1,
        name='Autoloader Minimum Manipulator Size Modifier')

    _MultiLinkMaxGroupSize = 4

    _MultiLinkAttackKnownDiceNote = 'When the {count} linked weapons are fired as a group, only a single attack is made. If a hit occurs, a single damage roll is made and an additional +{modifier} damage is added to the result. (p61)'
    _MultiLinkAttackUnknownDiceNote = 'When the {count} linked weapons are fired as a group, only a single attack is made. If a hit occurs, a single damage roll is made and  an additional +{modifier} damage is added to the result of each damage dice. (p61)'

    # Data Structure: Min TL, Cost, Weapon Skill DM
    _FireControlDataMap = {
        FireControlLevel.Basic: (6, 10000, +1),
        FireControlLevel.Improved: (8, 25000, +2),
        FireControlLevel.Enhanced: (10, 50000, +3),
        FireControlLevel.Advanced: (12, 100000, +4),
    }
    _FireControlMinTL = common.ScalarCalculation(
        value=6,
        name='Fire Control System Min TL')
    _FireControlRequiredSlots = common.ScalarCalculation(
        value=1,
        name='Fire Control System Required Slots')
    _FireControlScopeNote = 'The Fire Control System gives the Scope trait. (p60)'
    _FireControlWeaponSkillNote = \
        'When making an attack roll, you can choose to use the fire control ' \
        'system\'s Weapon Skill DM of {modifier} instead of the robot\'s ' \
        '{skill} skill. Note that this is only in place of the skill (p60 ' \
        'and clarified by Geir Lanesskog)\n\n' \
        'Note that the worksheets for example robots in the Robot Handbook ' \
        'list the weapon skill given by a fire control system. It\'s listed ' \
        'as a normal skill, however, it only applies in relation to using  ' \
        'the abilities of the fire control system. Auto-Jimmy will also do ' \
        'this when including DMs in final skill levels is enabled.'
    _FireControlLaserDesignatorComponents = [
        robots.LaserDesignatorDefaultSuiteOption,
        robots.LaserDesignatorSlotOption]
    _FireControlLaserDesignatorNote = 'DM+2 to attacks against targets that have been illuminated with the robot\'s laser designator. (p37)'

    def __init__(self) -> None:
        super().__init__()

        self._weaponCategoryOption = construction.EnumOption(
            id='WeaponCategory',
            name='Weapon Category',
            type=traveller.WeaponCategory,
            description='Specify the category of weapon.')

        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            value=None,
            choices=['default'], # This will be replaced when updateOptions is called
            isEditable=False,
            description='Specify the weapon that is mounted.')

        self._autoLoaderOption = construction.IntegerOption(
            id='Autoloader',
            name='Autoloader Magazines',
            value=None,
            minValue=1,
            maxValue=10,
            isOptional=True,
            description='Specify if the mount is equipped with an Autoloader and, if so, how many magazines it contains.')

        self._linkedCountOption = construction.IntegerOption(
            id='LinkedCount',
            name='Linked Weapons',
            value=None,
            minValue=2,
            maxValue=_WeaponImpl._MultiLinkMaxGroupSize,
            isOptional=True,
            description='Specify the number of weapons to link so they fire as a single action.')

        self._fireControlOption = construction.EnumOption(
            id='FireControl',
            name='Fire Control',
            type=FireControlLevel,
            isOptional=True,
            description='Specify Fire Control System level.')

    def weaponCategory(self) -> typing.Optional[traveller.WeaponCategory]:
        return self._weaponCategoryOption.value() if self._weaponCategoryOption.isEnabled() else None

    def weaponName(self) -> typing.Optional[str]:
        return self._weaponOption.value() if self._weaponOption.isEnabled() else None

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        weaponName = self.weaponName()
        if not weaponName:
            return None
        return traveller.lookupStockWeapon(
            name=weaponName,
            weaponSet=weaponSet)

    def linkedGroupSize(self) -> typing.Optional[common.ScalarCalculation]:
        if not self._linkedCountOption.isEnabled():
            return None
        linkCount = self._linkedCountOption.value()
        if not linkCount or linkCount < 2:
            return None
        return common.ScalarCalculation(
            value=linkCount,
            name='Specified Linked Weapon Group Size')

    def autoloaderMagazineCount(self) -> typing.Optional[common.ScalarCalculation]:
        if not self._autoLoaderOption.isEnabled() or not self._autoLoaderOption.value():
            return None
        return common.ScalarCalculation(
            value=self._autoLoaderOption.value(),
            name='Specified Autoloader Magazine Count')

    def fireControl(self) -> typing.Optional[FireControlLevel]:
        if not self._fireControlOption.isEnabled():
            return None
        return self._fireControlOption.value()

    def fireControlSkill(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Tuple[
                typing.Optional[traveller.SkillDefinition],
                typing.Optional[typing.Union[str, enum.Enum]], # Speciality
                typing.Optional[common.ScalarCalculation]]: # Level
        fireControl = self.fireControl()
        if not fireControl:
            return (None, None, None)
        weaponData = self.weaponData(weaponSet=weaponSet)
        if not weaponData:
            return (None, None, None)
        skillDef = weaponData.skill()
        speciality = weaponData.specialty()

        _, _, level = _WeaponImpl._FireControlDataMap[fireControl]
        level = common.ScalarCalculation(
            value=level,
            name=f'Fire Control {skillDef.name(speciality=speciality)} Skill')
        return (skillDef, speciality, level)

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
                componentType=robots.Chassis,
                sequence=sequence):
            return False

        # NOTE: Don't call _allowedWeapons as it may rely on the value that
        # options are set to and updateOptions might not have been called yet
        weapons = traveller.enumerateStockWeapons(
            weaponSet=context.weaponSet(),
            maxTL=context.techLevel())
        foundUsableWeapon = False
        for weapon in weapons:
            if weapon.robotMount():
                foundUsableWeapon = True
                break
        return foundUsableWeapon

    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._weaponCategoryOption.isEnabled():
            options.append(self._weaponCategoryOption)
        if self._weaponOption.isEnabled():
            options.append(self._weaponOption)
        if self._autoLoaderOption.isEnabled():
            options.append(self._autoLoaderOption)
        if self._linkedCountOption.isEnabled():
            options.append(self._linkedCountOption)
        if self._fireControlOption.isEnabled():
            options.append(self._fireControlOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        weaponCategoryOptions = self._allowedWeaponCategories(
            sequence=sequence,
            context=context)
        if weaponCategoryOptions:
            self._weaponCategoryOption.setChoices(choices=weaponCategoryOptions)
        self._weaponCategoryOption.setEnabled(
            enabled=len(weaponCategoryOptions) > 0)

        weaponOptions = self._allowedWeapons(
            sequence=sequence,
            context=context)
        if weaponOptions:
            self._weaponOption.setChoices(choices=weaponOptions)
        self._weaponOption.setEnabled(
            enabled=len(weaponOptions) > 0)

        self._autoLoaderOption.setEnabled(
            enabled=self._allowedAutoloader(sequence=sequence, context=context))

        self._linkedCountOption.setEnabled(
            enabled=self._allowedLinkedWeapons(sequence=sequence, context=context))

        fireControlOptions = self._allowedFireControls(
            sequence=sequence,
            context=context)
        if fireControlOptions:
            self._fireControlOption.setChoices(choices=fireControlOptions)
            self._fireControlOption.setOptional(
                isOptional=not self._linkedCountOption.value()) # Mandatory if linked
        self._fireControlOption.setEnabled(
            enabled=len(fireControlOptions) > 0)

    def createSteps(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext,
            ) -> None:
        step = self._createWeaponStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

        step = self._createMountStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

        step = self._createAutoloaderStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

        step = self._createFireControlStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

    def _createWeaponStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None

        stepName = weaponData.name()
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=typeString)

        weaponCost = weaponData.cost()
        if weaponCost:
            weaponCost = common.ScalarCalculation(
                value=weaponCost,
                name=f'{weaponData.name()} Cost')

        if weaponCost and linkedGroupSize:
            weaponCost = common.Calculator.multiply(
                lhs=weaponCost,
                rhs=linkedGroupSize,
                name=f'Linked {weaponCost.name()}')

        if weaponCost and weaponCost.value() > 0:
            step.setCredits(credits=construction.ConstantModifier(value=weaponCost))

        weaponDamage = weaponData.damage()
        if weaponDamage:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Base Damage = {weaponDamage}'))

        weaponRange = weaponData.range()
        if weaponRange:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Range = {weaponRange}m'))

        weaponTraits = weaponData.traits()
        if weaponTraits:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Traits = {weaponTraits}'))

        magazineCapacity = weaponData.magazineCapacity()
        magazineCost = weaponData.magazineCost()

        skill = weaponData.skill()
        skillName = skill.name(speciality=weaponData.specialty())
        weaponStats = [f'Skill: {skillName}']
        if weaponDamage:
            weaponStats.append(f'Damage: {weaponDamage}')
        if weaponRange:
            weaponStats.append(f'Range: {weaponRange}m')
        if weaponTraits:
            weaponStats.append(f'Traits: {weaponTraits}')
        if magazineCapacity:
            weaponStats.append(f'Magazine Capacity: {magazineCapacity}')
        if magazineCost:
            weaponStats.append(f'Magazine Cost: Cr{magazineCost}')
        step.addNote(note='\n'.join(weaponStats))

        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            damageDieCount = None
            if weaponDamage:
                damageRoll = common.DiceRoll.fromString(weaponDamage)
                if damageRoll:
                    damageDieCount = damageRoll.dieCount()

            if damageDieCount:
                step.addNote(note=_WeaponImpl._MultiLinkAttackKnownDiceNote.format(
                    count=linkedGroupSize.value(),
                    modifier=(linkedGroupSize.value() - 1) * damageDieCount.value()))
            else:
                step.addNote(note=_WeaponImpl._MultiLinkAttackUnknownDiceNote.format(
                    count=linkedGroupSize.value(),
                    modifier=linkedGroupSize.value() - 1))

        return step

    def _createMountStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None

        mountSize = weaponData.robotMount()
        if not mountSize:
            return None

        stepName = f'Mounting ({mountSize.value})'
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=typeString)

        mountCost, mountSlots = _WeaponImpl._MountSizeData[mountSize]
        mountCost = common.ScalarCalculation(
            value=mountCost,
            name=f'{mountSize.value} Mount Cost')
        mountSlots = common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots')

        if linkedGroupSize:
            mountCost = common.Calculator.multiply(
                lhs=mountCost,
                rhs=linkedGroupSize,
                name=f'Linked {mountCost.name()}')
            mountSlots = common.Calculator.multiply(
                lhs=mountSlots,
                rhs=linkedGroupSize,
                name=f'Linked {mountSlots.name()}')

        step.setCredits(credits=construction.ConstantModifier(value=mountCost))
        step.setSlots(slots=construction.ConstantModifier(value=mountSlots))

        return step

    def _createAutoloaderStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        autoloaderMagazineCount = self.autoloaderMagazineCount()
        if not autoloaderMagazineCount:
            return None

        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None

        magazineCost = weaponData.magazineCost()
        if not magazineCost:
            return None

        mountSize = weaponData.robotMount()
        if not mountSize:
            return None

        stepName = f'Autoloader {autoloaderMagazineCount.value()}'
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=typeString)

        magazineCost = common.ScalarCalculation(
            value=magazineCost,
            name=f'{weaponData.name()} Magazine Cost')
        autoloaderCost = common.Calculator.multiply(
            lhs=common.Calculator.multiply(
                lhs=magazineCost,
                rhs=autoloaderMagazineCount),
            rhs=_WeaponImpl._AutoloaderMagazineCostMultiplier,
            name='Autoloader Cost')

        _, mountSlots = _WeaponImpl._MountSizeData[mountSize]
        autoloaderSlots = common.ScalarCalculation(
            value=mountSlots,
            name='Autoloader Required Slots')

        if linkedGroupSize:
            autoloaderCost = common.Calculator.multiply(
                lhs=autoloaderCost,
                rhs=linkedGroupSize,
                name=f'Linked {autoloaderCost.name()}')
            autoloaderSlots = common.Calculator.multiply(
                lhs=autoloaderSlots,
                rhs=linkedGroupSize,
                name=f'Linked {autoloaderSlots.name()}')

        step.setCredits(credits=construction.ConstantModifier(value=autoloaderCost))
        step.setSlots(slots=construction.ConstantModifier(value=autoloaderSlots))

        return step

    def _createFireControlStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        fireControl = self.fireControl()
        if not fireControl:
            return None
        assert(isinstance(fireControl, FireControlLevel))

        stepName = f'Fire Control System ({fireControl.value})'
        step = robots.RobotStep(
            name=stepName,
            type=typeString)

        _, fireControlCost, weaponSkillDM = \
            _WeaponImpl._FireControlDataMap[fireControl]

        fireControlCost = common.ScalarCalculation(
            value=fireControlCost,
            name=f'{fireControl.value} Fire Control System Cost')
        step.setCredits(credits=construction.ConstantModifier(
            value=fireControlCost))

        step.setSlots(slots=construction.ConstantModifier(
            value=_WeaponImpl._FireControlRequiredSlots))

        skill, speciality, _ = self.fireControlSkill(weaponSet=context.weaponSet())
        if skill:
            skillName = skill.name(speciality=speciality)
        else:
            skillName = 'weapon'
        step.addNote(note=_WeaponImpl._FireControlWeaponSkillNote.format(
            modifier=common.formatNumber(number=weaponSkillDM, alwaysIncludeSign=True),
            skill=skillName))

        step.addNote(note=_WeaponImpl._FireControlScopeNote)

        hasLaserDesignator = False
        for componentType in _WeaponImpl._FireControlLaserDesignatorComponents:
            if context.hasComponent(
                    componentType=componentType,
                    sequence=sequence):
                hasLaserDesignator = True
                break
        if hasLaserDesignator:
            step.addNote(note=_WeaponImpl._FireControlLaserDesignatorNote)

        return step

    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        return traveller.WeaponSize # All sizes are allowed by default

    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < _WeaponImpl._AutoloaderMinTL.value():
            return False

        weaponData = self.weaponData(weaponSet=context.weaponSet())
        return weaponData and weaponData.magazineCost() != None

    def _allowedWeaponCategories(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponCategory]:
        weapons = traveller.enumerateStockWeapons(
            weaponSet=context.weaponSet(),
            maxTL=context.techLevel())
        allowed = []
        for weapon in weapons:
            if not weapon.robotMount():
                continue
            category = weapon.category()
            if category in allowed:
                continue
            allowed.append(category)
        return allowed

    def _allowedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[str]:
        weapons = traveller.enumerateStockWeapons(
            weaponSet=context.weaponSet(),
            maxTL=context.techLevel(),
            category=self.weaponCategory())
        allowed = []
        for weapon in weapons:
            if not weapon.robotMount():
                continue
            allowed.append(weapon.name())
        return allowed

    def _allowedLinkedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # Linking weapons requires a Fire Control System
        if context.techLevel() < _WeaponImpl._FireControlMinTL.value():
            return False
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        return weaponData and weaponData.linkable()

    def _allowedFireControls(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[FireControlLevel]:
        robotTL = context.techLevel()
        allowed = []
        for level in FireControlLevel:
            minTL, _, _ = _WeaponImpl._FireControlDataMap[level]
            if minTL <= robotTL:
                allowed.append(level)
        return allowed

# This component is for weapons mounted to/in a manipulator.
class _ManipulatorWeaponImpl(_WeaponImpl):
    """
    - Requirement: Only compatible with robots that have manipulators
    - Option: Manipulator
        - Requirement: The ability to select which manipulator the weapon is
        mounted to
    - Option: Mount Size
        - Small
            - Requirement: Only compatible with manipulators of size >= 3
        - Medium
            - Requirement: Only compatible with manipulators of size >= 5
        - Heavy
            - Requirement: Only compatible with manipulators of size >= 7
        - Vehicle
            - Requirement: Not compatible with manipulator mounts
    - Option: Autoloader
        - Requirement: The minimum manipulator size is increased by 1
    - Option: Multi-Link
        - Requirement: All weapons must be mounted to the same manipulator
        in order to be linked (clarified by Geir)
    """
    # NOTE: I'm working on the assumption that the fact there is no min
    # manipulator size for Vehicle sized weapons is because the can't
    # be mounted on manipulators
    # NOTE: The fact the Autoloader increases the Min Manipulator Size for
    # the mount by 1 complicates things. The manipulator is the first
    # thing the user selects. You could either have autoloader selection
    # next and, if selected, it effectively _reduces_ the size of the
    # manipulator when it comes to determining which mount sizes are possible
    # for the manipulator. The alternative is to have the size selection
    # followed by the autoloader selection. With the list of possible mount
    # sizes filtered by the unmodified size of the manipulator and the
    # autoloader option only enabled if the base manipulator size is greater
    # than or equal to the min manipulator size for the selected mount size
    # plus 1. I've gone with the later as I think it's done closer to how it
    # is in the book so should hopefully be easier for the user.
    # NOTE: The current implementation won't let you select a mount size
    # where the selected manipulator doesn't meet the min manipulator
    # requirement. Technically the it's not a hard requirement, you just don't
    # get the manipulators STR/DEX characteristic DM when making  attacks if
    # it doesn't meet the min requirement. I think the current behaviour is
    # desirable as I would expect the in the majority of cases the user wouldn't
    # want to mount weapons the robot can use effectively so it's best to stop
    # them doing it accidentally. If the user really wants to do it they can
    # just add a servo mount and say it's mounted to a manipulator.

    # NOTE: This maps weapon sizes to the min size a manipulator must be to
    # effectively use the weapon (p61)
    _MinManipulatorSizeData = {
        traveller.WeaponSize.Small: 3,
        traveller.WeaponSize.Medium: 5,
        traveller.WeaponSize.Heavy: 7,
        traveller.WeaponSize.Vehicle: None # Not compatible with manipulator mounts
    }

    def __init__(self) -> None:
        super().__init__()

        self._manipulatorOption = construction.StringOption(
            id='Manipulator',
            name='Manipulator',
            isEditable=False,
            choices=[''], # This will be replaced by updateOptions
            description='Specify which manipulator the weapon is mounted on')

    def manipulatorString(self) -> typing.Optional[str]:
        return self._manipulatorOption.value() if self._manipulatorOption.isEnabled() else None

    def manipulator(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.Manipulator]:
        manipulatorString = self.manipulatorString()
        if not manipulatorString:
            return None
        manipulators = self._enumerateRobotManipulators(
            sequence=sequence,
            context=context)
        return manipulators.get(manipulatorString)

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        manipulators = self._enumerateRobotManipulators(
            sequence=sequence,
            context=context)
        return len(manipulators) > 0

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.insert(0, self._manipulatorOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        manipulators = self._enumerateRobotManipulators(
            sequence=sequence,
            context=context)
        self._manipulatorOption.setChoices(
            choices=manipulators.keys())

        super().updateOptions(sequence=sequence, context=context)

    def _createMountStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        step = super()._createMountStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if not step:
            return None

        manipulatorString = self.manipulatorString()
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        mountSize = weaponData.robotMount() if isinstance(weaponData, traveller.StockWeapon) else None
        if not manipulatorString or not mountSize:
            return step

        return robots.RobotStep(
            name=f'{manipulatorString} {step.name()}',
            type=step.type(),
            costs=step.costs(),
            factors=step.factors(),
            notes=step.notes())

    def _addManipulatorFactor(
            self,
            step: robots.RobotStep
            ) -> None:
        manipulatorString = self.manipulatorString()
        if manipulatorString:
            step.addFactor(factor=construction.StringFactor(
                string=f'Manipulator = {manipulatorString}'))

    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        allowed = super()._allowedMountSizes(
            sequence=sequence,
            context=context)

        autoLoaderCount = self.autoloaderMagazineCount()
        manipulator = self.manipulator(
            sequence=sequence,
            context=context)
        if not manipulator:
            return []

        filtered = []
        for mountSize in allowed:
            minSize = _ManipulatorMountedWeaponImpl._MinManipulatorSizeData[mountSize]
            if not minSize:
                continue # Not compatible with manipulators
            if autoLoaderCount:
                minSize += _ManipulatorWeaponImpl._AutoloaderMinManipulatorSizeModifier.value()
            if manipulator.size() >= minSize:
                filtered.append(mountSize)
        return filtered

    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # NOTE: Intentionally don't call base impl
        if context.techLevel() < _ManipulatorWeaponImpl._AutoloaderMinTL.value():
            return False

        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData or weaponData.magazineCost() == None:
            return False

        mountSize = weaponData.robotMount()
        if not mountSize:
            return False

        manipulator = self.manipulator(
            sequence=sequence,
            context=context)
        if not manipulator:
            return False

        minSize = _ManipulatorMountedWeaponImpl._MinManipulatorSizeData[mountSize]
        if not minSize:
            return False # Vehicle weapons don't support autoloading
        minSize += _ManipulatorWeaponImpl._AutoloaderMinManipulatorSizeModifier.value()
        return manipulator.size() >= minSize

    # NOTE: The names generated by this function MUST remain consistent between
    # versions otherwise it will break robots saved with previous versions. For
    # this reason it shouldn't use things like the components instance string.
    def _enumerateRobotManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.Manipulator]:
        results = {}

        manipulators = context.findComponents(
            componentType=robots.Manipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            if isinstance(manipulator, robots.RemoveBaseManipulator):
                continue
            assert(isinstance(manipulator, robots.Manipulator))
            results[f'Manipulator #{index + 1}'] = manipulator

        return results

class _ServoMountedWeaponImpl(_WeaponImpl):
    pass

class _ManipulatorMountedWeaponImpl(_ManipulatorWeaponImpl):
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        manipulators = self._enumerateRobotManipulators(
            sequence=sequence,
            context=context)
        minUsableSize = _ManipulatorMountedWeaponImpl._MinManipulatorSizeData[traveller.WeaponSize.Small]
        hasRequiredManipulator = False
        for manipulator in manipulators.values():
            if manipulator.size() >= minUsableSize:
                hasRequiredManipulator = True
                break
        return hasRequiredManipulator

class _HandHeldFireControlImpl(_ManipulatorWeaponImpl):
    _WeaponSkills = [
        traveller.GunCombatSkillDefinition,
        traveller.HeavyWeaponsSkillDefinition,
        traveller.MeleeSkillDefinition
        ]

    def __init__(self) -> None:
        super().__init__()

        self._combatSkillOption = construction.StringOption(
            id='WeaponSkill',
            name='Weapon Skill',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon skill the fire control is for')

        self._specialityOption = construction.StringOption(
            id='WeaponSpeciality',
            name='Speciality',
            choices=['default'],
            isEditable=False,
            isOptional=False,
            description='Specify the weapon speciality the fire control is for')

    def fireControlSkill(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Tuple[
                typing.Optional[traveller.SkillDefinition],
                typing.Optional[typing.Union[str, enum.Enum]], # Speciality
                typing.Optional[common.ScalarCalculation]]: # Level
        fireControl = self.fireControl()
        if not fireControl:
            return (None, None, None)

        skillDef = self._selectedSkill()
        if not skillDef:
            return (None, None, None)
        speciality = self._selectedSpeciality()

        _, _, level = _WeaponImpl._FireControlDataMap[fireControl]
        level = common.ScalarCalculation(
            value=level,
            name=f'Hand Held Fire Control {skillDef.name(speciality=speciality)} Skill')
        return (skillDef, speciality, level)

    def isCompatible(self, sequence: str, context: robots.RobotContext) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        return context.techLevel() >= _WeaponImpl._FireControlMinTL.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._combatSkillOption)
        options.append(self._specialityOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        super().updateOptions(sequence=sequence, context=context)

        # Override control configuration set by base class
        self._fireControlOption.setOptional(False)

        # Update skill speciality
        self._combatSkillOption.setChoices(
            choices=[s.name() for s in _HandHeldFireControlImpl._WeaponSkills])

        skill = self._selectedSkill()
        specialityChoices = []
        if skill:
            if skill.isFixedSpeciality():
                specialityChoices = [s.value for s in skill.fixedSpecialities()]
            elif skill.isCustomSpeciality():
                specialityChoices = skill.customSpecialities()
        self._specialityOption.setChoices(choices=specialityChoices)
        self._specialityOption.setEnabled(len(specialityChoices) > 0)

    def _allowedWeaponCategories(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponCategory]:
        return []

    def _allowedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[str]:
        return []

    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        return []

    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return False

    def _allowedLinkedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return False

    def _createWeaponStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

    def _createMountStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

    def _createAutoloaderStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

    def _selectedSkill(self) -> typing.Optional[traveller.SkillDefinition]:
        skillName = self._combatSkillOption.value() if self._combatSkillOption.isEnabled() else None
        if not skillName:
            return None
        return _SkillNameMap.get(skillName)

    def _selectedSpeciality(self) -> typing.Optional[typing.Union[enum.Enum, str]]:
        specialityName = self._specialityOption.value() if self._specialityOption.isEnabled() else None
        if not specialityName:
            return None
        assert(isinstance(specialityName, str))

        skill = self._selectedSkill()
        if not skill:
            return None
        if skill.isFixedSpeciality():
            for speciality in skill.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                if specialityName == speciality.value:
                    return speciality
        elif skill.isCustomSpeciality():
            return specialityName

        return None

    def _createFireControlStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        step = super()._createFireControlStep(
            typeString=typeString,
            sequence=sequence,
            context=context)
        if not step:
            return None

        manipulatorString = self.manipulatorString()
        fireControl = self.fireControl()
        if not manipulatorString or not fireControl:
            return step

        return robots.RobotStep(
            name=f'{manipulatorString} ({fireControl.value})',
            type=step.type(),
            costs=step.costs(),
            factors=step.factors(),
            notes=step.notes())

class _HandHeldWeaponImpl(_WeaponImpl):
    # NOTE: Unlike with manipulator mounted weapons, this implementation
    # intentionally doesn't limit the selectable mount size by the min
    # manipulator size. If the user wants to purchase a weapon the robot
    # can't use effectively then it's on them
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        manipulators = context.findComponents(
            componentType=robots.Manipulator,
            sequence=sequence)
        hasManipulator = False
        for manipulator in manipulators:
            assert(isinstance(manipulator, robots.Manipulator))
            if not isinstance(manipulator, robots.RemoveBaseManipulator):
                hasManipulator = True
                break
        return hasManipulator

    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return False

    def _allowedLinkedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return False

    def _allowedFireControls(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[FireControlLevel]:
        return []

    def _createMountStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

    def _createAutoloaderStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

    def _createFireControlStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        return None

class Weapon(robots.RobotComponentInterface):
    def weaponName(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from Weapon so must implement weaponName')

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        raise RuntimeError(f'{type(self)} is derived from Weapon so must implement weaponData')

class MountedWeapon(Weapon):
    def __init__(
            self,
            impl: _WeaponImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def weaponName(self) -> str:
        return self._impl.weaponName()

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        return self._impl.weaponData(weaponSet=weaponSet)

    def linkedGroupSize(self) -> typing.Optional[common.ScalarCalculation]:
        return self._impl.linkedGroupSize()

    def autoloaderMagazineCount(self) -> typing.Optional[common.ScalarCalculation]:
        return self._impl.autoloaderMagazineCount()

    def fireControl(self) -> typing.Optional[FireControlLevel]:
        return self._impl.fireControl()

    def fireControlSkill(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Tuple[
                typing.Optional[traveller.SkillDefinition],
                typing.Optional[typing.Union[str, enum.Enum]], # Speciality
                typing.Optional[common.ScalarCalculation]]: # Level
        return self._impl.fireControlSkill(weaponSet=weaponSet)

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        typeString = self.typeString()
        otherMounts = context.findComponents(
            componentType=type(self),
            sequence=sequence)
        for index, otherMount in enumerate(otherMounts):
            if otherMount == self:
                typeString += f' #{index + 1}'
                break

        self._impl.createSteps(
            typeString=typeString,
            sequence=sequence,
            context=context)

class ServoMountedWeapon(MountedWeapon):
    def __init__(self) -> None:
        super().__init__(impl=_ServoMountedWeaponImpl())

    def componentString(self) -> str:
        return 'Servo Mount'

    def typeString(self) -> str:
        return 'Servo Mount'

class ManipulatorMountedWeapon(MountedWeapon):
    def __init__(self) -> None:
        super().__init__(impl=_ManipulatorMountedWeaponImpl())

    def componentString(self) -> str:
        return 'Manipulator Mount'

    def typeString(self) -> str:
        return 'Manipulator Mount'

class HandHeldWeapon(Weapon):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _HandHeldWeaponImpl()

    def weaponName(self) -> str:
        return self._impl.weaponName()

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        return self._impl.weaponData(weaponSet=weaponSet)

    def componentString(self) -> str:
        return 'Handheld Weapon'

    def typeString(self) -> str:
        return 'Handheld Weapon'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._impl.createSteps(
            typeString=self.typeString(),
            sequence=sequence,
            context=context)

class HandHeldFireControl(robots.RobotComponentInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _HandHeldFireControlImpl()

    def manipulator(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.Manipulator]:
        return self._impl.manipulator(sequence=sequence, context=context)

    def fireControl(self) -> FireControlLevel:
        return self._impl.fireControl()

    def fireControlSkill(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Tuple[
                typing.Optional[traveller.SkillDefinition],
                typing.Optional[typing.Union[str, enum.Enum]], # Speciality
                typing.Optional[common.ScalarCalculation]]: # Level
        return self._impl.fireControlSkill(weaponSet=weaponSet)

    def componentString(self) -> str:
        return 'Handheld Fire Control'

    def typeString(self) -> str:
        return 'Handheld Fire Control'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return self._impl.isCompatible(
            sequence=sequence,
            context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._impl.createSteps(
            typeString=self.typeString(),
            sequence=sequence,
            context=context)

class Magazines(robots.RobotComponentInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _HandHeldWeaponImpl()

        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            value=None,
            choices=['default'], # This will be replaced when updateOptions is called
            isEditable=False,
            description='The weapon to purchase magazines for.')

        self._countOption = construction.IntegerOption(
            id='Count',
            name='Count',
            value=1,
            minValue=1,
            maxValue=100000,
            description='The number of "magazines" to purchase for the selected weapon.')

    def weaponName(self) -> str:
        return self._weaponOption.value()

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        weaponName = self.weaponName()
        if not weaponName:
            return None
        return traveller.lookupStockWeapon(
            name=weaponName,
            weaponSet=weaponSet)

    def magazineCount(self) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=self._countOption.value(),
            name='Specified Magazine Count')

    def componentString(self) -> str:
        return 'Magazines'

    def typeString(self) -> str:
        return 'Magazines'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        allowedWeapons = self._allowedWeapons(sequence=sequence, context=context)
        return len(allowedWeapons) > 0

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._weaponOption, self._countOption]

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._weaponOption.setChoices(
            choices=self._allowedWeapons(sequence=sequence, context=context))

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        weaponData = self.weaponData(context.weaponSet())
        if not weaponData:
            return None

        magazineCost = weaponData.magazineCost()
        if magazineCost == None:
            return None
        magazineCost = common.ScalarCalculation(
            value=magazineCost,
            name=f'{weaponData.name()} Magazine Cost')

        magazineCount = self.magazineCount()

        stepName = f'{weaponData.name()} Magazine'
        if magazineCount.value() > 1:
            stepName += f' x{magazineCount.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())

        totalCost = common.Calculator.multiply(
            lhs=magazineCost,
            rhs=magazineCount,
            name='Total Magazine Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        context.applyStep(
            sequence=sequence,
            step=step)

    def _allowedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[str]:
        weapons = self._enumerateRobotWeapons(sequence=sequence, context=context)
        return [weapon.name() for weapon in weapons if weapon.magazineCost() != None]

    def _enumerateRobotWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.StockWeapon]:
        weapons = []

        mounts = context.findComponents(
            componentType=MountedWeapon,
            sequence=sequence)
        for mount in mounts:
            assert(isinstance(mount, MountedWeapon))
            weaponData = mount.weaponData(context.weaponSet())
            assert(weaponData == None or isinstance(weaponData, traveller.StockWeapon))
            if weaponData and weaponData not in weapons:
                weapons.append(weaponData)

        handhelds = context.findComponents(
            componentType=HandHeldWeapon,
            sequence=sequence)
        for handheld in handhelds:
            assert(isinstance(handheld, HandHeldWeapon))
            weaponData = handheld.weaponData(context.weaponSet())
            assert(weaponData == None or isinstance(weaponData, traveller.StockWeapon))
            if weaponData and weaponData not in weapons:
                weapons.append(weaponData)

        return weapons
