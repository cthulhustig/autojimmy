import common
import construction
import enum
import robots
import typing

class _MountSize(enum.Enum):
    Small = 'Small'
    Medium = 'Medium'
    Heavy = 'Heavy'
    Vehicle = 'Vehicle'

class _FireControlLevel(enum.Enum):
    Basic = 'Basic'
    Improved = 'Improved'
    Enhanced = 'Enhanced'
    Advanced = 'Advanced'

class _WeaponData(object):
    def __init__(
            self,
            name: str,
            techLevel: int,
            cost: int,
            size: _MountSize,
            skill: str,
            magazineCost: int = 0,
            multiLink: bool = False,
            damage: str = '',
            traits: str = ''
            ) -> None:
        self._name = name
        self._techLevel = techLevel
        self._cost = cost
        self._size = size
        self._skill = skill
        self._magazineCost = magazineCost
        self._multiLink = multiLink
        self._damage = damage
        self._traits = traits

    def name(self) -> str:
        return self._name
    
    def techLevel(self) -> int:
        return self._techLevel
    
    def cost(self) -> int:
        return self._cost
    
    def size(self) -> int:
        return self._size
    
    def skill(self) -> str:
        return self._skill

    def magazineCost(self) -> int:
        return self._magazineCost
        
    def multiLink(self) -> bool:
        return self._multiLink
    
    def damage(self) -> str:
        return self._damage
    
    def traits(self) -> str:
        return self._traits
    
