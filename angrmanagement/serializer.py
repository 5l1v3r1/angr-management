import angr
import simuvex

class Serializer(object):
    def __init__(self):
        pass

    def serialize(self, o, ref=False):
        if isinstance(o, angr.Surveyor):
            return self._serialize_surveyor(o)
        if isinstance(o, angr.Path):
            return self._serialize_path(o)
        if isinstance(o, simuvex.SimState):
            return self._serialize_state(o)
        if isinstance(o, simuvex.SimRun):
            return self._serialize_simrun(o, ref)
        else:
            raise Exception("Can't serialize %s", o)

    def _serialize_state(self, s):
        raise NotImplementedError("TODO")

    def _serialize_path(self, p):
        raise NotImplementedError("TODO")

    def _serialize_surveyor(self, s):
        return { 'id': s, 'active': 'TODO' }

    def _serialize_simrun(self, s, ref):
        if isinstance(s, simuvex.SimIRSB):
            data = {'type': 'IRSB', 'addr': s.addr}
            if not ref:
                data['irsb'] = s._crawl_vex(s.irsb)
            return data
        if isinstance(s, simuvex.SimProcedure):
            return {'type': 'proc', 'name': s.__class__.__name__}
        else:
            raise Exception("Can't serialize SimRun {}".format(s))
