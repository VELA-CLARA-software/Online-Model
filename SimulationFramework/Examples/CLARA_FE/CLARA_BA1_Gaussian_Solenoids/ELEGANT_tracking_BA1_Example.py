import sys, os
import numpy as np
import csv
from scipy.optimize import minimize
sys.path.append('../../../../')
from SimulationFramework.Framework import *
import SimulationFramework.Modules.read_beam_file as rbf
beam = rbf.beam()
import SimulationFramework.Modules.read_twiss_file as rtf
from SimulationFramework.Modules.merge_two_dicts import merge_two_dicts
from SimulationFramework.Modules.constraints import *
twiss = rtf.twiss()


def before_tracking():
    elements = lattice.elementObjects.values()
    for e in elements:
        e.lsc_enable = True
        e.lsc_bins = 200
        e.current_bins = 0
        e.longitudinal_wakefield_enable = True
        e.transverse_wakefield_enable = True
    lattices = lattice.latticeObjects.values()
    for l in lattices:
        l.lscDrifts = True
        l.lsc_bins = 200

def create_base_files(scaling, charge=70):
    framework = Framework('basefiles_'+str(scaling)+'_'+str(charge), overwrite=True, clean=True)
    framework.loadSettings('CLA10-BA1_TOMP_Separated.def')
    if not os.name == 'nt':
        framework.defineASTRACommand(scaling=(scaling))
        framework.defineCSRTrackCommand(scaling=(scaling))
    framework.generator.number_of_particles = 2**(3*scaling)
    framework.modifyElement('CLA-LRG1-GUN-CAV', 'phase', -5)
    framework['generator'].charge = charge * 1e-12
    # before_tracking()
    framework.track(files=['generator','injector10'])

## Modify as appropriate! ##
# for i in [6]:
    # create_base_files(i,20)
    # create_base_files(i,50)
    # create_base_files(i,70)
    # create_base_files(i,150)
    # create_base_files(i,250)
# exit()

def optFunc(linac1field):
    global dir, lattice
    lattice.modifyElement('CLA-L01-CAV', 'field_amplitude', abs(linac1field[0]))
    lattice.track(startfile='L01', endfile='L01', track=True)
    beam.read_HDF5_beam_file(dir+'/CLA-S02-APER-01.hdf5')
    print ('mom = ', abs(np.mean(beam.cp)) , 35500000)
    return abs(np.mean(beam.cp) - 35500000)


def setMomentum():
    global dir, lattice
    best = [lattice.getElement('CLA-L01-CAV', 'field_amplitude')]
    res = minimize(optFunc, best, method='nelder-mead', tol=1000, options={'disp': False, 'adaptive': True})
    # res = minimize(optFunc, best, method='BFGS', tol=1, options={'eps': 10000, 'disp': True})
    return res.x

def set_Phase(phase, charge=70, track=True):
    global dir, lattice, scaling
    dir = 'SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    if track:
        lattice.change_Lattice_Code('L01','elegant')
        elements = lattice.elementObjects.values()
        for e in elements:
            e.lsc_enable = False
            # e.lsc_bins = 200
            # e.current_bins = 0
            # e.longitudinal_wakefield_enable = True
            # e.transverse_wakefield_enable = True
        lattice.modifyElement('CLA-L01-CAV', 'phase', phase)
        lattice['L01'].file_block['input']['prefix'] = '../../../CLARA_BA1_Gaussian/basefiles_'+str(scaling)+'_'+str(charge)+'/'
        lattice['L01'].sample_interval = 8
        mom = setMomentum()
        print('mom = ', mom)
        optFunc(mom)
    lattice.change_Lattice_Code('L01','ASTRA')
    if track:
        elements = lattice.elementObjects.values()
        for e in elements:
            e.lsc_enable = False
    lattice['L01'].file_block['input']['prefix'] = '../../../CLARA_BA1_Gaussian/basefiles_'+str(scaling)+'_'+str(charge)+'/'
    lattice['L01'].sample_interval = 8
    lattice.modifyElement('CLA-L01-CAV', 'phase', phase)
    before_tracking()
    if track:
        lattice.modifyElement('CLA-L01-CAV', 'field_amplitude', abs(mom[0]))
        lattice.track(startfile='L01', endfile='L01')
    lattice['S02'].file_block['input']['prefix'] = '../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'

