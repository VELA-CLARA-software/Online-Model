import yaml, collections, subprocess, os, math, re, sys
from shutil import copyfile
import numpy as np
from FrameworkHelperFunctions import *
from getGrids import *
sys.path.append('..')
import read_beam_file as rbf
from collections import defaultdict
from Framework_ASTRA import ASTRA
from Framework_CSRTrack import CSRTrack

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return dict(z)

class Framework(object):

    def __init__(self, subdir='test', overwrite=None, runname='CLARA_240'):
        super(Framework, self).__init__()
        self.lineIterator = 0
        self.basedirectory = os.getcwd()
        self.subdir = subdir
        self.overwrite = overwrite
        self.runname = runname
        self.subdirectory = self.basedirectory+'/'+subdir
        self.globalSettings = dict()
        self.fileSettings = dict()
        self.elements = dict()
        self.groups = dict()
        self.astra = ASTRA(parent=self, directory=self.subdir)
        self.CSRTrack = CSRTrack(parent=self, directory=self.subdir)
        if not os.path.exists(self.subdirectory):
            os.makedirs(self.subdirectory)
        if self.overwrite == None:
            if not os.path.exists(self.subdirectory):
                os.makedirs(self.subdirectory)
                self.overwrite = True
            else:
                response = raw_input('Overwrite existing directory ? [Y/n]')
                self.overwrite = True if response in {'','y','Y','yes','Yes','YES'} else False
        self.astraFiles = []

    def loadElementsFile(self, input):
        if isinstance(input,(list,tuple)):
            filename = input
        else:
            filename = [input]
        for f in filename:
            stream = file(f, 'r')
            elements = yaml.load(stream)['elements']
            stream.close()
            if 'filename' in elements:
                self.loadElementsFile(elements['filename'])
            self.elements = merge_two_dicts(self.elements, elements)

    def loadSettings(self, filename='short_240.settings'):
        """Load Lattice Settings from file"""
        stream = file(filename, 'r')
        settings = yaml.load(stream)
        self.globalSettings = settings['global']
        self.generatorFile = self.globalSettings['generatorFile'] if 'generatorFile' in self.globalSettings else None
        self.fileSettings = settings['files']
        self.elements = settings['elements']
        self.groups = settings['groups']
        stream.close()
        if 'filename' in self.elements:
            self.loadElementsFile(self.elements['filename'])
        elements = [k for k in self.elements if 'type' in self.elements[k]]
        elements_ordered = OrderedDict()
        for elem in sorted(elements, key=lambda x: self.elements[x]['position_start'][2]):
            elements_ordered[elem] = self.elements[elem]
        self.elements = elements_ordered

    def getFileSettings(self, file, block, default={}):
        """Return the correct settings 'block' from 'file' dict if exists else return empty dict"""
        if file in self.fileSettings and block in self.fileSettings[file]:
            return self.fileSettings[file][block]
        else:
            return default

    def getSettingsBlock(self, dict, block):
        """Return the correct settings 'block' from dict if exists else return empty dict"""
        if block in dict:
            return dict[block]
        else:
            return {}

    def modifyFile(self, filename, setting, value):
        if filename in self.fileSettings:
            if isinstance(setting, (list,tuple)):
                dic = self.fileSettings[filename]
                for key in setting[:-1]:
                    dic = dic.setdefault(key, {})
                dic[setting[-1]] = value
            elif not setting in self.fileSettings:
                self.fileSettings[setting] = {}
                self.fileSettings[filename][setting] = value

    def getElement(self, element='', setting=None):
        """return 'element' from the main elements dict"""
        if element in self.elements:
            if setting is not None:
                return self.elements[element][setting]
            else:
                return self.elements[element]
        else:
            return []

    def modifyElement(self, element='', setting='', value=''):
        """return 'element' from the main elements dict"""
        element = self.getElement(element)
        if setting in element:
            element[setting] = value

    def getElementType(self, type='', setting=None):
        """return 'element' from the main elements dict"""
        elems = []
        for name, element in self.elements.viewitems():
            if 'type' in element and element['type'] == type:
                elems.append(name)
                # print element
        elems = sorted(elems, key=lambda x: self.elements[x]['position_start'][2])
        if setting is not None:
            return [self.elements[x][setting] for x in elems]
        else:
            return elems

    def setElementType(self, type='', setting=None, values=[]):
        """return 'element' from the main elements dict"""
        elems = self.getElementType(type)
        if len(elems) == len(values):
            for e, v  in zip(elems, values):
                self.elements[e][setting] = v
        else:
            raise ValueError

    def getElementsBetweenS(self, elementtype, output={}, zstart=None, zstop=None):
        # zstart = zstart if zstart is not None else getParameter(output,'zstart',default=0)
        if zstart is None:
            zstart = getParameter(output,'zstart',default=None)
            if zstart is None:
                startelem = getParameter(output,'start_element',default=None)
                if startelem is None or startelem not in self.elements:
                    zstart = 0
                else:
                    zstart = self.elements[startelem]['position_start'][2]
        # zstop = zstop if zstop is not None else getParameter(output,'zstop',default=0)
        if zstop is None:
            zstop = getParameter(output,'zstop',default=None)
            if zstop is None:
                endelem = getParameter(output,'end_element',default=None)
                if endelem is None or endelem not in self.elements:
                    zstop = 0
                else:
                    zstop = self.elements[endelem]['position_end'][2]

        elements = findSetting('type',elementtype,dictionary=self.elements)
        elements = sorted([[s[1]['position_start'][2],s[0]] for s in elements if s[1]['position_start'][2] >= zstart and s[1]['position_start'][2] <= zstop])

        return [e[1] for e in elements]

    def getGroup(self, group=''):
        """return all elements in a group from the main elements dict"""
        elements = []
        if group in self.groups:
            groupelements = self.groups[group]['elements']
            for e in groupelements:
                elements.append([e,self.getElement(e)])
        return elements

    def xform(self, theta, tilt, length, x, r):
        """Calculate the change on local coordinates through an element"""
        theta = theta if abs(theta) > 1e-6 else 1e-6
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

    def elementPositions(self, elements, startpos=None):
        """Calculate element positions for the given 'elements'"""
        anglesum = [0]
        localXYZ = np.identity(3)
        if startpos == None:
            startpos = elements[0][1]['position_start']
            if len(startpos) == 1:
                startpos = [0,0,startpos]
        x1 = np.matrix(np.transpose([startpos]))
        x = [np.array(x1)]
        for name, d in elements:
            angle = getParameter(d,'angle',default=1e-9)
            anglesum.append(anglesum[-1]+angle)
            x1, localXYZ = self.xform(angle, 0, getParameter(d,'length'), x1, localXYZ)
            x.append(x1)
        return zip(x, anglesum[:-1], elements), localXYZ

    def createDrifts(self, elements, startpos=None):
        """Insert drifts into a sequence of 'elements'"""
        positions = []
        elementno = 0
        for name, e in elements:
            pos = np.array(e['position_start'])
            positions.append(pos)
            # length = np.array(e['position_end'])
            positions.append(e['position_end'])
        if not startpos == None:
            positions.prepend(startpos)
        else:
            positions = positions[1:]
            positions.append(positions[-1]+[0,0,0.0001])
        driftdata = list(chunks(positions, 2))
        for d in driftdata:
            if len(d) > 1:
                length = d[1][2] - d[0][2]
                if length > 0:
                    elementno += 1
                    elements.append(['drift'+str(elementno),
                                {'length': length, 'type': 'drift',
                                 'position_start': list(d[0]),
                                 'position_end': list(d[1])
                                }])
        return sorted(elements, key=sortByPositionFunction)

    def setDipoleAngle(self, dipole, angle=0):
        """Set the dipole angle for a given 'dipole'"""
        name, d = dipole
        if getParameter(d,'entrance_edge_angle') == 'angle':
            d['entrance_edge_angle'] = np.sign(d['angle'])*angle
        if getParameter(d,'exit_edge_angle') == 'angle':
            d['exit_edge_angle'] = np.sign(d['angle'])*angle
        d['angle'] = np.sign(d['angle'])*angle
        return [name, d]

    def createInputFiles(self):
        for f in self.fileSettings.keys():
            filename = self.subdirectory+'/'+f+'.in'
            if 'code' in self.fileSettings[f]:
                code = self.fileSettings[f]['code']
                if code.upper() == 'ASTRA':
                    saveFile(filename, lines=self.astra.createASTRAFileText(f))
                if code.upper() == 'CSRTRACK':
                    saveFile(filename, lines=self.CSRTrack.createCSRTrackFileText(f))
            else:
                saveFile(filename, lines=self.astra.createASTRAFileText(f))

    def runInputFiles(self, files=None):
        if not isinstance(files, (list, tuple)):
            files = self.fileSettings.keys()
        for f in files:
            if f in self.fileSettings.keys():
                filename = f+'.in'
                # print 'Running file: ', f
                if 'code' in self.fileSettings[f]:
                    code = self.fileSettings[f]['code']
                    if code.upper() == 'ASTRA':
                        self.astra.runASTRA(filename)
                    if code.upper() == 'CSRTRACK':
                        self.CSRTrack.runCSRTrack(filename)
                        self.CSRTrack.convertCSRTrackOutput(f)
            else:
                print 'File does not exist! - ', f
