import pickle

from atom.api import Atom, Int, List, Typed

import ana
from angr import Project
from .workspace import WorkspaceData

class Instance(Atom):
    proj = Typed(Project)
    workspaces = List(WorkspaceData, [])
    counter = Int(1)

    def __init__(self, **kwargs):
        super(Instance, self).__init__(**kwargs)

    def add_workspace(self, wk):
        self.workspaces = self.workspaces + [wk]
        self.counter += 1

    def save(self, loc):
        with open(loc, 'wb') as f:
            pickled = pickle.dumps(self)
            store = ana.get_dl()._state_store
            pickle.dump({'store': store, 'pickled': pickled}, f)

    @staticmethod
    def from_file(loc):
        with open(loc, 'rb') as f:
            saved = pickle.load(f)
            ana.get_dl()._state_store = saved['store']
            return pickle.loads(saved['pickled'])

