import common
import enum
import construction
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

        # It's important that, when returning stages for multiple phases, they're returned in
        # construction order. Due to the way stages are added to _stageMap its values probably
        # won't naturally be in the correct order. Doing this makes processing of the stages
        # much simpler for consumers
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

            # Update mapping of component types to stages with the stages that handle components of those
            # types or components derived from those types. The later part is important as the
            # mapping should contain entries for things like AccessoryInterface that map to all stages
            # that deal with classes derived from AccessoryInterface even though those stages only
            # match classes derived from that type. This is why the subclass check is performed in both
            # directions rather than just checking that the stage matches the component type.
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

        # Apply attribute factors to attribute group
        for factor in step.factors():
            if not isinstance(factor, construction.AttributeFactor):
                continue
            factor.applyTo(attributeGroup=self._attributes)

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
            component = self._stepComponents.get(step, [])
            return [component] if component else []

        # When returning components for multiple phases, return them in construction order
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

    def attribute(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> construction.AttributeInterface:
        return self._attributes.attribute(attributeId=attributeId)

    def attributeValue(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        return self._attributes.attributeValue(attributeId=attributeId)

    def hasAttribute(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> bool:
        return self._attributes.hasAttribute(attributeId=attributeId)

    def constructionNotes(
            self,
            component: construction.ComponentInterface = None,
            phase: construction.ConstructionPhase = None
            ) -> typing.Iterable[str]:
        notes = []

        if component:
            steps = self._componentSteps.get(component)
            if steps:
                for step in steps:
                    notes.extend(step.notes())
        else:
            # Return notes in construction order if a specific phase isn't specified
            phases = self._phasesType if not phase else [phase]
            for phase in phases:
                steps = self._phaseSteps.get(phase)
                if steps:
                    for step in steps:
                        notes.extend(step.notes())

        return notes

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

        # When searching for components return them in construction order. This is done for
        # consistency with how stages are returned
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
            if stage.components():
                stage.clearComponents()
                modified = True

        # If regenerate is specified always regenerate even if nothing was modified
        if regenerate:
            self.regenerate()

        return modified

    def createSteps(
            self,
            sequence: str,
            stage: construction.ConstructionStage
            ) -> None:
        self._activeStage = stage
        components = stage.components()
        for self._activeComponent in components:
            self._activeComponent.createSteps(sequence=sequence, context=self)
        self._activeStage = None
        self._activeComponent = None

    def regenerate(
            self,
            stopStage: typing.Optional[construction.ConstructionStage] = None
            ) -> None:
        self._resetConstruction()

        for phase in self._phasesType:
            if self._regeneratePhase(
                    phase=phase,
                    stopStage=stopStage):
                break

    def constructionNotes(
            self,
            sequence: str,
            component: construction.ComponentInterface = None,
            phase: construction.ConstructionPhase = None
            ) -> typing.Iterable[str]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.constructionNotes(component=component, phase=phase)

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

    # The replaceComponent parameter can be used to get the list of components that would be
    # compatible if the specified component was being replaced. If the replaceComponent is
    # compatible with the weapon (which generally it always should be) then it will be included
    # in the returned list of components
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
            # In order to ignore a component it needs to be temporarily removed from the stage.
            # When components are checking for the presence of a component it will result in a
            # call back to the stage to check what components it contains. By removing the
            # component from the list these checks won't see it.
            restoreIndex = stage.removeComponent(replaceComponent)

        try:
            if restoreIndex >= 0:
                # Regenerate the weapon up to this stage. This is VERY important as we need to
                # regenerate attributes to the value the are when this stage is applied. When doing
                # this it means this functor must fully regenerate the weapon once compatibility has
                # been checked
                self.regenerate(stopStage=stage)

            componentTypes = common.getSubclasses(
                classType=stage.baseType(),
                topLevelOnly=True)

            compatible = []
            for componentType in componentTypes:
                if replaceComponent and componentType == type(replaceComponent):
                    # This is the same type of component as the component being replaced so use
                    # that component rather than creating a new component
                    component = replaceComponent
                else:
                    # Create a new component for the compatibility check
                    component = componentType()
                    assert(isinstance(component, construction.ComponentInterface))

                    # Initialise options to default values for the weapon. Note that the sequence
                    # will be None for common components. The fact they're common means their
                    # options shouldn't be dependant on the state of a specific sequence
                    component.updateOptions(
                        sequence=stage.sequence(),
                        context=self)

                # Check if the component is compatible with the weapon in its current state. Note
                # that the sequence will be None for common components. The fact they're common
                # means their compatibility shouldn't be determined by the state of a specific
                # sequence
                if component.isCompatible(
                        sequence=stage.sequence(),
                        context=self):
                    compatible.append(component)
        finally:
            if restoreIndex >= 0:
                stage.insertComponent(
                    index=restoreIndex,
                    component=replaceComponent)
                self.regenerate() # Regenerate the entire weapon to get it back to a good state

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

    def attributeValue(
            self,
            attributeId: construction.ConstructionAttributeId,
            sequence: str
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.attributeValue(attributeId=attributeId)

    def hasAttribute(
            self,
            attributeId: construction.ConstructionAttributeId,
            sequence: str
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.hasAttribute(attributeId=attributeId)

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

    def _regeneratePhase(
            self,
            phase: construction.ConstructionPhase,
            stopStage: typing.Optional[construction.ConstructionStage] = None
            ) -> bool:  # True if stop stage was hit
        for sequence, sequenceState in self._sequenceStates.items():
            for stage in sequenceState.stages(phase=phase):
                if stage == stopStage:
                    return True

                # Remove incompatible components from the stage. This may cause the weapon to have
                # no component selected
                self._removeIncompatibleComponents(stage=stage)

                if self._isIncomplete:
                    # The weapon is incomplete so don't continue applying components, however we do
                    # want to continue removing incompatible components from stages
                    continue

                # Get the list of components for the stage and make sure mandatory stages have a
                # component selected
                components = stage.components()
                if not components:
                    if stage.requirement() == construction.ConstructionStage.RequirementLevel.Optional:
                        # The stage is optional so the fact there are currently no components is
                        # completely valid, it does however mean there is nothing more to do for
                        # this stage
                        continue

                    defaultComponent = stage.defaultComponent()
                    if defaultComponent \
                        and not defaultComponent.isCompatible(
                            sequence=sequence,
                            context=self):
                        # The default component for this stage isn't compatible with the the current
                        # weapon setup so it can't be used
                        defaultComponent = None

                    if not defaultComponent:
                        # Try to find any compatible components
                        compatible = self.findCompatibleComponents(stage=stage)
                        if not compatible:
                            # There are no compatible components. If the stage is mandatory then it
                            # means the weapon is incomplete. If the stage is was only desirable
                            # then no selection is ok if there is nothing to select from. Either way
                            # there is no more processing required for this stage
                            if stage.requirement() == construction.ConstructionStage.RequirementLevel.Mandatory:
                                self._isIncomplete = True
                            continue
                        defaultComponent = compatible[0] # Select the first compatible component

                    self.addComponent(
                        stage=stage,
                        component=defaultComponent,
                        regenerate=False)

                # Create steps for the stage
                self.createSteps(
                    sequence=sequence,
                    stage=stage)

        return False # Stop stage wasn't hit

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
            # No need to check compatibility when replacing a component with its self
            # just regenerate the weapon if requested
            if regenerate:
                self.regenerate()
            return

        components = list(stage.components())

        removedIndex = None
        if removeComponent:
            if removeComponent not in components:
                assert(False)
                return
            removedIndex = components.index(removeComponent)
            stage.removeComponent(component=removeComponent)

        if addComponent and addComponent not in components:
            if not stage.matchesComponent(component=addComponent):
                raise construction.CompatibilityException()

            # Check that the component to be added is compatible with the weapon. This needs to be
            # done after the component to be removed has been removed to allow for the case where
            # one component is replacing a different version of the same component (e.g stealth
            # replacing extreme stealth). Note that the sequence will be None for common components.
            # The fact they're common means their compatibility shouldn't be determined by the
            # state of a specific sequence
            if not addComponent.isCompatible(
                    sequence=stage.sequence(),
                    context=self):
                raise construction.CompatibilityException()

            if removedIndex == None:
                stage.addComponent(addComponent)
            else:
                stage.insertComponent(removedIndex, addComponent)

        if regenerate:
            self.regenerate()

    def _removeIncompatibleComponents(
            self,
            stage: construction.ConstructionStage
            ) -> None:
        sequenceState = None
        if stage.sequence():
            sequenceState = self._sequenceStates.get(stage.sequence())
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {stage.sequence()}')

        originalComponents = list(stage.components())

        try:
            for component in originalComponents:
                # Remove the component from the stage in order to perform the compatibility check.
                # This is required to prevent the component causing its self to be reported as
                # incompatible. The code that does this should take care that after the operation
                # has completed, any components that weren't removed are still in the same relative
                # order
                stage.removeComponent(component=component)

                # Check if the component is compatible with the weapon in its current state. Note
                # that the sequence will be None for common components. The fact they're common
                # means their compatibility shouldn't be determined by the state of a specific
                # sequence
                if component.isCompatible(
                        sequence=stage.sequence(),
                        context=self):
                    # The basic component is compatible but the current options may not be, update
                    # them to reset any that are incompatible. Note that the sequence will be None
                    # for common components. The fact they're common means their options shouldn't
                    # be dependant on the state of a specific sequence
                    component.updateOptions(
                        sequence=stage.sequence(),
                        context=self)

                    # Add the component back onto the stage
                    stage.addComponent(component=component)
        except:
            # Something went wrong so just restore previous state
            stage.setComponents(components=originalComponents)
            raise
