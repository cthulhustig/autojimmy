import common
import enum
import gunsmith
import typing

class _AttachmentType(enum.Enum):
    Fixed = 'Fixed'
    Attached = 'Attached'
    Detached = 'Detached'


_AttachmentOptionDescription = \
    '<p>Specify how the accessory is attached to the weapon.</p>' \
    '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">' \
    '<li><b>Fixed</b> - The accessory is permanently attached to the weapon.</li>' \
    '<li><b>Attached</b> - The accessory is currently attached to the weapon but can be removed if required.</li>' \
    '<li><b>Detached</b> - The accessory is currently detached from the weapon and will have no affect on it.</li>' \
    '</ul>'


# ███████████                                         ████
#░░███░░░░░███                                       ░░███
# ░███    ░███  ██████   ████████  ████████   ██████  ░███
# ░██████████  ░░░░░███ ░░███░░███░░███░░███ ███░░███ ░███
# ░███░░░░░███  ███████  ░███ ░░░  ░███ ░░░ ░███████  ░███
# ░███    ░███ ███░░███  ░███      ░███     ░███░░░   ░███
# ███████████ ░░████████ █████     █████    ░░██████  █████
#░░░░░░░░░░░   ░░░░░░░░ ░░░░░     ░░░░░      ░░░░░░  ░░░░░

class BarrelAccessory(gunsmith.BarrelAccessoryInterface):
    _AttachmentOptionDescription = \
        '<p>Specify how the accessory is attached to the weapon.</p>' \
        '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">' \
        '<li><b>Fixed</b> - The accessory is permanently attached to the weapon.</li>' \
        '<li><b>Attached</b> - The accessory is currently attached to the weapon but can be removed if required.</li>' \
        '<li><b>Detached</b> - The accessory is currently detached from the weapon and will have no affect on it.</li>' \
        '</ul>'

    def __init__(
            self,
            componentString: str,
            defaultAttachType: typing.Optional[_AttachmentType],
            minTechLevel: typing.Optional[int] = None
            ) -> None:
        super().__init__()

        self._componentString = componentString
        self._minTechLevel = minTechLevel

        self._attachedOption = gunsmith.EnumComponentOption(
            id='Attachment',
            name='Attachment',
            type=_AttachmentType,
            value=defaultAttachType,
            description=BarrelAccessory._AttachmentOptionDescription,
            enabled=defaultAttachType != None)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Barrel Accessory'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if self._minTechLevel != None:
            if context.techLevel() < self._minTechLevel:
                return False

        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.ReceiverInterface,
                sequence=sequence):
            return False

        # Don't allow multiple accessories of the same type in this sequence
        return not context.hasComponent(
            componentType=type(self),
            sequence=sequence)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = []
        if self._attachedOption.isEnabled():
            options.append(self._attachedOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

    def isDetachable(self) -> bool:
        # Accessory is detachable if the option to attach it exists and the user hasn't set it
        # to be permanently attached
        return self._attachedOption.isEnabled() and \
            (self._attachedOption.value() != _AttachmentType.Fixed)

    def isAttached(self) -> bool:
        if not self._attachedOption.isEnabled():
            return True # Accessories of this type don't give the user the option to detach
        return self._attachedOption.value() != _AttachmentType.Detached

    def setAttached(self, attached: bool) -> None:
        if not self._attachedOption.isEnabled() or \
                (self._attachedOption.value() == _AttachmentType.Fixed):
            # Don't update attached state if accessory isn't detachable
            return

        self._attachedOption.setValue(
            value=_AttachmentType.Attached if attached else _AttachmentType.Detached)

class SuppressorAccessory(BarrelAccessory):
    def __init__(
            self,
            componentString: str,
            fixedWeight: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            receiverCostPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            physicalSignatureModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            rangeModifierPercentage: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            quickdrawModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            penetrationModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            inaccurateModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            defaultAttachType=_AttachmentType.Attached)

        if fixedWeight != None and not isinstance(fixedWeight, common.ScalarCalculation):
            fixedWeight = common.ScalarCalculation(
                value=fixedWeight,
                name=f'{componentString} Weight')

        if receiverCostPercentage != None and not isinstance(receiverCostPercentage, common.ScalarCalculation):
            receiverCostPercentage = common.ScalarCalculation(
                value=receiverCostPercentage,
                name=f'{componentString} Receiver Cost Percentage')

        if physicalSignatureModifier != None and not isinstance(physicalSignatureModifier, common.ScalarCalculation):
            physicalSignatureModifier = common.ScalarCalculation(
                value=physicalSignatureModifier,
                name=f'{componentString} Physical Signature Modifier')

        if rangeModifierPercentage != None and not isinstance(rangeModifierPercentage, common.ScalarCalculation):
            rangeModifierPercentage = common.ScalarCalculation(
                value=rangeModifierPercentage,
                name=f'{componentString} Range Modifier Percentage')

        if quickdrawModifier != None and not isinstance(quickdrawModifier, common.ScalarCalculation):
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name=f'{componentString} Quickdraw Modifier')

        if penetrationModifier != None and not isinstance(penetrationModifier, common.ScalarCalculation):
            penetrationModifier = common.ScalarCalculation(
                value=penetrationModifier,
                name=f'{componentString} Quickdraw Modifier')

        if inaccurateModifier != None and not isinstance(inaccurateModifier, common.ScalarCalculation):
            inaccurateModifier = common.ScalarCalculation(
                value=inaccurateModifier,
                name=f'{componentString} Inaccurate Modifier')

        self._fixedWeight = fixedWeight
        self._receiverCostPercentage = receiverCostPercentage
        self._physicalSignatureModifier = physicalSignatureModifier
        self._rangeModifierPercentage = rangeModifierPercentage
        self._quickdrawModifier = quickdrawModifier
        self._penetrationModifier = penetrationModifier
        self._inaccurateModifier = inaccurateModifier

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return not context.hasComponent(
            componentType=gunsmith.ArchaicCalibre,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        cost = None
        weight = None
        operations = []

        if self._receiverCostPercentage:
            cost = gunsmith.ConstantModifier(
                value=common.Calculator.takePercentage(
                    value=context.receiverCredits(sequence=sequence),
                    percentage=self._receiverCostPercentage,
                    name=f'{self.componentString()} Cost'))

        if self.isAttached():
            if self._fixedWeight:
                weight = gunsmith.ConstantModifier(value=self._fixedWeight)

            if self._physicalSignatureModifier:
                # Only apply signature modification if the weapon actually has a physical signature
                if context.hasAttribute(
                        sequence=sequence,
                        attributeId=gunsmith.AttributeId.PhysicalSignature):
                    operations.append(gunsmith.ModifyAttributeFactor(
                        attributeId=gunsmith.AttributeId.PhysicalSignature,
                        modifier=gunsmith.ConstantModifier(
                            value=self._physicalSignatureModifier)))

            if self._rangeModifierPercentage:
                operations.append(gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Range,
                    modifier=gunsmith.PercentageModifier(
                        value=self._rangeModifierPercentage)))

            if self._quickdrawModifier:
                operations.append(gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Quickdraw,
                    modifier=gunsmith.ConstantModifier(
                        value=self._quickdrawModifier)))

            if self._penetrationModifier:
                operations.append(gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Penetration,
                    modifier=gunsmith.ConstantModifier(
                        value=self._penetrationModifier)))

            if self._inaccurateModifier:
                operations.append(gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Inaccurate,
                    modifier=gunsmith.ConstantModifier(
                        value=self._inaccurateModifier)))

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=cost,
            weight=weight,
            factors=operations)
        context.applyStep(
            sequence=sequence,
            step=step)

