from PySide2.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QMenu
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt

import angr

from ..dialogs.new_state import NewState


class QStateTableItem(QTableWidgetItem):
    def __init__(self, state, *args, **kwargs):
        super(QStateTableItem, self).__init__(*args, **kwargs)

        self.state = state

    def widgets(self):
        state = self.state

        name = state.gui_data.name
        base_name = state.gui_data.base_name
        is_changed = 'No' if state.gui_data.is_original else 'Yes'
        mode = state.mode
        address = '%#x' % state.addr if isinstance(state.addr, int) else 'Symbolic'
        state_options = {o for o, v in state.options._options.items() if v is True}
        options_plus = state_options - angr.sim_options.modes[mode]
        options_minus = angr.sim_options.modes[mode] - state_options
        options = ' '.join([' '.join('+' + o for o in options_plus), ' '.join('-' + o for o in options_minus)])

        widgets = [
            QTableWidgetItem(name),
            QTableWidgetItem(address),
            QTableWidgetItem(is_changed),
            QTableWidgetItem(base_name),
            QTableWidgetItem(mode),
            QTableWidgetItem(options),
        ]

        if state.gui_data.is_base:
            color = QColor(0, 0, 0x80)
        elif state.gui_data.is_original:
            color = QColor(0, 0x80, 0)
        else:
            color = QColor(0, 0, 0)

        for w in widgets:
            w.setFlags(w.flags() & ~Qt.ItemIsEditable)
            w.setForeground(color)

        return widgets


class QStateTable(QTableWidget):
    def __init__(self, instance, parent, selection_callback=None):
        super(QStateTable, self).__init__(parent)

        self._selected = selection_callback

        header_labels = [ 'Name', 'Address', 'Changed?', 'Base State', 'Mode', 'Options' ]

        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.items = [ ]
        self.instance = instance
        self.states = instance.states

        self.itemDoubleClicked.connect(self._on_state_selected)
        self.cellDoubleClicked.connect(self._on_state_selected)
        self.states.am_subscribe(self._watch_states)

    def current_state_record(self):
        selected_index = self.currentRow()
        if 0 <= selected_index < len(self.items):
            return self.items[selected_index]
        else:
            return None


    def reload(self):
        current_row = self.currentRow()
        self.clearContents()

        self.items = [QStateTableItem(f) for f in self.states]
        items_count = len(self.items)
        self.setRowCount(items_count)

        for idx, item in enumerate(self.items):
            for i, it in enumerate(item.widgets()):
                self.setItem(idx, i, it)

        #if 0 <= current_row < len(self.items):
        #    self.setCurrentItem(current_row, 0)

    def _on_state_selected(self, *args):
        if self._selected is not None:
            self._selected(self.current_state_record())

    def contextMenuEvent(self, event):
        sr = self.current_state_record()

        menu = QMenu("", self)

        menu.addAction('New state...', self._action_new_state)
        menu.addSeparator()

        a = menu.addAction('Duplicate state', self._action_duplicate)
        if sr is None:
            a.setDisabled(True)

        a = menu.addAction('Delete state', self._action_delete)
        if sr is None:
            a.setDisabled(True)

        a = menu.addAction('New simulation manager', self._action_new_simgr)
        if sr is None:
            a.setDisabled(True)

        menu.exec_(event.globalPos())

    def _action_new_state(self):
        dialog = NewState(self.instance, parent=self)
        dialog.exec_()
        if dialog.state is not None:
            self.states.append(dialog.state)
            self.states.am_event()

    def _action_duplicate(self):
        pass

    def _action_delete(self):
        self.states.pop(self.currentRow())
        self.states.am_event()

    def _action_new_simgr(self):
        pass

    def _watch_states(self, **kwargs):
        self.reload()
