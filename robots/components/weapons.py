import common
import construction
import enum
import robots
import traveller
import typing

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
# NOTE: I got another chance to pick Geir's brains and he clarified the
# following
# https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/
#
# Clarification 4: Fire Control System can be used with hand held weapons
#
# Clarification 5: Hand held weapons can be multi-linked but only if they're
# being controlled by a Fire Control System
# TODO: If Geir comes back saying he likes the new proposal for multi-link
# better then I think I'm pretty much reverting back to how weapons were
# before all the recent changes. I'll keep support for multi-select options
# but they won't be used. The old implementation might need some rejigging:
# - Remove hand held mounts. I think this might make sense as it's own
# stage where you can just select weapons that the robot can pick up/put down.
# It would consume slots and would just have the weapon cost.
# - Probably need to update some notes
# - Rewrite all the big comments above to match the new understanding

# This is the mapping of weapon size to the min manipulator size required to
# use the weapon and still get the robots DEX/STR modifier (p61). There is
# no entry for Vehicle weapons as no manipulator can wield them
_MinManipulatorSizeMap = {
    traveller.WeaponSize.Small: 3,
    traveller.WeaponSize.Medium: 5,
    traveller.WeaponSize.Heavy: 7
}

# NOTE: The names generated by this function MUST remain consistent between
# versions otherwise it will break robots saved with previous versions. For
# this reason it shouldn't use things like the components instance string.
# TODO: Check I'm happy with the format before release
def _enumerateManipulators(
        sequence: str,
        context: robots.RobotContext
        ) -> typing.Mapping[str, robots.ManipulatorInterface]:
    results = {}

    manipulators = context.findComponents(
        componentType=robots.BaseManipulator,
        sequence=sequence)
    for index, manipulator in enumerate(manipulators):
        assert(isinstance(manipulator, robots.BaseManipulator))
        name = 'Base Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
            index=index + 1,
            size=manipulator.size(),
            dex=manipulator.dexterity(),
            str=manipulator.strength())
        results[name] = manipulator

    manipulators = context.findComponents(
        componentType=robots.AdditionalManipulator,
        sequence=sequence)
    for index, manipulator in enumerate(manipulators):
        assert(isinstance(manipulator, robots.AdditionalManipulator))    
        name = 'Additional Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
            index=index + 1,
            size=manipulator.size(),
            dex=manipulator.dexterity(),
            str=manipulator.strength())
        results[name] = manipulator

    manipulators = context.findComponents(
        componentType=robots.LegManipulator,
        sequence=sequence)
    for index, manipulator in enumerate(manipulators):
        assert(isinstance(manipulator, robots.LegManipulator))      
        name = 'Leg Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
            index=index + 1,
            size=manipulator.size(),
            dex=manipulator.dexterity(),
            str=manipulator.strength())
        results[name] = manipulator                   

    return results

