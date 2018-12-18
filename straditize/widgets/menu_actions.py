"""The main control widget for a straditizer
"""
import os
import os.path as osp
import weakref
import pandas as pd
from itertools import chain
import datetime as dt
import six
from straditize.widgets import StraditizerControlBase
from straditize.common import rgba2rgb
from psyplot_gui.compat.qtcompat import (
    with_qt5, QFileDialog, QMenu, QKeySequence, QDialog, QDialogButtonBox,
    QLineEdit, QToolButton, QIcon, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel,
    QDesktopWidget, QPushButton, QTreeWidgetItem, Qt, QMessageBox)
from PyQt5 import QtWidgets
from psyplot_gui.common import get_icon
import numpy as np
from PIL import Image
from straditize.widgets import get_straditizer_widgets

straditizer = None


# axes that are being updated currently
_updating = []


class ExportDfDialog(QDialog):

    def __init__(self, df, straditizer, fname=None, *args, **kwargs):
        """
        Parameters
        ----------
        df: pandas.DataFrame
            The DataFrame to be exported
        straditizer: straditize.straditizer.Straditizer
            The source straditizer
        fname: str
            The file name to export to
        """
        super().__init__(*args, **kwargs)
        self.df = df
        self.stradi = straditizer
        self.txt_fname = QLineEdit()
        self.bt_open_file = QToolButton()
        self.bt_open_file.setIcon(QIcon(get_icon('run_arrow.png')))
        self.bt_open_file.setToolTip('Select the export file on your drive')

        self.cb_include_meta = QCheckBox('Include meta data')
        self.cb_include_meta.setChecked(True)

        self.bbox = bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                            QDialogButtonBox.Cancel)

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------
        vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Export to:'))
        hbox.addWidget(self.txt_fname)
        hbox.addWidget(self.bt_open_file)
        vbox.addLayout(hbox)

        vbox.addWidget(self.cb_include_meta)

        vbox.addWidget(bbox)
        self.setLayout(vbox)

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------
        bbox.accepted.connect(self._export)
        bbox.rejected.connect(self.reject)
        self.bt_open_file.clicked.connect(self.get_open_file_name)

        if fname is not None:
            self.txt_fname.setText(fname)
            self._export()

    def get_open_file_name(self):
        def check_current():
            dirname = osp.dirname(current)
            if osp.exists(dirname) and osp.isdir(dirname):
                return dirname
        current = self.txt_fname.text().strip()
        start = None
        if current:
            start = check_current()
        if start is None:
            for attr in 'project_file', 'image_file':
                try:
                    current = self.stradi.get_attr(attr)
                except KeyError:
                    pass
                else:
                    start = check_current()
                    if start is not None:
                        break
        if start is None:
            start = os.getcwd()
        fname = QFileDialog.getSaveFileName(
            self, 'DataFrame file destination', start,
            'Excel files (*.xlsx *.xls);;'
            'csv files (*.csv);;'
            'All files (*)'
            )
        if with_qt5:  # the filter is passed as well
            fname = fname[0]
        if not fname:
            return
        self.txt_fname.setText(fname)

    def _export(self):
        fname = self.txt_fname.text()
        ending = osp.splitext(fname)[1]
        meta = self.stradi.valid_attrs.copy(True)
        meta.loc['exported'] = str(dt.datetime.now())
        if ending in ['.xls', '.xlsx']:
            with pd.ExcelWriter(fname) as writer:
                self.df.to_excel(writer, 'Data')
                if self.cb_include_meta.isChecked() and len(meta):
                    meta.to_excel(writer, 'Metadata', header=False)
        else:
            with open(fname, 'w') as f:
                if self.cb_include_meta.isChecked():
                    for t in meta.iloc[:, 0].items():
                        f.write('# %s: %s\n' % t)
            self.df.to_csv(fname, mode='a')
        self.accept()

    def cancel(self):
        del self.stradi, self.df
        super().cancel()

    def accept(self):
        del self.stradi, self.df
        super().accept()

    @classmethod
    def export_df(cls, parent, df, straditizer, fname=None, exec_=True):
        """Open a dialog for exporting a DataFrame"""
        dialog = cls(df, straditizer, fname, parent=parent)
        if fname is None:
            available_width = QDesktopWidget().availableGeometry().width() / 3.
            width = dialog.sizeHint().width()
            height = dialog.sizeHint().height()
            # The plot creator window should cover at least one third of the
            # screen
            dialog.resize(max(available_width, width), height)
            if exec_:
                dialog.exec_()
            else:
                return dialog


