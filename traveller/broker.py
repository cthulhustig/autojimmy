import common
import traveller
import typing

def calculateLocalBrokerDetails(
    # For MGT the brokerDm is the desired skill level of the broker (range 1-6)
    # For MGT2 the brokerDm is the skill increase above base (range 1-4)
    # For MGT2022 the brokerDm isn't used as the broker skill is based purely on dice rolls
    ruleSystem: traveller.RuleSystem,
    brokerDm: typing.Optional[typing.Union[int, common.ScalarCalculation]],
    blackMarket: bool,
    diceRoller: typing.Optional[common.DiceRoller] = None,
    ) -> typing.Tuple[
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker DM
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker cut percentage
        bool]: # Is broker an informant. Only used for black market brokers when using 2022 rules _and_ when rolling dice
    if (brokerDm != None) and (not isinstance(brokerDm, common.ScalarCalculation)):
        assert(isinstance(brokerDm, int))
        brokerDm = common.ScalarCalculation(
            value=brokerDm,
            name='Broker DM Increase')

    if ruleSystem == traveller.RuleSystem.MGT:
        return _calculateMgtBrokerDetails(skillValue=brokerDm)
    elif ruleSystem == traveller.RuleSystem.MGT2:
        return _calculateMgt2BrokerDetails(
            skillModifier=brokerDm,
            blackMarket=blackMarket,
            diceRoller=diceRoller)
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        return _calculateMgt2022BrokerDetails(
            blackMarket=blackMarket,
            diceRoller=diceRoller)
    else:
        assert(False)

def minLocalBrokerDm(ruleSystem: traveller.RuleSystem) -> int:
    if ruleSystem == traveller.RuleSystem.MGT or \
            ruleSystem == traveller.RuleSystem.MGT2:
        return 1
    if ruleSystem == traveller.RuleSystem.MGT2022:
        # There is no user controlled modifier for 2022 rules
        return 0
    else:
        assert(False)

def maxLocalBrokerDm(ruleSystem: traveller.RuleSystem) -> int:
    if ruleSystem == traveller.RuleSystem.MGT:
        return 6
    elif ruleSystem == traveller.RuleSystem.MGT2:
        return 4
    elif ruleSystem == traveller.RuleSystem.MGT2022:
        # There is no user controlled modifier for 2022 rules
        return 0
    else:
        assert(False)


"""
This MGT rules for hiring a broker (Core rules p164) just use a simple one to one mapping of broker
skill to broker percentage. There doesn't appear to be any dice rolling involved. There also doesn't
seem to be any difference in percentage for legal/black market.
"""
_MgtBrokerPercentageMap = {
    1: 1,
    2: 2,
    3: 5,
    4: 7,
    5: 10,
    6: 15,
}
_MgtBrokerMaxDm = common.ScalarCalculation(value=6, name='Max Allowed Broker DM')

class MgtBrokerPercentageLookupFunction(common.CalculatorFunction):
    def __init__(
            self,
            skill: common.ScalarCalculation,
            percentage: int
            ) -> None:
        self._skill = skill
        self._percentage = percentage

    def value(self) -> typing.Union[int, float]:
        return self._percentage

    def calculationString(
            self,
            outerBrackets: bool,
            decimalPlaces: int = 2
            ) -> str:
        valueString = self._skill.name(forCalculation=True)
        if not valueString:
            valueString = self._skill.calculationString(
                outerBrackets=False,
                decimalPlaces=decimalPlaces)
        return f'BrokerCutPercentageForDM({valueString})'

    def calculations(self) -> typing.List[common.ScalarCalculation]:
        if self._skill.name():
            return [self._skill]
        return self._skill.subCalculations()

    def copy(self) -> 'MgtBrokerPercentageLookupFunction':
        return MgtBrokerPercentageLookupFunction(
            skill=self._skill.copy(),
            percentage=self._percentage)

    @staticmethod
    def serialisationType() -> str:
        return 'mgtbrokercut'

    def toJson(self) -> typing.Mapping[str, typing.Any]:
        # TODO: Should the percentage be stored as a ScalarValue for
        # consistency rather than an integer
        return {
            'skill': common.serialiseCalculation(self._skill, includeVersion=False),
            'percentage': self._percentage}

    @staticmethod
    def fromJson(
        jsonData: typing.Mapping[str, typing.Any]
        ) -> 'MgtBrokerPercentageLookupFunction':
        skill = jsonData.get('skill')
        if skill is None:
            raise RuntimeError('Mongoose broker cut function is missing the skill property')
        skill = common.deserialiseCalculation(jsonData=skill)

        percentage = jsonData.get('percentage')
        if percentage is None:
            raise RuntimeError('Mongoose broker cut function is missing the percentage property')
        if not isinstance(percentage, int):
            raise RuntimeError('Mongoose broker cut function percentage property is not an integer')

        return MgtBrokerPercentageLookupFunction(skill=skill, percentage=percentage)

def _calculateMgtBrokerDetails(
    skillValue: common.ScalarCalculation
    ) -> typing.Tuple[
        common.ScalarCalculation, # Broker DM
        common.ScalarCalculation, # Broker cut percentage
        bool]: # Is broker an informant. Always false for 1e rules
    if (not skillValue) or (skillValue.value() < 1):
        return (None, None, False)

    brokerPercentage = _MgtBrokerPercentageMap.get(skillValue.value())
    if brokerPercentage == None:
        # If we don't find a value assume that the requested DM is over the max possible for a
        # broker and clamp the requested value
        skillValue = common.Calculator.min(
            lhs=skillValue,
            rhs=_MgtBrokerMaxDm,
            name='Clamped Broker DM')
        brokerPercentage = _MgtBrokerPercentageMap.get(skillValue.value())

    brokerPercentage = common.ScalarCalculation(
        value=MgtBrokerPercentageLookupFunction(
            skill=skillValue,
            percentage=brokerPercentage),
        name='Broker Cut Percentage')

    return (skillValue, brokerPercentage, False)


