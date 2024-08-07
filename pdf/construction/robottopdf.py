from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import CellStyle, PageBreak, Table, TableStyle, Flowable

import app
import math
import pdf
import robots
import typing

_PageSize = A4

_TopMargin = 72.0
_BottomMargin = 72.0
_LeftMargin = 72.0
_RightMargin = 72.0

_FontName = 'Helvetica'
_TitleFontSize = 12
_HeadingFontSize = 8
_NormalFontSize = 5
_NormalFontLeading = _NormalFontSize * 1.2 # Add 20% to font height

_TitleSpacing = 20
_SectionSpacing = 30
_HeadingElementSpacing = 10
_ElementSpacing = 20
_ListItemSpacing = _NormalFontSize * 0.8

_PageColour = '#D4D4D4'
_TextColour = '#000000'

_TableGridColour = '#414141'
_TableLineWidth = 1.5
_CellHorizontalPadding = 5
_CellVerticalPadding = 3

_SingleLineEditBoxVerticalScale = 1.6

_FooterFontSize = 5
_FooterTextColour = '#696969'
_FooterVerticalMargin = 10
_FooterText = f'Created with {app.AppName} v{app.AppVersion}'

_PageNumberFontSize = 8
_PageNumberHorizontalMargin = 20
_PageNumberVerticalMargin = 10

_MaxWastedSpace = 200

_HitsEditBoxWidth = 15

# This controls the number of empty rows added at the bottom of the current details table for user
# specified stuff. These row will have both the state name and value as editable fields
_EditableInfoRows = 4

_ApplySkillModifiersText = \
    'The skills listed in the worksheet have had characteristic DMs and  ' \
    'some other modifiers pre-applied to match how worksheets are shown ' \
    'in the Robot Handbook. These modifiers are also covered in the notes ' \
    'section so care should be taken to not apply the same modifier ' \
    'multiple times.'

_NormalStyle = ParagraphStyle(
    name='Normal',
    parent=getSampleStyleSheet()['Normal'],
    fontName=_FontName,
    alignment=TA_LEFT,
    wordWrap='LTR',
    fontSize=_NormalFontSize,
    leading=_NormalFontLeading,
    textColor=colors.toColor(_TextColour),
    splitLongWords=False,
    justifyBreaks=1)

_TitleStyle = ParagraphStyle(
    name='Title',
    parent=_NormalStyle,
    fontName=_FontName + '-Bold',
    alignment=TA_CENTER,
    fontSize=_TitleFontSize,
    leading=_TitleFontSize)

_HeadingStyle = ParagraphStyle(
    name='Heading',
    parent=_NormalStyle,
    fontName=_FontName + '-Bold',
    fontSize=_HeadingFontSize,
    leading=_HeadingFontSize)

_TableHeaderNormalStyle = ParagraphStyle(
    name='TableHeader',
    parent=_NormalStyle,
    fontName=_FontName + '-Bold')

_TableDataNormalStyle = ParagraphStyle(
    name='TableDataNormal',
    parent=_NormalStyle)

_TableDataBoldStyle = ParagraphStyle(
    name='TableDataBold',
    parent=_TableDataNormalStyle,
    fontName=_FontName + '-Bold')

_TableDataBoldHighlightedStyle = ParagraphStyle(
    name='TableDataBold',
    parent=_TableDataNormalStyle,
    fontName=_FontName + '-Bold',
    backColor='#AAAAAA')

_ListItemStyle = ParagraphStyle(
    name='ListItem',
    parent=_NormalStyle,
    spaceAfter=_ListItemSpacing)

_WorksheetTopRow = [
    robots.Worksheet.Field.Robot,
    robots.Worksheet.Field.Hits,
    robots.Worksheet.Field.Locomotion,
    robots.Worksheet.Field.Speed,
    robots.Worksheet.Field.TL,
    robots.Worksheet.Field.Cost
]

class _Counter():
    def __init__(self) -> None:
        self._value = 0

    def increment(self) -> None:
        self._value += 1

    def value(self) -> int:
        return self._value

