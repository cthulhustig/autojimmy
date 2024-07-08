import enum
import traveller
import typing

class StockWeaponSet(enum.Enum):
    Core2 = 'Core Rules 2e'
    Core2022 = 'Core Rules 2022'
    CSC2 = 'Central Supply Catalogue 2e'
    CSC2023 = 'Central Supply Catalogue 2023'


_CoreCompatible = [StockWeaponSet.Core2, StockWeaponSet.Core2022]
_SupplyCatalogueCompatible = [StockWeaponSet.CSC2, StockWeaponSet.CSC2023]
_AllCompatible = _CoreCompatible + _SupplyCatalogueCompatible

class WeaponCategory(enum.Enum):
    Bludgeoning = 'Bludgeoning'
    Blade = 'Blade'
    UpClose = 'Up Close'
    Shield = 'Shield'
    Whip = 'Whip'
    SlugPistol = 'Slug Pistol'
    SlugRifle = 'Slug Rifle'
    EnergyPistol = 'Energy Pistol'
    EnergyRifle = 'Energy Rifle'
    Archaic = 'Archaic'
    Grenade = 'Grenade'
    Explosive = 'Explosive'
    HeavyPortable = 'Heavy Portable'
    Artillery = 'Artillery'
    Vehicle = 'Vehicle'
    Launched = 'Launched'

class WeaponSize(enum.Enum):
    Small = 'Small'
    Medium = 'Medium'
    Heavy = 'Heavy'
    Vehicle = 'Vehicle'

class StockWeapon(object):
    def __init__(
            self,
            name: str,
            category: WeaponCategory,
            techLevel: int,
            skill: traveller.SkillDefinition,
            specialty: typing.Optional[enum.Enum] = None,
            cost: typing.Optional[int] = None,
            weight: typing.Optional[float] = None,
            range: typing.Optional[float] = None,
            magazineCapacity: typing.Optional[int] = None,
            magazineCost: typing.Optional[int] = None,
            damage: typing.Union[str] = '',
            traits: typing.Union[str] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            ) -> None:
        self._name = name
        self._techLevel = techLevel
        self._category = category
        self._skill = skill
        self._specialty = specialty
        self._cost = cost
        self._weight = weight
        self._range = range
        self._magazineCapacity = magazineCapacity
        self._magazineCost = magazineCost
        self._damage = damage
        self._traits = traits
        self._robotMount = robotMount
        self._linkable = linkable

    def name(self) -> str:
        return self._name

    def category(self) -> WeaponCategory:
        return self._category

    def techLevel(self) -> int:
        return self._techLevel

    def skill(self) -> traveller.SkillDefinition:
        return self._skill

    def specialty(self) -> typing.Optional[enum.Enum]:
        return self._specialty

    def cost(self) -> int:
        return self._cost

    def weight(self) -> typing.Optional[float]:
        return self._weight

    def range(self) -> typing.Optional[float]:
        return self._range

    def magazineCapacity(self) -> typing.Optional[int]:
        return self._magazineCapacity

    def magazineCost(self) -> typing.Optional[int]:
        return self._magazineCost

    def damage(self) -> str:
        return self._damage

    def traits(self) -> str:
        return self._traits

    def robotMount(self) -> typing.Optional[WeaponSize]:
        return self._robotMount

    def linkable(self) -> bool:
        return self._linkable

    # This class represents immutable data so there should be no need to deep
    # copy it and doing so could introduce bugs because code performs
    # comparisons with the static class instances below. I could add an
    # equality operator but, due to the fact the data its self is static, it
    # seems better to do this
    def __deepcopy__(self, memo: typing.Dict) -> 'StockWeapon':
        return self

class _StockWeaponDescription(object):
    def __init__(
            self,
            name: str,
            category: WeaponCategory,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            skill: traveller.SkillDefinition,
            specialty: typing.Optional[enum.Enum] = None,
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        self._name = name
        self._category = category
        self._techLevel = techLevel
        self._skill = skill
        self._specialty = specialty
        self._cost = cost
        self._weight = weight
        self._range = range
        self._magazineCapacity = magazineCapacity
        self._magazineCost = magazineCost
        self._damage = damage
        self._traits = traits
        self._robotMount = robotMount
        self._linkable = linkable
        self._weaponSets = weaponSets

    def name(self) -> str:
        return self._name

    def isCompatible(
            self,
            weaponSet: StockWeaponSet
            ) -> bool:
        return not self._weaponSets or weaponSet in self._weaponSets

    def createStockWeapon(
            self,
            weaponSet: StockWeaponSet
            ) -> typing.Optional[StockWeapon]:
        if self._weaponSets and weaponSet not in self._weaponSets:
            return None
        return StockWeapon(
            name=self._name,
            category=self._category,
            techLevel=self._techLevel[weaponSet] if isinstance(self._techLevel, dict) else self._techLevel,
            skill=self._skill,
            specialty=self._specialty,
            cost=self._cost[weaponSet] if isinstance(self._cost, dict) else self._cost,
            weight=self._weight[weaponSet] if isinstance(self._weight, dict) else self._weight,
            range=self._range[weaponSet] if isinstance(self._range, dict) else self._range,
            damage=self._damage[weaponSet] if isinstance(self._damage, dict) else self._damage,
            magazineCapacity=self._magazineCapacity[weaponSet] if isinstance(self._magazineCapacity, dict) else self._magazineCapacity,
            magazineCost=self._magazineCost[weaponSet] if isinstance(self._magazineCost, dict) else self._magazineCost,
            traits=self._traits[weaponSet] if isinstance(self._traits, dict) else self._traits,
            robotMount=self._robotMount,
            linkable=self._linkable)

class _StockBludgeoningWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Bludgeoning,
            techLevel=techLevel,
            skill=traveller.MeleeSkillDefinition,
            specialty=traveller.MeleeSkillSpecialities.Bludgeon,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=robotMount,
            linkable=False,
            weaponSets=weaponSets)

class _StockBladeWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Blade,
            techLevel=techLevel,
            skill=traveller.MeleeSkillDefinition,
            specialty=traveller.MeleeSkillSpecialities.Blade,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=robotMount,
            linkable=False,
            weaponSets=weaponSets)

class _StockUpCloseWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.UpClose,
            techLevel=techLevel,
            skill=traveller.MeleeSkillDefinition,
            specialty=traveller.MeleeSkillSpecialities.Unarmed,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=WeaponSize.Small,
            linkable=False,
            weaponSets=weaponSets)

class _StockShieldDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Shield,
            techLevel=techLevel,
            skill=traveller.MeleeSkillDefinition,
            specialty=traveller.MeleeSkillSpecialities.Bludgeon,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=robotMount,
            linkable=False,
            weaponSets=weaponSets)

class _StockWhipDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Whip,
            techLevel=techLevel,
            skill=traveller.MeleeSkillDefinition,
            specialty=traveller.MeleeSkillSpecialities.Whip,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=WeaponSize.Small,
            linkable=False,
            weaponSets=weaponSets)

class _StockSlugPistolDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.SlugPistol,
            techLevel=techLevel,
            skill=traveller.GunCombatSkillDefinition,
            specialty=traveller.GunCombatSkillSpecialities.Slug,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockSlugRifleDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.SlugRifle,
            techLevel=techLevel,
            skill=traveller.GunCombatSkillDefinition,
            specialty=traveller.GunCombatSkillSpecialities.Slug,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockEnergyPistolDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.EnergyPistol,
            techLevel=techLevel,
            skill=traveller.GunCombatSkillDefinition,
            specialty=traveller.GunCombatSkillSpecialities.Energy,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockEnergyRifleDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.EnergyRifle,
            techLevel=techLevel,
            skill=traveller.GunCombatSkillDefinition,
            specialty=traveller.GunCombatSkillSpecialities.Energy,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockArchaicWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Archaic,
            techLevel=techLevel,
            skill=traveller.GunCombatSkillDefinition,
            specialty=traveller.GunCombatSkillSpecialities.Archaic,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockGrenadeDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Grenade,
            techLevel=techLevel,
            skill=traveller.AthleticsSkillDefinition,
            specialty=traveller.AthleticsSkillSpecialities.Dexterity,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=WeaponSize.Small,
            linkable=False,
            weaponSets=weaponSets)

class _StockExplosiveDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Explosive,
            techLevel=techLevel,
            skill=traveller.ExplosivesSkillDefinition,
            cost=cost,
            weight=weight,
            range=None,
            damage=damage,
            magazineCapacity=None,
            magazineCost=None,
            traits=traits,
            robotMount=WeaponSize.Small,
            linkable=False,
            weaponSets=weaponSets)

class _StockHeavyPortableWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.HeavyPortable,
            techLevel=techLevel,
            skill=traveller.HeavyWeaponsSkillDefinition,
            specialty=traveller.HeavyWeaponsSkillSpecialities.Portable,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockArtilleryDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Artillery,
            techLevel=techLevel,
            skill=traveller.HeavyWeaponsSkillDefinition,
            specialty=traveller.HeavyWeaponsSkillSpecialities.Artillery,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockVehicleWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Vehicle,
            techLevel=techLevel,
            skill=traveller.HeavyWeaponsSkillDefinition,
            specialty=traveller.HeavyWeaponsSkillSpecialities.Vehicle,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

class _StockLaunchedWeaponDescription(_StockWeaponDescription):
    def __init__(
            self,
            name: str,
            techLevel: typing.Union[int, typing.Mapping[StockWeaponSet, int]],
            cost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            weight: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            range: typing.Optional[typing.Union[float, typing.Mapping[StockWeaponSet, float]]] = None,
            damage: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            magazineCapacity: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            magazineCost: typing.Optional[typing.Union[int, typing.Mapping[StockWeaponSet, int]]] = None,
            traits: typing.Union[str, typing.Mapping[StockWeaponSet, str]] = '',
            robotMount: typing.Optional[WeaponSize] = None,
            linkable: bool = False,
            weaponSets: typing.Optional[typing.Iterable[StockWeaponSet]] = None,
            ) -> None:
        super().__init__(
            name=name,
            category=WeaponCategory.Launched,
            techLevel=techLevel,
            skill=traveller.HeavyWeaponsSkillDefinition,
            specialty=traveller.HeavyWeaponsSkillSpecialities.Vehicle,
            cost=cost,
            weight=weight,
            range=range,
            damage=damage,
            magazineCapacity=magazineCapacity,
            magazineCost=magazineCost,
            traits=traits,
            robotMount=robotMount,
            linkable=linkable,
            weaponSets=weaponSets)

# List of weapons taken from the MGT2 Robot Worksheet v1.50.01 spreadsheet
# IMPORTANT: These weapon names MUST remain constant between versions otherwise
# it will break weapons saved by older versions
# NOTE: Based on some of the weapons on the list (pepper spray, some of the
# grenades etc) I think this is the list of weapons from the 2023 update of the
# companion
# NOTE: The linkable flag that some weapons have come from the spreadsheet.
# I've not found anything that would indicate it's official but it does seem to
# have some logic behind it. As far as I can tell it's generally weapons that
# are fired rather than wielded or thrown, although there are a few exceptions
# (notably launchers).
# I've kept the value here for completeness but I don't plan to use it. I don't
# see why you couldn't have a multi-linked melee weapon for example. I think
# it's best to allow any weapon to be multi-linked and leave it up to referees
# to say if it's allowed.


