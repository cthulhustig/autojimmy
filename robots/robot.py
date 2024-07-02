import common
import construction
import enum
import math
import robots
import traveller
import typing
import uuid

# NOTE: This maps skills to the characteristic that gives the DM
# modifier. The values come from the table on p74
_SkillCharacteristicMap = {
    traveller.AdminSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AdvocateSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AnimalsSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ArtSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AstrogationSkillDefinition: traveller.Characteristics.Intellect,
    traveller.AthleticsSkillDefinition: {
        traveller.AthleticsSkillSpecialities.Dexterity: traveller.Characteristics.Dexterity,
        traveller.AthleticsSkillSpecialities.Endurance: None, # No characteristic modifier for Endurance
        traveller.AthleticsSkillSpecialities.Strength: traveller.Characteristics.Strength,
    },
    traveller.BrokerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.CarouseSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DeceptionSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DiplomatSkillDefinition: traveller.Characteristics.Intellect,
    traveller.DriveSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.ElectronicsSkillDefinition: traveller.Characteristics.Intellect,
    traveller.EngineerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ExplosivesSkillDefinition: traveller.Characteristics.Intellect,
    traveller.FlyerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.GamblerSkillDefinition: traveller.Characteristics.Intellect,
    traveller.GunCombatSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.GunnerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.HeavyWeaponsSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.InvestigateSkillDefinition: traveller.Characteristics.Intellect,
    traveller.JackOfAllTradesSkillDefinition: traveller.Characteristics.Intellect,
    traveller.LanguageSkillDefinition: traveller.Characteristics.Intellect,
    traveller.LeadershipSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MechanicSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MedicSkillDefinition: traveller.Characteristics.Intellect,
    traveller.MeleeSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.NavigationSkillDefinition: traveller.Characteristics.Intellect,
    traveller.PersuadeSkillDefinition: traveller.Characteristics.Intellect,
    traveller.PilotSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.ProfessionSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ReconSkillDefinition: traveller.Characteristics.Intellect,
    traveller.ScienceSkillDefinition: traveller.Characteristics.Intellect,
    traveller.SeafarerSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.StealthSkillDefinition: traveller.Characteristics.Dexterity,
    traveller.StewardSkillDefinition: traveller.Characteristics.Intellect,
    traveller.StreetwiseSkillDefinition: traveller.Characteristics.Intellect,
    traveller.SurvivalSkillDefinition: traveller.Characteristics.Intellect,
    traveller.TacticsSkillDefinition: traveller.Characteristics.Intellect,
    # Vacc Suit isn't included in the list of skills on p74. The fact it
    # uses Intellect is based on the fact the example use of the skill in
    # the core rules use EDU which is INT for a robot
    traveller.VaccSuitSkillDefinition: traveller.Characteristics.Intellect,
    # Jack of all trades is needed for Brain in a Jar
    traveller.JackOfAllTradesSkillDefinition: None,
    # Non-standard skills added for robot construction
    robots.RobotVehicleSkillDefinition: traveller.Characteristics.Dexterity,
    robots.RobotWeaponSkillDefinition: traveller.Characteristics.Dexterity,
}

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
            techLevel: int,
            weaponSet: traveller.StockWeaponSet
            ) -> None:
        super().__init__(
            phasesType=robots.RobotPhase,
            componentsType=robots.RobotComponentInterface,
            techLevel=techLevel)
        self._weaponSet = weaponSet
        
    def weaponSet(self) -> traveller.StockWeaponSet:
        return self._weaponSet

    def setWeaponSet(
            self,
            weaponSet: traveller.StockWeaponSet,
            regenerate: bool = True
            ) -> None:
        self._weaponSet = weaponSet
        if regenerate:
            self.regenerate()        
        
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

    def totalCredits(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        slotsUsed = self.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Credits)
        return common.Calculator.equals(
            value=slotsUsed,
            name='Total Cost')         
    
    def maxSlots(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        maxSlots = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.MaxSlots)
        if not isinstance(maxSlots, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Max Slots')
        return common.Calculator.equals(
            value=maxSlots,
            name='Max Slots')  

    def usedSlots(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        slotsUsed = self.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Slots)
        return common.Calculator.equals(
            value=slotsUsed,
            name='Used Slots')
    
    def spareSlots(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        return common.Calculator.subtract(
            lhs=self.maxSlots(sequence=sequence),
            rhs=self.usedSlots(sequence=sequence),
            name='Spare Slots')      

    def maxBandwidth(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        maxBandwidth = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.MaxBandwidth)
        if not isinstance(maxBandwidth, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Max Bandwidth')
        return common.Calculator.equals(
            value=maxBandwidth,
            name='Max Bandwidth') 
    
    def usedBandwidth(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        bandwidthUsed = self.multiPhaseCost(
            sequence=sequence,
            costId=robots.RobotCost.Bandwidth)
        return common.Calculator.equals(
            value=bandwidthUsed,
            name='Used Bandwidth')      

    def spareBandwidth(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        return common.Calculator.subtract(
            lhs=self.maxBandwidth(sequence=sequence),
            rhs=self.usedBandwidth(sequence=sequence),
            name='Spare Bandwidth') 
    
    def multiPhaseCost(
            self,
            sequence: str,
            costId: robots.RobotCost,
            phases: typing.Optional[typing.Iterable[robots.RobotPhase]] = None,
            ) -> common.ScalarCalculation:
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
            name=f'Total {costId.value} Cost')
    
class Robot(construction.ConstructableInterface):
    def __init__(
            self,
            name: str,
            techLevel: int,
            weaponSet: traveller.StockWeaponSet,
            userNotes: typing.Optional[str] = None
            ) -> None:
        self._name = name
        self._userNotes = userNotes if userNotes else ''

        # NOTE: It's important that the context is created at construction and
        # never recreated for the lifetime of the weapon as things like the UI
        # may hold onto references to it.
        # NOTE: It's also important that this class doesn't cache any state as
        # the context may be modified without it knowing.
        self._constructionContext = RobotContext(
            techLevel=techLevel,
            weaponSet=weaponSet)

        # Robots only have a single sequence
        self._sequence = str(uuid.uuid4())
        sequenceState = _RobotSequenceState(
            stages=self._createStages())
        self._constructionContext.addSequence(
            sequence=self._sequence,
            sequenceState=sequenceState,
            regenerate=True)
        
    def name(self) -> str:
        return self._name
    
    def setName(self, name: str) -> None:
        self._name = name    

    def robotName(self) -> typing.Optional[str]:
        return self._name
    
    def setRobotName(
            self,
            name: typing.Optional[str]
            ) -> None:
        self._name = name

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
        
    def weaponSet(self) -> traveller.StockWeaponSet:
        return self._constructionContext.weaponSet()
        
    def setWeaponSet(
            self,
            weaponSet: traveller.StockWeaponSet,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setWeaponSet(
            weaponSet=weaponSet,
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
    
    def findFirstComponent(
            self,
            componentType: typing.Type[robots.RobotComponentInterface]
            ) -> typing.Optional[robots.RobotComponentInterface]:
        return self._constructionContext.findFirstComponent(
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
    
    def loadComponents(
            self,
            components: typing.Iterable[typing.Tuple[ # List of components
                str, # Component type
                typing.Optional[typing.Mapping[ # Options for this component
                    str, # Option ID
                    typing.Any # Option value
                    ]]
                ]]
            ) -> None:
        self._constructionContext.loadComponents(
            commonComponents=components)     

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
    
    def skills(self) -> typing.Iterable[construction.Skill]:
        return self._constructionContext.skills(
            sequence=self._sequence)    
    
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
            ) -> typing.Optional[construction.Skill]:
        return self._constructionContext.skill(
            sequence=self._sequence,
            skillDef=skillDef)
    
    def skillLevel(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
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
    
    def totalCredits(self) -> common.ScalarCalculation:
        return self._constructionContext.totalCredits(
            sequence=self._sequence)
    
    def maxSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.maxSlots(
            sequence=self._sequence)     
    
    def usedSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.usedSlots(
            sequence=self._sequence)
    
    def spareSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.spareSlots(
            sequence=self._sequence)
    
    def maxBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.maxBandwidth(
            sequence=self._sequence)     
    
    def usedBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.usedBandwidth(
            sequence=self._sequence)
    
    def spareBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.spareBandwidth(
            sequence=self._sequence)
    
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
                    costs = step.costs()

                    factors = []
                    for factor in step.factors():
                        if isinstance(factor, construction.AttributeFactor) and \
                            factor.attributeId() in robots.InternalAttributeIds:
                            # Don't include attribute factors that modify internal
                            # attributes
                            continue
                        factors.append(factor)

                    if phase == robots.RobotPhase.Finalisation and not costs and not factors:
                        # Don't include finalisation steps that have no costs
                        # or factors as they clutter up the manifest. This
                        # doesn't apply to steps from other stages as they
                        # (generally) related to something the user has
                        # specifically selected so should always be included
                        continue

                    manifestSection.createEntry(
                        component=entryText,
                        costs=costs,
                        factors=factors)

        return manifest
    
    # NOTE: The Finalisation section (p76) says, as well as characteristics DMs,
    # any additional modifiers should be included in the skill levels listed in
    # a robots worksheet. It would only make sense for this to be done for
    # modifiers that are applied in all situations (rather than situation specific
    # ones), but I'm not sure which modifiers this would be.
    # One case I know where the skill levels don't match this in the book is the
    # levels of Athletics (Dexterity/Strength) skill that a robot can get from its
    # manipulators. The Robots Handbook lists these in the skills section (e.g the
    # StarTek example robot) whereas I'm listing them as notes as the modifier
    # varies for robots with multiple manipulators.
    def worksheet(
            self,
            applySkillModifiers: bool
            ) -> robots.Worksheet:
        worksheet = robots.Worksheet()

        for field in robots.Worksheet.Field:
            fieldText = ''
            calculations = []
            if field == robots.Worksheet.Field.Robot:
                fieldText = self.name()
            elif field == robots.Worksheet.Field.Hits:
                attributeValue = self.attributeValue(
                    attributeId=robots.RobotAttributeId.Hits)
                if isinstance(attributeValue, common.ScalarCalculation):
                    fieldText = common.formatNumber(number=attributeValue.value())
                    calculations.append(attributeValue)
                else:
                    fieldText = '-'
            elif field == robots.Worksheet.Field.Locomotion:
                # TODO: Ideally this wouldn't include anything for the primary
                # locomotion if it's NoPrimaryLocomotion and there are any
                # secondary locomotions as it looks weird. The problem with
                # doing it though is the Endurance field currently will
                # display the endurance for the primary locomotion but not
                # the secondary, but if I make the change here it will be
                # easy to think the displayed endurance is for when using
                # the secondary locomotion
                locomotions = self.findComponents(
                    componentType=robots.Locomotion)
                locomotionStrings = []
                for locomotion in locomotions:
                    assert(isinstance(locomotion, robots.Locomotion))
                    componentString = locomotion.componentString()
                    if componentString not in locomotionStrings:
                        locomotionStrings.append(componentString)
                fieldText = Robot._formatWorksheetListString(locomotionStrings)
            elif field == robots.Worksheet.Field.Speed:
                speedStrings = []

                attributeValue = self.attributeValue(
                    attributeId=robots.RobotAttributeId.Speed)
                if isinstance(attributeValue, common.ScalarCalculation):
                    speedStrings.append(common.formatNumber(
                        number=attributeValue.value(),
                        suffix='m'))
                    calculations.append(attributeValue)
                else:
                    speedStrings.append('-')

                attributeValue = self.attributeValue(
                    attributeId=robots.RobotAttributeId.SecondarySpeed)
                if isinstance(attributeValue, common.ScalarCalculation):
                    speedStrings.append(common.formatNumber(
                        number=attributeValue.value(),
                        suffix='m'))
                    calculations.append(attributeValue)

                # NOTE: Finalisation (p76) says to use a '-' for speed if
                # the robot has VSM. This would suggest that a robot with
                # VSM can only move at VSM speeds but that seems odd.
                attributeValue = self.attributeValue(
                    attributeId=robots.RobotAttributeId.VehicleSpeed)
                if isinstance(attributeValue, robots.SpeedBand):
                    speedStrings.append(attributeValue.value)

                fieldText = Robot._formatWorksheetListString(speedStrings)
            elif field == robots.Worksheet.Field.TL:
                fieldText = str(self.techLevel())
            elif field == robots.Worksheet.Field.Cost:
                cost = self.totalCredits()
                fieldText = common.formatNumber(
                    number=cost.value(),
                    prefix='Cr')
                calculations.append(cost)
            elif field == robots.Worksheet.Field.Skills:
                skillString = []
                for skill in self.skills():
                    specialities = skill.specialities()
                    if not specialities:
                        specialities = [None]
                    for speciality in specialities:
                        if applySkillModifiers:
                            skillLevel = self._calcModifierSkillLevel(
                                skill=skill,
                                speciality=speciality)
                        else:
                            skillLevel = skill.level(speciality=speciality)

                        skillString.append('{skill} {level}'.format(
                            skill=skill.name(speciality=speciality),
                            level=skillLevel.value()))
                        calculations.append(skillLevel)
                skillString.sort()

                # Add the amount of spare bandwidth, this should always be done at
                # end of the string (i.e. after sorting)
                spareBandwidth = self.spareBandwidth()
                if spareBandwidth.value() > 0:
                    skillString.append('+{bandwidth} Available Bandwidth'.format(
                        bandwidth=common.formatNumber(number=spareBandwidth.value())))
                    calculations.append(spareBandwidth)

                fieldText = Robot._formatWorksheetListString(skillString)
            elif field == robots.Worksheet.Field.Attacks:
                components = self.findComponents(
                    componentType=robots.Weapon)
                seenWeapons: typing.Dict[str, int] = {}
                for component in components:
                    assert(isinstance(component, robots.Weapon))
                    weaponData = component.weaponData(
                        weaponSet=self.weaponSet())
                    if not weaponData:
                        continue
                    damage = weaponData.damage()
                    traits = weaponData.traits()

                    weaponInfo = '{damage}{separator}{traits}'.format(
                        damage=weaponData.damage(),
                        separator=', ' if damage and traits else '',
                        traits=traits)
                    if isinstance(component, robots.MountedWeapon):
                        weaponInfo += '{separator}Mounted'.format(
                            separator=', ' if weaponInfo and traits else '')    
                        autoloaderCount = component.autoloaderMagazineCount()
                        if autoloaderCount:
                            weaponInfo += '{separator}Autoloader x{count}'.format(
                                separator=', ' if weaponInfo and traits else '',
                                count=common.formatNumber(number=autoloaderCount.value()))                                 
                        linkedCount = component.linkedGroupSize()
                        if linkedCount:
                            weaponInfo += '{separator}Linked x{count}'.format(
                                separator=', ' if weaponInfo and traits else '',
                                count=common.formatNumber(number=linkedCount.value()))                            
                        fireControl = component.fireControl()
                        if fireControl:
                            weaponInfo += '{separator}{level} Fire Control'.format(
                                separator=', ' if weaponInfo and traits else '',
                                level=fireControl.value)
                    elif isinstance(component, robots.HandHeldWeapon):
                        weaponInfo += '{separator}Hand Held'.format(
                            separator=', ' if weaponInfo and traits else '')  
                    weaponString = weaponData.name()
                    if weaponInfo:
                        weaponString += f' ({weaponInfo})'

                    count = seenWeapons.get(weaponString, 0)
                    seenWeapons[weaponString] = count + 1

                weaponStrings = []                 
                for weaponString, count in seenWeapons.items():
                    if count > 1:
                        weaponString = '{count} x {weapon}'.format(
                            count=common.formatNumber(number=count),
                            weapon=weaponString)
                    weaponStrings.append(weaponString)
                fieldText = Robot._formatWorksheetListString(weaponStrings)
            elif field == robots.Worksheet.Field.Manipulators:
                handheldFireControl = self.findComponents(
                    componentType=robots.HandHeldFireControl)
                fireControlManipulators: typing.Dict[robots.Manipulator, robots.FireControlLevel] = {}
                for component in handheldFireControl:
                    assert(isinstance(component, robots.HandHeldFireControl))
                    manipulator = component.manipulator(
                        context=self._constructionContext,
                        sequence=self._sequence)
                    fireControl = component.fireControl()
                    if manipulator and fireControl:
                        fireControlManipulators[manipulator] = fireControl
                    
                components = self.findComponents(
                    componentType=robots.Manipulator)
                seenManipulators: typing.Dict[str, int] = {}
                for component in components:
                    assert(isinstance(component, robots.Manipulator))
                    if isinstance(component, robots.RemoveBaseManipulator):
                        continue

                    manipulatorString = 'STR {strength}, DEX {dexterity}'.format(
                        strength=common.formatNumber(number=component.strength()),
                        dexterity=common.formatNumber(number=component.dexterity()))
                    fireControl = fireControlManipulators.get(component)
                    if fireControl:
                        manipulatorString += f', {fireControl.value} Fire Control'
                    
                    count = seenManipulators.get(manipulatorString, 0)
                    seenManipulators[manipulatorString] = count + 1

                manipulatorStrings = []
                for manipulatorString, count in seenManipulators.items():
                    manipulatorStrings.append('{count} x ({manipulator})'.format(
                        count=common.formatNumber(number=count),
                        manipulator=manipulatorString))
                fieldText = Robot._formatWorksheetListString(manipulatorStrings)
            elif field == robots.Worksheet.Field.Endurance:
                # NOTE: Although it seems unusual, the Endurance is rounded to the nearest
                # hour rather than rounding down as would possibly seem more logical. The
                # book explicitly says this is what should be done in the Final Endurance
                # section (p23)
                # TODO: Need to include the endurance when using secondary locomotion. I
                # think the simplest way to do this would be to only allow a single
                # secondary locomotion and add Endurance (and probably Speed) attributes
                # for it. The intention does seem to be that there is only a single
                # secondary locomotion, it's implied by the rules and both spreadsheets
                # only support 1.
                isBiological = self.hasComponent(componentType=robots.BioRobotSynthetic)
                if isBiological:
                    fieldText = 'As biological being'
                else:
                    enduranceStrings = []
                    attributeValue = self.attributeValue(
                        attributeId=robots.RobotAttributeId.Endurance)
                    if isinstance(attributeValue, common.ScalarCalculation):
                        enduranceStrings.append(common.formatNumber(
                            number=round(attributeValue.value()),
                            suffix=' hours'))
                        calculations.append(attributeValue)
                    else:
                        enduranceStrings.append('None')

                    attributeValue = self.attributeValue(
                        attributeId=robots.RobotAttributeId.SecondaryEndurance)
                    if isinstance(attributeValue, common.ScalarCalculation):
                        enduranceStrings.append(common.formatNumber(
                            number=round(attributeValue.value()),
                            suffix=' hours'))
                        calculations.append(attributeValue)

                    attributeValue = self.attributeValue(
                        attributeId=robots.RobotAttributeId.VehicleEndurance)
                    if isinstance(attributeValue, common.ScalarCalculation):
                        enduranceStrings.append(common.formatNumber(
                            number=round(attributeValue.value()),
                            suffix=' hours'))
                        calculations.append(attributeValue) 

                    fieldText = Robot._formatWorksheetListString(enduranceStrings)
            elif field == robots.Worksheet.Field.Traits:
                traitStrings = []
                for trait in robots.TraitAttributeIds:
                    attribute = self.attribute(attributeId=trait)
                    if not attribute:
                        continue
                    traitString = trait.value
                    value = attribute.value()
                    valueString = None
                    if isinstance(value, common.ScalarCalculation):
                        valueString = common.formatNumber(
                            number=value.value(),
                            alwaysIncludeSign=True)
                    elif isinstance(value, common.DiceRoll):
                        valueString = str(value)
                    elif isinstance(value, enum.Enum):
                        valueString = str(value.value)
                    if valueString:
                        traitString += f' ({valueString})'
                    traitStrings.append(traitString)
                    calculations.extend(attribute.calculations())
                traitStrings.sort()
                fieldText = Robot._formatWorksheetListString(traitStrings)
            elif field == robots.Worksheet.Field.Programming:
                brain = self.findFirstComponent(
                    componentType=robots.Brain)
                if brain:
                    assert(isinstance(brain, robots.Brain))
                    fieldText = brain.componentString()

                    characteristicStrings = []
                    for characteristic in robots.CharacteristicAttributeIds:
                        characteristicValue = self.attributeValue(
                            attributeId=characteristic)
                        if characteristicValue:
                            assert(isinstance(characteristicValue, common.ScalarCalculation))
                            characteristicStrings.append(
                                f'{characteristic.value} {characteristicValue.value()}')
                            calculations.append(characteristicValue)
                    if characteristicStrings:
                        fieldText += ' ({characteristics})'.format(
                            characteristics=', '.join(characteristicStrings))
                else:
                    fieldText = 'None'
            elif field == robots.Worksheet.Field.Options:
                options: typing.Dict[str, int] = {}
                components: typing.List[robots.RobotComponentInterface] = []
                components.extend(self.findComponents(
                    componentType=robots.DefaultSuiteOption))
                components.extend(self.findComponents(
                    componentType=robots.SlotOption))                
                for component in components:
                    componentString = component.instanceString()
                    count = options.get(componentString, 0)
                    options[componentString] = count + 1

                optionStrings = []
                orderedKeys = list(options.keys())
                orderedKeys.sort()
                for componentString in orderedKeys:
                    count = options[componentString]
                    if count > 1:
                        componentString += ' x {count}'.format(
                            count=common.formatNumber(number=count))
                    optionStrings.append(componentString)

                # Add the number of spare slots, this should always be done at
                # end of the string (i.e. after sorting)
                spareSlots = self.spareSlots()
                if spareSlots.value() > 0:
                    optionStrings.append('Spare Slots x {slots}'.format(
                        slots=common.formatNumber(number=spareSlots.value())))
                    calculations.append(spareSlots)

                # At this point the strings should already be sorted
                # alphabetically (but ignoring any count multiplier)
                fieldText = Robot._formatWorksheetListString(optionStrings)

            if fieldText:
                worksheet.setField(
                    field=field,
                    value=fieldText,
                    calculations=calculations if calculations else None)

        return worksheet
    
    def _calcModifierSkillLevel(
            self,
            skill: construction.Skill,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        level = skill.level(speciality=speciality)
        flags = skill.flags(speciality=speciality)
        if (flags & construction.SkillFlagsCharacteristicModifierMask) == 0:
            # Characteristic modifiers aren't applied for this skill
            return level

        characteristic = _SkillCharacteristicMap[skill.skillDef()]
        if isinstance(characteristic, dict):
            characteristic = characteristic.get(speciality)   
        if not characteristic:
            # There is no applicable robot characteristic for this skill
            return level
            
        if characteristic == traveller.Characteristics.Intellect:
            characteristicValue = self.attributeValue(
                attributeId=robots.RobotAttributeId.Intellect)
            if not characteristicValue:
                return level
        else:
            manipulators = self.findComponents(
                componentType=robots.Manipulator)
            highestValue = None
            for manipulator in manipulators:
                if isinstance(manipulator, robots.RemoveBaseManipulator):
                    continue
                assert(isinstance(manipulator, robots.Manipulator))
                if characteristic == traveller.Characteristics.Strength:
                    manipulatorValue = manipulator.strength()
                else:
                    manipulatorValue = manipulator.dexterity()
                if highestValue == None or manipulatorValue > highestValue:
                    highestValue = manipulatorValue
            if not highestValue:
                # No manipulators so no DEX characteristic
                return level

            characteristicValue = common.ScalarCalculation(
                value=highestValue,
                name=f'Highest Manipulator {characteristic.value}')
        
        characteristicModifier = common.ScalarCalculation(
            value=traveller.CharacteristicDMFunction(
                characteristic=characteristic,
                level=characteristicValue))
        if characteristicModifier.value() > 0:
            if (flags & construction.SkillFlags.ApplyPositiveCharacteristicModifier) == 0:
                return level
        elif characteristicModifier.value() < 0:
            if (flags & construction.SkillFlags.ApplyNegativeCharacteristicModifier) == 0:
                return level
        else:
            return level

        return common.Calculator.add(
            lhs=level,
            rhs=characteristicModifier,
            name=f'Modified {skill.name(speciality=speciality)} Skill Level')       

    def _createStages(
            self
            ) -> typing.List[construction.ConstructionStage]:
        stages = []

        stages.append(construction.ConstructionStage(
            name='Chassis',
            sequence=self._sequence,
            phase=robots.RobotPhase.BaseChassis,
            baseType=robots.Chassis,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Primary Locomotion',
            sequence=self._sequence,
            phase=robots.RobotPhase.BaseChassis,
            baseType=robots.PrimaryLocomotion,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Synthetics',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.Synthetic,
            # Optional single component
            minComponents=0,
            maxComponents=1))        
        
        stages.append(construction.ConstructionStage(
            name='Armour Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.ArmourModification,
            # Optional single component
            minComponents=0,
            maxComponents=1))

        stages.append(construction.ConstructionStage(
            name='Endurance Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.EnduranceModification,
            # Optional single component
            minComponents=0,
            maxComponents=1))     

        stages.append(construction.ConstructionStage(
            name='Resiliency Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.ChassisOptions,
            baseType=robots.ResiliencyModification,
            # Optional single component
            minComponents=0,
            maxComponents=1))  

        stages.append(construction.ConstructionStage(
            name='Agility Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.LocomotiveMods,
            baseType=robots.AgilityEnhancement,
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
            baseType=robots.SpeedModification,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))        
        
        # NOTE: I've not seen anything anything in the rules that explicitly
        # says you can only have one secondary locomotion, although it could be
        # the expectation is it's implied by the name. I've decided to make it
        # singular as it makes it easier to track things like endurance for
        # displaying in the worksheet
        stages.append(construction.ConstructionStage(
            name='Secondary Locomotion',
            sequence=self._sequence,
            phase=robots.RobotPhase.LocomotiveMods,
            baseType=robots.SecondaryLocomotion,
            # Optional single component
            minComponents=0,
            maxComponents=1)) 
        
        stages.append(construction.ConstructionStage(
            name='Base Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.BaseManipulator,
            # Mandatory fixed size
            minComponents=2,
            maxComponents=2))
        
        stages.append(construction.ConstructionStage(
            name='Additional Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.AdditionalManipulator,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Leg Manipulators',
            sequence=self._sequence,
            phase=robots.RobotPhase.Manipulators,
            baseType=robots.LegManipulator,
            # Optional multi component
            minComponents=None,
            maxComponents=None)) 

        stage = construction.ConstructionStage(
            name='Default Suite',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.DefaultSuiteOption,
            # Mandatory fixed size
            minComponents=5,
            maxComponents=5)
        # Pre-add the standard default suite (p29)
        stage.addComponent(component=robots.VisualSpectrumSensorDefaultSuiteOption())
        stage.addComponent(component=robots.VoderSpeakerDefaultSuiteOption())
        stage.addComponent(component=robots.AuditorySensorDefaultSuiteOption())
        stage.addComponent(component=robots.WirelessDataLinkDefaultSuiteOption())
        stage.addComponent(component=robots.TransceiverDefaultSuiteOption())
        stages.append(stage)
        
        stages.append(construction.ConstructionStage(
            name='Chassis Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.ChassisSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))

        stages.append(construction.ConstructionStage(
            name='Communication Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.CommunicationSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Medical Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.MedicalSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Miscellaneous Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.MiscSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Power Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.PowerSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))  

        stages.append(construction.ConstructionStage(
            name='Sensor Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.SensorSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))  

        stages.append(construction.ConstructionStage(
            name='Toolkit Options',
            sequence=self._sequence,
            phase=robots.RobotPhase.SlotOptions,
            baseType=robots.ToolkitSlotOption,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Servo Mounted Weapons',
            sequence=self._sequence,
            phase=robots.RobotPhase.Weapons,
            baseType=robots.ServoMountedWeapon,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Manipulator Mounted Weapons',
            sequence=self._sequence,
            phase=robots.RobotPhase.Weapons,
            baseType=robots.ManipulatorMountedWeapon,
            # Optional multi component
            minComponents=None,
            maxComponents=None))        

        stages.append(construction.ConstructionStage(
            name='Handheld Weapons',
            sequence=self._sequence,
            phase=robots.RobotPhase.Weapons,
            baseType=robots.HandHeldWeapon,
            # Optional multi component
            minComponents=None,
            maxComponents=None))        
        
        stages.append(construction.ConstructionStage(
            name='Handheld Weapon Fire Control',
            sequence=self._sequence,
            phase=robots.RobotPhase.Weapons,
            baseType=robots.HandHeldFireControl,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        stages.append(construction.ConstructionStage(
            name='Magazines',
            sequence=self._sequence,
            phase=robots.RobotPhase.Weapons,
            baseType=robots.Magazines,
            # Optional multi component
            minComponents=None,
            maxComponents=None))          
        
        stages.append(construction.ConstructionStage(
            name='Brain',
            sequence=self._sequence,
            phase=robots.RobotPhase.Brain,
            baseType=robots.Brain,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))
        
        stages.append(construction.ConstructionStage(
            name='Skill Package',
            sequence=self._sequence,
            phase=robots.RobotPhase.Skills,
            baseType=robots.SkillPackage,
            # Optional single component
            minComponents=0,
            maxComponents=1,
            # Force a component to be selected if there is one
            forceComponent=True))          

        stages.append(construction.ConstructionStage(
            name='Skills',
            sequence=self._sequence,
            phase=robots.RobotPhase.Skills,
            baseType=robots.Skill,
            # Optional multi component
            minComponents=None,
            maxComponents=None))
        
        # NOTE: If I ever change this so the default isn't None then I'll need
        # to handle the fact the label in the UI will always show the max slots
        # as the number of slots as 0. I'd also need a migration step as I
        # suspect 
        stages.append(construction.ConstructionStage(
            name='Unused Slot Removal',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.UnusedSlotRemoval,
            # Optional single component
            minComponents=0,
            maxComponents=1))
        
        # NOTE: This should happen AFTER unused slots are removed. I think the
        # google spreadsheet might be incorrect and is doing it the other way
        # round. I'm basing this on the fact the Mongoose excel spreadsheet
        # removes the slots first (so the saving from removing unused slots is
        # effectively multiplied).        
        stages.append(construction.ConstructionStage(
            name='Synth Additional Costs',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.SynthAdditionalCosts,
            # Optional single component
            minComponents=0,
            maxComponents=1,
            # Force a component to be selected if there is one. There should
            # only be compatible components if the robot is a synth
            forceComponent=True,
            isInternal=True))
        
        stages.append(construction.ConstructionStage(
            name='Cost Modification',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.CostModification,
            # Optional single component
            minComponents=0,
            maxComponents=1))
        
        # NOTE: It's important that no other costs are added to the robot
        # after this stage
        stages.append(construction.ConstructionStage(
            name='Cost Rounding',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.SignificantFigureCostRounding,
            # Optional single component
            minComponents=0,
            maxComponents=1))           

        # NOTE: This is the final stage of construction it MUST be last,
        # including after other stages in the finalisation phase
        stages.append(construction.ConstructionStage(
            name='Finalisation',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.Finalisation,
            # Mandatory single component
            minComponents=1,
            maxComponents=1,
            isInternal=True)) 
        
        return stages

    @staticmethod
    def _formatWorksheetListString(
            stringList: typing.Iterable[str]
            ) -> str:
        if not stringList:
            return 'None'
        return ', '.join(stringList)
 