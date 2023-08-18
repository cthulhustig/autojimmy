import common
import enum
import gunsmith
import typing

ConstructionDecimalPlaces = 3

class Signature(enum.Enum):
    Minimal = 'Minimal'
    Small = 'Small'
    Low = 'Low'
    Normal = 'Normal'
    High = 'High'
    VeryHigh = 'Very High'
    Extreme = 'Extreme'

class Distraction(enum.Enum):
    Small = 'Small'
    Minor = 'Minor'
    Typical = 'Typical'
    Potent = 'Potent'
    Overwhelming = 'Overwhelming'

class AttributeId(enum.Enum):
    # Attributes Used By All Weapons (Numeric unless otherwise stated)
    Range = 'Range'
    Damage = 'Damage' # This is a DiceRoll
    AmmoCapacity = 'Ammo Capacity'
    AmmoCost = 'Ammo Cost'
    Quickdraw = 'Quickdraw'
    BarrelCount = 'Barrel Count'

    # Optional Attributes (Numeric unless otherwise stated)
    Penetration = 'Penetration'
    HeatGeneration = 'Heat Generation'
    AutoHeatGeneration = 'Auto Heat Generation'
    HeatDissipation = 'Heat Dissipation'
    OverheatThreshold = 'Overheat Threshold'
    DangerHeatThreshold = 'Danger Heat Threshold'
    DisasterHeatThreshold = 'Disaster Heat Threshold'
    MalfunctionDM = 'Malfunction DM'
    Armour = 'Armour'

    # Conventional Specific Attributes
    Recoil = 'Recoil'
    AutoRecoil = 'Auto Recoil'

    # Projector Specific Attributes
    PropellantWeight = 'Propellant Weight'
    FuelWeight = 'Fuel Weight'
    PropellantCost = 'Propellant Cost Per Kg'
    FuelCost = 'Fuel Cost Per Kg'

    # Energy Weapon Specific Attributes
    MaxDamageDice = 'Max Damage Dice'
    PowerPerShot = 'Power Per Shot'
    Power = 'Power' # Only used by power pack energy weapons

    # Core Rules Flag Traits (Core Rules p75)
    Bulky = 'Bulky'
    VeryBulky = 'Very Bulky'
    Scope = 'Scope'
    Stun = 'Stun'
    ZeroG = 'Zero-G'

    # Field Catalogue Flag Traits
    Corrosive = 'Corrosive' # Field Catalogue p6 & p24

    # Hack Flag Traits
    RF = 'RF' # This is really a modifier on the Auto score
    VRF = 'VRF' # This is really a modifier on the Auto score

    # Core Rule Numeric Traits (Core Rules p6)
    AP = 'AP'
    Auto = 'Auto'
    Blast = 'Blast'

    # Field Catalogue Traits
    Hazardous = 'Hazardous' # Field Catalogue p6
    Inaccurate = 'Inaccurate' # Field Catalogue p7
    LoPen = 'Lo-Pen' # Field Catalogue p7
    Ramshackle = 'Ramshackle' # Field Catalogue p7
    SlowLoader = 'SlowLoader' # Field Catalogue p7
    Spread = 'Spread' # Field Catalogue p7
    Unreliable = 'Unreliable' # Field Catalogue p7
    PulseIntensity = 'Pulse Intensity' # Field Catalogue p25

    # Field Catalogue Enum Traits
    EmissionsSignature = 'Emissions Signature' # Field Catalogue p6
    PhysicalSignature = 'Physical Signature' # Field Catalogue p7
    Distraction = 'Distraction' # Field Catalogue p23

    # Hybrid Traits. These are generally a Numeric traits but can be a DiceRoll trait in some cases (e.g. when dealing with Projector Fuel.
    Burn = 'Burn' # Field Catalogue p6
    Incendiary = 'Incendiary' # Field Catalogue p7


TraitAttributeIds = [
    AttributeId.Bulky,
    AttributeId.VeryBulky,
    AttributeId.Scope,
    AttributeId.ZeroG,
    AttributeId.Corrosive,
    AttributeId.RF,
    AttributeId.VRF,
    AttributeId.Stun,
    AttributeId.Auto,
    AttributeId.Inaccurate,
    AttributeId.Hazardous,
    AttributeId.Unreliable,
    AttributeId.SlowLoader,
    AttributeId.Ramshackle,
    AttributeId.AP,
    AttributeId.LoPen,
    AttributeId.Spread,
    AttributeId.Blast,
    AttributeId.Incendiary,
    AttributeId.Burn,
    AttributeId.PulseIntensity,
    AttributeId.PhysicalSignature,
    AttributeId.EmissionsSignature,
    AttributeId.Distraction
]

