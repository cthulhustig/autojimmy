import common
import logic
import traveller
import travellermap
import typing

class TradeOption(object):
    def __init__(
            self,
            cargoRecord: logic.CargoRecord,
            purchaseWorld: travellermap.World,
            purchasePricePerTon: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            saleWorld: travellermap.World,
            salePricePerTon: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            cargoQuantity: typing.Union[common.ScalarCalculation, common.RangeCalculation],
            alreadyOwned: bool,
            routeLogistics: logic.RouteLogistics,
            tradeNotes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        self._cargoRecord = cargoRecord
        self._purchaseWorld = purchaseWorld
        self._purchasePricePerTon = purchasePricePerTon
        self._saleWorld = saleWorld
        self._salePricePerTon = salePricePerTon
        self._cargoQuantity = cargoQuantity
        self._alreadyOwned = alreadyOwned
        self._routeLogistics = routeLogistics
        self._tradeNotes = tradeNotes

        self._investment = common.Calculator.add(
            lhs=common.Calculator.multiply(
                lhs=self._purchasePricePerTon,
                rhs=self._cargoQuantity,
                name='Purchase Cost'),
            rhs=self._routeLogistics.totalCosts(),
            name='Investment')

        self._profitPerTon = common.Calculator.subtract(
            lhs=self._salePricePerTon,
            rhs=self._purchasePricePerTon,
            name='Profit Per Ton')

        self._grossProfit = common.Calculator.multiply(
            lhs=self._profitPerTon,
            rhs=self._cargoQuantity,
            name='Gross Profit')

        self._netProfit = common.Calculator.subtract(
            lhs=self._grossProfit,
            rhs=self._routeLogistics.totalCosts(),
            name='Net Profit')

        self._returnOnInvestment = common.Calculator.multiply(
            lhs=common.Calculator.divideFloat(
                lhs=self._netProfit,
                rhs=self._investment),
            rhs=common.ScalarCalculation(value=100),
            name='ROI')

    # This gets the CargoRecord that the TradeOption was generated from.
    # IMPORTANT: You can't assume that the purchase price and quantity are the same for the
    # CargoRecord and TradeOption. Although this is used to determine the trade good for the
    # TradeOption, it's only really here so other pieces of code can link TradeOptions to
    # CargoRecords
    def originalCargoRecord(self) -> logic.CargoRecord:
        return self._cargoRecord

    def tradeGood(self) -> traveller.TradeGood:
        return self._cargoRecord.tradeGood()

    def purchaseWorld(self) -> travellermap.World:
        return self._purchaseWorld

    def saleWorld(self) -> travellermap.World:
        return self._saleWorld

    def purchasePricePerTon(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._purchasePricePerTon

    def salePricePerTon(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._salePricePerTon

    def profitPerTon(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._profitPerTon

    def cargoQuantity(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._cargoQuantity

    def isAlreadyOwned(self) -> bool:
        return self._alreadyOwned

    def routeLogistics(self) -> logic.RouteLogistics:
        return self._routeLogistics

    def jumpCount(self) -> int:
        jumpRoute = self._routeLogistics.jumpRoute()
        return jumpRoute.jumpCount()

    def jumpRoute(self) -> logic.JumpRoute:
        return self._routeLogistics.jumpRoute()

    def tradeNotes(self) -> typing.Optional[typing.Iterable[str]]:
        return self._tradeNotes

    def logisticsCosts(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._routeLogistics.totalCosts()

    def investment(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._investment

    def grossProfit(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._grossProfit

    def netProfit(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._netProfit

    def returnOnInvestment(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._returnOnInvestment
