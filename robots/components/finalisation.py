import common
import construction
import math
import robots
import traveller
import typing

# This is based on the min manipulator size for different mounts (p61)
def _manipulatorSizeToWeaponSize(manipulatorSize: int) -> typing.Optional[traveller.WeaponSize]:
    if manipulatorSize >= 7:
        return traveller.WeaponSize.Heavy
    if manipulatorSize >= 5:
        return traveller.WeaponSize.Medium
    if manipulatorSize >= 3:
        return traveller.WeaponSize.Small
    return None

class SlotRemoval(robots.SlotRemovalInterface):
    def typeString(self) -> str:
        return 'Slot Removal'
    
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return True    
    
    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        pass    

# NOTE: This component is hack to allow the stage to default to
# CustomSlotRemoval but still allow the user to select None as
# an option
class NoSlotRemoval(SlotRemoval):
    def __init__(self) -> None:
        super().__init__()

    def componentString(self) -> str:
        return 'None'

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        pass

class ActualSlotRemoval(SlotRemoval):
    """
    - Cost Saving: Cr100 per slot removed
    """    
    # NOTE: The fact this component doesn't check if there are any slots to
    # remove is important as we don't want the component to be removed if
    # the user temporarily adds a new component that takes the robot over
    # the slot limit. The problem with having it removed is the None option
    # will be selected (as it would be compatible) and then when the
    # temporary component is removed it it will remain as None as the
    # default component logic won't get applied (as there is a component)
    
    _PerSlotCostSaving = common.ScalarCalculation(
        value=-100,
        name='Slot Removal Per Slot Cost Saving')
    
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:   
        slots = self._slotCount()
        if not slots: # None indicates remove all slots
            slots = self._calculateUnusedSlots(
                sequence=sequence,
                context=context)
        if slots.value() <= 0:
            return # No slots to remove so no step to create
            
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())               

        # NOTE: This assumes that the saving is a negative value
        cost = common.Calculator.multiply(
            lhs=CustomSlotRemoval._PerSlotCostSaving,
            rhs=slots,
            name=f'{self.componentString()} Total Cost Saving')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        # NOTE: The slots count is negated as this is a reduction in the max slots
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxSlots,
            modifier=construction.ConstantModifier(
                value=common.Calculator.negate(
                    value=slots,
                    name=f'{self.componentString()} Max Slot Reduction'))))

        context.applyStep(
            sequence=sequence,
            step=step)    
    
    def _calculateUnusedSlots(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> common.ScalarCalculation:
        maxSlots = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxSlots,
            sequence=sequence)
        assert(isinstance(maxSlots, common.ScalarCalculation))
        usedSlots = context.usedSlots(sequence=sequence)

        # NOTE: Construction intentionally allows more than the max slots to be
        # allocated so the unused slots needs to be clamped to a min of 0
        return common.Calculator.max(
            lhs=common.Calculator.subtract(
                lhs=maxSlots,
                rhs=usedSlots),
            rhs=common.ScalarCalculation(value=0),
            name='Unused Slots')
    
    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        raise RuntimeError(f'{type(self)} is derived from ActualSlotRemoval so must implement _slotCount')    

class AllSlotRemoval(ActualSlotRemoval):
    def __init__(self) -> None:
        super().__init__()
        
    def componentString(self) -> str:
        return 'Remove All'
        
    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        return None # Remove all

class CustomSlotRemoval(ActualSlotRemoval):
    def __init__(self) -> None:
        super().__init__()

        self._slotCountOption = construction.IntegerOption(
            id='SlotCount',
            name='Slot Count',
            value=1,
            minValue=1,
            description='Specify the number of slots to remove')
        
    def instanceString(self) -> str:
        slots = self._slotCount()
        if slots:      
            return f'{self.componentString()} (x{slots.value()})'      
        return super().instanceString()
        
    def componentString(self) -> str:
        return 'Remove Custom'

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._slotCountOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        removableSlots = self._calculateUnusedSlots(
            sequence=sequence,
            context=context)
        hasSlotsToRemove = removableSlots.value() > 0
        if hasSlotsToRemove:
            self._slotCountOption.setMax(value=removableSlots.value())
        self._slotCountOption.setEnabled(hasSlotsToRemove)

    def _slotCount(self) -> typing.Optional[common.ScalarCalculation]:
        return common.ScalarCalculation(
            value=self._slotCountOption.value() if self._slotCountOption.isEnabled() else 0,
            name='Specified Custom Slot Count')
    
