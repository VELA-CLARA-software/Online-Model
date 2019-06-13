import time, os, subprocess, re
from ruamel import yaml
import traceback
import itertools
import copy
from collections import OrderedDict
from .ASTRARules import *
from SimulationFramework.Modules.merge_two_dicts import merge_two_dicts
from SimulationFramework.FrameworkHelperFunctions import *
import SimulationFramework.Modules.read_beam_file as rbf
import SimulationFramework.Executables as exes
beam = rbf.beam()
from operator import add
import progressbar
from munch import Munch, unmunchify
# from dotmap import DotMap

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(iter(list(data.items())))

def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

yaml.add_representer(OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)


astra_generator_keywords = {
    'keywords':[
        'fname','add','ipart','species','probe','noise_reduc','high_res','cathode','lprompt', 'q_total','ref_zpos','ref_clock','dist_z','ref_ekin','lt','rt','sig_clock','sig_z','lz','rz',
        'dist_pz','le','dist_x','sig_x','dist_y','sig_y','dist_px','nemit',
    ],
    'defaults': {
        'clara_400_3ps':{
            'add': False,'species': 'electrons', 'probe': True,'noise_reduc': False, 'high_res': True, 'cathode': True, 'lprompt': False, 'ref_zpos': 0, 'ref_clock': 0, 'dist_z': 'p',
            'ref_ekin': 0, 'lt': 3e-3, 'rt': 0.2e-3, 'dist_pz': 'i', 'le': 0.62e-3, 'dist_x': 'radial', 'sig_x': 0.25, 'dist_y': 'r', 'sig_y': 0.25,
        },
        'clara_400_1ps':{
            'add': False,'species': 'electrons', 'probe': True,'noise_reduc': False, 'high_res': True, 'cathode': True, 'lprompt': False, 'ref_zpos': 0, 'ref_clock': 0, 'dist_z': 'p',
            'ref_ekin': 0, 'lt': 1e-3, 'rt': 0.2e-3, 'dist_pz': 'i', 'le': 0.62e-3, 'dist_x': 'radial', 'sig_x': 0.25, 'dist_y': 'r', 'sig_y': 0.25,
        },
        'clara_400_2ps_Gaussian':{
            'add': False,'species': 'electrons', 'probe': True,'noise_reduc': False, 'high_res': True, 'cathode': True, 'lprompt': False, 'ref_zpos': 0, 'ref_clock': 0, 'dist_z': 'g',
            'sig_clock': 0.85e-3,
            'ref_ekin': 0, 'dist_pz': 'i', 'le': 0.62e-3, 'dist_x': 'radial', 'sig_x': 0.25, 'dist_y': 'r', 'sig_y': 0.25,
        },
    },
    'framework_keywords': [
        'number_of_particles', 'charge', 'filename',
    ]
}

elegant_generator_keywords = {
    'keywords':[
        'bunch','n_particles_per_bunch', 'time_start', 'matched_to_cell', 'emit_x', 'emit_nx', 'beta_x', 'alpha_x', 'eta_x', 'etap_x', 'emit_y',
        'emit_ny', 'beta_y', 'alpha_y', 'eta_y', 'etap_y', 'use_twiss_command_values', 'use_moments_output_values', 'Po', 'sigma_dp','sigma_s',
        'dp_s_coupling', 'emit_z', 'beta_z', 'alpha_z', 'momentum_chirp', 'one_random_bunch', 'symmetrize', 'optimized_halton', 'limit_invariants',
        'limit_in_4d', 'first_is_fiducial', 'save_initial_coordinates', 'halton_sequence', 'halton_radix', 'randomize_order', 'enforce_rms_values',
        'distribution_cutoff', 'distribution_type', 'centroid'
    ],
    'defaults': {
    },
    'framework_keywords': [
        'number_of_particles', 'charge', 'filename',
    ]
}

with open(os.path.dirname( os.path.abspath(__file__))+'/commands_Elegant.yaml', 'r') as infile:
    commandkeywords = yaml.load(infile, Loader=yaml.UnsafeLoader)

with open(os.path.dirname( os.path.abspath(__file__))+'/csrtrack_defaults.yaml', 'r') as infile:
    csrtrack_defaults = yaml.load(infile, Loader=yaml.UnsafeLoader)

with open(os.path.dirname( os.path.abspath(__file__))+'/elementkeywords.yaml', 'r') as infile:
    elementkeywords = yaml.load(infile, Loader=yaml.UnsafeLoader)

with open(os.path.dirname( os.path.abspath(__file__))+'/elements_Elegant.yaml', 'r') as infile:
    elements_Elegant = yaml.load(infile, Loader=yaml.UnsafeLoader)

type_conversion_rules_Elegant = {'dipole': 'csrcsbend', 'quadrupole': 'kquad', 'beam_position_monitor': 'moni', 'screen': 'watch', 'aperture': 'rcol',
                         'collimator': 'ecol', 'monitor': 'moni', 'solenoid': 'sole', 'wall_current_monitor': 'moni', 'cavity': 'rfcw',
                         'rf_deflecting_cavity': 'rfdf', 'drift': 'csrdrift', 'longitudinal_wakefield': 'wake', 'modulator': 'lsrmdltr'}

section_header_text_ASTRA = {'cavities': {'header': 'CAVITY', 'bool': 'LEField'},
                             'wakefields': {'header': 'WAKE', 'bool': 'LWAKE'},
                             'solenoids': {'header': 'SOLENOID', 'bool': 'LBField'},
                             'quadrupoles': {'header': 'QUADRUPOLE', 'bool': 'LQuad'},
                             'dipoles': {'header': 'DIPOLE', 'bool': 'LDipole'},
                             'astra_newrun': {'header': 'NEWRUN'},
                             'astra_output': {'header': 'OUTPUT'},
                             'astra_charge': {'header': 'CHARGE'},
                             'global_error': {'header': 'ERROR'},
                            }

def isevaluable(self, s):
    try:
        eval(s)
        return True
    except:
        return False

def expand_substitution(self, param, subs={}):
    if isinstance(param,(str)):
        regex = re.compile('\$(.*)\$')
        s = re.search(regex, param)
        if s:
            if isevaluable(self, s.group(1)) is True:
                replaced_str = str(eval(re.sub(regex, str(eval(s.group(1))), param)))
            else:
                replaced_str = re.sub(regex, s.group(1), param)
            for key in subs:
                replaced_str = replaced_str.replace(key, subs[key])
            if os.path.exists(replaced_str):
                replaced_str = os.path.relpath(replaced_str, master_subdir).replace('\\','/')
            return replaced_str
        else:
            return param
    else:
        return param

def checkValue(self, d, default=None):
    if isinstance(d,dict):
        if 'type' in d and d['type'] == 'list':
            if 'default' in d:
                return [a if a is not None else b for a,b in zip(d['value'],d['default'])]
            else:
                if isinstance(d['value'], list):
                    return [val if val is not None else default for val in d['value']]
                else:
                    return None
        else:
            d['value'] = expand_substitution(self, d['value'])
            return d['value'] if d['value'] is not None else d['default'] if 'default' in d else default
    elif isinstance(d, str):
        return getattr(self, d) if hasattr(self, d) and getattr(self, d) is not None else default