class MountedWeapon(robots.MountedWeaponInterface):
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
    # NOTE: The note about which weapons a mount of a given size can use is
    # handled in finalisation
    # TODO: After all the clarifications I still need to support weapons
    # held by a manipulator using a Fire Control System (they just can't
    # be multi-linked)

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

    _MultiLinkFireControlNote = 'Linked weapons require a Fire Control System to be fired as a group. (clarified by Geir Lanesskog, Robot Handbook author)'
    # TODO: Should the modifier in this note include the DEX/STR characteristic modifier? If not should it say explicitly what the modifier does include?
    _MultiLinkAttackKnownDiceNote = 'Only a single attack is made when the {count} linked weapons are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result. (p61)'
    _MultiLinkAttackUnknownDiceNote = 'Only a single attack is made when the {count} linked weapons are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result of each damage dice. (p61)'

    class FireControlLevel(enum.Enum):
        Basic = 'Basic'
        Improved = 'Improved'
        Enhanced = 'Enhanced'
        Advanced = 'Advanced'

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
    _FireControlScopeNote = 'The Fire Control System gives the Scope trait (p60).'
    _FireControlWeaponSkillNote = 'When making an attack roll, you can choose to use the Fire Control System\'s Weapon Skill DM of {modifier} instead of the robots {skill} skill (p60 and clarified by Geir Lanesskog, Robot Handbook author)'
    _FireControlLaserDesignatorComponents = [
        robots.LaserDesignatorDefaultSuiteOption,
        robots.LaserDesignatorSlotOption]
    _FireControlLaserDesignatorNote = 'DM+2 to attacks against targets that have been illuminated with the Laser Designator (p37).'

    def __init__(
            self,
            componentString: str
            ) -> None:
        super().__init__()

        self._componentString = componentString

        self._mountSizeOption = construction.EnumOption(
            id='MountSize',
            name='Mount Size',
            type=traveller.WeaponSize,
            description='Specify the size of the mount, this determines what size of weapons can be mounted to it.')            
        
        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            value=None,
            options=['default'], # This will be replaced when updateOptions is called
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
            maxValue=MountedWeapon._MultiLinkMaxGroupSize,
            isOptional=True,
            description='Specify the number of weapons to link so they fire as a single action.')
        
        self._fireControlOption = construction.EnumOption(
            id='FireControl',
            name='Fire Control',
            type=MountedWeapon.FireControlLevel,
            isOptional=True,
            description='Specify Fire Control System level.')
        
    def mountSize(self) -> traveller.WeaponSize:
        return self._mountSizeOption.value()
    
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
    
    def fireControl(self) -> typing.Optional['MountedWeapon.FireControlLevel']:
        if not self._fireControlOption.isEnabled():
            return None
        return self._fireControlOption.value()
    
    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Mounted Weapon'            
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
        
        weaponOptions = self._allowedWeapons(
            sequence=sequence,
            context=context)
        return len(weaponOptions) > 0
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        options.append(self._mountSizeOption)
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
        mountSizeOptions = self._allowedMountSizes(
            sequence=sequence,
            context=context)
        if mountSizeOptions:
            self._mountSizeOption.setOptions(options=mountSizeOptions)
        
        weaponOptions = self._allowedWeapons(
            sequence=sequence,
            context=context)
        if weaponOptions:
            self._weaponOption.setOptions(options=weaponOptions)

        self._autoLoaderOption.setEnabled(
            enabled=self._allowedAutoloader(sequence=sequence, context=context))

        self._linkedCountOption.setEnabled(
            enabled=self._allowedLinkedWeapons(sequence=sequence, context=context))
        
        fireControlOptions = self._allowedFireControls(
            sequence=sequence,
            context=context)        
        if fireControlOptions:
            self._fireControlOption.setOptions(options=fireControlOptions)        
            self._fireControlOption.setOptional(
                isOptional=not self._linkedCountOption.value()) # Mandatory if linked
        self._fireControlOption.setEnabled(
            enabled=len(fireControlOptions) > 0)
        
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        mountIndex = None
        otherMounts = context.findComponents(
            componentType=type(self),
            sequence=sequence)
        for index, otherMount in enumerate(otherMounts):
            if otherMount == self:
                mountIndex = index + 1
                break

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
        
    def _createWeaponStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        mountSize = self.mountSize()
        if not mountSize:
            return None
        
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None
        
        stepName = self.componentString()
        if mountIndex:
            stepName += f' #{mountIndex}'
        stepName += f' - {weaponData.name()}'
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
            
        weaponCost = common.ScalarCalculation(
            value=weaponData.cost(),
            name=f'{weaponData.name()} Cost')
        
        if linkedGroupSize:
            weaponCost = common.Calculator.multiply(
                lhs=weaponCost,
                rhs=linkedGroupSize,
                name=f'Linked {weaponCost.name()}')

        if weaponCost.value() > 0:
            step.setCredits(credits=construction.ConstantModifier(value=weaponCost))

        damage = weaponData.damage()
        if damage:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Base Damage = {damage}'))

        traits = weaponData.traits()
        if traits:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Traits = {traits}'))

        # TODO: This should be combined with the note about additional damage
        # for multi-linked weapons. I think it's coming down to they always
        # fire all weapons at the same time so they're effectively a single
        # weapon that does more damage.
        skill = weaponData.skill()
        skillName = skill.name(speciality=weaponData.specialty())        
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
    
    def _createMountStep(
            self,
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        mountSize = self.mountSize()
        if not mountSize:
            return None
        
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None
        
        stepName = self.componentString()
        if mountIndex:
            stepName += f' #{mountIndex}'
        stepName += ' - Mounting'
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())

        mountCost, mountSlots = MountedWeapon._MountSizeData[mountSize]        
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
            mountIndex: typing.Optional[int],
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

        mountSize = self.mountSize()
        if not mountSize:
            return None

        stepName = self.componentString()
        if mountIndex:
            stepName += f' #{mountIndex}'
        stepName += f' - Autoloader {autoloaderMagazineCount.value()}'
        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            stepName += f' - x{linkedGroupSize.value()}'

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())                       

        magazineCost = common.ScalarCalculation(
            value=magazineCost,
            name=f'{weaponData.name()} Magazine Cost')
        autoloaderCost = common.Calculator.multiply(
            lhs=common.Calculator.multiply(
                lhs=magazineCost,
                rhs=autoloaderMagazineCount),
            rhs=MountedWeapon._AutoloaderMagazineCostMultiplier,
            name='Autoloader Cost')
        
        _, mountSlots = MountedWeapon._MountSizeData[mountSize]
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
            mountIndex: typing.Optional[int],
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        fireControl = self.fireControl()
        if not fireControl:
            return None
        assert(isinstance(fireControl, MountedWeapon.FireControlLevel))

        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return None
        
        stepName = self.componentString()
        if mountIndex:
            stepName += f' #{mountIndex}'
        stepName += f' - Fire Control System ({fireControl.value})'
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString()) 

        _, fireControlCost, weaponSkillDM = \
            MountedWeapon._FireControlDataMap[fireControl]
        
        fireControlCost = common.ScalarCalculation(
            value=fireControlCost,
            name=f'{fireControl.value} Fire Control System Cost')
        step.setCredits(credits=construction.ConstantModifier(value=fireControlCost))
        
        skill = weaponData.skill()
        skillName = skill.name(speciality=weaponData.specialty())        
        step.addNote(note=MountedWeapon._FireControlWeaponSkillNote.format(
            modifier=common.formatNumber(number=weaponSkillDM, alwaysIncludeSign=True),
            skill=skillName))

        step.addNote(note=MountedWeapon._FireControlScopeNote)

        linkedGroupSize = self.linkedGroupSize()
        if linkedGroupSize:
            step.addNote(note=MountedWeapon._MultiLinkFireControlNote)

            damageDieCount = None
            if weaponData:
                damageRoll = common.DiceRoll.fromString(weaponData.damage())
                if damageRoll:
                    damageDieCount = damageRoll.dieCount()

            if damageDieCount:
                step.addNote(note=MountedWeapon._MultiLinkAttackKnownDiceNote.format(
                    count=linkedGroupSize.value(),
                    modifier=(linkedGroupSize.value() - 1) * damageDieCount.value()))
            else:
                step.addNote(note=MountedWeapon._MultiLinkAttackUnknownDiceNote.format(
                    count=linkedGroupSize.value(),
                    modifier=linkedGroupSize.value() - 1))        

        hasLaserDesignator = False
        for componentType in MountedWeapon._FireControlLaserDesignatorComponents:
            if context.hasComponent(
                componentType=componentType,
                sequence=sequence):
                hasLaserDesignator = True
                break
        if hasLaserDesignator:
            step.addNote(note=MountedWeapon._FireControlLaserDesignatorNote)

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

        weapons = traveller.findStockWeapons(
            weaponSet=context.weaponSet(),
            currentTL=context.techLevel())
        allowed = []
        for weapon in weapons:
            if weapon.size() == mountSize:
                allowed.append(weapon.name())
        return allowed
    
    def _allowedLinkedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # Linking weapons requires a Fire Control System
        if context.techLevel() < MountedWeapon._FireControlMinTL.value():
            return False
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        return weaponData and weaponData.multiLink()
    
    def _allowedFireControls(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[FireControlLevel]:
        robotTL = context.techLevel()
        allowed = []
        for level in MountedWeapon.FireControlLevel:
            minTL, _, _ = MountedWeapon._FireControlDataMap[level]
            if minTL <= robotTL:
                allowed.append(level)
        return allowed    
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < MountedWeapon._AutoloaderMinTL.value():
            return False
                
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        return weaponData and weaponData.magazineCost() != None
    
class ServoMountedWeapon(MountedWeapon):
    def __init__(self) -> None:
        super().__init__(componentString='Servo Mount')

# This component is for weapons mounted to/in a manipulator.
class ManipulatorMountedWeapon(MountedWeapon):
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

    _ManipulatorSizeData = {
        traveller.WeaponSize.Small: 3,
        traveller.WeaponSize.Medium: 5,
        traveller.WeaponSize.Heavy: 7,
        traveller.WeaponSize.Vehicle: None # Not compatible with manipulator mounts
    }

    def __init__(self) -> None:
        super().__init__(componentString='Manipulator Mount')

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
        
        manipulators = _enumerateManipulators(
            sequence=sequence, 
            context=context)
        minUsableSize = _MinManipulatorSizeMap[traveller.WeaponSize.Small]
        meetsMinimum = False
        for manipulator in manipulators.values():
            if manipulator.size() >= minUsableSize:
                meetsMinimum = True
                break
        return meetsMinimum
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.insert(0, self._manipulatorOption)
        return options
    
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        manipulators = _enumerateManipulators(sequence=sequence, context=context)
        self._manipulatorOption.setOptions(
            options=manipulators.keys())

        super().updateOptions(sequence=sequence, context=context)
        
    def _manipulator(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.ManipulatorInterface]:
        manipulatorName = self.manipulatorName()
        if not manipulatorName:
            return None
        manipulators = _enumerateManipulators(
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
            minSize = ManipulatorMountedWeapon._ManipulatorSizeData[mountSize]
            if not minSize:
                continue # Not compatible with manipulators
            if autoLoaderCount:
                minSize += ManipulatorMountedWeapon._AutoloaderMinManipulatorSizeModifier.value()
            if manipulator.size() >= minSize:
                filtered.append(mountSize)
        return filtered
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        # NOTE: Intentionally don't call base impl
        if context.techLevel() < ManipulatorMountedWeapon._AutoloaderMinTL.value():
            return False
                
        weaponData = self.weaponData(weaponSet=context.weaponSet())
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
            minSize = ManipulatorMountedWeapon._ManipulatorSizeData[mountSize] + \
                ManipulatorMountedWeapon._AutoloaderMinManipulatorSizeModifier.value()
            supportsAutoloader = manipulator.size() >= minSize
        return supportsAutoloader
