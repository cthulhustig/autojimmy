import astronomer
import common
import enum
import traveller
import typing

# MGT2 Trade Goods

# Availability
# - Suppliers on all worlds have all common goods
# - Suppliers have all goods with an availability that matches that worlds trade codes
# - Suppliers have 1D6 random goods
# - The quantity a supplier has available for each trade good is determined by a dice roll, what to roll depends on the trade good
# - If some of the randomly rolled goods are already available (due to the rules above), then
#   the quantity of those goods the seller has available is doubled (or more if the same good is
#   randomly rolled multiple times)
# - Illegal goods are only available if using a black market supplier
# - Black market suppliers have all illegal goods that match that worlds trade codes

# Purchase price
# 1. Roll 3D6
# 2. Add broker skill
# 3. Add any DM from purchase column (only use highest one if there are multiple)
# 4. Subtract any DM from the sale column (only use highest one if there are multiple)
# 5. Subtract supplier DM

# Sale price
# 1. Roll 3D6
# 2. Add broker skill
# 3. Subtract any DM from the purchase column (only use highest one if there are multiple)
# 4. Add any DM from the sale column (only use highest one if there are multiple)
# 5. Subtract supplier DM

# NOTE: If I ever update the value of these enums I'll need to do something
# for backward compatibility with serialisation
class TradeType(enum.Enum):
    Sale = 'Sale'
    Purchase = 'Purchase'


_TradeTypeSerialisationTypeToStr = {e: e.value.lower() for e in TradeType}
_TradeTypeSerialisationStrToType = {v: k for k, v in _TradeTypeSerialisationTypeToStr.items()}

class _TradeGoodDefinition(object):
    def __init__(
            self,
            id: int,
            name: str,
            basePrice: int,
            availableTonsD6Count: int,
            availableTonsMultiplier: int,
            availabilityTradeCodes: typing.Optional[typing.Iterable[traveller.TradeCode]] = None, # None means available everywhere
            buyTradeCodeDmMap: typing.Optional[typing.Mapping[traveller.TradeCode, int]] = None,
            buyAmberZoneDm: typing.Optional[int] = None,
            buyRedZoneDm: typing.Optional[int] = None,
            sellTradeCodeDmMap: typing.Optional[typing.Mapping[traveller.TradeCode, int]] = None,
            sellAmberZoneDm: typing.Optional[int] = None,
            sellRedZoneDm: typing.Optional[int] = None,
            illegalLawLevel: typing.Optional[int] = None, # None means legal at all law levels
            ) -> None:
        self._id = id
        self._name = name
        self._basePrice = common.ScalarCalculation(
            value=basePrice,
            name=f'{name} Base Price')

        self._availableTonsD6Count = common.ScalarCalculation(
            value=availableTonsD6Count,
            name=f'{name} Available Quantity Die Count')

        self._availableTonsMultiplier = common.ScalarCalculation(
            value=availableTonsMultiplier,
            name=f'{name} Available Quantity Multiplier')

        self._availabilityTradeCodes = list(availabilityTradeCodes) if availabilityTradeCodes else list()

        self._buyTradeCodeDmMap = {}
        if buyTradeCodeDmMap is not None:
            for tradeCode, tradeCodeDm in buyTradeCodeDmMap.items():
                self._buyTradeCodeDmMap[tradeCode] = common.ScalarCalculation(
                    value=tradeCodeDm,
                    name=f'{traveller.tradeCodeName(tradeCode)} Purchase DM')

        self._buyAmberZoneDm = None
        if buyAmberZoneDm:
            self._buyAmberZoneDm = common.ScalarCalculation(
                value=buyAmberZoneDm,
                name=f'Amber Zone Purchase DM')

        self._buyRedZoneDm = None
        if buyRedZoneDm is not None:
            self._buyRedZoneDm = common.ScalarCalculation(
                value=buyRedZoneDm,
                name=f'Red Zone Purchase DM')

        self._sellTradeCodes = {}
        if sellTradeCodeDmMap is not None:
            for tradeCode, tradeCodeDm in sellTradeCodeDmMap.items():
                self._sellTradeCodes[tradeCode] = common.ScalarCalculation(
                    value=tradeCodeDm,
                    name=f'{traveller.tradeCodeName(tradeCode)} Sale DM')

        self._sellAmberZoneDm = None
        if sellAmberZoneDm:
            self._sellAmberZoneDm = common.ScalarCalculation(
                value=sellAmberZoneDm,
                name=f'Amber Zone Sale DM')

        self._sellRedZoneDm = None
        if sellRedZoneDm is not None:
            self._sellRedZoneDm = common.ScalarCalculation(
                value=sellRedZoneDm,
                name=f'Red Zone Sale DM')

        self._illegalLawLevel = illegalLawLevel

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def basePrice(self) -> common.ScalarCalculation:
        return self._basePrice

    def availableTonsD6Count(self) -> common.ScalarCalculation:
        return self._availableTonsD6Count

    def availableTonsMultiplier(self) -> common.ScalarCalculation:
        return self._availableTonsMultiplier

    def availabilityTradeCodes(self) -> typing.Iterable[traveller.TradeCode]:
        return self._availabilityTradeCodes

    def buyTradeCodeDmMap(self) -> typing.Mapping[traveller.TradeCode, common.ScalarCalculation]:
        return self._buyTradeCodeDmMap

    def buyAmberZoneDm(self) -> typing.Optional[common.ScalarCalculation]:
        return self._buyAmberZoneDm

    def buyRedZoneDm(self) -> typing.Optional[common.ScalarCalculation]:
        return self._buyRedZoneDm

    def sellTradeCodeDmMap(self) -> typing.Mapping[traveller.TradeCode, common.ScalarCalculation]:
        return self._sellTradeCodes

    def sellAmberZoneDm(self) -> typing.Optional[common.ScalarCalculation]:
        return self._sellAmberZoneDm

    def sellRedZoneDm(self) -> typing.Optional[common.ScalarCalculation]:
        return self._sellRedZoneDm

    def illegalLawLevel(self) -> typing.Optional[int]:
        return self._illegalLawLevel

