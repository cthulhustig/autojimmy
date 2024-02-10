import construction
import enum

ConstructionDecimalPlaces = 3

class WeaponType(enum.Enum):
    ConventionalWeapon = 'Conventional'
    GrenadeLauncherWeapon = 'Grenade Launcher'
    PowerPackWeapon = 'Power Pack'
    EnergyCartridgeWeapon = 'Energy Cartridge'
    ProjectorWeapon = 'Projector'

# The order of this enum determines construction order
class WeaponPhase(construction.ConstructionPhase):
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
    WeaponPhase.Receiver,
    WeaponPhase.Barrel,
    WeaponPhase.BarrelAccessories,
    WeaponPhase.Mounting
]

# Phases that are applied to the weapon as a whole
CommonConstructionPhases = [
    WeaponPhase.Stock,
    WeaponPhase.WeaponFeatures,
    WeaponPhase.WeaponAccessories,
    WeaponPhase.MultiMount,
]

# Phases that don't affect the basic construction of the weapon
AncillaryConstructionPhases = [
    WeaponPhase.Loading,
    WeaponPhase.Munitions
]

# Internal phases
InternalConstructionPhases = [
    WeaponPhase.Initialisation,
    WeaponPhase.Finalisation,
]

# Phases that make up the base weapon. Conceptually these phases get the weapon to the
# point that it's basically usable. Accessories, loading and munitions are not included.
BaseWeaponConstructionPhases = [
    WeaponPhase.Receiver,
    WeaponPhase.Barrel,
    WeaponPhase.Mounting,
    WeaponPhase.Stock,
    WeaponPhase.WeaponFeatures
]

# Phases that make the weapon ready for combat. Conceptually this includes all the phases
# needed to get the stats for using the weapon in combat.
CombatReadyConstructionPhases = [
    WeaponPhase.Receiver,
    WeaponPhase.Barrel,
    WeaponPhase.BarrelAccessories,
    WeaponPhase.Mounting,
    WeaponPhase.Stock,
    WeaponPhase.WeaponFeatures,
    WeaponPhase.WeaponAccessories,
    WeaponPhase.MultiMount,
    WeaponPhase.Loading
]