def clean_directory(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            #elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

def list_add(list1, list2):
    return list(map(add, list1, list2))

# def detect_changes(framework):
#     start = time.time()
#     origfw = Framework(None)
#     origfw.loadSettings(framework.settingsFilename)
#     changedict = {}
#     for e in framework.elementObjects:
#         if not origfw.elementObjects[e] == framework.elementObjects[e]:
#             orig = origfw.elementObjects[e]
#             new = framework.elementObjects[e]
#             changedict[e] = {k: new[k] for k in new if not new[k] == orig[k]}
#     return changedict
#
# def save_change_file(framework, filename=None):
#     if filename is None:
#         pre, ext = os.path.splitext(os.path.basename(framework.settingsFilename))
#         filename =  pre     + '_changes.yaml'
#     changedict = detect_changes(framework)
#     with open(filename,"w") as yaml_file:
#         yaml.dump(changedict, yaml_file, default_flow_style=False)
class Framework(Munch):

    def __init__(self, directory='test', master_lattice=None, overwrite=None, runname='CLARA_240', clean=False, verbose=True):
        super(Framework, self).__init__()
        global master_lattice_location
        self.verbose = verbose
        self.subdir = directory
        self.clean = clean
        self.elementObjects = OrderedDict()
        self.latticeObjects = OrderedDict()
        self.commandObjects = OrderedDict()
        self.groupObjects = OrderedDict()

        self.basedirectory = os.getcwd()
        self.filedirectory = os.path.dirname(os.path.abspath(__file__))
        self.overwrite = overwrite
        self.runname = runname
        if self.subdir is not None:
            self.setSubDirectory(self.subdir)
        if master_lattice is None:
            master_lattice_location = (os.path.relpath(os.path.dirname(os.path.abspath(__file__)) + '/../MasterLattice/')+'/').replace('\\','/')
        else:
            master_lattice_location = master_lattice

        self.executables = exes.Executables(master_lattice_location)
        self.defineASTRACommand = self.executables.define_astra_command
        self.defineElegantCommand = self.executables.define_elegant_command
        self.defineGeneratorCommand = self.executables.define_generator_command
        self.defineCSRTrackCommand = self.executables.define_csrtrack_command
        # self.executables = {'generator': [master_lattice_location+'Codes/generator'], 'astra': [master_lattice_location+'Codes/astra'],
        #                     'elegant': [master_lattice_location+'Codes/elegant'], 'csrtrack': [master_lattice_location+'Codes/csrtrack'],
        #                     'gpt': [r'C:/Program Files/General Particle Tracer/bin/gpt.exe']}

    def setSubDirectory(self, dir):
        global master_subdir, master_lattice_location
        self.subdirectory = os.path.abspath(self.basedirectory+'/'+dir)
        master_subdir = self.subdirectory
        if not os.path.exists(self.subdirectory):
            os.makedirs(self.subdirectory)
        else:
            if self.clean == True:
                clean_directory(self.subdirectory)
        if self.overwrite == None:
            self.overwrite = True
        # master_lattice_location = (os.path.relpath(os.path.dirname(os.path.abspath(__file__)) + '/../MasterLattice/', self.subdirectory)+'/').replace('\\','/')

    # def defineASTRACommand(self, ncpu=1):
    #     """Modify the defined ASTRA command variable"""
    #     self.executables.define_astra_command(
    #
    # def defineElegantCommand(self, command=['elegant']):
    #     """Modify the defined Elegant command variable"""
    #     self.executables['elegant'] = command
    #
    # def defineGeneratorCommand(self,command=['generator']):
    #     self.executables['generator'] = command
    #
    # def defineCSRTrackCommand(self,command=['csrtrack']):
    #     self.executables['csrtrack'] = command

    def load_Elements_File(self, input):
        if isinstance(input,(list,tuple)):
            filename = input
        else:
            filename = [input]
        for f in filename:
            if os.path.isfile(f):
                with open(f, 'r') as stream:
                    elements = yaml.load(stream, Loader=yaml.UnsafeLoader)['elements']
            else:
                with open(master_lattice_location + f, 'r') as stream:
                    elements = yaml.load(stream, Loader=yaml.UnsafeLoader)['elements']
            for name, elem in list(elements.items()):
                self.read_Element(name, elem)

    def loadSettings(self, filename='short_240.settings'):
        """Load Lattice Settings from file"""
        global master_run_no
        self.settingsFilename = filename
        # print 'self.settingsFilename = ', self.settingsFilename
        if os.path.exists(filename):
            stream = open(filename, 'r')
        else:
            stream = open(master_lattice_location+filename, 'r')
        self.settings = yaml.load(stream, Loader=yaml.UnsafeLoader)
        self.globalSettings = self.settings['global']
        master_run_no = self.globalSettings['run_no'] if 'run_no' in self.globalSettings else 1
        if 'generator' in self.settings:
            self.generatorSettings = self.settings['generator']
            self.add_Generator(**self.generatorSettings)
        self.fileSettings = self.settings['files']
        elements = self.settings['elements']
        self.groups = self.settings['groups'] if 'groups' in self.settings and self.settings['groups'] is not None else {}
        changes = self.settings['changes'] if 'changes' in self.settings and self.settings['changes'] is not None else {}
        stream.close()

        for name, elem in list(self.groups.items()):
            group = globals()[elem['type']](name, self.elementObjects, **elem)
            self.groupObjects[name] = group

        for name, elem in list(elements.items()):
            self.read_Element(name, elem)

        for name, lattice in list(self.fileSettings.items()):
            self.read_Lattice(name, lattice)

        self.apply_changes(changes)

        self.original_elementObjects = {}
        for e in self.elementObjects:
            self.original_elementObjects[e] = unmunchify(self.elementObjects[e])


    def read_Lattice(self, name, lattice):
        code = lattice['code'] if 'code' in lattice else 'astra'
        self.latticeObjects[name] = globals()[lattice['code'].lower()+'Lattice'](name, lattice, self.elementObjects, self.groupObjects, self.settings, self.executables)

    def convert_numpy_types(self, v):
        if isinstance(v, (np.ndarray, list, tuple)):
            return [self.convert_numpy_types(l) for l in v]
        elif isinstance(v, (np.float64, np.float32, np.float16, np.float_ )):
            return float(v)
        elif isinstance(v, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(v)
        else:
            return v

    def detect_changes(self, elementtype=None, elements=None, function=None):
        start = time.time()
        changedict = {}
        if elementtype is not None:
            changeelements = self.getElementType(elementtype, 'objectname')
        elif elements is not None:
            changeelements = elements
        else:
            changeelements = self.elementObjects
        # print('changeelements = ', changeelements)
        if len(changeelements) > 0 and len(changeelements[0]) > 1:
            for ek in changeelements:
                new = None
                e, k = ek[:2]
                if e in self.elementObjects:
                    new = unmunchify(self.elementObjects[e])
                elif e in self.groupObjects:
                    new = self.groupObjects[e]
                    # print 'detecting group = ', e, new, new[k]
                if new is not None:
                    if e not in changedict:
                        changedict[e] = {}
                    changedict[e][k] = self.convert_numpy_types(new[k])
        else:
            for e in changeelements:
                # print 'saving element: ', e
                if not self.original_elementObjects[e] == unmunchify(self.elementObjects[e]):
                    orig = self.original_elementObjects[e]
                    new = unmunchify(self.elementObjects[e])
                    changedict[e] = {k: self.convert_numpy_types(new[k]) for k in new if not new[k] == orig[k]}
        return changedict

    def save_changes_file(self, filename=None, type=None, elements=None, function=None):
        if filename is None:
            pre, ext = os.path.splitext(os.path.basename(self.settingsFilename))
            filename =  pre     + '_changes.yaml'
        changedict = self.detect_changes(elementtype=type, elements=elements, function=function)
        with open(filename,"w") as yaml_file:
            yaml.dump(changedict, yaml_file, default_flow_style=False)

    def load_changes_file(self, filename=None, apply=True):
        if isinstance(filename, (tuple, list)):
            for c in filename:
                self.load_changes_file(c)
        else:
            if filename is None:
                pre, ext = os.path.splitext(os.path.basename(self.settingsFilename))
                filename =  pre     + '_changes.yaml'
            with open(filename,"r") as infile:
                changes = dict(yaml.load(infile, Loader=yaml.UnsafeLoader))
            if apply:
                self.apply_changes(changes)
            else:
                return changes

    def apply_changes(self, changes):
        for e, d in list(changes.items()):
            # print 'found change element = ', e
            if e in self.elementObjects:
                # print 'change element exists!'
                for k, v in list(d.items()):
                    self.modifyElement(e, k, v)
                    # print ('modifying ',e,'[',k,']', ' = ', v)
            if e in self.groupObjects:
                # print ('change group exists!')
                for k, v in list(d.items()):
                    self.groupObjects[e].change_Parameter(k, v)
                    # print ('modifying ',e,'[',k,']', ' = ', v)

    def change_Lattice_Code(self, name, code):
        if name == 'All':
            [self.change_Lattice_Code(l, code) for l in self.latticeObjects]
        elif isinstance(name, (tuple, list)):
            [self.change_Lattice_Code(l, code) for l in name]
        else:
            if not name == 'generator':
                currentLattice = self.latticeObjects[name]
                self.latticeObjects[name] = globals()[code.lower()+'Lattice'](currentLattice.objectname, currentLattice.file_block, self.elementObjects, self.groupObjects, self.settings, self.executables)

    def read_Element(self, name, element, subelement=False):
        if name == 'filename':
            self.load_Elements_File(element)
        else:
            if subelement:
                self.add_Element(name, subelement=True, **element)
            else:
                self.add_Element(name, **element)
            if 'sub_elements' in element:
                for name, elem in list(element['sub_elements'].items()):
                    self.read_Element(name, elem, subelement=True)

    def add_Element(self, name=None, type=None, **kwargs):
        if name == None:
            if not 'name' in kwargs:
                raise NameError('Element does not have a name')
            else:
                name = kwargs['name']
        # try:
        element = globals()[type](name, type, **kwargs)
        # print element
        self.elementObjects[name] = element
        return element
        # except Exception as e:
        #     raise NameError('Element \'%s\' does not exist' % type)

    def getElement(self, element, param=None):
        if self.__getitem__(element) is not None:
            if param is not None:
                param = param.lower()
                return getattr(self.__getitem__(element), param)
            else:
                return self.__getitem__(element)
        else:
            print(( 'WARNING: Element ', element,' does not exist'))
            return {}

    def getElementType(self, type, setting=None):
        return [self.elementObjects[element] if setting is None else self.elementObjects[element][setting] for element in list(self.elementObjects.keys()) if self.elementObjects[element].objecttype.lower() == type.lower()]

    def setElementType(self, type, setting, values):
        elems = self.getElementType(type)
        if len(elems) == len(values):
            for e, v  in zip(elems, values):
                e[setting] = v
        else:
            # print(( len(elems), len(values)))
            raise ValueError

    def modifyElement(self, elementName, parameter, value):
        if elementName in self.groupObjects:
            self.groupObjects[elementName].change_Parameter(parameter,value)
        else:
            setattr(self.elementObjects[elementName], parameter, value)
        # set(getattr(self.elementObjects[elementName], parameter), value)

    def add_Generator(self, default=None, **kwargs):
        if default in astra_generator_keywords['defaults']:
            self.generator = frameworkGenerator(self.executables, **merge_two_dicts(kwargs,astra_generator_keywords['defaults'][default]))
        else:
            self.generator = frameworkGenerator(self.executables, **kwargs)
        self.latticeObjects['generator'] = self.generator

    def loadParametersFile(self, file):
        pass

    def saveParametersFile(self, file, parameters):
        output = {}
        if isinstance(parameters, dict):
            for k,v in list(parameters.items()):
                output[k] = {}
                if isinstance(v, (list, tuple)):
                    for p in v:
                        output[k][p] = getattr(self[k],p)
                else:
                    output[k][v] = getattr(self[k],v)
        elif isinstance(parameters, (list,tuple)):
            for k, v in parameters:
                output[k] = {}
                if isinstance(v, (list, tuple)):
                    for p in v:
                        output[k][p] = getattr(self[k],p)
                else:
                    output[k][v] = getattr(self[k],v)
        with open(file,"w") as yaml_file:
            yaml.dump(output, yaml_file, default_flow_style=False)
        # try:
        # elem = self.getelement(k, v)
        # outputfile.write(k+' '+v+' ')

    def __getitem__(self,key):
        if key in self.get('elementObjects', {}):
            return self.elementObjects.get(key)
        elif key in self.get('latticeObjects', {}):
            return self.latticeObjects.get(key)
        elif key in self.get('groupObjects', {}):
            return self.groupObjects.get(key)
        else:
            return self.get(key, None)

    @property
    def elements(self):
        return list(self.elementObjects.keys())

    @property
    def lines(self):
        return list(self.latticeObjects.keys())

    @property
    def commands(self):
        return list(self.commandObjects.keys())

    def track(self, files=None, startfile=None, endfile=None, preprocess=True, write=True, track=True, postprocess=True):
        if files is None:
            files = ['generator'] + self.lines if hasattr(self, 'generator') else self.lines
        if startfile is not None and startfile in files:
            index = files.index(startfile)
            files = files[index:]
        if endfile is not None and endfile in files:
            index = files.index(endfile)
            files = files[:index+1]
        if self.verbose:
            format_custom_text = progressbar.FormatCustomText(
                'File: %(running)s', {'running': ''}
            )
            bar = progressbar.ProgressBar(widgets=[format_custom_text, progressbar.Percentage(), progressbar.Bar(), progressbar.Percentage(),], max_value=len(files))
            format_custom_text.update_mapping(running=files[0]+'  ')
            for i in bar(list(range(len(files)))):
                l = files[i]
                if l == 'generator' and hasattr(self, 'generator'):
                    format_custom_text.update_mapping(running='Generator  ')
                    if write:
                        self.generator.write()
                    if track:
                        self.generator.run()
                    if postprocess:
                        self.generator.astra_to_hdf5()
                else:
                    if i == (len(files) - 1):
                        format_custom_text.update_mapping(running='Finished')
                    else:
                        format_custom_text.update_mapping(running=files[i+1]+'  ')
                    if preprocess:
                        self.latticeObjects[l].preProcess()
                    if write:
                        self.latticeObjects[l].write()
                    if track:
                        self.latticeObjects[l].run()
                    if postprocess:
                        self.latticeObjects[l].postProcess()
        else:
            for i in range(len(files)):
                l = files[i]
                if l == 'generator' and hasattr(self, 'generator'):
                    if write:
                        self.generator.write()
                    if track:
                        self.generator.run()
                    if postprocess:
                        self.generator.astra_to_hdf5()
                else:
                    if preprocess:
                        self.latticeObjects[l].preProcess()
                    if write:
                        self.latticeObjects[l].write()
                    if track:
                        self.latticeObjects[l].run()
                    if postprocess:
                        self.latticeObjects[l].postProcess()

class frameworkLattice(Munch):
    def __init__(self, name, file_block, elementObjects, groupObjects, settings, executables):
        super(frameworkLattice, self).__init__()
        self.objectname = name
        for key, value in list(elementObjects.items()):
            setattr(self, key, value)
        self.allElementObjects = elementObjects
        self.groupObjects = groupObjects
        self.allElements = list(self.allElementObjects.keys())
        self.file_block = file_block
        self.settings = settings
        self.globalSettings = settings['global']
        self.groupSettings = file_block['groups'] if 'groups' in file_block else {}
        self.update_groups()
        self.executables = executables
        self.lscDrifts = False

    @property
    def prefix(self):
        if 'input' not in self.file_block:
            self.file_block['input'] = {}
        if 'prefix' not in self.file_block['input']:
            self.file_block['input']['prefix'] = ''
        return self.file_block['input']['prefix']
    @prefix.setter
    def prefix(self, prefix):
        self.file_block['input']['prefix'] = prefix

    def update_groups(self):
        for g in list(self.groupSettings.keys()):
            if g in self.groupObjects:
                self.groupObjects[g].update(**self.groupSettings[g])

    def getElement(self, element, param=None):
        if element in self.allElements:
            if param is not None:
                return getattr(self.allElementObjects[element], param.lower())
            else:
                return self.allElements[element]
        elif element in list(self.groupObjects.keys()):
            if param is not None:
                return getattr(self.groupObjects[element], param.lower())
            else:
                return self.groupObjects[element]
        else:
            print(( 'WARNING: Element ', element,' does not exist'))
            return {}

    def getElementType(self, type, setting=None):
        return [self.elements[element] if setting is None else self.elements[element][setting] for element in list(self.elements.keys()) if self.elements[element].objecttype.lower() == type.lower()]

    def setElementType(self, type, setting, values):
        elems = self.getElementType(type)
        if len(elems) == len(values):
            for e, v  in zip(elems, values):
                e[setting] = v
        else:
            raise ValueError

    @property
    def quadrupoles(self):
        return self.getElementType('quadrupole')

    @property
    def cavities(self):
        return self.getElementType('cavity')

    @property
    def solenoids(self):
        return self.getElementType('solenoid')

    @property
    def dipoles(self):
        return self.getElementType('dipole')

    @property
    def kickers(self):
        return self.getElementType('kicker')

    @property
    def dipoles_and_kickers(self):
        return sorted(self.getElementType('dipole') + self.getElementType('kicker'), key=lambda x: x.position_end[2])

    @property
    def wakefields(self):
        return self.getElementType('longitudinal_wakefield')

    @property
    def screens(self):
        return self.getElementType('screen')

    @property
    def screens_and_bpms(self):
        return sorted(self.getElementType('screen') + self.getElementType('beam_position_monitor'), key=lambda x: x.position_end[2])

    @property
    def lines(self):
        return list(self.lineObjects.keys())

    @property
    def start(self):
        if 'start_element' in self.file_block['output']:
            return self.file_block['output']['start_element']
        elif 'zstart' in self.file_block['output']:
            for e in list(self.allElementObjects.keys()):
                if self.allElementObjects[e].position_start[2] == self.file_block['output']['zstart']:
                    return e
        else:
            return self.allElementObjects[0]

    @property
    def startObject(self):
        return self.allElementObjects[self.start]

    @property
    def end(self):
        if 'end_element' in self.file_block['output']:
            return self.file_block['output']['end_element']
        elif 'zstop' in self.file_block['output']:
            endelems = []
            for e in list(self.allElementObjects.keys()):
                if self.allElementObjects[e]['position_end'] == self.file_block['output']['zstop']:
                    endelems.append(e)
                elif self.allElementObjects[e]['position_end'] > self.file_block['output']['zstop'] and len(endelems) == 0:
                    endelems.append(e)
            return endelems[-1]
        else:
            return self.allElementObjects[0]

    @property
    def endObject(self):
        return self.allElementObjects[self.end]

    # @property
    def endScreen(self, **kwargs):
        return screen(name='end', type='screen', position_start=self.endObject.position_start, position_end=self.endObject.position_start, global_rotation=self.endObject.global_rotation, **kwargs)

    @property
    def elements(self):
        index_start = self.allElements.index(self.start)
        index_end = self.allElements.index(self.end)
        f = OrderedDict([[e,self.allElementObjects[e]] for e in self.allElements[index_start:index_end+1]])
        return f

    def createDrifts(self):
        """Insert drifts into a sequence of 'elements'"""
        positions = []
        originalelements = OrderedDict()
        elementno = 0
        newelements = OrderedDict()
        for name in list(self.elements.keys()):
            if not self.elements[name].subelement:
                originalelements[name] = self.elements[name]
                pos = np.array(self.allElementObjects[name].position_start)
                positions.append(pos)
                positions.append(self.allElementObjects[name].position_end)
        positions = positions[1:]
        positions.append(positions[-1])
        driftdata = list(zip(iter(list(originalelements.items())), list(chunks(positions, 2))))
        for e, d in driftdata:
            newelements[e[0]] = e[1]
            if len(d) > 1:
                x1, y1, z1 = d[0]
                x2, y2, z2 = d[1]
                length = np.sqrt((x2-x1)**2 + (z2-z1)**2)
                if length > 0:
                    elementno += 1
                    name = 'drift'+str(elementno)
                    if self.lscDrifts:
                        newdrift = csrdrift(name, type='csrdrift', **{'length': length,
                         'position_start': list(d[0]),
                         'position_end': list(d[1]),
                         'use_stupakov': 1,
                         'csrdz': 0.01,
                         'lsc_bins': 100,
                        })
                    else:
                        newdrift = csrdrift(name, type='csrdrift', **{'length': length,
                         'position_start': list(d[0]),
                         'position_end': list(d[1]),
                         'use_stupakov': 1,
                         'csrdz': 0.01,
                        })

                    newelements[name] = newdrift
        return newelements

    def getSValues(self):
        elems = self.createDrifts()
        s = [0]
        for e in list(elems.values()):
            s.append(s[-1]+e.length)
        return s[1:]

    def getNames(self):
        elems = self.createDrifts()
        return [e.objectname for e in list(elems.values())]

    def getSNames(self):
        s = self.getSValues()
        names = self.getNames()
        return list(zip(names, s))

    def findS(self, elem):
        if elem in self.allElements:
            sNames = self.getSNames()
            return [a for a in sNames if a[0] == elem]

    def write(self):
        pass

    def run(self):
        """Run the code with input 'filename'"""
        command = self.executables[self.code] + [self.objectname]
        with open(os.path.relpath(master_subdir+'/'+self.objectname+'.log', '.'), "w") as f:
            subprocess.call(command, stdout=f, cwd=master_subdir)

    def postProcess(self):
        pass

    def preProcess(self):
        pass

    def __repr__(self):
        return self.elements

    def __str__(self):
        str = self.objectname + ' = ('
        for e in self.elements:
            if len((str + e).splitlines()[-1]) > 60:
                str += '&\n'
            str += e+', '
        return str + ')'

class frameworkObject(Munch):

    def __init__(self, objectname=None, objecttype=None, **kwargs):
        super(frameworkObject, self).__init__()
        if objectname == None:
            raise NameError('Command does not have a name')
        if objecttype == None:
            raise NameError('Command does not have a type')
        setattr(self, 'objectdefaults', OrderedDict())
        setattr(self, 'objectname', objectname)
        setattr(self, 'objecttype', objecttype)
        if self.objecttype in commandkeywords:
            self.allowedkeywords = commandkeywords[self.objecttype]
        elif self.objecttype in elementkeywords:
            self.allowedkeywords = merge_two_dicts(elementkeywords[self.objecttype]['keywords'], elementkeywords['common']['keywords'])
            if 'framework_keywords' in  elementkeywords[self.objecttype]:
                 self.allowedkeywords = merge_two_dicts(self.allowedkeywords, elementkeywords[self.objecttype]['framework_keywords'])
        else:
            print(( 'Unknown type = ', objecttype))
            raise NameError
        self.allowedkeywords = [x.lower() for x in self.allowedkeywords]
        for key, value in list(kwargs.items()):
            self.add_property(key, value)

    def add_property(self, key, value):
        key = key.lower()
        if key in self.allowedkeywords:
            try:
                setattr(self, key, value)
            except Exception as e:
                print((self.objecttype,'[', key, ']: ', e))

    def add_default(self, key, value):
        self.objectdefaults[key] = value

    @property
    def parameters(self):
        return list(self.keys())

    @property
    def objectproperties(self):
        return self

    def __getitem__(self, key, default=None):
        key = key.lower()
        defaults = self.get('objectdefaults', {})
        if key in defaults:
            return self.get(key, defaults[key])
        else:
            return self.get(key, None)

    def __repr__(self):
        string = ''
        for k,v in list(self.items()):
            string+="{} ({})".format(k, v)+'\n'
        return string

class elegantLattice(frameworkLattice):
    def __init__(self, *args, **kwargs):
        super(elegantLattice, self).__init__(*args, **kwargs)
        self.code = 'elegant'
        self.particle_definition = self.allElementObjects[self.start].objectname
        self.bunch_charge = None
        self.q = charge(name='START', type='charge',**{'total': 250e-12})
        self.sample_interval = self.file_block['input']['sample_interval'] if 'input' in self.file_block and 'sample_interval' in self.file_block['input'] else 1

    def writeElements(self):
        self.w = self.endScreen(output_filename=self.end+'.SDDS')
        elements = self.createDrifts()
        fulltext = ''
        fulltext += self.q.write_Elegant()
        for element in list(elements.values()):
            if not element.subelement:
                fulltext += element.write_Elegant()
        fulltext += self.w.write_Elegant()
        fulltext += self.objectname+': Line=(START, '
        for e, element in list(elements.items()):
            if not element.subelement:
                if len((fulltext + e).splitlines()[-1]) > 60:
                    fulltext += '&\n'
                fulltext += e+', '
        return fulltext[:-2] + ', END )\n'

    def write(self):
        self.lattice_file = master_subdir+'/'+self.objectname+'.lte'
        saveFile(self.lattice_file, self.writeElements())
        self.command_file = master_subdir+'/'+self.objectname+'.ele'
        saveFile(self.command_file, self.commandFile.write())

    def preProcess(self):
        prefix = self.file_block['input']['prefix'] if 'input' in self.file_block and 'prefix' in self.file_block['input'] else ''
        # print 'prefix = ', prefix
        self.hdf5_to_sdds(prefix)
        self.commandFile = elegantTrackFile(lattice=self, elegantbeamfilename=self.particle_definition+'.sdds', sample_interval=self.sample_interval)

    def postProcess(self):
        for s in self.screens:
            s.sdds_to_hdf5()
        self.w.sdds_to_hdf5()

    def hdf5_to_sdds(self, prefix=''):
        HDF5filename = prefix+self.particle_definition+'.hdf5'
        beam.read_HDF5_beam_file(master_subdir + '/' + HDF5filename)
        if self.bunch_charge is not None:
            self.q = charge(name='START', type='charge',**{'total': abs(self.bunch_charge)})
        else:
            self.q = charge(name='START', type='charge',**{'total': abs(beam.charge)})
        sddsbeamfilename = self.particle_definition+'.sdds'
        beam.write_SDDS_file(master_subdir + '/' + sddsbeamfilename)

    def run(self):
        """Run the code with input 'filename'"""
        if not os.name == 'nt':
            command = self.executables[self.code] + ['-rpnDefns='+os.path.relpath(master_lattice_location,master_subdir)+'/Codes/defns.rpn'] + [self.objectname+'.ele']
        else:
            command = self.executables[self.code] + [self.objectname+'.ele']
        # print ('run command = ', command)
        with open(os.path.relpath(master_subdir+'/'+self.objectname+'.log', '.'), "w") as f:
            subprocess.call(command, stdout=f, cwd=master_subdir)

class elegantCommandFile(object):
    def __init__(self, lattice='', *args, **kwargs):
        super(elegantCommandFile, self).__init__()
        self.commandObjects = OrderedDict()
        self.lattice_filename = lattice.objectname+'.lte'

    def addCommand(self, name=None, **kwargs):
        if name == None:
            if not 'name' in kwargs:
                if not 'type' in kwargs:
                    raise NameError('Command does not have a name')
                else:
                    name = kwargs['type']
            else:
                name = kwargs['name']
        command = frameworkCommand(name, **kwargs)
        self.commandObjects[name] = command
        return command

    def write(self):
        output = ''
        for c in list(self.commandObjects.values()):
            output += c.write()
        return output

class elegantTrackFile(elegantCommandFile):
    def __init__(self, lattice='', elegantbeamfilename='', *args, **kwargs):
        super(elegantTrackFile, self).__init__(lattice, *args, **kwargs)
        self.elegantbeamfilename = elegantbeamfilename
        self.sample_interval = kwargs['sample_interval'] if 'sample_interval' in kwargs else 1
        self.addCommand(type='run_setup',lattice=self.lattice_filename, \
            use_beamline=lattice.objectname,p_central=np.mean(beam.BetaGamma), \
            centroid='%s.cen',always_change_p0 = 1, \
            sigma='%s.sig', default_order=3)
        self.addCommand(type='run_control',n_steps=1, n_passes=1)
        self.addCommand(type='twiss_output',matched = 0,output_at_each_step=0,radiation_integrals=1,statistics=1,filename="%s.twi",
        beta_x  = beam.beta_x,
        alpha_x = beam.alpha_x,
        beta_y  = beam.beta_y,
        alpha_y = beam.alpha_y)
        flr = self.addCommand(type='floor_coordinates', filename="%s.flr",
        X0  = lattice.startObject['position_start'][0],
        Z0 = lattice.startObject['position_start'][2],
        theta0 = 0)
        mat = self.addCommand(type='matrix_output', SDDS_output="%s.mat",
        full_matrix_only=1, SDDS_output_order=2)
        self.addCommand(type='sdds_beam', input=self.elegantbeamfilename, sample_interval=self.sample_interval)
        self.addCommand(type='track')

class elegantOptimisation(elegantCommandFile):

    def __init__(self, lattice='', variables={}, constraints={}, terms={}, settings={}, *args, **kwargs):
        super(elegantOptimisation, self).__init__(lattice, *args, **kwargs)
        for k, v in list(variables.items()):
            self.add_optimisation_variable(k, **v)

    def add_optimisation_variable(self, name, item=None, lower=None, upper=None, step=None, restrict_range=None):
        self.addCommand(name=name, type='optimization_variable', item=item, lower_limit=lower, upper_limit=upper, step_size=step, force_inside=restrict_range)

    def add_optimisation_constraint(self, name, item=None, lower=None, upper=None):
        self.addCommand(name=name, type='optimization_constraint', quantity=item, lower=lower, upper=upper)

    def add_optimisation_term(self, name, item=None, **kwargs):
        self.addCommand(name=name, type='optimization_term', term=item, **kwargs)


class frameworkCommand(frameworkObject):

    def __init__(self, name=None, type=None, **kwargs):
        super(frameworkCommand, self).__init__(name, type, **kwargs)
        if not type in commandkeywords:
            raise NameError('Command \'%s\' does not exist' % commandname)

    def write(self):
        wholestring=''
        string = '&'+self.objecttype+'\n'
        # print(self.objecttype, self.objectproperties)
        for key in commandkeywords[self.objecttype]:
            if key.lower() in self.objectproperties and not key =='name' and not key == 'type' and not self.objectproperties[key.lower()] is None:
                string+='\t'+key+' = '+str(self.objectproperties[key.lower()])+'\n'
        string+='&end\n'
        return string

class astraLattice(frameworkLattice):
    def __init__(self, *args, **kwargs):
        super(astraLattice, self).__init__(*args, **kwargs)
        self.code = 'astra'
        self.bunch_charge = None
        self.headers = OrderedDict()
        self.starting_offset = eval(expand_substitution(self, self.file_block['starting_offset'])) if 'starting_offset' in self.file_block else [0,0,0]

        # This calculated the starting rotation based on the input file and the number of dipoles
        self.starting_rotation = -1*self.allElementObjects[self.start].global_rotation[2] if self.allElementObjects[self.start].global_rotation is not None else 0
        # print 'self.starting_rotation = ', self.starting_rotation
        # Calculate the correct starting offset by adding up the dipole angles
        for d in self.dipoles:
            self.starting_rotation -= d.angle
        # print 'self.starting_rotation after subtraction = ', self.starting_rotation
        self.starting_rotation = eval(expand_substitution(self, str(self.file_block['starting_rotation']))) if 'starting_rotation' in self.file_block else self.starting_rotation
        # print 'self.starting_rotation at end = ', self.starting_rotation

        # Create a "newrun" block
        if 'input' not in self.file_block:
            self.file_block['input'] = {}
        self.headers['newrun'] = astra_newrun(self.starting_offset, self.starting_rotation, **merge_two_dicts(self.file_block['input'],self.globalSettings['ASTRAsettings']))
        # If the initial distribution is derived from a generator file, we should use that
        if self.headers['newrun']['particle_definition'] == 'initial_distribution':
            self.headers['newrun']['particle_definition'] = 'laser.astra'
        else:
            self.headers['newrun']['particle_definition'] = self.allElementObjects[self.start].objectname+'.astra'

        # Create an "output" block
        if 'output' not in self.file_block:
            self.file_block['output'] = {}
        self.headers['output'] = astra_output(self.screens_and_bpms, self.starting_offset, self.starting_rotation, **merge_two_dicts(self.file_block['output'],self.globalSettings['ASTRAsettings']))

        # Create a "charge" block
        if 'charge' not in self.file_block:
            self.file_block['charge'] = {}
        self.headers['charge'] = astra_charge(**merge_two_dicts(self.file_block['charge'],self.globalSettings['ASTRAsettings']))

        # Create an "error" block
        if 'global_errors' not in self.file_block:
            self.file_block['global_errors'] = {}
        if 'global_errors' not in self.globalSettings:
            self.globalSettings['global_errors'] = {}
        if 'global_errors' in self.file_block or 'global_errors' in self.globalSettings:
            self.global_error = global_error(name=self.objectname+'_global_error')
            self.headers['global_errors'] = astra_errors(element=self.global_error, **merge_two_dicts(self.file_block['global_errors'], self.globalSettings['global_errors']))
        # print 'errors = ', self.file_block, self.headers['global_errors']

    def writeElements(self):
        fulltext = ''
        # Create objects for the newrun, output and charge blocks
        self.headers['output'].start_element = self.allElementObjects[self.start]
        self.headers['output'].end_element = self.allElementObjects[self.end]
        # write the headers and their elements
        for header in self.headers:
            fulltext += self.headers[header].write_ASTRA()+'\n'
        # Initialise a counter object
        counter = frameworkCounter(sub={'kicker': 'dipole'})
        for t in [['cavities'], ['wakefields'], ['solenoids'], ['quadrupoles'], ['dipoles', 'dipoles_and_kickers']]:
            fulltext += '&' + section_header_text_ASTRA[t[0]]['header']+'\n'
            elements = getattr(self, t[-1])
            fulltext += section_header_text_ASTRA[t[0]]['bool']+' = '+str(len(elements) > 0)+'\n'
            for element in elements:
                element.starting_offset = self.starting_offset
                element.starting_rotation = self.starting_rotation
                elemstr = element.write_ASTRA(counter.counter(element.objecttype))
                if elemstr is not None and not elemstr == '':
                    fulltext += elemstr+'\n'
                    if element.objecttype == 'kicker':
                        counter.add(element.objecttype,2)
                    elif element.objecttype == 'longitudinal_wakefield':
                        counter.add(element.objecttype, element.cells)
                    else:
                        counter.add(element.objecttype)
            fulltext += '\n/\n'
        return fulltext

    def write(self):
        self.code_file = master_subdir+'/'+self.objectname+'.in'
        saveFile(self.code_file, self.writeElements())

    def preProcess(self):
        prefix = self.file_block['input']['prefix'] if 'input' in self.file_block and 'prefix' in self.file_block['input'] else ''
        self.headers['newrun'].hdf5_to_astra(prefix)
        self.headers['charge'].npart = len(beam.x)

    def postProcess(self):
        for e in self.screens_and_bpms:
            if not self.starting_offset == [0,0,0]:
                e.zstart = self.allElementObjects[self.start].start
            else:
                e.zstart = [0,0,0]
            e.astra_to_hdf5(self.objectname)
        self.astra_to_hdf5()

    def astra_to_hdf5(self):
        if not self.starting_offset == [0,0,0]:
            zstart = self.allElementObjects[self.start].start
        else:
            zstart = [0,0,0]
        endpos = np.array(self.allElementObjects[self.end].end)-np.array(zstart)
        astrabeamfilename = self.objectname + '.' + str(int(round(endpos[2]*100))).zfill(4) + '.' + str(master_run_no).zfill(3)
        beam.read_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)
        beam.rotate_beamXZ(-1*self.starting_rotation, preOffset=[0,0,0], postOffset=-1*np.array(self.starting_offset))
        HDF5filename = self.allElementObjects[self.end].objectname+'.hdf5'
        beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, centered=False, sourcefilename=astrabeamfilename, pos=self.allElementObjects[self.end].middle)

