"""The straditizer widgets

This module contains widgets to digitize the straditizer diagrams through a GUI
"""
import six
import os.path as osp
from psyplot_gui.compat.qtcompat import (
    QWidget, QtCore, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, Qt, QToolButton, QIcon, with_qt5,
    QComboBox, QLabel)
from psyplot_gui.common import (
    DockMixin, get_icon as get_psy_icon, PyErrorMessage)
import numpy as np
import glob


if with_qt5:
    from PyQt5.QtWidgets import QHeaderView
else:
    from PyQt4.QtGui import QHeaderView


def get_doc_file(fname):
    """Return the path to a documentation file"""
    return osp.join(osp.dirname(__file__), 'docs', fname)


def read_doc_file(fname):
    """Return the content of a rst documentation file"""
    with open(get_doc_file(fname)) as f:
        return f.read()


def get_icon(fname):
    """Return the path of an icon"""
    return osp.join(osp.dirname(__file__), 'icons', fname)


class EnableButton(QPushButton):
    """A `QPushButton` that emits a signal when enabled"""

    enabled = QtCore.pyqtSignal(bool)

    def setEnabled(self, b):
        if b is self.isEnabled():
            return
        super(EnableButton, self).setEnabled(b)
        self.enabled.emit(b)


def get_straditizer_widgets(mainwindow=None):
    """Get the :class:`StraditizerWidgets` from the psyplot GUI mainwindow"""
    if mainwindow is None:
        from psyplot_gui.main import mainwindow
    if mainwindow is None:
        raise NotImplementedError(
            "Not running in interactive psyplot GUI!")
    try:
        straditizer_widgets = mainwindow.plugins[
            'straditize.widgets:StraditizerWidgets:straditizer']
    except KeyError:
        raise KeyError('Straditize not implemented as a GUI plugin!')
    return straditizer_widgets


