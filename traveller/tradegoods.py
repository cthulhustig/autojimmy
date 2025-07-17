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

class _TradeGoodData(object):
    def __init__(
            self,
            id: int,
            name: str,
            basePrice: int,
            availabilityTradeCodes: typing.Iterable[traveller.TradeCode],
            purchaseTradeCodes: typing.Dict[traveller.TradeCode, int],
            saleTradeCodes: typing.Dict[traveller.TradeCode, int],
            illegalLawLevelCode: typing.Optional[str],
            availableTonsD6Count: int,
            availableTonsMultiplier: int
            ) -> None:
        self._id = id
        self._name = name
        self._basePrice = common.ScalarCalculation(
            value=basePrice,
            name=f'{name} Base Price')
        self._availabilityTradeCodes = availabilityTradeCodes

        self._purchaseTradeCodes = {}
        for tradeCode, tradeCodeDm in purchaseTradeCodes.items():
            self._purchaseTradeCodes[tradeCode] = common.ScalarCalculation(
                value=tradeCodeDm,
                name=f'{traveller.tradeCodeName(tradeCode)} Purchase DM')

        self._saleTradeCodes = {}
        for tradeCode, tradeCodeDm in saleTradeCodes.items():
            self._saleTradeCodes[tradeCode] = common.ScalarCalculation(
                value=tradeCodeDm,
                name=f'{traveller.tradeCodeName(tradeCode)} Sale DM')

        self._illegalLawLevel = None
        if illegalLawLevelCode:
            self._illegalLawLevel = traveller.ehexToInteger(
                value=illegalLawLevelCode,
                default=None)

        self._availableTonsD6Count = common.ScalarCalculation(
            value=availableTonsD6Count,
            name=f'{name} Available Quantity Die Count')

        self._availableTonsMultiplier = common.ScalarCalculation(
            value=availableTonsMultiplier,
            name=f'{name} Available Quantity Multiplier')

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def basePrice(self) -> common.ScalarCalculation:
        return self._basePrice

    def availabilityTradeCodes(self) -> typing.Iterable[traveller.TradeCode]:
        return self._availabilityTradeCodes

    def purchaseTradeCodes(self) -> typing.Dict[traveller.TradeCode, common.ScalarCalculation]:
        return self._purchaseTradeCodes

    def saleTradeCodes(self) -> typing.Dict[traveller.TradeCode, common.ScalarCalculation]:
        return self._saleTradeCodes

    def illegalLawLevel(self) -> typing.Optional[int]:
        return self._illegalLawLevel

    def availableTonsD6Count(self) -> common.ScalarCalculation:
        return self._availableTonsD6Count

    def availableTonsMultiplier(self) -> common.ScalarCalculation:
        return self._availableTonsMultiplier

