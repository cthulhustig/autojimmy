import html
import typing

# Details of what HTML subset is supported for tooltips
# https://doc.qt.io/qt-5/richtext-html-subset.html

TooltipIndentListStyle = 'margin-left:15px; -qt-list-indent:0;'

# Over time this has become a little pointless. Its being kept in case I need to add a style sheet to all
# tool tips
def createStringToolTip(
        string: str,
        escape: bool = True
        ) -> str:
    if escape:
        string = html.escape(string)
    return f'<html>{string}</html>'

def createListToolTip(
        title: str,
        strings: typing.Iterable[str],
        stringColours: typing.Optional[typing.Dict[str, str]] = None,
        stringIndents: typing.Optional[typing.Dict[str, int]] = None
        ) -> str:
    # This is a hack. Create a list with a single item for the title then have a sub list containing
    # the supplied list entries. This is done as I couldn't figure out another way to prevent a big
    # gap between the title and the list
    toolTip = '<html>'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'
    toolTip += f'<li>{html.escape(title)}</li>'
    toolTip += f'<ul style="{TooltipIndentListStyle}">'

    for string in strings:
        indent = 0
        if stringIndents and string in stringIndents:
            indent = stringIndents[string]
        if indent:
            for _ in range(indent):
                toolTip += f'<ul style="{TooltipIndentListStyle}">'

        style = None
        if stringColours and string in stringColours:
            style = f'style="background-color:{stringColours[string]}"'
        toolTip += f'<li><span {style}><nobr>{html.escape(string)}</nobr></span></li>'

        if indent:
            for _ in range(indent):
                toolTip += '</ul>'

    toolTip += '</ul>'
    toolTip += '</ul>'
    toolTip += '</html>'

    return toolTip
