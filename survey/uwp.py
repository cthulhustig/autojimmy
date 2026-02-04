import common
import re
import typing

_UWPPattern = re.compile(r'([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])-([0-9A-Za-z?])')
_ValidStarportCodes = set(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'X', 'Y'])
_ValidWorldSizeCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidAtmosphereCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidHydrographicsCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A'])
_ValidPopulationCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidGovernmentCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                             'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X'])
_ValidLawLevelCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                           'G', 'H', 'J', 'K', 'L', 'S'])
_ValidTechLevelCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                            'G', 'H', 'J', 'K', 'L'])

def _processParsedCode(
        code: str,
        allowed: typing.Set[str],
        name: str,
        strict: bool
        ) -> typing.Optional[str]:
    if code == '?':
        return None

    if code in allowed:
        # TODO: This should log something and probably inform the user for custom sectors
        return code

    if not strict:
        return None

    raise ValueError(f'Invalid UWP {name} code "{code}"')

def parseSystemUWPString(
        uwp: str,
        strict: bool = False
        ) -> typing.Tuple[
            typing.Optional[str], # Starport
            typing.Optional[str], # World Size
            typing.Optional[str], # Atmosphere
            typing.Optional[str], # Hydrographics
            typing.Optional[str], # Population
            typing.Optional[str], # Government
            typing.Optional[str], # Law Level
            typing.Optional[str]]: # Tech Level
    # Handle a uwp of XXXXXXX-X as a special case to indicate none of the fields are known
    # (equivalent of ???????-?). This format is used by a number of the Traveller Map
    # sectors. It's important to treat it as a special case rather than treating 'X' as
    # unknown for individual fields as 'X' is a valid value for starport and government.
    if not strict and uwp == 'XXXXXXX-X':
        return (None, None, None, None, None, None, None, None)

    result = _UWPPattern.match(uwp)
    if not result:
        if not strict:
            return (None, None, None, None, None, None, None, None)
        raise ValueError(f'Invalid UWP string "{uwp}"')

    return (
        _processParsedCode(code=result[1], allowed=_ValidStarportCodes, name='Starport', strict=strict),
        _processParsedCode(code=result[2], allowed=_ValidWorldSizeCodes, name='World Size', strict=strict),
        _processParsedCode(code=result[3], allowed=_ValidAtmosphereCodes, name='Atmosphere', strict=strict),
        _processParsedCode(code=result[4], allowed=_ValidHydrographicsCodes, name='Hydrographics', strict=strict),
        _processParsedCode(code=result[5], allowed=_ValidPopulationCodes, name='Population', strict=strict),
        _processParsedCode(code=result[6], allowed=_ValidGovernmentCodes, name='Government', strict=strict),
        _processParsedCode(code=result[7], allowed=_ValidLawLevelCodes, name='Law Level', strict=strict),
        _processParsedCode(code=result[8], allowed=_ValidTechLevelCodes, name='Tech Level', strict=strict))

def _processFormatCode(
        code: typing.Optional[str],
        allowed: typing.Set[str],
        name: str
        ) -> str:
    if code is None:
        return '?'
    if code not in allowed:
        raise ValueError(f'Invalid UWP {name} code "{code}"')
    return code

def formatSystemUWPString(
        starport: typing.Optional[str],
        worldSize: typing.Optional[str],
        atmosphere: typing.Optional[str],
        hydrographics: typing.Optional[str],
        population: typing.Optional[str],
        government: typing.Optional[str],
        lawLevel: typing.Optional[str],
        techLevel: typing.Optional[str]
        ) -> str:
    return '{starport}{worldSize}{atmosphere}{hydrographics}{population}{government}{lawLevel}-{techLevel}'.format(
        starport=_processFormatCode(code=starport, allowed=_ValidStarportCodes, name='Starport'),
        worldSize=_processFormatCode(code=worldSize, allowed=_ValidWorldSizeCodes, name='World Size'),
        atmosphere=_processFormatCode(code=atmosphere, allowed=_ValidAtmosphereCodes, name='Atmosphere'),
        hydrographics=_processFormatCode(code=hydrographics, allowed=_ValidHydrographicsCodes, name='Hydrographics'),
        population=_processFormatCode(code=population, allowed=_ValidPopulationCodes, name='Population'),
        government=_processFormatCode(code=government, allowed=_ValidGovernmentCodes, name='Government'),
        lawLevel=_processFormatCode(code=lawLevel, allowed=_ValidLawLevelCodes, name='Law Level'),
        techLevel=_processFormatCode(code=techLevel, allowed=_ValidTechLevelCodes, name='Tech Level'))

def _mandatoryUWPElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value not in allowed:
        raise ValueError(f'{name} must be a valid UWP {element} code')

def _optionalUWPElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f'{name} must be a valid UWP {element} code or None')

def validateMandatoryStarport(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Starport',
            allowed=_ValidStarportCodes))

def validateOptionalStarport(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Starport',
            allowed=_ValidStarportCodes))

def validateMandatoryWorldSize(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='World Size',
            allowed=_ValidWorldSizeCodes))

def validateOptionalWorldSize(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='World Size',
            allowed=_ValidWorldSizeCodes))

def validateMandatoryAtmosphere(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Atmosphere',
            allowed=_ValidAtmosphereCodes))

def validateOptionalAtmosphere(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Atmosphere',
            allowed=_ValidAtmosphereCodes))

def validateMandatoryHydrographics(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Hydrographics',
            allowed=_ValidHydrographicsCodes))

def validateOptionalHydrographics(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Hydrographics',
            allowed=_ValidHydrographicsCodes))

def validateMandatoryPopulation(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Population',
            allowed=_ValidPopulationCodes))

def validateOptionalPopulation(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Population',
            allowed=_ValidPopulationCodes))

def validateMandatoryGovernment(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Government',
            allowed=_ValidGovernmentCodes))

def validateOptionalGovernment(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Government',
            allowed=_ValidGovernmentCodes))

def validateMandatoryLawLevel(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Law Level',
            allowed=_ValidLawLevelCodes))

def validateOptionalLawLevel(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Law Level',
            allowed=_ValidLawLevelCodes))

def validateMandatoryTechLevel(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryUWPElementValidator(
            name=name,
            value=value,
            element='Tech Level',
            allowed=_ValidTechLevelCodes))

def validateOptionalTechLevel(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalUWPElementValidator(
            name=name,
            value=value,
            element='Tech Level',
            allowed=_ValidTechLevelCodes))