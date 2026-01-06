import app
import astronomer
import csv
import enum
import gui
import io
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexTableTabBar(gui.TabBarEx):
    class DisplayMode(enum.Enum):
        AllColumns = 0
        SystemColumns = 1
        UWPColumns = 2
        EconomicsColumns = 3
        CultureColumns = 4
        RefuellingColumns = 5

    _StateVersion = 'HexTableTabBar_v1'

    def __init__(self) -> None:
        tabs = [
            (HexTableTabBar.DisplayMode.AllColumns, 'All'),
            (HexTableTabBar.DisplayMode.SystemColumns, 'System'),
            (HexTableTabBar.DisplayMode.UWPColumns, 'UWP'),
            (HexTableTabBar.DisplayMode.EconomicsColumns, 'Economics'),
            (HexTableTabBar.DisplayMode.CultureColumns, 'Culture'),
            (HexTableTabBar.DisplayMode.RefuellingColumns, 'Refuelling'),
        ]
        super().__init__()
        for index, (mode, text) in enumerate(tabs):
            self.addTab(text)
            self.setTabData(index, mode)

    def currentDisplayMode(self) -> DisplayMode:
        return self.tabData(self.currentIndex())

    def setCurrentDisplayMode(
            self,
            displayMode: DisplayMode
            ) -> None:
        for index in range(self.count()):
            if displayMode == self.tabData(index):
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        displayMode = self.currentDisplayMode()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexTableTabBar._StateVersion)
        stream.writeQString(displayMode.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexTableTabBar._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexTableTabBar state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in self.DisplayMode.__members__:
            logging.warning(f'Failed to restore HexTableTabBar state (Unknown DisplayMode "{name}")')
            return False
        self.setCurrentDisplayMode(self.DisplayMode.__members__[name])
        return True

class HexTable(gui.FrozenColumnListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Sector = 'Sector'
        Subsector = 'Subsector'
        Zone = 'Zone'
        Allegiance = 'Allegiance'
        PopulationCount = 'Population\n(Count)'
        StarPort = 'Star Port\n(ehex)'
        TechLevel = 'Tech Level\n(ehex)'
        LawLevel = 'Law Level\n(ehex)'
        Population = 'Population\n(ehex)'
        Government = 'Government\n(ehex)'
        WorldSize = 'World Size\n(ehex)'
        Atmosphere = 'Atmosphere\n(ehex)'
        Hydrographics = 'Hydrographics\n(ehex)'
        Resources = 'Resources\n(ehex)'
        Labour = 'Labour\n(ehex)'
        Infrastructure = 'Infrastructure\n(ehex)'
        Efficiency = 'Efficiency\n(ehex)'
        Heterogeneity = 'Heterogeneity\n(ehex)'
        Acceptance = 'Acceptance\n(ehex)'
        Strangeness = 'Strangeness\n(ehex)'
        Symbols = 'Symbols\n(ehex)'
        Nobilities = 'Nobilities'
        Sophont = 'Sophont'
        TradeCodes = 'Trade Codes'
        PopulationMultiplier = 'Population\nMultiplier'
        PlanetoidBeltCount = 'Planetoid Belts\n(Count)'
        GasGiantCount = 'Gas Giants\n(Count)'
        StarCount = 'Stars\n(Count)'
        SystemWorldCount = 'System Worlds\n(Count)'
        StarPortRefuelling = 'Star Ports\nRefuelling'
        GasGiantRefuelling = 'Gas Giant\nRefuelling'
        WaterRefuelling = 'Water\nRefuelling'
        FuelCache = 'Fuel\nCache'
        Anomaly = 'Anomaly'
        Bases = 'Bases'
        ScoutBase = 'Scout Base'
        MilitaryBase = 'Military Base'
        OwnerWorlds = 'Owners\n(Count)'
        ColonyWorlds = 'Colonies\n(Count)'
        Remarks = 'Remarks'

    AllColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.Zone,
        ColumnType.Allegiance,
        ColumnType.PopulationCount,
        ColumnType.StarPort,
        ColumnType.TechLevel,
        ColumnType.LawLevel,
        ColumnType.Population,
        ColumnType.Government,
        ColumnType.WorldSize,
        ColumnType.Atmosphere,
        ColumnType.Hydrographics,
        ColumnType.Resources,
        ColumnType.Labour,
        ColumnType.Infrastructure,
        ColumnType.Efficiency,
        ColumnType.Heterogeneity,
        ColumnType.Acceptance,
        ColumnType.Strangeness,
        ColumnType.Symbols,
        ColumnType.Nobilities,
        ColumnType.Sophont,
        ColumnType.TradeCodes,
        ColumnType.PopulationMultiplier,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount,
        ColumnType.StarCount,
        ColumnType.SystemWorldCount,
        ColumnType.StarPortRefuelling,
        ColumnType.GasGiantRefuelling,
        ColumnType.WaterRefuelling,
        ColumnType.FuelCache,
        ColumnType.Bases,
        ColumnType.ScoutBase,
        ColumnType.MilitaryBase,
        ColumnType.OwnerWorlds,
        ColumnType.ColonyWorlds,
        ColumnType.Anomaly,
        ColumnType.Remarks
    ]

    SystemColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.Zone,
        ColumnType.Allegiance,
        ColumnType.PopulationCount,
        ColumnType.Nobilities,
        ColumnType.Sophont,
        ColumnType.TradeCodes,
        ColumnType.StarCount,
        ColumnType.SystemWorldCount,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount,
        ColumnType.Bases,
        ColumnType.ScoutBase,
        ColumnType.MilitaryBase,
        ColumnType.OwnerWorlds,
        ColumnType.ColonyWorlds,
        ColumnType.Anomaly,
    ]

    UWPColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.StarPort,
        ColumnType.WorldSize,
        ColumnType.Atmosphere,
        ColumnType.Hydrographics,
        ColumnType.Population,
        ColumnType.Government,
        ColumnType.LawLevel,
        ColumnType.TechLevel
    ]

    EconomicsColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.Resources,
        ColumnType.Labour,
        ColumnType.Infrastructure,
        ColumnType.Efficiency
    ]

    CultureColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.Heterogeneity,
        ColumnType.Acceptance,
        ColumnType.Strangeness,
        ColumnType.Symbols
    ]

    PBGColumns = [
        ColumnType.PopulationMultiplier,
        ColumnType.PlanetoidBeltCount,
        ColumnType.GasGiantCount
    ]

    RefuellingColumns = [
        ColumnType.Name,
        ColumnType.Sector,
        ColumnType.Subsector,
        ColumnType.StarPortRefuelling,
        ColumnType.GasGiantRefuelling,
        ColumnType.WaterRefuelling,
        ColumnType.FuelCache,
        ColumnType.StarPort,
        ColumnType.GasGiantCount,
        ColumnType.Hydrographics,
        ColumnType.Atmosphere,
    ]

    class MenuAction(enum.Enum):
        ShowSelectionDetails = enum.auto()
        ShowAllDetails = enum.auto()
        ShowSelectionOnMap = enum.auto()
        ShowAllOnMap = enum.auto()

    # Version 1 format used a world list rather than a hex list. Note that
    # this just used 'v1' for the version rather than 'WorldTable_v1'
    # Version 2 format was added when the table was switched from using worlds
    # to hexes as part of support for dead space routing
    _ContentVersion = 'HexTable_v2'

    def __init__(
            self,
            milieu: astronomer.Milieu,
            rules: traveller.Rules,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[ColumnType] = AllColumns,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None
        self._hexTooltipProvider = None

        action = QtWidgets.QAction('Show Details...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectionDetails)
        self.setMenuAction(HexTable.MenuAction.ShowSelectionDetails, action)

        action = QtWidgets.QAction('Show All Details...', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.showAllDetails)
        self.setMenuAction(HexTable.MenuAction.ShowAllDetails, action)

        action = QtWidgets.QAction('Show on Map...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectionOnMap)
        self.setMenuAction(HexTable.MenuAction.ShowSelectionOnMap, action)

        action = QtWidgets.QAction('Show All on Map...', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.showAllOnMap)
        self.setMenuAction(HexTable.MenuAction.ShowAllOnMap, action)

        self.setColumnHeaders(columns)
        self.setUserColumnHiding(True)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        for index, column in enumerate(columns):
            if column == self.ColumnType.Name or \
                    column == self.ColumnType.Sector or \
                    column == self.ColumnType.Subsector:
                self.setColumnWidth(index, 100)

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def setMilieu(self, milieu: astronomer.Milieu) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._syncContent()

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._syncContent()

    def worldTagging(self) -> typing.Optional[logic.WorldTagging]:
        return logic.WorldTagging(self._worldTagging) if self._worldTagging else None

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._syncContent()

    def taggingColours(self) -> typing.Optional[app.TaggingColours]:
        return app.TaggingColours(self._taggingColours) if self._taggingColours else None

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._syncContent()

    def hex(self, row: int) -> typing.Optional[astronomer.HexPosition]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[0]

    def world(self, row: int) -> typing.Optional[astronomer.World]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[1]

    def hexes(self) -> typing.List[astronomer.HexPosition]:
        hexes = []
        for row in range(self.rowCount()):
            hexes.append(self.hex(row))
        return hexes

    # NOTE: Indexing into the list of returned worlds does not match
    # table row indexing if the table contains dead space hexes.
    def worlds(self) -> typing.List[astronomer.World]:
        worlds = []
        for row in range(self.rowCount()):
            world = self.world(row)
            if world:
                worlds.append(world)
        return worlds

    def hexAt(self, y: int) -> typing.Optional[astronomer.HexPosition]:
        row = self.rowAt(y)
        return self.hex(row) if row >= 0 else None

    def worldAt(self, y: int) -> typing.Optional[astronomer.World]:
        row = self.rowAt(y)
        return self.world(row) if row >= 0 else None

    def insertHex(
            self,
            row: int,
            hex: astronomer.HexPosition
            ) -> int:
        self.insertRow(row)
        return self._fillRow(row, hex)

    def setHex(
            self,
            row: int,
            hex: astronomer.HexPosition
            ) -> int:
        return self._fillRow(row, hex)

    def setHexes(
            self,
            hexes: typing.Iterator[astronomer.HexPosition]
            ) -> None:
        self.removeAllRows()
        for hex in hexes:
            self.addHex(hex)

    def addHex(
            self,
            hex: astronomer.HexPosition
            ) -> int:
        return self.insertHex(self.rowCount(), hex)

    def addHexes(
            self,
            hexes: typing.Iterable[astronomer.HexPosition]
            ) -> None:
        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for hex in hexes:
                self.insertHex(self.rowCount(), hex)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def removeHex(
            self,
            hex: astronomer.HexPosition
            ) -> bool:
        removed = False
        for row in range(self.rowCount() - 1, -1, -1):
            if hex == self.hex(row):
                self.removeRow(row)
                removed = True
        return removed

    def currentHex(self) -> typing.Optional[astronomer.HexPosition]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.hex(row)

    def containsHex(
            self,
            hex: astronomer.HexPosition
            ) -> bool:
        for row in range(self.rowCount()):
            if hex == self.hex(row):
                return True
        return False

    def selectedHexes(self) -> typing.List[astronomer.HexPosition]:
        hexes = []
        for row in range(self.rowCount()):
            if self.isRowSelected(row):
                hex = self.hex(row)
                if hex:
                    hexes.append(hex)
        return hexes

    # NOTE: Indexing into the list of returned worlds does not match table
    # selection indexing if the selection contains dead space hexes.
    def selectedWorlds(self) -> typing.List[astronomer.World]:
        worlds = []
        for row in range(self.rowCount()):
            if self.isRowSelected(row):
                world = self.world(row)
                if world:
                    worlds.append(world)
        return worlds

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTooltipProvider = provider

    def showSelectionDetails(self) -> None:
        self._showDetails(hexes=self.selectedHexes())

    def showAllDetails(self) -> None:
        self._showDetails(hexes=self.hexes())

    def showSelectionOnMap(self) -> None:
        self._showOnMap(hexes=self.selectedHexes())

    def showAllOnMap(self) -> None:
        self._showOnMap(hexes=self.hexes())

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        needsSeparator = False

        action = self.menuAction(HexTable.MenuAction.ShowSelectionDetails)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(HexTable.MenuAction.ShowAllDetails)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        action = self.menuAction(HexTable.MenuAction.ShowSelectionOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(HexTable.MenuAction.ShowAllOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        # Add base class menu options (export, copy to clipboard etc)
        super().fillContextMenu(menu)

    # NOTE: Override base ListTable implementation of contentToCsv so that x/y
    # hex positions can be inserted in the exported data. This is done so in
    # the future I can add milieu independent import of the exported files by
    # just using the x/y position and ignoring the rest of the details.
    def contentToCsv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        header = []
        for column in range(self.columnCount()):
            if self.isColumnHidden(column):
                continue
            header.append(self._csvHeaderText(column))
        header.extend(['Reference X', 'Reference Y'])
        writer.writerow(header)

        for row in range(self.rowCount()):
            hex = self.hex(row)
            if not hex:
                continue

            content = []
            for column in range(self.columnCount()):
                if self.isColumnHidden(column):
                    continue
                content.append(self._csvCellText(row, column))
            content.extend([hex.absoluteX(), hex.absoluteY()])

            writer.writerow(content)

        content = output.getvalue()
        # The csv writer inserts \r\n which get messed up if you try
        # to write the content to a file, resulting in blank lines
        # between every line of data
        return content.replace('\r\n', '\n')

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexTable._ContentVersion)

        count = self.rowCount()
        stream.writeUInt32(count)
        for row in range(self.rowCount()):
            hex = self.hex(row)
            stream.writeInt32(hex.absoluteX())
            stream.writeInt32(hex.absoluteY())

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexTable content (Unsupported version)')
            return False

        count = stream.readUInt32()
        hexes = []
        for _ in range(count):
            hexes.append(astronomer.HexPosition(
                absoluteX=stream.readInt32(),
                absoluteY=stream.readInt32()))
        self.setHexes(hexes=hexes)

        return True

    def isEmptyChanged(self) -> None:
        super().isEmptyChanged()
        self._syncHexTableActions()

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)
        self._syncHexTableActions()

    def _fillRow(
            self,
            row: int,
            hex: astronomer.HexPosition
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            uwp = economics = culture = pbg = worldTagColour = None

            world = astronomer.WorldManager.instance().worldByPosition(
                milieu=self._milieu,
                hex=hex)
            if world:
                uwp = world.uwp()
                economics = world.economics()
                culture = world.culture()
                pbg = world.pbg()
                worldTagLevel = worldTagColour = None
                if self._worldTagging:
                    worldTagLevel = self._worldTagging.calculateWorldTagLevel(
                        rules=self._rules,
                        world=world)
                    worldTagColour = self._taggingColour(worldTagLevel) if worldTagLevel else None

            # NOTE: It's important that an item is always created for each of the
            # cells in the row, even if it has no text. If you don't and you use
            # the move selection up/down functions, it doesn't move the selection
            # highlight for the cells that have no items. This appears to be a Qt
            # bug as it's it that is implementing the full row selection and, as
            # far as I can see, the api only allows user code to manipulate the
            # selection if there is an item in the cell
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                tagColour = None
                if columnType == self.ColumnType.Name:
                    tableItem = gui.TableWidgetItemEx()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.name())
                        tagColour = worldTagColour
                    else:
                        hexString = f'Dead Space {hex.offsetX():02d}{hex.offsetY():02d}'
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, hexString)
                        tableItem.setItalic(enable=True)
                        tagColour = self._taggingColour(level=logic.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.Sector:
                    tableItem = gui.TableWidgetItemEx()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.sectorName())
                        tagColour = worldTagColour
                    else:
                        sector = astronomer.WorldManager.instance().sectorByPosition(
                            milieu=self._milieu,
                            hex=hex)
                        tableItem.setData(
                            QtCore.Qt.ItemDataRole.DisplayRole,
                            sector.name() if sector else 'Unknown')
                        tableItem.setItalic(enable=not sector)
                        tagColour = self._taggingColour(level=logic.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.Subsector:
                    tableItem = gui.TableWidgetItemEx()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.subsectorName())
                        tagColour = worldTagColour
                    else:
                        subsector = astronomer.WorldManager.instance().subsectorByPosition(
                            milieu=self._milieu,
                            hex=hex)
                        tableItem.setData(
                            QtCore.Qt.ItemDataRole.DisplayRole,
                            subsector.name() if subsector else 'Unknown')
                        tableItem.setItalic(enable=not sector)
                        tagColour = self._taggingColour(level=logic.TagLevel.Danger) # Tag dead space as danger level
                elif columnType == self.ColumnType.Zone:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, astronomer.zoneTypeCode(world.zone()))
                        tagLevel = self._worldTagging.calculateZoneTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.StarPort:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.StarPort))
                        tagLevel = self._worldTagging.calculateStarPortTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.TechLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.TechLevel))
                        tagLevel = self._worldTagging.calculateTechLevelTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.LawLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.LawLevel))
                        tagLevel = self._worldTagging.calculateLawLevelTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Population:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.Population))
                        tagLevel = self._worldTagging.calculatePopulationTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Government:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.Government))
                        tagLevel = self._worldTagging.calculateGovernmentTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.WorldSize:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.WorldSize))
                        tagLevel = self._worldTagging.calculateWorldSizeTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Atmosphere:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.Atmosphere))
                        tagLevel = self._worldTagging.calculateAtmosphereTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Hydrographics:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(astronomer.UWP.Element.Hydrographics))
                        tagLevel = self._worldTagging.calculateHydrographicsTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.StarPortRefuelling:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        text = ''
                        if world.hasStarPortRefuelling(rules=self._rules, includeUnrefined=False):
                            text += 'refined'
                        if world.hasStarPortRefuelling(rules=self._rules, includeRefined=False):
                            if text:
                                text += ' & '
                            text += 'unrefined'
                        if not text:
                            text = 'none'
                        tableItem.setText(text)
                elif columnType == self.ColumnType.GasGiantRefuelling:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        hasRefuelling = world.hasGasGiantRefuelling()
                        tableItem.setText('yes' if hasRefuelling else 'no' )
                elif columnType == self.ColumnType.WaterRefuelling:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        hasRefuelling = world.hasWaterRefuelling()
                        tableItem.setText('yes' if hasRefuelling else 'no' )
                elif columnType == self.ColumnType.FuelCache:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setText('yes' if world.isFuelCache() else 'no' )
                elif columnType == self.ColumnType.Anomaly:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setText('yes' if world.isAnomaly() else 'no' )
                elif columnType == self.ColumnType.Resources:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(astronomer.Economics.Element.Resources))
                        tagLevel = self._worldTagging.calculateResourcesTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Labour:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(astronomer.Economics.Element.Labour))
                        tagLevel = self._worldTagging.calculateLabourTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Infrastructure:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(astronomer.Economics.Element.Infrastructure))
                        tagLevel = self._worldTagging.calculateInfrastructureTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Efficiency:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(astronomer.Economics.Element.Efficiency))
                        tagLevel = self._worldTagging.calculateEfficiencyTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Heterogeneity:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(astronomer.Culture.Element.Heterogeneity))
                        tagLevel = self._worldTagging.calculateHeterogeneityTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Acceptance:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(astronomer.Culture.Element.Acceptance))
                        tagLevel = self._worldTagging.calculateAcceptanceTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Strangeness:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(astronomer.Culture.Element.Strangeness))
                        tagLevel = self._worldTagging.calculateStrangenessTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Symbols:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(astronomer.Culture.Element.Symbols))
                        tagLevel = self._worldTagging.calculateSymbolsTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Nobilities:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        nobilities = world.nobilities()
                        highestTagLevel = None
                        if self._worldTagging:
                            for nobility in nobilities:
                                tagLevel = self._worldTagging.calculateNobilityTagLevel(nobility)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, nobilities.string())
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                elif columnType == self.ColumnType.Allegiance:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        allegiance = world.allegiance()
                        if allegiance:
                            tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, allegiance.code())
                            tagLevel = self._worldTagging.calculateAllegianceTagLevel(allegiance=allegiance) if self._worldTagging else None
                            tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Sophont:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        displayText = ''
                        remarks = world.remarks()
                        for sophont in remarks.sophonts():
                            if displayText:
                                displayText += ', '
                            displayText += sophont.name()

                            if sophont.isHomeWorld():
                                displayText += ' (Home World)'

                            if sophont.isDieBack():
                                displayText += ' (Die Back)'
                            elif sophont.percentage() is not None:
                                displayText += f' (Population: {sophont.percentage()}%)'

                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.TradeCodes:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tradeCodeStrings = [traveller.tradeCodeString(tc) for tc in world.tradeCodes(rules=self._rules)]
                        tradeCodeStrings.sort()
                        tableItem.setData(
                            QtCore.Qt.ItemDataRole.DisplayRole, ', '.join(tradeCodeStrings))
                elif columnType == self.ColumnType.PopulationCount:
                    if world:
                        count = world.population()
                        if count >= 0:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.PopulationMultiplier:
                    if world:
                        count = pbg.numeric(
                            element=astronomer.PBG.Element.PopulationMultiplier,
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.PlanetoidBeltCount:
                    if world:
                        count = pbg.numeric(
                            element=astronomer.PBG.Element.PlanetoidBelts,
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.GasGiantCount:
                    if world:
                        count = pbg.numeric(
                            element=astronomer.PBG.Element.GasGiants,
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.StarCount:
                    if world:
                        tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfStars())
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.SystemWorldCount:
                    if world and world.numberOfSystemWorlds() is not None:
                        tableItem = gui.FormattedNumberTableWidgetItem(world.numberOfSystemWorlds())
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.Bases:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        bases = world.bases()
                        highestTagLevel = None
                        if self._worldTagging:
                            for base in bases:
                                tagLevel = self._worldTagging.calculateBaseTypeTagLevel(base)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, bases.string())
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                elif columnType == self.ColumnType.ScoutBase:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        bases = world.bases()
                        scoutBases = bases.scoutBases()
                        highestTagLevel = None
                        if scoutBases and self._worldTagging:
                            for base in scoutBases:
                                tagLevel = self._worldTagging.calculateBaseTypeTagLevel(base)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'yes' if scoutBases else 'no')
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                elif columnType == self.ColumnType.MilitaryBase:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        bases = world.bases()
                        militaryBases = bases.militaryBases()
                        highestTagLevel = None
                        if militaryBases and self._worldTagging:
                            for base in militaryBases:
                                tagLevel = self._worldTagging.calculateBaseTypeTagLevel(base)
                                if tagLevel and (not highestTagLevel or highestTagLevel < tagLevel):
                                    highestTagLevel = tagLevel
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'yes' if militaryBases else 'no')
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                elif columnType == self.ColumnType.OwnerWorlds:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        highestTagLevel = None
                        if self._worldTagging:
                            for ownerWorldRef in world.ownerWorldReferences():
                                ownerSector = None
                                if ownerWorldRef.sectorAbbreviation():
                                    matchSectors = astronomer.WorldManager.instance().sectorByAbbreviation(
                                        milieu=self._milieu,
                                        abbreviation=ownerWorldRef.sectorAbbreviation())
                                    if matchSectors:
                                        ownerSector = matchSectors[0]
                                else:
                                    ownerSector = astronomer.WorldManager.instance().sectorBySectorIndex(
                                        milieu=self._milieu,
                                        index=hex.sectorIndex())

                                ownerWorld = None
                                if ownerSector:
                                    ownerHex = astronomer.HexPosition(
                                        sectorIndex=ownerSector.index(),
                                        offsetX=ownerWorldRef.hexX(),
                                        offsetY=ownerWorldRef.hexY())
                                    ownerWorld = astronomer.WorldManager.instance().worldByPosition(
                                        milieu=self._milieu,
                                        hex=ownerHex)

                                if ownerWorld:
                                    tagLevel = self._worldTagging.calculateWorldTagLevel(
                                        rules=self._rules,
                                        world=ownerWorld)
                                    if tagLevel and (not highestTagLevel or tagLevel > highestTagLevel):
                                        highestTagLevel = tagLevel
                                else:
                                    # We don't know about this world so the tag level is error, no need to continue looking
                                    highestTagLevel = logic.TagLevel.Danger
                                    break
                        tableItem = gui.FormattedNumberTableWidgetItem(world.ownerCount())
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                elif columnType == self.ColumnType.ColonyWorlds:
                    if world:
                        highestTagLevel = None
                        if self._worldTagging:
                            for colonyWorldRef in world.colonyWorldReferences():
                                colonySector = None
                                if colonyWorldRef.sectorAbbreviation():
                                    matchSectors = astronomer.WorldManager.instance().sectorByAbbreviation(
                                        milieu=self._milieu,
                                        abbreviation=colonyWorldRef.sectorAbbreviation())
                                    if matchSectors:
                                        colonySector = matchSectors[0]
                                else:
                                    colonySector = astronomer.WorldManager.instance().sectorBySectorIndex(
                                        milieu=self._milieu,
                                        index=hex.sectorIndex())

                                colonyWorld = None
                                if colonySector:
                                    colonyHex = astronomer.HexPosition(
                                        sectorIndex=colonySector.index(),
                                        offsetX=colonyWorldRef.hexX(),
                                        offsetY=colonyWorldRef.hexY())
                                    colonyWorld = astronomer.WorldManager.instance().worldByPosition(
                                        milieu=self._milieu,
                                        hex=colonyHex)

                                if colonyWorld:
                                    tagLevel = self._worldTagging.calculateWorldTagLevel(
                                        rules=self._rules,
                                        world=colonyWorld)
                                    if tagLevel and (not highestTagLevel or tagLevel > highestTagLevel):
                                        highestTagLevel = tagLevel
                                else:
                                    # We don't know about this world so the tag level is error, no need to continue looking
                                    highestTagLevel = logic.TagLevel.Danger
                                    break
                        tableItem = gui.FormattedNumberTableWidgetItem(world.colonyCount())
                        if highestTagLevel:
                            tagColour = self._taggingColour(level=highestTagLevel)
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.Remarks:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        remarks = world.remarks()
                        tableItem.setData(
                            QtCore.Qt.ItemDataRole.DisplayRole,
                            remarks.string(rules=self._rules))

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (hex, world))
                    if tagColour:
                        tableItem.setBackground(QtGui.QColor(tagColour))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _createToolTip(self, item: QtWidgets.QTableWidgetItem) -> typing.Optional[str]:
        hex = self.hex(item.row())
        if not hex:
            return None
        world = self.world(item.row())

        columnType = self.columnHeader(item.column())

        if columnType == self.ColumnType.Name or columnType == self.ColumnType.Sector or \
                columnType == self.ColumnType.Subsector:
            if self._hexTooltipProvider:
                return self._hexTooltipProvider.tooltip(hex=hex)
            elif world:
                return astronomer.WorldManager.instance().canonicalHexName(
                    milieu=world.milieu(),
                    hex=world.hex())

        if world == None:
            return gui.createStringToolTip('Dead Space')

        if columnType == self.ColumnType.Zone:
            zone = world.zone()
            if not zone:
                return None
            return gui.createStringToolTip(astronomer.zoneTypeName(zone))
        elif columnType == self.ColumnType.StarPort:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.StarPort))
        elif columnType == self.ColumnType.TechLevel:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.TechLevel))
        elif columnType == self.ColumnType.LawLevel:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.LawLevel))
        elif columnType == self.ColumnType.Population:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.Population))
        elif columnType == self.ColumnType.Government:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.Government))
        elif columnType == self.ColumnType.WorldSize:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.WorldSize))
        elif columnType == self.ColumnType.Atmosphere:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.Atmosphere))
        elif columnType == self.ColumnType.Hydrographics:
            return gui.createStringToolTip(world.uwp().description(astronomer.UWP.Element.Hydrographics))
        elif columnType == self.ColumnType.Resources:
            return gui.createStringToolTip(world.economics().description(astronomer.Economics.Element.Resources))
        elif columnType == self.ColumnType.Labour:
            return gui.createStringToolTip(world.economics().description(astronomer.Economics.Element.Labour))
        elif columnType == self.ColumnType.Infrastructure:
            return gui.createStringToolTip(world.economics().description(astronomer.Economics.Element.Infrastructure))
        elif columnType == self.ColumnType.Efficiency:
            return gui.createStringToolTip(world.economics().description(astronomer.Economics.Element.Efficiency))
        elif columnType == self.ColumnType.Heterogeneity:
            return gui.createStringToolTip(world.culture().description(astronomer.Culture.Element.Heterogeneity))
        elif columnType == self.ColumnType.Acceptance:
            return gui.createStringToolTip(world.culture().description(astronomer.Culture.Element.Acceptance))
        elif columnType == self.ColumnType.Strangeness:
            return gui.createStringToolTip(world.culture().description(astronomer.Culture.Element.Strangeness))
        elif columnType == self.ColumnType.Symbols:
            return gui.createStringToolTip(world.culture().description(astronomer.Culture.Element.Symbols))
        elif columnType == self.ColumnType.Nobilities:
            lines = []
            lineColours = {}
            nobilities = world.nobilities()
            for nobilityType in nobilities:
                nobilityDescription = astronomer.Nobilities.description(nobilityType)
                lines.append(nobilityDescription)

                tagLevel = self._worldTagging.calculateNobilityTagLevel(nobilityType) if self._worldTagging else None
                if tagLevel:
                    lineColours[nobilityDescription] = self._taggingColour(level=tagLevel)
            if lines:
                return gui.createListToolTip(
                    title=f'Nobilities: {nobilities.string()}',
                    strings=lines,
                    stringColours=lineColours)
        elif columnType == self.ColumnType.Allegiance:
            allegiance = world.allegiance()
            if not allegiance:
                return None
            return gui.createStringToolTip(allegiance.name())
        elif columnType == self.ColumnType.Sophont:
            lines = []
            remarks = world.remarks()
            for sophont in remarks.sophonts():
                line = sophont.name()

                if sophont.isHomeWorld():
                    line += ' (Home World)'

                if sophont.isDieBack():
                    line += ' (Die Back)'
                elif sophont.percentage() is not None:
                    line += f' (Population: {sophont.percentage()}%)'

                lines.append(line)
            if lines:
                return gui.createListToolTip(
                    title='Sophonts:',
                    strings=lines)
        elif columnType == self.ColumnType.TradeCodes:
            lines = []
            for tradeCode in world.tradeCodes(rules=self._rules):
                lines.append('{code} - {name} - {description}'.format(
                    code=traveller.tradeCodeString(tradeCode=tradeCode),
                    name=traveller.tradeCodeName(tradeCode=tradeCode),
                    description=traveller.tradeCodeDescription(tradeCode=tradeCode)))
            if lines:
                lines.sort()
                return gui.createListToolTip(
                    title='Trade Codes:',
                    strings=lines)
        elif columnType == self.ColumnType.StarCount:
            lines = []
            lineIndents = {}
            lineColours = {}
            stellar = world.stellar()
            for star in stellar:
                lines.append(f'Classification: {star.string()}')

                luminosityClass = star.code(astronomer.Star.Element.LuminosityClass)
                luminosityClass = f'Luminosity Class: {luminosityClass} - {star.description(astronomer.Star.Element.LuminosityClass)}'
                lines.append(luminosityClass)
                lineIndents[luminosityClass] = 1
                tagLevel = self._worldTagging.calculateLuminosityTagLevel(star=star) if self._worldTagging else None
                if tagLevel:
                    lineColours[luminosityClass] = self._taggingColour(level=tagLevel)

                spectralClass = star.code(astronomer.Star.Element.SpectralClass)
                if spectralClass is not None:
                    spectralClass = f'Spectral Class: {spectralClass} - {star.description(astronomer.Star.Element.SpectralClass)}'
                    lines.append(spectralClass)
                    lineIndents[spectralClass] = 1
                    tagLevel = self._worldTagging.calculateSpectralTagLevel(star=star) if self._worldTagging else None
                    if tagLevel:
                        lineColours[spectralClass] = self._taggingColour(level=tagLevel)

                    spectralScale = star.code(astronomer.Star.Element.SpectralScale)
                    if spectralScale is not None:
                        spectralScale = f'Spectral Scale: {spectralScale} - {star.description(astronomer.Star.Element.SpectralScale)}'
                        lines.append(spectralScale)
                        lineIndents[spectralScale] = 1

            if lines:
                return gui.createListToolTip(
                    title=f'Stellar: {stellar.string()}',
                    strings=lines,
                    stringColours=lineColours,
                    stringIndents=lineIndents)
        elif columnType == self.ColumnType.PopulationCount:
            if world.population() >= 0:
                return None
            return gui.createStringToolTip(string='Unknown')
        elif columnType == self.ColumnType.PopulationMultiplier:
            return gui.createStringToolTip(world.pbg().description(element=astronomer.PBG.Element.PopulationMultiplier))
        elif columnType == self.ColumnType.PlanetoidBeltCount:
            return gui.createStringToolTip(world.pbg().description(element=astronomer.PBG.Element.PlanetoidBelts))
        elif columnType == self.ColumnType.GasGiantCount:
            return gui.createStringToolTip(world.pbg().description(element=astronomer.PBG.Element.GasGiants))
        elif columnType == self.ColumnType.Bases:
            return gui.createBasesToolTip(
                world=world,
                worldTagging=self._worldTagging,
                taggingColours=self._taggingColours)
        elif columnType == self.ColumnType.ScoutBase:
            bases = world.bases()
            scoutBases = bases.scoutBases()
            if scoutBases:
                return gui.createBasesToolTip(
                    world=world,
                    includeBaseTypes=scoutBases,
                    worldTagging=self._worldTagging,
                    taggingColours=self._taggingColours)
        elif columnType == self.ColumnType.MilitaryBase:
            bases = world.bases()
            militaryBases = bases.militaryBases()
            if militaryBases:
                return gui.createBasesToolTip(
                    world=world,
                    includeBaseTypes=militaryBases,
                    worldTagging=self._worldTagging,
                    taggingColours=self._taggingColours)
        elif columnType == self.ColumnType.OwnerWorlds:
            if world.ownerCount() > 0:
                listStrings = []
                listColours = {}
                for ownerWorldRef in world.ownerWorldReferences():
                    ownerSector = None
                    if ownerWorldRef.sectorAbbreviation():
                        matchSectors = astronomer.WorldManager.instance().sectorByAbbreviation(
                            milieu=self._milieu,
                            abbreviation=ownerWorldRef.sectorAbbreviation())
                        if matchSectors:
                            ownerSector = matchSectors[0]
                    else:
                        ownerSector = astronomer.WorldManager.instance().sectorBySectorIndex(
                            milieu=self._milieu,
                            index=hex.sectorIndex())

                    ownerWorld = None
                    if ownerSector:
                        ownerHex = astronomer.HexPosition(
                            sectorIndex=ownerSector.index(),
                            offsetX=ownerWorldRef.hexX(),
                            offsetY=ownerWorldRef.hexY())
                        ownerWorld = astronomer.WorldManager.instance().worldByPosition(
                            milieu=self._milieu,
                            hex=ownerHex)

                    if ownerWorld:
                        ownerString = ownerWorld.name(includeSubsector=True)
                        listStrings.append(ownerString)
                        if self._worldTagging:
                            tagLevel = self._worldTagging.calculateWorldTagLevel(
                                rules=self._rules,
                                world=ownerWorld)
                            if tagLevel:
                                listColours[ownerString] = self._taggingColour(level=tagLevel)
                    else:
                        ownerString = 'Unknown world at {sector} {x:02d}{y:02d}'.format(
                            sector=ownerSector.name() if ownerSector else 'Unknown Sector',
                            x=ownerWorldRef.hexX(),
                            y=ownerWorldRef.hexY())
                        listStrings.append(ownerString)
                        listColours[ownerString] = self._taggingColour(
                            level=logic.TagLevel.Danger)
                return gui.createListToolTip(
                    title='Owner Worlds',
                    strings=listStrings,
                    stringColours=listColours)
        elif columnType == self.ColumnType.ColonyWorlds:
            if world.colonyCount() > 0:
                listStrings = []
                listColours = {}
                for colonyWorldRef in world.colonyWorldReferences():
                    colonySector = None
                    if colonyWorldRef.sectorAbbreviation():
                        matchSectors = astronomer.WorldManager.instance().sectorByAbbreviation(
                            milieu=self._milieu,
                            abbreviation=colonyWorldRef.sectorAbbreviation())
                        if matchSectors:
                            colonySector = matchSectors[0]
                    else:
                        colonySector = astronomer.WorldManager.instance().sectorBySectorIndex(
                            milieu=self._milieu,
                            index=hex.sectorIndex())

                    colonyWorld = None
                    if colonySector:
                        colonyHex = astronomer.HexPosition(
                            sectorIndex=colonySector.index(),
                            offsetX=colonyWorldRef.hexX(),
                            offsetY=colonyWorldRef.hexY())
                        colonyWorld = astronomer.WorldManager.instance().worldByPosition(
                            milieu=self._milieu,
                            hex=colonyHex)

                    if colonyWorld:
                        colonyString = colonyWorld.name(includeSubsector=True)
                        listStrings.append(colonyString)
                        if self._worldTagging:
                            tagLevel = self._worldTagging.calculateWorldTagLevel(
                                rules=self._rules,
                                world=colonyWorld)
                            if tagLevel:
                                listColours[colonyString] = self._taggingColour(level=tagLevel)
                    else:
                        colonyString = 'Unknown world at {sector} {x:02d}{y:02d}'.format(
                            sector=colonySector.name() if colonySector else 'Unknown Sector',
                            x=colonyWorldRef.hexX(),
                            y=colonyWorldRef.hexY())
                        listStrings.append(colonyString)
                        listColours[colonyString] = self._taggingColour(
                            level=logic.TagLevel.Danger)
                return gui.createListToolTip(
                    title='Colony Worlds',
                    strings=listStrings,
                    stringColours=listColours)
        elif columnType == self.ColumnType.Remarks:
            remarks = world.remarks()
            return gui.createStringToolTip(remarks.string(rules=self._rules))

        return None

    def _taggingColour(
            self,
            level: typing.Optional[logic.TagLevel]
            ) -> typing.Optional[str]:
        if not level or not self._taggingColours:
            return None
        return self._taggingColours.colour(level=level)

    def _syncContent(self) -> None:
        # Disable sorting during sync then re-enable after so sort is
        # only performed once rather than per row
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for row in range(self.rowCount()):
                self._fillRow(row=row, hex=self.hex(row=row))
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _syncHexTableActions(self) -> None:
        hasContent = not self.isEmpty()
        hasSelection = self.hasSelection()

        action = self.menuAction(HexTable.MenuAction.ShowSelectionDetails)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(HexTable.MenuAction.ShowAllDetails)
        if action:
            action.setEnabled(hasContent)

        action = self.menuAction(HexTable.MenuAction.ShowSelectionOnMap)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(HexTable.MenuAction.ShowAllOnMap)
        if action:
            action.setEnabled(hasContent)

    def _showDetails(
            self,
            hexes: typing.Iterable[astronomer.HexPosition]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showHexDetailsWindow()
        detailsWindow.addHexes(hexes=hexes)

    def _showOnMap(
            self,
            hexes: typing.Iterable[astronomer.HexPosition]
            ) -> None:
        try:
            mapWindow = gui.WindowManager.instance().showUniverseMapWindow()
            mapWindow.clearOverlays()
            mapWindow.highlightHexes(hexes=hexes)
        except Exception as ex:
            message = 'Failed to show hexes(s) on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
