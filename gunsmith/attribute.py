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

class WeaponAttributeId(construction.ConstructionAttributeId):
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
    WeaponAttributeId.Bulky,
    WeaponAttributeId.VeryBulky,
    WeaponAttributeId.Scope,
    WeaponAttributeId.ZeroG,
    WeaponAttributeId.Corrosive,
    WeaponAttributeId.RF,
    WeaponAttributeId.VRF,
    WeaponAttributeId.Stun,
    WeaponAttributeId.Auto,
    WeaponAttributeId.Inaccurate,
    WeaponAttributeId.Hazardous,
    WeaponAttributeId.Unreliable,
    WeaponAttributeId.SlowLoader,
    WeaponAttributeId.Ramshackle,
    WeaponAttributeId.AP,
    WeaponAttributeId.LoPen,
    WeaponAttributeId.Spread,
    WeaponAttributeId.Blast,
    WeaponAttributeId.Incendiary,
    WeaponAttributeId.Burn,
    WeaponAttributeId.PulseIntensity,
    WeaponAttributeId.PhysicalSignature,
    WeaponAttributeId.EmissionsSignature,
    WeaponAttributeId.Distraction
]

ConventionalWeaponAttributeIds = [
    WeaponAttributeId.Range,
    WeaponAttributeId.Damage,
    WeaponAttributeId.AmmoCapacity,
    WeaponAttributeId.Quickdraw,
    WeaponAttributeId.Penetration,
    WeaponAttributeId.Recoil,
    WeaponAttributeId.AutoRecoil,
    WeaponAttributeId.AmmoCost,
    WeaponAttributeId.BarrelCount,
]

LauncherWeaponAttributeIds = [
    WeaponAttributeId.Range,
    WeaponAttributeId.Damage,
    WeaponAttributeId.AmmoCapacity,
    WeaponAttributeId.Quickdraw,
    WeaponAttributeId.AmmoCost,
    WeaponAttributeId.BarrelCount
]

PowerPackEnergyWeaponAttributeIds = [
    WeaponAttributeId.Range,
    WeaponAttributeId.Damage,
    WeaponAttributeId.AmmoCapacity,
    WeaponAttributeId.Quickdraw,
    WeaponAttributeId.Penetration,
    WeaponAttributeId.BarrelCount,
    WeaponAttributeId.Power,
    WeaponAttributeId.PowerPerShot,
    WeaponAttributeId.MaxDamageDice,
]

CartridgeEnergyWeaponAttributeIds = [
    WeaponAttributeId.Range,
    WeaponAttributeId.Damage,
    WeaponAttributeId.AmmoCapacity,
    WeaponAttributeId.Quickdraw,
    WeaponAttributeId.Penetration,
    WeaponAttributeId.AmmoCost,
    WeaponAttributeId.BarrelCount,
    WeaponAttributeId.Power,
    WeaponAttributeId.PowerPerShot,
    WeaponAttributeId.MaxDamageDice
]

ProjectorWeaponAttributeIds = [
    WeaponAttributeId.Range,
    WeaponAttributeId.Damage,
    WeaponAttributeId.AmmoCapacity,
    WeaponAttributeId.Quickdraw,
    WeaponAttributeId.BarrelCount,
    WeaponAttributeId.FuelWeight,
    WeaponAttributeId.FuelCost,
    WeaponAttributeId.PropellantWeight,
    WeaponAttributeId.PropellantCost
]

ReliabilityAttributeIds = [
    WeaponAttributeId.HeatGeneration,
    WeaponAttributeId.AutoHeatGeneration,
    WeaponAttributeId.HeatDissipation,
    WeaponAttributeId.OverheatThreshold,
    WeaponAttributeId.DangerHeatThreshold,
    WeaponAttributeId.DisasterHeatThreshold,
    WeaponAttributeId.MalfunctionDM,
    WeaponAttributeId.Armour
]