class BasicSuppressorAccessory(SuppressorAccessory):
    """
    - Cost: 50% of Receiver Cost
    - Weight: +0.2kg (when attached)
    - Range: -25% (when attached)
    - Quickdraw: -2 (when attached)
    - Physical Signature: Reduced by 1 level (when attached)
    - Trait: Inaccurate (-1) (when attached)
    - Requirement: Not compatible with Archaic calibre
    """
    # NOTE: Requirement is handled by base class

    def __init__(self) -> None:
        super().__init__(
            componentString='Suppressor (Basic)',
            fixedWeight=0.2,
            receiverCostPercentage=50,
            physicalSignatureModifier=-1,
            rangeModifierPercentage=-25,
            quickdrawModifier=-2,
            inaccurateModifier=-1)

class StandardSuppressorAccessory(SuppressorAccessory):
    """
    - Cost: 100% of Receiver Cost
    - Weight: +0.3kg (when attached)
    - Range: -50% (when attached)
    - Quickdraw: -3 (when attached)
    - Penetration: -1 (when attached)
    - Physical Signature: Reduced by 2 level (when attached)
    - Trait: Inaccurate (-1) (when attached)
    - Requirement: Not compatible with Archaic calibre
    """
    # NOTE: Requirement is handled by base class

    def __init__(self) -> None:
        super().__init__(
            componentString='Suppressor (Standard)',
            fixedWeight=0.3,
            receiverCostPercentage=100,
            physicalSignatureModifier=-2,
            rangeModifierPercentage=-50,
            quickdrawModifier=-3,
            penetrationModifier=-1,
            inaccurateModifier=-1)

