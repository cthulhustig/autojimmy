from reportlab.lib.styles import ListStyle, ParagraphStyle
from reportlab.platypus import Flowable, ListFlowable, Table, TableStyle

import construction
import pdf
import typing

def createNotesTable(
        steps: typing.Iterable[construction.ConstructionStep],
        tableStyle: typing.Optional[TableStyle] = None,
        headerStyle: typing.Optional[ParagraphStyle] = None,
        contentStyle: typing.Optional[ParagraphStyle] = None,
        listStyle: typing.Optional[ListStyle] = None,
        listItemStyle: typing.Optional[ParagraphStyle] = None,
        copyHeaderOnSplit: bool = True,
        horzCellPadding: float = 5,
        vertCellPadding: float = 3,        
        ) -> typing.Optional[Table]:
    tableData = [[
        pdf.ParagraphEx(
            text='Rule',
            style=headerStyle),
        pdf.ParagraphEx(
            text='Notes',
            style=headerStyle),
        ]]
    
    stepNotesMap = dict()
    for step in steps:
        stepNotes = step.notes()
        if stepNotes:
            rule = f'{step.type()}: {step.name()}'
            cumulative = stepNotesMap.get(rule)
            if not cumulative:
                cumulative = list(stepNotes)
                stepNotesMap[rule] = cumulative
            else:
                # NOTE: Duplicate notes are removed if there are multiple
                # instances of a component
                assert(isinstance(cumulative, list))
                for note in stepNotes:
                    if note not in cumulative:
                        cumulative.append(note)

    for rule, stepNotes in stepNotesMap.items():
        tableData.append([
            pdf.ParagraphEx(
                text=rule,
                style=contentStyle),
            _createNotesList(
                notes=stepNotes,
                listStyle=listStyle,
                itemStyle=listItemStyle)])        

    if len(tableData) <= 1:
        return None # No notes added (only header) so no point creating a table
    
    cellStyles = pdf.createTableCellStyles(
        tableData=tableData,
        horzCellPadding=horzCellPadding,
        vertCellPadding=vertCellPadding)

    return Table(
        data=tableData,
        repeatRows=1 if copyHeaderOnSplit else 0,
        style=tableStyle,
        # Don't expand any columns as long notes cause the left column to be
        # compressed
        colWidths=['*', '*'],
        cellStyles=cellStyles)

def _createNotesList(
        notes: typing.Iterable[str],
        listStyle: typing.Optional[ListStyle],
        itemStyle: typing.Optional[ParagraphStyle]
        ) -> typing.Optional[Flowable]:
    if not notes:
        return None

    listItems = []
    for note in notes:
        listItems.append(pdf.ParagraphEx(
            text=note,
            style=itemStyle))

    return ListFlowable(
        listItems,
        bulletType='bullet',
        start='',
        style=listStyle,
        bulletFontSize=0,
        leftIndent=0)