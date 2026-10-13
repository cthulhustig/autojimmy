import typing

# Parses tab separated table content
def parseTabTableContent(content: str) -> typing.Tuple[
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

def readTabTableFail(path: str) -> typing.Mapping[
    str, # Group
    typing.Mapping[
        str, # Key
        str]]: # Value
    with open(path, encoding='utf-8-sig') as file:
        return parseTabTableContent(content=file.read())