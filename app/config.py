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

# NOTE: If I ever change the name of these enums I'll need some mapping
# as they're written to the config file. This only applies to the name
# not the value
class ColourTheme(enum.Enum):
    DarkMode = 'Dark Mode'
    LightMode = 'Light Mode'
    UseOSSetting = 'Use OS Setting'

# NOTE: If I ever change the name of these enums I'll need some mapping
# as they're written to the config file. This only applies to the name
# not the value
class MapEngine(enum.Enum):
    InApp = app.AppName
    WebProxy = 'Web (Proxy)'
    WebDirect = 'Web (Direct)'

class MapRendering(enum.Enum):
    Tiled = 'Tiled' # Tiles rendered in background (i.e. the same as Traveller Map)
    Hybrid = 'Hybrid' # Tiles rendered in foreground
    Full = 'Full' # Entire frame rendered each redraw and no digital zoom between log zoom levels

class ConfigOption(enum.Enum):
    # Debug
    LogLevel = 100

    # Map
    Milieu = 200
    MapStyle = 201
    MapOptions = 202
    MapEngine = 203
    MapRendering = 204
    MapAnimations = 205

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
    OutcomeColours = 603

    # Tagging
    DesirableTagColour = 700
    WarningTagColour = 701
    DangerTagColour = 702

    # TODO: I'm thinking I might just want one Tagging config option
    # that covers all the tagging as having so many will mean consumers
    # need to check for a lot of different types. The same could also
    # be true for tagging colours and avg/worst/best colours
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

