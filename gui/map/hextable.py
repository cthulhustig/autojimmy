import app
import enum
import gui
import logging
import logic
import traveller
import travellermap
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
        OwnerWorld = 'Owner'
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
        ColumnType.OwnerWorld,
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
        ColumnType.OwnerWorld,
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

    # Version 1 format used a world list rather than a hex list. Note that
    # this just used 'v1' for the version rather than 'WorldTable_v1'
    # Version 2 format was added when the table was switched from using worlds
    # to hexes as part of support for dead space routing
    _ContentVersion = 'HexTable_v2'

    def __init__(
            self,
            milieu: travellermap.Milieu,
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

        self._showSelectionDetailsAction =  QtWidgets.QAction('Show Selection Details...', self)
        self._showSelectionDetailsAction.setEnabled(False) # No selection
        self._showSelectionDetailsAction.triggered.connect(self.showSelectionDetails)

        self._showAllDetailsAction =  QtWidgets.QAction('Show All Details...', self)
        self._showAllDetailsAction.setEnabled(False) # No content
        self._showAllDetailsAction.triggered.connect(self.showAllDetails)

        self._showSelectionOnMapAction =  QtWidgets.QAction('Show Selection on Map...', self)
        self._showSelectionOnMapAction.setEnabled(False) # No selection
        self._showSelectionOnMapAction.triggered.connect(self.showSelectionOnMap)

        self._showAllOnMapAction =  QtWidgets.QAction('Show All on Map...', self)
        self._showAllOnMapAction.setEnabled(False) # No content
        self._showAllOnMapAction.triggered.connect(self.showAllOnMap)

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

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
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

    def hex(self, row: int) -> typing.Optional[travellermap.HexPosition]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[0]

    def world(self, row: int) -> typing.Optional[traveller.World]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)[1]

    def hexes(self) -> typing.List[travellermap.HexPosition]:
        hexes = []
        for row in range(self.rowCount()):
            hexes.append(self.hex(row))
        return hexes

    # NOTE: Indexing into the list of returned worlds does not match
    # table row indexing if the table contains dead space hexes.
    def worlds(self) -> typing.List[traveller.World]:
        worlds = []
        for row in range(self.rowCount()):
            world = self.world(row)
            if world:
                worlds.append(world)
        return worlds

    def hexAt(self, y: int) -> typing.Optional[travellermap.HexPosition]:
        row = self.rowAt(y)
        return self.hex(row) if row >= 0 else None

    def worldAt(self, y: int) -> typing.Optional[traveller.World]:
        row = self.rowAt(y)
        return self.world(row) if row >= 0 else None

    def insertHex(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        self.insertRow(row)
        return self._fillRow(row, hex)

    def setHex(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        return self._fillRow(row, hex)

    def setHexes(
            self,
            hexes: typing.Iterator[travellermap.HexPosition]
            ) -> None:
        self.removeAllRows()
        for hex in hexes:
            self.addHex(hex)

    def addHex(
            self,
            hex: travellermap.HexPosition
            ) -> int:
        return self.insertHex(self.rowCount(), hex)

    def addHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
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
            hex: travellermap.HexPosition
            ) -> bool:
        removed = False
        for row in range(self.rowCount() - 1, -1, -1):
            if hex == self.hex(row):
                self.removeRow(row)
                removed = True
        return removed

    def currentHex(self) -> typing.Optional[travellermap.HexPosition]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.hex(row)

    def containsHex(
            self,
            hex: travellermap.HexPosition
            ) -> bool:
        for row in range(self.rowCount()):
            if hex == self.hex(row):
                return True
        return False

    def selectedHexes(self) -> typing.List[travellermap.HexPosition]:
        hexes = []
        for row in range(self.rowCount()):
            if self.isRowSelected(row):
                hex = self.hex(row)
                if hex:
                    hexes.append(hex)
        return hexes

    # NOTE: Indexing into the list of returned worlds does not match table
    # selection indexing if the selection contains dead space hexes.
    def selectedWorlds(self) -> typing.List[traveller.World]:
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

    def showSelectionDetailsAction(self) -> QtWidgets.QAction:
        return self._showSelectionDetailsAction

    def setShowSelectionDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectionDetailsAction = action

    def showAllDetailsAction(self) -> QtWidgets.QAction:
        return self._showAllDetailsAction

    def setShowAllDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._showAllDetailsAction = action

    def showSelectionOnMapAction(self) -> QtWidgets.QAction:
        return self._showSelectionOnMapAction

    def setShowSelectionOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectionOnMapAction = action

    def showAllOnMapAction(self) -> QtWidgets.QAction:
        return self._showAllOnMapAction

    def setShowAllOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showAllOnMapAction = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.showSelectionDetailsAction())
        menu.addAction(self.showAllDetailsAction())
        menu.addSeparator()
        menu.addAction(self.showSelectionOnMapAction())
        menu.addAction(self.showAllOnMapAction())
        menu.addSeparator()

        # Add base class menu options (export, copy to clipboard etc)
        super().fillContextMenu(menu)

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
            hexes.append(travellermap.HexPosition(
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
            hex: travellermap.HexPosition
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            uwp = economics = culture = pbg = worldTagColour = None

            world = traveller.WorldManager.instance().worldByPosition(
                milieu=self._milieu,
                hex=hex)
            if world:
                uwp = world.uwp()
                economics = world.economics()
                culture = world.culture()
                pbg = world.pbg()
                worldTagColour = self._taggingColour(
                    level=self._worldTagging.calculateWorldTagLevel(world) if self._worldTagging else None)

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
                        sector = traveller.WorldManager.instance().sectorByPosition(
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
                        subsector = traveller.WorldManager.instance().subsectorByPosition(
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
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, traveller.zoneTypeCode(world.zone()))
                        tagLevel = self._worldTagging.calculateZoneTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.StarPort:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.StarPort))
                        tagLevel = self._worldTagging.calculateStarPortTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.TechLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.TechLevel))
                        tagLevel = self._worldTagging.calculateTechLevelTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.LawLevel:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.LawLevel))
                        tagLevel = self._worldTagging.calculateLawLevelTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Population:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Population))
                        tagLevel = self._worldTagging.calculatePopulationTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Government:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Government))
                        tagLevel = self._worldTagging.calculateGovernmentTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.WorldSize:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.WorldSize))
                        tagLevel = self._worldTagging.calculateWorldSizeTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Atmosphere:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Atmosphere))
                        tagLevel = self._worldTagging.calculateAtmosphereTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Hydrographics:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, uwp.code(traveller.UWP.Element.Hydrographics))
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
                        tableItem.setText('yes' if world.hasGasGiantRefuelling() else 'no' )
                elif columnType == self.ColumnType.WaterRefuelling:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setText('yes' if world.hasWaterRefuelling() else 'no' )
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
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Resources))
                        tagLevel = self._worldTagging.calculateResourcesTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Labour:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Labour))
                        tagLevel = self._worldTagging.calculateLabourTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Infrastructure:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Infrastructure))
                        tagLevel = self._worldTagging.calculateInfrastructureTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Efficiency:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, economics.code(traveller.Economics.Element.Efficiency))
                        tagLevel = self._worldTagging.calculateEfficiencyTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Heterogeneity:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Heterogeneity))
                        tagLevel = self._worldTagging.calculateHeterogeneityTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Acceptance:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Acceptance))
                        tagLevel = self._worldTagging.calculateAcceptanceTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Strangeness:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Strangeness))
                        tagLevel = self._worldTagging.calculateStrangenessTagLevel(world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Symbols:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, culture.code(traveller.Culture.Element.Symbols))
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
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, world.allegiance())
                        tagLevel = self._worldTagging.calculateAllegianceTagLevel(world=world) if self._worldTagging else None
                        tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.Sophont:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        displayText = ''
                        remarks = world.remarks()
                        for sophont in remarks.sophonts():
                            percentage = remarks.sophontPercentage(sophont)
                            displayText += f', {sophont}' if displayText else sophont
                            displayText += f' ({percentage}%)'
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
                elif columnType == self.ColumnType.TradeCodes:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        displayText = ''
                        for tradeCode in world.tradeCodes():
                            tradeCodeString = traveller.tradeCodeString(tradeCode)
                            displayText += f', {tradeCodeString}' if displayText else tradeCodeString
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, displayText)
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
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.PopulationMultiplier),
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.PlanetoidBeltCount:
                    if world:
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.PlanetoidBelts),
                            default=None)
                        if count != None:
                            tableItem = gui.FormattedNumberTableWidgetItem(value=count)
                        else:
                            tableItem = QtWidgets.QTableWidgetItem('?')
                    else:
                        tableItem = QtWidgets.QTableWidgetItem()
                elif columnType == self.ColumnType.GasGiantCount:
                    if world:
                        count = traveller.ehexToInteger(
                            value=pbg.code(element=traveller.PBG.Element.GasGiants),
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
                    if world:
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
                elif columnType == self.ColumnType.OwnerWorld:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if world:
                        ownerString = None
                        tagLevel = None
                        if world.hasOwner():
                            try:
                                ownerWorld = traveller.WorldManager.instance().worldBySectorHex(
                                    milieu=self._milieu,
                                    sectorHex=world.ownerSectorHex())
                            except Exception:
                                ownerWorld = None

                            if ownerWorld:
                                ownerString = ownerWorld.name(includeSubsector=True)
                                tagLevel = self._worldTagging.calculateWorldTagLevel(world=ownerWorld) if self._worldTagging else None
                            else:
                                # We don't know about this world so just display the sector hex and tag it as danger
                                ownerString = world.ownerSectorHex()
                                tagLevel = logic.TagLevel.Danger
                            tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, ownerString)
                        if tagLevel:
                            tagColour = self._taggingColour(level=tagLevel)
                elif columnType == self.ColumnType.ColonyWorlds:
                    if world:
                        highestTagLevel = None
                        if self._worldTagging:
                            for colonySectorHex in world.colonySectorHexes():
                                try:
                                    colonyWorld = traveller.WorldManager.instance().worldBySectorHex(
                                        milieu=self._milieu,
                                        sectorHex=colonySectorHex)
                                except Exception:
                                    colonyWorld = None

                                if colonyWorld:
                                    tagLevel = self._worldTagging.calculateWorldTagLevel(world=colonyWorld)
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
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, remarks.string())

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
                return traveller.WorldManager.instance().canonicalHexName(
                    milieu=world.milieu(),
                    hex=world.hex())

        if world == None:
            return gui.createStringToolTip('Dead Space')

        if columnType == self.ColumnType.Zone:
            zone = world.zone()
            if not zone:
                return None
            return gui.createStringToolTip(traveller.zoneTypeName(zone))
        elif columnType == self.ColumnType.StarPort:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.StarPort))
        elif columnType == self.ColumnType.TechLevel:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.TechLevel))
        elif columnType == self.ColumnType.LawLevel:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.LawLevel))
        elif columnType == self.ColumnType.Population:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Population))
        elif columnType == self.ColumnType.Government:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Government))
        elif columnType == self.ColumnType.WorldSize:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.WorldSize))
        elif columnType == self.ColumnType.Atmosphere:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Atmosphere))
        elif columnType == self.ColumnType.Hydrographics:
            return gui.createStringToolTip(world.uwp().description(traveller.UWP.Element.Hydrographics))
        elif columnType == self.ColumnType.Resources:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Resources))
        elif columnType == self.ColumnType.Labour:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Labour))
        elif columnType == self.ColumnType.Infrastructure:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Infrastructure))
        elif columnType == self.ColumnType.Efficiency:
            return gui.createStringToolTip(world.economics().description(traveller.Economics.Element.Efficiency))
        elif columnType == self.ColumnType.Heterogeneity:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Heterogeneity))
        elif columnType == self.ColumnType.Acceptance:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Acceptance))
        elif columnType == self.ColumnType.Strangeness:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Strangeness))
        elif columnType == self.ColumnType.Symbols:
            return gui.createStringToolTip(world.culture().description(traveller.Culture.Element.Symbols))
        elif columnType == self.ColumnType.Nobilities:
            lines = []
            lineColours = {}
            nobilities = world.nobilities()
            for nobilityType in nobilities:
                nobilityDescription = traveller.Nobilities.description(nobilityType)
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
            allegiance = traveller.AllegianceManager.instance().allegianceName(
                milieu=self._milieu,
                code=world.allegiance(),
                sectorName=world.sectorName())
            if allegiance:
                return gui.createStringToolTip(allegiance)
        elif columnType == self.ColumnType.Sophont:
            lines = []
            remarks = world.remarks()
            for sophont in remarks.sophonts():
                percentage = remarks.sophontPercentage(sophont)
                sophont += f' ({percentage}%)'
                lines.append(sophont)
            if lines:
                return gui.createListToolTip(
                    title='Sophonts:',
                    strings=lines)
        elif columnType == self.ColumnType.TradeCodes:
            lines = []
            for tradeCode in world.tradeCodes():
                lines.append(traveller.tradeCodeName(tradeCode=tradeCode))
            if lines:
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
                spectralClass = f'Spectral Class: {star.code(traveller.Star.Element.SpectralClass)} - {star.description(traveller.Star.Element.SpectralClass)}'
                spectralScale = f'Spectral Scale: {star.code(traveller.Star.Element.SpectralScale)} - {star.description(traveller.Star.Element.SpectralScale)}'
                luminosityClass = f'Luminosity Class: {star.code(traveller.Star.Element.LuminosityClass)} - {star.description(traveller.Star.Element.LuminosityClass)}'
                lines.append(spectralClass)
                lines.append(spectralScale)
                lines.append(luminosityClass)

                # There could be collisions when adding to dicts in the following code as multiple
                # stars can have the same spectral/luminosity text. This isn't an issue though as
                # the mapping value will always be the same for a given piece of text
                lineIndents[spectralClass] = 1
                lineIndents[spectralScale] = 1
                lineIndents[luminosityClass] = 1

                tagLevel = self._worldTagging.calculateSpectralTagLevel(star=star) if self._worldTagging else None
                if tagLevel:
                    lineColours[spectralClass] = self._taggingColour(level=tagLevel)

                tagLevel = self._worldTagging.calculateLuminosityTagLevel(star=star) if self._worldTagging else None
                if tagLevel:
                    lineColours[luminosityClass] = self._taggingColour(level=tagLevel)

            if lines:
                return gui.createListToolTip(
                    title=f'Stars: {stellar.string()}',
                    strings=lines,
                    stringColours=lineColours,
                    stringIndents=lineIndents)
        elif columnType == self.ColumnType.PopulationCount:
            if world.population() >= 0:
                return None
            return gui.createStringToolTip(string='Unknown')
        elif columnType == self.ColumnType.PopulationMultiplier:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.PopulationMultiplier))
        elif columnType == self.ColumnType.PlanetoidBeltCount:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.PlanetoidBelts))
        elif columnType == self.ColumnType.GasGiantCount:
            return gui.createStringToolTip(world.pbg().description(element=traveller.PBG.Element.GasGiants))
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
        elif columnType == self.ColumnType.OwnerWorld:
            if world.hasOwner():
                try:
                    ownerWorld = traveller.WorldManager.instance().worldBySectorHex(
                        milieu=self._milieu,
                        sectorHex=world.ownerSectorHex())
                except Exception:
                    ownerWorld = None

                if ownerWorld:
                    if self._hexTooltipProvider:
                        return self._hexTooltipProvider.tooltip(hex=ownerWorld.hex())
                    else:
                        return traveller.WorldManager.instance().canonicalHexName(
                            milieu=ownerWorld.milieu(),
                            hex=ownerWorld.hex())
                else:
                    return gui.createStringToolTip(f'Unknown world at {world.ownerSectorHex()}')
        elif columnType == self.ColumnType.ColonyWorlds:
            if world.hasColony():
                listStrings = []
                listColours = {}
                for colonySectorHex in world.colonySectorHexes():
                    try:
                        colonyWorld = traveller.WorldManager.instance().worldBySectorHex(
                            milieu=self._milieu,
                            sectorHex=colonySectorHex)
                    except Exception:
                        colonyWorld = None

                    if colonyWorld:
                        colonyString = colonyWorld.name(includeSubsector=True)
                        listStrings.append(colonyString)
                        tagLevel = self._worldTagging.calculateWorldTagLevel(world=colonyWorld) if self._worldTagging else None
                        if tagLevel:
                            listColours[colonyString] = self._taggingColour(level=tagLevel)
                    else:
                        colonyString = f'Unknown world at {colonySectorHex}'
                        listStrings.append(colonyString)
                        listColours[colonyString] = self._taggingColour(
                            level=logic.TagLevel.Danger)
                return gui.createListToolTip(
                    title='Colony Worlds',
                    strings=listStrings,
                    stringColours=listColours)
        elif columnType == self.ColumnType.Remarks:
            remarks = world.remarks()
            return gui.createStringToolTip(remarks.string())

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
        if self._showSelectionDetailsAction:
            self._showSelectionDetailsAction.setEnabled(hasSelection)
        if self._showAllDetailsAction:
            self._showAllDetailsAction.setEnabled(hasContent)
        if self._showSelectionOnMapAction:
            self._showSelectionOnMapAction.setEnabled(hasSelection)
        if self._showAllOnMapAction:
            self._showAllOnMapAction.setEnabled(hasContent)

    def _showDetails(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showHexDetailsWindow()
        detailsWindow.addHexes(hexes=hexes)

    def _showOnMap(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
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
