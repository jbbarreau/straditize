# -*- coding: utf-8 -*-
"""A widget for controlling the appearance of markers
"""
from __future__ import division
import numpy as np
from itertools import chain
import matplotlib as mpl
import matplotlib.colors as mcol
from straditize.widgets import StraditizerControlBase, get_icon
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,
    QComboBox, QLineEdit, QDoubleValidator, QtGui, QTableWidget,
    QTableWidgetItem, Qt, with_qt5, QtCore, QGridLayout, QToolBar, QIcon)

if with_qt5:
    from PyQt5.QtWidgets import QHeaderView, QColorDialog
else:
    from PyQt4.QtGui import QHeaderView, QColorDialog


class ColorLabel(QTableWidget):
    """A QTableWidget with one cell and no headers to just display a color"""

    #: a signal that is emitted with an rgba color if the chosen color changes
    color_changed = QtCore.pyqtSignal(QtGui.QColor)

    def __init__(self, color='w', *args, **kwargs):
        """The color to display

        Parameters
        ----------
        color: object
            Either a QtGui.QColor object or a color that can be converted
            to RGBA using the :func:`matplotlib.colors.to_rgba` function"""
        super(ColorLabel, self).__init__(*args, **kwargs)
        self.setColumnCount(1)
        self.setRowCount(1)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalHeader().setHidden(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setHidden(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.itemClicked.connect(self.select_color)
        self.color_item = QTableWidgetItem()
        self.setItem(0, 0, self.color_item)
        self.adjust_height()
        self.set_color(color)

    def select_color(self, *args):
        """Select a color using :meth:`PyQt5.QtWidgets.QColorDialog.getColor`
        """
        self.set_color(QColorDialog.getColor(
            self.color_item.background().color()))

    def set_color(self, color):
        """Set the color of the label

        This method sets the given `color` as background color for the cell
        and emits the :attr:`color_changed` signal

        Parameters
        ----------
        color: object
            Either a QtGui.QColor object or a color that can be converted
            to RGBA using the :func:`matplotlib.colors.to_rgba` function"""
        color = self._set_color(color)
        self.color_changed.emit(color)

    def _set_color(self, color):
        if not isinstance(color, QtGui.QColor):
            color = QtGui.QColor(
                *map(int, np.round(mcol.to_rgba(color)) * 255))
        self.color_item.setBackground(color)
        return color

    def adjust_height(self):
        """Adjust the height to match the row height"""
        h = self.rowHeight(0) * self.rowCount()
        self.setMaximumHeight(h)
        self.setMinimumHeight(h)

    def sizeHint(self):
        """Reimplemented to use the rowHeight as height"""
        s = super(ColorLabel, self).sizeHint()
        return QtCore.QSize(s.width(), self.rowHeight(0) * self.rowCount())


class MarkerControl(StraditizerControlBase, QWidget):
    """Widget to control the appearance of the marks

    This widget controls the appearance of the
    :class:`straditize.cross_mark.CrossMark` instances in the
    :attr:`~straditize.straditizer.Straditizer.marks` attribute of the
    :attr:`~straditize.widgets.StraditizerControlBase.straditizer`"""

    _toolbar = None

    @property
    def marks(self):
        return chain(self.straditizer.marks, self.straditizer.magni_marks)

    def __init__(self, straditizer_widgets, *args, **kwargs):
        super(MarkerControl, self).__init__(*args, **kwargs)
        self.init_straditizercontrol(straditizer_widgets)
        vbox = QVBoxLayout()

        # auto hide button
        box_hide = QGridLayout()
        self.cb_auto_hide = QCheckBox('Auto-hide')
        self.cb_show_connected = QCheckBox('Show additionals')
        self.cb_drag_hline = QCheckBox('Drag in y-direction')
        self.cb_drag_vline = QCheckBox('Drag in x-direction')
        self.cb_selectable_hline = QCheckBox('Horizontal lines selectable')
        self.cb_selectable_vline = QCheckBox('Vertical lines selectable')
        self.cb_show_hlines = QCheckBox('Show horizontal lines')
        self.cb_show_vlines = QCheckBox('Show vertical lines')
        box_hide.addWidget(self.cb_auto_hide, 0, 0)
        box_hide.addWidget(self.cb_show_connected, 0, 1)
        box_hide.addWidget(self.cb_show_vlines, 1, 0)
        box_hide.addWidget(self.cb_show_hlines, 1, 1)
        box_hide.addWidget(self.cb_drag_hline, 2, 0)
        box_hide.addWidget(self.cb_drag_vline, 2, 1)
        box_hide.addWidget(self.cb_selectable_hline, 3, 0)
        box_hide.addWidget(self.cb_selectable_vline, 3, 1)
        vbox.addLayout(box_hide)

        style_box = QGridLayout()
        style_box.addWidget(QLabel('Unselected:'), 0, 1)
        selected_label = QLabel('Selected:')
        style_box.addWidget(selected_label, 0, 2)
        max_width = selected_label.sizeHint().width()

        # line color
        self.lbl_color_select = ColorLabel()
        self.lbl_color_unselect = ColorLabel()
        self.lbl_color_select.setMaximumWidth(max_width)
        self.lbl_color_unselect.setMaximumWidth(max_width)
        style_box.addWidget(QLabel('Line color:'), 1, 0)
        style_box.addWidget(self.lbl_color_unselect, 1, 1)
        style_box.addWidget(self.lbl_color_select, 1, 2)

        # line width
        self.txt_line_width = QLineEdit()
        self.txt_line_width_select = QLineEdit()

        validator = QDoubleValidator()
        validator.setBottom(0)
        self.txt_line_width.setValidator(validator)
        self.txt_line_width_select.setValidator(validator)

        style_box.addWidget(QLabel('Line width:'), 2, 0)
        style_box.addWidget(self.txt_line_width, 2, 1)
        style_box.addWidget(self.txt_line_width_select, 2, 2)

        vbox.addLayout(style_box)

        # line style
        hbox_line_style = QHBoxLayout()
        hbox_line_style.addWidget(QLabel('Line style'))
        self.combo_line_style = QComboBox()
        hbox_line_style.addWidget(self.combo_line_style)
        vbox.addLayout(hbox_line_style)
        self.fill_linestyles()
        self.combo_line_style.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # marker style
        hbox_marker_style = QHBoxLayout()
        hbox_marker_style.addWidget(QLabel('Marker size'))
        self.txt_marker_size = QLineEdit()
        self.txt_marker_size.setMinimumWidth(40)
        self.txt_marker_size.setText(str(mpl.rcParams['lines.markersize']))
        validator = QDoubleValidator()
        validator.setBottom(0)
        self.txt_marker_size.setValidator(validator)
        hbox_marker_style.addWidget(self.txt_marker_size)
        hbox_marker_style.addWidget(QLabel('Marker style'))
        self.combo_marker_style = QComboBox()
        hbox_marker_style.addWidget(self.combo_marker_style)
        vbox.addLayout(hbox_marker_style)

        self.setLayout(vbox)

        self.widgets2disable = [
            self.lbl_color_select, self.lbl_color_unselect,
            self.cb_auto_hide, self.txt_line_width, self.txt_line_width_select,
            self.combo_line_style, self.cb_show_connected,
            self.txt_marker_size, self.combo_marker_style,
            self.cb_drag_vline, self.cb_drag_hline,
            self.cb_selectable_vline, self.cb_selectable_hline,
            self.cb_show_hlines, self.cb_show_vlines]

        self.fill_markerstyles()

        self.tb_actions = []

        # ---------------------------------------------------------------------
        # ---------------------------- connections ----------------------------
        # ---------------------------------------------------------------------

        self.lbl_color_select.color_changed.connect(self.change_select_colors)
        self.lbl_color_unselect.color_changed.connect(
            self.change_unselect_colors)
        self.txt_line_width.textChanged.connect(self.change_line_widths)
        self.txt_line_width_select.textChanged.connect(
            self.change_selection_line_widths)
        self.cb_auto_hide.stateChanged.connect(self.change_auto_hide)
        self.combo_marker_style.currentIndexChanged.connect(
            self.change_marker_style)
        self.combo_line_style.currentIndexChanged.connect(
            self.change_line_style)
        self.txt_marker_size.textChanged.connect(self.change_marker_size)
        self.cb_show_connected.stateChanged.connect(
            self.change_show_connected_artists)
        self.cb_drag_hline.stateChanged.connect(self.change_hline_draggable)
        self.cb_drag_vline.stateChanged.connect(self.change_vline_draggable)
        self.cb_selectable_hline.stateChanged.connect(
            self.change_hline_selectable)
        self.cb_selectable_vline.stateChanged.connect(
            self.change_vline_selectable)
        self.cb_show_vlines.stateChanged.connect(self.change_show_vlines)
        self.cb_show_hlines.stateChanged.connect(self.change_show_hlines)

    def draw_figs(self):
        for canvas in {m.fig.canvas for m in self.marks}:
            canvas.draw_idle()

    def fill_linestyles(self):
        self.line_styles = [
            ('-', 'solid'),
            ('--', 'dashed'),
            ('-.', 'dashdot'),
            (':', 'dotted'),
            ('None', None, '', ' ')
            ]
        self.combo_line_style.addItems([t[0] for t in self.line_styles])

    def fill_markerstyles(self):
        self.marker_styles = [
            ('point', (".", )),
            ('pixel', (",", )),
            ('circle', ("o", )),
            ('triangle down', ("v", "1")),
            ('triangle up', ("^", "2")),
            ('triangle left', ("<", "3")),
            ('triangle right', (">", "4")),
            ('octagon', ("8", )),
            ('square', ("s", )),
            ('pentagon', ("p", )),
            ('plus (filled)', ("P", )),
            ('star', ("*", )),
            ('hexagon1', ("h", )),
            ('hexagon2', ("H", )),
            ('plus', ("+", )),
            ('x', ("x", )),
            ('x (filled)', ("X", )),
            ('diamond', ("D", )),
            ('thin diamond', ("d", )),
            ('vline', ("|", )),
            ('hline', ("_", )),
            ('no marker', ('None', None, '', ' '))
            ]
        self.combo_marker_style.addItems([
            '%s (%s)' % (key.capitalize(), ','.join(map(str, filter(None, t))))
            for key, t in self.marker_styles])

    def set_marker_item(self, marker):
        """Switch the :attr:`combo_marker_style` to the given `marker`

        Parameters
        ----------
        marker: str
            A matplotlib marker string"""
        for i, (key, t) in enumerate(self.marker_styles):
            if marker in t:
                block = self.combo_marker_style.blockSignals(True)
                self.combo_marker_style.setCurrentIndex(i)
                self.combo_marker_style.blockSignals(block)
                break

    def set_line_style_item(self, ls):
        """Switch the :attr:`combo_line_style` to the given linestyle

        Parameters
        ----------
        ls: str
            The matplotlib linestyle string
        """
        for i, t in enumerate(self.line_styles):
            if ls in t:
                block = self.combo_line_style.blockSignals(True)
                self.combo_line_style.setCurrentIndex(i)
                self.combo_line_style.blockSignals(block)
                break

    def should_be_enabled(self, w):
        """Check if a widget `w` should be enabled or disabled

        Parameters
        ----------
        w: PyQt5.QtWidgets.QWidget
            The widget to (potentially) enable

        Returns
        -------
        bool
            True if the :attr:`straditizer` of this instance has marks.
            Otherwise False"""
        return self.straditizer is not None and bool(self.straditizer.marks)

    def change_select_colors(self, color):
        """Change the selection color of the marks

        Change the selection color of the marks to the given color.

        Parameters
        ----------
        color: PyQt5.QtGui.QColor or a matplotlib color
            The color to use
        """
        if isinstance(color, QtGui.QColor):
            color = np.array(color.getRgb()) / 255.
        for mark in self.marks:
            key = 'color' if 'color' in mark._select_props else 'c'
            mark._select_props[key] = color
            mark._unselect_props[key] = mark.hline.get_c()
        self.draw_figs()

    def change_unselect_colors(self, color):
        """Change the :attr:`straditize.cross_mark.CrossMark.cunselect` color

        Change the unselection color of the marks to the given color.

        Parameters
        ----------
        color: PyQt5.QtGui.QColor or a matplotlib color
            The color to use
        """
        if isinstance(color, QtGui.QColor):
            color = np.array(color.getRgb()) / 255.
        for mark in self.marks:
            key = 'color' if 'color' in mark._unselect_props else 'c'
            mark._unselect_props[key] = color
            for l in chain(mark.hlines, mark.vlines, mark.line_connections):
                l.set_color(color)
        self.draw_figs()

    def change_line_widths(self, lw):
        """Change the linewidth of the marks

        Parameters
        ----------
        lw: float
            The line width to use
        """
        lw = float(lw or 0)
        for mark in self.marks:
            key = 'lw' if 'lw' in mark._unselect_props else 'linewidth'
            mark._unselect_props[key] = lw
            if not mark.auto_hide:
                for l in chain(mark.hlines, mark.vlines,
                               mark.line_connections):
                    l.set_lw(lw)
        self.draw_figs()

    def change_selection_line_widths(self, lw):
        lw = float(lw or 0)
        for mark in self.marks:
            key = 'lw' if 'lw' in mark._select_props else 'linewidth'
            mark._select_props[key] = lw

    def change_auto_hide(self, auto_hide):
        """Toggle the :attr:`~straditize.cross_mark.CrossMark.auto_hide`

        This method disables or enables the
        :attr:`~straditize.cross_mark.CrossMark.auto_hide` of the marks

        Parameters
        ----------
        auto_hide: bool or PyQt5.QtGui.Qt.Checked or PyQt5.QtGui.Qt.Unchecked
            The value to use for the auto_hide. :data:`PyQt5.QtGui.Qt.Checked`
            is equivalent to ``True``
        """
        if auto_hide is Qt.Checked:
            auto_hide = True
        elif auto_hide is Qt.Unchecked:
            auto_hide = False
        for mark in self.marks:
            mark.auto_hide = auto_hide
            if auto_hide:
                for l in chain(mark.hlines, mark.vlines,
                               mark.line_connections):
                    l.set_lw(0)
            else:
                lw = mark._unselect_props.get(
                    'lw', mark._unselect_props.get('linewidth'))
                for l in chain(mark.hlines, mark.vlines,
                               mark.line_connections):
                    l.set_lw(lw)
        self.draw_figs()

    def change_show_connected_artists(self, show):
        if show is Qt.Checked:
            show = True
        elif show is Qt.Unchecked:
            show = False
        for mark in self.marks:
            mark.set_connected_artists_visible(show)
        self.draw_figs()

    def change_line_style(self, i):
        """Change the line style of the marks

        Parameters
        ----------
        i: int
            The index of the line style in the :attr:`line_styles` attribute
            to use
        """
        ls = self.line_styles[i][0]
        for mark in self.marks:
            for l in chain(mark.hlines, mark.vlines, mark.line_connections):
                l.set_ls(ls)
        self.draw_figs()

    def change_marker_style(self, i):
        """Change the marker style of the marks

        Parameters
        ----------
        i: int
            The index of the marker style in the :attr:`marker_styles`
            attribute to use
        """
        marker = self.marker_styles[i][1][0]
        for mark in self.marks:
            for l in chain(mark.hlines, mark.vlines, mark.line_connections):
                l.set_marker(marker)
        self.draw_figs()

    def change_marker_size(self, markersize):
        """Change the size of the markers

        Parameters
        ----------
        markersize: float
            The size of the marker to use"""
        markersize = float(markersize or 0)
        for mark in self.marks:
            for l in chain(mark.hlines, mark.vlines, mark.line_connections):
                l.set_markersize(markersize)
        self.draw_figs()

    def fill_from_mark(self, mark):
        """Set the widgets of this :class:`MarkerControl` from a mark

        This method sets the color labels, combo boxes, check boxes and
        text edits to match the properties of the given `mark`

        Parameters
        ----------
        mark: straditize.cross_mark.CrossMark
            The mark to use the attributes from
        """
        line = mark.hline
        try:
            cselect = mark._select_props['c']
        except KeyError:
            try:
                cselect = mark._select_props['color']
            except KeyError:
                cselect = mark.hline.get_c()
        lw_key = 'lw' if 'lw' in mark._unselect_props else 'linewidth'
        self.set_line_style_item(line.get_linestyle())
        self.set_marker_item(line.get_marker())
        self.txt_line_width.setText(str(mark._unselect_props.get(lw_key, 0)))
        self.txt_line_width_select.setText(
            str(mark._select_props.get(lw_key, 0)))
        self.txt_marker_size.setText(str(line.get_markersize()))
        self.lbl_color_select._set_color(cselect)
        self.lbl_color_unselect._set_color(mark.hline.get_c())
        self.cb_auto_hide.setChecked(mark.auto_hide)
        self.cb_show_connected.setChecked(mark.show_connected_artists)
        try:
            mark.x
        except NotImplementedError:
            self.cb_drag_vline.setEnabled(False)
            self.cb_show_vlines.setEnabled(False)
            self.cb_selectable_vline.setEnabled(False)
        else:
            self.cb_drag_vline.setEnabled(True)
            self.cb_show_vlines.setEnabled(True)
            self.cb_selectable_vline.setEnabled(True)
        try:
            mark.y
        except NotImplementedError:
            self.cb_drag_hline.setEnabled(False)
            self.cb_show_hlines.setEnabled(False)
            self.cb_selectable_hline.setEnabled(False)
        else:
            self.cb_drag_hline.setEnabled(True)
            self.cb_show_hlines.setEnabled(True)
            self.cb_selectable_hline.setEnabled(True)
        self.cb_drag_hline.setChecked('h' in mark.draggable)
        self.cb_drag_vline.setChecked('v' in mark.draggable)
        self.cb_show_hlines.setChecked(not mark.hide_horizontal)
        self.cb_show_vlines.setChecked(not mark.hide_vertical)
        self.cb_selectable_hline.setChecked('h' in mark.selectable)
        self.cb_selectable_vline.setChecked('v' in mark.selectable)

    def change_hline_draggable(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.draggable = np.unique(np.r_[['h'], mark.draggable])
        else:
            for mark in self.marks:
                mark.draggable = np.array(list(set(mark.draggable) - {'h'}))

    def change_hline_selectable(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.selectable = np.unique(np.r_[['h'], mark.selectable])
        else:
            for mark in self.marks:
                mark.selectable = np.array(list(set(mark.selectable) - {'h'}))

    def change_vline_draggable(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.draggable = np.unique(np.r_[['v'], mark.draggable])
        else:
            for mark in self.marks:
                mark.draggable = np.array(list(set(mark.draggable) - {'v'}))

    def change_vline_selectable(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.selectable = np.unique(np.r_[['v'], mark.selectable])
        else:
            for mark in self.marks:
                mark.selectable = np.array(list(set(mark.selectable) - {'v'}))

    def change_show_hlines(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.hide_horizontal = False
                mark.set_visible(True)
        else:
            for mark in self.marks:
                mark.hide_horizontal = True
                mark.set_visible(True)
        self.draw_figs()

    def change_show_vlines(self, state):
        if state == Qt.Checked:
            for mark in self.marks:
                mark.hide_vertical = False
                mark.set_visible(True)
        else:
            for mark in self.marks:
                mark.hide_vertical = True
                mark.set_visible(True)
        self.draw_figs()

    def enable_or_disable_widgets(self, b):
        """Renabled to use the :meth:`refresh` method
        """
        self.refresh()

    def fill_after_adding(self, mark):
        if not self._filled:
            self.refresh()

    def go_to_right_mark(self):
        ax = self.straditizer.marks[0].ax
        if ax.xaxis_inverted():
            return self.go_to_smaller_x_mark(min(ax.get_xlim()))
        else:
            return self.go_to_greater_x_mark(max(ax.get_xlim()))

    def go_to_left_mark(self):
        ax = self.straditizer.marks[0].ax
        if ax.xaxis_inverted():
            return self.go_to_greater_x_mark(max(ax.get_xlim()))
        else:
            return self.go_to_smaller_x_mark(min(ax.get_xlim()))

    def go_to_greater_x_mark(self, x):
        ax = next(self.marks).ax
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        marks = self.straditizer.marks
        distances = (
            (mark.xa > x).any() and (mark.xa[mark.xa > x] - x).min()
            for mark in marks)
        try:
            dist, mark = min((t for t in zip(distances, marks) if t[0]),
                             key=lambda t: t[0])
        except ValueError:  # empty sequence
            return
        mask = mark.xa > x
        i = mark.xa[mask].argmin()
        x, y = mark.xa[mask][i], mark.ya[mask][i]
        dx = np.diff(xlim) / 2.
        ax.set_xlim(x - dx, x + dx)
        dy = np.diff(ylim) / 2.
        ax.set_ylim(y - dy, y + dy)
        self.straditizer.draw_figure()

    def go_to_smaller_x_mark(self, x):
        ax = next(self.marks).ax
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        marks = self.straditizer.marks
        distances = (
            (mark.xa < x).any() and (mark.xa[mark.xa < x] - x).min()
            for mark in marks)
        try:
            dist, mark = min((t for t in zip(distances, marks) if t[0]),
                             key=lambda t: t[0])
        except ValueError:  # empty sequence
            return
        mask = mark.xa < x
        i = mark.xa[mask].argmin()
        x, y = mark.xa[mask][i], mark.ya[mask][i]
        dx = np.diff(xlim) / 2.
        ax.set_xlim(x - dx, x + dx)
        dy = np.diff(ylim) / 2.
        ax.set_ylim(y - dy, y + dy)
        self.straditizer.draw_figure()

    def go_to_upper_mark(self):
        ax = self.straditizer.marks[0].ax
        if ax.xaxis_inverted():
            return self.go_to_greater_y_mark(max(ax.get_ylim()))
        else:
            return self.go_to_smaller_y_mark(min(ax.get_ylim()))

    def go_to_lower_mark(self):
        ax = self.straditizer.marks[0].ax
        if ax.xaxis_inverted():
            return self.go_to_smaller_y_mark(min(ax.get_ylim()))
        else:
            return self.go_to_greater_y_mark(max(ax.get_ylim()))

    def go_to_greater_y_mark(self, y):
        ax = next(self.marks).ax
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        marks = self.straditizer.marks
        distances = (
            (mark.ya > y).any() and (mark.xa[mark.ya > y] - y).min()
            for mark in marks)
        try:
            dist, mark = min((t for t in zip(distances, marks) if t[0]),
                             key=lambda t: t[0])
        except ValueError:  # empty sequence
            return
        mask = mark.ya > y
        i = mark.ya[mask].argmin()
        x, y = mark.xa[mask][i], mark.ya[mask][i]
        dx = np.diff(xlim) / 2.
        ax.set_xlim(x - dx, x + dx)
        dy = np.diff(ylim) / 2.
        ax.set_ylim(y - dy, y + dy)
        self.straditizer.draw_figure()

    def go_to_smaller_y_mark(self, y):
        ax = next(self.marks).ax
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        marks = self.straditizer.marks
        distances = (
            (mark.ya < y).any() and (mark.ya[mark.ya < y] - y).min()
            for mark in marks)
        try:
            dist, mark = min((t for t in zip(distances, marks) if t[0]),
                             key=lambda t: t[0])
        except ValueError:  # empty sequence
            return
        mask = mark.ya < y
        i = mark.ya[mask].argmin()
        x, y = mark.xa[mask][i], mark.ya[mask][i]
        dx = np.diff(xlim) / 2.
        ax.set_xlim(x - dx, x + dx)
        dy = np.diff(ylim) / 2.
        ax.set_ylim(y - dy, y + dy)
        self.straditizer.draw_figure()

    def add_toolbar_widgets(self, mark):
        tb = self.straditizer.marks[0].ax.figure.canvas.toolbar
        if not isinstance(tb, QToolBar):
            return
        if self.tb_actions:
            self.remove_actions()

        self.tb_actions.append(tb.addSeparator())
        try:
            mark.x
        except NotImplementedError:
            add_right = False
        else:
            a = tb.addAction(
                QIcon(get_icon('left_mark.png')), 'left mark',
                self.go_to_left_mark)
            a.setToolTip('Move to the next cross mark on the left')
            self.tb_actions.append(a)
            add_right = True

        try:
            mark.y
        except NotImplementedError:
            pass
        else:
            a = tb.addAction(
                QIcon(get_icon('upper_mark.png')), 'upper mark',
                self.go_to_upper_mark)
            a.setToolTip('Move to the next cross mark above')
            self.tb_actions.append(a)

            a = tb.addAction(
                QIcon(get_icon('lower_mark.png')), 'lower mark',
                self.go_to_lower_mark)
            a.setToolTip('Move to the next cross mark below')
            self.tb_actions.append(a)

        if add_right:
            a = tb.addAction(
                QIcon(get_icon('right_mark.png')), 'right mark',
                self.go_to_right_mark)
            a.setToolTip(
                'Move to the next cross mark on the right')
            self.tb_actions.append(a)
        self._toolbar = tb

    def remove_actions(self):
        if self._toolbar is None:
            return
        tb = self._toolbar
        for a in self.tb_actions:
            tb.removeAction(a)
        self.tb_actions.clear()

    def refresh(self):
        """Reimplemented to also set the properties of this widget
        """
        super(MarkerControl, self).refresh()
        if self.straditizer is not None and self.straditizer.marks:
            self._filled = True
            mark = self.straditizer.marks[0]
            self.fill_from_mark(mark)
            self.add_toolbar_widgets(mark)
        else:
            self.remove_actions()
            self._filled = False
        if self.straditizer is not None:
            self.straditizer.mark_added.connect(self.fill_after_adding)