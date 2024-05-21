import common
import construction
import gunsmith
import typing

class Mechanism(gunsmith.WeaponComponentInterface):
    """
    - Requirement: Not compatible with projectors
    """
    # NOTE: I've added the requirement that the mechanisms aren't compatible with launchers as
    # I don't think they really apply to that kind of weapon.
    # NOTE: It's not obvious if energy weapons should have a mechanism or not. The rules don't
    # say they do but then they don't say they don't either so I've allowed it. If users don't
    # think they should have a mechanism they can just leave it as the default semi-automatic
    # which has no effect on the weapon cost/weight/stats

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__()

        if costModifierPercentage != None and not isinstance(costModifierPercentage, common.ScalarCalculation):
            costModifierPercentage = common.ScalarCalculation(
                value=costModifierPercentage,
                name=f'{componentString} Mechanism Receiver Cost Modifier Percentage')

        self._componentString = componentString
        self._minTechLevel = minTechLevel
        self._costModifierPercentage = costModifierPercentage

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Mechanism'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < self._minTechLevel:
            return False

        if context.hasComponent(
                componentType=gunsmith.ProjectorReceiver,
                sequence=sequence):
            return False

        # Only compatible with weapons that have a receiver.
        return context.hasComponent(
            componentType=gunsmith.Receiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        if self._costModifierPercentage:
            step.setCredits(credits=construction.PercentageModifier(
                value=self._costModifierPercentage))

        return step

class SemiAutomaticMechanism(Mechanism):
    """
    - Min TL: 6
    - Requirement: Not compatible with single shot launchers
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. I've gone with TL 6 as that's the min TL for a Autopistol and
    # Autorifle in the Core Rules p118

    def __init__(self) -> None:
        super().__init__(
            componentString='Semi-automatic',
            minTechLevel=6)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with single shot launchers
        return not context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence)

class SingleShotMechanism(Mechanism):
    """
    - Min TL: 3
    - Receiver Cost: -75%
    - Ammo Capacity: Max capacity is number of barrels
    - Requirement: Not compatible with semi-automatic launchers
    - Requirement: Not compatible with power pack energy weapons
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. I've gone with TL 3 as that's the min TL for a Antique weapons in
    # the Core Rules p118
    # NOTE: The max ammo capacity is partially handled here and partially in the capacity and
    # Feature code. The ammo capacity is set to 1 here and the capacity/high capacity feature
    # will report that they're incompatible with the single shot mechanism.
    # NOTE: I've added the requirement that the single shot mechanism isn't compatible with power pack
    # energy weapons as their number of shots is determined by the power pack size. As they don't have
    # a standard ammo capacity attribute this mechanism would just be a cost reduction without any
    # negative impact on the weapon. I think it still makes sense to allow it for cartridge based energy
    # weapons as it could be a weapon that only holds a single cartridge

    def __init__(self) -> None:
        super().__init__(
            componentString='Single Shot',
            minTechLevel=3,
            costModifierPercentage=-75)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with semi-automatic launchers and power pack energy weapons
        return not context.hasComponent(
            componentType=gunsmith.LightSemiAutomaticLauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSemiAutomaticLauncherReceiver,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        barrelCount = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.BarrelCount)
        assert(isinstance(barrelCount, common.ScalarCalculation)) # Construction logic should enforce this

        ammoCapacity = common.Calculator.equals(
            value=barrelCount,
            name=f'{self.componentString()} Ammo Capacity')
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            value=ammoCapacity))

        return step