class gptLattice(frameworkLattice):
    def __init__(self, *args, **kwargs):
        super(gptLattice, self).__init__(*args, **kwargs)
        self.code = 'gpt'
        self.headers = OrderedDict()
        # self.headers['newrun'] = astra_newrun(**merge_two_dicts(self.file_block['input'],self.globalSettings['ASTRAsettings']))
        # self.headers['output'] = astra_output(self.screens_and_bpms, **merge_two_dicts(self.file_block['output'],self.globalSettings['ASTRAsettings']))
        # self.headers['charge'] = astra_charge(**merge_two_dicts(self.file_block['charge'],self.globalSettings['ASTRAsettings']))
        # if self.headers['newrun'].particle_definition == 'initial_distribution':
        #             self.headers['newrun'].particle_definition = 'laser.astra'
        # else:
        #     self.headers['newrun'].particle_definition = self.allElementObjects[self.start].objectname+'.astra'
    def writeElements(self):
        fulltext = ''
        for element in list(self.elements.values()):
            fulltext += element.write_GPT(1)
        fulltext += self.endScreen().write_GPT(1)
        return fulltext

    def write(self):
        self.code_file = master_subdir+'/'+self.objectname+'.in'
        # saveFile(self.code_file, self.writeElements())
        return self.writeElements()

    def preProcess(self):
        self.headers['newrun'].hdf5_to_astra()

    def postProcess(self):
        for e in self.screens_and_bpms:
            e.astra_to_hdf5(self.objectname)
        self.astra_to_hdf5()

    def astra_to_hdf5(self):
        astrabeamfilename = self.objectname + '.' + str(int(round((self.allElementObjects[self.end].position_end[2])*100))).zfill(4) + '.' + str(master_run_no).zfill(3)
        beam.read_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)
        HDF5filename = self.allElementObjects[self.end].objectname+'.hdf5'
        beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, centered=False, sourcefilename=astrabeamfilename)

