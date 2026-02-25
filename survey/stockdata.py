import enum
import common
import json
import survey
import typing

class StockAllegiancesFormat(enum.Enum):
    TAB = 0
    JSON  = 1

class StockSophontsFormat(enum.Enum):
    TAB = 0
    JSON  = 1

def detectStockAllegiancesFormat(
        content: str
        ) -> StockAllegiancesFormat:
    try:
        result = json.loads(content)
        if result:
            return StockAllegiancesFormat.JSON
    except:
        pass

    return StockAllegiancesFormat.TAB

def parseTabStockAllegiances(
        content: str
        ) -> typing.List[survey.RawStockAllegiance]:
    _, results = common.parseTabTableContent(content=content)

    allegiances: typing.List[survey.RawStockAllegiance] = []
    for index, allegiance in enumerate(results):
        code = allegiance.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for stock allegiance {index + 1}')
        name = allegiance.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for stock allegiance {index + 1}')
        legacy = allegiance.get('Legacy')
        if not legacy:
            raise RuntimeError(f'No legacy code specified for stock allegiance {index + 1}')
        base = allegiance.get('BaseCode')
        location = allegiance.get('Location')

        allegiances.append(survey.RawStockAllegiance(
            code=code,
            name=name,
            legacy=legacy,
            base=base,
            location=location))

    return allegiances

def parseJsonStockAllegiances(
        content: str
        ) -> typing.List[survey.RawStockAllegiance]:
    jsonList = json.loads(content)
    if not isinstance(jsonList, list):
        raise RuntimeError(f'Content is not a json list')

    allegiances: typing.List[survey.RawStockAllegiance] = []
    for index, allegiance in enumerate(jsonList):
        if not isinstance(allegiance, dict):
            raise RuntimeError(f'Item {index + 1} is not a json object')

        code = allegiance.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for stock allegiance {index + 1}')
        if not isinstance(code, str):
            raise RuntimeError(f'Code specified for stock allegiance {index + 1} is not a string')

        name = allegiance.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for stock allegiance {index + 1}')
        if not isinstance(name, str):
            raise RuntimeError(f'Name specified for stock allegiance {index + 1} is not a string')

        legacy = allegiance.get('Legacy')
        if not legacy:
            raise RuntimeError(f'No legacy code specified for stock allegiance {index + 1}')
        if not isinstance(legacy, str):
            raise RuntimeError(f'Legacy code specified for stock allegiance {index + 1} is not a string')

        base = allegiance.get('BaseCode')
        if base is not None and not isinstance(base, str):
            raise RuntimeError(f'Base code specified for stock allegiance {index + 1} is not a string')

        location = allegiance.get('Location')
        if location is not None and not isinstance(location, str):
            raise RuntimeError(f'Location specified for stock allegiance {index + 1} is not a string')

        allegiances.append(survey.RawStockAllegiance(
            code=code,
            name=name,
            legacy=legacy,
            base=base,
            location=location))

    return allegiances

def parseStockAllegiances(
        content: str,
        format: typing.Optional[StockAllegiancesFormat] = None
        ) -> typing.List[survey.RawStockAllegiance]:
    if format is None:
        format = detectStockAllegiancesFormat(content=content)
        if format is None:
            raise ValueError(f'Unable to detect stock allegiances format')

    if format is StockAllegiancesFormat.TAB:
        return parseTabStockAllegiances(content=content)
    elif format is StockAllegiancesFormat.JSON:
        return parseJsonStockAllegiances(content=content)

    raise ValueError('Unrecognised stock allegiances content format')

def detectStockSophontsFormat(
        content: str
        ) -> StockSophontsFormat:
    try:
        result = json.loads(content)
        if result:
            return StockSophontsFormat.JSON
    except:
        pass

    return StockSophontsFormat.TAB

def parseTabStockSophonts(
        content: str
        ) -> typing.List[survey.RawStockSophont]:
    _, results = common.parseTabTableContent(content=content)

    sophonts: typing.List[survey.RawStockSophont] = []
    for index, sophont in enumerate(results):
        code = sophont.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for stock sophont {index + 1}')
        name = sophont.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for stock sophont {index + 1}')
        location = sophont.get('Location')

        sophonts.append(survey.RawStockSophont(
            code=code,
            name=name,
            location=location))

    return sophonts

def parseJsonStockSophonts(
        content: str
        ) -> typing.List[survey.RawStockSophont]:
    jsonList = json.loads(content)
    if not isinstance(jsonList, list):
        raise RuntimeError(f'Content is not a json list')

    sophonts: typing.List[survey.RawStockSophont] = []
    for index, sophont in enumerate(jsonList):
        if not isinstance(sophont, dict):
            raise RuntimeError(f'Item {index + 1} is not a json object')

        code = sophont.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for stock sophont {index + 1}')
        if not isinstance(code, str):
            raise RuntimeError(f'Code specified for stock sophont {index + 1} is not a string')

        name = sophont.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for stock sophont {index + 1}')
        if not isinstance(name, str):
            raise RuntimeError(f'Name specified for stock sophont {index + 1} is not a string')

        location = sophont.get('Location')
        if location is not None and not isinstance(location, str):
            raise RuntimeError(f'Location specified for stock sophont {index + 1} is not a string')

        sophonts.append(survey.RawStockSophont(
            code=code,
            name=name,
            location=location))

    return sophonts

def parseStockSophonts(
        content: str,
        format: typing.Optional[StockSophontsFormat] = None
        ) -> typing.List[survey.RawStockSophont]:
    if format is None:
        format = detectStockSophontsFormat(content=content)
        if format is None:
            raise ValueError(f'Unable to detect stock sophonts format')

    if format is StockSophontsFormat.TAB:
        return parseTabStockSophonts(content=content)
    elif format is StockSophontsFormat.JSON:
        return parseJsonStockSophonts(content=content)

    raise ValueError('Unrecognised stock sophonts content format')