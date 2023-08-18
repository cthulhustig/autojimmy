from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Flowable, ListFlowable, CellStyle

import app
import common
import copy
import enum
import gunsmith
import math
import pdf
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

# This controls the number of empty rows added at the bottom of the current details table for user
# specified stuff. These row will have both the state name and value as editable fields
_CustomCurrentDetailRows = 4

_FooterFontSize = 5
_FooterTextColour = '#696969'
_FooterVerticalMargin = 10
_FooterText = f'Created with {app.AppName} v{app.AppVersion}'

_PageNumberFontSize = 8
_PageNumberHorizontalMargin = 20
_PageNumberVerticalMargin = 10

_CompactLayoutMaxSequences = 2
_CompactLayoutColumnWidth = 80
_StandardLayoutNotesHeight = 100

_MaxWastedSpace = 200

_BaseDetailsSectionText = \
    'This section shows the details of the base weapon. This is without modifiers for munitions ' \
    'and removable accessories applied.'
_AccessoriesSectionText = \
    'This section shows the details of the weapon with different removable accessories attached. ' \
    'Attribute values and notes from the Basic Configuration section apply unless alternates are ' \
    'specified. Traits show are the complete list of traits for the weapon when the accessory is ' \
    'attached.'
_AmmoSectionText = \
    'This section shows the details of the weapon when loaded with different types of ammunition ' \
    'and, if appropriate, magazines. Attribute values and notes from the Basic Configuration ' \
    'section apply unless alternates are specified. Traits show are the complete list of traits for ' \
    'the weapon when using the ammunition/magazine.'

# Mapping that defines alternate strings to be used for attributes. If an attribute
# doesn't have an entry its name will be used
_AttributeHeaderOverrideMap = {
    gunsmith.AttributeId.AmmoCapacity: 'Ammo\nCapacity',
    gunsmith.AttributeId.AmmoCost: 'Ammo\nCost',
    gunsmith.AttributeId.BarrelCount: 'Barrel\nCount',
    gunsmith.AttributeId.HeatGeneration: 'Heat\nGeneration',
    gunsmith.AttributeId.AutoHeatGeneration: 'Auto Heat\nGeneration',
    gunsmith.AttributeId.HeatDissipation: 'Heat\nDissipation',
    gunsmith.AttributeId.OverheatThreshold: 'Overheat\nThreshold',
    gunsmith.AttributeId.DangerHeatThreshold: 'Danger Heat\nThreshold',
    gunsmith.AttributeId.DisasterHeatThreshold: 'Disaster Heat\nThreshold',
    gunsmith.AttributeId.MalfunctionDM: 'Malfunction\nDM',
    gunsmith.AttributeId.AutoRecoil: 'Auto\nRecoil',
    gunsmith.AttributeId.PropellantWeight: 'Propellant\nWeight',
    gunsmith.AttributeId.FuelWeight: 'Fuel\nWeight',
    gunsmith.AttributeId.PropellantCost: 'Propellant\nCost Per Kg',
    gunsmith.AttributeId.FuelCost: 'Fuel Cost\nPer Kg',
    gunsmith.AttributeId.MaxDamageDice: 'Max Damage\nDice',
    gunsmith.AttributeId.PowerPerShot: 'Power\nPer Shot',
    gunsmith.AttributeId.EmissionsSignature: 'Emissions\nSignature',
    gunsmith.AttributeId.PhysicalSignature: 'Physical\nSignature'
}

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

def exportToPDF(
        weapon: gunsmith.Weapon,
        filePath: str,
        includeEditableFields: bool = True,
        includeAmmoTable: bool = True,
        usePurchasedMagazines: bool = False,
        usePurchasedAmmo: bool = False,
        progressCallback: typing.Optional[typing.Callable[[int, int], None]] = None
        ) -> None:
    notifier = None
    if progressCallback:
        # Perform a dry run to calculate the number of progress updates
        counter = _Counter()
        _layoutDocument(
            weapon=weapon,
            includeEditableFields=includeEditableFields,
            includeAmmoTable=includeAmmoTable,
            usePurchasedMagazines=usePurchasedMagazines,
            usePurchasedAmmo=usePurchasedAmmo,
            layout=None,
            progressCallback=counter.increment)
        counter.increment() # Add 1 for the build step

        notifier = _Notifier(
            total=counter.value(),
            callback=progressCallback)

    layout: typing.List[Flowable] = []
    _layoutDocument(
        weapon=weapon,
        includeEditableFields=includeEditableFields,
        includeAmmoTable=includeAmmoTable,
        usePurchasedMagazines=usePurchasedMagazines,
        usePurchasedAmmo=usePurchasedAmmo,
        layout=layout,
        progressCallback=notifier.update if notifier else None)

    template = pdf.MultiPageDocTemplateEx(
        filePath=filePath,
        pagesize=_PageSize,
        pageColour=_PageColour,
        footerText=_FooterText,
        footerFontName=_FontName,
        footerFontSize=_FooterFontSize,
        footerTextColour=_FooterTextColour,
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
        weapon: gunsmith.Weapon,
        includeEditableFields: bool,
        includeAmmoTable: bool,
        usePurchasedMagazines: bool,
        usePurchasedAmmo: bool,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]],
        ) -> None:
    # Create a copy of the passed in weapon as it will be modified during the export
    if layout != None:
        weapon = _createExportWeapon(originalWeapon=weapon)
    if progressCallback:
        progressCallback()

    _addTitle(
        weapon=weapon,
        layout=layout,
        progressCallback=progressCallback)

    if includeEditableFields:
        _addCurrentDetails(
            weapon=weapon,
            layout=layout,
            progressCallback=progressCallback)

    _addManifest(
        weapon=weapon,
        layout=layout,
        progressCallback=progressCallback)

    _addInformation(
        weapon=weapon,
        includeAmmoTables=includeAmmoTable,
        usePurchasedMagazines=usePurchasedMagazines,
        usePurchasedAmmo=usePurchasedAmmo,
        layout=layout,
        progressCallback=progressCallback)

def _addTitle(
        weapon: gunsmith.Weapon,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        ) -> None:
    if layout != None:
        layout.append(_createParagraph(text=weapon.weaponName(), style=_TitleStyle))
        layout.append(_createVerticalSpacer(spacing=_TitleSpacing))
    if progressCallback:
        progressCallback()

