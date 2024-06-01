import common
import enum
import construction
import logging
import traveller
import typing

class CompatibilityException(Exception):
    pass

class SequenceState(object):
    def __init__(
            self,
            phasesType: typing.Type[construction.ConstructionPhase],
            componentsType: typing.Type[construction.ComponentInterface],
            isPrimary: bool,
            stages: typing.Optional[typing.Iterable[construction.ConstructionStage]]
            ) -> None:
        self._phasesType = phasesType
        self._componentsType = componentsType
        self._isPrimary = isPrimary
        self._phaseStages: typing.Dict[construction.ConstructionPhase, typing.List[construction.ConstructionStage]] = {}
        self._componentTypeStages: typing.Dict[typing.Type[construction.ComponentInterface], typing.List[construction.ConstructionStage]] = {}
        self._attributes = construction.AttributesGroup()
        self._skills = construction.SkillGroup()
        self._phaseSteps: typing.Dict[construction.ConstructionPhase, typing.List[construction.ConstructionStep]] = {}
        self._stepComponents: typing.Dict[construction.ConstructionStep, construction.ComponentInterface] = {}
        self._componentSteps: typing.Dict[construction.ComponentInterface, typing.List[construction.ConstructionStep]] = {}
        if stages:
            self.setStages(stages=stages)

    def isPrimary(self) -> bool:
        return self._isPrimary

    def setPrimary(self, primary: bool) -> None:
        self._isPrimary = primary

    def stages(
            self,
            phase: typing.Optional[construction.ConstructionPhase] = None,
            componentType: typing.Optional[typing.Type[construction.ComponentInterface]] = None
            ) -> typing.Collection[construction.ConstructionStage]:
        if componentType and not isinstance(componentType, type):
            componentType = type(componentType)

        if phase:
            stages = self._phaseStages.get(phase, [])
            if not componentType:
                return stages
            return [stage for stage in stages if stage.matchesComponent(component=componentType)]

        # It's important that, when returning stages for multiple phases,
        # they're returned in construction order. Due to the way stages are
        # added to _stageMap its values probably won't naturally be in the
        # correct order. Doing this makes processing of the stages much
        # simpler for consumers
        matched = []
        for phase in self._phasesType:
            stages = self._phaseStages.get(phase)
            if not stages:
                continue

            if not componentType:
                matched.extend(stages)
            else:
                for stage in stages:
                    if stage.matchesComponent(component=componentType):
                        matched.append(stage)
        return matched

    def setStages(
            self,
            stages: typing.Iterable[construction.ConstructionStage]
            ) -> None:
        self._phaseStages.clear()
        self._componentTypeStages.clear()

        componentTypes = common.getSubclasses(
            classType=self._componentsType,
            topLevelOnly=False)

        for stage in stages:
            phaseStages = self._phaseStages.get(stage.phase())
            if not phaseStages:
                self._phaseStages[stage.phase()] = [stage]
            else:
                phaseStages.append(stage)

            # Update mapping of component types to stages with the stages that
            # handle components of those types or components derived from those
            # types. The later part is important as the mapping should contain
            # entries for things like Accessory that map to all stages that deal
            # with classes derived from Accessory even though those stages only
            # match classes derived from that type. This is why the subclass
            # check is performed in both directions rather than just checking
            # that the stage matches the component type.
            for componentType in componentTypes:
                if issubclass(stage.baseType(), componentType) or \
                        issubclass(componentType, stage.baseType()):
                    typeStages = self._componentTypeStages.get(componentType)
                    if not typeStages:
                        typeStages = []
                        self._componentTypeStages[componentType] = typeStages
                    typeStages.append(stage)

    def clearStages(self) -> None:
        self._phaseStages.clear()
        self._componentTypeStages.clear()

    def applyStep(
            self,
            phase: construction.ConstructionPhase,
            component: construction.ComponentInterface,
            step: construction.ConstructionStep
            ) -> None:
        phaseSteps = self._phaseSteps.get(phase)
        if phaseSteps == None:
            phaseSteps = []
            self._phaseSteps[phase] = phaseSteps
        phaseSteps.append(step)

        self._stepComponents[step] = component

        componentSteps = self._componentSteps.get(component)
        if componentSteps:
            componentSteps.append(step)
        else:
            self._componentSteps[component] = [step]

        for factor in step.factors():
            if isinstance(factor, construction.AttributeFactor):
                # Apply attribute factors to attribute group
                factor.applyTo(attributeGroup=self._attributes)
            elif isinstance(factor, construction.SkillFactor):
                # Apply skill factors to skill group
                factor.applyTo(skillGroup=self._skills)

    def steps(
            self,
            component: typing.Optional[construction.ComponentInterface] = None,
            phase: typing.Optional[construction.ConstructionPhase] = None
            ) -> typing.Collection[construction.ConstructionStep]:
        if component:
            return self._componentSteps.get(component, [])

        # Return all steps in construction order
        phaseList = self._phasesType if not phase else [phase]
        steps = []
        for phase in phaseList:
            phaseSteps = self._phaseSteps.get(phase)
            if phaseSteps:
                steps.extend(phaseSteps)
        return steps

    def components(
            self,
            phase: typing.Optional[construction.ConstructionPhase] = None,
            step: typing.Optional[construction.ConstructionStep] = None
            ) -> typing.Collection[construction.ComponentInterface]:
        if step:
            component = self._stepComponents.get(step)
            return [component] if component else []

        # When returning components for multiple phases, return them in
        # construction order
        phaseList = self._phasesType if not phase else [phase]
        components = []
        for phase in phaseList:
            stages = self._phaseStages.get(phase)
            if not stages:
                continue
            for stage in stages:
                components.extend(stage.components())
        return components

    def findFirstComponent(
            self,
            componentType: typing.Type[construction.ComponentInterface]
            ) -> typing.Optional[construction.ComponentInterface]:
        components = self._componentSearch(
            componentType=componentType,
            stopOnFirst=True)
        if not components:
            return None
        return components[0]

    def findComponents(
            self,
            componentType: typing.Type[construction.ComponentInterface]
            ) -> typing.Iterable[construction.ComponentInterface]:
        return self._componentSearch(
            componentType=componentType,
            stopOnFirst=False)

    def hasComponent(
            self,
            componentType: typing.Type[construction.ComponentInterface]
            ) -> bool:
        return self.findFirstComponent(componentType=componentType) != None

    def hasAttribute(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> bool:
        return self._attributes.hasAttribute(attributeId=attributeId)

    def attribute(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> typing.Optional[construction.AttributeInterface]:
        return self._attributes.attribute(attributeId=attributeId)

    def attributeValue(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        return self._attributes.attributeValue(attributeId=attributeId)
    
    # NOTE: A skill is only classed as having a speciality if it has the
    # speciality at level 1 or higher
    def hasSkill(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> bool:
        return self._skills.hasSkill(
            skillDef=skillDef,
            speciality=speciality)

    def skill(
            self,
            skillDef: traveller.SkillDefinition
            ) -> typing.Optional[construction.TrainedSkill]:
        return self._skills.skill(skillDef)
    
    def skillLevel(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        return self._skills.level(
            skillDef=skillDef,
            speciality=speciality)

    def phaseCost(
            self,
            costId: construction.ConstructionCost,
            phase: construction.ConstructionPhase
            ) -> common.ScalarCalculation:
        steps = self._phaseSteps.get(phase)
        if not steps:
            return common.ScalarCalculation(
                value=0,
                name=f'Total {phase.value} {costId.value}')

        cost = construction.ConstructionStep.calculateSequenceCost(
            costId=costId,
            steps=steps)
        if not cost:
            raise RuntimeError(
                f'Unable to calculate {costId.value} for phase {phase.value} as starting modifier is not absolute')
        return common.Calculator.rename(
            value=cost,
            name=f'Total {phase.value} {costId.value}')

    def resetConstruction(self) -> None:
        self._attributes.clear()
        self._skills.clear()
        self._phaseSteps.clear()
        self._stepComponents.clear()
        self._componentSteps.clear()

    def _componentSearch(
            self,
            componentType: typing.Type[construction.ComponentInterface],
            stopOnFirst: bool
            ) -> typing.Iterable[construction.ComponentInterface]:
        if not isinstance(componentType, type):
            componentType = type(componentType)

        stages = self._componentTypeStages.get(componentType)
        if not stages:
            return []

        # When searching for components return them in construction order. This
        # is done for consistency with how stages are returned
        matched = []
        for stage in stages:
            for component in stage.components():
                if not isinstance(component, componentType):
                    continue
                matched.append(component)
                if stopOnFirst:
                    return matched
        return matched

class ConstructionContext(object):
    def __init__(
            self,
            phasesType: typing.Type[construction.ConstructionPhase],
            componentsType: typing.Type[construction.ComponentInterface],
            techLevel: int
            ) -> None:
        self._phasesType = phasesType
        self._componentsType = componentsType
        self._techLevel = techLevel
        self._sequenceStates: typing.Dict[str, SequenceState] = {}
        self._activeStage = None
        self._activeComponent = None

    def techLevel(self) -> int:
        return self._techLevel

    def setTechLevel(
            self,
            techLevel: int,
            regenerate: bool = True
            ) -> None:
        self._techLevel = techLevel

        if regenerate:
            self.regenerate()

    def sequences(self) -> typing.Iterable[str]:
        return list(self._sequenceStates.keys())

    def addSequence(
            self,
            sequence: str,
            sequenceState: SequenceState,
            regenerate: bool = True
            ) -> None:
        self._sequenceStates[sequence] = sequenceState

        if regenerate:
            self.regenerate()

    def removeSequence(
            self,
            sequence: str,
            regenerate: bool = True
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        del self._sequenceStates[sequence]

        # If the primary sequence was deleted set the first remaining sequence
        # as the primary
        if sequenceState.isPrimary() and len(self._sequenceStates) > 0:
            self._sequenceStates[0].setPrimary(primary=True)

        if regenerate:
            self.regenerate()

    def sequenceCount(self) -> int:
        return len(self._sequenceStates)

    def clearSequences(self) -> None:
        self._activeSequence = None
        self._activeComponent = None
        self._sequenceStates.clear()

        # Reset construction to clear stored state. No point regenerating as
        # there is nothing to regenerate
        self._resetConstruction()

    def isPrimary(
            self,
            sequence: str
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.isPrimary()

    def state(
            self,
            sequence: str
            ) -> typing.Optional[SequenceState]:
        return self._sequenceStates.get(sequence)

    def states(self) -> typing.Iterable[SequenceState]:
        return list(self._sequenceStates.values())

    def stages(
            self,
            sequence: typing.Optional[str] = None,
            phase: typing.Optional[construction.ConstructionPhase] = None,
            componentType: typing.Optional[typing.Type[construction.ComponentInterface]] = None
            ) -> typing.Iterable[construction.ConstructionStage]:
        if sequence != None:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')

            return sequenceState.stages(
                phase=phase,
                componentType=componentType)

        matched = []
        phaseList = self._phasesType if phase == None else [phase]
        for phase in phaseList:
            for sequenceState in self._sequenceStates.values():
                for stage in sequenceState.stages(phase=phase, componentType=componentType):
                    if stage not in matched: # Avoid duplicates for common stages
                        matched.append(stage)
        return matched

    def loadComponents(
            self,
            sequenceComponents: typing.Optional[typing.Mapping[
                str, # Sequence
                typing.Iterable[typing.Tuple[ # List of components in sequence
                    str, # Component type
                    typing.Optional[typing.Mapping[ # Options for this component
                        str, # Option ID
                        typing.Any # Option value
                        ]]
                    ]]]] = None,
            commonComponents: typing.Optional[typing.Iterable[typing.Tuple[ # List of common components
                str, # Component type
                typing.Optional[typing.Mapping[ # Options for this component
                    str, # Option ID
                    typing.Any # Option value
                    ]]
                ]]] = None
            ) -> None:
        self.clearComponents(regenerate=False)

        # This get a list of ALL component classes under the base
        # construction component type used by the contents
        componentClasses = common.getSubclasses(
            classType=self._componentsType,
            topLevelOnly=True)

        componentTypeMap = {}
        for componentClass in componentClasses:
            componentTypeMap[componentClass.__name__] = componentClass

        stages = self.stages()
        componentOptionData: typing.Dict[
            construction.ComponentInterface,
            typing.Dict[str, typing.Any]] = {}

        if sequenceComponents:
            # Add sequence components to stages
            for sequence, componentDataList in sequenceComponents.items():
                for componentType, optionData in componentDataList:
                    componentClass = componentTypeMap.get(componentType)
                    if not componentClass:
                        logging.warning(f'Ignoring unknown component type {componentType} when loading sequence {sequence} components')
                        continue
                    component = componentClass()

                    for stage in stages:
                        stageSequence = stage.sequence()
                        if stageSequence and stageSequence != sequence:
                            # The stage is for a sequence but not this one
                            continue

                        if stage.matchesComponent(component=componentClass):
                            stage.addComponent(component=component)
                            break

                    componentOptionData[component] = optionData

        if commonComponents:
            # Add common components to stages
            for componentType, optionData in commonComponents:
                componentClass = componentTypeMap.get(componentType)
                if not componentClass:
                    logging.warning(f'Ignoring unknown component type {componentType} when loading common components')
                    continue
                component = componentClass()

                for stage in stages:
                    if stage.matchesComponent(component=componentClass):
                        stage.addComponent(component=component)
                        break

                componentOptionData[component] = optionData                

        if not componentOptionData:
            # If there are no component options then we can bail early.
            # Regenerate the weapon so it's in a consistent state
            # compared to if there had been options
            self.regenerate()
            return
        
        self._resetConstruction()

        # Regenerate the weapon, loading component options as we go
        # NOTE: This doesn't use the stages method to get a list of stages in
        # construction order as it only includes common stages once and actual
        # construction needs to generate common component steps for each each
        # stage. It's simpler to just iterate over stages as we need than adding
        # some complex logic. This also avoids the overhead of creating a list
        # of the stages.
        # NOTE: It's important that the order components are processed is kept
        # the same as in regenerate method
        for phase in self._phasesType:
            for sequence, sequenceState in self._sequenceStates.items():
                stages = sequenceState.stages(phase=phase)
                for stage in stages:
                    for component in stage.components(dependencyOrder=True):
                        optionData = componentOptionData.get(component)
                        if not optionData:
                            continue

                        # NOTE: Options that are successfully set will be
                        # removed from optionData
                        self._loadComponentOptions(
                            stage=stage,
                            component=component,
                            optionData=optionData)

                    self._regenerateStage(
                        sequence=sequence,
                        stage=stage)
                    
        for component, optionData in componentOptionData.items():
            if not optionData:
                continue # All options were applied
            for option in optionData.keys():
                logging.warning(f'Ignoring unknown option {option} for component {component}')

    def addComponent(
            self,
            stage: construction.ConstructionStage,
            component: construction.ComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            addComponent=component,
            regenerate=regenerate)

    def removeComponent(
            self,
            stage: construction.ConstructionStage,
            component: construction.ComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            removeComponent=component,
            regenerate=regenerate)

    def replaceComponent(
            self,
            stage: construction.ConstructionStage,
            oldComponent: typing.Optional[construction.ComponentInterface],
            newComponent: typing.Optional[construction.ComponentInterface],
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            removeComponent=oldComponent,
            addComponent=newComponent,
            regenerate=regenerate)

    def clearComponents(
            self,
            phase: typing.Optional[construction.ConstructionPhase] = None,
            sequence: typing.Optional[str] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        stages = self.stages(sequence=sequence, phase=phase)
        modified = False
        for stage in stages:
            if self.clearStage(stage=stage, regenerate=False):
                modified = True

        # If regenerate is specified always regenerate even if nothing was
        # modified
        if regenerate:
            self.regenerate()

        return modified
    
    def clearStage(
            self,
            stage: construction.ConstructionStage,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        modified = False
        if stage.components():
            stage.clearComponents()
            modified = True

        # If regenerate is specified always regenerate even if nothing was
        # modified
        if regenerate:
            self.regenerate()            

        return modified

    def regenerate(
            self,
            stopStage: typing.Optional[construction.ConstructionStage] = None
            ) -> None:
        try:
            self._resetConstruction()

            # NOTE: This doesn't use the stages method to get a list of stages
            # in construction order as it only includes common stages once and
            # actual construction needs to generate common component steps for
            # each each stage. It's simpler to just iterate over stages as we
            # need than adding some complex logic. This also avoids the overhead
            # of creating a list of the stages.
            # NOTE: It's important that the order components are processed is kept
            # the same as in loadComponents method
            for phase in self._phasesType:
                for sequence, sequenceState in self._sequenceStates.items():
                    stages = sequenceState.stages(phase=phase)
                    for stage in stages:
                        if stage == stopStage:
                            return True
                        self._regenerateStage(stage=stage, sequence=sequence)
        except:
            self._isIncomplete = True
            raise

    def phaseCost(
            self,
            sequence: str,
            phase: construction.ConstructionPhase,
            costId: construction.ConstructionCost
            ) -> common.ScalarCalculation:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.phaseCost(
            costId=costId,
            phase=phase)

    def steps(
            self,
            sequence: str,
            component: typing.Optional[construction.ComponentInterface] = None,
            phase: typing.Optional[construction.ConstructionPhase] = None,
            ) -> typing.Collection[construction.ConstructionStep]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.steps(component=component, phase=phase)

    def findFirstComponent(
            self,
            componentType: typing.Type[construction.ComponentInterface],
            sequence: typing.Optional[str] = None
            ) -> typing.Optional[construction.ComponentInterface]:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.findFirstComponent(componentType=componentType)

        for sequenceState in self._sequenceStates.values():
            matched = sequenceState.findFirstComponent(componentType=componentType)
            if matched:
                return matched
        return None

    def findComponents(
            self,
            componentType: typing.Type[construction.ComponentInterface],
            sequence: typing.Optional[str] = None
            ) -> typing.Iterable[construction.ComponentInterface]:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.findComponents(componentType=componentType)

        matched = []
        for sequenceState in self._sequenceStates.values():
            components = sequenceState.findComponents(componentType=componentType)
            for component in components:
                if component not in matched: # Prevent duplicates for common phases
                    matched.append(component)
        return matched

    # The replaceComponent parameter can be used to get the list of components
    # that would be compatible if the specified component was being replaced. If
    # the replaceComponent is compatible with the context (which generally it
    # always should be) then it will be included in the returned list of
    # components
    def findCompatibleComponents(
            self,
            stage: construction.ConstructionStage,
            replaceComponent: typing.Optional[construction.ComponentInterface] = None
            ) -> typing.Iterable[construction.ComponentInterface]:
        sequenceState = None
        if stage.sequence():
            sequenceState = self._sequenceStates.get(stage.sequence())
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {stage.sequence()}')

        restoreIndex = -1
        if replaceComponent:
            # In order to ignore a component it needs to be temporarily removed
            # from the stage. When components are checking for the presence of a
            # component it will result in a call back to the stage to check what
            # components it contains. By removing the component from the list
            # these checks won't see it.
            restoreIndex = stage.removeComponent(replaceComponent)
            if restoreIndex < 0:
                # The component to replace isn't part of the stage. Treat it as
                # if no replace component was specified. In theory this could
                # happen if the component has already been removed from the
                # stage due to requiring another component to be present but
                # it's since been removed (e.g. the Drone Interface for a robot
                # requires the robot to have a Transmitter).
                replaceComponent = None

        try:
            if restoreIndex >= 0:
                # Regenerate the context up to this stage. Doing this is VERY
                # important as we need to regenerate attributes to the value the
                # are when this stage is applied. When doing this it means this
                # functor must fully regenerate the context once compatibility
                # has been checked
                self.regenerate(stopStage=stage)

            componentTypes = common.getSubclasses(
                classType=stage.baseType(),
                topLevelOnly=True)
            # TODO: This change needs a lot of testing. I think it should be
            # safe as it will only come into play if there was a stage where
            # prior to the change there were never any compatible components.
            if not componentTypes:
                # The stage base type has no subclasses. This is expected for
                # stages that only ever have one compatible component type (that
                # being the base type its self)
                componentTypes = [stage.baseType()]

            compatible = []
            for componentType in componentTypes:
                if replaceComponent and componentType == type(replaceComponent):
                    # This is the same type of component as the component being
                    # replaced so use that component rather than creating a new
                    # component
                    # I really wish I had written down _why_ this is done or if
                    # it's even important. It could have been an optimisation to
                    # save creating a new component but that seems unlikely as
                    # it will make effectively no difference.
                    # One thing that this behaviour means is the component that
                    # is checked for compatibility will have the options of the
                    # replaceComponent rather than default options for the
                    # component. However I can't think why that would be
                    # required.
                    component = replaceComponent
                else:
                    # Create a new component for the compatibility check
                    component = componentType()
                    assert(isinstance(component, construction.ComponentInterface))

                # Check if the component is compatible with the context in its
                # current state. Note that the sequence will be None for common
                # components. The fact they're common means their compatibility
                # shouldn't be determined by the state of a specific sequence
                if component.isCompatible(
                        sequence=stage.sequence(),
                        context=self):
                    if component != replaceComponent:
                        # Initialise options to default values for this context
                        # so that the components returned by the function are
                        # ready to use.
                        # Note that this MUST be done AFTER compatibility is
                        # checked as updateOption implementations are allowed to
                        # make assumptions that they will only be called if the
                        # component is compatible.
                        component.updateOptions(
                            sequence=stage.sequence(),
                            context=self)

                    compatible.append(component)
        finally:
            if restoreIndex >= 0:
                stage.insertComponent(
                    index=restoreIndex,
                    component=replaceComponent)
                # Regenerate the entire context to get it back to a good state
                self.regenerate()

        return compatible

    def hasComponent(
            self,
            componentType: typing.Type[construction.ComponentInterface],
            sequence: typing.Optional[str] = None
            ) -> bool:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.hasComponent(componentType=componentType)

        for sequenceState in self._sequenceStates.values():
            if sequenceState.hasComponent(componentType=componentType):
                return True
        return False
    
    def hasAttribute(
            self,
            attributeId: construction.ConstructionAttributeId,
            sequence: str
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.hasAttribute(attributeId=attributeId)    
    
    def attribute(
            self,
            attributeId: construction.ConstructionAttributeId,
            sequence: str
            ) -> typing.Optional[construction.AttributeInterface]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.attribute(attributeId=attributeId)    

    def attributeValue(
            self,
            attributeId: construction.ConstructionAttributeId,
            sequence: str
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.attributeValue(attributeId=attributeId)
    
    # NOTE: A skill is only classed as having a speciality if it has the
    # speciality at level 1 or higher    
    def hasSkill(
            self,
            skillDef: traveller.SkillDefinition,
            sequence: str,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.hasSkill(
            skillDef=skillDef,
            speciality=speciality)
    
    def skill(
            self,
            skillDef: traveller.SkillDefinition,
            sequence: str
            ) -> typing.Optional[construction.TrainedSkill]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.skill(skillDef=skillDef)
    
    def skillLevel(
            self,
            skillDef: traveller.SkillDefinition,
            sequence: str,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.hasAttribute(
            skillDef=skillDef,
            speciality=speciality)

    def applyStep(
            self,
            sequence: str,
            step: construction.ConstructionStep
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        sequenceState.applyStep(
            component=self._activeComponent,
            phase=self._activeStage.phase(),
            step=step)

    def _resetConstruction(self) -> None:
        self._isIncomplete = False
        for state in self._sequenceStates.values():
            state.resetConstruction()

    def _loadComponentOptions(
            self,
            stage: construction.ConstructionStage,
            component: construction.ComponentInterface,
            # NOTE: Options that are successfully set will be removed from
            # optionData
            optionData: typing.Dict[str, typing.Any]
            ) -> None:
        # This code is more complicated than you might expect as it has to cope
        # with the fact setting one option may change what other options are
        # available. It makes multiple passes at setting the options. At each
        # pass it retrieves the current list of options from the component and
        # sets any that still need to be set. This process repeats until there
        # are no more options needing set _OR_ we have a pass where none of the
        # remaining options were set (the later avoids an infinite loop if there
        # is an invalid option)        
        while optionData:
            component.updateOptions(
                sequence=stage.sequence(),
                context=self)

            componentOptions = {}
            for option in component.options():
                componentOptions[option.id()] = option

            optionFound = False
            # NOTE: Copy keys so found entries can be removed while iterating
            for optionId in list(optionData.keys()):
                option = componentOptions.get(optionId)
                if not option:
                    continue
                optionValue = optionData[optionId]

                # NOTE: The option setValue functions will throw if the value is
                # invalid
                try:
                    if isinstance(option, construction.BooleanOption):
                        option.setValue(value=optionValue)
                    elif isinstance(option, construction.StringOption):
                        option.setValue(value=optionValue)
                    elif isinstance(option, construction.IntegerOption):
                        option.setValue(value=optionValue)
                    elif isinstance(option, construction.FloatOption):
                        option.setValue(value=optionValue)
                    elif isinstance(option, construction.MultiSelectOption):
                        option.setValue(value=optionValue)
                    elif isinstance(option, construction.EnumOption):
                        enumValue = None
                        if optionValue != None:
                            enumType = option.type()
                            enumValue = enumType.__members__.get(optionValue)
                            if not enumValue:
                                raise RuntimeError(f'Option {option.id()} for component type {type(component).__name__} has unknown value "{optionValue}"')
                        elif not option.isOptional():
                            raise RuntimeError(f'Option {option.id()} for component type {type(component).__name__} must have a value')

                        option.setValue(value=enumValue)
                except Exception:
                    # The option couldn't be set to the value. This may be
                    # because it's invalid or it might be the components options
                    # need updated for it to be valid. Don't remove the option
                    # from the ones still to be set so it will be tried again next
                    # time round the main loop
                    continue

                # The option has been set so remove it from the pending options
                # and record the fact we've found at least one option this time
                # round the loop
                del optionData[optionId]
                optionFound = True

            if not optionFound:
                # No pending options are found so no reason to think another
                # iteration will cause any more to be applied
                break 

    def _modifyStage(
            self,
            stage: construction.ConstructionStage,
            regenerate: bool,
            removeComponent: typing.Optional[construction.ComponentInterface] = None,
            addComponent: typing.Optional[construction.ComponentInterface] = None
            ) -> None:
        sequenceState = None
        if stage.sequence():
            sequenceState = self._sequenceStates.get(stage.sequence())
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {stage.sequence()}')

        if removeComponent == addComponent:
            # No need to check compatibility when replacing a component with its
            # self, just regenerate the context if requested
            if regenerate:
                self.regenerate()
            return

        components = list(stage.components())

        removedIndex = None
        if removeComponent:
            if removeComponent in components:
                removedIndex = components.index(removeComponent)
                stage.removeComponent(component=removeComponent)
            else:
                # The component to be removed isn't in the list of components
                # for the stage. This can happen when the component has been
                # removed due to comparability but some external system (e.g.
                # the UI is holding onto the component). An example of where
                # this can be hit is if a robot has a Transceiver and a Drone
                # Interface and then the Transceiver is removed. As the Drone
                # interface requires the robot to have a Transceiver to be
                # compatible, if it is removed the Drone Interface will be
                # removed when the robot is next regenerated. This can cause
                # this situation to be hit when the UI widget that was for
                # the Drone Interface is updated to show whatever component
                # automatically replaces the Drone Interface (as it's part of
                # the Default Suite). The "correct" way to handle this would
                # be for the caller to be aware of what has happened and add
                # the component instead of doing a replace but that isn't
                # straight forward and it would run the risk of bugs if I
                # missed anywhere that needs updated. The safer option is to
                # just handle it here by doing an simple add instead of a
                # replace. The downside of this is it could mask legitimate
                # coding errors.
                removeComponent = None

        try:
            if addComponent and addComponent not in components:
                if not stage.matchesComponent(component=addComponent):
                    raise construction.CompatibilityException()
                
                # Check that the component to be added is compatible with the
                # context. This needs to be done after the component to be
                # removed has been removed in order to to allow for the case where
                # one component is replacing a different version of the same
                # component (e.g stealth replacing extreme stealth). Note that the
                # sequence will be None for common components. The fact they're
                # common means their compatibility shouldn't be determined by the
                # state of a specific sequence
                if not addComponent.isCompatible(
                        sequence=stage.sequence(),
                        context=self):
                    raise construction.CompatibilityException()

                if removedIndex == None:
                    if not stage.hasFreeCapacity(requiredCapacity=1):
                        # The stage doesn't have enough space for the new
                        # component. I don't think this is a case I'd really
                        # expect to see as it would require a stage that has
                        # a max number of components _and_ allowed the user to
                        # dynamically add the components. Even if such a
                        # component did exist the expectation is the UI would
                        # prevent the user adding more components than the stage
                        # allowed. Apart from a bug the only time I could see it
                        # happening is if the user has been monkeying with the
                        # data file on disk _or_ there has been a change in
                        # implementation between versions and the max number of
                        # components for a stage has been lowered.
                        # There is no nice answer to what to do in this case.
                        # For such a corner case I don't really want to have to
                        # go to the effort of handling it as an error. The other
                        # options are, don't add the new component or remove an
                        # existing component and add the new one. I've gone with
                        # the later as it seems slightly nicer if in the case
                        # there is a UI bug, it's somewhat consistent with the
                        # way changing one component can cause other components
                        # to be automatically removed due to compatibility. It's
                        # not obvious which component to remove, I went with
                        # the most recently added as it is probably less likely
                        # to affect compatibility of other components.
                        stage.removeComponentAt(
                            index=stage.componentCount() - 1)

                    stage.addComponent(addComponent)
                else:
                    # This assumes that because we've removed a component there
                    # must be free space
                    stage.insertComponent(removedIndex, addComponent)
        except:
            # Something wen't wrong adding the component so, if a component has
            # been removed, re-add it in its original position
            if removedIndex != None:
                stage.insertComponent(removedIndex, removeComponent)
            raise

        if regenerate:
            self.regenerate()

    def _regenerateStage(
            self,
            sequence: str,
            stage: construction.ConstructionStage,
            ) -> None:
        # Remove incompatible components from the stage. This may cause the
        # context to have no component selected
        self._removeIncompatibleComponents(
            sequence=sequence,
            stage=stage)

        if self._isIncomplete:
            # The context is incomplete so don't create steps
            return

        # Add/remove components if the stage requires it
        self._enforceStageLimits(sequence=sequence, stage=stage)

        # Create steps for the stage
        self._createSteps(sequence=sequence, stage=stage)            

    def _removeIncompatibleComponents(
            self,
            sequence: str,
            stage: construction.ConstructionStage
            ) -> None:
        originalComponents = list(stage.components())

        try:
            for component in originalComponents:
                # Remove the component from the stage in order to perform the
                # compatibility check. This is required to prevent the component
                # causing its self to be reported as incompatible.
                # NOTE: This code should take care that, after the  operation
                # has completed, any components that weren't removed are still
                # in the same relative order
                stage.removeComponent(component=component)

                # Check if the component is compatible with the context in its
                # current state. Note that the sequence will be None for common
                # components. The fact they're common means their compatibility
                # shouldn't be determined by the state of a specific sequence
                if not component.isCompatible(
                        sequence=sequence,
                        context=self):
                    # The component isn't compatible so remove it, or more
                    # accurately, don't add it back to the stage
                    continue

                # The basic component is compatible but the options might
                # not be, update them to reset any that are incompatible.
                # Note that the sequence will be None for common components.
                # The fact they're common means their options shouldn't be
                # dependant on the state of a specific sequence
                component.updateOptions(
                    sequence=sequence,
                    context=self)

                # Add the component back onto the stage. No need to check
                # the stage max size as we know it has the capacity
                stage.addComponent(component=component)
        except:
            # Something went wrong so just restore previous state
            stage.setComponents(components=originalComponents)
            raise

    def _enforceStageLimits(
            self,
            sequence: str,
            stage: construction.ConstructionStage,
            ) -> None:
        # Create default components if current stage component count is to low
        minComponents = stage.minComponents()
        if stage.requirement() == construction.ConstructionStage.RequirementLevel.Desirable:
            # If the stage is desirable then it should contain the max number of
            # components if there are any compatible
            if self.findCompatibleComponents(stage=stage):
                minComponents = stage.maxComponents()

        if minComponents != None:
            while stage.componentCount() < minComponents:
                defaultComponent = stage.defaultComponent()
                if defaultComponent and not defaultComponent.isCompatible(
                        sequence=sequence,
                        context=self):
                    # The default component for this stage isn't compatible
                    # with the the current context setup so it can't be used
                    defaultComponent = None

                if not defaultComponent:
                    # Try to find any compatible components. This MUST be called each
                    # time we try to add a component as adding previous components may
                    # have changed the compatible components
                    compatible = self.findCompatibleComponents(stage=stage)
                    if not compatible:
                        # There were no compatible components found. If the
                        # stage is mandatory then it means the context is
                        # incomplete. If the stage is was only desirable
                        # then no selection is ok if there is nothing to
                        # select from.
                        if stage.requirement() == construction.ConstructionStage.RequirementLevel.Mandatory:
                            self._isIncomplete = True
                        return
                    # Select the first compatible component
                    defaultComponent = compatible[0]

                self.addComponent(
                    stage=stage,
                    component=defaultComponent,
                    regenerate=False)
            
        # Remove components if current stage component count is to high
        maxComponents = stage.maxComponents()
        if maxComponents != None:
            while stage.componentCount() > maxComponents:
                stage.removeComponentAt(index=-1)

    def _createSteps(
            self,
            sequence: str,
            stage: construction.ConstructionStage,
            component: typing.Optional[construction.ComponentInterface] = None
            ) -> None:
        try:
            self._activeStage = stage

            if component:
                self._activeComponent = component
                self._activeComponent.createSteps(sequence=sequence, context=self)
            else:
                components = stage.components(dependencyOrder=True)
                for self._activeComponent in components:
                    self._activeComponent.createSteps(sequence=sequence, context=self)
        finally:
            self._activeStage = None
            self._activeComponent = None
