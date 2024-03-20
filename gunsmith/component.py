import construction

class WeaponComponentInterface(construction.ComponentInterface):
    pass

class ReceiverInterface(WeaponComponentInterface):
    pass

class CalibreInterface(WeaponComponentInterface):
    def isRocket(self) -> bool:
        raise RuntimeError('The isRocket method must be implemented by classes derived from CalibreInterface')

    def isHighVelocity(self) -> bool:
        raise RuntimeError('The isHighVelocity method must be implemented by classes derived from CalibreInterface')

class PropellantTypeInterface(WeaponComponentInterface):
    pass

class FeedInterface(WeaponComponentInterface):
    pass

class MultiBarrelInterface(WeaponComponentInterface):
    pass

class MechanismInterface(WeaponComponentInterface):
    pass

class ReceiverFeatureInterface(WeaponComponentInterface):
    pass

class CapacityModificationInterface(WeaponComponentInterface):
    pass

class FireRateInterface(WeaponComponentInterface):
    pass

class BarrelInterface(WeaponComponentInterface):
    pass

class MultiMountInterface(WeaponComponentInterface):
    def weaponCount(self) -> int:
        raise RuntimeError('The weaponCount method must be implemented by classes derived from MultiMountInterface')

class StockInterface(WeaponComponentInterface):
    pass

class WeaponFeatureInterface(WeaponComponentInterface):
    pass

class SecondaryMountInterface(WeaponComponentInterface):
    pass

class AccessoryInterface(WeaponComponentInterface):
    def isDetachable(self) -> bool:
        raise RuntimeError('The isDetachable method must be implemented by classes derived from AccessoryInterface')

    def isAttached(self) -> bool:
        raise RuntimeError('The isAttached method must be implemented by classes derived from AccessoryInterface')

    def setAttached(self, attached: bool) -> None:
        raise RuntimeError('The setAttached method must be implemented by classes derived from AccessoryInterface')

class BarrelAccessoryInterface(AccessoryInterface):
    pass

class WeaponAccessoryInterface(AccessoryInterface):
    pass

class LoaderQuantityInterface(WeaponComponentInterface):
    pass

class MagazineLoadedInterface(WeaponComponentInterface):
    pass

class MagazineQuantityInterface(WeaponComponentInterface):
    def createLoadedMagazine(self) -> MagazineLoadedInterface:
        raise RuntimeError('The createLoadedMagazine method must be implemented by classes derived from MagazineQuantityInterface')

class AmmoLoadedInterface(WeaponComponentInterface):
    pass

class MultiMountLoadedInterface(WeaponComponentInterface):
    pass

class AmmoQuantityInterface(WeaponComponentInterface):
    def createLoadedAmmo(self) -> AmmoLoadedInterface:
        raise RuntimeError('The createLoadedAmmo method must be implemented by classes derived from AmmoQuantityInterface')

class InternalPowerPackLoadedInterface(AmmoLoadedInterface):
    pass

class ExternalPowerPackLoadedInterface(AmmoLoadedInterface):
    pass

class ProjectorPropellantQuantityInterface(WeaponComponentInterface):
    pass

class HandGrenadeQuantityInterface(WeaponComponentInterface):
    pass