class ExtremeSuppressorAccessory(SuppressorAccessory):
    """
    - Cost: 200% of Receiver Cost
    - Weight: +0.5kg (when attached)
    - Range: -75% (when attached)
    - Quickdraw: -4 (when attached)
    - Penetration: -2 (when attached)
    - Physical Signature: Reduced by 3 level (when attached)
    - Trait: Inaccurate (-1) (when attached)
    - Requirement: Not compatible with Archaic calibre
    """
    # NOTE: Requirement is handled by base class

    def __init__(self) -> None:
        super().__init__(
            componentString='Suppressor (Extreme)',
            fixedWeight=0.5,
            receiverCostPercentage=200,
            physicalSignatureModifier=-3,
            rangeModifierPercentage=-75,
            quickdrawModifier=-4,
            penetrationModifier=-2,
            inaccurateModifier=-1)


# This isn't listed in the Accessories section, it comes from the Weapon Mounted
# Launchers section (Field Catalogue p41). It allows a one-shot rocket propelled
# grenade to be mounted to the muzzle and launched by firing a round
class MuzzleDischargerAccessory(BarrelAccessory):
    """
    - TL 5+ (Field Catalogue p58)
    - Weight: 0.05kg
    - Cost: Cr75
    - Note: DM-3 to Quickdraw checks with rocket propelled grenade in place
    - Note: Weapon can't be fired normally with rocket propelled grenade in place
    - Requirement: Only compatible with Conventional Weapons
    """
    # NOTE: I've added the requirement that it's only compatible with conventional
    # weapons as it wouldn't work for other kind of weapons
    _FixedWeight = common.ScalarCalculation(
        value=0.05,
        name='Muzzle Discharger Weight')
    _FixedCost = common.ScalarCalculation(
        value=75,
        name='Muzzle Discharger Cost')
    _Notes = [
        'DM-3 to Quickdraw checks with rocket propelled grenade in place',
        'Weapon can\'t be fired normally with rocket propelled grenade in place'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Muzzle Discharger',
            defaultAttachType=_AttachmentType.Attached,
            minTechLevel=5)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=gunsmith.ConstantModifier(value=self._FixedCost))

        for note in self._Notes:
            step.addNote(note=note)

        if self.isAttached():
            step.setWeight(weight=gunsmith.ConstantModifier(
                value=self._FixedWeight))

        context.applyStep(
            sequence=sequence,
            step=step)

# This isn't listed in the Accessories section, it comes from the Weapon Mounted
# Launchers section (Field Catalogue p41). It allows a regular grenade to be mounted
# to the muzzle and launched by firing a blank round
class CupDischargerAccessory(BarrelAccessory):
    """
    - TL 5+ (Field Catalogue p58)
    - Weight: 0.15kg
    - Cost: Cr50
    - Quickdraw: -2
    - Note: Additional Quickdraw -2 modifier when grenade in place
    - Note: Weapon can't be fired normally with grenade in place
    - Requirement: Only compatible with Conventional Weapons
    """
    # NOTE: I've added the requirement that it's only compatible with conventional
    # weapons as it wouldn't work for other kind of weapons
    _FixedWeight = common.ScalarCalculation(
        value=0.15,
        name='Cup Discharger Weight')
    _FixedCost = common.ScalarCalculation(
        value=50,
        name='Cup Discharger Cost')
    _QuickdrawModifier = common.ScalarCalculation(
        value=-2,
        name='Cup Discharger Quickdraw modifier')
    _Notes = [
        'DM-2 to Quickdraw checks when grenade in place. This is in addition to the DM-2 to Quickdraw checks that comes from having the Cup discharger attached to the weapon.',
        'Weapon can\'t be fired normally with grenade in place'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Cup Discharger',
            defaultAttachType=_AttachmentType.Attached,
            minTechLevel=5)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=gunsmith.ConstantModifier(value=self._FixedCost))

        for note in self._Notes:
            step.addNote(note=note)

        if self.isAttached():
            step.setWeight(weight=gunsmith.ConstantModifier(
                value=self._FixedWeight))

            step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.Quickdraw,
                modifier=gunsmith.ConstantModifier(
                    value=self._QuickdrawModifier)))

        context.applyStep(
            sequence=sequence,
            step=step)


