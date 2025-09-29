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