class StraditizerMenuActions(StraditizerControlBase):
    """An object to control the main functionality of a Straditizer

    This object is creates menu actions to load the straditizer"""

    save_actions = data_actions = text_actions = []

    window_layout_action = None

    #: The path to a directory from where to open a straditizer. Is set in the
    #: tutorial
    _dirname_to_use = None

    @property
    def all_actions(self):
        return chain(self.save_actions, self.data_actions, self.text_actions)

    def __init__(self, straditizer_widgets):
        self.init_straditizercontrol(straditizer_widgets)

    def setup_menu_actions(self, main):
        """Create the actions for the file menu

        Parameters
        ----------
        main: psyplot_gui.main.MainWindow
            The mainwindow whose menubar shall be adapted"""
        # load buttons
        self.open_menu = menu = QMenu('Open straditizer')
        main.open_project_menu.addMenu(self.open_menu)

        self.load_stradi_action = self._add_action(
            menu, 'Project or image', self.open_straditizer,
            tooltip='Reload a digitization project or load a picture')

        self.load_clipboard_action = self._add_action(
            menu, 'From clipboard', self.from_clipboard,
            tooltip='Load a picture from the clipboard')

        # save and export data buttons
        self.save_straditizer_action = self._add_action(
            main.save_project_menu, 'Save straditizer', self.save_straditizer,
            tooltip='Save the digitization project')

        self.save_straditizer_as_action = self._add_action(
            main.save_project_as_menu, 'Save straditizer as',
            self.save_straditizer_as,
            tooltip='Save the digitization project to a different file')

        self.export_data_menu = menu = QMenu('Straditizer data')
        main.export_project_menu.addMenu(menu)

        self.export_full_action = self._add_action(
            menu, 'Full data', self.export_full,
            tooltip='Export the full digitized data')

        self.export_final_action = self._add_action(
            menu, 'Samples', self.export_final,
            tooltip='Export the data at the sample locations')

        # close menu
        self.close_straditizer_action = self._add_action(
            main.close_project_menu, 'Close straditizer',
            self.straditizer_widgets.close_straditizer,
            tooltip='Close the current straditize project')

        self.close_all_straditizer_action = self._add_action(
            main.close_project_menu, 'Close all straditizers',
            self.straditizer_widgets.close_all_straditizers,
            tooltip='Close all open straditize projects')

        # export image buttons
        self.export_images_menu = menu = QMenu('Straditizer image(s)')
        menu.setToolTipsVisible(True)
        main.export_project_menu.addMenu(menu)

        self.export_full_image_action = self._add_action(
            menu, 'Full image', self.save_full_image,
            tooltip='Save the full image to a file')

        self.export_data_image_action = self._add_action(
            menu, 'Save data image', self.save_data_image,
            tooltip='Save the binary image that represents the data part')

        self.export_text_image_action = self._add_action(
            menu, 'Save text image', self.save_text_image,
            tooltip='Save the image part with the rotated column descriptions')

        # import image buttons
        self.import_images_menu = menu = QMenu('Import straditizer image(s)')
        menu.setToolTipsVisible(True)

        self.import_full_image_action = self._add_action(
            menu, 'Full image', self.import_full_image,
            tooltip='Import the diagram into the current project')

        self.import_data_image_action = self._add_action(
            menu, 'Data image', self.import_data_image,
            tooltip='Import the data part image')

        self.import_binary_image_action = self._add_action(
            menu, 'Binary data image', self.import_binary_image,
            tooltip='Import the binary image for the data part')

        self.import_text_image_action = self._add_action(
            menu, 'Text image', self.import_text_image,
            tooltip='Import the image for the column names')

        self.window_layout_action = main.window_layouts_menu.addAction(
            'Straditizer layout',
            self.straditizer_widgets.switch_to_straditizer_layout)

        self.save_actions = [self.export_full_image_action,
                             self.save_straditizer_action,
                             self.import_full_image_action]
        self.data_actions = [self.export_data_image_action,
                             self.export_full_action,
                             self.export_final_action,
                             self.import_binary_image_action,
                             self.import_data_image_action]
        self.text_actions = [self.export_text_image_action,
                             self.import_text_image_action]

        self.widgets2disable = [self.load_stradi_action,
                                self.load_clipboard_action]

        self.refresh()

    def setup_shortcuts(self, main):
        """Setup the shortcuts when switched to the straditizer layout"""
        main.register_shortcut(self.save_straditizer_action, QKeySequence.Save)
        main.register_shortcut(self.save_straditizer_as_action,
                               QKeySequence.SaveAs)
        main.register_shortcut(self.close_straditizer_action,
                               QKeySequence.Close)
        main.register_shortcut(
            self.close_all_straditizer_action,
            QKeySequence('Ctrl+Shift+W', QKeySequence.NativeText))

        main.register_shortcut(
            self.export_final_action, QKeySequence(
                'Ctrl+E', QKeySequence.NativeText))
        main.register_shortcut(
            self.export_full_action, QKeySequence(
                'Ctrl+Shift+E', QKeySequence.NativeText))
        main.register_shortcut(self.load_stradi_action,
                               [QKeySequence.Open, QKeySequence.New])

    def _add_action(self, menu, *args, **kwargs):
        tooltip = kwargs.pop('tooltip', None)
        a = menu.addAction(*args, **kwargs)
        if tooltip:
            a.setToolTip(tooltip)
        return a

    @property
    def _start_directory(self):
        def check_current():
            dirname = osp.dirname(current)
            if osp.exists(dirname) and osp.isdir(dirname):
                return dirname
        if self.straditizer is not None:
            current = None
            for attr in 'project_file', 'image_file':
                try:
                    current = self.straditizer.get_attr(attr)
                except KeyError:
                    pass
                else:
                    start = check_current()
                    if start is not None:
                        break
            if current:
                return osp.splitext(current)[0]
        return os.getcwd()

    def import_full_image(self, fname=None):
        image = self._open_image(fname)
        if image is not None:
            if self.straditizer is None:
                self.open_straditizer(image)
            else:
                self.straditizer.reset_image(image)

    def import_data_image(self, fname=None):
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.data_reader.reset_image(image)

    def import_binary_image(self, fname=None):
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.data_reader.reset_image(image, binary=True)

    def import_text_image(self, fname):
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.colnames_reader.highres_image = image

    def _open_image(self, fname=None):
        if fname is None or (not isinstance(fname, six.string_types) and
                             np.ndim(fname) < 2):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Stratigraphic diagram',
                self._dirname_to_use or self._start_directory,
                'All images '
                '(*.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not np.ndim(fname) and not fname:
            return
        elif np.ndim(fname) >= 2:
            return fname
        else:
            from PIL import Image
            return Image.open(fname)

    def open_straditizer(self, fname=None, *args, **kwargs):
        from straditize.straditizer import Straditizer
        if fname is None or (not isinstance(fname, six.string_types) and
                             np.ndim(fname) < 2):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Straditizer project',
                self._dirname_to_use or self._start_directory,
                'Projects and images '
                '(*.nc *.nc4 *.pkl *.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif'
                ' *.tiff);;'
                'NetCDF files (*.nc *.nc4);;'
                'Pickle files (*.pkl);;'
                'All images '
                '(*.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Raw RGBA bitmap (*.raw *.rbga);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not np.ndim(fname) and not fname:
            return
        elif np.ndim(fname) >= 2:
            stradi = Straditizer(fname, *args, **kwargs)
        elif fname.endswith('.nc') or fname.endswith('.nc4'):
            import xarray as xr
            ds = xr.open_dataset(fname)
            stradi = Straditizer.from_dataset(ds.load(), *args, **kwargs)
            stradi.set_attr('project_file', fname)
            ds.close()
        elif fname.endswith('.pkl'):
            stradi = Straditizer.load(fname, *args, **kwargs)
            stradi.set_attr('project_file', fname)
        else:
            from PIL import Image
            image = Image.open(fname)
            w, h = image.size
            im_size = w * h
            if im_size > 20e6:
                recom_frac = 17403188.0 / im_size
                answer = (
                    QMessageBox.Yes
                    if self.straditizer_widgets.always_yes else
                    QMessageBox.question(
                        self.straditizer_widgets, "Large straditizer image",
                        "This is a rather large image with %1.0f pixels. "
                        "Shall I reduce it to %1.0f%% of it's size for a "
                        "better interactive experience?<br>"
                        "If not, you can rescale it via<br><br>"
                        "Transform source image &rarr; Rescale image" % (
                            im_size, 100. * recom_frac)))
                if answer == QMessageBox.Yes:
                    image = image.resize((int(round(w * recom_frac)),
                                          int(round(h * recom_frac))))

            stradi = Straditizer(image, *args, **kwargs)
            stradi.set_attr('image_file', fname)
        self.finish_loading(stradi)
        self._dirname_to_use = None

    def finish_loading(self, stradi):
        self.straditizer = stradi
        stradi.show_full_image()
        self.create_sliders(stradi)
        self.set_stradi_in_console()
        self.stack_zoom_window()
        self.straditizer_widgets.refresh()

    def create_sliders(self, stradi):
        """Create sliders to navigate in the given axes"""
        ax = stradi.ax
        try:
            manager = ax.figure.canvas.manager
            dock = manager.window
            fig_widget = manager.parent_widget
        except AttributeError:
            raise
        from psyplot_gui.backend import FigureWidget
        import matplotlib.colors as mcol
        xs, ys = stradi.image.size
        fc = ax.figure.get_facecolor()
        rgb = tuple(np.round(np.array(mcol.to_rgb(fc)) * 255).astype(int))

        slh = QtWidgets.QSlider(Qt.Horizontal)
        slv = QtWidgets.QSlider(Qt.Vertical)

        slh.setStyleSheet("background-color:rgb{};".format(rgb))
        slv.setStyleSheet("background-color:rgb{};".format(rgb))

        slh.setMaximum(xs)
        slv.setMaximum(ys)
        slv.setInvertedAppearance(True)
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        vbox.setSpacing(0)
        hbox.setSpacing(0)

        hbox.addWidget(fig_widget)
        hbox.addWidget(slv)
        vbox.addLayout(hbox)
        vbox.addWidget(slh)

        w = FigureWidget()
        w.dock = dock
        w.setLayout(vbox)
        dock.setWidget(w)

        ax.callbacks.connect('xlim_changed', self.update_x_navigation_sliders)
        ax.callbacks.connect('ylim_changed', self.update_y_navigation_sliders)
        self.update_x_navigation_sliders(ax)
        self.update_y_navigation_sliders(ax)
        ref = weakref.ref(ax)
        slh.valueChanged.connect(self.set_ax_xlim(ref))
        slv.valueChanged.connect(self.set_ax_ylim(ref))

    @staticmethod
    def set_ax_xlim(ax_ref):
        """Define a function to update xlim from a given centered value"""
        def update(val):
            ax = ax_ref()
            if ax in _updating or ax is None:
                return

            _updating.append(ax)
            lims = ax.get_xlim()
            diff = (lims[1] - lims[0]) / 2
            ax.set_xlim(val - diff, val + diff)
            ax.figure.canvas.draw_idle()
            _updating.remove(ax)
        return update

    @staticmethod
    def set_ax_ylim(ax_ref):
        """Define a function to update ylim from a given centered value"""
        def update(val):
            ax = ax_ref()
            if ax in _updating or ax is None:
                return

            _updating.append(ax)
            lims = ax.get_ylim()
            diff = (lims[1] - lims[0]) / 2
            ax.set_ylim(val - diff, val + diff)
            ax.figure.canvas.draw_idle()
            _updating.remove(ax)
        return update

    @staticmethod
    def update_x_navigation_sliders(ax):
        """Update the horizontal navigation slider for the given `ax``
        """
        w = ax.figure.canvas.manager.window.widget()
        slh = w.layout().itemAt(1).widget()

        xc = np.mean(ax.get_xlim())

        slh.setValue(max(0, min(slh.maximum(), int(round(xc)))))

    @staticmethod
    def update_y_navigation_sliders(ax):
        """Update the vertical navigation slider for the given `ax``
        """
        w = ax.figure.canvas.manager.window.widget()
        slv = w.layout().itemAt(0).itemAt(1).widget()

        yc = np.mean(ax.get_ylim())
        slv.setValue(max(0, min(slv.maximum(), int(round(yc)))))

    def stack_zoom_window(self):
        from psyplot_gui.main import mainwindow
        if mainwindow.figures:
            found = False
            for stradi in self.straditizer_widgets._straditizers:
                if stradi is not self.straditizer and stradi.magni:
                    ref_dock = stradi.magni.ax.figure.canvas.manager.window
                    found = True
                    break
            if not found:
                ref_dock = mainwindow.help_explorer.dock
            dock = self.straditizer.magni.ax.figure.canvas.manager.window
            pos = mainwindow.dockWidgetArea(ref_dock)
            mainwindow.addDockWidget(pos, dock)
            if not found:
                mainwindow.addDockWidget(pos, ref_dock)
            else:
                mainwindow.tabifyDockWidget(ref_dock, dock)
                # show the zoom figure
                dock.widget().show_plugin()
                dock.raise_()
            mainwindow.figures.insert(-1, mainwindow.figures.pop(-1))
            # show the straditizer figure
            mainwindow.figures[-1].widget().show_plugin()
            mainwindow.figures[-1].raise_()

    def from_clipboard(self):
        from PIL import ImageGrab
        from straditize.straditizer import Straditizer
        image = ImageGrab.grabclipboard()
        if np.shape(image)[-1] == 3:
            image.putalpha(255)
        stradi = Straditizer(image)
        return self.finish_loading(stradi)

    def save_straditizer(self):
        try:
            fname = self.straditizer.attrs.loc['project_file', 0]
        except KeyError:
            fname = None
        return self.save_straditizer_as(fname)

    def save_straditizer_as(self, fname=None):
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                self._start_directory,
                ('NetCDF files (*.nc *.nc4);;Pickle files (*.pkl);;'
                 'All files (*)')
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not fname:
            return
        ending = os.path.splitext(fname)[1]
        self.straditizer.set_attr('saved', str(dt.datetime.now()))
        self.straditizer.set_attr('project_file', fname)
        if ending == '.pkl':
            self.straditizer.save(fname)
        else:
            ds = self.straditizer.to_dataset()
            # -- Compression with a level of 4. Requires netcdf4 engine
            comp = dict(zlib=True, complevel=4)
            encoding = {var: comp for var in ds.data_vars}

            ds.to_netcdf(fname, encoding=encoding, engine='netcdf4')

    def save_text_image(self, fname=None):
        reader = self.straditizer.colnames_reader
        self._save_image(reader.highres_image, fname)

    def save_full_image(self, fname=None):
        self._save_image(self.straditizer.image, fname)

    def save_data_image(self, fname=None):
        arr = np.tile(self.straditizer.data_reader.binary[:, :, np.newaxis],
                      (1, 1, 4))
        arr[..., 3] *= 255
        arr[..., :3] = 0
        image = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        self._save_image(image, fname)

    def set_stradi_in_console(self):
        from psyplot_gui.main import mainwindow
        global straditizer
        straditizer = self.straditizer
        if mainwindow is not None:
            mainwindow.console.kernel_manager.kernel.shell.run_code(
                'from %s import straditizer as stradi' % __name__)
        straditizer = None

    def _save_image(self, image, fname=None):
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                self._start_directory,
                'All images '
                '(*.png *.jpeg *.jpg *.pdf *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not fname:
            return
        ext = osp.splitext(fname)[1]
        if ext.lower() in ['.jpg', '.jpeg', '.pdf'] and image.mode == 'RGBA':
            image = rgba2rgb(image)
        image.save(fname)

    def _export_df(self, df, fname=None):
        ExportDfDialog.export_df(self.straditizer_widgets, df,
                                 self.straditizer, fname)

    def export_final(self, fname=None):
        try:
            df = self.straditizer.final_df
        except Exception as e:
            self.straditizer_widgets.error_msg.showTraceback(
                e.message if six.PY2 else str(e))
        else:
            self._export_df(df, fname)

    def export_full(self, fname=None):
        self._export_df(self.straditizer.full_df, fname)

    def refresh(self):
        stradi = self.straditizer
        import_stradi_action = getattr(self, 'import_full_image_action', None)
        if stradi is None:
            for w in filter(lambda w: w is not import_stradi_action,
                            self.all_actions):
                w.setEnabled(False)
        else:
            if stradi.data_reader is None:
                for w in self.data_actions:
                    w.setEnabled(False)
            else:
                reader = stradi.data_reader
                self.export_data_image_action.setEnabled(True)
                self.import_binary_image_action.setEnabled(True)
                self.import_data_image_action.setEnabled(True)
                self.export_full_action.setEnabled(reader.full_df is not None)
                self.export_final_action.setEnabled(reader.full_df is not None)
            for w in self.text_actions:
                w.setEnabled(stradi.colnames_reader is not None)
            for w in self.save_actions:
                w.setEnabled(True)

    def setup_children(self, item):
        tree = self.straditizer_widgets.tree

        # import menu
        import_child = QTreeWidgetItem(0)
        item.addChild(import_child)
        self.btn_import = QToolButton()
        self.btn_import.setText('Import images')
        self.btn_import.setMenu(self.import_images_menu)
        self.btn_import.setPopupMode(QToolButton.InstantPopup)
        tree.setItemWidget(import_child, 0, self.btn_import)

        # export menu
        export_child = QTreeWidgetItem(0)
        item.addChild(export_child)
        self.btn_export = QToolButton()
        self.btn_export.setText('Export images')
        self.btn_export.setMenu(self.export_images_menu)
        self.btn_export.setPopupMode(QToolButton.InstantPopup)
        tree.setItemWidget(export_child, 0, self.btn_export)