# List of weapons taken from the MGT2 Robot Worksheet v1.50.01 spreadsheet
# IMPORTANT: These weapon names MUST remain constant between versions otherwise
# it will break weapons saved by older versions
# TODO: The multilink flag comes from the spreadsheet but I'm not currently
# using it. It's not clear where it's come from and why some weapons are
# multi-linkable and some aren't
_WeaponDataList = [
    _WeaponData(name='Aerosol Grenade', techLevel=9, cost=15, size=_MountSize.Small, skill='Athletics (Dexterity)', traits='Blast 9'),
    _WeaponData(name='Chemical Grenade', techLevel=5, cost=50, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='Special', traits='Blast 9'),
    _WeaponData(name='EMP Grenade', techLevel=9, cost=100, size=_MountSize.Small, skill='Athletics (Dexterity)', traits='Blast 6'),
    _WeaponData(name='Frag Grenade', techLevel=6, cost=30, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='5D', traits='Blast 9'),
    _WeaponData(name='Incendiary Grenade', techLevel=7, cost=75, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='2D', traits='Blast 3, Fire'),
    _WeaponData(name='Neurotoxin Grenade', techLevel=9, cost=250, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='Special', traits='Blast 9'),
    _WeaponData(name='Plasma Grenade', techLevel=16, cost=500, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='8D', traits='Blast 6'),
    _WeaponData(name='Smoke Grenade', techLevel=6, cost=15, size=_MountSize.Small, skill='Athletics (Dexterity)', traits='Blast 9'),
    _WeaponData(name='Stun Grenade', techLevel=7, cost=30, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='3D', traits='Blast 9, Stun'),
    _WeaponData(name='Thermal Smoke Grenade', techLevel=7, cost=30, size=_MountSize.Small, skill='Athletics (Dexterity)', traits='Blast 9'),
    _WeaponData(name='Tranq Gas Grenade', techLevel=8, cost=75, size=_MountSize.Small, skill='Athletics (Dexterity)', damage='Special', traits='Blast 9'),
    _WeaponData(name='Breaching Charge', techLevel=8, cost=250, size=_MountSize.Small, skill='Explosives', damage='4D', traits='AP 6, Blast 1'),
    _WeaponData(name='Complex Chemical Charge', techLevel=10, cost=500, size=_MountSize.Small, skill='Explosives', damage='4D', traits='AP 15, Blast 9'),
    _WeaponData(name='Fusion Block', techLevel=16, cost=10000, size=_MountSize.Small, skill='Explosives', damage='1DD', traits='AP 50, Blast 12, Radiation'),
    _WeaponData(name='Neutrino Detonator', techLevel=17, cost=50000, size=_MountSize.Small, skill='Explosives', damage='8D', traits='AP ∞, Blast 25'),
    _WeaponData(name='Plastic Explosive', techLevel=6, cost=200, size=_MountSize.Small, skill='Explosives', damage='3D', traits='Blast 9'),
    _WeaponData(name='Pocket Nuke', techLevel=12, cost=250000, size=_MountSize.Small, skill='Explosives', damage='6DD', traits='Blast 1,000, Radiation'),
    _WeaponData(name='TDX', techLevel=12, cost=1000, size=_MountSize.Small, skill='Explosives', damage='4D', traits='Blast 15'),
    _WeaponData(name='Atlatl', techLevel=0, cost=20, size=_MountSize.Small, skill='Gun Combat (Archaic)'),
    _WeaponData(name='Compound Cam Bow', techLevel=5, cost=250, size=_MountSize.Medium, skill='Gun Combat (Archaic)', magazineCost=5, multiLink=True, damage='3D-3', traits='AP 2, Silent'), 
    _WeaponData(name='Crossbow', techLevel=1, cost=200, size=_MountSize.Small, skill='Gun Combat (Archaic)', magazineCost=1, multiLink=True, damage='3D-3', traits='AP 2, Silent'),
    _WeaponData(name='Dart', techLevel=0, cost=10, size=_MountSize.Small, skill='Gun Combat (Archaic)', damage='2D-2', traits='One Use, Silent'),
    _WeaponData(name='Javelin', techLevel=0, cost=10, size=_MountSize.Small, skill='Gun Combat (Archaic)', damage='2D', traits='One Use, Silent'),
    _WeaponData(name='Long Bow', techLevel=1, cost=150, size=_MountSize.Medium, skill='Gun Combat (Archaic)', magazineCost=1, multiLink=True, damage='3D-3', traits='AP 2, Silent'),
    _WeaponData(name='Repeating Crossbow', techLevel=2, cost=400, size=_MountSize.Small, skill='Gun Combat (Archaic)', magazineCost=6, multiLink=True, damage='2D', traits='Silent'),        
    _WeaponData(name='Short Bow', techLevel=0, cost=50, size=_MountSize.Small, skill='Gun Combat (Archaic)', magazineCost=1, multiLink=True, damage='2D-3', traits='Silent'),
    _WeaponData(name='Cartridge Laser Carbine, TL 10', techLevel=10, cost=2500, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=70, multiLink=True, damage='4D', traits='Zero-G'),
    _WeaponData(name='Cartridge Laser Carbine, TL 12', techLevel=12, cost=4000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=70, multiLink=True, damage='4D+3', traits='Zero-G'),
    _WeaponData(name='Cartridge Laser Rifle, TL 10', techLevel=10, cost=3500, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=150, multiLink=True, damage='5D', traits='Auto 3, Zero-G'),
    _WeaponData(name='Cartridge Laser Rifle, TL 12', techLevel=12, cost=8000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=150, multiLink=True, damage='5D+3', traits='Auto 3, Zero-G'),
    _WeaponData(name='Cryo Rifle', techLevel=13, cost=6000, size=_MountSize.Heavy, skill='Gun Combat (Energy)', magazineCost=150, multiLink=True, damage='4D', traits='Blast 3'),
    _WeaponData(name='Flame Rifle', techLevel=9, cost=2500, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=50, multiLink=True, damage='4D', traits='Blast 3, Fire'),      
    _WeaponData(name='Gauntlet Laser', techLevel=10, cost=2500, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=1100, multiLink=True, damage='3D', traits='Zero-G'),        
    _WeaponData(name='Hand Flamer', techLevel=10, cost=1500, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=25, multiLink=True, damage='3D', traits='Blast 2, Fire'),      
    _WeaponData(name='Heavy Laser Rifle', techLevel=12, cost=14000, size=_MountSize.Heavy, skill='Gun Combat (Energy)', magazineCost=500, multiLink=True, damage='6D', traits='Scope, Zero-G'),
    _WeaponData(name='Ion Rifle, TL 14', techLevel=14, cost=16000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=5000, multiLink=True, damage='Special', traits='Zero-G'),
    _WeaponData(name='Ion Rifle, TL 15', techLevel=15, cost=24000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=8000, multiLink=True, damage='Special', traits='Zero-G'),
    _WeaponData(name='Laser Carbine, TL 11', techLevel=11, cost=4000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=3000, multiLink=True, damage='4D+3', traits='Zero-G'),
    _WeaponData(name='Laser Carbine, TL 9', techLevel=9, cost=2500, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=1000, multiLink=True, damage='4D', traits='Zero-G'),   
    _WeaponData(name='Laser Pistol, TL 11', techLevel=11, cost=3000, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=3000, multiLink=True, damage='3D+3', traits='Zero-G'), 
    _WeaponData(name='Laser Pistol, TL 9', techLevel=9, cost=2000, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=1000, multiLink=True, damage='3D', traits='Zero-G'),     
    _WeaponData(name='Laser Rifle, TL 11', techLevel=11, cost=8000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=3500, multiLink=True, damage='5D+3', traits='Zero-G'), 
    _WeaponData(name='Laser Rifle, TL 9', techLevel=9, cost=3500, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=1500, multiLink=True, damage='5D', traits='Zero-G'),     
    _WeaponData(name='Laser Sniper Rifle', techLevel=12, cost=9000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=250, multiLink=True, damage='5D+3', traits='Scope, Zero-G'),
    _WeaponData(name='Maser Pistol', techLevel=17, cost=25000, size=_MountSize.Small, skill='Gun Combat (Energy)', multiLink=True, damage='3D+3', traits='AP 10, Zero-G'),
    _WeaponData(name='Maser Rifle', techLevel=16, cost=30000, size=_MountSize.Heavy, skill='Gun Combat (Energy)', multiLink=True, damage='5D+3', traits='AP 10, Zero-G'),
    _WeaponData(name='Matter Disintegrator, TL 18', techLevel=18, cost=2500000, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=50000, multiLink=True, damage='1DD', traits='Zero-G'),
    _WeaponData(name='Matter Disintegrator, TL 19', techLevel=19, cost=4000000, size=_MountSize.Small, skill='Gun Combat (Energy)', multiLink=True, damage='2DD', traits='Zero-G'),
    _WeaponData(name='Pepper Spray', techLevel=5, cost=5, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=5, damage='Special', traits='Stun'),
    _WeaponData(name='Personal Defence Laser', techLevel=13, cost=6000, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=100, multiLink=True, damage='3D+3', traits='Auto 2, Zero-G'),
    _WeaponData(name='Plasma Rifle', techLevel=16, cost=100000, size=_MountSize.Medium, skill='Gun Combat (Energy)', multiLink=True, damage='6D'),
    _WeaponData(name='Solar Beam Rifle', techLevel=17, cost=200000, size=_MountSize.Medium, skill='Gun Combat (Energy)', multiLink=True, damage='1DD', traits='AP 20, Zero-G'),
    _WeaponData(name='Stagger Laser Rifle, TL 12', techLevel=12, cost=10000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=5000, multiLink=True, damage='5D', traits='Auto 2, Zero-G'),
    _WeaponData(name='Stagger Laser Rifle, TL 14', techLevel=14, cost=15000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=6000, multiLink=True, damage='5D+3', traits='Auto 3, Zero-G'),
    _WeaponData(name='Stun Blaster', techLevel=13, cost=3000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=500, multiLink=True, damage='4D', traits='Stun, Zero-G'),    
    _WeaponData(name='Stun Carbine', techLevel=12, cost=2000, size=_MountSize.Medium, skill='Gun Combat (Energy)', magazineCost=200, multiLink=True, damage='3D', traits='Stun, Zero-G'),    
    _WeaponData(name='Stunner, TL 10', techLevel=10, cost=750, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=200, multiLink=True, damage='2D+3', traits='Stun, Zero-G'),  
    _WeaponData(name='Stunner, TL 12', techLevel=12, cost=1000, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=200, multiLink=True, damage='3D', traits='Stun, Zero-G'),   
    _WeaponData(name='Stunner, TL 8', techLevel=8, cost=500, size=_MountSize.Small, skill='Gun Combat (Energy)', magazineCost=200, multiLink=True, damage='2D', traits='Stun, Zero-G'),      
    _WeaponData(name='Accelerator Rifle, TL 11', techLevel=11, cost=1500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=40, multiLink=True, damage='3D', traits='Zero-G'), 
    _WeaponData(name='Accelerator Rifle, TL 9', techLevel=9, cost=900, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=30, multiLink=True, damage='3D', traits='Zero-G'),    
    _WeaponData(name='Advanced Combat Rifle', techLevel=10, cost=1000, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=15, multiLink=True, damage='3D', traits='Auto 3, Scope'),
    _WeaponData(name='Air Rifle, TL 3', techLevel=3, cost=225, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=1, multiLink=True, damage='2D', traits='Silent'),
    _WeaponData(name='Air Rifle, TL 4', techLevel=4, cost=350, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=1, multiLink=True, damage='3D-2', traits='Silent'),
    _WeaponData(name='Antique Pistol', techLevel=2, cost=100, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=5, multiLink=True, damage='2D-3'),
    _WeaponData(name='Antique Rifle', techLevel=2, cost=150, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-3'),
    _WeaponData(name='Assault Pistol', techLevel=6, cost=250, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-3', traits='Auto 2'),
    _WeaponData(name='Assault Rifle', techLevel=7, cost=500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=15, multiLink=True, damage='3D', traits='Auto 2'),
    _WeaponData(name='Assault Shotgun', techLevel=6, cost=500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=40, multiLink=True, damage='4D', traits='Auto 2'),
    _WeaponData(name='Autopistol', techLevel=5, cost=200, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-3'),
    _WeaponData(name='Autorifle', techLevel=6, cost=750, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D', traits='Auto 2'),
    _WeaponData(name='Big Game Rifle', techLevel=5, cost=1250, size=_MountSize.Heavy, skill='Gun Combat (Slug)', magazineCost=50, multiLink=True, damage='3D+3'),
    _WeaponData(name='Body Pistol', techLevel=8, cost=500, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='2D'),
    _WeaponData(name='Cartridge Pistol', techLevel=7, cost=300, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='4D'),
    _WeaponData(name='Coach Pistol', techLevel=3, cost=200, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='4D-3', traits='Dangerous'),
    _WeaponData(name='Duck\'s Foot Pistol', techLevel=3, cost=300, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=25, multiLink=True, damage='3D-3', traits='Auto 4, Dangerous'),
    _WeaponData(name='Flechette Pistol', techLevel=9, cost=275, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-2', traits='Silent'),
    _WeaponData(name='Flechette Submachine Gun', techLevel=9, cost=500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=20, multiLink=True, damage='3D-2', traits='Auto 3, Silent'),
    _WeaponData(name='Gauss Assault Gun', techLevel=12, cost=1300, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=35, multiLink=True, damage='4D', traits='AP 5, Auto 2'),   
    _WeaponData(name='Gauss Pistol', techLevel=13, cost=500, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=20, multiLink=True, damage='3D', traits='AP 3, Auto 2'),
    _WeaponData(name='Gauss Rifle', techLevel=12, cost=1500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=80, multiLink=True, damage='4D', traits='AP 5, Auto 3, Scope'), 
    _WeaponData(name='Gauss Sniper RIfle', techLevel=12, cost=2500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=20, multiLink=True, damage='5D', traits='AP 6, Scope'),  
    _WeaponData(name='Gauss Submachine Gun', techLevel=12, cost=1000, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=60, multiLink=True, damage='3D+2', traits='AP 3, Auto 4'),
    _WeaponData(name='Heavy Advanced Combat Rifle', techLevel=10, cost=2000, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=20, multiLink=True, damage='4D', traits='Auto 2, Scope'),
    _WeaponData(name='Heavy Revolver', techLevel=5, cost=400, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=15, multiLink=True, damage='4D-3'),
    _WeaponData(name='Light Shotgun', techLevel=4, cost=150, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D'),
    _WeaponData(name='Magrail Pistol', techLevel=14, cost=750, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=60, multiLink=True, damage='3D+3', traits='Auto 4'),
    _WeaponData(name='Magrail Rifle', techLevel=14, cost=2500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=100, multiLink=True, damage='4D+3', traits='Auto 6'),
    _WeaponData(name='Revolver', techLevel=4, cost=150, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=5, multiLink=True, damage='3D-3'),
    _WeaponData(name='Rifle', techLevel=5, cost=200, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D'),
    _WeaponData(name='Sawed-Off Shotgun', techLevel=4, cost=200, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='4D'),
    _WeaponData(name='Shot Pistol', techLevel=5, cost=60, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=5, multiLink=True, damage='3D'),
    _WeaponData(name='Shotgun', techLevel=4, cost=200, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='4D'),
    _WeaponData(name='Sniper Rifle', techLevel=8, cost=700, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D', traits='AP 5, Scope, Silent'),  
    _WeaponData(name='Snub Carbine', techLevel=11, cost=500, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=30, multiLink=True, damage='3D-3', traits='Zero-G'),
    _WeaponData(name='Snub Pistol', techLevel=8, cost=150, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-3', traits='Zero-G'),
    _WeaponData(name='Spear Gun', techLevel=6, cost=50, size=_MountSize.Medium, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D', traits='Silent'),
    _WeaponData(name='Submachine Gun', techLevel=6, cost=400, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D', traits='Auto 3'),
    _WeaponData(name='Universal Autopistol', techLevel=8, cost=300, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=10, multiLink=True, damage='3D-3'),
    _WeaponData(name='Zip Gun', techLevel=3, cost=50, size=_MountSize.Small, skill='Gun Combat (Slug)', magazineCost=5, multiLink=True, damage='2D-3', traits='Dangerous'),
    _WeaponData(name='Infantry Mortar', techLevel=5, cost=3500, size=_MountSize.Heavy, skill='Heavy Weapons (Artillery)', magazineCost=50, multiLink=True, damage='5D', traits='Artillery, Blast 5'),
    _WeaponData(name='Support Mortar', techLevel=7, cost=11000, size=_MountSize.Vehicle, skill='Heavy Weapons (Artillery)', magazineCost=100, multiLink=True, damage='9D', traits='Artillery, Blast 6'),
    _WeaponData(name='Anti-Material Rifle', techLevel=7, cost=3000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=10, multiLink=True, damage='5D', traits='AP 5, Scope'),
    _WeaponData(name='ARL (PDW)', techLevel=10, cost=200, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='4D', traits='Auto 4, Zero-G'),  
    _WeaponData(name='ARL (Standard)', techLevel=10, cost=800, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='4D', traits='Zero-G'),     
    _WeaponData(name='ARL (Support)', techLevel=10, cost=1300, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=200, multiLink=True, damage='4D', traits='Auto 4, Zero-G'),
    _WeaponData(name='CPPG-11', techLevel=11, cost=8000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=300, multiLink=True, damage='6D', traits='AP 6, Blast 2, Scope'),
    _WeaponData(name='CPPG-12', techLevel=12, cost=15000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=450, multiLink=True, damage='8D', traits='AP 8, Blast 3, Scope'),
    _WeaponData(name='CPPG-13', techLevel=13, cost=25000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=600, multiLink=True, damage='1DD', traits='AP 10, Blast 3, Scope'),
    _WeaponData(name='Cryojet', techLevel=11, cost=4000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=200, multiLink=True, damage='4D', traits='Blast 5'),
    _WeaponData(name='Disposable Plasma Launcher', techLevel=12, cost=8000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', damage='2DD', traits='One Use, Smart'),
    _WeaponData(name='Early Machinegun', techLevel=4, cost=1200, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='3D', traits='Auto 3'),   
    _WeaponData(name='FGHP-14', techLevel=14, cost=100000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='2DD', traits='Radiation'),
    _WeaponData(name='FGHP-15', techLevel=15, cost=400000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='2DD', traits='Radiation'),
    _WeaponData(name='FGHP-16', techLevel=16, cost=500000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='2DD', traits='Radiation'),
    _WeaponData(name='Flamethrower, TL 4', techLevel=4, cost=800, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=60, multiLink=True, damage='3D', traits='Blast 5, Fire'),
    _WeaponData(name='Flamethrower, TL 6', techLevel=6, cost=1500, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=80, multiLink=True, damage='4D', traits='Blast 5, Fire'),
    _WeaponData(name='Flamethrower, TL 8', techLevel=8, cost=2000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='4D', traits='Blast 5, Fire'),
    _WeaponData(name='Grenade Launcher', techLevel=7, cost=400, size=_MountSize.Medium, skill='Heavy Weapons (Portable)', magazineCost=180, damage='As Grenade'),
    _WeaponData(name='Light Assault Gun', techLevel=8, cost=4000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='7D', traits='AP 5'),    
    _WeaponData(name='Light Gatling Laser', techLevel=9, cost=4500, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=300, multiLink=True, damage='3D', traits='Auto 4, Zero-G'),
    _WeaponData(name='Machinegun', techLevel=5, cost=1500, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='3D', traits='Auto 4, Zero-G'), 
    _WeaponData(name='PGHP-12', techLevel=12, cost=20000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='1DD'),
    _WeaponData(name='PGHP-13', techLevel=13, cost=65000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='1DD'),
    _WeaponData(name='PGHP-14', techLevel=14, cost=100000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='1DD'),
    _WeaponData(name='Plasma Jet, TL 12', techLevel=12, cost=16000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='1DD', traits='Blast 5'),
    _WeaponData(name='Plasma Jet, TL 14', techLevel=14, cost=80000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', multiLink=True, damage='1DD', traits='Blast 10'),
    _WeaponData(name='RAM Grenade Launcher', techLevel=8, cost=800, size=_MountSize.Medium, skill='Heavy Weapons (Portable)', magazineCost=240, damage='As Grenade', traits='Auto 3'),       
    _WeaponData(name='Rapid-Fire Machinegun', techLevel=7, cost=3000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=100, multiLink=True, damage='3D', traits='Auto 4 (8)'),
    _WeaponData(name='Rocket Launcher, TL 6', techLevel=6, cost=2000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=300, damage='4D+3', traits='Blast 6'),
    _WeaponData(name='Rocket Launcher, TL 7', techLevel=7, cost=2000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=400, damage='4D', traits='Blast 6, Smart'),      
    _WeaponData(name='Rocket Launcher, TL 8', techLevel=8, cost=2000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=600, damage='5D', traits='Blast 6, Scope, Smart'),
    _WeaponData(name='Rocket Launcher, TL 9', techLevel=9, cost=2000, size=_MountSize.Heavy, skill='Heavy Weapons (Portable)', magazineCost=800, damage='5D+3', traits='Blast 6, Scope, Smart'),
    _WeaponData(name='Heavy Machinegun', techLevel=6, cost=4500, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=400, multiLink=True, damage='5D', traits='Auto 3'),  
    _WeaponData(name='Light Anti-Air Missile', techLevel=7, cost=5000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', damage='6D', traits='One Use, Smart'),
    _WeaponData(name='Light Autocannon', techLevel=6, cost=10000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=1000, multiLink=True, damage='6D', traits='Auto 3'),_WeaponData(name='Rocket Pod', techLevel=6, cost=8000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', damage='4D', traits='Auto 3, Blast 5'),
    _WeaponData(name='Tac Launcher, Anti-Aircraft', techLevel=10, cost=16000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=8000, damage='8D', traits='Scope, Smart'),
    _WeaponData(name='Tac Launcher, Anti-Personnel', techLevel=10, cost=12000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=4000, damage='4D', traits='Blast 10, Scope, Smart'),
    _WeaponData(name='Tac Launcher, Armour Piercing', techLevel=10, cost=15000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=6000, damage='8D', traits='AP 10, Scope, Smart'),
    _WeaponData(name='VRF Gauss Gun', techLevel=12, cost=20000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=1000, multiLink=True, damage='4D', traits='AP 5, Auto 8'),
    _WeaponData(name='VRF Machinegun', techLevel=7, cost=12000, size=_MountSize.Vehicle, skill='Heavy Weapons (Vehicle)', magazineCost=1250, multiLink=True, damage='4D', traits='Auto 6'),  
    _WeaponData(name='Arc-Field Weapon', techLevel=14, cost=25000, size=_MountSize.Small, skill='Melee (Blade)', damage='5D+2', traits='AP 30'),
    _WeaponData(name='Assault Pike, TL 5', techLevel=5, cost=200, size=_MountSize.Heavy, skill='Melee (Blade)', damage='4D', traits='AP 4, One Use'),
    _WeaponData(name='Assault Pike, TL 8', techLevel=8, cost=400, size=_MountSize.Medium, skill='Melee (Blade)', damage='4D', traits='AP 4, One Use'),
    _WeaponData(name='Battle Axe', techLevel=1, cost=225, size=_MountSize.Medium, skill='Melee (Blade)', damage='3D', traits='AP 2'),
    _WeaponData(name='Blade', techLevel=1, cost=100, size=_MountSize.Small, skill='Melee (Blade)', damage='2D'),
    _WeaponData(name='Broadsword', techLevel=1, cost=500, size=_MountSize.Medium, skill='Melee (Blade)', damage='4D'),
    _WeaponData(name='Chaindrive Axe', techLevel=10, cost=600, size=_MountSize.Medium, skill='Melee (Blade)', damage='4D', traits='AP 4'),
    _WeaponData(name='Chaindrive Sword', techLevel=10, cost=500, size=_MountSize.Small, skill='Melee (Blade)', damage='4D', traits='AP 2'),
    _WeaponData(name='Cutlass', techLevel=2, cost=200, size=_MountSize.Small, skill='Melee (Blade)', damage='3D'),
    _WeaponData(name='Dagger', techLevel=1, cost=10, size=_MountSize.Small, skill='Melee (Blade)', damage='1D+2'),
    _WeaponData(name='Great Axe', techLevel=1, cost=750, size=_MountSize.Heavy, skill='Melee (Blade)', damage='4D+2', traits='Smasher'),
    _WeaponData(name='Hatchet', techLevel=1, cost=50, size=_MountSize.Small, skill='Melee (Blade)', damage='2D+2'),
    _WeaponData(name='Lance', techLevel=1, cost=250, size=_MountSize.Medium, skill='Melee (Blade)', damage='5D', traits='AP 4'),
    _WeaponData(name='Long Blade, TL 1', techLevel=1, cost=200, size=_MountSize.Small, skill='Melee (Blade)', damage='3D'),
    _WeaponData(name='Long Blade, TL 3', techLevel=3, cost=300, size=_MountSize.Small, skill='Melee (Blade)', damage='3D+2'),
    _WeaponData(name='Monoblade', techLevel=12, cost=2500, size=_MountSize.Small, skill='Melee (Blade)', damage='3D', traits='AP 10'),
    _WeaponData(name='Monofilament Axe', techLevel=12, cost=3000, size=_MountSize.Medium, skill='Melee (Blade)', damage='4D'),
    _WeaponData(name='Piston Spear', techLevel=7, cost=400, size=_MountSize.Small, skill='Melee (Blade)', damage='3D+2', traits='AP 2'),
    _WeaponData(name='Psi Blade', techLevel=16, cost=30000, size=_MountSize.Small, skill='Melee (Blade)', damage='2D', traits='Special (PSI)'),
    _WeaponData(name='Psi Dagger', techLevel=16, cost=25000, size=_MountSize.Small, skill='Melee (Blade)', damage='1D+2', traits='Special (PSI)'),
    _WeaponData(name='Rapier', techLevel=2, cost=200, size=_MountSize.Small, skill='Melee (Blade)', damage='2D'),
    _WeaponData(name='Spear', techLevel=0, cost=10, size=_MountSize.Small, skill='Melee (Blade)', damage='2D'),
    _WeaponData(name='Static Axe, TL 11', techLevel=11, cost=750, size=_MountSize.Heavy, skill='Melee (Blade)', damage='4D', traits='AP 6, Smasher'),
    _WeaponData(name='Static Axe, TL 12', techLevel=12, cost=1000, size=_MountSize.Medium, skill='Melee (Blade)', damage='4D+2', traits='AP 8, Smasher'),
    _WeaponData(name='Static Blade, TL 11', techLevel=11, cost=700, size=_MountSize.Small, skill='Melee (Blade)', damage='3D', traits='AP 5'),
    _WeaponData(name='Static Blade, TL 12', techLevel=12, cost=900, size=_MountSize.Small, skill='Melee (Blade)', damage='3D+2', traits='AP 6, Smasher'),
    _WeaponData(name='Stealth Dagger', techLevel=8, cost=175, size=_MountSize.Small, skill='Melee (Blade)', damage='1D+2'),
    _WeaponData(name='Stone Axe', techLevel=0, cost=5, size=_MountSize.Small, skill='Melee (Blade)', damage='2D+1'),
    _WeaponData(name='War Pick', techLevel=1, cost=275, size=_MountSize.Small, skill='Melee (Blade)', damage='2D+2', traits='AP 4'),
    _WeaponData(name='Anti-Armour Flail', techLevel=8, cost=250, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='4D', traits='AP 5, One Use'),
    _WeaponData(name='Boarding Shield', techLevel=9, cost=1500, size=_MountSize.Medium, skill='Melee (Bludgeon)', damage='1D', traits='Bulky'),
    _WeaponData(name='Buckler', techLevel=1, cost=10, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D'),
    _WeaponData(name='Club', techLevel=0, cost=0, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='2D'),
    _WeaponData(name='Expandable Shield', techLevel=12, cost=2500, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D'),
    _WeaponData(name='Gravitic Shield', techLevel=17, cost=2500, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D'),
    _WeaponData(name='Gravity Hammer', techLevel=13, cost=10000, size=_MountSize.Medium, skill='Melee (Bludgeon)', damage='5D', traits='AP 50, Smasher'),
    _WeaponData(name='Large Shield', techLevel=1, cost=200, size=_MountSize.Medium, skill='Melee (Bludgeon)', damage='0D'),
    _WeaponData(name='Mace', techLevel=1, cost=20, size=_MountSize.Medium, skill='Melee (Bludgeon)', damage='2D+2', traits='Smasher'),
    _WeaponData(name='Riot Shield', techLevel=6, cost=175, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D'),
    _WeaponData(name='Sap', techLevel=1, cost=30, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D', traits='Stun'),
    _WeaponData(name='Shield', techLevel=0, cost=150, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='1D'),
    _WeaponData(name='Sledgehammer', techLevel=1, cost=30, size=_MountSize.Heavy, skill='Melee (Bludgeon)', damage='4D', traits='Smasher'),
    _WeaponData(name='Staff', techLevel=1, cost=5, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='2D'),
    _WeaponData(name='Static Maul', techLevel=11, cost=650, size=_MountSize.Medium, skill='Melee (Bludgeon)', damage='3D', traits='AP 4, Smasher'),
    _WeaponData(name='Stunstick', techLevel=8, cost=300, size=_MountSize.Small, skill='Melee (Bludgeon)', damage='2D', traits='Stun'),
    _WeaponData(name='Brass Knuckles', techLevel=1, cost=10, size=_MountSize.Small, skill='Melee (Unarmed)', damage='1D+2'),
    _WeaponData(name='Claw, Arc-Field', techLevel=14, cost=25000, size=_MountSize.Small, skill='Melee (Unarmed)', damage='4D', traits='AP 30'),
    _WeaponData(name='Claw, Edging', techLevel=11, cost=3000, size=_MountSize.Small, skill='Melee (Unarmed)', damage='2D+2', traits='AP 4'),
    _WeaponData(name='Claw, Hardened', techLevel=10, cost=1000, size=_MountSize.Small, skill='Melee (Unarmed)', damage='1D+2', traits='AP 2'),
    _WeaponData(name='Claw, Monofilament', techLevel=12, cost=5000, size=_MountSize.Small, skill='Melee (Unarmed)', damage='3D', traits='AP 10'),
    _WeaponData(name='Garotte', techLevel=0, cost=10, size=_MountSize.Small, skill='Melee (Unarmed)', damage='2D'),
    _WeaponData(name='Handspikes', techLevel=2, cost=100, size=_MountSize.Small, skill='Melee (Unarmed)', damage='2D'),
    _WeaponData(name='Knuckleblasters', techLevel=8, cost=150, size=_MountSize.Small, skill='Melee (Unarmed)', damage='5D'),
    _WeaponData(name='Monofilament Garotte', techLevel=12, cost=1000, size=_MountSize.Small, skill='Melee (Unarmed)', damage='3D', traits='AP 10, Dangerous'),
    _WeaponData(name='Piston Fist', techLevel=9, cost=150, size=_MountSize.Small, skill='Melee (Unarmed)', damage='3D+2'),
    _WeaponData(name='Stunfist', techLevel=8, cost=250, size=_MountSize.Small, skill='Melee (Unarmed)', damage='1D+2', traits='Stun'),
    _WeaponData(name='Shock Whip', techLevel=9, cost=450, size=_MountSize.Small, skill='Melee (Whip)', damage='2D', traits='Stun'),
    _WeaponData(name='Whip', techLevel=1, cost=15, size=_MountSize.Small, skill='Melee (Whip)', damage='D3')
]

_WeaponDataMap = {weapon.name(): weapon for weapon in _WeaponDataList}

class WeaponMount(robots.WeaponMountInterface):
    """
    - Option: Mount Size
        - Small
            - Slots: 1
            - Cost: 500
            - Note: A small weapon mount may hold any melee weapon useable with
            one hand, any pistol or equivalent single-handed ranged weapon, or
            an explosive charge or grenade of less than three kilograms
        - Medium
            - Slots: 2
            - Cost: 1000
            - Note: A medium weapon mount may hold any larger weapon usable by
            Melee or Gun Combat skills or an explosive of up to six kilograms
        - Heavy
            - Slots: 10
            - Cost: 5000       
            - Note: A heavy mount may hold any weapon usable with Heavy
            Weapons (portable)
        - Vehicle
            - Slots: 15
            - Cost: 10000        
            - Note: A vehicle mount may hold any weapon of mass 250 kilograms or
            less that requires Heavy Weapons (vehicle).
    - Option: Weapon
        - Requirement: Ability to select a weapon from a predefined list
    - Option: Autoloader
        - Min TL: 6
        - Cost: Weapon magazine cost * Number of Magazines * 2
        - Slots: Doubles the slots used by the weapon/mount
        - Option: Number of magazines the Autoloader holds    
    - Option: Multi-link
        - Option: Number of multi-linked mounts, up to a max of 4
        - Note: Up to 4 weapons OF THE SAME TYPE can be linked to fire as a
        single attack. If the attack succeeds, only one damage roll is made and
        +1 is added for each additional weapon
    - Option: Fire Control System
        - <All>
            - Slots: 1
            - Trait: Scope
        - Basic
            - Min TL: 6
            - Cost: 10000
            - Weapon Skill DM: +1
        - Improved
            - Min TL: 8
            - Cost: 25000
            - Weapon Skill DM: +2       
        - Enhanced
            - Min TL: 10
            - Cost: 50000
            - Weapon Skill DM: +3  
        - Advanced
            - Min TL: 12
            - Cost: 100000
            - Weapon Skill DM: +4   
    """
    # NOTE: The rule seem to describe 3 different types of weapon mount, torso,
    # servo and manipulator.
    #
    # Manipulator mounts seem the easiest to understand but most complicated to
    # implement. The user specifies which manipulator the weapon is mounted on.
    # The chosen manipulator determines how big a mount (and therefore weapon)
    # can be installed and the DEX level used when calculating the attack
    # modifier. The slot usage and cost for the mount come from the table on
    # p61. The table also specifies the minimum manipulator size required for
    #that size mount.
    #
    # Servo mounts are a bit confusing. The slots and cost for the mount come
    # from the table on p61 but the minimum manipulator size doesn't apply. The
    # only limit on how big a mount (and therefore weapon) you can install is
    # the available slots. What's not clear (if any) DEX level is used when
    # calculating the attack modifier. It's also a little odd that there is no
    # min TL for a servo mount.
    # When it comes to the DEX level it's not clear. There are combat drones on
    # p132 that don't have manipulators and don't have a DEX skill. In relation
    # to robots as characters it says the robots DEX is that of the manipulator
    # with the highest DEX score, but it's not obvious that this would apply to
    # robots in general.
    #
    # Torso mounts are the most confusing. The rules specifically say "A weapon
    # mounted in the robot’s torso may use any available Slots.". The fact that is
    # specifically calls this out would suggest the slot usage is in some way
    # different to manipulator and servo mounts, however it's now obvious how it's
    # meant to be different.
    # It could be that it's related to the text on p14 where it talks about slots
    # holding ~3kg and gives an example of a battle axe probably taking 2 slots,
    # this would make sense as the Central Supply Catalogue has the weight of a
    # battle axe at 4kg (p101). It could be that you're meant to use the weight
    # of the weapon (e.g. from the Central Supply Catalogue) and use that to
    # calculate how many slots the torso mounted weapon would take. If this is
    # the interpretation then it's not obvious what the cost of the torso mount
    # would be, it wouldn't really make sense for it to come from the table on
    # p61 if the slots requirement didn't come from the same table. This
    # interpretation also doesn't really make logical sense. The weapon weights
    # in the rules include things like stocks which wouldn't be needed if the
    # weapon was mounted into the torso of the robot.
    # The other option is i'm reading to much into somewhat cosmetic fluff
    # wording and there is no effective difference in the slot requirement for
    # different types of mounting. It would be determined by the size of the
    # mount that was installed and that size would determine which weapons can
    # be installed based on the description on p61. With this interpretation
    # the the cost of the torso mount would logically also come from the table
    # on p61.
    # My current best guess is it's the later option and I'm reading to much into
    # it. If it was the other interpretation you would think they would make it
    # a little clearer rather than expecting you to join the dots between this
    # wording and some paragraph 50 pages back.
    # As with the servo mount it's not also not clear what DEX level is used for
    # calculating the attack modifier for a torso mount.
    # NOTE: The rules around how the Fire Control System affects attack rolls is
    # a little convoluted. I __think__ it works like this
    #
    # For Internal/Servo mounts the Weapon Skill DM for the Fire Control
    # System is used instead of the robots Weapon Skill. This is based on
    # "For finalisation purposes, Weapon Skill DM is treated as the weapon skill
    # of the robot with the integrated weapon".
    #
    # For Manipulator mounts (or weapons held by the robot) which ever is higher
    # of the manipulators DEX modifier _OR_ the mounts Weapon Skill DM is added
    # to the robots weapon skill.
    # Update: I've got confirmation from the guy who wrote the book (Geir) that
    # his intention was that robots only get a DEX modifier for weapons held in or
    # mounted to a manipulator.
    # https://forum.mongoosepublishing.com/threads/robot-tl-8-sentry-gun.124598/#post-973844

    # Data Structure: Cost, Slots
    _MountSizeData = {
        _MountSize.Small: (500, 1),
        _MountSize.Medium: (1000, 2),
        _MountSize.Heavy: (5000, 10),
        _MountSize.Vehicle: (10000, 15)
    }

    _AutoloaderMinTL = common.ScalarCalculation(
        value=6,
        name='Autoloader Min TL')
    _AutoloaderMagazineCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Autoloader Magazine Cost Multiplier')
    _AutoloaderMinManipulatorSizeModifier = common.ScalarCalculation(
        value=1,
        name='Autoloader Minimum Manipulator Size Modifier')
    
    _MultiLinkAttackNote = 'Only a single attack is made when the {count} linked mounts are fired together. If a hit occurs a single damage roll is made and +{modifier} is added to the result.'

    # Data Structure: Min TL, Cost, Weapon Skill DM
    _FireControlData = {
        _FireControlLevel.Basic: (6, 10000, +1),
        _FireControlLevel.Improved: (8, 25000, +2),
        _FireControlLevel.Enhanced: (10, 50000, +3),
        _FireControlLevel.Advanced: (12, 100000, +4),
    }
    _FireControlSlots = common.ScalarCalculation(
        value=1,
        name='Fore Control System Required Slots')
    _FireControlScopeNote = 'The Fire Control System gives the Scope trait'

    def __init__(
            self,
            componentString: str,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__()

        self._mountSizeOption = construction.EnumOption(
            id='MountSize',
            name='Mount Size',
            type=_MountSize,
            description='Specify the size of the mount, this determines what size of weapons can be mounted on it.')
        
        self._weaponOption = construction.StringOption(
            id='Weapon',
            name='Weapon',
            value=None,
            options=list(_WeaponDataMap.keys()),
            isEditable=False,
            isOptional=True,
            description='Specify the weapon that is mounted.')

        self._autoLoaderOption = construction.IntegerOption(
            id='Autoloader',
            name='Autoloader Magazines',
            value=None,
            minValue=1,
            maxValue=10,
            isOptional=True,
            description='Specify if the mount is equipped with an Autoloader and, if so, how many magazines it contains.')
        
        self._multiLinkOption = construction.IntegerOption(
            id='MultiLink',
            name='Multi-Link',
            value=None,
            minValue=2,
            maxValue=4,
            isOptional=True,
            description='Specify if this is a set of linked weapons that target and fire as a single action.')
        
        self._fireControlOption = construction.EnumOption(
            id='FireControl',
            name='Fire Control',
            type=_FireControlLevel,
            isOptional=True,
            description='Specify if the mount or multi-linked group of mounts is controlled by a Fire Control System.')
        
        self._componentString = componentString
        self._notes = notes
        
    def instanceString(self) -> str:
        mountSize: _MountSize = self._mountSizeOption.value()
        return f'{self.componentString()} ({mountSize.value})'

    def componentString(self) -> str:
        return self._componentString
    
    def typeString(self) -> str:
        return 'Weapon Mount'

    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        options.append(self._mountSizeOption)
        options.append(self._weaponOption)
        if self._autoLoaderOption.isEnabled():
            options.append(self._autoLoaderOption)
        if self._multiLinkOption.isEnabled():
            options.append(self._multiLinkOption)
        if self._fireControlOption.isEnabled():
            options.append(self._fireControlOption)
        return options
        
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._mountSizeOption.setOptions(
            options=self._allowedMountSizes(sequence=sequence, context=context))
        
        self._weaponOption.setOptions(
            options=self._allowedWeapons(sequence=sequence, context=context))
        
        supportsAutoloader = False
        if context.techLevel() >= WeaponMount._AutoloaderMinTL.value():
            weaponData = self._weaponData()
            supportsAutoloader = weaponData and weaponData.magazineCost()
        self._autoLoaderOption.setEnabled(enabled=supportsAutoloader)

        self._multiLinkOption.setEnabled(enabled=True)
        
        fireControlOptions = self._allowedFireControls(
            sequence=sequence,
            context=context)
        self._fireControlOption.setOptions(options=fireControlOptions)
        self._fireControlOption.setEnabled(len(fireControlOptions))

    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        step = self._createBasicMountStep(sequence=sequence, context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)
        step = self._createWeaponStep(sequence=sequence, context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)
        step = self._createAutoloaderStep(sequence=sequence, context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)
        step = self._createFireControlStep(sequence=sequence, context=context)
        if step:
            context.applyStep(
                sequence=sequence,
                step=step)            

    def _createBasicMountStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        linkedMountCount = self._linkedMountCount()

        stepName = self.instanceString()
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())

        mountSize = self._mountSizeOption.value()
        assert(isinstance(mountSize, _MountSize))
        mountCost, mountSlots = WeaponMount._MountSizeData[mountSize]
        
        mountCost = common.ScalarCalculation(
            value=mountCost,
            name=f'{mountSize.value} Mount Cost')
        mountSlots = common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots')        
        
        if linkedMountCount:
            mountCost = common.Calculator.multiply(
                lhs=mountCost,
                rhs=linkedMountCount,
                name=f'Multi-Link {mountCost.name()}')
            mountSlots = common.Calculator.multiply(
                lhs=mountSlots,
                rhs=linkedMountCount,
                name=f'Multi-Link {mountSlots.name()}')

        step.setCredits(credits=construction.ConstantModifier(value=mountCost))
        step.setSlots(slots=construction.ConstantModifier(value=mountSlots))

        if self._notes:
            for note in self._notes:
                step.addNote(note=note)

        if linkedMountCount:
            step.addNote(note=WeaponMount._MultiLinkAttackNote.format(
                count=linkedMountCount.value(),
                modifier=linkedMountCount.value() - 1))
            
        return step
        
    def _createWeaponStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        weaponData = self._weaponData()
        if not weaponData:
            return None
        linkedMountCount = self._linkedMountCount()

        stepName = weaponData.name()
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        
        weaponCost = common.ScalarCalculation(
            value=weaponData.cost(),
            name=f'{weaponData.name()} Cost')
        if linkedMountCount:
            weaponCost = common.Calculator.multiply(
                lhs=weaponCost,
                rhs=linkedMountCount,
                name=f'Multi-Link {weaponCost.name()}')            
        step.setCredits(credits=construction.ConstantModifier(value=weaponCost))
        
        # TODO: I'm not sure if the skill name is the thing to put in the note in
        # all cases. If the weapon has fire control then the Weapon Skill DM for
        # the fire control system is used instead of the robots weapon skill (p60)
        skill = weaponData.skill()
        damage = weaponData.damage()
        traits = weaponData.traits()
        note = f'The weapon uses the {skill} skill'
        if damage and traits:
            note += f', does a base {damage} damage and has the {traits} trait(s)'
        elif damage:
            note += f' and does {damage} damage'
        elif traits:
            note += f' and has the {traits} traits'
        note += '.'
        step.addNote(note)

        if weaponData.magazineCost():
            step.addNote(f'A magazine for the weapon costs Cr{weaponData.magazineCost()}')

        return step
            
    def _createAutoloaderStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        autoloaderMagazineCount = self._autoloaderMagazineCount()
        if not autoloaderMagazineCount:
            return None
        
        weaponData = self._weaponData()
        linkedMountCount = self._linkedMountCount()

        stepName = f'Autoloader ({autoloaderMagazineCount.value()})'
        if linkedMountCount:
            stepName += f' x{linkedMountCount.value()}'            
        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        
        # The autoloader uses the same number of slots as the mount.
        mountSize = self._mountSizeOption.value()
        assert(isinstance(mountSize, _MountSize))
        _, mountSlots = WeaponMount._MountSizeData[mountSize]

        mountSlots = common.ScalarCalculation(
            value=mountSlots,
            name=f'{mountSize.value} Mount Required Slots')
        autoloaderSlots = common.Calculator.equals(
            value=mountSlots,
            name='Autoloader Required Slots')
        if linkedMountCount:
            autoloaderSlots = common.Calculator.multiply(
                lhs=autoloaderSlots,
                rhs=linkedMountCount,
                name=f'Multi-Link {autoloaderSlots.name()}')
        step.setSlots(slots=construction.ConstantModifier(value=autoloaderSlots))

        magazineCost = weaponData.magazineCost() if weaponData else None
        if magazineCost:
            magazineCost = common.ScalarCalculation(
                value=magazineCost,
                name=f'{weaponData.name()} Magazine Cost')
                                            
            autoloaderCost = common.Calculator.multiply(
                lhs=common.Calculator.multiply(
                    lhs=magazineCost,
                    rhs=autoloaderMagazineCount),
                rhs=WeaponMount._AutoloaderMagazineCostMultiplier,
                name='Autoloader Cost')
            if linkedMountCount:
                autoloaderCost = common.Calculator.multiply(
                    lhs=autoloaderCost,
                    rhs=linkedMountCount,
                    name=f'Multi-Link {autoloaderCost.name()}')                

            step.setCredits(credits=construction.ConstantModifier(
                value=autoloaderCost))
        
        return step

    def _createFireControlStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        fireControlLevel = self._fireControlLevel()
        if not fireControlLevel:
            return None

        step = robots.RobotStep(
            name=f'Fire Control System ({fireControlLevel.value})',
            type=self.typeString())
        
        _, fireControlCost, _ = WeaponMount._FireControlData[fireControlLevel]
        
        fireControlCost = common.ScalarCalculation(
            value=fireControlCost,
            name=f'{fireControlLevel.value} Fire Control System Cost')
        step.setCredits(credits=construction.ConstantModifier(
            value=fireControlCost))
        
        step.setSlots(slots=construction.ConstantModifier(
            value=WeaponMount._FireControlSlots))
        
        step.addNote(note=WeaponMount._FireControlScopeNote)
        
        return step

    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[_MountSize]:
        return _MountSize # All sizes are allowed by default
    
    def _allowedWeapons(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[str]:
        robotTL = context.techLevel()
        mountSize = self._mountSizeOption.value()
        allowed = []
        for weapon in _WeaponDataList:
            if weapon.size() == mountSize and weapon.techLevel() <= robotTL:
                allowed.append(weapon.name())
        return allowed
    
    def _allowedFireControls(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[_FireControlLevel]:
        robotTL = context.techLevel()
        allowed = []
        for level in _FireControlLevel:
            minTL, _, _ = WeaponMount._FireControlData[level]
            if minTL <= robotTL:
                allowed.append(level)
        return allowed
    
    def _weaponData(self) -> typing.Optional[_WeaponData]:
        weaponName = self._weaponOption.value()
        if not weaponName:
            return None
        return _WeaponDataMap.get(weaponName)
    
    def _autoloaderMagazineCount(self) -> typing.Optional[common.ScalarCalculation]:
        magazineCount = self._autoLoaderOption.value() if self._autoLoaderOption.isEnabled() else None
        if not magazineCount:
            return None
        return common.ScalarCalculation(
            value=magazineCount,
            name='Specified Autoloader Magazine Count') 
    
    def _linkedMountCount(self) -> typing.Optional[common.ScalarCalculation]:
        multiLinkCount = self._multiLinkOption.value() if self._multiLinkOption.isEnabled() else None
        if not multiLinkCount:
            return None
        return common.ScalarCalculation(
            value=multiLinkCount,
            name='Specified Multi-Link Mount Count')
    
    def _fireControlLevel(self) -> typing.Optional[_FireControlLevel]:
        return self._fireControlOption.value() if self._fireControlOption.isEnabled() else None        
    
class InternalMount(WeaponMount):
    """
    - Note: Attacks made with weapons mounted internally do not get a DEX modifier
    unless the weapon is mounted in a manipulator
    - Option: Fire Control System
        - <All>
            - Note: The Fire Control Systems Weapon Skill DM is used instead of
            the robots weapon skill when making attack rolls
    """
    # TODO: Handle some kind of note to cover how attack modifiers are
    # calculated for manipulator mounted weapons.
    
    def __init__(self) -> None:
        super().__init__(
            componentString='Internal Mount',
            notes=['Attacks made with weapons mounted internally don\'t get a DEX modifier'])
        
class ServoMount(WeaponMount):
    """
    - Note: Attacks made with weapons mounted internally do not get a DEX modifier
    unless the weapon is mounted in a manipulator    
    - Option: Fire Control System
        - <All>
            - Note: The Fire Control Systems Weapon Skill DM is used instead of
            the robots weapon skill when making attack rolls
    """
    # TODO: Handle some kind of note to cover how attack modifiers are
    # calculated for manipulator mounted weapons.
    
    def __init__(self) -> None:
        super().__init__(
            componentString='Servo Mount',
            notes=['Attacks made with weapons mounted on a servo don\'t get a DEX modifier'])

class ManipulatorMount(WeaponMount):
    """
    - Requirement: Only compatible with robots that have manipulators
    - Option: Manipulator
        - Requirement: The ability to select which manipulator the weapon is
        mounted to    
    - Option: Mount Size
        - Small
            - Requirement: Only compatible with manipulators of size >= 3
        - Medium
            - Requirement: Only compatible with manipulators of size >= 5
        - Heavy
            - Requirement: Only compatible with manipulators of size >= 7
        - Vehicle
            - Requirement: Not compatible with manipulator mounts
    - Option: Autoloader
        - Requirement: The minimum manipulator size is increased by 1 
    - Option: Multi-Link
        - Requirement: The number of manipulators that can be multi-linked
        should be limited to the number of manipulators that are a large
        enough size for the selected mount size and the have DEX and STR
        of at least the same level.
    - Option: Fire Control System
        - <All>
            - Note: If the Weapon Skill DM for the Fire Control System is
            higher than the DEX for the manipulator, it can be added to the
            robots weapon skill instead of the DEX.
    - Note: When calculating the robots Attack Modifier the DEX of the
    manipulator it's attached to is used.
        - Remember the final modifier should be calculated using the new
        characteristicDM function    
    """
    # NOTE: I'm working on the assumption that the fact there is no min
    # manipulator size for Vehicle sized weapons is because the can't
    # be mounted on manipulators
    # NOTE: There are two main ways the increase in Min Manipulator Size an
    # Autoloader adds. Either you need to specify if it has an autoloader
    # before selecting the manipulator so that the list of manipulators can
    # be filtered _or_ you need to choose the manipulator first then disable
    # the ability to add an autoloader if the selected manipulator wouldn't
    # allow it. I've gone with the later as I think it's easier to understand
    # when you select the manipulator first.
    # NOTE: As far as I can see the rules don't give any guidance as to what
    # manipulators can be linked together. I've gone with the principle that
    # they all need to have a size large enough to allow the selected mount size
    # and DEX and STR values that are at least as high as the selected
    # manipulator. The reason for the DEX/STR requirement is those
    # characteristics affect the single attack and damage rolls made when linked
    # weapons are fired. Although the rules don't explicitly state it, it would
    # seem logical that the manipulators being linked would need to be capable
    # of the same level of attack/damage. The implication being manipulators
    # with a higher DEX and/or STR could be linked but their attack/damage
    # levels would be limited to the selected manipulator.
    # TODO: Handle some kind of note to cover how attack modifiers are
    # calculated for manipulator mounted weapons.

    _ManipulatorSizeData = {
        _MountSize.Small: 3,
        _MountSize.Medium: 5,
        _MountSize.Heavy: 7,
        _MountSize.Vehicle: None # Not compatible
    }
    _MinManipulatorSize = common.ScalarCalculation(
        value=3, # Size required for small mount
        name='Manipulator Mount Min Manipulator Size')

    def __init__(
            self,
            componentString: str
            ) -> None:
        super().__init__(componentString=componentString)

        self._manipulatorOption = construction.StringOption(
            id='Manipulator',
            name='Manipulator',
            isEditable=False,
            options=[''], # This will be replaced by updateOptions
            description='Specify which manipulator the weapon is mounted on')
        
    def isCompatible(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> bool:
        if not super().isCompatible(sequence=sequence, context=context):
            return False
        
        manipulators = self._usableManipulators(
            sequence=sequence, 
            context=context)
        return len(manipulators) > 0
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.insert(0, self._manipulatorOption)
        return options
    
    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        manipulators = self._usableManipulators(sequence=sequence, context=context)
        self._manipulatorOption.setOptions(
            options=list(manipulators.keys()))

        super().updateOptions(sequence=sequence, context=context)

        # Disable the option to enable autoloader if the selected manipulator
        # doesn't allow for the size
        if self._autoLoaderOption.isEnabled():
            manipulator = self._selectedManipulator(
                sequence=sequence,
                context=context)
            supportsAutoloader = False
            if manipulator:
                mountSize = self._mountSizeOption.value()
                minSize = AttachedManipulatorMount._ManipulatorSizeData[mountSize] + \
                    AttachedManipulatorMount._AutoloaderMinManipulatorSizeModifier.value()
                supportsAutoloader = manipulator.size() >= minSize
            self._autoLoaderOption.setEnabled(supportsAutoloader)

        if self._multiLinkOption.isEnabled():
            manipulators = self._linkableManipulators(
                sequence=sequence,
                context=context)
            linkableCount = min(len(manipulators) + 1, 4)
            if linkableCount > 1:
                self._multiLinkOption.setMax(value=linkableCount)
            else:
                self._multiLinkOption.setEnabled(enabled=False)
    
    # NOTE: The names generated for this manipulator MUST remain consistent
    # between versions otherwise it will break weapons saved with previous
    # versions. For this reason it shouldn't use things like the components
    # instance string.
    def _usableManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.ManipulatorInterface]:
        mapping = {}

        manipulators = context.findComponents(
            componentType=robots.BaseManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.BaseManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Base Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator

        manipulators = context.findComponents(
            componentType=robots.AdditionalManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.AdditionalManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Additional Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator

        manipulators = context.findComponents(
            componentType=robots.LegManipulator,
            sequence=sequence)
        for index, manipulator in enumerate(manipulators):
            assert(isinstance(manipulator, robots.LegManipulator))
            if manipulator.size() < self._MinManipulatorSize.value():
                continue

            name = 'Leg Manipulator #{index} - Size: {size}, STR: {str}, DEX: {dex}'.format(
                index=index + 1,
                size=manipulator.size(),
                dex=manipulator.dexterity(),
                str=manipulator.strength())
            mapping[name] = manipulator                   

        return mapping
    
    def _linkableManipulators(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Mapping[str, robots.ManipulatorInterface]:
        manipulators = self._usableManipulators(
            sequence=sequence,
            context=context)
        manipulator = manipulators.get(self._manipulatorOption.value())

        mountSize = self._mountSizeOption.value()
        minSize = AttachedManipulatorMount._ManipulatorSizeData[mountSize]
        if self._autoloaderMagazineCount():
            minSize += AttachedManipulatorMount._AutoloaderMinManipulatorSizeModifier.value()

        filtered = {}
        if manipulator:
            for name, other in manipulators.items():
                if other == manipulator:
                    continue
                if other.size() >= minSize and \
                    other.dexterity() >= manipulator.dexterity() and \
                    other.strength() >= manipulator.strength():
                    filtered[name] = other
        return filtered
    
    def _selectedManipulator(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.ManipulatorInterface]:
        manipulators = self._usableManipulators(
            sequence=sequence,
            context=context)
        return manipulators.get(self._manipulatorOption.value())
    
    def _allowedMountSizes(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Iterable[_MountSize]:
        allowed = super()._allowedMountSizes(
            sequence=sequence,
            context=context)

        autoLoaderCount = self._autoloaderMagazineCount()
        manipulator = self._selectedManipulator(
            sequence=sequence,
            context=context)
        filtered = []
        for mountSize in allowed:
            minSize = AttachedManipulatorMount._ManipulatorSizeData[mountSize]
            if not minSize:
                continue # Not compatible with manipulators
            if autoLoaderCount:
                minSize += AttachedManipulatorMount._AutoloaderMinManipulatorSizeModifier.value()
            if manipulator.size() >= minSize:
                filtered.append(mountSize)
        return filtered
    
# NOTE: It's intentional that the component name doesn't mention that this is
# 'Attached'. The attached part is implied and is only needed to differentiate
# from the base class
class AttachedManipulatorMount(ManipulatorMount):
    def __init__(self) -> None:
        super().__init__(componentString='Manipulator Mount')

# NOTE: This class is a bit of a hack to allow for Fire Control Systems to be
# added for hand held weapons
class HandHeldManipulatorMount(ManipulatorMount):
    """
    - Option: Autoloader
        - Requirement: Not compatible with hand held weapons
    """
    # NOTE: The fact that Autoloaders aren't compatible with hand held weapons
    # is a bit leap of logic on my part. It seems reasonably logical autoloading
    # needs the weapon to be connected to the robot in some way so ammo can be
    # transferred. This wouldn't really make sense for a weapon the robot can
    # pick up and put down freely. If the robots manipulator was sufficiently
    # human like it could even use unmodified human weapons.

    def __init__(self) -> None:
        super().__init__(componentString='Hand Held')

    def updateOptions(self, sequence: str, context: robots.RobotContext) -> None:
        super().updateOptions(sequence, context)

        self._autoLoaderOption.setEnabled(enabled=False)

    def _createBasicMountStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        baseStep = super()._createBasicMountStep(
            sequence=sequence,
            context=context)
        
        # Hand held weapons don't use a mount so there is not cost or slot
        # requirement so copy the base step without those values.
        return robots.RobotStep(
            name=baseStep.name(),
            type=baseStep.type(),
            factors=baseStep.factors(),
            notes=baseStep.notes())
    
