
import common
import re
import typing

# Details of the format of the stars string can be found here
# https://travellermap.com/doc/secondsurvey#stellar
# https://travellermap.com/doc/fileformats#legacy-sec-format
# The additional (\S+) at the end matches unrecognised data so it
# can be handled if required
_StellarPattern = re.compile(r'([OBAFGKM][0-9])\s*(D|Ia|Ib|III|II|IV|VII|VI|V||)|(D[OBAFGKM]?)|(BD|BH|NS|PSR)|(\S+)')
_ValidLuminosityClasses = set(['D', 'Ia', 'Ib', 'III', 'II', 'IV', 'VII', 'VI', 'V', 'BD', 'BH', 'NS', 'PSR'])
_ValidSpectralClasses = set(['O', 'B', 'A', 'F', 'G', 'K', 'M'])
_ValidSpectralScales = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])

def parseSystemStellarString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[typing.Tuple[
            str, # Luminosity Class
            typing.Optional[str], # Spectral Class
            typing.Optional[str] # Spectral Scale
            ]]:
    stars = []
    for match in _StellarPattern.finditer(string):
        if match[1] and match[2]:
            # Traveller 5 star format
            stars.append((match[2], match[1][0], match[1][1]))
        elif match[3]:
            # Legacy white dwarf format
            stars.append((match[3][0], None if len(match[3]) == 1 else match[3][1], None))
        elif match[4]:
            # Traveller 5 white dwarf/black hole/Neutron Star/Pulsar format
            stars.append((match[4], None, None))
        elif match[5]:
            # Unrecognised data
            if reporter:
                reporter.addMessage(f'Ignoring invalid Stellar string "{match[0]}"')
            continue # Ignore Unrecognised data
    return stars

def formatSystemStellarString(
        stars: typing.Iterable[typing.Tuple[
            str, # Luminosity Class
            typing.Optional[str], # Spectral Class
            typing.Optional[str]]], # Spectral Scale
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    string = ''
    for luminosityClass, spectralClass, spectralScale in stars:
        isValid = True

        if luminosityClass not in _ValidLuminosityClasses:
            if reporter:
                reporter.addMessage(f'Ignoring invalid Stellar Luminosity Class "{luminosityClass}"')
            isValid = False

        if spectralClass is not None and spectralClass not in _ValidSpectralClasses:
            if reporter:
                reporter.addMessage(f'Ignoring invalid Stellar Spectral Class "{spectralClass}"')
            isValid = False

        if spectralScale is not None and spectralScale not in _ValidSpectralScales:
            if reporter:
                reporter.addMessage(f'Ignoring invalid Stellar Spectral Scale "{spectralScale}"')
            isValid = False

        if not isValid:
            continue

        if spectralClass is not None and spectralScale is not None:
            # Traveller 5 star format
            string += '{sep}{spectralClass}{spectralScale} {luminosityClass}'.format(
                sep = ' ' if len(string) > 0 else '',
                luminosityClass=luminosityClass,
                spectralClass=spectralClass,
                spectralScale=spectralScale)
        elif spectralClass is not None:
            # Legacy white dwarf format with spectral class
            string += '{sep}{luminosityClass}{spectralClass}'.format(
                sep = ' ' if len(string) > 0 else '',
                luminosityClass=luminosityClass,
                spectralClass=spectralClass)
        else:
            # Traveller 5 white dwarf/black hole/Neutron Star/Pulsar format and legacy white
            # dwarf format without a spectral class
            string += '{sep}{luminosityClass}'.format(
                sep = ' ' if len(string) > 0 else '',
                luminosityClass=luminosityClass)
    return string

def _mandatoryStellarElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value not in allowed:
        raise ValueError(f'{name} must be a valid stellar {element} code')

def _optionalStellarElementValidator(
        name: str,
        value: str,
        element: str,
        allowed: typing.Collection[str],
        ) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f'{name} must be a valid stellar {element} code or None')

def validateMandatoryLuminosityClass(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryStellarElementValidator(
            name=name,
            value=value,
            element='Luminosity Class',
            allowed=_ValidLuminosityClasses))

def validateOptionalLuminosityClass(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalStellarElementValidator(
            name=name,
            value=value,
            element='Luminosity Class',
            allowed=_ValidLuminosityClasses))

def validateMandatorySpectralClass(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryStellarElementValidator(
            name=name,
            value=value,
            element='Spectral Class',
            allowed=_ValidSpectralClasses))

def validateOptionalSpectralClass(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalStellarElementValidator(
            name=name,
            value=value,
            element='Spectral Class',
            allowed=_ValidSpectralClasses))

def validateMandatorySpectralScale(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryStellarElementValidator(
            name=name,
            value=value,
            element='Spectral Scale',
            allowed=_ValidSpectralScales))

def validateOptionalSpectralScale(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalStellarElementValidator(
            name=name,
            value=value,
            element='Spectral Scale',
            allowed=_ValidSpectralScales))