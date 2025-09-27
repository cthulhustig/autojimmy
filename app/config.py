import app
import cartographer
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
import multiverse
import typing
from PyQt5 import QtCore

# NOTE: If I ever change the name of these enums I'll need some mapping
# as they're written to the config file. This only applies to the name
# not the value
class ColourTheme(enum.Enum):
    DarkMode = 'Dark Mode'
    LightMode = 'Light Mode'
    UseOSSetting = 'Use OS Setting'

class ConfigOption(enum.Enum):
    # Debug
    LogLevel = 100

    # Map
    Milieu = 200
    MapStyle = 201
    MapOptions = 202
    MapRendering = 204
    MapAnimations = 205

    # Game
    Rules = 500
    PlayerBrokerDM = 501
    ShipTonnage = 502
    ShipJumpRating = 503
    ShipFuelCapacity = 504
    ShipCurrentFuel = 505
    UseShipFuelPerParsec = 506
    ShipFuelPerParsec = 507
    PerJumpOverhead = 508
    AvailableFunds = 509
    MaxCargoTonnage = 510
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
    ShowUnprofitableTrades = 530

    # UI
    ColourTheme = 600
    InterfaceScale = 601
    OutcomeColours = 602

    WorldTagging = 700
    TaggingColours = 701

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
        app.MapOption.GalacticDirections: '/GalacticDirections',
        app.MapOption.SectorGrid: '/SectorGrid',
        app.MapOption.SelectedSectorNames: '/SelectedSectorNames',
        app.MapOption.AllSectorNames: '/AllSectorNames',
        app.MapOption.Borders: '/Borders',
        app.MapOption.Routes: '/Routes',
        app.MapOption.RegionNames: '/RegionNames',
        app.MapOption.ImportantWorlds: '/ImportantWorlds',
        app.MapOption.WorldColours: '/WorldColours',
        app.MapOption.FilledBorders: '/FilledBorders',
        app.MapOption.DimUnofficial: '/DimUnofficial',
        app.MapOption.ImportanceOverlay: '/ImportanceOverlay',
        app.MapOption.PopulationOverlay: '/PopulationOverlay',
        app.MapOption.CapitalsOverlay: '/CapitalsOverlay',
        app.MapOption.MinorRaceOverlay: '/MinorRaceOverlay',
        app.MapOption.DroyneWorldOverlay: '/DroyneWorldOverlay',
        app.MapOption.AncientSitesOverlay: '/AncientSitesOverlay',
        app.MapOption.StellarOverlay: '/StellarOverlay',
        app.MapOption.EmpressWaveOverlay: '/EmpressWaveOverlay',
        app.MapOption.QrekrshaZoneOverlay: '/QrekrshaZoneOverlay',
        app.MapOption.AntaresSupernovaOverlay: '/AntaresSupernovaOverlay',
        app.MapOption.MainsOverlay: '/MainsOverlay'
    }

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            default: typing.Iterable[app.MapOption] = None
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._default = set(default) if default else set()
        self._currentValue = self._futureValue = self._default

    def value(self, futureValue: bool = False) -> typing.Iterable[app.MapOption]:
        return list(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: typing.Iterable[app.MapOption]) -> None:
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
            restart: bool,
            default: traveller.Rules
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._default = traveller.Rules(default)
        self._currentValue = self._futureValue = self._default

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
            self._default.system()

        classAFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassAFuelTypeKey,
            default=None,
            type=str)
        classAFuelType = \
            traveller.StarPortFuelType.__members__[classAFuelType] \
            if classAFuelType in traveller.StarPortFuelType.__members__ else \
            self._default.starPortFuelType(code='A')

        classBFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassBFuelTypeKey,
            default=None,
            type=str)
        classBFuelType = \
            traveller.StarPortFuelType.__members__[classBFuelType] \
            if classBFuelType in traveller.StarPortFuelType.__members__ else \
            self._default.starPortFuelType(code='B')

        classCFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassCFuelTypeKey,
            default=None,
            type=str)
        classCFuelType = \
            traveller.StarPortFuelType.__members__[classCFuelType] \
            if classCFuelType in traveller.StarPortFuelType.__members__ else \
            self._default.starPortFuelType(code='C')

        classDFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassDFuelTypeKey,
            default=None,
            type=str)
        classDFuelType = \
            traveller.StarPortFuelType.__members__[classDFuelType] \
            if classDFuelType in traveller.StarPortFuelType.__members__ else \
            self._default.starPortFuelType(code='D')

        classEFuelType = self.loadConfigSetting(
            settings=settings,
            key=self._section + RulesConfigItem._ClassEFuelTypeKey,
            default=None,
            type=str)
        classEFuelType = \
            traveller.StarPortFuelType.__members__[classEFuelType] \
            if classEFuelType in traveller.StarPortFuelType.__members__ else \
            self._default.starPortFuelType(code='E')

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
    _AverageCaseKey = '/AverageCaseColour'
    _WorstCaseKey = '/WorstCaseColour'
    _BestCaseKey = '/BestCaseColour'

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            restart: bool,
            default: app.OutcomeColours
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._default = app.OutcomeColours(default)
        self._currentValue = self._futureValue = self._default

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
            default=self._default.colour(logic.RollOutcome.AverageCase),
            type=str)

        worstCaseColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + OutcomeColoursConfigItem._WorstCaseKey,
            default=self._default.colour(logic.RollOutcome.WorstCase),
            type=str)

        bestCaseColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + OutcomeColoursConfigItem._BestCaseKey,
            default=self._default.colour(logic.RollOutcome.BestCase),
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
            default: typing.Optional[typing.Mapping[typing.Any, logic.TagLevel]],
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

    def setValue(self, value: typing.Mapping[typing.Any, logic.TagLevel]) -> None:
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
                        if value not in logic.TagLevel.__members__:
                            logging.warning(f'Ignoring tag map for "{key}" in section {self._section} as "{value}" is not a valid tag level')
                            continue
                        values[key] = logic.TagLevel.__members__[value]
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
            default: typing.Optional[typing.Mapping[str, logic.TagLevel]] = None,
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
            default: typing.Optional[typing.Mapping[enum.Enum, logic.TagLevel]] = None,
            ) -> None:
        super().__init__(
            option=option,
            section=section,
            restart=restart,
            default=default,
            keyToStringCb=lambda e: e.name,
            keyFromStringCb=lambda s: enumType.__members__[s] if s in enumType.__members__ else None)

