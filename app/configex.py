import app
import common
import darkdetect
import enum
import logging
import logic
import os
import re
import urllib
import threading
import traveller
import travellermap
import typing
from PyQt5 import QtCore

class ConfigOption(enum.Enum):
    # Debug
    LogLevel = 100

    # Map
    Milieu = 200
    MapStyle = 201
    MapEngine = 202
    MapRenderingType = 203
    MapAnimations = 204

    # Map Options
    GalacticDirectionsMapOption = 300
    SectorGridMapOption = 301
    SelectedSectorNamesMapOption = 302
    AllSectorNamesMapOption = 303
    BordersMapOption = 304
    RoutesMapOption = 305
    RegionNamesMapOption = 306
    ImportantWorldsMapOption = 307
    WorldColoursMapOption = 308
    FilledBordersMapOption = 309
    DimUnofficialMapOption = 310
    ImportanceOverlayMapOption = 311
    PopulationOverlayMapOption = 312
    CapitalsOverlayMapOption = 313
    MinorRaceOverlayMapOption = 314
    DroyneWorldOverlayMapOption = 315
    AncientSitesOverlayMapOption = 316
    StellarOverlayMapOption = 317
    EmpressWaveOverlayMapOption = 318
    QrekrshaZoneOverlayMapOption = 319
    AntaresSupernovaOverlayMapOption = 320
    MainsOverlayMapOption = 321

    # Proxy
    ProxyPort = 400
    ProxyHostPoolSize = 401
    ProxyMapUrl = 402
    ProxyTileCacheSize = 403
    ProxyTileCacheLifetime = 404
    ProxySvgComposition = 405

    # Game
    Rules = 500
    PlayerBrokerDM = 501
    ShipTonnage = 502
    ShipJumpRating = 503
    ShipCargoCapacity = 504
    ShipFuelCapacity = 505
    ShipCurrentFuel = 506
    UseShipFuelPerParsec = 507
    ShipFuelPerParsec = 508
    PerJumpOverhead = 509
    AvailableFunds = 510
    MinSellerDM = 511
    MaxSellerDM = 512
    MinBuyerDM = 513
    MaxBuyerDM = 514
    UsePurchaseBroker = 515
    PurchaseBrokerDmBonus = 516
    UseSaleBroker = 517
    SaleBrokerDmBonus = 518
    RoutingType = 519
    RouteOptimisation = 520
    RefuellingStrategy = 521
    UseFuelCaches = 522
    UseAnomalyRefuelling = 523
    AnomalyFuelCost = 524
    UseAnomalyBerthing = 525
    AnomalyBerthingCost = 526
    IncludeStartBerthing = 527
    IncludeFinishBerthing = 528
    IncludeLogisticsCosts = 529
    IncludeUnprofitableTrades = 530

    # UI
    ColourTheme = 600
    InterfaceScale = 601
    ShowToolTipImages = 602
    AverageCaseColour = 603
    WorstCaseColour = 604
    BestCaseColour = 605

    # Tagging
    DesirableTagColour = 700
    WarningTagColour = 701
    DangerTagColour = 702

    ZoneTagging = 800
    StarPortTagging = 801
    WorldSizeTagging = 802
    AtmosphereTagging = 803
    HydrographicsTagging = 804
    PopulationTagging = 805
    GovernmentTagging = 806
    LawLevelTagging = 807
    TechLevelTagging = 808
    BaseTypeTagging = 809
    TradeCodeTagging = 810
    ResourcesTagging = 811
    LabourTagging = 812
    InfrastructureTagging = 813
    EfficiencyTagging = 814
    HeterogeneityTagging = 815
    AcceptanceTagging = 816
    StrangenessTagging = 817
    SymbolsTagging = 818
    NobilityTagging = 819
    AllegianceTagging = 820
    SpectralTagging = 821
    LuminosityTagging = 822