class FinalisationComponent(robots.FinalisationInterface):
    _AtmosphereFlyerLocomotions = [
        robots.AeroplanePrimaryLocomotion,
        robots.VTOLPrimaryLocomotion,
        robots.VTOLSecondaryLocomotion
    ]
    _GraveFlyerLocomotions = [
        robots.GravPrimaryLocomotion,
        robots.GravSecondaryLocomotion
    ]
    _ImprovedMaintenanceOptions = [
        robots.SelfMaintenanceEnhancementDefaultSuiteOption,
        robots.SelfMaintenanceEnhancementSlotOption
    ]
    _AutopilotVehicleSkills = [
        traveller.DriveSkillDefinition,
        traveller.FlyerSkillDefinition,
        robots.RobotVehicleSkillDefinition
    ]

    # These are the sensor components that require an Electronics skill
    _SkilledSensorSlotOptions = [
        robots.BioscannerSensorSlotOption,
        robots.DensitometerSensorSlotOption,
        robots.NeuralActivitySensorSlotOption,
        robots.PlanetologySensorSuiteSlotOption
    ]

    _InoperableNote = 'When a robot\'s Hits reach 0, it is inoperable and considered wrecked, or at least cannot be easily repaired; at a cumulative damage of {doubleHits} the robot is irreparably destroyed. (p13)'
    _DefaultMaintenanceNote = 'The robot requires maintenance once a year and malfunction checks must be made every month if it\'s not followed (p108)'
    
    _AutopilotNote = 'The modifiers for the robot\'s Autopilot rating and its vehicle operating skills don\'t stack, the higher of the values should be used.'

    _CombatManipulatorDexterityNote = 'Attacks rolls for weapons mounted on or held by a manipulator receive the DEX modifier for the manipulator in the same way as players receive a DEX characteristic modifier (clarified by Geir Lanesskog, Robot Handbook author)'
    _CombatNonManipulatorDexterityNote = 'Attack rolls for weapons _not_ mounted on or held by a manipulator do not receive a DEX modifier (clarified by Geir Lanesskog, Robot Handbook author)'
    _CombatManipulatorUndersizedNote = 'Manipulators of Size {sizes} are to small to use weapons effectively. Attacks rolls do not get the manipulators STR or DEX bonus (p61)'
    _CombatManipulatorWeaponSizeNote = 'Manipulators of Size {sizes} can use {examples}. If weapons larger than this are used, attack rolls do not get the manipulators STR or DEX bonus (p61)'
    _CombatWeaponSizeExamples = {
        traveller.WeaponSize.Small: 'melee weapon useable with one hand, any pistol or equivalent single-handed ranged weapon, or an explosive charge or grenade of less than three kilograms',
        traveller.WeaponSize.Medium: 'any larger weapon usable by Melee or Gun Combat skills or an explosive of up to six kilograms',
        traveller.WeaponSize.Heavy: 'any weapon usable with Heavy Weapons (portable)'
    }   
 
    _SkilledSensorNote = 'WARNING: The robot doesn\'t have the Electronics (sensors) 0 skill required to operate its {component}'

    def componentString(self) -> str:
        return 'Finalisation'

    def typeString(self) -> str:
        return 'Finalisation'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return True

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._createProtectionStep(sequence=sequence, context=context)
        self._createTraitNoteSteps(sequence=sequence, context=context)
        self._createInoperableStep(sequence=sequence, context=context)
        self._createMaintenanceStep(sequence=sequence, context=context)
        self._createAutopilotStep(sequence=sequence, context=context)
        self._createCombatStep(sequence=sequence, context=context)

        # These are intentionally left to last to hopefully make them more
        # obvious.
        self._skilledSensorsSteps(sequence=sequence, context=context)
        self._slotUsageStep(sequence=sequence, context=context)
        self._bandwidthUsageStep(sequence=sequence, context=context)

    def _createProtectionStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        protection = context.attributeValue(
            attributeId=robots.RobotAttributeId.Protection,
            sequence=sequence)
        if not protection:
            return # Nothing to do
        
        armour = common.Calculator.equals(
            value=protection,
            name='Armour Trait Value')
        
        step = robots.RobotStep(
            name=f'Protection ({protection.value()})',
            type='Trait')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Armour,
            value=armour))
        context.applyStep(
            sequence=sequence,
            step=step)

    def _createTraitNoteSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        for trait in robots.TraitAttributesIds:
            if trait in robots.InternalAttributeIds:
                continue
            if not context.hasAttribute(sequence=sequence, attributeId=trait):
                continue

            name = trait.value
            notes = []
            if trait == robots.RobotAttributeId.ACV:
                notes.append('The robot can travel over solid and liquid surfaces.')
                notes.append('The robot only hover up to a few meters over above the surface and requires at least at thin atmosphere to operate.')
            elif trait == robots.RobotAttributeId.Alarm:
                pass
            elif trait == robots.RobotAttributeId.Amphibious:
                # NOTE: I've not added anything for this as can't find anything
                # that adds it. If I do add something it's not straight forward
                # as the exact wording of the note should probably vary depending
                # on if the robot can operate while submerged or if it's just
                # on land and on top of water. I'm also not sure if it's just
                # water or liquid. The Submersible Environment Protection
                # description (p42) says Hostile Environment Protection can also
                # allow the robot to operate while submerged.
                pass
            elif trait == robots.RobotAttributeId.ATV:
                notes.append('DM+2 to checks made to negotiate rough terrain.')
            elif trait == robots.RobotAttributeId.Hardened:
                notes.append('The robot\'s brain is immune to ion weapons.')
                notes.append('Radiation damage inflicted on the robot is halved.')
            elif trait == robots.RobotAttributeId.HeightenedSenses:
                notes.append('DM+1 to Recon and Survival Checks.')
            elif trait == robots.RobotAttributeId.Invisible:
                notes.append('DM-4 to checks to see the robot. This applies across the electromagnetic spectrum.')
            elif trait == robots.RobotAttributeId.IrVision:
                notes.append('The robot can sense its environment in the visual and infrared spectrum, allowing it to see heat sources without visible light.')
            elif trait == robots.RobotAttributeId.IrUvVision:
                notes.append('The robot can sense its environment in a greatly extended electromagnetic range. It can see clearly without the need for visible light and, at the Referee\'s discretion, it may see electromagnetic emissions from equipment.')
            elif trait == robots.RobotAttributeId.Seafarer:
                pass
            elif trait == robots.RobotAttributeId.Large:
                # TODO: I've commented this out as I __think__ it might be the
                # same modifier that has a note added for the chassis rather
                # than being in addition to it. It's a little unclear as the
                # description for chassis (p13) makes it sound like it's for all
                # attacks but the description for the trait (p8) says it's just
                # ranged attacks
                # This would be a good one for Geir
                """
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                notes.append(f'Ranged attacks made against to robot receive DM+{value.value()}')
                """
            elif trait == robots.RobotAttributeId.Small:
                # TODO: See above for reason this is commented out
                """
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                notes.append(f'Ranged attacks made against to robot receive DM{value.value()}')
                """
            elif trait == robots.RobotAttributeId.Stealth:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                notes.append(f'DM+{value.value()} to checks made to evade electronic sensors such as radar or lidar.')
                notes.append(f'Electronic (sensors) checks to detect the robot suffer a negative DM equal to the difference between the robot\'s TL ({context.techLevel()} and the TL of the equipment.')
            elif trait == robots.RobotAttributeId.Thruster:
                value = context.attributeValue(
                    attributeId=trait,
                    sequence=sequence)
                notes.append(f'The robot\'s thrusters can provide {value.value()}G of thrust.')
            elif trait == robots.RobotAttributeId.Flyer:
                needsAtmosphere = False
                for locomotion in FinalisationComponent._AtmosphereFlyerLocomotions:
                    if context.hasComponent(
                        componentType=locomotion,
                        sequence=sequence):
                        needsAtmosphere = True
                        break
                if needsAtmosphere:
                    notes.append(f'Aeroplane or VTOL Flyer robots require at least a thin atmosphere to operate.')    
            
                needsGrav = False
                for locomotion in FinalisationComponent._GraveFlyerLocomotions:
                    if context.hasComponent(
                        componentType=locomotion,
                        sequence=sequence):
                        needsGrav = True
                        break
                if needsGrav:
                    notes.append(f'Grav Flyer robots require at a gravitational field to operate.')    

            if notes:
                step = robots.RobotStep(
                    name=name,
                    type='Trait',
                    notes=notes)
                context.applyStep(
                    sequence=sequence,
                    step=step)

    def _createInoperableStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        hits = context.attributeValue(
            attributeId=robots.RobotAttributeId.Hits,
            sequence=sequence)
        if not hits:
            return # Nothing to do
        assert(isinstance(hits, common.ScalarCalculation))

        step = robots.RobotStep(
            name='Damage',
            type='Resilience')
        step.addNote(note=FinalisationComponent._InoperableNote.format(
            doubleHits=hits.value() * 2))
        context.applyStep(
            sequence=sequence,
            step=step)                      

    def _createMaintenanceStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        for component in FinalisationComponent._ImprovedMaintenanceOptions:
            if context.hasComponent(
                componentType=component,
                sequence=sequence):
                # Nothing to do, the note only applies if the robot doesn't have
                # improved maintenance
                return

        step = robots.RobotStep(
            name='Maintenance',
            type='Resilience',
            notes=[FinalisationComponent._DefaultMaintenanceNote])
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _createAutopilotStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        autopilot = context.hasAttribute(
            attributeId=robots.RobotAttributeId.Autopilot,
            sequence=sequence)
        if not autopilot:
            return
        
        hasVehicleSkill = False
        for skill in FinalisationComponent._AutopilotVehicleSkills:
            if context.hasSkill(skillDef=skill, sequence=sequence):
                hasVehicleSkill = True
                break

        if not hasVehicleSkill:
            return
            
        step = robots.RobotStep(
            name='Autopilot',
            type='Skills',
            notes=[FinalisationComponent._AutopilotNote])
        context.applyStep(
            sequence=sequence,
            step=step)

    def _createCombatStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        manipulators = context.findComponents(
            componentType=robots.ManipulatorInterface,
            sequence=sequence)
        usableManipulatorSizes: typing.List[int] = []
        for manipulator in manipulators:
            assert(isinstance(manipulator, robots.ManipulatorInterface))
            if isinstance(manipulator, robots.RemoveBaseManipulator):
                continue
            hasManipulator = True

            size = manipulator.size()
            if not _manipulatorSizeToWeaponSize(manipulatorSize=size):
                # Ignore manipulators that are to small to hold a weapon
                continue

            if size not in usableManipulatorSizes:
                usableManipulatorSizes.append(size)
        usableManipulatorSizes.sort()

        weaponMounts = context.findComponents(
            componentType=robots.Weapon,
            sequence=sequence)
        hasNonManipulatorWeapon = False
        for mount in weaponMounts:
            assert(isinstance(mount, robots.Weapon))
            isManipulatorBased = isinstance(mount, robots.ManipulatorMountedWeapon) or \
                isinstance(mount, robots.HandHeldWeapon)
            if not isManipulatorBased:
                hasNonManipulatorWeapon = True

        # Cover how DEX is used in attack rolls
        if hasManipulator or hasNonManipulatorWeapon:
            step = robots.RobotStep(
                name='Dexterity',
                type='Combat')
            if hasManipulator:
                step.addNote(note=FinalisationComponent._CombatManipulatorDexterityNote)
            if hasNonManipulatorWeapon:
                step.addNote(note=FinalisationComponent._CombatNonManipulatorDexterityNote)
            context.applyStep(
                sequence=sequence,
                step=step)
            
        # Cover what happens if a manipulator holds a weapon that would require
        # a larger mount that the manipulator can handle
        if hasManipulator:
            step = robots.RobotStep(
                name='Weapon Size',
                type='Combat')            
            sizingMap: typing.Dict[traveller.WeaponSize, typing.Iterable[str]] = {}
            for manipulatorSize in usableManipulatorSizes:
                weaponSize = _manipulatorSizeToWeaponSize(manipulatorSize=size)
                manipulatorSizes = sizingMap.get(weaponSize)
                if not manipulatorSizes:
                    manipulatorSizes = []
                    sizingMap[weaponSize] = manipulatorSizes
                manipulatorSizes.append(str(manipulatorSize))
            for weaponSize, manipulatorSizes in sizingMap.items():
                if weaponSize:
                    step.addNote(note=FinalisationComponent._CombatManipulatorWeaponSizeNote.format(
                        sizes=common.humanFriendlyListString(manipulatorSizes),
                        examples=FinalisationComponent._CombatWeaponSizeExamples[weaponSize]))
                else:
                    step.addNote(note=FinalisationComponent._CombatManipulatorUndersizedNote.format(
                        sizes=common.humanFriendlyListString(manipulatorSizes)))
            context.applyStep(
                sequence=sequence,
                step=step)                

    def _skilledSensorsSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        # NOTE: The rules say that Electronics (sensors) 0 is required to use these
        # sensors. This is just base Electronics so no need to check speciality
        if context.hasSkill(
            skillDef=traveller.ElectronicsSkillDefinition,
            sequence=sequence):
            return

        for componentType in FinalisationComponent._SkilledSensorSlotOptions:
            component = context.findFirstComponent(
                componentType=componentType,
                sequence=sequence)
            if not component:
                continue

            note = FinalisationComponent._SkilledSensorNote.format(
                component=component.componentString())
            step = robots.RobotStep(
                name=f'{component.componentString()}',
                type='Skills',
                notes=[note])
            context.applyStep(
                sequence=sequence,
                step=step)
        
    def _slotUsageStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxSlots = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxSlots,
            sequence=sequence)
        assert(isinstance(maxSlots, common.ScalarCalculation))
        usedSlots = context.usedSlots(sequence=sequence)
        if usedSlots.value() <= maxSlots.value():
            # Nothing to do, the note only applies the used slots greater
            # than the max slots
            return
        
        note = f'WARNING: {usedSlots.value()} slots have been used but the max allowed is {maxSlots.value()}'
        step = robots.RobotStep(
            name='Slots',
            type='Usage',
            notes=[note])
        context.applyStep(
            sequence=sequence,
            step=step)
        
    def _bandwidthUsageStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        maxBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            sequence=sequence)
        assert(isinstance(maxBandwidth, common.ScalarCalculation))
        usedBandwidth = context.usedBandwidth(sequence=sequence)
        if usedBandwidth.value() <= maxBandwidth.value():
            # Nothing to do, the note only applies the used slots greater
            # than the max slots
            return
        
        # NOTE: The max slots can be a float as some components add/remove a
        # percentage of the slots (e.g. None locomotion adds 25%)        
        note = f'WARNING: {usedBandwidth.value()} bandwidth has been used but the max allowed is {math.floor(maxBandwidth.value())}'
        step = robots.RobotStep(
            name='Bandwidth',
            type='Usage',
            notes=[note])
        context.applyStep(
            sequence=sequence,
            step=step)