class TradeGood(object):
    _ValueRangeOf3D6 = common.calculateValueRangeForDice(
        dieCount=3,
        higherIsBetter=True)

    def __init__(
            self,
            system: traveller.RuleSystem,
            data: _TradeGoodData
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
            world: traveller.World,
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
            world: traveller.World,
            ) -> bool:
        if not self._data.illegalLawLevel():
            # Note that it's intentional that this covers the cases where it's
            # None (i.e. legal everywhere) and 0 (i.e. it's universally illegal)
            return False

        # Check if the world law level is greater or equal to the law level where the trade goode
        # becomes illegal. If the law level is unknown use a default of -1 so that it will never be
        # higher (i.e. trade goods aren't world illegal if the law level is unknown)
        worldLawLevel = traveller.ehexToInteger(
            value=world.uwp().code(traveller.UWP.Element.LawLevel),
            default=-1)
        return worldLawLevel >= self._data.illegalLawLevel()

    def availableTonsD6Count(self) -> common.ScalarCalculation:
        return self._data.availableTonsD6Count()

    def availableTonsMultiplier(self) -> common.ScalarCalculation:
        return self._data.availableTonsMultiplier()

    def checkTradeGoodAvailability(
            self,
            world: traveller.World
            ) -> bool:
        availabilityTradeCodes = self._data.availabilityTradeCodes()
        if availabilityTradeCodes == None:
            # Trade goods with an availability set to None are available everywhere
            return True

        for tradeCode in world.tradeCodes():
            if tradeCode in availabilityTradeCodes:
                # The world has this trade good available due to the world trade codes
                return True
        return False

    def calculatePurchaseTradeCodeDm(
            self,
            world: traveller.World
            ) -> typing.Optional[common.ScalarCalculation]:
        return self._calculateTradeCodeDm(
            world=world,
            tradeCodeMap=self._data.purchaseTradeCodes())

    def calculateSaleTradeCodeDm(
            self,
            world: traveller.World
            ) -> typing.Optional[common.ScalarCalculation]:
        return self._calculateTradeCodeDm(
            world=world,
            tradeCodeMap=self._data.saleTradeCodes())

    def calculateTotalPurchaseDm(
            self,
            world: traveller.World,
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

        tradeCodeDm = self._calculateTradeCodeDm(world, self._data.purchaseTradeCodes())
        if tradeCodeDm:
            purchaseDm = common.Calculator.add(
                lhs=brokerDm,
                rhs=tradeCodeDm)
        else:
            purchaseDm = brokerDm

        tradeCodeDm = self._calculateTradeCodeDm(world, self._data.saleTradeCodes())
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
            world: traveller.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            sellerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        purchaseDm = self.calculateTotalPurchaseDm(
            world=world,
            brokerDm=brokerDm,
            sellerDm=sellerDm,
            known3D6Roll=known3D6Roll)

        if isinstance(purchaseDm, common.ScalarCalculation):
            priceModifier = common.ScalarCalculation(
                value=_calculatePurchasePriceModifier(
                    ruleSystem=self._system,
                    purchaseDm=purchaseDm),
                name='Base Price Scale')
        else:
            priceModifier = common.RangeCalculation(
                worstCase=_calculatePurchasePriceModifier(
                    ruleSystem=self._system,
                    purchaseDm=purchaseDm.worstCaseCalculation()),
                bestCase=_calculatePurchasePriceModifier(
                    ruleSystem=self._system,
                    purchaseDm=purchaseDm.bestCaseCalculation()),
                averageCase=_calculatePurchasePriceModifier(
                    ruleSystem=self._system,
                    purchaseDm=purchaseDm.averageCaseCalculation()),
                name='Base Price Scale')

        return common.Calculator.multiply(
            lhs=self._data.basePrice(),
            rhs=priceModifier,
            name='Purchase Price Per Ton')

    def calculateTotalSaleDm(
            self,
            world: traveller.World,
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

        tradeCodeDm = self._calculateTradeCodeDm(world, self._data.saleTradeCodes())
        if tradeCodeDm:
            saleDm = common.Calculator.add(
                lhs=brokerDm,
                rhs=tradeCodeDm)
        else:
            saleDm = brokerDm

        tradeCodeDm = self._calculateTradeCodeDm(world, self._data.purchaseTradeCodes())
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
            world: traveller.World,
            brokerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            buyerDm: typing.Union[int, common.ScalarCalculation, common.RangeCalculation],
            known3D6Roll: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        saleDm = self.calculateTotalSaleDm(
            world=world,
            brokerDm=brokerDm,
            buyerDm=buyerDm,
            known3D6Roll=known3D6Roll)

        if isinstance(saleDm, common.ScalarCalculation):
            priceModifier = common.ScalarCalculation(
                value=_calculateSalePriceModifier(
                    ruleSystem=self._system,
                    saleDm=saleDm),
                name='Base Price Scale')
        else:
            priceModifier = common.RangeCalculation(
                worstCase=_calculateSalePriceModifier(
                    ruleSystem=self._system,
                    saleDm=saleDm.worstCaseCalculation()),
                bestCase=_calculateSalePriceModifier(
                    ruleSystem=self._system,
                    saleDm=saleDm.bestCaseCalculation()),
                averageCase=_calculateSalePriceModifier(
                    ruleSystem=self._system,
                    saleDm=saleDm.averageCaseCalculation()),
                name='Base Price Scale')

        return common.Calculator.multiply(
            lhs=self._data.basePrice(),
            rhs=priceModifier,
            name='Sale Price Per Ton')

    def _calculateTradeCodeDm(
            self,
            world: traveller.World,
            tradeCodeMap: typing.Dict[traveller.TradeCode, common.ScalarCalculation]
            ) -> typing.Optional[common.ScalarCalculation]:
        largestDm = None
        for tradeCode in world.tradeCodes():
            if tradeCode in tradeCodeMap:
                tradeCodeDm = tradeCodeMap[tradeCode]

                if self.isWorldIllegal(world):
                    # The trade good is illegal on the world due to its law level
                    tradeCodeDm = self._calculateWorldIllegalDm(
                        world=world,
                        baseDm=tradeCodeDm)

                if not largestDm:
                    largestDm = tradeCodeDm
                else:
                    largestDm = common.Calculator.max(
                        lhs=largestDm,
                        rhs=tradeCodeDm)

        # Note that largestModifier will be None if there are no applicable trade codes
        return largestDm

    # The MGT2 rules says, for goods that are illegal because of the world law level, the DM should
    # be the difference between the law level of the world and the law level the trade good becomes
    # illegal. If the item is also universally illegal the largest of the two DMs is used
    def _calculateWorldIllegalDm(
            self,
            world: traveller.World,
            baseDm: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        worldLawLevel = common.ScalarCalculation(
            value=traveller.ehexToInteger(
                value=world.uwp().code(traveller.UWP.Element.LawLevel),
                default=-1),
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

    def copy(self) -> 'TradeDMToPriceModifierFunction':
        return TradeDMToPriceModifierFunction(
            tradeType=self._tradeType,
            tradeDm=self._tradeDm.copy(),
            priceModifier=self._priceModifier.copy())

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
            raise RuntimeError('Significant digits function type property is not a string')
        type = type.lower()
        if type not in _TradeTypeSerialisationStrToType:
            raise RuntimeError(f'Trade DM function has invalid type property {type}')
        type = _TradeTypeSerialisationStrToType[type]

        value = jsonData.get('value')
        if value is None:
            raise RuntimeError('Characteristic DM function is missing the value property')
        value = common.deserialiseCalculation(jsonData=value)

        modifier = jsonData.get('modifier')
        if modifier is None:
            raise RuntimeError('Characteristic DM function is missing the modifier property')
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
        ruleSystem: traveller.RuleSystem,
        world: traveller.World,
        includeLegal: bool,
        includeIllegal: bool
        ) -> typing.List[TradeGood]:
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
        if tradeGood.checkTradeGoodAvailability(world):
            available.append(tradeGood)
    return available

def worldCargoQuantityModifiers(
        ruleSystem: traveller.RuleSystem,
        world: traveller.World
        ) -> typing.Iterable[common.ScalarCalculation]:
    modifiers = []

    if ruleSystem != traveller.RuleSystem.MGT2022:
        return modifiers # Modifiers only apply for 2022 rules

    # In Mongoose 2022 rules, the amount of cargo available is affected by population. Worlds with
    # a population <= 3 get DM-3 modifier to the available quantity roll. Worlds with a population
    # >= 9 get a DM+3 modifier. Note that this can cause an available quantity of <= 0
    population = traveller.ehexToInteger(
        value=world.uwp().code(traveller.UWP.Element.Population),
        default=0) # If unknown, assume 0 to be pessimistic
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
        world: traveller.World,
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
    worldModifiers = traveller.worldCargoQuantityModifiers(ruleSystem=ruleSystem, world=world)
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
    _TradeGoodData(
        TradeGoodIds.CommonElectronics,
        'Common Electronics',
        20000,
        None, # Available everywhere
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3,
            traveller.TradeCode.RichWorld: 1
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.LowTechWorld: 1,
            traveller.TradeCode.PoorWorld: 1
        },
        None, # Legal everywhere
        2, 10), # 2D x 10

    _TradeGoodData(
        TradeGoodIds.CommonIndustrialGoods,
        'Common Industrial Goods',
        10000,
        None, # Available everywhere
        {
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.AgriculturalWorld: 2
        },
        None, # Legal everywhere
        2, 10), # 2D x 10

    _TradeGoodData(
        TradeGoodIds.CommonManufacturedGoods,
        'Common Manufactured Goods',
        20000,
        None, # Available everywhere
        {
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        None, # Legal everywhere
        2, 10), # 2D x 10

    _TradeGoodData(
        TradeGoodIds.CommonRawMaterials,
        'Common Raw Materials',
        5000,
        None, # Available everywhere
        {
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.GardenWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 2
        },
        None, # Legal everywhere
        2, 20), # 2D x 20

    _TradeGoodData(
        TradeGoodIds.CommonConsumables,
        'Common Consumables',
        500,
        None, # Available everywhere
        {
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.WaterWorld: 2,
                traveller.TradeCode.GardenWorld: 1,
                traveller.TradeCode.AsteroidBelt: -4
        },
        {
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.FluidWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        None, # Legal everywhere
        2, 20), # 2D x 20

    _TradeGoodData(
        TradeGoodIds.CommonOre,
        'Common Ore',
        1000,
        None, # Available everywhere
        {
                traveller.TradeCode.AsteroidBelt: 4
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        2, 20), # 2D x 20

    _TradeGoodData(
        TradeGoodIds.AdvancedElectronics,
        'Advanced Electronics',
        100000,
        [
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 1,
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.AsteroidBelt: 3
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedMachineParts,
        'Advanced Machine Parts',
        75000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedManufacturedGoods,
        'Advanced Manufactured Goods',
        100000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 1
        },
        {
            traveller.TradeCode.HighPopulationWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedWeapons,
        'Advanced Weapons',
        150000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.AmberZone: 2,
            traveller.TradeCode.RedZone: 4
        },
        # It's not clear if advanced weapons should be world illegal and, if so, at
        # what law level. As it's so unclear I've chosen to not make it world illegal
        None,
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedVehicles,
        'Advanced Vehicles',
        180000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Biochemicals,
        'Biochemicals',
        50000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.WaterWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.CrystalsAndGems,
        'Crystals & Gems',
        20000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.IceCappedWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.RichWorld: 2,
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Cybernetics,
        'Cybernetics',
        250000,
        [
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.LiveAnimals,
        'Live Animals',
        10000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2
        },
        {
            traveller.TradeCode.LowPopulationWorld: 3
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.LuxuryConsumables,
        'Luxury Consumables',
        20000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.LuxuryGoods,
        'Luxury Goods',
        200000,
        [
                traveller.TradeCode.HighPopulationWorld
        ],
        {
            traveller.TradeCode.HighPopulationWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 4
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.MedicalSupplies,
        'Medical Supplies',
        50000,
        [
            traveller.TradeCode.HighTechWorld,
            traveller.TradeCode.HighPopulationWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.RichWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Petrochemicals,
        'Petrochemicals',
        10000,
        [
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.FluidWorld,
            traveller.TradeCode.IceCappedWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.DesertWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.LowTechWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Pharmaceuticals,
        'Pharmaceuticals',
        100000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.HighPopulationWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.LowTechWorld: 1
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Polymers,
        'Polymers',
        7000,
        [
            traveller.TradeCode.IndustrialWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.PreciousMetals,
        'Precious Metals',
        50000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.IceCappedWorld,
                traveller.TradeCode.FluidWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 3,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 2,
        },
        {
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Radioactives,
        'Radioactives',
        1000000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.LowPopulationWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.LowPopulationWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.HighTechWorld: 1,
            traveller.TradeCode.NonIndustrialWorld: -2,
            traveller.TradeCode.AgriculturalWorld: -3
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Robots,
        'Robots',
        400000,
        [
            traveller.TradeCode.IndustrialWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 1
        },
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Spices,
        'Spices',
        6000,
        [
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.DesertWorld: 2
        },
        {
            traveller.TradeCode.HighPopulationWorld: 2,
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.PoorWorld: 3
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Textiles,
        'Textiles',
        3000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.NonIndustrialWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 7
        },
        {
            traveller.TradeCode.HighPopulationWorld: 3,
            traveller.TradeCode.NonAgriculturalWorld: 2
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.UncommonOre,
        'Uncommon Ore',
        5000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.IceCappedWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 4
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.UncommonRawMaterials,
        'Uncommon Raw Materials',
        20000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Wood,
        'Wood',
        1000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 6
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.IndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.Vehicles,
        'Vehicles',
        15000,
        [
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.IllegalBiochemicals,
        'Illegal Biochemicals',
        50000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.WaterWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 6
        },
        '0', # Illegal at all law levels
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.IllegalCybernetics,
        'Illegal Cybernetics',
        250000,
        [
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.AsteroidBelt: 4,
            traveller.TradeCode.IceCappedWorld: 4,
            traveller.TradeCode.RichWorld: 8,
            traveller.TradeCode.AmberZone: 6,
            traveller.TradeCode.RedZone: 6,
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalDrugs,
        'Illegal Drugs',
        100000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.HighPopulationWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.GardenWorld: 1,
            traveller.TradeCode.WaterWorld: 1,
        },
        {
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 6
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalLuxuries,
        'Illegal Luxuries',
        50000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 4
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalWeapons,
        'Illegal Weapons',
        150000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.PoorWorld: 6,
            traveller.TradeCode.AmberZone: 8,
            traveller.TradeCode.RedZone: 10
        },
        '0', # Illegal at all law levels
        1, 5), # 1D x 5

    # Exotics are a weird case that the rule book says require roll playing,
    # this entry is just here as a place holder to capture the fact they exist
    # Note: The availability is set to an empty list which means no availability
    # based on world TradeCodes, this is different to None which is used elsewhere
    # to indicate availability everywhere
    _TradeGoodData(
        TradeGoodIds.Exotics,
        'Exotics',
        0,
        [],
        {},
        {},
        None, # Legal everywhere
        0, 0)
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
    _TradeGoodData(
        TradeGoodIds.CommonElectronics,
        'Basic Electronics',
        10000,
        None, # Available everywhere
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3,
            traveller.TradeCode.RichWorld: 1
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.LowTechWorld: 1,
            traveller.TradeCode.PoorWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.CommonIndustrialGoods,
        'Basic Machine Parts',
        10000,
        None, # Available everywhere
        {
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.AgriculturalWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.CommonManufacturedGoods,
        'Basic Manufactured Goods',
        10000,
        None, # Available everywhere
        {
                traveller.TradeCode.NonAgriculturalWorld: 2,
                traveller.TradeCode.IndustrialWorld: 5
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 3,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.CommonRawMaterials,
        'Basic Raw Materials',
        5000,
        None, # Available everywhere
        {
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.GardenWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 2
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.CommonConsumables,
        'Basic Consumables',
        2000,
        None, # Available everywhere
        {
                traveller.TradeCode.AgriculturalWorld: 3,
                traveller.TradeCode.WaterWorld: 2,
                traveller.TradeCode.GardenWorld: 1,
                traveller.TradeCode.AsteroidBelt: -4
        },
        {
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.FluidWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.CommonOre,
        'Basic Ore',
        1000,
        None, # Available everywhere
        {
                traveller.TradeCode.AsteroidBelt: 4
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.AdvancedElectronics,
        'Advanced Electronics',
        100000,
        [
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 3
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 1,
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.AsteroidBelt: 3
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedMachineParts,
        'Advanced Machine Parts',
        75000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedManufacturedGoods,
        'Advanced Manufactured Goods',
        100000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 1
        },
        {
            traveller.TradeCode.HighPopulationWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedWeapons,
        'Advanced Weapons',
        150000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.AmberZone: 2,
            traveller.TradeCode.RedZone: 4
        },
        # It's not clear if advanced weapons should be world illegal and, if so, at
        # what law level. As it's so unclear I've chosen to not make it world illegal
        None,
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.AdvancedVehicles,
        'Advanced Vehicles',
        180000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Biochemicals,
        'Biochemicals',
        50000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.WaterWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.CrystalsAndGems,
        'Crystals & Gems',
        20000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.IceCappedWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 1,
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.RichWorld: 2,
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Cybernetics,
        'Cybernetics',
        250000,
        [
            traveller.TradeCode.HighTechWorld
        ],
        {},
        {
            traveller.TradeCode.AsteroidBelt: 1,
            traveller.TradeCode.IceCappedWorld: 1,
            traveller.TradeCode.RichWorld: 2
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.LiveAnimals,
        'Live Animals',
        10000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2
        },
        {
            traveller.TradeCode.LowPopulationWorld: 3
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.LuxuryConsumables,
        'Luxury Consumables',
        20000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.LuxuryGoods,
        'Luxury Goods',
        200000,
        [
                traveller.TradeCode.HighPopulationWorld
        ],
        {},
        {
            traveller.TradeCode.RichWorld: 4
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.MedicalSupplies,
        'Medical Supplies',
        50000,
        [
            traveller.TradeCode.HighTechWorld,
            traveller.TradeCode.HighPopulationWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.PoorWorld: 1,
            traveller.TradeCode.RichWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Petrochemicals,
        'Petrochemicals',
        10000,
        [
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.FluidWorld,
            traveller.TradeCode.IceCappedWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.DesertWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.AgriculturalWorld: 1,
            traveller.TradeCode.LowTechWorld: 2
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Pharmaceuticals,
        'Pharmaceuticals',
        100000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.HighPopulationWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.LowTechWorld: 1
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Polymers,
        'Polymers',
        7000,
        [
            traveller.TradeCode.IndustrialWorld
        ],
        {},
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.PreciousMetals,
        'Precious Metals',
        50000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.IceCappedWorld,
                traveller.TradeCode.FluidWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 3,
            traveller.TradeCode.DesertWorld: 1,
            traveller.TradeCode.IceCappedWorld: 2,
        },
        {
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Radioactives,
        'Radioactives',
        1000000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.LowPopulationWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 2,
            traveller.TradeCode.LowPopulationWorld: -4
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.HighTechWorld: 1,
            traveller.TradeCode.NonIndustrialWorld: -2,
            traveller.TradeCode.AgriculturalWorld: -3
        },
        None, # Legal everywhere
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.Robots,
        'Robots',
        400000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {},
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.Spices,
        'Spices',
        6000,
        [
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.DesertWorld: 2
        },
        {
            traveller.TradeCode.HighPopulationWorld: 2,
            traveller.TradeCode.RichWorld: 3,
            traveller.TradeCode.PoorWorld: 3
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Textiles,
        'Textiles',
        3000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.NonIndustrialWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 7
        },
        {
            traveller.TradeCode.HighPopulationWorld: 3,
            traveller.TradeCode.NonAgriculturalWorld: 2
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.UncommonOre,
        'Uncommon Ore',
        5000,
        [
                traveller.TradeCode.AsteroidBelt,
                traveller.TradeCode.IceCappedWorld
        ],
        {
            traveller.TradeCode.AsteroidBelt: 4
        },
        {
            traveller.TradeCode.IndustrialWorld: 3,
            traveller.TradeCode.NonIndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 20), # 1D x 20

    _TradeGoodData(
        TradeGoodIds.UncommonRawMaterials,
        'Uncommon Raw Materials',
        20000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.DesertWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Wood,
        'Wood',
        1000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.GardenWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 6
        },
        {
            traveller.TradeCode.RichWorld: 2,
            traveller.TradeCode.IndustrialWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.Vehicles,
        'Vehicles',
        15000,
        [
                traveller.TradeCode.IndustrialWorld,
                traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.IndustrialWorld: 2,
            traveller.TradeCode.HighTechWorld: 1
        },
        {
            traveller.TradeCode.NonIndustrialWorld: 2,
            traveller.TradeCode.HighPopulationWorld: 1
        },
        None, # Legal everywhere
        1, 10), # 1D x 10

    _TradeGoodData(
        TradeGoodIds.IllegalBiochemicals,
        'Illegal Biochemicals',
        50000,
        [
                traveller.TradeCode.AgriculturalWorld,
                traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.WaterWorld: 2
        },
        {
            traveller.TradeCode.IndustrialWorld: 6
        },
        '0', # Illegal at all law levels
        1, 5), # 1D x 5

    _TradeGoodData(
        TradeGoodIds.IllegalCybernetics,
        'Illegal Cybernetics',
        250000,
        [
            traveller.TradeCode.HighTechWorld
        ],
        {},
        {
            traveller.TradeCode.AsteroidBelt: 4,
            traveller.TradeCode.IceCappedWorld: 4,
            traveller.TradeCode.RichWorld: 8,
            traveller.TradeCode.AmberZone: 6,
            traveller.TradeCode.RedZone: 6,
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalDrugs,
        'Illegal Drugs',
        100000,
        [
            traveller.TradeCode.AsteroidBelt,
            traveller.TradeCode.DesertWorld,
            traveller.TradeCode.HighPopulationWorld,
            traveller.TradeCode.WaterWorld
        ],
        {},
        {
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 6
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalLuxuries,
        'Illegal Luxuries',
        50000,
        [
            traveller.TradeCode.AgriculturalWorld,
            traveller.TradeCode.GardenWorld,
            traveller.TradeCode.WaterWorld
        ],
        {
            traveller.TradeCode.AgriculturalWorld: 2,
            traveller.TradeCode.WaterWorld: 1
        },
        {
            traveller.TradeCode.RichWorld: 6,
            traveller.TradeCode.HighPopulationWorld: 4
        },
        '0', # Illegal at all law levels
        1, 1), # 1D (x 1)

    _TradeGoodData(
        TradeGoodIds.IllegalWeapons,
        'Illegal Weapons',
        150000,
        [
            traveller.TradeCode.IndustrialWorld,
            traveller.TradeCode.HighTechWorld
        ],
        {
            traveller.TradeCode.HighTechWorld: 2
        },
        {
            traveller.TradeCode.PoorWorld: 6,
            traveller.TradeCode.AmberZone: 8,
            traveller.TradeCode.RedZone: 10
        },
        '0', # Illegal at all law levels
        1, 5), # 1D x 5

    # Exotics are a weird case that the rule book says require roll playing,
    # this entry is just here as a place holder to capture the fact they exist
    # Note: The availability is set to an empty list which means no availability
    # based on world TradeCodes, this is different to None which is used elsewhere
    # to indicate availability everywhere
    _TradeGoodData(
        TradeGoodIds.Exotics,
        'Exotics',
        0,
        [],
        {},
        {},
        None, # Legal everywhere
        0, 0)
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