class ConfigItem(object):
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
        raise RuntimeError(f'{type(self)} is derived from ConfigItem so must implement value')

    def setValue(self, value: typing.Any) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConfigItem so must implement setValue')

    def isRestartRequired(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from ConfigItem so must implement restartRequired')

    def read(self, settings: QtCore.QSettings) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConfigItem so must implement read')

    def write(self, settings: QtCore.QSettings) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConfigItem so must implement write')

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

class SimpleConfigItem(ConfigItem):
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

    def setValue(self, value: typing.Any) -> None:
        if value == self._futureValue:
            return

        value = self._type(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        if self._valueToStringCb and self._valueFromStringCb:
            value = self._valueFromStringCb(self.loadConfigSetting(
                settings=settings,
                key=self._key,
                default=self._valueToStringCb(self._default),
                type=str))
        else:
            value = self.loadConfigSetting(
                settings=settings,
                key=self._key,
                default=self._default,
                type=self._type)

        self._currentValue = self._futureValue = value

    def write(self, settings: QtCore.QSettings) -> None:
        if self._valueToStringCb and self._valueFromStringCb:
            settings.setValue(self._key, self._valueToStringCb(self._futureValue))
        else:
            settings.setValue(self._key, self._futureValue)

class StringConfigItem(SimpleConfigItem):
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

    def setValue(self, value: float) -> None:
        if self._validateCb and not self._validateCb(value):
            value = self._default
        super().setValue(value=value)

    def read(self, settings) -> None:
        super().read(settings=settings)
        if self._validateCb and not self._validateCb(self._currentValue):
            self._currentValue = self._futureValue = self._default

class BoolConfigItem(SimpleConfigItem):
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

class IntConfigItem(SimpleConfigItem):
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

    def setValue(self, value: int) -> None:
        return super().setValue(value=self._clamp(value=value))

    def read(self, settings) -> None:
        super().read(settings=settings)
        self._currentValue = self._futureValue = self._clamp(self._currentValue)

    def _clamp(self, value: int) -> int:
        oldValue = value
        if self._min is not None and value < self._min:
            value = self._min
        if self._max is not None and value > self._max:
            value = self._max

        if value != oldValue:
            logging.warning(f'Clamped config option {self._key} to range {self._min} - {self._max}')

        return value

class FloatConfigItem(SimpleConfigItem):
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

    def setValue(self, value: float) -> None:
        super().setValue(value=self._clamp(value=value))

    def read(self, settings) -> None:
        super().read(settings=settings)
        self._currentValue = self._futureValue = self._clamp(self._currentValue)

    def _clamp(self, value: float) -> float:
        oldValue = value
        if self._min is not None and value < self._min:
            value = self._min
        if self._max is not None and value > self._max:
            value = self._max

        if value != oldValue:
            logging.warning(f'Clamped config option {self._key} to range {self._min} - {self._max}')

        return value

class EnumConfigItem(SimpleConfigItem):
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

class MappedConfigItem(SimpleConfigItem):
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

    def setValue(self, value: typing.Any) -> None:
        if value not in self._toStringMap:
            value = self._default
        super().setValue(value=value)

class UrlConfigItem(StringConfigItem):
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

class ColourConfigItem(StringConfigItem):
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

class MapOptionsConfigItem(ConfigItem):
    _MapOptionToSettingsKey = {
        travellermap.Option.GalacticDirections: '/GalacticDirections',
        travellermap.Option.SectorGrid: '/SectorGrid',
        travellermap.Option.SelectedSectorNames: '/SelectedSectorNames',
        travellermap.Option.SectorNames: '/AllSectorNames',
        travellermap.Option.Borders: '/Borders',
        travellermap.Option.Routes: '/Routes',
        travellermap.Option.RegionNames: '/RegionNames',
        travellermap.Option.ImportantWorlds: '/ImportantWorlds',
        travellermap.Option.WorldColours: '/WorldColours',
        travellermap.Option.FilledBorders: '/FilledBorders',
        travellermap.Option.DimUnofficial: '/DimUnofficial',
        travellermap.Option.ImportanceOverlay: '/ImportanceOverlay',
        travellermap.Option.PopulationOverlay: '/PopulationOverlay',
        travellermap.Option.CapitalsOverlay: '/CapitalsOverlay',
        travellermap.Option.MinorRaceOverlay: '/MinorRaceOverlay',
        travellermap.Option.DroyneWorldOverlay: '/DroyneWorldOverlay',
        travellermap.Option.AncientSitesOverlay: '/AncientSitesOverlay',
        travellermap.Option.StellarOverlay: '/StellarOverlay',
        travellermap.Option.EmpressWaveOverlay: '/EmpressWaveOverlay',
        travellermap.Option.QrekrshaZoneOverlay: '/QrekrshaZoneOverlay',
        travellermap.Option.AntaresSupernovaOverlay: '/AntaresSupernovaOverlay',
        travellermap.Option.MainsOverlay: '/MainsOverlay'
    }

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            default: typing.Iterable[travellermap.Option] = None
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._default = set(default) if default else set()
        self._currentValue = self._futureValue = self._default

    def value(self, futureValue: bool = False) -> typing.Iterable[travellermap.Option]:
        return list(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: typing.Iterable[travellermap.Option]) -> None:
        if value == self._futureValue:
            return

        value = list(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        values = set()
        for option, settingKey in MapOptionsConfigItem._MapOptionToSettingsKey.items():
            value = settings.value(
                self._section + settingKey,
                defaultValue=option in self._default,
                type=bool)
            if value:
                values.add(option)

        self._currentValue = self._futureValue = values

    def write(self, settings: QtCore.QSettings) -> None:
        for option, settingKey in MapOptionsConfigItem._MapOptionToSettingsKey.items():
            settings.setValue(
                self._section + settingKey,
                option in self._futureValue)

class RulesConfigItem(ConfigItem):
    _DefaultSystem = traveller.RuleSystem.MGT2022
    _DefaultClassAFuelType = traveller.StarPortFuelType.AllTypes
    _DefaultClassBFuelType = traveller.StarPortFuelType.AllTypes
    _DefaultClassCFuelType = traveller.StarPortFuelType.UnrefinedOnly
    _DefaultClassDFuelType = traveller.StarPortFuelType.UnrefinedOnly
    _DefaultClassEFuelType = traveller.StarPortFuelType.NoFuel

    _RuleSystemKey = '/Rules' # NOTE: This name isn't ideal but it is what it is for backwards compatibility
    _ClassAFuelTypeKey = '/ClassAFuelTypeRule'
    _ClassBFuelTypeKey = '/ClassBFuelTypeRule'
    _ClassCFuelTypeKey = '/ClassCFuelTypeRule'
    _ClassDFuelTypeKey = '/ClassDFuelTypeRule'
    _ClassEFuelTypeKey = '/ClassEFuelTypeRule'

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._currentValue = self._futureValue = traveller.Rules(
            system=RulesConfigItem._DefaultSystem,
            classAStarPortFuelType=RulesConfigItem._DefaultClassAFuelType,
            classBStarPortFuelType=RulesConfigItem._DefaultClassBFuelType,
            classCStarPortFuelType=RulesConfigItem._DefaultClassCFuelType,
            classDStarPortFuelType=RulesConfigItem._DefaultClassDFuelType,
            classEStarPortFuelType=RulesConfigItem._DefaultClassEFuelType)

    def value(self, futureValue: bool = False) -> typing.Any:
        return traveller.Rules(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: traveller.Rules) -> None:
        if value == self._futureValue:
            return

        value = traveller.Rules(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        system = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._RuleSystemKey,
            default=None,
            type=str)
        system = \
            traveller.RuleSystem.__members__[system] \
            if system in traveller.RuleSystem.__members__ else \
            RulesConfigItem._DefaultSystem

        classAFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassAFuelTypeKey,
            default=None,
            type=str)
        classAFuelType = \
            traveller.StarPortFuelType.__members__[classAFuelType] \
            if classAFuelType in traveller.StarPortFuelType.__members__ else \
            RulesConfigItem._DefaultClassAFuelType

        classBFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassBFuelTypeKey,
            default=None,
            type=str)
        classBFuelType = \
            traveller.StarPortFuelType.__members__[classBFuelType] \
            if classBFuelType in traveller.StarPortFuelType.__members__ else \
            RulesConfigItem._DefaultClassBFuelType

        classCFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassCFuelTypeKey,
            default=None,
            type=str)
        classCFuelType = \
            traveller.StarPortFuelType.__members__[classCFuelType] \
            if classCFuelType in traveller.StarPortFuelType.__members__ else \
            RulesConfigItem._DefaultClassCFuelType

        classDFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassDFuelTypeKey,
            default=None,
            type=str)
        classDFuelType = \
            traveller.StarPortFuelType.__members__[classDFuelType] \
            if classDFuelType in traveller.StarPortFuelType.__members__ else \
            RulesConfigItem._DefaultClassDFuelType

        classEFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassEFuelTypeKey,
            default=None,
            type=str)
        classEFuelType = \
            traveller.StarPortFuelType.__members__[classEFuelType] \
            if classEFuelType in traveller.StarPortFuelType.__members__ else \
            RulesConfigItem._DefaultClassEFuelType

        self._currentValue = self._futureValue = traveller.Rules(
            system=system,
            classAStarPortFuelType=classAFuelType,
            classBStarPortFuelType=classBFuelType,
            classCStarPortFuelType=classCFuelType,
            classDStarPortFuelType=classDFuelType,
            classEStarPortFuelType=classEFuelType)

    def write(self, settings: QtCore.QSettings) -> None:
        settings.setValue(
            self._section + RulesConfigItem._RuleSystemKey,
            self._futureValue.system().name)
        settings.setValue(
            self._section + RulesConfigItem._ClassAFuelTypeKey,
            self._futureValue.starPortFuelType(code='A').name)
        settings.setValue(
            self._section + RulesConfigItem._ClassBFuelTypeKey,
            self._futureValue.starPortFuelType(code='B').name)
        settings.setValue(
            self._section + RulesConfigItem._ClassCFuelTypeKey,
            self._futureValue.starPortFuelType(code='C').name)
        settings.setValue(
            self._section + RulesConfigItem._ClassDFuelTypeKey,
            self._futureValue.starPortFuelType(code='D').name)
        settings.setValue(
            self._section + RulesConfigItem._ClassEFuelTypeKey,
            self._futureValue.starPortFuelType(code='E').name)

