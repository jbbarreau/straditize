"""The main control widget for handling the data
"""
from __future__ import division
import warnings
import os
import six
import glob
import re
import numpy as np
import pandas as pd
from straditize.widgets import (
    StraditizerControlBase, read_doc_file, get_doc_file, get_icon)
from psyplot_gui.compat.qtcompat import (
    QPushButton, QLineEdit, QComboBox, QLabel, QDoubleValidator,
    Qt, QHBoxLayout, QVBoxLayout, QWidget, QTreeWidgetItem, QtGui,
    QTableWidget, QTableWidgetItem, QtCore, QMenu, QAction, with_qt5,
    QIcon, QIntValidator, QTreeWidget, QToolBar, QGridLayout, QCheckBox,
    QInputDialog, QFileDialog)
from itertools import chain

if with_qt5:
    from PyQt5.QtWidgets import QGroupBox, QSpinBox
else:
    from PyQt4.QtGui import QGroupBox, QSpinBox

if six.PY2:
    from itertools import (
        izip_longest as zip_longest, ifilterfalse as filterfalse)
else:
    from itertools import zip_longest, filterfalse


reader_types = ['area', 'bars', 'rounded bars', 'stacked area',
                'line']


def int_list2str(numbers):
    """Create a short string representation of an integer list

    Parameters
    ----------
    numbers: list of ints
        Integer list

    Returns
    -------
    str
        The string representation

    Examples
    --------
    ``[1, 2, 3]`` becomes ``'1-3'``,
    ``[1, 2, 3, 5, 7, 8, 9]`` becomes ``'1-3, 5, 7-9'``"""
    numbers = sorted(map(int, numbers))
    s = str(numbers[0])
    for last, curr, nex in zip_longest(numbers[:-1], numbers[1:], numbers[2:]):
        if curr - last <= 1 and nex and nex - curr <= 1:
            continue
        elif curr - last <= 1:
            s += '-%s' % curr
        else:
            s += ', %s' % curr
    return s


def get_reader_name(reader):
    from straditize.binary import readers
    # import stacked_area_reader to make sure StackedReader is registered
    import straditize.widgets.stacked_area_reader
    for key, cls in readers.items():
        if reader.__class__ is cls:
            return key


class DigitizingControl(StraditizerControlBase):

    @property
    def reader(self):
        return self.straditizer.data_reader

    @property
    def tree(self):
        return self.straditizer_widgets.tree

    #: Button for selecting the data box
    btn_select_data = None