class csrtrackLattice(frameworkLattice):
    def __init__(self, *args, **kwargs):
        super(csrtrackLattice, self).__init__(*args, **kwargs)
        self.code = 'csrtrack'
        self.particle_definition = ''
        self.CSRTrackelementObjects = OrderedDict()
        self.set_particles_filename()

    def set_particles_filename(self):
        self.CSRTrackelementObjects['particles'] = csrtrack_particles(particle_definition=self.particle_definition)
        self.CSRTrackelementObjects['particles'].format = 'astra'
        if self.particle_definition == 'initial_distribution':
            self.CSRTrackelementObjects['particles'].particle_definition = 'laser.astra'
            self.CSRTrackelementObjects['particles'].add_default('array', '#file{name=laser.astra}')
        else:
            self.CSRTrackelementObjects['particles'].particle_definition = self.allElementObjects[self.start].objectname
            self.CSRTrackelementObjects['particles'].add_default('array', '#file{name='+self.allElementObjects[self.start].objectname+'.astra'+'}')

    @property
    def dipoles_screens_and_bpms(self):
        return sorted(self.getElementType('dipole') + self.getElementType('screen') + self.getElementType('beam_position_monitor'), key=lambda x: x.position_end[2])

    def setCSRMode(self):
        if 'csr' in self.file_block and 'csr_mode' in self.file_block['csr']:
            if self.file_block['csr']['csr_mode'] == '3D':
                self.CSRTrackelementObjects['forces'] = csrtrack_forces(type='csr_g_to_p')
            elif self.file_block['csr']['csr_mode'] == '1D':
                self.CSRTrackelementObjects['forces'] = csrtrack_forces(type='projected')
        else:
            self.CSRTrackelementObjects['forces'] = csrtrack_forces()

    def writeElements(self):
        fulltext = 'io_path{logfile = log.txt}\nlattice{\n'
        counter = frameworkCounter(sub={'beam_position_monitor': 'screen'})
        for e in self.dipoles_screens_and_bpms:
            # if not e.type == 'dipole':
                # self.CSRTrackelementObjects[e.name] = csrtrack_online_monitor(filename=e.name+'.fmt2', monitor_type='phase', marker='screen'+str(counter.counter(e.type)), particle='all')
            fulltext += e.write_CSRTrack(counter.counter(e.objecttype))
            counter.add(e.objecttype)
        fulltext += self.endScreen().write_CSRTrack(counter.counter(self.endScreen().objecttype))
        fulltext += '}\n'
        self.set_particles_filename()
        self.setCSRMode()
        self.CSRTrackelementObjects['track_step'] = csrtrack_track_step()
        self.CSRTrackelementObjects['tracker'] = csrtrack_tracker(end_time_marker='screen'+str(counter.counter(self.endScreen().objecttype))+'a')
        self.CSRTrackelementObjects['monitor'] = csrtrack_monitor(name=self.end+'.fmt2')
        for c in self.CSRTrackelementObjects:
            fulltext += self.CSRTrackelementObjects[c].write_CSRTrack()
        return fulltext

    def write(self):
        self.code_file = master_subdir+'/csrtrk.in'
        saveFile(self.code_file, self.writeElements())

    def preProcess(self):
        prefix = self.file_block['input']['prefix'] if 'input' in self.file_block and 'prefix' in self.file_block['input'] else ''
        self.CSRTrackelementObjects['particles'].hdf5_to_astra(prefix)

    def postProcess(self):
        self.CSRTrackelementObjects['monitor'].csrtrack_to_hdf5()

class frameworkGroup(object):
    def __init__(self, name, elementObjects, type, elements, **kwargs):
        super(frameworkGroup, self).__init__()
        self.objectname = name
        self.type = type
        self.elements = elements
        self.allElementObjects = elementObjects

    def get_Parameter(self, p):
        try:
            isinstance(type(self).p, p)
            return getattr(self, p)
        except:
            return self.allElementObjects[self.elements[0]][p]

    def change_Parameter(self, p, v):
        # print 'p = ', getattr(self, p)
        try:
            getattr(self, p)
            setattr(self, p, v)
            if p == 'angle':
                self.set_angle(v)
            # print ('Changing group ', self.objectname, ' ', p, ' = ', v, '  result = ', self.get_Parameter(p))
        except:
            for e in self.elements:
                setattr(self.allElementObjects[e], p, v)
                # print ('Changing group elements ', self.objectname, ' ', p, ' = ', v, '  result = ', self.allElementObjects[self.elements[0]].objectname, self.get_Parameter(p))


    # def __getattr__(self, p):
    #     return self.get_Parameter(p)

    def __repr__(self):
        return [self.allElementObjects[e].objectname for e in self.elements]

    def __str__(self):
        return str([self.allElementObjects[e].objectname for e in self.elements])

    def __getitem__(self, key):
        return self.get_Parameter(key)

