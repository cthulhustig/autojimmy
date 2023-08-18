import common
import enum
import gunsmith
import typing
import uuid

class CompatibilityException(Exception):
    pass

class _SequenceState(object):
    def __init__(
            self,
            weaponType: gunsmith.WeaponType,
            isPrimary: bool,
            stages: typing.Optional[typing.Iterable[gunsmith.ConstructionStage]]
            ) -> None:
        self._weaponType = weaponType
        self._isPrimary = isPrimary
        self._phaseStages: typing.Dict[gunsmith.ConstructionPhase, typing.List[gunsmith.ConstructionStage]] = {}
        self._componentTypeStages: typing.Dict[typing.Type[gunsmith.ComponentInterface], typing.List[gunsmith.ConstructionStage]] = {}
        self._attributes = gunsmith.AttributesGroup()
        self._phaseSteps: typing.Dict[gunsmith.ConstructionPhase, typing.List[gunsmith.ConstructionStep]] = {}
        self._stepComponents: typing.Dict[gunsmith.ConstructionStep, gunsmith.ComponentInterface] = {}
        self._componentSteps: typing.Dict[gunsmith.ComponentInterface, typing.List[gunsmith.ConstructionStep]] = {}
        if stages:
            self.setStages(stages=stages)

    def weaponType(self) -> gunsmith.WeaponType:
        return self._weaponType

    def setWeaponType(
            self,
            weaponType: gunsmith.WeaponType,
            stages: typing.Iterable[gunsmith.ConstructionStage]
            ) -> None:
        self._weaponType = weaponType
        self.setStages(stages=stages)

    def isPrimary(self) -> bool:
        return self._isPrimary

    def setPrimary(self, primary: bool) -> None:
        self._isPrimary = primary

    def stages(
            self,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None,
            componentType: typing.Optional[typing.Type[gunsmith.ComponentInterface]] = None
            ) -> typing.Collection[gunsmith.ConstructionStage]:
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
        for phase in gunsmith.ConstructionPhase:
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
            stages: typing.Iterable[gunsmith.ConstructionStage]
            ) -> None:
        self._phaseStages.clear()
        self._componentTypeStages.clear()

        componentTypes = common.getSubclasses(
            classType=gunsmith.ComponentInterface,
            topLevelOnly=False)

        for stage in stages:
            phaseStages = self._phaseStages.get(stage.phase())
            if not phaseStages:
                self._phaseStages[stage.phase()] = [stage]
            else:
                phaseStages.append(stage)

            # Update mapping of component types to stages the stages that handle components of those
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
            phase: gunsmith.ConstructionPhase,
            component: gunsmith.ComponentInterface,
            step: gunsmith.ConstructionStep
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
            if not isinstance(factor, gunsmith.AttributeFactor):
                continue
            factor.applyTo(attributeGroup=self._attributes)

    def steps(
            self,
            component: typing.Optional[gunsmith.ComponentInterface] = None,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None
            ) -> typing.Collection[gunsmith.ConstructionStep]:
        if component:
            return self._componentSteps.get(component, [])

        # Return all steps in construction order
        phaseList = gunsmith.ConstructionPhase if not phase else [phase]
        steps = []
        for phase in phaseList:
            phaseSteps = self._phaseSteps.get(phase)
            if phaseSteps:
                steps.extend(phaseSteps)
        return steps

    def components(
            self,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None,
            step: typing.Optional[gunsmith.ConstructionStep] = None
            ) -> typing.Collection[gunsmith.ComponentInterface]:
        if step:
            component = self._stepComponents.get(step, [])
            return [component] if component else []

        # When returning components for multiple phases, return them in construction order
        phaseList = gunsmith.ConstructionPhase if not phase else [phase]
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
            componentType: typing.Type[gunsmith.ComponentInterface]
            ) -> typing.Optional[gunsmith.ComponentInterface]:
        components = self._componentSearch(
            componentType=componentType,
            stopOnFirst=True)
        if not components:
            return None
        return components[0]

    def findComponents(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface]
            ) -> typing.Iterable[gunsmith.ComponentInterface]:
        return self._componentSearch(
            componentType=componentType,
            stopOnFirst=False)

    def hasComponent(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface]
            ) -> bool:
        return self.findFirstComponent(componentType=componentType) != None

    def attribute(
            self,
            attributeId: gunsmith.AttributeId
            ) -> gunsmith.AttributeInterface:
        return self._attributes.attribute(attributeId=attributeId)

    def attributeValue(
            self,
            attributeId: gunsmith.AttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        return self._attributes.attributeValue(attributeId=attributeId)

    def hasAttribute(
            self,
            attributeId: gunsmith.AttributeId
            ) -> bool:
        return self._attributes.hasAttribute(attributeId=attributeId)

    def constructionNotes(
            self,
            component: gunsmith.ComponentInterface = None,
            phase: gunsmith.ConstructionPhase = None
            ) -> typing.Iterable[str]:
        notes = []

        if component:
            steps = self._componentSteps.get(component)
            if steps:
                for step in steps:
                    notes.extend(step.notes())
        else:
            # Return notes in construction order if a specific phase isn't specified
            phases = gunsmith.ConstructionPhase if not phase else [phase]
            for phase in phases:
                steps = self._phaseSteps.get(phase)
                if steps:
                    for step in steps:
                        notes.extend(step.notes())

        return notes

    def phaseCost(
            self,
            phase: gunsmith.ConstructionPhase
            ) -> common.ScalarCalculation:
        steps = self._phaseSteps.get(phase)
        if not steps:
            return common.ScalarCalculation(
                value=0,
                name=f'Total {phase.value} Cost')

        cost = gunsmith.ConstructionStep.calculateSequenceCost(steps=steps)
        if not cost:
            raise RuntimeError(
                f'Unable to calculate cost for phase {phase.value} as starting modifier is not absolute')
        return common.Calculator.rename(
            value=cost,
            name=f'Total {phase.value} Cost')

    def phaseWeight(
            self,
            phase: gunsmith.ConstructionPhase
            ) -> common.ScalarCalculation:
        steps = self._phaseSteps.get(phase)
        if not steps:
            return common.ScalarCalculation(
                value=0,
                name=f'Total {phase.value} Weight')

        weight = gunsmith.ConstructionStep.calculateSequenceWeight(steps=steps)
        if not weight:
            raise RuntimeError(
                f'Unable to calculate weight for phase {phase.value} as starting modifier is not absolute')
        return common.Calculator.rename(
            value=weight,
            name=f'Total {phase.value} Weight')

    def resetConstruction(self) -> None:
        self._attributes.clear()
        self._phaseSteps.clear()
        self._stepComponents.clear()
        self._componentSteps.clear()

    def _componentSearch(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface],
            stopOnFirst: bool
            ) -> typing.Iterable[gunsmith.ComponentInterface]:
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