class OutcomeColoursConfigItem(ConfigItem):
    _DefaultAverageCaseColour = '#0A0000FF'
    _DefaultWorstCaseColour = '#0AFF0000'
    _DefaultBestCaseColour = '#0A00FF00'

    _AverageCaseKey = '/AverageCaseColour'
    _WorstCaseKey = '/WorstCaseColour'
    _BestCaseKey = '/BestCaseColour'

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._currentValue = self._futureValue = app.OutcomeColours(
            averageCaseColour=OutcomeColoursConfigItem._DefaultAverageCaseColour,
            worstCaseColour=OutcomeColoursConfigItem._DefaultWorstCaseColour,
            bestCaseColour=OutcomeColoursConfigItem._DefaultBestCaseColour)

    def value(self, futureValue: bool = False) -> typing.Any:
        return app.OutcomeColours(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: app.OutcomeColours) -> None:
        if value == self._futureValue:
            return

        value = app.OutcomeColours(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        averageCaseColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + OutcomeColoursConfigItem._AverageCaseKey,
            default=OutcomeColoursConfigItem._DefaultAverageCaseColour,
            type=str)

        worstCaseColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + OutcomeColoursConfigItem._WorstCaseKey,
            default=OutcomeColoursConfigItem._DefaultWorstCaseColour,
            type=str)

        bestCaseColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + OutcomeColoursConfigItem._BestCaseKey,
            default=OutcomeColoursConfigItem._DefaultBestCaseColour,
            type=str)

        self._currentValue = self._futureValue = app.OutcomeColours(
            averageCaseColour=averageCaseColour,
            worstCaseColour=worstCaseColour,
            bestCaseColour=bestCaseColour)

    def write(self, settings: QtCore.QSettings) -> None:
        settings.setValue(
            self._section + OutcomeColoursConfigItem._AverageCaseKey,
            self._futureValue.colour(logic.RollOutcome.AverageCase))
        settings.setValue(
            self._section + OutcomeColoursConfigItem._WorstCaseKey,
            self._futureValue.colour(logic.RollOutcome.WorstCase))
        settings.setValue(
            self._section + OutcomeColoursConfigItem._BestCaseKey,
            self._futureValue.colour(logic.RollOutcome.BestCase))

