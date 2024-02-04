import construction
import enum

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

class WeaponAttribute(construction.ConstructionAttribute):
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
    WeaponAttribute.Bulky,
    WeaponAttribute.VeryBulky,
    WeaponAttribute.Scope,
    WeaponAttribute.ZeroG,
    WeaponAttribute.Corrosive,
    WeaponAttribute.RF,
    WeaponAttribute.VRF,
    WeaponAttribute.Stun,
    WeaponAttribute.Auto,
    WeaponAttribute.Inaccurate,
    WeaponAttribute.Hazardous,
    WeaponAttribute.Unreliable,
    WeaponAttribute.SlowLoader,
    WeaponAttribute.Ramshackle,
    WeaponAttribute.AP,
    WeaponAttribute.LoPen,
    WeaponAttribute.Spread,
    WeaponAttribute.Blast,
    WeaponAttribute.Incendiary,
    WeaponAttribute.Burn,
    WeaponAttribute.PulseIntensity,
    WeaponAttribute.PhysicalSignature,
    WeaponAttribute.EmissionsSignature,
    WeaponAttribute.Distraction
]

ConventionalWeaponAttributeIds = [
    WeaponAttribute.Range,
    WeaponAttribute.Damage,
    WeaponAttribute.AmmoCapacity,
    WeaponAttribute.Quickdraw,
    WeaponAttribute.Penetration,
    WeaponAttribute.Recoil,
    WeaponAttribute.AutoRecoil,
    WeaponAttribute.AmmoCost,
    WeaponAttribute.BarrelCount,
]

LauncherWeaponAttributeIds = [
    WeaponAttribute.Range,
    WeaponAttribute.Damage,
    WeaponAttribute.AmmoCapacity,
    WeaponAttribute.Quickdraw,
    WeaponAttribute.AmmoCost,
    WeaponAttribute.BarrelCount
]

PowerPackEnergyWeaponAttributeIds = [
    WeaponAttribute.Range,
    WeaponAttribute.Damage,
    WeaponAttribute.AmmoCapacity,
    WeaponAttribute.Quickdraw,
    WeaponAttribute.Penetration,
    WeaponAttribute.BarrelCount,
    WeaponAttribute.Power,
    WeaponAttribute.PowerPerShot,
    WeaponAttribute.MaxDamageDice,
]

CartridgeEnergyWeaponAttributeIds = [
    WeaponAttribute.Range,
    WeaponAttribute.Damage,
    WeaponAttribute.AmmoCapacity,
    WeaponAttribute.Quickdraw,
    WeaponAttribute.Penetration,
    WeaponAttribute.AmmoCost,
    WeaponAttribute.BarrelCount,
    WeaponAttribute.Power,
    WeaponAttribute.PowerPerShot,
    WeaponAttribute.MaxDamageDice
]

ProjectorWeaponAttributeIds = [
    WeaponAttribute.Range,
    WeaponAttribute.Damage,
    WeaponAttribute.AmmoCapacity,
    WeaponAttribute.Quickdraw,
    WeaponAttribute.BarrelCount,
    WeaponAttribute.FuelWeight,
    WeaponAttribute.FuelCost,
    WeaponAttribute.PropellantWeight,
    WeaponAttribute.PropellantCost
]

ReliabilityAttributeIds = [
    WeaponAttribute.HeatGeneration,
    WeaponAttribute.AutoHeatGeneration,
    WeaponAttribute.HeatDissipation,
    WeaponAttribute.OverheatThreshold,
    WeaponAttribute.DangerHeatThreshold,
    WeaponAttribute.DisasterHeatThreshold,
    WeaponAttribute.MalfunctionDM,
    WeaponAttribute.Armour
]