# █████   ███   █████
#░░███   ░███  ░░███
# ░███   ░███   ░███   ██████   ██████   ████████   ██████  ████████
# ░███   ░███   ░███  ███░░███ ░░░░░███ ░░███░░███ ███░░███░░███░░███
# ░░███  █████  ███  ░███████   ███████  ░███ ░███░███ ░███ ░███ ░███
#  ░░░█████░█████░   ░███░░░   ███░░███  ░███ ░███░███ ░███ ░███ ░███
#    ░░███ ░░███     ░░██████ ░░████████ ░███████ ░░██████  ████ █████
#     ░░░   ░░░       ░░░░░░   ░░░░░░░░  ░███░░░   ░░░░░░  ░░░░ ░░░░░
#                                        ░███
#                                        █████
#                                       ░░░░░

class WeaponAccessory(gunsmith.WeaponAccessoryInterface):
    def __init__(
            self,
            componentString: str,
            defaultAttachType: typing.Optional[_AttachmentType],
            minTechLevel: typing.Optional[int] = None
            ) -> None:
        super().__init__()

        self._componentString = componentString
        self._minTechLevel = minTechLevel

        self._attachedOption = gunsmith.EnumComponentOption(
            id='Attachment',
            name='Attachment',
            type=_AttachmentType,
            value=defaultAttachType,
            description=_AttachmentOptionDescription,
            enabled=defaultAttachType != None)

    def componentString(self) -> str:
        return self._componentString

    def typeString(self) -> str:
        return 'Weapon Accessory'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if self._minTechLevel != None:
            if context.techLevel() < self._minTechLevel:
                return False

        # Only compatible with weapons that have a receiver. A whole weapon search is used as
        # this is a common component so it can be any of the weapon sequences
        if not context.hasComponent(
                componentType=gunsmith.ReceiverInterface,
                sequence=None):
            return False

        # Don't allow multiple accessories of the same type. This is a common component s a whole
        # weapon search is redundant but it's done for clarity
        return not context.hasComponent(
            componentType=type(self),
            sequence=None)

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = []
        if self._attachedOption.isEnabled():
            options.append(self._attachedOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        pass

    def isDetachable(self) -> bool:
        # Accessory is detachable if the option to attach it exists and the user hasn't set it
        # to be permanently attached
        return self._attachedOption.isEnabled() and \
            (self._attachedOption.value() != _AttachmentType.Fixed)

    def isAttached(self) -> bool:
        if not self._attachedOption.isEnabled():
            return True # Accessories of this type don't give the user the option to detach
        return self._attachedOption.value() != _AttachmentType.Detached

    def setAttached(self, attached: bool) -> None:
        if not self._attachedOption.isEnabled() or \
                (self._attachedOption.value() == _AttachmentType.Fixed):
            # Don't update attached state if accessory isn't detachable
            return

        self._attachedOption.setValue(
            value=_AttachmentType.Attached if attached else _AttachmentType.Detached)

class SightAccessory(WeaponAccessory):
    def __init__(
            self,
            componentString: str,
            defaultAttachType: typing.Optional['_AttachmentType'] = _AttachmentType.Fixed,
            minTechLevel: typing.Optional[int] = None,
            fixedWeight: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            fixedCost: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            quickdrawModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            scopeTrait: bool = False,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            componentString=componentString,
            defaultAttachType=defaultAttachType,
            minTechLevel=minTechLevel)

        if fixedWeight != None and not isinstance(fixedWeight, common.ScalarCalculation):
            fixedWeight = common.ScalarCalculation(
                value=fixedWeight,
                name=f'{componentString} Weight')

        if fixedCost != None and not isinstance(fixedCost, common.ScalarCalculation):
            fixedCost = common.ScalarCalculation(
                value=fixedCost,
                name=f'{componentString} Cost')

        if quickdrawModifier != None:
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name=f'{componentString} Quickdraw Modifier')

        self._fixedWeight = fixedWeight
        self._fixedCost = fixedCost
        self._quickdrawModifier = quickdrawModifier
        self._scopeTrait = scopeTrait
        self._notes = notes

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        if self._fixedCost:
            step.setCredits(credits=gunsmith.ConstantModifier(value=self._fixedCost))

        if self.isAttached():
            if self._fixedWeight:
                step.setWeight(weight=gunsmith.ConstantModifier(value=self._fixedWeight))

            # Only apply the quickdraw modifier to the primary as this is a weapon feature so it should
            # only be included once
            if self._quickdrawModifier and context.isPrimary(sequence=sequence):
                step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                    attributeId=gunsmith.AttributeId.Quickdraw,
                    modifier=gunsmith.ConstantModifier(
                        value=self._quickdrawModifier)))

            if self._scopeTrait:
                step.addFactor(factor=gunsmith.SetAttributeFactor(
                    attributeId=gunsmith.AttributeId.Scope))

            if self._notes:
                for note in self._notes:
                    step.addNote(note=note)

        context.applyStep(
            sequence=sequence,
            step=step)