class StraditizerWidgets(QWidget, DockMixin):
    """A widget that contains widgets to control a
    :class:`straditize.straditizer.Straditizer`"""

    #: The QTreeWidget that contains the different widgets for the digitization
    tree = None

    #: The apply button
    apply_button = None

    #: The cancel button
    cancel_button = None

    #: The button to edit the straditizer attributes
    attrs_button = None

    #: The :class:`straditize.straditizer.Straditizer` instance
    straditizer = None

    #: open straditizers
    _straditizers = []

    dock_position = Qt.LeftDockWidgetArea

    hidden = True

    title = 'Stratigraphic diagram digitization'

    window_layout_action = None

    open_external = QtCore.pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        from straditize.widgets.menu_actions import StraditizerMenuActions
        from straditize.widgets.data import DigitizingControl
        from straditize.widgets.selection_toolbar import SelectionToolbar
        from straditize.widgets.marker_control import MarkerControl
        from straditize.widgets.plots import PlotControl
        from straditize.widgets.axes_translations import AxesTranslations
        from straditize.widgets.image_correction import ImageRotator
        self._straditizers = []
        super(StraditizerWidgets, self).__init__(*args, **kwargs)
        self.tree = QTreeWidget(parent=self)
        self.tree.setSelectionMode(QTreeWidget.NoSelection)
        self.refresh_button = QToolButton(self)
        self.refresh_button.setIcon(QIcon(get_psy_icon('refresh.png')))
        self.refresh_button.setToolTip('Refresh from the straditizer')
        self.apply_button = EnableButton('Apply', parent=self)
        self.cancel_button = EnableButton('Cancel', parent=self)
        self.attrs_button = QPushButton('Attributes', parent=self)
        self.error_msg = PyErrorMessage(self)
        self.stradi_combo = QComboBox()
        self.btn_open_stradi = QToolButton()
        self.btn_open_stradi.setIcon(QIcon(get_psy_icon('run_arrow.png')))
        self.btn_close_stradi = QToolButton()
        self.btn_close_stradi.setIcon(QIcon(get_psy_icon('invalid.png')))

        # ---------------------------------------------------------------------
        # --------------------------- Tree widgets ----------------------------
        # ---------------------------------------------------------------------
        self.tree.setHeaderLabels(['', ''])
        self.tree.setColumnCount(2)

        self.menu_actions = StraditizerMenuActions(self)

        self.digitizer = DigitizingControl(self)
        item = QTreeWidgetItem(0)
        item.setText(0, 'Digitization control')
        self.tree.addTopLevelItem(item)
        self.digitizer.setup_children(item)

        self.axes_translations = AxesTranslations(self)
        item = QTreeWidgetItem(0)
        item.setText(0, 'Axes translations')
        self.tree.addTopLevelItem(item)
        self.axes_translations.setup_children(item)

        self.image_rotator = ImageRotator(self)
        item = QTreeWidgetItem(0)
        item.setText(0, 'Rotate image')
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.addTopLevelItem(item)
        self.tree.setItemWidget(child, 0, self.image_rotator)

        self.plot_control = PlotControl(self)
        item = QTreeWidgetItem(0)
        item.setText(0, 'Plot control')
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.addTopLevelItem(item)
        self.tree.setItemWidget(child, 0, self.plot_control)
        self.add_info_button(item, 'plot_control.rst')

        self.marker_control = MarkerControl(self)
        item = QTreeWidgetItem(0)
        item.setText(0, 'Marker control')
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.addTopLevelItem(item)
        self.tree.setItemWidget(child, 0, self.marker_control)
        self.add_info_button(item, 'marker_control.rst')

        # ---------------------------------------------------------------------
        # ----------------------------- Toolbars ------------------------------
        # ---------------------------------------------------------------------
        self.selection_toolbar = SelectionToolbar(self, 'Selection toolbar')

        # ---------------------------------------------------------------------
        # ----------------------------- InfoButton ----------------------------
        # ---------------------------------------------------------------------
        self.info_button = InfoButton(self, get_doc_file('straditize.rst'))

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------

        stradi_box = QHBoxLayout()
        stradi_box.addWidget(self.stradi_combo, 1)
        stradi_box.addWidget(self.btn_open_stradi)
        stradi_box.addWidget(self.btn_close_stradi)

        attrs_box = QHBoxLayout()
        attrs_box.addWidget(self.attrs_button)
        attrs_box.addStretch(0)

        btn_box = QHBoxLayout()
        btn_box.addWidget(self.refresh_button)
        btn_box.addWidget(self.info_button)
        btn_box.addStretch(0)
        btn_box.addWidget(self.apply_button)
        btn_box.addWidget(self.cancel_button)

        vbox = QVBoxLayout()
        vbox.addLayout(stradi_box)
        vbox.addWidget(self.tree)
        vbox.addLayout(attrs_box)
        vbox.addLayout(btn_box)

        self.setLayout(vbox)

        self.apply_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.tree.expandItem(self.tree.topLevelItem(0))

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------
        self.stradi_combo.currentIndexChanged.connect(self.set_current_stradi)
        self.refresh_button.clicked.connect(self.refresh)
        self.attrs_button.clicked.connect(self.edit_attrs)
        self.open_external.connect(self._create_straditizer_from_args)
        self.btn_open_stradi.clicked.connect(
            self.menu_actions.open_straditizer)
        self.btn_close_stradi.clicked.connect(self.close_straditizer)

        self.refresh()
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

    def disable_apply_button(self):
        """Method that is called when the :attr:`cancel_button` is clicked"""
        self.apply_button.clicked.disconnect()
        self.cancel_button.clicked.disconnect()
        self.apply_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.apply_button.setText('Apply')
        self.cancel_button.setText('Cancel')
        self.refresh_button.setEnabled(True)

    def switch_to_straditizer_layout(self):
        mainwindow = self.dock.parent()
        mainwindow.figures_tree.hide_plugin()
        mainwindow.ds_tree.hide_plugin()
        self.show_plugin()
        mainwindow.tabifyDockWidget(mainwindow.project_content.dock, self.dock)
        hsize = self.marker_control.sizeHint().width() + 50
        self.menu_actions.setup_shortcuts(mainwindow)
        if with_qt5:
            mainwindow.resizeDocks([self.dock], [hsize], Qt.Horizontal)
            self.tree.resizeColumnToContents(0)
            self.tree.resizeColumnToContents(1)
        self.info_button.click()

    def to_dock(self, main, *args, **kwargs):
        ret = super(StraditizerWidgets, self).to_dock(main, *args, **kwargs)
        if self.menu_actions.window_layout_action is None:
            main.window_layouts_menu.addAction(self.window_layout_action)
            main.callbacks['straditize'] = self.open_external.emit
            main.addToolBar(self.selection_toolbar)
            self.dock.toggleViewAction().triggered.connect(
                self.show_or_hide_toolbar)
            self.menu_actions.setup_menu_actions(main)
        return ret

    def show_or_hide_toolbar(self):
        self.selection_toolbar.setVisible(self.is_shown)

    def _create_straditizer_from_args(self, args):
        """A method that is called when the :attr:`psyplot_gui.main.mainwindow`
        receives a 'straditize' callback"""
        self.create_straditizer_from_args(*args)

    def create_straditizer_from_args(self, fnames, project, xlim, ylim,
                                     full, reader_type):
            fname = fnames[0]
            if fname is not None:
                self.menu_actions.open_straditizer(fname)
                stradi = self.straditizer
                if stradi is None:
                    return
                if xlim is not None:
                    stradi.data_xlim = xlim
                if ylim is not None:
                    stradi.data_ylim = ylim
                if xlim is not None or ylim is not None or full:
                    if stradi.data_xlim is None:
                        stradi.data_xlim = [0, np.shape(stradi.image)[1]]
                    if stradi.data_ylim is None:
                        stradi.data_ylim = [0, np.shape(stradi.image)[0]]
                    stradi.init_reader(reader_type)
                    stradi.data_reader.digitize()
                self.refresh()
            if not self.is_shown:
                self.switch_to_straditizer_layout()

    def edit_attrs(self):
        def add_attr(key):
            model = editor.table.model()
            n = len(attrs)
            model.insertRow(n)
            model.setData(model.index(n, 0), key)
            model.setData(model.index(n, 1), '', change_type=six.text_type)
        from psyplot_gui.main import mainwindow
        from straditize.straditizer import common_attributes
        attrs = self.straditizer.attrs
        editor = mainwindow.new_data_frame_editor(
            attrs, 'Straditizer attributes')
        editor.table.resizeColumnToContents(1)
        editor.table.horizontalHeader().setVisible(False)
        editor.table.frozen_table_view.horizontalHeader().setVisible(False)
        combo = QComboBox()
        combo.addItems([''] + common_attributes)
        combo.currentTextChanged.connect(add_attr)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Common attributes:'))
        hbox.addWidget(combo)
        hbox.addStretch(0)
        editor.layout().insertLayout(1, hbox)
        return editor, combo

    def refresh(self):
        """Refresh from the straditizer"""
        for i, stradi in enumerate(self._straditizers):
            for key in ['project_file', 'image_file']:
                try:
                    self.stradi_combo.setItemText(
                        i, osp.basename(stradi.get_attr(key)))
                except KeyError:
                    pass
                else:
                    break
        # toggle visibility of close button and attributes button
        enable = self.straditizer is not None
        self.btn_close_stradi.setVisible(enable)
        self.attrs_button.setEnabled(enable)
        # refresh controls
        self.menu_actions.refresh()
        self.digitizer.refresh()
        self.selection_toolbar.refresh()
        self.plot_control.refresh()
        self.marker_control.refresh()
        self.axes_translations.refresh()

    def add_info_button(self, child, fname=None, rst=None, name=None,
                        connections=[]):
        button = InfoButton(self, fname=fname, rst=rst, name=name)
        self.tree.setItemWidget(child, 1, button)
        for btn in connections:
            btn.clicked.connect(button.click)
        return button

    def raise_figures(self):
        from psyplot_gui.main import mainwindow
        if mainwindow.figures and self.straditizer:
            dock = self.straditizer.ax.figure.canvas.manager.window
            dock.widget().show_plugin()
            dock.raise_()
            if self.straditizer.magni is not None:
                dock = self.straditizer.magni.ax.figure.canvas.manager.window
                dock.widget().show_plugin()
                dock.raise_()

    def set_current_stradi(self, i):
        """Set the i-th straditizer to the current one"""
        if not self._straditizers:
            return
        self.straditizer = self._straditizers[i]
        self.menu_actions.set_stradi_in_console()
        block = self.stradi_combo.blockSignals(True)
        self.stradi_combo.setCurrentIndex(i)
        self.stradi_combo.blockSignals(block)
        self.raise_figures()
        self.refresh()

    def close_straditizer(self):
        stradi = self.straditizer
        stradi.close()
        try:
            i = self._straditizers.index(stradi)
        except ValueError:
            pass
        else:
            del self._straditizers[i]
            self.stradi_combo.removeItem(i)
        if self._straditizers:
            self.stradi_combo.setCurrentIndex(0)
        else:
            self.straditizer = None
            self.refresh()

    def close_all_straditizers(self):
        for stradi in self._straditizers:
            stradi.close()
        self._straditizers.clear()
        self.stradi_combo.clear()
        self.refresh()

    def add_straditizer(self, stradi):
        if stradi and stradi not in self._straditizers:
            self._straditizers.append(stradi)
            self.stradi_combo.addItem(' ')
            self.set_current_stradi(len(self._straditizers) - 1)


