import re
import typing

_DefinitionPattern = re.compile(r'(?:\/*(.|\n)*\*\/|\s*)\s*([^{]*?|\n)\s*{\s*([^{]*?|\n)\s*}')
_GroupPattern = re.compile(r'(\w+(?:\.(?:\\\s|\w)+)?)') # The \\\s matches escaped spaces for names with spaces (e.g. Core Route)
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
            key = str(key)
            properties[key.lower()] = str(value)

        for group in _GroupPattern.findall(definition[1]):
            group = str(group)

            # Groups names can use '\ ' to allow a space in the name. These
            # should be replaced when parsed
            group = group.replace('\\ ', ' ')

            results[group] = properties.copy()
    return results
