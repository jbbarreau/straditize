"""DataReader for stacked area plots"""
from itertools import chain
import numpy as np
from straditize.binary import DataReader, readers
from straditize.widgets import StraditizerControlBase, get_straditizer_widgets
import skimage.morphology as skim
from psyplot_gui.compat.qtcompat import (
    QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLabel, QVBoxLayout)


class StackedReader(DataReader, StraditizerControlBase):
    """A DataReader for stacked area plots"""

    #: The QTreeWidgetItem that holds the digitization widgets
    digitize_child = None

    _current_col = 0

    def digitize(self):
        if getattr(self, 'straditizer_widgets', None) is None:
            self.init_straditizercontrol(get_straditizer_widgets())
        digitizer = self.straditizer_widgets.digitizer
        digitizing = digitizer.btn_digitize.isChecked()
        if digitizing and self.digitize_child is None:
            raise ValueError("Apparently another digitization is in progress!")
        elif not digitizing and self.digitize_child is None:
            if len(self.columns) == 1:
                self._current_col = self.columns[0]
                super(StackedReader, self).digitize()
            # start digitization
            digitizer.btn_digitize.setCheckable(True)
            digitizer.btn_digitize.setChecked(True)
            self._init_digitize_child(digitizer)
            # Disable the changing of readers
            digitizer.cb_readers.setEnabled(False)
            digitizer.tree.expandItem(digitizer.digitize_item)
            self.enable_or_disable_navigation_buttons()
        elif not digitizing:
            # stop digitization
            digitizer.btn_digitize.setChecked(False)
            digitizer.btn_digitize.setCheckable(False)
            self._remove_digitze_child(digitizer)
            digitizer.cb_readers.setEnabled(
                digitizer.should_be_enabled(digitizer.cb_readers))
            del self.straditizer_widgets

    def _init_digitize_child(self, digitizer):
            self.lbl_col = QLabel('')
            self.btn_prev = QPushButton('<')
            self.btn_next = QPushButton('>')
            self.btn_edit = QPushButton('Edit')
            self.btn_add = QPushButton('+')
            self.reset_lbl_col()
            w = QWidget()
            vbox = QVBoxLayout()
            vbox.addWidget(self.lbl_col)
            hbox = QHBoxLayout()
            hbox.addWidget(self.btn_prev)
            hbox.addWidget(self.btn_next)
            hbox.addWidget(self.btn_edit)
            hbox.addWidget(self.btn_add)
            vbox.addLayout(hbox)
            w.setLayout(vbox)

            self.digitize_child = QTreeWidgetItem(0)
            digitizer.digitize_item.addChild(self.digitize_child)
            digitizer.tree.setItemWidget(self.digitize_child, 0, w)
            self.widgets2disable = [self.btn_prev, self.btn_next,
                                    self.btn_edit, self.btn_add]

            self.btn_next.clicked.connect(self.increase_current_col)
            self.btn_prev.clicked.connect(self.decrease_current_col)
            self.btn_edit.clicked.connect(lambda: self.select_current_column())
            self.btn_add.clicked.connect(lambda: self.select_current_column(
                True))

    def reset_lbl_col(self):
        self.lbl_col.setText('Part %i of %i' % (
            self.columns.index(self._current_col) + 1, len(self.columns)))

    def increase_current_col(self):
        self._current_col = min(self.columns[-1], self._current_col + 1)
        self.reset_lbl_col()

    def decrease_current_col(self):
        self._current_col = max(self.columns[0], self._current_col - 1)
        self.reset_lbl_col()

    def _remove_digitze_child(self, digitizer):
        digitizer.digitize_item.takeChild(
            digitizer.digitize_item.indexOfChild(
                self.digitize_child))
        digitizer.btn_digitize.setChecked(False)
        digitizer.btn_digitize.setCheckable(False)
        del self.digitize_child, self.btn_prev, self.btn_next, self.btn_add
        self.widgets2disable.clear()

    def enable_or_disable_navigation_buttons(self):
        disable_all = self.columns is None or len(self.columns) == 1
        self.btn_prev.setEnabled(not disable_all and
                                 self._current_col != self.columns[1])
        self.btn_next.setEnabled(not disable_all and
                                 self._current_col != self.columns[-1])

    def select_current_column(self, add_on_apply=False):
        image = np.array(self.image.convert('L')).astype(int) + 1
        start = self.start_of_current_col
        end = start + self.full_df[self._current_col].values
        all_end = start + self.full_df[self.columns[-1]].values
        x = np.meshgrid(*map(np.arange, image.shape[::-1]))[0]
        image[(x < start[:, np.newaxis]) | (x > all_end[:, np.newaxis])] = 0
        labels = skim.label(image, 8)
        self.straditizer_widgets.selection_toolbar.data_obj = self
        self.apply_button.clicked.connect(
            self.add_col if add_on_apply else self.update_col)
        self.straditizer_widgets.selection_toolbar.start_selection(
            labels, rgba=self.image_array(), remove_on_apply=False)
        self.select_all_labels()
        # set values outside the current column to 0
        self._selection_arr[(x < start[:, np.newaxis]) |
                            (x > end[:, np.newaxis])] = -1
        self._select_img.set_array(self._selection_arr)
        self.draw_figure()

    @property
    def start_of_current_col(self):
        if self._current_col == self.columns[0]:
            start = np.zeros(self.binary.shape[:1])
        else:
            idx = self.columns.index(self._current_col)
            start = self.full_df.iloc[:, :idx].values.sum(axis=1)
        start += self.column_starts[0]
        return start

    def update_col(self):
        """Update the current column based on the selection"""
        current = self._current_col
        start = self.start_of_current_col
        selected = self.selected_part
        end = (self.binary.shape[1] - selected[:, ::-1].argmax(axis=1) - 1 -
               start)
        not_selected = ~selected.any()
        end[not_selected] = 0

        diff_end = self.parent._full_df.loc[:, current] - end
        self.parent._full_df.loc[:, current] = end
        if current != self.columns[-1]:
            self.parent._full_df.loc[:, current + 1] += diff_end

    def get_binary_for_col(self, col):
        s, e = self.column_bounds[self.columns.index(col)]
        if self.parent._full_df is None:
            return self.binary[:, s:e]
        else:
            vals = self.full_df.loc[:, col].values
            ret = np.zeros((self.binary.shape[0], int(vals.max())))
            dist = np.tile(np.arange(ret.shape[1])[np.newaxis], (len(ret), 1))
            ret[dist <= vals[:, np.newaxis]] = 1
            return ret

    def add_col(self):
        """Create a column out of the current selection"""
        def increase_col_nums(df):
            df_cols = df.columns.values
            df_cols[df_cols >= current] += 1
            df.columns = df_cols
        current = self._current_col
        start = self.start_of_current_col
        selected = self.selected_part
        end = (self.binary.shape[1] - selected[:, ::-1].argmax(axis=1) - 1 -
               start)
        not_selected = ~selected.any()
        end[not_selected] = 0

        # ----- Update of reader column numbers -----
        for reader in self.iter_all_readers:
            for i, col in enumerate(reader.columns):
                if col >= current:
                    reader.columns[i] += 1
        self.columns.insert(self.columns.index(current + 1), current)
        self.parent._column_starts = np.insert(
            self.parent._column_starts, current, self._column_starts[current])
        if self.parent._column_ends is not None:
            self.parent._column_ends = np.insert(
                self.parent._column_ends, current,
                self.parent._column_ends[current])

        # ----- Update of column numbers in dataframes -----
        # increase column numbers in full_df
        full_df = self.parent._full_df
        increase_col_nums(full_df)
        # increase column numbers in measurements
        measurements = self.parent.measurement_locs
        if measurements is not None:
            increase_col_nums(measurements)
        # increase column numbers in rough locations
        rough_locs = self.parent.rough_locs
        if rough_locs is not None:
            increase_col_nums(rough_locs)

        # ----- Update of DataFrames -----
        # update the current column in full_df and add the new one
        full_df.loc[:, current + 1] -= end
        full_df[current] = end
        full_df.sort_index(axis=1, inplace=True)
        # update the current column in measurements and add the new one
        if measurements is not None:
            new_measurements = full_df.loc[measurements.index, current]
            measurements.loc[:, current + 1] -= new_measurements
            measurements[:, current] = new_measurements
        if rough_locs is not None:
            rough_locs[current] = 0
        self.reset_lbl_col()
        self.enable_or_disable_navigation_buttons()

    def plot_full_df(self, ax=None):
        """Plot the lines for the digitized diagram"""
        vals = self.full_df.values
        starts = self.column_starts
        self.lines = lines = []
        y = np.arange(np.shape(self.image)[0])
        ax = ax or self.ax
        if self.extent is not None:
            y += self.extent[-1]
            starts += self.extent[0]
        x = np.zeros_like(vals[:, 0]) + starts[0]
        for i in range(vals.shape[1]):
            x += vals[:, i]
            lines.extend(ax.plot(x, y, lw=2.0))

    def plot_potential_measurements(self, excluded=False, ax=None,
                                    *args, **kwargs):
        """Plot the ranges for potential measurements"""
        vals = self.full_df.values.copy()
        starts = self.column_starts.copy()
        self.measurement_ranges = lines = []
        y = np.arange(np.shape(self.image)[0])
        ax = ax or self.ax
        if self.extent is not None:
            y += self.extent[-1]
            starts = starts + self.extent[0]
        x = np.zeros(vals.shape[0]) + starts[0]
        for i, arr in enumerate(vals.T):
            all_indices, excluded_indices = self.find_potential_measurements(
                i, *args, **kwargs)
            if excluded:
                all_indices = excluded_indices
            if not all_indices:
                continue
            indices = list(chain.from_iterable(all_indices))
            mask = np.ones(arr.size, dtype=bool)
            mask[indices] = False
            for l in all_indices:
                lines.extend(ax.plot(np.where(mask, np.nan, arr)[l] + x[l],
                                     y[l], marker='+'))
            x += arr


readers.setdefault('stacked area', StackedReader)