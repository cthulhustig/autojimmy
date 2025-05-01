import app
import common
import darkdetect
import enum
import logging
import logic
import os
import re
import threading
import traveller
import travellermap
import typing
import urllib
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

class MapRenderingType(enum.Enum):
    Tiled = 'Tiled' # Tiles rendered in background (i.e. the same as Traveller Map)
    Hybrid = 'Hybrid' # Tiles rendered in foreground
    Full = 'Full' # Entire frame rendered each redraw and no digital zoom between log zoom levels

class Config(object):
    _ConfigFileName = 'autojimmy.ini'

    _LogLevelKeyName = 'Debug/LogLevel'
    _MilieuKeyName = 'TravellerMap/Milieu'
    _MapStyleKeyName = 'TravellerMap/MapStyle'
    _MapEngineTypeKeyName = 'TravellerMap/MapEngine'
    _MapRenderingTypeKeyName = 'TravellerMap/MapRenderingType'
    _MapAnimationsKeyName = 'TravellerMap/MapAnimations'

    _ProxyEnabledKeyName = 'Proxy/Enabled'
    _ProxyPortKeyName = 'Proxy/Port'
    _ProxyHostPoolSizeKeyName = 'Proxy/HostPoolSize'
    _ProxyMapUrlKeyName = 'Proxy/MapUrl'
    _ProxyTileCacheSizeKeyName = 'Proxy/TileCacheSize'
    _ProxyTileCacheLifetimeKeyName = 'Proxy/TileCacheLifetime'
    _ProxySvgCompositionKeyName = 'Proxy/SvgComposition'

    _RuleSystemKeyName = 'Game/Rules' # NOTE: This name isn't ideal but it is what it is for backwards compatibility
    _RuleClassAFuelTypeKeyName = 'Game/ClassAFuelTypeRule'
    _RuleClassBFuelTypeKeyName = 'Game/ClassBFuelTypeRule'
    _RuleClassCFuelTypeKeyName = 'Game/ClassCFuelTypeRule'
    _RuleClassDFuelTypeKeyName = 'Game/ClassDFuelTypeRule'
    _RuleClassEFuelTypeKeyName = 'Game/ClassEFuelTypeRule'
    _PlayerBrokerDmKeyName = 'Game/PlayerBrokerDM'
    _ShipTonnageKeyName = 'Game/ShipTonnage'
    _ShipJumpRatingKeyName = 'Game/ShipJumpRating'
    _ShipCargoCapacityKeyName = 'Game/ShipCargoCapacity'
    _ShipFuelCapacityKeyName = 'Game/ShipFuelCapacity'
    _ShipCurrentFuelKeyName = 'Game/ShipCurrentFuel'
    _UseShipFuelPerParsecKeyName = 'Game/UseShipFuelPerParsec'
    _ShipFuelPerParsecKeyName = 'Game/ShipFuelPerParsec'
    _PerJumpOverheadKeyName = 'Game/PerJumpOverhead'
    _AvailableFundsKeyName = 'Game/AvailableFunds'
    _MinSellerDmKeyName = 'Game/MinSellerDM'
    _MaxSellerDmKeyName = 'Game/MaxSellerDM'
    _MinBuyerDmKeyName = 'Game/MinBuyerDM'
    _MaxBuyerDmKeyName = 'Game/MaxBuyerDM'
    _UsePurchaseBrokerKeyName = 'Game/UsePurchaseBroker'
    _PurchaseBrokerDmBonusKeyName = 'Game/PurchaseBrokerDmBonus'
    _UseSaleBrokerKeyName = 'Game/UseSaleBroker'
    _SaleBrokerDmBonusKeyName = 'Game/SaleBrokerDmBonus'
    _RoutingTypeKeyName = 'Game/RoutingType'
    _RouteOptimisationKeyName = 'Game/RouteOptimisation'
    _RefuellingStrategyKeyName = 'Game/RefuellingStrategy'
    _UseFuelCachesKeyName = 'Game/UseFuelCaches'
    _UseAnomalyRefuellingKeyName = 'Game/UseAnomalyRefuelling'
    _AnomalyFuelCostKeyName = 'Game/AnomalyFuelCost'
    _UseAnomalyBerthingKeyName = 'Game/UseAnomalyBerthing'
    _AnomalyBerthingCostKeyName = 'Game/AnomalyBerthingCost'
    _IncludeStartBerthingKeyName = 'Game/IncludeStartBerthing'
    _IncludeFinishBerthingKeyName = 'Game/IncludeFinishBerthing'
    _IncludeLogisticsCostsKeyName = 'Game/IncludeLogisticsCosts'
    _IncludeUnprofitableTradesKeyName = 'Game/IncludeUnprofitableTrades'

    _ColourThemeKeyName = 'GUI/ColourTheme'
    _InterfaceScaleKeyName = 'GUI/InterfaceScale'
    _ShowToolTipImagesKeyName = 'GUI/ShowToolTipImages'
    _AverageCaseColourKeyName = 'GUI/AverageCaseColour'
    _WorstCaseColourKeyName = 'GUI/WorstCaseColour'
    _BestCaseColourKeyName = 'GUI/BestCaseColour'

    _ZoneTaggingSectionName = 'ZoneTagging'
    _StarPortTaggingSectionName = 'StarPortTagging'
    _WorldSizeTaggingSectionName = 'WorldSizeTagging'
    _AtmosphereTaggingSectionName = 'AtmosphereTagging'
    _HydrographicsTaggingSectionName = 'HydrographicsTagging'
    _PopulationTaggingSectionName = 'PopulationTagging'
    _GovernmentTaggingSectionName = 'GovernmentTagging'
    _LawLevelTaggingSectionName = 'LawLevelTagging'
    _TechLevelTaggingSectionName = 'TechLevelTagging'
    _BaseTypeTaggingSectionName = 'BaseTypeTagging'
    _TradeCodeTaggingSectionName = 'TradeCodeTagging'
    _ResourcesTaggingSectionName = 'ResourcesTagging'
    _LabourTaggingSectionName = 'LabourTagging'
    _InfrastructureTaggingSectionName = 'InfrastructureTagging'
    _EfficiencyTaggingSectionName = 'EfficiencyTagging'
    _HeterogeneityTaggingSectionName = 'HeterogeneityTagging'
    _AcceptanceTaggingSectionName = 'AcceptanceTagging'
    _StrangenessTaggingSectionName = 'StrangenessTagging'
    _SymbolsTaggingSectionName = 'SymbolsTagging'
    _NobilityTaggingSectionName = 'NobilityTagging'
    _AllegianceTaggingSectionName = 'AllegianceTagging'
    _SpectralTaggingSectionName = 'SpectralTagging'
    _LuminosityTaggingSectionName = 'LuminosityTagging'

    _StringToLogLevel = {
        'critical': logging.CRITICAL,
        'crit': logging.CRITICAL,
        'error': logging.ERROR,
        'err': logging.ERROR,
        'warning': logging.WARNING,
        'warn': logging.WARNING,
        'information': logging.INFO,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'dbg': logging.DEBUG,
    }
    _LogLevelToString = {
        logging.CRITICAL: 'critical',
        logging.ERROR: 'error',
        logging.WARNING: 'warning',
        logging.INFO: 'information',
        logging.DEBUG: 'debug'
    }

    _MapOptionToKeyNameMap = {
        travellermap.Option.GalacticDirections: 'TravellerMap/GalacticDirections',
        travellermap.Option.SectorGrid: 'TravellerMap/SectorGrid',
        travellermap.Option.SelectedSectorNames: 'TravellerMap/SelectedSectorNames',
        travellermap.Option.SectorNames: 'TravellerMap/AllSectorNames',
        travellermap.Option.Borders: 'TravellerMap/Borders',
        travellermap.Option.Routes: 'TravellerMap/Routes',
        travellermap.Option.RegionNames: 'TravellerMap/RegionNames',
        travellermap.Option.ImportantWorlds: 'TravellerMap/ImportantWorlds',
        travellermap.Option.WorldColours: 'TravellerMap/WorldColours',
        travellermap.Option.FilledBorders: 'TravellerMap/FilledBorders',
        travellermap.Option.DimUnofficial: 'TravellerMap/DimUnofficial',
        travellermap.Option.ImportanceOverlay: 'TravellerMap/ImportanceOverlay',
        travellermap.Option.PopulationOverlay: 'TravellerMap/PopulationOverlay',
        travellermap.Option.CapitalsOverlay: 'TravellerMap/CapitalsOverlay',
        travellermap.Option.MinorRaceOverlay: 'TravellerMap/MinorRaceOverlay',
        travellermap.Option.DroyneWorldOverlay: 'TravellerMap/DroyneWorldOverlay',
        travellermap.Option.AncientSitesOverlay: 'TravellerMap/AncientSitesOverlay',
        travellermap.Option.StellarOverlay: 'TravellerMap/StellarOverlay',
        travellermap.Option.EmpressWaveOverlay: 'TravellerMap/EmpressWaveOverlay',
        travellermap.Option.QrekrshaZoneOverlay: 'TravellerMap/QrekrshaZoneOverlay',
        travellermap.Option.AntaresSupernovaOverlay: 'TravellerMap/AntaresSupernovaOverlay',
        travellermap.Option.MainsOverlay: 'TravellerMap/MainsOverlay',
    }

    # Map options that are enabled by default
    _DefaultMapOptions = set([
        travellermap.Option.GalacticDirections,
        travellermap.Option.SectorGrid,
        travellermap.Option.SelectedSectorNames,
        travellermap.Option.Borders,
        travellermap.Option.Routes,
        travellermap.Option.RegionNames,
        travellermap.Option.ImportantWorlds,
        travellermap.Option.FilledBorders,
    ])

    _TagLevelToKeyNameMap = {
        app.TagLevel.Desirable: 'Tagging/DesirableTagColour',
        app.TagLevel.Warning: 'Tagging/WarningTagColour',
        app.TagLevel.Danger: 'Tagging/DangerTagColour',
    }

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _appDir = '.\\'
    _installDir = '.\\'

    def __init__(self):
        raise RuntimeError('Call instance() instead')

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

    def logLevel(self) -> int:
        return self._logLevel

    def setLogLevel(self, logLevel: int) -> bool:
        if logLevel == self._logLevel:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        if logLevel in self._LogLevelToString:
            self._settings.setValue(Config._LogLevelKeyName, self._LogLevelToString[logLevel])
        else:
            self._settings.remove(Config._LogLevelKeyName)

        return True # Restart required

    def mapEngine(self) -> MapEngine:
        return self._mapEngine

    def setMapEngine(self, engine: MapEngine) -> None:
        if engine == self._mapEngine:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._MapEngineTypeKeyName, engine.name)
        return True # Restart required

    # NOTE: This is called every time LocalMapWidget draws the view so it needs
    # to be quick
    def mapRenderingType(self) -> MapRenderingType:
        return self._mapRenderingType

    def setMapRenderingType(self, type: MapRenderingType) -> None:
        self._mapRenderingType = type
        self._settings.setValue(Config._MapRenderingTypeKeyName, type.name)
        return False # No restart required

    def mapAnimations(self) -> bool:
        return self._mapAnimations

    def setMapAnimations(self, enabled: bool) -> bool:
        self._mapAnimations = enabled
        self._settings.setValue(Config._MapAnimationsKeyName, enabled)
        return False # No restart required

    def proxyPort(self) -> int:
        return self._proxyPort

    def setProxyPort(
            self,
            port: int
            ) -> None:
        if port == self._proxyPort:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxyPortKeyName, port)
        return True # Restart required

    # Number of loopback addresses to listen on to work around 6 connection per
    # host limit
    def proxyHostPoolSize(self) -> int:
        return self._proxyHostPoolSize

    def setProxyHostPoolSize(self, size: int) -> bool:
        if size == self._proxyHostPoolSize:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxyHostPoolSizeKeyName, size)
        return True # Restart required

    # The Traveller Map URL used by the proxy
    def proxyMapUrl(self) -> str:
        return self._proxyMapUrl

    def setProxyMapUrl(self, url: str) -> bool:
        if url == self._proxyMapUrl:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxyMapUrlKeyName, url)
        return True # Restart required

    # Size of tile cache in bytes
    def proxyTileCacheSize(self) -> int:
        return self._proxyTileCacheSize

    def setProxyTileCacheSize(self, size: int) -> bool:
        if size == self._proxyTileCacheSize:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxyTileCacheSizeKeyName, size)
        return True # Restart required

    # Lifetime of cache entries in days
    def proxyTileCacheLifetime(self) -> int:
        return self._proxyTileCacheLifetime

    def setProxyTileCacheLifetime(self, days: int) -> bool:
        if days == self._proxyTileCacheLifetime:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxyTileCacheLifetimeKeyName, days)
        return True # Restart required

    def proxySvgCompositionEnabled(self) -> bool:
        return self._proxySvgComposition

    def setProxySvgCompositionEnabled(self, enabled) -> bool:
        if enabled == self._proxySvgComposition:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ProxySvgCompositionKeyName, enabled)
        return True # Restart required

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> bool:
        if milieu == self._milieu:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._MilieuKeyName, milieu.name)
        return True # Restart required

    def mapStyle(self) -> travellermap.Style:
        return self._mapStyle

    def setMapStyle(self, style: travellermap.Style) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._mapStyle = style
        self._settings.setValue(Config._MapStyleKeyName, style.name)
        return False # No restart required

    def mapOptions(self) -> typing.Iterable[travellermap.Option]:
        return set(self._mapOptions)

    def mapOption(
            self,
            option: travellermap.Option
            ) -> bool:
        return option in self._mapOptions

    def setMapOption(
            self,
            option: travellermap.Option,
            enabled: bool
            ) -> bool:
        key = Config._MapOptionToKeyNameMap.get(option)
        if not key:
            return False

        # This setting can be modified live so update the internal and disk copy
        if enabled:
            self._mapOptions.add(option)
        elif option in self._mapOptions:
            self._mapOptions.remove(option)

        self._settings.setValue(key, enabled)
        return False

    def setMapOptions(self, options: typing.Iterable[travellermap.Option]) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._mapOptions = set(options) # Take copy to prevent list being modified externally
        for option, key in Config._MapOptionToKeyNameMap.items():
            self._settings.setValue(key, option in self._mapOptions)
        return False # No restart required

    def rules(self) -> traveller.Rules:
        return self._rules

    def setRules(self, rules: traveller.Rules) -> bool:
        if rules == self._rules:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(
            Config._RuleSystemKeyName,
            rules.system().name)

        fuelTypes = (
            ('A', Config._RuleClassAFuelTypeKeyName),
            ('B', Config._RuleClassBFuelTypeKeyName),
            ('C', Config._RuleClassCFuelTypeKeyName),
            ('D', Config._RuleClassDFuelTypeKeyName),
            ('E', Config._RuleClassEFuelTypeKeyName))
        for code, key in fuelTypes:
            fuelType = rules.starPortFuelType(code=code)
            if fuelType:
                self._settings.setValue(key, fuelType.name)
        return True # Restart required

    def playerBrokerDm(self) -> int:
        return self._playerBrokerDm

    def setPlayerBrokerDm(self, skill: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._playerBrokerDm = skill
        self._settings.setValue(Config._PlayerBrokerDmKeyName, skill)
        return False # No restart required

    def shipTonnage(self) -> int:
        return self._shipTonnage

    def setShipTonnage(self, tonnage: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._shipTonnage = tonnage
        self._settings.setValue(Config._ShipTonnageKeyName, tonnage)
        return False # No restart required

    def shipJumpRating(self) -> int:
        return self._shipJumpRating

    def setShipJumpRating(self, rating: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._shipJumpRating = rating
        self._settings.setValue(Config._ShipJumpRatingKeyName, rating)
        return False # No restart required

    def shipCargoCapacity(self) -> int:
        return self._shipCargoCapacity

    def setShipCargoCapacity(self, tonnage: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._shipCargoCapacity = tonnage
        self._settings.setValue(Config._ShipCargoCapacityKeyName, tonnage)
        return False # No restart required

    def shipFuelCapacity(self) -> int:
        return self._shipFuelCapacity

    def setShipFuelCapacity(self, tonnage: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._shipFuelCapacity = tonnage
        self._settings.setValue(Config._ShipFuelCapacityKeyName, tonnage)
        return False # No restart required

    def shipCurrentFuel(self) -> float:
        return self._shipCurrentFuel

    def setShipCurrentFuel(self, tonnage: float) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._shipCurrentFuel = tonnage
        self._settings.setValue(Config._ShipCurrentFuelKeyName, tonnage)
        return False # No restart required

    def useShipFuelPerParsec(self) -> bool:
        return self._useShipFuelPerParsec

    def setUseShipFuelPerParsec(self, enable: bool) -> bool:
        self._useShipFuelPerParsec = enable
        self._settings.setValue(Config._UseShipFuelPerParsecKeyName, enable)
        return False # No restart required

    def shipFuelPerParsec(self) -> float:
        return self._shipFuelPerParsec

    def setShipFuelPerParsec(self, value: float) -> bool:
        self._shipFuelPerParsec = value
        self._settings.setValue(Config._ShipFuelPerParsecKeyName, value)
        return False # No restart required

    def perJumpOverheads(self) -> int:
        return self._perJumpOverheads

    def setPerJumpOverheads(self, credits: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._perJumpOverheads = credits
        self._settings.setValue(Config._PerJumpOverheadKeyName, credits)
        return False # No restart required

    def availableFunds(self) -> int:
        return self._availableFunds

    def setAvailableFunds(self, credits: int) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._availableFunds = credits
        self._settings.setValue(Config._AvailableFundsKeyName, credits)
        return False # No restart required

    def sellerDmRange(self) -> typing.Tuple[int, int]:
        return self._sellerDmRange

    def setSellerDmRange(self, lowerValue: int, upperValue: int) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._sellerDmRange = (lowerValue, upperValue)
        self._settings.setValue(Config._MinSellerDmKeyName, lowerValue)
        self._settings.setValue(Config._MaxSellerDmKeyName, upperValue)
        return False # No restart required

    def buyerDmRange(self) -> typing.Tuple[int, int]:
        return self._buyerDmRange

    def setBuyerDmRange(self, minValue: int, maxValue: int) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._buyerDmRange = (minValue, maxValue)
        self._settings.setValue(Config._MinBuyerDmKeyName, minValue)
        self._settings.setValue(Config._MaxBuyerDmKeyName, maxValue)
        return False # No restart required

    def usePurchaseBroker(self) -> bool:
        return self._usePurchaseBroker

    def setUsePurchaseBroker(self, enabled: bool):
        # This setting can be modified live so update the internal and disk copy
        self._usePurchaseBroker = enabled
        self._settings.setValue(Config._UsePurchaseBrokerKeyName, enabled)
        return False # No restart required

    def purchaseBrokerDmBonus(self) -> int:
        return self._purchaseBrokerDmBonus

    def setPurchaseBrokerDmBonus(self, value) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._purchaseBrokerDmBonus = value
        self._settings.setValue(Config._PurchaseBrokerDmBonusKeyName, value)
        return False # No restart required

    def useSaleBroker(self) -> bool:
        return self._useSaleBroker

    def setUseSaleBroker(self, enabled: bool):
        # This setting can be modified live so update the internal and disk copy
        self._useSaleBroker = enabled
        self._settings.setValue(Config._UseSaleBrokerKeyName, enabled)
        return False # No restart required

    def saleBrokerDmBonus(self) -> int:
        return self._saleBrokerDmBonus

    def setSaleBrokerDmBonus(self, value) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._saleBrokerDmBonus = value
        self._settings.setValue(Config._SaleBrokerDmBonusKeyName, value)
        return False # No restart required

    def routingType(self) -> logic.RoutingType:
        return self._routingType

    def setRoutingType(self, type: logic.RoutingType) -> bool:
        self._routingType = type
        self._settings.setValue(Config._RoutingTypeKeyName, type.name)
        return False # No restart required

    def routeOptimisation(self) -> logic.RouteOptimisation:
        return self._routeOptimisation

    def setRouteOptimisation(self, optimisation: logic.RouteOptimisation) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._routeOptimisation = optimisation
        self._settings.setValue(Config._RouteOptimisationKeyName, optimisation.name)
        return False # No restart required

    def refuellingStrategy(self) -> logic.RefuellingStrategy:
        return self._refuellingStrategy

    def setRefuellingStrategy(self, strategy: logic.RefuellingStrategy) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._refuellingStrategy = strategy
        self._settings.setValue(Config._RefuellingStrategyKeyName, strategy.name)
        return False # No restart required

    def setUseFuelCaches(self, enabled: bool) -> bool:
        self._useFuelCaches = enabled
        self._settings.setValue(Config._UseFuelCachesKeyName, enabled)
        return False # No restart required

    def useFuelCaches(self) -> bool:
        return self._useFuelCaches

    def setUseAnomalyRefuelling(self, enabled: bool) -> bool:
        self._useAnomalyRefuelling = enabled
        self._settings.setValue(Config._UseAnomalyRefuellingKeyName, enabled)
        return False # No restart required

    def useAnomalyRefuelling(self) -> bool:
        return self._useAnomalyRefuelling

    def setAnomalyFuelCost(self, cost: int) -> bool:
        self._anomalyFuelCost = cost
        self._settings.setValue(Config._AnomalyFuelCostKeyName, cost)
        return False # No restart required

    def anomalyFuelCost(self) -> int:
        return self._anomalyFuelCost

    def setUseAnomalyBerthing(self, enabled: bool) -> bool:
        self._useAnomalyBerthing = enabled
        self._settings.setValue(Config._UseAnomalyBerthingKeyName, enabled)
        return False # No restart required

    def useAnomalyBerthing(self) -> bool:
        return self._useAnomalyBerthing

    def setAnomalyBerthingCost(self, cost: int) -> bool:
        self._anomalyBerthingCost = cost
        self._settings.setValue(Config._AnomalyBerthingCostKeyName, cost)
        return False # No restart required

    def anomalyBerthingCost(self) -> int:
        return self._anomalyBerthingCost

    def includeStartBerthing(self) -> bool:
        return self._includeStartBerthing

    def setIncludeStartBerthing(self, include: bool) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._includeStartBerthing = include
        self._settings.setValue(Config._IncludeStartBerthingKeyName, include)
        return False # No restart required

    def includeFinishBerthing(self) -> bool:
        return self._includeFinishBerthing

    def setIncludeFinishBerthing(self, include: bool) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._includeFinishBerthing = include
        self._settings.setValue(Config._IncludeFinishBerthingKeyName, include)
        return False # No restart required

    def includeLogisticsCosts(self) -> bool:
        return self._includeLogisticsCosts

    def setIncludeLogisticsCosts(self, include: bool) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._includeLogisticsCosts = include
        self._settings.setValue(Config._IncludeLogisticsCostsKeyName, include)
        return False # No restart required

    def includeUnprofitableTrades(self) -> bool:
        return self._includeUnprofitableTrades

    def setIncludeUnprofitableTrades(self, include: bool) -> None:
        # This setting can be modified live so update the internal and disk copy
        self._includeUnprofitableTrades = include
        self._settings.setValue(Config._IncludeUnprofitableTradesKeyName, include)
        return False # No restart required

    def zoneTagLevel(
            self,
            zoneType: traveller.ZoneType
            ) -> app.TagLevel:
        return self._taggedZoneCodes.get(zoneType)

    def zoneTagLevels(self) -> typing.Dict[traveller.ZoneType, app.TagLevel]:
        return self._taggedZoneCodes

    def setZoneTagLevels(
            self,
            codes: typing.Dict[traveller.ZoneType, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedZoneCodes = codes
        self._saveTaggingMap(Config._ZoneTaggingSectionName, codes)
        return False # No restart required

    def starPortTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        if code in self._taggedStarPortCodes:
            return self._taggedStarPortCodes[code]
        return None

    def starPortTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedStarPortCodes

    def setStarPortTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedStarPortCodes = codes
        self._saveTaggingMap(Config._StarPortTaggingSectionName, codes)
        return False # No restart required

    def worldSizeTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedWorldSizeCodes.get(code)

    def worldSizeTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedWorldSizeCodes

    def setWorldSizeTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedWorldSizeCodes = codes
        self._saveTaggingMap(Config._WorldSizeTaggingSectionName, codes)
        return False # No restart required

    def atmosphereTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedAtmosphereCodes.get(code)

    def atmosphereTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedAtmosphereCodes

    def setAtmosphereTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedAtmosphereCodes = codes
        self._saveTaggingMap(Config._AtmosphereTaggingSectionName, codes)
        return False # No restart required

    def hydrographicsTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedHydrographicsCodes.get(code)

    def hydrographicsTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedHydrographicsCodes

    def setHydrographicsTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedHydrographicsCodes = codes
        self._saveTaggingMap(Config._HydrographicsTaggingSectionName, codes)
        return False # No restart required

    def populationTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedPopulationCodes.get(code)

    def populationTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedPopulationCodes

    def setPopulationTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedPopulationCodes = codes
        self._saveTaggingMap(Config._PopulationTaggingSectionName, codes)
        return False # No restart required

    def governmentTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedGovernmentCodes.get(code)

    def governmentTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedGovernmentCodes

    def setGovernmentTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedGovernmentCodes = codes
        self._saveTaggingMap(Config._GovernmentTaggingSectionName, codes)
        return False # No restart required

    def lawLevelTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedLawLevelCodes.get(code)

    def lawLevelTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedLawLevelCodes

    def setLawLevelTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedLawLevelCodes = codes
        self._saveTaggingMap(Config._LawLevelTaggingSectionName, codes)
        return False # No restart required

    def techLevelTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedTechLevelCodes.get(code)

    def techLevelTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedTechLevelCodes

    def setTechLevelTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedTechLevelCodes = codes
        self._saveTaggingMap(Config._TechLevelTaggingSectionName, codes)
        return False # No restart required

    def baseTypeTagLevel(
            self,
            baseType: traveller.BaseType
            ) -> app.TagLevel:
        return self._taggedBaseTypes.get(baseType)

    def baseTypeTagLevels(self) -> typing.Dict[traveller.BaseType, app.TagLevel]:
        return self._taggedBaseTypes

    def setBaseTypeTagLevels(
            self,
            baseTypes: typing.Dict[traveller.BaseType, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedBaseTypes = baseTypes
        self._saveTaggingMap(Config._BaseTypeTaggingSectionName, baseTypes)
        return False # No restart required

    def tradeCodeTagLevel(
            self,
            code: traveller.TradeCode
            ) -> app.TagLevel:
        return self._taggedTradeCodes.get(code)

    def tradeCodeTagLevels(self) -> typing.Dict[traveller.TradeCode, app.TagLevel]:
        return self._taggedTradeCodes

    def setTradeCodeTagLevels(
            self,
            codes: typing.Dict[traveller.TradeCode, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedTradeCodes = codes
        self._saveTaggingMap(Config._TradeCodeTaggingSectionName, codes)
        return False # No restart required

    def resourcesTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedResourcesCodes.get(code)

    def resourceTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedResourcesCodes

    def setResourceTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedResourcesCodes = codes
        self._saveTaggingMap(Config._ResourcesTaggingSectionName, codes)
        return False # No restart required

    def labourTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedLabourCodes.get(code)

    def labourTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedLabourCodes

    def setLabourTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedLabourCodes = codes
        self._saveTaggingMap(Config._LabourTaggingSectionName, codes)
        return False # No restart required

    def infrastructureTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedInfrastructureCodes.get(code)

    def infrastructureTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedInfrastructureCodes

    def setInfrastructureTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedInfrastructureCodes = codes
        self._saveTaggingMap(Config._InfrastructureTaggingSectionName, codes)
        return False # No restart required

    def efficiencyTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedEfficiencyCodes.get(code)

    def efficiencyTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedEfficiencyCodes

    def setEfficiencyTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedEfficiencyCodes = codes
        self._saveTaggingMap(Config._EfficiencyTaggingSectionName, codes)
        return False # No restart required

    def heterogeneityTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedHeterogeneityCodes.get(code)

    def heterogeneityTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedHeterogeneityCodes

    def setHeterogeneityTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedHeterogeneityCodes = codes
        self._saveTaggingMap(Config._HeterogeneityTaggingSectionName, codes)
        return False # No restart required

    def acceptanceTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedAcceptanceCodes.get(code)

    def acceptanceTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedAcceptanceCodes

    def setAcceptanceTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedAcceptanceCodes = codes
        self._saveTaggingMap(Config._AcceptanceTaggingSectionName, codes)
        return False # No restart required

    def strangenessTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedStrangenessCodes.get(code)

    def strangenessTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedStrangenessCodes

    def setStrangenessTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedStrangenessCodes = codes
        self._saveTaggingMap(Config._StrangenessTaggingSectionName, codes)
        return False # No restart required

    def symbolsTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedSymbolsCodes.get(code)

    def symbolsTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedSymbolsCodes

    def setSymbolsTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedSymbolsCodes = codes
        self._saveTaggingMap(Config._SymbolsTaggingSectionName, codes)
        return False # No restart required

    def nobilityTagLevel(
            self,
            nobility: traveller.NobilityType
            ) -> app.TagLevel:
        return self._taggedNobilityTypes.get(nobility)

    def nobilityTagLevels(self) -> typing.Dict[traveller.NobilityType, app.TagLevel]:
        return self._taggedNobilityTypes

    def setNobilityTagLevels(
            self,
            nobilities: typing.Dict[traveller.NobilityType, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedNobilityTypes = nobilities
        self._saveTaggingMap(Config._NobilityTaggingSectionName, nobilities)
        return False # No restart required

    def allegianceTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedAllegianceCodes.get(code)

    def allegianceTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedAllegianceCodes

    def setAllegianceTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedAllegianceCodes = codes
        self._saveTaggingMap(Config._AllegianceTaggingSectionName, codes)
        return False # No restart required

    def spectralTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedSpectralCodes.get(code)

    def spectralTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedSpectralCodes

    def setSpectralTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedSpectralCodes = codes
        self._saveTaggingMap(Config._SpectralTaggingSectionName, codes)
        return False # No restart required

    def luminosityTagLevel(
            self,
            code: str
            ) -> app.TagLevel:
        return self._taggedLuminosityCodes.get(code)

    def luminosityTagLevels(self) -> typing.Dict[str, app.TagLevel]:
        return self._taggedLuminosityCodes

    def setLuminosityTagLevels(
            self,
            codes: typing.Dict[str, app.TagLevel]
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._taggedLuminosityCodes = codes
        self._saveTaggingMap(Config._LuminosityTaggingSectionName, codes)
        return False # No restart required

    # Returns colour as a string in #AARRGGBB format
    def tagColour(
            self,
            tagLevel: app.TagLevel
            ) -> str:
        return self._tagColours.get(tagLevel)

    # Takes a colour as a string in #AARRGGBB format
    def setTagColour(
            self,
            tagLevel: app.TagLevel,
            colour: str
            ) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._tagColours[tagLevel] = colour
        keyName = Config._TagLevelToKeyNameMap.get(tagLevel)
        if keyName:
            self._settings.setValue(keyName, colour)
        return False # No restart required

    def colourTheme(self) -> ColourTheme:
        return self._colourTheme

    def setColourTheme(self, theme: ColourTheme) -> bool:
        if theme == self._colourTheme:
            return False # Nothing has changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._ColourThemeKeyName, theme.name)
        return True # Restart required

    def interfaceScale(self) -> float:
        return self._interfaceScale

    def setInterfaceScale(self, scale: float) -> bool:
        if scale == self._interfaceScale:
            return False # Nothing changed

        # Don't update internal copy of setting, it's only applied after a restart
        self._settings.setValue(Config._InterfaceScaleKeyName, scale)
        return True # Restart required

    def showToolTipImages(self) -> bool:
        return self._showToolTipImages

    def setShowToolTipImages(self, enable: bool) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._showToolTipImages = enable
        self._settings.setValue(Config._ShowToolTipImagesKeyName, enable)
        return False # No restart required

    def averageCaseColour(self) -> str:
        return self._averageCaseColour

    # Takes a colour as a string in #AARRGGBB format
    def setAverageCaseColour(self, colour: str) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._averageCaseColour = colour
        self._settings.setValue(Config._AverageCaseColourKeyName, colour)
        return False # No restart required

    def worstCaseColour(self) -> str:
        return self._worstCaseColour

    # Takes a colour as a string in #AARRGGBB format
    def setWorstCaseColour(self, colour: str) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._worstCaseColour = colour
        self._settings.setValue(Config._WorstCaseColourKeyName, colour)
        return False # No restart required

    def bestCaseColour(self) -> str:
        return self._bestCaseColour

    # Takes a colour as a string in #AARRGGBB format
    def setBestCaseColour(self, colour: str) -> bool:
        # This setting can be modified live so update the internal and disk copy
        self._bestCaseColour = colour
        self._settings.setValue(Config._BestCaseColourKeyName, colour)
        return False # No restart required

    def load(self):
        if not self._settings:
            filePath = os.path.join(self._appDir, self._ConfigFileName)
            self._settings = QtCore.QSettings(filePath, QtCore.QSettings.Format.IniFormat)

        self._logLevel = self._loadLogLevelSetting(
            key=Config._LogLevelKeyName,
            default=logging.WARNING)

        self._mapEngine = self._loadEnumSetting(
            key=Config._MapEngineTypeKeyName,
            default=MapEngine.InApp,
            members=MapEngine.__members__)

        self._mapRenderingType = self._loadEnumSetting(
            key=Config._MapRenderingTypeKeyName,
            default=MapRenderingType.Tiled,
            members=MapRenderingType.__members__)

        self._mapAnimations = self._loadBoolSetting(
            key=Config._MapAnimationsKeyName,
            default=True)

        self._proxyPort = self._loadIntSetting(
            key=Config._ProxyPortKeyName,
            default=61977,
            minValue=1024, # Don't allow system ports
            maxValue=65535)
        # NOTE: Default to 1 host on macOS as it doesn't enable other loopback
        # addresses by default
        self._proxyHostPoolSize = self._loadIntSetting(
            key=Config._ProxyHostPoolSizeKeyName,
            default=1 if common.isMacOS() else 4,
            minValue=1,
            maxValue=10)
        self._proxyMapUrl = self._loadUrlSetting(
            key=Config._ProxyMapUrlKeyName,
            default=travellermap.TravellerMapBaseUrl)
        self._proxyTileCacheSize = self._loadIntSetting(
            key=Config._ProxyTileCacheSizeKeyName,
            default=500 * 1000 * 1000, # 500MB
            minValue=0) # 0 means disable cache
        self._proxyTileCacheLifetime = self._loadIntSetting(
            key=Config._ProxyTileCacheLifetimeKeyName,
            default=14, # Days
            minValue=0) # 0 means never expire
        self._proxySvgComposition = self._loadBoolSetting(
            key=Config._ProxySvgCompositionKeyName,
            default=False)

        self._milieu = self._loadEnumSetting(
            key=Config._MilieuKeyName,
            default=travellermap.Milieu.M1105,
            members=travellermap.Milieu.__members__)
        self._mapStyle = self._loadEnumSetting(
            key=Config._MapStyleKeyName,
            default=travellermap.Style.Poster,
            members=travellermap.Style.__members__)
        self._mapOptions = set()
        for option, key in Config._MapOptionToKeyNameMap.items():
            if self._hasKey(key=key):
                enabled = self._loadBoolSetting(key=key, default=False)
            else:
                enabled = option in Config._DefaultMapOptions
            if enabled:
                self._mapOptions.add(option)

        self._rules = traveller.Rules(
            system=self._loadEnumSetting(
                key=Config._RuleSystemKeyName,
                default=traveller.RuleSystem.MGT2022,
                members=traveller.RuleSystem.__members__),
            classAStarPortFuelType=self._loadEnumSetting(
                key=Config._RuleClassAFuelTypeKeyName,
                default=traveller.StarPortFuelType.AllTypes,
                members=traveller.StarPortFuelType.__members__),
            classBStarPortFuelType=self._loadEnumSetting(
                key=Config._RuleClassBFuelTypeKeyName,
                default=traveller.StarPortFuelType.AllTypes,
                members=traveller.StarPortFuelType.__members__),
            classCStarPortFuelType=self._loadEnumSetting(
                key=Config._RuleClassCFuelTypeKeyName,
                default=traveller.StarPortFuelType.UnrefinedOnly,
                members=traveller.StarPortFuelType.__members__),
            classDStarPortFuelType=self._loadEnumSetting(
                key=Config._RuleClassDFuelTypeKeyName,
                default=traveller.StarPortFuelType.UnrefinedOnly,
                members=traveller.StarPortFuelType.__members__),
            classEStarPortFuelType=self._loadEnumSetting(
                key=Config._RuleClassEFuelTypeKeyName,
                default=traveller.StarPortFuelType.NoFuel,
                members=traveller.StarPortFuelType.__members__))

        self._playerBrokerDm = self._loadIntSetting(
            key=Config._PlayerBrokerDmKeyName,
            default=0,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm)
        # Set default ship tonnage, jump rating, cargo and fuel capacities to the values for a standard Scout ship
        self._shipTonnage = self._loadIntSetting(
            key=Config._ShipTonnageKeyName,
            default=100,
            minValue=100)
        self._shipJumpRating = self._loadIntSetting(
            key=Config._ShipJumpRatingKeyName,
            default=2,
            minValue=app.MinPossibleJumpRating,
            maxValue=app.MaxPossibleJumpRating)
        self._shipCargoCapacity = self._loadIntSetting(
            key=Config._ShipCargoCapacityKeyName,
            default=12,
            minValue=0)
        self._shipFuelCapacity = self._loadIntSetting(
            key=Config._ShipFuelCapacityKeyName,
            default=23,
            minValue=0)
        self._shipCurrentFuel = self._loadFloatSetting(
            key=Config._ShipCurrentFuelKeyName,
            default=0,
            maxValue=self._shipFuelCapacity)
        self._useShipFuelPerParsec = self._loadBoolSetting(
            key=Config._UseShipFuelPerParsecKeyName,
            default=False)
        self._shipFuelPerParsec = self._loadFloatSetting(
            key=Config._ShipFuelPerParsecKeyName,
            default=self._shipTonnage * 0.1) # 10% of ship tonnage
        self._perJumpOverheads = self._loadIntSetting(
            key=Config._PerJumpOverheadKeyName,
            default=0,
            minValue=0)
        self._availableFunds = self._loadIntSetting(
            key=Config._AvailableFundsKeyName,
            default=10000,
            minValue=0)
        self._sellerDmRange = self._loadRangeSetting(
            minKey=Config._MinSellerDmKeyName,
            maxKey=Config._MaxSellerDmKeyName,
            lowerDefault=1,
            upperDefault=3,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm)
        self._buyerDmRange = self._loadRangeSetting(
            minKey=Config._MinBuyerDmKeyName,
            maxKey=Config._MaxBuyerDmKeyName,
            lowerDefault=1,
            upperDefault=3,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm)
        self._usePurchaseBroker = self._loadBoolSetting(
            key=Config._UsePurchaseBrokerKeyName,
            default=False)
        self._purchaseBrokerDmBonus = self._loadIntSetting(
            key=Config._PurchaseBrokerDmBonusKeyName,
            default=1)
        self._useSaleBroker = self._loadBoolSetting(
            key=Config._UseSaleBrokerKeyName,
            default=False)
        self._saleBrokerDmBonus = self._loadIntSetting(
            key=Config._SaleBrokerDmBonusKeyName,
            default=1)
        self._routingType = self._loadEnumSetting(
            key=self._RoutingTypeKeyName,
            default=logic.RoutingType.FuelBased,
            members=logic.RoutingType.__members__)
        self._routeOptimisation = self._loadEnumSetting(
            key=Config._RouteOptimisationKeyName,
            default=logic.RouteOptimisation.ShortestDistance,
            members=logic.RouteOptimisation.__members__)
        self._refuellingStrategy = self._loadEnumSetting(
            key=Config._RefuellingStrategyKeyName,
            default=logic.RefuellingStrategy.WildernessPreferred,
            members=logic.RefuellingStrategy.__members__)
        self._useFuelCaches = self._loadBoolSetting(
            key=Config._UseFuelCachesKeyName,
            default=True)
        self._useAnomalyRefuelling = self._loadBoolSetting(
            key=Config._UseAnomalyRefuellingKeyName,
            default=True)
        self._anomalyFuelCost = self._loadIntSetting(
            key=Config._AnomalyFuelCostKeyName,
            default=0,
            minValue=0)
        self._useAnomalyBerthing = self._loadBoolSetting(
            key=Config._UseAnomalyBerthingKeyName,
            default=False)
        self._anomalyBerthingCost = self._loadIntSetting(
            key=Config._AnomalyBerthingCostKeyName,
            default=0,
            minValue=0)
        self._includeStartBerthing = self._loadBoolSetting(
            key=Config._IncludeStartBerthingKeyName,
            default=False)
        self._includeFinishBerthing = self._loadBoolSetting(
            key=Config._IncludeFinishBerthingKeyName,
            default=True)
        self._includeLogisticsCosts = self._loadBoolSetting(
            key=Config._IncludeLogisticsCostsKeyName,
            default=True)
        self._includeUnprofitableTrades = self._loadBoolSetting(
            key=Config._IncludeUnprofitableTradesKeyName,
            default=False)

        # Colours are in #AARRGGBB format
        self._colourTheme = self._loadEnumSetting(
            key=Config._ColourThemeKeyName,
            default=ColourTheme.DarkMode,
            members=ColourTheme.__members__)
        self._interfaceScale = self._loadFloatSetting(
            key=Config._InterfaceScaleKeyName,
            default=1.0,
            minValue=1.0,
            maxValue=4.0)
        self._showToolTipImages = self._loadSetting(
            key=Config._ShowToolTipImagesKeyName,
            default=True,
            type=bool)
        self._averageCaseColour = self._loadColourSetting(
            key=Config._AverageCaseColourKeyName,
            default='#0A0000FF')
        self._worstCaseColour = self._loadColourSetting(
            key=Config._WorstCaseColourKeyName,
            default='#0AFF0000')
        self._bestCaseColour = self._loadColourSetting(
            key=Config._BestCaseColourKeyName,
            default='#0A00FF00')

        isDarkMode = self._colourTheme == ColourTheme.DarkMode or \
            (self._colourTheme == ColourTheme.UseOSSetting and darkdetect.isDark())

        self._tagColours = {
            app.TagLevel.Desirable: self._loadColourSetting(
                key=Config._TagLevelToKeyNameMap[app.TagLevel.Desirable],
                default='#8000AA00' if isDarkMode else '#808CD47E'),
            app.TagLevel.Warning: self._loadColourSetting(
                key=Config._TagLevelToKeyNameMap[app.TagLevel.Warning],
                default='#80FF7700' if isDarkMode else '#80994700'),
            app.TagLevel.Danger: self._loadColourSetting(
                key=Config._TagLevelToKeyNameMap[app.TagLevel.Danger],
                default='#80BC2023' if isDarkMode else '#80FF6961')
        }

        self._taggedZoneCodes = self._loadTaggingMap(
            section=Config._ZoneTaggingSectionName,
            keyType=traveller.ZoneType,
            default={
                traveller.ZoneType.AmberZone: app.TagLevel.Warning,
                traveller.ZoneType.RedZone: app.TagLevel.Danger,
                traveller.ZoneType.Unabsorbed: app.TagLevel.Warning,
                traveller.ZoneType.Forbidden: app.TagLevel.Danger
            })

        self._taggedStarPortCodes = self._loadTaggingMap(
            section=Config._StarPortTaggingSectionName,
            keyType=str,
            default={
                'X': app.TagLevel.Warning
            })

        self._taggedWorldSizeCodes = self._loadTaggingMap(
            section=Config._WorldSizeTaggingSectionName,
            keyType=str)

        self._taggedAtmosphereCodes = self._loadTaggingMap(
            section=Config._AtmosphereTaggingSectionName,
            keyType=str,
            default={
                # Tag corrosive and insidious atmospheres
                'B': app.TagLevel.Danger,
                'C': app.TagLevel.Danger,
            })

        self._taggedHydrographicsCodes = self._loadTaggingMap(
            section=Config._HydrographicsTaggingSectionName,
            keyType=str)

        self._taggedPopulationCodes = self._loadTaggingMap(
            section=Config._PopulationTaggingSectionName,
            keyType=str,
            default={
                # Tag worlds with less than 100 people
                '0': app.TagLevel.Danger,
                '1': app.TagLevel.Warning,
                '2': app.TagLevel.Warning,
            })

        self._taggedGovernmentCodes = self._loadTaggingMap(
            section=Config._GovernmentTaggingSectionName,
            keyType=str)

        self._taggedLawLevelCodes = self._loadTaggingMap(
            section=Config._LawLevelTaggingSectionName,
            keyType=str,
            default={
                '0': app.TagLevel.Danger
            })

        self._taggedTechLevelCodes = self._loadTaggingMap(
            section=Config._TechLevelTaggingSectionName,
            keyType=str)

        self._taggedBaseTypes = self._loadTaggingMap(
            section=Config._BaseTypeTaggingSectionName,
            keyType=traveller.BaseType)

        self._taggedTradeCodes = self._loadTaggingMap(
            section=Config._TradeCodeTaggingSectionName,
            keyType=traveller.TradeCode,
            default={
                traveller.TradeCode.AmberZone: app.TagLevel.Warning,
                traveller.TradeCode.RedZone: app.TagLevel.Danger,
                traveller.TradeCode.HellWorld: app.TagLevel.Danger,
                traveller.TradeCode.PenalColony: app.TagLevel.Danger,
                traveller.TradeCode.PrisonCamp: app.TagLevel.Danger,
                traveller.TradeCode.Reserve: app.TagLevel.Danger,
                traveller.TradeCode.DangerousWorld: app.TagLevel.Danger,
                traveller.TradeCode.ForbiddenWorld: app.TagLevel.Danger
            })

        self._taggedResourcesCodes = self._loadTaggingMap(
            section=Config._ResourcesTaggingSectionName,
            keyType=str)

        self._taggedLabourCodes = self._loadTaggingMap(
            section=Config._LabourTaggingSectionName,
            keyType=str)

        self._taggedInfrastructureCodes = self._loadTaggingMap(
            section=Config._InfrastructureTaggingSectionName,
            keyType=str)

        self._taggedEfficiencyCodes = self._loadTaggingMap(
            section=Config._EfficiencyTaggingSectionName,
            keyType=str)

        self._taggedHeterogeneityCodes = self._loadTaggingMap(
            section=Config._HeterogeneityTaggingSectionName,
            keyType=str)

        self._taggedAcceptanceCodes = self._loadTaggingMap(
            section=Config._AcceptanceTaggingSectionName,
            keyType=str)

        self._taggedStrangenessCodes = self._loadTaggingMap(
            section=Config._StrangenessTaggingSectionName,
            keyType=str)

        self._taggedSymbolsCodes = self._loadTaggingMap(
            section=Config._SymbolsTaggingSectionName,
            keyType=str)

        self._taggedNobilityTypes = self._loadTaggingMap(
            section=Config._NobilityTaggingSectionName,
            keyType=traveller.NobilityType)

        self._taggedAllegianceCodes = self._loadTaggingMap(
            section=Config._AllegianceTaggingSectionName,
            keyType=str)

        self._taggedSpectralCodes = self._loadTaggingMap(
            section=Config._SpectralTaggingSectionName,
            keyType=str)

        self._taggedLuminosityCodes = self._loadTaggingMap(
            section=Config._LuminosityTaggingSectionName,
            keyType=str)

    def _hasKey(self, key: str) -> bool:
        return self._settings.contains(key)

    def _saveTaggingMap(
            self,
            section: str,
            taggingMap: typing.Union[typing.Dict[str, app.TagLevel], typing.Dict[enum.Enum, app.TagLevel]]
            ) -> None:
        self._settings.remove(section)
        self._settings.beginWriteArray(section)
        for index, (key, tagLevel) in enumerate(taggingMap.items()):
            if tagLevel == None:
                continue
            self._settings.setArrayIndex(index)
            self._settings.setValue(key.name if isinstance(key, enum.Enum) else key, tagLevel.name)
        self._settings.endArray()

    def _loadTaggingMap(
            self,
            section: str,
            keyType: typing.Type[typing.Union[str, traveller.ZoneType, traveller.BaseType, traveller.NobilityType, traveller.TradeCode]],
            default: typing.Dict[
                typing.Union[str, traveller.ZoneType, traveller.BaseType, traveller.NobilityType, traveller.TradeCode],
                app.TagLevel] = {},
            ) -> typing.Union[typing.Dict[str, app.TagLevel], typing.Dict[enum.Enum, app.TagLevel]]:
        hasSection = False
        for childSectionName in self._settings.childGroups():
            if childSectionName == section:
                hasSection = True
                break

        if not hasSection:
            # Only return default if there is no section. If the section exists but is empty then return
            # an empty mapping
            return default

        taggingMap = {}
        self._settings.beginReadArray(section)
        for key in self._settings.allKeys():
            if key == 'size':
                continue

            # Strip of the index that QSettings puts on array elements. For reasons I don't understand it's
            # not consistent with which separator it uses
            name = re.sub('.*[\\/]', '', key)

            value = self._loadStringSetting(
                key=key,
                default=None)
            if value not in app.TagLevel.__members__:
                logging.warning(f'Ignoring {section} tagging list entry {name} ({value} is not a valid TagLevel)')
                continue
            tagLevel = app.TagLevel.__members__[value]

            if keyType == traveller.ZoneType:
                if name not in traveller.ZoneType.__members__:
                    logging.warning(f'Ignoring {section} tagging list entry {name} ({name} is not a valid ZoneType)')
                    continue
                taggingMap[traveller.ZoneType.__members__[name]] = tagLevel
            elif keyType == traveller.BaseType:
                if name not in traveller.BaseType.__members__:
                    logging.warning(f'Ignoring {section} tagging list entry {name} ({name} is not a valid BaseType)')
                    continue
                taggingMap[traveller.BaseType.__members__[name]] = tagLevel
            elif keyType == traveller.NobilityType:
                if name not in traveller.NobilityType.__members__:
                    logging.warning(f'Ignoring {section} tagging list entry {name} ({name} is not a valid NobilityType)')
                    continue
                taggingMap[traveller.NobilityType.__members__[name]] = tagLevel
            elif keyType == traveller.TradeCode:
                if name not in traveller.TradeCode.__members__:
                    logging.warning(f'Ignoring {section} tagging list entry {name} ({name} is not a valid TradeCode)')
                    continue
                taggingMap[traveller.TradeCode.__members__[name]] = tagLevel
            else:
                assert(keyType == str)
                taggingMap[name] = tagLevel

        self._settings.endArray()

        return taggingMap

    def _loadSetting(
            self,
            key: str,
            default: typing.Any,
            type: type
            ) -> typing.Any:
        try:
            # Explicitly check for key not being present and use default if it's not. This is
            # preferable to relying on value() as it can have some unexpected behaviour (e.g.
            # a default of None when reading a float will return 0.0 rather than None)
            if not self._settings.contains(key):
                return default

            return self._settings.value(key, defaultValue=default, type=type)
        except TypeError as ex:
            logging.error(f'Failed to read "{key}" from "{self._settings.group()}" in "{self._settings.fileName()}""  (value is not a {type.__name__})')
            return default
        except Exception as ex:
            logging.error(f'Failed to read "{key}" from "{self._settings.group()}" in "{self._settings.fileName()}"', exc_info=ex)
            return default

    def _loadStringSetting(
            self,
            key: str,
            default: str
            ) -> str:
        return self._loadSetting(
            key=key,
            default=default,
            type=str)

    def _loadBoolSetting(
            self,
            key: str,
            default: bool
            ) -> str:
        return self._loadSetting(
            key=key,
            default=default,
            type=bool)

    def _loadIntSetting(
            self,
            key: str,
            default: int,
            minValue: typing.Optional[int] = None,
            maxValue: typing.Optional[int] = None
            ) -> int:
        value = self._loadSetting(
            key=key,
            default=default,
            type=int)
        if ((minValue != None) and (value < minValue)) or ((maxValue != None) and (value > maxValue)):
            if (minValue != None) and (maxValue != None):
                reason = f'{value} is not in the range {minValue} - {maxValue}'
            elif minValue != None:
                reason = f'{value} is not greater than or equal to {minValue}'
            else:
                assert(maxValue != None)
                reason = f'{value} is not less than or equal to {maxValue}'

            logging.warning(f'Ignoring {key} from "{self._settings.group()}" in "{self._settings.fileName()}" ({reason})')
            return default
        return value

    def _loadFloatSetting(
            self,
            key: str,
            default: float,
            minValue: typing.Optional[float] = None,
            maxValue: typing.Optional[float] = None
            ) -> float:
        value = self._loadSetting(
            key=key,
            default=default,
            type=float)
        if ((minValue != None) and (value < minValue)) or ((maxValue != None) and (value > maxValue)):
            if (minValue != None) and (maxValue != None):
                reason = f'{value} is not in the range {minValue} - {maxValue}'
            elif minValue != None:
                reason = f'{value} is not greater than or equal to {minValue}'
            else:
                assert(maxValue != None)
                reason = f'{value} is not less than or equal to {maxValue}'

            logging.warning(f'Ignoring {key} from "{self._settings.group()}" in "{self._settings.fileName()}" ({reason})')
            return default
        return value

    def _loadEnumSetting(
            self,
            key: str,
            default: enum.Enum,
            members: typing.Iterable[enum.Enum]
            ) -> enum.Enum:
        value = self._loadSetting(
            key=key,
            default=default.name,
            type=str)
        if value not in members:
            logging.warning(f'Ignoring {key} from "{self._settings.group()}" in "{self._settings.fileName()}" ({value} is not a valid {type(default).__name__})')
            return default
        return members[value]

    def _loadUrlSetting(
            self,
            key: str,
            default: str
            ) -> str:
        value = self._loadSetting(
            key=key,
            default=default,
            type=str)
        if not urllib.parse.urlparse(value):
            logging.warning(f'Ignoring {key} from "{self._settings.group()}" in "{self._settings.fileName()}" ({value} is not a valid URL)')
            return default
        return value

    def _loadColourSetting(
            self,
            key: str,
            default: str
            ) -> str:
        value = self._loadSetting(
            key=key,
            default=default,
            type=str)
        if not re.match(r'^#[0-9a-fA-F]{8}$', value):
            logging.warning(f'Ignoring {key} from "{self._settings.group()}" in "{self._settings.fileName()}" ({value} is not a valid #AARRGGBB colour)')
            return default
        return value

    def _loadLogLevelSetting(
            self,
            key: str,
            default: int
            ) -> int:
        value = self._loadStringSetting(
            key=key,
            default=None)
        if not value or value not in self._StringToLogLevel:
            return default
        return self._StringToLogLevel[value]

    # Ranges are stored as two separate keys to it easier to manually edit the config
    def _loadRangeSetting(
            self,
            minKey: str,
            maxKey: str,
            lowerDefault: int,
            upperDefault: int,
            minValue: int,
            maxValue: int
            ) -> int:
        minValue = self._loadIntSetting(
            key=minKey,
            default=lowerDefault,
            minValue=minValue,
            maxValue=maxValue)
        maxValue = self._loadIntSetting(
            key=maxKey,
            default=upperDefault,
            minValue=minValue,
            maxValue=maxValue)
        if minValue > maxValue:
            minValue, maxValue = maxValue, minValue
        return (minValue, maxValue)
