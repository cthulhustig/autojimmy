import common
import construction
import enum
import robots
import traveller
import typing
import uuid

# TODO: Androids
# - <ALL>
#   - Slots: 50% of Base Slots
#   - Requirement: The min brain is only the min to successfully emulate the desired species, if a lower brain is used the robot receives an additional DM-2 to social skills
# - Basic
#   - Min TL: 8
#   - Cost: Cr1000 Per Slot
#   - Minimum Brain: Basic (X) or Hunter/Killer
#   - Note: Barely emulating. DM-2 on all social interactions from uncanny valley effect.
# - Improved
#   - Min TL: 10
#   - Cost: Cr2000 Per Slot
#   - Minimum Brain: Advanced
#   - Note: Natural-looking. Passes at a distance but uncanny valley DM-2 within 5 metres.
# - Enhanced
#   - Min TL: 12
#   - Cost: Cr5000 Per Slot
#   - Minimum Brain: Very Advanced
#   - Note: Natural-looking; Invisitech. Passes in close interaction, but on a roll of a natural 2 the uncanny valley sets in.
# - Advanced
#   - Min TL: 14
#   - Cost: Cr10000 Per Slot
#   - Minimum Brain: Very Advanced
#   - Note: Natural-looking; Invisitech; Self-repairing. Can pass as a biological being unless scanned.
#   - Requirement: The self-repairing property provides the same effect as the self-repairing chassis option and ‘heals wounds’ at a rate similar to natural healing.
# - Superior 
#   - Min TL: 16
#   - Cost: Cr1000 Per Slot
#   - Minimum Brain: Self-Aware
#   - Note: Natural-looking; Invisitech; Self-repairing. Can pass even after most scans.
#   - Requirement: The self-repairing property provides the same effect as the self-repairing chassis option and ‘heals wounds’ at a rate similar to natural healing.
#
# - I think this might make sense as a chassis option
#   - This is how the spreadsheet does it
# - No default armour, can only add up to 2 slots of armour
# - The size of an android is limited to the size of the species it's trying to mimic
#   - I think this effectively means I don't have any restriction as I'm not having the species specified
# - The locomotion of an android is limited to the locomotion of the species it's trying to mimic
#   - Not sure what to do about this one. Some probably don't make sense (e.g. Wheels)
# - In addition to the per slot cost of the android modification there is also a x3 cost multiplier for every part of the robot apart from skills
#   - This multiplier is also applied o the per slot cost of the modification, I assume this is just to make the math easier
#   - This could be complex
#       - Adding the multiplier to every component seems like a pain in the ass
#       - Could add a finalisation step (in addition to the android modification component) that gets the multi-phase cost for everything apart from the skills phase
#
# TODO: Biological Robot
# - <ALL>
#   - Slots: 75% of Base Slots
#   - Requirement: All biological robots have 'Natural-looking' and 'Selfrepairing' properties
#   - Requirement: The min brain is only the min to successfully emulate the desired species, if a lower brain is used the robot receives an additional DM-2 to social skills
#   - Requirement: Locomotion is limited to natural forms of locomotion
#   - Requirement: Standard Endurance doesn't apply to Biological Robots, they have to eat, drink & breath
#   - Requirement: A Biological Robot can use any of the body augments from the Central Supply Catalogue or Robot Handbook
# - Basic
#   - Min TL: 11
#   - Cost: Cr2000
#   - Minimum Brain: Basic (x) or Hunter/Killer
#   - Note: DM-2 on all healing checks. Emissions from the electronic brain or interfaces are detectable by attuned scanners and by any psionic life detection.
# - Improved
#   - Min TL: 13
#   - Cost: Cr5000
#   - Minimum Brain: Advanced
#   - Note: Treat detection of an artificial brain as DM-2 on any scanner check, including psionic life detection.
# - Enhanced
#   - Min TL: 15
#   - Cost: Cr10000
#   - Minimum Brain: Very Advanced
#   - Note: DM+2 on all healing checks. DM-4 on any scanner check, including psionic life detection.
# - Advanced
#   - Min TL: 17
#   - Cost: Cr20000
#   - Minimum Brain: Self-Aware
#   - Note: DM+4 on all healing checks. Undisguisable from a fully biological being, even psionically
#
# - The stuff about 'Selfrepairing' property means the robot heals in the same way as some of the higher TL androids
# - I'm not sure what to do about biological robots being able to use body modifications
#   - It feels like a load of components that are specific to biological robots
#   - I think the robot handbook mods it's talking about might be the cybernetics stuff
#   - What does the spreadsheet do?
# - When it comes to what locomotions are available it's probably just the same list as the spreadsheet
#   - None, Aeroplane, Aquatic, VTOL, Walker, Lighter Than Air
# - Not sure what to do about the Endurance requirement
#   - Could wrap all calls to set/modify the Endurance
#       - This would avoid having meaningless Endurance factors being shown in the manifest
#       - Would need to make sure things that use the Endurance trait handle it not being there
#       - The Vehicle Endurance attribute should probably be handled in the same way
#           - Can you have Vehicle Speed Movement on a biological????
#       - I suspect this means biological robots can't have endurance modifications





