import common
import re
import typing

_PBGPattern = re.compile(r'^\s*([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])\s*$')
# NOTE: Technically 0 is not a valid option, but, it's allowed as higher level code
# should interpret it as 1 (as per the Traveller Map second survey documentation)
_ValidPopulationMultiplierCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
_ValidPlanetoidBeltsCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
                                'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']) # Any valid ehex
_ValidGasGiantsCodes = _ValidPlanetoidBeltsCodes

def _processParsedCode(
        code: str,
        allowed: typing.Set[str],
        name: str,
        reporter: typing.Optional[common.Reporter]
        ) -> typing.Optional[str]:
    if code == '?':
        return None

    checkCode = code.upper()
    if checkCode not in allowed:
        if reporter:
            reporter.addMessage(f'Ignoring invalid PBG {name} code "{code}"')
        return None

    return checkCode

def parseSystemPBGString(
        pbg: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.Optional[str], # Population Multiplier
            typing.Optional[str], # Planetoid Belts
            typing.Optional[str]]: # Gas Giants
    result = _PBGPattern.match(pbg)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid PBG string "{pbg}"')
        return (None, None, None)

    # Handle a PBG of XXX as a special case to indicate none of the fields are known
    # (equivalent of ???). This format is used by a number of the Traveller Map
    # sectors. It's important to treat it as a special case rather than treating 'X' as
    # unknown for individual fields as 'X' is a valid value for planetoid belt and gas
    # giant counts.
    if result[1] == 'X' and result[2] == 'X' and result[3] == 'X':
        return (None, None, None)

    populationMultiplier = result[1]
    if populationMultiplier == '0':
        # The multiplier is 0 so interpret it as 1, as per the Traveller Map
        # second survey documentation
        populationMultiplier = '1'

        # NOTE: Don't log this as it happens a LOT in stock data
        #if reporter:
        #   reporter.addMessage(f'Interpreting Population Multiplier 0 as 1')

    return (
        _processParsedCode(code=populationMultiplier, allowed=_ValidPopulationMultiplierCodes, name='Population Multiplier', reporter=reporter),
        _processParsedCode(code=result[2], allowed=_ValidPlanetoidBeltsCodes, name='Planetoid Belts', reporter=reporter),
        _processParsedCode(code=result[3], allowed=_ValidGasGiantsCodes, name='Gas Giants', reporter=reporter))

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
            reporter.addMessage(f'Ignoring invalid PBG {name} code "{code}"')
        return '?'

    return checkCode

def formatSystemPBGString(
        populationMultiplier: typing.Optional[str],
        planetoidBelts: typing.Optional[str],
        gasGiants: typing.Optional[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    return '{multiplier}{belts}{giants}'.format(
        multiplier=_processFormatCode(code=populationMultiplier, allowed=_ValidPopulationMultiplierCodes, name='Population Multiplier', reporter=reporter),
        belts=_processFormatCode(code=planetoidBelts, allowed=_ValidPlanetoidBeltsCodes, name='Planetoid Belts', reporter=reporter),
        giants=_processFormatCode(code=gasGiants, allowed=_ValidGasGiantsCodes, name='Gas Giants', reporter=reporter))

def _mandatoryPBGElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value not in allowed:
        raise ValueError(f'{name} must be a valid PBG {element} code')

def _optionalPBGElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f'{name} must be a valid PBG {element} code or None')

def validateMandatoryPopulationMultiplier(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryPBGElementValidator(
            name=name,
            value=value,
            element='PopulationMultiplier',
            allowed=_ValidPopulationMultiplierCodes))

def validateOptionalPopulationMultiplier(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalPBGElementValidator(
            name=name,
            value=value,
            element='PopulationMultiplier',
            allowed=_ValidPopulationMultiplierCodes))

def validateMandatoryPlanetoidBelts(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryPBGElementValidator(
            name=name,
            value=value,
            element='Planetoid Belts',
            allowed=_ValidPlanetoidBeltsCodes))

def validateOptionalPlanetoidBelts(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalPBGElementValidator(
            name=name,
            value=value,
            element='Planetoid Belts',
            allowed=_ValidPlanetoidBeltsCodes))

def validateMandatoryGasGiants(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryPBGElementValidator(
            name=name,
            value=value,
            element='Gas Giants',
            allowed=_ValidGasGiantsCodes))

def validateOptionalGasGiants(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalPBGElementValidator(
            name=name,
            value=value,
            element='Gas Giants',
            allowed=_ValidGasGiantsCodes))