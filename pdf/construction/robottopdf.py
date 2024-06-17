from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Table, TableStyle, Flowable

import app
import pdf
import robots
import typing

_PageSize = A4

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

_TableGridColour = '#D36852'
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

_TableHeaderCenterStyle = ParagraphStyle(
    name='TableHeaderCenter',
    parent=_TableHeaderNormalStyle,
    alignment=TA_CENTER)

_TableDataNormalStyle = ParagraphStyle(
    name='TableDataNormal',
    parent=_NormalStyle)

_TableDataBoldStyle = ParagraphStyle(
    name='TableDataBold',
    parent=_TableDataNormalStyle,
    fontName=_FontName + '-Bold')

_ListItemStyle = ParagraphStyle(
    name='ListItem',
    parent=_NormalStyle,
    spaceAfter=_ListItemSpacing)

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
            pageNumberVMargin=_PageNumberVerticalMargin)
        template.build(layout)
        if notifier:
            notifier.update()

    def _layoutDocument(
            self,
            robot: robots.Robot,
            includeEditableFields: bool,
            includeManifestTable: bool,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]],
            ) -> None:
        if progressCallback:
            progressCallback()

        self._addTitle(
            robot=robot,
            layout=layout,
            progressCallback=progressCallback)

        if includeEditableFields:
            # TODO: Include editable fields???????
            pass

        if includeManifestTable:
            self._addManifest(
                robot=robot,
                layout=layout,
                progressCallback=progressCallback)
            
        # TODO: Add robot stats

        self._addNotes(
            robot=robot,
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
                totalStyle=_TableDataBoldStyle,
                copyHeaderOnSplit=True,
                horzCellPadding=5,
                vertCellPadding=3,
                decimalPlaces=robots.ConstructionDecimalPlaces,
                costUnits={
                    robots.RobotCost.Credits: ('Cr', True)}) # Prefix
            if manifestTable:
                flowables = [
                    pdf.VerticalSpacer(height=_SectionSpacing),
                    pdf.ParagraphEx(text='Manifest', style=_HeadingStyle),
                    pdf.VerticalSpacer(height=_HeadingElementSpacing),
                    manifestTable
                ]
                layout.append(pdf.KeepTogetherEx(
                    flowables=flowables,
                    limitWaste=_MaxWastedSpace))

        if progressCallback:
            progressCallback()

    def _addNotes(
            self,
            robot: robots.Robot,
            layout: typing.Optional[typing.List[Flowable]],
            progressCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> None:
        if layout != None:
            notesTable = pdf.createNotesTable(
                steps=robot.steps(),
                tableStyle=self._createTableStyle(),
                headerStyle=_TableHeaderNormalStyle,
                contentStyle=_TableDataNormalStyle,
                listItemStyle=_ListItemStyle,
                copyHeaderOnSplit=True,
                horzCellPadding=_CellHorizontalPadding,
                vertCellPadding=_CellVerticalPadding)
            if notesTable:
                flowables = [
                    pdf.VerticalSpacer(height=_ElementSpacing),
                    notesTable
                ]
                layout.append(pdf.KeepTogetherEx(
                    flowables=flowables,
                    limitWaste=_MaxWastedSpace))

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
            spans: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]] = None,
            ) -> Table:
        gridColour = _TableGridColour if self._colour else '#000000'
        styles = [
            ('INNERGRID', (0, 0), (-1, -1), _TableLineWidth, gridColour),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]
        if spans:
            for ul, br in spans:
                styles.append(('SPAN', ul, br))

        return TableStyle(styles)
    
    def _createTable(
            self,
            data: typing.List[typing.List[typing.Union[str, Flowable]]],
            spans: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]] = None,
            colWidths: typing.Optional[typing.List[typing.Optional[typing.Union[str, int]]]] = None,
            copyHeaderOnSplit: bool = True
            ) -> Table:
        tableStyle = self._createTableStyle(spans=spans)

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
