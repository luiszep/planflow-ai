"""
PlanFlow — demo UI for AI-assisted floor plan iterations (2D + 3D).
Run: python planflow_app.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.colors import to_rgba


@dataclass(frozen=True)
class RoomSpec:
    label: str
    x: float
    y: float
    w: float
    h: float
    fill: str
    edge: str
    height: float


def compute_rooms(prompt: str) -> List[RoomSpec]:
    p = prompt.lower()
    rooms: List[RoomSpec] = [
        RoomSpec("Living", 1, 1, 4, 4, "#BAE6FD", "#0284C7", 2.9),
        RoomSpec("Kitchen", 5, 1, 4, 4, "#FDE68A", "#D97706", 2.65),
        RoomSpec("Bedroom", 1, 5, 4, 4, "#BBF7D0", "#15803D", 2.9),
        RoomSpec("Flex", 5, 5, 4, 4, "#DDD6FE", "#7C3AED", 2.75),
    ]
    if "office" in p:
        rooms = [r for r in rooms if r.label != "Flex"]
        rooms.append(
            RoomSpec("Office", 5, 5, 4, 4, "#C4B5FD", "#5B21B6", 2.75)
        )
    if "expand kitchen" in p:
        rooms = [r for r in rooms if r.label != "Kitchen"]
        rooms.append(
            RoomSpec("Kitchen (expanded)", 5, 1, 5, 4, "#FCD34D", "#EA580C", 2.65)
        )
    if "bath" in p:
        rooms.append(
            RoomSpec("Powder bath", 4, 4, 2, 2, "#BFDBFE", "#1D4ED8", 2.35)
        )
    return rooms


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


class PlanCanvas2D(FigureCanvas):
    def __init__(self):
        self.fig = Figure(facecolor="#0B1220")
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.fig.subplots_adjust(left=0.05, right=0.97, top=0.90, bottom=0.05)
        self._last_prompt: str = ""
        self._last_w: int = 0
        self.draw_from_prompt("")

    def _font_sizes(self):
        w = max(self.width(), 240)
        # Scale with canvas width (points)
        title = _clamp(w / 62.0, 11.0, 18.0)
        room = _clamp(w / 72.0, 9.0, 15.0)
        return title, room

    def draw_from_prompt(self, prompt: str):
        self._last_prompt = prompt
        rooms = compute_rooms(prompt)
        title_fs, room_fs = self._font_sizes()
        self.ax.clear()
        self.ax.set_facecolor("#0B1220")
        self.ax.set_title(
            "Floor plan",
            fontsize=title_fs,
            fontweight="600",
            pad=max(8, title_fs * 0.85),
            color="#E2E8F0",
        )
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.set_aspect("equal")
        self.ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for spine in self.ax.spines.values():
            spine.set_color("#334155")

        for r in rooms:
            patch = patches.Rectangle(
                (r.x, r.y),
                r.w,
                r.h,
                linewidth=_clamp(self.width() / 520.0, 1.0, 2.2),
                edgecolor=r.edge,
                facecolor=r.fill,
                alpha=0.92,
            )
            self.ax.add_patch(patch)
            self.ax.text(
                r.x + r.w / 2,
                r.y + r.h / 2,
                r.label,
                ha="center",
                va="center",
                fontsize=room_fs,
                color="#0F172A",
                fontweight="600",
            )

        self.draw()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        nw = self.width()
        if abs(nw - self._last_w) < 12:
            return
        self._last_w = nw
        self.draw_from_prompt(self._last_prompt)


class PlanCanvas3D(FigureCanvas):
    def __init__(self):
        self.fig = Figure(facecolor="#0B1220", dpi=110)
        self.ax = self.fig.add_subplot(111, projection="3d")
        super().__init__(self.fig)
        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        self._default_view = (28, -52)
        self._last_prompt: str = ""
        self._last_w: int = 0
        self.draw_from_prompt("")

    def _font_sizes(self):
        w = max(self.width(), 280)
        tick = _clamp(w / 58.0, 10.0, 17.0)
        room = _clamp(w / 68.0, 9.0, 16.0)
        return tick, room

    def _grid_floor(self):
        g = "#1E293B"
        lw = _clamp(self.width() / 900.0, 0.45, 1.1)
        for i in np.linspace(0, 10, 11):
            self.ax.plot([i, i], [0, 10], [0, 0], color=g, linewidth=lw, alpha=0.85)
            self.ax.plot([0, 10], [i, i], [0, 0], color=g, linewidth=lw, alpha=0.85)

    def reset_camera(self):
        elev, azim = self._default_view
        self.ax.view_init(elev=elev, azim=azim)
        self.ax._dist = 7.2
        self.draw()

    def draw_from_prompt(self, prompt: str):
        self._last_prompt = prompt
        rooms = compute_rooms(prompt)
        tick_fs, room_fs = self._font_sizes()
        self.ax.clear()
        self.ax.set_facecolor("#0B1220")
        self.ax.set_box_aspect((10, 10, 3.5))
        self._grid_floor()

        z_scale = 0.42
        for r in rooms:
            dz = r.height * z_scale
            rgba = to_rgba(r.fill, alpha=0.88)
            self.ax.bar3d(
                r.x,
                r.y,
                0,
                r.w,
                r.h,
                dz,
                color=rgba,
                edgecolor=to_rgba(r.edge, alpha=0.95),
                linewidth=_clamp(self.width() / 700.0, 0.25, 0.65),
                shade=True,
            )
            self.ax.text(
                r.x + r.w / 2,
                r.y + r.h / 2,
                dz + 0.08,
                r.label,
                ha="center",
                va="bottom",
                fontsize=room_fs,
                color="#F1F5F9",
                fontweight="600",
            )

        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.set_zlim(
            0,
            max(3.8, max((rr.height * z_scale for rr in rooms), default=0) + 0.6),
        )
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")
        self.ax.set_zticks([])
        self.ax.tick_params(axis="x", colors="#CBD5E1", labelsize=tick_fs)
        self.ax.tick_params(axis="y", colors="#CBD5E1", labelsize=tick_fs)
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.xaxis.pane.set_edgecolor("#1E293B")
        self.ax.yaxis.pane.set_edgecolor("#1E293B")
        self.ax.zaxis.pane.set_edgecolor("#1E293B")
        self.ax.grid(False)

        elev, azim = self._default_view
        self.ax.view_init(elev=elev, azim=azim)
        self.ax._dist = 7.2
        self.draw()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        nw = self.width()
        if abs(nw - self._last_w) < 12:
            return
        self._last_w = nw
        self.draw_from_prompt(self._last_prompt)


class App(QWidget):
    DEMO_HINT = (
        "Tip: choose a quick scenario or describe a change, then Generate. "
        "In 3D, drag to orbit and scroll to zoom."
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlanFlow — Layout studio")
        self.setMinimumSize(1180, 700)
        self.setGeometry(60, 40, 1480, 820)

        self._scale_timer: Optional[QTimer] = None
        self._font_scale: float = 1.0

        root = QHBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(480)
        sidebar.setMaximumWidth(920)
        sidebar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        side = QVBoxLayout(sidebar)
        side.setSpacing(18)
        side.setContentsMargins(32, 32, 28, 32)

        self.badge = QLabel("  DEMO  ")
        side.addWidget(self.badge, alignment=Qt.AlignLeft)

        self.header = QLabel("PlanFlow")
        hf = QFont()
        hf.setWeight(QFont.DemiBold)
        self.header.setFont(hf)
        side.addWidget(self.header)

        self.sub = QLabel(
            "Natural-language layout edits, rendered as a live 2D plan "
            "and an interactive 3D massing model."
        )
        self.sub.setWordWrap(True)
        side.addWidget(self.sub)

        self.input = QTextEdit()
        self.input.setPlaceholderText(
            "Describe a change… e.g. add a powder bath near the living room"
        )
        self.input.setMinimumHeight(124)
        self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        side.addWidget(self.input)

        self.dd_label = QLabel("Quick scenarios")
        side.addWidget(self.dd_label)

        self.dropdown = QComboBox()
        self.dropdown.addItems(
            [
                "Add powder bath near living room",
                "Convert flex room to office",
                "Expand kitchen",
            ]
        )
        self.dropdown.setMinimumHeight(46)
        side.addWidget(self.dropdown)

        self.run_btn = QPushButton("Generate")
        self.run_btn.setMinimumHeight(48)
        self.run_btn.setDefault(True)
        self.run_btn.clicked.connect(self.run)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setMinimumHeight(48)
        self.reset_btn.setObjectName("ghostBtn")
        self.reset_btn.clicked.connect(self.reset_plan)
        side.addWidget(self.run_btn)
        side.addWidget(self.reset_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #1E293B; max-height: 1px; border: none;")
        side.addWidget(sep)

        self.out_label = QLabel("What changed")
        side.addWidget(self.out_label)

        self.output = QLabel(self.DEMO_HINT)
        self.output.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.output.setWordWrap(True)
        self.output.setMinimumHeight(148)
        self.output.setObjectName("summaryBox")
        side.addWidget(self.output)
        side.addStretch(1)

        self.canvas3d = PlanCanvas3D()
        self.canvas3d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas3d.setMinimumHeight(380)
        self.tb3d = NavigationToolbar(self.canvas3d, self)
        self.tb3d.setStyleSheet(
            "background: #0F172A; border: none; color: #CBD5E1; "
            "spacing: 6px; padding: 4px 8px;"
        )

        wrap3d = QVBoxLayout()
        wrap3d.setSpacing(0)
        wrap3d.setContentsMargins(0, 0, 0, 0)
        hint_row_3d = QHBoxLayout()
        hint_row_3d.setContentsMargins(16, 12, 16, 8)
        self.hint3d = QLabel(
            "Drag to rotate · scroll to zoom · use the toolbar below for pan / home"
        )
        self.hint3d.setWordWrap(True)
        self.cam_btn = QPushButton("Reset 3D view")
        self.cam_btn.setObjectName("ghostBtnSmall")
        self.cam_btn.setMinimumHeight(36)
        self.cam_btn.clicked.connect(self.canvas3d.reset_camera)
        hint_row_3d.addWidget(self.hint3d, 1)
        hint_row_3d.addWidget(self.cam_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        wrap3d.addLayout(hint_row_3d)
        wrap3d.addWidget(self.canvas3d, 1)
        wrap3d.addWidget(self.tb3d)

        w3d = QWidget()
        w3d.setLayout(wrap3d)

        self.canvas2d = PlanCanvas2D()
        self.canvas2d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas2d.setMinimumHeight(380)
        self.tb2d = NavigationToolbar(self.canvas2d, self)
        self.tb2d.setStyleSheet(
            "background: #0F172A; border: none; color: #CBD5E1; "
            "spacing: 6px; padding: 4px 8px;"
        )

        wrap2d = QVBoxLayout()
        wrap2d.setSpacing(0)
        self.hint2d = QLabel("Pan and zoom from the toolbar when you need a closer look.")
        wrap2d.addWidget(self.hint2d)
        wrap2d.addWidget(self.canvas2d, 1)
        wrap2d.addWidget(self.tb2d)

        w2d = QWidget()
        w2d.setLayout(wrap2d)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.addTab(w3d, "3D model")
        self.tabs.addTab(w2d, "2D plan")

        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(12, 10, 16, 12)
        right.addWidget(self.tabs, 1)

        right_w = QWidget()
        right_w.setLayout(right)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(sidebar)
        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([600, 880])

        root.addWidget(splitter)
        self.setLayout(root)

        self._apply_window_scale()

    def _px(self, base: float) -> int:
        return max(11, int(round(base * self._font_scale)))

    def _apply_window_scale(self):
        ww = max(self.width(), 900)
        self._font_scale = _clamp(ww / 1280.0, 0.92, 1.38)

        px = self._px
        self.badge.setStyleSheet(
            f"background: #1E293B; color: #38BDF8; font-size: {px(10)}px; "
            "font-weight: 800; letter-spacing: 2px; "
            f"padding: {px(6)}px {px(11)}px; border-radius: 6px;"
        )
        hf = self.header.font()
        hf.setPixelSize(px(26))
        hf.setWeight(QFont.DemiBold)
        self.header.setFont(hf)
        self.header.setStyleSheet("color: #F8FAFC; margin-top: 2px;")

        self.sub.setStyleSheet(
            f"color: #B8C5D4; font-size: {px(15)}px; line-height: 1.52; margin-top: 4px;"
        )
        self.dd_label.setStyleSheet(
            f"color: #E8EDF4; font-weight: 700; font-size: {px(14)}px;"
        )
        self.out_label.setStyleSheet(
            f"color: #E8EDF4; font-weight: 700; font-size: {px(14)}px;"
        )
        self.hint3d.setStyleSheet(
            f"background: #0F172A; color: #A8B8C8; font-size: {px(14)}px; padding: 4px 0;"
        )
        self.hint2d.setStyleSheet(
            f"background: #0F172A; color: #A8B8C8; font-size: {px(14)}px; "
            f"padding: {px(11)}px {px(15)}px {px(8)}px {px(15)}px;"
        )

        icon = max(20, px(22))
        self.tb3d.setIconSize(QSize(icon, icon))
        self.tb2d.setIconSize(QSize(icon, icon))

        self._apply_stylesheet()

        mh_in = max(120, int(110 * self._font_scale))
        mh_dd = max(42, int(44 * self._font_scale))
        self.input.setMinimumHeight(mh_in)
        self.dropdown.setMinimumHeight(mh_dd)
        self.run_btn.setMinimumHeight(max(44, int(48 * self._font_scale)))
        self.reset_btn.setMinimumHeight(max(44, int(48 * self._font_scale)))

        self.canvas2d.draw_from_prompt(self.canvas2d._last_prompt)
        self.canvas3d.draw_from_prompt(self.canvas3d._last_prompt)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._scale_timer is None:
            self._scale_timer = QTimer(self)
            self._scale_timer.setSingleShot(True)
            self._scale_timer.timeout.connect(self._on_debounced_scale)
        self._scale_timer.stop()
        self._scale_timer.start(45)

    def _on_debounced_scale(self):
        self._apply_window_scale()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_window_scale)

    def _apply_stylesheet(self):
        px = self._px
        fs = px(15)
        fs_tab = px(15)
        self.setStyleSheet(
            f"""
            QWidget#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #020617, stop:1 #0F172A);
                border-right: 1px solid #1E293B;
            }}
            QTextEdit {{
                border: 1px solid #334155;
                border-radius: 10px;
                padding: {px(14)}px;
                font-size: {fs}px;
                background: #0F172A;
                color: #E8EDF4;
                selection-background-color: #2563EB;
            }}
            QTextEdit:focus {{ border-color: #38BDF8; }}
            QComboBox {{
                border: 1px solid #334155;
                border-radius: 10px;
                padding: {px(10)}px {px(16)}px;
                background: #0F172A;
                color: #E8EDF4;
                font-size: {fs}px;
                min-height: {px(24)}px;
            }}
            QComboBox:focus {{ border-color: #38BDF8; }}
            QComboBox::drop-down {{ border: none; width: {px(28)}px; }}
            QComboBox QAbstractItemView {{
                background: #0F172A;
                color: #E8EDF4;
                selection-background-color: #1D4ED8;
                border: 1px solid #334155;
                font-size: {fs}px;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38BDF8, stop:1 #0284C7);
                color: #0F172A;
                border: none;
                border-radius: 10px;
                padding: {px(12)}px {px(22)}px;
                font-weight: 700;
                font-size: {fs}px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7DD3FC, stop:1 #0EA5E9);
            }}
            QPushButton:pressed {{ background: #0369A1; color: #F8FAFC; }}
            QPushButton#ghostBtn {{
                background: #1E293B;
                color: #E8EDF4;
                border: 1px solid #334155;
                font-weight: 600;
                font-size: {fs}px;
            }}
            QPushButton#ghostBtn:hover {{ background: #334155; }}
            QPushButton#ghostBtnSmall {{
                background: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: {px(8)}px {px(16)}px;
                font-weight: 600;
                font-size: {px(13)}px;
            }}
            QPushButton#ghostBtnSmall:hover {{
                background: #1E293B;
                color: #E8EDF0;
            }}
            QLabel#summaryBox {{
                color: #E8EDF4;
                font-size: {px(15)}px;
                line-height: 1.48;
                padding: {px(16)}px;
                background: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
            }}
            QTabWidget::pane {{
                border: none;
                background: #0F172A;
                top: -1px;
            }}
            QTabWidget#mainTabs QWidget {{ background: #0F172A; }}
            QTabBar::tab {{
                background: #0F172A;
                color: #94A3B8;
                padding: {px(12)}px {px(26)}px;
                font-weight: 700;
                font-size: {fs_tab}px;
                border-bottom: 2px solid transparent;
                min-height: {px(22)}px;
            }}
            QTabBar::tab:selected {{
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }}
            QTabBar::tab:hover {{ color: #E8EDF0; }}
            """
        )

    def reset_plan(self):
        self.canvas2d.draw_from_prompt("")
        self.canvas3d.draw_from_prompt("")
        self.output.setText(self.DEMO_HINT)

    def run(self):
        text = self.input.toPlainText().strip()
        if not text:
            text = self.dropdown.currentText()

        self.canvas2d.draw_from_prompt(text)
        self.canvas3d.draw_from_prompt(text)

        result = []
        tl = text.lower()
        if "bath" in tl:
            result.append("• Insert powder bath adjacent to the living zone.")
        if "office" in tl:
            result.append("• Repurpose the flex space as a dedicated office.")
        if "kitchen" in tl:
            result.append("• Extend the kitchen footprint along the east wall.")

        if result:
            self.output.setText("\n".join(result))
        else:
            self.output.setText(
                "No matching scenario — try a quick demo or mention bath, office, "
                "or expanding the kitchen."
            )


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("PlanFlow")
    app.setOrganizationName("PlanFlow Demo")
    window = App()
    window.show()
    sys.exit(app.exec_())
