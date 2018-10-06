from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, \
    QLineEdit, QMessageBox

from ...utils.namegen import NameGenerator
from ..widgets import QAddressInput, QStateComboBox


class NewPath(QDialog):
    def __init__(self, workspace, addr, parent=None):
        super(NewPath, self).__init__(parent)

        # initialization

        self._addr = addr
        self._workspace = workspace

        self._name_box = None  # type: QLineEdit
        self._address_box = None
        self._status_label = None
        self._init_state_combo = None
        self._ok_button = None

        self.setWindowTitle('New Path')

        self.main_layout = QVBoxLayout()

        self._init_widgets()

        self.setLayout(self.main_layout)

        # self.show()

    #
    # Private methods
    #

    def _init_widgets(self):

        layout = QGridLayout()

        row = 0

        # name

        name_label = QLabel(self)
        name_label.setText("Name")

        name_box = QLineEdit(self)
        name_box.setText(NameGenerator.random_name())

        self._name_box = name_box

        layout.addWidget(name_label, row, 0)
        layout.addWidget(name_box, row, 1)
        row += 1

        # address label

        address_label = QLabel(self)
        address_label.setText('Address')

        address = QAddressInput(None, parent=self, default="%#x" % self._addr)
        self._address_box = address

        layout.addWidget(address_label, row, 0)
        layout.addWidget(address, row, 1)
        row += 1

        # initial state

        state_label = QLabel(self)
        state_label.setText('Initial state')

        init_state_combo = QStateComboBox(self._workspace.instance, self)
        self._init_state_combo = init_state_combo

        layout.addWidget(state_label, row, 0)
        layout.addWidget(init_state_combo, row, 1)
        row += 1

        # buttons

        ok_button = QPushButton(self)
        ok_button.setText('OK')
        ok_button.clicked.connect(self._on_ok_clicked)
        self._ok_button = ok_button

        cancel_button = QPushButton(self)
        cancel_button.setText('Cancel')
        cancel_button.clicked.connect(self._on_cancel_clicked)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)

        self.main_layout.addLayout(layout)
        self.main_layout.addLayout(buttons_layout)

    #
    # Event handlers
    #

    def _on_address_changed(self, new_text):
        if new_text.strip():
            self._ok_button.setEnabled(True)
        else:
            self._ok_button.setEnabled(False)

    def _on_ok_clicked(self):
        name = self._name_box.text()
        if not name:
            return

        self._addr = self._address_box.raw_target

        if self._addr is None:
            return

        if self._new_state(name, self._addr):
            self.close()

    def _on_cancel_clicked(self):
        self.cfg_args = None
        self.close()

    #
    # Private methods
    #

    def _new_state(self, state_name, addr):

        state = self._init_state_combo.state

        if state is None:
            QMessageBox.critical(self, "Unknown initial state",
                                 "Please select a state to start symbolic execution with.",
                                 QMessageBox.Ok
                                 )
            return False

        state._ip = addr

        self._workspace.create_simulation_manager(state, state_name)

        return True