class StraditizerControlBase(object):
    """A base class for the straditizer widget"""

    #: A list of widgets to disable or enable if the apply_button is enabled
    widgets2disable = []

    @property
    def straditizer(self):
        return self.straditizer_widgets.straditizer

    @straditizer.setter
    def straditizer(self, value):
        self.straditizer_widgets.straditizer = value
        self.straditizer_widgets.add_straditizer(value)

    @property
    def help_explorer(self):
        """The :class:`psyplot_gui.help_explorer.HelpExplorer` of the
        :attr:`psyplot_gui.main.mainwindow`"""
        from psyplot_gui.main import mainwindow
        return mainwindow.help_explorer

    @property
    def apply_button(self):
        return self.straditizer_widgets.apply_button

    @property
    def cancel_button(self):
        return self.straditizer_widgets.cancel_button

    def init_straditizercontrol(self, straditizer_widgets):
        self.straditizer_widgets = straditizer_widgets
        self.apply_button.enabled.connect(self.enable_or_disable_widgets)

    def enable_or_disable_widgets(self, b):
        if not b:  # use only those widget, that should be enabled
            it = filter(self.should_be_enabled, self.widgets2disable)
        else:
            it = self.widgets2disable
        for w in it:
            w.setEnabled(not b)

    def should_be_enabled(self, w):
        """Check if a widget should be enabled

        This function checks if a given widget `w` from the
        :attr:`widgets2disable` attribute should be enabled or not

        Parameters
        ----------
        w: QWidget
            The widget to check

        Returns
        -------
        bool
            True, if the widget should be enabled"""
        return True

    def refresh(self):
        """Refresh from the straditizer"""
        for w in self.widgets2disable:
            w.setEnabled(self.should_be_enabled(w))

    def connect2apply(self, *funcs):
        btn = self.apply_button
        for func in funcs:
            btn.clicked.connect(func)
        btn.clicked.connect(self.straditizer_widgets.disable_apply_button)
        btn.setEnabled(True)
        self.straditizer_widgets.refresh_button.setEnabled(False)

    def connect2cancel(self, *funcs):
        btn = self.cancel_button
        for func in funcs:
            btn.clicked.connect(func)
        btn.clicked.connect(self.straditizer_widgets.disable_apply_button)
        btn.setEnabled(True)
        self.straditizer_widgets.refresh_button.setEnabled(False)

    def add_info_button(self, child, fname=None, rst=None, name=None,
                        connections=[]):
        return self.straditizer_widgets.add_info_button(
            child, fname, rst, name, connections)


class InfoButton(QToolButton):
    """A button to display help informations in the help explorer"""

    def __init__(self, parent, fname=None, rst=None, name=None):
        if fname is None and rst is None:
            raise ValueError("Either `fname` or `rst` must be specified!")
        elif fname is not None and rst is not None:
            raise ValueError("Either `fname` or `rst` must be specified! "
                             "Not both!")
        elif rst is not None and name is None:
            raise ValueError("A title must be specified for the rst document!")
        self.fname = fname
        self.rst = rst
        self.files = glob.glob(get_doc_file('*.rst')) + glob.glob(
            get_doc_file('*.png')) + glob.glob(get_icon('*.png'))
        self.name = name
        QToolButton.__init__(self, parent)
        self.setIcon(QIcon(get_psy_icon('info.png')))
        self.clicked.connect(self.show_docs)

    def show_docs(self):
        from psyplot_gui.main import mainwindow
        if self.fname is not None:
            rst = read_doc_file(self.fname)
            name = osp.splitext(osp.basename(self.fname))[0]
        else:
            rst = self.rst
            name = self.name
        mainwindow.help_explorer.show_rst(
            rst, name, files=list(set(self.files) - {self.fname}))
