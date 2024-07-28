import common
import construction
import enum
import math
import robots
import traveller
import typing
import uuid

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
    _DefaultSuiteComponentCount = common.ScalarCalculation(
        value=5,
        name='Default Suite Zero Slot Count')

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

    def maxZeroSlots(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        size = self.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        if not isinstance(size, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Max Zero Slot Count')

        values = [
            size,
            common.ScalarCalculation(
                value=self.techLevel(),
                name='Robot TL'),
            RobotContext._DefaultSuiteComponentCount
        ]
        return common.Calculator.sum(
            values=values,
            name='Max Zero Slot Count')

    def usedZeroSlots(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        zeroSlots = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.ZeroSlotCount)
        if not isinstance(zeroSlots, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Used Zero Slot Count')
        return common.Calculator.equals(
            value=zeroSlots,
            name='Used Zero Slot Count')

    def spareZeroSlots(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        return common.Calculator.subtract(
            lhs=self.maxZeroSlots(sequence=sequence),
            rhs=self.usedZeroSlots(sequence=sequence),
            name='Spare Zero Slot Count')

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

    def maxZeroBandwidth(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        zeroBandwidth = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.InherentBandwidth)
        if not isinstance(zeroBandwidth, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Max Zero Bandwidth Skill Count')
        return common.Calculator.equals(
            value=zeroBandwidth,
            name='Max Zero Bandwidth Skill Count')

    def usedZeroBandwidth(
            self,
            sequence: str
            ) -> common.ScalarCalculation:
        zeroBandwidth = self.attributeValue(
            sequence=sequence,
            attributeId=robots.RobotAttributeId.ZeroBandwidthSkillCount)
        if not isinstance(zeroBandwidth, common.ScalarCalculation):
            return common.ScalarCalculation(
                value=0,
                name='Used Zero Bandwidth Skill Count')
        return common.Calculator.equals(
            value=zeroBandwidth,
            name='Used Zero Bandwidth Skill Count')

    def spareZeroBandwidth(
            self,
            sequence: str,
            ) -> common.ScalarCalculation:
        return common.Calculator.subtract(
            lhs=self.maxZeroBandwidth(sequence=sequence),
            rhs=self.usedZeroBandwidth(sequence=sequence),
            name='Spare Zero Bandwidth Skill Count')

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

    def maxZeroSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.maxZeroSlots(
            sequence=self._sequence)

    def usedZeroSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.usedZeroSlots(
            sequence=self._sequence)

    def spareZeroSlots(self) -> common.ScalarCalculation:
        return self._constructionContext.spareZeroSlots(
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

    def maxZeroBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.maxZeroBandwidth(
            sequence=self._sequence)

    def usedZeroBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.usedZeroBandwidth(
            sequence=self._sequence)

    def spareZeroBandwidth(self) -> common.ScalarCalculation:
        return self._constructionContext.spareZeroBandwidth(
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

    # NOTE: The Finalisation section (p76) says, as well as characteristic DMs,
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
            applySkillModifiers: bool,
            specialityGroupingCount: int # 0 means don't group
            ) -> robots.Worksheet:
        worksheet = robots.Worksheet()

        for field in robots.Worksheet.Field:
            fieldText = None
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
                locomotions = self.findComponents(
                    componentType=robots.Locomotion)
                locomotionStrings = []
                for locomotion in locomotions:
                    assert(isinstance(locomotion, robots.Locomotion))
                    if isinstance(locomotion, robots.NoPrimaryLocomotion):
                        continue
                    componentString = locomotion.componentString()
                    if componentString not in locomotionStrings:
                        locomotionStrings.append(componentString)

                if self.hasComponent(componentType=robots.VehicleSpeedMovement):
                    locomotionStrings.append('VSM')

                fieldText = Robot._formatWorksheetListString(
                    locomotionStrings,
                    emptyText='-')
            elif field == robots.Worksheet.Field.Speed:
                speedStrings = []

                attributeValue = self.attributeValue(
                    attributeId=robots.RobotAttributeId.Speed)
                if isinstance(attributeValue, common.ScalarCalculation):
                    speedStrings.append(common.formatNumber(
                        number=attributeValue.value(),
                        suffix='m'))
                    calculations.append(attributeValue)

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

                fieldText = Robot._formatWorksheetListString(
                    speedStrings,
                    emptyText='-')
            elif field == robots.Worksheet.Field.TL:
                fieldText = str(self.techLevel())
            elif field == robots.Worksheet.Field.Cost:
                cost = self.totalCredits()
                fieldText = common.formatNumber(
                    number=cost.value(),
                    infix='Cr')
                calculations.append(cost)
            elif field == robots.Worksheet.Field.Skills:
                skillMap: typing.Dict[
                    traveller.SkillDefinition,
                    typing.Dict[
                        typing.Union[str, enum.Enum],
                        typing.Tuple[common.ScalarCalculation, construction.SkillFlags]]] = {}
                for skill in self.skills():
                    skillDef = skill.skillDef()
                    specialities = skill.specialities()

                    specialityMap = {}
                    skillMap[skillDef] = specialityMap
                    if specialities:
                        for speciality in specialities:
                            specialityMap[speciality] = (
                                skill.level(speciality=speciality),
                                skill.flags(speciality=speciality))
                    else:
                        specialityMap[None] = (skill.level(), skill.flags())

                if applySkillModifiers:
                    # Apply fire control to weapon skills
                    weaponSet = self.weaponSet()
                    fireControlSkills: typing.List[
                        typing.Tuple[
                            traveller.SkillDefinition,
                            typing.Union[str, enum.Enum],
                            common.ScalarCalculation]] = []
                    for component in self.findComponents(componentType=robots.MountedWeapon):
                        assert(isinstance(component, robots.MountedWeapon))
                        if component.fireControl():
                            fireControlSkills.append(component.fireControlSkill(weaponSet=weaponSet))
                    for component in self.findComponents(componentType=robots.HandHeldFireControl):
                        assert(isinstance(component, robots.HandHeldFireControl))
                        if component.fireControl():
                            fireControlSkills.append(component.fireControlSkill(weaponSet=weaponSet))

                    for skillDef, speciality, level in fireControlSkills:
                        if skillDef in skillMap and speciality in skillMap[skillDef]:
                            currentLevel, _ = skillMap[skillDef][speciality]
                        else:
                            currentLevel = None

                        if (not currentLevel) or (currentLevel.value() < level.value()):
                            specialityMap = skillMap.get(skillDef)
                            if not specialityMap:
                                specialityMap = {}
                                skillMap[skillDef] = specialityMap

                            specialityMap[speciality] = (
                                level,
                                # Positive and negative characteristics DMs
                                # should be applied. I can't find anywhere that
                                # explicitly states this but it seems logical
                                # based on the clarifications from Geir where he
                                # said the intention fire control was intended
                                # to be used instead of the robots weapon skill
                                # _and_ that combat was meant to work the same
                                # as for meatsack travellers.
                                construction.SkillFlags(0))

                            if None in specialityMap:
                                # Remove zero level skill as it's implied by the
                                # speciality that was just added
                                del specialityMap[None]

                    # Apply manipulator DEX/STR to athletics skill
                    skill = self.skill(skillDef=traveller.AthleticsSkillDefinition)
                    if skill:
                        manipulators = self.findComponents(componentType=robots.Manipulator)
                        baseDexLevel = skill.level(speciality=traveller.AthleticsSkillSpecialities.Dexterity)
                        baseStrLevel = skill.level(speciality=traveller.AthleticsSkillSpecialities.Strength)
                        newDexLevel = newStrLevel = None
                        for index, component in enumerate(manipulators):
                            if isinstance(component, robots.RemoveBaseManipulator):
                                continue
                            assert(isinstance(component, robots.Manipulator))

                            if baseDexLevel:
                                manipulatorDexDM = traveller.characteristicDM(
                                    level=component.dexterity())
                                manipulatorDexDM = common.ScalarCalculation(
                                    value=manipulatorDexDM,
                                    name=f'Manipulator #{index} DEX Characteristic DM')
                                manipulatorDexLevel = common.Calculator.add(
                                    lhs=baseDexLevel,
                                    rhs=manipulatorDexDM,
                                    name=f'Manipulator #{index} Athletics (Dexterity) Skill')
                                if (newDexLevel == None) or manipulatorDexLevel.value() > newDexLevel.value():
                                    newDexLevel = manipulatorDexLevel

                            if baseStrLevel:
                                manipulatorStrDM = traveller.characteristicDM(
                                    level=component.strength())
                                manipulatorStrDM = common.ScalarCalculation(
                                    value=manipulatorStrDM,
                                    name=f'Manipulator #{index} STR Characteristic DM')
                                manipulatorStrLevel = common.Calculator.add(
                                    lhs=baseStrLevel,
                                    rhs=manipulatorStrDM,
                                    name=f'Manipulator #{index} Athletics (Strength) Skill')
                                if (newStrLevel == None) or manipulatorStrLevel.value() > newStrLevel.value():
                                    newStrLevel = manipulatorStrLevel

                        if newDexLevel or newStrLevel:
                            specialityMap = skillMap.get(traveller.AthleticsSkillDefinition)
                            if not specialityMap:
                                specialityMap = {}
                                skillMap[skillDef] = specialityMap

                            # NOTE: When athletics skills are from manipulators,
                            # characteristics DMs shouldn't be applied (p26)
                            noCharacteristicDMs = construction.SkillFlags.NoNegativeCharacteristicModifier | \
                                construction.SkillFlags.NoPositiveCharacteristicModifier
                            if newDexLevel:
                                specialityMap[traveller.AthleticsSkillSpecialities.Dexterity] = \
                                    (newDexLevel, noCharacteristicDMs)
                            if newStrLevel:
                                specialityMap[traveller.AthleticsSkillSpecialities.Strength] = \
                                    (newStrLevel, noCharacteristicDMs)

                            # If a new skill was set remove the level 0 Athletics
                            # skill if it's set (as the listed specialisations
                            # will imply Athletics 0)
                            if None in specialityMap:
                                del specialityMap[None]

                    # Apply active camouflage stealth skill
                    component = self.findFirstComponent(
                        componentType=robots.ActiveCamouflageSlotSlotOption)
                    if isinstance(component, robots.ActiveCamouflageSlotSlotOption):
                        specialityMap = skillMap.get(traveller.StealthSkillDefinition)
                        if not specialityMap:
                            specialityMap = {}
                            skillMap[traveller.StealthSkillDefinition] = specialityMap
                        specialityMap[None] = (component.stealthSkill(),
                                               # Don't apply characteristics modifiers. This is based
                                               # on Ultra (p258) as it would have Stealth 7 if it's DEX
                                               # characteristic DM was being applied
                                               construction.SkillFlags.NoNegativeCharacteristicModifier |
                                               construction.SkillFlags.NoPositiveCharacteristicModifier)

                    # Apply characteristics modifiers to skills
                    for skillDef, specialityMap in skillMap.items():
                        for speciality, skillData in specialityMap.items():
                            level = skillData[0]
                            flags = skillData[1]
                            level = self._calcModifierSkillLevel(
                                skillDef=skillDef,
                                speciality=speciality,
                                level=level,
                                flags=flags)
                            skillMap[skillDef][speciality] = (level, flags)

                skillString = []
                for skillDef, specialityMap in skillMap.items():
                    if specialityGroupingCount and len(specialityMap) >= specialityGroupingCount:
                        allSameLevel = True
                        lastLevel = None
                        for level, _ in specialityMap.values():
                            if lastLevel and level.value() != lastLevel.value():
                                allSameLevel = False
                                break
                            lastLevel = level

                        if allSameLevel:
                            skillString.append('{skill} {level}'.format(
                                skill=skillDef.name(speciality='all'),
                                level=lastLevel.value()))
                            for level, _ in specialityMap.values():
                                calculations.append(level)
                            continue

                    for speciality, skillData in specialityMap.items():
                        level = skillData[0]
                        if not skillDef.isSimple() and not speciality and level.value() > 0:
                            # This should only happen if applying modifiers to skills
                            # is enabled and a level 0 skill has been taken over 0.
                            # In this situation use a fake speciality of 'all' to make
                            # things look a bit more like the rule book
                            speciality = 'all'
                        skillString.append('{skill} {level}'.format(
                            skill=skillDef.name(speciality=speciality),
                            level=level.value()))
                        calculations.append(level)
                skillString.sort(key=str.casefold)

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
                    infoStrings = []
                    damage = weaponData.damage()
                    if damage:
                        infoStrings.append(damage)
                    traits = weaponData.traits()
                    if traits:
                        infoStrings.append(traits)

                    if isinstance(component, robots.MountedWeapon):
                        infoStrings.append('Mounted')
                        autoloaderCount = component.autoloaderMagazineCount()
                        if autoloaderCount:
                            infoStrings.append('Autoloader x{count}'.format(
                                count=common.formatNumber(number=autoloaderCount.value())))
                        linkedCount = component.linkedGroupSize()
                        if linkedCount:
                            infoStrings.append('Linked x{count}'.format(
                                count=common.formatNumber(number=linkedCount.value())))
                        fireControl = component.fireControl()
                        if fireControl:
                            infoStrings.append('{level} Fire Control'.format(
                                level=fireControl.value))
                    elif isinstance(component, robots.HandHeldWeapon):
                        infoStrings.append('Hand Held')
                    weaponString = weaponData.name()
                    if infoStrings:
                        weaponString += ' ({info})'.format(
                            info=', '.join(infoStrings))

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

                    manipulatorString = f'({manipulatorString})'
                    if isinstance(component, robots.LegManipulator):
                        manipulatorString = f'Leg Manipulator {manipulatorString}'

                    count = seenManipulators.get(manipulatorString, 0)
                    seenManipulators[manipulatorString] = count + 1

                manipulatorStrings = []
                for manipulatorString, count in seenManipulators.items():
                    manipulatorStrings.append('{count} x {manipulator}'.format(
                        count=common.formatNumber(number=count),
                        manipulator=manipulatorString))
                fieldText = Robot._formatWorksheetListString(manipulatorStrings)
            elif field == robots.Worksheet.Field.Endurance:
                # NOTE: Although it seems unusual, the Endurance is rounded to the nearest
                # hour rather than rounding down as would possibly seem more logical. The
                # book explicitly says this is what should be done in the Final Endurance
                # section (p23)
                isBiological = self.hasComponent(componentType=robots.BioRobotSynthetic)
                if isBiological:
                    fieldText = 'As biological being'
                else:
                    enduranceStrings = []

                    primaryLocomotion = self.findFirstComponent(
                        componentType=robots.PrimaryLocomotion)
                    if isinstance(primaryLocomotion, robots.NoPrimaryLocomotion):
                        primaryLocomotion = None
                    secondaryLocomotion = self.findFirstComponent(
                        componentType=robots.SecondaryLocomotion)

                    primaryString = 'None'
                    if primaryLocomotion:
                        primaryEndurance = self.attributeValue(
                            attributeId=robots.RobotAttributeId.Endurance)
                        if isinstance(primaryEndurance, common.ScalarCalculation):
                            primaryString = common.formatNumber(
                                number=round(primaryEndurance.value()),
                                suffix=' hours')
                            calculations.append(primaryEndurance)

                    if primaryLocomotion and secondaryLocomotion:
                        primaryString += f' ({primaryLocomotion.componentString()})'
                    enduranceStrings.append(primaryString)

                    if secondaryLocomotion:
                        secondaryEndurance = self.attributeValue(
                            attributeId=robots.RobotAttributeId.SecondaryEndurance)
                        if isinstance(secondaryEndurance, common.ScalarCalculation):
                            enduranceStrings.append(common.formatNumber(
                                number=round(secondaryEndurance.value()),
                                suffix=f' hours ({secondaryLocomotion.componentString()})'))
                            calculations.append(secondaryEndurance)

                    vsmEndurance = self.attributeValue(
                        attributeId=robots.RobotAttributeId.VehicleEndurance)
                    if isinstance(vsmEndurance, common.ScalarCalculation):
                        enduranceStrings.append(common.formatNumber(
                            number=round(vsmEndurance.value()),
                            suffix=' hours (VSM)'))
                        calculations.append(vsmEndurance)

                    fieldText = Robot._formatWorksheetListString(
                        stringList=enduranceStrings,
                        # No placeholder as need to take other power sources into account
                        emptyText='')

                    powerTypes = (
                        robots.SolarCoatingDefaultSuiteOption,
                        robots.SolarCoatingSlotOption,
                        robots.SolarPowerUnitSlotOption,
                        robots.RTGSlotOption)
                    powerSources = {}
                    for componentType in powerTypes:
                        powerComponents = self.findComponents(componentType=componentType)
                        for component in powerComponents:
                            powerString = component.instanceString()
                            count = powerSources.get(powerString, 0)
                            powerSources[powerString] = count + 1
                    if powerSources:
                        for powerSource, count in powerSources.items():
                            if count > 1:
                                powerSource = f'{count} x {powerSource}'
                            if fieldText:
                                fieldText += ' + '
                            fieldText += powerSource
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
                traitStrings.sort(key=str.casefold)
                fieldText = Robot._formatWorksheetListString(traitStrings)
            elif field == robots.Worksheet.Field.Programming:
                brain = self.findFirstComponent(
                    componentType=robots.Brain)
                if brain:
                    assert(isinstance(brain, robots.Brain))
                    fieldText = brain.componentString()

                    attributeValue = self.attributeValue(
                        attributeId=robots.RobotAttributeId.INT)
                    if isinstance(attributeValue, common.ScalarCalculation):
                        fieldText += f' (INT {attributeValue.value()})'
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
                orderedKeys.sort(key=str.casefold)
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
            elif field == robots.Worksheet.Field.Characteristics:
                isPlayerCharacter = self.hasComponent(
                    componentType=robots.PlayerCharacter)
                isBrainInAJar = self.hasComponent(
                    componentType=robots.BrainInAJarBrain)
                if isPlayerCharacter or isBrainInAJar:
                    characteristicStrings = []
                    for characteristic in robots.CharacteristicAttributeIds:
                        characteristicValue = self.attributeValue(
                            attributeId=characteristic)
                        if isinstance(characteristicValue, common.ScalarCalculation):
                            characteristicStrings.append(
                                f'{characteristic.value} {characteristicValue.value()}')
                            calculations.append(characteristicValue)
                    fieldText = Robot._formatWorksheetListString(characteristicStrings)
                else:
                    # Don't add characteristics field
                    fieldText = None

            if fieldText != None:
                worksheet.setField(
                    field=field,
                    value=fieldText,
                    calculations=calculations if calculations else None)

        return worksheet

    def _calcModifierSkillLevel(
            self,
            skillDef: traveller.SkillDefinition,
            level: common.ScalarCalculation,
            flags: construction.SkillFlags,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        noNegativeModifiers = (flags & construction.SkillFlags.NoNegativeCharacteristicModifier) != 0
        noPositiveModifiers = (flags & construction.SkillFlags.NoPositiveCharacteristicModifier) != 0
        if noNegativeModifiers and noPositiveModifiers:
            # Characteristic modifiers aren't applied for this skill
            return level

        characteristic = robots.skillToCharacteristic(
            skillDef=skillDef,
            speciality=speciality)
        if not characteristic:
            # There is no applicable robot characteristic for this skill
            return level

        if characteristic == traveller.Characteristic.Intellect:
            characteristicValue = self.attributeValue(
                attributeId=robots.RobotAttributeId.INT)
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
                if characteristic == traveller.Characteristic.Strength:
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
            if noPositiveModifiers:
                return level
        elif characteristicModifier.value() < 0:
            if noNegativeModifiers:
                return level
        else:
            return level

        return common.Calculator.add(
            lhs=level,
            rhs=characteristicModifier,
            name=f'Modified {skillDef.name(speciality=speciality)} Skill Level')

    def _createStages(
            self
            ) -> typing.List[construction.ConstructionStage]:
        stages = []

        stages.append(construction.ConstructionStage(
            name='Chassis',
            sequence=self._sequence,
            phase=robots.RobotPhase.BaseChassis,
            baseType=robots.Chassis,
            defaultType=robots.Size5Chassis, # Default to human size
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

        stages.append(construction.ConstructionStage(
            name='Special Use',
            sequence=self._sequence,
            phase=robots.RobotPhase.Finalisation,
            baseType=robots.PlayerCharacter,
            # Optional single component
            minComponents=0,
            maxComponents=1))

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
            stringList: typing.Iterable[str],
            emptyText: str = '-'
            ) -> str:
        if not stringList:
            return emptyText
        return ', '.join(stringList)