class element_group(frameworkGroup):
    def __init__(self, name, elementObjects, type, elements, **kwargs):
        super(element_group, self).__init__(name, elementObjects, type, elements, **kwargs)

class chicane(frameworkGroup):
    def __init__(self, name, elementObjects, type, elements, **kwargs):
        super(chicane, self).__init__(name, elementObjects, type, elements, **kwargs)

    def xform(self, theta, tilt, length, x, r):
        """Calculate the change on local coordinates through an element"""
        theta = theta if abs(theta) > 1e-9 else 1e-9
        tiltMatrix = np.matrix([
            [np.cos(tilt), -np.sin(tilt), 0],
            [np.sin(tilt), np.cos(tilt), 0],
            [0, 0, 1]
        ])
        angleMatrix = np.matrix([
            [length/theta*(np.cos(theta)-1)],
            [0],
            [length/theta*np.sin(theta)]
        ])
        dx = np.dot(r, angleMatrix)
        rt = np.transpose(r)
        n = rt[1]*np.cos(tilt)-rt[0]*np.sin(tilt)
        crossMatrix = np.matrix([
            np.cross(rt[0], n),
            np.cross(rt[1], n),
            np.cross(rt[2], n)
        ])*np.sin(theta)
        rp = np.outer(np.dot(rt,n), n)*(1-np.cos(theta))+rt*np.cos(theta)+crossMatrix
        return [np.array(x + dx), np.array(np.transpose(rp))]

    def update(self, **kwargs):
        if 'dipoleangle' in kwargs:
            self.set_angle(kwargs['dipoleangle'])
        if 'width' in kwargs:
            self.change_Parameter('width', kwargs['width'])
        if 'gap' in kwargs:
            self.change_Parameter('gap', kwargs['gap'])

    @property
    def angle(self):
        obj = [self.allElementObjects[e] for e in self.elements]
        return float(obj[0].angle)
    @angle.setter
    def angle(self, theta):
        'using setter! angle = ', theta
        self.set_angle(theta)

    def set_angle(self, a):
        # print (self.objectname, ' setting angle = ', a)
        obj = [self.allElementObjects[e] for e in self.elements]
        starting_angle = obj[0].theta
        for i in [0,1,2,3]:
            x1 = np.transpose([self.allElementObjects[self.elements[i]].position_start])
            angle = obj[i].angle
            obj[i].global_rotation[2] = starting_angle
            obj[i].angle = np.sign(angle)*a
            localXYZ = self.xform(starting_angle, 0, 0, x1, np.identity(3))[1]
            x1, localXYZ = self.xform(obj[i].angle, 0, obj[i].length, x1, localXYZ)
            xstart, ystart, zstart = x1
            obj[i].position_end[0] = chop(float(xstart))
            if i < 3:
                xend, yend, zend = obj[i+1].position_start
                angle = starting_angle + obj[i].angle
                length = float((-zstart + zend) * (1.0/np.cos(angle)))
                endx = chop(float(xstart + np.tan(-1*angle)*length))
                obj[i+1].position_start[0] =  endx
                starting_angle += obj[i].angle

    def __str__(self):
        return str([[self.allElementObjects[e].objectname, self.allElementObjects[e].angle, self.allElementObjects[e].position_start[0], self.allElementObjects[e].position_end[0]] for e in self.elements])

class s_chicane(chicane):
    def __init__(self, name, elementObjects, type, elements, **kwargs):
        super(s_chicane, self).__init__(name, elementObjects, type, elements, **kwargs)

    def update(self, **kwargs):
        if 'dipoleangle' in kwargs:
            self.set_angle(kwargs['dipoleangle'])
        if 'width' in kwargs:
            self.change_Parameter('width', kwargs['width'])
        if 'gap' in kwargs:
            self.change_Parameter('gap', kwargs['gap'])

    def set_angle(self, a):
        obj = [self.allElementObjects[e] for e in self.elements]
        starting_angle = obj[0].theta
        ratios = (-1,2,-2,1)
        for i in [0,1,2,3]:
            x1 = np.transpose([self.allElementObjects[self.elements[i]].position_start])
            angle = obj[i].angle
            obj[i].global_rotation[2] = starting_angle
            obj[i].angle = np.sign(angle)*a*ratios[i]
            localXYZ = self.xform(starting_angle, 0, 0, x1, np.identity(3))[1]
            x1, localXYZ = self.xform(obj[i].angle, 0, obj[i].length, x1, localXYZ)
            xstart, ystart, zstart = x1
            obj[i].position_end[0] = chop(float(xstart))
            if i < 3:
                xend, yend, zend = obj[i+1].position_start
                angle = starting_angle + obj[i].angle
                length = float((-zstart + zend) * (1.0/np.cos(angle)))
                endx = chop(float(xstart + np.tan(-1*angle)*length))
                obj[i+1].position_start[0] =  endx
                starting_angle += obj[i].angle

    def __str__(self):
        return str([[self.allElementObjects[e].objectname, self.allElementObjects[e].angle, self.allElementObjects[e].position_start[0], self.allElementObjects[e].position_end[0]] for e in self.elements])

class frameworkCounter(dict):
    def __init__(self, sub={}):
        super(frameworkCounter, self).__init__()
        self.sub = sub

    def counter(self, type):
        if type not in self:
            return 1
        return self[type] + 1

    def value(self, type):
        if type not in self:
            return 1
        return self[type]

    def add(self, type, n=1):
        type = self.sub[type] if type in self.sub else type
        if type not in self:
            self[type] = n
        else:
            self[type] += n
        return self[type]

    def subtract(self, type):
        type = self.sub[type] if type in self.sub else type
        if type not in self:
            self[type] = 0
        else:
            self[type] = self[type] - 1 if self[type] > 0 else 0
        return self[type]

class frameworkGenerator(object):
    def __init__(self, executables, **kwargs):
        super(frameworkGenerator, self).__init__()
        self.executables = executables
        self.objectdefaults = {}
        self.objectproperties = {}
        self.allowedKeyWords = astra_generator_keywords['keywords'] + astra_generator_keywords['framework_keywords']
        self.allowedKeyWords = [x.lower() for x in self.allowedKeyWords]
        for key, value in list(kwargs.items()):
            key = key.lower()
            if key in self.allowedKeyWords:
                try:
                    # print 'key = ', key
                    self.objectproperties[key] = value
                    setattr(self, key, value)
                except:
                    pass
                    # print 'WARNING: Unknown keyword: ', key, value
                    # exit()

    def run(self):
        command = self.executables['generator'] + [self.objectname+'.in']
        with open(os.devnull, "w") as f:
            subprocess.call(command, stdout=f, cwd=master_subdir)

    def load_defaults(self, defaults):
        if isinstance(defaults, str) and defaults in astra_generator_keywords['defaults']:
            self.__init__(**astra_generator_keywords['defaults'][defaults])
        elif isinstance(defaults, dict):
            self.__init__(**defaults)

    @property
    def particles(self):
        return self.number_of_particles if self.number_of_particles is not None else 512

    @particles.setter
    def particles(self, npart):
        self.add_property('number_of_particles', npart)

    def _write_ASTRA(self, d):
        output = ''
        for k, v in list(d.items()):
            val = v['value'] if v['value'] is not None else v['default'] if 'default' in v else None
            if isinstance(val,str):
                param_string = k+' = \''+str(val)+'\',\n'
            else:
                param_string = k+' = '+str(val)+',\n'
            if len((output + param_string).splitlines()[-1]) > 70:
                output += '\n'
            output += param_string
        return output[:-2]

    @property
    def charge(self):
        return float(self.objectproperties['charge']) if 'charge' in self.objectproperties and self.objectproperties['charge'] is not None else 250e-12
    @charge.setter
    def charge(self, q):
        self.objectproperties['charge'] = q

    @property
    def objectname(self):
        return self.objectproperties['name'] if 'name' in self.objectproperties and self.objectproperties['name'] is not None else 'laser'

    def write(self):
        output = '&INPUT\n'
        try:
            npart = eval(self.number_of_particles)
        except:
            npart = self.number_of_particles
        if self.filename is None:
            self.filename = 'laser.generator'
        framework_dict = OrderedDict([
            ['FName', {'value': self.filename, 'default': 'laser.generator'}],
            ['q_total', {'value': self.charge*1e9, 'default': 0.25}],
            ['Ipart', {'value': npart, 'default': 2**(3*3)}],
        ])
        keyword_dict = OrderedDict()
        for k in astra_generator_keywords['keywords']:
            k = k.lower()
            if getattr(self, k) is not None:
                try:
                    val = eval(getattr(self, k))
                except:
                    val = getattr(self, k)
                keyword_dict[k] = {'value': val}
        output += self._write_ASTRA(merge_two_dicts(framework_dict, keyword_dict))
        output += '\n/\n'
        saveFile(master_subdir+'/'+self.objectname+'.in', output)

    @property
    def parameters(self):
        return self.objectproperties

    def __getattr__(self, a):
        return None

    def add_property(self, key, value):
        if key.lower() in self.allowedKeyWords:
            self.objectproperties[key.lower()] = value
            self.__setattr__(key.lower(), value)

    def astra_to_hdf5(self):
        astrabeamfilename = self.filename
        beam.read_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)
        HDF5filename = self.filename.replace('.generator','.hdf5')
        beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, centered=False, sourcefilename=astrabeamfilename)

