import functools
import json
import ast
import os
import random
import subprocess
import time
import uuid

import flask
from werkzeug.utils import secure_filename
import angr
from simuvex import SimIRSB, SimProcedure
import rpyc
from rpyc.utils.classic import obtain

try:
    import standard_logging #pylint:disable=W0611
    import angr_debug #pylint:disable=W0611
except ImportError:
    pass

from .serializer import Serializer

def spawn_child():
    port = random.randint(30000, 39999)
    cmd = ['python', '-c', '''from rpyc.core import SlaveService
from rpyc.utils.server import OneShotServer
OneShotServer(SlaveService, hostname='localhost', port={}).start()
'''.format(port)]
    subprocess.Popen(cmd)
    time.sleep(2.0)
    return rpyc.classic.connect('localhost', port)

def jsonize(func):
    @functools.wraps(func)
    def jsonned(*args, **kwargs):
        result = func(*args, **kwargs)
        try:
            return json.dumps(result)
        except:
            import ipdb; ipdb.set_trace()
    return jsonned

def with_projects(func):
    @functools.wraps(func)
    def projectsed(*args, **kwargs):
        return func(*args, projects=app.config['PROJECTS'], **kwargs)
    return projectsed

app = flask.Flask(__name__, static_folder='../static')
the_serializer = Serializer()
active_projects = {}
active_conns = {}
active_tokens = {}
active_surveyors = {}

ROOT = os.environ.get('ANGR_MANAGEMENT_ROOT', '.')
PROJDIR = ROOT + '/projects/'

@app.route('/')
def index():
    return app.send_static_file("index.html")

@app.route('/api/tokens/<token>')
@jsonize
def redeem(token):
    if token not in active_tokens:
        flask.abort(400)
    ty, async_thing, result = active_tokens[token]
    if result.ready:
        del active_tokens[token]
        if ty == 'CFG':
            cfg = result.value
            return {'ready': True, 'value': {
                'nodes': [the_serializer.serialize(node) for node in cfg._cfg.nodes()],
                'edges': [{'from': the_serializer.serialize(from_, ref=True),
                           'to': the_serializer.serialize(to, ref=True)}
                          for from_, to in cfg._cfg.edges()],
                'functions': {addr: obtain(f.basic_blocks) for addr, f in cfg.get_function_manager().functions.items()},
            }}
    else:
        return {'ready': False}

@app.route('/api/projects/')
@jsonize
def list_projects():
    # Makes sure the PROJDIR exists
    if not os.path.exists(PROJDIR):
        os.makedirs(PROJDIR)
    return {name: {'name': name, 'activated': name in active_projects} for name in app.config['PROJECTS']}

@app.route('/api/projects/', methods=('POST',))
@jsonize
def new_project():
    file = flask.request.files['file'] #pylint:disable=W0622
    metadata = json.loads(flask.request.form['metadata'])
    name = secure_filename(metadata['name'])
    os.mkdir(PROJDIR + name)
    file.save(PROJDIR + name + '/binary')
    open(PROJDIR + name + '/metadata', 'wb').write(json.dumps(metadata))

# @app.route('/api/projects/<name>/activate', methods=('POST',))
# @jsonize
# def activate_project(name):
#     name = secure_filename(name)
#     if name not in active_projects and os.path.exists(PROJDIR + name):
#         metadata = json.load(open(PROJDIR + name + '/metadata', 'rb'))
#         print metadata
#         remote = spawn_child()
#         active_conns[name] = remote
#         print remote
#         proj = remote.modules.angr.Project(PROJDIR + name + '/binary', load_libs=False,
#                                            default_analysis_mode='symbolic',
#                                            use_sim_procedures=True,
#                                            arch=str(metadata['arch']))
#         print type(proj)
#         active_projects[name] = proj

