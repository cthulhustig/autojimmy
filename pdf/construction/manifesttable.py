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
                style=contentStyle,
                decimalPlaces=decimalPlaces,
                costUnits=costUnits))

        tableData.append(_createManifestSectionTotalRow(
            section=section,
            costType=costType,
            style=totalStyle,
            decimalPlaces=decimalPlaces,
            costUnits=costUnits))

    tableData.append(_createManifestTotalRow(
        manifest=manifest,
        costType=costType,
        style=totalStyle,
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
        style: typing.Optional[ParagraphStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text=entry.component(),
        style=style)]
    
    for costId in costType:
        cost = entry.cost(costId=costId)
        if cost:
            if isinstance(cost, construction.ConstantModifier):
                units = None
                prefix = False
                if costUnits and costId in costUnits:
                    units, prefix = costUnits[costId]
                costString = common.formatNumber(
                    number=cost.numeric(),
                    decimalPlaces=decimalPlaces,
                    prefix=units if prefix else None,
                    suffix=units if not prefix else None)
            else:
                costString = cost.displayString(
                    decimalPlaces=decimalPlaces)          
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=style))

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
        style=style))

    return elements

def _createManifestSectionTotalRow(
        section: construction.ManifestSection,
        costType: enum.Enum,
        style: typing.Optional[ParagraphStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],        
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text=f'{section.name()} Total',
        style=style)]
    
    for costId in costType:
        cost = section.totalCost(costId=costId)
        if cost and cost.value() != 0:
            units = None
            prefix = False
            if costUnits and costId in costUnits:
                units, prefix = costUnits[costId]
            costString = common.formatNumber(
                number=cost.value(),
                decimalPlaces=decimalPlaces,
                prefix=units if prefix else None,
                suffix=units if not prefix else None)
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=style))    

    # Total rows have no factors
    elements.append(pdf.ParagraphEx(
        text='-',
        style=style))

    return elements

def _createManifestTotalRow(
        manifest: construction.Manifest,
        costType: enum.Enum,
        style: typing.Optional[ParagraphStyle],
        decimalPlaces: int,
        costUnits: typing.Optional[typing.Mapping[
            construction.ConstructionCost,
            typing.Tuple[str, bool] # unit string, is prefix
            ]],            
        ) -> typing.List[typing.Union[str, Flowable]]:
    elements = [pdf.ParagraphEx(
        text='Total',
        style=style)]
    
    for costId in costType:
        cost = manifest.totalCost(costId=costId)
        if cost and cost.value() != 0:
            units = None
            prefix = False
            if costUnits and costId in costUnits:
                units, prefix = costUnits[costId]
            costString = common.formatNumber(
                number=cost.value(),
                decimalPlaces=decimalPlaces,
                prefix=units if prefix else None,
                suffix=units if not prefix else None)
        else:
            costString = '-'
        elements.append(pdf.ParagraphEx(
            text=costString,
            style=style))  

    # Total rows have no factors
    elements.append(pdf.ParagraphEx(
        text='-',
        style=style))

    return elements