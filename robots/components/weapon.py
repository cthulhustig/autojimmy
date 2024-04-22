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

class _WeaponMountImpl(object):
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
    - Option: Multi-link
        - Option: Number of multi-linked mounts, up to a max of 4
        - Requirement: Up to 4 weapons OF THE SAME TYPE can be linked to fire as
        a single attack. If the attack succeeds, only one damage roll is made
        and +1 is added for each additional weapon
        - Requirement: Hand held weapons can't be multi-linked
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
    # NOTE: The rule seem to describe 2 or 3 different types of weapon mount
    # servo and manipulator mounted and possibly torso mounted as a separate
    # class depending on how you interpret the wording.
    #
    # Manipulator mounts seem the easiest to understand but most complicated to
    # implement. The user specifies which manipulator the weapon is mounted on.
    # The chosen manipulator determines how big a mount (and therefore weapon)
    # can be installed and the DEX level used when calculating the attack
    # modifier. The slot usage and cost for the mount come from the table on
    # p61. The table also specifies the minimum manipulator size required for
    # that size mount.
    #
    # Servo mounts seem straight forward. The slots and cost for the mount come
    # from the table on p61 but the minimum manipulator size doesn't apply. The
    # only limit on how big a mount (and therefore weapon) you can install is
    # the available slots. After clarifications from Geir (see below) the only
    # thing that's not clear is why there is no min TL for servo mounts.
    #
    # Torso mounts are the most confusing. The rules specifically say "A weapon
    # mount is integrated into a robot, either as an attachment to a manipulator
    # or a separate weapon servo." (p61) and then later "A weapon mounted in the
    # robot’s torso may use any available Slots.". There are a couple of things
    # that are unclear, how a 'torso' mounted weapon relates to a servo or
    # manipulator weapon and why it's specifically calling out that a torso
    # mounted weapon can use "any available Slots".
    # The simplest interpretation is that 'torso mounted' is just a catch all
    # term for manipulators mounted in or on the robot (rather than held by it).
    # This would make some sense as the "any available Slots" would just be
    # saying that these types of weapons consume slots (where as held weapons
    # don't).
    # The other option is 'torso' mounted means mounted inside the robot rather
    # than to the exterior of the robot and it's trying to differentiate how
    # slots are consumed in those cases. With this interpretation the fact
    # its' explicitly saying these types of weapons can use "any available
    # Slots" could be taken to mean weapons mounted to the exterior of the robot
    # don't consume slots.
    #
    # My current best guess is the former option. If it was something as
    # fundamental as mounting to the exterior doesn't consume slots then you
    # would have thought it would be a lot clearer. You would also have thought
    # that mounting externally would be an option for other components.
    # NOTE: The rules around how the Fire Control System affects attack rolls are
    # confusing. I got a chance to put some questions to Geir Lanesskog (the
    # author of the book) and he clarified some stuff.
    # https://forum.mongoosepublishing.com/threads/robot-tl-8-sentry-gun.124598/#post-973844
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
    # NOTE: The wording of the Fire Control System section (p60) is contradictory.
    # It says "A fire control system provides targeting assistance to weapons that
    # are integrally mounted on a robot". If it's for integrally mounted weapons
    # that would mean it wouldn't apply to hand held weapons. However, later it
    # says "A dedicated fire control system for a manipulator held weapon...."
    # which seems to be explicitly saying you can use a fire control system with
    # a hand held weapon.
    # NOTE: I added the requirement that hand held weapons can't be multi-linked.
    # Along with the fact nothing explicitly says you can multi-link hand held
    # weapons there is also the the wording "A dedicated fire control system for
    # a manipulator held weapon...." (p60) and "Linked mounts make only one
    # attack roll and require only one fire control system" (p61). If you
    # combine the fact that each hand held weapon needs a dedicated fire control
    # system and muli-linked mounts only need one fire control system for the
    # group, it would suggest that hand held weapons can't be multi-linked.
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
    
    _MultiLinkAttackNote = 'Only a single attack is made when the {count} linked mounts are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result. (p61)'

    # Data Structure: Min TL, Cost, Weapon Skill DM
    _FireControlData = {
        FireControlLevel.Basic: (6, 10000, +1),
        FireControlLevel.Improved: (8, 25000, +2),
        FireControlLevel.Enhanced: (10, 50000, +3),
        FireControlLevel.Advanced: (12, 100000, +4),
    }
    _FireControlSlots = common.ScalarCalculation(
        value=1,
        name='Fire Control System Required Slots')
    _FireControlScopeNote = 'The Fire Control System gives the Scope trait (p60).'
    _FireControlLaserDesignatorComponents = [
        robots.LaserDesignatorDefaultSuiteOption,
        robots.LaserDesignatorSlotOption]
    _FireControlWeaponSkillNote = 'When making an attack roll, you can choose to use the Fire Control System\'s Weapon Skill DM of {modifier} instead of the robots {skill} skill (p60 and clarified by Geir Lanesskog, Robot Handbook author)'
    _FireControlLaserDesignatorNote = 'DM+2 to attacks against targets that have been illuminated with the Laser Designator (p37).'

    def __init__(self) -> None:
        super().__init__()

        self._mountSizeOption = construction.EnumOption(
            id='MountSize',
            name='Mount Size',
            type=traveller.WeaponSize,
            description='Specify the size of the mount, this determines what size of weapons can be mounted on it.')            
        
        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            value=None,
            options=list(traveller.TravellerCompanionWeaponDataMap.keys()),
            isEditable=False,
            description='Specify the weapon that is mounted.')    
        
        self._fireControlOption = construction.EnumOption(
            id='FireControl',
            name='Fire Control',
            type=FireControlLevel,
            isOptional=True,
            description='Specify if the mount or multi-linked group of mounts is controlled by a Fire Control System.')        

        self._autoLoaderOption = construction.IntegerOption(
            id='Autoloader',
            name='Autoloader Magazines',
            value=None,
            minValue=1,
            maxValue=10,
            isOptional=True,
            description='Specify if the mount is equipped with an Autoloader and, if so, how many magazines it contains.')
        
        self._multiLinkOption = construction.IntegerOption(
            id='MultiLink',
            name='Multi-Link',
            value=None,
            minValue=2,
            maxValue=4,
            isOptional=True,
            description='Specify if this is a set of linked weapons that target and fire as a single action.')

    def mountSize(self) -> typing.Optional[traveller.WeaponSize]:
        return self._mountSizeOption.value() if self._mountSizeOption.isEnabled() else None
    
    def weaponName(self) -> typing.Optional[str]:
        return self._weaponOption.value() if self._weaponOption.isEnabled() else None

    def weaponData(self) -> typing.Optional[traveller.WeaponData]:
        weaponName = self.weaponName()
        if not weaponName:
            return None
        return traveller.TravellerCompanionWeaponDataMap.get(weaponName)
        
    def autoloaderMagazineCount(self) -> typing.Optional[int]:
        return self._autoLoaderOption.value() if self._autoLoaderOption.isEnabled() else None
    
    def linkedMountCount(self) -> typing.Optional[int]:
        return self._multiLinkOption.value() if self._multiLinkOption.isEnabled() else None
    
    def fireControlLevel(self) -> typing.Optional[FireControlLevel]:
        return self._fireControlOption.value() if self._fireControlOption.isEnabled() else None          

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._mountSizeOption.isEnabled():
            options.append(self._mountSizeOption)
        if self._weaponOption.isEnabled():
            options.append(self._weaponOption)
        if self._fireControlOption.isEnabled():
            options.append(self._fireControlOption)            
        if self._autoLoaderOption.isEnabled():
            options.append(self._autoLoaderOption)
        if self._multiLinkOption.isEnabled():
            options.append(self._multiLinkOption)
        return options
        
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        mountSizeOptions = self._allowedMountSizes(
            sequence=sequence,
            context=context)
        if mountSizeOptions:
            self._mountSizeOption.setOptions(options=mountSizeOptions)
        self._mountSizeOption.setEnabled(enabled=len(mountSizeOptions) > 0)
        
        weaponOptions = self._allowedWeapons(
            sequence=sequence,
            context=context)
        if weaponOptions:
            self._weaponOption.setOptions(options=weaponOptions)
        self._weaponOption.setEnabled(enabled=len(weaponOptions) > 0)
        
        self._autoLoaderOption.setEnabled(
            enabled=self._allowedAutoloader(sequence=sequence, context=context))

        maxMultiLinkCount = self._allowedMultiLinkCount(sequence=sequence, context=context)
        if maxMultiLinkCount:
            self._multiLinkOption.setMax(min(maxMultiLinkCount, 4))
        self._multiLinkOption.setEnabled(
            enabled=maxMultiLinkCount > 0)
        
        fireControlOptions = self._allowedFireControls(
            sequence=sequence,
            context=context)
        if fireControlOptions:
            self._fireControlOption.setOptions(options=fireControlOptions)
        self._fireControlOption.setEnabled(enabled=len(fireControlOptions) > 0)

    def createSteps(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = self._createWeaponStep(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)            
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)
                              
        step = self._createMountStep(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

        step = self._createAutoloaderStep(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)            
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)
    
        step = self._createFireControlStep(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)

    def _createMountStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        mountSize = self.mountSize()
        if not mountSize:
            return None
        mountCost, mountSlots = _WeaponMountImpl._MountSizeData[mountSize]

        linkedMountCount = self.linkedMountCount()
        if linkedMountCount:
            linkedMountCount = common.ScalarCalculation(
                value=linkedMountCount,
                name='Specified Multi-Link Mount Count')        

        stepName = f'Weapon Mount ({mountSize.value})'
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'
        stepType = f'Weapon #{mountIndex}'
        step = robots.RobotStep(
            name=stepName,
            type=stepType)
        
        mountCost = common.ScalarCalculation(
            value=mountCost,
            name=f'{mountSize.value} Mount Cost')
        mountSlots = common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots')        
        
        if linkedMountCount:
            mountCost = common.Calculator.multiply(
                lhs=mountCost,
                rhs=linkedMountCount,
                name=f'Multi-Link {mountCost.name()}')
            mountSlots = common.Calculator.multiply(
                lhs=mountSlots,
                rhs=linkedMountCount,
                name=f'Multi-Link {mountSlots.name()}')

        step.setCredits(credits=construction.ConstantModifier(value=mountCost))
        step.setSlots(slots=construction.ConstantModifier(value=mountSlots))

        if linkedMountCount:
            step.addNote(note=_WeaponMountImpl._MultiLinkAttackNote.format(
                count=linkedMountCount.value(),
                modifier=linkedMountCount.value() - 1))
            
        return step
        
    def _createWeaponStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        weaponData = self.weaponData()
        if not weaponData:
            return None
        linkedMountCount = self.linkedMountCount()
        if linkedMountCount:
            linkedMountCount = common.ScalarCalculation(
                    value=linkedMountCount,
                    name='Specified Multi-Link Mount Count')

        stepName = weaponData.name()
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'
        stepType = f'Weapon #{mountIndex}'
        step = robots.RobotStep(
            name=stepName,
            type=stepType)
        
        weaponCost = common.ScalarCalculation(
            value=weaponData.cost(),
            name=f'{weaponData.name()} Cost')
        if linkedMountCount:
            weaponCost = common.Calculator.multiply(
                lhs=weaponCost,
                rhs=linkedMountCount,
                name=f'Multi-Link {weaponCost.name()}')            
        step.setCredits(credits=construction.ConstantModifier(value=weaponCost))
        
        skill = weaponData.skill()
        specialty = weaponData.specialty()
        skillName = skill.name()
        if specialty:
            skillName += f' ({specialty.value})'

        damage = weaponData.damage()
        traits = weaponData.traits()

        if damage:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Base Damage = {damage}'))
        if traits:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Traits = {traits}'))

        note = f'The weapon uses the {skillName} skill'
        if damage and traits:
            note += f', does a base {damage} damage and has the {traits} trait(s)'
        elif damage:
            note += f' and does a base {damage} damage'
        elif traits:
            note += f' and has the {traits} traits'
        note += '.'
        step.addNote(note)

        if weaponData.magazineCost():
            step.addNote(f'A magazine for the weapon costs Cr{weaponData.magazineCost()}')

        return step
            
    def _createAutoloaderStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        autoloaderMagazineCount = self.autoloaderMagazineCount()
        if not autoloaderMagazineCount:
            return None
        autoloaderMagazineCount = common.ScalarCalculation(
            value=autoloaderMagazineCount,
            name='Specified Autoloader Magazine Count')         
        
        # The autoloader uses the same number of slots as the mount.
        mountSize = self.mountSize()
        if not mountSize:
            return None
        _, mountSlots = _WeaponMountImpl._MountSizeData[mountSize]        
        
        weaponData = self.weaponData()
        if not weaponData:
            return None
        
        magazineCost = weaponData.magazineCost()
        if magazineCost == None:
            return None
        magazineCost = common.ScalarCalculation(
            value=magazineCost,
            name=f'{weaponData.name()} Magazine Cost')        

        linkedMountCount = self.linkedMountCount()
        if linkedMountCount:
            linkedMountCount = common.ScalarCalculation(
                value=linkedMountCount,
                name='Specified Multi-Link Mount Count')

        stepName = f'Autoloader ({autoloaderMagazineCount.value()})'
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'            
        stepType = f'Weapon #{mountIndex}'
        step = robots.RobotStep(
            name=stepName,
            type=stepType)

        mountSlots = common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots')
        autoloaderSlots = common.Calculator.equals(
            value=mountSlots,
            name='Autoloader Required Slots')
        if linkedMountCount:
            autoloaderSlots = common.Calculator.multiply(
                lhs=autoloaderSlots,
                rhs=linkedMountCount,
                name=f'Multi-Link {autoloaderSlots.name()}')
        step.setSlots(slots=construction.ConstantModifier(value=autoloaderSlots))

        autoloaderCost = common.Calculator.multiply(
            lhs=common.Calculator.multiply(
                lhs=magazineCost,
                rhs=autoloaderMagazineCount),
            rhs=_WeaponMountImpl._AutoloaderMagazineCostMultiplier,
            name='Autoloader Cost')
        if linkedMountCount:
            autoloaderCost = common.Calculator.multiply(
                lhs=autoloaderCost,
                rhs=linkedMountCount,
                name=f'Multi-Link {autoloaderCost.name()}')
        step.setCredits(credits=construction.ConstantModifier(
            value=autoloaderCost))
        
        return step

    def _createFireControlStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        fireControlLevel = self.fireControlLevel()
        if not fireControlLevel:
            return None
        
        stepName = f'Fire Control System ({fireControlLevel.value})'
        stepType = f'Weapon #{mountIndex}'
        step = robots.RobotStep(
            name=stepName,
            type=stepType)
        
        _, fireControlCost, weaponSkillDM = _WeaponMountImpl._FireControlData[fireControlLevel]
        
        fireControlCost = common.ScalarCalculation(
            value=fireControlCost,
            name=f'{fireControlLevel.value} Fire Control System Cost')
        step.setCredits(credits=construction.ConstantModifier(
            value=fireControlCost))
        
        step.setSlots(slots=construction.ConstantModifier(
            value=_WeaponMountImpl._FireControlSlots))
        
        weaponData = self.weaponData()
        if weaponData:
            skill = weaponData.skill()
            specialty = weaponData.specialty()
            skillName = skill.name()
            if specialty:
                skillName += f' ({specialty.value})'
        else:
            skillName = 'relevant weapon'
        step.addNote(note=_WeaponMountImpl._FireControlWeaponSkillNote.format(
            modifier=common.formatNumber(number=weaponSkillDM, alwaysIncludeSign=True),
            skill=skillName))

        step.addNote(note=_WeaponMountImpl._FireControlScopeNote)

        hasLaserDesignator = False
        for componentType in _WeaponMountImpl._FireControlLaserDesignatorComponents:
            if context.hasComponent(
                componentType=componentType,
                sequence=sequence):
                hasLaserDesignator = True
                break
        if hasLaserDesignator:
            step.addNote(note=_WeaponMountImpl._FireControlLaserDesignatorNote)
        
        return step

    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        return traveller.WeaponSize # All sizes are allowed by default
    
    def _allowedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[str]:
        mountSize = self.mountSize()
        if not mountSize:
            return []

        robotTL = context.techLevel()
        allowed = []
        for weapon in traveller.TravellerCompanionWeapons:
            if weapon.size() == mountSize and weapon.techLevel() <= robotTL:
                allowed.append(weapon.name())
        return allowed
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < _WeaponMountImpl._AutoloaderMinTL.value():
            return False
                
        weaponData = self.weaponData()
        return weaponData and weaponData.magazineCost() != None
    
    def _allowedMultiLinkCount(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        weaponData = self.weaponData()
        if not weaponData or not weaponData.multiLink():
            return 0
        return 4            
    
    def _allowedFireControls(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[FireControlLevel]:
        robotTL = context.techLevel()
        allowed = []
        for level in FireControlLevel:
            minTL, _, _ = _WeaponMountImpl._FireControlData[level]
            if minTL <= robotTL:
                allowed.append(level)
        return allowed

class _ManipulatorMountImpl(_WeaponMountImpl):
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
        - Requirement: The number of manipulators that can be multi-linked
        should be limited to the number of manipulators of the same size,
        STR & DEX
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
    # NOTE: As far as I can see the rules don't give any guidance when it
    # comes to if manipulators mounted weapons of different Size, STR or DEX
    # can be linked together. I've gone with that all 3 attributes must be
    # identical for multi-linking. This is my best guess based on the
    # description of linked mounts (p61) where it says weapons of the same
    # type so it would make logical sense that the manipulators would need
    # to be the same type

    _ManipulatorSizeData = {
        traveller.WeaponSize.Small: 3,
        traveller.WeaponSize.Medium: 5,
        traveller.WeaponSize.Heavy: 7,
        traveller.WeaponSize.Vehicle: None # Not compatible with manipulator mounts
    }
    _MinManipulatorSize = common.ScalarCalculation(
        value=3, # Size required for small mount
        name='Manipulator Mount Min Manipulator Size')

    def __init__(self) -> None:
        super().__init__()

        self._manipulatorOption = construction.StringOption(
            id='Manipulator',
            name='Manipulator',
            isEditable=False,
            options=[''], # This will be replaced by updateOptions
            description='Specify which manipulator the weapon is mounted on')
        
    def manipulatorName(self) -> typing.Optional[str]:
        return self._manipulatorOption.value() if self._manipulatorOption.isEnabled() else None
        
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        manipulators = self._usableManipulators(
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
        manipulators = self._usableManipulators(sequence=sequence, context=context)
        self._manipulatorOption.setOptions(
            options=list(manipulators.keys()))

        super().updateOptions(sequence=sequence, context=context)
        
    # NOTE: The names generated for this manipulator MUST remain consistent
    # between versions otherwise it will break weapons saved with previous
    # versions. For this reason it shouldn't use things like the components
    # instance string.
    def _usableManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.ManipulatorInterface]:
        mapping = {}

        manipulators = context.findComponents(
            componentType=robots.BaseManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.BaseManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Base Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator

        manipulators = context.findComponents(
            componentType=robots.AdditionalManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.AdditionalManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Additional Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator

        manipulators = context.findComponents(
            componentType=robots.LegManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.LegManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Leg Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator                   

        return mapping
    
    def _linkableManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.ManipulatorInterface]:
        mountSize = self.mountSize()
        if not mountSize:
            # Only mounted weapons are linkable
            return {}            

        manipulators = self._usableManipulators(
            sequence=sequence,
            context=context)
        manipulator = manipulators.get(self._manipulatorOption.value())
        if not manipulator:
            return {}

        filtered = {}
        for name, other in manipulators.items():
            if other == manipulator:
                continue
            if other.size() == manipulator.size() and \
                other.dexterity() == manipulator.dexterity() and \
                other.strength() == manipulator.strength():
                filtered[name] = other
        return filtered
        
    def _manipulator(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.ManipulatorInterface]:
        manipulatorName = self.manipulatorName()
        if not manipulatorName:
            return None
        manipulators = self._usableManipulators(
            sequence=sequence,
            context=context)
        return manipulators.get(manipulatorName)
    
    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        allowed = super()._allowedMountSizes(
            sequence=sequence,
            context=context)

        autoLoaderCount = self.autoloaderMagazineCount()
        manipulator = self._manipulator(
            sequence=sequence,
            context=context)
        if not manipulator:
            return []
        
        filtered = []
        for mountSize in allowed:
            minSize = _ManipulatorMountImpl._ManipulatorSizeData[mountSize]
            if not minSize:
                continue # Not compatible with manipulators
            if autoLoaderCount:
                minSize += _ManipulatorMountImpl._AutoloaderMinManipulatorSizeModifier.value()
            if manipulator.size() >= minSize:
                filtered.append(mountSize)
        return filtered
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # NOTE: Intentionally don't call base impl
        if context.techLevel() < _WeaponMountImpl._AutoloaderMinTL.value():
            return False
                
        weaponData = self.weaponData()
        if not weaponData or weaponData.magazineCost() == None:
            return False

        mountSize = self.mountSize()
        manipulator = self._manipulator(
            sequence=sequence,
            context=context)
        if not manipulator:
            return False

        supportsAutoloader = False
        if mountSize and manipulator:
            minSize = _ManipulatorMountImpl._ManipulatorSizeData[mountSize] + \
                _ManipulatorMountImpl._AutoloaderMinManipulatorSizeModifier.value()
            supportsAutoloader = manipulator.size() >= minSize
        return supportsAutoloader
    
    def _allowedMultiLinkCount(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        # NOTE: Intentionally don't call base impl
        weaponData = self.weaponData()
        if not weaponData or not weaponData.multiLink():
            return 0
                
        manipulators = self._linkableManipulators(
            sequence=sequence,
            context=context)
        if not manipulators:
            return 0
        # Return the number of manipulators that can be in the group including
        # the main selected manipulator (i.e. the number that can be linked
        # with it + 1)
        return len(manipulators) + 1
    
class _HandHeldMountImpl(_ManipulatorMountImpl):
    """
    - Requirement: Not compatible if there are no compatible Fire Control
    Systems
    - Option: Mount Size
        - Requirement: Not compatible with hand held weapons
    - Option: Weapon
        - Requirement: Not compatible with hand held weapons
    - Option: Autoloader
        - Requirement: Not compatible with hand held weapons
    - Option: Multi-Link
        - Requirement: Not compatible with hand held weapons
    - Option: Fire Control System
        - Requirement: Selection is mandatory
    """
    # NOTE: I added the requirement that the hand held mount is incompatible
    # if there are no compatible Fire Control Systems and selection of one is
    # mandatory as the Fire Control System is the only thing that the
    # component adds so it's useless without it.
    # NOTE: The fact that Autoloaders aren't compatible with hand held weapons
    # is a bit leap of logic on my part. It seems reasonably logical autoloading
    # needs the weapon to be connected to the robot in some way so ammo can be
    # transferred. This wouldn't really make sense for a weapon the robot can
    # pick up and put down freely. If the robots manipulator was sufficiently
    # human like it could even use unmodified human weapons.

    def __init__(self) -> None:
        super().__init__()
        self._fireControlOption.setOptional(isOptional=False)

    def weaponName(self) -> typing.Optional[str]:
        return None
    
    def weaponData(self) -> typing.Optional[traveller.WeaponData]:
        return None

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        allowedFireControl = self._allowedFireControls(
            sequence=sequence,
            context=context)
        return len(allowedFireControl) > 1
    
    def _createFireControlStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        step = super()._createFireControlStep(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)
        if not step:
            return None
        
        # Create a new step that is the same as the base one but with a
        # different name that makes it clear it's for hand held weapons. This is
        # needed as there is no actual 'mount' step for hand held mounts, only a
        # fire control step
        return robots.RobotStep(
            name=f'Hand Held Weapon {step.name()}',
            type=step.type(),
            costs=step.costs(),
            factors=step.factors(),
            notes=step.notes())
    
    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[traveller.WeaponSize]:
        return []

    def _allowedMultiLinkCount(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> int:
        return 0
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return False

class Weapon(robots.WeaponInterface):
    def __init__(
            self,
            componentString: str,
            impl: _WeaponMountImpl
            ) -> None:
        super().__init__()
        self._componentString = componentString
        self._impl = impl

    def mountSize(self) -> typing.Optional[traveller.WeaponSize]:
        return self._impl.mountSize()
    
    def weaponName(self) -> typing.Optional[str]:
        return self._impl.weaponName()

    def weaponData(self) -> typing.Optional[traveller.WeaponData]:
        return self._impl.weaponData()
        
    def autoloaderMagazineCount(self) -> typing.Optional[int]:
        return self._impl.autoloaderMagazineCount()
    
    def linkedMountCount(self) -> typing.Optional[int]:
        return self._impl.linkedMountCount()
    
    def fireControlLevel(self) -> typing.Optional[FireControlLevel]:
        return self._impl.fireControlLevel()

    def componentString(self) -> str:
        return self._componentString
    
    def typeString(self) -> str:
        return 'Weapon'

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
        return self._impl.updateOptions(
            sequence=sequence,
            context=context)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        mounts = context.findComponents(
            componentType=robots.Weapon,
            sequence=sequence)
        mountIndex = None
        for index, mount in enumerate(mounts):
            if mount == self:
                mountIndex = index + 1
                break

        self._impl.createSteps(
            mountIndex=mountIndex,
            sequence=sequence,
            context=context)  

class ServoMountedWeapon(Weapon):
    def __init__(self) -> None:
        super().__init__(
            componentString='Servo Mounted',
            impl=_WeaponMountImpl())
    
# This component is for weapons mounted to/in a manipulator.
class ManipulatorMountedWeapon(Weapon):
    def __init__(self) -> None:
        super().__init__(
            componentString='Manipulator Mounted',
            impl=_ManipulatorMountImpl())

# This component exists to allow for Fire Control Systems to be added for hand
# held weapons.
class HandHeldWeapon(Weapon):
    def __init__(self) -> None:
        super().__init__(
            componentString='Hand Held',
            impl=_HandHeldMountImpl())
