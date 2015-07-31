import itertools
import functools

import pygraphviz

from atom.api import List, Typed, Dict, ForwardTyped, observe
from enaml.widgets.api import Container
from enaml.widgets.frame import Frame, ProxyFrame
from enaml.core.declarative import d_
from enaml.qt.QtGui import QGraphicsScene, QGraphicsView, QPainterPath, QPainter
from enaml.qt.QtCore import QPointF, QRectF, Qt
from enaml.qt.qt_frame import QtFrame
from enaml.qt.qt_factories import QT_FACTORIES
from enaml.qt.qt_container import QtContainer

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    args = [iter(iterable)] * n
    return itertools.izip_longest(*args, fillvalue=fillvalue)


class ZoomingGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            zoomInFactor = 1.25
            zoomOutFactor = 1 / zoomInFactor

            # Save the scene pos
            oldPos = self.mapToScene(event.pos())

            # Zoom
            if event.delta() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            self.scale(zoomFactor, zoomFactor)

            # Get the new position
            newPos = self.mapToScene(event.pos())

            # Move scene to old position
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y())
        else:
            super(ZoomingGraphicsView, self).wheelEvent(event)

class ProxyGraph(ProxyFrame):
    declaration = ForwardTyped(lambda: Graph)


class QtGraph(QtFrame, ProxyGraph):
    widget = Typed(QGraphicsView)
    scene = Typed(QGraphicsScene)
    _proxies = Dict()
    _edge_paths = List()

    def create_widget(self):
        self.scene = QGraphicsScene(self.parent_widget())
        self.widget = ZoomingGraphicsView(self.parent_widget())
        self.widget.setScene(self.scene)
        self.widget.setDragMode(QGraphicsView.ScrollHandDrag)
        self.widget.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.HighQualityAntialiasing)

    def child_added(self, child):
        super(QtGraph, self).child_added(child)
        cw = child.widget
        if cw is not None:
            cw.setParent(None)
            self._proxies[child] = self.scene.addWidget(cw)

    def child_removed(self, child):
        super(QtGraph, self).child_removed(child)
        if child in self._proxies:
            self.scene.removeItem(self._proxies[child])

    def init_layout(self):
        super(QtGraph, self).init_layout()

    def request_relayout(self):
        # y = 0.0

        # for child in self.children():
        #     if not isinstance(child, QtContainer):
        #         continue
        #     scene_proxy = self._proxies[child]
        #     width, height = child._layout_manager.best_size()
        #     scene_proxy.setPos(0.0, y)
        #     y += height + 25.0

        for p in self._edge_paths:
            self.scene.removeItem(p)
        self._edge_paths = []

        g = pygraphviz.AGraph(directed=True)
        g.graph_attr['nodesep'] = 100
        g.graph_attr['ranksep'] = 50
        g.node_attr['shape'] = 'rect'

        children_names = {child.declaration.name for child in self.children() if isinstance(child, QtContainer)}

        if any(from_ not in children_names or to not in children_names for (from_, to) in self.declaration.edges):
            # hasn't finished being set up yet
            return

        for child in self.children():
            if not isinstance(child, QtContainer):
                continue
            scene_proxy = self._proxies[child]
            width, height = child._layout_manager.best_size()
            scene_proxy.setGeometry(QRectF(0.0, 0.0, width, height))
            g.add_node(child.declaration.name, width=width, height=height)

        for from_, to in self.declaration.edges:
            g.add_edge(from_, to)

        g.layout(prog='dot')

        for child in self.children():
            if not isinstance(child, QtContainer):
                continue
            scene_proxy = self._proxies[child]
            node = g.get_node(child.declaration.name)
            center_x, center_y = (-float(v)/72.0 for v in node.attr['pos'].split(','))
            width, height = child._layout_manager.best_size()
            x = center_x - (width / 2.0)
            y = center_y - (height / 2.0)
            scene_proxy.setPos(x, y)

        for from_, to in self.declaration.edges:
            if from_ not in children_names or to not in children_names:
                continue
            edge = g.get_edge(from_, to)
            # TODO: look at below code
            all_points = [tuple(-float(v)/72.0 for v in t.strip('e,').split(',')) for t in edge.attr['pos'].split(' ')]
            arrow = all_points[0]
            start_point = all_points[1]

            painter = QPainterPath(QPointF(*start_point))
            for c1, c2, end in grouper(all_points[2:], 3):
                painter.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*end))

            self._edge_paths.append(self.scene.addPath(painter))