class ReflexSightAccessory(SightAccessory):
    """
    - Min TL: 6
    - Note: Attack DM+1 when aiming or snap shooting
    - Note: Quickdraw is halved if sight is used
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Reflex)',
            minTechLevel=6,
            notes=[
                'DM+1 to attack rolls when aiming or snap shooting',
                'Quickdraw is halved if sight is used'
            ])

class ScopeAccessory(SightAccessory):
    """
    - Min TL: 5
    - Cost: Cr50
    - Weight: 0.2kg
    - Note: Quickdraw -2 when mounted
    - Trait: Scope
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Scope)',
            minTechLevel=5,
            fixedWeight=0.2,
            fixedCost=50,
            quickdrawModifier=-2,
            scopeTrait=True)

class LongRangeScopeAccessory(SightAccessory):
    """
    - Min TL: 6
    - Cost: Cr500
    - Weight: 0.5kg
    - Trait: Scope
    - Note: Quickdraw -2 when mounted
    - Note: Reduces any negative DM due to range by -2 when aiming
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Long Range Scope)',
            minTechLevel=6,
            fixedWeight=0.5,
            fixedCost=500,
            quickdrawModifier=-2,
            scopeTrait=True,
            notes=['Reduces any negative DM due to range by -2 when aiming'])

class LowLightScopeAccessory(SightAccessory):
    """
    - Min TL: 6
    - Cost: Cr150
    - Weight: 0.4kg
    - Trait: Scope
    - Note: Quickdraw -2 when mounted
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Low Light Scope)',
            minTechLevel=6,
            fixedWeight=0.4,
            fixedCost=150,
            quickdrawModifier=-2,
            scopeTrait=True)


_ThermalScopeNote = 'DM+4 to Recon checks to spot concealed targets, locate the source of a shot, and so forth'
class ThermalScopeAccessory(SightAccessory):
    """
    - Min TL: 6
    - Cost: Cr250
    - Weight: 0.25kg
    - Note: Quickdraw -2 when mounted
    - Note: DM+4 to Recon checks to spot concealed targets, locate the source of a shot, and so forth
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Thermal Scope)',
            minTechLevel=6,
            fixedWeight=0.25,
            fixedCost=250,
            quickdrawModifier=-2,
            notes=[_ThermalScopeNote])

class CombinedScopeAccessory(SightAccessory):
    """
    - Min TL: 7
    - Cost: Cr400
    - Weight: 0.5kg
    - Trait: Scope
    - Note: Quickdraw -2 when mounted
    - Note: Same notes as Low Light and Thermal Scopes
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Combined Scope)',
            minTechLevel=7,
            fixedWeight=0.5,
            fixedCost=400,
            quickdrawModifier=-2,
            scopeTrait=True,
            notes=[_ThermalScopeNote])


_MultispectralScopeNote1 = 'DM+6 to Recon checks to spot concealed targets, locate the source of a shot, and so forth'
_MultispectralScopeNote2 = 'DM+1 to attack rolls at all ranges when aiming'
class MultispectralScopeAccessory(SightAccessory):
    """
    - Min TL: 9
    - Cost: Cr600
    - Weight: 0.5kg
    - Trait: Scope
    - Note: Quickdraw -2 when mounted
    - Note: Same notes as Low Light Scope
    - Note: DM+6 to Recon checks to spot concealed targets, locate the source of a shot, and so forth
    - Note: Attack DM+1 at all ranges
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Multispectral Scope)',
            minTechLevel=9,
            fixedWeight=0.5,
            fixedCost=600,
            quickdrawModifier=-2,
            scopeTrait=True,
            notes=[_MultispectralScopeNote1, _MultispectralScopeNote2])

class LaserPointerAccessory(SightAccessory):
    """
    - Min TL: 8
    - Cost: Cr200
    - Weight: 0.1kg
    - Note: DM+1 to attack rolls at ranges <= 50m
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Laser Pointer)',
            minTechLevel=8,
            fixedWeight=0.1,
            fixedCost=200,
            notes=['DM+1 to attack rolls at ranges <= 50m'])

class IntegratedSightingSystemAccessory(SightAccessory):
    """
    - Min TL: 10
    - Cost: Cr500
    - Weight: 0.4kg
    - Trait: Scope
    - Note: DM+6 to Recon checks to spot concealed targets, locate the source of a shot, and so forth
    - Note: DM+1 to attack rolls at all ranges when aiming
    """
    # NOTE: The description for the ISS (Field Catalogue p46) says it gives all the _benefits_ of the
    # Multispectral Scope but doesn't. I'm taking this to mean it doesn't have the same negative
    # Quickdraw modifier
    # NOTE: I've made the ISS permanent by default as it's integrated into the weapon. However the rules
    # don't say you can't remove it so i've still allowed it to be detached

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (ISS)',
            defaultAttachType=_AttachmentType.Fixed,
            minTechLevel=10,
            fixedWeight=0.4,
            fixedCost=500,
            scopeTrait=True,
            notes=[_MultispectralScopeNote1, _MultispectralScopeNote2])

