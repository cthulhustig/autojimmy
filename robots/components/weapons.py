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

#  ██████   ██████                                 █████           
# ░░██████ ██████                                 ░░███            
#  ░███░█████░███   ██████  █████ ████ ████████   ███████    █████ 
#  ░███░░███ ░███  ███░░███░░███ ░███ ░░███░░███ ░░░███░    ███░░  
#  ░███ ░░░  ░███ ░███ ░███ ░███ ░███  ░███ ░███   ░███    ░░█████ 
#  ░███      ░███ ░███ ░███ ░███ ░███  ░███ ░███   ░███ ███ ░░░░███
#  █████     █████░░██████  ░░████████ ████ █████  ░░█████  ██████ 
# ░░░░░     ░░░░░  ░░░░░░    ░░░░░░░░ ░░░░ ░░░░░    ░░░░░  ░░░░░░  

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
    """
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
    
    def __init__(self) -> None:
        super().__init__()

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
        
    def autoloaderMagazineCount(self) -> typing.Optional[common.ScalarCalculation]:
        if not self._autoLoaderOption.isEnabled() or not self._autoLoaderOption.value():
            return None
        return common.ScalarCalculation(
            value=self._autoLoaderOption.value(),
            name='Specified Autoloader Magazine Count')
    
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

    def createStep(
            self,
            typeString: str,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        mountSize = self.mountSize()
        if not mountSize:
            return
        
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        if not weaponData:
            return
        
        stepName = weaponData.name()
        autoloaderMagazineCount = self.autoloaderMagazineCount()
        if autoloaderMagazineCount:
            stepName += f' (Autoloader {autoloaderMagazineCount.value()})'
        step = robots.RobotStep(
            name=stepName,
            type=typeString)        

        mountCost, mountSlots = _WeaponMountImpl._MountSizeData[mountSize]
        costs = []
        slots = []
        
        costs.append(common.ScalarCalculation(
            value=mountCost,
            name=f'{mountSize.value} Mount Cost'))
        slots.append(common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots'))

        weaponCost = weaponData.cost()
        costs.append(common.ScalarCalculation(
            value=weaponCost,
            name=f'{weaponData.name()} Cost'))
        
        skill = weaponData.skill()
        specialty = weaponData.specialty()
        skillName = skill.name()
        if specialty:
            skillName += f' ({specialty.value})'

        damage = weaponData.damage()
        if damage:
            step.addFactor(factor=construction.StringFactor(
                string=f'Weapon Base Damage = {damage}'))

        traits = weaponData.traits()
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

        magazineCost = weaponData.magazineCost()
        if autoloaderMagazineCount and magazineCost != None:       
            magazineCost = common.ScalarCalculation(
                value=magazineCost,
                name=f'{weaponData.name()} Magazine Cost')        

            mountSlots = common.ScalarCalculation(
                value=mountSlots,
                name=f'{mountSize.value} Mount Required Slots')
            slots.append(common.Calculator.equals(
                value=mountSlots,
                name='Autoloader Required Slots'))

            costs.append(common.Calculator.multiply(
                lhs=common.Calculator.multiply(
                    lhs=magazineCost,
                    rhs=autoloaderMagazineCount),
                rhs=_WeaponMountImpl._AutoloaderMagazineCostMultiplier,
                name='Autoloader Cost'))
            
        totalCost = common.Calculator.sum(
            values=costs,
            name=f'Total Cost')
        totalSlots = common.Calculator.sum(
            values=slots,
            name=f'Total Required Slots')

        if totalCost.value() > 0:
            step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        if totalSlots.value() > 0:
            step.setSlots(slots=construction.ConstantModifier(value=totalSlots))

        context.applyStep(
            sequence=sequence,
            step=step)

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
    
    def _allowedAutoloader(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < _WeaponMountImpl._AutoloaderMinTL.value():
            return False
                
        weaponData = self.weaponData(weaponSet=context.weaponSet())
        return weaponData and weaponData.magazineCost() != None
    
class _ServoMountImpl(_WeaponMountImpl):
    def __init__(self) -> None:
        super().__init__()

# This component is for weapons mounted to/in a manipulator.
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
        
    def _linkableManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.ManipulatorInterface]:
        mountSize = self.mountSize()
        if not mountSize:
            # Only mounted weapons are linkable
            return {}            

        manipulators = _enumerateManipulators(
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
        if context.techLevel() < _ManipulatorMountImpl._AutoloaderMinTL.value():
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
            minSize = _ManipulatorMountImpl._ManipulatorSizeData[mountSize] + \
                _ManipulatorMountImpl._AutoloaderMinManipulatorSizeModifier.value()
            supportsAutoloader = manipulator.size() >= minSize
        return supportsAutoloader
    
class ServoWeaponMount(robots.ServoWeaponMountInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _ServoMountImpl()

    def mountSize(self) -> traveller.WeaponSize:
        return self._impl.mountSize()
    
    def weaponName(self) -> str:
        return self._impl.weaponName()

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        return self._impl.weaponData(weaponSet=weaponSet)
        
    def autoloaderMagazineCount(self) -> typing.Optional[int]:
        return self._impl.autoloaderMagazineCount()
    
    def componentString(self) -> str:
        return 'Servo Mount'
    
    def typeString(self) -> str:
        return 'Servo Mount'

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
        self._impl.createStep(
            typeString=self.typeString(),
            sequence=sequence,
            context=context)
        
class ManipulatorWeaponMount(robots.ManipulatorWeaponMountInterface):
    def __init__(self) -> None:
        super().__init__()
        self._impl = _ManipulatorMountImpl()
        
    def mountSize(self) -> traveller.WeaponSize:
        return self._impl.mountSize()
    
    def weaponName(self) -> str:
        return self._impl.weaponName()

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        return self._impl.weaponData(weaponSet=weaponSet)
        
    def autoloaderMagazineCount(self) -> typing.Optional[int]:
        return self._impl.autoloaderMagazineCount()
    
    def componentString(self) -> str:
        return 'Manipulator Mount'
    
    def typeString(self) -> str:
        return 'Manipulator Mount'

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
        self._impl.createStep(
            typeString=self.typeString(),
            sequence=sequence,
            context=context)


#  ██████   ██████            ████   █████     ███             █████        ███             █████     
# ░░██████ ██████            ░░███  ░░███     ░░░             ░░███        ░░░             ░░███      
#  ░███░█████░███  █████ ████ ░███  ███████   ████             ░███        ████  ████████   ░███ █████
#  ░███░░███ ░███ ░░███ ░███  ░███ ░░░███░   ░░███  ██████████ ░███       ░░███ ░░███░░███  ░███░░███ 
#  ░███ ░░░  ░███  ░███ ░███  ░███   ░███     ░███ ░░░░░░░░░░  ░███        ░███  ░███ ░███  ░██████░  
#  ░███      ░███  ░███ ░███  ░███   ░███ ███ ░███             ░███      █ ░███  ░███ ░███  ░███░░███ 
#  █████     █████ ░░████████ █████  ░░█████  █████            ███████████ █████ ████ █████ ████ █████
# ░░░░░     ░░░░░   ░░░░░░░░ ░░░░░    ░░░░░  ░░░░░            ░░░░░░░░░░░ ░░░░░ ░░░░ ░░░░░ ░░░░ ░░░░░ 

# NOTE: The names generated by this function MUST remain consistent between
# versions otherwise it will break robots saved with previous versions. For
# this reason it shouldn't use things like the components instance string.
# TODO: Make sure I'm happy with what is being written before release
def _enumerateMounts(
        sequence: str,
        context: robots.RobotContext
        ) -> typing.Mapping[str, robots.WeaponMountInterface]:
    results = {}

    mounts = context.findComponents(
        componentType=ServoWeaponMount,
        sequence=sequence)
    for index, mount in enumerate(mounts):
        assert(isinstance(mount, ServoWeaponMount))
        weaponName = mount.weaponName()
        if not weaponName:
            continue
        weaponString = f'Servo Mount #{index + 1}: {weaponName}'
        results[weaponString] = mount

    mounts = context.findComponents(
        componentType=ManipulatorWeaponMount,
        sequence=sequence)
    for index, mount in enumerate(mounts):
        assert(isinstance(mount, ManipulatorWeaponMount))
        weaponName = mount.weaponName()
        if not weaponName:
            continue
        weaponString = f'Manipulator Mount #{index + 1}: {weaponName}'
        results[weaponString] = mount

    return results

class MultiLink(robots.MultiLinkInterface):
    """
    - Requirement: Hand held weapons can be multi-linked but only if they're
    being controlled by a Fire Control System (clarified by Geir)
    - Requirement: Up to 4 weapons OF THE SAME TYPE can be linked to fire as
    a single attack. If the attack succeeds, only one damage roll is made
    and +1 PER DAMAGE DICE is added for each additional weapon (p61)
    """
    # TODO: Need something to handle that hand held weapons can only be
    # multi-linked when controlled by a fire control system
    # - This will probably need to be done in finalisation
    # - I'm kind of tempted to just not bother
    # TODO: Need something to handle the case where linked manipulators have
    # different DEX/STR values. This could be manipulators with mounts or 
    # manipulators holding weapons
    # Update: I've sent a question to Geir about this

    _MaxMultiLinkWeaponCount = 4

    # TODO: Should the modifier in this note include the DEX/STR characteristic modifier? If not should it say explicitly what the modifier does include?
    _MultiLinkAttackKnownDiceNote = 'Only a single attack is made when the {count} linked weapons are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result. (p61)'
    _MultiLinkAttackUnknownDiceNote = 'Only a single attack is made when the {count} linked weapons are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result of each damage dice. (p61)'

    _MultiLinkManipulatorNote = 'Weapons held in a robots manipulator can only be used as part of a linked group of weapons when the weapon being held is of the same type as the other manipulators and mounts in the group. (p61)'

    def __init__(self) -> None:
        super().__init__()

        self._weaponsOption = construction.MultiSelectOption(
            id='Weapons',
            name='Weapons',
            options=[],
            description='Select the weapons to be linked')
        
    def weaponStrings(self) -> typing.Iterable[str]:
        return self._weaponsOption.value()
        
    def instanceString(self) -> str:
        weapons = self._weaponsOption.value()
        if not weapons:
            return self.componentString()
        assert(isinstance(weapons, list))
        return f'{self.componentString()} ({len(weapons)})'

    def componentString(self) -> str:
        return 'Linked Group'
    
    def typeString(self) -> str:
        return 'Weapon Link'    
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
        
        weapons = self._enumerateWeapons(sequence=sequence, context=context)
        return len(weapons) >= 2 # Must be at least 2 to link
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._weaponsOption]
        
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        weapons = self._enumerateWeapons(
            sequence=sequence,
            context=context)
        self._weaponsOption.setOptions(options=weapons.keys())
        selection = list(self._weaponsOption.value())
        unselectable = set()

        # Make weapons in use with other multi links unselectable
        others = context.findComponents(
            componentType=MultiLink,
            sequence=sequence)
        for other in others:
            assert(isinstance(other, MultiLink))
            if other == self:
                continue
            for inUseWeapon in other.weaponStrings():
                unselectable.add(inUseWeapon)
                if inUseWeapon in selection:
                    selection.remove(inUseWeapon)

        # If there are any mounts in the multi-link, find the weapon type being
        # used. This works on the assumption that the current selection should
        # generally only contain a single weapon type (or no weapon type if only
        # manipulators are being multi-linked). If there does happen to be more
        # than one type (e.g. a bug or manually edited file data) then weapon
        # type of the first mount will be used as the canonical type.
        weaponName = None
        mountSize = None
        for weaponString in selection:
            weapon = weapons.get(weaponString)
            if weapon and isinstance(weapon, robots.WeaponMountInterface):
                weaponName = weapon.weaponName()
                mountSize = weapon.mountSize()
                break

        # Make weapons of different types unselectable
        if weaponName:
            for weaponString, weapon in weapons.items():
                if isinstance(weapon, robots.WeaponMountInterface) and \
                        weapon.weaponName() != weaponName:
                    unselectable.add(weaponString)
                    if weaponString in selection:
                        selection.remove(weaponString)

        # Make manipulators that don't allow for the weapon size unselectable
        if mountSize:
            minManipulatorSize = _MinManipulatorSizeMap.get(mountSize)
            for weaponString, weapon in weapons.items():
                if isinstance(weapon, robots.ManipulatorInterface) and \
                        weapon.size() < minManipulatorSize:
                    unselectable.add(weaponString)
                    if weaponString in selection:
                        selection.remove(weaponString)

        if len(selection) >= MultiLink._MaxMultiLinkWeaponCount:
            # When the max number of linked weapons has been reached, all
            # remaining weapons are unselectable
            for weaponString in weapons.keys():
                if weaponString not in selection:
                    unselectable.add(weaponString)

        self._weaponsOption.setUnselectable(unselectable=unselectable)
        self._weaponsOption.setValue(value=selection)
            
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        linkedWeapons = self._weaponsOption.value()
        assert(isinstance(linkedWeapons, list))
        linkedWeaponCount = len(linkedWeapons)
        if linkedWeaponCount < 2:
            # TODO: This should probably add the step with a warning note
            return
        
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        weapons = self._enumerateWeapons(sequence=sequence, context=context)
        weaponData: typing.Optional[traveller.StockWeapon] = None
        for weaponString in linkedWeapons:
            weapon = weapons.get(weaponString)
            if isinstance(weapon, robots.WeaponMountInterface):
                weaponData = weapon.weaponData(context.weaponSet())
                if weaponData:
                    break

        damageDieCount = None
        if weaponData:
            damageRoll = common.DiceRoll.fromString(weaponData.damage())
            if damageRoll:
                damageDieCount = damageRoll.dieCount()

        if damageDieCount:
            step.addNote(note=MultiLink._MultiLinkAttackKnownDiceNote.format(
                count=linkedWeaponCount,
                modifier=(linkedWeaponCount - 1) * damageDieCount.value()))
        else:
            step.addNote(note=MultiLink._MultiLinkAttackUnknownDiceNote.format(
                count=linkedWeaponCount,
                modifier=linkedWeaponCount - 1))
        
        weapons = self._enumerateWeapons(sequence=sequence, context=context)
        containsManipulator = False
        for weaponString in linkedWeapons:
            weapon = weapons.get(weaponString)
            if isinstance(weapon, robots.ManipulatorInterface):
                containsManipulator = True
                break
        if containsManipulator:
            step.addNote(note=MultiLink._MultiLinkManipulatorNote)
        
        context.applyStep(
            sequence=sequence,
            step=step)

    def _enumerateWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, typing.Union[robots.WeaponMountInterface, robots.ManipulatorInterface]]:
        weapons = {}

        mounts = _enumerateMounts(sequence=sequence, context=context)
        for mountString, mount in mounts.items():
            weapon = mount.weaponData(weaponSet=context.weaponSet())
            if weapon and weapon.multiLink():
                weapons[mountString] = mount

        weapons.update(_enumerateManipulators(sequence=sequence, context=context))
        return weapons
        


#  ███████████  ███                          █████████                       █████                       ████ 
# ░░███░░░░░░█ ░░░                          ███░░░░░███                     ░░███                       ░░███ 
#  ░███   █ ░  ████  ████████   ██████     ███     ░░░   ██████  ████████   ███████   ████████   ██████  ░███ 
#  ░███████   ░░███ ░░███░░███ ███░░███   ░███          ███░░███░░███░░███ ░░░███░   ░░███░░███ ███░░███ ░███ 
#  ░███░░░█    ░███  ░███ ░░░ ░███████    ░███         ░███ ░███ ░███ ░███   ░███     ░███ ░░░ ░███ ░███ ░███ 
#  ░███  ░     ░███  ░███     ░███░░░     ░░███     ███░███ ░███ ░███ ░███   ░███ ███ ░███     ░███ ░███ ░███ 
#  █████       █████ █████    ░░██████     ░░█████████ ░░██████  ████ █████  ░░█████  █████    ░░██████  █████
# ░░░░░       ░░░░░ ░░░░░      ░░░░░░       ░░░░░░░░░   ░░░░░░  ░░░░ ░░░░░    ░░░░░  ░░░░░      ░░░░░░  ░░░░░ 

# NOTE: The names generated by this function MUST remain consistent between
# versions otherwise it will break robots saved with previous versions. For
# this reason it shouldn't use things like the components instance string.
# TODO: Make sure I'm happy with what is being written before release
def _enumerateMultiLinks(
        sequence: str,
        context: robots.RobotContext
        ) -> typing.Mapping[str, robots.MultiLinkInterface]:
    results = {}

    multiLinks = context.findComponents(
        componentType=MultiLink,
        sequence=sequence)
    for index, multiLink in enumerate(multiLinks):
        assert(isinstance(multiLink, MultiLink))
        multiLinkString = f'Linked Group #{index + 1}'
        results[multiLinkString] = multiLink

    return results

class FireControl(robots.FireControlInterface):
    """
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
    class Level(enum.Enum):
        Basic = 'Basic'
        Improved = 'Improved'
        Enhanced = 'Enhanced'
        Advanced = 'Advanced'

     # Data Structure: Min TL, Cost, Weapon Skill DM
    _DataMap = {
        Level.Basic: (6, 10000, +1),
        Level.Improved: (8, 25000, +2),
        Level.Enhanced: (10, 50000, +3),
        Level.Advanced: (12, 100000, +4),
    }
    _MinTL = common.ScalarCalculation(
        value=6,
        name='Fire Control System Min TL')
    _RequiredSlots = common.ScalarCalculation(
        value=1,
        name='Fire Control System Required Slots')
    _ScopeNote = 'The Fire Control System gives the Scope trait (p60).'
    _WeaponSkillNote = 'When making an attack roll, you can choose to use the Fire Control System\'s Weapon Skill DM of {modifier} instead of the robots {skill} skill (p60 and clarified by Geir Lanesskog, Robot Handbook author)'
    _LaserDesignatorComponents = [
        robots.LaserDesignatorDefaultSuiteOption,
        robots.LaserDesignatorSlotOption]
    _LaserDesignatorNote = 'DM+2 to attacks against targets that have been illuminated with the Laser Designator (p37).'

    def __init__(self) -> None:
        super().__init__()

        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            options=[''],
            isEditable=False,
            isOptional=False,
            description='Select the weapon(s) to be controlled by the Fire Control System')
        
        self._levelOption = construction.EnumOption(
            id='Level',
            name='Level',
            type=FireControl.Level,
            description='Specify Fire Control System level.')
        
    def weaponString(self) -> str:
        return self._weaponOption.value()
        
    def instanceString(self) -> str:
        level = self._levelOption.value()
        if not level:
            return self.componentString()
        assert(isinstance(level, FireControl.Level))
        return f'{self.componentString()} ({level.value})'

    def componentString(self) -> str:
        return 'Fire Control System'
    
    def typeString(self) -> str:
        return 'Fire Control'    
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if context.techLevel() < FireControl._MinTL.value():
            return False

        if not context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence):
            return False
        
        weapons = self._enumerateWeapons(
            sequence=sequence,
            context=context)
        return len(weapons) > 0
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._weaponOption, self._levelOption]
        
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        weapons = self._enumerateWeapons(
            sequence=sequence,
            context=context)
        weaponStrings = list(weapons.keys())

        # Remove weapons that are controlled by other fire control systems
        others = context.findComponents(
            componentType=FireControl,
            sequence=sequence)
        for other in others:
            assert(isinstance(other, FireControl))
            if other != self:
                otherWeapon = other.weaponString()
                if otherWeapon in weaponStrings:
                    weaponStrings.remove(otherWeapon)

        # Remove weapons that are part of a multi-link (the multi-link should be
        # selected instead)
        for weapon in weapons.values():
            if not isinstance(weapon, robots.MultiLinkInterface):
                continue
            for linkedWeapon in weapon.weaponStrings():
                if linkedWeapon in weaponStrings:
                    weaponStrings.remove(linkedWeapon)
        
        self._weaponOption.setOptions(options=weaponStrings)
            
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        level = self._levelOption.value()
        assert(isinstance(level, FireControl.Level))

        _, fireControlCost, weaponSkillDM = FireControl._DataMap[level]
        
        fireControlCost = common.ScalarCalculation(
            value=fireControlCost,
            name=f'{level.value} Fire Control System Cost')
        step.setCredits(credits=construction.ConstantModifier(
            value=fireControlCost))
        
        step.setSlots(slots=construction.ConstantModifier(
            value=FireControl._RequiredSlots))
        
        weaponData = self._currentWeaponData(sequence=sequence, context=context)
        if weaponData:
            skill = weaponData.skill()
            specialty = weaponData.specialty()
            skillName = skill.name()
            if specialty:
                skillName += f' ({specialty.value})'
        else:
            skillName = 'relevant weapon'                
        step.addNote(note=FireControl._WeaponSkillNote.format(
            modifier=common.formatNumber(number=weaponSkillDM, alwaysIncludeSign=True),
            skill=skillName))

        step.addNote(note=FireControl._ScopeNote)

        hasLaserDesignator = False
        for componentType in FireControl._LaserDesignatorComponents:
            if context.hasComponent(
                componentType=componentType,
                sequence=sequence):
                hasLaserDesignator = True
                break
        if hasLaserDesignator:
            step.addNote(note=FireControl._LaserDesignatorNote)        
        
        context.applyStep(
            sequence=sequence,
            step=step)

    def _enumerateWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[
                str,
                typing.Union[
                    robots.WeaponMountInterface,
                    robots.ManipulatorInterface,
                    robots.MultiLinkInterface]]:
        weapons = {}
        weapons.update(_enumerateMounts(sequence=sequence, context=context))
        weapons.update(_enumerateManipulators(sequence=sequence, context=context))
        weapons.update(_enumerateMultiLinks(sequence=sequence, context=context))
        return weapons
    
    def _currentWeaponData(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[traveller.StockWeapon]:
        weapons = self._enumerateWeapons(sequence=sequence, context=context)
        weapon = weapons.get(self._weaponOption.value())
        if isinstance(weapon, robots.WeaponMountInterface):
            return weapon.weaponData(weaponSet=context.weaponSet())
        elif isinstance(weapon, robots.MultiLinkInterface):
            weaponStrings = weapon.weaponStrings()
            for weaponString in weaponStrings:
                linkedWeapon = weapons.get(weaponString)
                if isinstance(linkedWeapon, robots.WeaponMountInterface):
                    return linkedWeapon.weaponData(weaponSet=context.weaponSet())
        return None