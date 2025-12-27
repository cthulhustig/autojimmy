import astronomer
import common
import json
import survey
import traveller
import typing

class CargoRecord(object):
    def __init__(
            self,
            tradeGood: traveller.TradeGood,
            pricePerTon: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            quantity: typing.Union[common.ScalarCalculation, common.RangeCalculation]
            ) -> None:
        self._tradeGood = tradeGood
        self._pricePerTon = pricePerTon
        self._quantity = quantity

    def ruleSystem(self) -> traveller.RuleSystem:
        return self._tradeGood.ruleSystem()

    def tradeGood(self) -> traveller.TradeGood:
        return self._tradeGood

    def pricePerTon(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._pricePerTon

    def quantity(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._quantity

    def totalPrice(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return common.Calculator.multiply(self._quantity, self._pricePerTon)

def generateSpeculativePurchaseCargo(
        ruleSystem: traveller.RuleSystem,
        world: astronomer.World,
        playerBrokerDm: typing.Union[int, common.ScalarCalculation],
        minSellerDm: typing.Union[int, common.ScalarCalculation],
        maxSellerDm: typing.Union[int, common.ScalarCalculation],
        useLocalBroker: bool = False,
        localBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
        tradeGoods: typing.Optional[typing.Iterable[traveller.TradeGood]] = None, # If None standard world availability will be used for the trade goods list
        includeLegal: bool = True, # Only applies if tradeGoods is None
        includeIllegal: bool = True, # Only applies if tradeGoods is None
        ) -> typing.Iterable[CargoRecord]:
    if not isinstance(minSellerDm, common.ScalarCalculation):
        assert(isinstance(minSellerDm, int))
        minSellerDm = common.ScalarCalculation(
            value=minSellerDm,
            name='Min Seller DM')
    if not isinstance(maxSellerDm, common.ScalarCalculation):
        assert(isinstance(maxSellerDm, int))
        maxSellerDm = common.ScalarCalculation(
            value=maxSellerDm,
            name='Max Seller DM')
    if useLocalBroker and localBrokerDm != None and not isinstance(localBrokerDm, common.ScalarCalculation):
        assert(isinstance(localBrokerDm, int))
        localBrokerDm = common.ScalarCalculation(
            value=localBrokerDm,
            name='Local Broker DM')

    if minSellerDm.value() == maxSellerDm.value():
        sellerDm = common.Calculator.rename(
            value=minSellerDm,
            name='Seller DM')
    else:
        # When calculating the average buyers DM we round up to be pessimistic
        sellerDm = common.RangeCalculation(
            worstCase=maxSellerDm,
            bestCase=minSellerDm,
            averageCase=common.Calculator.ceil(
                value=common.Calculator.average(
                    lhs=minSellerDm,
                    rhs=maxSellerDm)),
            name='Seller DM')

    if not tradeGoods:
        # An explicit list of trade goods wasn't supplied so get the trade goods available due to
        # the worlds trade codes
        tradeGoods = traveller.worldTradeGoods(
            ruleSystem=ruleSystem,
            world=world,
            includeLegal=includeLegal,
            includeIllegal=includeIllegal)

    # Calculate legal and illegal broker DM and cut percentage if required
    legalLocalBrokerDm = None
    legalLocalBrokerCutPercentage = None
    illegalLocalBrokerDm = None
    illegalLocalBrokerCutPercentage = None
    if useLocalBroker:
        # Note that these are generated even if includeLegal or includeIllegal are false as they
        # may be required if the list of trade goods was explicitly specified
        legalLocalBrokerDm, legalLocalBrokerCutPercentage, _ = \
            traveller.calculateLocalBrokerDetails(
                ruleSystem=ruleSystem,
                brokerDm=localBrokerDm,
                blackMarket=False)
        illegalLocalBrokerDm, illegalLocalBrokerCutPercentage, _ = \
            traveller.calculateLocalBrokerDetails(
                ruleSystem=ruleSystem,
                brokerDm=localBrokerDm,
                blackMarket=True)

    # Generate a CargoRecord for each trade good
    cargoRecords = []
    for tradeGood in tradeGoods:
        # TODO: There is a deficiency here that I can't see how to easily fix. Exotics can be
        # legal or illegal but I don't currently have a way to represent that. As such they're
        # not explicitly illegal so a legal broker will always be used for them. This should only
        # a problem when a list of trade goods are passed into this function, exotics have special
        # availability so should never appear in the list of trade goods for a world
        isIllegal = tradeGood.isIllegal(world)

        finalBrokerDm = playerBrokerDm
        localBrokerCutPercentage = None
        if useLocalBroker:
            if not isIllegal:
                finalBrokerDm = legalLocalBrokerDm
                localBrokerCutPercentage = legalLocalBrokerCutPercentage
            else:
                finalBrokerDm = illegalLocalBrokerDm
                localBrokerCutPercentage = illegalLocalBrokerCutPercentage

        purchasePricePerTon = tradeGood.calculatePurchasePrice(
            world=world,
            brokerDm=finalBrokerDm,
            sellerDm=sellerDm)

        if localBrokerCutPercentage:
            # The local broker's cut effectively increases the per ton purchase price
            # of goods as they take their cut before any other overheads. In order
            # for this to work out the same as taking the cut from the final trade
            # price, it's important that we don't round here. Rounding should only
            # be done when the final price is calculated by multiplying by a quantity
            brokerCutPerTon = common.Calculator.multiply(
                lhs=common.Calculator.divideFloat(
                    lhs=purchasePricePerTon,
                    rhs=common.ScalarCalculation(value=100)),
                rhs=localBrokerCutPercentage,
                name='Local Broker Cut Per Ton')
            purchasePricePerTon = common.Calculator.add(
                lhs=purchasePricePerTon,
                rhs=brokerCutPerTon,
                name='Brokered Purchase Price Per Ton')

        availability = traveller.calculateWorldTradeGoodQuantity(
            ruleSystem=ruleSystem,
            world=world,
            tradeGood=tradeGood)

        cargoRecords.append(CargoRecord(
            tradeGood=tradeGood,
            pricePerTon=purchasePricePerTon,
            quantity=availability))

    return cargoRecords

def generateRandomPurchaseCargo(
        ruleSystem: traveller.RuleSystem,
        world: astronomer.World,
        playerBrokerDm: typing.Union[int, common.ScalarCalculation],
        sellerDm: typing.Union[int, common.ScalarCalculation],
        blackMarket: bool,
        diceRoller: common.DiceRoller,
        useLocalBroker: bool = False,
        localBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
        ) -> typing.Tuple[
            typing.Iterable[CargoRecord],
            bool]: # Is broker an informant. Only used for local black market brokers under the 2002 rules _and_ when rolling dice
    # Get the trade goods always available on the world
    tradeGoods = traveller.worldTradeGoods(
        ruleSystem=ruleSystem,
        world=world,
        includeLegal=not blackMarket,
        includeIllegal=blackMarket)

    # Generate randomly available trade goods
    if ruleSystem == traveller.RuleSystem.MGT2022:
        # For the 2022 rules the number of randomly available trade goods is
        # determined by the population (see p242)
        population = common.ScalarCalculation(
            value=survey.ehexToInteger(
                value=world.uwp().code(astronomer.UWP.Element.Population),
                default=0),
            name=f'{world.name(includeSubsector=True)} Population Code')
        numberOfRandomTradeGoods = common.Calculator.equals(
            value=population,
            name='Random Item Count')
    else:
        # For 1e & 2e rules the number of random trade goods is also random
        numberOfRandomTradeGoods = diceRoller.makeRoll(
            name='Random Item Count Roll',
            dieCount=1)
    extraAvailabilityMultipliers: typing.Dict[traveller.TradeGood, int] = {}
    for index in range(0, numberOfRandomTradeGoods.value()):
        tradeGood = _rollRandomTradeGood(
            ruleSystem=ruleSystem,
            blackMarket=blackMarket,
            diceRoller=diceRoller,
            rollIndex=index,
            isReRoll=False)

        # Mongoose 1e & 2e say to ignore rolled trade goods if they don't match the required legality
        # (p163 & p211 respectively). However the 2022 rules say to re-roll (p242). It should be noted
        # that re-rolling in the converse situation should never be required as the 2022 rules have you
        # roll just once dice for illegal trade goods and prefix a 6 to it.
        # Exotics are treated as a special case as legal and illegal sellers can have exotic goods.
        # I can't find anything that explicitly says this in the 1e/2e rules but the 2022 rules
        # (p242) do so I think it makes sense for it to apply in all cases.
        if tradeGood.id() != traveller.TradeGoodIds.Exotics:
            if ruleSystem == traveller.RuleSystem.MGT2022:
                while tradeGood.isIllegal(world) != blackMarket:
                    tradeGood = _rollRandomTradeGood(
                        ruleSystem=ruleSystem,
                        blackMarket=blackMarket,
                        diceRoller=diceRoller,
                        rollIndex=index,
                        isReRoll=True)
            elif tradeGood.isIllegal(world) != blackMarket:
                continue # Ignore for 1e & 2e

        if tradeGood in tradeGoods:
            # The trade good is already on the list so it's availability needs to be multiplied
            if tradeGood not in extraAvailabilityMultipliers:
                extraAvailabilityMultipliers[tradeGood] = 2
            else:
                extraAvailabilityMultipliers[tradeGood] += 1
        else:
            tradeGoods.append(tradeGood)

    # Roll 3D6 for this seller
    purchase3D6Roll = diceRoller.makeRoll(
        dieCount=3,
        name='Purchase Roll')

    # Calculate legal and illegal broker DM and cut percentage if required
    localBrokerCutPercentage = None
    localBrokerIsInformant = False
    if useLocalBroker:
        # Note that these are generated even if includeLegal or includeIllegal are false as they
        # may be required if the list of trade goods was explicitly specified
        localBrokerDm, localBrokerCutPercentage, localBrokerIsInformant = \
            traveller.calculateLocalBrokerDetails(
                ruleSystem=ruleSystem,
                brokerDm=localBrokerDm,
                blackMarket=blackMarket,
                diceRoller=diceRoller)

    # Generate a CargoRecord for each trade good
    cargoRecords = []
    for tradeGood in tradeGoods:
        purchasePricePerTon = tradeGood.calculatePurchasePrice(
            world=world,
            brokerDm=localBrokerDm if localBrokerDm else playerBrokerDm,
            sellerDm=sellerDm,
            known3D6Roll=purchase3D6Roll)

        if localBrokerCutPercentage:
            # The local broker's cut effectively increases the per ton purchase price
            # of goods as they take their cut before any other overheads. In order
            # for this to work out the same as taking the cut from the final trade
            # price, it's important that we don't round here. Rounding should only
            # be done when the final price is calculated by multiplying by a quantity
            brokerCutPerTon = common.Calculator.multiply(
                lhs=common.Calculator.divideFloat(
                    lhs=purchasePricePerTon,
                    rhs=common.ScalarCalculation(value=100)),
                rhs=localBrokerCutPercentage,
                name='Local Broker Cut Per Ton')
            purchasePricePerTon = common.Calculator.add(
                lhs=purchasePricePerTon,
                rhs=brokerCutPerTon,
                name='Brokered Purchase Price Per Ton')

        availability = traveller.calculateWorldTradeGoodQuantity(
            ruleSystem=ruleSystem,
            world=world,
            tradeGood=tradeGood,
            diceRoller=diceRoller)

        availabilityMultiplier = extraAvailabilityMultipliers.get(tradeGood)
        if availabilityMultiplier:
            availabilityMultiplier = common.ScalarCalculation(
                value=availabilityMultiplier,
                name='Extra Quantity Multiplier')
            availability = common.Calculator.multiply(
                lhs=availability,
                rhs=availabilityMultiplier,
                name=availability.name())

        # Don't create a CargoRecord if the trade good has no availability (can happen with 2022
        # rules). Exotics are treated as a special case as they have special availability and always
        # have a value of 0
        if (availability.value() <= 0) and \
                (tradeGood.id() != traveller.TradeGoodIds.Exotics):
            continue

        cargoRecords.append(CargoRecord(
            tradeGood=tradeGood,
            pricePerTon=purchasePricePerTon,
            quantity=availability))

    return (cargoRecords, localBrokerIsInformant)

def generateRandomSaleCargo(
        ruleSystem: traveller.RuleSystem,
        world: astronomer.World,
        currentCargo: typing.Iterable[CargoRecord],
        playerBrokerDm: typing.Union[int, common.ScalarCalculation],
        buyerDm: typing.Union[int, common.ScalarCalculation],
        blackMarket: bool,
        diceRoller: typing.Optional[common.DiceRoller],
        useLocalBroker: bool = False,
        localBrokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None, # Only used for 1e & 2e
        ) -> typing.Tuple[
            typing.Iterable[CargoRecord],
            bool]: # Is broker an informant. Only used for local black market brokers under the 2002 rules _and_ when rolling dice
    sale3D6Roll = diceRoller.makeRoll(
        dieCount=3,
        name='Sale Roll')

    # Calculate legal and illegal broker DM and cut percentage if required
    localBrokerCutPercentage = None
    localBrokerIsInformant = False
    if useLocalBroker:
        localBrokerDm, localBrokerCutPercentage, localBrokerIsInformant = \
            traveller.calculateLocalBrokerDetails(
                ruleSystem=ruleSystem,
                brokerDm=localBrokerDm,
                blackMarket=blackMarket,
                diceRoller=diceRoller)

    # Calculate a sale CargoRecord for each supplied CargoRecord
    saleRecords = []
    for cargo in currentCargo:
        tradeGood = cargo.tradeGood()

        # Skip trade goods that don't meet the requested legality.
        # Exotics are treated as a special case as legal and illegal buyers can take exotic goods.
        # I can't find anything that explicitly says this in the 1e/2e rules but the 2022 rules do
        # so that it applies to sellers so seems logical it would apply to buyers (in game it would
        # probably depend on what the exotics were)
        if (tradeGood.id() != traveller.TradeGoodIds.Exotics) and \
                (tradeGood.isIllegal(world) != blackMarket):
            continue

        salePricePerTon = tradeGood.calculateSalePrice(
            world=world,
            brokerDm=localBrokerDm if localBrokerDm else playerBrokerDm,
            buyerDm=buyerDm,
            known3D6Roll=sale3D6Roll)

        if localBrokerCutPercentage:
            # The local broker's cut effectively decreases the per ton sale price
            # of goods as they take their cut before any other overheads. In order
            # for this to work out the same as taking the cut from the final trade
            # price, it's important that we don't round here. Rounding should only
            # be done when the final price is calculated by multiplying by a quantity
            brokerCutPerTon = common.Calculator.multiply(
                lhs=common.Calculator.divideFloat(
                    lhs=salePricePerTon,
                    rhs=common.ScalarCalculation(value=100)),
                rhs=localBrokerCutPercentage,
                name='Local Broker Cut Per Ton')
            salePricePerTon = common.Calculator.subtract(
                lhs=salePricePerTon,
                rhs=brokerCutPerTon,
                name='Brokered Sale Price Per Ton')

        saleRecords.append(CargoRecord(
            tradeGood=tradeGood,
            pricePerTon=salePricePerTon,
            quantity=cargo.quantity())) # Just copy the quantity from the source CargoRecord

    return (saleRecords, localBrokerIsInformant)

def _rollRandomTradeGood(
        ruleSystem: traveller.RuleSystem,
        blackMarket: bool,
        diceRoller: common.DiceRoller,
        rollIndex: int,
        isReRoll: bool
        ) -> traveller.TradeGood:
    rollPrefix = f'Random Item {rollIndex + 1} '
    if isReRoll:
        rollPrefix = 'Re-Roll ' + rollPrefix

    if blackMarket and (ruleSystem == traveller.RuleSystem.MGT2022):
        # The Mongoose 2002 rules (p242) say that whe rolling for random items for a black market
        # seller you only use 1 dice and use 6 for the most significant digit. The knock of
        # effect of this is your're more likely to get exotics from an illegal seller
        majorRoll = common.ScalarCalculation(
            value=6,
            name='Black Market Seller Major Digit')
    else:
        majorRoll = diceRoller.makeRoll(
            dieCount=1,
            name=rollPrefix + 'Major Digit Roll')
    minorRoll = diceRoller.makeRoll(
        dieCount=1,
        name=rollPrefix + 'Minor Digit Roll')

    tradeGoodId = int(f'{majorRoll.value()}{minorRoll.value()}')
    return traveller.tradeGoodFromId(
        ruleSystem=ruleSystem,
        tradeGoodId=tradeGoodId)


#
# Serialisation
#
def serialiseCargoRecord(
        cargoRecord: CargoRecord
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'ruleSystem': cargoRecord.ruleSystem().name,
        'tradeGoodId': cargoRecord.tradeGood().id(),
        'quantity': common.serialiseCalculation(cargoRecord.quantity()),
        'pricePerTon': common.serialiseCalculation(cargoRecord.pricePerTon())}

def deserialiseCargoRecord(data: typing.Mapping[str, typing.Any]) -> CargoRecord:
    ruleSystem = data.get('ruleSystem')
    if ruleSystem is None:
        # HACK: The RuleSystem was added to the data stored for cargo records as part
        # of overhaul of the config system that made rules changeable at runtime.
        # There is no great way of working out what rule system was in use when
        # previous cargo records were serialised so assume it was the default and
        # hope for the best :(
        ruleSystem = 'MGT2022'
    if ruleSystem not in traveller.RuleSystem.__members__:
        raise RuntimeError(f'Cargo record data has unknown rule system "{ruleSystem}"')
    ruleSystem = traveller.RuleSystem.__members__[ruleSystem]

    tradeGoodId = data.get('tradeGoodId')
    if tradeGoodId == None:
        raise RuntimeError('Cargo record data is missing the tradeGoodId property')

    quantity = data.get('quantity')
    if quantity == None:
        raise RuntimeError('Cargo record data is missing the quantity property')

    pricePerTon = data.get('pricePerTon')
    if pricePerTon == None:
        raise RuntimeError('Cargo record data is missing the pricePerTon property')

    return CargoRecord(
        tradeGood=traveller.tradeGoodFromId(
            ruleSystem=ruleSystem,
            tradeGoodId=tradeGoodId),
        quantity=common.deserialiseCalculation(quantity),
        pricePerTon=common.deserialiseCalculation(pricePerTon))

def serialiseCargoRecordList(
        cargoRecords: typing.Iterable[CargoRecord]
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    items = []
    for cargoRecord in cargoRecords:
        items.append(serialiseCargoRecord(cargoRecord=cargoRecord))
    return {'cargoRecords': items}

def deserialiseCargoRecordList(
        data: typing.Mapping[str, typing.Any]
        ) -> typing.Iterable[CargoRecord]:
    items = data.get('cargoRecords')
    if items == None:
        raise RuntimeError('Cargo record list is missing the cargoRecords property')

    cargoRecords = []
    for item in items:
        cargoRecords.append(deserialiseCargoRecord(data=item))
    return cargoRecords

def writeCargoRecordList(
        cargoRecords: typing.Iterable[CargoRecord],
        filePath: str
        ) -> None:
    data = serialiseCargoRecordList(cargoRecords=cargoRecords)
    with open(filePath, 'w', encoding='UTF8') as file:
        json.dump(data, file, indent=4)

def readCargoRecordList(filePath: str) -> typing.Iterable[CargoRecord]:
    with open(filePath, 'r') as file:
        return deserialiseCargoRecordList(
            data=json.load(file))