class frameworkElement(frameworkObject):

    keyword_conversion_rules_elegant = {'length': 'l','entrance_edge_angle': 'e1', 'exit_edge_angle': 'e2', 'edge_field_integral': 'fint', 'horizontal_size': 'x_max', 'vertical_size': 'y_max',
                                 'field_amplitude': 'volt', 'frequency': 'freq', 'output_filename': 'filename', 'csr_bins': 'bins', 'hangle': 'hkick', 'vangle': 'vkick',
                                 'csrdz': 'dz', 'field_definition_sdds': 'inputfile', 'change_momentum': 'change_p0', 'bunched_beam': 'bunched_beam_mode', 'nbins': 'n_bins'}

    def __init__(self, elementName=None, elementType=None, **kwargs):
        super(frameworkElement, self).__init__(elementName, elementType, **kwargs)
        self.add_default('length', 0)
        self.add_property('position_errors', [0,0,0])
        self.add_property('rotation_errors', [0,0,0])
        self.add_property('global_rotation', [0,0,0])


    def __mul__(self, other):
        return [self.objectproperties for x in range(other)]

    def __rmul__(self, other):
        return [self.objectproperties for x in range(other)]

    def __neg__(self):
        return self

    @property
    def x(self):
        return self.position_start[0]
    @x.setter
    def x(self, x):
        self.position_start[0] = x
        self.position_end[0] = x
    @property
    def y(self):
        return self.position_start[1]
    @y.setter
    def y(self, y):
        self.position_start[1] = y
        self.position_end[1] = y
    @property
    def z(self):
        return self.position_start[2]
    @z.setter
    def z(self, z):
        self.position_start[2] = z
        self.position_end[2] = z

    @property
    def dx(self):
        return self.position_errors[0]
    @dx.setter
    def dx(self, x):
        self.position_errors[0] = x
    @property
    def dy(self):
        return self.position_errors[1]
    @dy.setter
    def dy(self, y):
        self.position_errors[1] = y
    @property
    def dz(self):
        return self.position_errors[2]
    @dz.setter
    def dz(self, z):
        self.position_errors[2] = z

    @property
    def x_rot(self):
        return self.global_rotation[1]
    @property
    def y_rot(self):
        return self.global_rotation[2]
    @property
    def z_rot(self):
        return self.global_rotation[0]

    @property
    def dx_rot(self):
        return self.rotation_errors[1]
    @dx_rot.setter
    def dx_rot(self, x):
        self.rotation_errors[1] = x
    @property
    def dy_rot(self):
        return self.rotation_errors[2]
    @dy_rot.setter
    def dy_rot(self, y):
        self.rotation_errors[2] = y
    @property
    def dz_rot(self):
        return self.rotation_errors[0]
    @dz_rot.setter
    def dz_rot(self, z):
        self.rotation_errors[0] = z
    @property
    def tilt(self):
        return self.dz_rot

    @property
    def theta(self):
        if hasattr(self, 'global_rotation') and self.global_rotation is not None:
            rotation =  self.global_rotation[2] if len(self.global_rotation) is 3 else self.global_rotation
        else:
            rotation = 0
        if hasattr(self, 'starting_rotation') and self.starting_rotation is not None:
            rotation +=  self.starting_rotation
        return rotation

    def _rotation_matrix(self, theta):
        return np.array([[np.cos(theta), 0, np.sin(theta)], [0, 1, 0], [-1*np.sin(theta), 0, np.cos(theta)]])

    @property
    def rotation_matrix(self):
        return self._rotation_matrix(self.theta)

    def rotated_position(self, pos=[0,0,0], offset=None, theta=None):
        if offset is None:
            if not hasattr(self, 'starting_offset') or self.starting_offset is None:
                offset = [0,0,0]
            else:
                offset = self.starting_offset
        if theta is None:
            return chop(np.dot(np.array(pos) - np.array(offset), self.rotation_matrix), 1e-6)
        else:
            return chop(np.dot(np.array(pos) - np.array(offset), self._rotation_matrix(theta)), 1e-6)

    @property
    def start(self):
        start = self.position_start
        length_vector = self.rotated_position([0,0,0], offset=[0,0,0], theta=self.theta)
        starting_middle = np.array(start) + length_vector
        return self.rotated_position(starting_middle, offset=self.starting_offset, theta=self.starting_rotation)

    @property
    def middle(self):
        start = self.position_start
        length_vector = self.rotated_position([0,0, self.length / 2.0], offset=[0,0,0], theta=self.theta)
        starting_middle = np.array(start) + length_vector
        return self.rotated_position(starting_middle, offset=self.starting_offset, theta=self.starting_rotation)

    @property
    def end(self):
        start = self.position_start
        length_vector = self.rotated_position([0,0, self.length], offset=[0,0,0], theta=self.theta)
        starting_middle = np.array(start) + length_vector
        return self.rotated_position(starting_middle, offset=self.starting_offset, theta=self.starting_rotation)

    def _write_ASTRA(self, d, n=1):
        output = ''
        for k, v in list(d.items()):
            if checkValue(self, v) is not None:
                if 'type' in v and v['type'] == 'list':
                    for i, l in enumerate(checkValue(self, v)):
                        if n is not None:
                            param_string = k+'('+str(i+1)+','+str(n)+') = '+str(l)+', '
                        else:
                            param_string = k+' = '+str(l)+'\n'
                        if len((output + param_string).splitlines()[-1]) > 70:
                            output += '\n'
                        output += param_string
                elif 'type' in v and v['type'] == 'array':
                    if n is not None:
                        param_string = k+'('+str(n)+') = ('
                    else:
                        param_string = k+' = ('
                    for i, l in enumerate(checkValue(self, v)):
                        param_string += str(l)+', '
                        if len((output + param_string).splitlines()[-1]) > 70:
                            output += '\n'
                    output += param_string[:-2] + '),\n'
                else:
                    if n is not None:
                        param_string = k+'('+str(n)+') = '+str(checkValue(self, v))+', '
                    else:
                        param_string = k+' = '+str(checkValue(self, v))+',\n'
                    if len((output + param_string).splitlines()[-1]) > 70:
                        output += '\n'
                    output += param_string
        return output[:-2]

    def write_ASTRA(self, n):
        return ""

    def _write_Elegant(self):
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        k1 = self.k1 if self.k1 is not None else 0
        for key, value in list(merge_two_dicts({'k1': k1}, merge_two_dicts(self.objectproperties, self.objectdefaults)).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

    def write_Elegant(self):
        if not self.subelement:
            return self._write_Elegant()

    def _convertType_Elegant(self, etype):
        return type_conversion_rules_Elegant[etype] if etype in type_conversion_rules_Elegant else etype

    def _convertKeword_Elegant(self, keyword):
        return self.keyword_conversion_rules_elegant[keyword] if keyword in self.keyword_conversion_rules_elegant else keyword

    def write_CSRTrack(self, n=0):
        return ""

    def write_GPT(self, Brho):
        return ""

    def gpt_coordinates(self):
        x,y,z = self.middle
        psi, phi, theta = self.global_rotation
        output =''
        for c in [x, y, z]:
            output += str(c)+', '
        output += 'cos('+str(theta)+'), 0, -sin('+str(theta)+'), 0, 1 ,0'
        return output

class dipole(frameworkElement):

    def __init__(self, name=None, type='dipole', **kwargs):
        super(dipole, self).__init__(name, type, **kwargs)
        self.add_default('bins',100)
        self.add_default('csr', 1)
        self.add_default('isr', 1)
        self.add_default('n_kicks', 10)
        self.add_default('synch_rad', 1)
        self.add_default('integration_order', 4)
        self.add_default('nonlinear', 1)
        self.add_default('sg_halfwidth', 2)


    @property
    def width(self):
        if 'width' in self.objectproperties:
            return self.objectproperties['width']
        else:
            return 0.2
    @width.setter
    def width(self, w):
        self.objectproperties['width'] = w

    def __neg__(self):
        newself = copy.deepcopy(self)
        if 'exit_edge_angle' in newself.objectproperties and 'entrance_edge_angle' in newself.objectproperties:
            e1 = newself['entrance_edge_angle']
            e2 = newself['exit_edge_angle']
            newself.objectproperties['entrance_edge_angle'] = e2
            newself.objectproperties['exit_edge_angle'] = e1
        elif 'entrance_edge_angle' in newself.objectproperties:
            newself.objectproperties['exit_edge_angle'] = newself.objectproperties['entrance_edge_angle']
            del newself.objectproperties['entrance_edge_angle']
        elif 'exit_edge_angle' in newself.objectproperties:
            newself.objectproperties['entrance_edge_angle'] = newself.objectproperties['exit_edge_angle']
            del newself.objectproperties['exit_edge_angle']
        newself.objectname = '-'+newself.objectname
        return newself

    def _edge_angles(self, estr):
        if estr in self.objectproperties:
            if isinstance(self.objectproperties[estr], str):
                return checkValue(self, self.objectproperties[estr],0)
            else:
                return self.objectproperties[estr]
        else:
            return 0

    @property
    def rho(self):
        return self.length/self.angle if self.length is not None and abs(self.angle) > 1e-9 else 0

    @property
    def e1(self):
        return self._edge_angles('entrance_edge_angle')
    @property
    def e2(self):
        return self._edge_angles('exit_edge_angle')

    @property
    def corners(self):
        corners = [0,0,0,0]
        if hasattr(self, 'global_rotation') and self.global_rotation is not None:
            rotation =  self.global_rotation[2] if len(self.global_rotation) is 3 else self.global_rotation
        else:
            rotation = 0
        theta = self.e1+rotation
        corners[0] = np.array(list(map(add, np.transpose(self.position_start), np.dot([-self.width*self.length,0,0], self._rotation_matrix(theta)))))
        corners[3] = np.array(list(map(add, np.transpose(self.position_start), np.dot([self.width*self.length,0,0], self._rotation_matrix(theta)))))
        theta = self.angle-self.e2+rotation
        corners[1] = np.array(list(map(add, np.transpose(self.position_end), np.dot([-self.width*self.length,0,0], self._rotation_matrix(theta)))))
        corners[2] = np.array(list(map(add, np.transpose(self.position_end), np.dot([self.width*self.length,0,0], self._rotation_matrix(theta)))))
        corners = [self.rotated_position(x, offset=self.starting_offset, theta=self.starting_rotation) for x in corners]
        return corners

    def write_CSRTrack(self, n):
        z1 = self.position_start[2]
        z2 = self.position_end[2]
        return """dipole{\nposition{rho="""+str(z1)+""", psi="""+str(chop(self.theta+self.e1))+""", marker=d"""+str(n)+"""a}\nproperties{r="""+str(self.rho)+"""}\nposition{rho="""+str(z2)+""", psi="""+str(chop(self.theta+self.angle-self.e2))+""", marker=d"""+str(n)+"""b}\n}\n"""

    def write_ASTRA(self, n):
        if abs(checkValue(self, 'strength', default=0)) > 0 or abs(self.rho) > 0:
            corners = self.corners
            if self.plane is None:
                self.plane = 'horizontal'
            params = OrderedDict([
                ['D_Type', {'value': '\''+self.plane+'\'', 'default': '\'horizontal\''}],
                ['D_Gap', {'type': 'list', 'value': [self.gap, self.gap], 'default': [0.02, 0.02]}],
                ['D1', {'type': 'array', 'value': [corners[3][0],corners[3][2]] }],
                ['D3', {'type': 'array', 'value': [corners[2][0],corners[2][2]] }],
                ['D4', {'type': 'array', 'value': [corners[1][0],corners[1][2]] }],
                ['D2', {'type': 'array', 'value': [corners[0][0],corners[0][2]] }],
                # ['D_xoff', {'value': self.start[0] + self.dx, 'default': 0}],
                # ['D_yoff', {'value': self.start[1] + self.dy, 'default': 0}],
                # ['D_zoff', {'value': self.dz, 'default': 0}],
                # ['D_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
                # ['D_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
                # ['D_zrot', {'value': self.z_rot + self.dz_rot, 'default': 0}],
                ])
            if abs(checkValue(self, 'strength', default=0)) > 0 or not abs(self.rho) > 0:
                params['D_strength'] = {'value': checkValue(self, 'strength', 0), 'default': 1e6}
            else:
                params['D_radius'] =  {'value': self.rho, 'default': 1e6}
            return self._write_ASTRA(params, n)
        else:
            return None

class kicker(dipole):

    def __init__(self, name=None, type='kicker', **kwargs):
        super(kicker, self).__init__(name, type, **kwargs)

    @property
    def angle(self):
        if self.plane == 'horizontal' and hasattr(self, 'hangle') and self.hangle is not None:
            return self.hangle
        elif hasattr(self, 'vangle') and self.vangle is not None:
            return self.vangle
        else:
            return 0

    def write_ASTRA(self, n):
        output = ''
        self.plane = 'horizontal'
        hkick = super(kicker, self).write_ASTRA(n)
        if hkick is not None:
            output += hkick
        else:
            n = n-1
        self.plane = 'vertical'
        vkick = super(kicker, self).write_ASTRA(n+1)
        if vkick is not None:
            output += vkick
        return output

class quadrupole(frameworkElement):

    def __init__(self, name=None, type='quadrupole', **kwargs):
        super(quadrupole, self).__init__(name, type, **kwargs)
        self.add_default('k1l', 0)
        self.add_default('n_kicks', 20)
        self.strength_errors = [0]

    @property
    def k1(self):
        return self.k1l / self.length
    @k1.setter
    def k1(self, k1):
        self.k1l = self.length * k1

    @property
    def dk1(self):
        return self.strength_errors[0]
    @dk1.setter
    def dk1(self, dk1):
        self.strength_errors[0] = dk1

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['Q_pos', {'value': self.middle[2] + self.dz, 'default': 0}],
            ['Q_xoff', {'value': self.middle[0] + self.dx, 'default': 0}],
            ['Q_yoff', {'value': self.middle[1] + self.dy, 'default': 0}],
            ['Q_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
            ['Q_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
            ['Q_zrot', {'value': self.z_rot + self.dz_rot, 'default': 0}],
            ['Q_k', {'value': self.k1 + self.dk1, 'default': 0}],
            ['Q_length', {'value': self.length, 'default': 0}],
            ['Q_smooth', {'value': self.smooth, 'default': 10}],
            ['Q_bore', {'value': self.bore, 'default': 0.016}],
            ['Q_noscale', {'value': self.scale_field}],
            ['Q_mult_a', {'type': 'list', 'value': self.multipoles}],
        ]), n)

    def write_GPT(self, Brho):
        output = str(self.objecttype) + '( "wcs", '+self.gpt_coordinates()+', '+str(self.length)+', '+str(Brho*self.k1)+');\n'
        return output

