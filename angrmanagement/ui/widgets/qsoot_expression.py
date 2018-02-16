
from PySide.QtCore import Qt

from .qgraph_object import QGraphObject


class QSootExpression(QGraphObject):
    def __init__(self, workspace, func_addr, disasm_view, disasm, infodock, stmt, expr, expr_index, config):

        super(QSootExpression, self).__init__()

        self.workspace = workspace
        self.disasm_view = disasm_view
        self.disasm = disasm
        self.infodock = infodock
        self.expr = expr
        self.expr_index = expr_index
        self._config = config

        self._label = None
        self._label_width = None

        self._init_widgets()

    #
    # Public methods
    #

    def paint(self, painter):
        """

        :param QPainter painter:
        :return:
        """

        x = self.x

        painter.drawText(x, self.y + self._config.disasm_font_ascent, self._label)

    def refresh(self):
        super(QSootExpression, self).refresh()

        self._init_widgets()

        self._update_size()

    #
    # Private methods
    #

    def _init_widgets(self):
        self._label = self.expr.render()[0]
        self._label_width = len(self._label) * self._config.disasm_font_width

        self._update_size()

    def _update_size(self):
        self._width = self._label_width
        self._height = self._config.disasm_font_height