class ConfigOptionDetails(object):
    def __init__(
            self,
            option: ConfigOption,
            restart: bool
            ) -> None:
        self._option = option
        self._restart = restart

    def option(self) -> ConfigOption:
        return self._option

    def value(self, futureValue: bool = False) -> typing.Any:
        raise RuntimeError(f'{type(self)} is derived from ConfigOptionDetails so must implement value')

    def setValue(self, value: typing.Any) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ConfigOptionDetails so must implement setValue')

    def isRestartRequired(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ConfigOptionDetails so must implement restartRequired')

    def read(self, settings: QtCore.QSettings) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ConfigOptionDetails so must implement read')

    def write(self, settings: QtCore.QSettings) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConfigOptionDetails so must implement write')

    @staticmethod
    def loadConfigSetting(
            settings: QtCore.QSettings,
            key: str,
            default: typing.Any,
            type: type
            ) -> typing.Any:
        try:
            # Explicitly check for key not being present and use default if it's not. This is
            # preferable to relying on value() as it can have some unexpected behaviour (e.g.
            # a default of None when reading a float will return 0.0 rather than None)
            if not settings.contains(key):
                return default

            return settings.value(key, defaultValue=default, type=type)
        except TypeError as ex:
            logging.error(f'Failed to read "{key}" from "{settings.group()}" in "{settings.fileName()}""  (value is not a {type.__name__})')
            return default
        except Exception as ex:
            logging.error(f'Failed to read "{key}" from "{settings.group()}" in "{settings.fileName()}"', exc_info=ex)
            return default

class SimpleOptionDetails(ConfigOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            type: typing.Type[object],
            default: typing.Any,
            restart: bool,
            valueToStringCb: typing.Optional[typing.Callable[[typing.Any], str]] = None,
            valueFromStringCb: typing.Optional[typing.Callable[[str], typing.Any]] = None
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._key = key
        self._type = type
        self._default = self._type(default)
        self._currentValue = self._futureValue = self._default
        self._valueToStringCb = valueToStringCb
        self._valueFromStringCb = valueFromStringCb

    def value(self, futureValue: bool = False) -> typing.Any:
        value = self._futureValue if futureValue else self._currentValue
        return value

    def setValue(self, value: typing.Any) -> bool:
        if value == self._futureValue:
            return False

        value = self._type(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

        return True

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> bool:
        if self._valueToStringCb and self._valueFromStringCb:
            value = self._valueFromStringCb(self.loadConfigSetting(
                settings=settings,
                key=self._key,
                default=self._valueToStringCb(self._currentValue),
                type=str))
        else:
            value = self.loadConfigSetting(
                settings=settings,
                key=self._key,
                default=self._currentValue,
                type=self._type)

        oldValue = self._currentValue
        self._currentValue = self._futureValue = value
        return self._currentValue != oldValue

    def write(self, settings: QtCore.QSettings) -> None:
        if self._valueToStringCb and self._valueFromStringCb:
            settings.setValue(self._key, self._valueToStringCb(self._futureValue))
        else:
            settings.setValue(self._key, self._futureValue)

class StringOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            default: str,
            restart: bool,
            validateCb: typing.Optional[typing.Callable[[str], bool]] = None
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=str,
            default=default,
            restart=restart)
        self._validateCb = validateCb

    def setValue(self, value: float) -> bool:
        if self._validateCb and not self._validateCb(value):
            value = self._default
        return super().setValue(value=value)

    def read(self, settings) -> bool:
        oldValue = self._currentValue
        if not super().read(settings=settings):
            return False
        if self._validateCb and not self._validateCb(self._currentValue):
            self._currentValue = self._futureValue = self._default
        return oldValue != self._currentValue

class BoolOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            default: bool
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=bool,
            default=default,
            restart=restart)

class IntOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            default: int,
            min: typing.Optional[int] = None,
            max: typing.Optional[int] = None
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=int,
            default=default,
            restart=restart)
        self._min = int(min) if min is not None else None
        self._max = int(max) if max is not None else None
        if self._min is not None and self._max is not None:
            self._min, self._max = common.minmax(self._min, self._max)

    def setValue(self, value: int) -> bool:
        value = self._clamp(value=value)
        return super().setValue(value=value)

    def read(self, settings) -> bool:
        oldValue = self._currentValue
        if not super().read(settings=settings):
            return False
        self._currentValue = self._futureValue = self._clamp(self._currentValue)
        return oldValue != self._currentValue

    def _clamp(self, value: int) -> int:
        if self._min is not None and value < self._min:
            value = self._min
        if self._max is not None and value > self._max:
            value = self._max
        return value

class FloatOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            default: float,
            min: typing.Optional[float] = None,
            max: typing.Optional[float] = None
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=float,
            default=default,
            restart=restart)
        self._min = float(min) if min is not None else None
        self._max = float(max) if max is not None else None
        if self._min is not None and self._max is not None:
            self._min, self._max = common.minmax(self._min, self._max)

    def setValue(self, value: float) -> bool:
        value = self._clamp(value=value)
        return super().setValue(value=value)

    def read(self, settings) -> bool:
        oldValue = self._currentValue
        if not super().read(settings=settings):
            return False
        self._currentValue = self._futureValue = self._clamp(self._currentValue)
        return oldValue != self._currentValue

    def _clamp(self, value: float) -> float:
        oldValue = value
        if self._min is not None and value < self._min:
            value = self._min
        if self._max is not None and value > self._max:
            value = self._max

        if value != oldValue:
            logging.warning(f'Clamped config option {self._key} to range {self._min} - {self._max}')

        return value

class EnumOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            enumType: typing.Type[enum.Enum],
            default: enum.Enum
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=enumType,
            default=default,
            restart=restart,
            valueToStringCb=lambda e: e.name,
            valueFromStringCb=lambda s: enumType.__members__[s] if s in enumType.__members__ else default)

class MappedOptionDetails(SimpleOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            keyType: typing.Type[typing.Any],
            default: typing.Any,
            toStringMap: typing.Mapping[typing.Any, str],
            fromStringMap: typing.Mapping[str, typing.Any]
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            type=keyType,
            default=default,
            restart=restart,
            valueToStringCb=lambda o: toStringMap[o],
            valueFromStringCb=lambda s: fromStringMap.get(s, default))
        self._toStringMap = dict(toStringMap)
        self._fromStringMap = dict(fromStringMap)

    def setValue(self, value: typing.Any) -> bool:
        if value not in self._toStringMap:
            value = self._default
        return super().setValue(value=value)

class UrlOptionDetails(StringOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            default: typing.Any
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            default=default,
            restart=restart,
            validateCb=self._validate)

    def _validate(self, value: str) -> bool:
        if not urllib.parse.urlparse(value):
            logging.warning(f'Ignoring config option {self._key} as URL "{value}" is invalid')
            return False
        return True

class ColourOptionDetails(StringOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            key: str,
            restart: bool,
            default: typing.Any
            ) -> None:
        super().__init__(
            option=option,
            key=key,
            default=default,
            restart=restart,
            validateCb=common.validateHtmlColour)

class RulesOptionDetails(ConfigOptionDetails):
    _DefaultSystem = traveller.RuleSystem.MGT2022
    _DefaultClassAFuelType = traveller.StarPortFuelType.AllTypes
    _DefaultClassBFuelType = traveller.StarPortFuelType.AllTypes
    _DefaultClassCFuelType = traveller.StarPortFuelType.UnrefinedOnly
    _DefaultClassDFuelType = traveller.StarPortFuelType.UnrefinedOnly
    _DefaultClassEFuelType = traveller.StarPortFuelType.NoFuel

    _RuleSystemKey = 'Rules' # NOTE: This name isn't ideal but it is what it is for backwards compatibility
    _ClassAFuelTypeKey = 'ClassAFuelTypeRule'
    _ClassBFuelTypeKey = 'ClassBFuelTypeRule'
    _ClassCFuelTypeKey = 'ClassCFuelTypeRule'
    _ClassDFuelTypeKey = 'ClassDFuelTypeRule'
    _ClassEFuelTypeKey = 'ClassEFuelTypeRule'

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._currentValue = self._futureValue = traveller.Rules(
            system=RulesOptionDetails._DefaultSystem,
            classAStarPortFuelType=RulesOptionDetails._DefaultClassAFuelType,
            classBStarPortFuelType=RulesOptionDetails._DefaultClassBFuelType,
            classCStarPortFuelType=RulesOptionDetails._DefaultClassCFuelType,
            classDStarPortFuelType=RulesOptionDetails._DefaultClassDFuelType,
            classEStarPortFuelType=RulesOptionDetails._DefaultClassEFuelType)

    def value(self, futureValue: bool = False) -> typing.Any:
        return traveller.Rules(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: traveller.Rules) -> bool:
        if value == self._futureValue:
            return False

        value = traveller.Rules(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

        return True

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> bool:
        system = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._RuleSystemKey,
            default=None,
            type=str)
        system = \
            traveller.RuleSystem.__members__[system] \
            if system in traveller.RuleSystem.__members__ else \
            RulesOptionDetails._DefaultSystem

        classAFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._ClassAFuelTypeKey,
            default=None,
            type=str)
        classAFuelType = \
            traveller.StarPortFuelType.__members__[classAFuelType] \
            if classAFuelType in traveller.StarPortFuelType.__members__ else \
            RulesOptionDetails._DefaultClassAFuelType

        classBFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._ClassBFuelTypeKey,
            default=None,
            type=str)
        classBFuelType = \
            traveller.StarPortFuelType.__members__[classBFuelType] \
            if classBFuelType in traveller.StarPortFuelType.__members__ else \
            RulesOptionDetails._DefaultClassBFuelType

        classCFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._ClassCFuelTypeKey,
            default=None,
            type=str)
        classCFuelType = \
            traveller.StarPortFuelType.__members__[classCFuelType] \
            if classCFuelType in traveller.StarPortFuelType.__members__ else \
            RulesOptionDetails._DefaultClassCFuelType

        classDFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._ClassDFuelTypeKey,
            default=None,
            type=str)
        classDFuelType = \
            traveller.StarPortFuelType.__members__[classDFuelType] \
            if classDFuelType in traveller.StarPortFuelType.__members__ else \
            RulesOptionDetails._DefaultClassDFuelType

        classEFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesOptionDetails._ClassEFuelTypeKey,
            default=None,
            type=str)
        classEFuelType = \
            traveller.StarPortFuelType.__members__[classEFuelType] \
            if classEFuelType in traveller.StarPortFuelType.__members__ else \
            RulesOptionDetails._DefaultClassEFuelType

        oldValue = self._currentValue
        self._currentValue = self._futureValue = traveller.Rules(
            system=system,
            classAStarPortFuelType=classAFuelType,
            classBStarPortFuelType=classBFuelType,
            classCStarPortFuelType=classCFuelType,
            classDStarPortFuelType=classDFuelType,
            classEStarPortFuelType=classEFuelType)
        return self._currentValue != oldValue

    def write(self, settings: QtCore.QSettings) -> None:
        settings.setValue(
            self._section + RulesOptionDetails._RuleSystemKey,
            self._futureValue.system().name)
        settings.setValue(
            self._section + RulesOptionDetails._ClassAFuelTypeKey,
            self._futureValue.starPortFuelType(code='A').name)
        settings.setValue(
            self._section + RulesOptionDetails._ClassBFuelTypeKey,
            self._futureValue.starPortFuelType(code='B').name)
        settings.setValue(
            self._section + RulesOptionDetails._ClassCFuelTypeKey,
            self._futureValue.starPortFuelType(code='C').name)
        settings.setValue(
            self._section + RulesOptionDetails._ClassDFuelTypeKey,
            self._futureValue.starPortFuelType(code='D').name)
        settings.setValue(
            self._section + RulesOptionDetails._ClassEFuelTypeKey,
            self._futureValue.starPortFuelType(code='E').name)