ConventionalWeaponAttributeIds = [
    AttributeId.Range,
    AttributeId.Damage,
    AttributeId.AmmoCapacity,
    AttributeId.Quickdraw,
    AttributeId.Penetration,
    AttributeId.Recoil,
    AttributeId.AutoRecoil,
    AttributeId.AmmoCost,
    AttributeId.BarrelCount,
]

LauncherWeaponAttributeIds = [
    AttributeId.Range,
    AttributeId.Damage,
    AttributeId.AmmoCapacity,
    AttributeId.Quickdraw,
    AttributeId.AmmoCost,
    AttributeId.BarrelCount
]

PowerPackEnergyWeaponAttributeIds = [
    AttributeId.Range,
    AttributeId.Damage,
    AttributeId.AmmoCapacity,
    AttributeId.Quickdraw,
    AttributeId.Penetration,
    AttributeId.BarrelCount,
    AttributeId.Power,
    AttributeId.PowerPerShot,
    AttributeId.MaxDamageDice,
]

CartridgeEnergyWeaponAttributeIds = [
    AttributeId.Range,
    AttributeId.Damage,
    AttributeId.AmmoCapacity,
    AttributeId.Quickdraw,
    AttributeId.Penetration,
    AttributeId.AmmoCost,
    AttributeId.BarrelCount,
    AttributeId.Power,
    AttributeId.PowerPerShot,
    AttributeId.MaxDamageDice
]

ProjectorWeaponAttributeIds = [
    AttributeId.Range,
    AttributeId.Damage,
    AttributeId.AmmoCapacity,
    AttributeId.Quickdraw,
    AttributeId.BarrelCount,
    AttributeId.FuelWeight,
    AttributeId.FuelCost,
    AttributeId.PropellantWeight,
    AttributeId.PropellantCost
]

ReliabilityAttributeIds = [
    AttributeId.HeatGeneration,
    AttributeId.AutoHeatGeneration,
    AttributeId.HeatDissipation,
    AttributeId.OverheatThreshold,
    AttributeId.DangerHeatThreshold,
    AttributeId.DisasterHeatThreshold,
    AttributeId.MalfunctionDM,
    AttributeId.Armour
]

class ModifierInterface(object):
    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by the class derived from ModifierInterface')

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        raise RuntimeError('The displayString method must be implemented by classes derived from ModifierInterface')

    def applyTo(
            self,
            baseValue: common.ScalarCalculation,
            ) -> common.ScalarCalculation:
        raise RuntimeError('The applyTo method must be implemented by classes derived from ModifierInterface')

class NumericModifierInterface(ModifierInterface):
    def numericModifier(self) -> common.ScalarCalculation:
        raise RuntimeError('The calculation method must be implemented by classes derived from NumericModifierInterface')

    def isAbsolute(self) -> bool:
        raise RuntimeError('The isAbsolute method must be implemented by classes derived from NumericModifierInterface')

class ConstantModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation
            ) -> None:
        super().__init__()
        self._value = value

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return True

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        return common.formatNumber(
            number=self._value.value(),
            decimalPlaces=decimalPlaces,
            alwaysIncludeSign=True)

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        return common.Calculator.add(
            lhs=baseValue,
            rhs=self._value)

class PercentageModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation,
            roundDown: bool = False
            ) -> None:
        super().__init__()
        self._value = value
        self._roundDown = roundDown

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return False

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        return common.formatNumber(
            number=self._value.value(),
            decimalPlaces=decimalPlaces,
            alwaysIncludeSign=True) + '%'

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        result = common.Calculator.applyPercentage(
            value=baseValue,
            percentage=self._value)
        if self._roundDown:
            result = common.Calculator.floor(value=result)
        return result

class MultiplierModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation,
            roundDown: bool = False
            ) -> None:
        super().__init__()
        self._value = value
        self._roundDown = roundDown

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return False

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        value = self._value.value()
        if value >= 0:
            return 'x' + common.formatNumber(
                number=value,
                decimalPlaces=decimalPlaces)
        else:
            return 'x(' + common.formatNumber(
                number=value,
                decimalPlaces=decimalPlaces) + ')'

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        result = common.Calculator.multiply(
            lhs=baseValue,
            rhs=self._value)
        if self._roundDown:
            result = common.Calculator.floor(value=result)
        return result

