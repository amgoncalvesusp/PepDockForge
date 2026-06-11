from __future__ import annotations

import sys
import os
import math

if "--self-test" in sys.argv:
    import tempfile
    from pathlib import Path

    import pepdock_core as _core

    _record = _core.PeptideRecord(serial=1, sequence="FDSVH", source="self-test", values=(1, "FDSVH"))
    _ile_record = _core.PeptideRecord(serial=2, sequence="FDSIH", source="self-test", values=(2, "FDSIH"))
    with tempfile.TemporaryDirectory() as _tmp:
        _settings = _core.BuildSettings(
            output_dir=Path(_tmp),
            formats=("pdb", "sdf", "mol2", "pdbqt"),
            pdb_record_type="ATOM",
            source_name="self-test",
        )
        _result = _core.build_and_export(_record, _settings)
        if not _result.ok or len(_result.files) != 4:
            print(_result.message or "Self-test failed.")
            raise SystemExit(1)
        _ile_settings = _core.BuildSettings(
            output_dir=Path(_tmp),
            formats=("mol2",),
            pdb_record_type="ATOM",
            source_name="self-test",
        )
        _ile_result = _core.build_and_export(_ile_record, _ile_settings)
        if not _ile_result.ok or len(_ile_result.files) != 1:
            print(_ile_result.message or "Ile geometry self-test failed.")
            raise SystemExit(1)
        _charmm_settings = _core.BuildSettings(
            output_dir=Path(_tmp),
            formats=("pdb",),
            pdb_record_type="ATOM",
            force_field="charmm36",
            source_name="self-test",
        )
        _charmm_result = _core.build_and_export(_record, _charmm_settings)
        if not _charmm_result.ok or len(_charmm_result.files) != 1:
            print(_charmm_result.message or "CHARMM36 self-test failed.")
            raise SystemExit(1)
    print("Self-test OK.")
    raise SystemExit(0)

import tempfile
from dataclasses import replace
from pathlib import Path


_DLL_DIRECTORY_HANDLES = []


def _prepare_frozen_qt_runtime() -> None:
    if not getattr(sys, "frozen", False):
        return

    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    dll_dirs = [
        bundle_dir / "PySide6",
        bundle_dir / "shiboken6",
        bundle_dir,
    ]
    existing_dirs = [str(path) for path in dll_dirs if path.exists()]

    for path in existing_dirs:
        try:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(path))
        except (AttributeError, OSError):
            pass

    os.environ["PATH"] = os.pathsep.join(existing_dirs + [os.environ.get("PATH", "")])

    plugins_dir = bundle_dir / "PySide6" / "plugins"
    qml_dir = bundle_dir / "PySide6" / "qml"
    if plugins_dir.exists():
        os.environ["QT_PLUGIN_PATH"] = str(plugins_dir)
    if qml_dir.exists():
        os.environ["QML2_IMPORT_PATH"] = str(qml_dir)


_prepare_frozen_qt_runtime()

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import pepdock_core as core


APP_NAME = "PepDock Forge"


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "assets" / name
    return Path(__file__).resolve().parent / "assets" / name