def track_phase_elegant(phase, charge=70):
    global dir, lattice
    dir = './NoSC/TOMP_NoSC_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','elegant')
    lattice['S02'].lscDrifts = False
    lattice.change_Lattice_Code('C2V','elegant')
    lattice['C2V'].lscDrifts = False
    lattice.change_Lattice_Code('VELA','elegant')
    lattice['VELA'].lscDrifts = False
    before_tracking()
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tElegant No SC ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tElegant No SC ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans

def track_phase_elegant_SC(phase, charge=70):
    global dir, lattice
    dir = './SC/TOMP_SC_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','elegant')
    lattice['S02'].lscDrifts = True
    lattice['S02'].csrDrifts = False
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    elements = lattice.elementObjects.values()
    for e in elements:
        e.csr_enable = False
        e.sr_enable = False
        e.isr_enable = False
        e.current_bins = 0
        e.lsc_enable = True
        e.lsc_bins = 128
        e.longitudinal_wakefield_enable = True
        e.transverse_wakefield_enable = True
        e.smoothing_half_width = 2
        e.lsc_high_frequency_cutoff_start = 0.25
        e.lsc_high_frequency_cutoff_end = 0.33
    lattices = lattice.latticeObjects.values()
    for l in lattices:
        l.csr_enable = False
        l.lscDrifts = True
        l.csrDrifts = False
        l.lsc_bins = 128
        l.lsc_high_frequency_cutoff_start = 0.25
        l.lsc_high_frequency_cutoff_end = 0.33
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tElegant SC ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tElegant SC ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans

def track_phase_elegant_SC_CSR(phase, charge=70):
    global dir, lattice
    dir = './SC_CSR/TOMP_SC_CSR_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','elegant')
    lattice['S02'].lscDrifts = True
    lattice['S02'].csrDrifts = False
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    elements = lattice.elementObjects.values()
    for e in elements:
        e.csr_enable = True
        e.sr_enable = True
        e.isr_enable = True
        e.csr_bins = 50
        e.lsc_enable = True
        e.lsc_bins = 50
        e.longitudinal_wakefield_enable = True
        e.transverse_wakefield_enable = True
        e.smoothing_half_width = 1
        e.lsc_high_frequency_cutoff_start = -1#0.25
        e.lsc_high_frequency_cutoff_end = -1#0.33
    lattices = lattice.latticeObjects.values()
    for l in lattices:
        l.csr_enable = True
        l.lscDrifts = True
        l.csrDrifts = True
        l.lsc_bins = 50
        l.lsc_high_frequency_cutoff_start = -1#0.25
        l.lsc_high_frequency_cutoff_end = -1#0.33
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tElegant SC CSR ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tElegant SC CSR ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans

def track_phase_astra(phase, charge=70):
    global dir, lattice
    dir = './ASTRA/TOMP_ASTRA_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','ASTRA')
    lattice.change_Lattice_Code('C2V','Elegant')
    lattice.change_Lattice_Code('VELA','ASTRA')
    lattice.change_Lattice_Code('BA1','ASTRA')
    # before_tracking()
    lattice['S02'].sample_interval = 2**(3*1)
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tASTRA ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tASTRA ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans

def track_phase_gpt(phase, charge=70):
    global dir, lattice
    dir = './GPT/TOMP_GPT_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','GPT')
    lattice.change_Lattice_Code('C2V','GPT')
    lattice.change_Lattice_Code('VELA','GPT')
    lattice.change_Lattice_Code('BA1','GPT')
    # before_tracking()
    lattice['S02'].sample_interval = 2**(3*2)
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    lattices = lattice.latticeObjects.values()
    for l in lattices:
        l.csr_enable = False
        try:
            l.file_block['charge']['space_charge_mode'] = '3D'
        except:
            pass
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tGPT ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tGPT ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans


