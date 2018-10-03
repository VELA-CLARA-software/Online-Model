import numpy as np
import os, sys
sys.path.append(os.path.abspath(__file__+'/../../../../'))
from SimulationFramework.Framework import *
from SimulationFramework.Modules.constraints import *
import SimulationFramework.Modules.read_beam_file as rbf
import SimulationFramework.Modules.read_twiss_file as rtf
import shutil
import uuid
from functools import partial

def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z

class TemporaryDirectory(object):
    """Context manager for tempfile.mkdtemp() so it's usable with "with" statement."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def tempname(self):
        return 'tmp'+str(uuid.uuid4())

    def __enter__(self, dir=os.getcwd()):
        exists = True
        while exists:
            self.name = dir + '/' + self.tempname()
            if not os.path.exists(self.name):
                exists=False
                os.makedirs(self.name)
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.name)

class fitnessFunc():

    def __init__(self, args, tempdir, scaling=4, overwrite=True, verbose=False, summary=False, post_injector=True):
        self.cons = constraintsClass()
        self.beam = rbf.beam()
        self.twiss = rtf.twiss()
        self.scaling = scaling
        self.tmpdir = tempdir
        self.verbose = verbose
        self.summary = summary
        self.overwrite = overwrite
        self.post_injector = post_injector
        # print 'self.post_injector = ', self.post_injector
        ''' if only post-injector optimisation'''
        if self.post_injector:
            linac2field, linac2phase, linac3field, linac3phase, fhcfield, fhcphase, linac4field, linac4phase, bcangle = args
            self.parameters = dict(zip(['linac2field', 'linac2phase', 'linac3field', 'linac3phase', 'fhcfield', 'fhcphase', 'linac4field', 'linac4phase', 'bcangle'], args))
        else:
            ''' including injector parameters '''
            gunphase, gunsol, linac1field, linac1phase, linac1sol1, linac1sol2, linac2field, linac2phase, linac3field, linac3phase, fhcfield, fhcphase, linac4field, linac4phase, bcangle = args
            self.parameters = dict(zip(['gunphase','gunsol','linac1field','linac1phase', 'linac1sol1', 'linac1sol2', 'linac2field', 'linac2phase', 'linac3field', 'linac3phase', 'fhcfield', 'fhcphase', 'linac4field', 'linac4phase', 'bcangle'], args))
        self.npart=2**(3*scaling)
        ncpu = scaling*3
        if self.post_injector:
            self.sbandlinacfields = np.array([linac2field, linac3field, linac4field])
        else:
            self.sbandlinacfields = np.array([linac1field, linac2field, linac3field, linac4field])
        self.dirname = os.path.basename(self.tmpdir)
        self.framework = Framework(self.dirname, overwrite=overwrite, verbose=verbose)
        if not os.name == 'nt':
            self.framework.defineGeneratorCommand(['/opt/ASTRA/generator'])
            self.framework.defineASTRACommand(['mpiexec','-np',str(ncpu),'/opt/ASTRA/astra_MPICH2.sh'])
            self.framework.defineCSRTrackCommand(['/opt/OpenMPI-1.4.3/bin/mpiexec','-n',str(ncpu),'/opt/CSRTrack/csrtrack_openmpi.sh'])
        self.framework.defineElegantCommand(['elegant'])
        self.framework.loadSettings('Lattices/clara400_v12_v3.def')
        if not self.post_injector:
            self.framework.generator.particles = self.npart
            self.framework.modifyElement('CLA-HRG1-GUN-CAV', 'phase', gunphase)
            self.framework.modifyElement('CLA-HRG1-GUN-SOL', 'field_amplitude', gunsol)
            self.framework.modifyElement('CLA-L01-CAV', 'field_amplitude', abs(linac1field))
            self.framework.modifyElement('CLA-L01-CAV', 'phase', linac1phase)
            self.framework.modifyElement('CLA-L01-CAV-SOL-01', 'field_amplitude', linac1sol1)
            self.framework.modifyElement('CLA-L01-CAV-SOL-02', 'field_amplitude', linac1sol2)
        self.framework.modifyElement('CLA-L02-CAV', 'field_amplitude', abs(linac2field))
        self.framework.modifyElement('CLA-L02-CAV', 'phase', linac2phase)
        self.framework.modifyElement('CLA-L03-CAV', 'field_amplitude', abs(linac3field))
        self.framework.modifyElement('CLA-L03-CAV', 'phase', linac3phase)
        self.framework.modifyElement('CLA-L4H-CAV', 'field_amplitude', abs(fhcfield))
        self.framework.modifyElement('CLA-L4H-CAV', 'phase', fhcphase)
        self.framework.modifyElement('CLA-L04-CAV', 'field_amplitude', abs(linac4field))
        self.framework.modifyElement('CLA-L04-CAV', 'phase', linac4phase)
        self.framework['bunch_compressor'].set_angle(abs(bcangle))

    def between(self, value, minvalue, maxvalue, absolute=True):
        if absolute:
            result = max([minvalue,min([maxvalue,abs(value)])])
        else:
            result = np.sign(value)*max([minvalue,min([maxvalue,abs(value)])])
        return result

    def calculateBeamParameters(self):
        bcangle = self.framework['bunch_compressor'].angle
        # print 'bcangle = ', bcangle
        try:
            # if abs(bcangle) < 0.01 or abs(bcangle) > 0.175:
                # raise ValueError
            if self.overwrite:
                startS = self.framework['L02'].startObject['position_start'][2]
                if self.post_injector:
                    self.framework['L02'].file_block['input']['prefix'] = '../basefiles_'+str(self.scaling)+'/'
                    self.framework.track(startfile='L02', endfile='S07')#startfile='FMS')
                else:
                    self.framework.track(endfile='S07')

            # self.beam.read_astra_beam_file(self.dirname+'/S07.4928.001')
            self.beam.read_HDF5_beam_file(self.dirname+'/CLA-S07-MARK-03.hdf5')
            self.beam.slices = 10
            self.beam.bin_time()
            sigmat = 1e12*np.std(self.beam.t)
            sigmap = np.std(self.beam.p)
            meanp = np.mean(self.beam.p)
            emitx = 1e6*self.beam.normalized_mve_horizontal_emittance
            emity = 1e6*self.beam.normalized_mve_horizontal_emittance
            volume = 1/((1e-6)**5) * self.beam.volume
            fitp = 100*sigmap/meanp
            fhcfield = self.parameters['fhcfield']
            peakI, peakIMomentumSpread, peakIEmittanceX, peakIEmittanceY, peakIMomentum, peakIVolume = self.beam.mvesliceAnalysis()
            peakIVolume = peakIVolume/((1e-6)**5)
            chirp = self.beam.chirp
            constraintsList = {
                'peakI_min': {'type': 'greaterthan', 'value': abs(peakI), 'limit': 600, 'weight': 60},
                'peakI_max': {'type': 'lessthan', 'value': abs(peakI), 'limit': 750, 'weight': 10},
                # 'peakIMomentumSpread': {'type': 'lessthan', 'value': peakIMomentumSpread, 'limit': 0.1, 'weight': 2},
                # 'peakIEmittanceX': {'type': 'lessthan', 'value': 1e6*peakIEmittanceX, 'limit': 0.75, 'weight': 5},
                # 'peakIEmittanceY': {'type': 'lessthan', 'value': 1e6*peakIEmittanceY, 'limit': 0.75, 'weight': 5},
                'peakIMomentum': {'type': 'equalto','value': 1e-6*peakIMomentum, 'limit': 220, 'weight': 20},
                'sband_linac fields': {'type': 'lessthan', 'value': 1e-6*self.sbandlinacfields, 'limit': 32, 'weight': 100},
                # 'xband_linac fields': {'type': 'lessthan', 'value': 1e-6*self.xbandlinacfields, 'limit': 100, 'weight': 100},
                '4hc field': {'type': 'lessthan', 'value': 1e-6*fhcfield, 'limit': 35, 'weight': 100},
                # 'horizontal emittance': {'type': 'lessthan', 'value': emitx, 'limit': 2, 'weight': 0},
                # 'vertical emittance': {'type': 'lessthan', 'value': emity, 'limit': 2, 'weight': 0},
                # 'momentum_spread': {'type': 'lessthan', 'value': fitp, 'limit': 0.1, 'weight': 2},
                'chirp': {'type': 'equalto', 'value': abs(chirp), 'limit': 0, 'weight': 10},
                'positive_chirp': {'type': 'lessthan', 'value': chirp, 'limit': 0, 'weight': 1},
                'peakI_volume': {'type': 'lessthan', 'value': peakIVolume, 'limit': 50, 'weight': 5},
                'volume': {'type': 'lessthan', 'value': volume, 'limit': 5000, 'weight': 2},
            }
            # self.twiss.read_astra_emit_files(self.dirname+'/S07.Zemit.001')
            # constraintsList5 = {
            #     'last_exn_5': {'type': 'lessthan', 'value': 1e6*self.twiss['enx'], 'limit': 0.75, 'weight': 1},
            #     'last_eyn_5': {'type': 'lessthan', 'value': 1e6*self.twiss['eny'], 'limit': 0.75, 'weight': 1},
            # }
            # constraintsList = merge_two_dicts(constraintsList, constraintsList5)
            fitness = self.cons.constraints(constraintsList)
            if self.verbose:
                print self.cons.constraintsList(constraintsList)
            if self.summary:
                np.save('summary_constraints.txt', self.cons.constraintsList(constraintsList))
                # self.astra.createHDF5Summary(reference='Longitudinal_GA')
            print fitness, 1e-6*peakIMomentum, abs(peakI), 1e6*peakIEmittanceX, 1e6*peakIEmittanceY, chirp, peakIVolume, volume
            return fitness
        except Exception as e:
            print(e)
            return 1e6
