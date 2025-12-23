import re
import typing

_CulturePattern = re.compile(r'\[\s*([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])\s*\]')
_ValidHeterogeneityCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G'])
_ValidAcceptanceCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidStrangenessCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A'])
_ValidSymbolsCodes = set(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L'])

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
        return None

    raise ValueError(f'Invalid Culture {name} code "{code}"')

def parseSystemCultureString(
        culture: str,
        strict: bool = False
        ) -> typing.Tuple[
            typing.Optional[str], # Heterogeneity
            typing.Optional[str], # Acceptance
            typing.Optional[str], # Strangeness
            typing.Optional[str]]: # Symbols
    result = _CulturePattern.match(culture)
    if not result:
        if not strict:
            return (None, None, None, None)
        raise ValueError(f'Invalid Culture string "{culture}"')

    return (
        _processParsedCode(code=result[1], allowed=_ValidHeterogeneityCodes, name='Heterogeneity', strict=strict),
        _processParsedCode(code=result[2], allowed=_ValidAcceptanceCodes, name='Acceptance', strict=strict),
        _processParsedCode(code=result[3], allowed=_ValidStrangenessCodes, name='Strangeness', strict=strict),
        _processParsedCode(code=result[4], allowed=_ValidSymbolsCodes, name='Symbols', strict=strict))

def _processFormatCode(
        code: typing.Optional[str],
        allowed: typing.Set[str],
        name: str
        ) -> str:
    if code is None:
        return '?'
    code = code.upper()
    if code not in allowed:
        raise ValueError(f'Invalid Culture {name} code "{code}"')
    return code

def formatSystemCultureString(
        heterogeneity: typing.Optional[str],
        acceptance: typing.Optional[str],
        strangeness: typing.Optional[str],
        symbols: typing.Optional[str]
        ) -> str:
    return '[{heterogeneity}{acceptance}{strangeness}{symbols}]'.format(
        heterogeneity=_processFormatCode(code=heterogeneity, allowed=_ValidHeterogeneityCodes, name='Heterogeneity'),
        acceptance=_processFormatCode(code=acceptance, allowed=_ValidAcceptanceCodes, name='Acceptance'),
        strangeness=_processFormatCode(code=strangeness, allowed=_ValidStrangenessCodes, name='Strangeness'),
        symbols=_processFormatCode(code=symbols, allowed=_ValidSymbolsCodes, name='Symbols'))