class cavity(frameworkElement):

    def __init__(self, name=None, type='cavity', **kwargs):
        super(cavity, self).__init__(name, type, **kwargs)
        self.keyword_conversion_rules_elegant['field_amplitude'] = 'volt'
        # self.keyword_conversion_rules_elegant['frequency'] = 'frequency'
        self.keyword_conversion_rules_elegant['longitudinal_wakefield_sdds'] = 'zwakefile'
        self.keyword_conversion_rules_elegant['transverse_wakefield_sdds'] = 'trwakefile'
        self.add_default('tcolumn', '"t"')
        self.add_default('wzcolumn', '"W"')
        self.add_default('wxcolumn', '"W"')
        self.add_default('wycolumn', '"W"')
        self.add_default('wcolumn', '"Ez"')
        self.add_default('change_p0', 1)
        # self.add_default('method', '"non-adaptive runge-kutta"')
        self.add_default('focussing', 1)

    def update_field_definition(self):
        if hasattr(self, 'field_definition') and self.field_definition is not None:
            self.field_definition = '"' + expand_substitution(self, '\''+self.field_definition+'\'').strip('\'"')+'"'
        if hasattr(self, 'field_definition_sdds') and self.field_definition_sdds is not None:
            self.field_definition_sdds = '"' + expand_substitution(self, '\''+self.field_definition_sdds+'\'').strip('\'"')+'"'
        if hasattr(self, 'longitudinal_wakefield_sdds') and self.longitudinal_wakefield_sdds is not None:
            self.longitudinal_wakefield_sdds = '"' + expand_substitution(self, '\''+self.longitudinal_wakefield_sdds+'\'').strip('\'"')+'"'
        if hasattr(self, 'transverse_wakefield_sdds') and self.transverse_wakefield_sdds is not None:
            self.transverse_wakefield_sdds = '"' + expand_substitution(self, '\''+self.transverse_wakefield_sdds+'\'').strip('\'"')+'"'

    @property
    def cells(self):
        if (self.n_cells is 0 or self.n_cells is None) and self.cell_length > 0:
                cells = round((self.length-self.cell_length)/self.cell_length)
                cells = int(cells - (cells % 3))
        elif self.n_cells > 0 and (self.cell_length is not None and self.cell_length) > 0:
            if self.cell_length == self.length:
                cells = 1
            else:
                cells = int(self.n_cells - (self.n_cells % 3))
        else:
            cells = None
        return cells

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['C_pos', {'value': self.start[2] + self.dz, 'default': 0}],
            ['FILE_EFieLD', {'value': '\''+expand_substitution(self, '\''+self.field_definition+'\'').strip('\'"')+'\'', 'default': 0}],
            ['C_numb', {'value': self.cells}],
            ['Nue', {'value': self.frequency / 1e9, 'default': 2998.5}],
            ['MaxE', {'value': self.field_amplitude / 1e6, 'default': 0}],
            ['Phi', {'value': self.phase, 'default': 0.0}],
            ['C_smooth', {'value': self.smooth, 'default': 10}],
            ['C_xoff', {'value': self.start[0] + self.dx, 'default': 0}],
            ['C_yoff', {'value': self.start[1] + self.dy, 'default': 0}],
            ['C_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
            ['C_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
            ['C_zrot', {'value': self.z_rot + self.dz_rot, 'default': 0}],
        ]), n)

    def _write_Elegant(self):
        self.update_field_definition()
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):

            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                if self.objecttype == 'cavity':
                    # In ELEGANT all phases are +90degrees!!
                    value = value + 90 if key.lower() == 'phase' else value
                    # If using rftmez0 or similar
                    # value = ((90+value)/360.0)*(2*3.14159) if key.lower() == 'phase' else value
                    # In ELEGANT the voltages  need to be compensated
                    value = (self.cells+4.8) * self.cell_length * (1 / np.sqrt(2)) * value if key.lower() == 'volt' else value
                    # If using rftmez0 or similar
                    value = 1/(2**0.5) * value if key.lower() == 'ez' else value
                    # In CAVITY NKICK = n_cells
                    value = self.cells if key.lower() == 'n_kicks' else value
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class rf_deflecting_cavity(cavity):

    def __init__(self, name=None, type='rf_deflecting_cavity', **kwargs):
        super(rf_deflecting_cavity, self).__init__(name, type, **kwargs)

class solenoid(frameworkElement):

    def __init__(self, name=None, type='solenoid', **kwargs):
        super(solenoid, self).__init__(name, type, **kwargs)
        self.keyword_conversion_rules_elegant['field_amplitude'] = 'B'

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['S_pos', {'value': self.start[2] + self.dz, 'default': 0}],
            ['FILE_BFieLD', {'value': '\''+expand_substitution(self, '\''+self.field_definition+'\'')+'\''}],
            ['MaxB', {'value': self.field_amplitude, 'default': 0}],
            ['S_smooth', {'value': self.smooth, 'default': 10}],
            ['S_xoff', {'value': self.start[0] + self.dx, 'default': 0}],
            ['S_yoff', {'value': self.start[1] + self.dy, 'default': 0}],
            ['S_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
            ['S_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
        ]), n)

class aperture(frameworkElement):

    def __init__(self, name=None, type='aperture', **kwargs):
        super(aperture, self).__init__(name, type, **kwargs)

    def write_GPT(self, Brho):
        if self.shape == 'elliptical':
            output = 'rmax'
        else:
            output = 'xymax'
        output += '( "wcs", '+self.gpt_coordinates()+', '+str(self.horizontal_size)+', '+str(self.length)+');\n'
        return output

class wall_current_monitor(frameworkElement):

    def __init__(self, name=None, type='wall_current_monitor', **kwargs):
        super(wall_current_monitor, self).__init__(name, type, **kwargs)

class screen(frameworkElement):

    def __init__(self, name=None, type='screen', **kwargs):
        super(screen, self).__init__(name, type, **kwargs)
        if 'output_filename' not in kwargs:
            self.output_filename = str(self.objectname)+'.sdds'

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['Screen', {'value': self.middle[2], 'default': 0}],
            ['Scr_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
            ['Scr_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
        ]), n)

    def write_CSRTrack(self, n):
        z = self.start[2]
        return """quadrupole{\nposition{rho="""+str(z)+""", psi=0.0, marker=screen"""+str(n)+"""a}\nproperties{strength=0.0, alpha=0, horizontal_offset=0,vertical_offset=0}\nposition{rho="""+str(z+1e-6)+""", psi=0.0, marker=screen"""+str(n)+"""b}\n}\n"""

    def write_GPT(self, Brho):
        output = 'screen( "wcs", '+self.gpt_coordinates()+');\n'
        return output

    def astra_to_hdf5(self, lattice):
        astrabeamfilename = None
        for i in [0, -0.001, 0.001]:
            tempfilename = lattice + '.' + str(int(round((self.middle[2]+i-self.zstart[2])*100))).zfill(4) + '.' + str(master_run_no).zfill(3)
            if os.path.isfile(master_subdir + '/' + tempfilename):
                astrabeamfilename = tempfilename
        if astrabeamfilename is None:
            print(( 'Screen Error: ', lattice, self.middle[2], self.zstart[2]))
        else:
            beam.read_astra_beam_file((master_subdir + '/' + astrabeamfilename).strip('\"'), normaliseZ=False)
            beam.rotate_beamXZ(-1*self.starting_rotation, preOffset=[0,0,0], postOffset=-1*np.array(self.starting_offset))
            HDF5filename = (self.objectname+'.hdf5').strip('\"')
            beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, centered=False, sourcefilename=astrabeamfilename, pos=self.middle)

    def sdds_to_hdf5(self):
        elegantbeamfilename = self.output_filename.replace('.sdds','.SDDS').strip('\"')
        beam.read_SDDS_beam_file(master_subdir + '/' + elegantbeamfilename)
        HDF5filename = self.output_filename.replace('.sdds','.hdf5').replace('.SDDS','.hdf5').strip('\"')
        beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, centered=False, sourcefilename=elegantbeamfilename, pos=self.middle, zoffset=self.end[2])

class monitor(screen):

    def __init__(self, name=None, type='monitor', **kwargs):
        super(monitor, self).__init__(name, type, **kwargs)

class watch_point(screen):

    def __init__(self, name=None, type='watch_point', **kwargs):
        super(watch_point, self).__init__(name, 'screen', **kwargs)

class beam_position_monitor(screen):

    def __init__(self, name=None, type='beam_position_monitor', **kwargs):
        super(beam_position_monitor, self).__init__(name, type, **kwargs)

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['Screen', {'value': self.middle[2], 'default': 0}],
            ['Scr_xrot', {'value': self.y_rot + self.dy_rot, 'default': 0}],
            ['Scr_yrot', {'value': self.x_rot + self.dx_rot, 'default': 0}],
        ]), n)

class collimator(frameworkElement):

    def __init__(self, name=None, type='collimator', **kwargs):
        super(collimator, self).__init__(name, type, **kwargs)

class marker(screen):

    def __init__(self, name=None, type='marker', **kwargs):
        super(marker, self).__init__(name, 'screen', **kwargs)

    def write_CSRTrack(self, n):
        return ''

class drift(frameworkElement):

    def __init__(self, name=None, type='drift', **kwargs):
        super(drift, self).__init__(name, type, **kwargs)

    def _write_Elegant(self):
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class csrdrift(frameworkElement):

    def __init__(self, name=None, type='csrdrift', **kwargs):
        super(csrdrift, self).__init__(name, type, **kwargs)
        self.keyword_conversion_rules_elegant['csrdz'] = 'dz'

    def _write_Elegant(self):
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class modulator(frameworkElement):

    def __init__(self, name=None, type='modulator', **kwargs):
        super(modulator, self).__init__(name, type, **kwargs)
        self.add_default('k1l', 0)
        self.add_default('n_steps', 1*self.periods)
        self.keyword_conversion_rules_elegant.update({'peak_field': 'bu', 'gradient': 'TGU_GRADIENT', 'wavelength': 'LASER_WAVELENGTH', 'peak_power': 'LASER_PEAK_POWER',
        'phase': 'LASER_PHASE', 'horizontal_mode_number': 'LASER_M', 'vertical_mode_number': 'LASER_N'})

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['Q_pos', {'value': self.middle[2] + self.dz, 'default': 0}],
        ]), n)

    def _write_Elegant(self):
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class wiggler(frameworkElement):

    def __init__(self, name=None, type='wiggler', **kwargs):
        super(wiggler, self).__init__(name, type, **kwargs)
        # self.add_default('k1l', 0)
        # self.add_default('n_steps', 1*self.periods)
        self.keyword_conversion_rules_elegant.update({'peak_field': 'B'})

    def write_ASTRA(self, n):
        return self._write_ASTRA(OrderedDict([
            ['Q_pos', {'value': self.middle[2] + self.dz, 'default': 0}],
        ]), n)

    def _write_Elegant(self):
        wholestring=''
        if ('k' in self and abs(self.k) > 0) or ('peak_field' in self and abs(self.peak_field) > 0) or ('radius' in self and abs(self.radius) > 0):
            etype = self._convertType_Elegant(self.objecttype)
        else:
            etype = 'drift'
        string = self.objectname+': '+ etype
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class charge(frameworkElement):
    def __init__(self, name=None, type='charge', **kwargs):
        super(charge, self).__init__(name, 'charge', **kwargs)

class global_error(frameworkElement):

    def __init__(self, name=None, type='global_error', **kwargs):
        super(global_error, self).__init__(name, 'global_error', **kwargs)
        # self._errordict = {}

    def add_Error(self, type, sigma):
        if type in global_Error_Types:
            self.add_property(type, sigma)

    def write_ASTRA(self):
        return self._write_ASTRA(OrderedDict([[key, {'value': value}] for key, value in self._errordict]))

    def write_GPT(self, Brho):
        output = str(self.objecttype) + '( "wcs", '+self.gpt_coordinates()+', '+str(self.length)+', '+str(Brho*self.k1)+');\n'
        return output