#    #: Button for selecting colors to ignore
#    btn_add_bc_colors = None

    #: Combobox for selecting the reader type
    cb_reader_type = None

    #: Button for initializing the reader
    btn_init_reader = None

    #: Button for selecting and modifying column separators
    btn_column_starts = None

    #: Button for removing disconnected parts in the plot
    btn_show_disconnected_parts = None

    #: LineEditor for specifying the fraction of vertical and horizontal lines
    txt_line_fraction = None

    #: Button for removing vertical lines
    btn_remove_vlines = None

    #: button for removing horizontal lines
    btn_remove_hlines = None

    #: Button for digitizing the diagram
    btn_digitize = None

    #: Line edit for setting the tolerance for bars
    txt_tolerance = None

    _change_reader = True

    digitize_item = None

    @property
    def selection_toolbar(self):
        return self.straditizer_widgets.selection_toolbar

    def __init__(self, straditizer_widgets):
        self.init_straditizercontrol(straditizer_widgets)

        # ---------------------------------------------------------------------
        # --------------------------- Buttons ---------------------------------
        # ---------------------------------------------------------------------

        self.btn_select_data = QPushButton('Select data part')
        self.btn_select_data.setToolTip(
            'Create marks for selecting the data in the image')

        self.cb_reader_type = cb = QComboBox()
        cb.setEditable(False)
        cb.addItems(reader_types)
        cb.setCurrentIndex(0)

        self.btn_init_reader = QPushButton('Convert image')
        self.btn_init_reader.setToolTip(
            'Convert the image to a binary image that can be read')

        self.txt_column_thresh = QLineEdit()
        self.txt_column_thresh.setValidator(QDoubleValidator(0, 100, 10))
        self.txt_column_thresh.setToolTip(
            'The fraction between 0 and 100 that has to be covered for a '
            'valid column start. Set this to a low value, e.g. 1, if you have '
            'columns with only a little bit of data.')
        self.txt_column_thresh.setText('10')

        self.btn_column_starts = QPushButton('Column starts')
        self.btn_column_starts.setToolTip(
            'Modify the column starts in the diagram')

        self.btn_column_ends = QPushButton('ends')
        self.btn_column_ends.setToolTip(
            'Modify the column ends in the diagram')

        self.btn_reset_columns = QPushButton('Reset')
        self.btn_reset_columns.setToolTip(
            'Reset the column starts')

        self.btn_align_vertical = QPushButton('Align columns')
        self.btn_align_vertical.setToolTip('Align the columns vertically')

        # column specific readers
        self.cb_readers = QComboBox()
        self.cb_readers.setEditable(False)

        self.btn_new_child_reader = QPushButton('+')

        self.txt_exag_factor = QLineEdit()
        self.txt_exag_factor.setValidator(QDoubleValidator(1, 100, 4))
        self.txt_exag_factor.setText('10')
        self.txt_exag_factor.setPlaceholderText('1-100')
        self.txt_exag_factor.setToolTip(
            'The factor that the data is exaggerated.')

        self.cb_exag_reader_type = cb = QComboBox()
        cb.setEditable(False)
        cb.addItems(reader_types)
        cb.setCurrentIndex(0)

        self.btn_new_exaggeration = QPushButton('+')
        self.btn_select_exaggerations = QPushButton('Select exaggerations')
        self.btn_select_exaggerations.setToolTip(
            'Select the features that represent the exaggerations')

        self.txt_exag_percentage = QLineEdit()
        self.txt_exag_percentage.setText('5')
        self.txt_exag_percentage.setValidator(QDoubleValidator(0, 100, 4))
        self.txt_exag_percentage.setPlaceholderText('0-100%')
        self.txt_exag_percentage.setToolTip(
            'The percentage of the column width under which the exaggerated '
            'digitized result shall be used.')
        self.txt_exag_absolute = QLineEdit()
        self.txt_exag_absolute.setText('8')
        self.txt_exag_absolute.setValidator(QIntValidator(0, 100000))
        self.txt_exag_absolute.setPlaceholderText('1,2,3,... px')
        self.txt_exag_absolute.setToolTip(
            'The absolute pixel value under which the exaggerated '
            'digitized result shall be used.')

        self.btn_digitize_exag = QPushButton('Digitize exaggerations')
        self.btn_digitize_exag.setToolTip('Digitize the exaggerations')

        self.btn_show_disconnected_parts = QPushButton('Disconnected features')
        self.btn_show_disconnected_parts.setToolTip(
            'Highlight the disconnected features in the binary image, i.e. '
            'features that are not associated with the data and might be '
            'picture artifacts')

        self.txt_fromlast = QLineEdit()
        self.txt_fromlast.setValidator(QIntValidator())
        self.txt_fromlast.setText('5')
        self.txt_fromlast.setToolTip(
            'Number of pixels after which a feature is regarded as '
            'disconnected from the previous feature.')
        self.cb_fromlast = QCheckBox('from previous feature by')
        self.cb_fromlast.setChecked(True)

        self.txt_from0 = QLineEdit()
        self.txt_from0.setValidator(QIntValidator(0, 100000))
        self.txt_from0.setText('10')
        self.txt_from0.setToolTip(
            'Number of pixels after which a feature is regarded as '
            'disconnected from the column start.')
        self.cb_from0 = QCheckBox('from column start by')
        self.cb_from0.setChecked(True)

        self.btn_show_cross_column = QPushButton('Cross column features')
        self.btn_show_cross_column.setToolTip(
            'Highlight features that cross multiple columns.')

        self.txt_cross_column_px = QLineEdit()
        self.txt_cross_column_px.setValidator(QIntValidator(0, 100000))
        self.txt_cross_column_px.setText('50')
        self.txt_cross_column_px.setToolTip(
            'The number of pixels that must be in any of the columns')

        self.btn_show_small_parts = QPushButton(
            'Small features')
        self.btn_show_small_parts.setToolTip(
            'Remove features smaller than 6 pixels')
        self.txt_min_size = QLineEdit()
        self.txt_min_size.setValidator(QIntValidator())
        self.txt_min_size.setText('6')

        self.btn_highlight_small_selection = QPushButton(
            'Highlight selection smaller than')
        self.btn_highlight_small_selection.setCheckable(True)
        self.txt_min_highlight = QLineEdit()
        self.txt_min_highlight.setValidator(QIntValidator())
        self.txt_min_highlight.setText('20')

        self.btn_show_parts_at_column_ends = QPushButton(
            'Features at column ends')
        self.btn_show_parts_at_column_ends.setToolTip(
            'Highlight the features in the binary image, that touch the end '
            'of the corresponding column')

        self.txt_line_fraction = QLineEdit()
        self.txt_line_fraction.setValidator(QDoubleValidator(0.0, 100.0, 5))
        self.txt_line_fraction.setText('75.0')
        self.txt_line_fraction.setToolTip(
            'The percentage that shall be used to identify a straight line')

        self.sp_min_lw = QSpinBox()
        self.sp_min_lw.setValue(2)
        self.sp_min_lw.setMaximum(10000)
        self.sp_min_lw.setToolTip(
            'Set the minimal width for selected vertical or horizontal lines')

        self.cb_max_lw = QCheckBox('Maximum line width')
        self.sp_max_lw = QSpinBox()
        self.sp_max_lw.setMaximum(10000)
        self.sp_max_lw.setValue(20)
        self.sp_max_lw.setToolTip(
            'Set the maximal width for selected vertical or horizontal lines')
        self.sp_max_lw.setEnabled(False)

        self.btn_remove_vlines = QPushButton('vertical lines')
        self.btn_remove_vlines.setToolTip(
            'Remove vertical lines, i.e. y-axes')

        self.btn_remove_hlines = QPushButton('horizontal lines')
        self.btn_remove_vlines.setToolTip(
            'Remove horizonal lines, i.e. lines parallel to the x-axis')

        self.btn_digitize = QPushButton('Digitize')
        self.btn_digitize.setToolTip('Digitize the binary file')

        self.btn_find_samples = QPushButton('Find samples')
        self.btn_find_samples.setToolTip(
            'Estimate positions of the samples in the diagram')

        self.btn_load_samples = QPushButton('Load samples')
        self.btn_load_samples.setToolTip(
            'Load the sample locations from a CSV file')

        self.btn_edit_samples = QPushButton('Edit samples')
        self.btn_edit_samples.setToolTip(
            'Modify and edit the samples')
        self.btn_reset_samples = QPushButton('Reset')
        self.btn_reset_samples.setToolTip('Reset the samples')

        self.cb_edit_separate = QCheckBox('In separate figure')
        self.cb_edit_separate.setToolTip(
            'Edit the samples in a separate figure where you have one '
            'plot for each column')
        self.txt_edit_rows = QLineEdit()
        self.txt_edit_rows.setValidator(QIntValidator(1, 1000))
        self.txt_edit_rows.setToolTip(
            'The number of plot rows in the editing figure?')
        self.txt_edit_rows.setText('3')
        self.txt_edit_rows.setEnabled(False)

        self.txt_min_len = QLineEdit()
        self.txt_min_len.setToolTip(
            'Minimum length of a potential sample to be included')
        self.txt_max_len = QLineEdit()
        self.txt_max_len.setText('8')
        self.txt_max_len.setToolTip(
            'Maximum length of a potential sample to be included')
        self.sp_pixel_tol = QSpinBox()
        self.sp_pixel_tol.setMaximum(10000)
        self.sp_pixel_tol.setValue(5)
        self.sp_pixel_tol.setToolTip(
            'Minimum distance between two measurements in pixels')

        self.tree_bar_split = BarSplitter(straditizer_widgets)

        self.widgets2disable = [
            self.btn_column_starts, self.btn_column_ends,
            self.cb_readers, self.btn_new_child_reader,
            self.txt_exag_factor, self.cb_exag_reader_type,
            self.txt_exag_percentage, self.txt_exag_absolute,
            self.btn_digitize_exag,
            self.btn_new_exaggeration, self.btn_select_exaggerations,
            self.btn_select_data, self.btn_remove_hlines,
            self.btn_reset_columns, self.btn_reset_samples,
            self.btn_remove_vlines, self.txt_line_fraction,
            self.sp_max_lw, self.sp_min_lw,
            self.btn_show_disconnected_parts, self.txt_fromlast,
            self.btn_show_cross_column, self.txt_cross_column_px,
            self.btn_show_parts_at_column_ends,
            self.btn_show_small_parts, self.txt_min_size,
            self.btn_align_vertical,
            self.btn_edit_samples, self.btn_find_samples,
            self.btn_load_samples]

        self.init_reader_kws = {}

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------

        self.btn_select_data.clicked.connect(self.select_data_part)
        self.btn_column_starts.clicked.connect(self.select_column_starts)
        self.btn_column_ends.clicked.connect(self.modify_column_ends)
        self.btn_reset_columns.clicked.connect(self.reset_column_starts)
        self.cb_reader_type.currentTextChanged.connect(
            self.toggle_txt_tolerance)
        self.btn_init_reader.clicked.connect(self.init_reader)
        self.btn_digitize.clicked.connect(self.digitize)
        self.btn_digitize_exag.clicked.connect(self.digitize_exaggerations)
        self.btn_digitize.clicked.connect(self.straditizer_widgets.refresh)
        self.btn_remove_hlines.clicked.connect(self.remove_hlines)
        self.btn_remove_vlines.clicked.connect(self.remove_vlines)
        self.btn_show_disconnected_parts.clicked.connect(
            self.show_disconnected_parts)
        self.btn_show_parts_at_column_ends.clicked.connect(
            self.show_parts_at_column_ends)
        self.btn_align_vertical.clicked.connect(self.align_vertical)
        self.btn_find_samples.clicked.connect(self.find_samples)
        self.btn_load_samples.clicked.connect(self.load_samples)
        self.btn_edit_samples.clicked.connect(self.edit_samples)
        self.btn_reset_samples.clicked.connect(self.reset_samples)
        self.btn_show_small_parts.clicked.connect(self.show_small_parts)
        self.txt_min_size.textChanged.connect(
            self._update_btn_show_small_parts)
        self.txt_min_highlight.textChanged.connect(
            self._update_btn_highlight_small_selection)
        self.btn_highlight_small_selection.toggled.connect(
            self.toggle_btn_highlight_small_selection)
        self.cb_from0.stateChanged.connect(self.toggle_txt_from0)
        self.cb_fromlast.stateChanged.connect(self.toggle_txt_fromlast)
        self.btn_show_cross_column.clicked.connect(
            self.show_cross_column_features)
        self.btn_new_child_reader.clicked.connect(
            self.enable_col_selection_for_new_reader)
        self.cb_readers.currentTextChanged.connect(self.change_reader)
        self.btn_new_exaggeration.clicked.connect(self.init_exaggerated_reader)
        self.btn_select_exaggerations.clicked.connect(
            self.select_exaggerated_features)
        self.cb_edit_separate.stateChanged.connect(self.toggle_txt_edit_rows)
        self.cb_max_lw.stateChanged.connect(self.toggle_sp_max_lw)

        # disable warning if bars cannot be separated
        warnings.filterwarnings('ignore', 'Could not separate bars',
                                UserWarning)

    def refresh(self):
        super(DigitizingControl, self).refresh()
        self.tree_bar_split.refresh()
        self.bar_split_child.setHidden(not self.tree_bar_split.filled)
        if self.tree_bar_split.filled:
            self.bar_split_child.setText(0, 'Split %i too long columns' % (
                sum(map(len, self.straditizer.data_reader._splitted.values())))
                )
        self.maybe_show_btn_reset_columns()
        self.maybe_show_btn_reset_samples()
        for w in [self.btn_init_reader, self.btn_digitize]:
            w.setEnabled(self.should_be_enabled(w))
        self.enable_or_disable_btn_highlight_small_selection()
        if (self.straditizer is not None and
                self.straditizer.data_reader is not None):
            self.cb_reader_type.setCurrentText(get_reader_name(
                self.straditizer.data_reader))
            reader = self.straditizer.data_reader.exaggerated_reader
            self.cb_exag_reader_type.setCurrentText(get_reader_name(
                reader or self.straditizer.data_reader))
            if reader is not None:
                self.txt_exag_factor.setText(str(reader.is_exaggerated))
        self.fill_cb_readers()

    def toggle_sp_max_lw(self, state):
        self.sp_max_lw.setEnabled(state == Qt.Checked)

    def toggle_txt_fromlast(self, state):
        self.txt_fromlast.setEnabled(state == Qt.Checked)

    def toggle_txt_edit_rows(self, state):
        self.txt_edit_rows.setEnabled(state == Qt.Checked)

    def toggle_txt_from0(self, state):
        self.txt_from0.setEnabled(state == Qt.Checked)

    def enable_or_disable_widgets(self, *args, **kwargs):
        super(DigitizingControl, self).enable_or_disable_widgets(*args,
                                                                 **kwargs)
        if not self.tree_bar_split.isHidden():
            self.tree_bar_split.enable_or_disable_widgets(*args, **kwargs)
        self.maybe_show_btn_reset_columns()
        self.maybe_show_btn_reset_samples()
        self.toggle_txt_tolerance(self.cb_reader_type.currentText())
        self.enable_or_disable_btn_highlight_small_selection()

    def enable_or_disable_btn_highlight_small_selection(self):
        enable = self.should_be_enabled(self.btn_highlight_small_selection)
        self.btn_highlight_small_selection.setEnabled(enable)
        self.btn_highlight_small_selection.setChecked(
            enable and bool(self.selection_toolbar.data_obj._ellipses))

    def maybe_show_btn_reset_columns(self):
        show = self.should_be_enabled(self.btn_reset_columns)
        self.btn_reset_columns.setVisible(show)
        self.btn_column_ends.setVisible(show)

    def maybe_show_btn_reset_samples(self):
        self.btn_reset_samples.setVisible(
            self.should_be_enabled(self.btn_reset_samples))

    def update_tolerance(self, s):
        if (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                hasattr(self.straditizer.data_reader, 'tolerance')):
            self.straditizer.data_reader.tolerance = int(s or 0)

    def toggle_txt_tolerance(self, s):
        enable = 'bars' in s
        if enable:
            if self.txt_tolerance is None:
                self.tolerance_child = QTreeWidgetItem(0)
                self.lbl_tolerance = QLabel('Tolerance:')
                self.txt_tolerance = QLineEdit()
                validator = QIntValidator()
                validator.setBottom(0)
                self.txt_tolerance.setValidator(validator)
                self.txt_tolerance.setEnabled(False)
                self.txt_tolerance.textChanged.connect(self.update_tolerance)

                hbox = QHBoxLayout()
                hbox.addWidget(self.lbl_tolerance)
                hbox.addWidget(self.txt_tolerance)
                self.digitize_item.addChild(self.tolerance_child)
                w = QWidget()
                w.setLayout(hbox)
                self.tree.setItemWidget(self.tolerance_child, 0, w)

            if self.txt_tolerance is not None:
                self.txt_tolerance.setEnabled(enable)
                self._set_txt_tolerance_tooltip()
                # use the value of the reader by default
                if (self.straditizer is not None and
                        self.straditizer.data_reader is not None):
                    self.txt_tolerance.setText(str(getattr(
                        self.straditizer.data_reader, 'tolerance', '')))
                # otherwise use a default value of 10 for roundedtt bars
                elif enable and int(self.txt_tolerance.text() or 2) == 2:
                    self.txt_tolerance.setText('10')
                # and 2 for rectangular bars
                elif (enable and s == 'bars' and
                      int(self.txt_tolerance.text() or 10) == 10):
                    self.txt_tolerance.setText('2')
        # and nothing else
        elif self.txt_tolerance is not None:
            self.digitize_item.takeChild(self.digitize_item.indexOfChild(
                self.tolerance_child))
            del self.tolerance_child, self.txt_tolerance

    def _set_txt_tolerance_tooltip(self):
        enable = self.txt_tolerance and self.txt_tolerance.isEnabled()
        if enable:
            self.txt_tolerance.setToolTip(
                'Enter the difference in height to distinguish to adjacent '
                'bars')
        else:
            self.txt_tolerance.setToolTip('Not implemented.')

    def should_be_enabled(self, w):
        if self.straditizer is None:
            return False
        elif w in [self.btn_select_data]:
            return True
        elif w is self.btn_init_reader:
            if (self.straditizer.data_xlim is None or
                    self.straditizer.data_ylim is None):
                return False
        elif (self.straditizer.data_xlim is None or
              self.straditizer.data_ylim is None or
              self.straditizer.data_reader is None):
            return False
        elif (w is self.btn_highlight_small_selection and
              not self.selection_toolbar._selecting):
            return False
        # widgets depending on that the columns have been set already
        elif (self.straditizer.data_reader._column_starts is None and
              w in [self.btn_reset_columns, self.btn_align_vertical,
                    self.btn_column_ends,
                    self.cb_readers, self.btn_new_child_reader,
                    self.cb_exag_reader_type, self.btn_new_exaggeration,
                    self.txt_exag_factor, self.txt_exag_absolute,
                    self.txt_exag_percentage, self.btn_digitize_exag,
                    self.btn_show_disconnected_parts, self.txt_fromlast,
                    self.cb_fromlast, self.txt_from0, self.cb_from0,
                    self.btn_show_cross_column, self.txt_cross_column_px,
                    self.btn_show_parts_at_column_ends, self.btn_digitize]):
            return False
        elif (self.straditizer.data_reader.exaggerated_reader is None and
              w in [self.txt_exag_percentage, self.txt_exag_absolute,
                    self.btn_digitize_exag, self.btn_select_exaggerations]):
            return False
        elif (w in [self.txt_exag_percentage, self.txt_exag_absolute,
                    self.btn_digitize_exag] and
              not self.straditizer.data_reader.exaggerated_reader.binary.any()
              ):
            return False
        elif (self.straditizer.data_reader.exaggerated_reader is not None and
              w in [self.cb_exag_reader_type, self.btn_new_exaggeration,
                    self.txt_exag_factor]):
            return False
        elif (w is self.btn_reset_samples and
              self.straditizer.data_reader._sample_locs is None):
            return False
        elif (w in [self.btn_find_samples, self.btn_edit_samples,
                    self.btn_load_samples, self.btn_digitize_exag] and
              self.straditizer.data_reader.full_df is None):
            return False
        elif (w is self.btn_show_small_parts and
              not self.txt_min_size.text()):
            return False
        elif w is self.sp_max_lw and not self.cb_max_lw.isChecked():
            return False
        return True

    def reset_column_starts(self):
        self.straditizer.data_reader.reset_column_starts()
        self.maybe_show_btn_reset_columns()
        self.refresh()

    def reset_samples(self):
        self.straditizer.data_reader.reset_samples()
        self.maybe_show_btn_reset_samples()
        self.refresh()

    def setup_children(self, item):

        self.add_info_button(item, 'straditize_steps.rst')

        # 0: start parts before creating the reader
        vbox_start = QVBoxLayout()
        hbox_start = QHBoxLayout()
        hbox_start.addWidget(self.btn_select_data)
        hbox_start.addWidget(self.cb_reader_type)
        vbox_start.addLayout(hbox_start)

        w = QWidget()
        w.setLayout(vbox_start)

        child = QTreeWidgetItem(0)
        child.setText(0, 'Reader initialization')
        item.addChild(child)
        child2 = QTreeWidgetItem(0)
        child.addChild(child2)
        self.tree.setItemWidget(child2, 0, w)
        self.tree.expandItem(child)
        self.add_info_button(child2, 'select_data_part.rst',
                             connections=[self.btn_select_data])

        # init reader
        child4 = QTreeWidgetItem(0)
        child.addChild(child4)
        self.tree.setItemWidget(child4, 0, self.btn_init_reader)
        self.add_info_button(child4, 'select_reader.rst',
                             connections=[self.btn_init_reader])

        child = QTreeWidgetItem(0)
        item.addChild(child)
        w = QGroupBox('Column separations')
        vbox_cols = QVBoxLayout()
        hbox_thresh = QHBoxLayout()
        hbox_thresh.addWidget(QLabel('Threshold:'))
        hbox_thresh.addWidget(self.txt_column_thresh)
        hbox_thresh.addWidget(QLabel('%'))
        vbox_cols.addLayout(hbox_thresh)
        hbox_cols = QHBoxLayout()
        hbox_cols.addWidget(self.btn_column_starts)
        hbox_cols.addWidget(self.btn_column_ends)
        hbox_cols.addWidget(self.btn_reset_columns)
        vbox_cols.addLayout(hbox_cols)
        vbox_cols.addWidget(self.btn_align_vertical)
        w.setLayout(vbox_cols)
        self.tree.setItemWidget(child, 0, w)
        self.button = self.straditizer_widgets.add_info_button(
            child, 'select_column_starts.rst',
            connections=[self.btn_column_starts])

        # 1: column specific readers
        self.current_reader_item = child = QTreeWidgetItem(0)
        child.setText(0, 'Current reader')
        item.addChild(child)
        child2 = QTreeWidgetItem(0)
        child.addChild(child2)
        self.add_info_button(child, 'child_readers.rst',
                             connections=[self.btn_new_child_reader])

        w = QWidget()
        hbox = QHBoxLayout()
        self.cb_readers.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        hbox.addWidget(self.cb_readers)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_new_child_reader)
        w.setLayout(hbox)
        self.tree.setItemWidget(child2, 0, w)

        # 2: Exaggerations readers
        child = QTreeWidgetItem(0)
        child.setText(0, 'Exaggerations')
        item.addChild(child)
        self.add_info_button(child, 'exaggerations.rst',
                             connections=[self.btn_new_exaggeration])

        child2 = QTreeWidgetItem(0)
        child.addChild(child2)
        w = QWidget()
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Exaggeration factor:'))
        hbox.addWidget(self.txt_exag_factor)
        vbox.addLayout(hbox)
        hbox = QHBoxLayout()
        hbox.addWidget(self.cb_exag_reader_type)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_new_exaggeration)
        vbox.addLayout(hbox)
        vbox.addWidget(self.btn_select_exaggerations)
        digitizer_layout = QGridLayout()
        digitizer_layout.addWidget(QLabel('Percentage:'), 0, 0)
        digitizer_layout.addWidget(self.txt_exag_percentage, 0, 1)
        digitizer_layout.addWidget(QLabel('%'), 0, 2)
        digitizer_layout.addWidget(QLabel('Absolute:'), 1, 0)
        digitizer_layout.addWidget(self.txt_exag_absolute, 1, 1)
        digitizer_layout.addWidget(QLabel('px'), 1, 2)
        digitizer_layout.addWidget(self.btn_digitize_exag, 2, 0, 1, 3)
        vbox.addLayout(digitizer_layout)
        w.setLayout(vbox)
        self.tree.setItemWidget(child2, 0, w)

        # 3: parts to remove features from the binary image
        self.remove_child = child = QTreeWidgetItem(0)
        child.setText(0, 'Remove features')
        item.addChild(child)
        self.add_info_button(child, 'removing_features.rst')

        # disconnected parts
        dc_child = QTreeWidgetItem(0)
        child.addChild(dc_child)
        self.tree.setItemWidget(dc_child, 0, self.btn_show_disconnected_parts)
        self.add_info_button(dc_child, 'remove_disconnected_parts.rst',
                             connections=[self.btn_show_disconnected_parts])

        dc_child2 = QTreeWidgetItem(0)
        grid = QGridLayout()
        grid.addWidget(self.cb_fromlast, 0, 0)
        grid.addWidget(self.txt_fromlast, 0, 1)
        grid.addWidget(QLabel('px'), 0, 2)
        grid.addWidget(self.cb_from0, 1, 0)
        grid.addWidget(self.txt_from0, 1, 1)
        grid.addWidget(QLabel('px'), 1, 2)
        w = QWidget()
        w.setLayout(grid)
        dc_child.addChild(dc_child2)
        self.tree.setItemWidget(dc_child2, 0, w)

        # parts at column ends
        end_child = QTreeWidgetItem(0)
        child.addChild(end_child)
        self.tree.setItemWidget(end_child, 0,
                                self.btn_show_parts_at_column_ends)
        self.add_info_button(end_child, 'remove_col_ends.rst',
                             connections=[self.btn_show_parts_at_column_ends])

        # cross column features
        cross_child = QTreeWidgetItem(0)
        child.addChild(cross_child)
        self.tree.setItemWidget(cross_child, 0, self.btn_show_cross_column)
        self.add_info_button(cross_child, 'remove_cross_column.rst',
                             connections=[self.btn_show_cross_column])

        cross_child2 = QTreeWidgetItem(0)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Number of pixels:'))
        hbox.addWidget(self.txt_cross_column_px)
        hbox.addWidget(QLabel('px'))
        w = QWidget()
        w.setLayout(hbox)
        cross_child.addChild(cross_child2)
        self.tree.setItemWidget(cross_child2, 0, w)

        # small parts
        small_child = QTreeWidgetItem(0)
        child.addChild(small_child)
        self.tree.setItemWidget(small_child, 0, self.btn_show_small_parts)
        self.add_info_button(small_child, 'remove_small_parts.rst',
                             connections=[self.btn_show_small_parts])

        small_child2 = QTreeWidgetItem(0)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Smaller than'))
        hbox.addWidget(self.txt_min_size)
        hbox.addWidget(QLabel('px'))
        w = QWidget()
        w.setLayout(hbox)
        small_child.addChild(small_child2)
        self.tree.setItemWidget(small_child2, 0, w)

        # lines
        self.remove_line_child = line_child = QTreeWidgetItem(0)
        hbox = QHBoxLayout()
        hbox.addWidget(self.btn_remove_vlines)
        hbox.addWidget(self.btn_remove_hlines)
        w = QWidget()
        w.setLayout(hbox)
        child.addChild(line_child)
        self.tree.setItemWidget(line_child, 0, w)
        self.add_info_button(line_child, 'remove_lines.rst',
                             connections=[self.btn_remove_vlines,
                                          self.btn_remove_hlines])

        w = QWidget()
        line_child2 = QTreeWidgetItem(0)
        layout = QGridLayout()
        layout.addWidget(QLabel('Minimum fraction:'), 0, 0)
        layout.addWidget(self.txt_line_fraction, 0, 1)
        layout.addWidget(QLabel('%'), 0, 2)
        layout.addWidget(QLabel('Minimum line width'), 1, 0)
        layout.addWidget(self.sp_min_lw, 1, 1)
        layout.addWidget(QLabel('px'), 1, 2)
        layout.addWidget(self.cb_max_lw, 2, 0)
        layout.addWidget(self.sp_max_lw, 2, 1)
        layout.addWidget(QLabel('px'), 2, 2)
        w.setLayout(layout)
        line_child.addChild(line_child2)
        self.tree.setItemWidget(line_child2, 0, w)

        # highlight selection
        highlight_child = QTreeWidgetItem(0)
        child.addChild(highlight_child)
        self.tree.setItemWidget(highlight_child, 0,
                                self.btn_highlight_small_selection)

        highlight_child2 = QTreeWidgetItem(0)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Smaller than'))
        hbox.addWidget(self.txt_min_highlight)
        hbox.addWidget(QLabel('px'))
        w = QWidget()
        w.setLayout(hbox)
        highlight_child.addChild(highlight_child2)
        self.tree.setItemWidget(highlight_child2, 0, w)

        # 4: digitize button
        self.digitize_item = child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.setItemWidget(child, 0, self.btn_digitize)
        self.add_info_button(child, 'digitize.rst',
                             connections=[self.btn_digitize])

        # 5: bar splitter
        self.bar_split_child = QTreeWidgetItem(0)
        self.bar_split_child.setText(0, 'Split too long bars')
        child2 = QTreeWidgetItem(0)
        self.bar_split_child.addChild(child2)
        self.tree.setItemWidget(child2, 0, self.tree_bar_split)
        item.addChild(self.bar_split_child)
        self.bar_split_child.setHidden(not self.tree_bar_split.filled)

        # 6: edit samples button
        self.edit_samples_child = child = QTreeWidgetItem(0)
        child.setText(0, 'Edit samples')
        item.addChild(child)
        self.add_info_button(child, 'samples.rst')

        find_child = QTreeWidgetItem(0)
        child.addChild(find_child)
        self.tree.setItemWidget(find_child, 0, self.btn_find_samples)
        self.add_info_button(find_child, 'find_samples.rst',
                             connections=[self.btn_find_samples])

        find_child2 = QTreeWidgetItem(0)
        samples_box = QGridLayout()
        samples_box.addWidget(QLabel('Minimum length'), 0, 0)
        samples_box.addWidget(QLabel('Maximum length'), 0, 1)
        samples_box.addWidget(self.txt_min_len, 1, 0)
        samples_box.addWidget(self.txt_max_len, 1, 1)
        samples_box.addWidget(QLabel('Minimum distance'),
                              2, 0)
        samples_box.addWidget(self.sp_pixel_tol, 2, 1)
        samples_box.addWidget(QLabel('px'), 2, 2)
        w = QWidget()
        w.setLayout(samples_box)
        find_child.addChild(find_child2)
        self.tree.setItemWidget(find_child2, 0, w)

        load_child = QTreeWidgetItem(0)
        child.addChild(load_child)
        self.tree.setItemWidget(load_child, 0, self.btn_load_samples)
        self.add_info_button(load_child, 'load_samples.rst',
                             connections=[self.btn_load_samples])

        edit_child = QTreeWidgetItem(0)
        child.addChild(edit_child)
        self.add_info_button(edit_child, 'edit_samples.rst',
                             connections=[self.btn_edit_samples])

        hbox_cols = QHBoxLayout()
        hbox_cols.addWidget(self.btn_edit_samples)
        hbox_cols.addWidget(self.btn_reset_samples)
        w = QWidget()
        w.setLayout(hbox_cols)

        self.tree.setItemWidget(edit_child, 0, w)

        edit_child2 = QTreeWidgetItem(0)
        samples_box = QGridLayout()
        samples_box.addWidget(self.cb_edit_separate, 0, 0, 1, 2)
        samples_box.addWidget(QLabel('Number of rows:'), 1, 0)
        samples_box.addWidget(self.txt_edit_rows, 1, 1)
        w = QWidget()
        w.setLayout(samples_box)
        edit_child.addChild(edit_child2)
        self.tree.setItemWidget(edit_child2, 0, w)

    def init_reader(self):
        """Initialize the reader"""
        # make sure, the StackedReader is registered
        import straditize.widgets.stacked_area_reader
        kws = self.init_reader_kws.copy()
        reader_type = self.cb_reader_type.currentText()
        kws['reader_type'] = reader_type
        if self.straditizer.data_reader is not None:
            for reader in self.straditizer.data_reader.iter_all_readers:
                reader.remove_plots()
        self.straditizer.init_reader(**kws)
        self.straditizer.show_full_image()
        self.straditizer.draw_figure()
        self.straditizer_widgets.refresh()

    def init_exaggerated_reader(self):
        """Initialize the reader for exaggeration features"""
        from straditize.binary import readers
        reader_type = self.cb_exag_reader_type.currentText()
        if reader_type == get_reader_name(self.straditizer.data_reader):
            loader = None
        else:
            loader = readers[reader_type]
        factor = float(self.txt_exag_factor.text())
        self.straditizer.data_reader.create_exaggerations_reader(
            factor, loader)
        self.straditizer_widgets.refresh()

    def select_exaggerated_features(self):
        """Enable the selection of exaggerated features"""
        tb = self.selection_toolbar
        self.apply_button.clicked.connect(self.finish_exaggerated_features)
        reader = self.straditizer.data_reader
        if reader.is_exaggerated:
            reader = reader.non_exaggerated_reader
        tb.data_obj = reader
        tb.start_selection(
            tb.labels, rgba=reader.image_array(), remove_on_apply=False)
        tb.add_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
            tb.toggle_selection()
        self.apply_button.setText('Select')

    def finish_exaggerated_features(self):
        mask = self.selection_toolbar.data_obj.selected_part
        self.straditizer.data_reader.mark_as_exaggerations(mask)

    def fill_cb_readers(self):
        self._change_reader = False
        self.cb_readers.clear()
        if self.straditizer is None or self.straditizer.data_reader is None:
            return
        reader = self.straditizer.data_reader
        if reader.columns:
            for child in chain([reader], reader.children):
                name = get_reader_name(child) or child.__class__.__name__
                exag = 'exag. ' if child.is_exaggerated else ''
                self.cb_readers.addItem(
                    exag + name + ': Columns ' +
                    int_list2str(child.columns or []))
        self._change_reader = True

    def new_reader_for_selection(self, cls=None):
        reader = self.straditizer.data_reader
        cols = sorted(reader._selected_cols)
        if not cols:
            raise ValueError("No columns selected!")
        if not cls:
            from straditize.binary import readers
            current = get_reader_name(reader)
            items = list(readers)
            try:  # put the current type at the front
                items.insert(0, items.pop(items.index(current)))
            except ValueError:
                pass
            name, ok = QInputDialog.getItem(
                self.straditizer_widgets, 'Reader type',
                'Select the reader type for the selected columns',
                items)
            if not ok:
                return
            cls = readers[name]
        reader.new_child_for_cols(cols, cls)
        self.fill_cb_readers()

    def change_reader(self, txt):
        if not self._change_reader:
            return
        match = re.search('Columns (\d.*)', txt)
        if not match:
            return
        cols = set(map(int, re.findall('\d+', match.group(1))))
        old = self.straditizer.data_reader
        children = chain([old], old.children)
        filter_func = filter if txt.startswith('exag') else filterfalse
        children = filter_func(lambda c: c.is_exaggerated, children)
        new = next(child for child in children if cols <= set(child.columns))
        new.set_as_parent()
        self.straditizer.data_reader = new
        self.straditizer_widgets.refresh()

    def enable_col_selection_for_new_reader(self):
        """Start the selection process to get a new reader for specific cols"""
        reader = self.straditizer.data_reader
        reader.start_column_selection()
        self.connect2apply(
            lambda: self.new_reader_for_selection(),
            reader.end_column_selection,
            reader.draw_figure)
        self.connect2cancel(
            reader.end_column_selection,
            reader.draw_figure)

    def find_samples(self):
        kws = dict(pixel_tol=self.sp_pixel_tol.value())
        if self.txt_min_len.text().strip():
            kws['min_len'] = int(self.txt_min_len.text())
        if self.txt_max_len.text().strip():
            kws['max_len'] = int(self.txt_max_len.text())
        self.straditizer.data_reader.add_samples(
            *self.straditizer.data_reader.find_samples(**kws))
        self.straditizer_widgets.refresh()

    def load_samples(self, fname=None):
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'samples', os.getcwd(),
                'CSV files (*.csv);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not fname:
            return
        df = pd.read_csv(fname)
        samples = df.iloc[:, 0].values
        try:
            samples = self.straditizer.data2px_y(samples)
        except ValueError:
            pass
        self.straditizer.data_reader.add_samples(samples.astype(int))
        self.straditizer_widgets.refresh()

    def edit_samples(self):
        from psyplot_gui.main import mainwindow
        from straditize.widgets.samples_table import (
            MultiCrossMarksEditor, SingleCrossMarksEditor)
        draw_sep = self.cb_edit_separate.isChecked()
        if draw_sep:
            fig, axes = self.straditizer.marks_for_samples_sep()
            self._samples_fig = fig
            if mainwindow.figures:  # using psyplot backend
                fig_dock = self._samples_fig.canvas.manager.window
                stradi_dock = self.straditizer.ax.figure.canvas.manager.window
                mainwindow.tabifyDockWidget(stradi_dock, fig_dock)
                a = fig_dock.toggleViewAction()
                if not a.isChecked():
                    a.trigger()
                fig_dock.raise_()
            self._samples_editor = editor = MultiCrossMarksEditor(
                self.straditizer, axes=axes)
        else:
            self.straditizer.marks_for_samples()
            self._samples_editor = editor = SingleCrossMarksEditor(
                self.straditizer)
        dock = editor.to_dock(
            mainwindow, title='Samples editor')
        editor.show_plugin()
        editor.maybe_tabify()
        editor.raise_()
        # zoom to the first 3 samples
        ncols = editor.table.model().columnCount() - 1
        nrows = min(3, editor.table.model().rowCount())
        if draw_sep:
            editor.table.zoom_to_cells(
                chain.from_iterable([i] * ncols for i in range(nrows)),
                list(range(ncols)) * nrows)
        args = (self.straditizer.draw_figure, ) if not draw_sep else ()
        update = self.straditizer.update_samples_sep if draw_sep else \
            self.straditizer.update_samples
        self.connect2apply(lambda: update(),
                           self._close_samples_fig,
                           dock.close,
                           self.straditizer_widgets.refresh, *args)
        self.connect2cancel(self.straditizer.remove_marks,
                            self._close_samples_fig,
                            dock.close, *args)
        self.maybe_show_btn_reset_samples()

    def _close_samples_fig(self):
        import matplotlib.pyplot as plt
        for l in self._samples_editor.table.model().lines:
            try:
                l.remove()
            except ValueError:
                pass
        try:
            plt.close(self._samples_fig)
        except AttributeError:
            pass
        else:
            del self._samples_fig
        del self._samples_editor
        try:
            del self.straditizer._plotted_full_df
        except AttributeError:
            pass

    def digitize(self):
        reader = self.reader
        if self.txt_tolerance and self.txt_tolerance.isEnabled():
            reader.tolerance = int(self.txt_tolerance.text())
        if reader.is_exaggerated:
            reader = reader.non_exaggerated_reader
        reader.digitize()
        pc = self.straditizer_widgets.plot_control.table
        if pc.can_plot_full_df():
            if pc.get_full_df_lines():
                pc.remove_full_df_plot()
            pc.plot_full_df()
            pc.refresh()

    def digitize_exaggerations(self):
        reader = self.reader
        fraction = float(self.txt_exag_percentage.text().strip() or 0) / 100.
        absolute = int(self.txt_exag_absolute.text().strip() or 0)
        reader.digitize_exaggerated(fraction=fraction, absolute=absolute)

    def remove_hlines(self):
        """Remove horizontal lines"""
        fraction = float(self.txt_line_fraction.text().strip() or 0) / 100.
        max_lw = int(self.sp_max_lw.text().strip() or 0) or None
        min_lw = int(self.sp_min_lw.text().strip() or 1)
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        self.reader.recognize_hlines(fraction=fraction, min_lw=min_lw,
                                     max_lw=max_lw)
        self.straditizer_widgets.apply_button.clicked.connect(
            self.reader.set_hline_locs_from_selection)
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
        tb.select_action.setEnabled(False)
        tb.auto_expand = True
        self.straditizer.draw_figure()

    def remove_vlines(self):
        """Remove horizontal lines"""
        fraction = float(self.txt_line_fraction.text().strip() or 0) / 100.
        max_lw = self.sp_max_lw.value() if self.cb_max_lw.isChecked() else None
        min_lw = self.sp_min_lw.value()
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        self.reader.recognize_vlines(fraction=fraction, min_lw=min_lw,
                                     max_lw=max_lw)
        self.straditizer_widgets.apply_button.clicked.connect(
            self.reader.set_vline_locs_from_selection)
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
        tb.select_action.setEnabled(False)
        tb.auto_expand = True
        self.straditizer.draw_figure()

    def show_disconnected_parts(self):
        """Remove disconnected parts"""
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        if self.cb_fromlast.isChecked():
            fromlast = int(self.txt_fromlast.text() or 0)
        else:
            fromlast = 0
        if self.cb_from0.isChecked():
            from0 = int(self.txt_from0.text() or 0)
        else:
            from0 = 0
        self.reader.show_disconnected_parts(
            fromlast=fromlast, from0=from0)
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
            tb.toggle_selection()
        self.straditizer.draw_figure()

    def show_cross_column_features(self):
        """Remove cross column features"""
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        min_px = int(self.txt_cross_column_px.text().strip() or 0)
        self.reader.show_cross_column_features(min_px)
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
            tb.toggle_selection()
        self.straditizer.draw_figure()

    def show_parts_at_column_ends(self):
        """Remove parts that touch the column ends"""
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        self.reader.show_parts_at_column_ends()
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
            tb.toggle_selection()
        self.straditizer.draw_figure()

    def show_small_parts(self):
        """Remove parts that touch the column ends"""
        tb = self.selection_toolbar
        tb.data_obj = 'Reader'
        self.reader.show_small_parts(int(self.txt_min_size.text()))
        tb.start_selection(rgba=tb.data_obj.image_array())
        tb.remove_select_action.setChecked(True)
        if not tb.wand_action.isChecked():
            tb.wand_action.setChecked(True)
            tb.toggle_selection()
        self.straditizer.draw_figure()

    def _update_btn_show_small_parts(self, txt):
        if txt:
            self.btn_show_small_parts.setToolTip(
                'Remove parts smaller than %s pixels' % txt)
            self.btn_show_small_parts.setEnabled(
                self.should_be_enabled(self.btn_show_small_parts))
        else:
            self.btn_show_small_parts.setEnabled(False)
            self.btn_show_small_parts.setToolTip('')

    def _update_btn_highlight_small_selection(self, txt):
        if txt:
            self.btn_highlight_small_selection.setToolTip(
                'Highlight selected features smaller than %s pixels' % txt)
            self.btn_show_small_parts.setEnabled(
                self.should_be_enabled(self.btn_highlight_small_selection))
        else:
            self.btn_highlight_small_selection.setEnabled(False)
            self.btn_highlight_small_selection.setToolTip('')

    def toggle_btn_highlight_small_selection(self):
        obj = self.selection_toolbar.data_obj
        if obj is not None and self.btn_highlight_small_selection.isChecked():
            obj.highlight_small_selections(
                n=int(self.txt_min_highlight.text()))
        elif obj is not None:
            obj.remove_small_selection_ellipses()
        else:
            return
        if obj._select_img is not None:
            obj._select_img.axes.figure.canvas.draw()

    def select_data_part(self):
        self.straditizer.marks_for_data_selection()
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.update_data_part,
                           self.straditizer.draw_figure,
                           self.straditizer_widgets.refresh)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)

    def align_vertical(self):
        """Create marks for vertical alignment of the columns"""
        self.straditizer.marks_for_vertical_alignment()
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.align_columns,
                           self.straditizer.draw_figure)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)

    def select_column_starts(self):
        threshold = self.txt_column_thresh.text()
        threshold = float(threshold) / 100. if threshold else None
        self.straditizer.marks_for_column_starts(threshold)
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.update_column_starts,
                           self.straditizer_widgets.refresh,
                           self.straditizer.draw_figure)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)

    def modify_column_ends(self):
        threshold = self.txt_column_thresh.text()
        threshold = float(threshold) / 100. if threshold else None
        self.straditizer.marks_for_column_ends(threshold)
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.update_column_ends,
                           self.straditizer.draw_figure)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)