class TaggingColoursConfigItem(ConfigItem):
    _DesirableKey = '/AverageCaseColour'
    _WarningKey = '/WorstCaseColour'
    _DangerKey = '/BestCaseColour'

    def __init__(
            self,
            option: ConfigOption,
            section: str,
            default: app.TaggingColours,
            restart: bool
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._section = section
        self._default = app.TaggingColours(default)
        self._currentValue = self._futureValue = self._default

    def value(self, futureValue: bool = False) -> typing.Any:
        return app.TaggingColours(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: app.TaggingColours) -> None:
        if value == self._futureValue:
            return

        value = app.TaggingColours(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings: QtCore.QSettings) -> None:
        desirableColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + TaggingColoursConfigItem._DesirableKey,
            default=self._default.colour(level=logic.TagLevel.Desirable),
            type=str)

        warningColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + TaggingColoursConfigItem._WarningKey,
            default=self._default.colour(level=logic.TagLevel.Warning),
            type=str)

        dangerColour = self.loadConfigSetting(
            settings=settings,
            key=self._section + TaggingColoursConfigItem._DangerKey,
            default=self._default.colour(level=logic.TagLevel.Danger),
            type=str)

        self._currentValue = self._futureValue = app.TaggingColours(
            desirableColour=desirableColour,
            warningColour=warningColour,
            dangerColour=dangerColour)

    def write(self, settings: QtCore.QSettings) -> None:
        settings.setValue(
            self._section + TaggingColoursConfigItem._DesirableKey,
            self._futureValue.colour(logic.TagLevel.Desirable))
        settings.setValue(
            self._section + TaggingColoursConfigItem._WarningKey,
            self._futureValue.colour(logic.TagLevel.Warning))
        settings.setValue(
            self._section + TaggingColoursConfigItem._DangerKey,
            self._futureValue.colour(logic.TagLevel.Danger))