class longitudinal_wakefield(cavity):

    def __init__(self, name=None, type='longitudinal_wakefield', **kwargs):
        super(longitudinal_wakefield, self).__init__(name, type, **kwargs)
        self.add_default('coupling_cell_length', 0)

    def write_ASTRA(self, startn):
        self.update_field_definition()
        output = ''
        if self.scale_kick > 0:
            for n in range(startn, startn+self.cells):
                output += self._write_ASTRA(OrderedDict([
                    ['Wk_Type', {'value': self.waketype, 'default': '\'Taylor_Method_F\''}],
                    ['Wk_filename', {'value': '\''+expand_substitution(self, '\''+self.field_definition+'\'').strip('\'"')+'\'', 'default': 0}],
                    ['Wk_x', {'value': self.x_offset, 'default': 0}],
                    ['Wk_y', {'value': self.y_offset, 'default': 0}],
                    ['Wk_z', {'value': self.start[2] + self.coupling_cell_length + (n-1)*self.cell_length}],
                    ['Wk_ex', {'value': self.scale_field_ex, 'default': 0}],
                    ['Wk_ey', {'value': self.scale_field_ey, 'default': 0}],
                    ['Wk_ez', {'value': self.scale_field_ez, 'default': 1}],
                    ['Wk_hx', {'value': self.scale_field_hx, 'default': 1}],
                    ['Wk_hy', {'value': self.scale_field_hy, 'default': 0}],
                    ['Wk_hz', {'value': self.scale_field_hz, 'default': 0}],
                    ['Wk_equi_grid', {'value': self.equal_grid, 'default': 0}],
                    ['Wk_N_bin', {'value': self.nbins, 'default': 11}],
                    ['Wk_ip_method', {'value': self.interpolation_method, 'default': 2}],
                    ['Wk_smooth', {'value': self.smooth, 'default': 0.5}],
                    ['Wk_sub', {'value': self.subbins, 'default': 4}],
                    ['Wk_scaling', {'value': self.scale_kick, 'default': 1}],
                ]), n)
                output += '\n'
        return output

    def _write_Elegant(self):
        self.update_field_definition()
        wholestring=''
        etype = self._convertType_Elegant(self.objecttype)
        string = self.objectname+': '+ etype
        if self.length > 0:
            d = drift(self.objectname+'-drift', type='drift', **{'length': self.length})
            wholestring+=d._write_Elegant()
        for key, value in list(merge_two_dicts(self.objectproperties, self.objectdefaults).items()):
            if not key is 'name' and not key is 'type' and not key is 'commandtype' and self._convertKeword_Elegant(key) in elements_Elegant[etype]:
                value = getattr(self, key) if hasattr(self, key) and getattr(self, key) is not None else value
                key = self._convertKeword_Elegant(key)
                tmpstring = ', '+key+' = '+str(value)
                if len(string+tmpstring) > 76:
                    wholestring+=string+',&\n'
                    string=''
                    string+=tmpstring[2::]
                else:
                    string+= tmpstring
        wholestring+=string+';\n'
        return wholestring

class astra_header(frameworkElement):

    def __init__(self, name=None, type=None, **kwargs):
        super(astra_header, self).__init__(name, type, **kwargs)

    def framework_dict(self):
        return OrderedDict()

    def write_ASTRA(self):
        keyword_dict = OrderedDict()
        for k in elementkeywords[self.objecttype]['keywords']:
            if getattr(self, k.lower()) is not None:
                keyword_dict[k.lower()] = {'value': getattr(self,k.lower())}
        output = '&' + section_header_text_ASTRA[self.objecttype]['header']+'\n'
        output += self._write_ASTRA(merge_two_dicts(self.framework_dict(), keyword_dict), None) + '\n/\n'
        return output

class astra_newrun(astra_header):
    def __init__(self, offset, rotation, **kwargs):
        super(astra_header, self).__init__('newrun', 'astra_newrun', **kwargs)
        self.starting_offset = offset
        self.starting_rotation = rotation
        if 'run' not in kwargs:
            self.run = 1
        if 'head' not in kwargs:
            self.head = 'trial'
        if 'lprompt' not in kwargs:
            self.add_property('lprompt', False)

    def framework_dict(self):
        return OrderedDict([
            ['Distribution', {'value': '\''+self.particle_definition+'\''}],
            ['high_res', {'value': self.high_res, 'default': True}],
            ['auto_phase', {'value': self.auto_phase, 'default': True}]
        ])

    def hdf5_to_astra(self, prefix=''):
        HDF5filename = prefix+self.particle_definition.replace('.astra','')+'.hdf5'
        beam.read_HDF5_beam_file(master_subdir + '/' + HDF5filename)
        beam.rotate_beamXZ(self.theta, preOffset=self.starting_offset)
        astrabeamfilename = self.particle_definition
        beam.write_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)

class astra_output(astra_header):
    def __init__(self, screens, offset, rotation, **kwargs):
        super(astra_header, self).__init__('output', 'astra_output', **kwargs)
        self.screens = screens
        self.starting_offset = offset
        self.starting_rotation = rotation

    def framework_dict(self):
        self.start_element.starting_offset = self.starting_offset
        self.end_element.starting_offset = self.starting_offset
        self.start_element.starting_rotation = self.starting_rotation
        self.end_element.starting_rotation = self.starting_rotation
        keyworddict = OrderedDict([
            ['zstart', {'value': self.start_element.start[2]}],
            ['zstop', {'value': self.end_element.end[2]}],
        ])
        for i, element in enumerate(self.screens,1):
            element.starting_offset = self.starting_offset
            element.starting_rotation = self.starting_rotation
            keyworddict['Screen('+str(i)+')'] = {'value': element.middle[2]}
            # if abs(element.theta) > 0:
                # keyworddict['Scr_xrot('+str(i)+')'] = {'value': element.theta}
        return keyworddict

class astra_charge(astra_header):
    def __init__(self, **kwargs):
        super(astra_header, self).__init__('charge', 'astra_charge', **kwargs)
        self.npart = 2**(3*5)
        self.grids = getGrids(npart=self.npart)

    @property
    def space_charge(self):
        return False if self.space_charge_mode == 'False' or self.space_charge_mode == False else True

    @property
    def space_charge_2D(self):
        return True if self.space_charge and self.space_charge_mode != '3D' else False

    @property
    def space_charge_3D(self):
        return True if self.space_charge and not self.space_charge_2D else False

    @property
    def grid_size(self):
        # print 'asking for grid sizes n = ', self.npart, ' is ', self.grids.getGridSizes(self.npart)
        return self.grids.getGridSizes(self.npart)

    def framework_dict(self):
        sc_dict = OrderedDict([
            ['Lmirror', {'value': self.cathode, 'default': False}],
            ['LSPCH', {'value': self.space_charge, 'default': True}],
            ['LSPCH3D', {'value': self.space_charge_3D, 'default': True}]
        ])
        if self.space_charge_2D:
            sc_n_dict = OrderedDict([
                ['nrad', {'value': self.grid_size, 'default': 32}],
                ['nlong_in', {'value': self.grid_size, 'default': 32}],
            ])
        elif self.space_charge_3D:
            sc_n_dict = OrderedDict([
                ['nxf', {'value': self.grid_size, 'default': 6}],
                ['nyf', {'value': self.grid_size, 'default': 6}],
                ['nzf', {'value': self.grid_size, 'default': 6}],
            ])
        else:
            sc_n_dict = OrderedDict([])
        return merge_two_dicts(sc_dict, sc_n_dict)

class getGrids(object):

    def __init__(self, npart=1000):
        self.powersof8 = np.asarray([ 2**(j) for j in range(1,20) ])
        self.n = npart
        self.gridSizes = self.getGridSizes(int(self.n))

    def getGridSizes(self):
        return self.gridSizes

    def getGridSizes(self, x):
        self.x = abs(x)
        self.cuberoot = int(round(self.x ** (1. / 3)))
        return max([4,self.find_nearest(self.powersof8, self.cuberoot)])

    def find_nearest(self, array, value):
        self.array = array
        self.value = value
        self.idx = (np.abs(self.array - self.value)).argmin()
        return self.array[self.idx]

class astra_errors(astra_header):
    def __init__(self, element=None, **kwargs):
        super(astra_errors, self).__init__('astra_error', 'global_error', **kwargs)
        self._element = element
        self.add_property('global_errors', True)
        self.add_property('Log_Error', True)
        self.add_property('generate_output', True)
        self.add_property('Suppress_output', False)

    def write_ASTRA(self):
        keyword_dict = {}
        conversion = dict([a, b] for a, b in zip(elementkeywords[self.objecttype]['keywords'], elementkeywords[self.objecttype]['astra_keywords']))
        for k in elementkeywords[self.objecttype]['keywords']:
            # print k, conversion[k]
            if getattr(self, k.lower()) is not None:
                keyword_dict[conversion[k].lower()] = {'value': getattr(self,k.lower())}
        joineddict = merge_two_dicts(self.framework_dict(), keyword_dict)
        if len(joineddict) > 0:
            output = '&' + section_header_text_ASTRA[self.objecttype]['header']+'\n'
            output += self._write_ASTRA(merge_two_dicts(self.framework_dict(), keyword_dict), None) + '\n/\n'
        else:
            output = ''
        return output

class csrtrack_element(frameworkElement):

    def __init__(self, elementName=None, elementType=None, **kwargs):
        super(csrtrack_element, self).__init__(elementName, elementType, **kwargs)
        self.header = ''
        if elementName in csrtrack_defaults:
            for k, v in list(csrtrack_defaults[elementName].items()):
                self.add_default(k, v)

    def CSRTrack_str(self, s):
        if s is True:
            return 'yes'
        elif s is False:
            return 'no'
        else:
            return str(s)

    def write_CSRTrack(self):
        output = str(self.header) + '{\n'
        for k in elementkeywords[self.objecttype]['keywords']:
            k = k.lower()
            if getattr(self,k) is not None:
                output += k+'='+self.CSRTrack_str(getattr(self, k))+'\n'
            elif k in self.objectdefaults:
                output += k+'='+self.CSRTrack_str(self.objectdefaults[k])+'\n'
        output+='}\n'
        return output

class csrtrack_online_monitor(csrtrack_element):

    def __init__(self, marker='', **kwargs):
        super(csrtrack_online_monitor, self).__init__('online_monitor', 'csrtrack_online_monitor', **kwargs)
        self.header = 'online_monitor'
        self.end_time_marker = marker+'b'

class csrtrack_forces(csrtrack_element):

    def __init__(self, **kwargs):
        super(csrtrack_forces, self).__init__('forces', 'csrtrack_forces', **kwargs)
        self.header = 'forces'

class csrtrack_track_step(csrtrack_element):

    def __init__(self, **kwargs):
        super(csrtrack_track_step, self).__init__('track_step', 'csrtrack_track_step', **kwargs)
        self.header = 'track_step'

class csrtrack_tracker(csrtrack_element):

    def __init__(self, end_time_marker=''):
        super(csrtrack_tracker, self).__init__('tracker', 'csrtrack_tracker')
        self.header = 'tracker'
        self.end_time_marker = end_time_marker

class csrtrack_monitor(csrtrack_element):

    def __init__(self, **kwargs):
        super(csrtrack_monitor, self).__init__(elementName='monitor', elementType='csrtrack_monitor', **kwargs)
        self.header = 'monitor'

    def csrtrack_to_hdf5(self):
        csrtrackbeamfilename = self.name
        astrabeamfilename = csrtrackbeamfilename.replace('.fmt2','.astra')
        beam.convert_csrtrackfile_to_astrafile(master_subdir + '/' + csrtrackbeamfilename, master_subdir + '/' + astrabeamfilename)
        beam.read_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)
        HDF5filename = self.name.replace('.fmt2','.hdf5')
        beam.write_HDF5_beam_file(master_subdir + '/' + HDF5filename, sourcefilename=csrtrackbeamfilename)

class csrtrack_particles(csrtrack_element):

    def __init__(self, **kwargs):
        super(csrtrack_particles, self).__init__('particles', 'csrtrack_particles', **kwargs)
        self.header = 'particles'

    # def hdf5_to_astra(self):
    #     HDF5filename = self.particle_definition+'.hdf5'
    #     beam.read_HDF5_beam_file(master_subdir + '/' + HDF5filename)
    #     astrabeamfilename = self.particle_definition+'.astra'
    #     beam.write_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)
    def hdf5_to_astra(self, prefix=''):
        # print 'self.particle_definition = ', self.particle_definition
        HDF5filename = prefix+self.particle_definition.replace('.astra','')+'.hdf5'
        beam.read_HDF5_beam_file(master_subdir + '/' + HDF5filename)
        # print 'self.theta = ', self.theta
        # beam.rotate_beamXZ(self.theta, preOffset=self.starting_offset)
        astrabeamfilename = self.particle_definition+'.astra'
        beam.write_astra_beam_file(master_subdir + '/' + astrabeamfilename, normaliseZ=False)

class gpt_element(frameworkElement):

    def __init__(self, elementName=None, elementType=None, **kwargs):
        super(gpt_element, self).__init__(elementName, elementType, **kwargs)
        if elementName in csrtrack_defaults:
            for k, v in list(csrtrack_defaults[elementName].items()):
                self.add_default(k, v)

    def write_GPT(self):
        output = str(self.elementName) + '('
        for k in elementkeywords[self.objecttype]['keywords']:
            k = k.lower()
            if getattr(self,k) is not None:
                output += getattr(self, k)+', '
            elif k in self.objectdefaults :
                output += self.objectdefaults[k]+', '
        output[:-2]+=')\n'
        return output

class gpt_setfile(gpt_element):

    def __init__(self, **kwargs):
        super(gpt_setfile, self).__init__('setfile', 'gpt_setfile', **kwargs)