class BarSplitter(QTreeWidget, StraditizerControlBase):
    """A widget that is designed for splitting bars"""

    selected_child = None

    prev_action = None

    @property
    def previous_item(self):
        child = self.selected_child
        top = child.parent()
        idx_child = top.indexOfChild(child)
        # for the first child, go to the previous topLevelItem (if possible)
        if idx_child == 0:
            idx_top = self.indexOfTopLevelItem(top)
            if idx_top == 0:
                return None
            previous_top = self.topLevelItem(idx_top - 1)
            return previous_top.child(previous_top.childCount() - 1)
        return top.child(idx_child - 1)

    @property
    def next_item(self):
        child = self.selected_child
        top = child.parent()
        idx_child = top.indexOfChild(child)
        # for the last child, go to the next topLevelItem (if possible)
        if top.childCount() == idx_child + 1:
            idx_top = self.indexOfTopLevelItem(top)
            if self.topLevelItemCount() == idx_top + 1:
                return None
            next_top = self.topLevelItem(idx_top + 1)
            return next_top.child(0)
        return top.child(idx_child + 1)

    def __init__(self, straditizer_widgets, *args, **kwargs):
        super(BarSplitter, self).__init__(*args, **kwargs)
        self.init_straditizercontrol(straditizer_widgets)
        self.setColumnCount(1)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.filled = False
        self._enable_doubleclick = False
        self.itemDoubleClicked.connect(self.start_splitting)
        try:
            if self.straditizer.data_reader._splitted:
                self.fill_table()
        except AttributeError:
            pass

    def fill_table(self):
        """Fill the table with the bars that should be splitted"""
        self.clear()
        self.filled = False
        try:
            items = self.straditizer.data_reader._splitted.items()
        except AttributeError:
            return
        for col, lists in sorted(items):
            if not lists:
                continue
            top = QTreeWidgetItem(0)
            top.setText(0, 'Column %i - %i bars to split' % (col, len(lists)))
            for indices in lists:
                child = QTreeWidgetItem(0)
                child.setText(0, ', '.join(map(str, range(*indices))))
                top.addChild(child)
            self.addTopLevelItem(top)
            self.filled = True
            self._enable_doubleclick = True

    def refresh(self):
        """Reimplemented to use the :meth:`fill_table` method"""
        self.fill_table()

    def start_splitting(self, item, *args, **kwargs):
        parent = item.parent()
        found = False
        for top in map(self.topLevelItem, range(self.topLevelItemCount())):
            if parent is top:
                found = True
                break
        if not found:
            return
        # if we are already in the selection, we just switch to another
        # bar. Otherwise we check if this widget is enabled and if yes, zoom
        # to the item
        if self.selected_child is not None:
            self.remove_lines()
            self.disconnect()
            self.clearSelection()
            item.setSelected(True)
        elif not self._enable_doubleclick:
            return
        self._col = col = int(top.text(0).split()[1])
        reader = self.straditizer.data_reader
        extent = reader.extent
        if extent is not None:
            x0 = extent[0]
            y0 = min(extent[2:])
        else:
            x0 = y0 = 0
        indices = list(map(int, item.text(0).split(', ')))
        bounds = x0 + reader.column_bounds
        idx_col = reader.columns.index(col)
        ax = reader.ax
        ax.set_xlim(*bounds[idx_col])
        ax.set_ylim(y0 + max(indices) + len(indices) * 0.5,
                    y0 + min(indices) - len(indices) * 0.5)
        self.lines = [ax.plot(
            bounds[idx_col, 0] + reader._full_df_orig.loc[indices, col].values,
            y0 + np.array(indices) + 0.5, marker='+', lw=0)[0]]
        self.selected_child = item
        self.selected_col = col
        self.selected_indices = list(indices)
        self.split_cid = ax.figure.canvas.mpl_connect(
            'button_press_event', self.prepare_for_split)
        if self.prev_action is None:
            self.add_toolbar_widgets()
        if self._enable_doubleclick:
            self.connect2apply(self.split_cols, self.remove_lines,
                               self.disconnect, self.remove_actions,
                               reader.draw_figure,
                               self.straditizer_widgets.digitizer.refresh)
            self.connect2cancel(self.remove_lines, self.disconnect,
                                self.remove_actions, reader.draw_figure,
                                self.remove_split_children)
        for i, child in enumerate(map(item.child, range(item.childCount()-1))):
            y = int(child.text(0).split(', ')[-1])
            self.lines.append(reader.ax.hlines(
                y0 + y + 1, *bounds[idx_col], color='red'))
        reader.draw_figure()

    def remove_lines(self):
        for l in self.lines:
            try:
                l.remove()
            except ValueError:
                pass
        self.lines.clear()

    def prepare_for_split(self, event):
        """Select or deselect a split location

        LeftButton selects the given location for a new split (see
        :meth:`new_split`), RightButton deselects it (see :meth:`revert_split`)
        """
        reader = self.straditizer.data_reader
        if (event.inaxes != reader.ax or event.button not in [1, 3] or
                reader.fig.canvas.manager.toolbar.mode != ''):
            return
        y = int(np.floor(event.ydata - 0.5))
        extent = reader.extent or [0] * 4
        idx_col = reader.columns.index(self._col)
        start, end = reader.column_bounds[idx_col] + min(extent[:2])
        indices = self.selected_indices
        if extent is not None:
            y0 = min(extent[2:])
            y -= y0
        if y not in indices or y in [indices[0], indices[-1]]:
            return
        if event.button == 1:
            self.new_split(
                y, y0, *reader.column_bounds[idx_col] + min(extent[:2]))
        elif self.selected_child.childCount():
            self.revert_split(y, y0)

    def new_split(self, y, y0, start, end):
        reader = self.straditizer.data_reader
        item = self.selected_child
        draw_line = False
        if not item.childCount():
            indices = self.selected_indices
            c1 = QTreeWidgetItem(0)
            c2 = QTreeWidgetItem(1)
            item.addChildren([c1, c2])
            c1.setText(0, ', '.join(map(str, indices[:indices.index(y) + 1])))
            c2.setText(0, ', '.join(map(
                str, indices[indices.index(y) + 1:])))
            self.expandItem(item)
            draw_line = True
        else:
            for i, child in enumerate(map(item.child,
                                          range(item.childCount()))):
                indices = list(map(int, child.text(0).split(', ')))
                if y in indices:
                    if y in [indices[0], indices[-1]]:
                        return
                    c1 = QTreeWidgetItem(0)
                    c2 = child
                    item.insertChild(i, c1)
                    c1.setText(0, ', '.join(map(
                        str, indices[:indices.index(y) + 1])))
                    c2.setText(0, ', '.join(map(
                        str, indices[indices.index(y) + 1:])))
                    draw_line = True
        if draw_line:
            self.lines.append(reader.ax.hlines(
                y0 + y + 1, start, end, color='red'))
            reader.draw_figure()

    def revert_split(self, y, y0):
        """Revert the split"""
        item = self.selected_child
        previous = None
        for i, child in enumerate(map(item.child,
                                      range(item.childCount()))):
            indices = list(map(int, child.text(0).split(', ')))
            if previous:
                previous.setText(0, previous.text(0) + ', ' + child.text(0))
                item.removeChild(child)
                if item.childCount() == 1:
                    item.removeChild(previous)
                break
            if y == indices[-1]:
                previous = child
        if previous:  # remove the drawn line
            y += y0 + 1
            for hline in self.lines[1:]:
                if y == hline.get_segments()[0][0, 1]:
                    hline.remove()
                    self.lines.remove(hline)
                    self.straditizer.data_reader.draw_figure()
                    break

    def split_cols(self):
        """Split the columns after they have been separated manually"""

        def reset_values(col, indices):
            reader._full_df.loc[indices, col] = reader._full_df_orig.loc[
                indices, col].max()

        reader = self.straditizer.data_reader
        for item in map(self.topLevelItem, range(self.topLevelItemCount())):
            col = int(item.text(0).split()[1])
            for child in map(item.child, range(item.childCount())):
                nchildren = child.childCount()
                if not nchildren:
                    continue
                all_indices = list(map(int, child.text(0).split(', ')))
                for i, l in enumerate(reader._all_indices[col]):
                    if l[0] == all_indices[0]:
                        indices = list(map(int, child.child(
                            nchildren - 1).text(0).split(', ')))
                        reader._all_indices[col][i] = [indices[0],
                                                       indices[-1] + 1]
                        reset_values(col, indices)
                        for child2 in map(child.child, range(nchildren - 1)):
                            indices = list(map(int,
                                               child2.text(0).split(', ')))
                            reader._all_indices[col].insert(
                                i, [indices[0], indices[-1] + 1])
                            reset_values(col, indices)
                        break
                for i, l in enumerate(reader._splitted[col]):
                    if l[0] == all_indices[0]:
                        del reader._splitted[col][i]
                        break

    def remove_split_children(self):
        for item in map(self.topLevelItem, range(self.topLevelItemCount())):
            for child in map(item.child, range(item.childCount())):
                nchildren = child.childCount()
                if nchildren:
                    for child2 in list(map(child.child, range(nchildren))):
                        child.removeChild(child2)

    def disconnect(self):
        try:
            canvas = self.straditizer.data_reader.ax.figure.canvas
        except AttributeError:
            pass
        else:
            canvas.mpl_disconnect(self.split_cid)
        del self.selected_child, self.selected_col, self.selected_indices

    def add_toolbar_widgets(self):
        tb = self.straditizer.data_reader.ax.figure.canvas.toolbar
        if not isinstance(tb, QToolBar):
            return
        self.tb_separator = tb.addSeparator()
        self.prev_action = tb.addAction(
            QIcon(get_icon('prev_bar.png')), 'previous bar',
            self.go_to_prev_bar)
        self.prev_action.setToolTip(
            'Move to the previous bar that was too long')
        self.next_action = tb.addAction(
            QIcon(get_icon('next_bar.png')), 'next bar',
            self.go_to_next_bar)
        self.next_action.setToolTip('Move to the next bar that is too long')

    def remove_actions(self):
        if self.prev_action is not None:
            try:
                tb = self.straditizer.data_reader.fig.canvas.toolbar
            except AttributeError:
                pass
            else:
                tb.removeAction(self.next_action)
                tb.removeAction(self.prev_action)
                tb.removeAction(self.tb_separator)
            del self.prev_action

    def go_to_next_bar(self):
        self._go_to_item(self.next_item)

    def go_to_prev_bar(self):
        self._go_to_item(self.previous_item)

    def _go_to_item(self, item):
        self.start_splitting(item)
        self.expandItem(item.parent())
        self.expandItem(item)
        self.scrollToItem(item)
        self.next_action.setEnabled(self.next_item is not None)
        self.prev_action.setEnabled(self.previous_item is not None)

    def enable_or_disable_widgets(self, b):
        if not b:
            self.setSelectionMode(QTreeWidget.SingleSelection)
            self._enable_doubleclick = True
        else:
            self.setSelectionMode(QTreeWidget.NoSelection)
            self._enable_doubleclick = False
