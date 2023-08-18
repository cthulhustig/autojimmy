import gunsmith
import typing

class InitialisationComponent(gunsmith.ComponentInterface):
    def componentString(self) -> str:
        return 'Initialisation'

    def typeString(self) -> str:
        return 'Initialisation'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        return True

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        self._createCoreRulesCompatibleStep(sequence=sequence, context=context)

    """
    Create a step that adds a note to make it obvious when a weapon has been generated with the Core
    Rules Compatible rule. This is done in initialisation as the rule should always be one of the
    first listed.
    """

    def _createCoreRulesCompatibleStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        if not context.isRuleEnabled(rule=gunsmith.RuleId.CoreRulesCompatible):
            return # Nothing to do

        step = gunsmith.ConstructionStep(
            name=f'Core Rules Compatibility',
            type='Rules',
            notes=['Some construction values may have been modified to make it easier to use the weapon in existing games where players or npcs are using weapons from other rule books.'])
        context.applyStep(
            sequence=sequence,
            step=step)