class TaggingConfigItem(ConfigItem):
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
        self._default = dict(default) if default else {}
        self._currentValue = self._futureValue = self._default
        self._keyToStringCb = keyToStringCb
        self._keyFromStringCb = keyFromStringCb

    def value(self, futureValue: bool = False) -> typing.Any:
        return dict(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: typing.Mapping[typing.Any, app.TagLevel]) -> None:
        if value == self._futureValue:
            return

        value = dict(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        # Check to see if there is a size element for this section. This is a hack
        # to differentiate between there being no section and there being a section
        # with no entries. The distinction is important as we want to use the
        # default configuration if there is no section but not if there is a section
        # with no entries as the user must have configured it like that.
        if settings.contains(self._section + '/size'):
            values = {}
            settings.beginReadArray(self._section)
            try:
                for settingKey in settings.allKeys():
                    if settingKey == 'size':
                        continue

                    # Strip of the index that QSettings puts on array elements. For reasons I don't understand it's
                    # not consistent with which separator it uses
                    key = self._keyFromStringCb(TaggingConfigItem._SettingIndexFixPattern.sub('', settingKey))
                    if key is None:
                        logging.warning(f'Ignoring tag map for "{key}" in section {self._section} as "{key}" is not a valid key')
                        continue

                    value = settings.value(settingKey, defaultValue=None, type=str)
                    if value:
                        if value not in app.TagLevel.__members__:
                            logging.warning(f'Ignoring tag map for "{key}" in section {self._section} as "{value}" is not a valid tag level')
                            continue
                        values[key] = app.TagLevel.__members__[value]
            finally:
                settings.endArray()
        else:
            # There is no section preset so use default configuration.
            values = self._default

        self._currentValue = self._futureValue = values

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

class StringTaggingConfigItem(TaggingConfigItem):
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

class EnumTaggingConfigItem(TaggingConfigItem):
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

class Config(QtCore.QObject):
    configChanged = QtCore.pyqtSignal(
        ConfigOption, # Config option that has changed
        object, # Old value
        object) # New value

    _ConfigFileName = 'autojimmy.ini'

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _appDir = '.\\'
    _installDir = '.\\'
    _configItems: typing.Dict[ConfigOption, ConfigItem] = {}

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
                    QtCore.QObject.__init__(cls._instance)
                    cls._instance._settings = None
                    cls._instance.load()
        return cls._instance

    @staticmethod
    def setDirs(
            installDir: str,
            appDir: str
            ) -> None:
        if Config._instance:
            raise RuntimeError('You can\'t set the app directories after the singleton has been initialised')
        Config._installDir = installDir
        Config._appDir = appDir

    @staticmethod
    def installDir() -> str:
        return Config._installDir

    @staticmethod
    def appDir() -> str:
        return Config._appDir

    def load(self) -> None:
        if not self._settings:
            filePath = os.path.join(self._appDir, self._ConfigFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        self._configItems.clear()

        self._addConfigItem(MappedConfigItem(
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

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.Milieu,
            key='TravellerMap/Milieu',
            restart=False, # TODO: This being 'live' is a work in progress
            enumType=travellermap.Milieu,
            default=travellermap.Milieu.M1105))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.MapStyle,
            key='TravellerMap/MapStyle',
            restart=False,
            enumType=travellermap.Style,
            default=travellermap.Style.Poster))
        self._addConfigItem(MapOptionsConfigItem(
            option=ConfigOption.MapOptions,
            section='TravellerMap',
            restart=False,
            default=[
                travellermap.Option.GalacticDirections,
                travellermap.Option.SectorGrid,
                travellermap.Option.SelectedSectorNames,
                travellermap.Option.Borders,
                travellermap.Option.Routes,
                travellermap.Option.RegionNames,
                travellermap.Option.ImportantWorlds,
                travellermap.Option.FilledBorders]))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.MapEngine,
            key='TravellerMap/MapEngine',
            restart=True,
            # TODO: The MapEngine should be moved to this .py file
            enumType=MapEngine,
            default=MapEngine.InApp))
        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.MapRendering,
            key='TravellerMap/MapRenderingType',
            restart=False,
            enumType=MapRendering,
            default=MapRendering.Tiled))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.MapAnimations,
            key='TravellerMap/MapAnimations',
            restart=False,
            default=True))

        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ProxyPort,
            key='Proxy/Port',
            restart=True,
            default=61977,
            min=1024, # Don't allow system ports
            max=65535))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ProxyHostPoolSize,
            key='Proxy/HostPoolSize',
            restart=True,
            default=1 if common.isMacOS() else 4,
            min=1,
            max=10))
        self._addConfigItem(UrlConfigItem(
            option=ConfigOption.ProxyMapUrl,
            key='Proxy/MapUrl',
            restart=True,
            default=travellermap.TravellerMapBaseUrl))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ProxyTileCacheSize,
            key='Proxy/TileCacheSize',
            restart=True,
            default=500 * 1000 * 1000, # 500MB
            min=0)) # 0 means disable cache
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ProxyTileCacheLifetime,
            key='Proxy/TileCacheLifetime',
            restart=True,
            default=14, # Days
            min=0)) # 0 means never expire
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.ProxySvgComposition,
            key='Proxy/SvgComposition',
            restart=True,
            default=False))

        self._addConfigItem(RulesConfigItem(
            option=ConfigOption.Rules,
            section='Game',
            restart=False))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.PlayerBrokerDM,
            key='Game/PlayerBrokerDM',
            restart=False,
            default=0,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        # Default ship values are based on a standard Scout ship
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ShipTonnage,
            key='Game/ShipTonnage',
            restart=False,
            default=100,
            min=100))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ShipJumpRating,
            key='Game/ShipJumpRating',
            restart=False,
            default=2,
            min=app.MinPossibleJumpRating,
            max=app.MaxPossibleJumpRating))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ShipCargoCapacity,
            key='Game/ShipCargoCapacity',
            restart=False,
            default=12,
            min=0))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.ShipFuelCapacity,
            key='Game/ShipFuelCapacity',
            restart=False,
            default=23,
            min=0))
        self._addConfigItem(FloatConfigItem(
            option=ConfigOption.ShipCurrentFuel,
            key='Game/ShipCurrentFuel',
            restart=False,
            default=0,
            min=0))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UseShipFuelPerParsec,
            key='Game/UseShipFuelPerParsec',
            restart=False,
            default=False))
        self._addConfigItem(FloatConfigItem(
            option=ConfigOption.ShipFuelPerParsec,
            key='Game/ShipFuelPerParsec',
            restart=False,
            # NOTE: Setting the default like this assumes the ShitTonnage option
            # has already been added
            default=self.value(option=ConfigOption.ShipTonnage) * 0.1, # 10% of ship tonnage
            # TODO: Not sure about this value, need to make sure it still allows hop-3
            min=0.01))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.PerJumpOverhead,
            key='Game/PerJumpOverhead',
            restart=False,
            default=0,
            min=0))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.AvailableFunds,
            key='Game/AvailableFunds',
            restart=False,
            default=10000,
            min=0))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.MinSellerDM,
            key='Game/MinSellerDM',
            restart=False,
            default=1,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.MaxSellerDM,
            key='Game/MaxSellerDM',
            restart=False,
            default=3,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.MinBuyerDM,
            key='Game/MinBuyerDM',
            restart=False,
            default=1,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.MaxBuyerDM,
            key='Game/MaxBuyerDM',
            restart=False,
            default=3,
            min=app.MinPossibleDm,
            max=app.MaxPossibleDm))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UsePurchaseBroker,
            key='Game/UsePurchaseBroker',
            restart=False,
            default=False))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.PurchaseBrokerDmBonus,
            key='Game/PurchaseBrokerDmBonus',
            restart=False,
            default=1))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UseSaleBroker,
            key='Game/UseSaleBroker',
            restart=False,
            default=False))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.SaleBrokerDmBonus,
            key='Game/SaleBrokerDmBonus',
            restart=False,
            default=1))
        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.RoutingType,
            key='Game/RoutingType',
            restart=False,
            enumType=logic.RoutingType,
            default=logic.RoutingType.FuelBased))
        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.RouteOptimisation,
            key='Game/RouteOptimisation',
            restart=False,
            enumType=logic.RouteOptimisation,
            default=logic.RouteOptimisation.ShortestDistance))
        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.RefuellingStrategy,
            key='Game/RefuellingStrategy',
            restart=False,
            enumType=logic.RefuellingStrategy,
            default=logic.RefuellingStrategy.WildernessPreferred))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UseFuelCaches,
            key='Game/UseFuelCaches',
            restart=False,
            default=True))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UseAnomalyRefuelling,
            key='Game/UseAnomalyRefuelling',
            restart=False,
            default=True))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.AnomalyFuelCost,
            key='Game/AnomalyFuelCost',
            restart=False,
            default=0,
            min=0))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.UseAnomalyBerthing,
            key='Game/UseAnomalyBerthing',
            restart=False,
            default=False))
        self._addConfigItem(IntConfigItem(
            option=ConfigOption.AnomalyBerthingCost,
            key='Game/AnomalyBerthingCost',
            restart=False,
            default=0,
            min=0))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.IncludeStartBerthing,
            key='Game/IncludeStartBerthing',
            restart=False,
            default=False))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.IncludeFinishBerthing,
            key='Game/IncludeFinishBerthing',
            restart=False,
            default=True))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.IncludeLogisticsCosts,
            key='Game/IncludeLogisticsCosts',
            restart=False,
            default=True))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.IncludeUnprofitableTrades,
            key='Game/IncludeUnprofitableTrades',
            restart=False,
            default=False))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.ColourTheme,
            key='GUI/ColourTheme',
            restart=True,
            # TODO: The ColourTheme should be moved to this .py file
            enumType=ColourTheme,
            default=ColourTheme.DarkMode))
        self._addConfigItem(FloatConfigItem(
            option=ConfigOption.InterfaceScale,
            key='GUI/InterfaceScale',
            restart=True,
            default=1,
            min=1,
            max=4))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.ShowToolTipImages,
            key='GUI/ShowToolTipImages',
            restart=False,
            default=True))
        self._addConfigItem(OutcomeColoursConfigItem(
            option=ConfigOption.OutcomeColours,
            section='GUI',
            restart=False))

        colourTheme = self.value(option=ConfigOption.ColourTheme)
        isDarkMode = colourTheme is ColourTheme.DarkMode or \
            (colourTheme is ColourTheme.UseOSSetting and darkdetect.isDark())
        self._addConfigItem(ColourConfigItem(
            option=ConfigOption.DesirableTagColour,
            key='Tagging/DesirableTagColour',
            restart=False,
            default='#8000AA00' if isDarkMode else '#808CD47E'))
        self._addConfigItem(ColourConfigItem(
            option=ConfigOption.WarningTagColour,
            key='Tagging/WarningTagColour',
            restart=False,
            default='#80FF7700' if isDarkMode else '#80994700'))
        self._addConfigItem(ColourConfigItem(
            option=ConfigOption.DangerTagColour,
            key='Tagging/DangerTagColour',
            restart=False,
            default='#80BC2023' if isDarkMode else '#80FF6961'))

        self._addConfigItem(EnumTaggingConfigItem(
            option=ConfigOption.ZoneTagging,
            section='ZoneTagging',
            restart=False,
            enumType=traveller.ZoneType,
            default={
                traveller.ZoneType.AmberZone: app.TagLevel.Warning,
                traveller.ZoneType.RedZone: app.TagLevel.Danger,
                traveller.ZoneType.Unabsorbed: app.TagLevel.Warning,
                traveller.ZoneType.Forbidden: app.TagLevel.Danger}))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.StarPortTagging,
            section='StarPortTagging',
            restart=False,
            default={'X': app.TagLevel.Warning}))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.WorldSizeTagging,
            section='WorldSizeTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.AtmosphereTagging,
            section='AtmosphereTagging',
            restart=False,
            default={
                # Tag corrosive and insidious atmospheres
                'B': app.TagLevel.Danger,
                'C': app.TagLevel.Danger}))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.HydrographicsTagging,
            section='HydrographicsTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.PopulationTagging,
            section='PopulationTagging',
            restart=False,
            default={
                # Tag worlds with less than 100 people
                '0': app.TagLevel.Danger,
                '1': app.TagLevel.Warning,
                '2': app.TagLevel.Warning}))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.GovernmentTagging,
            section='GovernmentTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.LawLevelTagging,
            section='LawLevelTagging',
            restart=False,
            default={'0': app.TagLevel.Danger}))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.TechLevelTagging,
            section='TechLevelTagging',
            restart=False))
        self._addConfigItem(EnumTaggingConfigItem(
            option=ConfigOption.BaseTypeTagging,
            section='BaseTypeTagging',
            restart=False,
            enumType=traveller.BaseType))
        self._addConfigItem(EnumTaggingConfigItem(
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
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.ResourcesTagging,
            section='ResourcesTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.LabourTagging,
            section='LabourTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.InfrastructureTagging,
            section='InfrastructureTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.EfficiencyTagging,
            section='EfficiencyTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.HeterogeneityTagging,
            section='HeterogeneityTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.AcceptanceTagging,
            section='AcceptanceTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.StrangenessTagging,
            section='StrangenessTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.SymbolsTagging,
            section='SymbolsTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.SymbolsTagging,
            section='SymbolsTagging',
            restart=False))
        self._addConfigItem(EnumTaggingConfigItem(
            option=ConfigOption.NobilityTagging,
            section='NobilityTagging',
            restart=False,
            enumType=traveller.NobilityType))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.AllegianceTagging,
            section='AllegianceTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.SpectralTagging,
            section='SpectralTagging',
            restart=False))
        self._addConfigItem(StringTaggingConfigItem(
            option=ConfigOption.LuminosityTagging,
            section='LuminosityTagging',
            restart=False))

    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.LogLevel], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.Milieu], futureValue: bool = False) -> travellermap.Milieu: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapStyle], futureValue: bool = False) -> travellermap.Style: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapOptions], futureValue: bool = False) -> typing.Collection[travellermap.Option]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapEngine], futureValue: bool = False) -> MapEngine: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapRendering], futureValue: bool = False) -> MapRendering: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapAnimations], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyPort], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyHostPoolSize], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyMapUrl], futureValue: bool = False) -> str: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyTileCacheSize], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyTileCacheLifetime], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ProxyTileCacheLifetime], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.Rules], futureValue: bool = False) -> traveller.Rules: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.PlayerBrokerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipTonnage], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipJumpRating], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipCargoCapacity], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipFuelCapacity], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipCurrentFuel], futureValue: bool = False) -> float: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseShipFuelPerParsec], futureValue: bool = False) -> float: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseShipFuelPerParsec], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipFuelPerParsec], futureValue: bool = False) -> float: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.PerJumpOverhead], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AvailableFunds], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MinSellerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MaxSellerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MinBuyerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MaxBuyerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UsePurchaseBroker], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.PurchaseBrokerDmBonus], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseSaleBroker], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.SaleBrokerDmBonus], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.RoutingType], futureValue: bool = False) -> logic.RoutingType: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.RouteOptimisation], futureValue: bool = False) -> logic.RouteOptimisation: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.RefuellingStrategy], futureValue: bool = False) -> logic.RefuellingStrategy: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseFuelCaches], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseAnomalyRefuelling], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AnomalyFuelCost], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.UseAnomalyBerthing], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AnomalyBerthingCost], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.IncludeStartBerthing], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.IncludeFinishBerthing], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.IncludeLogisticsCosts], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.IncludeUnprofitableTrades], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ColourTheme], futureValue: bool = False) -> ColourTheme: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.InterfaceScale], futureValue: bool = False) -> float: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShowToolTipImages], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.OutcomeColours], futureValue: bool = False) -> app.OutcomeColours: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.DesirableTagColour], futureValue: bool = False) -> str: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.WarningTagColour], futureValue: bool = False) -> str: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.DangerTagColour], futureValue: bool = False) -> str: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ZoneTagging], futureValue: bool = False) -> typing.Mapping[traveller.ZoneType, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.StarPortTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AtmosphereTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.HydrographicsTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.PopulationTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.GovernmentTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.LawLevelTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.TechLevelTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.BaseTypeTagging], futureValue: bool = False) -> typing.Mapping[traveller.BaseType, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.TradeCodeTagging], futureValue: bool = False) -> typing.Mapping[traveller.TradeCode, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ResourcesTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.LabourTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.InfrastructureTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.EfficiencyTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.HeterogeneityTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AcceptanceTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.StrangenessTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.SymbolsTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.SymbolsTagging], futureValue: bool = False) -> typing.Mapping[traveller.NobilityType, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.AllegianceTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.SpectralTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.LuminosityTagging], futureValue: bool = False) -> typing.Mapping[str, app.TagLevel]: ...

    def value(
            self,
            option: ConfigOption,
            futureValue: bool = False
            ) -> typing.Any:
        item = self._configItems[option]
        return item.value(futureValue=futureValue)

    def setValue(
            self,
            option: ConfigOption,
            value: typing.Any
            ) -> bool:
        item = self._configItems[option]

        oldValue = item.value()
        item.setValue(value=value)
        newValue = item.value()

        # Do a write even if the value "hasn't changed" as the change
        # comparison is based on the current value but it's the future
        # value that will be written
        item.write(self._settings)

        if newValue == oldValue:
            return False

        self.configChanged.emit(option, oldValue, newValue)
        return True

    def isRestartRequired(self) -> bool:
        for item in self._configItems.values():
            if item.isRestartRequired():
                return True
        return False

    def _addConfigItem(self, item: ConfigItem) -> None:
        Config._configItems[item.option()] = item
        try:
            item.read(settings=self._settings)
        except Exception as ex:
            logging.warning(f'Failed to read config option {item.option().name}', exc_info=ex)
