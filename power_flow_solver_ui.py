
import sys
import math
import traceback
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QTabWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QTextEdit, QGroupBox,
    QSpinBox, QFileDialog, QStyledItemDelegate, QLineEdit as QLE,
    QScrollArea, QToolBar, QCheckBox, QSizePolicy, QMenu, QProgressBar
)
from PyQt6.QtGui import QIntValidator, QDoubleValidator, QAction
from PyQt6.QtCore import Qt, QDateTime, QPoint, QTimer

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

# -------------------- Delegates --------------------
class IntDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLE(parent)
        editor.setValidator(QIntValidator(-2147483648, 2147483647, editor))
        return editor

class DoubleDelegate(QStyledItemDelegate):
    def __init__(self, bottom=-1e12, top=1e12, decimals=8, parent=None):
        super().__init__(parent)
        self.bottom = bottom
        self.top = top
        self.decimals = decimals
    def createEditor(self, parent, option, index):
        editor = QLE(parent)
        validator = QDoubleValidator(self.bottom, self.top, self.decimals, editor)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        editor.setValidator(validator)
        return editor



class TypeDelegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(['Slack', 'PV', 'PQ'])
        combo.setEditable(False)
        return combo

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if val is None:
            return
        idx = editor.findText(val)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # Ensure the editor fills the entire cell rectangle.
        editor.setGeometry(option.rect)

# -------------------- Window --------------------

# -------------------- Convergence Plot Dialog --------------------
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel

class ConvergenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Convergence Monitor")
        self.setMinimumSize(480, 360)
        self.iterations = []
        self.residuals = []

        layout = QVBoxLayout()
        self.setLayout(layout)

        # matplotlib figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)

        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export CSV")
        self.close_btn = QPushButton("Close")
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.export_btn.clicked.connect(self.export_csv)
        self.close_btn.clicked.connect(self.close)

        self.info_label = QLabel("")
        layout.addWidget(self.info_label)

    def add_point(self, it, res):
        self.iterations.append(it)
        self.residuals.append(res)
        self.update_plot()

    def update_plot(self):
        try:
            self.ax.clear()
            if len(self.iterations) > 0:
                self.ax.semilogy(self.iterations, self.residuals, marker='o')
                self.ax.set_xlabel('Iteration')
                self.ax.set_ylabel('Residual (2-norm)')
                self.ax.grid(True, which='both', linestyle='--', linewidth=0.5)
                self.info_label.setText(f"Last residual: {self.residuals[-1]:.3e} (iter {self.iterations[-1]})")
            else:
                self.info_label.setText("No data yet")
            self.canvas.draw()
        except Exception:
            pass

    def export_csv(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save convergence data", filter="CSV Files (*.csv)")
            if path:
                import csv
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['iteration', 'residual'])
                    for it, r in zip(self.iterations, self.residuals):
                        writer.writerow([it, r])
        except Exception as e:
            QMessageBox.warning(self, "Export failed", str(e))

class PowerSystemUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Power Flow Solver')
        self.setMinimumSize(770, 700)
        self.resize(770, 700)

        self.last_summary = None
        self.last_businfo = None

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_deferred_resize)
        self._need_resize_contents = False

        central = QWidget()
        central.setObjectName('central_widget')
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6,6,6,6)
        main_layout.setSpacing(6)

        # toolbar
        self._build_toolbar()
        main_layout.addWidget(self.toolbar)

        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName('main_tabs')
        self.main_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tabs_scroll = QScrollArea()
        tabs_scroll.setWidgetResizable(True)
        tabs_scroll.setWidget(self.main_tabs)
        main_layout.addWidget(tabs_scroll, stretch=1)

        # build tabs
        self.dataTab = QWidget()
        self._build_data_tab()
        self.main_tabs.addTab(self.dataTab, "Data")

        self.resultsTab = QWidget()
        self._build_results_tab()
        self.main_tabs.addTab(self.resultsTab, "Results")

        self.examplesTab = QWidget()
        self._build_examples_tab()
        self.main_tabs.addTab(self.examplesTab, "Examples")

        self.helpTab = QWidget()
        self._build_help_tab()
        self.main_tabs.addTab(self.helpTab, "Help")

        # console log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)
        self.log.setPlaceholderText("Console log: status messages appear here.")
        main_layout.addWidget(self.log)

        # examples
        self.exampleCases = []
        self._init_examples()

        # apply small light stylesheet
        self._apply_light_stylesheet()
        self._apply_table_size_policies(compact=True)

        # attach context menus
        self._attach_table_context_menu(self.busTable, 'bus')
        self._attach_table_context_menu(self.branchTable, 'branch')

    # -------------------- Toolbar --------------------
    def _build_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)

        self.run_btn = QPushButton('▶ RUN')
        self.run_btn.setStyleSheet("""
            QPushButton { background-color: #d0d3d6; border: 1px solid #bdbfc1; padding:6px 12px; border-radius:6px; font-weight:bold; }
            QPushButton:pressed { background-color: #bfc3c6; }
        """)
        self.run_btn.clicked.connect(self.runFlowCallback)
        self.toolbar.addWidget(self.run_btn)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel('Solver:'))
        self.solverCombo = QComboBox()
        self.solverCombo.addItems(['NR','GS'])
        self.toolbar.addWidget(self.solverCombo)

        self.toolbar.addWidget(QLabel('Tol:'))
        self.tolEdit = QLE()
        self.tolEdit.setText('1e-10')
        self.tolEdit.setFixedWidth(120)
        self.tolEdit.setPlaceholderText('e.g. 1e-10')
        self.toolbar.addWidget(self.tolEdit)

        self.toolbar.addWidget(QLabel('MaxIt:'))
        self.maxIterSpin = QSpinBox()
        self.maxIterSpin.setRange(1,100000)
        self.maxIterSpin.setValue(100)
        self.maxIterSpin.setFixedWidth(80)
        self.toolbar.addWidget(self.maxIterSpin)

        self.toolbar.addSeparator()
        # Convergence plot toggle
        self.chkConvPlot = QCheckBox('Convergence Plot')
        self.chkConvPlot.setChecked(False)
        self.chkConvPlot.setToolTip('Show convergence plot while solving')
        self.toolbar.addWidget(self.chkConvPlot)

        self.iterLabel = QLabel('Iterations: N/A')
        self.toolbar.addWidget(self.iterLabel)

        # spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Progress

        self.status_progress = QProgressBar()
        self.status_progress.setFixedWidth(160)
        self.status_progress.setFixedHeight(14)
        self.status_progress.setRange(0,100)
        self.status_progress.setValue(0)
        self.statusBar().addPermanentWidget(self.status_progress)


    # -------------------- Data Tab --------------------
    def _build_data_tab(self):
        layout = QVBoxLayout(self.dataTab)
        layout.setContentsMargins(6,6,6,6)
        layout.setSpacing(8)

        busGroup = QGroupBox('Bus Data')
        busLayout = QVBoxLayout(busGroup)
        busLayout.setContentsMargins(6,6,6,6)
        self.busTable = QTableWidget(3,12)
        headers = ['Bus','Type','V (pu)','Phase (deg)','Pgen (MW)','Qgen (MVAr)','Pload (MW)','Qload (MVAr)','G (pu)','B (pu)','Qmin','Qmax']
        self.busTable.setHorizontalHeaderLabels(headers)
        self.busTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h = self.busTable.horizontalHeader()
        h.setDefaultSectionSize(90)
        h.setMinimumSectionSize(40)
        h.setStretchLastSection(True)
        self.busTable.verticalHeader().setVisible(False)
        self.busTable.verticalHeader().setDefaultSectionSize(28)
        self.busTable.setMinimumHeight(140)
        self.busTable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        busLayout.addWidget(self.busTable)

        initBusData = [
            [1,'Slack',1.00,0,0,0,0,0,0,0,np.nan,np.nan],
            [2,'PQ',1.00,0,0,0,0,0,0,0,np.nan,np.nan],
            [3,'PV',1.00,0,0,0,0,0,0,0,np.nan,np.nan]
        ]
        # batch fill initial rows
        self.busTable.setUpdatesEnabled(False)
        self.busTable.blockSignals(True)
        try:
            self.busTable.setRowCount(len(initBusData))
            for r,row in enumerate(initBusData):
                for c,val in enumerate(row):
                    self.busTable.setItem(r,c, QTableWidgetItem('' if pd.isna(val) else str(val)))
        finally:
            self.busTable.blockSignals(False)
            self.busTable.setUpdatesEnabled(True)

        self.busTable.setItemDelegateForColumn(0, IntDelegate(self.busTable))
        self.busTable.setItemDelegateForColumn(1, TypeDelegate(self.busTable))
        for col in [2,3,4,5,6,7,8,9,10,11]:
            self.busTable.setItemDelegateForColumn(col, DoubleDelegate(bottom=-1e9, top=1e12, decimals=8, parent=self.busTable))

        # buttons
        bbtn_layout = QHBoxLayout()
        addBusBtn = QPushButton('Add Bus')
        addBusBtn.clicked.connect(lambda: self.addRow('bus'))
        delBusBtn = QPushButton('Delete Bus')
        delBusBtn.clicked.connect(lambda: self.deleteRow('bus'))
        self.busToggleBtn = QPushButton('Advanced')
        self.busToggleBtn.setCheckable(True)
        self.busToggleBtn.clicked.connect(self.toggleBusAdvanced)
        bbtn_layout.addWidget(addBusBtn)
        bbtn_layout.addWidget(delBusBtn)
        bbtn_layout.addWidget(self.busToggleBtn)
        bbtn_layout.addStretch()
        busLayout.addLayout(bbtn_layout)
        layout.addWidget(busGroup)

        # Branch Data
        branchGroup = QGroupBox('Branch Data')
        branchLayout = QVBoxLayout(branchGroup)
        branchLayout.setContentsMargins(6,6,6,6)
        self.branchTable = QTableWidget(3,7)
        branchHeaders = ['From Bus','To Bus','R (pu)','X (pu)','Half B (pu)','Tap Ratio','Shift Angle (deg)']
        self.branchTable.setHorizontalHeaderLabels(branchHeaders)
        self.branchTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hb = self.branchTable.horizontalHeader()
        hb.setDefaultSectionSize(90)
        hb.setMinimumSectionSize(40)
        hb.setStretchLastSection(True)
        self.branchTable.verticalHeader().setVisible(False)
        self.branchTable.verticalHeader().setDefaultSectionSize(28)
        self.branchTable.setMinimumHeight(120)
        self.branchTable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        branchLayout.addWidget(self.branchTable)

        initBranchData = [
            [1,2,0.0,0.025,0.0,1.0,0.0],
            [1,3,0.0,0.05,0.0,1.0,0.0],
            [2,3,0.0,0.025,0.0,1.0,0.0]
        ]
        self.branchTable.setUpdatesEnabled(False)
        self.branchTable.blockSignals(True)
        try:
            self.branchTable.setRowCount(len(initBranchData))
            for r,row in enumerate(initBranchData):
                for c,val in enumerate(row):
                    self.branchTable.setItem(r,c,QTableWidgetItem('' if pd.isna(val) else str(val)))
        finally:
            self.branchTable.blockSignals(False)
            self.branchTable.setUpdatesEnabled(True)

        self.branchTable.setItemDelegateForColumn(0, IntDelegate(self.branchTable))
        self.branchTable.setItemDelegateForColumn(1, IntDelegate(self.branchTable))
        for col in [2,3,4,5,6]:
            self.branchTable.setItemDelegateForColumn(col, DoubleDelegate(bottom=-1e9, top=1e12, decimals=8, parent=self.branchTable))

        brbtn_layout = QHBoxLayout()
        addBranchBtn = QPushButton('Add Branch')
        addBranchBtn.clicked.connect(lambda: self.addRow('branch'))
        delBranchBtn = QPushButton('Delete Branch')
        delBranchBtn.clicked.connect(lambda: self.deleteRow('branch'))
        self.branchToggleBtn = QPushButton('Advanced')
        self.branchToggleBtn.setCheckable(True)
        self.branchToggleBtn.clicked.connect(self.toggleBranchAdvanced)
        brbtn_layout.addWidget(addBranchBtn)
        brbtn_layout.addWidget(delBranchBtn)
        brbtn_layout.addWidget(self.branchToggleBtn)
        brbtn_layout.addStretch()
        branchLayout.addLayout(brbtn_layout)
        layout.addWidget(branchGroup)

        # hide advanced columns initially
        self.advancedBusCols = [8,9,10,11]
        self.advancedBranchCols = [4,5,6]
        for c in self.advancedBusCols:
            self.busTable.setColumnHidden(c, True)
        for c in self.advancedBranchCols:
            self.branchTable.setColumnHidden(c, True)

        self.dataTab.setLayout(layout)

    # -------------------- Results Tab --------------------
    def _build_results_tab(self):
        layout = QVBoxLayout(self.resultsTab)
        layout.setContentsMargins(6,6,6,6)
        layout.setSpacing(8)

        self.results_subtabs = QTabWidget()

        # Branch results
        branchWidget = QWidget()
        b_layout = QVBoxLayout(branchWidget)
        self.resultBranchTable = QTableWidget()
        self.resultBranchTable.setMinimumHeight(140)
        self.resultBranchTable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        b_layout.addWidget(self.resultBranchTable)
        self.results_subtabs.addTab(branchWidget, 'Branch Results')

        # Bus results
        busWidget = QWidget()
        bu_layout = QVBoxLayout(busWidget)
        self.resultBusTable = QTableWidget()
        self.resultBusTable.setMinimumHeight(120)
        self.resultBusTable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bu_layout.addWidget(self.resultBusTable)
        self.results_subtabs.addTab(busWidget, 'Bus Results')

        layout.addWidget(self.results_subtabs)

        # copy/export
        action_row = QHBoxLayout()
        copy_branch_btn = QPushButton('Copy Branch CSV')
        copy_branch_btn.clicked.connect(lambda: self.copy_table_to_clipboard(self.resultBranchTable))
        export_branch_btn = QPushButton('Export Branch CSV')
        export_branch_btn.clicked.connect(lambda: self.export_table_to_file(self.resultBranchTable, 'csv'))
        copy_bus_btn = QPushButton('Copy Bus CSV')
        copy_bus_btn.clicked.connect(lambda: self.copy_table_to_clipboard(self.resultBusTable))
        export_bus_btn = QPushButton('Export Bus CSV')
        export_bus_btn.clicked.connect(lambda: self.export_table_to_file(self.resultBusTable, 'csv'))
        action_row.addWidget(copy_branch_btn)
        action_row.addWidget(export_branch_btn)
        action_row.addStretch()
        action_row.addWidget(copy_bus_btn)
        action_row.addWidget(export_bus_btn)
        layout.addLayout(action_row)

        self.resultsTab.setLayout(layout)
        self.resultBranchTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.resultBusTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    # -------------------- Examples & Help --------------------
    def _build_examples_tab(self):
        layout = QVBoxLayout(self.examplesTab)
        layout.addWidget(QLabel('Select and load example cases:'))
        self.exampleCombo = QComboBox()
        layout.addWidget(self.exampleCombo)
        loadBtn = QPushButton('Load Example into Data Tab')
        loadBtn.clicked.connect(self.loadExampleCallback)
        layout.addWidget(loadBtn)
        layout.addStretch()
        self.examplesTab.setLayout(layout)

    def _build_help_tab(self):
        layout = QVBoxLayout(self.helpTab)
        helpText = QTextEdit()
        helpText.setReadOnly(True)
        helpText.setPlainText(
            "Power Flow UI — Help\n\n"
            "Data tab: Enter bus and branch data. Type must be Slack/PV/PQ.\n"
            "Use Add/Delete to manage rows; advanced fields are hidden by default.\n\n"
            "Toolbar: Run solver (NR/GS), set tolerance and max iterations.\n"
            "Results tab: Branch and Bus results are separated into subtabs.\n"
            "Created by: Jasper\n\n"
        )
        layout.addWidget(helpText)
        self.helpTab.setLayout(layout)

    # -------------------- Table helpers --------------------
    def addRow(self, tableType):
        """Add row with minimal overhead; keep delegate for Type."""
        if tableType == 'bus':
            # close editors to avoid commit warnings
            try:
                if self.busTable.state() == self.busTable.State.EditingState:
                    it = self.busTable.currentItem()
                    if it is not None:
                        self.busTable.closePersistentEditor(it)
            except Exception:
                pass
            r = self.busTable.rowCount()
            # lightweight insert
            self.busTable.insertRow(r)
            self.busTable.setRowHeight(r, self.busTable.verticalHeader().defaultSectionSize())
            defaults = [r+1, 'PQ', 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, '', '']
            self.busTable.setUpdatesEnabled(False)
            self.busTable.blockSignals(True)
            try:
                for c,val in enumerate(defaults):
                    self.busTable.setItem(r, c, QTableWidgetItem(str(val)))
            finally:
                self.busTable.blockSignals(False)
                self.busTable.setUpdatesEnabled(True)
            self.log_append(f'Added bus row #{r+1}')
        else:
            try:
                if self.branchTable.state() == self.branchTable.State.EditingState:
                    it = self.branchTable.currentItem()
                    if it is not None:
                        self.branchTable.closePersistentEditor(it)
            except Exception:
                pass
            r = self.branchTable.rowCount()
            self.branchTable.insertRow(r)
            self.branchTable.setRowHeight(r, self.branchTable.verticalHeader().defaultSectionSize())
            defaults = [1,2,0.01,0.05,0.0,1.0,0.0]
            self.branchTable.setUpdatesEnabled(False)
            self.branchTable.blockSignals(True)
            try:
                for c,val in enumerate(defaults):
                    self.branchTable.setItem(r,c,QTableWidgetItem(str(val)))
            finally:
                self.branchTable.blockSignals(False)
                self.branchTable.setUpdatesEnabled(True)
            self.log_append(f'Added branch row #{r+1}')

        self._need_resize_contents = True
        # lightweight adjust
        self.adjust_table_columns(self.busTable)
        self.adjust_table_columns(self.branchTable)

    def deleteRow(self, tableType):
        reply = QMessageBox.question(self, 'Confirm delete', 'Delete last row? This cannot be undone.',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if tableType == 'bus':
            r = self.busTable.rowCount()
            if r > 0:
                self.busTable.removeRow(r-1)
                self.log_append(f'Removed bus row #{r}')
        else:
            r = self.branchTable.rowCount()
            if r > 0:
                self.branchTable.removeRow(r-1)
                self.log_append(f'Removed branch row #{r}')
        self._need_resize_contents = True
        self.adjust_table_columns(self.busTable)
        self.adjust_table_columns(self.branchTable)

    def toggleBusAdvanced(self):
        show = self.busToggleBtn.isChecked()
        for c in self.advancedBusCols:
            self.busTable.setColumnHidden(c, not show)
        self.busToggleBtn.setText('Hide' if show else 'Advanced')
        self._need_resize_contents = True
        self.adjust_table_columns(self.busTable)

    def toggleBranchAdvanced(self):
        show = self.branchToggleBtn.isChecked()
        for c in self.advancedBranchCols:
            self.branchTable.setColumnHidden(c, not show)
        self.branchToggleBtn.setText('Hide' if show else 'Advanced')
        self._need_resize_contents = True
        self.adjust_table_columns(self.branchTable)

    def loadExampleCallback(self):
        idx = self.exampleCombo.currentIndex()
        if idx < 0 or idx >= len(self.exampleCases):
            return
        ex = self.exampleCases[idx]
        bus = ex['bus']
        br = ex['branch']

        self.busTable.setUpdatesEnabled(False)
        self.busTable.blockSignals(True)
        try:
            self.busTable.setRowCount(len(bus))
            for r,row in enumerate(bus):
                for c,val in enumerate(row):
                    self.busTable.setItem(r, c, QTableWidgetItem('' if pd.isna(val) else str(val)))
                self.busTable.setRowHeight(r, self.busTable.verticalHeader().defaultSectionSize())
        finally:
            self.busTable.blockSignals(False)
            self.busTable.setUpdatesEnabled(True)

        self.branchTable.setUpdatesEnabled(False)
        self.branchTable.blockSignals(True)
        try:
            self.branchTable.setRowCount(len(br))
            for r,row in enumerate(br):
                for c,val in enumerate(row):
                    self.branchTable.setItem(r,c,QTableWidgetItem('' if pd.isna(val) else str(val)))
                self.branchTable.setRowHeight(r, self.branchTable.verticalHeader().defaultSectionSize())
        finally:
            self.branchTable.blockSignals(False)
            self.branchTable.setUpdatesEnabled(True)

        self.main_tabs.setCurrentWidget(self.dataTab)
        self.log_append(f'Loaded example: {ex["name"]}')
        self._need_resize_contents = True
        self.adjust_table_columns(self.busTable)
        self.adjust_table_columns(self.branchTable)

    # -------------------- Run / Validation / Results --------------------
    def runFlowCallback(self):
        # update both progress bars (toolbar and status) so one is visible in small windows
        def set_progress(v):
            try:
                # Only update status progress bar (top progress removed)
                self.status_progress.setValue(v)
                QApplication.processEvents()
            except Exception:
                pass

        set_progress(5)

        try:
            tol_text = self.tolEdit.text().strip()
            if tol_text == '':
                raise ValueError('Tolerance must be provided (e.g. 1e-10)')
            tolVal = float(tol_text)
            if tolVal <= 0:
                raise ValueError('Tolerance must be positive')
        except Exception as e:
            QMessageBox.critical(self, 'Input Error', f'Tolerance error: {e}')
            set_progress(0)
            return

        try:
            maxIterVal = int(self.maxIterSpin.value())
            if maxIterVal <= 0:
                raise ValueError('Max Iter must be positive integer')
        except Exception as e:
            QMessageBox.critical(self, 'Input Error', str(e))
            set_progress(0)
            return

        solver = self.solverCombo.currentText()
        try:
            busData, ok = self.validateBusData()
            if not ok:
                set_progress(0)
                return
            branchData, okb = self.validateBranchData(busData['Bus'])
            if not okb:
                set_progress(0)
                return

            self.log_append(f'Running {solver} solver (tol={tolVal}, maxIter={maxIterVal}).')
            set_progress(20)

            # show convergence monitor (only if enabled)
            try:
                if getattr(self, 'chkConvPlot', None) is not None and not self.chkConvPlot.isChecked():
                    conv = None
                else:
                    conv = ConvergenceDialog(self)
                    conv.show()
            except Exception:
                conv = None

            def _conv_cb(it, res):
                try:
                    if conv is not None:
                        conv.add_point(it, res)
                    QApplication.processEvents()
                except Exception:
                    pass

            if solver == 'NR':
                summary, businfo, iters, residuals = computePowerFlow_NR(busData, branchData, tolVal, maxIterVal, progress_callback=_conv_cb)
            else:
                summary, businfo, iters, residuals = computePowerFlow_GS(busData, branchData, tolVal, maxIterVal, progress_callback=_conv_cb)

            self.last_summary = summary.copy()
            self.last_businfo = businfo.copy()

            # log final residual if available
            try:
                if residuals and len(residuals) > 0:
                    self.log_append(f'Final residual after {iters} iterations: {residuals[-1]:.3e}')
            except Exception:
                pass

            self._populate_result_table(self.resultBranchTable, summary, table_type='branch')
            self._populate_result_table(self.resultBusTable, businfo, table_type='bus')
            self.iterLabel.setText(f'Iterations: {iters}')
            self.log_append(f'Solver finished — iterations: {iters}')
            set_progress(80)

            self.adjust_table_columns(self.resultBranchTable)
            self.adjust_table_columns(self.resultBusTable)

            self.main_tabs.setCurrentWidget(self.resultsTab)

            set_progress(100)
            QTimer.singleShot(300, lambda: set_progress(0))

        except Exception as e:
            QMessageBox.critical(self, 'Power Flow Error', str(e))
            self.log_append(f'Error: {e}')
            self.log_append(traceback.format_exc())
            set_progress(0)

    def _populate_result_table(self, tableWidget, df: pd.DataFrame, table_type: str = 'branch'):
        tableWidget.clear()
        if df is None or df.empty:
            tableWidget.setRowCount(0)
            tableWidget.setColumnCount(0)
            return

        branch_units = {'Pij': 'MW', 'Qij': 'MVAr', 'Pji': 'MW', 'Qji': 'MVAr', 'P_loss': 'MW', 'Q_loss': 'MVAr'}
        bus_units = {'V': 'pu', 'Phase': 'deg', 'Pgen': 'MW', 'Qgen': 'MVAr', 'Pload': 'MW',
                     'Qload': 'MVAr', 'Qinj': 'MVAr', 'Pbus_loss': 'MW'}

        headers = list(df.columns)
        tableWidget.setUpdatesEnabled(False)
        tableWidget.blockSignals(True)
        try:
            tableWidget.setColumnCount(len(headers))
            tableWidget.setRowCount(len(df.index))
            tableWidget.setHorizontalHeaderLabels(headers)

            def display_text(val, colname):
                if pd.isna(val):
                    return ''
                if isinstance(val, (float, np.floating, int, np.integer, np.complexfloating)):
                    if isinstance(val, complex):
                        val = val.real
                    unit = branch_units.get(colname) if table_type == 'branch' else bus_units.get(colname)
                    if unit:
                        return f'{val:.6g} {unit}'
                    return f'{val:.6g}'
                else:
                    return str(val)

            for r in range(len(df.index)):
                for c, colname in enumerate(headers):
                    val = df.iat[r, c]
                    text = display_text(val, colname)
                    item = QTableWidgetItem(text)
                    if isinstance(val, (float, int, np.floating, np.integer)) and not pd.isna(val):
                        item.setData(Qt.ItemDataRole.UserRole, float(val))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    else:
                        item.setData(Qt.ItemDataRole.UserRole, None)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    tableWidget.setItem(r, c, item)
        finally:
            tableWidget.blockSignals(False)
            tableWidget.setUpdatesEnabled(True)

        tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._need_resize_contents = True
        # lightweight adjust
        self.adjust_table_columns(tableWidget)

    # -------------------- Validation --------------------
    def validateBusData(self):
        rows = self.busTable.rowCount()
        if rows == 0:
            QMessageBox.critical(self, 'Validation Error', 'Bus table is empty!')
            return None, False
        Bus=[]; Type=[]; V=[]; Phase=[]; Pgen=[]; Qgen=[]
        Pload=[]; Qload=[]; G=[]; B=[]; Qmin=[]; Qmax=[]
        busNums=[]
        for i in range(rows):
            try:
                b = self._get_cell_numeric(self.busTable, i, 0, required=True, integer=True)
                t = self._get_cell_text(self.busTable, i, 1, required=True)
                v = self._get_cell_numeric(self.busTable, i, 2, required=False, default=np.nan)
                phase = self._get_cell_numeric(self.busTable, i, 3, required=False, default=0.0)
                pgen = self._get_cell_numeric(self.busTable, i, 4, required=False, default=0.0)
                qgen = self._get_cell_numeric(self.busTable, i, 5, required=False, default=0.0)
                pload = self._get_cell_numeric(self.busTable, i, 6, required=False, default=0.0)
                qload = self._get_cell_numeric(self.busTable, i, 7, required=False, default=0.0)
                g = self._get_cell_numeric(self.busTable, i, 8, required=False, default=0.0)
                bb = self._get_cell_numeric(self.busTable, i, 9, required=False, default=0.0)
                qmin = self._get_cell_numeric(self.busTable, i, 10, required=False, default=np.nan)
                qmax = self._get_cell_numeric(self.busTable, i, 11, required=False, default=np.nan)
            except ValueError as e:
                QMessageBox.critical(self, 'Validation Error', str(e))
                return None, False

            validTypes = ['Slack','PV','PQ']
            if t not in validTypes:
                QMessageBox.critical(self, 'Validation Error', f'Invalid bus type (row {i+1}) — must be one of {validTypes}')
                return None, False
            if not np.isnan(v) and v <= 0:
                QMessageBox.critical(self, 'Validation Error', f'Voltage ≤ 0 (row {i+1})')
                return None, False

            Bus.append(int(b))
            Type.append(t)
            V.append(float(v) if not np.isnan(v) else np.nan)
            Phase.append(float(phase))
            Pgen.append(float(pgen))
            Qgen.append(float(qgen))
            Pload.append(float(pload))
            Qload.append(float(qload))
            G.append(float(g))
            B.append(float(bb))
            Qmin.append(float(qmin) if not np.isnan(qmin) else np.nan)
            Qmax.append(float(qmax) if not np.isnan(qmax) else np.nan)
            busNums.append(int(b))

        if len(set(busNums)) != len(busNums):
            QMessageBox.critical(self, 'Validation Error', 'Bus numbers must be unique!')
            return None, False

        busData = {
            'Bus': np.array(Bus),'Type': np.array(Type),'V': np.array(V),'Phase': np.array(Phase),
            'Pgen': np.array(Pgen),'Qgen': np.array(Qgen),'Pload': np.array(Pload),'Qload': np.array(Qload),
            'G': np.array(G),'B': np.array(B),'Qmin': np.array(Qmin),'Qmax': np.array(Qmax)
        }
        return busData, True

    def validateBranchData(self, validBuses):
        rows = self.branchTable.rowCount()
        if rows == 0:
            QMessageBox.critical(self, 'Validation Error', 'Branch table is empty!')
            return None, False
        bus_i=[]; bus_j=[]; R=[]; X=[]; half_B=[]; Tap=[]; Shift=[]
        for i in range(rows):
            try:
                bi = self._get_cell_numeric(self.branchTable, i, 0, required=True, integer=True)
                bj = self._get_cell_numeric(self.branchTable, i, 1, required=True, integer=True)
                r = self._get_cell_numeric(self.branchTable, i, 2, required=True, default=0.0)
                x = self._get_cell_numeric(self.branchTable, i, 3, required=True, default=0.0)
                hb = self._get_cell_numeric(self.branchTable, i, 4, required=False, default=0.0)
                tap = self._get_cell_numeric(self.branchTable, i, 5, required=False, default=1.0)
                shift = self._get_cell_numeric(self.branchTable, i, 6, required=False, default=0.0)
            except ValueError as e:
                QMessageBox.critical(self, 'Validation Error', str(e))
                return None, False

            if bi not in validBuses:
                QMessageBox.critical(self, 'Validation Error', f'Invalid From Bus (row {i+1})')
                return None, False
            if bj not in validBuses:
                QMessageBox.critical(self, 'Validation Error', f'Invalid To Bus (row {i+1})')
                return None, False
            if bi == bj:
                QMessageBox.critical(self, 'Validation Error', f'No self-loop (row {i+1})')
                return None, False

            if np.isclose(r,0.0) and np.isclose(x,0.0):
                QMessageBox.critical(self, 'Validation Error', f'Branch #{i+1} has zero impedance (R==0 and X==0). Set non-zero R or X.')
                return None, False

            if r < 0:
                QMessageBox.warning(self, 'Warning', f'Branch #{i+1} has negative resistance (R < 0). Proceed only if intentional.')
                self.log_append(f'Warning: negative R on branch row {i+1}')
            if x < 0:
                QMessageBox.warning(self, 'Warning', f'Branch #{i+1} has negative reactance (X < 0). Proceed only if intentional.')
                self.log_append(f'Warning: negative X on branch row {i+1}')

            bus_i.append(int(bi)); bus_j.append(int(bj)); R.append(float(r)); X.append(float(x))
            half_B.append(float(hb)); Tap.append(float(tap)); Shift.append(float(shift))

        branchData = {
            'bus_i': np.array(bus_i),'bus_j': np.array(bus_j),'R': np.array(R),'X': np.array(X),
            'half_B': np.array(half_B),'Tap': np.array(Tap),'Shift': np.array(Shift)
        }
        return branchData, True

    def _get_cell_text(self, table, r, c, required=False):
        item = table.item(r,c)
        if item is None or item.text().strip() == '':
            if required:
                raise ValueError(f'Missing value at row {r+1}, col {c+1}')
            return ''
        return item.text().strip()

    def _get_cell_numeric(self, table, r, c, required=False, integer=False, default=np.nan):
        item = table.item(r,c)
        if item is None or item.text().strip() == '':
            if required:
                raise ValueError(f'Missing value at row {r+1}, col {c+1}')
            return default
        txt = item.text().strip()
        try:
            if integer:
                return int(float(txt))
            return float(txt)
        except Exception:
            raise ValueError(f'Invalid numeric value at row {r+1}, col {c+1}')

    def tablewidget_to_dataframe(self, table: QTableWidget) -> pd.DataFrame:
        if table.columnCount() == 0:
            return pd.DataFrame()
        cols = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        rows = []
        for r in range(table.rowCount()):
            row = []
            for c in range(table.columnCount()):
                item = table.item(r,c)
                if item is None:
                    row.append(np.nan)
                    continue
                raw = item.data(Qt.ItemDataRole.UserRole)
                if raw is not None:
                    row.append(raw)
                else:
                    txt = item.text()
                    try:
                        val = float(txt.split()[0])
                        row.append(val)
                    except Exception:
                        row.append(txt if txt != '' else np.nan)
            rows.append(row)
        return pd.DataFrame(rows, columns=cols)

    def export_table_to_file(self, table: QTableWidget, fmt: str = 'csv'):
        df = self.tablewidget_to_dataframe(table)
        if df.empty:
            QMessageBox.information(self, 'Export', 'No data to export.')
            return
        if fmt == 'csv':
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv);;All Files (*)")
            if path:
                try:
                    df.to_csv(path, index=False)
                    QMessageBox.information(self, 'Export', f'CSV saved to:\n{path}')
                    self.log_append(f'Exported CSV: {path}')
                except Exception as e:
                    QMessageBox.critical(self, 'Export Error', str(e))

    def copy_table_to_clipboard(self, table: QTableWidget):
        df = self.tablewidget_to_dataframe(table)
        if df.empty:
            QMessageBox.information(self, 'Copy', 'No data to copy.')
            return
        csv = df.to_csv(index=False)
        QApplication.clipboard().setText(csv)
        QMessageBox.information(self, 'Copy', 'Table copied to clipboard (CSV format).')
        self.log_append('Table copied to clipboard (CSV).')

    def clear_results(self):
        self.resultBranchTable.clear()
        self.resultBusTable.clear()
        self.last_summary = None
        self.last_businfo = None
        self.log_append('Results cleared.')
        self.iterLabel.setText('Iterations: N/A')

    def _apply_table_size_policies(self, compact: bool = True):
        if compact:
            default_section = 90
            min_section = 40
            bus_min_h = 140
            branch_min_h = 120
            result_min_h_branch = 140
            result_min_h_bus = 120
        else:
            default_section = 120
            min_section = 60
            bus_min_h = 260
            branch_min_h = 220
            result_min_h_branch = 220
            result_min_h_bus = 180

        h = self.busTable.horizontalHeader()
        h.setDefaultSectionSize(default_section)
        h.setMinimumSectionSize(min_section)
        self.busTable.setMinimumHeight(bus_min_h)

        hb = self.branchTable.horizontalHeader()
        hb.setDefaultSectionSize(default_section)
        hb.setMinimumSectionSize(min_section)
        self.branchTable.setMinimumHeight(branch_min_h)

        self.resultBranchTable.setMinimumHeight(result_min_h_branch)
        self.resultBusTable.setMinimumHeight(result_min_h_bus)

        self.busTable.resizeColumnsToContents()
        self.branchTable.resizeColumnsToContents()

    def adjust_table_columns(self, table: QTableWidget, force_contents_resize: bool = False):
        if table is None or table.columnCount() == 0:
            return
        header = table.horizontalHeader()

        if force_contents_resize or self._need_resize_contents:
            header.blockSignals(True)
            table.setUpdatesEnabled(False)
            try:
                table.resizeColumnsToContents()
            finally:
                table.setUpdatesEnabled(True)
                header.blockSignals(False)
            self._need_resize_contents = False

        try:
            viewport_w = max(200, table.viewport().width() or table.width())
            total = sum(table.columnWidth(c) for c in range(table.columnCount()))
        except Exception:
            return

        if total > viewport_w:
            for c in range(table.columnCount()):
                header.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        else:
            for c in range(table.columnCount()):
                header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self._resize_timer.start(300)
        except Exception:
            pass

    def _on_deferred_resize(self):
        try:
            for tbl in (getattr(self, 'busTable', None),
                        getattr(self, 'branchTable', None),
                        getattr(self, 'resultBranchTable', None),
                        getattr(self, 'resultBusTable', None)):
                if tbl is None:
                    continue
                if not tbl.isVisible():
                    continue
                self.adjust_table_columns(tbl, force_contents_resize=False)
        except Exception:
            pass

    def _attach_table_context_menu(self, table: QTableWidget, table_type: str):
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, t=table, tt=table_type: self._show_table_context_menu(t, tt, pos))

    def _show_table_context_menu(self, table: QTableWidget, table_type: str, pos: QPoint):
        menu = QMenu()
        add_act = QAction('Add row', self)
        add_act.triggered.connect(lambda: self.addRow('bus' if table_type == 'bus' else 'branch'))
        menu.addAction(add_act)
        del_act = QAction('Delete last row', self)
        del_act.triggered.connect(lambda: self.deleteRow('bus' if table_type == 'bus' else 'branch'))
        menu.addAction(del_act)
        copy_act = QAction('Copy table (CSV)', self)
        copy_act.triggered.connect(lambda: self.copy_table_to_clipboard(table))
        menu.addAction(copy_act)
        export_act = QAction('Export as CSV...', self)
        export_act.triggered.connect(lambda: self.export_table_to_file(table, 'csv'))
        menu.addAction(export_act)
        menu.exec(table.mapToGlobal(pos))

    def log_append(self, msg: str):
        ts = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.log.append(f'[{ts}] {msg}')

    def _apply_light_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow#central_widget, QWidget#central_widget { background-color: #ffffff; }
            QMainWindow { background-color: #ffffff; color: #222; }
            QWidget { color: #222; background-color: #ffffff; }
            QTabWidget::pane { background: #ffffff; border: 1px solid #e6e6e6; }
            QGroupBox { font-weight: bold; border: 1px solid #d0d0d0; margin-top: 8px; background: #ffffff; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; }
            QTableWidget { background: #ffffff; gridline-color: #eaeaea; }
            QHeaderView::section { background: #f5f5f5; padding: 4px; border: 1px solid #e6e6e6; }
            QPushButton { background: #f0f0f0; color: #222; border-radius: 6px; padding: 6px; }
            QPushButton:pressed { background: #e0e0e0; }
            QLabel { color: #222; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { background: #ffffff; color: #222; border: 1px solid #d0d0d0; padding: 3px; }
            QToolBar { background: #ffffff; spacing: 8px; border-bottom: 1px solid #e6e6e6; }
            QScrollBar:vertical { background: #f7f7f7; width: 12px; margin: 0px; }
            QScrollBar::handle:vertical { background: #d6d6d6; min-height: 20px; border-radius: 6px; }
            QScrollBar:horizontal { background: #f7f7f7; height: 12px; margin: 0px; }
            QScrollBar::handle:horizontal { background: #d6d6d6; min-width: 20px; border-radius: 6px; }
        """)

    def _init_examples(self):
        ex1_bus = [
            [1, 'Slack', 1.025, 0, 0, 0, 0, 0, 0, 0, np.nan, np.nan],
            [2, 'PQ',    1.0,   0, 0, 0, 400, 200, 0, 0, np.nan, np.nan],
            [3, 'PV',    1.03,  0, 300, 0, 0, 0, 0, 0, np.nan, np.nan]
        ]
        ex1_branch = [
            [1,2,0.0,0.025,0.0,1.0,0.0],
            [1,3,0.0,0.05, 0.0,1.0,0.0],
            [2,3,0.0,0.025,0.0,1.0,0.0]
        ]
        ex2_bus = [
            [1, 'Slack', 1.00, 0,  0, 0,  0,  0, 0, 0, np.nan, np.nan],
            [2, 'PV',    1.02, 0, 40, 0, 10,  5, 0, 0,  -20, 75],
            [3, 'PQ',    1.00, 0,  0, 0, 60, 20, 0, 0, np.nan, np.nan],
            [4, 'PQ',    1.00, 0,  0, 0, 20, 10, 0, 0, np.nan, np.nan]
        ]
        ex2_branch = [
            [1, 2, 0.01,  0.03,  0.02, 1, 0],
            [1, 3, 0.02,  0.04,  0.01, 1, 0],
            [2, 3, 0.012, 0.036, 0.015, 1, 0],
            [2, 4, 0.015, 0.045,  0.02, 1, 0],
            [3, 4, 0.01,  0.03, 0.025, 1, 0]
        ]
        ex3_bus = [
            [1, 'Slack', 1.0, 0, 0, 0, 0, 0, 0, 0, np.nan, np.nan],
            [2, 'PQ',    np.nan, np.nan, 0, 0, 100, 50, 0, 0, np.nan, np.nan]
        ]
        ex3_branch = [[1,2,0.12,0.16,0.0,1.0,0.0]]

        self.exampleCases = [
            {'name': '3-Bus System', 'bus': ex1_bus, 'branch': ex1_branch},
            {'name': '4-Bus System', 'bus': ex2_bus, 'branch': ex2_branch},
            {'name': '2-Bus System', 'bus': ex3_bus, 'branch': ex3_branch},
        ]
        try:
            self.exampleCombo.clear()
            for ex in self.exampleCases:
                self.exampleCombo.addItem(ex['name'])
        except Exception:
            pass

# -------------------- Solvers (full implementations) --------------------
def computePowerFlow_NR(busData: dict, branchData: dict, tol: float, maxIter: int, progress_callback=None):
    Bus = np.array(busData['Bus'], dtype=int)
    order = np.argsort(Bus)
    Bus = Bus[order]
    Type = np.array(busData['Type'])[order]
    V_init = np.array(busData['V'])[order]
    Phase_deg_init = np.array(busData['Phase'])[order]
    Pgen = np.array(busData['Pgen'])[order]
    Qgen = np.array(busData['Qgen'])[order]
    Pload = np.array(busData['Pload'])[order]
    Qload = np.array(busData['Qload'])[order]
    G = np.array(busData['G'])[order]
    B_sh = np.array(busData['B'])[order]
    Qmin = np.array(busData['Qmin'])[order]
    Qmax = np.array(busData['Qmax'])[order]

    bi_arr = np.array(branchData['bus_i'], dtype=int)
    bj_arr = np.array(branchData['bus_j'], dtype=int)
    R = np.array(branchData['R'], dtype=float)
    X = np.array(branchData['X'], dtype=float)
    half_B = np.array(branchData['half_B'], dtype=float)
    Tap = np.array(branchData['Tap'], dtype=float)
    Shift = np.array(branchData['Shift'], dtype=float)

    bus_to_idx = {bus: idx for idx, bus in enumerate(Bus)}
    N = len(Bus)
    residuals = []
    S_base = 100.0

    zero_taps = np.where(Tap == 0)[0]
    if zero_taps.size > 0:
        Tap[zero_taps] = 1.0

    z_all = R + 1j * X
    zero_z_idx = np.where(np.isclose(z_all, 0.0))[0]
    if zero_z_idx.size > 0:
        k = int(z_all.size and zero_z_idx[0])
        raise RuntimeError(
            f'Invalid branch data: branch #{k+1} has zero impedance (R==0 and X==0). '
            'Set a non-zero X (and/or R).'
        )

    # Build Ybus safely
    Y = np.zeros((N, N), dtype=complex)
    for k in range(len(bi_arr)):
        bi = int(bi_arr[k]); bj = int(bj_arr[k])
        i = bus_to_idx[bi]; j = bus_to_idx[bj]
        a = Tap[k]
        shift_rad = math.radians(Shift[k])
        a_exp = a * np.exp(1j * shift_rad)
        z = R[k] + 1j * X[k]
        Y[i, j] -= 1.0 / (np.conj(a_exp) * z)
        Y[j, i] -= 1.0 / (a_exp * z)
        Y[i, i] += 1.0 / (a ** 2 * z) + 1j * half_B[k]
        Y[j, j] += 1.0 / (z) + 1j * half_B[k]

    for k in range(N):
        Y[k, k] += G[k] + 1j * B_sh[k]

    V = np.array(V_init, dtype=float)
    Phase = np.radians(Phase_deg_init)
    V = np.where(np.isnan(V), 1.0, V)
    Phase = np.where(np.isnan(Phase), 0.0, Phase)

    isPQ = (Type == 'PQ')
    isPV = (Type == 'PV')
    isSlack = (Type == 'Slack')
    Log_load = isPQ
    Log_pv_load = isPV | Log_load

    P_variable_buses = Bus[Log_pv_load]
    Q_variable_buses = Bus[Log_load]

    P_sch = (Pgen - Pload) / S_base
    Q_sch = (Qgen - Qload) / S_base

    if P_variable_buses.size == 0 and Q_variable_buses.size == 0:
        S_network = np.zeros(N, dtype=complex)
        rows = []
        for k in range(len(bi_arr)):
            bi = int(bi_arr[k]); bj = int(bj_arr[k])
            i = bus_to_idx[bi]; j = bus_to_idx[bj]
            a = Tap[k]; shift_rad = math.radians(Shift[k])
            a_exp = a * np.exp(1j * shift_rad)
            Vi = V[i] * np.exp(1j * Phase[i])
            Vj = V[j] * np.exp(1j * Phase[j])
            Rk = R[k]; Xk = X[k]
            y = 1.0 / (Rk + 1j * Xk)
            if abs(shift_rad) > 1e-12:
                Iij = -(y / np.conj(a_exp)) * Vj + (y / (a ** 2)) * Vi
                Iji = y * Vj - (y / a_exp) * Vi
                Sij = Vi * np.conjugate(Iij) * S_base
                Sji = Vj * np.conjugate(Iji) * S_base
            else:
                Mid = y / a
                Half_i = 1j * half_B[k] + y * (1 - a) / (a ** 2)
                Half_j = 1j * half_B[k] + y * (a - 1) / a
                Iij_line = (Vi - Vj) * Mid
                Ii0 = Half_i * Vi
                Iij = Iij_line + Ii0
                Sij_line = Vi * np.conjugate(Iij_line) * S_base
                Si0 = Vi * np.conjugate(Ii0) * S_base
                Sij = Sij_line + Si0
                Iji_line = (Vj - Vi) * Mid
                Ij0 = Half_j * Vj
                Iji = Iji_line + Ij0
                Sji_line = Vj * np.conjugate(Iji_line) * S_base
                Sj0 = Vj * np.conjugate(Ij0) * S_base
                Sji = Sji_line + Sj0

            S_network[i] += Sij
            S_network[j] += Sji

            Ploss = (np.real(Sij) + np.real(Sji))
            Qloss = (np.imag(Sij) + np.imag(Sji))
            rows.append({'i': bi, 'j': bj, 'Pij': np.real(Sij), 'Qij': np.imag(Sij),
                         'Pji': np.real(Sji), 'Qji': np.imag(Sji), 'P_loss': Ploss, 'Q_loss': Qloss})

        summary = pd.DataFrame(rows)
        totals = {'i': np.nan, 'j': np.nan, 'Pij': np.nan, 'Qij': np.nan, 'Pji': np.nan, 'Qji': np.nan,
                  'P_loss': summary['P_loss'].sum() if not summary.empty else 0.0,
                  'Q_loss': summary['Q_loss'].sum() if not summary.empty else 0.0}
        summary = pd.concat([summary, pd.DataFrame([totals])], ignore_index=True)

        Q_injected = S_base * B_sh * (V ** 2)
        P_bus_loss = S_base * G * (V ** 2)
        P_network = np.real(S_network)
        Q_network = np.imag(S_network)
        P_gen = P_network + Pload + P_bus_loss
        Q_gen = Q_network + Qload - Q_injected
        Phase_deg = np.degrees(Phase)
        businfo = pd.DataFrame({
            'Bus': Bus,
            'V': V,
            'Phase': Phase_deg,
            'Pgen': P_gen,
            'Qgen': Q_gen,
            'Pload': Pload,
            'Qload': Qload,
            'Qinj': Q_injected,
            'Pbus_loss': P_bus_loss
        })
        totals_bus = {'Bus': np.nan, 'V': np.nan, 'Phase': np.nan,
                      'Pgen': businfo['Pgen'].sum(), 'Qgen': businfo['Qgen'].sum(),
                      'Pload': businfo['Pload'].sum(), 'Qload': businfo['Qload'].sum(),
                      'Qinj': businfo['Qinj'].sum(), 'Pbus_loss': businfo['Pbus_loss'].sum()}
        businfo = pd.concat([businfo, pd.DataFrame([totals_bus])], ignore_index=True)
        return summary, businfo, 0, residuals

    iterCount = 0
    # NR iterations
    for outer in range(maxIter):
        iterCount = 0
        while True:
            iterCount += 1

            # Build full Jacobian pieces
            J1_full = np.zeros((N, N))
            J2_full = np.zeros((N, N))
            J3_full = np.zeros((N, N))
            J4_full = np.zeros((N, N))

            for i in range(N):
                w = x = y = zacc = 0.0
                for j in range(N):
                    if i == j:
                        continue
                    Yij = Y[i, j]
                    angleYij = np.angle(Yij)
                    absYij = np.abs(Yij)
                    J1_full[i, j] = V[i] * V[j] * absYij * np.sin(Phase[i] - Phase[j] - angleYij)
                    w += J1_full[i, j]
                    J2_full[i, j] = V[i] * absYij * np.cos(Phase[i] - Phase[j] - angleYij)
                    x += (V[j] / V[i]) * J2_full[i, j]
                    J3_full[i, j] = -V[i] * V[j] * absYij * np.cos(Phase[i] - Phase[j] - angleYij)
                    y -= J3_full[i, j]
                    J4_full[i, j] = V[i] * absYij * np.sin(Phase[i] - Phase[j] - angleYij)
                    zacc += (V[j] / V[i]) * J4_full[i, j]
                J1_full[i, i] = -w
                Yii = Y[i, i]
                J2_full[i, i] = 2 * V[i] * np.abs(Yii) * np.cos(np.angle(Yii)) + x
                J3_full[i, i] = y
                J4_full[i, i] = -2 * V[i] * np.abs(Yii) * np.sin(np.angle(Yii)) + zacc

            P_idx = [bus_to_idx[b] for b in P_variable_buses]
            Q_idx = [bus_to_idx[b] for b in Q_variable_buses]

            P_size = len(P_idx)
            Q_size = len(Q_idx)
            Delta_size = P_size
            V_size = Q_size

            J1 = np.zeros((P_size, Delta_size))
            J2 = np.zeros((P_size, V_size))
            P_cal = np.zeros(P_size)
            for ii in range(P_size):
                kBus = P_idx[ii]
                for jj in range(Delta_size):
                    J1[ii, jj] = J1_full[kBus, P_idx[jj]]
                for jj in range(V_size):
                    J2[ii, jj] = J2_full[kBus, Q_idx[jj]]
                ptemp = 0.0
                for j in range(N):
                    ptemp += V[kBus] * V[j] * np.abs(Y[kBus, j]) * np.cos(Phase[kBus] - Phase[j] - np.angle(Y[kBus, j]))
                P_cal[ii] = ptemp

            J3 = np.zeros((Q_size, Delta_size))
            J4 = np.zeros((Q_size, V_size))
            Q_cal = np.zeros(Q_size)
            for ii in range(Q_size):
                kBus = Q_idx[ii]
                for jj in range(Delta_size):
                    J3[ii, jj] = J3_full[kBus, P_idx[jj]]
                for jj in range(V_size):
                    J4[ii, jj] = J4_full[kBus, Q_idx[jj]]
                qtemp = 0.0
                for j in range(N):
                    qtemp += V[kBus] * V[j] * np.abs(Y[kBus, j]) * np.sin(Phase[kBus] - Phase[j] - np.angle(Y[kBus, j]))
                Q_cal[ii] = qtemp

            top = np.hstack([J1, J2]) if J2.size else J1
            bottom = np.hstack([J3, J4]) if J4.size else J3
            Jacobian = np.vstack([top, bottom]) if bottom.size else top

            P_vec = P_sch[Log_pv_load]
            Q_vec = Q_sch[Log_load]
            residual = np.concatenate([P_vec - P_cal, Q_vec - Q_cal]) if Q_vec.size else (P_vec - P_cal)

            # record residual norm for convergence diagnostics
            try:
                res_norm = float(np.linalg.norm(residual)) if hasattr(residual, '__len__') and np.size(residual) > 0 else 0.0
            except Exception:
                res_norm = 0.0
            residuals.append(res_norm)
            # call UI callback if provided (allows live plotting)
            if progress_callback is not None:
                try:
                    progress_callback(iterCount, res_norm)
                except Exception:
                    pass

            mismatch = None
            if Jacobian.size == 0:
                mismatch = np.zeros(0)
            else:
                try:
                    mismatch = np.linalg.solve(Jacobian, residual)
                except np.linalg.LinAlgError:
                    mismatch, *_ = np.linalg.lstsq(Jacobian, residual, rcond=None)
                    if np.linalg.norm(Jacobian @ mismatch - residual) > 1e-6:
                        raise RuntimeError('Jacobian singular/ill-conditioned in NR. Check data or initial guess.')

            if mismatch.size > 0:
                Phase_updates = mismatch[0:Delta_size]
                V_updates = mismatch[Delta_size:Delta_size + V_size] if V_size > 0 else np.array([])
                for idx_u, bus_ind in enumerate(P_idx):
                    Phase[bus_ind] += Phase_updates[idx_u]
                for idx_u, bus_ind in enumerate(Q_idx):
                    V[bus_ind] += V_updates[idx_u]

                if np.linalg.norm(mismatch) < tol or iterCount >= maxIter:
                    break
            else:
                break

            if iterCount >= maxIter:
                break

        S_network = np.zeros(N, dtype=complex)
        S_line_rows = []
        for k in range(len(bi_arr)):
            bi = int(bi_arr[k]); bj = int(bj_arr[k])
            i = bus_to_idx[bi]; j = bus_to_idx[bj]
            a = Tap[k]
            shift_rad = math.radians(Shift[k])
            a_exp = a * np.exp(1j * shift_rad)
            Vi = V[i] * np.exp(1j * Phase[i])
            Vj = V[j] * np.exp(1j * Phase[j])
            Rk = R[k]; Xk = X[k]
            y = 1.0 / (Rk + 1j * Xk)

            if abs(shift_rad) > 1e-12:
                Iij = -(y / np.conj(a_exp)) * Vj + (y / (a ** 2)) * Vi
                Iji = y * Vj - (y / a_exp) * Vi
                Sij = Vi * np.conjugate(Iij) * S_base
                Sji = Vj * np.conjugate(Iji) * S_base
            else:
                Mid = y / a
                Half_i = 1j * half_B[k] + y * (1 - a) / (a ** 2)
                Half_j = 1j * half_B[k] + y * (a - 1) / a
                Iij_line = (Vi - Vj) * Mid
                Ii0 = Half_i * Vi
                Iij = Iij_line + Ii0
                Sij_line = Vi * np.conjugate(Iij_line) * S_base
                Si0 = Vi * np.conjugate(Ii0) * S_base
                Sij = Sij_line + Si0
                Iji_line = (Vj - Vi) * Mid
                Ij0 = Half_j * Vj
                Iji = Iji_line + Ij0
                Sji_line = Vj * np.conjugate(Iji_line) * S_base
                Sj0 = Vj * np.conjugate(Ij0) * S_base
                Sji = Sji_line + Sj0

            S_network[i] += Sij
            S_network[j] += Sji
            Ploss = (np.real(Sij) + np.real(Sji))
            Qloss = (np.imag(Sij) + np.imag(Sji))
            S_line_rows.append({'i': bi, 'j': bj, 'Pij': np.real(Sij), 'Qij': np.imag(Sij),
                                'Pji': np.real(Sji), 'Qji': np.imag(Sji), 'P_loss': Ploss, 'Q_loss': Qloss})

        summary = pd.DataFrame(S_line_rows)
        totals = {'i': np.nan, 'j': np.nan, 'Pij': np.nan, 'Qij': np.nan, 'Pji': np.nan, 'Qji': np.nan,
                  'P_loss': summary['P_loss'].sum() if not summary.empty else 0.0,
                  'Q_loss': summary['Q_loss'].sum() if not summary.empty else 0.0}
        summary = pd.concat([summary, pd.DataFrame([totals])], ignore_index=True)

        Q_injected = S_base * B_sh * (V ** 2)
        P_bus_loss = S_base * G * (V ** 2)
        P_network = np.real(S_network)
        Q_network = np.imag(S_network)
        P_gen = P_network + Pload + P_bus_loss
        Q_gen = Q_network + Qload - Q_injected

        Phase_deg = np.degrees(Phase)
        businfo = pd.DataFrame({
            'Bus': Bus,
            'V': V,
            'Phase': Phase_deg,
            'Pgen': P_gen,
            'Qgen': Q_gen,
            'Pload': Pload,
            'Qload': Qload,
            'Qinj': Q_injected,
            'Pbus_loss': P_bus_loss
        })
        totals_bus = {'Bus': np.nan, 'V': np.nan, 'Phase': np.nan,
                      'Pgen': businfo['Pgen'].sum(), 'Qgen': businfo['Qgen'].sum(),
                      'Pload': businfo['Pload'].sum(), 'Qload': businfo['Qload'].sum(),
                      'Qinj': businfo['Qinj'].sum(), 'Pbus_loss': businfo['Pbus_loss'].sum()}
        businfo = pd.concat([businfo, pd.DataFrame([{
            'Bus': np.nan, 'V': np.nan, 'Phase': np.nan,
            'Pgen': businfo['Pgen'].sum(), 'Qgen': businfo['Qgen'].sum(),
            'Pload': businfo['Pload'].sum(), 'Qload': businfo['Qload'].sum(),
            'Qinj': businfo['Qinj'].sum(), 'Pbus_loss': businfo['Pbus_loss'].sum()
        }])], ignore_index=True)

        return summary, businfo, iterCount, residuals
def computePowerFlow_GS(busData: dict, branchData: dict, tol: float, maxIter: int, progress_callback=None):
    Bus = np.array(busData['Bus'], dtype=int)
    order = np.argsort(Bus)
    Bus = Bus[order]
    Type = np.array(busData['Type'])[order]
    V_init = np.array(busData['V'])[order]
    Phase_deg_init = np.array(busData['Phase'])[order]
    Pgen = np.array(busData['Pgen'])[order]
    Qgen = np.array(busData['Qgen'])[order]
    Pload = np.array(busData['Pload'])[order]
    Qload = np.array(busData['Qload'])[order]
    G = np.array(busData['G'])[order]
    B_sh = np.array(busData['B'])[order]

    bi_arr = np.array(branchData['bus_i'], dtype=int)
    bj_arr = np.array(branchData['bus_j'], dtype=int)
    R = np.array(branchData['R'], dtype=float)
    X = np.array(branchData['X'], dtype=float)
    half_B = np.array(branchData['half_B'], dtype=float)
    Tap = np.array(branchData['Tap'], dtype=float)
    Shift = np.array(branchData['Shift'], dtype=float)

    bus_to_idx = {bus: idx for idx, bus in enumerate(Bus)}
    N = len(Bus)
    residuals = []
    S_base = 100.0

    zero_taps = np.where(Tap == 0)[0]
    if zero_taps.size > 0:
        Tap[zero_taps] = 1.0

    z_all = R + 1j * X
    zero_z_idx = np.where(np.isclose(z_all, 0.0))[0]
    if zero_z_idx.size > 0:
        k = int(zero_z_idx[0])
        raise RuntimeError(f'Invalid branch data: branch #{k+1} has zero impedance (R==0 and X==0). Set a non-zero X (and/or R).')

    Ybus = np.zeros((N, N), dtype=complex)
    for k in range(len(bi_arr)):
        bi = int(bi_arr[k]); bj = int(bj_arr[k])
        i = bus_to_idx[bi]; j = bus_to_idx[bj]
        a = Tap[k]
        shift_rad = math.radians(Shift[k])
        a_exp = a * np.exp(1j * shift_rad)
        z = R[k] + 1j * X[k]
        Ybus[i, j] -= 1.0 / (np.conj(a_exp) * z)
        Ybus[j, i] -= 1.0 / (a_exp * z)
        Ybus[i, i] += 1.0 / (a ** 2 * z) + 1j * half_B[k]
        Ybus[j, j] += 1.0 / (z) + 1j * half_B[k]

    for k in range(N):
        Ybus[k, k] += G[k] + 1j * B_sh[k]

    V = np.array([
        (v if not np.isnan(v) else 1.0) * np.exp(1j * math.radians(phi if not np.isnan(phi) else 0.0))
        for v, phi in zip(V_init, Phase_deg_init)
    ], dtype=complex)

    P_spec = (Pgen - Pload) / S_base
    Q_spec = (Qgen - Qload) / S_base

    isSlack = (Type == 'Slack')
    isPV = (Type == 'PV')
    isPQ = (Type == 'PQ')

    iterCount = 0
    for it in range(maxIter):
        iterCount += 1
        V_old = V.copy()
        for i in range(N):
            if isSlack[i]:
                continue
            sumYV = 0+0j
            for j in range(N):
                if j != i:
                    sumYV += Ybus[i, j] * V[j]

            if isPQ[i]:
                S = P_spec[i] + 1j * Q_spec[i]
                if np.isclose(Ybus[i, i], 0.0):
                    raise RuntimeError(f'Ybus diagonal nearly zero at bus {i+1}. Check network data.')
                V[i] = (1.0 / Ybus[i, i]) * (np.conjugate(S) / np.conjugate(V[i]) - sumYV)

            elif isPV[i]:
                S_temp = P_spec[i] + 1j * 0.0
                if np.isclose(Ybus[i, i], 0.0):
                    raise RuntimeError(f'Ybus diagonal nearly zero at bus {i+1}. Check network data.')
                V_temp = (1.0 / Ybus[i, i]) * (np.conjugate(S_temp) / np.conjugate(V[i]) - sumYV)
                V[i] = abs(V_init[i]) * np.exp(1j * np.angle(V_temp))
                Q_spec[i] = -np.imag(np.conjugate(V[i]) * (Ybus[i, :] @ V))

        
            # record residual norm for convergence diagnostics (max voltage change)
            try:
                res_norm = float(np.max(np.abs(V - V_old)))
            except Exception:
                res_norm = 0.0
            residuals.append(res_norm)
            if progress_callback is not None:
                try:
                    progress_callback(iterCount, res_norm)
                except Exception:
                    pass
            if np.max(np.abs(V - V_old)) < tol:
                break

    S_network = np.zeros(N, dtype=complex)
    S_line_rows = []
    for k in range(len(bi_arr)):
        bi = int(bi_arr[k]); bj = int(bj_arr[k])
        i = bus_to_idx[bi]; j = bus_to_idx[bj]
        a = Tap[k]
        shift_rad = math.radians(Shift[k])
        a_exp = a * np.exp(1j * shift_rad)

        Vi = V[i]; Vj = V[j]
        Rk = R[k]; Xk = X[k]
        y = 1.0 / (Rk + 1j * Xk)

        if abs(shift_rad) > 1e-12:
            Iij = -(y / np.conj(a_exp)) * Vj + (y / (a ** 2)) * Vi
            Iji = y * Vj - (y / a_exp) * Vi
            Sij = Vi * np.conjugate(Iij) * S_base
            Sji = Vj * np.conjugate(Iji) * S_base
        else:
            Mid = y / a
            Half_i = 1j * half_B[k] + y * (1 - a) / (a ** 2)
            Half_j = 1j * half_B[k] + y * (a - 1) / a
            Iij_line = (Vi - Vj) * Mid
            Ii0 = Half_i * Vi
            Iij = Iij_line + Ii0
            Sij_line = Vi * np.conjugate(Iij_line) * S_base
            Si0 = Vi * np.conjugate(Ii0) * S_base
            Sij = Sij_line + Si0
            Iji_line = (Vj - Vi) * Mid
            Ij0 = Half_j * Vj
            Iji = Iji_line + Ij0
            Sji_line = Vj * np.conjugate(Iji_line) * S_base
            Sj0 = Vj * np.conjugate(Ij0) * S_base
            Sji = Sji_line + Sj0

        S_network[i] += Sij
        S_network[j] += Sji
        Ploss = (np.real(Sij) + np.real(Sji))
        Qloss = (np.imag(Sij) + np.imag(Sji))
        S_line_rows.append({'i': bi, 'j': bj, 'Pij': np.real(Sij), 'Qij': np.imag(Sij),
                            'Pji': np.real(Sji), 'Qji': np.imag(Sji), 'P_loss': Ploss, 'Q_loss': Qloss})

    summary = pd.DataFrame(S_line_rows)
    totals = {'i': np.nan, 'j': np.nan, 'Pij': np.nan, 'Qij': np.nan, 'Pji': np.nan, 'Qji': np.nan,
              'P_loss': summary['P_loss'].sum() if not summary.empty else 0.0,
              'Q_loss': summary['Q_loss'].sum() if not summary.empty else 0.0}
    summary = pd.concat([summary, pd.DataFrame([totals])], ignore_index=True)

    Q_injected = np.zeros(N)
    P_bus_loss = np.zeros(N)
    for kbus in range(N):
        Q_injected[kbus] = S_base * B_sh[kbus] * (abs(V[kbus]) ** 2)
        P_bus_loss[kbus] = S_base * G[kbus] * (abs(V[kbus]) ** 2)

    P_network = np.real(S_network)
    Q_network = np.imag(S_network)
    P_gen = P_network + Pload + P_bus_loss
    Q_gen = Q_network + Qload - Q_injected

    Phase_deg = np.degrees(np.angle(V))

    businfo = pd.DataFrame({
        'Bus': Bus,
        'V': np.abs(V),
        'Phase': Phase_deg,
        'Pgen': P_gen,
        'Qgen': Q_gen,
        'Pload': Pload,
        'Qload': Qload,
        'Qinj': Q_injected,
        'Pbus_loss': P_bus_loss
    })
    totals_bus = {'Bus': np.nan, 'V': np.nan, 'Phase': np.nan,
                  'Pgen': businfo['Pgen'].sum(), 'Qgen': businfo['Qgen'].sum(),
                  'Pload': businfo['Pload'].sum(), 'Qload': businfo['Qload'].sum(),
                  'Qinj': businfo['Qinj'].sum(), 'Pbus_loss': businfo['Pbus_loss'].sum()}
    businfo = pd.concat([businfo, pd.DataFrame([totals_bus])], ignore_index=True)

    return summary, businfo, iterCount, residuals

# -------------------- Main --------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = PowerSystemUI()
    win.show()
    sys.exit(app.exec())