class DiceRollModifier(ModifierInterface):
    def __init__(
            self,
            countModifier: typing.Optional[common.ScalarCalculation] = None,
            constantModifier: typing.Optional[common.ScalarCalculation] = None
            ) -> None:
        super().__init__()
        self._countModifier = countModifier
        self._constantModifier = constantModifier

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        calculations = []
        if self._countModifier:
            calculations.append(self._countModifier)
        if self._constantModifier:
            calculations.append(self._constantModifier)
        return calculations

    def displayString(
            self,
            decimalPlaces: int = 2 # Not used for dice rolls as they're always integers
            ) -> str:
        displayString = ''

        if self._countModifier and self._countModifier.value() != 0:
            displayString += common.formatNumber(
                number=int(self._countModifier.value()),
                alwaysIncludeSign=True) + 'D'

        if self._constantModifier and self._constantModifier.value() != 0:
            if self._constantModifier.value() > 0:
                displayString += ' + ' if displayString else '+'
            else:
                displayString += ' - ' if displayString else '-'
            displayString += common.formatNumber(
                number=int(abs(self._constantModifier.value())))

        return displayString

    def applyTo(
            self,
            baseValue: common.DiceRoll
            ) -> common.DiceRoll:
        dieCount = baseValue.dieCount()
        constant = baseValue.constant()

        if self._countModifier:
            dieCount = common.Calculator.add(
                lhs=dieCount,
                rhs=self._countModifier,
                name=dieCount.name())

        if self._constantModifier:
            constant = common.Calculator.add(
                lhs=constant,
                rhs=self._constantModifier,
                name=constant.name())

        return common.DiceRoll(
            count=dieCount,
            type=baseValue.dieType(),
            constant=constant)

def calculateNumericModifierSequence(
        modifiers: typing.Iterable[NumericModifierInterface]
        ) -> typing.Optional[common.ScalarCalculation]:
    total = None
    for modifier in modifiers:
        if not total:
            if modifier.isAbsolute():
                total = modifier.numericModifier()
                continue
            total = common.ScalarCalculation(value=0)

        total = modifier.applyTo(baseValue=total)
    if not total:
        return common.ScalarCalculation(
            value=0,
            name=f'Modifier Sequence Total')
    if len(modifiers) == 1:
        return common.Calculator.equals(
            value=total,
            name=f'Modifier Sequence Total')
    return common.Calculator.rename(
        value=total,
        name=f'Modifier Sequence Total')

class AttributeInterface(object):
    def __init__(self) -> None:
        pass

    def id(self) -> AttributeId:
        raise RuntimeError('The attribute method must be implemented by classes derived from AttributeInterface')

    def name(self) -> str:
        raise RuntimeError('The name method must be implemented by classes derived from AttributeInterface')

    def value(self) -> typing.Any:
        raise RuntimeError('The value method must be implemented by classes derived from AttributeInterface')

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by classes derived from AttributeInterface')

    def applyModifier(
            self,
            modifier: ModifierInterface
            ) -> None:
        raise RuntimeError('The applyModifier method must be implemented by classes derived from AttributeInterface')

class FlagAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: AttributeId
            ) -> None:
        super().__init__()
        self._attributeId = attributeId

    def id(self) -> AttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.ScalarCalculation:
        return None

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return None

    def applyModifier(
            self,
            modifier: ModifierInterface
            ) -> None:
        # Applying a modifier to a flag has no effect
        pass

class NumericAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: AttributeId,
            value: common.ScalarCalculation
            ) -> None:
        super().__init__()
        self._attributeId = attributeId
        self._value = common.Calculator.equals(
            value=value,
            name=f'{self._attributeId.value} Value')

    def id(self) -> AttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.ScalarCalculation:
        return self._value

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._value]

    def applyModifier(
            self,
            modifier: ModifierInterface
            ) -> None:
        self._value = common.Calculator.rename(
            value=modifier.applyTo(baseValue=self._value),
            name=f'{self._attributeId.value} Value')

class EnumAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: AttributeId,
            value: enum.Enum
            ) -> None:
        super().__init__()

        self._attributeId = attributeId

        # Create a list of enums in definition order that can be used when modifying the attribute
        # by an integer amount. This assumes that iterating the enum type gives you the elements in
        # definition order (https://docs.python.org/3/library/enum.html)
        self._order = [e for e in type(value)]

        # Store the value as an integer value that is mapped back to an enum when required. This is
        # done to prevent clamping of modifier values. For example, a light handgun calibre pistol
        # (base signature Low) with the an extreme stealth receiver (signature -3) and a handgun
        # barrel (signature +1) should have Minimal signature not a Small signature as you would get
        # if the signature value was clamped to the available enums when the extreme stealth modifier
        # was applied.
        valueIndex = self._order.index(value)
        self._numericValue = common.ScalarCalculation(
            value=valueIndex,
            name=f'{attributeId.value} Value')

    def id(self) -> AttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> enum.Enum:
        valueIndex = common.clamp(
            value=self._numericValue.value(),
            minValue=0,
            maxValue=len(self._order) - 1)
        return self._order[valueIndex]

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._numericValue]

    def applyModifier(
            self,
            modifier: ModifierInterface
            ) -> None:
        if isinstance(modifier, ConstantModifier):
            self._numericValue = common.Calculator.rename(
                value=modifier.applyTo(baseValue=self._numericValue),
                name=f'{self._attributeId.value} Value')
        elif isinstance(modifier, PercentageModifier):
            raise RuntimeError(f'Unable to add percentage modifier to Enum attribute {self._attributeId.name}')
        elif isinstance(modifier, MultiplierModifier):
            raise RuntimeError(f'Unable to apply multiplier modifier to Enum attribute {self._attributeId.name}')
        elif isinstance(modifier, DiceRollModifier):
            raise RuntimeError(f'Unable to apply dice roll modifier to Enum attribute {self._attributeId.name}')
        else:
            raise RuntimeError(f'Unable to apply unknown modifier type {type(modifier)} to Enum attribute {self._attributeId.name}' )

class DiceRollAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: AttributeId,
            roll: common.DiceRoll
            ) -> None:
        super().__init__()
        self._attributeId = attributeId
        self._roll = common.DiceRoll(
            count=common.Calculator.equals(
                value=roll.dieCount(),
                name=f'{attributeId.value} Die Count'),
            type=roll.dieType(),
            constant=common.Calculator.equals(
                value=roll.constant(),
                name=f'{attributeId.value} Constant'))

    def id(self) -> AttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.DiceRoll:
        return self._roll

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._roll.dieCount(), self._roll.constant()]

    def applyModifier(
            self,
            modifier: ModifierInterface
            ) -> None:
        if isinstance(modifier, ConstantModifier):
            raise RuntimeError(f'Unable to apply constant modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, PercentageModifier):
            raise RuntimeError(f'Unable to apply percentage modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, MultiplierModifier):
            raise RuntimeError(f'Unable to apply multiplier modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, DiceRollModifier):
            self._roll = modifier.applyTo(baseValue=self._roll)
        else:
            raise RuntimeError(f'Unable to apply unknown modifier type {type(modifier)} to Dice Roll attribute {self._attributeId.name}' )

class AttributesGroup(object):
    def __init__(self) -> None:
        self._attributes: typing.Dict[AttributeId, AttributeInterface] = {}

    def attributes(
            self
            ) -> typing.Iterable[AttributeInterface]:
        return self._attributes.values()

    def attribute(
            self,
            attributeId: AttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        assert(isinstance(attributeId, AttributeId))
        return self._attributes.get(attributeId)

    def attributeValue(
            self,
            attributeId: AttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        assert(isinstance(attributeId, AttributeId))
        value = self._attributes.get(attributeId)
        if not value:
            return None
        return value.value()

    def hasAttribute(
            self,
            attributeId: AttributeId
            ) -> bool:
        assert(isinstance(attributeId, AttributeId))
        return attributeId in self._attributes

    def setAttribute(
            self,
            attributeId: AttributeId,
            value: typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]] = None
            ) -> None:
        assert(isinstance(attributeId, AttributeId))
        if value == None:
            self._attributes[attributeId] = FlagAttribute(
                attributeId=attributeId)
        elif isinstance(value, common.ScalarCalculation):
            self._attributes[attributeId] = NumericAttribute(
                attributeId=attributeId,
                value=value)
        elif isinstance(value, common.DiceRoll):
            self._attributes[attributeId] = DiceRollAttribute(
                attributeId=attributeId,
                roll=value)
        elif isinstance(value, enum.Enum):
            self._attributes[attributeId] = EnumAttribute(
                attributeId=attributeId,
                value=value)
        else:
            raise RuntimeError(f'Unknown type {type(value)} when setting attribute {attributeId.name}' )

    def modifyAttribute(
            self,
            attributeId: AttributeId,
            modifier: ModifierInterface
            ) -> None:
        assert(isinstance(attributeId, AttributeId))
        assert(isinstance(modifier, ModifierInterface))
        attribute = self._attributes.get(attributeId)
        if attribute:
            attribute.applyModifier(modifier=modifier)
        else:
            # This attribute is currently uninitialised
            if isinstance(modifier, ConstantModifier):
                # An absolute value is being applied to the attribute so just initialise a new numeric
                # attribute with the modifier value
                self._attributes[attributeId] = NumericAttribute(
                    attributeId=attributeId,
                    value=modifier.numericModifier())
            elif isinstance(modifier, PercentageModifier):
                raise RuntimeError(f'Unable to use percentage modifier to initialise attribute {attributeId.name}')
            elif isinstance(modifier, MultiplierModifier):
                raise RuntimeError(f'Unable to use multiplier modifier to initialise attribute {attributeId.name}')
            elif isinstance(modifier, DiceRollModifier):
                raise RuntimeError(f'Unable to use dice roll modifier to initialise attribute {attributeId.name}')

    def deleteAttribute(
            self,
            attributeId: AttributeId
            ) -> None:
        if attributeId in self._attributes:
            del self._attributes[attributeId]

    def clear(self) -> None:
        self._attributes.clear()
