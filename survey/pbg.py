import common
import re
import typing

# TODO: The PBG elements should probably be stored as integers in the db and
# treated as integers elsewhere in the code

_PBGPattern = re.compile(r'([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])')
_ValidPopulationMultiplierCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
_ValidPlanetoidBeltsCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
                                'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']) # Any valid ehex
_ValidGasGiantsCodes = _ValidPlanetoidBeltsCodes

def _processParsedCode(
        code: str,
        allowed: typing.Set[str],
        name: str,
        strict: bool
        ) -> typing.Optional[str]:
    if code == '?':
        return None

    if code in allowed:
        return code

    if not strict:
        # TODO: This should log something and probably inform the user for custom sectors
        return None

    raise ValueError(f'Invalid PBG {name} code "{code}"')

def parseSystemPBGString(
        pbg: str,
        strict: bool = False
        ) -> typing.Tuple[
            typing.Optional[str], # Heterogeneity
            typing.Optional[str], # Acceptance
            typing.Optional[str], # Strangeness
            typing.Optional[str]]: # Symbols
    # Handle a PBG of XXX as a special case to indicate none of the fields are known
    # (equivalent of ???). This format is used by a number of the Traveller Map
    # sectors. It's important to treat it as a special case rather than treating 'X' as
    # unknown for individual fields as 'X' is a valid value for planetoid belt and gas
    # giant counts.
    if not strict and pbg == 'XXX':
        return (None, None, None)

    result = _PBGPattern.match(pbg)
    if not result:
        if not strict:
            return (None, None, None, None)
        raise ValueError(f'Invalid PBG string "{pbg}"')

    return (
        _processParsedCode(code=result[1], allowed=_ValidPopulationMultiplierCodes, name='Population Multiplier', strict=strict),
        _processParsedCode(code=result[2], allowed=_ValidPlanetoidBeltsCodes, name='Planetoid Belts', strict=strict),
        _processParsedCode(code=result[3], allowed=_ValidGasGiantsCodes, name='Gas Giants', strict=strict))

def _processFormatCode(
        code: typing.Optional[str],
        allowed: typing.Set[str],
        name: str
        ) -> str:
    if code is None:
        return '?'
    if code not in allowed:
        raise ValueError(f'Invalid PBG {name} code "{code}"')
    return code

def formatSystemPBGString(
        populationMultiplier: typing.Optional[str],
        planetoidBelts: typing.Optional[str],
        gasGiants: typing.Optional[str]
        ) -> str:
    return '{multiplier}{belts}{giants}'.format(
        multiplier=_processFormatCode(code=populationMultiplier, allowed=_ValidPopulationMultiplierCodes, name='Population Multiplier'),
        belts=_processFormatCode(code=planetoidBelts, allowed=_ValidPlanetoidBeltsCodes, name='Planetoid Belts'),
        giants=_processFormatCode(code=gasGiants, allowed=_ValidGasGiantsCodes, name='Gas Giants'))

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