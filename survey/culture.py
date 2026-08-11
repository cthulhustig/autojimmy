import common
import re
import typing

# This regex allows the following
# - Matches with and without []
# - Matches with empty brackets or brackets that only contain white space
# - Ignores leading/trailing white space
# - Doesn't match strings that are only white space
# - Treats ? as a valid value for each attribute
_CulturePattern = re.compile(r'^\s*(?:\[\s*(?:([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?]))?\s*\]|([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?])([0-9A-Za-z?]))\s*$')

# NOTE: Use ordered set to hold valid strings as they may get listed in
# error messages a validate* function fails
_ValidHeterogeneityCodes = common.OrderedSet(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G'])
_ValidAcceptanceCodes = common.OrderedSet(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'])
_ValidStrangenessCodes = common.OrderedSet(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A'])
_ValidSymbolsCodes = common.OrderedSet(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L'])

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
            reporter.addMessage(f'Ignoring invalid Culture {name} code "{code}"')
        return None

    return checkCode

def parseSystemCultureString(
        culture: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.Optional[str], # Heterogeneity
            typing.Optional[str], # Acceptance
            typing.Optional[str], # Strangeness
            typing.Optional[str]]: # Symbols
    result = _CulturePattern.match(culture)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Culture string "{culture}"')
        return (None, None, None, None)

    return (
        _processParsedCode(code=result[1], allowed=_ValidHeterogeneityCodes, name='Heterogeneity', reporter=reporter),
        _processParsedCode(code=result[2], allowed=_ValidAcceptanceCodes, name='Acceptance', reporter=reporter),
        _processParsedCode(code=result[3], allowed=_ValidStrangenessCodes, name='Strangeness', reporter=reporter),
        _processParsedCode(code=result[4], allowed=_ValidSymbolsCodes, name='Symbols', reporter=reporter))

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
            reporter.addMessage(f'Ignoring invalid Culture {name} code "{code}"')
        return '?'

    return checkCode

def formatSystemCultureString(
        heterogeneity: typing.Optional[str],
        acceptance: typing.Optional[str],
        strangeness: typing.Optional[str],
        symbols: typing.Optional[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    return '[{heterogeneity}{acceptance}{strangeness}{symbols}]'.format(
        heterogeneity=_processFormatCode(code=heterogeneity, allowed=_ValidHeterogeneityCodes, name='Heterogeneity', reporter=reporter),
        acceptance=_processFormatCode(code=acceptance, allowed=_ValidAcceptanceCodes, name='Acceptance', reporter=reporter),
        strangeness=_processFormatCode(code=strangeness, allowed=_ValidStrangenessCodes, name='Strangeness', reporter=reporter),
        symbols=_processFormatCode(code=symbols, allowed=_ValidSymbolsCodes, name='Symbols', reporter=reporter))

def validateHeterogeneity(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidHeterogeneityCodes)

def validateAcceptance(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidAcceptanceCodes)

def validateStrangeness(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidStrangenessCodes)

def validateSymbols(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidSymbolsCodes)