def track_phase_gpt_CSR(phase, charge=70):
    global dir, lattice
    dir = './GPT_CSR/TOMP_GPT_CSR_'+str(phase)+'_'+str(charge)
    lattice.setSubDirectory(dir)
    lattice.change_Lattice_Code('S02','GPT')
    lattice.change_Lattice_Code('C2V','GPT')
    lattice.change_Lattice_Code('VELA','GPT')
    lattice.change_Lattice_Code('BA1','GPT')
    # before_tracking()
    lattice['S02'].sample_interval = 2**(3*1)
    lattice['S02'].file_block['input']['prefix'] = '../../SETUP/TOMP_SETUP_'+str(phase)+'_'+str(charge)+'/'
    lattices = lattice.latticeObjects.values()
    for l in lattices:
        l.csr_enable = True
    lattice.track(startfile='S02', endfile='S02', track=True)
    beam.read_HDF5_beam_file(dir+'/EBT-INJ-DIA-YAG-05.hdf5')
    ansNear = [phase, np.mean(beam.cp), beam.sigma_z, beam.momentum_spread]
    print('Phase = ', phase)
    print('\t\tGPT CSR ', charge, 'pC NEAR:  sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    beam.read_HDF5_beam_file(dir+'/EBT-BA1-COFFIN-FOC.hdf5')
    ansFar = [beam.sigma_z, beam.momentum_spread]
    print('\t\tGPT CSR ', charge, 'pC FAR:   sigma_z = ', beam.sigma_z, '    momentum-spread = ', beam.momentum_spread)
    ans = ansNear + ansFar + [charge]
    return ans

def updateOutput(output):
    sys.stdout.write(output + '\r')
    sys.stdout.flush()

def optFuncChicane(args):
    global dir, lattice
    s02q1, s02q2, s02q3, s02q4, c2vq1, c2vq2 = args
    lattice.modifyElement('CLA-S02-MAG-QUAD-01', 'k1l', s02q1)
    lattice.modifyElement('CLA-S02-MAG-QUAD-02', 'k1l', s02q2)
    lattice.modifyElement('CLA-S02-MAG-QUAD-03', 'k1l', s02q3)
    lattice.modifyElement('CLA-S02-MAG-QUAD-04', 'k1l', s02q4)
    lattice.modifyElement('CLA-C2V-MAG-QUAD-01', 'k1l', c2vq1)
    lattice.modifyElement('CLA-C2V-MAG-QUAD-02', 'k1l', c2vq2)
    lattice.modifyElement('CLA-C2V-MAG-QUAD-03', 'k1l', c2vq1)
    lattice.track(startfile='S02', endfile='C2V', track=True)
    beam.read_HDF5_beam_file(dir+'/CLA-C2V-MARK-01.hdf5')
    twiss.reset_dicts()
    twiss.read_sdds_file(dir+'/C2V.twi')
    emitStart = beam.normalized_horizontal_emittance
    betaXStart = twiss.elegant['betax'][0]
    betaYStart = twiss.elegant['betay'][0]
    # print 'Start beta_x = ', betaXStart, '  beta_y = ', betaYStart, '  emit_x = ', emitStart
    beam.read_HDF5_beam_file(dir+'/CLA-C2V-MARK-02.hdf5')
    emitEnd = beam.normalized_horizontal_emittance
    betaXEnd = twiss.elegant['betax'][-1]
    betaYEnd = twiss.elegant['betay'][-1]
    betaYPenalty = betaYStart - 50 if betaYStart > 50 else 0
    etaXEnd = twiss.elegant['etax'][-1]
    etaXEnd = etaXEnd if abs(etaXEnd) > 1e-3 else 0
    etaXPEnd = twiss.elegant['etaxp'][-1]
    etaXPEnd = etaXEnd if abs(etaXEnd) > 1e-3 else 0
    # print 'End beta_x = ', betaXEnd, '  beta_y = ', betaYEnd, '  emit_x = ', emitEnd
    delta = np.sqrt((1e6*abs(emitStart-emitEnd))**2 + 1*abs(betaXStart-betaXEnd)**2 + 1*abs(betaYStart-betaYEnd)**2 + 10*abs(betaYPenalty)**2 + 100*abs(etaXEnd)**2 + 100*abs(etaXPEnd)**2)
    if delta < 0.1:
        delta = 0.1
    updateOutput('Chicane delta = ' + str(delta))
    return delta

def setChicane(quads):
    global dir, lattice
    best = [lattice.getElement('CLA-S02-MAG-QUAD-01', 'k1l'),
            lattice.getElement('CLA-S02-MAG-QUAD-02', 'k1l'),
            lattice.getElement('CLA-S02-MAG-QUAD-03', 'k1l'),
            lattice.getElement('CLA-S02-MAG-QUAD-04', 'k1l'),
            lattice.getElement('CLA-C2V-MAG-QUAD-01', 'k1l'),
            lattice.getElement('CLA-C2V-MAG-QUAD-02', 'k1l')
    ]
    best = quads
    res = minimize(optFuncChicane, best, method='nelder-mead', options={'disp': False, 'adaptive': True})
    return res.x

def optFuncVELA(args):
    global dir, lattice, bestdelta
    try:
        lattice.modifyElement('CLA-S02-MAG-QUAD-01', 'k1l', args[0])
        lattice.modifyElement('CLA-S02-MAG-QUAD-02', 'k1l', args[1])
        lattice.modifyElement('CLA-S02-MAG-QUAD-03', 'k1l', args[2])
        lattice.modifyElement('CLA-S02-MAG-QUAD-04', 'k1l', args[3])
        lattice.modifyElement('CLA-C2V-MAG-QUAD-01', 'k1l', args[4])
        lattice.modifyElement('CLA-C2V-MAG-QUAD-02', 'k1l', args[5])
        lattice.modifyElement('CLA-C2V-MAG-QUAD-03', 'k1l', args[4])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-07', 'k1l', args[6])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-08', 'k1l', args[7])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-09', 'k1l', args[8])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-10', 'k1l', args[9])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-11', 'k1l', args[10])
        lattice.modifyElement('EBT-INJ-MAG-QUAD-15', 'k1l', args[11])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-01', 'k1l', args[12])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-02', 'k1l', args[13])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-03', 'k1l', args[14])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-04', 'k1l', args[15])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-05', 'k1l', args[16])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-06', 'k1l', args[17])
        lattice.modifyElement('EBT-BA1-MAG-QUAD-07', 'k1l', args[18])
        lattice.track(startfile='S02', endfile='S02', track=True)

        constraintsList = {}
        twiss.reset_dicts()
        twiss.read_elegant_twiss_files(dir+'/S02.twi')
        c2v1index = list(twiss['element_name']).index('CLA-C2V-MARK-01')
        c2v2index = list(twiss['element_name']).index('CLA-C2V-MARK-02')
        ipindex = list(twiss['element_name']).index('EBT-BA1-COFFIN-FOC')
        constraintsListBA1 = {
            'BA1_max_betax': {'type': 'lessthan', 'value': twiss['beta_x'][c2v2index:ipindex], 'limit': 30, 'weight': 150},
            'BA1_max_betay': {'type': 'lessthan', 'value': twiss['beta_y'][c2v2index:ipindex], 'limit': 30, 'weight': 150},

            'c2v_betax': {'type': 'equalto', 'value': twiss['beta_x'][c2v1index], 'limit': twiss['beta_x'][c2v2index], 'weight': 10},
            'c2v_betay': {'type': 'equalto', 'value': twiss['beta_y'][c2v1index], 'limit': twiss['beta_y'][c2v2index], 'weight': 10},
            'c2v_alphax': {'type': 'equalto', 'value': twiss['alpha_x'][c2v1index], 'limit': -1*twiss['alpha_x'][c2v2index], 'weight': 10},
            'c2v_alphay': {'type': 'equalto', 'value': twiss['alpha_y'][c2v1index], 'limit': -1*twiss['alpha_y'][c2v2index], 'weight': 10},

            'ip_betax': {'type': 'lessthan', 'value': twiss['beta_x'][ipindex], 'limit': 0.5, 'weight': 25},
            'ip_betay': {'type': 'lessthan', 'value': twiss['beta_y'][ipindex], 'limit': 0.5, 'weight': 25},
            'ip_alphax': {'type': 'equalto', 'value': twiss['alpha_x'][ipindex], 'limit': 0., 'weight': 2.5},
            'ip_alphay': {'type': 'equalto', 'value': twiss['alpha_y'][ipindex], 'limit': 0., 'weight': 2.5},
            'ip_etax': {'type': 'lessthan', 'value': abs(twiss['eta_x'][ipindex]), 'limit': 1e-4, 'weight': 50},
            'ip_etaxp': {'type': 'lessthan', 'value': abs(twiss['eta_xp'][ipindex]), 'limit': 1e-4, 'weight': 50},
            'dump_etax': {'type': 'equalto', 'value': twiss['eta_x'][-1], 'limit': 0.67, 'weight': 5000},
            'dump_betax': {'type': 'lessthan', 'value': twiss['beta_x'][-1], 'limit': 20, 'weight': 1.5},
            'dump_betay': {'type': 'lessthan', 'value': twiss['beta_y'][-1], 'limit': 20, 'weight': 1.5},
        }
        constraintsList = merge_two_dicts(constraintsList, constraintsListBA1)

        cons = constraintsClass()
        delta = cons.constraints(constraintsList)
        updateOutput('VELA delta = ' + str(delta))
        if delta < bestdelta:
            bestdelta = delta
            print('### New Best: ', delta)
            # print(*args, sep = ", ")
            print '[',', '.join(map(str,args)),']'
            # print(cons.constraintsList(constraintsList))
    except:
        delta = 1e6
    else:
        return delta