def _addCurrentDetails(
        weapon: gunsmith.Weapon,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        ) -> None:
    if layout != None:
        flowables = [
            _createVerticalSpacer(spacing=_SectionSpacing),
            _createParagraph(text='Current Details', style=_HeadingStyle),
            _createVerticalSpacer(spacing=_HeadingElementSpacing),
            _createCurrentDetails(weapon=weapon)
        ]
        layout.append(pdf.KeepTogetherEx(
            flowables=flowables,
            limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

def _addManifest(
        weapon: gunsmith.Weapon,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        ) -> None:
    if layout != None:
        flowables = [
            _createVerticalSpacer(spacing=_SectionSpacing),
            _createParagraph(text='Manifest', style=_HeadingStyle),
            _createVerticalSpacer(spacing=_HeadingElementSpacing),
            _createManifestTable(weapon=weapon)
        ]
        layout.append(pdf.KeepTogetherEx(
            flowables=flowables,
            limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

def _addInformation(
        weapon: gunsmith.Weapon,
        includeAmmoTables: bool,
        usePurchasedMagazines: bool,
        usePurchasedAmmo: bool,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        ) -> None:
    baseWeapon = None
    if layout != None:
        baseWeapon = copy.deepcopy(weapon)
    if progressCallback:
        progressCallback()

    sequences = weapon.sequences()
    for index, sequence in enumerate(sequences):
        if layout != None:
            _resetWeaponToBase(weapon=baseWeapon)
        if progressCallback:
            progressCallback()

        prefix = _generateSequencePrefix(
            sequenceIndex=index,
            sequenceCount=len(sequences))

        _addWeaponDetails(
            weapon=baseWeapon, # Use base weapon for details
            sequence=sequence,
            prefix=prefix,
            layout=layout,
            progressCallback=progressCallback)

        _addAccessoriesTable(
            weapon=baseWeapon,  # Use base weapon for accessories
            sequence=sequence,
            prefix=prefix,
            layout=layout,
            progressCallback=progressCallback)

        if includeAmmoTables:
            _addLoadedAmmoTable(
                weapon=weapon, # User original weapon as ammo/magazine quantities may be needed
                sequence=sequence,
                usePurchasedMagazines=usePurchasedMagazines,
                usePurchasedAmmo=usePurchasedAmmo,
                prefix=prefix,
                layout=layout,
                progressCallback=progressCallback)

# Create tables for base weapon details
def _addWeaponDetails(
        weapon: gunsmith.Weapon,
        sequence: str,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        prefix: typing.Optional[str] = None
        ) -> None:
    if layout != None:
        flowables = [
            _createVerticalSpacer(spacing=_SectionSpacing),
            _createParagraph(
                text=_prefixText(prefix=prefix, text='Basic Configuration'),
                style=_HeadingStyle),
            _createVerticalSpacer(spacing=_HeadingElementSpacing),
            _createParagraph(
                text=_BaseDetailsSectionText,
                style=_NormalStyle),
            _createVerticalSpacer(spacing=_HeadingElementSpacing),
            _createWeaponTable(weapon=weapon, sequence=sequence)
        ]
        layout.append(pdf.KeepTogetherEx(
            flowables=flowables,
            limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

    # Create a table for the base weapon. This doesn't include notes for
    # detachable accessories or loaded magazine & ammo
    if layout != None:
        notesTable = _createNotesTable(weapon=weapon, sequence=sequence)
        if notesTable:
            flowables = [
                _createVerticalSpacer(spacing=_ElementSpacing),
                notesTable
            ]
            layout.append(pdf.KeepTogetherEx(
                flowables=flowables,
                limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

def _addAccessoriesTable(
        weapon: gunsmith.Weapon,
        sequence: str,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        prefix: typing.Optional[str] = None
        ) -> None:
    if layout != None:
        accessoriesTable = _createAccessoriesTable(weapon=weapon, sequence=sequence)
        if accessoriesTable:
            flowables = [
                _createVerticalSpacer(spacing=_SectionSpacing),
                _createParagraph(
                    text=_prefixText(prefix=prefix, text='Removable Accessories'),
                    style=_HeadingStyle),
                _createVerticalSpacer(spacing=_HeadingElementSpacing),
                _createParagraph(
                    text=_AccessoriesSectionText,
                    style=_NormalStyle),
                _createVerticalSpacer(spacing=_HeadingElementSpacing),
                accessoriesTable
            ]
            layout.append(pdf.KeepTogetherEx(
                flowables=flowables,
                limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

def _addLoadedAmmoTable(
        weapon: gunsmith.Weapon,
        sequence: str,
        usePurchasedMagazines: bool,
        usePurchasedAmmo: bool,
        layout: typing.Optional[typing.List[Flowable]],
        progressCallback: typing.Optional[typing.Callable[[], None]] = None,
        prefix: typing.Optional[str] = None
        ) -> None:
    if layout != None:
        ammoTable = _createAmmoTable(
            weapon=weapon,
            sequence=sequence,
            usePurchasedMagazines=usePurchasedMagazines,
            usePurchasedAmmo=usePurchasedAmmo)
        if ammoTable:
            hasRemovableMagazine = weapon.hasComponent(
                componentType=gunsmith.RemovableMagazineFeed,
                sequence=sequence)
            baseText = 'Magazines & Ammunition' if hasRemovableMagazine else 'Ammunition'

            flowables = [
                _createVerticalSpacer(spacing=_SectionSpacing),
                _createParagraph(
                    text=_prefixText(prefix=prefix, text=baseText),
                    style=_HeadingStyle),
                _createVerticalSpacer(spacing=_HeadingElementSpacing),
                _createParagraph(
                    text=_AmmoSectionText,
                    style=_NormalStyle),
                _createVerticalSpacer(spacing=_HeadingElementSpacing),
                ammoTable
            ]
            layout.append(pdf.KeepTogetherEx(
                flowables=flowables,
                limitWaste=_MaxWastedSpace))

    if progressCallback:
        progressCallback()

# Create a copy of the weapon for the export process. This has all accessories attached and all
# loaded ammo/magazines removed. This is done in preparation for generating the manifest where
# it should reflect the full (unloaded) weapon weight/cost and all accessory modifiers should be
# show. The final attributes and notes don't mater at this point as they're not displayed in the
# manifest. The weapon will be updated again later for the other tables
def _createExportWeapon(
        originalWeapon: gunsmith.Weapon
        ) -> gunsmith.Weapon:
    weapon = copy.deepcopy(originalWeapon)

    updated = False

    # Remove loaded magazines & ammo from all sequences
    if weapon.unloadWeapon(sequence=None, regenerate=False):
        updated = True

    # Attach detachable accessories for all sequences
    if weapon.setAccessorAttachment(sequence=None, attach=True, regenerate=False):
        updated = True

    if updated:
        weapon.regenerate()

    return weapon

# This resets the weapon to its base setup. The weapon is unloaded, all munitions are removed and
# all detachable accessories are detached
def _resetWeaponToBase(
        weapon: gunsmith.Weapon
        ):
    updated = False

    # Remove munitions and loaded magazines & ammo from all sequences
    if weapon.clearComponents(sequence=None, phase=gunsmith.ConstructionPhase.Munitions, regenerate=False):
        updated = True
    if weapon.unloadWeapon(sequence=None, regenerate=False):
        updated = True

    # Detach all detachable accessories fpr all sequences
    if weapon.setAccessorAttachment(sequence=None, attach=False, regenerate=False):
        updated = True

    if updated:
        weapon.regenerate()

def _generateSequencePrefix(
        sequenceIndex: int,
        sequenceCount: int
        ) -> typing.Optional[str]:
    if sequenceCount == 1:
        return None
    elif sequenceIndex == 0:
        return 'Primary Weapon'
    elif sequenceCount == 2:
        return 'Secondary Weapon'
    else:
        return f'Secondary Weapon {sequenceIndex}'

def _prefixText(
        prefix: typing.Optional[str],
        text: str
        ) -> str:
    if not prefix:
        return text
    return prefix + ' ' + text

def _formatAttributeString(
        attribute: gunsmith.AttributeInterface,
        includeName: bool = False,
        alwaysSignNumbers: bool = False,
        useDashForNoValue: bool = False,
        bracketValue: bool = False
        ) -> str:
    value = attribute.value()
    valueString = None
    if value == None:
        if useDashForNoValue:
            valueString = '-'
    elif isinstance(value, common.ScalarCalculation):
        valueString = common.formatNumber(
            number=value.value(),
            alwaysIncludeSign=alwaysSignNumbers)
    elif isinstance(value, common.DiceRoll):
        valueString = str(value)
    elif isinstance(value, enum.Enum):
        valueString = str(value.value)
    else:
        raise TypeError(f'Attribute {attribute.name()} has unknown value type {type(value)}')

    text = ''
    if includeName:
        text += attribute.name()
    if valueString:
        if bracketValue:
            if text:
                text += ' '
            text += '('
        text += valueString
        if bracketValue:
            text += ')'

    return text

def _collectConstructionNotes(
        weapon: gunsmith.Weapon,
        sequence: str,
        ) -> typing.Mapping[str, typing.Collection[str]]:
    results = dict()
    for step in weapon.steps(sequence=sequence):
        notes = step.notes()
        if notes:
            results[f'{step.type()}: {step.name()}'] = list(notes)
    return results

def _diffConstructionNotes(
        weapon: gunsmith.Weapon,
        sequence: str,
        originalNotes: typing.Mapping[str, typing.Collection[str]]
        ) -> typing.Mapping[str, typing.Collection[str]]:
    results = dict()
    processed = set()

    for step in weapon.steps(sequence=sequence):
        rule = f'{step.type()}: {step.name()}'
        processed.add(rule)

        original = originalNotes[rule] if rule in originalNotes else []
        current = step.notes()

        # Determine if _ANY_ of the notes have changed for this stage. If they have then all notes
        # for the stage need to be returned. This is the best way I can see to make things
        # unambiguous, if an accessory or munitions entry has notes for a stage then they completely
        # replace all notes for that stage in the base notes section
        hasChanged = False
        if len(original) != len(current):
            # The number of notes is different so something must have changed
            hasChanged = True
        else:
            for note in original:
                if note not in current:
                    hasChanged = True
                    break

        if not hasChanged:
            continue # Nothing more to do for this stage

        # Create a copy of the list of notes that can be added to the results
        current = list(current)
        if not current:
            # There are no current notes but there were previously
            current.append('Notes listed for this rule in the Base Configuration section no longer apply.')
        results[rule] = current

    # Check for rules that are no-longer present
    for rule in originalNotes.keys():
        if rule not in processed:
            results[rule] = ['Notes listed for this rule in the Base Configuration section no longer apply.']

    return results

def _createParagraph(
        text: str,
        style: ParagraphStyle
        ) -> Paragraph:
    return Paragraph(
        text=text.replace('\n', '<br />\n'),
        style=style)

def _createEditBox(
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
        name: str,
        style: ParagraphStyle,
        value: str = '',
        fixedWidth: typing.Optional[float] = None,
        maxWidth: typing.Optional[float] = None,
        ) -> pdf.TextFormField:
    return _createEditBox(
        name=name,
        style=style,
        value=value,
        fixedWidth=fixedWidth,
        fixedHeight=style.fontSize * _SingleLineEditBoxVerticalScale,
        maxWidth=maxWidth,
        multiline=False)

def _createMultiLineEditBox(
        name: str,
        style: ParagraphStyle,
        value: str = '',
        fixedWidth: typing.Optional[float] = None,
        fixedHeight: typing.Optional[float] = None,
        maxWidth: typing.Optional[float] = None,
        maxHeight: typing.Optional[float] = None
        ) -> pdf.TextFormField:
    return _createEditBox(
        name=name,
        style=style,
        value=value,
        fixedWidth=fixedWidth,
        fixedHeight=fixedHeight,
        maxWidth=maxWidth,
        maxHeight=maxHeight,
        multiline=True)

def _createAttributeParagraph(
        attribute: gunsmith.AttributeInterface,
        style: ParagraphStyle,
        includeName: bool = False,
        alwaysSignNumbers: bool = False,
        useDashForNoValue: bool = False
        ) -> Paragraph:
    if not attribute:
        return _createParagraph(text='-', style=style)

    text = _formatAttributeString(
        attribute=attribute,
        includeName=includeName,
        alwaysSignNumbers=alwaysSignNumbers,
        useDashForNoValue=useDashForNoValue)
    return _createParagraph(text=text, style=style)

def _createVerticalSpacer(
        spacing: float
        ) -> Spacer:
    return Spacer(width=0, height=spacing)

def _createTable(
        data: typing.List[typing.List[typing.Union[str, Flowable]]],
        spans: typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]] = None,
        colWidths: typing.Optional[typing.List[typing.Optional[typing.Union[str, int]]]] = None,
        copyHeaderOnSplit: bool = True
        ) -> Table:
    styles = [
        ('INNERGRID', (0, 0), (-1, -1), _TableLineWidth, _TableGridColour),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]
    if spans:
        for ul, br in spans:
            styles.append(('SPAN', ul, br))

    cellStyles = []
    for row in range(len(data)):
        rowStyles = []
        for column in range(len(data[row])):
            style = CellStyle(repr((row, column)))
            style.topPadding = _CellVerticalPadding
            style.bottomPadding = _CellVerticalPadding
            style.leftPadding = _CellHorizontalPadding
            style.rightPadding = _CellHorizontalPadding
            rowStyles.append(style)
        cellStyles.append(rowStyles)

    return Table(
        data=data,
        repeatRows=1 if copyHeaderOnSplit else 0,
        style=TableStyle(styles),
        colWidths=colWidths,
        cellStyles=cellStyles)

def _createAttributeParagraphs(
        weapon: gunsmith.Weapon,
        sequence: str,
        attributeIds: typing.Iterable[gunsmith.AttributeId],
        alwaysSignNumbers: bool = False,
        useDashForNoValue: bool = False
        ) -> typing.Tuple[typing.List[Paragraph], typing.List[Paragraph]]:
    keyParagraphs: typing.List[typing.Tuple[Paragraph, Paragraph]] = []
    valueParagraphs: typing.List[typing.Tuple[Paragraph, Paragraph]] = []

    for attributeId in attributeIds:
        attribute = weapon.attribute(sequence=sequence, attributeId=attributeId)
        if not attribute:
            continue

        nameText = _AttributeHeaderOverrideMap.get(attributeId)
        if not nameText:
            nameText = attribute.name()

        keyParagraphs.append(_createParagraph(
            text=nameText,
            style=_TableHeaderCenterStyle))
        valueParagraphs.append(_createAttributeParagraph(
            attribute=attribute,
            style=_TableDataNormalStyle,
            alwaysSignNumbers=alwaysSignNumbers,
            useDashForNoValue=useDashForNoValue))

    return (keyParagraphs, valueParagraphs)

def _createTraitsParagraph(
        weapon: gunsmith.Weapon,
        sequence: str
        ) -> Paragraph:
    traitsText = ''
    for attributeId in gunsmith.TraitAttributeIds:
        attribute = weapon.attribute(sequence=sequence, attributeId=attributeId)
        if not attribute:
            continue

        if len(traitsText) > 0:
            traitsText += '\n'

        traitsText += _formatAttributeString(
            attribute=attribute,
            includeName=True,
            alwaysSignNumbers=False,
            bracketValue=True)

    if not traitsText:
        traitsText = '-'

    return _createParagraph(
        text=traitsText,
        style=_TableDataNormalStyle)

def _createNotesList(
        notes: typing.Iterable[str]
        ) -> typing.Optional[Flowable]:
    if not notes:
        return None

    listItems = []
    for note in notes:
        listItems.append(_createParagraph(
            text=note,
            style=_ListItemStyle))

    return ListFlowable(
        listItems,
        bulletType='bullet',
        start='',
        bulletFontSize=0,
        leftIndent=0
        )

def _createCurrentDetails(
        weapon: gunsmith.Weapon,
        ) -> Table:
    sequences = weapon.sequences()

    compactLayout = len(sequences) <= _CompactLayoutMaxSequences

    columnHeaders = ['Attribute']
    expandFlags = [False]
    if len(sequences) == 1:
        columnHeaders.append('Value')
        expandFlags.append(not compactLayout)
    else:
        columnHeaders.append('Primary')
        expandFlags.append(not compactLayout)
        if len(sequences) == 2:
            columnHeaders.append('Secondary')
            expandFlags.append(not compactLayout)
        else:
            for row in range(len(sequences) - 1):
                columnHeaders.append(f'Secondary {row + 1}')
                expandFlags.append(not compactLayout)
    if compactLayout:
        columnHeaders.append('Notes')
        expandFlags.append(True)

    rows = ['Weapon Weight', 'Loaded Ammo', 'Range', 'Damage', 'Capacity', 'Remaining Shots']
    if _CustomCurrentDetailRows:
        rows.extend([None] * _CustomCurrentDetailRows)

    headerRow = []
    for text in columnHeaders:
        headerRow.append(_createParagraph(text=text, style=_TableHeaderNormalStyle))
    tableData: typing.List[typing.List[Paragraph]] = [headerRow]
    tableSpans = []

    columnWidth = _CompactLayoutColumnWidth if compactLayout else None
    for row, rowName in enumerate(rows):
        rowData = []
        if rowName:
            rowData.append(_createParagraph(
                text=rowName,
                style=_TableDataNormalStyle))
        else:
            rowData.append(_createSingleLineEditBox(
                name=f'key_{row}',
                style=_TableDataNormalStyle,
                fixedWidth=columnWidth))

        for column in range(len(sequences)):
            rowData.append(_createSingleLineEditBox(
                name=f'value_{row}_{column}',
                style=_TableDataNormalStyle,
                fixedWidth=columnWidth))

        if compactLayout:
            if row == 0:
                rowHeight = (_TableDataNormalStyle.fontSize * _SingleLineEditBoxVerticalScale) + \
                    (_CellVerticalPadding * 2)
                spanHeight = (rowHeight * len(rows)) - (_CellVerticalPadding * 2)

                rowData.append(_createMultiLineEditBox(
                    name=f'notes',
                    style=_TableDataNormalStyle,
                    fixedHeight=spanHeight))
            else:
                rowData.append(_createParagraph(
                    text='',
                    style=_TableDataNormalStyle))

        tableData.append(rowData)

    colWidths = None
    if not compactLayout:
        rowData = []
        for index in range(len(headerRow)):
            if index == 0:
                rowData.append(_createMultiLineEditBox(
                    name=f'notes',
                    style=_TableDataNormalStyle,
                    fixedHeight=_StandardLayoutNotesHeight))
            else:
                rowData.append(_createParagraph(
                    text='',
                    style=_TableDataNormalStyle))
        tableData.append(rowData)
        tableSpans.append(((0, len(tableData) - 1), (len(headerRow) - 1, len(tableData) - 1)))
    else:
        tableSpans.append(((len(headerRow) - 1, 1), (len(headerRow) - 1, len(tableData) - 1)))
        colWidths = [None] * (len(headerRow) - 1) + ['*']

    return _createTable(
        data=tableData,
        spans=tableSpans,
        colWidths=colWidths) # Expand last column

def _createManifestTable(
        weapon: gunsmith.Weapon
        ) -> Table:
    manifest = weapon.manifest()
    tableData = [[
        _createParagraph(text='Component', style=_TableHeaderNormalStyle),
        _createParagraph(text='Cost', style=_TableHeaderNormalStyle),
        _createParagraph(text='Weight', style=_TableHeaderNormalStyle),
        _createParagraph(text='Other Factors', style=_TableHeaderNormalStyle),
    ]]
    for section in manifest.sections():
        entries = section.entries()
        if not entries:
            continue

        for entry in entries:
            tableData.append(_createManifestEntryRow(entry=entry))

        tableData.append(_createManifestSectionTotalRow(section=section))

    tableData.append(_createManifestTotalRow(manifest=manifest))

    return _createTable(
        data=tableData,
        colWidths=['*', None, None, '*'])

def _createManifestEntryRow(
        entry: gunsmith.ManifestEntry
        ) -> typing.List[typing.Union[str, Flowable]]:
    componentElement = _createParagraph(
        text=entry.component(),
        style=_TableDataNormalStyle)

    cost = entry.cost()
    if cost:
        costString = cost.displayString(
            decimalPlaces=gunsmith.ConstructionDecimalPlaces)
        if isinstance(cost, gunsmith.ConstantModifier):
            costString = costString.strip('+')
            costString = 'Cr' + costString
    else:
        costString = '-'
    costElement = _createParagraph(
        text=costString,
        style=_TableDataNormalStyle)

    weight = entry.weight()
    if weight:
        weightString = weight.displayString(
            decimalPlaces=gunsmith.ConstructionDecimalPlaces)
        if isinstance(weight, gunsmith.ConstantModifier):
            weightString = weightString.strip('+')
            weightString += 'kg'
    else:
        weightString = '-'
    weightElement = _createParagraph(
        text=weightString,
        style=_TableDataNormalStyle)

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
    factorsElement = _createParagraph(
        text=factorsString,
        style=_TableDataNormalStyle)

    return [
        componentElement,
        costElement,
        weightElement,
        factorsElement
    ]

def _createManifestSectionTotalRow(
        section: gunsmith.ManifestSection
        ) -> typing.List[typing.Union[str, Flowable]]:
    componentElement = _createParagraph(
        text=f'{section.name()} Total',
        style=_TableDataBoldStyle)

    cost = section.totalCost()
    costElement = _createParagraph(
        text=f'Cr{common.formatNumber(number=cost.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}',
        style=_TableDataBoldStyle)

    weight = section.totalWeight()
    weightElement = _createParagraph(
        text=f'{common.formatNumber(number=weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}kg',
        style=_TableDataBoldStyle)

    factorsElement = _createParagraph(
        text='-',
        style=_TableDataBoldStyle)

    return [
        componentElement,
        costElement,
        weightElement,
        factorsElement
    ]

def _createManifestTotalRow(
        manifest: gunsmith.Manifest
        ) -> typing.List[typing.Union[str, Flowable]]:
    componentElement = _createParagraph(
        text='Total',
        style=_TableDataBoldStyle)

    cost = manifest.totalCost()
    costElement = _createParagraph(
        text=f'Cr{common.formatNumber(number=cost.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}',
        style=_TableDataBoldStyle)

    weight = manifest.totalWeight()
    weightElement = _createParagraph(
        text=f'{common.formatNumber(number=weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}kg',
        style=_TableDataBoldStyle)

    factorsElement = _createParagraph(
        text='-',
        style=_TableDataBoldStyle)

    return [
        componentElement,
        costElement,
        weightElement,
        factorsElement
    ]

def _createWeaponTable(
        weapon: gunsmith.Weapon,
        sequence: str
        ) -> Table:
    if weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.ConventionalWeapon:
        weaponAttributeIds = gunsmith.ConventionalWeaponAttributeIds
        weightHeader = 'Loaded\nWeight'
    elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.GrenadeLauncherWeapon:
        weaponAttributeIds = gunsmith.LauncherWeaponAttributeIds
        weightHeader = 'Unloaded\nWeight'
    elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.PowerPackWeapon:
        weaponAttributeIds = gunsmith.PowerPackEnergyWeaponAttributeIds
        weightHeader = 'Unloaded\nWeight'
    elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.EnergyCartridgeWeapon:
        weaponAttributeIds = gunsmith.CartridgeEnergyWeaponAttributeIds
        weightHeader = 'Unloaded\nWeight'
    elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.ProjectorWeapon:
        weaponAttributeIds = gunsmith.ProjectorWeaponAttributeIds
        weightHeader = 'Loaded\nWeight'
    else:
        raise TypeError(f'Unable to export unknown weapon type {type(weapon)}')

    weaponHeaders, weaponValues = _createAttributeParagraphs(
        weapon=weapon,
        sequence=sequence,
        attributeIds=weaponAttributeIds)

    reliabilityHeaders, reliabilityValues = _createAttributeParagraphs(
        weapon=weapon,
        sequence=sequence,
        attributeIds=gunsmith.ReliabilityAttributeIds)

    # TL and weight come from the primary weapon. Note that the weight header text
    # is still based on the secondary weapon type as that still determines if the
    # primary weapon weight (which includes both weapons) includes the weight for
    # the secondary weapon
    weaponHeaders = [
        _createParagraph(
            text='TL',
            style=_TableHeaderCenterStyle),
        _createParagraph(
            text=weightHeader,
            style=_TableHeaderCenterStyle)
    ] + weaponHeaders
    weaponValues = [
        _createParagraph(
            text=str(weapon.techLevel()),
            style=_TableDataNormalStyle),
        _createParagraph(
            text=common.formatNumber(
                number=weapon.totalWeight().value(),
                decimalPlaces=gunsmith.ConstructionDecimalPlaces),
            style=_TableDataNormalStyle)
    ] + weaponValues

    tableColumns = max(len(weaponHeaders), len(reliabilityHeaders))
    while len(weaponHeaders) < tableColumns:
        weaponHeaders.append('')
        weaponValues.append('')
    while len(reliabilityHeaders) < tableColumns:
        reliabilityHeaders.append('')
        reliabilityValues.append('')

    weaponHeaders.append(_createParagraph(
        text='Traits',
        style=_TableHeaderNormalStyle))
    weaponValues.append(_createTraitsParagraph(
        weapon=weapon,
        sequence=sequence))
    if reliabilityHeaders:
        reliabilityHeaders.append('')
        reliabilityValues.append('')
        tableColumns += 1
    tableData = [
        weaponHeaders,
        weaponValues,
    ]
    if reliabilityHeaders:
        tableData.append(reliabilityHeaders)
        tableData.append(reliabilityValues)

    return _createTable(
        data=tableData,
        spans=[((tableColumns - 1, 1), (tableColumns - 1, 3))] if reliabilityHeaders else None,
        colWidths=[None] * (tableColumns - 1) + ['*'], # Expand last column
        copyHeaderOnSplit=False)

def _createNotesTable(
        weapon: gunsmith.Weapon,
        sequence: str
        ) -> typing.Optional[Table]:
    tableData = [[
        _createParagraph(
            text='Rule',
            style=_TableHeaderNormalStyle),
        _createParagraph(
            text='Notes',
            style=_TableHeaderNormalStyle),
        ]]

    for step in weapon.steps(sequence=sequence):
        notes = step.notes()
        if not notes:
            continue

        tableData.append([
            _createParagraph(
                text=f'{step.type()}: {step.name()}',
                style=_TableDataNormalStyle),
            _createNotesList(notes=notes)
        ])

    if len(tableData) <= 1:
        return None # No notes added (only header) so no point creating a table

    return _createTable(
        data=tableData,
        colWidths=['*', '*']) # Don't expand any columns as long notes cause the left column to be compressed

def _createAccessoriesTable(
        weapon: gunsmith.Weapon,
        sequence: str,
        ) -> typing.Optional[Table]:
    # Find all components derived from AccessoryInterface in order to find barrel and weapon
    # accessories
    accessories = weapon.findComponents(
        sequence=sequence,
        componentType=gunsmith.AccessoryInterface)

    # Detach all accessories, they'll be re-attached one by one as the table is generated.
    weapon.setAccessorAttachment(sequence=sequence, attach=False, regenerate=True)

    # Take note of the base weight so we can calculate the weight of the accessory
    baseWeight = weapon.totalWeight()

    # Take note of the base notes so we can just list the ones that apply to the accessory
    baseNotes = _collectConstructionNotes(weapon=weapon, sequence=sequence)

    headerRow = [
        _createParagraph(text='Type', style=_TableHeaderNormalStyle),
        _createParagraph(text='Range', style=_TableHeaderCenterStyle),
        _createParagraph(text='Damage', style=_TableHeaderCenterStyle),
        _createParagraph(text='Weapon\nWeight', style=_TableHeaderCenterStyle),
        _createParagraph(text='Ammo\nCapacity', style=_TableHeaderCenterStyle),
        _createParagraph(text='Accessory\nWeight', style=_TableHeaderCenterStyle),
        _createParagraph(text='Quickdraw', style=_TableHeaderCenterStyle),
        _createParagraph(text='Malfunction\nTable DM', style=_TableHeaderCenterStyle),
        _createParagraph(text='Traits', style=_TableHeaderNormalStyle)
    ]
    tableData = [headerRow]
    tableSpans = []

    for accessory in accessories:
        assert(isinstance(accessory, gunsmith.AccessoryInterface))
        if not accessory.isDetachable():
            continue # Not interested in fixed accessories

        accessory.setAttached(attached=True)
        weapon.regenerate()

        accessoryWeight = common.Calculator.subtract(
            lhs=weapon.totalWeight(),
            rhs=baseWeight,
            name=f'Calculated Weight For {accessory.instanceString()}')

        # Generate the list of notes that were added by the accessory (this includes finalisation notes)
        accessoryNotes = _diffConstructionNotes(
            weapon=weapon,
            sequence=sequence,
            originalNotes=baseNotes)

        rows, spans = _createAccessoryRows(
            weapon=weapon,
            sequence=sequence,
            accessory=accessory,
            weight=accessoryWeight,
            accessoryNotes=accessoryNotes,
            baseRowIndex=len(tableData))
        assert(not any(len(row) != len(headerRow) for row in rows))
        tableData.extend(rows)
        if spans:
            tableSpans.extend(spans)

        # Detach the accessory ready to attach the next one. No need to regenerate as that will be
        # done after the next one is attached
        accessory.setAttached(attached=False)

    # Regenerate the weapon one more time to update it after the last accessory was detached
    weapon.regenerate()

    if len(tableData) <= 1:
        return None # No notes added (only header) so no point creating a table

    return _createTable(
        data=tableData,
        spans=tableSpans,
        colWidths=['*'] + ([None] * (len(tableData[0]) - 2)) + ['*']) # Expand first and last columns

def _createAccessoryRows(
        weapon: gunsmith.Weapon,
        sequence: str,
        accessory: gunsmith.AccessoryInterface,
        weight: common.ScalarCalculation,
        accessoryNotes: typing.Mapping[str, typing.Collection[str]],
        baseRowIndex: int
        ) -> typing.Tuple[
        typing.List[typing.List[typing.Union[Flowable, typing.List[Flowable]]]], # List of rows
        typing.Optional[typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]]] # Optional list of spans
        ]:
    typeElement = _createParagraph(
        text=accessory.instanceString(),
        style=_TableDataNormalStyle)

    rangeElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Range),
        style=_TableDataNormalStyle)

    damageElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage),
        style=_TableDataNormalStyle)

    weaponWeight = weapon.combatWeight()
    weaponWeight = weaponWeight.value()
    weaponWeightElement = _createParagraph(
        text=common.formatNumber(number=weaponWeight, decimalPlaces=gunsmith.ConstructionDecimalPlaces),
        style=_TableDataNormalStyle)

    capacityElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCapacity),
        style=_TableDataNormalStyle)

    accessoryWeightString = \
        '-' \
        if math.isclose(weight.value(), 0.0) else \
        common.formatNumber(number=weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)
    accessoryWeightElement = _createParagraph(
        text=accessoryWeightString,
        style=_TableDataNormalStyle)

    quickdrawElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Quickdraw),
        style=_TableDataNormalStyle)

    malfunctionElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.MalfunctionDM),
        style=_TableDataNormalStyle)

    traitsElement = _createTraitsParagraph(
        weapon=weapon,
        sequence=sequence)

    mainRow = [
        typeElement,
        rangeElement,
        damageElement,
        weaponWeightElement,
        capacityElement,
        accessoryWeightElement,
        quickdrawElement,
        malfunctionElement,
        traitsElement]
    rows = [mainRow]
    if not accessoryNotes:
        return rows, None

    notesList = []
    for rule, notes in accessoryNotes.items():
        for note in notes:
            notesList.append(_createParagraph(
                text=f'{rule} - {note}',
                style=_ListItemStyle))
    notesRow = [_createParagraph(text='', style=_TableDataNormalStyle), notesList] + \
        ([_createParagraph(text='', style=_TableDataNormalStyle)] * (len(mainRow) - 2))
    rows.append(notesRow)

    spans = [
        ((0, baseRowIndex), (0, baseRowIndex + 1)),
        ((1, baseRowIndex + 1), (len(mainRow) - 1, baseRowIndex + 1))
    ]

    return rows, spans