_WeaponDescriptions: typing.List[_StockWeaponDescription] = [
    #  ███████████  ████                 █████                                        ███
    # ░░███░░░░░███░░███                ░░███                                        ░░░
    #  ░███    ░███ ░███  █████ ████  ███████   ███████  ██████   ██████  ████████   ████  ████████    ███████
    #  ░██████████  ░███ ░░███ ░███  ███░░███  ███░░███ ███░░███ ███░░███░░███░░███ ░░███ ░░███░░███  ███░░███
    #  ░███░░░░░███ ░███  ░███ ░███ ░███ ░███ ░███ ░███░███████ ░███ ░███ ░███ ░███  ░███  ░███ ░███ ░███ ░███
    #  ░███    ░███ ░███  ░███ ░███ ░███ ░███ ░███ ░███░███░░░  ░███ ░███ ░███ ░███  ░███  ░███ ░███ ░███ ░███
    #  ███████████  █████ ░░████████░░████████░░███████░░██████ ░░██████  ████ █████ █████ ████ █████░░███████
    # ░░░░░░░░░░░  ░░░░░   ░░░░░░░░  ░░░░░░░░  ░░░░░███ ░░░░░░   ░░░░░░  ░░░░ ░░░░░ ░░░░░ ░░░░ ░░░░░  ░░░░░███
    #                                          ███ ░███                                               ███ ░███
    #                                         ░░██████                                               ░░██████
    #                                          ░░░░░░                                                 ░░░░░░

    _StockBludgeoningWeaponDescription(
        name='Anti-Armour Flail',
        techLevel=8,
        cost=250,
        weight=3,
        damage='4D',
        traits='AP 5, One Use',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Club',
        techLevel={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 1,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        weight={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        damage='2D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBludgeoningWeaponDescription(
        name='Gravity Hammer',
        techLevel=13,
        cost=10000,
        weight=5,
        damage='5D',
        traits='AP 50, Bulky, Smasher',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Mace',
        techLevel=1,
        cost=20,
        weight=3,
        damage='2D+2',
        traits='Bulky, Smasher',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Sap',
        techLevel={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=30,
        weight=1,
        damage='1D',
        traits='Stun',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Sledgehammer',
        techLevel=1,
        cost=30,
        weight=8,
        damage='4D',
        traits='Smasher, Very Bulky',
        robotMount=WeaponSize.Heavy,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Staff',
        techLevel=1,
        cost={
            StockWeaponSet.Core2: None,
            StockWeaponSet.Core2022: None,
            StockWeaponSet.CSC2: None,
            StockWeaponSet.CSC2023: 5},
        weight={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        damage='2D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBludgeoningWeaponDescription(
        name='Static Maul',
        techLevel=11,
        cost=650,
        weight=3,
        damage='3D',
        traits='AP 4, Smasher',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBludgeoningWeaponDescription(
        name='Stunstick',
        techLevel=8,
        cost=300,
        weight={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 0.5,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        damage='2D',
        traits='Stun',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),


    #  ███████████  ████                █████
    # ░░███░░░░░███░░███               ░░███
    #  ░███    ░███ ░███   ██████    ███████   ██████
    #  ░██████████  ░███  ░░░░░███  ███░░███  ███░░███
    #  ░███░░░░░███ ░███   ███████ ░███ ░███ ░███████
    #  ░███    ░███ ░███  ███░░███ ░███ ░███ ░███░░░
    #  ███████████  █████░░████████░░████████░░██████
    # ░░░░░░░░░░░  ░░░░░  ░░░░░░░░  ░░░░░░░░  ░░░░░░

    _StockBladeWeaponDescription(
        name='Arc-Field Weapon',
        techLevel=14,
        weight=4,
        cost=25000,
        damage='5D+2',
        traits='AP 30',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Assault Pike - TL 5',
        techLevel=5,
        cost=200,
        weight=8,
        damage='4D',
        traits='AP 4, One Use',
        robotMount=WeaponSize.Heavy,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Assault Pike - TL 8',
        techLevel=8,
        cost=400,
        weight=5,
        damage='4D',
        traits='AP 4, One Use',
        robotMount=WeaponSize.Medium,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockBladeWeaponDescription(
        name='Battle Axe',
        techLevel={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=225,
        weight=4,
        damage='3D',
        traits='AP 2, Bulky',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Blade',
        techLevel={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=100,
        weight={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 1,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        damage='2D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBladeWeaponDescription(
        name='Broadsword',
        techLevel={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=500,
        weight={
            StockWeaponSet.Core2: 8,
            StockWeaponSet.Core2022: 3,
            StockWeaponSet.CSC2: 8,
            StockWeaponSet.CSC2023: 3},
        damage='4D',
        traits='Bulky',
        robotMount=WeaponSize.Medium,
        weaponSets=_AllCompatible),
    _StockBladeWeaponDescription(
        name='Chaindrive Axe',
        techLevel=10,
        cost=600,
        weight={
            StockWeaponSet.CSC2: 7,
            StockWeaponSet.CSC2023: 6},
        damage='4D',
        traits='AP 4, Bulky',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Chaindrive Sword',
        techLevel=10,
        cost=500,
        weight={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 4},
        damage='4D',
        traits='AP 2',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Cutlass',
        techLevel=2,
        cost=200,
        weight={
            StockWeaponSet.Core2: 4,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 2},
        damage='3D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBladeWeaponDescription(
        name='Dagger',
        techLevel=1,
        cost=10,
        weight={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 0.5,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        damage='1D+2',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBladeWeaponDescription(
        name='Great Axe',
        techLevel=1,
        cost=750,
        weight={
            StockWeaponSet.CSC2: 10,
            StockWeaponSet.CSC2023: 8},
        damage='4D+2',
        traits='Smasher, Very Bulky',
        robotMount=WeaponSize.Heavy,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Hatchet',
        techLevel={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 1},
        cost=50,
        weight=2,
        damage='2D+2',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Knife',
        techLevel=1,
        cost=5,
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2]),
    _StockBladeWeaponDescription(
        name='Lance',
        techLevel=1,
        cost={
            StockWeaponSet.CSC2: 75,
            StockWeaponSet.CSC2023: 250},
        weight=4,
        damage='5D',
        traits='AP 4',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Long Blade - TL 1',
        techLevel=1,
        cost=200,
        weight=2,
        damage='3D',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockBladeWeaponDescription(
        name='Long Blade - TL 2',
        techLevel=2,
        cost=200,
        weight=4,
        damage='3D',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2]),
    _StockBladeWeaponDescription(
        name='Long Blade - TL 3',
        techLevel=3,
        cost=300,
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 2},
        damage='3D+2',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Monoblade',
        techLevel=12,
        cost=2500,
        weight={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        damage='3D',
        traits='AP 10',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Monofilament Axe',
        techLevel=12,
        cost=3000,
        damage='4D',
        traits='AP 15, Bulky, Smasher',
        robotMount=WeaponSize.Medium,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockBladeWeaponDescription(
        name='Piston Spear',
        techLevel=7,
        cost=400,
        weight=3,
        damage='3D+2',
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'AP 2'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Psi Blade',
        techLevel=16,
        cost=30000,
        weight={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        damage='2D',
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'Special (PSI)'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Psi Dagger',
        techLevel={
            StockWeaponSet.CSC2: 17,
            StockWeaponSet.CSC2023: 16},
        cost=25000,
        weight={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        damage='1D+2',
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'Special (PSI)'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Rapier',
        techLevel={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 3,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        cost=200,
        weight={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 0.5,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        damage='2D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),
    _StockBladeWeaponDescription(
        name='Spear',
        techLevel={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        cost=10,
        weight=2,
        damage='2D',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Static Axe - TL 11',
        techLevel=11,
        cost=750,
        weight={
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 5},
        damage='4D',
        traits='AP 6, Smasher',
        robotMount=WeaponSize.Heavy,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Static Axe - TL 12',
        techLevel=12,
        cost=1000,
        weight={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 4},
        damage='4D+2',
        traits='AP 8, Smasher',
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Static Blade - TL 11',
        techLevel=11,
        cost=700,
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 3},
        damage='3D',
        traits='AP 5',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Static Blade - TL 12',
        techLevel=12,
        cost=900,
        weight={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        damage='3D+2',
        traits='AP 6',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Stealth Dagger',
        techLevel=8,
        cost=175,
        weight={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        damage='1D+2',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='Stone Axe',
        techLevel=0,
        cost=5,
        weight={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        damage={
            StockWeaponSet.CSC2: '2D',
            StockWeaponSet.CSC2023: '2D+1'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockBladeWeaponDescription(
        name='War Pick',
        techLevel={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 1},
        cost=275,
        damage='2D+2',
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 3},
        traits='AP 4',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),


    #  █████  █████                █████████  ████
    # ░░███  ░░███                ███░░░░░███░░███
    #  ░███   ░███  ████████     ███     ░░░  ░███   ██████   █████   ██████
    #  ░███   ░███ ░░███░░███   ░███          ░███  ███░░███ ███░░   ███░░███
    #  ░███   ░███  ░███ ░███   ░███          ░███ ░███ ░███░░█████ ░███████
    #  ░███   ░███  ░███ ░███   ░░███     ███ ░███ ░███ ░███ ░░░░███░███░░░
    #  ░░████████   ░███████     ░░█████████  █████░░██████  ██████ ░░██████
    #   ░░░░░░░░    ░███░░░       ░░░░░░░░░  ░░░░░  ░░░░░░  ░░░░░░   ░░░░░░
    #               ░███
    #               █████
    #              ░░░░░

    _StockUpCloseWeaponDescription(
        name='Brass Knuckles',
        techLevel=1,
        cost=10,
        damage='1D+2',
        weaponSets=_SupplyCatalogueCompatible),
    _StockUpCloseWeaponDescription(
        name='Claw - Arc-Field',
        techLevel=14,
        cost=25000,
        damage='4D',
        traits='AP 30',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockUpCloseWeaponDescription(
        name='Claw - Edging',
        techLevel=11,
        cost=3000,
        damage='2D+2',
        traits='AP 4',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockUpCloseWeaponDescription(
        name='Claw - Hardened',
        techLevel=10,
        cost=1000,
        damage='1D+2',
        traits='AP 2',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockUpCloseWeaponDescription(
        name='Claw - Monofilament',
        techLevel=12,
        cost=5000,
        damage='3D',
        traits='AP 10',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockUpCloseWeaponDescription(
        name='Garotte',
        techLevel={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        cost=10,
        damage='2D',
        weaponSets=_SupplyCatalogueCompatible),
    _StockUpCloseWeaponDescription(
        name='Handspikes',
        techLevel=2,
        cost=100,
        damage='2D',
        weaponSets=_SupplyCatalogueCompatible),
    _StockUpCloseWeaponDescription(
        name='Knuckleblasters',
        techLevel=8,
        cost=150,
        weight={
            StockWeaponSet.CSC2: None,
            StockWeaponSet.CSC2023: 0.5},
        damage='5D',
        weaponSets=_SupplyCatalogueCompatible),
    _StockUpCloseWeaponDescription(
        name='Monofilament Garotte',
        techLevel=12,
        cost=1000,
        damage='3D',
        traits='AP 10, Dangerous',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockUpCloseWeaponDescription(
        name='Piston Fist',
        techLevel=9,
        cost=150,
        weight={
            StockWeaponSet.CSC2: None,
            StockWeaponSet.CSC2023: 0.5},
        damage='3D+2',
        weaponSets=_SupplyCatalogueCompatible),
    _StockUpCloseWeaponDescription(
        name='Stunfist',
        techLevel=8,
        cost=250,
        damage='1D+2',
        traits='Stun',
        weaponSets=_SupplyCatalogueCompatible),


    #   █████████  █████       ███           ████      █████
    #  ███░░░░░███░░███       ░░░           ░░███     ░░███
    # ░███    ░░░  ░███████   ████   ██████  ░███   ███████
    # ░░█████████  ░███░░███ ░░███  ███░░███ ░███  ███░░███
    #  ░░░░░░░░███ ░███ ░███  ░███ ░███████  ░███ ░███ ░███
    #  ███    ░███ ░███ ░███  ░███ ░███░░░   ░███ ░███ ░███
    # ░░█████████  ████ █████ █████░░██████  █████░░████████
    #  ░░░░░░░░░  ░░░░ ░░░░░ ░░░░░  ░░░░░░  ░░░░░  ░░░░░░░░

    _StockShieldDescription(
        name='Boarding Shield',
        techLevel=9,
        cost=1500,
        weight={
            StockWeaponSet.CSC2: 7,
            StockWeaponSet.CSC2023: 5},
        damage='1D',
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'Bulky'},
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockShieldDescription(
        name='Buckler',
        techLevel={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=10,
        weight={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockShieldDescription(
        name='Expandable Shield',
        techLevel=12,
        cost=2500,
        weight=1,
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockShieldDescription(
        name='Gravitic Shield',
        techLevel=17,
        cost=2500,
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockShieldDescription(
        name='Large Shield',
        techLevel=1,
        cost=200,
        weight={
            StockWeaponSet.CSC2: 8,
            StockWeaponSet.CSC2023: 5},
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockShieldDescription(
        name='Riot Shield',
        techLevel=6,
        cost=175,
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 1.5},
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockShieldDescription(
        name='Shield',
        techLevel={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 1,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        cost=150,
        weight={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 2},
        damage='1D',
        robotMount=WeaponSize.Small,
        weaponSets=_AllCompatible),


    #  █████   ███   █████ █████       ███
    # ░░███   ░███  ░░███ ░░███       ░░░
    #  ░███   ░███   ░███  ░███████   ████  ████████
    #  ░███   ░███   ░███  ░███░░███ ░░███ ░░███░░███
    #  ░░███  █████  ███   ░███ ░███  ░███  ░███ ░███
    #   ░░░█████░█████░    ░███ ░███  ░███  ░███ ░███
    #     ░░███ ░░███      ████ █████ █████ ░███████
    #      ░░░   ░░░      ░░░░ ░░░░░ ░░░░░  ░███░░░
    #                                       ░███
    #                                       █████
    #                                      ░░░░░

    _StockWhipDescription(
        name='Shock Whip',
        techLevel=9,
        cost=450,
        weight=1,
        damage='2D',
        traits='Stun',
        weaponSets=_SupplyCatalogueCompatible),
    _StockWhipDescription(
        name='Whip',
        techLevel=1,
        cost=15,
        weight=1,
        damage='D3',
        weaponSets=_SupplyCatalogueCompatible),


    #   █████████  ████                         ███████████   ███           █████             ████
    #  ███░░░░░███░░███                        ░░███░░░░░███ ░░░           ░░███             ░░███
    # ░███    ░░░  ░███  █████ ████  ███████    ░███    ░███ ████   █████  ███████    ██████  ░███
    # ░░█████████  ░███ ░░███ ░███  ███░░███    ░██████████ ░░███  ███░░  ░░░███░    ███░░███ ░███
    #  ░░░░░░░░███ ░███  ░███ ░███ ░███ ░███    ░███░░░░░░   ░███ ░░█████   ░███    ░███ ░███ ░███
    #  ███    ░███ ░███  ░███ ░███ ░███ ░███    ░███         ░███  ░░░░███  ░███ ███░███ ░███ ░███
    # ░░█████████  █████ ░░████████░░███████    █████        █████ ██████   ░░█████ ░░██████  █████
    #  ░░░░░░░░░  ░░░░░   ░░░░░░░░  ░░░░░███   ░░░░░        ░░░░░ ░░░░░░     ░░░░░   ░░░░░░  ░░░░░
    #                               ███ ░███
    #                              ░░██████
    #                               ░░░░░░

    _StockSlugPistolDescription(
        name='Antique Pistol',
        techLevel={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        cost=100,
        weight={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 0.5,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        range=5,
        damage='2D-3',
        magazineCapacity=1,
        magazineCost=5,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugPistolDescription(
        name='Assault Pistol',
        techLevel=6,
        cost=250,
        weight=1,
        range=10,
        damage='3D-3',
        magazineCapacity=15,
        magazineCost=10,
        traits='Auto 2',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Autopistol',
        techLevel={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 5,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 5},
        cost=200,
        weight=1,
        range=10,
        damage='3D-3',
        magazineCapacity=15,
        magazineCost=10,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugPistolDescription(
        name='Body Pistol',
        techLevel=8,
        cost=500,
        range=5,
        damage='2D',
        magazineCapacity=6,
        magazineCost=10,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Cartridge Pistol',
        techLevel=7,
        cost=300,
        weight=1.5,
        range=20,
        damage='4D',
        magazineCapacity=6,
        magazineCost=10,
        traits='Bulky',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Coach Pistol',
        techLevel=3,
        cost=200,
        weight=2,
        range=5,
        damage='4D-3',
        magazineCapacity=2,
        magazineCost=10,
        traits='Dangerous',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Duck\'s Foot Pistol',
        techLevel=3,
        cost=300,
        weight=2,
        range=5,
        damage='3D-3',
        magazineCapacity=24,
        magazineCost=25,
        traits='Auto 4, Dangerous',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Flechette Pistol',
        techLevel=9,
        cost=275,
        weight=1,
        range=10,
        damage='3D-2',
        magazineCapacity=20,
        magazineCost=10,
        traits='Silent',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Gauss Pistol',
        techLevel=13,
        cost=500,
        weight=1,
        range=20,
        damage='3D',
        magazineCapacity=40,
        magazineCost=20,
        traits='AP 3, Auto 2',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugPistolDescription(
        name='Heavy Revolver',
        techLevel={
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 5},
        cost=400,
        weight=1.5,
        range=10,
        damage='4D-3',
        magazineCapacity=6,
        magazineCost=15,
        robotMount=WeaponSize.Medium,
        traits='Bulky',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Magrail Pistol',
        techLevel=14,
        cost=750,
        weight=1,
        range=15,
        damage='3D+3',
        magazineCapacity=20,
        magazineCost=60,
        traits='Auto 4',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Revolver',
        techLevel={
            StockWeaponSet.Core2: 5,
            StockWeaponSet.Core2022: 4,
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 4},
        cost=150,
        weight={
            StockWeaponSet.Core2: 1,
            StockWeaponSet.Core2022: 0.5,
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0.5},
        range=10,
        damage='3D-3',
        magazineCapacity=6,
        magazineCost=5,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugPistolDescription(
        name='Shot Pistol',
        techLevel=5,
        cost=60,
        weight=0.5,
        range=2,
        damage='3D',
        magazineCapacity=1,
        magazineCost=5,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugPistolDescription(
        name='Snub Pistol',
        techLevel=8,
        cost=150,
        range=5,
        damage='3D-3',
        magazineCapacity=6,
        magazineCost=10,
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugPistolDescription(
        name='Universal Autopistol',
        techLevel=8,
        cost=300,
        weight=1,
        range=10,
        damage='3D-3',
        magazineCapacity=10,
        magazineCost=10,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugPistolDescription(
        name='Zip Gun',
        techLevel=3,
        cost=50,
        range=5,
        damage='2D-3',
        magazineCapacity=1,
        magazineCost=5,
        traits='Dangerous',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),


    #   █████████  ████                         ███████████    ███     ██████  ████
    #  ███░░░░░███░░███                        ░░███░░░░░███  ░░░     ███░░███░░███
    # ░███    ░░░  ░███  █████ ████  ███████    ░███    ░███  ████   ░███ ░░░  ░███   ██████
    # ░░█████████  ░███ ░░███ ░███  ███░░███    ░██████████  ░░███  ███████    ░███  ███░░███
    #  ░░░░░░░░███ ░███  ░███ ░███ ░███ ░███    ░███░░░░░███  ░███ ░░░███░     ░███ ░███████
    #  ███    ░███ ░███  ░███ ░███ ░███ ░███    ░███    ░███  ░███   ░███      ░███ ░███░░░
    # ░░█████████  █████ ░░████████░░███████    █████   █████ █████  █████     █████░░██████
    #  ░░░░░░░░░  ░░░░░   ░░░░░░░░  ░░░░░███   ░░░░░   ░░░░░ ░░░░░  ░░░░░     ░░░░░  ░░░░░░
    #                               ███ ░███
    #                              ░░██████
    #                               ░░░░░░

    _StockSlugRifleDescription(
        name='Accelerator Rifle - TL 9',
        techLevel=9,
        cost=900,
        weight=2,
        # NOTE: The original CSC has 25 but I suspect that is a misprint
        # as the Core 2e, Core 2022 & CSC 2023 all have it as 250
        range=250,
        damage='3D',
        magazineCapacity=15,
        magazineCost=30,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Accelerator Rifle - TL 11',
        techLevel=11,
        cost=1500,
        weight=2,
        range=400,
        damage='3D',
        magazineCapacity=20,
        magazineCost=40,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugRifleDescription(
        name='Advanced Combat Rifle',
        techLevel=10,
        cost=1000,
        weight=3,
        range=450,
        damage='3D',
        magazineCapacity=40,
        magazineCost=15,
        traits='Auto 3, Scope',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Air Rifle - TL 3',
        techLevel=3,
        cost=225,
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 3},
        range=50,
        damage='2D',
        magazineCapacity=1,
        magazineCost=1,
        traits='Silent',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Air Rifle - TL 4',
        techLevel=4,
        cost=350,
        weight={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 3},
        range=75,
        damage='3D-2',
        magazineCapacity=1,
        magazineCost=1,
        traits='Silent',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Antique Rifle',
        techLevel={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        cost=150,
        weight={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 3,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 3},
        range=25,
        damage='3D-3',
        magazineCapacity=1,
        magazineCost=10,
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Assault Rifle',
        techLevel=7,
        cost=500,
        weight=4,
        range=200,
        damage='3D',
        magazineCapacity=30,
        magazineCost=15,
        traits='Auto 2',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Assault Shotgun',
        techLevel=6,
        cost=500,
        weight=5,
        range=50,
        damage='4D',
        magazineCapacity=24,
        magazineCost=40,
        traits='Auto 2, Bulky',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Autorifle',
        techLevel=6,
        cost=750,
        weight=5,
        range=300,
        damage='3D',
        magazineCapacity=20,
        magazineCost=10,
        traits='Auto 2',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Big Game Rifle',
        techLevel=5,
        cost=1250,
        weight={
            StockWeaponSet.CSC2: 9,
            StockWeaponSet.CSC2023: 8},
        range=200,
        damage='3D+3',
        magazineCapacity=5,
        magazineCost=50,
        traits='Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Flechette Submachine Gun',
        techLevel=9,
        cost=500,
        weight=3,
        range=20,
        damage='3D-2',
        magazineCapacity=40,
        magazineCost=20,
        traits='Auto 3, Silent',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Gauss Assault Gun',
        techLevel=12,
        cost=1300,
        weight=2,
        range=20,
        damage='4D',
        magazineCapacity=36,
        magazineCost=35,
        traits='AP 5, Auto 2',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugRifleDescription(
        name='Gauss Rifle',
        techLevel=12,
        cost=1500,
        weight=4,
        range=600,
        damage='4D',
        magazineCapacity=80,
        magazineCost={
            StockWeaponSet.Core2: 40,
            StockWeaponSet.Core2022: 40,
            StockWeaponSet.CSC2: 40,
            StockWeaponSet.CSC2023: 80},
        traits='AP 5, Auto 3, Scope',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Gauss Sniper RIfle',
        techLevel=12,
        cost=2500,
        weight=4,
        range=1000,
        damage='5D',
        magazineCapacity=12,
        magazineCost=20,
        traits='AP 6, Scope',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Gauss Submachine Gun',
        techLevel=12,
        cost=1000,
        weight=3,
        range=50,
        damage='3D+2',
        magazineCapacity=60,
        magazineCost=60,
        traits='AP 3, Auto 4',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugRifleDescription(
        name='Heavy Advanced Combat Rifle',
        techLevel=10,
        cost=2000,
        weight=5,
        range=450,
        damage='4D',
        magazineCapacity=30,
        magazineCost=20,
        traits='Auto 2, Bulky, Scope',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Light Shotgun',
        techLevel=4,
        cost=150,
        weight=3,
        range=40,
        damage='3D',
        magazineCapacity=6,
        magazineCost=10,
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugRifleDescription(
        name='Magrail Rifle',
        techLevel=14,
        cost=2500,
        weight=4,
        range=150,
        damage='4D+3',
        magazineCapacity=30,
        magazineCost=100,
        traits='Auto 6',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Rifle',
        techLevel=5,
        cost=200,
        weight={
            StockWeaponSet.Core2: 5,
            StockWeaponSet.Core2022: 3,
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 3},
        range=250,
        damage='3D',
        magazineCapacity=5,
        magazineCost=10,
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Sawed-Off Shotgun',
        techLevel={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 4},
        cost=200,
        weight=2,
        range=10,
        damage='4D',
        magazineCapacity=1,
        magazineCost={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 10},
        traits='Bulky',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Shotgun',
        techLevel=4,
        cost=200,
        weight=4,
        range=50,
        damage='4D',
        magazineCapacity=6,
        magazineCost=10,
        traits='Bulky',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockSlugRifleDescription(
        name='Sniper Rifle',
        techLevel=8,
        cost=700,
        weight=5,
        range=500,
        damage='3D',
        magazineCapacity=4,
        magazineCost=10,
        traits='AP 5, Scope, Silent',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Snub Carbine',
        techLevel=11,
        cost=500,
        weight=1,
        range=75,
        damage='3D-3',
        magazineCapacity=20,
        magazineCost=30,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockSlugRifleDescription(
        name='Spear Gun',
        techLevel=6,
        cost=50,
        weight=2,
        range=25,
        damage='3D',
        magazineCapacity=1,
        magazineCost=10,
        traits='Silent',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockSlugRifleDescription(
        name='Submachine Gun',
        techLevel=6,
        cost=400,
        weight=3,
        range=25,
        damage='3D',
        magazineCapacity=20,
        magazineCost=10,
        traits='Auto 3',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),


    #  ██████████                                                      ███████████   ███           █████             ████
    # ░░███░░░░░█                                                     ░░███░░░░░███ ░░░           ░░███             ░░███
    #  ░███  █ ░  ████████    ██████  ████████   ███████ █████ ████    ░███    ░███ ████   █████  ███████    ██████  ░███
    #  ░██████   ░░███░░███  ███░░███░░███░░███ ███░░███░░███ ░███     ░██████████ ░░███  ███░░  ░░░███░    ███░░███ ░███
    #  ░███░░█    ░███ ░███ ░███████  ░███ ░░░ ░███ ░███ ░███ ░███     ░███░░░░░░   ░███ ░░█████   ░███    ░███ ░███ ░███
    #  ░███ ░   █ ░███ ░███ ░███░░░   ░███     ░███ ░███ ░███ ░███     ░███         ░███  ░░░░███  ░███ ███░███ ░███ ░███
    #  ██████████ ████ █████░░██████  █████    ░░███████ ░░███████     █████        █████ ██████   ░░█████ ░░██████  █████
    # ░░░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░░      ░░░░░███  ░░░░░███    ░░░░░        ░░░░░ ░░░░░░     ░░░░░   ░░░░░░  ░░░░░
    #                                           ███ ░███  ███ ░███
    #                                          ░░██████  ░░██████
    #                                           ░░░░░░    ░░░░░░

    _StockEnergyPistolDescription(
        name='Gauntlet Laser',
        techLevel=10,
        cost=2500,
        weight={
            StockWeaponSet.CSC2: 4,
            StockWeaponSet.CSC2023: 2},
        range=20,
        damage='3D',
        magazineCapacity=100,
        magazineCost=1100,
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        # NOTE: The spreadsheet has these as linkable but that doesn't make
        # sense with the current implementation of the rules as we've said you
        # can't link across manipulator and you could only have one gauntlet
        # per manipulator
        linkable=False,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Hand Flamer',
        techLevel=10,
        cost=1500,
        weight=2,
        range=5,
        damage='3D',
        magazineCapacity=5,
        magazineCost=25,
        traits='Blast 2, Fire',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Laser Pistol - TL 9',
        techLevel=9,
        cost=2000,
        weight={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        range=20,
        damage='3D',
        magazineCapacity=100,
        magazineCost=1000,
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyPistolDescription(
        name='Laser Pistol - TL 11',
        techLevel=11,
        cost=3000,
        weight={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 1,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        range=30,
        damage='3D+3',
        magazineCapacity=100,
        magazineCost=3000,
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyPistolDescription(
        name='Maser Pistol',
        techLevel=17,
        cost=25000,
        weight={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        range=20,
        damage='3D+3',
        magazineCapacity=12,
        traits='AP 10, Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Matter Disintegrator - TL 18',
        techLevel=18,
        cost=2500000,
        weight=1,
        range=5,
        damage='1DD',
        magazineCost=50000,
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Matter Disintegrator - TL 19',
        techLevel=19,
        cost=4000000,
        weight=1,
        range=10,
        damage='2DD',
        traits='Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Pepper Spray',
        techLevel=5,
        cost=5,
        range=3,
        damage='Special',
        magazineCapacity=5,
        magazineCost=5,
        robotMount=WeaponSize.Small,
        traits='Stun',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyPistolDescription(
        name='Personal Defence Laser',
        techLevel=13,
        cost=6000,
        weight={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        range=25,
        damage='3D+3',
        magazineCapacity=25,
        magazineCost=100,
        traits='Auto 2, Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyPistolDescription(
        name='Stunner - TL 8',
        techLevel=8,
        cost=500,
        weight=0.5,
        range=5,
        damage='2D',
        magazineCapacity=100,
        magazineCost=200,
        traits='Stun, Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyPistolDescription(
        name='Stunner - TL 10',
        techLevel=10,
        cost=750,
        weight={
            StockWeaponSet.Core2: 0.5,
            StockWeaponSet.Core2022: None,
            StockWeaponSet.CSC2: 0.5,
            StockWeaponSet.CSC2023: None},
        range=5,
        damage='2D+3',
        magazineCapacity=100,
        magazineCost=200,
        traits='Stun, Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyPistolDescription(
        name='Stunner - TL 12',
        techLevel=12,
        cost=1000,
        weight={
            StockWeaponSet.Core2: 0.5,
            StockWeaponSet.Core2022: None,
            StockWeaponSet.CSC2: 0.5,
            StockWeaponSet.CSC2023: None},
        range=10,
        damage='3D',
        magazineCapacity=100,
        magazineCost=200,
        traits='Stun, Zero-G',
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_AllCompatible),


    #  ██████████                                                      ███████████    ███     ██████  ████
    # ░░███░░░░░█                                                     ░░███░░░░░███  ░░░     ███░░███░░███
    #  ░███  █ ░  ████████    ██████  ████████   ███████ █████ ████    ░███    ░███  ████   ░███ ░░░  ░███   ██████
    #  ░██████   ░░███░░███  ███░░███░░███░░███ ███░░███░░███ ░███     ░██████████  ░░███  ███████    ░███  ███░░███
    #  ░███░░█    ░███ ░███ ░███████  ░███ ░░░ ░███ ░███ ░███ ░███     ░███░░░░░███  ░███ ░░░███░     ░███ ░███████
    #  ░███ ░   █ ░███ ░███ ░███░░░   ░███     ░███ ░███ ░███ ░███     ░███    ░███  ░███   ░███      ░███ ░███░░░
    #  ██████████ ████ █████░░██████  █████    ░░███████ ░░███████     █████   █████ █████  █████     █████░░██████
    # ░░░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░░      ░░░░░███  ░░░░░███    ░░░░░   ░░░░░ ░░░░░  ░░░░░     ░░░░░  ░░░░░░
    #                                           ███ ░███  ███ ░███
    #                                          ░░██████  ░░██████
    #                                           ░░░░░░    ░░░░░░

    _StockEnergyRifleDescription(
        name='Cartridge Laser Carbine - TL 10',
        techLevel=10,
        cost=2500,
        weight=3,
        range=150,
        damage='4D',
        magazineCapacity=15,
        magazineCost=70,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Cartridge Laser Carbine - TL 12',
        techLevel=12,
        cost=4000,
        weight=2.5,
        range=200,
        damage='4D+3',
        magazineCapacity=20,
        magazineCost=70,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Cartridge Laser Rifle - TL 10',
        techLevel=10,
        cost=3500,
        weight=5,
        range=200,
        damage='5D',
        magazineCapacity=20,
        magazineCost=150,
        traits='Auto 3, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Cartridge Laser Rifle - TL 12',
        techLevel=12,
        cost=8000,
        weight=4,
        range=400,
        damage='5D+3',
        magazineCapacity=25,
        magazineCost=150,
        traits='Auto 3, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Cryo Rifle',
        techLevel=13,
        cost=6000,
        weight=9,
        range=10,
        damage='4D',
        magazineCapacity=12,
        magazineCost=150,
        traits='Blast 3',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Flame Rifle',
        techLevel=9,
        cost=2500,
        weight=8,
        range=10,
        damage='4D',
        magazineCapacity=10,
        magazineCost=50,
        traits='Blast 3, Fire',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Heavy Laser Rifle',
        techLevel=12,
        cost=14000,
        weight={
            StockWeaponSet.CSC2: 18,
            StockWeaponSet.CSC2023: 12},
        range=1200,
        damage='6D',
        magazineCapacity=12,
        magazineCost=500,
        traits='Scope, Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Ion Rifle - TL 14',
        techLevel=14,
        cost=16000,
        weight=6,
        range=600,
        damage='Special',
        magazineCapacity=100,
        magazineCost=5000,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Ion Rifle - TL 15',
        techLevel=15,
        cost=24000,
        weight=5,
        range=800,
        damage='Special',
        magazineCapacity=100,
        magazineCost=8000,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Laser Carbine - TL 9',
        techLevel=9,
        cost=2500,
        weight=4,
        range=150,
        damage='4D',
        magazineCapacity=50,
        magazineCost=1000,
        traits='Zero-G',
        linkable=True,
        robotMount=WeaponSize.Medium,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Laser Carbine - TL 11',
        techLevel=11,
        cost=4000,
        weight={
            StockWeaponSet.Core2: 3,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        range=200,
        damage='4D+3',
        magazineCapacity=50,
        magazineCost=3000,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Laser Rifle - TL 9',
        techLevel=9,
        cost=3500,
        weight={
            StockWeaponSet.Core2: 8,
            StockWeaponSet.Core2022: 5,
            StockWeaponSet.CSC2: 8,
            StockWeaponSet.CSC2023: 5},
        range=200,
        damage='5D',
        magazineCapacity=100,
        magazineCost=1500,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Laser Rifle - TL 11',
        techLevel=11,
        cost=8000,
        weight={
            StockWeaponSet.Core2: 5,
            StockWeaponSet.Core2022: 3,
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 3},
        range=400,
        damage='5D+3',
        magazineCapacity=100,
        magazineCost=3500,
        traits='Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Laser Sniper Rifle',
        techLevel=12,
        cost=9000,
        weight={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 4,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 4},
        range=600,
        damage={
            StockWeaponSet.Core2: '5D+3',
            StockWeaponSet.Core2022: '5D+3',
            StockWeaponSet.CSC2: '6D+3',
            StockWeaponSet.CSC2023: '5D+3'},
        magazineCapacity=6,
        magazineCost=250,
        traits='Scope, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Maser Rifle',
        techLevel=16,
        cost=30000,
        weight=8,
        range=300,
        damage='5D+3',
        magazineCapacity=20,
        traits='AP 10, Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Plasma Rifle',
        techLevel=16,
        cost=100000,
        weight={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 4,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 4},
        range=300,
        damage={
            StockWeaponSet.Core2: '6D',
            StockWeaponSet.Core2022: '6D',
            StockWeaponSet.CSC2: '1DD',
            StockWeaponSet.CSC2023: '6D'},
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockEnergyRifleDescription(
        name='Solar Beam Rifle',
        techLevel=17,
        cost=200000,
        weight=4,
        range=500,
        damage='1DD',
        magazineCapacity=20,
        traits='AP 20, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Stagger Laser Rifle - TL 12',
        techLevel=12,
        cost=10000,
        weight={
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 4},
        range=300,
        damage='5D',
        magazineCapacity=50,
        magazineCost=5000,
        traits='Auto 2, Zero-G',
        linkable=True,
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Stagger Laser Rifle - TL 14',
        techLevel=14,
        cost=15000,
        weight={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 3},
        range=350,
        damage='5D+3',
        magazineCapacity=100,
        magazineCost=6000,
        traits='Auto 3, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockEnergyRifleDescription(
        name='Stun Blaster',
        techLevel=13,
        cost=3000,
        weight=5,
        range=20,
        damage='4D',
        magazineCapacity=200,
        magazineCost=500,
        traits='Stun, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockEnergyRifleDescription(
        name='Stun Carbine',
        techLevel=12,
        cost=2000,
        weight=4,
        range=20,
        damage='3D',
        magazineCapacity=50,
        magazineCost=200,
        traits='Stun, Zero-G',
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),


    #    █████████                      █████                 ███
    #   ███░░░░░███                    ░░███                 ░░░
    #  ░███    ░███  ████████   ██████  ░███████    ██████   ████   ██████
    #  ░███████████ ░░███░░███ ███░░███ ░███░░███  ░░░░░███ ░░███  ███░░███
    #  ░███░░░░░███  ░███ ░░░ ░███ ░░░  ░███ ░███   ███████  ░███ ░███ ░░░
    #  ░███    ░███  ░███     ░███  ███ ░███ ░███  ███░░███  ░███ ░███  ███
    #  █████   █████ █████    ░░██████  ████ █████░░████████ █████░░██████
    # ░░░░░   ░░░░░ ░░░░░      ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░ ░░░░░  ░░░░░░

    # NOTE: The Atlatl isn't a weapon it's a tool that allows you to throw
    # darts or javelin better. It doubles the range and allows you to add
    # your DEX _AND_ STR bonus to the damage.
    _StockArchaicWeaponDescription(
        name='Atlatl - Dart',
        techLevel=0,
        cost=30, # Cost of Atlatl + Dart
        weight=1.5, # Weigh of Atlatl + Dart
        range=100, # Range of Dart + 100%
        damage='2D-2 + STR & DEX bonus',
        magazineCapacity=1,
        magazineCost=10, # Cost of Dart
        traits='One Use, Silent',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockArchaicWeaponDescription(
        name='Atlatl - Javelin',
        techLevel=0,
        cost=30, # Cost of Atlatl + Javelin
        weight=2, # Weigh of Atlatl + Javelin
        range=50, # Range of Javelin + 100%
        damage='2D + STR & DEX bonus',
        magazineCapacity=1,
        magazineCost=10, # Cost of Javelin
        traits={
            StockWeaponSet.CSC2: 'One Shot',
            StockWeaponSet.CSC2023: 'One Shot, Silent'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Compound Cam Bow',
        techLevel=5,
        cost=250,
        weight=1,
        range=100,
        damage='3D-3',
        magazineCapacity=1,
        magazineCost=5,
        traits={
            StockWeaponSet.CSC2: 'AP 2',
            StockWeaponSet.CSC2023: 'AP 2, Silent'},
        linkable=True,
        robotMount=WeaponSize.Medium,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Crossbow',
        techLevel={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=200,
        weight=3,
        damage='3D-3',
        magazineCapacity=1,
        magazineCost={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 1},
        traits={
            StockWeaponSet.CSC2: 'AP 2',
            StockWeaponSet.CSC2023: 'AP 2, Silent'},
        linkable=True,
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Dart',
        techLevel=0,
        cost=10,
        weight=0.5,
        range=50,
        damage='2D-2',
        traits='One Shot, Silent',
        robotMount=WeaponSize.Small,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockArchaicWeaponDescription(
        name='Javelin',
        techLevel={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        cost={
            StockWeaponSet.CSC2: 15,
            StockWeaponSet.CSC2023: 10},
        weight=1,
        range=25,
        damage='2D',
        traits={
            StockWeaponSet.CSC2: 'One Shot',
            StockWeaponSet.CSC2023: 'One Shot, Silent'},
        robotMount=WeaponSize.Small,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Long Bow',
        techLevel={
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 1},
        cost=150,
        weight=1.5,
        range=100,
        damage='3D-3',
        magazineCapacity=1,
        magazineCost={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 1},
        traits={
            StockWeaponSet.CSC2: 'AP 2, Bulky, Silent',
            StockWeaponSet.CSC2023: 'AP 2, Silent'},
        robotMount=WeaponSize.Medium,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Repeating Crossbow',
        techLevel={
            StockWeaponSet.CSC2: 3,
            StockWeaponSet.CSC2023: 2},
        cost=400,
        weight=4,
        range=75,
        damage='2D',
        magazineCapacity=6,
        magazineCost={
            StockWeaponSet.CSC2: 30,
            StockWeaponSet.CSC2023: 6},
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'Silent'},
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArchaicWeaponDescription(
        name='Short Bow',
        techLevel={
            StockWeaponSet.CSC2: 1,
            StockWeaponSet.CSC2023: 0},
        cost=50,
        weight=1,
        range=75,
        damage='2D-3',
        magazineCapacity=1,
        magazineCost={
            StockWeaponSet.CSC2: 5,
            StockWeaponSet.CSC2023: 1},
        traits={
            StockWeaponSet.CSC2: '',
            StockWeaponSet.CSC2023: 'Silent'},
        robotMount=WeaponSize.Small,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),


    #    █████████                                              █████
    #   ███░░░░░███                                            ░░███
    #  ███     ░░░  ████████   ██████  ████████    ██████    ███████   ██████
    # ░███         ░░███░░███ ███░░███░░███░░███  ░░░░░███  ███░░███  ███░░███
    # ░███    █████ ░███ ░░░ ░███████  ░███ ░███   ███████ ░███ ░███ ░███████
    # ░░███  ░░███  ░███     ░███░░░   ░███ ░███  ███░░███ ░███ ░███ ░███░░░
    #  ░░█████████  █████    ░░██████  ████ █████░░████████░░████████░░██████
    #   ░░░░░░░░░  ░░░░░      ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░  ░░░░░░░░  ░░░░░░

    _StockGrenadeDescription(
        name='Aerosol Grenade',
        techLevel=9,
        cost=15,
        weight=0.5,
        range=20,
        traits='Blast 9',
        weaponSets=_AllCompatible),
    _StockGrenadeDescription(
        name='Chemical Grenade', # NOTE: Not in original CSC
        techLevel=5,
        cost=50,
        weight=0.5,
        range=20,
        damage='Special',
        traits='Blast 9',
        weaponSets=_SupplyCatalogueCompatible),
    _StockGrenadeDescription(
        name='EMP Grenade',
        techLevel=9,
        cost=100,
        weight=0.5,
        range=20,
        traits='Blast 6',
        weaponSets=_SupplyCatalogueCompatible),
    _StockGrenadeDescription(
        name='Frag Grenade',
        techLevel=6,
        cost=30,
        weight=0.5,
        range=20,
        damage='5D',
        traits='Blast 9',
        weaponSets=_AllCompatible),
    _StockGrenadeDescription(
        name='Incendiary Grenade',
        techLevel={
            StockWeaponSet.CSC2: 8,
            StockWeaponSet.CSC2023: 7},
        cost=75,
        weight=0.5,
        range=20,
        damage='2D',
        traits='Blast 3, Fire',
        weaponSets=_SupplyCatalogueCompatible),
    _StockGrenadeDescription(
        name='Neurotoxin Grenade',
        techLevel=9,
        cost=250,
        weight=0.5,
        range=20,
        damage='Special',
        traits='Blast 9',
        weaponSets=_SupplyCatalogueCompatible),
    _StockGrenadeDescription(
        name='Plasma Grenade',
        techLevel=16,
        cost=500,
        weight=0.5,
        range=20,
        damage='8D',
        traits='Blast 6',
        weaponSets=_SupplyCatalogueCompatible),
    _StockGrenadeDescription(
        name='Smoke Grenade',
        techLevel=6,
        cost=15,
        weight=0.5,
        range=20,
        traits='Blast 9',
        weaponSets=_AllCompatible),
    _StockGrenadeDescription(
        name='Stun Grenade',
        techLevel=7,
        cost=30,
        weight=0.5,
        range=20,
        damage='3D',
        traits='Blast 9, Stun',
        weaponSets=_AllCompatible),
    _StockGrenadeDescription(
        name='Thermal Smoke Grenade',
        techLevel=7,
        cost=30,
        weight=0.5,
        range=20,
        traits='Blast 9',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockGrenadeDescription(
        name='Tranq Gas Grenade',
        techLevel=8,
        cost=75,
        range=20,
        damage='Special',
        traits='Blast 9',
        weaponSets=[StockWeaponSet.CSC2023]),


    #  ██████████                       ████                    ███
    # ░░███░░░░░█                      ░░███                   ░░░
    #  ░███  █ ░  █████ █████ ████████  ░███   ██████   █████  ████  █████ █████  ██████
    #  ░██████   ░░███ ░░███ ░░███░░███ ░███  ███░░███ ███░░  ░░███ ░░███ ░░███  ███░░███
    #  ░███░░█    ░░░█████░   ░███ ░███ ░███ ░███ ░███░░█████  ░███  ░███  ░███ ░███████
    #  ░███ ░   █  ███░░░███  ░███ ░███ ░███ ░███ ░███ ░░░░███ ░███  ░░███ ███  ░███░░░
    #  ██████████ █████ █████ ░███████  █████░░██████  ██████  █████  ░░█████   ░░██████
    # ░░░░░░░░░░ ░░░░░ ░░░░░  ░███░░░  ░░░░░  ░░░░░░  ░░░░░░  ░░░░░    ░░░░░     ░░░░░░
    #                         ░███
    #                         █████
    #                        ░░░░░

    _StockExplosiveDescription(
        name='Breaching Charge',
        techLevel=8,
        cost=250,
        weight=1,
        damage='4D',
        traits='AP 6, Blast 1',
        weaponSets=_SupplyCatalogueCompatible),
    _StockExplosiveDescription(
        name='Complex Chemical Charge',
        techLevel=10,
        cost=500,
        weight=1,
        damage='4D',
        traits='AP 15, Blast 9',
        weaponSets=_SupplyCatalogueCompatible),
    _StockExplosiveDescription(
        name='Fusion Block',
        techLevel=16,
        cost=10000,
        weight=1,
        damage='1DD',
        traits={
            StockWeaponSet.CSC2: 'Blast 12, Radiation',
            StockWeaponSet.CSC2023: 'AP 50, Blast 12, Radiation'},
        weaponSets=_SupplyCatalogueCompatible),
    _StockExplosiveDescription(
        name='Neutrino Detonator',
        techLevel=17,
        cost=50000,
        weight=1,
        damage='8D',
        traits={
            StockWeaponSet.CSC2: 'Blast 25',
            StockWeaponSet.CSC2023: 'AP ∞, Blast 25'},
        weaponSets=_SupplyCatalogueCompatible),
    _StockExplosiveDescription(
        name='Plastic Explosive',
        techLevel=6,
        cost=200,
        weight={
            StockWeaponSet.Core2: None,
            StockWeaponSet.Core2022: None,
            StockWeaponSet.CSC2: None,
            StockWeaponSet.CSC2023: 1},
        damage='3D',
        traits='Blast 9',
        weaponSets=_AllCompatible),
    _StockExplosiveDescription(
        name='Pocket Nuke',
        techLevel=12,
        cost=250000,
        weight=4,
        damage='6DD',
        traits='Blast 1,000, Radiation',
        weaponSets=_AllCompatible),
    _StockExplosiveDescription(
        name='TDX',
        techLevel=12,
        cost=1000,
        weight={
            StockWeaponSet.Core2: None,
            StockWeaponSet.Core2022: None,
            StockWeaponSet.CSC2: None,
            StockWeaponSet.CSC2023: 1},
        damage='4D',
        traits='Blast 15',
        weaponSets=_AllCompatible),


    #  █████   █████                                              ███████████                      █████              █████     ████
    # ░░███   ░░███                                              ░░███░░░░░███                    ░░███              ░░███     ░░███
    #  ░███    ░███   ██████   ██████   █████ █████ █████ ████    ░███    ░███  ██████  ████████  ███████    ██████   ░███████  ░███   ██████
    #  ░███████████  ███░░███ ░░░░░███ ░░███ ░░███ ░░███ ░███     ░██████████  ███░░███░░███░░███░░░███░    ░░░░░███  ░███░░███ ░███  ███░░███
    #  ░███░░░░░███ ░███████   ███████  ░███  ░███  ░███ ░███     ░███░░░░░░  ░███ ░███ ░███ ░░░   ░███      ███████  ░███ ░███ ░███ ░███████
    #  ░███    ░███ ░███░░░   ███░░███  ░░███ ███   ░███ ░███     ░███        ░███ ░███ ░███       ░███ ███ ███░░███  ░███ ░███ ░███ ░███░░░
    #  █████   █████░░██████ ░░████████  ░░█████    ░░███████     █████       ░░██████  █████      ░░█████ ░░████████ ████████  █████░░██████
    # ░░░░░   ░░░░░  ░░░░░░   ░░░░░░░░    ░░░░░      ░░░░░███    ░░░░░         ░░░░░░  ░░░░░        ░░░░░   ░░░░░░░░ ░░░░░░░░  ░░░░░  ░░░░░░
    #                                                ███ ░███
    #                                               ░░██████
    #                                                ░░░░░░

    _StockHeavyPortableWeaponDescription(
        name='Anti-Material Rifle',
        techLevel=7,
        cost=3000,
        weight=15,
        range=1000,
        damage='5D',
        magazineCapacity=1,
        magazineCost={
            StockWeaponSet.CSC2: 100,
            StockWeaponSet.CSC2023: 10},
        traits='AP 5, Scope, Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='ARL - PDW',
        techLevel=10,
        cost=200,
        weight=3,
        range=50,
        damage='4D',
        magazineCapacity=20,
        magazineCost=100,
        traits='Auto 4, Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='ARL - Standard',
        techLevel=10,
        cost=800,
        weight=4,
        range=80,
        damage='4D',
        magazineCapacity=20,
        magazineCost=100,
        traits='Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='ARL - Support',
        techLevel=10,
        cost=1300,
        weight=2,
        range=80,
        damage='4D',
        magazineCapacity=40,
        magazineCost=200,
        traits='Auto 4, Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='CPPG-11',
        techLevel=11,
        cost=8000,
        weight=12,
        range=200,
        damage='6D',
        magazineCapacity=6,
        magazineCost=300,
        traits='AP 6, Blast 2, Bulky, Scope',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='CPPG-12',
        techLevel=12,
        cost=15000,
        weight=12,
        range=300,
        damage='8D',
        magazineCapacity=6,
        magazineCost=450,
        traits='AP 8, Blast 3, Bulky, Scope',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='CPPG-13',
        techLevel=13,
        cost=25000,
        weight=10,
        range=500,
        damage='1DD',
        magazineCapacity=6,
        magazineCost=600,
        traits='AP 10, Blast 3, Bulky, Scope',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Cryojet',
        techLevel=11,
        cost=4000,
        weight=14,
        range=10,
        damage='4D',
        magazineCapacity=16,
        magazineCost=200,
        traits='Blast 5, Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Disposable Plasma Launcher',
        techLevel=12,
        cost=8000,
        weight=8,
        range=300,
        damage='2DD',
        traits='One Use, Smart',
        robotMount=WeaponSize.Heavy,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Early Machinegun',
        techLevel=4,
        cost=1200,
        weight=14,
        range=400,
        damage='3D',
        magazineCapacity=30,
        magazineCost=100,
        traits='Auto 3, Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='FGHP-14', # NOTE: FGMP in Core 2e rules
        techLevel=14,
        cost=100000,
        weight=12,
        range=450,
        damage='2DD',
        traits='Radiation, Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='FGHP-15', # NOTE: FGMP in Core 2e rules
        techLevel=15,
        cost=400000,
        weight=12,
        range=450,
        damage='2DD',
        traits='Bulky, Radiation',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='FGHP-16', # NOTE: FGMP in Core 2e rules
        techLevel=16,
        cost=500000,
        weight=15,
        range=450,
        damage='2DD',
        traits='Radiation',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Flamethrower - TL 4',
        techLevel=4,
        cost=800,
        weight=20,
        range=5,
        damage='3D',
        magazineCapacity=30,
        magazineCost=60,
        traits='Blast 5, Bulky, Fire',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Flamethrower - TL 6',
        techLevel=6,
        cost=1500,
        weight=15,
        range=5,
        damage='4D',
        magazineCapacity=40,
        magazineCost=80,
        traits='Blast 5, Bulky, Fire',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Flamethrower - TL 8',
        techLevel=8,
        cost=2000,
        weight=10,
        range=10,
        damage='4D',
        magazineCapacity=50,
        magazineCost=100,
        traits='Blast 5, Fire',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Grenade Launcher',
        techLevel=7,
        cost=400,
        weight={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 6,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 2},
        range=100,
        damage='As grenade',
        magazineCapacity=6,
        traits={
            StockWeaponSet.Core2: 'Bulky',
            StockWeaponSet.Core2022: 'Bulky',
            StockWeaponSet.CSC2: 'Bulky',
            StockWeaponSet.CSC2023: ''},
        robotMount=WeaponSize.Medium,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Light Assault Gun',
        techLevel=8,
        cost=4000,
        weight=40,
        range=800,
        damage='7D',
        magazineCapacity=5,
        magazineCost=100,
        traits='AP 5, Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='Light Gatling Laser',
        techLevel=9,
        cost=4500,
        weight=18,
        range=180,
        damage='3D',
        magazineCapacity=100,
        magazineCost=300,
        traits='Auto 4, Zero-G',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockHeavyPortableWeaponDescription(
        name='Machinegun',
        techLevel={
            StockWeaponSet.Core2: 6,
            StockWeaponSet.Core2022: 6,
            StockWeaponSet.CSC2: 6,
            StockWeaponSet.CSC2023: 5},
        cost=1500,
        weight={
            StockWeaponSet.Core2: 12,
            StockWeaponSet.Core2022: 10,
            StockWeaponSet.CSC2: 12,
            StockWeaponSet.CSC2023: 10},
        range=500,
        damage='3D',
        magazineCapacity=60,
        magazineCost=100,
        traits={
            StockWeaponSet.Core2: 'Auto 4',
            StockWeaponSet.Core2022: 'Auto 4',
            StockWeaponSet.CSC2: 'Auto 4',
            StockWeaponSet.CSC2023: 'Auto 4, Bulky'},
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='PGHP-12', # NOTE: PGMP in Core 2e rules
        techLevel=12,
        cost=20000,
        weight=10,
        range=250,
        damage='1DD',
        traits='Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='PGHP-13', # NOTE: PGMP in Core 2e rules
        techLevel=13,
        cost=65000,
        weight=10,
        range=450,
        damage='1DD',
        traits='Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='PGHP-14', # NOTE: PGMP in Core 2e rules
        techLevel=14,
        cost=100000,
        weight=10,
        range=450,
        damage='1DD',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Plasma Jet - TL 12',
        techLevel=12,
        cost=16000,
        weight=10,
        range=25,
        damage='1DD',
        traits='Blast 5, Very Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Plasma Jet - TL 14',
        techLevel=14,
        cost=80000,
        weight=10,
        range=50,
        damage='1DD',
        traits='Blast 10, Bulky',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='RAM Grenade Launcher',
        techLevel=8,
        cost=800,
        weight={
            StockWeaponSet.Core2: 2,
            StockWeaponSet.Core2022: 2,
            StockWeaponSet.CSC2: 2,
            StockWeaponSet.CSC2023: 6},
        range=250,
        damage='As Grenade',
        magazineCapacity=6,
        traits='Auto 3, Bulky',
        robotMount=WeaponSize.Medium,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Rapid-Fire Machinegun',
        techLevel=7,
        cost=3000,
        weight=12,
        range=500,
        damage='3D',
        magazineCapacity=60,
        magazineCost=100,
        traits='Auto 4 (8)',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Rocket Launcher - TL 6',
        techLevel=6,
        cost=2000,
        weight=8,
        range=120,
        damage='4D',
        magazineCapacity=1,
        magazineCost=300,
        traits='Blast 6',
        robotMount=WeaponSize.Heavy,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Rocket Launcher - TL 7',
        techLevel=7,
        cost=2000,
        weight=8,
        range=150,
        damage='4D+3',
        magazineCapacity=1,
        magazineCost=400,
        traits='Blast 6, Smart',
        robotMount=WeaponSize.Heavy,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Rocket Launcher - TL 8',
        techLevel=8,
        cost=2000,
        weight=8,
        range=200,
        damage='5D',
        magazineCapacity=2,
        magazineCost=600,
        traits='Blast 6, Scope, Smart',
        robotMount=WeaponSize.Heavy,
        weaponSets=_AllCompatible),
    _StockHeavyPortableWeaponDescription(
        name='Rocket Launcher - TL 9',
        techLevel=9,
        cost=2000,
        weight=8,
        range=250,
        damage='5D+6',
        magazineCapacity=2,
        magazineCost=800,
        traits='Blast 6, Scope, Smart',
        robotMount=WeaponSize.Heavy,
        weaponSets=_AllCompatible),


    #    █████████              █████     ███  ████  ████
    #   ███░░░░░███            ░░███     ░░░  ░░███ ░░███
    #  ░███    ░███  ████████  ███████   ████  ░███  ░███   ██████  ████████  █████ ████
    #  ░███████████ ░░███░░███░░░███░   ░░███  ░███  ░███  ███░░███░░███░░███░░███ ░███
    #  ░███░░░░░███  ░███ ░░░   ░███     ░███  ░███  ░███ ░███████  ░███ ░░░  ░███ ░███
    #  ░███    ░███  ░███       ░███ ███ ░███  ░███  ░███ ░███░░░   ░███      ░███ ░███
    #  █████   █████ █████      ░░█████  █████ █████ █████░░██████  █████     ░░███████
    # ░░░░░   ░░░░░ ░░░░░        ░░░░░  ░░░░░ ░░░░░ ░░░░░  ░░░░░░  ░░░░░       ░░░░░███
    #                                                                          ███ ░███
    #                                                                         ░░██████
    #                                                                          ░░░░░░

    _StockArtilleryDescription(
        name='Black Powder Mortar',
        techLevel=3,
        cost=2000,
        weight=500,
        range=500,
        damage='6D',
        magazineCapacity=1,
        magazineCost=50,
        traits='Artillery, Blast 6',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Bombardment Gun',
        techLevel=5,
        cost=500000,
        weight=220000,
        range=30000,
        damage='2DD',
        magazineCapacity=1,
        magazineCost=1500,
        traits='Artillery, Blast 20',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Demolition Gun',
        techLevel=6,
        cost=30000,
        weight=5000,
        range=100,
        damage='1DD',
        magazineCapacity=1,
        magazineCost=500,
        traits='AP 10, Artillery, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Heavy Bombardment Gun',
        techLevel=5,
        cost=750000,
        weight=500000,
        range=40000,
        damage='3DD',
        magazineCapacity=1,
        magazineCost=2500,
        traits='Artillery, Blast 20',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Heavy Gun',
        techLevel=8,
        cost=120000,
        weight=12000,
        range=12000,
        damage='1DD',
        magazineCapacity=1,
        magazineCost=400,
        traits='AP 8, Artillery, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Infantry Mortar',
        techLevel=5,
        cost=3500,
        weight=12,
        range=1000,
        damage={
            StockWeaponSet.CSC2: '2D',
            StockWeaponSet.CSC2023: '5D'},
        magazineCapacity=1,
        magazineCost=50,
        traits='Artillery, Blast 5',
        robotMount=WeaponSize.Heavy,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Light Howitzer',
        techLevel=5,
        cost=50000,
        weight=2000,
        range=6000,
        damage='8D',
        magazineCapacity=1,
        magazineCost=150,
        traits='Artillery, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Light Gun',
        techLevel=6,
        cost=75000,
        weight=2000,
        range=9000,
        damage='8D',
        magazineCapacity=1,
        magazineCost=200,
        traits='AP 5, Artillery, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Mass Driver',
        techLevel=12,
        cost=500000,
        weight=7000,
        range=40000,
        damage='1DD',
        magazineCapacity=1,
        magazineCost=750,
        traits='Artillery, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Siege Gun',
        techLevel=12,
        cost=19000000,
        weight=1200000,
        range=50000,
        damage='4DD',
        magazineCapacity=1,
        magazineCost=5000,
        traits='AP 10, Artillery, Blast 50',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockArtilleryDescription(
        name='Support Mortar',
        techLevel=7,
        cost=11000,
        # NOTE: The CSC 2023 has 0.25kg but I think this is a mistake and
        # just hasn't been converted from tons to kg correctly
        weight=250,
        range=3,
        damage='9D',
        magazineCapacity=1,
        magazineCost=100,
        traits='Artillery, Blast 6',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),


    #  █████   █████          █████       ███           ████
    # ░░███   ░░███          ░░███       ░░░           ░░███
    #  ░███    ░███   ██████  ░███████   ████   ██████  ░███   ██████
    #  ░███    ░███  ███░░███ ░███░░███ ░░███  ███░░███ ░███  ███░░███
    #  ░░███   ███  ░███████  ░███ ░███  ░███ ░███ ░░░  ░███ ░███████
    #   ░░░█████░   ░███░░░   ░███ ░███  ░███ ░███  ███ ░███ ░███░░░
    #     ░░███     ░░██████  ████ █████ █████░░██████  █████░░██████
    #      ░░░       ░░░░░░  ░░░░ ░░░░░ ░░░░░  ░░░░░░  ░░░░░  ░░░░░░

    _StockVehicleWeaponDescription(
        name='Aerospace Defence Laser',
        techLevel=12,
        cost=4000000,
        weight=12000,
        range=120000,
        damage='8D',
        traits={
            StockWeaponSet.CSC2: 'Track',
            StockWeaponSet.CSC2023: None},
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Light Autocannon',
        techLevel=6,
        cost=10000,
        weight=250,
        range=1000,
        # NOTE: The Core 2e rules have this as 1D (p136) but I think
        # that must be a miss-print as all other books have it as 6D
        damage='6D',
        magazineCapacity=500,
        magazineCost=1000,
        traits='Auto 3',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockVehicleWeaponDescription(
        name='Medium Autocannon',
        techLevel=6,
        cost=25000,
        weight=500,
        range=1000,
        damage='8D',
        magazineCapacity=100,
        magazineCost=1500,
        traits='Auto 3',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Heavy Autocannon',
        techLevel=6,
        cost=45000,
        weight=1000,
        range=1000,
        damage='1DD',
        magazineCapacity=100,
        magazineCost=2000,
        traits='Auto 3',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Black Powder Cannon',
        techLevel=3,
        cost=3000,
        weight=500,
        range=500,
        damage='7D',
        magazineCapacity=1,
        magazineCost=50,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Light Cannon',
        techLevel=5,
        cost=200000,
        weight=1000,
        range=1500,
        damage='6D',
        magazineCapacity=50,
        magazineCost=5000,
        traits='Blast 6',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='Medium Cannon', # NOTE: This is Cannon in Core rules and CSC 2
        techLevel=8,
        cost=400000,
        weight=2500,
        range=2000,
        damage={
            StockWeaponSet.Core2: '8D',
            StockWeaponSet.Core2022: '8D',
            StockWeaponSet.CSC2: '1DD',
            StockWeaponSet.CSC2023: '1DD'},
        magazineCapacity=30,
        magazineCost=5000,
        traits='Blast 10',
        linkable=True,
        weaponSets=_AllCompatible),
    _StockVehicleWeaponDescription(
        name='Heavy Cannon',
        techLevel={
            StockWeaponSet.CSC2: 8,
            StockWeaponSet.CSC2023: 7},
        cost=600000,
        weight=4000,
        range=3000,
        damage='2DD',
        magazineCapacity=10,
        magazineCost=5000,
        traits='Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Field Gun',
        techLevel=4,
        cost=5000,
        weight=500,
        range=1000,
        damage='8D',
        magazineCapacity=1,
        magazineCost=75,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Fusion Gun - TL 13',
        techLevel=13,
        cost=2000000,
        weight=4000,
        range=3000,
        damage='3DD',
        traits='AP 10, Blast 25, Radiation',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Fusion Gun - TL 14',
        techLevel=14,
        cost=3000000,
        weight=4000,
        range=5000,
        damage='3DD',
        traits='AP 20, Blast 20, Radiation',
        linkable=True,
        weaponSets=[StockWeaponSet.Core2, StockWeaponSet.CSC2, StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='Fusion Gun - TL 15',
        techLevel=13,
        cost=8000000,
        weight=4000,
        range=10000,
        damage='3DD',
        traits='AP 30, Blast 30, Radiation',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Gatling Laser',
        techLevel=8,
        cost=125000,
        weight=7000,
        range=4000,
        damage='6D',
        traits='AP 5, Auto 4',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Light Gauss Cannon',
        techLevel=12,
        cost=60000,
        weight=500,
        range=1000,
        damage='6D',
        magazineCapacity=200,
        magazineCost=800,
        traits='AP 5, Auto 3',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='Medium Gauss Cannon', # NOTE: This is Gauss Cannon in CSC2
        techLevel=12,
        cost=100000,
        weight=1000,
        range=2000,
        damage='1DD',
        magazineCapacity=200,
        magazineCost=1000,
        traits='AP 10, Auto 3',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Heavy Gauss Cannon',
        techLevel=12,
        cost=225000,
        weight=2000,
        range=3000,
        damage='2DD',
        magazineCapacity=60,
        magazineCost=800,
        traits='AP 15, Auto 2',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Heavy Machinegun',
        techLevel=6,
        cost=4500,
        weight=100,
        range=1000,
        damage={
            StockWeaponSet.Core2: '4D',
            StockWeaponSet.Core2022: '4D',
            StockWeaponSet.CSC2: '4D',
            StockWeaponSet.CSC2023: '5D'},
        magazineCapacity=100,
        magazineCost=400,
        traits='Auto 3',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_AllCompatible),
    _StockVehicleWeaponDescription(
        name='Hypervelocity Cannon',
        techLevel=13,
        cost=28000000,
        weight=20000,
        range=5000,
        damage='2DD',
        magazineCapacity=50,
        magazineCost=5000,
        traits='AP 30, Scope',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Light Laser Cannon',
        techLevel=9,
        cost=60000,
        weight=3000,
        range=2000,
        damage='8D',
        traits='AP 5',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='Medium Laser Cannon', # NOTE: This is Laser Cannon in Core and CSC 2e rules
        techLevel=9,
        cost=100000,
        weight=6000,
        range=2500,
        damage={
            StockWeaponSet.Core2: '4D',
            StockWeaponSet.Core2022: '1DD',
            StockWeaponSet.CSC2: '1DD',
            StockWeaponSet.CSC2023: '1DD'},
        traits='AP 10',
        linkable=True,
        weaponSets=_AllCompatible),
    _StockVehicleWeaponDescription(
        name='Heavy Laser Cannon',
        techLevel=9,
        cost=250000,
        weight=9000,
        range=25000,
        damage={
            StockWeaponSet.CSC2: '2DD',
            StockWeaponSet.CSC2023: '1DD'},
        traits='AP 20',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Meson Accelerator',
        techLevel=15,
        cost=20000000,
        weight=60000,
        range=150000,
        damage='4DD',
        traits={
            StockWeaponSet.CSC2: 'AP Special, Radiation',
            StockWeaponSet.CSC2023: 'AP ∞, Radiation'},
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Orbital Defence Cannon',
        techLevel=14,
        cost=40000000,
        weight=35000,
        range=5000,
        damage='4DD',
        magazineCapacity=20,
        magazineCost=10000,
        traits={
            StockWeaponSet.CSC2: 'AP 30, Scope, Track',
            StockWeaponSet.CSC2023: 'AP 30, Scope'},
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Plasma Gun-A',
        techLevel=10,
        cost=500000,
        weight=4000,
        range=6000,
        damage='2DD',
        traits='AP 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Plasma Gun-B',
        techLevel=11,
        cost=1000000,
        weight=4000,
        range=8000,
        damage='2DD',
        traits='AP 20',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Plasma Gun-C',
        techLevel=12,
        cost=1500000,
        weight=4000,
        range=10000,
        damage='2DD',
        traits='AP 30',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='Rail Gun',
        techLevel=9,
        cost=75000,
        weight=3000,
        range=4000,
        damage='1DD',
        magazineCapacity=50,
        magazineCost=2500,
        traits='AP 20',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockVehicleWeaponDescription(
        name='VRF Gauss Gun',
        techLevel=12,
        cost=20000,
        weight=250,
        range=750,
        damage='4D',
        magazineCapacity=400,
        magazineCost=1000,
        traits='AP 5, Auto 8',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='VRF Machinegun',
        techLevel=7,
        cost=12000,
        weight=250,
        range=500,
        damage='4D',
        magazineCapacity=400,
        magazineCost=1250,
        traits='Auto 6',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockVehicleWeaponDescription(
        name='Vulkan Machinegun',
        techLevel=7,
        cost=12000,
        weight=250,
        range=500,
        damage='4D',
        magazineCapacity=1000,
        magazineCost=1250,
        traits='Auto 6',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2]),


    #  █████                                                █████                   █████
    # ░░███                                                ░░███                   ░░███
    #  ░███         ██████   █████ ████ ████████    ██████  ░███████    ██████   ███████
    #  ░███        ░░░░░███ ░░███ ░███ ░░███░░███  ███░░███ ░███░░███  ███░░███ ███░░███
    #  ░███         ███████  ░███ ░███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███████ ░███ ░███
    #  ░███      █ ███░░███  ░███ ░███  ░███ ░███ ░███  ███ ░███ ░███ ░███░░░  ░███ ░███
    #  ███████████░░████████ ░░████████ ████ █████░░██████  ████ █████░░██████ ░░████████
    # ░░░░░░░░░░░  ░░░░░░░░   ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░   ░░░░░░░░

    # This section is missing some items

    _StockLaunchedWeaponDescription(
        name='Light Anti-Air Missile',
        techLevel=7,
        cost=5000,
        weight=250,
        range=5000,
        damage='6D',
        traits='One Use, Smart',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Anti-Air Missile',
        techLevel=7,
        cost=12000,
        weight=500,
        range=8000,
        damage='8D',
        traits='One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Long Range Anti-Air Missile',
        techLevel=7,
        cost=22000,
        weight=750,
        range=40000,
        damage='8D',
        traits='One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Anti-Tank Missile',
        techLevel=7,
        cost=2000,
        weight=500,
        range=6000,
        damage='8D',
        magazineCapacity=1,
        magazineCost=6000,
        traits='AP 30, One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Bolt Thrower',
        techLevel=1,
        cost=2000,
        weight=500,
        range=200,
        damage='4D',
        magazineCapacity=1,
        magazineCost=25,
        traits='AP 5',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Light Bomb',
        techLevel=4,
        cost=1500,
        weight=100,
        damage='1DD',
        traits='AP 20, Blast 20, One Use',
        robotMount=WeaponSize.Vehicle,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Medium Bomb',
        techLevel=4,
        cost=4000,
        weight=500,
        damage='2DD',
        traits='AP 25, Blast 25, One Use',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Heavy Bomb',
        techLevel=4,
        cost=8000,
        weight=1000,
        damage='3DD',
        traits='AP 30, Blast 30, One Use',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Bombardment Missile',
        techLevel=9,
        cost=36000,
        weight=1000,
        range=200000,
        damage='1DD',
        traits='AP 20, Blast 20, One Use, Smart',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Bombardment Rocket Rack',
        techLevel=6,
        cost=30000,
        weight=2000,
        range=8000,
        damage='5D',
        magazineCapacity=12,
        magazineCost=8000,
        traits='Auto 3, Blast 15',
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Earthquake Bomb',
        techLevel=4,
        cost=100000,
        weight=10000,
        range=2000,
        damage='5DD',
        magazineCapacity=12,
        magazineCost=8000,
        traits='Blast 250, One Use',
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Heavy Rocket Pod',
        techLevel=6,
        cost=12000,
        weight=500,
        range=2000,
        damage='6D',
        magazineCapacity=6,
        magazineCost=6000,
        traits='Auto 3, Blast 10',
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Plasma Missile Rack',
        techLevel=12,
        cost=1000000,
        weight=2000,
        range=50000,
        damage='4DD',
        magazineCapacity=12,
        magazineCost=400000,
        traits='AP 20, Auto 3, Blast 15, One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Rocket Pod',
        techLevel=6,
        cost=8000,
        weight=250,
        range=1500,
        damage='4D',
        magazineCapacity=18,
        magazineCost=8000,
        traits='Auto 3, Blast 5',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Rotary Autocannon',
        techLevel=7,
        cost=25000,
        weight=500,
        range=1000,
        damage='6D',
        magazineCapacity=500,
        magazineCost=1200,
        traits='Auto 3, Blast 5',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Tac Launcher - Anti-Aircraft',
        techLevel=10,
        cost=16000,
        weight=250,
        range=10000,
        damage='8D',
        magazineCapacity=4,
        magazineCost=8000,
        traits={
            StockWeaponSet.CSC2: 'Scope, Smart, Track',
            StockWeaponSet.CSC2023: 'Scope, Smart'},
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Tac Launcher - Anti-Personnel',
        techLevel=10,
        cost=12000,
        weight=250,
        range=6000,
        damage='4D',
        magazineCapacity=4,
        magazineCost=4000,
        traits='Blast 10, Scope, Smart',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Tac Launcher - Armour Piercing',
        techLevel=10,
        cost=15000,
        weight=250,
        range=6000,
        damage='8D',
        magazineCapacity=4,
        magazineCost=6000,
        traits='AP 10, Scope, Smart',
        robotMount=WeaponSize.Vehicle,
        linkable=True,
        weaponSets=_SupplyCatalogueCompatible),
    _StockLaunchedWeaponDescription(
        name='Torpedo - TL 4',
        techLevel=4,
        cost=3000,
        weight=500,
        range=1000,
        damage='1DD',
        magazineCapacity=4,
        magazineCost=6000,
        traits='AP 10, One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Torpedo - TL 5',
        techLevel=5,
        cost=5000,
        weight=500,
        range=5000,
        damage='3DD',
        magazineCapacity=4,
        magazineCost=6000,
        traits='AP 30, One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Torpedo - TL 8',
        techLevel=5,
        cost=12000,
        weight=500,
        range=50000,
        damage='5DD',
        magazineCapacity=4,
        magazineCost=6000,
        traits='AP 50, One Use, Smart',
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
    _StockLaunchedWeaponDescription(
        name='Water Cannon',
        techLevel=5,
        cost=2000,
        weight=500,
        range=100,
        magazineCapacity=10,
        linkable=True,
        weaponSets=[StockWeaponSet.CSC2023]),
]

_WeaponDescriptionMap = {
    weaponSet: {desc.name(): desc.createStockWeapon(weaponSet) for desc in _WeaponDescriptions if desc.isCompatible(weaponSet)} \
    for weaponSet in StockWeaponSet}

def lookupStockWeapon(
        name: str,
        weaponSet: StockWeaponSet
        ) -> typing.Optional[StockWeapon]:
    weaponMap = _WeaponDescriptionMap.get(weaponSet)
    return weaponMap.get(name)

def enumerateStockWeapons(
        weaponSet: StockWeaponSet,
        minTL: typing.Optional[int] = None,
        maxTL: typing.Optional[int] = None,
        category: typing.Optional[WeaponCategory] = None,
        skill: typing.Optional[traveller.SkillDefinition] = None,
        speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
        ) -> typing.Iterable[StockWeapon]:
    weaponMap = _WeaponDescriptionMap.get(weaponSet)
    if not weaponMap:
        return []

    weapons = []
    for weapon in weaponMap.values():
        if minTL != None and weapon.techLevel() < minTL:
            continue
        if maxTL != None and weapon.techLevel() > maxTL:
            continue
        if category != None and weapon.category() != category:
            continue
        if skill != None and weapon.skill() != skill:
            continue
        if speciality != None and weapon.specialty() != speciality:
            continue
        weapons.append(weapon)
    return weapons
