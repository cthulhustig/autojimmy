import common
import typing

# There are two sets of base codes, an older set from before Traveller 5th
# edition and a newer set from 5th edition onwards. Unfortunately there are
# some minor conflicts (see https://travellermap.com/doc/secondsurvey#bases).
# I've gone with the approach of using a super set of them all, where there
# are conflicts, going with the 5th edition definition.

_ValidBaseCodes = set([
    'A', # Imperial Naval Base _AND_ Imperial Scout Base
    'B', # Imperial Naval Base _AND_ Way Station
    'C', # Vargr Corsair Base
    'D', # Naval Depot. This was 'Depot (Imerial)' prior to 5th edition
    'E', # Hiver Embassy. This was 'Embassy Center (Hiver)' prior to 5th edition
    'F', # Military Base _AND_ Naval Base
    'G', # Vargr Naval Base
    'H', # Vargr Corsair Base _AND_ Vargr Naval Base
    'J', # Naval Base
    'K', # Naval Base. This was 'Naval Base (K'kree)' prior to 5th edition
    'L', # Hiver Naval Base
    'M', # Military Base
    'N', # Imperial Naval Base
    'O', # K'kree Naval Outpose. Note this uses O so the base codes aren't valid ehex
    'P', # Droyne Naval Base
    'Q', # Droyne Military Garrison
    'R', # Aslan Clan Base
    'S', # Imperial Scout Base
    'T', # Aslan Tlaukhu Base
    'U', # Aslan Tlaukhu Base _AND_ Aslan Clan Base. This was 'Tlauku Base (Aslan)' prior to 5th edition
    'V', # Exploration Base. This was 'Scout/Exploration Base' prior to 5th edition
    'W', # Way Station. This was 'Way Station (Imperial)' prior to 5th edition
    'X', # Zhodani Relay Station
    'Y', # Zhodani Depot
    'Z', # Zhodani Naval Military Base
])

def parseSystemBasesString(
        string: str,
        strict: bool = False
        ) -> typing.Generator[str, None, None]:
    for code in string:
        if code not in _ValidBaseCodes:
            if not strict:
                # TODO: This should probably log
                continue
            raise ValueError(f'Bases string "{string}" contains unrecognised value "{code}"')

        yield code

def formatSystemBasesString(
        bases: typing.Iterable[str]
        ) -> str:
    validCodes = set()
    for code in bases:
        if code not in _ValidBaseCodes:
            raise ValueError(f'Invalid base code "{code}"')
        validCodes.add(code)

    return ''.join(sorted(validCodes))

def _mandatoryBaseValidator(
        name: str,
        value: str
        ) -> None:
    if value not in _ValidBaseCodes:
        raise ValueError(f'{name} must be a valid base code')

def _optionalBaseValidator(
        name: str,
        value: str
        ) -> None:
    if value is not None and value not in _ValidBaseCodes:
        raise ValueError(f'{name} must be a valid base code or None')

def validateMandatoryBase(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryBaseValidator(
            name=name,
            value=value))

def validateOptionalBase(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalBaseValidator(
            name=name,
            value=value))