"""Theme browser: visual previews of all twelve themes with live preview.

Hovering a theme previews it instantly in the whole application; clicking
selects it, and Apply/OK commits. Cancel restores the previous theme.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPen, QResizeEvent)
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSlider, QVBoxLayout, QWidget, QCheckBox,
                               QGridLayout as _G)

from ..themes.definitions import ALL_THEMES
from ..themes.manager import build_stylesheet
from ..themes.models import Theme
from .icons import draw_logo, icon


class ThemeCard(QFrame):
    """A miniature preview of a theme: chrome, panel, canvas, and a page."""

    clicked = Signal(str)
    hovered = Signal(str)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(190, 150)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def set_selected(self, on: bool) -> None:
        self._selected = on
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._theme.id)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit(self._theme.id)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._theme
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setClipRect(r)

        # window background
        p.fillRect(r, QColor(t.window_bg))

        # toolbar strip
        p.fillRect(QRectF(r.left(), r.top(), r.width(), 22), QColor(t.toolbar_bg))
        p.setPen(QPen(QColor(t.border)))
        p.drawLine(r.left(), r.top() + 22, r.right(), r.top() + 22)
        # toolbar buttons
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.accent))
        p.drawRoundedRect(QRectF(6, 7, 9, 9), 2, 2)
        p.setBrush(QColor(t.button_bg))
        for i in range(3):
            p.drawRoundedRect(QRectF(r.width() - 56 + i * 17, 7, 12, 9), 2, 2)

        # side panel
        p.fillRect(QRectF(r.left(), r.top() + 23, 38, r.height() - 23),
                   QColor(t.panel_bg))
        p.setPen(QPen(QColor(t.border)))
        p.drawLine(38, r.top() + 23, 38, r.bottom())
        # panel rows
        p.setPen(QPen(QColor(t.text_muted)))
        for i in range(4):
            y = r.top() + 32 + i * 12
            p.setPen(QPen(QColor(t.selection_bg if i == 1 else t.text_muted)))
            p.drawLine(6, y, 31, y)

        # canvas + page pair
        canvas = QRectF(39, r.top() + 23, r.width() - 39, r.height() - 23)
        p.fillRect(canvas, QColor(t.canvas_bg))
        if t.effects.wood:
            p.setPen(QPen(QColor(t.canvas_bg).lighter(120)))
            for x in range(int(canvas.left()), int(canvas.right()), 9):
                p.drawLine(x, int(canvas.top()), x + 2, int(canvas.bottom()))
        if t.effects.stars:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t.accent))
            import random
            rng = random.Random(hash(t.id) & 0xffff)
            for _ in range(40):
                x = rng.randrange(int(canvas.left()), max(int(canvas.left()) + 1, int(canvas.right())))
                y = rng.randrange(int(canvas.top()), max(int(canvas.top()) + 1, int(canvas.bottom())))
                p.drawEllipse(x, y, 1, 1)
        if t.effects.grid:
            p.setPen(QPen(QColor(t.accent), 1, Qt.PenStyle.DotLine))
            for x in range(int(canvas.left()) + 8, int(canvas.right()), 12):
                p.drawLine(x, int(canvas.top()), x, int(canvas.bottom()))
            for y in range(int(canvas.top()) + 8, int(canvas.bottom()), 12):
                p.drawLine(int(canvas.left()), y, int(canvas.right()), y)
        if t.effects.horizon:
            p.setPen(QPen(QColor(t.accent), 1))
            hy = int(canvas.bottom()) - 22
            p.drawLine(int(canvas.left()), hy, int(canvas.right()), hy)

        # the "open book": two page rectangles with spine
        margin = 12
        pw = (canvas.width() - 2 * margin - 4) / 2
        ph = min(canvas.height() - 2 * margin, pw * 1.35)
        px = canvas.left() + margin
        py = canvas.top() + (canvas.height() - ph) / 2
        if ph > 10 and pw > 8:
            for i in range(2):
                pg = QRectF(px + i * (pw + 4), py, pw, ph)
                p.fillRect(pg.adjusted(0, 0, 0, 0), QColor(t.page_shadow))
                p.fillRect(pg.adjusted(1.5, 2, -1, -1.5), QColor("#fbf7ec"))
                p.setPen(QPen(QColor("#b9b0a0")))
                for li in range(5):
                    ly = pg.top() + 8 + li * 5
                    p.drawLine(int(pg.left() + 5), int(ly), int(pg.right() - 5), int(ly))
            # spine
            spine = QRectF(px + pw + 0.5, py, 3, ph)
            g = QLinearGradient(spine.left(), 0, spine.right(), 0)
            g.setColorAt(0, QColor(t.page_shadow))
            g.setColorAt(0.5, QColor(t.spine_color))
            g.setColorAt(1, QColor(t.page_shadow))
            p.fillRect(spine, g)

        # status bar strip
        p.fillRect(QRectF(r.left(), r.bottom() - 12, r.width(), 12),
                   QColor(t.toolbar_bg))
        p.setPen(QPen(QColor(t.text_muted)))
        p.setFont(QFont("Monospace", 6))
        p.drawText(QRectF(r.left() + 6, r.bottom() - 12, r.width() - 6, 12),
                   Qt.AlignmentFlag.AlignVCenter, "12 / 240     100%")

        p.setClipping(False)
        # frame + selection
        border = QColor(t.accent) if self._selected else QColor(t.border)
        pen = QPen(border, 2 if self._selected else 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 5, 5)
        if self._selected:
            p.setPen(QPen(QColor(t.accent_text) if t.dark else QColor(t.accent)))
            p.setFont(QFont("", 7, QFont.Weight.Bold))
            p.drawText(r.adjusted(6, 4, -6, -4),
                       Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, "✓")
        p.end()


class ThemeBrowser(QDialog):
    """Grid of theme cards with preview-on-hover and accent controls."""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.tm = theme_manager
        self._original_id = theme_manager.theme.id
        self._selected_id = theme_manager.theme.id
        self.setWindowTitle("ABNORA — Themes")
        self.setMinimumSize(880, 620)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        head = QLabel("Twelve worlds")
        head.setObjectName("AppTitle")
        root.addWidget(head)
        sub = QLabel("Hover to preview instantly · click to choose · Apply to commit")
        sub.setProperty("role", "muted")
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setSpacing(12)
        self.cards: dict[str, ThemeCard] = {}
        for i, theme in enumerate(ALL_THEMES):
            card = ThemeCard(theme)
            card.clicked.connect(self._on_card_clicked)
            card.hovered.connect(self._on_card_hovered)
            self.cards[theme.id] = card
            col = i % 3
            row = i // 3
            box = QVBoxLayout()
            box.setSpacing(3)
            box.addWidget(card)
            name = QLabel(theme.name)
            name.setProperty("role", "heading")
            box.addWidget(name)
            desc = QLabel(theme.description)
            desc.setWordWrap(True)
            desc.setProperty("role", "muted")
            box.addWidget(desc)
            holder = QWidget()
            holder.setLayout(box)
            self.grid.addWidget(holder, row, col)
        for c in range(3):
            self.grid.setColumnStretch(c, 1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        # options row
        opts = QHBoxLayout()
        opts.setSpacing(14)

        opts.addWidget(QLabel("Accent:"))
        self._accent_buttons = QButtonGroup(self)
        for i, (label, color) in enumerate((
            ("Default", None), ("Bronze", "#8a6a3d"), ("Crimson", "#b03a48"),
            ("Cyan", "#2fb6c9"), ("Violet", "#8d7bff"), ("Green", "#5aa05a"),
        )):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setFixedHeight(26)
            b.setProperty("accent", "false")
            if color:
                b.setStyleSheet(
                    f"QPushButton {{ border-left: 6px solid {color}; }}")
            b.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            self._accent_buttons.addButton(b, i)
            opts.addWidget(b)
            if color is None:
                b.setChecked(True)
            b._color = color  # type: ignore[attr-defined]

        opts.addSpacing(10)
        opts.addWidget(QLabel("UI font size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(-3, 5)
        self.font_slider.setValue(self.tm.ui_font_scale)
        self.font_slider.setFixedWidth(120)
        self.font_slider.valueChanged.connect(self._set_font_scale)
        opts.addWidget(self.font_slider)
        self.font_label = QLabel(f"{self.tm.base_font_size()}px")
        self.font_label.setProperty("role", "mono")
        opts.addWidget(self.font_label)

        self.motion_check = QCheckBox("Reduced motion")
        self.motion_check.setChecked(self.tm.reduced_motion)
        self.motion_check.toggled.connect(self._set_motion)
        opts.addWidget(self.motion_check)

        opts.addStretch(1)
        root.addLayout(opts)

        # effect toggles + actions
        bottom = QHBoxLayout()
        self.effects_label = QLabel("")
        self.effects_label.setProperty("role", "muted")
        bottom.addWidget(self.effects_label)
        bottom.addStretch(1)

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset)
        bottom.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._cancel)
        bottom.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("accent", "true")
        apply_btn.clicked.connect(self._apply)
        bottom.addWidget(apply_btn)
        root.addLayout(bottom)

        self._mark_selected(self._selected_id)
        self._update_effects_label()

    # ------------------------------------------------------------- actions

    def _on_card_clicked(self, theme_id: str) -> None:
        self._selected_id = theme_id
        self.tm.set_theme(theme_id, persist=False)
        self._mark_selected(theme_id)
        self._update_effects_label()

    def _on_card_hovered(self, theme_id: str) -> None:
        if theme_id != self.tm.theme.id:
            self.tm.set_theme(theme_id, persist=False)

    def _mark_selected(self, theme_id: str) -> None:
        for tid, card in self.cards.items():
            card.set_selected(tid == theme_id)

    def _update_effects_label(self) -> None:
        t = self.tm.theme
        fx = [n for n, v in t.effects.__dict__.items() if v]
        self.effects_label.setText(
            f"Theme: {t.name}  ·  effects: {', '.join(fx) if fx else 'none'}")

    def _set_accent(self, color: str | None) -> None:
        self.tm.set_accent(color, persist=False)

    def _set_font_scale(self, v: int) -> None:
        self.tm.set_ui_font_scale(v, persist=False)
        self.font_label.setText(f"{self.tm.base_font_size()}px")

    def _set_motion(self, on: bool) -> None:
        self.tm.set_reduced_motion(on, persist=False)

    def _reset(self) -> None:
        self._selected_id = self._original_id
        self.tm.reset()
        self._mark_selected(self.tm.theme.id)
        self.font_slider.setValue(0)
        self.motion_check.setChecked(False)
        self._accent_buttons.button(0).setChecked(True)
        self._update_effects_label()

    def _apply(self) -> None:
        self.tm.set_theme(self._selected_id, persist=True)
        self.accept()

    def _cancel(self) -> None:
        # restore whatever theme was active when the dialog opened
        self.tm.set_theme(self._original_id, persist=False)
        self.reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.tm.set_theme(self._original_id, persist=False)
        super().closeEvent(event)