def peptide_icon() -> QIcon:
    icon_asset = asset_path("pepdock_app_icon.png")
    if icon_asset.exists():
        return QIcon(str(icon_asset))

    pixmap = QPixmap(128, 128)
    pixmap.fill(QColor("#101720"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    points = [(24, 84), (45, 48), (66, 78), (87, 42), (108, 72)]
    pen = QPen(QColor("#66e3c4"), 8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    for start, end in zip(points, points[1:]):
        painter.drawLine(*start, *end)

    painter.setPen(Qt.NoPen)
    for index, point in enumerate(points):
        painter.setBrush(QColor("#f6d365" if index % 2 else "#6ca8ff"))
        painter.drawEllipse(point[0] - 9, point[1] - 9, 18, 18)

    painter.end()
    return QIcon(pixmap)


class BuildWorker(QThread):
    progress = Signal(int, int, str)
    result_ready = Signal(object)
    finished_all = Signal(list)

    def __init__(self, records: list[core.PeptideRecord], settings: core.BuildSettings):
        super().__init__()
        self.records = records
        self.settings = settings

    def run(self) -> None:
        results = []
        total = len(self.records)
        for index, record in enumerate(self.records, start=1):
            self.progress.emit(index - 1, total, f"Building {record.sequence}")
            result = core.build_and_export(record, self.settings)
            results.append(result)
            status = "OK" if result.ok else "FAILED"
            message = f"[{status}] {record.sequence}: {result.message}"
            self.result_ready.emit(result)
            self.progress.emit(index, total, message)
        self.finished_all.emit(results)


class StructureCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.structure: core.PdbStructure | None = None
        self.rotation = (25.0, -35.0, 10.0)
        self.zoom = 1.0
        self.setMinimumHeight(340)

    def set_structure(self, structure: core.PdbStructure | None) -> None:
        self.structure = structure
        self.update()

    def set_rotation_x(self, value: int) -> None:
        self.rotation = (float(value), self.rotation[1], self.rotation[2])
        self.update()

    def set_rotation_y(self, value: int) -> None:
        self.rotation = (self.rotation[0], float(value), self.rotation[2])
        self.update()

    def set_rotation_z(self, value: int) -> None:
        self.rotation = (self.rotation[0], self.rotation[1], float(value))
        self.update()

    def set_zoom(self, value: int) -> None:
        self.zoom = max(0.25, value / 100.0)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0f1722"))

        if not self.structure or not self.structure.atoms:
            painter.setPen(QColor("#8fa1b6"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Load a PDB file to preview the structure")
            painter.end()
            return

        projected = self._project_atoms()
        painter.setPen(QPen(QColor("#536276"), 1.3))
        for serial_a, serial_b in self.structure.bonds:
            if serial_a not in projected or serial_b not in projected:
                continue
            x1, y1, _, _ = projected[serial_a]
            x2, y2, _, _ = projected[serial_b]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        for _, (x, y, z, atom) in sorted(projected.items(), key=lambda item: item[1][2]):
            color = self._atom_color(atom.element)
            radius = self._atom_radius(atom.element)
            painter.setBrush(color)
            painter.setPen(QPen(QColor("#0b1118"), 1))
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)

        painter.setPen(QColor("#8fa1b6"))
        atom_count = len(self.structure.atoms)
        bond_count = len(self.structure.bonds)
        painter.drawText(14, 24, f"{atom_count} atoms | {bond_count} bonds")
        painter.end()

    def _project_atoms(self) -> dict[int, tuple[float, float, float, core.PdbAtom]]:
        assert self.structure is not None
        atoms = self.structure.atoms
        cx = sum(atom.x for atom in atoms) / len(atoms)
        cy = sum(atom.y for atom in atoms) / len(atoms)
        cz = sum(atom.z for atom in atoms) / len(atoms)

        rotated = []
        for atom in atoms:
            x, y, z = self._rotate(atom.x - cx, atom.y - cy, atom.z - cz)
            rotated.append((atom, x, y, z))

        x_values = [item[1] for item in rotated]
        y_values = [item[2] for item in rotated]
        span = max(max(x_values) - min(x_values), max(y_values) - min(y_values), 1.0)
        scale = min(self.width(), self.height()) * 0.78 * self.zoom / span
        center_x = self.width() / 2
        center_y = self.height() / 2

        return {
            atom.serial: (center_x + x * scale, center_y - y * scale, z, atom)
            for atom, x, y, z in rotated
        }

    def _rotate(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        rx, ry, rz = (math.radians(value) for value in self.rotation)

        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        return x, y, z

    @staticmethod
    def _atom_color(element: str) -> QColor:
        colors = {
            "C": "#c4ccd6",
            "N": "#6ca8ff",
            "O": "#ff6b6b",
            "S": "#f6d365",
            "H": "#f8fafc",
            "P": "#ffb86b",
        }
        return QColor(colors.get(element.upper(), "#66e3c4"))

    @staticmethod
    def _atom_radius(element: str) -> int:
        return {"H": 3, "C": 5, "N": 5, "O": 5, "S": 6, "P": 6}.get(element.upper(), 5)


class PositionBuilder(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.length_spin = QSpinBox()
        self.length_spin.setRange(1, core.MAX_PEPTIDE_LENGTH)
        self.length_spin.setValue(5)
        self.length_spin.valueChanged.connect(self._sync_enabled_rows)

        self.max_count_spin = QSpinBox()
        self.max_count_spin.setRange(1, 1_000_000)
        self.max_count_spin.setValue(10000)

        top = QHBoxLayout()
        top.addWidget(QLabel("Length"))
        top.addWidget(self.length_spin)
        top.addSpacing(16)
        top.addWidget(QLabel("Max count"))
        top.addWidget(self.max_count_spin)
        top.addStretch(1)

        self.rows: list[tuple[QComboBox, QLineEdit]] = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Position"), 0, 0)
        grid.addWidget(QLabel("Class"), 0, 1)
        grid.addWidget(QLabel("Choices"), 0, 2)

        options = ["Custom"] + list(core.AA_CLASSES)
        for index in range(core.MAX_PEPTIDE_LENGTH):
            combo = QComboBox()
            combo.addItems(options)
            choices = QLineEdit()
            choices.setPlaceholderText("Amino acid letters")
            if index == 0:
                combo.setCurrentText("Aromatic")
                choices.setText(core.AA_CLASSES["Aromatic"])
            elif index == 1:
                combo.setCurrentText("Acidic")
                choices.setText(core.AA_CLASSES["Acidic"])
            elif index == 2:
                combo.setCurrentText("Polar neutral")
                choices.setText("STN")
            elif index == 3:
                combo.setCurrentText("Hydrophobic")
                choices.setText("VLI")
            elif index == 4:
                combo.setCurrentText("Basic")
                choices.setText("H")
            else:
                combo.setCurrentText("Custom")
                choices.setText("A")

            combo.currentTextChanged.connect(lambda value, field=choices: self._class_changed(value, field))
            choices.textChanged.connect(self.changed.emit)
            grid.addWidget(QLabel(str(index + 1)), index + 1, 0)
            grid.addWidget(combo, index + 1, 1)
            grid.addWidget(choices, index + 1, 2)
            self.rows.append((combo, choices))

        body = QWidget()
        body.setLayout(grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        scroll.setMinimumHeight(260)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(scroll)
        self._sync_enabled_rows()

    def _class_changed(self, value: str, field: QLineEdit) -> None:
        if value in core.AA_CLASSES:
            field.setText(core.AA_CLASSES[value])
        self.changed.emit()

    def _sync_enabled_rows(self) -> None:
        length = self.length_spin.value()
        for index, (combo, choices) in enumerate(self.rows):
            enabled = index < length
            combo.setEnabled(enabled)
            choices.setEnabled(enabled)
        self.changed.emit()

    def choices(self) -> list[str]:
        length = self.length_spin.value()
        return [self.rows[index][1].text().strip().upper() for index in range(length)]

    def max_count(self) -> int:
        return self.max_count_spin.value()


class PepDockForgeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.records: list[core.PeptideRecord] = []
        self.imported_header: tuple[str, ...] = ()
        self.worker: BuildWorker | None = None
        self.descriptor_rows_cache: list[dict[str, object]] = []
        self.last_pdb_path: Path | None = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(peptide_icon())
        self.setMinimumSize(760, 520)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(224)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 18)
        sidebar_layout.setSpacing(14)

        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("BrandLogo")
        self.brand_logo.setAlignment(Qt.AlignCenter)
        logo_pixmap = QPixmap(str(asset_path("pepdock_logo_lockup.png")))
        if not logo_pixmap.isNull():
            self.brand_logo.setPixmap(logo_pixmap.scaled(178, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.brand_logo.setMinimumHeight(56)
        else:
            self.brand_logo.setText(APP_NAME)
        sidebar_layout.addWidget(self.brand_logo)

        self.nav = QListWidget()
        for name in ["Library", "Build & Optimize", "Analyze & View", "Run Log"]:
            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignVCenter)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._switch_page)
        sidebar_layout.addWidget(self.nav, 1)
        root_layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.library_page = self._library_page()
        self.build_page = self._build_page()
        self.analysis_page = self._analysis_page()
        self.log_page = self._log_page()
        self.stack.addWidget(self.library_page)
        self.stack.addWidget(self.build_page)
        self.stack.addWidget(self.analysis_page)
        self.stack.addWidget(self.log_page)
        root_layout.addWidget(self.stack, 1)

        self.setCentralWidget(root)
        self._set_initial_window_size()
        self.nav.setCurrentRow(0)
        self._refresh_table()

    def _library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Peptide Library")
        title.setObjectName("Title")
        layout.addWidget(title)

        actions_top = QHBoxLayout()
        actions_bottom = QHBoxLayout()
        import_btn = QPushButton("Import XLSX")
        import_btn.clicked.connect(self.import_xlsx)
        save_btn = QPushButton("Save Library XLSX")
        save_btn.clicked.connect(self.save_library)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_library)
        actions_top.addWidget(import_btn)
        actions_top.addWidget(save_btn)
        actions_top.addStretch(1)
        actions_bottom.addWidget(clear_btn)
        actions_bottom.addStretch(1)
        layout.addLayout(actions_top)
        layout.addLayout(actions_bottom)

        manual_group = QGroupBox("Manual sequence")
        manual_layout = QHBoxLayout(manual_group)
        self.manual_sequence = QLineEdit()
        self.manual_sequence.setPlaceholderText("Sequence, 1-20 amino acids")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_manual_sequence)
        manual_layout.addWidget(self.manual_sequence, 1)
        manual_layout.addWidget(add_btn)
        layout.addWidget(manual_group)

        generator_group = QGroupBox("Combinatorial builder")
        generator_layout = QVBoxLayout(generator_group)
        self.position_builder = PositionBuilder()
        self.position_builder.changed.connect(self._update_combination_label)
        generator_layout.addWidget(self.position_builder)
        generator_actions = QHBoxLayout()
        self.combination_label = QLabel("")
        generate_btn = QPushButton("Generate Library")
        generate_btn.clicked.connect(self.generate_library)
        generator_actions.addWidget(self.combination_label)
        generator_actions.addStretch(1)
        generator_actions.addWidget(generate_btn)
        generator_layout.addLayout(generator_actions)
        layout.addWidget(generator_group)

        self.library_summary = QLabel("")
        layout.addWidget(self.library_summary)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Selected", "Serial", "Sequence", "Length", "Source", "Status", "Reason"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(180)
        self.table.itemChanged.connect(self._table_item_changed)
        layout.addWidget(self.table, 1)
        self._update_combination_label()
        return self._scrollable_page(page)

    def _build_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Build & Optimize")
        title.setObjectName("Title")
        layout.addWidget(title)

        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output folder")
        output_btn = QPushButton("Output Folder")
        output_btn.clicked.connect(self.choose_output_folder)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(output_btn)
        layout.addLayout(output_row)

        options = QFrame()
        options.setObjectName("Panel")
        grid = QGridLayout(options)
        grid.addWidget(QLabel("Formats"), 0, 0)
        self.format_checks = {}
        for column, fmt in enumerate(["pdb", "sdf", "mol2", "pdbqt"], start=1):
            box = QCheckBox(fmt.upper())
            box.setChecked(fmt == "pdb")
            self.format_checks[fmt] = box
            grid.addWidget(box, 0, column)

        grid.addWidget(QLabel("PDB records"), 1, 0)
        self.record_type = QComboBox()
        self.record_type.addItems(["ATOM", "HETATM"])
        grid.addWidget(self.record_type, 1, 1)

        grid.addWidget(QLabel("Force field"), 1, 2)
        self.force_field = QComboBox()
        for key in core.FORCE_FIELD_PRESETS:
            self.force_field.addItem(core.force_field_label(key), key)
        grid.addWidget(self.force_field, 1, 3, 1, 2)
        layout.addWidget(options)

        build_actions = QHBoxLayout()
        self.build_button = QPushButton("Build Selected")
        self.build_button.clicked.connect(self.build_selected)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        build_actions.addWidget(self.build_button)
        build_actions.addWidget(self.progress, 1)
        layout.addLayout(build_actions)

        self.build_summary = QLabel("")
        layout.addWidget(self.build_summary)
        layout.addStretch(1)
        return page

    def _analysis_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Analyze & View")
        title.setObjectName("Title")
        layout.addWidget(title)

        descriptor_group = QGroupBox("Publication descriptors")
        descriptor_layout = QVBoxLayout(descriptor_group)
        descriptor_actions = QHBoxLayout()
        self.report_selected_only = QCheckBox("Selected rows only")
        self.report_selected_only.setChecked(True)
        self.report_ranked = QCheckBox("Rank by score")
        self.report_ranked.setChecked(True)
        self.solubility_threshold = QSpinBox()
        self.solubility_threshold.setRange(0, 100)
        self.solubility_threshold.setValue(core.DEFAULT_SOLUBILITY_THRESHOLD)
        self.solubility_threshold.setSuffix(" min solubility")
        solubility_gate_btn = QPushButton("Select Soluble for 3D")
        solubility_gate_btn.clicked.connect(self.apply_solubility_gate)
        descriptor_btn = QPushButton("Calculate")
        descriptor_btn.clicked.connect(self.refresh_descriptors)
        save_xlsx_btn = QPushButton("Save XLSX")
        save_xlsx_btn.clicked.connect(self.save_descriptor_xlsx)
        save_md_btn = QPushButton("Save Markdown")
        save_md_btn.clicked.connect(self.save_descriptor_markdown)
        descriptor_actions.addWidget(self.report_selected_only)
        descriptor_actions.addWidget(self.report_ranked)
        descriptor_actions.addWidget(self.solubility_threshold)
        descriptor_actions.addWidget(solubility_gate_btn)
        descriptor_actions.addStretch(1)
        descriptor_actions.addWidget(descriptor_btn)
        descriptor_actions.addWidget(save_xlsx_btn)
        descriptor_actions.addWidget(save_md_btn)
        descriptor_layout.addLayout(descriptor_actions)

        self.descriptor_table = QTableWidget(0, len(core.PUBLICATION_DESCRIPTOR_HEADERS))
        self.descriptor_table.setHorizontalHeaderLabels(list(core.PUBLICATION_DESCRIPTOR_HEADERS))
        self.descriptor_table.setSortingEnabled(True)
        self.descriptor_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.descriptor_table.horizontalHeader().setMinimumSectionSize(72)
        self.descriptor_table.horizontalHeader().setStretchLastSection(False)
        self.descriptor_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.descriptor_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.descriptor_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.descriptor_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.descriptor_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.descriptor_table.setWordWrap(False)
        self.descriptor_table.setAlternatingRowColors(True)
        self._apply_descriptor_column_widths()
        descriptor_layout.addWidget(self.descriptor_table, 1)
        layout.addWidget(descriptor_group, 1)

        viewer_group = QGroupBox("PDB preview")
        viewer_layout = QVBoxLayout(viewer_group)
        viewer_actions = QHBoxLayout()
        self.viewer_path = QLineEdit()
        self.viewer_path.setPlaceholderText("PDB file")
        load_pdb_btn = QPushButton("Load PDB")
        load_pdb_btn.clicked.connect(self.load_pdb_file)
        load_last_btn = QPushButton("Load Last Built")
        load_last_btn.clicked.connect(self.load_last_built_pdb)
        viewer_actions.addWidget(self.viewer_path, 1)
        viewer_actions.addWidget(load_pdb_btn)
        viewer_actions.addWidget(load_last_btn)
        viewer_layout.addLayout(viewer_actions)

        self.structure_canvas = StructureCanvas()
        viewer_layout.addWidget(self.structure_canvas)

        controls = QGridLayout()
        self.viewer_x = self._viewer_slider(25, self.structure_canvas.set_rotation_x)
        self.viewer_y = self._viewer_slider(-35, self.structure_canvas.set_rotation_y)
        self.viewer_z = self._viewer_slider(10, self.structure_canvas.set_rotation_z)
        self.viewer_zoom = self._viewer_slider(100, self.structure_canvas.set_zoom, minimum=25, maximum=250)
        controls.addWidget(QLabel("X"), 0, 0)
        controls.addWidget(self.viewer_x, 0, 1)
        controls.addWidget(QLabel("Y"), 1, 0)
        controls.addWidget(self.viewer_y, 1, 1)
        controls.addWidget(QLabel("Z"), 2, 0)
        controls.addWidget(self.viewer_z, 2, 1)
        controls.addWidget(QLabel("Zoom"), 3, 0)
        controls.addWidget(self.viewer_zoom, 3, 1)
        viewer_layout.addLayout(controls)
        self.viewer_summary = QLabel("")
        viewer_layout.addWidget(self.viewer_summary)
        layout.addWidget(viewer_group, 1)
        return page

    def _set_initial_window_size(self) -> None:
        app = QApplication.instance()
        screen = app.primaryScreen() if app is not None else None
        if screen is None:
            self.resize(1120, 720)
            return
        available = screen.availableGeometry()
        width = max(760, min(1240, available.width() - 80))
        height = max(520, min(780, available.height() - 80))
        self.resize(width, height)

    def _scrollable_page(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(page)
        return scroll

    def _log_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Run Log")
        title.setObjectName("Title")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(title)
        layout.addWidget(self.log_text, 1)
        return page

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(max(0, index))

    def _viewer_slider(self, value: int, slot, minimum: int = -180, maximum: int = 180) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(slot)
        return slider

    def import_xlsx(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import peptide spreadsheet", "", "Excel files (*.xlsx)")
        if not path:
            return
        try:
            header, records = core.load_peptide_rows_from_xlsx(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.imported_header = header
        self.records = records
        self._append_log(f"Imported {len(records)} peptide rows from {Path(path).name}.")
        self._refresh_table()

    def save_library(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "No library", "No peptide rows to save.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save peptide library", "pepdock_library.xlsx", "Excel files (*.xlsx)")
        if not path:
            return
        try:
            core.export_library_to_xlsx(path, self.records, self.imported_header)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self._append_log(f"Saved library to {path}.")

    def add_manual_sequence(self) -> None:
        try:
            sequence = core.validate_sequence(self.manual_sequence.text())
        except Exception as exc:
            QMessageBox.warning(self, "Invalid sequence", str(exc))
            return
        serial = self._next_serial()
        self.records.append(core.PeptideRecord(serial=serial, sequence=sequence, source="manual", values=(serial, sequence)))
        self.manual_sequence.clear()
        self._append_log(f"Added manual sequence {sequence}.")
        self._refresh_table()

    def generate_library(self) -> None:
        try:
            records = core.generate_combinatorial_library(
                self.position_builder.choices(),
                max_count=self.position_builder.max_count(),
                start_serial=1,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Generation failed", str(exc))
            return
        self.records = records
        self.imported_header = ("Serial", "Sequence")
        self._append_log(f"Generated {len(records)} peptide sequences.")
        self._refresh_table()

    def apply_solubility_gate(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "No library", "No peptide rows available for solubility analysis.")
            return
        threshold = self.solubility_threshold.value()
        self.records = core.apply_solubility_gate(self.records, min_score=threshold)
        selected = sum(1 for record in self.records if record.selected and record.status != "excluded")
        low = sum(1 for record in self.records if record.status == "low_solubility")
        self._append_log(f"Applied solubility gate >= {threshold}: {selected} selected for 3D, {low} held.")
        self._refresh_table()
        if self.descriptor_rows_cache and (selected or not self.report_selected_only.isChecked()):
            self.refresh_descriptors()
        elif self.descriptor_rows_cache:
            self.descriptor_rows_cache = []
            self.descriptor_table.setRowCount(0)

    def clear_library(self) -> None:
        self.records = []
        self.imported_header = ()
        self.descriptor_rows_cache = []
        if hasattr(self, "descriptor_table"):
            self.descriptor_table.setRowCount(0)
        self._refresh_table()
        self._append_log("Cleared library.")

    def choose_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.output_path.setText(path)

    def _records_for_report(self) -> list[core.PeptideRecord]:
        if getattr(self, "report_selected_only", None) and self.report_selected_only.isChecked():
            return [record for record in self.records if record.selected]
        return list(self.records)

    def _rank_report_rows(self) -> bool:
        return bool(getattr(self, "report_ranked", None) and self.report_ranked.isChecked())

    def refresh_descriptors(self) -> None:
        records = self._records_for_report()
        if not records:
            QMessageBox.warning(self, "No rows", "No peptide rows available for descriptors.")
            return
        try:
            rows = core.descriptor_rows(records, ranked=self._rank_report_rows())
        except Exception as exc:
            QMessageBox.critical(self, "Descriptor calculation failed", str(exc))
            return
        self.descriptor_rows_cache = rows
        self._refresh_descriptor_table(rows)
        self._append_log(f"Calculated descriptor table for {len(rows)} peptides.")

    def save_descriptor_xlsx(self) -> None:
        records = self._records_for_report()
        if not records:
            QMessageBox.warning(self, "No rows", "No peptide rows available for export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save descriptor report",
            "pepdock_publication_descriptors.xlsx",
            "Excel files (*.xlsx)",
        )
        if not path:
            return
        try:
            core.export_descriptor_report_xlsx(path, records, ranked=self._rank_report_rows())
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self._append_log(f"Saved descriptor report to {path}.")

    def save_descriptor_markdown(self) -> None:
        records = self._records_for_report()
        if not records:
            QMessageBox.warning(self, "No rows", "No peptide rows available for export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save publication report",
            "pepdock_publication_report.md",
            "Markdown files (*.md)",
        )
        if not path:
            return
        try:
            core.export_publication_report_markdown(path, records, ranked=self._rank_report_rows())
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self._append_log(f"Saved publication report to {path}.")

    def load_pdb_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load PDB", "", "PDB files (*.pdb)")
        if not path:
            return
        self._load_pdb_path(Path(path))

    def load_last_built_pdb(self) -> None:
        if not self.last_pdb_path or not self.last_pdb_path.exists():
            QMessageBox.warning(self, "No PDB", "No built PDB is available yet.")
            return
        self._load_pdb_path(self.last_pdb_path)

    def _load_pdb_path(self, path: Path) -> None:
        try:
            structure = core.load_pdb_structure(path)
        except Exception as exc:
            QMessageBox.critical(self, "PDB load failed", str(exc))
            return
        self.last_pdb_path = path
        self.viewer_path.setText(str(path))
        self.structure_canvas.set_structure(structure)
        self.viewer_summary.setText(f"{path.name}: {len(structure.atoms)} atoms, {len(structure.bonds)} bonds")
        self._append_log(f"Loaded PDB preview from {path}.")

    def build_selected(self) -> None:
        selected = [record for record in self.records if record.selected and record.status != "excluded"]
        if not selected:
            QMessageBox.warning(self, "Nothing selected", "Select one or more peptide rows first.")
            return
        output = self.output_path.text().strip()
        if not output:
            QMessageBox.warning(self, "Missing output folder", "Choose an output folder first.")
            return
        formats = tuple(fmt for fmt, box in self.format_checks.items() if box.isChecked())
        if not formats:
            QMessageBox.warning(self, "Missing format", "Select at least one output format.")
            return

        settings = core.BuildSettings(
            output_dir=Path(output),
            formats=formats,
            pdb_record_type=self.record_type.currentText(),
            force_field=self.force_field.currentData(),
            source_name="PepDock Forge",
        )
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.build_button.setEnabled(False)
        self.worker = BuildWorker(selected, settings)
        self.worker.progress.connect(self._build_progress)
        self.worker.result_ready.connect(self._build_result)
        self.worker.finished_all.connect(self._build_finished)
        self.worker.start()
        self._append_log(f"Started build for {len(selected)} peptides.")

    def _build_progress(self, value: int, total: int, message: str) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(value)
        self.build_summary.setText(message)
        if message.startswith("["):
            self._append_log(message)

    def _build_result(self, result: core.BuildResult) -> None:
        if result.ok:
            pdb_files = [path for path in result.files if path.suffix.lower() == ".pdb"]
            if pdb_files:
                self.last_pdb_path = pdb_files[0]
                self.viewer_path.setText(str(self.last_pdb_path))

        updated = []
        for record in self.records:
            if record.serial == result.record.serial and record.sequence == result.record.sequence:
                status = "built" if result.ok else "failed"
                reason = "" if result.ok else result.message
                updated.append(replace(record, status=status, reason=reason))
            else:
                updated.append(record)
        self.records = updated
        self._refresh_table()

    def _build_finished(self, results: list[core.BuildResult]) -> None:
        built = sum(1 for result in results if result.ok)
        failed = len(results) - built
        self.build_button.setEnabled(True)
        self.build_summary.setText(f"Done: {built} built, {failed} failed.")
        self._append_log(f"Build complete: {built} built, {failed} failed.")

    def _table_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0 or item.row() >= len(self.records):
            return
        selected = item.checkState() == Qt.Checked
        self.records[item.row()] = replace(self.records[item.row()], selected=selected)
        self._update_summary()

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            selected_item = QTableWidgetItem("")
            selected_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            selected_item.setCheckState(Qt.Checked if record.selected else Qt.Unchecked)
            self.table.setItem(row, 0, selected_item)
            values = [
                str(record.serial),
                record.sequence,
                str(len(record.sequence)),
                record.source,
                record.status,
                record.reason,
            ]
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self._update_summary()

    def _refresh_descriptor_table(self, rows: list[dict[str, object]]) -> None:
        headers = list(core.PUBLICATION_DESCRIPTOR_HEADERS)
        self.descriptor_table.setSortingEnabled(False)
        self.descriptor_table.setRowCount(len(rows))
        self.descriptor_table.setColumnCount(len(headers))
        self.descriptor_table.setHorizontalHeaderLabels(headers)
        self._apply_descriptor_column_widths()
        for row_index, row in enumerate(rows):
            for column, header in enumerate(headers):
                value = row.get(header, "")
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.descriptor_table.setItem(row_index, column, item)
        self.descriptor_table.setSortingEnabled(True)

    def _apply_descriptor_column_widths(self) -> None:
        wide_columns = {
            "Sequence": 130,
            "Source": 150,
            "ScoreNotes": 260,
            "SolubilityNotes": 280,
            "Build3DRecommended": 150,
        }
        compact_columns = {
            "Serial": 72,
            "Length": 72,
            "Selected": 84,
            "Status": 110,
            "Rank": 72,
            "Score_0_100": 105,
            "ScoreBand": 105,
            "SolubilityClass": 120,
            "HydrophobicPatchMax": 150,
        }
        for column, header in enumerate(core.PUBLICATION_DESCRIPTOR_HEADERS):
            width = wide_columns.get(header, compact_columns.get(header, 116))
            self.descriptor_table.setColumnWidth(column, width)

    def _update_summary(self) -> None:
        total = len(self.records)
        selected = sum(1 for record in self.records if record.selected)
        excluded = sum(1 for record in self.records if record.status == "excluded")
        low_solubility = sum(1 for record in self.records if record.status == "low_solubility")
        built = sum(1 for record in self.records if record.status == "built")
        self.library_summary.setText(
            f"{total} rows | {selected} selected | {excluded} excluded | {low_solubility} low solubility | {built} built"
        )

    def _update_combination_label(self) -> None:
        choices = self.position_builder.choices()
        try:
            count = core.combination_count(choices)
            self.combination_label.setText(f"{count} combinations")
        except Exception:
            self.combination_label.setText("Invalid choices")

    def _next_serial(self) -> int:
        return max((record.serial for record in self.records), default=0) + 1

    def _append_log(self, message: str) -> None:
        self.log_text.append(message)


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QWidget {
            background: #f6f8fb;
            color: #18212f;
            font-family: "Segoe UI";
            font-size: 10.5pt;
        }
        QScrollArea {
            background: #f6f8fb;
            border: none;
        }
        QFrame#Sidebar {
            background: #ffffff;
            border-right: 1px solid #d8e0e8;
        }
        QLabel#BrandLogo {
            background: #ffffff;
            border: none;
        }
        QListWidget {
            background: #ffffff;
            border: none;
            padding: 4px 0;
        }
        QListWidget::item {
            color: #586779;
            padding: 12px 14px;
            margin: 4px;
            border-radius: 10px;
        }
        QListWidget::item:hover {
            background: #eef7f4;
            color: #0f2b27;
        }
        QListWidget::item:selected {
            background: #dff5ef;
            color: #08745f;
            font-weight: 700;
        }
        QLabel#Title {
            font-size: 20pt;
            font-weight: 700;
            color: #111821;
        }
        QGroupBox, QFrame#Panel {
            border: 1px solid #d8e0e8;
            border-radius: 10px;
            margin-top: 8px;
            padding: 12px;
            background: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #08745f;
            background: #ffffff;
            font-weight: 700;
        }
        QPushButton {
            background: #12a586;
            color: #ffffff;
            border: 1px solid #0e8e73;
            border-radius: 10px;
            padding: 8px 13px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #0e8e73;
            border-color: #08745f;
        }
        QPushButton:pressed {
            background: #08745f;
            border-color: #065d4d;
        }
        QPushButton:disabled {
            background: #e2e8ef;
            color: #8a97a7;
            border-color: #d0d8e2;
        }
        QLineEdit, QComboBox, QSpinBox, QTextEdit, QTableWidget {
            background: #ffffff;
            border: 1px solid #c7d1dc;
            border-radius: 10px;
            padding: 6px;
            color: #18212f;
            selection-background-color: #12a586;
            selection-color: #ffffff;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QTableWidget:focus {
            border: 1px solid #12a586;
        }
        QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
            background: #eef3f7;
            border: none;
            width: 22px;
        }
        QComboBox::down-arrow, QSpinBox::up-arrow, QSpinBox::down-arrow {
            width: 8px;
            height: 8px;
        }
        QTableWidget {
            gridline-color: #e2e8ef;
            alternate-background-color: #f7fafc;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background: #dff5ef;
            color: #0f2b27;
        }
        QHeaderView::section {
            background: #eef3f7;
            color: #2f3c4b;
            border: 1px solid #d8e0e8;
            padding: 7px;
            font-weight: 700;
        }
        QProgressBar {
            background: #eef3f7;
            border: 1px solid #c7d1dc;
            border-radius: 10px;
            height: 18px;
            text-align: center;
            color: #18212f;
        }
        QProgressBar::chunk {
            background: #12a586;
            border-radius: 10px;
        }
        QCheckBox {
            spacing: 8px;
            color: #263545;
            font-weight: 600;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #8fa0b3;
            border-radius: 5px;
            background: #ffffff;
        }
        QCheckBox::indicator:checked {
            background: #12a586;
            border: 2px solid #08745f;
        }
        QCheckBox::indicator:unchecked:hover {
            border: 2px solid #12a586;
            background: #eef7f4;
        }
        QSlider::groove:horizontal {
            background: #d8e0e8;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #12a586;
            border: 2px solid #ffffff;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        QScrollBar:horizontal {
            background: #eef3f7;
            height: 16px;
            margin: 0;
            border: 1px solid #d8e0e8;
        }
        QScrollBar:vertical {
            background: #eef3f7;
            width: 16px;
            margin: 0;
            border: 1px solid #d8e0e8;
        }
        QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
            background: #94a3b4;
            border-radius: 6px;
            min-width: 38px;
            min-height: 38px;
        }
        QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {
            background: #12a586;
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            width: 0;
            height: 0;
            border: none;
            background: transparent;
        }
        QScrollBar::add-page, QScrollBar::sub-page {
            background: transparent;
        }
        """
    )


def run_self_test() -> int:
    record = core.PeptideRecord(serial=1, sequence="FDSVH", source="self-test", values=(1, "FDSVH"))
    with tempfile.TemporaryDirectory() as tmp:
        settings = core.BuildSettings(
            output_dir=Path(tmp),
            formats=("pdb", "sdf", "mol2", "pdbqt"),
            pdb_record_type="ATOM",
            source_name="self-test",
        )
        result = core.build_and_export(record, settings)
        if not result.ok:
            print(result.message)
            return 1
        if len(result.files) != 4:
            print("Expected four exported files.")
            return 1
        charmm_settings = core.BuildSettings(
            output_dir=Path(tmp),
            formats=("pdb",),
            pdb_record_type="ATOM",
            force_field="charmm36",
            source_name="self-test",
        )
        charmm_result = core.build_and_export(record, charmm_settings)
        if not charmm_result.ok:
            print(charmm_result.message)
            return 1
        if len(charmm_result.files) != 1:
            print("Expected one CHARMM36 PDB file.")
            return 1
    print("Self-test OK.")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return run_self_test()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(peptide_icon())
    apply_theme(app)
    window = PepDockForgeWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