class _ConstructionContext(gunsmith.ConstructionContextInterface):
    def __init__(
            self,
            techLevel: int,
            rules: typing.Optional[typing.Iterable[gunsmith.RuleId]] = None
            ) -> None:
        super().__init__()
        self._techLevel = techLevel
        self._rules = set(rules) if rules else set()
        self._sequenceStates: typing.Dict[str, _SequenceState] = {}
        self._activeStage = None
        self._activeComponent = None

    def rules(self) -> typing.Collection[gunsmith.RuleId]:
        return self._rules

    def setRules(self, rules: typing.Iterable[gunsmith.RuleId]):
        self._rules.clear()
        for rule in rules:
            self._rules.add(rule)

    def enableRule(self, rule: gunsmith.RuleId) -> None:
        self._rules.add(rule)

    def disableRule(self, rule: gunsmith.RuleId) -> None:
        if rule in self._rules:
            self._rules.remove(rule)

    def clearRules(self) -> None:
        self._rules.clear()

    def addSequence(
            self,
            sequence: str,
            sequenceState: _SequenceState
            ) -> None:
        self._sequenceStates[sequence] = sequenceState

    def removeSequence(
            self,
            sequence: str
            ) -> None:
        del self._sequenceStates[sequence]

    def clearSequences(self) -> None:
        self._activeSequence = None
        self._sequenceStates.clear()

    def setTechLevel(
            self,
            techLevel: int
            ) -> None:
        self._techLevel = techLevel

    def createSteps(
            self,
            sequence: str,
            stage: gunsmith.ConstructionStage
            ) -> None:
        self._activeStage = stage
        components = stage.components()
        for self._activeComponent in components:
            self._activeComponent.createSteps(sequence=sequence, context=self)
        self._activeStage = None
        self._activeComponent = None

    def combatWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.CombatReadyConstructionPhases,
            calculationName='Total Combat Weight',
            sequence=sequence)

    def combatCost(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCost(
            phases=gunsmith.CombatReadyConstructionPhases,
            calculationName='Total Combat Cost',
            sequence=sequence)

    #
    # gunsmith.ConstructionContextInterface implementation
    #
    def isRuleEnabled(self, rule: gunsmith.RuleId):
        return rule in self._rules

    def techLevel(self) -> int:
        return self._techLevel

    def weaponType(
            self,
            sequence: str
            ) -> gunsmith.WeaponType:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.weaponType()

    def isPrimary(
            self,
            sequence: str
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.isPrimary()

    def findFirstComponent(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface],
            sequence: typing.Optional[str]
            ) -> typing.Optional[gunsmith.ComponentInterface]:
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
            componentType: typing.Type[gunsmith.ComponentInterface],
            sequence: typing.Optional[str]
            ) -> typing.Iterable[gunsmith.ComponentInterface]:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.findComponents(componentType=componentType)

        matched = []
        for sequenceState in self._sequenceStates.values():
            matched.extend(sequenceState.findComponents(componentType=componentType))
        return matched

    def hasComponent(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface],
            sequence: typing.Optional[str]
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
            attributeId: gunsmith.AttributeId,
            sequence: str
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.attributeValue(attributeId=attributeId)

    def hasAttribute(
            self,
            attributeId: gunsmith.AttributeId,
            sequence: str
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.hasAttribute(attributeId=attributeId)

    def phaseWeight(
            self,
            phase: gunsmith.ConstructionPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseWeight(phase=phase)

        if (phase in gunsmith.CommonConstructionPhases) or (len(self._sequenceStates) == 1):
            # This is a common phase or there is only one sequence. In the case of a common phase
            # the value should only be included once rather than for each sequence. The assumption
            # is the weight for common stages should be the same for all sequences so it doesn't
            # matter which it's pulled from.
            if not self._sequenceStates:
                return common.ScalarCalculation(
                    value=0,
                    name=f'Total {phase.value} Weight')
            sequenceState = next(iter(self._sequenceStates.values()))
            return sequenceState.phaseWeight(phase=phase)

        # Add the phase weight for each stage
        weights = []
        for sequenceState in self._sequenceStates.values():
            weights.append(sequenceState.phaseWeight(phase=phase))
        return common.Calculator.sum(
            values=weights,
            name=f'Total {phase.value} Weight')

    def phaseCost(
            self,
            phase: gunsmith.ConstructionPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseCost(phase=phase)

        if (phase in gunsmith.CommonConstructionPhases) or (len(self._sequenceStates) == 1):
            # This is a common phase or there is only one sequence. In the case of a common phase
            # the value should only be included once rather than for each sequence. The assumption
            # is the weight for common stages should be the same for all sequences so it doesn't
            # matter which it's pulled from.
            if not self._sequenceStates:
                return common.ScalarCalculation(
                    value=0,
                    name=f'Total {phase.value} Cost')
            sequenceState = next(iter(self._sequenceStates.values()))
            return sequenceState.phaseCost(phase=phase)

        # Add the phase weight for each stage
        costs = []
        for sequenceState in self._sequenceStates.values():
            costs.append(sequenceState.phaseCost(phase=phase))
        return common.Calculator.sum(
            values=costs,
            name=f'Total {phase.value} Cost')

    def receiverWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseWeight(phase=gunsmith.ConstructionPhase.Receiver)

        return self.phaseWeight(phase=gunsmith.ConstructionPhase.Receiver, sequence=None)

    def receiverCost(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseCost(phase=gunsmith.ConstructionPhase.Receiver)

        return self.phaseCost(phase=gunsmith.ConstructionPhase.Receiver, sequence=None)

    def baseWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.BaseWeaponConstructionPhases,
            calculationName='Total Base Weight',
            sequence=sequence)

    def baseCost(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCost(
            phases=gunsmith.BaseWeaponConstructionPhases,
            calculationName='Total Base Cost',
            sequence=sequence)

    def totalWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.ConstructionPhase,
            calculationName='Total Weight',
            sequence=sequence)

    def totalCost(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCost(
            phases=gunsmith.ConstructionPhase,
            calculationName='Total Cost',
            sequence=sequence)

    def applyStep(
            self,
            sequence: str,
            step: gunsmith.ConstructionStep
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        sequenceState.applyStep(
            component=self._activeComponent,
            phase=self._activeStage.phase(),
            step=step)

    def _multiPhaseWeight(
            self,
            phases: typing.Iterable[gunsmith.ConstructionPhase],
            calculationName: str,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        weights = []
        for phase in phases:
            weights.append(self.phaseWeight(
                phase=phase,
                sequence=sequence))
        return common.Calculator.sum(
            values=weights,
            name=calculationName)

    def _multiPhaseCost(
            self,
            phases: typing.Iterable[gunsmith.ConstructionPhase],
            calculationName: str,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        costs = []
        for phase in phases:
            costs.append(self.phaseCost(
                phase=phase,
                sequence=sequence))
        return common.Calculator.sum(
            values=costs,
            name=calculationName)

class Weapon(object):
    def __init__(
            self,
            weaponName: str,
            techLevel: int,
            rules: typing.Optional[typing.Iterable[gunsmith.RuleId]] = None,
            userNotes: typing.Optional[str] = None,
            weaponType: typing.Optional[gunsmith.WeaponType] = None, # Initial primary weapon type
            ) -> None:
        self._weaponName = weaponName
        self._techLevel = int(techLevel)
        self._userNotes = userNotes if userNotes else ''
        self._manifest = None

        self._commonStages = self._createCommonStages()
        self._sequenceStates: typing.Dict[str, _SequenceState] = {}
        self._constructionContext = _ConstructionContext(
            techLevel=self._techLevel,
            rules=rules)

        if weaponType:
            self.addSequence(
                weaponType=weaponType,
                regenerate=True) # Regenerate the weapon to initialise default components

    def weaponName(self) -> typing.Optional[str]:
        return self._weaponName

    def setWeaponName(
            self,
            name: typing.Optional[str]
            ) -> None:
        self._weaponName = name

    def techLevel(self) -> int:
        return self._techLevel

    def setTechLevel(
            self,
            techLevel: int,
            regenerate: bool = True
            ) -> None:
        self._techLevel = techLevel
        self._constructionContext.setTechLevel(techLevel=techLevel)

        if regenerate:
            self.regenerate()

    def rules(self) -> typing.Collection[gunsmith.RuleId]:
        return self._constructionContext.rules()

    def setRules(
            self,
            rules: typing.Iterable[gunsmith.RuleId],
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setRules(rules=rules)
        if regenerate:
            self.regenerate()

    def isRuleEnabled(self, rule: gunsmith.RuleId) -> bool:
        return self._constructionContext.isRuleEnabled(rule=rule)

    def enableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.enableRule(rule=rule)
        if regenerate:
            self.regenerate()

    def disableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.disableRule(rule=rule)
        if regenerate:
            self.regenerate()

    def clearRules(self, regenerate: bool = True) -> None:
        self._constructionContext.clearRules()
        if regenerate:
            self.regenerate()

    def userNotes(self) -> str:
        return self._userNotes

    def setUserNotes(self, notes: str) -> None:
        self._userNotes = notes

    def manifest(self) -> gunsmith.Manifest:
        if not self._manifest:
            # Generate manifest on demand
            self._manifest = self._createManifest()
        return self._manifest

    def addSequence(
            self,
            weaponType: gunsmith.WeaponType,
            regenerate: bool = True
            ) -> str:
        sequence = str(uuid.uuid4())
        sequenceState = _SequenceState(
            weaponType=weaponType,
            isPrimary=len(self._sequenceStates) == 0,
            stages=self._createSequenceStages(weaponType=weaponType, sequence=sequence))
        self._sequenceStates[sequence] = sequenceState
        self._constructionContext.addSequence(
            sequence=sequence,
            sequenceState=sequenceState)

        if regenerate:
            self.regenerate()
        return sequence

    def removeSequence(
            self,
            sequence: str,
            regenerate: bool = True
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        self._constructionContext.removeSequence(sequence=sequence)
        del self._sequenceStates[sequence]

        # If the primary sequence was deleted set the first remaining sequence
        # as the primary
        if sequenceState.isPrimary() and len(self._sequenceStates) > 0:
            self._sequenceStates[0].setPrimary(primary=True)

        if regenerate:
            self.regenerate()

    def clearSequences(self):
        self._sequenceStates.clear()
        self._constructionContext.clearSequences()

        # Remove components from common stages
        for stage in self._commonStages:
            stage.clearComponents()

        # Reset construction to clear stored state. No point regenerating as
        # there is nothing to regenerate
        self._resetConstruction()

    # The current assumption is the first sequence is the primary
    def sequences(self) -> typing.Collection[str]:
        return list(self._sequenceStates.keys())

    def sequenceCount(self) -> int:
        return len(self._sequenceStates)

    def weaponType(
            self,
            sequence: str
            ) -> gunsmith.WeaponType:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        return sequenceState.weaponType()

    def setWeaponType(
            self,
            sequence: str,
            weaponType: gunsmith.WeaponType,
            regenerate: bool = True
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        sequenceState.setWeaponType(
            weaponType=weaponType,
            stages=self._createSequenceStages(
                sequence=sequence,
                weaponType=weaponType))

        if regenerate:
            self.regenerate()

    def stages(
            self,
            sequence: typing.Optional[str] = None,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None,
            componentType: typing.Optional[typing.Type[gunsmith.ComponentInterface]] = None
            ) -> typing.Iterable[gunsmith.ConstructionStage]:
        if sequence != None:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')

            return sequenceState.stages(
                phase=phase,
                componentType=componentType)

        matched = []
        phaseList = gunsmith.ConstructionPhase if phase == None else [phase]
        for phase in phaseList:
            for sequenceState in self._sequenceStates.values():
                for stage in sequenceState.stages(phase=phase, componentType=componentType):
                    if stage not in matched: # Avoid duplicates for common stages
                        matched.append(stage)
        return matched

    def findComponents(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface],
            sequence: str = None,
            ) -> typing.Iterable[gunsmith.ComponentInterface]:
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

    def hasComponent(
            self,
            componentType: typing.Type[gunsmith.ComponentInterface],
            sequence: str = None
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

    # The replaceComponent parameter can be used to get the list of components that would be
    # compatible if the specified component was being replaced. If the replaceComponent is
    # compatible with the weapon (which generally it always should be) then it will be included
    # in the returned list of components
    def findCompatibleComponents(
            self,
            stage: gunsmith.ConstructionStage,
            replaceComponent: typing.Optional[gunsmith.ComponentInterface] = None
            ) -> typing.Iterable[gunsmith.ComponentInterface]:
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
                    assert(isinstance(component, gunsmith.ComponentInterface))

                    # Initialise options to default values for the weapon. Note that the sequence
                    # will be None for common components. The fact they're common means their
                    # options shouldn't be dependant on the state of a specific sequence
                    component.updateOptions(
                        sequence=stage.sequence(),
                        context=self._constructionContext)

                # Check if the component is compatible with the weapon in its current state. Note
                # that the sequence will be None for common components. The fact they're common
                # means their compatibility shouldn't be determined by the state of a specific
                # sequence
                if component.isCompatible(
                        sequence=stage.sequence(),
                        context=self._constructionContext):
                    compatible.append(component)
        finally:
            if restoreIndex >= 0:
                stage.insertComponent(
                    index=restoreIndex,
                    component=replaceComponent)
                self.regenerate() # Regenerate the entire weapon to get it back to a good state

        return compatible

    def addComponent(
            self,
            stage: gunsmith.ConstructionStage,
            component: gunsmith.ComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            addComponent=component,
            regenerate=regenerate)

    def removeComponent(
            self,
            stage: gunsmith.ConstructionStage,
            component: gunsmith.ComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            removeComponent=component,
            regenerate=regenerate)

    def replaceComponent(
            self,
            stage: gunsmith.ConstructionStage,
            oldComponent: typing.Optional[gunsmith.ComponentInterface],
            newComponent: typing.Optional[gunsmith.ComponentInterface],
            regenerate: bool = True
            ) -> None:
        self._modifyStage(
            stage=stage,
            removeComponent=oldComponent,
            addComponent=newComponent,
            regenerate=regenerate)

    def clearComponents(
            self,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None,
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

    def unloadWeapon(
            self,
            sequence: typing.Optional[str] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        return self.clearComponents(
            phase=gunsmith.ConstructionPhase.Loading,
            sequence=sequence,
            regenerate=regenerate)

    def setAccessorAttachment(
            self,
            attach: bool,
            sequence: typing.Optional[str] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        accessories = self.findComponents(
            sequence=sequence,
            componentType=gunsmith.AccessoryInterface)

        modified = False
        for accessory in accessories:
            assert(isinstance(accessory, gunsmith.AccessoryInterface))
            if not accessory.isDetachable():
                continue

            if attach != accessory.isAttached():
                accessory.setAttached(attached=attach)
                modified = True

        # If regenerate is specified always regenerate even if nothing was modified
        if regenerate:
            self.regenerate()

        return modified

    def regenerate(
            self,
            stopStage: typing.Optional[gunsmith.ConstructionStage] = None
            ) -> None:
        self._resetConstruction()

        for phase in gunsmith.ConstructionPhase:
            if self._regenerateStatePhase(
                    phase=phase,
                    stopStage=stopStage):
                break

    def hasAttribute(
            self,
            sequence: str,
            attributeId: gunsmith.AttributeId
            ) -> bool:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        return sequenceState.hasAttribute(attributeId=attributeId)

    def attribute(
            self,
            sequence: str,
            attributeId: gunsmith.AttributeId,
            ) -> typing.Optional[gunsmith.AttributeInterface]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')

        if (attributeId == gunsmith.AttributeId.Quickdraw) and (len(self._sequenceStates) > 1):
            return self._calculateQuickdrawScore()

        return sequenceState.attribute(attributeId=attributeId)

    def attributeValue(
            self,
            sequence: str,
            attributeId: gunsmith.AttributeId,
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        attribute = self.attribute(sequence=sequence, attributeId=attributeId)
        if not attribute:
            return None
        return attribute.value()

    def constructionNotes(
            self,
            sequence: str,
            component: gunsmith.ComponentInterface = None,
            phase: gunsmith.ConstructionPhase = None
            ) -> typing.Iterable[str]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.constructionNotes(component=component, phase=phase)

    def steps(
            self,
            sequence: str,
            component: typing.Optional[gunsmith.ComponentInterface] = None,
            phase: typing.Optional[gunsmith.ConstructionPhase] = None,
            ) -> typing.Collection[gunsmith.ConstructionStep]:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        return sequenceState.steps(component=component, phase=phase)

    # This returns the total weight of the specified phase for all weapon sequences
    def phaseWeight(
            self,
            phase: gunsmith.ConstructionPhase
            ) -> common.ScalarCalculation:
        return self._constructionContext.phaseWeight(phase=phase, sequence=None)

    # This returns the total cost of the specified phase for all weapon sequences
    def phaseCost(
            self,
            phase: gunsmith.ConstructionPhase
            ) -> common.ScalarCalculation:
        return self._constructionContext.phaseCost(phase=phase, sequence=None)

    def baseWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.baseWeight(sequence=None)

    def baseCost(self) -> common.ScalarCalculation:
        return self._constructionContext.baseCost(sequence=None)

    def combatWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.combatWeight(sequence=None)

    def combatCost(self) -> common.ScalarCalculation:
        return self._constructionContext.combatCost(sequence=None)

    def totalWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.totalWeight(sequence=None)

    def totalCost(self) -> common.ScalarCalculation:
        return self._constructionContext.totalCost(sequence=None)

    def _resetConstruction(self) -> None:
        self._isIncomplete = False
        for state in self._sequenceStates.values():
            state.resetConstruction()
        self._manifest = None

    def _regenerateStatePhase(
            self,
            phase: gunsmith.ConstructionPhase,
            stopStage: typing.Optional[gunsmith.ConstructionStage] = None
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
                    if stage.requirement() == gunsmith.ConstructionStage.RequirementLevel.Optional:
                        # The stage is optional so the fact there are currently no components is
                        # completely valid, it does however mean there is nothing more to do for
                        # this stage
                        continue

                    defaultComponent = stage.defaultComponent()
                    if defaultComponent \
                        and not defaultComponent.isCompatible(
                            sequence=sequence,
                            context=self._constructionContext):
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
                            if stage.requirement() == gunsmith.ConstructionStage.RequirementLevel.Mandatory:
                                self._isIncomplete = True
                            continue
                        defaultComponent = compatible[0] # Select the first compatible component

                    self.addComponent(
                        stage=stage,
                        component=defaultComponent,
                        regenerate=False)

                # Create steps for the stage
                self._constructionContext.createSteps(
                    sequence=sequence,
                    stage=stage)

        return False # Stop stage wasn't hit

    def _modifyStage(
            self,
            stage: gunsmith.ConstructionStage,
            regenerate: bool,
            removeComponent: typing.Optional[gunsmith.ComponentInterface] = None,
            addComponent: typing.Optional[gunsmith.ComponentInterface] = None
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
                raise gunsmith.CompatibilityException()

            # Check that the component to be added is compatible with the weapon. This needs to be
            # done after the component to be removed has been removed to allow for the case where
            # one component is replacing a different version of the same component (e.g stealth
            # replacing extreme stealth). Note that the sequence will be None for common components.
            # The fact they're common means their compatibility shouldn't be determined by the
            # state of a specific sequence
            if not addComponent.isCompatible(
                    sequence=stage.sequence(),
                    context=self._constructionContext):
                raise gunsmith.CompatibilityException()

            if removedIndex == None:
                stage.addComponent(addComponent)
            else:
                stage.insertComponent(removedIndex, addComponent)

        if regenerate:
            self.regenerate()

    def _removeIncompatibleComponents(
            self,
            stage: gunsmith.ConstructionStage
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
                        context=self._constructionContext):
                    # The basic component is compatible but the current options may not be, update
                    # them to reset any that are incompatible. Note that the sequence will be None
                    # for common components. The fact they're common means their options shouldn't
                    # be dependant on the state of a specific sequence
                    component.updateOptions(
                        sequence=stage.sequence(),
                        context=self._constructionContext)

                    # Add the component back onto the stage
                    stage.addComponent(component=component)
        except:
            # Something went wrong so just restore previous state
            stage.setComponents(components=originalComponents)
            raise

    def _createManifest(
            self
            ) -> gunsmith.Manifest:
        manifest = gunsmith.Manifest()

        for sequenceIndex, sequence in enumerate(self._sequenceStates.values()):
            for phase in gunsmith.SequenceConstructionPhases:
                sectionName = self._prefixManifestText(
                    sequenceIndex=sequenceIndex,
                    baseText=phase.value)

                manifestSection = None
                for component in sequence.components(phase=phase):
                    steps = sequence.steps(component=component)
                    if not steps:
                        continue
                    if not manifestSection:
                        manifestSection = manifest.createSection(name=sectionName)
                    for step in steps:
                        entryText = self._prefixManifestText(
                            sequenceIndex=sequenceIndex,
                            baseText=f'{step.type()}: {step.name()}')
                        manifestSection.createEntry(
                            component=entryText,
                            cost=step.cost(),
                            weight=step.weight(),
                            factors=step.factors())

        for phase in gunsmith.CommonConstructionPhases:
            componentMap: typing.Dict[gunsmith.ComponentInterface, typing.Dict[str, gunsmith.ConstructionStep]] = {}
            stepFactors: typing.Dict[gunsmith.ConstructionStep, typing.Dict[int, typing.List[gunsmith.FactorInterface]]] = {}
            for sequenceIndex, sequence in enumerate(self._sequenceStates.values()):
                for component in sequence.components(phase=phase):
                    steps = sequence.steps(component=component)
                    if not steps:
                        continue

                    stepNameMap = componentMap.get(component)
                    if not stepNameMap:
                        stepNameMap = {}
                        componentMap[component] = stepNameMap

                    for step in steps:
                        commonStep = stepNameMap.get(step.name())
                        if not commonStep:
                            commonStep = gunsmith.ConstructionStep(
                                name=step.name(),
                                type=step.type(),
                                cost=step.cost(),
                                weight=step.weight())
                            stepNameMap[step.name()] = commonStep
                            stepFactors[commonStep] = {}

                        sequenceFactors = stepFactors[commonStep]
                        sequenceFactors[sequenceIndex] = step.factors()

            # Add factors to step. This is done so that if a component adds the same factor to all
            # sequences then only a single factor will be added to the step. If factors are only
            # applied to some sequences or their values differ between sequences then factors are
            # prefixed to make it clear which sequence they apply to
            for step, sequenceFactors in stepFactors.items():
                factorTextCollisions: typing.Dict[str, typing.Dict[int, gunsmith.FactorInterface]] = {}
                for sequenceIndex, factorList in sequenceFactors.items():
                    for factor in factorList:
                        factorText = factor.displayString()
                        factorMap = factorTextCollisions.get(factorText)
                        if not factorMap:
                            factorMap = {}
                            factorTextCollisions[factorText] = factorMap
                        assert(sequenceIndex not in factorMap)
                        factorMap[sequenceIndex] = factor

                for factorMap in factorTextCollisions.values():
                    if not factorMap:
                        continue

                    if len(factorMap) == self.sequenceCount():
                        # The factor text is the same for all sequences so just add the factor from one
                        # of the sequences to the step as-is
                        step.addFactor(factor=factorMap[0])
                    else:
                        # This factor text is only for some weapon sequences so add a prefixed factor
                        # for each of the sequence it applies to
                        for sequenceIndex, factor in factorMap.items():
                            stepPrefix = self._prefixManifestText(
                                sequenceIndex=sequenceIndex,
                                baseText='') # Empty string to just generate the prefix
                            step.addFactor(gunsmith.NonModifyingFactor(
                                factor=factor,
                                prefix=stepPrefix))

            manifestSection = manifest.createSection(name=phase.value)
            for stepMap in componentMap.values():
                for step in stepMap.values():
                    manifestSection.createEntry(
                        component=f'{step.type()}: {step.name()}',
                        cost=step.cost(),
                        weight=step.weight(),
                        factors=step.factors())

        for phase in gunsmith.AncillaryConstructionPhases:
            for sequenceIndex, sequence in enumerate(self._sequenceStates.values()):
                sectionName = self._prefixManifestText(
                    sequenceIndex=sequenceIndex,
                    baseText=phase.value)

                manifestSection = None
                for component in sequence.components(phase=phase):
                    steps = sequence.steps(component=component)
                    if not steps:
                        continue

                    if not manifestSection:
                        manifestSection = manifest.createSection(name=sectionName)
                    for step in steps:
                        entryText = self._prefixManifestText(
                            sequenceIndex=sequenceIndex,
                            baseText=f'{step.type()}: {step.name()}')
                        manifestSection.createEntry(
                            component=entryText,
                            cost=step.cost(),
                            weight=step.weight(),
                            factors=step.factors())

        return manifest

    def _prefixManifestText(
            self,
            sequenceIndex: int,
            baseText: str
            ) -> None:
        sequenceCount = self.sequenceCount()
        if sequenceCount == 1:
            sectionName = baseText
        elif sequenceIndex == 0:
            sectionName = 'Primary ' + baseText
        elif sequenceCount == 2:
            sectionName = 'Secondary ' + baseText
        else:
            sectionName = f'Secondary {sequenceIndex} ' + baseText
        return sectionName

    def _calculateQuickdrawScore(self) -> gunsmith.NumericAttribute:
        scores = []
        for sequenceState in self._sequenceStates.values():
            attribute = sequenceState.attribute(attributeId=gunsmith.AttributeId.Quickdraw)
            if isinstance(attribute, gunsmith.NumericAttribute):
                scores.append(attribute.value())
        return gunsmith.NumericAttribute(
            attributeId=gunsmith.AttributeId.Quickdraw,
            value=common.Calculator.sum(
                values=scores,
                name='Total Quickdraw Score'))

    def _createCommonStages(
            self
            ) -> typing.List[gunsmith.ConstructionStage]:
        stages = []

        stages.extend(self._createInitialisationStages())
        stages.extend(self._createStockStages())
        stages.extend(self._createWeaponFeatureStages())
        stages.extend(self._createWeaponAccessoriesStages())
        stages.extend(self._createMultiMountStages())
        stages.extend(self._createFinalisationStages())

        return stages

    def _createSequenceStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.List[gunsmith.ConstructionStage]:
        stages = []

        # Add common stages
        stages.extend(self._commonStages)

        # Add firing sequence specific stages
        stages.extend(self._createReceiverStages(
            weaponType=weaponType,
            sequence=sequence))
        stages.extend(self._createBarrelStages(
            weaponType=weaponType,
            sequence=sequence))
        stages.extend(self._createMountingStages(
            weaponType=weaponType,
            sequence=sequence))
        stages.extend(self._createLoadingStages(
            weaponType=weaponType,
            sequence=sequence))
        stages.extend(self._createMunitionsStages(
            weaponType=weaponType,
            sequence=sequence))

        return stages

    def _createInitialisationStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Initialisation',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.Initialisation,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            singular=True,
            baseType=gunsmith.InitialisationComponent,
            defaultType=gunsmith.InitialisationComponent)]

    def _createReceiverStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> None:
        stages = []

        stages.append(gunsmith.ConstructionStage(
            name='Receiver',
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Receiver,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            singular=True,
            baseType=gunsmith.ReceiverInterface))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Calibre',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
                singular=True,
                baseType=gunsmith.CalibreInterface))

        if weaponType != gunsmith.WeaponType.ProjectorWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Multi-Barrel',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.MultiBarrelInterface))

            stages.append(gunsmith.ConstructionStage(
                name='Mechanism',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
                singular=True,
                baseType=gunsmith.MechanismInterface))
        else:
            # Having Propellant before Structure Feature is important as, in the case of
            # generated gas, there is a fixed receiver cost modification so you'll get different
            # results depending on if it's applied before or after any multiplier cost
            # modifications. The examples (Field Catalogue 111-113) have it in this order so i've
            # gone with that
            stages.append(gunsmith.ConstructionStage(
                name='Propellant',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
                singular=True,
                baseType=gunsmith.PropellantTypeInterface))

        stages.append(gunsmith.ConstructionStage(
            name='Receiver Features',
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Receiver,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
            singular=False,
            baseType=gunsmith.ReceiverFeatureInterface))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Capacity Modification',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.CapacityModificationInterface))

            # Feeds are processed after features and capacity so they can use the final receiver capacity
            stages.append(gunsmith.ConstructionStage(
                name='Feed',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Receiver,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
                singular=True,
                baseType=gunsmith.FeedInterface))

        # Fire Rate needs to be applied after Features as it needs to know the final Auto Score. It
        # needs to be applied after Feature as it needs to know if an RF/VRF feed is fitted
        stages.append(gunsmith.ConstructionStage(
            name='Fire Rate',
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Receiver,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            singular=True,
            baseType=gunsmith.FireRateInterface))

        return stages

    def _createBarrelStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[gunsmith.ConstructionStage]:
        stages = []

        if weaponType != gunsmith.WeaponType.ProjectorWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Barrel',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Barrel,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
                singular=True,
                baseType=gunsmith.BarrelInterface,
                # Default to Handgun as Minimal is a terrible default. We don't want to re-order the list
                # of barrels in code as the order they're defined determines the order they appear in lists
                # so they should stay in length order
                defaultType=gunsmith.HandgunBarrel))

            stages.append(gunsmith.ConstructionStage(
                name='Barrel Accessories',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.BarrelAccessories,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=False,
                baseType=gunsmith.BarrelAccessoryInterface))

        return stages

    def _createMountingStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Mounting',
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Mounting,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Desirable, # Will be None for primary
            singular=True,
            baseType=gunsmith.SecondaryMountInterface)]

    def _createStockStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Stock',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.Stock,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            singular=True,
            baseType=gunsmith.StockInterface)]

    def _createWeaponFeatureStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Weapon Features',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.WeaponFeatures,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
            singular=False,
            baseType=gunsmith.WeaponFeatureInterface)]

    def _createWeaponAccessoriesStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Weapon Accessories',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.WeaponAccessories,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
            singular=False,
            baseType=gunsmith.WeaponAccessoryInterface)]

    def _createMultiMountStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Multi-Mount',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.MultiMount,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
            singular=True,
            baseType=gunsmith.MultiMountInterface)]

    def _createLoadingStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[gunsmith.ConstructionStage]:
        stages = []

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Loaded Magazine',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Loading,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.MagazineLoadedInterface))

        if weaponType != gunsmith.WeaponType.PowerPackWeapon:
            if weaponType == gunsmith.WeaponType.ConventionalWeapon:
                loadedAmmoStageName = 'Loaded Ammo'
            elif weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon:
                loadedAmmoStageName = 'Loaded Cartridge Grenades'
            elif weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
                loadedAmmoStageName = 'Loaded Energy Cartridges'
            elif weaponType == gunsmith.WeaponType.ProjectorWeapon:
                loadedAmmoStageName = 'Loaded Fuel'
            stages.append(gunsmith.ConstructionStage(
                name=loadedAmmoStageName,
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Loading,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.AmmoLoadedInterface))
        else:
            stages.append(gunsmith.ConstructionStage(
                name='Inserted Internal Power Pack',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Loading,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.InternalPowerPackLoadedInterface))

            stages.append(gunsmith.ConstructionStage(
                name='Attached External Power Pack',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Loading,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=True,
                baseType=gunsmith.ExternalPowerPackLoadedInterface))

        # This stage is a hack to multiply the cost/weight of loaded ammo and magazine by the
        # number of multi-mounted weapons. In order for calculations to be consistent this stage
        # MUST be after the other loading stages as they generate constant cost/weight values but
        # this stage generates relative values
        stages.append(gunsmith.ConstructionStage(
            name='Multi-Mount Loading',
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Loading,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Desirable,
            singular=True,
            baseType=gunsmith.MultiMountLoadedInterface))

        return stages

    def _createMunitionsStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[gunsmith.ConstructionStage]:
        # I've made munitions quantities the last thing the user selects as they aren't part
        # of the actual weapon
        stages = []

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Magazine Quantities',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Munitions,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=False,
                baseType=gunsmith.MagazineQuantityInterface))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Loader Quantities',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Munitions,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=False,
                baseType=gunsmith.LoaderQuantityInterface))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon:
            ammoQuantityStageName = 'Ammo Quantities'
        elif weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon:
            ammoQuantityStageName = 'Cartridge Grenade Quantities'
        elif weaponType == gunsmith.WeaponType.PowerPackWeapon:
            ammoQuantityStageName = 'Power Pack Quantities'
        elif weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            ammoQuantityStageName = 'Energy Cartridge Quantities'
        elif weaponType == gunsmith.WeaponType.ProjectorWeapon:
            ammoQuantityStageName = 'Fuel Quantities'
        stages.append(gunsmith.ConstructionStage(
            name=ammoQuantityStageName,
            sequence=sequence,
            phase=gunsmith.ConstructionPhase.Munitions,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
            singular=False,
            baseType=gunsmith.AmmoQuantityInterface))

        if weaponType == gunsmith.WeaponType.ProjectorWeapon:
            stages.append(gunsmith.ConstructionStage(
                name='Propellant Quantities',
                sequence=sequence,
                phase=gunsmith.ConstructionPhase.Munitions,
                requirement=gunsmith.ConstructionStage.RequirementLevel.Optional,
                singular=False,
                baseType=gunsmith.ProjectorPropellantQuantityInterface))

        return stages

    def _createFinalisationStages(self) -> typing.Iterable[gunsmith.ConstructionStage]:
        return [gunsmith.ConstructionStage(
            name='Finalisation',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.ConstructionPhase.Finalisation,
            requirement=gunsmith.ConstructionStage.RequirementLevel.Mandatory,
            singular=True,
            baseType=gunsmith.FinalisationComponent,
            defaultType=gunsmith.FinalisationComponent)]
