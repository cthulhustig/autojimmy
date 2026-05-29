import common
import re
import typing

_UWPPattern = re.compile(r'^\s*([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])-([0-9A-Za-z?])\s*$')
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
        reporter: typing.Optional[common.Reporter]
        ) -> typing.Optional[str]:
    if code == '?':
        return None

    checkCode = code.upper()
    if checkCode not in allowed:
        if reporter:
            reporter.addMessage(f'Ignoring invalid UWP {name} code "{code}"')
        return None

    return checkCode

def parseSystemUWPString(
        uwp: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.Optional[str], # Starport
            typing.Optional[str], # World Size
            typing.Optional[str], # Atmosphere
            typing.Optional[str], # Hydrographics
            typing.Optional[str], # Population
            typing.Optional[str], # Government
            typing.Optional[str], # Law Level
            typing.Optional[str]]: # Tech Level
    result = _UWPPattern.match(uwp)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid UWP string "{uwp}"')
        return (None, None, None, None, None, None, None, None)

    # Handle a uwp of XXXXXXX-X as a special case to indicate none of the fields are known
    # (equivalent of ???????-?). This format is used by a number of the Traveller Map
    # sectors. It's important to treat it as a special case rather than treating 'X' as
    # unknown for individual fields as 'X' is a valid value for starport and government.
    isAllX = result[1] == 'X' and result[2] == 'X' and result[3] == 'X' and result[4] == 'X' and \
        result[5] == 'X' and result[6] == 'X' and result[7] == 'X' and result[8] == 'X'
    if isAllX:
        return (None, None, None, None, None, None, None, None)

    return (
        _processParsedCode(code=result[1], allowed=_ValidStarportCodes, name='Starport', reporter=reporter),
        _processParsedCode(code=result[2], allowed=_ValidWorldSizeCodes, name='World Size', reporter=reporter),
        _processParsedCode(code=result[3], allowed=_ValidAtmosphereCodes, name='Atmosphere', reporter=reporter),
        _processParsedCode(code=result[4], allowed=_ValidHydrographicsCodes, name='Hydrographics', reporter=reporter),
        _processParsedCode(code=result[5], allowed=_ValidPopulationCodes, name='Population', reporter=reporter),
        _processParsedCode(code=result[6], allowed=_ValidGovernmentCodes, name='Government', reporter=reporter),
        _processParsedCode(code=result[7], allowed=_ValidLawLevelCodes, name='Law Level', reporter=reporter),
        _processParsedCode(code=result[8], allowed=_ValidTechLevelCodes, name='Tech Level', reporter=reporter))

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
            reporter.addMessage(f'Ignoring invalid UWP {name} code "{code}"')
        return '?'

    return checkCode

def formatSystemUWPString(
        starport: typing.Optional[str],
        worldSize: typing.Optional[str],
        atmosphere: typing.Optional[str],
        hydrographics: typing.Optional[str],
        population: typing.Optional[str],
        government: typing.Optional[str],
        lawLevel: typing.Optional[str],
        techLevel: typing.Optional[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    return '{starport}{worldSize}{atmosphere}{hydrographics}{population}{government}{lawLevel}-{techLevel}'.format(
        starport=_processFormatCode(code=starport, allowed=_ValidStarportCodes, name='Starport', reporter=reporter),
        worldSize=_processFormatCode(code=worldSize, allowed=_ValidWorldSizeCodes, name='World Size', reporter=reporter),
        atmosphere=_processFormatCode(code=atmosphere, allowed=_ValidAtmosphereCodes, name='Atmosphere', reporter=reporter),
        hydrographics=_processFormatCode(code=hydrographics, allowed=_ValidHydrographicsCodes, name='Hydrographics', reporter=reporter),
        population=_processFormatCode(code=population, allowed=_ValidPopulationCodes, name='Population', reporter=reporter),
        government=_processFormatCode(code=government, allowed=_ValidGovernmentCodes, name='Government', reporter=reporter),
        lawLevel=_processFormatCode(code=lawLevel, allowed=_ValidLawLevelCodes, name='Law Level', reporter=reporter),
        techLevel=_processFormatCode(code=techLevel, allowed=_ValidTechLevelCodes, name='Tech Level', reporter=reporter))

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