class _RobotSequenceState(construction.SequenceState):
    def __init__(
            self,
            stages: typing.Optional[typing.Iterable[construction.ConstructionStage]]
            ) -> None:
        super().__init__(
            phasesType=robots.RobotPhase,
            componentsType=robots.RobotComponentInterface,
            isPrimary=True, # Robots only have one sequence
            stages=stages)

class RobotContext(construction.ConstructionContext):
    def __init__(
            self,
            techLevel: int
            ) -> None:
        super().__init__(
            phasesType=robots.RobotPhase,
            componentsType=robots.RobotComponentInterface,
            techLevel=techLevel)
        
    def baseSlots(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        slots = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.BaseSlots)
        if not isinstance(slots, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Base Slots')
        return slots
        
    def baseChassisCredits(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        return self.phaseCost(
            sequence=sequence,
            phase=robots.RobotPhase.BaseChassis,
            costId=robots.RobotCost.Credits)     
    
    def usedSlots(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        slotsUsed = self.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Slots)
        return common.Calculator.equals(
            value=slotsUsed,
            name='Total Slots Used')

    def usedBandwidth(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        slotsUsed = self.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Bandwidth)
        return common.Calculator.equals(
            value=slotsUsed,
            name='Total Bandwidth Used')

    def multiPhaseCost(
            self,
            sequence: str,
            costId: robots.RobotCost,
            phases: typing.Optional[typing.Iterable[robots.RobotPhase]] = None,
            ) -> None:
        if not phases:
            phases = robots.RobotPhase

        phaseCosts = []
        for phase in phases:
            phaseCost = self.phaseCost(
                sequence=sequence,
                phase=phase,
                costId=costId)
            phaseCosts.append(phaseCost)

        return common.Calculator.sum(
            values=phaseCosts,
            name=f'Total')
    
class Robot(object):
    def __init__(
            self,
            robotName: str,
            techLevel: int,
            userNotes: typing.Optional[str] = None
            ) -> None:
        self._robotName = robotName
        self._userNotes = userNotes if userNotes else ''

        # NOTE: It's important that the context is created at construction and
        # never recreated for the lifetime of the weapon as things like the UI
        # may hold onto references to it.
        # NOTE: It's also important that this class doesn't cache any state as
        # the context may be modified without it knowing.
        self._constructionContext = RobotContext(techLevel=techLevel)

        self._sequence = str(uuid.uuid4())
        sequenceState = _RobotSequenceState(
            stages=self._createStages())
        self._constructionContext.addSequence(
            sequence=self._sequence,
            sequenceState=sequenceState,
            regenerate=True)

    def robotName(self) -> typing.Optional[str]:
        return self._robotName

    def techLevel(self) -> int:
        return self._constructionContext.techLevel()

    def setTechLevel(
            self,
            techLevel: int,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setTechLevel(
            techLevel=techLevel,
            regenerate=regenerate)

    def context(self) -> RobotContext:
        return self._constructionContext

    def userNotes(self) -> str:
        return self._userNotes

    def setUserNotes(self, notes: str) -> None:
        self._userNotes = notes

    def stages(
            self,
            phase: typing.Optional[robots.RobotPhase] = None,
            componentType: typing.Optional[typing.Type[robots.RobotComponentInterface]] = None
            ) -> typing.Iterable[construction.ConstructionStage]:
        return self._constructionContext.stages(
            sequence=self._sequence,
            phase=phase,
            componentType=componentType)

    def findComponents(
            self,
            componentType: typing.Type[robots.RobotComponentInterface]
            ) -> typing.Iterable[robots.RobotComponentInterface]:
        return self._constructionContext.findComponents(
            componentType=componentType,
            sequence=self._sequence)

    def hasComponent(
            self,
            componentType: typing.Type[robots.RobotComponentInterface]
            ) -> bool:
        return self._constructionContext.hasComponent(
            componentType=componentType,
            sequence=self._sequence)

    # The replaceComponent parameter can be used to get the list of components that would be
    # compatible if the specified component was being replaced. If the replaceComponent is
    # compatible with the weapon (which generally it always should be) then it will be included
    # in the returned list of components
    def findCompatibleComponents(
            self,
            stage: construction.ConstructionStage,
            replaceComponent: typing.Optional[robots.RobotComponentInterface] = None
            ) -> typing.Iterable[robots.RobotComponentInterface]:
        return self._constructionContext.findCompatibleComponents(
            stage=stage,
            replaceComponent=replaceComponent)

    def addComponent(
            self,
            stage: construction.ConstructionStage,
            component: robots.RobotComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.addComponent(
            stage=stage,
            component=component,
            regenerate=regenerate)

    def removeComponent(
            self,
            stage: construction.ConstructionStage,
            component: robots.RobotComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.removeComponent(
            stage=stage,
            component=component,
            regenerate=regenerate)

    def replaceComponent(
            self,
            stage: construction.ConstructionStage,
            oldComponent: typing.Optional[robots.RobotComponentInterface],
            newComponent: typing.Optional[robots.RobotComponentInterface],
            regenerate: bool = True
            ) -> None:
        self._constructionContext.replaceComponent(
            stage=stage,
            oldComponent=oldComponent,
            newComponent=newComponent,
            regenerate=regenerate)

    def clearComponents(
            self,
            phase: typing.Optional[robots.RobotPhase] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        return self._constructionContext.clearComponents(
            phase=phase,
            sequence=self._sequence,
            regenerate=regenerate)

    def regenerate(
            self,
            stopStage: typing.Optional[construction.ConstructionStage] = None
            ) -> None:
        self._constructionContext.regenerate(
            stopStage=stopStage)

    def hasAttribute(
            self,
            attributeId: robots.RobotAttributeId
            ) -> bool:
        return self._constructionContext.hasAttribute(
            sequence=self._sequence,
            attributeId=attributeId)

    def attribute(
            self,
            attributeId: robots.RobotAttributeId,
            ) -> typing.Optional[construction.AttributeInterface]:
        return self._constructionContext.attribute(
            sequence=self._sequence,
            attributeId=attributeId)

    def attributeValue(
            self,
            attributeId: robots.RobotAttributeId,
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        return self._constructionContext.attributeValue(
            sequence=self._sequence,
            attributeId=attributeId)
    
    # NOTE: A skill is only classed as having a speciality if it has the
    # speciality at level 1 or higher    
    def hasSkill(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> bool:
        return self._constructionContext.hasSkill(
            sequence=self._sequence,
            skillDef=skillDef,
            speciality=speciality)
    
    def skill(
            self,
            skillDef: traveller.SkillDefinition
            ) -> typing.Optional[construction.TrainedSkill]:
        return self._constructionContext.skill(
            sequence=self._sequence,
            skillDef=skillDef)  
    
    def skillLevel(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> bool:
        return self._constructionContext.skillLevel(
            sequence=self._sequence,
            skillDef=skillDef,
            speciality=speciality)  
    
    def steps(
            self,
            component: typing.Optional[robots.RobotComponentInterface] = None,
            phase: typing.Optional[robots.RobotPhase] = None,
            ) -> typing.Collection[robots.RobotStep]:
        return self._constructionContext.steps(
            sequence=self._sequence,
            component=component,
            phase=phase)

    def phaseCost(
            self,
            phase: robots.RobotPhase,
            costId: robots.RobotCost
            ) -> common.ScalarCalculation:
        return self._constructionContext.phaseCost(
            sequence=self._sequence,
            phase=phase,
            costId=costId)

    def manifest(self) -> construction.Manifest:
        sequenceStates = self._constructionContext.state(
            sequence=self._sequence)
        manifest = construction.Manifest(costsType=robots.RobotCost)

        for phase in robots.RobotPhase:
            sectionName = phase.value

            manifestSection = None
            for component in sequenceStates.components(phase=phase):
                steps = sequenceStates.steps(component=component)
                if not steps:
                    continue

                if not manifestSection:
                    manifestSection = manifest.createSection(name=sectionName)
                for step in steps:
                    entryText = f'{step.type()}: {step.name()}'

                    factors = []
                    for factor in step.factors():
                        if isinstance(factor, construction.AttributeFactor) and \
                            factor.attributeId() in robots.InternalAttributeIds:
                            # Don't include attribute factors that modify internal
                            # attributes
                            continue
                        factors.append(factor)

                    manifestSection.createEntry(
                        component=entryText,
                        costs=step.costs(),
                        factors=factors)

        return manifest

    def _createStages(
            self
            ) -> typing.List[construction.ConstructionStage]:
        stages = []

        stages.append(construction.ConstructionStage(
            name='Chassis',
            sequence=self._sequence,
            phase=robots.RobotPhase.BaseChassis,
            baseType=robots.ChassisInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Primary Locomotion',
            sequence=self._sequence,
            phase=robots.RobotPhase.BaseChassis,
            baseType=robots.PrimaryLocomotionInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Armour Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.ArmourModificationInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1))

        stages.append(construction.ConstructionStage(
            name='Endurance Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.EnduranceModificationInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1))     

        stages.append(construction.ConstructionStage(
            name='Resiliency Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.ResiliencyModificationInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1))  

        stages.append(construction.ConstructionStage(
            name='Agility Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.LocomotiveMods,
            baseType=robots.AgilityEnhancementInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1))
        
        # NOTE: It's important that this stage is mandatory in order to force
        # robots with the Aeroplane locomotion type to have the Vehicle Movement
        # Speed component
        stages.append(construction.ConstructionStage(
            name='Speed Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.LocomotiveMods,
            baseType=robots.SpeedModificationInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))        
        
        # NOTE: I've not seen anything anything in the rules that explicitly
        # says you can only have one secondary locomotion, although it could be
        # the expectation is it's implied by the name. As it doesn't explicitly
        # say, i've chosen to allow it.
        stages.append(construction.ConstructionStage(
            name='Secondary Locomotion',
            sequence=self._sequence,
            phase=robots.RobotPhase.LocomotiveMods,
            baseType=robots.SecondaryLocomotionInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None)) 
        
        stages.append(construction.ConstructionStage(
            name='Base Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.BaseManipulatorInterface,
            # Mandatory fixed size
            minComponents=2,
            maxComponents=2))
        
        stages.append(construction.ConstructionStage(
            name='Additional Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.AdditionalManipulatorInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Leg Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.LegManipulatorInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None)) 

        stages.append(construction.ConstructionStage(
            name='Default Suite',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.DefaultSuiteOptionInterface,
            # Mandatory fixed size
            minComponents=5,
            maxComponents=5))
        
        stages.append(construction.ConstructionStage(
            name='Slot Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.SlotOptionInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Weapons',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.WeaponInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))

        stages.append(construction.ConstructionStage(
            name='Brain',
            sequence=self._sequence,
            phase=robots.RobotPhase.Brain,
            baseType=robots.BrainInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Skill Package',
            sequence=self._sequence,
            phase=robots.RobotPhase.Brain,
            baseType=robots.SkillPackageInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1,
            # Force a component to be selected if there is one
            forceComponent=True))          

        stages.append(construction.ConstructionStage(
            name='Skills',
            sequence=self._sequence,
            phase=robots.RobotPhase.Brain,
            baseType=robots.SkillInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        # NOTE: This stage is a little unusual as it uses a dummy None component
        # rather than being truly optional. This is needed to allow it to default
        # to the AllSlotRemoval component but still allow the user to specify
        # None to not have any slots removed
        stages.append(construction.ConstructionStage(
            name='Slot Removal',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.SlotRemovalInterface,
            defaultType=robots.AllSlotRemoval,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))

        # NOTE: This is the final stage of construction it MUST be last,
        # including after other stages in the finalisation phase
        stages.append(construction.ConstructionStage(
            name='Finalisation',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.FinalisationInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))     
        
        return stages
