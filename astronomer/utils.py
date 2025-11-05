import re
import typing

def parseTabContent(content: str) -> typing.Tuple[
        typing.List[str], # Headers
        typing.List[typing.Dict[
            str, # Header
            str]]]: # Value
    header = None
    rows = []
    for line in content.splitlines():
        if not line:
            continue
        if line.startswith('#'):
            continue
        tokens = [t.strip() for t in line.split('\t')]
        if not header:
            header = tokens
            continue

        rows.append({header[i]: t for i, t in enumerate(tokens)})
    return (header, rows)

_DefinitionPattern = re.compile(r'(?:\/*(.|\n)*\*\/|\s*)\s*([^{]*?|\n)\s*{\s*([^{]*?|\n)\s*}')
_GroupPattern = re.compile(r'([\w.]+)')
_PropertyPattern = re.compile(r'\s*(\w+)\s*\:\s*([^;]+?)\s*(?:;|\Z)')

# NOTE: This is a VERY basic css parser that is implements the minimum needed
# to parse the css style files used by Traveller Map (such as otu.css)
def readCssContent(content: str) -> typing.Mapping[
    str, # Group
    typing.Mapping[
        str, # Key
        str]]: # Value
    results = {}
    for definition in _DefinitionPattern.findall(content):
        properties = {}
        for key, value in _PropertyPattern.findall(definition[2]):
            assert(isinstance(key, str))
            properties[key.lower()] = value

        for group in _GroupPattern.findall(definition[1]):
            results[group] = properties.copy()
    return results

def readCssFile(path: str) -> typing.Mapping[
    str, # Group
    typing.Mapping[
        str, # Key
        str]]: # Value
    with open(path, encoding='utf-8-sig') as file:
        return readCssContent(content=file.read())