class HolographicSightAccessory(SightAccessory):
    """
    - Min TL: 12
    - Cost: Cr750
    - Trait: Scope
    """
    # NOTE: The description (Field Catalogue p46) doesn't explicitly say that a
    # Holographic Sight give the Scope trait but it does say that it can display a
    # scope and allows magnification. The example on p107 also shows it giving the
    # Scope trait

    def __init__(self) -> None:
        super().__init__(
            componentString='Sight (Holographic)',
            minTechLevel=12,
            fixedCost=750,
            scopeTrait=True)

class BayonetLugAccessory(WeaponAccessory):
    """
    - Note: DM-2 to Quickdraw checks when bayonet fitted
    """
    # NOTE: I've made the bayonet lug permanently attached by default as there doesn't seem any
    # point in making it detachable. However the rules don't say you can't so I've left it as
    # configurable.
    # NOTE: I've added the a weapon accessory as it only really makes sense for it to be something
    # attached to the weapon as a whole

    _Note = 'DM-2 to Quickdraw checks when bayonet fitted'

    def __init__(self) -> None:
        super().__init__(
            componentString='Bayonet Lug',
            defaultAttachType=_AttachmentType.Fixed)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            notes=[self._Note])
        context.applyStep(
            sequence=sequence,
            step=step)

class BlingAccessory(WeaponAccessory):
    """
    - Cost: This can be whatever the Traveller wants
    """
    # NOTE: I've made bling permanently attached by default as stuff like chrome plating isn't
    # detachable. I've left it as configurable as you never know, maybe someones idea of bling is
    # furry dice hanging off the end of the barrel (which could be detached)/
    # NOTE: I've made this a weapon accessory as it only really makes sense for it to be something
    # attached to the weapon as a whole

    def __init__(self) -> None:
        super().__init__(
            componentString='Bling',
            defaultAttachType=_AttachmentType.Fixed)

        self._costOption = gunsmith.FloatComponentOption(
            id='Cost',
            name='Cost',
            value=0,
            minValue=0,
            description='Specify the amount to the accessory.')

    def options(self) -> typing.List[gunsmith.ComponentOption]:
        options = super().options()
        options.append(self._costOption)
        return options

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        cost = common.ScalarCalculation(
            value=self._costOption.value(),
            name='Specified Cost')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=gunsmith.ConstantModifier(value=cost))

        context.applyStep(
            sequence=sequence,
            step=step)

class FlashlightAccessory(WeaponAccessory):
    """
    - Cost: Cr50
    - Note: Quickdraw -2 when fitted
    """
    # NOTE: I've made this a weapon accessory as it only really makes sense for it to be something
    # attached to the weapon as a whole

    _FixedCost = common.ScalarCalculation(
        value=50,
        name='Flashlight Cost')
    _QuickdrawModifier = common.ScalarCalculation(
        value=-2,
        name='Flashlight Quickdraw Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Flashlight',
            defaultAttachType=_AttachmentType.Attached)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        cost = gunsmith.ConstantModifier(value=self._FixedCost)
        operations = []

        # Only apply the quickdraw modifier to the primary as this is a weapon feature so it should
        # only be included once
        if self.isAttached() and context.isPrimary(sequence=sequence):
            operations.append(gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.Quickdraw,
                modifier=gunsmith.ConstantModifier(
                    value=self._QuickdrawModifier)))

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=cost,
            factors=operations)
        context.applyStep(
            sequence=sequence,
            step=step)