def setVELA(quads):
    global dir, lattice, bestdelta
    bestdelta = 1e10
    best = quads
    res = minimize(optFuncVELA, best, method='nelder-mead', options={'disp': False, 'adaptive': True, 'fatol': 1e-3, 'maxiter': 100})
    return res.x

def optimise_Lattice(phase=None, q=70, do_optimisation=False):
    global dir, lattice, scaling, bestdelta
    bestdelta = 1e10
    dir = './SETUP/TOMP_SETUP'
    lattice = Framework(dir, clean=False, verbose=False)
    lattice.loadSettings('CLA10-BA1_TOMP_Separated.def')
    scaling = 6
    if not os.name == 'nt':
        lattice.defineASTRACommand(scaling=(scaling))
        lattice.defineCSRTrackCommand(scaling=(scaling))
        lattice.define_gpt_command(scaling=(scaling))
    lattice['L01'].file_block['input']['prefix'] = '../basefiles_'+str(scaling)+'_'+str(q)+'/'
    quads = 0.107*np.array([  21.11058462, -11.36377551,  24.69336696, -22.63264054,  56.07039682, -51.58739658])
    # quads = setChicane(quads)
    # optFuncChicane(quads)
    # print('Chicane = ', quads)
    quads = [
        lattice.getElement('CLA-S02-MAG-QUAD-01', 'k1l'),
        lattice.getElement('CLA-S02-MAG-QUAD-02', 'k1l'),
        lattice.getElement('CLA-S02-MAG-QUAD-03', 'k1l'),
        lattice.getElement('CLA-S02-MAG-QUAD-04', 'k1l'),
        lattice.getElement('CLA-C2V-MAG-QUAD-01', 'k1l'),
        lattice.getElement('CLA-C2V-MAG-QUAD-02', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-07', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-08', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-09', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-10', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-11', 'k1l'),
        lattice.getElement('EBT-INJ-MAG-QUAD-15', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-01', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-02', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-03', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-04', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-05', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-06', 'k1l'),
        lattice.getElement('EBT-BA1-MAG-QUAD-07', 'k1l'),

    ]
    quads = np.array([
    1.7815538119218322, -1.6517067100557492, 2.3043853160232697, -1.3861969157005136, 5.757177173351052, -4.733558263809512, 1.7234634394591193, -1.5865723560117138, 0.3758596578541717, -0.3895175193164829, 0.17091495276247198, 0.12327634704511606, -0.2637956911506127, -0.9593369561940668, 1.2250265489541068, 1.150196537233205, 0.0385787389105507, -1.3341278723969179, 1.3605277843974064 
    ])
    lattice['S02'].file_block['output']['end_element'] = 'EBT-BA1-DIA-FCUP-01'
    lattice['S02'].sample_interval = 2**(3*3)
    if do_optimisation:
        if phase is not None:
            lattice['S02'].file_block['input']['prefix'] = '../TOMP_SETUP_'+str(phase)+'_'+str(q)+'/'
        quads = setVELA(quads)
    optFuncVELA(quads)
    lattice['S02'].file_block['output']['end_element'] = 'EBT-BA1-DIA-FCUP-01'
    lattice['S02'].sample_interval = 1


optimise_Lattice()
for i in [0]: # THIS IS THE LINAC RF PHASE
    for q in [70]: # THIS IS THE BUNCH CHARGE
        set_Phase(i, q, track=False) # THIS SETS UP THE RF TO THE CORRECT LINAC PHASE
        optimise_Lattice(phase=i, q=q, do_optimisation=True) # THIS SETS THE QUADRUPOLES TO THE RIGHT VALUES

        ## THE FOLLOWING RUN ELEGANT/ASTRA/GPT IN VARIOUS DIFFERENT MODES. UNCOMMENT AS APPROPRIATE

        data = track_phase_elegant(i, q)
        # data = track_phase_elegant_SC(i, q)
        # data = track_phase_elegant_SC_CSR(i, q)
        # data = track_phase_astra(i, q)
        # data = track_phase_gpt(i)
        # data = track_phase_gpt_CSR(i)