class TaggingOptionDetails(ConfigOptionDetails):
    _SettingIndexFixPattern = re.compile('.*[\\/]')

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            default: typing.Optional[typing.Mapping[typing.Any, app.TagLevel]],
            keyToStringCb: typing.Callable[[typing.Any], str],
            keyFromStringCb: typing.Callable[[str], typing.Optional[typing.Any]]
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._currentValue = self._futureValue = dict(default) if default else {}
        self._keyToStringCb = keyToStringCb
        self._keyFromStringCb = keyFromStringCb

    def value(self, futureValue: bool = False) -> typing.Any:
        return dict(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: typing.Mapping[typing.Any, app.TagLevel]) -> bool:
        if value == self._futureValue:
            return False

        value = dict(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

        return True

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> bool:
        values = {}
        settings.beginReadArray(self._section)
        try:
            for settingKey in settings.allKeys():
                if settingKey == 'size':
                    continue

                value = settings.value(settingKey, defaultValue=None, type=str)
                if value:
                    # Strip of the index that QSettings puts on array elements. For reasons I don't understand it's
                    # not consistent with which separator it uses
                    key = TaggingOptionDetails._SettingIndexFixPattern.sub('', settingKey)

                    if value not in app.TagLevel.__members__:
                        logging.warning(f'Ignoring tag map for "{key}" in section {self._section} as "{value}" is not a valid tag level')
                        continue

                    key = self._keyFromStringCb(key)
                    if key is None:
                        logging.warning(f'Ignoring tag map for "{key}" in section {self._section} as "{key}" is not a valid key')
                        continue
                    values[key] = app.TagLevel.__members__[value]
        finally:
            settings.endArray()

        oldValue = self._currentValue
        self._currentValue = self._futureValue = values
        return self._currentValue != oldValue

    def write(self, settings: QtCore.QSettings) -> None:
        settings.remove(self._section)
        settings.beginWriteArray(self._section)
        try:
            for index, (key, tagLevel) in enumerate(self._futureValue.items()):
                if tagLevel == None:
                    continue
                settings.setArrayIndex(index)
                settings.setValue(self._keyToStringCb(key), tagLevel.name)
        finally:
            settings.endArray()

class StringTaggingOptionDetails(TaggingOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            default: typing.Optional[typing.Mapping[str, app.TagLevel]] = None,
            ) -> None:
        super().__init__(
            option=option,
            section=section,
            restart=restart,
            default=default,
            keyToStringCb=lambda s: s,
            keyFromStringCb=lambda s: s)

class EnumTaggingOptionDetails(TaggingOptionDetails):
    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            enumType: typing.Type[enum.Enum],
            default: typing.Optional[typing.Mapping[enum.Enum, app.TagLevel]] = None,
            ) -> None:
        super().__init__(
            option=option,
            section=section,
            restart=restart,
            default=default,
            keyToStringCb=lambda e: e.name,
            keyFromStringCb=lambda s: enumType.__members__[s] if s in enumType.__members__ else None)