class GraviticSystemAccessory(WeaponAccessory):
    """
    - Min TL: 12
    - Cost: Cr2500 per kg of the Weapon
    - Weight: x3 Weapon Weight (when switched off)
    - Trait: Very Bulky becomes Bulky, Bulky is removed entirely
    - Note: Negates wait of Weapon when enabled
    """
    # NOTE: I've made this a weapon accessory as it only really makes sense to apply
    # it to the weapon as a whole.
    # NOTE: It's not clear if the weapon weight when calculating cost should include
    # the weight of accessories. I've chosen not to include accessory weight as there
    # would be ordering issues due to this being an accessory. I don't think it really
    # matters if it doesn't take the full weight into account as the weight of
    # accessories should be negligible.
    # NOTE: It's not clear if the grav system should be detachable or not. As I don't
    # know it's better to allow it
    _MinTechLevel = 12
    _WeaponWeightMultiplier = common.ScalarCalculation(
        value=3,
        name='Gravitic System Weapon Weight Multiplier')
    _PerWeaponKgCost = common.ScalarCalculation(
        value=2500,
        name='Gravitic System Cost Per Weapon kg')
    _Notes = [
        'Negates weight of weapon when system is enabled',
        'Very Bulky becomes Bulky and Bulky is removed when system is enabled'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Gravitic System',
            defaultAttachType=_AttachmentType.Fixed,
            minTechLevel=self._MinTechLevel)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        weaponWeight = context.baseWeight(sequence=None) # Use whole weapon base weight
        step.setCredits(credits=gunsmith.ConstantModifier(
            value=common.Calculator.multiply(
                lhs=weaponWeight,
                rhs=self._PerWeaponKgCost,
                name='Gravitic System Cost')))

        if self.isAttached():
            step.setWeight(weight=gunsmith.ConstantModifier(
                value=common.Calculator.multiply(
                    lhs=weaponWeight,
                    rhs=self._WeaponWeightMultiplier,
                    name='Gravitic System Weight')))

            for notes in self._Notes:
                step.addNote(note=notes)

        context.applyStep(
            sequence=sequence,
            step=step)

class GunCameraAccessory(WeaponAccessory):
    """
    - Cost: Cr75
    - Requirement: Not compatible with other gun cameras
    """
    # NOTE: I've made this a weapon accessory as it only really makes sense for it to be something
    # attached to the weapon as a whole

    _FixedCost = common.ScalarCalculation(
        value=75,
        name='Gun Camera Cost')

    def __init__(
            self,
            componentString: str,
            minTechLevel: int,
            ) -> None:
        super().__init__(
            componentString=componentString,
            defaultAttachType=_AttachmentType.Attached,
            minTechLevel=minTechLevel)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Not compatible with other gun cameras
        return not context.hasComponent(
            componentType=gunsmith.GunCameraAccessory,
            sequence=None) # Whole weapon search

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.WeaponStep:
        return gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=gunsmith.ConstantModifier(value=self._FixedCost))

class LowTechGunCameraAccessory(GunCameraAccessory):
    """
    - TL 6-7 Camera
        - Cost: Cr75
        - Note: Quickdraw -2 when fitted
    """
    # NOTE: Cost is handled by base class as it's the same for all gun cameras
    _QuickdrawModifier = common.ScalarCalculation(
        value=-2,
        name='Gun Camera (TL 6-7) Quickdraw Modifier')

    def __init__(self) -> None:
        super().__init__(
            componentString='Gun Camera (TL 6-7)',
            minTechLevel=6)

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        # Only apply the quickdraw modifier to the primary as this is a weapon feature so it should
        # only be included once
        if self.isAttached() and context.isPrimary(sequence=sequence):
            step.addFactor(factor=gunsmith.ModifyAttributeFactor(
                attributeId=gunsmith.AttributeId.Quickdraw,
                modifier=gunsmith.ConstantModifier(
                    value=self._QuickdrawModifier)))

        return step

class HighTechGunCameraAccessory(GunCameraAccessory):
    """
    - TL 8+ Camera
        - Cost: Cr75
    """
    # NOTE: Cost is handled by base class as it's the same for all gun cameras

    def __init__(self) -> None:
        super().__init__(
            componentString='Gun Camera (TL 8+)',
            minTechLevel=8)

