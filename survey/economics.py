import common
import re
import typing

# This regex allows the following
# - Matches with and without ()
# - Matches with empty brackets or brackets that only contain white space
# - Ignores leading/trailing white space
# - Doesn't match strings that are only white space
# - Treats ? as a valid value for each attribute
# - Requires a +/- on the the 4th (Efficiency) attribute (except if it's a ?)
_EconomicsPattern = re.compile(r'^\s*(?:\(\s*(?:([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])(?:([+-][0-9])|(?:[+-]?([?]))))?\s*\)|([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])(?:([+-][0-9])|(?:[+-]?([?]))))\s*$')
_ValidResourcesCodes = set(['2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'])
_ValidLabourCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidInfrastructureCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
_ValidEfficiencyCodes = set(['-5', '-4', '-3',  '-2', '-1', '+0', '+1', '+2', '+3', '+4', '+5'])

def _processParsedCode(
        code: typing.Optional[str], # Can be None if parsed string is just a empty set of brackets
        allowed: typing.Set[str],
        name: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if not code or code == '?':
        return None

    checkCode = code.upper()
    if checkCode not in allowed:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Economics {name} code "{code}"')
        return None

    return checkCode

def parseSystemEconomicsString(
        economics: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.Optional[str], # Resources
            typing.Optional[str], # Labour
            typing.Optional[str], # Infrastructure
            typing.Optional[int]]: # Efficiency
    result = _EconomicsPattern.match(economics)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Economics string "{economics}"')
        return (None, None, None, None)

    return (
        _processParsedCode(code=result[1], allowed=_ValidResourcesCodes, name='Resources', reporter=reporter),
        _processParsedCode(code=result[2], allowed=_ValidLabourCodes, name='Labour', reporter=reporter),
        _processParsedCode(code=result[3], allowed=_ValidInfrastructureCodes, name='Infrastructure', reporter=reporter),
        _processParsedCode(code=result[4], allowed=_ValidEfficiencyCodes, name='Efficiency', reporter=reporter))

def _processFormatCode(
        code: typing.Optional[str],
        allowed: typing.Set[str],
        name: str,
        reporter: typing.Optional[common.Reporter]
        ) -> str:
    if code is None:
        return '?'

    checkCode = code.upper()
    if checkCode not in allowed:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Economics {name} code "{code}"')
        return '?'

    return checkCode

def formatSystemEconomicsString(
        resources: typing.Optional[str],
        labour: typing.Optional[str],
        infrastructure: typing.Optional[str],
        efficiency: typing.Optional[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    return '({resources}{labour}{infrastructure}{efficiency})'.format(
        resources=_processFormatCode(code=resources, allowed=_ValidResourcesCodes, name='Resources', reporter=reporter),
        labour=_processFormatCode(code=labour, allowed=_ValidLabourCodes, name='Labour', reporter=reporter),
        infrastructure=_processFormatCode(code=infrastructure, allowed=_ValidInfrastructureCodes, name='Infrastructure', reporter=reporter),
        efficiency=_processFormatCode(code=efficiency, allowed=_ValidEfficiencyCodes, name='Efficiency', reporter=reporter))

def _validateEconomicsElement(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f'{name} must be a valid economics {element} code')

def validateResources(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        validationFn=lambda name, value: _validateEconomicsElement(
            name=name,
            value=value,
            element='Resources',
            allowed=_ValidResourcesCodes))

def validateLabour(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        validationFn=lambda name, value: _validateEconomicsElement(
            name=name,
            value=value,
            element='Labour',
            allowed=_ValidLabourCodes))

def validateInfrastructure(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        validationFn=lambda name, value: _validateEconomicsElement(
            name=name,
            value=value,
            element='Infrastructure',
            allowed=_ValidInfrastructureCodes))

def validateEfficiency(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        validationFn=lambda name, value: _validateEconomicsElement(
            name=name,
            value=value,
            element='Efficiency',
            allowed=_ValidEfficiencyCodes))