class ConfigEx(QtCore.QObject):
    configChanged = QtCore.pyqtSignal(str, object)

    _ConfigFileName = 'autojimmy.ini'

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _appDir = '.\\'
    _installDir = '.\\'
    _configDetails: typing.Dict[ConfigOption, ConfigOptionDetails] = {}

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
                    cls._instance._settings = None
                    cls._instance.load()
        return cls._instance

    @staticmethod
    def setDirs(
            installDir: str,
            appDir: str
            ) -> None:
        if ConfigEx._instance:
            raise RuntimeError('You can\'t set the app directories after the singleton has been initialised')
        ConfigEx._installDir = installDir
        ConfigEx._appDir = appDir

    @staticmethod
    def installDir() -> str:
        return ConfigEx._installDir

    @staticmethod
    def appDir() -> str:
        return ConfigEx._appDir

    def load(self) -> None:
        if not self._settings:
            filePath = os.path.join(self._appDir, self._ConfigFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        self._configDetails.clear()

        self._addOptionDetails(MappedOptionDetails(
            option=ConfigOption.LogLevel,
            key='Debug/LogLevel',
            restart=True,
            keyType=int,
            default=logging.WARNING,
            toStringMap={
                logging.CRITICAL: 'critical',
                logging.ERROR: 'error',
                logging.WARNING: 'warning',
                logging.INFO: 'information',
                logging.DEBUG: 'debug'},
            fromStringMap={
                'critical': logging.CRITICAL,
                'crit': logging.CRITICAL,
                'error': logging.ERROR,
                'err': logging.ERROR,
                'warning': logging.WARNING,
                'warn': logging.WARNING,
                'information': logging.INFO,
                'info': logging.INFO,
                'debug': logging.DEBUG,
                'dbg': logging.DEBUG}))

        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.Milieu,
            key='TravellerMap/Milieu',
            restart=True,
            enumType=travellermap.Milieu,
            default=travellermap.Milieu.M1105))

        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.MapStyle,
            key='TravellerMap/MapStyle',
            restart=False,
            enumType=travellermap.Style,
            default=travellermap.Style.Poster))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.GalacticDirectionsMapOption,
            key='TravellerMap/GalacticDirectionsMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.SectorGridMapOption,
            key='TravellerMap/SectorGridMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.SelectedSectorNamesMapOption,
            key='TravellerMap/SelectedSectorNamesMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.AllSectorNamesMapOption,
            key='TravellerMap/AllSectorNamesMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.BordersMapOption,
            key='TravellerMap/BordersMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.RoutesMapOption,
            key='TravellerMap/RoutesMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.RegionNamesMapOption,
            key='TravellerMap/RegionNamesMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.ImportantWorldsMapOption,
            key='TravellerMap/ImportantWorldsMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.WorldColoursMapOption,
            key='TravellerMap/WorldColoursMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.FilledBordersMapOption,
            key='TravellerMap/FilledBordersMapOption',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.DimUnofficialMapOption,
            key='TravellerMap/DimUnofficialMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.ImportanceOverlayMapOption,
            key='TravellerMap/ImportanceOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.PopulationOverlayMapOption,
            key='TravellerMap/PopulationOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.CapitalsOverlayMapOption,
            key='TravellerMap/CapitalsOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.MinorRaceOverlayMapOption,
            key='TravellerMap/MinorRaceOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.DroyneWorldOverlayMapOption,
            key='TravellerMap/DroyneWorldOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.AncientSitesOverlayMapOption,
            key='TravellerMap/AncientSitesOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.StellarOverlayMapOption,
            key='TravellerMap/StellarOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.EmpressWaveOverlayMapOption,
            key='TravellerMap/EmpressWaveOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.QrekrshaZoneOverlayMapOption,
            key='TravellerMap/QrekrshaZoneOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.AntaresSupernovaOverlayMapOption,
            key='TravellerMap/AntaresSupernovaOverlayMapOption',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.MainsOverlayMapOption,
            key='TravellerMap/MainsOverlayMapOption',
            restart=False,
            default=False))

        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.MapEngine,
            key='TravellerMap/MapEngine',
            restart=True,
            # TODO: The MapEngine should be moved to this .py file
            enumType=app.MapEngine,
            default=app.MapEngine.InApp))
        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.MapRenderingType,
            key='TravellerMap/MapRenderingType',
            restart=False,
            enumType=app.MapRenderingType,
            default=app.MapRenderingType.Tiled))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.MapAnimations,
            key='TravellerMap/MapAnimations',
            restart=False,
            default=True))

        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ProxyPort,
            key='Proxy/Port',
            restart=True,
            default=61977,
            min=1024, # Don't allow system ports
            max=65535))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ProxyHostPoolSize,
            key='Proxy/HostPoolSize',
            restart=True,
            default=1 if common.isMacOS() else 4,
            min=1,
            max=10))
        self._addOptionDetails(UrlOptionDetails(
            option=ConfigOption.ProxyMapUrl,
            key='Proxy/MapUrl',
            restart=True,
            default=travellermap.TravellerMapBaseUrl))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ProxyTileCacheSize,
            key='Proxy/TileCacheSize',
            restart=True,
            default=500 * 1000 * 1000, # 500MB
            min=0)) # 0 means disable cache
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ProxyTileCacheLifetime,
            key='Proxy/TileCacheLifetime',
            restart=True,
            default=14, # Days
            min=0)) # 0 means never expire
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.ProxySvgComposition,
            key='Proxy/SvgComposition',
            restart=True,
            default=False))

        self._addOptionDetails(RulesOptionDetails(
            option=ConfigOption.Rules,
            section='Game/',
            restart=True))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.PlayerBrokerDM,
            key='Game/PlayerBrokerDM',
            restart=False,
            default=0,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        # Default ship values are based on a standard Scout ship
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ShipTonnage,
            key='Game/ShipTonnage',
            restart=False,
            default=100,
            min=100))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ShipJumpRating,
            key='Game/ShipJumpRating',
            restart=False,
            default=2,
            min=app.MinPossibleJumpRating,
            max=app.MaxPossibleJumpRating))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ShipCargoCapacity,
            key='Game/ShipCargoCapacity',
            restart=False,
            default=12,
            min=0))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.ShipFuelCapacity,
            key='Game/ShipFuelCapacity',
            restart=False,
            default=23,
            min=0))
        self._addOptionDetails(FloatOptionDetails(
            option=ConfigOption.ShipCurrentFuel,
            key='Game/ShipCurrentFuel',
            restart=False,
            default=0,
            min=0))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UseShipFuelPerParsec,
            key='Game/UseShipFuelPerParsec',
            restart=False,
            default=False))
        self._addOptionDetails(FloatOptionDetails(
            option=ConfigOption.ShipFuelPerParsec,
            key='Game/ShipFuelPerParsec',
            restart=False,
            # NOTE: Setting the default like this assumes the ShitTonnage option
            # has already been added
            default=self.asInt(option=ConfigOption.ShipTonnage) * 0.1, # 10% of ship tonnage
            # TODO: Not sure about this value, need to make sure it still allows hop-3
            min=0.01))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.PerJumpOverhead,
            key='Game/PerJumpOverhead',
            restart=False,
            default=0,
            min=0))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.AvailableFunds,
            key='Game/AvailableFunds',
            restart=False,
            default=10000,
            min=0))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.MinSellerDM,
            key='Game/MinSellerDM',
            restart=False,
            default=1,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.MaxSellerDM,
            key='Game/MaxSellerDM',
            restart=False,
            default=3,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.MinBuyerDM,
            key='Game/MinBuyerDM',
            restart=False,
            default=1,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.MaxBuyerDM,
            key='Game/MaxBuyerDM',
            restart=False,
            default=3,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UsePurchaseBroker,
            key='Game/UsePurchaseBroker',
            restart=False,
            default=False))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.PurchaseBrokerDmBonus,
            key='Game/PurchaseBrokerDmBonus',
            restart=False,
            default=1))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UseSaleBroker,
            key='Game/UseSaleBroker',
            restart=False,
            default=False))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.SaleBrokerDmBonus,
            key='Game/SaleBrokerDmBonus',
            restart=False,
            default=1))
        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.RoutingType,
            key='Game/RoutingType',
            restart=False,
            enumType=logic.RoutingType,
            default=logic.RoutingType.FuelBased))
        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.RouteOptimisation,
            key='Game/RouteOptimisation',
            restart=False,
            enumType=logic.RouteOptimisation,
            default=logic.RouteOptimisation.ShortestDistance))
        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.RefuellingStrategy,
            key='Game/RefuellingStrategy',
            restart=False,
            enumType=logic.RefuellingStrategy,
            default=logic.RefuellingStrategy.WildernessPreferred))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UseFuelCaches,
            key='Game/UseFuelCaches',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UseAnomalyRefuelling,
            key='Game/UseAnomalyRefuelling',
            restart=False,
            default=True))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.AnomalyFuelCost,
            key='Game/AnomalyFuelCost',
            restart=False,
            default=0,
            min=0))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.UseAnomalyBerthing,
            key='Game/UseAnomalyBerthing',
            restart=False,
            default=False))
        self._addOptionDetails(IntOptionDetails(
            option=ConfigOption.AnomalyBerthingCost,
            key='Game/AnomalyBerthingCost',
            restart=False,
            default=0,
            min=0))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.IncludeStartBerthing,
            key='Game/IncludeStartBerthing',
            restart=False,
            default=False))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.IncludeFinishBerthing,
            key='Game/IncludeFinishBerthing',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.IncludeLogisticsCosts,
            key='Game/IncludeLogisticsCosts',
            restart=False,
            default=True))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.IncludeUnprofitableTrades,
            key='Game/IncludeUnprofitableTrades',
            restart=False,
            default=False))

        self._addOptionDetails(EnumOptionDetails(
            option=ConfigOption.ColourTheme,
            key='GUI/ColourTheme',
            restart=True,
            # TODO: The ColourTheme should be moved to this .py file
            enumType=app.ColourTheme,
            default=app.ColourTheme.DarkMode))
        self._addOptionDetails(FloatOptionDetails(
            option=ConfigOption.InterfaceScale,
            key='GUI/InterfaceScale',
            restart=True,
            default=1,
            min=1,
            max=4))
        self._addOptionDetails(BoolOptionDetails(
            option=ConfigOption.ShowToolTipImages,
            key='GUI/ShowToolTipImages',
            restart=False,
            default=True))

        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.AverageCaseColour,
            key='GUI/AverageCaseColour',
            restart=False,
            default='#0A0000FF'))
        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.WorstCaseColour,
            key='GUI/WorstCaseColour',
            restart=False,
            default='#0AFF0000'))
        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.BestCaseColour,
            key='GUI/BestCaseColour',
            restart=False,
            default='#0A00FF00'))

        colourTheme = self.asEnum(
            option=ConfigOption.ColourTheme,
            enumType=app.ColourTheme)
        isDarkMode = colourTheme is app.ColourTheme.DarkMode or \
            (colourTheme is app.ColourTheme.UseOSSetting and darkdetect.isDark())
        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.DesirableTagColour,
            key='Tagging/DesirableTagColour',
            restart=False,
            default='#8000AA00' if isDarkMode else '#808CD47E'))
        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.WarningTagColour,
            key='Tagging/WarningTagColour',
            restart=False,
            default='#80FF7700' if isDarkMode else '#80994700'))
        self._addOptionDetails(ColourOptionDetails(
            option=ConfigOption.DangerTagColour,
            key='Tagging/DangerTagColour',
            restart=False,
            default='#80BC2023' if isDarkMode else '#80FF6961'))

        self._addOptionDetails(EnumTaggingOptionDetails(
            option=ConfigOption.ZoneTagging,
            section='ZoneTagging',
            restart=False,
            enumType=traveller.ZoneType,
            default={
                traveller.ZoneType.AmberZone: app.TagLevel.Warning,
                traveller.ZoneType.RedZone: app.TagLevel.Danger,
                traveller.ZoneType.Unabsorbed: app.TagLevel.Warning,
                traveller.ZoneType.Forbidden: app.TagLevel.Danger}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.StarPortTagging,
            section='StarPortTagging',
            restart=False,
            default={'X': app.TagLevel.Warning}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.WorldSizeTagging,
            section='WorldSizeTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.AtmosphereTagging,
            section='AtmosphereTagging',
            restart=False,
            default={
                # Tag corrosive and insidious atmospheres
                'B': app.TagLevel.Danger,
                'C': app.TagLevel.Danger}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.HydrographicsTagging,
            section='HydrographicsTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.PopulationTagging,
            section='PopulationTagging',
            restart=False,
            default={
                # Tag worlds with less than 100 people
                '0': app.TagLevel.Danger,
                '1': app.TagLevel.Warning,
                '2': app.TagLevel.Warning}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.GovernmentTagging,
            section='GovernmentTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.LawLevelTagging,
            section='LawLevelTagging',
            restart=False,
            default={'0': app.TagLevel.Danger}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.TechLevelTagging,
            section='TechLevelTagging',
            restart=False))
        self._addOptionDetails(EnumTaggingOptionDetails(
            option=ConfigOption.BaseTypeTagging,
            section='BaseTypeTagging',
            restart=False,
            enumType=traveller.BaseType))
        self._addOptionDetails(EnumTaggingOptionDetails(
            option=ConfigOption.TradeCodeTagging,
            section='TradeCodeTagging',
            restart=False,
            enumType=traveller.TradeCode,
            default={
                traveller.TradeCode.AmberZone: app.TagLevel.Warning,
                traveller.TradeCode.RedZone: app.TagLevel.Danger,
                traveller.TradeCode.HellWorld: app.TagLevel.Danger,
                traveller.TradeCode.PenalColony: app.TagLevel.Danger,
                traveller.TradeCode.PrisonCamp: app.TagLevel.Danger,
                traveller.TradeCode.Reserve: app.TagLevel.Danger,
                traveller.TradeCode.DangerousWorld: app.TagLevel.Danger,
                traveller.TradeCode.ForbiddenWorld: app.TagLevel.Danger}))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.ResourcesTagging,
            section='ResourcesTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.LabourTagging,
            section='LabourTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.InfrastructureTagging,
            section='InfrastructureTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.EfficiencyTagging,
            section='EfficiencyTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.HeterogeneityTagging,
            section='HeterogeneityTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.AcceptanceTagging,
            section='AcceptanceTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.StrangenessTagging,
            section='StrangenessTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.SymbolsTagging,
            section='SymbolsTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.SymbolsTagging,
            section='SymbolsTagging',
            restart=False))
        self._addOptionDetails(EnumTaggingOptionDetails(
            option=ConfigOption.NobilityTagging,
            section='NobilityTagging',
            restart=False,
            enumType=traveller.NobilityType))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.AllegianceTagging,
            section='AllegianceTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.SpectralTagging,
            section='SpectralTagging',
            restart=False))
        self._addOptionDetails(StringTaggingOptionDetails(
            option=ConfigOption.LuminosityTagging,
            section='LuminosityTagging',
            restart=False))

    def option(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> typing.Any:
        optionDetails = self._configDetails[option]
        return optionDetails.value(futureValue=futureValue)

    def setOption(
            self,
            option: ConfigOption,
            value: typing.Any
            ) -> bool:
        optionDetails = self._configDetails[option]
        optionChanged = optionDetails.setValue(value=value)
        if optionChanged:
            optionDetails.write(self._settings)
        return optionChanged

    def asBool(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> bool:
        optionDetails = self._configDetails[option]
        return bool(optionDetails.value(futureValue=futureValue))

    def asStr(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> str:
        optionDetails = self._configDetails[option]
        return str(optionDetails.value(futureValue=futureValue))

    def asInt(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> int:
        optionDetails = self._configDetails[option]
        return int(optionDetails.value(futureValue=futureValue))

    def asFloat(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> int:
        optionDetails = self._configDetails[option]
        return float(optionDetails.value(futureValue=futureValue))

    def asEnum(
            self,
            option: ConfigOption,
            enumType: typing.Type[enum.Enum],
            futureValue: bool = False
            ) -> enum.Enum:
        optionDetails = self._configDetails[option]
        return enumType(optionDetails.value(futureValue=futureValue))

    def asObject(
            self,
            option: ConfigOption,
            objectType: typing.Type[typing.Any],
            futureValue: bool = False
            ) -> object:
        optionDetails = self._configDetails[option]
        return objectType(optionDetails.value(futureValue=futureValue))

    def asTagMap(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> typing.Mapping[typing.Any, app.TagLevel]:
        optionDetails = self._configDetails[option]
        return dict(optionDetails.value(futureValue=futureValue))

    def isRestartRequired(self) -> bool:
        for optionDetails in self._configDetails.values():
            if optionDetails.isRestartRequired():
                return True
        return False

    def _addOptionDetails(self, optionDetails: ConfigOptionDetails) -> None:
        ConfigEx._configDetails[optionDetails.option()] = optionDetails
        try:
            optionDetails.read(settings=self._settings)
        except Exception as ex:
            logging.warning(f'Failed to read config option {optionDetails.option().name}', exc_info=ex)