def _createAmmoTable(
        weapon: gunsmith.Weapon,
        sequence: str,
        usePurchasedMagazines: bool,
        usePurchasedAmmo: bool
        ) -> typing.Optional[Table]:
    # Detach all removable accessories, their modifiers & notes shouldn't be included
    weapon.setAccessorAttachment(attach=False)

    # Take a note of the weapon notes when unloaded. This will be used when generating the
    # lists of per weapon notes
    baseNotes = _collectConstructionNotes(weapon=weapon, sequence=sequence)

    # Generate the list of magazines to be loaded and the stage to load them. This assumes
    # that there is only one magazine loading stage
    magazines = None
    magazineLoadingStage = None
    removableFeeds = weapon.hasComponent(
        componentType=gunsmith.RemovableMagazineFeed,
        sequence=sequence)
    if removableFeeds:
        stages = weapon.stages(
            sequence=sequence,
            componentType=gunsmith.MagazineLoadedInterface)
        for stage in stages:
            magazineLoadingStage = stage
            break
        # If a weapon has a removable magazine feed it should always have a _single_ stage for
        # loading a magazine
        assert(magazineLoadingStage)

        magazines: typing.List[gunsmith.MagazineLoadedInterface] = []
        if usePurchasedMagazines:
            # Create loaded magazines for each of the purchased magazines
            purchasedMagazines = weapon.findComponents(
                sequence=sequence,
                componentType=gunsmith.MagazineQuantityInterface)
            for purchasedMagazine in purchasedMagazines:
                assert(isinstance(purchasedMagazine, gunsmith.MagazineQuantityInterface))
                magazines.append(purchasedMagazine.createLoadedMagazine())
        elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.EnergyCartridgeWeapon:
            # Treat cartridge energy weapons as a special case :(. The type of cartridge is
            # determined by the type of magazine so all compatible magazine types need to be tried
            # to generate an ammo entry for each cartridge type
            magazines.extend(weapon.findCompatibleComponents(
                stage=magazineLoadingStage))
        else:
            # It's a (non energy cartridge) removable magazine weapon. Add the first magazine that's
            # listed as compatible with the loading stage. This works on the assumption that this will
            # be the standard sized magazine that are included with the weapon
            compatibleMagazines = weapon.findCompatibleComponents(
                stage=magazineLoadingStage)
            if compatibleMagazines:
                magazines.append(compatibleMagazines[0])

        if not magazines:
            return None
    else:
        magazines = [None]

    ammoLoadingStages = weapon.stages(
        sequence=sequence,
        phase=gunsmith.ConstructionPhase.Loading)
    ammoLoadingStages = list(filter(lambda stage: issubclass(stage.baseType(), gunsmith.AmmoLoadedInterface), ammoLoadingStages))
    # All weapons should have at least one ammo loading stage, power pack energy weapons can have two
    assert(ammoLoadingStages)

    combinations: typing.List[typing.Tuple[
        gunsmith.ConstructionStage,
        gunsmith.AmmoLoadedInterface,
        typing.Optional[gunsmith.MagazineLoadedInterface]]] = []

    for magazine in magazines:
        # Load the magazine if there is one, fixed magazine weapons won't have one
        if magazine:
            weapon.addComponent(
                stage=magazineLoadingStage,
                component=magazine,
                regenerate=True)

        if usePurchasedAmmo:
            ammoQuantities = weapon.findComponents(
                sequence=sequence,
                componentType=gunsmith.AmmoQuantityInterface)
            for quantity in ammoQuantities:
                assert(isinstance(quantity, gunsmith.AmmoQuantityInterface))
                ammo = quantity.createLoadedAmmo()

                for stage in ammoLoadingStages:
                    # Load (and unload) the ammo to check for compatibility
                    try:
                        weapon.addComponent(
                            stage=stage,
                            component=ammo,
                            regenerate=False) # No need to regenerate to check for compatibility
                    except gunsmith.CompatibilityException:
                        continue

                    weapon.removeComponent(
                        stage=stage,
                        component=ammo,
                        regenerate=False) # Didn't regenerate when component was added so no need now
                    combinations.append((stage, ammo, magazine))
        elif weapon.weaponType(sequence=sequence) == gunsmith.WeaponType.PowerPackWeapon:
            # Treat power pack energy weapons as a special case :(. The ammo capacity of a power pack
            # energy weapon is dependant on the weight and type of the power pack being used. If not using
            # purchased ammo (i.e. purchased power packs) The best thing I can see to do is to generate an
            # external power pack of default weight for each of the types
            ammoLoadingStages = weapon.stages(
                sequence=sequence,
                componentType=gunsmith.ExternalPowerPackLoadedInterface)
            for stage in ammoLoadingStages:
                compatibleAmmo = weapon.findCompatibleComponents(stage=stage)
                for ammo in compatibleAmmo:
                    combinations.append((stage, ammo, None))
        else:
            # Generate entries for the ammo types compatible with each loading stage
            for stage in ammoLoadingStages:
                compatibleAmmo = weapon.findCompatibleComponents(stage=stage)
                for ammo in compatibleAmmo:
                    combinations.append((stage, ammo, magazine))

    if not combinations:
        return # Nothing to do

    headerRow = [
        _createParagraph(text='Type', style=_TableHeaderNormalStyle),
        _createParagraph(text='Range', style=_TableHeaderCenterStyle),
        _createParagraph(text='Damage', style=_TableHeaderCenterStyle),
        _createParagraph(text='Loaded\nWeapon\nWeight', style=_TableHeaderCenterStyle),
        _createParagraph(text='Ammo\nCapacity', style=_TableHeaderCenterStyle),
        _createParagraph(text='Loaded\nMagazine\nCost', style=_TableHeaderCenterStyle),
        _createParagraph(text='Loaded\nMagazine\nWeight', style=_TableHeaderCenterStyle),
        _createParagraph(text='Quickdraw', style=_TableHeaderCenterStyle),
        _createParagraph(text='Malfunction\nTable DM', style=_TableHeaderCenterStyle),
        _createParagraph(text='Traits', style=_TableHeaderNormalStyle)
    ]
    tableData = [headerRow]
    tableSpans = []

    optionIDs = [
        'Smart', # Conventional
        'Stealth', # Conventional
        'RAM', # Launchers
        'AdvancedFusing' # Launchers
    ]
    for stage, ammo, magazine in combinations:
        # Load the magazine if there is one, fixed magazine weapons won't have one
        if magazine:
            weapon.addComponent(
                stage=magazineLoadingStage,
                component=magazine,
                regenerate=False)
        weapon.addComponent(
            stage=stage,
            component=ammo,
            regenerate=False)

        # Regenerate weapon after loading it
        weapon.regenerate()

        # Generate the list of notes that were added by the ammo
        ammoNotes = _diffConstructionNotes(
            weapon=weapon,
            sequence=sequence,
            originalNotes=baseNotes)

        # Generate ammo table rows
        rows, spans = _createAmmoRows(
            weapon=weapon,
            sequence=sequence,
            ammo=ammo,
            magazine=magazine,
            ammoNotes=ammoNotes,
            baseRowIndex=len(tableData))
        tableData.extend(rows)
        if spans:
            tableSpans.extend(spans)

        if not usePurchasedAmmo:
            options = ammo.options()
            flagOptions = [option for option in options if option.id() in optionIDs]
            if flagOptions:
                # Add an entry for each option toggled to the non-default value
                for option in flagOptions:
                    assert(isinstance(option, gunsmith.BooleanComponentOption)) # Currently only booleans are supported
                    option.setValue(not option.value())
                    weapon.regenerate()
                    ammoNotes = _diffConstructionNotes(
                        weapon=weapon,
                        sequence=sequence,
                        originalNotes=baseNotes)
                    rows, spans = _createAmmoRows(
                        weapon=weapon,
                        sequence=sequence,
                        ammo=ammo,
                        magazine=magazine,
                        ammoNotes=ammoNotes,
                        baseRowIndex=len(tableData))
                    tableData.extend(rows)
                    if spans:
                        tableSpans.extend(spans)

                    # Put the option back to its default state
                    option.setValue(not option.value())
                    weapon.regenerate()

        # Remove the ammo/magazine and regenerate the weapon ready for the next combination.
        weapon.removeComponent(
            stage=stage,
            component=ammo,
            regenerate=False)
        if magazine:
            weapon.removeComponent(
                stage=magazineLoadingStage,
                component=magazine,
                regenerate=False)
        weapon.regenerate()

    return _createTable(
        data=tableData,
        spans=tableSpans,
        colWidths=['*'] + ([None] * (len(tableData[0]) - 2)) + ['*']) # Expand first and last columns