QT_FACTORIES['Graph'] = lambda: QtGraph


class Graph(Frame):
    #: The edges (as names) of the Graph
    edges = d_(List())

    proxy = Typed(ProxyGraph)

    hug_width = 'ignore'
    hug_height = 'ignore'

    def child_added(self, child):
        super(Graph, self).child_added(child)
        # print "got a child! %s" % child
        # if hasattr(child, 'path'):
        #     print "has id: %s" % child.path.path_id
        if isinstance(child, Container):
            self.request_relayout()

    @observe('edges')
    def _update(self, change):
        self.request_relayout()

# class BetterQtRawWidget(QtRawWidget):
#     def init_layout(self):
#         if hasattr(self.declaration, 'init_layout'):
#             self.declaration.init_layout()

# QT_FACTORIES['RawWidget'] = lambda: BetterQtRawWidget


# class Graph(RawWidget):
#     #: The edges (as IDs) of the Graph
#     edges = d_(List())

#     _view = Typed(QGraphicsView)
#     _scene = Typed(QGraphicsScene)
#     _proxies = Dict()

#     hug_width = 'ignore'
#     hug_height = 'ignore'

#     def create_widget(self, parent):
#         self._scene = QGraphicsScene(parent)
#         # t = self._scene.addText("hello world")
#         # t.setPos(25.0, 25.0)
#         # t2 = self._scene.addText("foo")
#         # t2.setPos(0.0, 0.0)

#         # add nodes...

#         self._view = QGraphicsView(parent)
#         self._view.setScene(self._scene)
#         self._view.setDragMode(QGraphicsView.ScrollHandDrag)

#         return self._view

#     def init_layout(self):
#         for child in self.children:
#             if not hasattr(child, 'proxy'):
#                 continue
#             child.proxy.widget.setParent(None)
#             scene_proxy = self._scene.addWidget(child.proxy.widget)
#             self._proxies[child] = scene_proxy

#         self.update_layout()

#     def child_added(self, child):
#         print "child added!"

#         if hasattr(child, 'proxy') and child.proxy is not None and child.proxy.widget is not None:
#             child.proxy.widget.setParent(None)
#             scene_proxy = self._scene.addWidget(child.proxy.widget)
#             self._proxies[child] = scene_proxy

#             self.update_layout()
#         else:
#             print "...but not available yet"

#     def update_layout(self):
#         y = 0.0

#         for child in self.children:
#             if not hasattr(child, 'proxy'):
#                 continue
#             scene_proxy = self._proxies[child]
#             width, height = child.proxy._layout_manager.best_size()
#             scene_proxy.setPos(0.0, y)
#             y += height + 50.0

#         __import__('ipdb').set_trace()

#         return

#         g = pygraphviz.AGraph(directed=True)
#         g.node_attr['shape'] = 'rect'

#         for child in self.children:
#             scene_proxy = self._proxies[child]
#             width, height = child.proxy._layout_manager.best_size()
#             # scene_proxy.setGeometry(QRectF(0.0, 0.0, width, height))
#             g.add_node(child.name, width=width, height=height)

#         for from_, to in self.edges:
#             g.add_edge(from_, to)

#         g.layout()

#         for child in self.children:
#             scene_proxy = self._proxies[child]
#             node = g.get_node(child.name)
#             x, y = (float(v) for v in node.attr['pos'].split(','))
#             scene_proxy.setPos(x, y)

#         self._view.setScene(self._scene)

#         # __import__('ipdb').set_trace()
