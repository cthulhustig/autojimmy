import astronomer
import common
import logic
import traveller
import typing

class TradeScore(object):
    def __init__(
            self,
            rules: traveller.Rules,
            world: astronomer.World,
            tradeGoods: typing.Optional[typing.Iterable[logic.TradeGood]] = None
            ) -> None:
        self._world = world
        self._ruleSystem = rules.system()
        self._tradeGoods = \
            logic.tradeGoodList(ruleSystem=self._ruleSystem) \
            if tradeGoods is None else \
            [tradeGood for tradeGood in tradeGoods if tradeGood.ruleSystem() == self._ruleSystem]

        self._purchaseScores: typing.Dict[logic.TradeGood, common.ScalarCalculation] = {}
        self._saleScores: typing.Dict[logic.TradeGood, common.ScalarCalculation] = {}
        for tradeGood in self._tradeGoods:
            purchaseScore = self._calculatePurchaseScore(
                rules=rules,
                world=world,
                tradeGood=tradeGood)
            if purchaseScore:
                self._purchaseScores[tradeGood] = purchaseScore

            saleScore = self._calculateSaleScore(
                rules=rules,
                world=world,
                tradeGood=tradeGood)
            if saleScore:
                self._saleScores[tradeGood] = saleScore

        self._quantityModifiers = logic.worldCargoQuantityModifiers(
            ruleSystem=self._ruleSystem,
            world=self._world)

        worldName = self._world.name(includeSubsector=True)
        self._totalPurchaseScore = common.Calculator.sum(
            values=list(self._purchaseScores.values()) + self._quantityModifiers,
            name=f'Purchase Trade Score for {worldName}')
        self._totalSaleScore = common.Calculator.sum(
            values=list(self._saleScores.values()) + self._quantityModifiers,
            name=f'Sale Trade Score for {worldName}')

    def world(self) -> astronomer.World:
        return self._world

    def ruleSystem(self) -> traveller.RuleSystem:
        return self._ruleSystem

    def tradeGoods(self) -> typing.Iterable[logic.TradeGood]:
        return self._tradeGoods

    def purchaseScores(self) -> typing.Mapping[logic.TradeGood, common.ScalarCalculation]:
        return self._purchaseScores

    def saleScores(self) -> typing.Mapping[logic.TradeGood, common.ScalarCalculation]:
        return self._saleScores

    def quantityModifiers(self) -> typing.Iterable[common.ScalarCalculation]:
        return self._quantityModifiers

    def tradeGoodPurchaseScore(
            self,
            tradeGood: logic.TradeGood
            ) -> typing.Optional[common.ScalarCalculation]:
        if tradeGood in self._purchaseScores:
            return self._purchaseScores[tradeGood]
        return None

    def tradeGoodSaleScore(
            self,
            tradeGood: logic.TradeGood
            ) -> typing.Optional[common.ScalarCalculation]:
        if tradeGood in self._saleScores:
            return self._saleScores[tradeGood]
        return None

    def totalPurchaseScore(self) -> common.ScalarCalculation:
        return self._totalPurchaseScore

    def totalSaleScore(self) -> common.ScalarCalculation:
        return self._totalSaleScore

    @staticmethod
    def _calculatePurchaseScore(
            rules: traveller.Rules,
            world: astronomer.World,
            tradeGood: logic.TradeGood
            ) -> typing.Optional[common.ScalarCalculation]:
        purchaseDm = tradeGood.calculatePurchaseTradeCodeDm(
            rules=rules,
            world=world)
        saleDm = tradeGood.calculateSaleTradeCodeDm(
            rules=rules,
            world=world)
        if not purchaseDm and not saleDm:
            return None

        name = f'Purchase Trade Score For {tradeGood.name()} on {world.name(includeSubsector=True)}'
        if purchaseDm and not saleDm:
            return common.Calculator.equals(
                value=purchaseDm,
                name=name)
        if saleDm and not purchaseDm:
            return common.Calculator.negate(
                value=saleDm,
                name=name)
        assert(purchaseDm and saleDm)

        return common.Calculator.subtract(
            lhs=purchaseDm,
            rhs=saleDm,
            name=name)

    @staticmethod
    def _calculateSaleScore(
            rules: traveller.Rules,
            world: astronomer.World,
            tradeGood: logic.TradeGood
            ) -> common.ScalarCalculation:
        purchaseDm = tradeGood.calculatePurchaseTradeCodeDm(
            rules=rules,
            world=world)
        saleDm = tradeGood.calculateSaleTradeCodeDm(
            rules=rules,
            world=world)
        if not purchaseDm and not saleDm:
            return None

        name = f'Sale Trade Score For {tradeGood.name()} on {world.name(includeSubsector=True)}'
        if saleDm and not purchaseDm:
            return common.Calculator.equals(
                value=saleDm,
                name=name)
        if purchaseDm and not saleDm:
            return common.Calculator.negate(
                value=purchaseDm,
                name=name)
        assert(purchaseDm and saleDm)

        return common.Calculator.subtract(
            lhs=saleDm,
            rhs=purchaseDm,
            name=name)
