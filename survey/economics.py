import re
import typing

_EconomicsPattern = re.compile(r'\(\s*([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])(?:([+-][0-9])|(?:[+-]?([?])))\s*\)')
_ValidResourcesCodes = set(['2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'])
_ValidLabourCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidInfrastructureCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
_ValidEfficiencyCodes = set(['-5', '-4', '-3',  '-2', '-1', '+0', '+1', '+2', '+3', '+4', '+5'])

def _processParsedCode(
        code: str,
        allowed: typing.Set[str],
        name: str,
        strict: bool
        ) -> typing.Optional[str]:
    if code == '?':
        return None

    code = code.upper()
    if code in allowed:
        return code

    if not strict:
        # TODO: This should log something and probably inform the user for custom sectors
        return None

    raise ValueError(f'Invalid Economics {name} code "{code}"')

def parseSystemEconomicsString(
        economics: str,
        strict: bool = False
        ) -> typing.Tuple[
            typing.Optional[str], # Resources
            typing.Optional[str], # Labour
            typing.Optional[str], # Infrastructure
            typing.Optional[int]]: # Efficiency
    result = _EconomicsPattern.match(economics)
    if not result:
        if not strict:
            return (None, None, None, None)
        raise ValueError(f'Invalid Economics string "{economics}"')

    return (
        _processParsedCode(code=result[1], allowed=_ValidResourcesCodes, name='Resources', strict=strict),
        _processParsedCode(code=result[2], allowed=_ValidLabourCodes, name='Labour', strict=strict),
        _processParsedCode(code=result[3], allowed=_ValidInfrastructureCodes, name='Infrastructure', strict=strict),
        _processParsedCode(code=result[4], allowed=_ValidEfficiencyCodes, name='Efficiency', strict=strict))

def _processFormatCode(
        code: typing.Optional[str],
        allowed: typing.Set[str],
        name: str
        ) -> str:
    if code is None:
        return '?'

    code = code.upper()
    if code not in allowed:
        raise ValueError(f'Invalid Economics {name} code "{code}"')

    return code

def formatSystemEconomicsString(
        resources: typing.Optional[str],
        labour: typing.Optional[str],
        infrastructure: typing.Optional[str],
        efficiency: typing.Optional[str]
        ) -> str:
    return '({resources}{labour}{infrastructure}{efficiency})'.format(
        resources=_processFormatCode(code=resources, allowed=_ValidResourcesCodes, name='Resources'),
        labour=_processFormatCode(code=labour, allowed=_ValidLabourCodes, name='Labour'),
        infrastructure=_processFormatCode(code=infrastructure, allowed=_ValidInfrastructureCodes, name='Infrastructure'),
        efficiency=_processFormatCode(code=efficiency, allowed=_ValidEfficiencyCodes, name='Efficiency'))