class _Notifier(object):
    def __init__(
            self,
            total: int,
            callback: typing.Callable[[int, int], None]
            ) -> None:
        self._total = total
        self._count = 0
        self._callback = callback

    def update(self) -> None:
        self._count += 1
        self._callback(self._count, self._total)

class RobotToPdf(object):
    def __init__(self) -> None:
        self._colour = True

    def export(
            self,
            robot: robots.Robot,
            filePath: str,
            colour: bool = True,
            includeEditableFields: bool = True,
            includeManifestTable: bool = True,
            applySkillModifiers: bool = False,
            specialityGroupingCount: int = 0,
            progressCallback: typing.Optional[typing.Callable[[int, int], None]] = None
            ) -> None:
        self._colour = colour

        notifier = None
        if progressCallback:
            # Perform a dry run to calculate the number of progress updates
            counter = _Counter()
            self._layoutDocument(
                robot=robot,
                includeEditableFields=includeEditableFields,
                includeManifestTable=includeManifestTable,
                applySkillModifiers=applySkillModifiers,
                specialityGroupingCount=specialityGroupingCount,
                layout=None,
                progressCallback=counter.increment)
            counter.increment() # Add 1 for the build step

            notifier = _Notifier(
                total=counter.value(),
                callback=progressCallback)

        layout: typing.List[Flowable] = []
        self._layoutDocument(
            robot=robot,
            includeEditableFields=includeEditableFields,
            includeManifestTable=includeManifestTable,
            applySkillModifiers=applySkillModifiers,
            specialityGroupingCount=specialityGroupingCount,
            layout=layout,
            progressCallback=notifier.update if notifier else None)

        template = pdf.MultiPageDocTemplateEx(
            filePath=filePath,
            pagesize=_PageSize,
            pageColour=_PageColour if self._colour else '#FFFFFF',
            footerText=_FooterText,
            footerFontName=_FontName,
            footerFontSize=_FooterFontSize,
            footerTextColour=_FooterTextColour if self._colour else '#000000',
            footerVMargin=_FooterVerticalMargin,
            enablePageNumbers=True,
            pageNumberFontName=_FontName,
            pageNumberFontSize=_PageNumberFontSize,
            pageNumberTextColour=_TextColour,
            pageNumberHMargin=_PageNumberHorizontalMargin,
            pageNumberVMargin=_PageNumberVerticalMargin,
            topMargin=_TopMargin,
            bottomMargin=_BottomMargin,
            leftMargin=_LeftMargin,
            rightMargin=_RightMargin)
        template.build(layout)
        if notifier:
            notifier.update()

    def _layoutDocument(
            self,
            robot: robots.Robot,
            includeEditableFields: bool,
            includeManifestTable: bool,
            applySkillModifiers: bool,
            specialityGroupingCount: int,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]],
            ) -> None:
        if progressCallback:
            progressCallback()

        self._addTitle(
            robot=robot,
            layout=layout,
            progressCallback=progressCallback)

        self._addInfo(
            robot=robot,
            layout=layout,
            includeEditableFields=includeEditableFields,
            applySkillModifiers=applySkillModifiers,
            specialityGroupingCount=specialityGroupingCount,
            progressCallback=progressCallback)

        if includeManifestTable:
            self._addManifest(
                robot=robot,
                layout=layout,
                progressCallback=progressCallback)

        if includeEditableFields:
            self._addTrailingPages(
                layout=layout,
                progressCallback=progressCallback)

    def _addTitle(
            self,
            robot: robots.Robot,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]] = None,
            ) -> None:
        if layout != None:
            layout.append(pdf.ParagraphEx(text=robot.name(), style=_TitleStyle))
            layout.append(pdf.VerticalSpacer(height=_TitleSpacing))
        if progressCallback:
            progressCallback()

    def _addInfo(
            self,
            robot: robots.Robot,
            layout: typing.Optional[typing.List[Flowable]],
            includeEditableFields: bool,
            applySkillModifiers: bool,
            specialityGroupingCount: int,
            progressCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> None:
        if layout != None:
            sheetTable = self._createWorksheetTable(
                robot=robot,
                includeEditableFields=includeEditableFields,
                applySkillModifiers=applySkillModifiers,
                specialityGroupingCount=specialityGroupingCount)
            notesTable = pdf.createNotesTable(
                steps=robot.steps(),
                tableStyle=self._createTableStyle(),
                headerStyle=_TableHeaderNormalStyle,
                contentStyle=_TableDataNormalStyle,
                listItemStyle=_ListItemStyle,
                copyHeaderOnSplit=True,
                horzCellPadding=_CellHorizontalPadding,
                vertCellPadding=_CellVerticalPadding)
            if sheetTable:
                flowables = []

                if applySkillModifiers:
                    flowables.append(pdf.ParagraphEx(
                        text=_ApplySkillModifiersText,
                        style=_NormalStyle))
                    flowables.append(pdf.VerticalSpacer(
                        height=_ElementSpacing))

                flowables.append(sheetTable)
                if notesTable:
                    flowables.append(pdf.VerticalSpacer(height=_ElementSpacing))
                    flowables.append(notesTable)

                layout.append(pdf.KeepTogetherEx(
                    flowables=flowables,
                    limitWaste=_MaxWastedSpace))

        if progressCallback:
            progressCallback()

    def _addManifest(
            self,
            robot: robots.Robot,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]] = None,
            ) -> None:
        if layout != None:
            manifestTable = pdf.createManifestTable(
                manifest=robot.manifest(),
                tableStyle=self._createTableStyle(),
                headerStyle=_TableHeaderNormalStyle,
                contentStyle=_TableDataNormalStyle,
                totalStyle=_TableDataBoldHighlightedStyle if self._colour else _TableDataBoldStyle,
                copyHeaderOnSplit=True,
                horzCellPadding=5,
                vertCellPadding=3,
                decimalPlaces=robots.ConstructionDecimalPlaces,
                costUnits={
                    robots.RobotCost.Credits: ('Cr', True)}) # Prefix
            if manifestTable:
                layout.append(PageBreak())
                flowables = [
                    pdf.ParagraphEx(text='Manifest', style=_HeadingStyle),
                    pdf.VerticalSpacer(height=_HeadingElementSpacing),
                    manifestTable
                ]
                layout.append(pdf.KeepTogetherEx(
                    flowables=flowables,
                    limitWaste=_MaxWastedSpace))

        if progressCallback:
            progressCallback()

    def _addTrailingPages(
            self,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> None:
        if layout != None:
            tableData = []
            tableSpans = []

            _, usableHeight = self._usablePageSize()
            usableHeight -= math.ceil(_HeadingStyle.fontSize)
            usableHeight -= min(_CellVerticalPadding * 2, usableHeight)
            usableHeight -= 20
            thirdHeight = usableHeight / 3

            row = [
                self._createMultiLineEditBox(
                    name=f'Notes 1',
                    style=_TableDataNormalStyle,
                    maxHeight=thirdHeight),
                pdf.ParagraphEx(text='', style=_TableDataNormalStyle)]
            tableData.append(row)
            tableSpans = [((0, 0), (1, 0))]

            row = [
                self._createMultiLineEditBox(
                    name=f'Notes 2',
                    style=_TableDataNormalStyle,
                    maxHeight=thirdHeight * 2),
                self._createMultiLineEditBox(
                    name=f'Notes 3',
                    style=_TableDataNormalStyle,
                    maxHeight=thirdHeight * 2)]
            tableData.append(row)

            layout.append(PageBreak())
            layout.append(pdf.ParagraphEx(text='Notes', style=_HeadingStyle))
            layout.append(self._createTable(
                data=tableData,
                spans=tableSpans,
                colWidths=['*', '*'],
                copyHeaderOnSplit=False))
            layout.append(PageBreak())
            layout.append(self._createMultiLineEditBox(
                name=f'Notes 4',
                style=_TableDataNormalStyle))

        if progressCallback:
            progressCallback()

    def _createEditBox(
            self,
            name: str,
            style: ParagraphStyle,
            value: str = '',
            multiline=False,
            fixedWidth: typing.Optional[float] = None,
            fixedHeight: typing.Optional[float] = None,
            maxWidth: typing.Optional[float] = None,
            maxHeight: typing.Optional[float] = None
            ) -> pdf.TextFormField:
        return pdf.TextFormField(
            name=name,
            value=value,
            fontName=style.fontName,
            fontSize=style.fontSize,
            textColour=style.textColor,
            multiline=multiline,
            fixedWidth=fixedWidth,
            fixedHeight=fixedHeight,
            maxWidth=maxWidth,
            maxHeight=maxHeight)

    def _createSingleLineEditBox(
            self,
            name: str,
            style: ParagraphStyle,
            value: str = '',
            fixedWidth: typing.Optional[float] = None,
            maxWidth: typing.Optional[float] = None,
            ) -> pdf.TextFormField:
        return self._createEditBox(
            name=name,
            style=style,
            value=value,
            fixedWidth=fixedWidth,
            fixedHeight=style.fontSize * _SingleLineEditBoxVerticalScale,
            maxWidth=maxWidth,
            multiline=False)

    def _createMultiLineEditBox(
            self,
            name: str,
            style: ParagraphStyle,
            value: str = '',
            fixedWidth: typing.Optional[float] = None,
            fixedHeight: typing.Optional[float] = None,
            maxWidth: typing.Optional[float] = None,
            maxHeight: typing.Optional[float] = None
            ) -> pdf.TextFormField:
        return self._createEditBox(
            name=name,
            style=style,
            value=value,
            fixedWidth=fixedWidth,
            fixedHeight=fixedHeight,
            maxWidth=maxWidth,
            maxHeight=maxHeight,
            multiline=True)

    def _createTableStyle(
            self,
            spans: typing.Optional[typing.Iterable[
                typing.Tuple[
                    typing.Tuple[int, int], # Upper left of span
                    typing.Tuple[int, int] # Lower right of span
                    ]]] = None,
            backColours: typing.Optional[typing.Iterable[
                typing.Tuple[
                    typing.Tuple[int, int], # Upper left of span
                    typing.Tuple[int, int], # Lower right of span
                    str, # Background colour string
                    ]]] = None,
            drawGrid: bool = True
            ) -> TableStyle:
        styles = [('VALIGN', (0, 0), (-1, -1), 'TOP')]
        if drawGrid:
            gridColour = _TableGridColour if self._colour else '#000000'
            styles.append(('INNERGRID', (0, 0), (-1, -1), _TableLineWidth, gridColour))
        if spans:
            for ul, br in spans:
                styles.append(('SPAN', ul, br))
        if self._colour and backColours:
            for ul, br, colour in backColours:
                styles.append(('BACKGROUND', ul, br, colour))

        return TableStyle(styles)

    def _createTable(
            self,
            data: typing.List[typing.List[typing.Union[str, Flowable]]],
            spans: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]] = None,
            colWidths: typing.Optional[typing.List[typing.Optional[typing.Union[str, int]]]] = None,
            copyHeaderOnSplit: bool = True,
            tableStyle: typing.Optional[TableStyle] = None,
            cellStyles: typing.Optional[typing.Iterable[typing.Iterable[CellStyle]]] = None,
            ) -> Table:
        if tableStyle == None:
            tableStyle = self._createTableStyle(spans=spans)

        if cellStyles == None:
            cellStyles = pdf.createTableCellStyles(
                tableData=data,
                horzCellPadding=_CellHorizontalPadding,
                vertCellPadding=_CellVerticalPadding)

        return Table(
            data=data,
            repeatRows=1 if copyHeaderOnSplit else 0,
            style=tableStyle,
            colWidths=colWidths,
            cellStyles=cellStyles)

    def _createWorksheetTable(
            self,
            robot: robots.Robot,
            includeEditableFields: bool,
            applySkillModifiers: bool,
            specialityGroupingCount: int
            ) -> Table:
        worksheet = robot.worksheet(
            applySkillModifiers=applySkillModifiers,
            specialityGroupingCount=specialityGroupingCount)
        tableData = []
        tableSpans = []
        cellStyles = []

        row = []
        styles = []
        for field in _WorksheetTopRow:
            if worksheet.hasField(field=field):
                row.append(pdf.ParagraphEx(
                    text=field.value,
                    style=_TableHeaderNormalStyle))
                styles.append(pdf.createTableCellStyle(
                    name=repr((len(row) - 1, 0))))
        tableData.append(row)
        cellStyles.append(styles)
        columnCount = len(row)

        row = []
        styles = []
        for field in _WorksheetTopRow:
            if not worksheet.hasField(field=field):
                continue

            topPadding = 3
            if includeEditableFields and (field == robots.Worksheet.Field.Hits):
                groupData = [[
                    self._createSingleLineEditBox(
                        name=f'HitsEdit',
                        fixedWidth=_HitsEditBoxWidth,
                        style=_TableDataNormalStyle),
                    pdf.ParagraphEx(
                        text=' / ' + worksheet.value(field=field),
                        style=_TableDataNormalStyle)]]
                groupTableStyle = self._createTableStyle(drawGrid=False)
                groupCellStyles = [[
                    pdf.createTableCellStyle(
                        name='HitsEditStyle',
                        horzCellPadding=0,
                        vertCellPadding=0),
                    pdf.createTableCellStyle(
                        name='HitsTextStyle',
                        horzCellPadding=0,
                        vertCellPadding=1)]]
                row.append(self._createTable(
                    data=groupData,
                    colWidths=[None, '*'],
                    tableStyle=groupTableStyle,
                    cellStyles=groupCellStyles))
                topPadding = 2
            else:
                row.append(pdf.ParagraphEx(
                    text=worksheet.value(field=field),
                    style=_TableDataNormalStyle))

            cellStyle = CellStyle(
                repr((len(row) - 1, len(tableData))))
            cellStyle.topPadding = topPadding
            cellStyle.bottomPadding = 3
            cellStyle.leftPadding = cellStyle.rightPadding = 5
            styles.append(cellStyle)
        tableData.append(row)
        cellStyles.append(styles)

        for field in robots.Worksheet.Field:
            if field in _WorksheetTopRow:
                continue
            if not worksheet.hasField(field=field):
                continue

            row = [
                pdf.ParagraphEx(
                    text=field.value,
                    style=_TableHeaderNormalStyle),
                pdf.ParagraphEx(
                    text=worksheet.value(field=field),
                    style=_TableDataNormalStyle)]
            styles = [
                pdf.createTableCellStyle(
                    name=repr((0, len(tableData)))),
                pdf.createTableCellStyle(
                    name=repr((1, len(tableData))))]
            for _ in range(len(row), columnCount):
                row.append(pdf.ParagraphEx(
                    text='',
                    style=_TableDataNormalStyle))
                styles.append(pdf.createTableCellStyle(
                    name=repr((len(row) - 1, len(tableData)))))
            tableData.append(row)
            cellStyles.append(styles)

            rowIndex = len(tableData) - 1
            tableSpans.append(((1, rowIndex), (columnCount - 1, rowIndex)))

        if includeEditableFields:
            for index in range(_EditableInfoRows):
                row = [
                    self._createSingleLineEditBox(
                        name=f'InfoEditName {index + 1}',
                        style=_TableHeaderNormalStyle),
                    self._createSingleLineEditBox(
                        name=f'InfoEditValue {index + 1}',
                        style=_TableHeaderNormalStyle)]
                styles = [
                    pdf.createTableCellStyle(
                        name=repr((0, len(tableData)))),
                    pdf.createTableCellStyle(
                        name=repr((1, len(tableData))))]
                for _ in range(len(row), columnCount):
                    row.append(pdf.ParagraphEx(
                        text='',
                        style=_TableDataNormalStyle))
                    styles.append(pdf.createTableCellStyle(
                        name=repr((len(row) - 1, len(tableData)))))
                tableData.append(row)
                cellStyles.append(styles)

                rowIndex = len(tableData) - 1
                tableSpans.append(((1, rowIndex), (columnCount - 1, rowIndex)))

        return self._createTable(
            data=tableData,
            spans=tableSpans,
            colWidths=[None] * columnCount,
            copyHeaderOnSplit=False,
            cellStyles=cellStyles)

    def _usablePageSize(self) -> typing.Tuple[float, float]:
        return (
            max(_PageSize[0] - (_LeftMargin + _RightMargin), 0),
            max(_PageSize[1] - (_TopMargin + _BottomMargin), 0))