class WorldTaggingConfigItem(ConfigItem):
    _PropertyConfig = [
        ('ZoneTagging', multiverse.ZoneType, logic.TaggingProperty.Zone),
        ('StarPortTagging', str, logic.TaggingProperty.StarPort),
        ('WorldSizeTagging', str, logic.TaggingProperty.WorldSize),
        ('AtmosphereTagging', str, logic.TaggingProperty.Atmosphere),
        ('HydrographicsTagging', str, logic.TaggingProperty.Hydrographics),
        ('PopulationTagging', str, logic.TaggingProperty.Population),
        ('GovernmentTagging', str, logic.TaggingProperty.Government),
        ('LawLevelTagging', str, logic.TaggingProperty.LawLevel),
        ('TechLevelTagging', str, logic.TaggingProperty.TechLevel),
        ('BaseTypeTagging', multiverse.BaseType, logic.TaggingProperty.BaseType),
        ('TradeCodeTagging', multiverse.TradeCode, logic.TaggingProperty.TradeCode),
        ('ResourcesTagging', str, logic.TaggingProperty.Resources),
        ('LabourTagging', str, logic.TaggingProperty.Labour),
        ('InfrastructureTagging', str, logic.TaggingProperty.Infrastructure),
        ('EfficiencyTagging', str, logic.TaggingProperty.Efficiency),
        ('HeterogeneityTagging', str, logic.TaggingProperty.Heterogeneity),
        ('AcceptanceTagging', str, logic.TaggingProperty.Acceptance),
        ('StrangenessTagging', str, logic.TaggingProperty.Strangeness),
        ('SymbolsTagging', str, logic.TaggingProperty.Symbols),
        ('NobilityTagging', multiverse.NobilityType, logic.TaggingProperty.Nobility),
        ('AllegianceTagging', str, logic.TaggingProperty.Allegiance),
        ('SpectralTagging', str, logic.TaggingProperty.Spectral),
        ('LuminosityTagging', str, logic.TaggingProperty.Luminosity)]

    _SettingIndexFixPattern = re.compile('.*[\\/]')

    def __init__(
            self,
            option: ConfigOption,
            restart: bool,
            default: typing.Optional[logic.WorldTagging]
            ) -> None:
        super().__init__(option=option, restart=restart)
        self._default = logic.WorldTagging(default) if default else logic.WorldTagging()
        self._currentValue = self._futureValue = self._default

    def value(self, futureValue: bool = False) -> typing.Any:
        return logic.WorldTagging(self._futureValue if futureValue else self._currentValue)

    def setValue(self, value: logic.WorldTagging) -> None:
        if value == self._futureValue:
            return

        value = logic.WorldTagging(value)
        if self._restart:
            self._futureValue = value
        else:
            self._currentValue = self._futureValue = value

    def isRestartRequired(self) -> bool:
        return self._currentValue != self._futureValue

    def read(self, settings):
        config = {}
        useDefault = True
        for section, type, property in WorldTaggingConfigItem._PropertyConfig:
            if issubclass(type, enum.Enum):
                keyFromStringCb = lambda s: type.__members__[s] if s in type.__members__ else None
            else:
                keyFromStringCb = lambda s: s

            propertyConfig = self._readProperty(
                settings=settings,
                section=section,
                keyFromStringCb=keyFromStringCb)
            if propertyConfig is not None:
                # There was a section present in the settings. This doesn't necessarily
                # mean it has an have any tag values set, but it does mean the config
                # has been changed so we shouldn't use the default
                useDefault = False

            if propertyConfig:
                config[property] = propertyConfig

        self._currentValue = self._futureValue = self._default if useDefault else logic.WorldTagging(config=config)

    def write(self, settings):
        config = self._futureValue.config()
        for section, type, property in WorldTaggingConfigItem._PropertyConfig:
            if issubclass(type, enum.Enum):
                keyToStringCb = lambda e: e.name
            else:
                keyToStringCb = lambda s: s

            propertyConfig = config.get(property)

            self._writeProperty(
                settings=settings,
                section=section,
                values=propertyConfig,
                keyToStringCb=keyToStringCb)

    def _readProperty(
            self,
            settings: QtCore.QSettings,
            section: str,
            keyFromStringCb: typing.Callable[[str], typing.Optional[typing.Any]]
            ) -> typing.Optional[typing.Dict[typing.Any, logic.TagLevel]]:
        # Check to see if there is a size element for this section. This is a hack
        # to differentiate between there being no section and there being a section
        # with no entries. The distinction is important as we want to use the
        # default configuration if there is no section but not if there is a section
        # with no entries as the user must have configured it like that.
        if not settings.contains(section + '/size'):
            return None

        values = {}
        settings.beginReadArray(section)
        try:
            for settingKey in settings.allKeys():
                if settingKey == 'size':
                    continue

                # Strip of the index that QSettings puts on array elements. For reasons I don't understand it's
                # not consistent with which separator it uses
                key = keyFromStringCb(TaggingConfigItem._SettingIndexFixPattern.sub('', settingKey))
                if key is None:
                    logging.warning(f'Ignoring tag map for "{key}" in section {section} as "{key}" is not a valid key')
                    continue

                value = settings.value(settingKey, defaultValue=None, type=str)
                if value:
                    if value not in logic.TagLevel.__members__:
                        logging.warning(f'Ignoring tag map for "{key}" in section {section} as "{value}" is not a valid tag level')
                        continue
                    values[key] = logic.TagLevel.__members__[value]
        finally:
            settings.endArray()

        return values

    def _writeProperty(
            self,
            settings: QtCore.QSettings,
            section: str,
            values: typing.Optional[typing.Dict[typing.Any, logic.TagLevel]],
            keyToStringCb: typing.Callable[[typing.Any], str]
            ) -> None:
        settings.remove(section)
        # Always write the array even if there are no values, otherwise it's not possible
        # to completely remove all tagging as it will revert to the default
        settings.beginWriteArray(section)
        try:
            if values:
                for index, (key, tagLevel) in enumerate(values.items()):
                    if tagLevel == None:
                        continue
                    settings.setArrayIndex(index)
                    settings.setValue(keyToStringCb(key), tagLevel.name)
        finally:
            settings.endArray()

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
            restart=False,
            enumType=multiverse.Milieu,
            default=multiverse.Milieu.M1105))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.MapStyle,
            key='TravellerMap/MapStyle',
            restart=False,
            enumType=cartographer.MapStyle,
            default=cartographer.MapStyle.Poster))
        self._addConfigItem(MapOptionsConfigItem(
            option=ConfigOption.MapOptions,
            section='TravellerMap',
            restart=False,
            default=[
                app.MapOption.GalacticDirections,
                app.MapOption.SectorGrid,
                app.MapOption.SelectedSectorNames,
                app.MapOption.Borders,
                app.MapOption.Routes,
                app.MapOption.RegionNames,
                app.MapOption.ImportantWorlds,
                app.MapOption.FilledBorders]))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.MapRendering,
            key='TravellerMap/MapRenderingType',
            restart=False,
            enumType=app.MapRendering,
            default=app.MapRendering.Tiled))
        self._addConfigItem(BoolConfigItem(
            option=ConfigOption.MapAnimations,
            key='TravellerMap/MapAnimations',
            restart=False,
            default=True))

        self._addConfigItem(RulesConfigItem(
            option=ConfigOption.Rules,
            section='Game',
            default=traveller.Rules(
                system=traveller.RuleSystem.MGT2022,
                classAStarPortFuelType=traveller.StarPortFuelType.AllTypes,
                classBStarPortFuelType=traveller.StarPortFuelType.AllTypes,
                classCStarPortFuelType=traveller.StarPortFuelType.UnrefinedOnly,
                classDStarPortFuelType=traveller.StarPortFuelType.UnrefinedOnly,
                classEStarPortFuelType=traveller.StarPortFuelType.NoFuel),
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
            # NOTE: Setting the default like this assumes the ShipTonnage option
            # has already been added
            default=self.value(option=ConfigOption.ShipTonnage) * 0.1, # 10% of ship tonnage
            # NOTE: The min value is pretty arbitrary, it needs to allow the user to
            # fake "hop-3" by setting the jump rating to 10 times a normal jump
            # drive and setting the fuel per parsec to 1/10th of the fuel per parsec
            # that the ship with that jump rating would normal use
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
            option=ConfigOption.MaxCargoTonnage,
            key='Game/MaxCargoTonnage',
            restart=False,
            default=1,
            min=1))
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
            option=ConfigOption.ShowUnprofitableTrades,
            key='Game/ShowUnprofitableTrades',
            restart=False,
            default=False))

        self._addConfigItem(EnumConfigItem(
            option=ConfigOption.ColourTheme,
            key='GUI/ColourTheme',
            restart=True,
            enumType=ColourTheme,
            default=ColourTheme.DarkMode))
        self._addConfigItem(FloatConfigItem(
            option=ConfigOption.InterfaceScale,
            key='GUI/InterfaceScale',
            restart=True,
            default=1,
            min=1,
            max=4))
        self._addConfigItem(OutcomeColoursConfigItem(
            option=ConfigOption.OutcomeColours,
            section='GUI',
            default=app.OutcomeColours(
                averageCaseColour='#0A0000FF',
                worstCaseColour='#0AFF0000',
                bestCaseColour='#0A00FF00'),
            restart=False))

        colourTheme = self.value(option=ConfigOption.ColourTheme)
        isDarkMode = colourTheme is ColourTheme.DarkMode or \
            (colourTheme is ColourTheme.UseOSSetting and darkdetect.isDark())

        self._addConfigItem(TaggingColoursConfigItem(
            option=ConfigOption.TaggingColours,
            section='Tagging',
            default=app.TaggingColours(
                desirableColour='#80007A00' if isDarkMode else '#808CD47E',
                warningColour='#808F4F00' if isDarkMode else '#80994700',
                dangerColour='#8087171A' if isDarkMode else '#80FF6961'),
            restart=False))
        self._addConfigItem(WorldTaggingConfigItem(
            option=ConfigOption.WorldTagging,
            restart=False,
            default=logic.WorldTagging(
                config={
                    logic.TaggingProperty.Zone: {
                        multiverse.ZoneType.AmberZone: logic.TagLevel.Warning,
                        multiverse.ZoneType.RedZone: logic.TagLevel.Danger,
                        multiverse.ZoneType.Unabsorbed: logic.TagLevel.Warning,
                        multiverse.ZoneType.Forbidden: logic.TagLevel.Danger},
                    logic.TaggingProperty.StarPort: {
                        'X': logic.TagLevel.Warning},
                    logic.TaggingProperty.Atmosphere: {
                        # Tag corrosive and insidious atmospheres
                        'B': logic.TagLevel.Danger,
                        'C': logic.TagLevel.Danger},
                    logic.TaggingProperty.Population: {
                        # Tag worlds with less than 100 people
                        '0': logic.TagLevel.Warning,
                        '1': logic.TagLevel.Warning,
                        '2': logic.TagLevel.Warning},
                    logic.TaggingProperty.LawLevel: {
                        '0': logic.TagLevel.Danger},
                    logic.TaggingProperty.TradeCode: {
                        multiverse.TradeCode.AmberZone: logic.TagLevel.Warning,
                        multiverse.TradeCode.RedZone: logic.TagLevel.Danger,
                        multiverse.TradeCode.HellWorld: logic.TagLevel.Danger,
                        multiverse.TradeCode.PenalColony: logic.TagLevel.Danger,
                        multiverse.TradeCode.PrisonCamp: logic.TagLevel.Danger,
                        multiverse.TradeCode.Reserve: logic.TagLevel.Danger,
                        multiverse.TradeCode.DangerousWorld: logic.TagLevel.Danger,
                        multiverse.TradeCode.ForbiddenWorld: logic.TagLevel.Danger}
                })))

    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.LogLevel], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.Milieu], futureValue: bool = False) -> multiverse.Milieu: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapStyle], futureValue: bool = False) -> cartographer.MapStyle: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapOptions], futureValue: bool = False) -> typing.Collection[app.MapOption]: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapRendering], futureValue: bool = False) -> app.MapRendering: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MapAnimations], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.Rules], futureValue: bool = False) -> traveller.Rules: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.PlayerBrokerDM], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipTonnage], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ShipJumpRating], futureValue: bool = False) -> int: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.MaxCargoTonnage], futureValue: bool = False) -> int: ...
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
    def value(self, option: typing.Literal[ConfigOption.ShowUnprofitableTrades], futureValue: bool = False) -> bool: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.ColourTheme], futureValue: bool = False) -> ColourTheme: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.InterfaceScale], futureValue: bool = False) -> float: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.OutcomeColours], futureValue: bool = False) -> app.OutcomeColours: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.TaggingColours], futureValue: bool = False) -> app.TaggingColours: ...
    @typing.overload
    def value(self, option: typing.Literal[ConfigOption.WorldTagging], futureValue: bool = False) -> logic.WorldTagging: ...

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
