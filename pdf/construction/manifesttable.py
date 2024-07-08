from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, Table, TableStyle

import common
import construction
import enum
import pdf
import typing

def createManifestTable(
        manifest: construction.Manifest,
        tableStyle: typing.Optional[TableStyle] = None,
        headerStyle: typing.Optional[ParagraphStyle] = None,
        contentStyle: typing.Optional[ParagraphStyle] = None,
        totalStyle: typing.Optional[ParagraphStyle] = None,
        copyHeaderOnSplit: bool = True,
        horzCellPadding: float = 5,
        vertCellPadding: float = 3,
        decimalPlaces: int = 3,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]] = None,
        ) -> typing.Optional[Table]:
    if manifest.isEmpty():
        return None

    # Copy table style as it will be updated to add change the
    # background colour on total rows to highlight them
    tableStyle = TableStyle(parent=tableStyle)

    costType = manifest.costsType()
    header = [pdf.ParagraphEx(
        text='Component',
        style=headerStyle)]

    for costId in costType:
        header.append(pdf.ParagraphEx(
            text=costId.value,
            style=headerStyle))
    header.append(pdf.ParagraphEx(
        text='Other Factors',
        style=headerStyle))

    tableData = [header]
    for section in manifest.sections():
        entries = section.entries()
        if not entries:
            continue

        for entry in entries:
            tableData.append(_createManifestEntryRow(
                entry=entry,
                costType=costType,
                contentStyle=contentStyle,
                decimalPlaces=decimalPlaces,
                costUnits=costUnits))

        tableData.append(_createManifestSectionTotalRow(
            row=len(tableData),
            section=section,
            costType=costType,
            contentStyle=totalStyle,
            tableStyle=tableStyle,
            decimalPlaces=decimalPlaces,
            costUnits=costUnits))

    tableData.append(_createManifestTotalRow(
        row=len(tableData),
        manifest=manifest,
        costType=costType,
        contentStyle=totalStyle,
        tableStyle=tableStyle,
        decimalPlaces=decimalPlaces,
        costUnits=costUnits))

    cellStyles = pdf.createTableCellStyles(
        tableData=tableData,
        horzCellPadding=horzCellPadding,
        vertCellPadding=vertCellPadding)

    colWidths = ['*'] + ([None] * (len(header) - 2)) + ['*']

    return Table(
        data=tableData,
        repeatRows=1 if copyHeaderOnSplit else 0,
        style=tableStyle,
        colWidths=colWidths,
        cellStyles=cellStyles)

def _createManifestEntryRow(
        entry: construction.ManifestEntry,
        costType: enum.Enum,
        contentStyle: typing.Optional[ParagraphStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text=entry.component(),
        style=contentStyle)]

    for costId in costType:
        cost = entry.cost(costId=costId)
        if cost:
            if isinstance(cost, construction.ConstantModifier):
                units = None
                prefix = False
                if costUnits and costId in costUnits:
                    units, prefix = costUnits[costId]
                # NOTE: This actually uses infix instead of prefix as the only
                # 'prefixed' numerical values displayed in a manifest are
                # credit amounts
                costString = common.formatNumber(
                    number=cost.numeric(),
                    decimalPlaces=decimalPlaces,
                    infix=units if prefix else None,
                    suffix=units if not prefix else None)
            else:
                costString = cost.displayString(
                    decimalPlaces=decimalPlaces)
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=contentStyle))

    factors = entry.factors()
    if factors:
        factorList = sorted([factor.displayString() for factor in factors])
        factorsString = ''
        for factor in factorList:
            if factorsString:
                factorsString += '\n'
            factorsString += factor
    else:
        factorsString = '-'
    elements.append(pdf.ParagraphEx(
        text=factorsString,
        style=contentStyle))

    return elements

def _createManifestSectionTotalRow(
        row: int,
        section: construction.ManifestSection,
        costType: enum.Enum,
        contentStyle: typing.Optional[ParagraphStyle],
        tableStyle: typing.Optional[TableStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text=f'{section.name()} Total',
        style=contentStyle)]

    for costId in costType:
        cost = section.totalCost(costId=costId)
        if cost and cost.value() != 0:
            units = None
            prefix = False
            if costUnits and costId in costUnits:
                units, prefix = costUnits[costId]
            # NOTE: This actually uses infix instead of prefix as the only
            # 'prefixed' numerical values displayed in a manifest are
            # credit amounts
            costString = common.formatNumber(
                number=cost.value(),
                decimalPlaces=decimalPlaces,
                infix=units if prefix else None,
                suffix=units if not prefix else None)
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=contentStyle))

    # Total rows have no factors
    elements.append(pdf.ParagraphEx(
        text='-',
        style=contentStyle))

    # Highlight total row
    if tableStyle and contentStyle and hasattr(contentStyle, 'backColor'):
        tableStyle.add('BACKGROUND', (0, row), (len(elements) - 1, row), contentStyle.backColor)

    return elements

def _createManifestTotalRow(
        row: int,
        manifest: construction.Manifest,
        costType: enum.Enum,
        contentStyle: typing.Optional[ParagraphStyle],
        tableStyle: typing.Optional[TableStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text='Total',
        style=contentStyle)]

    for costId in costType:
        cost = manifest.totalCost(costId=costId)
        if cost and cost.value() != 0:
            units = None
            prefix = False
            if costUnits and costId in costUnits:
                units, prefix = costUnits[costId]
            # NOTE: This actually uses infix instead of prefix as the only
            # 'prefixed' numerical values displayed in a manifest are
            # credit amounts
            costString = common.formatNumber(
                number=cost.value(),
                decimalPlaces=decimalPlaces,
                infix=units if prefix else None,
                suffix=units if not prefix else None)
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=contentStyle))

    # Total rows have no factors
    elements.append(pdf.ParagraphEx(
        text='-',
        style=contentStyle))

    # Highlight total row
    if tableStyle and contentStyle and hasattr(contentStyle, 'backColor'):
        tableStyle.add('BACKGROUND', (0, row), (len(elements) - 1, row), contentStyle.backColor)

    return elements
