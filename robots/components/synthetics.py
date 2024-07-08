import common
import construction
import robots
import typing

class Synthetic(robots.RobotComponentInterface):
    """
    - Protection: 0 (p19 & p86)
    - Requirement: Can only add up to 2 slots of armour (p86)
    - Requirement: The min brain is only the min to successfully preform
    basic emulation of the living creature it's trying to mimic, if lower
    level brains are used the robot receives an additional  DM-2 to social
    skills
    - Requirement: In addition to the per slot cost of the android
    modification there is also a x3 cost multiplier for every part of the
    robot apart from skills
    """
    # NOTE: The cost is per Base Slot _NOT_ per slot that is required by the
    # component
    # NOTE: The Android description (p86) says that armour is limited to 2
    # slots but the Biological description doesn't say the same (p88). I
    # expect this is just an oversight as, if anything, you'd expect a
    # biological to be more restrictive than an android.
    # NOTE: The requirement that armour is limited to 2 slots is handled by
    # the Armour Increase component
    # NOTE: The requirement that an additional x3 cost modifier is applied is
    # handled in finalisation
    # NOTE: The Minimum Brain requirement is handled in finalisation

    _BaseProtection = common.ScalarCalculation(
        value=0,
        name='Android Base Protection')

    def __init__(
            self,
            componentString: str,
            minTL: int,
            slotPercentage: int,
            perBaseSlotCost: int,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__()

        self._componentString = componentString

        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._componentString} Minimum TL')

        self._slotPercentage = common.ScalarCalculation(
            value=slotPercentage,
            name=f'{self._componentString} Required Base Slot Percentage')

        self._perBaseSlotCost = common.ScalarCalculation(
            value=perBaseSlotCost,
            name=f'{self._componentString} Per Slot Cost')

        self._notes = notes

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Synthetic'

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if context.techLevel() < self._minTL.value():
            return False

        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())

        baseSlots = context.baseSlots(sequence=sequence)
        slots = common.Calculator.ceil(
            value=common.Calculator.takePercentage(
                value=baseSlots,
                percentage=self._slotPercentage),
            name=f'{self.componentString()} Required Slots')
        step.setSlots(slots=construction.ConstantModifier(value=slots))

        cost = common.Calculator.multiply(
            lhs=baseSlots,
            rhs=self._perBaseSlotCost,
            name=f'{self.componentString()} Required Cost')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.BaseProtection,
            value=AndroidSynthetic._BaseProtection))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Protection,
            value=AndroidSynthetic._BaseProtection))

        if self._notes:
            for note in self._notes:
                step.addNote(note=note)

        return step

class AndroidSynthetic(Synthetic):
    """
    - Slots: 50% of Base Slots
    """

    def __init__(
            self,
            componentString: str,
            minTL: int,
            perSlotCost: int,
            notes: typing.Optional[typing.Iterable[str]]
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTL=minTL,
            slotPercentage=50,
            perBaseSlotCost=perSlotCost,
            notes=notes)

class BasicAndroidSynthetic(AndroidSynthetic):
    """
    - Min TL: 8
    - Cost: Cr1000 Per Base Slot
    - Minimum Brain: Basic (X) or Hunter/Killer
    - Note: Barely emulating. DM-2 on all social interactions from the uncanny valley effect.
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Basic Android',
            minTL=8,
            perSlotCost=1000,
            notes=['All social interaction receive a DM-2 due to the uncanny valley effect. (p87)'])

class ImprovedAndroidSynthetic(AndroidSynthetic):
    """
    - Min TL: 10
    - Cost: Cr2000 Per Slot
    - Minimum Brain: Advanced
    - Note: Natural-looking. Passes at a distance but triggers the uncanny valley DM-2 within 5 metres.
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Improved Android',
            minTL=10,
            perSlotCost=2000,
            notes=['Natural-looking. (p87)',
                   'Social interactions with others within 5m of the robot receive a DM-2 due to the uncanny valley effect. (p87)'])

class EnhancedAndroidSynthetic(AndroidSynthetic):
    """
    - Min TL: 12
    - Cost: Cr5000 Per Slot
    - Minimum Brain: Very Advanced
    - Note: Natural-looking; Invisitech. Passes in close interaction, but on a roll of a natural 2 the uncanny valley sets in.
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Enhanced Android',
            minTL=12,
            perSlotCost=5000,
            notes=['Natural-looking, Invisitech. (p87 & p93)',
                   'On a roll of a natural 2 for a social interaction, the uncanny valley effect sets in and further rolls are at DM-2. (p87)'])

class AdvancedAndroidSynthetic(AndroidSynthetic):
    """
    - Min TL: 14
    - Cost: Cr10000 Per Slot
    - Minimum Brain: Very Advanced
    - Note: Natural-looking; Invisitech; Self-repairing. Can pass as a
    biological being unless scanned.
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Advanced Android',
            minTL=14,
            perSlotCost=10000,
            notes=['Natural-looking, Invisitech, Self-repairing. (p87 & p93)',
                   'Scanning is required to distinguish the robot from the species it\'s designed to imitate. (p87)'])