# Treating Bipod and Support Mount as accessories. This seems to be how it's done in the Field
# Catalogue (see p96 for an example)
class BipodAccessory(WeaponAccessory):
    """
    - Cost: 10% of Receiver Price for fixed or 15% for detachable
    - Weight: 20% of Receiver Weight
    - Quickdraw: -4 (unless weapon is already on target)
    - Note: DM+1 to attack rolls at ranges > 50m when Bipod is deployed
    - Requirement: Must have Rifle, Long or Very Long Barrel
    - Requirement: Not compatible with other Bipod accessories
    """
    # NOTE: I'm handling the Quckdraw modifier as a note as it doesn't always apply
    # NOTE: I've made this a weapon accessory as it only really makes sense as something that's
    # applied to the weapon as a whole

    _FixedBipodReceiverCostPercentage = common.ScalarCalculation(
        value=10,
        name='Fixed Bipod Receiver Cost Percentage')
    _DetachableBipodReceiverCostPercentage = common.ScalarCalculation(
        value=15,
        name='Detachable Bipod Receiver Cost Percentage')
    _ReceiverWeightPercentage = common.ScalarCalculation(
        value=20,
        name='Bipod Receiver Weight Percentage')
    _Notes = [
        'DM+1 to attack rolls at ranges > 50m when Bipod is deployed',
        'DM-4 to Quickdraw checks unless weapon is already on target'
    ]

    def __init__(self) -> None:
        super().__init__(
            componentString='Bipod',
            defaultAttachType=_AttachmentType.Fixed)

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False

        # Only compatible with rifle barrel and longer. A whole weapon search is performed as it
        # can be any weapon sequence that has the barrel
        barrels = context.findComponents(
            componentType=gunsmith.Barrel,
            sequence=None) # Whole weapon search
        if not barrels:
            return False
        hasRequiredBarrel = False
        for barrel in barrels:
            hasRequiredBarrel = \
                isinstance(barrel, gunsmith.RifleBarrel) or \
                isinstance(barrel, gunsmith.LongBarrel) or \
                isinstance(barrel, gunsmith.VeryLongBarrel)
            if hasRequiredBarrel:
                break
        if not hasRequiredBarrel:
            return False

        # Not compatible with other bipod accessories
        return not context.hasComponent(
            componentType=gunsmith.BipodAccessory,
            sequence=None) # Whole weapon search

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        receiverCostPercentage = \
            self._DetachableBipodReceiverCostPercentage \
            if self.isDetachable() else \
            self._FixedBipodReceiverCostPercentage

        cost = common.Calculator.takePercentage(
            value=context.receiverCredits(sequence=None), # Use cost of all receivers
            percentage=receiverCostPercentage,
            name=f'{self.componentString()} Cost')
        step.setCredits(credits=gunsmith.ConstantModifier(value=cost))

        if self.isAttached():
            weight = common.Calculator.takePercentage(
                value=context.receiverWeight(sequence=None), # Use weight of all receivers
                percentage=self._ReceiverWeightPercentage,
                name=f'{self.componentString()} Weight')
            step.setWeight(weight=gunsmith.ConstantModifier(value=weight))

            for note in self._Notes:
                step.addNote(note=note)

        context.applyStep(
            sequence=sequence,
            step=step)

# This isn't listed in the Accessories section, it comes from the Weapon Mounted
# Launchers section (Field Catalogue p41). It allows a one-shot rocket propelled
# grenade to be mounted under the barrel
class UnderBarrelRailAccessory(WeaponAccessory):
    """
    - TL 5+ (Field Catalogue p58)
    - Weight: 0.1kg
    - Cost: Cr100
    - Note: DM-3 to Quickdraw checks with rocket propelled grenade in place
    """
    # NOTE: I've made this a weapon accessory as it it only really makes sense for it to be something
    # applied to the weapon as a whole. Which barrel it's attached to doesn't really matter from a
    # construction point of view

    _FixedWeight = common.ScalarCalculation(
        value=0.1,
        name='Under Barrel Rail Weight')
    _FixedCost = common.ScalarCalculation(
        value=100,
        name='Under Barrel Rail Cost')
    _Note = 'DM-3 to Quickdraw checks with rocket propelled grenade in place'

    def __init__(self) -> None:
        super().__init__(
            componentString='Under Barrel Rail',
            defaultAttachType=_AttachmentType.Fixed,
            minTechLevel=5)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString(),
            credits=gunsmith.ConstantModifier(value=self._FixedCost))

        if self.isAttached():
            step.setWeight(weight=gunsmith.ConstantModifier(
                value=self._FixedWeight))
            step.addNote(note=self._Note)

        context.applyStep(
            sequence=sequence,
            step=step)

class LaserDesignatorAccessory(WeaponAccessory):
    """
    - Min TL: 9
    - Weight: 0.2kg
    - Cost: Cr1000
    - Note: Can also act as a range finder
    """
    # NOTE: This isn't listed under the normal accessories, it's under the equipment on p139 of the
    # Field Catalogue.
    # NOTE: I've made this a weapon accessory as it only really makes sense for it to be something
    # applied to the weapon as a whole.
    _FixedWeight = common.ScalarCalculation(
        value=0.2,
        name='Laser Designator Weight')
    _FixedCost = common.ScalarCalculation(
        value=1000,
        name='Laser Designator Cost')
    _Note = 'Laser Designator can also act as a range finder'

    def __init__(self) -> None:
        super().__init__(
            componentString='Laser Designator',
            defaultAttachType=_AttachmentType.Attached,
            minTechLevel=9)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.ConstructionContextInterface
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())
        step.setCredits(credits=gunsmith.ConstantModifier(value=self._FixedCost))

        if self.isAttached():
            step.setWeight(weight=gunsmith.ConstantModifier(value=self._FixedWeight))
            step.addNote(note=self._Note)

        context.applyStep(
            sequence=sequence,
            step=step)