class RepeaterMechanism(Mechanism):
    """
    - Min TL: 5
    - Receiver Cost: -50%
    - Ammo Capacity: -50% except for Smoothbores (Field Catalogue p36)
    - Requirement: Not compatible with launchers
    - Requirement: Not compatible with power pack energy weapons
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. I've gone with TL 5 as that's the min TL for a Revolver in the
    # Core Rules p118
    # NOTE: I've added the requirement that this isn't compatible with launchers as it doesn't fit
    # with any of the descriptions in the rules. The mechanism for single shot and semi-automatic
    # launchers is obvious from the name and the idea of a belt fed support launcher with a repeater
    # mechanism doesn't really make sense.
    # NOTE: I've added the requirement that the single shot mechanism isn't compatible with power pack
    # energy weapons as it doesn't really make sense with their power being a continuous supply from
    # a power pack. As they don't have a standard ammo capacity attribute this mechanism would just be a
    # cost reduction without any negative impact on the weapon. I think it still makes sense to allow
    # it for cartridge based energy weapons as it could be a weapon that only holds a single cartridge.
    # I also quite like the idea of a mechanical revolver mechanism that rotates cartridges into place.

    _RepeaterAmmoCapacityModifierPercentage = common.ScalarCalculation(
        value=-50,
        name='Repeater Mechanism Ammo Capacity Modifier Percentage')

    def __init__(self) -> None:
        super().__init__(
            componentString='Repeater',
            minTechLevel=5,
            costModifierPercentage=-50)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with launchers and power pack energy weapons
        return not context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.PowerPackReceiver,
                sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Apply capacity modification if weapon isn't a smoothbore
        if not context.hasComponent(
                componentType=gunsmith.SmoothboreCalibre,
                sequence=sequence):
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
                modifier=construction.PercentageModifier(
                    value=self._RepeaterAmmoCapacityModifierPercentage,
                    roundDown=True)))

        return step

class AutoMechanism(Mechanism):
    """
    - Requirement: Not compatible with single shot or semi-automatic launchers
    """
    # NOTE: I've not made this incompatible with support launchers as the rules don't say you can't
    # do it. The Central Supply Catalogue has an example of a RAM launcher with an Auto trait so
    # it seems like it should be possible

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            costModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            autoModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            minTechLevel=minTechLevel,
            costModifierPercentage=costModifierPercentage)

        if autoModifier != None and not isinstance(autoModifier, common.ScalarCalculation):
            autoModifier = common.ScalarCalculation(
                value=autoModifier,
                name=f'{componentString} Auto Modifier')

        self._autoModifier = autoModifier

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with single shot or semi-automatic launchers
        return not context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSingleShotLauncherReceiver,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.LightSemiAutomaticLauncherReceiver,
                sequence=sequence) \
            and not context.hasComponent(
                componentType=gunsmith.StandardSemiAutomaticLauncherReceiver,
                sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        if self._autoModifier:
            step.addFactor(factor=construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Auto,
                modifier=construction.ConstantModifier(
                    value=self._autoModifier)))

        return step

class BurstCapableMechanism(AutoMechanism):
    """
    - Min TL: 6
    - Receiver Cost: +10%
    - Trait: Auto (2)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. I've gone with TL 6 as that's the min TL for a Submachine Gun in
    # the Core Rules p118

    def __init__(self) -> None:
        super().__init__(
            componentString='Burst-capable',
            minTechLevel=6,
            costModifierPercentage=+10,
            autoModifier=+2)

class FullyAutomaticMechanism(AutoMechanism):
    """
    - Min TL: 6
    - Receiver Cost: +20%
    - Trait: Auto (3)
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. I've gone with TL 6 as that's the min TL for a Submachine Gun in
    # the Core Rules p118

    def __init__(self) -> None:
        super().__init__(
            componentString='Fully Automatic',
            minTechLevel=6,
            costModifierPercentage=+20,
            autoModifier=+3)

# This mechanism was created by me to model the mechanical rotary setup described on p41 of the
# Field Catalogue
class MechanicalRotaryMechanism(AutoMechanism):
    """
    - Min TL: 5
    - Trait: Auto equal to barrel count / 2
    - Requirement: Only compatible with a multi-barrel setup
    """
    # NOTE: I can't find anything in the Field Catalogue the says at which TL different conventional
    # mechanisms become available. It's not obvious what TL mechanical rotary weapons would become
    # available, in our time line they're roughly contemporary with repeating revolvers so I've gone
    # with the same TL 5

    _BarrelDivisor = common.ScalarCalculation(
        value=2,
        name='Mechanical Rotary Barrels Required Per Auto Level'
    )

    def __init__(self) -> None:
        super().__init__(
            componentString='Mechanical Rotary',
            minTechLevel=5)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.MultiBarrel,
            sequence=sequence)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        barrelCount = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.BarrelCount)
        assert(isinstance(barrelCount, common.ScalarCalculation)) # Construction logic should enforce this

        autoModifier = common.Calculator.divideFloor(
            lhs=barrelCount,
            rhs=self._BarrelDivisor,
            name=f'{self.componentString()} Auto Modifier')

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Auto,
            modifier=construction.ConstantModifier(
                value=autoModifier)))

        return step