def _createAmmoRows(
        weapon: gunsmith.Weapon,
        sequence: str,
        ammo: gunsmith.AmmoLoadedInterface,
        magazine: typing.Optional[gunsmith.MagazineLoadedInterface],
        ammoNotes: typing.Mapping[str, typing.Collection[str]],
        baseRowIndex: int
        ) -> typing.Tuple[
        typing.List[typing.List[typing.Union[Flowable, typing.List[Flowable]]]], # List of rows
        typing.Optional[typing.List[typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int]]]] # Optional list of spans
        ]:
    if isinstance(ammo, gunsmith.ConventionalAmmoLoaded) or \
            isinstance(ammo, gunsmith.LauncherAmmoLoaded):
        typeText = 'Ammo: ' + ammo.instanceString()
    elif isinstance(ammo, gunsmith.InternalPowerPackLoaded):
        typeText = 'Internal Power Pack: ' + ammo.instanceString()
    elif isinstance(ammo, gunsmith.ExternalPowerPackLoaded):
        typeText = 'External Power Pack: ' + ammo.instanceString()
    elif isinstance(ammo, gunsmith.EnergyCartridgeLoaded):
        typeText = 'Cartridge: ' + ammo.instanceString()
    elif isinstance(ammo, gunsmith.ProjectorFuelLoaded):
        typeText = 'Fuel: ' + ammo.instanceString()
    else:
        assert(False)

    if magazine:
        typeText = f'Magazine: {magazine.instanceString()}\n{typeText}'
    typeElement = _createParagraph(
        text=typeText,
        style=_TableDataNormalStyle)

    rangeElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Range),
        style=_TableDataNormalStyle)

    damageElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Damage),
        style=_TableDataNormalStyle)

    weaponWeight = weapon.combatWeight()
    weaponWeight = weaponWeight.value()
    weaponWeightElement = _createParagraph(
        text=common.formatNumber(number=weaponWeight, decimalPlaces=gunsmith.ConstructionDecimalPlaces),
        style=_TableDataNormalStyle)

    capacityElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.AmmoCapacity),
        style=_TableDataNormalStyle)

    magazineCost = weapon.phaseCost(phase=gunsmith.ConstructionPhase.Loading)
    magazineCost = magazineCost.value()
    magazineCostString = \
        '-' \
        if math.isclose(magazineCost, 0.0) else \
        common.formatNumber(number=magazineCost, decimalPlaces=gunsmith.ConstructionDecimalPlaces)
    magazineCostElement = _createParagraph(
        text=magazineCostString,
        style=_TableDataNormalStyle)

    magazineWeight = weapon.phaseWeight(phase=gunsmith.ConstructionPhase.Loading)
    magazineWeight = magazineWeight.value()
    magazineWeightString = \
        '-' \
        if math.isclose(magazineWeight, 0.0) else \
        common.formatNumber(number=magazineWeight, decimalPlaces=gunsmith.ConstructionDecimalPlaces)
    magazineWeightElement = _createParagraph(
        text=magazineWeightString,
        style=_TableDataNormalStyle)

    quickdrawElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.Quickdraw),
        style=_TableDataNormalStyle)

    malfunctionElement = _createAttributeParagraph(
        attribute=weapon.attribute(
            sequence=sequence,
            attributeId=gunsmith.AttributeId.MalfunctionDM),
        style=_TableDataNormalStyle)

    traitsElement = _createTraitsParagraph(
        weapon=weapon,
        sequence=sequence)

    mainRow = [
        typeElement,
        rangeElement,
        damageElement,
        weaponWeightElement,
        capacityElement,
        magazineCostElement,
        magazineWeightElement,
        quickdrawElement,
        malfunctionElement,
        traitsElement]
    rows = [mainRow]
    if not ammoNotes:
        return rows, None

    notesList = []
    for rule, notes in ammoNotes.items():
        for note in notes:
            notesList.append(_createParagraph(
                text=f'{rule} - {note}',
                style=_ListItemStyle))
    notesRow = [_createParagraph(text='', style=_TableDataNormalStyle), notesList] + \
        ([_createParagraph(text='', style=_TableDataNormalStyle)] * (len(mainRow) - 2))
    rows.append(notesRow)

    spans = [
        ((0, baseRowIndex), (0, baseRowIndex + 1)),
        ((1, baseRowIndex + 1), (len(mainRow) - 1, baseRowIndex + 1))
    ]

    return rows, spans
