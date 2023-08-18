import enum

class WeaponType(enum.Enum):
    ConventionalWeapon = 'Conventional'
    GrenadeLauncherWeapon = 'Grenade Launcher'
    PowerPackWeapon = 'Power Pack'
    EnergyCartridgeWeapon = 'Energy Cartridge'
    ProjectorWeapon = 'Projector'

# The order of this enum determines construction order
class ConstructionPhase(enum.Enum):
    Initialisation = 'Initialisation'
    Receiver = 'Receiver'
    Barrel = 'Barrel'
    BarrelAccessories = 'Barrel Accessories'
    Mounting = 'Mounting'
    Stock = 'Stock'
    WeaponFeatures = 'Weapon Features'
    WeaponAccessories = 'Weapon Accessories'
    MultiMount = 'Multi-Mount'
    Loading = 'Loading'
    Munitions = 'Munitions'
    Finalisation = 'Finalisation'


# Phases applied in sequence to create the primary or secondary weapons
SequenceConstructionPhases = [
    ConstructionPhase.Receiver,
    ConstructionPhase.Barrel,
    ConstructionPhase.BarrelAccessories,
    ConstructionPhase.Mounting
]

# Phases that are applied to the weapon as a whole
CommonConstructionPhases = [
    ConstructionPhase.Stock,
    ConstructionPhase.WeaponFeatures,
    ConstructionPhase.WeaponAccessories,
    ConstructionPhase.MultiMount,
]

# Phases that don't affect the basic construction of the weapon
AncillaryConstructionPhases = [
    ConstructionPhase.Loading,
    ConstructionPhase.Munitions
]


# Internal phases
InternalConstructionPhases = [
    ConstructionPhase.Initialisation,
    ConstructionPhase.Finalisation,
]

# Phases that make up the base weapon. Conceptually these phases get the weapon to the
# point that it's basically usable. Accessories, loading and munitions are not included.
BaseWeaponConstructionPhases = [
    ConstructionPhase.Receiver,
    ConstructionPhase.Barrel,
    ConstructionPhase.Mounting,
    ConstructionPhase.Stock,
    ConstructionPhase.WeaponFeatures
]

# Phases that make the weapon ready for combat. Conceptually this includes all the phases
# needed to get the stats for using the weapon in combat.
CombatReadyConstructionPhases = [
    ConstructionPhase.Receiver,
    ConstructionPhase.Barrel,
    ConstructionPhase.BarrelAccessories,
    ConstructionPhase.Mounting,
    ConstructionPhase.Stock,
    ConstructionPhase.WeaponFeatures,
    ConstructionPhase.WeaponAccessories,
    ConstructionPhase.MultiMount,
    ConstructionPhase.Loading
]