"""
This MGT2 rules says the following for hiring a broker (Core rules p210)

"
A trader can hire a local guide, to help him find a
supplier, or a local broker to help him negotiate a
deal. A local guide will have a Broker skill equal to
1D-2. DM+1 can be added to this roll for every 5% of
the total value of the trade that is given to the guide,
to a maximum of DM+4. Black market guides require
10% of the value for every DM+1,
"

After re-reading it a LOT I _think_ I finally figured out how it's meant to work.
- It's implied that the trader MUST offer at least 5% to get a DM+1 on the 1D-2 roll. This
would make the minimum broker skill 0, which makes sense as it would mean they have the
broker skill.
- The maximum of DM+4 is the limit of how many DM points the trader can pay to increase
the roll for the brokers skill level. It's NOT the limit of what the brokers final skill
can be, the limit of the brokers skill is 8 ((6-2) + 4).

The following is for a non-black market broker (black market percentages are doubled):
DM+1 = 5% = Broker skill 0-5
DM+2 = 10% = Broker skill 1-6
DM+4 = 15% = Broker skill 2-7
DM+5 = 20% = Broker skill 3-8
"""
_Mgt2BrokerMaxDm = common.ScalarCalculation(value=4, name='Max Allowed Broker DM Increase')

def _calculateMgt2BrokerDetails(
    skillModifier: common.ScalarCalculation,
    blackMarket: bool,
    diceRoller: typing.Optional[common.DiceRoller] = None
    ) -> typing.Tuple[
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker DM
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker cut percentage
        bool]: # Is broker an informant. Always false for 2e rules
    if (not skillModifier) or (skillModifier.value() < 1):
        return (None, None, False)

    if skillModifier.value() > _Mgt2BrokerMaxDm.value():
        skillModifier = common.Calculator.min(
            lhs=skillModifier,
            rhs=_Mgt2BrokerMaxDm,
            name='Clamped Broker DM Increase')

    if diceRoller:
        brokerDmRoll = diceRoller.makeRoll(
            dieCount=1,
            name='Broker DM Roll')
    else:
        brokerDmRoll = common.calculateValueRangeForDice(
            dieCount=1,
            higherIsBetter=True)

    # Base broker DM is 1D-2, round down to be pessimistic
    baseBrokerDm = common.Calculator.floor(
        value=common.Calculator.subtract(
            lhs=brokerDmRoll,
            rhs=common.ScalarCalculation(2)),
        name='Broker Base DM')

    brokerDm = common.Calculator.add(
        lhs=baseBrokerDm,
        rhs=skillModifier,
        name='Black Market Broker DM' if blackMarket else 'Broker DM')

    if blackMarket:
        cutPercentagePerDmIncrease = common.ScalarCalculation(
            value=10,
            name='Black Market Broker Cut Percent Per DM+1 Increase')
    else:
        cutPercentagePerDmIncrease = common.ScalarCalculation(
            value=5,
            name='Broker Cut Percent Per DM+1 Increase')

    cutPercentage = common.Calculator.multiply(
        lhs=cutPercentagePerDmIncrease,
        rhs=skillModifier,
        name='Black Market Broker Cut Percentage' if blackMarket else 'Broker Cut Percentage')

    return (brokerDm, cutPercentage, False)

# The 2022 broker rules are a completely different from 1e/2e. The local broker has a broker skill
# of 2D/3 but they also get a DM+2 due to local knowledge. From the point of view of what I'm doing
# this effectively means they have a broker skill of (2D/3) + 2. The charge a flat 10% (20% for
# illegal) and there is no way to pay more to increase their skill level.
# There is also a rule that, if hiring an broker for illegal goods, if you get a natural 2 when
# making the roll for their skill (before the modifier is applied) then they're an informant.
def _calculateMgt2022BrokerDetails(
    blackMarket: bool,
    diceRoller: typing.Optional[common.DiceRoller] = None
    ) -> typing.Tuple[
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker DM
        typing.Union[common.ScalarCalculation, common.RangeCalculation], # Broker cut percentage
        bool]: # Is broker an informant. Only used for black market brokers _and_ when rolling dice
    if diceRoller:
        brokerDmRoll = diceRoller.makeRoll(
            dieCount=2,
            name='Broker DM Roll')
    else:
        brokerDmRoll = common.calculateValueRangeForDice(
            dieCount=2,
            higherIsBetter=True)
    brokerDm = common.Calculator.divideFloor(
        lhs=brokerDmRoll,
        rhs=common.ScalarCalculation(value=3, name='Broker DM Divisor'))
    brokerDm = common.Calculator.add(
        lhs=brokerDm,
        rhs=common.ScalarCalculation(value=2, name='Local Knowledge DM Modifier'),
        name='Black Market Broker DM' if blackMarket else 'Broker DM')
    cutPercentage = common.ScalarCalculation(
        value=20 if blackMarket else 10,
        name='Black Market Broker Cut Percentage' if blackMarket else 'Broker Cut Percentage')

    return (brokerDm, cutPercentage, blackMarket and diceRoller and brokerDmRoll.value() == 2)
