import common
import construction
import enum
import gunsmith
import typing
import uuid

class _WeaponSequenceState(construction.SequenceState):
    def __init__(
            self,
            weaponType: gunsmith.WeaponType,
            isPrimary: bool,
            stages: typing.Optional[typing.Iterable[construction.ConstructionStage]]
            ) -> None:
        super().__init__(
            phasesType=gunsmith.WeaponPhase,
            componentsType=gunsmith.WeaponComponentInterface,
            isPrimary=isPrimary,
            stages=stages)
        self._weaponType = weaponType

    def weaponType(self) -> gunsmith.WeaponType:
        return self._weaponType

    def setWeaponType(
            self,
            weaponType: gunsmith.WeaponType,
            stages: typing.Iterable[construction.ConstructionStage]
            ) -> None:
        self._weaponType = weaponType
        self.setStages(stages=stages)

class WeaponContext(construction.ConstructionContext):
    def __init__(
            self,
            techLevel: int,
            rules: typing.Optional[typing.Iterable[gunsmith.RuleId]] = None
            ) -> None:
        super().__init__(
            phasesType=gunsmith.WeaponPhase,
            componentsType=gunsmith.WeaponComponentInterface,
            techLevel=techLevel)
        self._rules = set(rules) if rules else set()

    def isRuleEnabled(self, rule: gunsmith.RuleId):
        return rule in self._rules

    def rules(self) -> typing.Collection[gunsmith.RuleId]:
        return self._rules

    def setRules(
            self,
            rules: typing.Iterable[gunsmith.RuleId],
            regenerate: bool = True
            ) -> None:
        self._rules.clear()
        for rule in rules:
            self._rules.add(rule)

        if regenerate:
            self.regenerate()

    def enableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        self._rules.add(rule)

        if regenerate:
            self.regenerate()

    def disableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        if rule in self._rules:
            self._rules.remove(rule)

        if regenerate:
            self.regenerate()

    def clearRules(
            self,
            regenerate: bool = True
            ) -> None:
        self._rules.clear()

        if regenerate:
            self.regenerate()

    def weaponType(
            self,
            sequence: str
            ) -> gunsmith.WeaponType:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        assert(isinstance(sequenceState, _WeaponSequenceState))

        return sequenceState.weaponType()

    def setWeaponType(
            self,
            sequence: str,
            weaponType: gunsmith.WeaponType,
            stages: typing.Iterable[construction.ConstructionStage],
            regenerate: bool = True
            ) -> None:
        sequenceState = self._sequenceStates.get(sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        assert(isinstance(sequenceState, _WeaponSequenceState))

        sequenceState.setWeaponType(
            weaponType=weaponType,
            stages=stages)

        if regenerate:
            self.regenerate()

    def phaseWeight(
            self,
            phase: gunsmith.WeaponPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Weight,
                phase=phase)

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
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Weight,
                phase=phase)

        # Add the phase weight for each stage
        weights = []
        for sequenceState in self._sequenceStates.values():
            weights.append(sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Weight,
                phase=phase))
        return common.Calculator.sum(
            values=weights,
            name=f'Total {phase.value} Weight')

    def phaseCredits(
            self,
            phase: gunsmith.WeaponPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Credits,
                phase=phase)

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
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Credits,
                phase=phase)

        # Add the phase weight for each stage
        costs = []
        for sequenceState in self._sequenceStates.values():
            costs.append(sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Credits,
                phase=phase))
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
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Weight,
                phase=gunsmith.WeaponPhase.Receiver)

        return self.phaseWeight(phase=gunsmith.WeaponPhase.Receiver, sequence=None)

    def receiverCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        if sequence:
            sequenceState = self._sequenceStates.get(sequence)
            if not sequenceState:
                raise RuntimeError(f'Unknown sequence {sequence}')
            return sequenceState.phaseCost(
                costId=gunsmith.WeaponCost.Credits,
                phase=gunsmith.WeaponPhase.Receiver)

        return self.phaseCredits(phase=gunsmith.WeaponPhase.Receiver, sequence=None)

    def baseWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.BaseWeaponConstructionPhases,
            calculationName='Total Base Weight',
            sequence=sequence)

    def baseCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCredits(
            phases=gunsmith.BaseWeaponConstructionPhases,
            calculationName='Total Base Cost',
            sequence=sequence)

    def totalWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.WeaponPhase,
            calculationName='Total Weight',
            sequence=sequence)

    def totalCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCredits(
            phases=gunsmith.WeaponPhase,
            calculationName='Total Cost',
            sequence=sequence)

    def combatWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseWeight(
            phases=gunsmith.CombatReadyConstructionPhases,
            calculationName='Total Combat Weight',
            sequence=sequence)

    def combatCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        return self._multiPhaseCredits(
            phases=gunsmith.CombatReadyConstructionPhases,
            calculationName='Total Combat Cost',
            sequence=sequence)

    def _multiPhaseWeight(
            self,
            phases: typing.Iterable[gunsmith.WeaponPhase],
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

    def _multiPhaseCredits(
            self,
            phases: typing.Iterable[gunsmith.WeaponPhase],
            calculationName: str,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        costs = []
        for phase in phases:
            costs.append(self.phaseCredits(
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
        self._userNotes = userNotes if userNotes else ''

        # NOTE: It's important that the context is created at construction and
        # never recreated for the lifetime of the weapon as things like the UI
        # may hold onto references to it.
        # NOTE: It's also important that this class doesn't cache any state as
        # the context may be modified without it knowing.
        self._constructionContext = WeaponContext(
            techLevel=techLevel,
            rules=rules)
        self._commonStages = self._createCommonStages()

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
        return self._constructionContext.techLevel()

    def setTechLevel(
            self,
            techLevel: int,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setTechLevel(
            techLevel=techLevel,
            regenerate=regenerate)

    def rules(self) -> typing.Collection[gunsmith.RuleId]:
        return self._constructionContext.rules()

    def setRules(
            self,
            rules: typing.Iterable[gunsmith.RuleId],
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setRules(
            rules=rules,
            regenerate=regenerate)

    def isRuleEnabled(self, rule: gunsmith.RuleId) -> bool:
        return self._constructionContext.isRuleEnabled(rule=rule)

    def enableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.enableRule(
            rule=rule,
            regenerate=regenerate)

    def disableRule(
            self,
            rule: gunsmith.RuleId,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.disableRule(
            rule=rule,
            regenerate=regenerate)

    def clearRules(self, regenerate: bool = True) -> None:
        self._constructionContext.clearRules(
            regenerate=regenerate)
        
    def context(self) -> WeaponContext:
        return self._constructionContext

    def userNotes(self) -> str:
        return self._userNotes

    def setUserNotes(self, notes: str) -> None:
        self._userNotes = notes

    def addSequence(
            self,
            weaponType: gunsmith.WeaponType,
            regenerate: bool = True
            ) -> str:
        sequence = str(uuid.uuid4())
        sequenceState = _WeaponSequenceState(
            weaponType=weaponType,
            isPrimary=self._constructionContext.sequenceCount() == 0,
            stages=self._createSequenceStages(weaponType=weaponType, sequence=sequence))
        self._constructionContext.addSequence(
            sequence=sequence,
            sequenceState=sequenceState,
            regenerate=regenerate)

        return sequence

    def removeSequence(
            self,
            sequence: str,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.removeSequence(
            sequence=sequence,
            regenerate=regenerate)

    def clearSequences(self) -> None:
        self._constructionContext.clearSequences()

        # Remove components from common stages
        for stage in self._commonStages:
            stage.clearComponents()

    def sequences(self) -> typing.Collection[str]:
        return self._constructionContext.sequences()

    def sequenceCount(self) -> int:
        return self._constructionContext.sequenceCount()

    def weaponType(
            self,
            sequence: str
            ) -> gunsmith.WeaponType:
        return self._constructionContext.weaponType(
            sequence=sequence)

    def setWeaponType(
            self,
            sequence: str,
            weaponType: gunsmith.WeaponType,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.setWeaponType(
            sequence=sequence,
            weaponType=weaponType,
            stages=self._createSequenceStages(
                sequence=sequence,
                weaponType=weaponType),
            regenerate=regenerate)

    def stages(
            self,
            sequence: typing.Optional[str] = None,
            phase: typing.Optional[gunsmith.WeaponPhase] = None,
            componentType: typing.Optional[typing.Type[gunsmith.WeaponComponentInterface]] = None
            ) -> typing.Iterable[construction.ConstructionStage]:
        return self._constructionContext.stages(
            sequence=sequence,
            phase=phase,
            componentType=componentType)

    def findComponents(
            self,
            componentType: typing.Type[gunsmith.WeaponComponentInterface],
            sequence: typing.Optional[str] = None,
            ) -> typing.Iterable[gunsmith.WeaponComponentInterface]:
        return self._constructionContext.findComponents(
            componentType=componentType,
            sequence=sequence)

    def hasComponent(
            self,
            componentType: typing.Type[gunsmith.WeaponComponentInterface],
            sequence: typing.Optional[str] = None
            ) -> bool:
        return self._constructionContext.hasComponent(
            componentType=componentType,
            sequence=sequence)

    # The replaceComponent parameter can be used to get the list of components that would be
    # compatible if the specified component was being replaced. If the replaceComponent is
    # compatible with the weapon (which generally it always should be) then it will be included
    # in the returned list of components
    def findCompatibleComponents(
            self,
            stage: construction.ConstructionStage,
            replaceComponent: typing.Optional[gunsmith.WeaponComponentInterface] = None
            ) -> typing.Iterable[gunsmith.WeaponComponentInterface]:
        return self._constructionContext.findCompatibleComponents(
            stage=stage,
            replaceComponent=replaceComponent)

    def loadComponents(
            self,
            sequenceComponents: typing.Mapping[str, typing.Iterable[typing.Tuple[str, typing.Optional[typing.Mapping[str, typing.Any]]]]],
            commonComponents: typing.Iterable[typing.Tuple[str, typing.Optional[typing.Mapping[str, typing.Any]]]]
            ) -> None:
        self._constructionContext.loadComponents(
            sequenceComponentData=sequenceComponents,
            commonComponentData=commonComponents)        

    def addComponent(
            self,
            stage: construction.ConstructionStage,
            component: gunsmith.WeaponComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.addComponent(
            stage=stage,
            component=component,
            regenerate=regenerate)

    def removeComponent(
            self,
            stage: construction.ConstructionStage,
            component: gunsmith.WeaponComponentInterface,
            regenerate: bool = True
            ) -> None:
        self._constructionContext.removeComponent(
            stage=stage,
            component=component,
            regenerate=regenerate)

    def replaceComponent(
            self,
            stage: construction.ConstructionStage,
            oldComponent: typing.Optional[gunsmith.WeaponComponentInterface],
            newComponent: typing.Optional[gunsmith.WeaponComponentInterface],
            regenerate: bool = True
            ) -> None:
        self._constructionContext.replaceComponent(
            stage=stage,
            oldComponent=oldComponent,
            newComponent=newComponent,
            regenerate=regenerate)

    def clearComponents(
            self,
            phase: typing.Optional[gunsmith.WeaponPhase] = None,
            sequence: typing.Optional[str] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        return self._constructionContext.clearComponents(
            phase=phase,
            sequence=sequence,
            regenerate=regenerate)

    def unloadWeapon(
            self,
            sequence: typing.Optional[str] = None,
            regenerate: bool = True
            ) -> bool: # True if modified, otherwise False
        return self.clearComponents(
            phase=gunsmith.WeaponPhase.Loading,
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
            stopStage: typing.Optional[construction.ConstructionStage] = None
            ) -> None:
        self._constructionContext.regenerate(
            stopStage=stopStage)

    def hasAttribute(
            self,
            sequence: str,
            attributeId: gunsmith.WeaponAttributeId
            ) -> bool:
        return self._constructionContext.hasAttribute(
            sequence=sequence,
            attributeId=attributeId)

    def attribute(
            self,
            sequence: str,
            attributeId: gunsmith.WeaponAttributeId,
            ) -> typing.Optional[construction.AttributeInterface]:
        sequenceState = self._constructionContext.state(
            sequence=sequence)
        if not sequenceState:
            raise RuntimeError(f'Unknown sequence {sequence}')
        assert(isinstance(sequenceState, _WeaponSequenceState))

        # For multi-sequence weapons the Quickdraw value is the sum of the
        # Quickdraw values for all sequences
        if (attributeId == gunsmith.WeaponAttributeId.Quickdraw) and \
                (self._constructionContext.sequenceCount() > 1):
            return self._calculateQuickdrawScore()

        return sequenceState.attribute(attributeId=attributeId)

    def attributeValue(
            self,
            sequence: str,
            attributeId: gunsmith.WeaponAttributeId,
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        # Call this classes implementation of attribute is important to get the
        # correct Quickdraw value
        attribute = self.attribute(sequence=sequence, attributeId=attributeId)
        if not attribute:
            return None
        return attribute.value()

    def constructionNotes(
            self,
            sequence: str,
            component: gunsmith.WeaponComponentInterface = None,
            phase: gunsmith.WeaponPhase = None
            ) -> typing.Iterable[str]:
        return self._constructionContext.constructionNotes(
            sequence=sequence,
            component=component,
            phase=phase)

    def steps(
            self,
            sequence: str,
            component: typing.Optional[gunsmith.WeaponComponentInterface] = None,
            phase: typing.Optional[gunsmith.WeaponPhase] = None,
            ) -> typing.Collection[gunsmith.WeaponStep]:
        return self._constructionContext.steps(
            sequence=sequence,
            component=component,
            phase=phase)

    # This returns the total weight of the specified phase for all weapon sequences
    def phaseWeight(
            self,
            phase: gunsmith.WeaponPhase
            ) -> common.ScalarCalculation:
        return self._constructionContext.phaseWeight(phase=phase, sequence=None)

    # This returns the total cost of the specified phase for all weapon sequences
    def phaseCredits(
            self,
            phase: gunsmith.WeaponPhase
            ) -> common.ScalarCalculation:
        return self._constructionContext.phaseCredits(phase=phase, sequence=None)

    def baseWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.baseWeight(sequence=None)

    def baseCredits(self) -> common.ScalarCalculation:
        return self._constructionContext.baseCredits(sequence=None)

    def combatWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.combatWeight(sequence=None)

    def combatCredits(self) -> common.ScalarCalculation:
        return self._constructionContext.combatCredits(sequence=None)

    def totalWeight(self) -> common.ScalarCalculation:
        return self._constructionContext.totalWeight(sequence=None)

    def totalCredits(self) -> common.ScalarCalculation:
        return self._constructionContext.totalCredits(sequence=None)

    def manifest(self) -> construction.Manifest:
        sequenceStates = self._constructionContext.states()
        manifest = construction.Manifest(costsType=gunsmith.WeaponCost)

        for sequenceIndex, sequence in enumerate(sequenceStates):
            assert(isinstance(sequence, _WeaponSequenceState))
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
                        assert(isinstance(step, gunsmith.WeaponStep))

                        entryText = self._prefixManifestText(
                            sequenceIndex=sequenceIndex,
                            baseText=f'{step.type()}: {step.name()}')
                        manifestSection.createEntry(
                            component=entryText,
                            costs=step.costs(),
                            factors=step.factors())

        for phase in gunsmith.CommonConstructionPhases:
            componentMap: typing.Dict[gunsmith.WeaponComponentInterface, typing.Dict[str, gunsmith.WeaponStep]] = {}
            stepFactors: typing.Dict[gunsmith.WeaponStep, typing.Dict[int, typing.List[construction.FactorInterface]]] = {}
            for sequenceIndex, sequence in enumerate(sequenceStates):
                assert(isinstance(sequence, _WeaponSequenceState))
                for component in sequence.components(phase=phase):
                    steps = sequence.steps(component=component)
                    if not steps:
                        continue

                    stepNameMap = componentMap.get(component)
                    if not stepNameMap:
                        stepNameMap = {}
                        componentMap[component] = stepNameMap

                    for step in steps:
                        assert(isinstance(step, gunsmith.WeaponStep))

                        commonStep = stepNameMap.get(step.name())
                        if not commonStep:
                            commonStep = gunsmith.WeaponStep(
                                name=step.name(),
                                type=step.type(),
                                credits=step.credits(),
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
                factorTextCollisions: typing.Dict[str, typing.Dict[int, construction.FactorInterface]] = {}
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
                            step.addFactor(construction.NonModifyingFactor(
                                factor=factor,
                                prefix=stepPrefix))

            manifestSection = manifest.createSection(name=phase.value)
            for stepMap in componentMap.values():
                for step in stepMap.values():
                    manifestSection.createEntry(
                        component=f'{step.type()}: {step.name()}',
                        costs=step.costs(),
                        factors=step.factors())

        for phase in gunsmith.AncillaryConstructionPhases:
            for sequenceIndex, sequence in enumerate(sequenceStates):
                assert(isinstance(sequence, _WeaponSequenceState))
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
                            costs=step.costs(),
                            factors=step.factors())

        for sequenceIndex, sequence in enumerate(sequenceStates):
            assert(isinstance(sequence, _WeaponSequenceState))
            sectionName = self._prefixManifestText(
                sequenceIndex=sequenceIndex,
                baseText=gunsmith.WeaponPhase.Finalisation.value)

            manifestSection = None
            for component in sequence.components(phase=gunsmith.WeaponPhase.Finalisation):
                steps = sequence.steps(component=component)
                if not steps:
                    continue

                for step in steps:
                    assert(isinstance(step, gunsmith.WeaponStep))

                    if not step.credits() and not step.weight() and not step.factors():
                        continue

                    if not manifestSection:
                        manifestSection = manifest.createSection(name=sectionName)

                    entryText = self._prefixManifestText(
                        sequenceIndex=sequenceIndex,
                        baseText=f'{step.type()}: {step.name()}')
                    manifestSection.createEntry(
                        component=entryText,
                        costs=step.costs(),
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

    def _calculateQuickdrawScore(self) -> construction.NumericAttribute:
        scores = []
        for sequenceState in self._constructionContext.states():
            assert(isinstance(sequenceState, _WeaponSequenceState))
            attribute = sequenceState.attribute(attributeId=gunsmith.WeaponAttributeId.Quickdraw)
            if isinstance(attribute, construction.NumericAttribute):
                scores.append(attribute.value())
        return construction.NumericAttribute(
            attributeId=gunsmith.WeaponAttributeId.Quickdraw,
            value=common.Calculator.sum(
                values=scores,
                name='Total Quickdraw Score'))

    def _createCommonStages(
            self
            ) -> typing.List[construction.ConstructionStage]:
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
            ) -> typing.List[construction.ConstructionStage]:
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

    def _createInitialisationStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Initialisation',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.Initialisation,
            baseType=gunsmith.InitialisationComponent,
            defaultType=gunsmith.InitialisationComponent,
            # Mandatory single component
            minComponents=1,
            maxComponents=1)]

    def _createReceiverStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> None:
        stages = []

        stages.append(construction.ConstructionStage(
            name='Receiver',
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Receiver,
            baseType=gunsmith.ReceiverInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon:
            stages.append(construction.ConstructionStage(
                name='Calibre',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.CalibreInterface,
                # Mandatory single component
                minComponents=1,
                maxComponents=1))

        if weaponType != gunsmith.WeaponType.ProjectorWeapon:
            stages.append(construction.ConstructionStage(
                name='Multi-Barrel',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.MultiBarrelInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))

            stages.append(construction.ConstructionStage(
                name='Mechanism',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.MechanismInterface,
                # Mandatory single component
                minComponents=1,
                maxComponents=1))
        else:
            # Having Propellant before Structure Feature is important as, in the case of
            # generated gas, there is a fixed receiver cost modification so you'll get different
            # results depending on if it's applied before or after any multiplier cost
            # modifications. The examples (Field Catalogue 111-113) have it in this order so i've
            # gone with that
            stages.append(construction.ConstructionStage(
                name='Propellant',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.PropellantTypeInterface,
                # Mandatory single component
                minComponents=1,
                maxComponents=1))

        stages.append(construction.ConstructionStage(
            name='Receiver Features',
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Receiver,
            baseType=gunsmith.ReceiverFeatureInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(construction.ConstructionStage(
                name='Capacity Modification',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.CapacityModificationInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))

            # Feeds are processed after features and capacity so they can use the final receiver capacity
            stages.append(construction.ConstructionStage(
                name='Feed',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Receiver,
                baseType=gunsmith.FeedInterface,
                # Mandatory single component
                minComponents=1,
                maxComponents=1))

        # Fire Rate needs to be applied after Features as it needs to know the final Auto Score. It
        # needs to be applied after Feature as it needs to know if an RF/VRF feed is fitted
        stages.append(construction.ConstructionStage(
            name='Fire Rate',
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Receiver,
            baseType=gunsmith.FireRateInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1))

        return stages

    def _createBarrelStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[construction.ConstructionStage]:
        stages = []

        if weaponType != gunsmith.WeaponType.ProjectorWeapon:
            stages.append(construction.ConstructionStage(
                name='Barrel',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Barrel,
                baseType=gunsmith.BarrelInterface,
                # Default to Handgun as Minimal is a terrible default. We don't want to re-order the list
                # of barrels in code as the order they're defined determines the order they appear in lists
                # so they should stay in length order
                defaultType=gunsmith.HandgunBarrel,
                # Mandatory single component
                minComponents=1,
                maxComponents=1))

            stages.append(construction.ConstructionStage(
                name='Barrel Accessories',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.BarrelAccessories,
                baseType=gunsmith.BarrelAccessoryInterface,
                # Optional multi component
                minComponents=None,
                maxComponents=None))

        return stages

    def _createMountingStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Mounting',
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Mounting,
            baseType=gunsmith.SecondaryMountInterface,
            # Optional single component 
            minComponents=0,
            maxComponents=1,
            # Force the stage to have a component if any are compatible
            forceComponent=True)]

    def _createStockStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Stock',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.Stock,
            baseType=gunsmith.StockInterface,
            # Mandatory single component
            minComponents=1,
            maxComponents=1)]

    def _createWeaponFeatureStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Weapon Features',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.WeaponFeatures,
            baseType=gunsmith.WeaponFeatureInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None)]

    def _createWeaponAccessoriesStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Weapon Accessories',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.WeaponAccessories,
            baseType=gunsmith.WeaponAccessoryInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None)]

    def _createMultiMountStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Multi-Mount',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.MultiMount,
            baseType=gunsmith.MultiMountInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1)]

    def _createLoadingStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[construction.ConstructionStage]:
        stages = []

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(construction.ConstructionStage(
                name='Loaded Magazine',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Loading,
                baseType=gunsmith.MagazineLoadedInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))

        if weaponType != gunsmith.WeaponType.PowerPackWeapon:
            if weaponType == gunsmith.WeaponType.ConventionalWeapon:
                loadedAmmoStageName = 'Loaded Ammo'
            elif weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon:
                loadedAmmoStageName = 'Loaded Cartridge Grenades'
            elif weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
                loadedAmmoStageName = 'Loaded Energy Cartridges'
            elif weaponType == gunsmith.WeaponType.ProjectorWeapon:
                loadedAmmoStageName = 'Loaded Fuel'
            stages.append(construction.ConstructionStage(
                name=loadedAmmoStageName,
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Loading,
                baseType=gunsmith.AmmoLoadedInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))
        else:
            stages.append(construction.ConstructionStage(
                name='Inserted Internal Power Pack',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Loading,
                baseType=gunsmith.InternalPowerPackLoadedInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))

            stages.append(construction.ConstructionStage(
                name='Attached External Power Pack',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Loading,
                baseType=gunsmith.ExternalPowerPackLoadedInterface,
                # Optional single component
                minComponents=0,
                maxComponents=1))

        # This stage is a hack to multiply the cost/weight of loaded ammo and magazine by the
        # number of multi-mounted weapons. In order for calculations to be consistent, this stage
        # MUST be after the other loading stages as they generate constant cost/weight values but
        # this stage generates relative values
        stages.append(construction.ConstructionStage(
            name='Multi-Mount Loading',
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Loading,
            baseType=gunsmith.MultiMountLoadedInterface,
            # Optional single component
            minComponents=0,
            maxComponents=1,
            # Force the stage to have a component if any are compatible
            forceComponent=True))

        return stages

    def _createMunitionsStages(
            self,
            weaponType: gunsmith.WeaponType,
            sequence: str
            ) -> typing.Iterable[construction.ConstructionStage]:
        # I've made munitions quantities the last thing the user selects as they aren't part
        # of the actual weapon
        stages = []

        if weaponType == gunsmith.WeaponType.ConventionalWeapon or \
                weaponType == gunsmith.WeaponType.GrenadeLauncherWeapon or \
                weaponType == gunsmith.WeaponType.EnergyCartridgeWeapon:
            stages.append(construction.ConstructionStage(
                name='Magazine Quantities',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Munitions,
                baseType=gunsmith.MagazineQuantityInterface,
                # Optional multi component
                minComponents=None,
                maxComponents=None))

        if weaponType == gunsmith.WeaponType.ConventionalWeapon:
            stages.append(construction.ConstructionStage(
                name='Loader Quantities',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Munitions,
                baseType=gunsmith.LoaderQuantityInterface,
                # Optional multi component
                minComponents=None,
                maxComponents=None))

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
        stages.append(construction.ConstructionStage(
            name=ammoQuantityStageName,
            sequence=sequence,
            phase=gunsmith.WeaponPhase.Munitions,
            baseType=gunsmith.AmmoQuantityInterface,
            # Optional multi component
            minComponents=None,
            maxComponents=None))

        if weaponType == gunsmith.WeaponType.ProjectorWeapon:
            stages.append(construction.ConstructionStage(
                name='Propellant Quantities',
                sequence=sequence,
                phase=gunsmith.WeaponPhase.Munitions,
                baseType=gunsmith.ProjectorPropellantQuantityInterface,
                # Optional multi component
                minComponents=None,
                maxComponents=None))

        return stages

    def _createFinalisationStages(self) -> typing.Iterable[construction.ConstructionStage]:
        return [construction.ConstructionStage(
            name='Finalisation',
            sequence=None, # Not tided to a specific sequence
            phase=gunsmith.WeaponPhase.Finalisation,
            baseType=gunsmith.FinalisationComponent,
            defaultType=gunsmith.FinalisationComponent,
            # Mandatory single component
            minComponents=1,
            maxComponents=1)]