class TradeGood(object):
    _ValueRangeOf3D6 = common.calculateValueRangeForDice(
        dieCount=3,
        higherIsBetter=True)

    def __init__(
            self,
            system: traveller.RuleSystem,
            data: _TradeGoodDefinition
            ) -> None:
        self._system = system
        self._data = data

    def ruleSystem(self) -> traveller.RuleSystem:
        return self._system

    def id(self) -> int:
        return self._data.id()

    def name(self) -> str:
        return self._data.name()

    def basePrice(self) -> common.ScalarCalculation:
        return self._data.basePrice()

    def isIllegal(
            self,
            world: astronomer.World,
            ) -> bool:
        if self._data.illegalLawLevel() == None:
            # It's legal everywhere. Note that it's important we compare to None
            # rather than using not as we need to differentiate between not
            # illegal (i.e. None) and illegal everywhere (i.e. 0)
            return False
        if self.isUniversallyIllegal():
            # It's illegal everywhere
            return True

        return self.isWorldIllegal(world)

    # Is the item illegal everywhere
    def isUniversallyIllegal(self) -> bool:
        return self._data.illegalLawLevel() == 0

    # Is the item illegal specifically because of the worlds law level (i.e. it's not illegal on all worlds)
    def isWorldIllegal(
            self,
            world: astronomer.World,
            ) -> bool:
        if not self._data.illegalLawLevel():
            # Note that it's intentional that this covers the cases where it's
            # None (i.e. legal everywhere) and 0 (i.e. it's universally illegal)
            return False

        # Check if the world law level is greater or equal to the law level where the trade good
        # becomes illegal. If the law level is unknown use a default of -1 so that it will never be
        # higher (i.e. trade goods aren't world illegal if the law level is unknown)
        worldLawLevel = world.uwp().numeric(
            element=astronomer.UWP.Element.LawLevel,
            default=-1)
        return worldLawLevel >= self._data.illegalLawLevel()

    def availableTonsD6Count(self) -> common.ScalarCalculation:
        return self._data.availableTonsD6Count()

    def availableTonsMultiplier(self) -> common.ScalarCalculation:
        return self._data.availableTonsMultiplier()

    def checkTradeGoodAvailability(
            self,
            rules: traveller.Rules,
            world: astronomer.World
            ) -> bool:
        availabilityTradeCodes = self._data.availabilityTradeCodes()
        if availabilityTradeCodes == None:
            # Trade goods with an availability set to None are available everywhere
            return True

        for tradeCode in world.tradeCodes(rules=rules):
            if tradeCode in availabilityTradeCodes:
                # The world has this trade good available due to the world trade codes
                return True
        return False

    def calculatePurchaseTradeCodeDm(
            self,
            rules: traveller.Rules,
            world: astronomer.World
            ) -> typing.Optional[common.ScalarCalculation]:
        return self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.buyTradeCodeDmMap(),
            amberZoneDm=self._data.buyAmberZoneDm(),
            redZoneDm=self._data.buyRedZoneDm())

    def calculateSaleTradeCodeDm(
            self,
            rules: traveller.Rules,
            world: astronomer.World
            ) -> typing.Optional[common.ScalarCalculation]:
        return self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.sellTradeCodeDmMap(),
            amberZoneDm=self._data.sellAmberZoneDm(),
            redZoneDm=self._data.sellRedZoneDm())

    def calculateTotalPurchaseDm(
            self,
            rules: traveller.Rules,
            world: astronomer.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            sellerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        # Convert arguments to calculations so we can track how values are calculated
        if not isinstance(brokerDm, common.ScalarCalculation) and not isinstance(brokerDm, common.RangeCalculation):
            assert(isinstance(brokerDm, int))
            brokerDm = common.ScalarCalculation(
                value=brokerDm,
                name='Broker DM')

        if not isinstance(sellerDm, common.ScalarCalculation) and not isinstance(sellerDm, common.RangeCalculation):
            assert(isinstance(sellerDm, int))
            sellerDm = common.ScalarCalculation(
                value=sellerDm,
                name='Seller DM')

        if known3D6Roll and not isinstance(known3D6Roll, common.ScalarCalculation):
            assert(isinstance(known3D6Roll, int))
            known3D6Roll = common.ScalarCalculation(
                value=known3D6Roll,
                name='3D6 Roll')

        tradeCodeDm = self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.buyTradeCodeDmMap(),
            amberZoneDm=self._data.buyAmberZoneDm(),
            redZoneDm=self._data.buyRedZoneDm())
        if tradeCodeDm:
            purchaseDm = common.Calculator.add(
                lhs=brokerDm,
                rhs=tradeCodeDm)
        else:
            purchaseDm = brokerDm

        tradeCodeDm = self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.sellTradeCodeDmMap(),
            amberZoneDm=self._data.sellAmberZoneDm(),
            redZoneDm=self._data.sellRedZoneDm())
        if tradeCodeDm:
            saleDm = common.Calculator.add(
                lhs=sellerDm,
                rhs=tradeCodeDm)
        else:
            saleDm = sellerDm

        worldDm = common.Calculator.subtract(
            lhs=purchaseDm,
            rhs=saleDm)

        if known3D6Roll:
            randomDm = known3D6Roll
            randomDm = common.Calculator.equals(
                value=randomDm,
                name='Random Purchase DM')
        else:
            randomDm = common.Calculator.floor(
                value=self._ValueRangeOf3D6,
                name='Random Purchase DM')

        return common.Calculator.add(
            lhs=randomDm,
            rhs=worldDm,
            name='Purchase DM')

    def calculatePurchasePrice(
            self,
            rules: traveller.Rules,
            world: astronomer.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            sellerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        purchaseDm = self.calculateTotalPurchaseDm(
            world=world,
            rules=rules,
            brokerDm=brokerDm,
            sellerDm=sellerDm,
            known3D6Roll=known3D6Roll)

        if isinstance(purchaseDm, common.ScalarCalculation):
            priceModifier = common.ScalarCalculation(
                value=_calculatePurchasePriceModifier(
                    ruleSystem=rules.system(),
                    purchaseDm=purchaseDm),
                name='Base Price Scale')
        else:
            priceModifier = common.RangeCalculation(
                worstCase=_calculatePurchasePriceModifier(
                    ruleSystem=rules.system(),
                    purchaseDm=purchaseDm.worstCaseCalculation()),
                bestCase=_calculatePurchasePriceModifier(
                    ruleSystem=rules.system(),
                    purchaseDm=purchaseDm.bestCaseCalculation()),
                averageCase=_calculatePurchasePriceModifier(
                    ruleSystem=rules.system(),
                    purchaseDm=purchaseDm.averageCaseCalculation()),
                name='Base Price Scale')

        return common.Calculator.multiply(
            lhs=self._data.basePrice(),
            rhs=priceModifier,
            name='Purchase Price Per Ton')

    def calculateTotalSaleDm(
            self,
            rules: traveller.rules,
            world: astronomer.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            buyerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        # Convert arguments to calculations so we can track how values are calculated
        if not isinstance(brokerDm, common.ScalarCalculation) and not isinstance(brokerDm, common.RangeCalculation):
            assert(isinstance(brokerDm, int))
            brokerDm = common.ScalarCalculation(
                value=brokerDm,
                name='Broker DM')

        if not isinstance(buyerDm, common.ScalarCalculation) and not isinstance(buyerDm, common.RangeCalculation):
            assert(isinstance(buyerDm, int))
            buyerDm = common.ScalarCalculation(
                value=buyerDm,
                name='Buyer DM')

        if known3D6Roll and not isinstance(known3D6Roll, common.ScalarCalculation):
            assert(isinstance(known3D6Roll, int))
            known3D6Roll = common.ScalarCalculation(
                value=known3D6Roll,
                name='3D6 Roll')

        tradeCodeDm = self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.sellTradeCodeDmMap(),
            amberZoneDm=self._data.sellAmberZoneDm(),
            redZoneDm=self._data.sellRedZoneDm())
        if tradeCodeDm:
            saleDm = common.Calculator.add(
                lhs=brokerDm,
                rhs=tradeCodeDm)
        else:
            saleDm = brokerDm

        tradeCodeDm = self._calculateTradeCodeDm(
            rules=rules,
            world=world,
            tradeCodeDmMap=self._data.buyTradeCodeDmMap(),
            amberZoneDm=self._data.buyAmberZoneDm(),
            redZoneDm=self._data.buyRedZoneDm())
        if tradeCodeDm:
            purchaseDm = common.Calculator.add(
                lhs=buyerDm,
                rhs=tradeCodeDm)
        else:
            purchaseDm = buyerDm

        worldDm = common.Calculator.subtract(
            lhs=saleDm,
            rhs=purchaseDm)

        if known3D6Roll:
            randomDm = known3D6Roll
            randomDm = common.Calculator.equals(
                value=randomDm,
                name='Random Sale DM')
        else:
            randomDm = common.Calculator.floor(
                value=self._ValueRangeOf3D6,
                name='Random Sale DM')

        return common.Calculator.add(
            lhs=randomDm,
            rhs=worldDm,
            name='Sale DM')

    def calculateSalePrice(
            self,
            rules: traveller.Rules,
            world: astronomer.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            buyerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        saleDm = self.calculateTotalSaleDm(
            rules=rules,
            world=world,
            brokerDm=brokerDm,
            buyerDm=buyerDm,
            known3D6Roll=known3D6Roll)

        if isinstance(saleDm, common.ScalarCalculation):
            priceModifier = common.ScalarCalculation(
                value=_calculateSalePriceModifier(
                    ruleSystem=rules.system(),
                    saleDm=saleDm),
                name='Base Price Scale')
        else:
            priceModifier = common.RangeCalculation(
                worstCase=_calculateSalePriceModifier(
                    ruleSystem=rules.system(),
                    saleDm=saleDm.worstCaseCalculation()),
                bestCase=_calculateSalePriceModifier(
                    ruleSystem=rules.system(),
                    saleDm=saleDm.bestCaseCalculation()),
                averageCase=_calculateSalePriceModifier(
                    ruleSystem=rules.system(),
                    saleDm=saleDm.averageCaseCalculation()),
                name='Base Price Scale')

        return common.Calculator.multiply(
            lhs=self._data.basePrice(),
            rhs=priceModifier,
            name='Sale Price Per Ton')

    def _calculateTradeCodeDm(
            self,
            rules: traveller.Rules,
            world: astronomer.World,
            tradeCodeDmMap: typing.Mapping[traveller.TradeCode, common.ScalarCalculation],
            amberZoneDm: typing.Optional[common.ScalarCalculation],
            redZoneDm: typing.Optional[common.ScalarCalculation]
            ) -> typing.Optional[common.ScalarCalculation]:
        largestDm = None
        for tradeCode in world.tradeCodes(rules=rules):
            tradeCodeDm = tradeCodeDmMap.get(tradeCode)
            if tradeCodeDm is not None:
                largestDm = self._compareTradeCodeDm(
                    world=world,
                    newDm=tradeCodeDm,
                    largestDm=largestDm)

        zone = world.zone()
        if zone is astronomer.ZoneType.AmberZone:
            largestDm = self._compareTradeCodeDm(
                world=world,
                newDm=amberZoneDm,
                largestDm=largestDm)
        elif zone is astronomer.ZoneType.RedZone:
            largestDm = self._compareTradeCodeDm(
                world=world,
                newDm=redZoneDm,
                largestDm=largestDm)

        # Note that largestModifier will be None if there are no applicable trade codes
        return largestDm

    def _compareTradeCodeDm(
            self,
            world: astronomer.World,
            newDm: typing.Optional[common.ScalarCalculation],
            largestDm: typing.Optional[common.ScalarCalculation]
            ) -> typing.Optional[common.ScalarCalculation]:
        if newDm is None:
            return largestDm

        if self.isWorldIllegal(world):
            # The trade good is illegal on the world due to its law level
            newDm = self._calculateWorldIllegalDm(
                world=world,
                baseDm=newDm)

        if largestDm is None:
            return newDm

        return common.Calculator.max(
            lhs=largestDm,
            rhs=newDm)

    # The MGT2 rules says, for goods that are illegal because of the world law level, the DM should
    # be the difference between the law level of the world and the law level the trade good becomes
    # illegal. If the item is also universally illegal the largest of the two DMs is used
    def _calculateWorldIllegalDm(
            self,
            world: astronomer.World,
            baseDm: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        worldLawLevel = common.ScalarCalculation(
            value=world.uwp().numeric(astronomer.UWP.Element.LawLevel, default=-1),
            name='World Law Level')
        illegalLawLevel = common.ScalarCalculation(
            value=self._data.illegalLawLevel(),
            name='Law Level Item Becomes Illegal')
        worldIllegalDm = common.Calculator.subtract(
            lhs=worldLawLevel,
            rhs=illegalLawLevel,
            name='World Legality DM')

        if self.isUniversallyIllegal():
            worldIllegalDm = common.Calculator.max(
                lhs=baseDm,
                rhs=worldIllegalDm,
                name='Illegal Goods Trade DM')

        return worldIllegalDm

class TradeDMToPriceModifierFunction(common.CalculatorFunction):
    def __init__(
            self,
            tradeType: TradeType,
            tradeDm: common.ScalarCalculation,
            priceModifier: common.ScalarCalculation
            ) -> None:
        self._tradeType = tradeType
        self._tradeDm = tradeDm
        self._priceModifier = priceModifier

    def value(self) -> typing.Union[int, float]:
        return self._priceModifier.value()

    def calculationString(
            self,
            outerBrackets: bool,
            decimalPlaces: int = 2
            ) -> str:
        valueString = self._tradeDm.name(forCalculation=True)
        if not valueString:
            valueString = self._tradeDm.calculationString(
                outerBrackets=False,
                decimalPlaces=decimalPlaces)
        return f'{self._tradeType.value}PriceScaleForDM({valueString})'

    def calculations(self) -> typing.List[common.ScalarCalculation]:
        if self._tradeDm.name():
            return [self._tradeDm]
        return self._tradeDm.subCalculations()

    @staticmethod
    def serialisationType() -> str:
        return 'tradedm'

    def toJson(self) -> typing.Mapping[str, typing.Any]:
        return {
            'type': _TradeTypeSerialisationTypeToStr[self._tradeType],
            'value': common.serialiseCalculation(self._tradeDm, includeVersion=False),
            'modifier': common.serialiseCalculation(self._priceModifier, includeVersion=False)}

    @staticmethod
    def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'TradeDMToPriceModifierFunction':
        type = jsonData.get('type')
        if type is None:
            raise RuntimeError('Trade DM function is missing the type property')
        if not isinstance(type, str):
            raise RuntimeError('Trade DM function type property is not a string')
        type = type.lower()
        if type not in _TradeTypeSerialisationStrToType:
            raise RuntimeError(f'Trade DM function has invalid type property {type}')
        type = _TradeTypeSerialisationStrToType[type]

        value = jsonData.get('value')
        if value is None:
            raise RuntimeError('Trade DM function is missing the value property')
        value = common.deserialiseCalculation(jsonData=value)

        modifier = jsonData.get('modifier')
        if modifier is None:
            raise RuntimeError('Trade DM function is missing the modifier property')
        modifier = common.deserialiseCalculation(jsonData=modifier)

        return TradeDMToPriceModifierFunction(
            tradeType=type,
            tradeDm=value,
            priceModifier=modifier)

def tradeGoodList(
        ruleSystem: traveller.RuleSystem,
        excludeTradeGoods: typing.Optional[typing.Iterable[TradeGood]] = None
        ) -> typing.Iterable[TradeGood]:
    # Always return a copy so nothing messes with master trade code lists
    if ruleSystem == traveller.RuleSystem.MGT:
        tradeGoods = _MgtTradeGoods.copy()
    elif ruleSystem == traveller.RuleSystem.MGT2:
        tradeGoods = _Mgt2TradeGoods.copy()
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        tradeGoods = _Mgt2022TradeGoods.copy()
    else:
        assert(False)

    if excludeTradeGoods:
        for excludedTradeGood in excludeTradeGoods:
            try:
                tradeGoods.remove(excludedTradeGood)
            except ValueError:
                pass
    return tradeGoods

def tradeGoodFromId(
        ruleSystem: traveller.RuleSystem,
        tradeGoodId: int
        ) -> TradeGood:
    if ruleSystem == traveller.RuleSystem.MGT:
        return _MgtTradeGoodsMap[tradeGoodId]
    elif ruleSystem == traveller.RuleSystem.MGT2:
        return _Mgt2TradeGoodsMap[tradeGoodId]
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        return _Mgt2022TradeGoodsMap[tradeGoodId]
    else:
        assert(False)

def worldTradeGoods(
        rules: traveller.Rules,
        world: astronomer.World,
        includeLegal: bool,
        includeIllegal: bool
        ) -> typing.List[TradeGood]:
    ruleSystem = rules.system()
    if ruleSystem == traveller.RuleSystem.MGT:
        tradeGoods = _MgtTradeGoods
    elif ruleSystem == traveller.RuleSystem.MGT2:
        tradeGoods = _Mgt2TradeGoods
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        tradeGoods = _Mgt2022TradeGoods
    else:
        assert(False)

    available = []
    for tradeGood in tradeGoods:
        # There is an ambiguity around exotics as they can be legal or illegal. It doesn't apply
        # here though as exotics don't have standard availability so wouldn't pass the check for
        # availability anyway
        isIllegal = tradeGood.isIllegal(world)
        if (isIllegal and not includeIllegal) or (not isIllegal and not includeLegal):
            continue
        if tradeGood.checkTradeGoodAvailability(rules=rules, world=world):
            available.append(tradeGood)
    return available

def worldCargoQuantityModifiers(
        ruleSystem: traveller.RuleSystem,
        world: astronomer.World
        ) -> typing.Iterable[common.ScalarCalculation]:
    modifiers = []

    if ruleSystem != traveller.RuleSystem.MGT2022:
        return modifiers # Modifiers only apply for 2022 rules

    # In Mongoose 2022 rules, the amount of cargo available is affected by population. Worlds with
    # a population <= 3 get DM-3 modifier to the available quantity roll. Worlds with a population
    # >= 9 get a DM+3 modifier. Note that this can cause an available quantity of <= 0
    # If population is unknown, assume 0 to be pessimistic.
    population = world.uwp().numeric(astronomer.UWP.Element.Population, default=0)
    if population <= 3:
        modifiers.append(common.ScalarCalculation(
            value=-3,
            name='Modified For Low Population'))
    elif population >= 9:
        modifiers.append(common.ScalarCalculation(
            value=+3,
            name='Modified For High Population'))

    return modifiers

def calculateWorldTradeGoodQuantity(
        ruleSystem: traveller.RuleSystem,
        world: astronomer.World,
        tradeGood: TradeGood,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> common.ScalarCalculation:
    if diceRoller:
        diceRoll = diceRoller.makeRoll(
            dieCount=tradeGood.availableTonsD6Count(),
            name=f'{tradeGood.name()} Quantity Roll')
    else:
        # When calculating availability we round down dice roll probabilities to be pessimistic
        diceRoll = common.Calculator.floor(
            value=common.calculateValueRangeForDice(
                dieCount=tradeGood.availableTonsD6Count(),
                higherIsBetter=True),
            name=f'{tradeGood.name()} Quantity Roll')

    # Note that these are dice modifiers so are applied to the roll before it's multiplied
    worldModifiers = worldCargoQuantityModifiers(ruleSystem=ruleSystem, world=world)
    if worldModifiers:
        totalModifier = common.Calculator.sum(
            values=worldModifiers,
            name=f'{world.name(includeSubsector=True)} Quantity DM')
        diceRoll = common.Calculator.max(
            lhs=common.Calculator.add(lhs=diceRoll, rhs=totalModifier),
            rhs=common.ScalarCalculation(value=0, name='Minimum Quantity'),
            name=f'{tradeGood.name()} Modified Quantity Roll')

    quantity = common.Calculator.multiply(
        lhs=diceRoll,
        rhs=tradeGood.availableTonsMultiplier(),
        name=f'{tradeGood.name()} Quantity')

    return quantity

def _calculatePurchasePriceModifier(
        ruleSystem: traveller.RuleSystem,
        purchaseDm: typing.Union[int, common.ScalarCalculation],
        ) -> common.ScalarCalculation:
    if not isinstance(purchaseDm, common.ScalarCalculation):
        purchaseDm = common.ScalarCalculation(
            value=purchaseDm,
            name='Purchase DM')

    return _calculatePriceModifier(
        ruleSystem=ruleSystem,
        operation=TradeType.Purchase,
        tradeDm=purchaseDm)

def _calculateSalePriceModifier(
        ruleSystem: traveller.RuleSystem,
        saleDm: typing.Union[int, common.ScalarCalculation]
        ) -> common.ScalarCalculation:
    if not isinstance(saleDm, common.ScalarCalculation):
        saleDm = common.ScalarCalculation(
            value=saleDm,
            name='Sale DM')

    return _calculatePriceModifier(
        ruleSystem=ruleSystem,
        operation=TradeType.Sale,
        tradeDm=saleDm)

def _calculatePriceModifier(
        ruleSystem: traveller.RuleSystem,
        operation: TradeType,
        tradeDm: common.ScalarCalculation
        ) -> common.ScalarCalculation:
    if ruleSystem == traveller.RuleSystem.MGT:
        modifierMap = _MgtPriceModifierMap
        minDm = _MgtMinPriceModifierDm
        maxDm = _MgtMaxPriceModifierDm
    elif ruleSystem == traveller.RuleSystem.MGT2:
        modifierMap = _Mgt2PriceModifierMap
        minDm = _Mgt2MinPriceModifierDm
        maxDm = _Mgt2MaxPriceModifierDm
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        modifierMap = _Mgt2022PriceModifierMap
        minDm = _Mgt2022MinPriceModifierDm
        maxDm = _Mgt2022MaxPriceModifierDm
    else:
        assert(False)

    if tradeDm.value() < minDm:
        priceModifier = modifierMap[minDm][operation]
    elif tradeDm.value() > maxDm:
        priceModifier = modifierMap[maxDm][operation]
    else:
        priceModifier = modifierMap[tradeDm.value()][operation]

    priceModifier = common.ScalarCalculation(
        value=priceModifier,
        name=f'Price Modifier for {operation.value} DM{tradeDm.value():+}')

    return common.ScalarCalculation(
        value=TradeDMToPriceModifierFunction(
            tradeType=operation,
            tradeDm=tradeDm,
            priceModifier=priceModifier),
        name=f'{operation} Price Modifier')

class TradeGoodIds:
    CommonElectronics = 11
    CommonIndustrialGoods = 12
    CommonManufacturedGoods = 13
    CommonRawMaterials = 14
    CommonConsumables = 15
    CommonOre = 16
    AdvancedElectronics = 21
    AdvancedMachineParts = 22
    AdvancedManufacturedGoods = 23
    AdvancedWeapons = 24
    AdvancedVehicles = 25
    Biochemicals = 26
    CrystalsAndGems = 31
    Cybernetics = 32
    LiveAnimals = 33
    LuxuryConsumables = 34
    LuxuryGoods = 35
    MedicalSupplies = 36
    Petrochemicals = 41
    Pharmaceuticals = 42
    Polymers = 43
    PreciousMetals = 44
    Radioactives = 45
    Robots = 46
    Spices = 51
    Textiles = 52
    UncommonOre = 53
    UncommonRawMaterials = 54
    Wood = 55
    Vehicles = 56
    IllegalBiochemicals = 61
    IllegalCybernetics = 62
    IllegalDrugs = 63
    IllegalLuxuries = 64
    IllegalWeapons = 65
    Exotics = 66

 # ██████   ██████   █████████  ███████████  ████████     ███████████   █████  █████ █████       ██████████  █████████
 # ░░██████ ██████   ███░░░░░███░█░░░███░░░█ ███░░░░███   ░░███░░░░░███ ░░███  ░░███ ░░███       ░░███░░░░░█ ███░░░░░███
 #  ░███░█████░███  ███     ░░░ ░   ░███  ░ ░░░    ░███    ░███    ░███  ░███   ░███  ░███        ░███  █ ░ ░███    ░░░
 #  ░███░░███ ░███ ░███             ░███       ███████     ░██████████   ░███   ░███  ░███        ░██████   ░░█████████
 #  ░███ ░░░  ░███ ░███    █████    ░███      ███░░░░      ░███░░░░░███  ░███   ░███  ░███        ░███░░█    ░░░░░░░░███
 #  ░███      ░███ ░░███  ░░███     ░███     ███      █    ░███    ░███  ░███   ░███  ░███      █ ░███ ░   █ ███    ░███
 #  █████     █████ ░░█████████     █████   ░██████████    █████   █████ ░░████████   ███████████ ██████████░░█████████
 # ░░░░░     ░░░░░   ░░░░░░░░░     ░░░░░    ░░░░░░░░░░    ░░░░░   ░░░░░   ░░░░░░░░   ░░░░░░░░░░░ ░░░░░░░░░░  ░░░░░░░░░


_Mgt2TradeGoodData = [
    _TradeGoodDefinition(
        id=TradeGoodIds.CommonElectronics,
        name='Common Electronics',
        basePrice=20000,
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3,
            traveller.TradeCode.RichWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.LowTechWorld: 1,
            traveller.TradeCode.PoorWorld: 1
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=10), # 2D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonIndustrialGoods,
        name='Common Industrial Goods',
        basePrice=10000,
        buyTradeCodeDmMap={
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.AgriculturalWorld: 2
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=10), # 2D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonManufacturedGoods,
        name='Common Manufactured Goods',
        basePrice=20000,
        buyTradeCodeDmMap={
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=10), # 2D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonRawMaterials,
        name='Common Raw Materials',
        basePrice=5000,
        buyTradeCodeDmMap={
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.GardenWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 2
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=20), # 2D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonConsumables,
        name='Common Consumables',
        basePrice=500,
        buyTradeCodeDmMap={
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.WaterWorld: 2,
                traveller.TradeCode.GardenWorld: 1,
                traveller.TradeCode.AsteroidBelt: -4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.FluidWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=20), # 2D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonOre,
        name='Common Ore',
        basePrice=1000,
        buyTradeCodeDmMap={
                traveller.TradeCode.AsteroidBelt: 4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=2,
        availableTonsMultiplier=20), # 2D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedElectronics,
        name='Advanced Electronics',
        basePrice=100000,
        availabilityTradeCodes=[
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 1,
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.AsteroidBelt: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedMachineParts,
        name='Advanced Machine Parts',
        basePrice=75000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedManufacturedGoods,
        name='Advanced Manufactured Goods',
        basePrice=100000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedWeapons,
        name='Advanced Weapons',
        basePrice=150000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.PoorWorld: 1
        },
        sellAmberZoneDm=2,
        sellRedZoneDm=4,
        # It's not clear if advanced weapons should be world illegal and, if so, at
        # what law level. As it's so unclear I've chosen to not make it world illegal
        illegalLawLevel=None,
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedVehicles,
        name='Advanced Vehicles',
        basePrice=180000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Biochemicals,
        name='Biochemicals',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.WaterWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.CrystalsAndGems,
        name='Crystals & Gems',
        basePrice=20000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.IceCappedWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.RichWorld: 2,
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Cybernetics,
        name='Cybernetics',
        basePrice=250000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.LiveAnimals,
        name='Live Animals',
        basePrice=10000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.LowPopulationWorld: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.LuxuryConsumables,
        name='Luxury Consumables',
        basePrice=20000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.LuxuryGoods,
        name='Luxury Goods',
        basePrice=200000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighPopulationWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 4
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.MedicalSupplies,
        name='Medical Supplies',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld,
            traveller.TradeCode.HighPopulationWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.RichWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Petrochemicals,
        name='Petrochemicals',
        basePrice=10000,
        availabilityTradeCodes=[
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.FluidWorld,
            traveller.TradeCode.IceCappedWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.DesertWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.LowTechWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Pharmaceuticals,
        name='Pharmaceuticals',
        basePrice=100000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.HighPopulationWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.LowTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Polymers,
        name='Polymers',
        basePrice=7000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.PreciousMetals,
        name='Precious Metals',
        basePrice=50000,
        availabilityTradeCodes=[
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.IceCappedWorld,
                traveller.TradeCode.FluidWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 3,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 2,
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Radioactives,
        name='Radioactives',
        basePrice=1000000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.LowPopulationWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.LowPopulationWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.HighTechWorld: 1,
            traveller.TradeCode.NonIndustrialWorld: -2,
            traveller.TradeCode.AgriculturalWorld: -3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Robots,
        name='Robots',
        basePrice=400000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Spices,
        name='Spices',
        basePrice=6000,
        availabilityTradeCodes=[
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.DesertWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 2,
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.PoorWorld: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Textiles,
        name='Textiles',
        basePrice=3000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.NonIndustrialWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 7
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 3,
            traveller.TradeCode.NonAgriculturalWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.UncommonOre,
        name='Uncommon Ore',
        basePrice=5000,
        availabilityTradeCodes=[
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.IceCappedWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.UncommonRawMaterials,
        name='Uncommon Raw Materials',
        basePrice=20000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Wood,
        name='Wood',
        basePrice=1000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 6
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.IndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.Vehicles,
        name='Vehicles',
        basePrice=15000,
        availabilityTradeCodes=[
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalBiochemicals,
        name='Illegal Biochemicals',
        basePrice=50000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.WaterWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 6
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalCybernetics,
        name='Illegal Cybernetics',
        basePrice=250000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 4,
            traveller.TradeCode.IceCappedWorld: 4,
            traveller.TradeCode.RichWorld: 8
        },
        sellAmberZoneDm=6,
        sellRedZoneDm=6,
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalDrugs,
        name='Illegal Drugs',
        basePrice=100000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.HighPopulationWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.GardenWorld: 1,
            traveller.TradeCode.WaterWorld: 1,
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 6
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalLuxuries,
        name='Illegal Luxuries',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 4
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalWeapons,
        name='Illegal Weapons',
        basePrice=150000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.PoorWorld: 6
        },
        sellAmberZoneDm=8,
        sellRedZoneDm=10,
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    # Exotics are a weird case that the rule book says require roll playing,
    # this entry is just here as a place holder to capture the fact they exist
    # Note: The availability is set to an empty list which means no availability
    # based on world TradeCodes, this is different to None which is used elsewhere
    # to indicate availability everywhere
    _TradeGoodDefinition(
        id=TradeGoodIds.Exotics,
        name='Exotics',
        basePrice=0,
        availableTonsD6Count=0,
        availableTonsMultiplier=0)
]

_Mgt2TradeGoods = [TradeGood(system=traveller.RuleSystem.MGT2, data=data) for data in _Mgt2TradeGoodData]
_Mgt2TradeGoodsMap = {x.id(): x for x in _Mgt2TradeGoods}
assert(len(_Mgt2TradeGoodsMap) == len(_Mgt2TradeGoods)) # Check for duplicate ids

# Values are in percent of base price
_Mgt2MinPriceModifierDm = -1
_Mgt2MaxPriceModifierDm = 23
_Mgt2PriceModifierMap = {
    -1: {
        TradeType.Purchase: 2.0,
        TradeType.Sale: 0.3
    },
    0: {
        TradeType.Purchase: 1.75,
        TradeType.Sale: 0.4
    },
    1: {
        TradeType.Purchase: 1.5,
        TradeType.Sale: 0.45
    },
    2: {
        TradeType.Purchase: 1.35,
        TradeType.Sale: 0.5
    },
    3: {
        TradeType.Purchase: 1.25,
        TradeType.Sale: 0.55
    },
    4: {
        TradeType.Purchase: 1.2,
        TradeType.Sale: 0.6
    },
    5: {
        TradeType.Purchase: 1.15,
        TradeType.Sale: 0.65
    },
    6: {
        TradeType.Purchase: 1.1,
        TradeType.Sale: 0.70
    },
    7: {
        TradeType.Purchase: 1.05,
        TradeType.Sale: 0.75
    },
    8: {
        TradeType.Purchase: 1.0,
        TradeType.Sale: 0.8
    },
    9: {
        TradeType.Purchase: 0.95,
        TradeType.Sale: 0.85
    },
    10: {
        TradeType.Purchase: 0.9,
        TradeType.Sale: 0.9
    },
    11: {
        TradeType.Purchase: 0.85,
        TradeType.Sale: 1.0
    },
    12: {
        TradeType.Purchase: 0.8,
        TradeType.Sale: 1.05
    },
    13: {
        TradeType.Purchase: 0.75,
        TradeType.Sale: 1.1
    },
    14: {
        TradeType.Purchase: 0.7,
        TradeType.Sale: 1.15
    },
    15: {
        TradeType.Purchase: 0.65,
        TradeType.Sale: 1.2
    },
    16: {
        TradeType.Purchase: 0.60,
        TradeType.Sale: 1.25
    },
    17: {
        TradeType.Purchase: 0.55,
        TradeType.Sale: 1.3
    },
    18: {
        TradeType.Purchase: 0.5,
        TradeType.Sale: 1.35
    },
    19: {
        TradeType.Purchase: 0.45,
        TradeType.Sale: 1.4
    },
    20: {
        TradeType.Purchase: 0.4,
        TradeType.Sale: 1.45
    },
    21: {
        TradeType.Purchase: 0.35,
        TradeType.Sale: 1.5
    },
    22: {
        TradeType.Purchase: 0.3,
        TradeType.Sale: 1.55
    },
    23: {
        TradeType.Purchase: 0.25,
        TradeType.Sale: 1.60
    }
}


#  ██████   ██████   █████████  ███████████    ███████████   █████  █████ █████       ██████████  █████████
# ░░██████ ██████   ███░░░░░███░█░░░███░░░█   ░░███░░░░░███ ░░███  ░░███ ░░███       ░░███░░░░░█ ███░░░░░███
#  ░███░█████░███  ███     ░░░ ░   ░███  ░     ░███    ░███  ░███   ░███  ░███        ░███  █ ░ ░███    ░░░
#  ░███░░███ ░███ ░███             ░███        ░██████████   ░███   ░███  ░███        ░██████   ░░█████████
#  ░███ ░░░  ░███ ░███    █████    ░███        ░███░░░░░███  ░███   ░███  ░███        ░███░░█    ░░░░░░░░███
#  ░███      ░███ ░░███  ░░███     ░███        ░███    ░███  ░███   ░███  ░███      █ ░███ ░   █ ███    ░███
#  █████     █████ ░░█████████     █████       █████   █████ ░░████████   ███████████ ██████████░░█████████
# ░░░░░     ░░░░░   ░░░░░░░░░     ░░░░░       ░░░░░   ░░░░░   ░░░░░░░░   ░░░░░░░░░░░ ░░░░░░░░░░  ░░░░░░░░░

_MgtTradeGoodData = [
    _TradeGoodDefinition(
        id=TradeGoodIds.CommonElectronics,
        name='Basic Electronics',
        basePrice=10000,
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3,
            traveller.TradeCode.RichWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.LowTechWorld: 1,
            traveller.TradeCode.PoorWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonIndustrialGoods,
        name='Basic Machine Parts',
        basePrice=10000,
        buyTradeCodeDmMap={
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.AgriculturalWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonManufacturedGoods,
        name='Basic Manufactured Goods',
        basePrice=10000,
        buyTradeCodeDmMap={
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonRawMaterials,
        name='Basic Raw Materials',
        basePrice=5000,
        buyTradeCodeDmMap={
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.GardenWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonConsumables,
        name='Basic Consumables',
        basePrice=2000,
        buyTradeCodeDmMap={
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.WaterWorld: 2,
                traveller.TradeCode.GardenWorld: 1,
                traveller.TradeCode.AsteroidBelt: -4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.FluidWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.CommonOre,
        name='Basic Ore',
        basePrice=1000,
        buyTradeCodeDmMap={
                traveller.TradeCode.AsteroidBelt: 4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedElectronics,
        name='Advanced Electronics',
        basePrice=100000,
        availabilityTradeCodes=[
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 1,
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.AsteroidBelt: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedMachineParts,
        name='Advanced Machine Parts',
        basePrice=75000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedManufacturedGoods,
        name='Advanced Manufactured Goods',
        basePrice=100000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedWeapons,
        name='Advanced Weapons',
        basePrice=150000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.PoorWorld: 1
        },
        sellAmberZoneDm=2,
        sellRedZoneDm=4,
        # It's not clear if advanced weapons should be world illegal and, if so, at
        # what law level. As it's so unclear I've chosen to not make it world illegal
        illegalLawLevel=None,
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.AdvancedVehicles,
        name='Advanced Vehicles',
        basePrice=180000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Biochemicals,
        name='Biochemicals',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.WaterWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.CrystalsAndGems,
        name='Crystals & Gems',
        basePrice=20000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.IceCappedWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.RichWorld: 2,
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Cybernetics,
        name='Cybernetics',
        basePrice=250000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.LiveAnimals,
        name='Live Animals',
        basePrice=10000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.LowPopulationWorld: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.LuxuryConsumables,
        name='Luxury Consumables',
        basePrice=20000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.LuxuryGoods,
        name='Luxury Goods',
        basePrice=200000,
        availabilityTradeCodes=[
                traveller.TradeCode.HighPopulationWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 4
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.MedicalSupplies,
        name='Medical Supplies',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld,
            traveller.TradeCode.HighPopulationWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.RichWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Petrochemicals,
        name='Petrochemicals',
        basePrice=10000,
        availabilityTradeCodes=[
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.FluidWorld,
            traveller.TradeCode.IceCappedWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.DesertWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.LowTechWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Pharmaceuticals,
        name='Pharmaceuticals',
        basePrice=100000,
        availabilityTradeCodes=[
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.HighPopulationWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.LowTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Polymers,
        name='Polymers',
        basePrice=7000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.PreciousMetals,
        name='Precious Metals',
        basePrice=50000,
        availabilityTradeCodes=[
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.IceCappedWorld,
                traveller.TradeCode.FluidWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 3,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 2,
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Radioactives,
        name='Radioactives',
        basePrice=1000000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.LowPopulationWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.LowPopulationWorld: -4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.HighTechWorld: 1,
            traveller.TradeCode.NonIndustrialWorld: -2,
            traveller.TradeCode.AgriculturalWorld: -3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.Robots,
        name='Robots',
        basePrice=400000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.Spices,
        name='Spices',
        basePrice=6000,
        availabilityTradeCodes=[
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.DesertWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 2,
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.PoorWorld: 3
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Textiles,
        name='Textiles',
        basePrice=3000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.NonIndustrialWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 7
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.HighPopulationWorld: 3,
            traveller.TradeCode.NonAgriculturalWorld: 2
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.UncommonOre,
        name='Uncommon Ore',
        basePrice=5000,
        availabilityTradeCodes=[
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.IceCappedWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 4
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=20), # 1D x 20

    _TradeGoodDefinition(
        id=TradeGoodIds.UncommonRawMaterials,
        name='Uncommon Raw Materials',
        basePrice=20000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Wood,
        name='Wood',
        basePrice=1000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 6
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.IndustrialWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.Vehicles,
        name='Vehicles',
        basePrice=15000,
        availabilityTradeCodes=[
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        availableTonsD6Count=1,
        availableTonsMultiplier=10), # 1D x 10

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalBiochemicals,
        name='Illegal Biochemicals',
        basePrice=50000,
        availabilityTradeCodes=[
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.WaterWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.IndustrialWorld: 6
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalCybernetics,
        name='Illegal Cybernetics',
        basePrice=250000,
        availabilityTradeCodes=[
            traveller.TradeCode.HighTechWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.AsteroidBelt: 4,
            traveller.TradeCode.IceCappedWorld: 4,
            traveller.TradeCode.RichWorld: 8
        },
        sellAmberZoneDm=6,
        sellRedZoneDm=6,
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalDrugs,
        name='Illegal Drugs',
        basePrice=100000,
        availabilityTradeCodes=[
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.HighPopulationWorld,
            traveller.TradeCode.WaterWorld
        ],
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 6
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalLuxuries,
        name='Illegal Luxuries',
        basePrice=50000,
        availabilityTradeCodes=[
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.WaterWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 4
        },
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=1), # 1D x 1

    _TradeGoodDefinition(
        id=TradeGoodIds.IllegalWeapons,
        name='Illegal Weapons',
        basePrice=150000,
        availabilityTradeCodes=[
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        buyTradeCodeDmMap={
            traveller.TradeCode.HighTechWorld: 2
        },
        sellTradeCodeDmMap={
            traveller.TradeCode.PoorWorld: 6
        },
        sellAmberZoneDm=8,
        sellRedZoneDm=10,
        illegalLawLevel=0, # Illegal at all law levels
        availableTonsD6Count=1,
        availableTonsMultiplier=5), # 1D x 5

    # Exotics are a weird case that the rule book says require roll playing,
    # this entry is just here as a place holder to capture the fact they exist
    # Note: The availability is set to an empty list which means no availability
    # based on world TradeCodes, this is different to None which is used elsewhere
    # to indicate availability everywhere
    _TradeGoodDefinition(
        id=TradeGoodIds.Exotics,
        name='Exotics',
        basePrice=0,
        availableTonsD6Count=0,
        availableTonsMultiplier=0)
]

_MgtTradeGoods = [TradeGood(system=traveller.RuleSystem.MGT, data=data) for data in _MgtTradeGoodData]

_MgtTradeGoodsMap = {x.id(): x for x in _MgtTradeGoods}
assert(len(_MgtTradeGoodsMap) == len(_MgtTradeGoods)) # Check for duplicate ids

# Values are in percent of base price
_MgtMinPriceModifierDm = -1
_MgtMaxPriceModifierDm = 21
_MgtPriceModifierMap = {
    -1: {
        TradeType.Purchase: 4.0,
        TradeType.Sale: 0.25
    },
    0: {
        TradeType.Purchase: 3.0,
        TradeType.Sale: 0.45
    },
    1: {
        TradeType.Purchase: 2.0,
        TradeType.Sale: 0.5
    },
    2: {
        TradeType.Purchase: 1.75,
        TradeType.Sale: 0.55
    },
    3: {
        TradeType.Purchase: 1.5,
        TradeType.Sale: 0.6
    },
    4: {
        TradeType.Purchase: 1.35,
        TradeType.Sale: 0.65
    },
    5: {
        TradeType.Purchase: 1.25,
        TradeType.Sale: 0.75
    },
    6: {
        TradeType.Purchase: 1.2,
        TradeType.Sale: 0.8
    },
    7: {
        TradeType.Purchase: 1.15,
        TradeType.Sale: 0.85
    },
    8: {
        TradeType.Purchase: 1.1,
        TradeType.Sale: 0.9
    },
    9: {
        TradeType.Purchase: 1.05,
        TradeType.Sale: 0.95
    },
    10: {
        TradeType.Purchase: 1.0,
        TradeType.Sale: 1.0
    },
    11: {
        TradeType.Purchase: 0.95,
        TradeType.Sale: 1.05
    },
    12: {
        TradeType.Purchase: 0.9,
        TradeType.Sale: 1.1
    },
    13: {
        TradeType.Purchase: 0.85,
        TradeType.Sale: 1.15
    },
    14: {
        TradeType.Purchase: 0.8,
        TradeType.Sale: 1.2
    },
    15: {
        TradeType.Purchase: 0.75,
        TradeType.Sale: 1.25
    },
    16: {
        TradeType.Purchase: 0.70,
        TradeType.Sale: 1.35
    },
    17: {
        TradeType.Purchase: 0.65,
        TradeType.Sale: 1.5
    },
    18: {
        TradeType.Purchase: 0.55,
        TradeType.Sale: 1.75
    },
    19: {
        TradeType.Purchase: 0.5,
        TradeType.Sale: 2.0
    },
    20: {
        TradeType.Purchase: 0.4,
        TradeType.Sale: 3.0
    },
    21: {
        TradeType.Purchase: 0.25,
        TradeType.Sale: 4.0
    }
}


# ██████   ██████   █████████  ███████████     ████████     █████     ████████   ████████
#░░██████ ██████   ███░░░░░███░█░░░███░░░█    ███░░░░███  ███░░░███  ███░░░░███ ███░░░░███
# ░███░█████░███  ███     ░░░ ░   ░███  ░    ░░░    ░███ ███   ░░███░░░    ░███░░░    ░███
# ░███░░███ ░███ ░███             ░███          ███████ ░███    ░███   ███████    ███████
# ░███ ░░░  ░███ ░███    █████    ░███         ███░░░░  ░███    ░███  ███░░░░    ███░░░░
# ░███      ░███ ░░███  ░░███     ░███        ███      █░░███   ███  ███      █ ███      █
# █████     █████ ░░█████████     █████      ░██████████ ░░░█████░  ░██████████░██████████
#░░░░░     ░░░░░   ░░░░░░░░░     ░░░░░       ░░░░░░░░░░    ░░░░░░   ░░░░░░░░░░ ░░░░░░░░░░

# Mongoose 2022 rules use the same Trade Good definitions as 2e
_Mgt2022TradeGoods = [TradeGood(system=traveller.RuleSystem.MGT2022, data=data) for data in _Mgt2TradeGoodData]
_Mgt2022TradeGoodsMap = {x.id(): x for x in _Mgt2022TradeGoods}
assert(len(_Mgt2022TradeGoodsMap) == len(_Mgt2022TradeGoods)) # Check for duplicate ids

# Values are in percent of base price
_Mgt2022MinPriceModifierDm = -3
_Mgt2022MaxPriceModifierDm = 25
_Mgt2022PriceModifierMap = {
    -3: {
        TradeType.Purchase: 3.0,
        TradeType.Sale: 0.1
    },
    -2: {
        TradeType.Purchase: 2.5,
        TradeType.Sale: 0.2
    },
    -1: {
        TradeType.Purchase: 2.0,
        TradeType.Sale: 0.3
    },
    0: {
        TradeType.Purchase: 1.75,
        TradeType.Sale: 0.4
    },
    1: {
        TradeType.Purchase: 1.5,
        TradeType.Sale: 0.45
    },
    2: {
        TradeType.Purchase: 1.35,
        TradeType.Sale: 0.5
    },
    3: {
        TradeType.Purchase: 1.25,
        TradeType.Sale: 0.55
    },
    4: {
        TradeType.Purchase: 1.2,
        TradeType.Sale: 0.6
    },
    5: {
        TradeType.Purchase: 1.15,
        TradeType.Sale: 0.65
    },
    6: {
        TradeType.Purchase: 1.1,
        TradeType.Sale: 0.70
    },
    7: {
        TradeType.Purchase: 1.05,
        TradeType.Sale: 0.75
    },
    8: {
        TradeType.Purchase: 1.0,
        TradeType.Sale: 0.8
    },
    9: {
        TradeType.Purchase: 0.95,
        TradeType.Sale: 0.85
    },
    10: {
        TradeType.Purchase: 0.9,
        TradeType.Sale: 0.9
    },
    11: {
        TradeType.Purchase: 0.85,
        TradeType.Sale: 1.0
    },
    12: {
        TradeType.Purchase: 0.8,
        TradeType.Sale: 1.05
    },
    13: {
        TradeType.Purchase: 0.75,
        TradeType.Sale: 1.1
    },
    14: {
        TradeType.Purchase: 0.7,
        TradeType.Sale: 1.15
    },
    15: {
        TradeType.Purchase: 0.65,
        TradeType.Sale: 1.2
    },
    16: {
        TradeType.Purchase: 0.60,
        TradeType.Sale: 1.25
    },
    17: {
        TradeType.Purchase: 0.55,
        TradeType.Sale: 1.3
    },
    18: {
        TradeType.Purchase: 0.5,
        TradeType.Sale: 1.4
    },
    19: {
        TradeType.Purchase: 0.45,
        TradeType.Sale: 1.5
    },
    20: {
        TradeType.Purchase: 0.4,
        TradeType.Sale: 1.6
    },
    21: {
        TradeType.Purchase: 0.35,
        TradeType.Sale: 1.75
    },
    22: {
        TradeType.Purchase: 0.3,
        TradeType.Sale: 2.0
    },
    23: {
        TradeType.Purchase: 0.25,
        TradeType.Sale: 2.5
    },
    24: {
        TradeType.Purchase: 0.20,
        TradeType.Sale: 3.0
    },
    25: {
        TradeType.Purchase: 0.15,
        TradeType.Sale: 4.0
    }
}
