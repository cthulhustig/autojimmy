import common
import construction
import math
import robots
import traveller
import typing

class FinalisationComponent(robots.RobotComponentInterface):
    # TODO: Need to handle removing unused slots. I don't like the idea of using
    # options on the finalisation component as it means I need to make the phase
    # visible in the config widget so you'll have a combo box with Finalisation
    # selected and no options to change it.
    #
    # Option 1: Use options but update the config widget so it doesn't show the
    # combo box but does show the options if the combo box only has a single
    # entry to select from.
    #
    # Option 2: Move unused slot removal into it's own phase and/or stage. The
    # last stage that uses slots is the brain so it needs to be processed after
    # that, it wouldn't make sense to do it between the brain and skills so
    # would make sense to be at the end (just before finalisation).
    # This would be a little ugly as it would just be sitting there on it's own.
    # One possibility would be add a stage after the slot options (it makes some
    # logical sense) and to have it set an attribute that finalisation checks for
    # and does the actual removal. This would also be a little ugly as the
    # removal would appear as a component but the slots/cost saving would appear
    # in finalisation.
    #
    # No mater what I do I think I need to make it a little more user friendly
    # than the spreadsheet. It needs to be very simple to turn on/off and when
    # you turn it on it should always default to removing all remaining slots

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

    _InoperableNote = 'When a robot\'s Hits reach 0, it is inoperable and considered wrecked, or at least cannot be easily repaired; at a cumulative damage of {doubleHits} the robot is irreparably destroyed. (p13)'
    _DefaultMaintenanceNote = 'The robot requires maintenance once a year and malfunction checks must be made every month if it\'s not followed (p108)'
    _AutopilotNote = 'The modifiers for the robot\'s Autopilot rating and its vehicle operating skills don\'t stack, the higher of the values should be used.'
    
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

        # These are intentionally left to last to hopefully make them more
        # obvious.
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
                # TODO: I've not added anything for this as can't find anything
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
                # See above for reason this is commented out
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
        
        # NOTE: The max slots can be a float as some components add/remove a
        # percentage of the slots (e.g. None locomotion adds 25%)
        note = f'WARNING: {usedSlots.value()} slots have been used but the max allowed is only {math.floor(maxSlots.value())}'
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
        note = f'WARNING: {usedBandwidth.value()} bandwidth has been used but the max allowed is only {math.floor(maxBandwidth.value())}'
        step = robots.RobotStep(
            name='Bandwidth',
            type='Usage',
            notes=[note])
        context.applyStep(
            sequence=sequence,
            step=step)