@app.route('/api/projects/<name>/cfg')
@with_projects
@jsonize
def get_cfg(name, projects=None):
    name = secure_filename(name)
    if name in projects:
        proj = projects[name]
        token = str(uuid.uuid4())
        async_construct = rpyc.async(proj.construct_cfg)
        active_tokens[token] = ('CFG', async_construct, async_construct())
        return {'token': token}
        return {
            'nodes': [the_serializer.serialize(node) for node in cfg._cfg.nodes()],
            'edges': [{'from': the_serializer.serialize(from_, ref=True),
                       'to': the_serializer.serialize(to, ref=True)}
                      for from_, to in cfg._cfg.edges()],
            'functions': {addr: obtain(f.basic_blocks) for addr, f in cfg.get_function_manager().functions.items()},
        }

@app.route('/api/projects/<name>/ddg')
@with_projects
@jsonize
def get_ddg(name, projects=None):
    name = secure_filename(name)
    if name in projects:
        proj = projects[name]
        ddg = angr.DDG(proj, proj.construct_cfg(), proj.entry)
        ddg.construct()
        return str(ddg._ddg)

def disasm(binary, block):
    return '\n'.join(binary.ida.idc.GetDisasm(s.addr)
                     for s in block.statements() if s.__class__.__name__ == 'IMark')

@app.route('/api/projects/<name>/dis/<int:block_addr>')
#@jsonize
def get_dis(name, block_addr):
    name = secure_filename(name)
    if name in active_projects:
        proj = active_projects[name]
        block = proj.block(block_addr)
        # import ipdb; ipdb.set_trace()
        return disasm(proj.main_binary, block)

#
# Surveyor functionality
#

@app.route('/api/surveyor_types')
@jsonize
def surveyor_types():
    return angr.surveyors.all_surveyors.keys()

@app.route('/api/projects/<project_name>/surveyors/new/<surveyor_type>', methods=('POST',))
@jsonize
def new_surveyor(project_name, surveyor_type):
    # TODO: take a SimExit as a starting point

    kwargs = dict(flask.request.json.get('kwargs', {}))
    for k,v in kwargs.items():
        if type(v) in (str,unicode) and v.startswith("PYTHON:"):
            kwargs[k] = ast.literal_eval(v[7:])

    p = active_projects[project_name]
    s = angr.surveyors.all_surveyors[surveyor_type](p, **kwargs)
    active_surveyors[str(id(s))] = s
    return the_serializer.serialize(s)

@app.route('/api/projects/<project_name>/surveyors')
@jsonize
def list_surveyors(project_name):
    p = active_projects[project_name]
    return [ the_serializer.serialize(s) for s in active_surveyors.itervalues() if s._project is p ]

@app.route('/api/projects/<project_name>/surveyors/<surveyor_id>')
@jsonize
def get_surveyor(project_name, surveyor_id): #pylint:disable=W0613
    return the_serializer.serialize(active_surveyors[surveyor_id])

@app.route('/api/projects/<project_name>/surveyors/<surveyor_id>/step', methods=('POST',))
@jsonize
def step_surveyors(project_name, surveyor_id): #pylint:disable=W0613
    steps = ( flask.request.json if flask.request.json is not None else flask.request.form ).get('steps', 1)
    s = active_surveyors[surveyor_id]
    s.run(n=int(steps))
    return the_serializer.serialize(s)

@app.route('/api/projects/<project_name>/surveyors/<surveyor_id>/resume/<path_id>', methods=('POST',))
@jsonize
def surveyor_resume_path(project_name, surveyor_id, path_id): #pylint:disable=W0613
    s = active_surveyors[surveyor_id]
    for list_name in s.path_lists:
        path_list = getattr(s, list_name)
        for p in path_list:
            if str(id(p)) == path_id:
                path_list.remove(p)
                s.active.append(p)
                return the_serializer.serialize(active_surveyors[surveyor_id])

@app.route('/api/projects/<project_name>/surveyors/<surveyor_id>/suspend/<path_id>', methods=('POST',))
@jsonize
def surveyor_suspend_path(project_name, surveyor_id, path_id): #pylint:disable=W0613
    s = active_surveyors[surveyor_id]
    for p in s.active:
        if str(id(p)) == path_id:
            s.active.remove(p)
            s.suspended.append(p)
            return the_serializer.serialize(active_surveyors[surveyor_id])