class SuperiorAndroidSynthetic(AndroidSynthetic):
    """
    - Min TL: 16
    - Cost: Cr2000 Per Slot
    - Minimum Brain: Self-Aware
    - Note: Natural-looking; Invisitech; Self-repairing. Can pass even after
      most scans.
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Superior Android',
            minTL=16,
            perSlotCost=20000,
            notes=['Natural-looking, Invisitech, Self-repairing. (p87 & p93)',
                   'Most scanners are unable to distinguish the robot from the species it\'s designed to imitate. (p87)'])

class BioRobotSynthetic(Synthetic):
    """
    - Slots: 75% of Base Slots
    - Note: Natural-looking, Self-repairing (p88)
    - Requirement: Locomotion is limited to natural forms of locomotion (p88)
    - Requirement: Standard Endurance doesn't apply to Biological Robots, they
      have to eat, drink & breath (p88)
    - Requirement: A Biological Robot can use any of the body augments from the
      Central Supply Catalogue or Robot Handbook (p88)
    """
    # NOTE: I've handled the locomotion requirement by making BioRobots only
    # compatible with None, Aeroplane, Aquatic, VTOL & Walker locomotions. This
    # list is based on the spreadsheet. It also has Lighter than Air as a
    # natural locomotion type but I don't know where that type is from so I've
    # not included it for now at least
    # NOTE: To handle the Endurance requirement I'm just deleting the Endurance
    # attribute and adding a note. The expectation is later components that
    # rely on Endurance will either be incompatible with BioRobots or able to
    # handle Endurance possibly not being set, which ever makes the most logical
    # sense for the component in question.
    # NOTE: I've intentionally not included the note about biological robots
    # needing to eat/drink/breath as it doesn't seem worth the clutter. I think
    # it's pretty obvious that the robot needs to partake in whatever activities
    # the species it's based on needs to in order to survive. What's not obvious
    # is that would always include eat/drink/breath.
    # TODO: Handle body augments

    def __init__(
            self,
            componentString: str,
            minTL: int,
            perSlotCost: int,
            notes: typing.Optional[typing.Iterable[str]]
            ) -> None:
        newNotes = ['Natural-looking, Self-repairing. (p88 & p93)']
        if notes:
            newNotes.extend(notes)
        super().__init__(
            componentString=componentString,
            minTL=minTL,
            slotPercentage=75,
            perBaseSlotCost=perSlotCost,
            notes=newNotes)

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if not super().isCompatible(sequence, context):
            return False

        locomotions = context.findComponents(
            componentType=robots.Locomotion,
            sequence=sequence)
        for locomotion in locomotions:
            assert(isinstance(locomotion, robots.Locomotion))
            if not locomotion.isNatural():
                return False
        return True

    def _createStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = super()._createStep(sequence, context)

        # Standard robot Endurance doesn't apply to BioRobots so delete the
        # attribute rather than setting it to 0. This avoids having it
        # displayed to the user and and lets later components check for
        # its presence to avoid applying Endurance modifiers
        # NOTE: Can't delete SecondaryEndurance here as it's not been set yet
        step.addFactor(factor=construction.DeleteAttributeFactor(
            attributeId=robots.RobotAttributeId.Endurance))

        return step

class BasicBioRobotSynthetic(BioRobotSynthetic):
    """
    - Min TL: 11
    - Cost: Cr2000
    - Minimum Brain: Basic (x) or Hunter/Killer
    - Note: DM-2 on all healing checks. Emissions from the electronic brain or
      interfaces are detectable by attuned scanners and by any psionic life
      detection. (p88)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Basic Bio-Robot',
            minTL=11,
            perSlotCost=2000,
            notes=['Only scanners and psionic life detection can differentiate the robot from the species it\'s designed to imitate. (p88)',
                   'DM-2 on all healing checks. (p88)'])

class ImprovedBioRobotSynthetic(BioRobotSynthetic):
    """
    - Min TL: 13
    - Cost: Cr5000
    - Minimum Brain: Advanced
    - Note: Treat detection of an artificial brain as DM-2 on any scanner check, including psionic life detection. (p88)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Improved Bio-Robot',
            minTL=13,
            perSlotCost=5000,
            notes=['Only scanners and psionic life detection can differentiate the robot from the species it\'s designed to imitate, and they do so at DM-2. (p88) '])

class EnhancedBioRobotSynthetic(BioRobotSynthetic):
    """
    - Min TL: 15
    - Cost: Cr10000
    - Minimum Brain: Very Advanced
    - Note: DM+2 on all healing checks. DM-4 on any scanner check, including psionic life detection. (p88)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Enhanced Bio-Robot',
            minTL=15,
            perSlotCost=10000,
            notes=['Only scanners and psionic life detection can differentiate the robot from the species it\'s designed to imitate, and they do so at DM-4. (p88)',
                   'DM+2 on all healing checks. (p88)'])

class AdvancedBioRobotSynthetic(BioRobotSynthetic):
    """
    - Min TL: 17
    - Cost: Cr20000
    - Minimum Brain: Self-Aware
    - Note: DM+4 on all healing checks. Indistinguishable from a fully biological being, even psionically. (p88)
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Advanced Bio-Robot',
            minTL=17,
            perSlotCost=20000,
            notes=['The robot is biologically indistinguishable from the species it\'s designed to imitate, even psionically. (p88)',
                   'DM+4 on all healing checks. (p88)'])
