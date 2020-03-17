import os, sys
sys.path.append('../../../')
import SimulationFramework.Framework as fw
from SimulationFramework.Modules.nelder_mead import nelder_mead
from SimulationFramework.ClassFiles.Optimise_transverse import Optimise_transverse
from SimulationFramework.Modules.merge_two_dicts import merge_two_dicts
from ruamel import yaml

framework = fw.Framework(None)
framework.loadSettings('FEBE.def')
parameters = framework.getElementType('quadrupole','k1l')
names = framework.getElementType('quadrupole','objectname')
index1 = names.index('CLA-S07F-MAG-QUAD-01')
index2 = names.index('CLA-S07F-MAG-QUAD-10')+1
index3 = names.index('CLA-FEB-MAG-QUAD-13')
parameter_names = []
# parameter_names = [q for q in names[index1:index2]]
# parameter_names.append('FODO_F')
# parameter_names.append('FODO_D')
parameter_names += [q for q in names[index3:]]
best = parameters
# for n, p in zip(names, parameters)[index3:]:
#     print n, p
# exit()
best = [-0.0744722, 0.47353, -0.0940485, -0.0244515, 0.0257142, -0.10087, 0.57013, -0.61296, #S07
#1.55838, -1.09374, #ARC F and D quads
#1.08184, -2.38876, 1.66352, -1.29897, 2.07599, -1.95901, -1.73588, 1.63013, -0.154276, -0.048223, 0.0478511, -0.0479035, 0.0472847,
]
best = best + parameters[index3:]

with open('FEBE_transverse_best_changes.yaml', 'r') as infile:
    data = dict(yaml.load(infile, Loader=yaml.UnsafeLoader))
    # best = [data[n]['k1l'] for n in parameter_names]
    best = []
    for n in parameter_names:
        if n in data:
            best.append(data[n]['k1l'])
        else:
            print(n)
            best.append(framework[n]['k1l'])

class FEBE_Transverse(Optimise_transverse):

    def __init__(self, lattice='FEBE.def', scaling=6):
        super(FEBE_Transverse, self).__init__(lattice=lattice, scaling=scaling)
        names = framework.getElementType('quadrupole','objectname')
        index1 = names.index('CLA-S07F-MAG-QUAD-01')
        index2 = names.index('CLA-S07F-MAG-QUAD-10') + 1
        index3 = names.index('CLA-FEA-MAG-QUAD-13')
        index4 = names.index('CLA-FEH-MAG-QUAD-24-CORR')
        self.parameter_names = []
        self.parameters = []
        # self.parameter_names = [q for q in names[index1:index2]]
        # self.parameters = [[q, 'k1l'] for q in names[index1:index2]]
        self.parameter_names += [q for q in names[index3:]]
        # self.parameters.append(['FODO_F', 'k1l'])
        # self.parameters.append(['FODO_D', 'k1l'])
        self.parameters += [[q, 'k1l'] for q in names[index3:]]
        self.save_parameters = [['FODO_F', 'k1l'], ['FODO_D', 'k1l']]
        self.base_files = '../../../CLARA/basefiles_' + str(int(scaling)) + '/'
        # self.base_files = '../../example/'
        self.best_changes = './FEBE_transverse_best_changes.yaml'
        self.clean = True
        self.start_file = 'PreFEBE'

    def before_tracking(self):
        self.framework.change_Lattice_Code('All','elegant')
        lattices = self.framework.latticeObjects.values()
        for l in lattices:
            l.trackBeam = True

    def calculateBeamParameters(self):
        twiss = self.twiss
        self.framework.defineElegantCommand(location=['elegant'])
        self.framework[self.start_file].prefix = self.base_files
        self.framework[self.start_file].sample_interval = 2**(3*1)
        # self.framework['FEBE'].betax = 0.74306
        # self.framework['FEBE'].betay = 3.96111
        # self.framework['FEBE'].alphax = -0.623844
        # self.framework['FEBE'].alphay = 0.872959
        self.framework.track(startfile=self.start_file)

        constraintsList = {}

        twiss.reset_dicts()
        twiss.read_sdds_file( self.dirname+'/FEBE.mat' )
        # print((1e3*twiss.elegant['R56'][-1]))
        constraintsListR56 = {
            'isochronous': {'type': 'lessthan', 'value': abs(1e3*twiss.elegant['R56'][-1]), 'limit': 0.1, 'weight': 00},
        }
        constraintsList = merge_two_dicts(constraintsList, constraintsListR56)

        for lat in ['FEBE']:
            quadkls = self.framework[lat].getElementType('quadrupole','k1l')
            quadlengths = self.framework[lat].getElementType('quadrupole','length')
            constraintsListQuads = {
                'max_k_'+lat: {'type': 'lessthan', 'value': [abs(k) for k, l in zip(quadkls, quadlengths)], 'limit': 2.0, 'weight': 75},

            }
            constraintsList = merge_two_dicts(constraintsList, constraintsListQuads)

        twiss.read_elegant_twiss_files( [ self.dirname+'/FEBE.twi'])
        ipindex1 = list(twiss['element_name']).index('CLA-FEH-FOCUS-01')
        ipindex2 = list(twiss['element_name']).index('CLA-FEH-FOCUS-02')
        constraintsListFEBE = {
            'max_betax': {'type': 'lessthan', 'value': max(twiss['beta_x']), 'limit': 25, 'weight': 150},
            'max_betay': {'type': 'lessthan', 'value': max(twiss['beta_y']), 'limit': 25, 'weight': 150},
            'ip1_sigmax': {'type': 'lessthan', 'value': 1e3*twiss['sigma_x'][ipindex1], 'limit': 0.05, 'weight': 15},
            'ip1_sigmay': {'type': 'lessthan', 'value': 1e3*twiss['sigma_y'][ipindex1], 'limit': 0.05, 'weight': 15},
            # 'ip_sigmaxy': {'type': 'equalto', 'value': 1e3*twiss['sigma_y'][ipindex], 'limit': 1e3*twiss['sigma_x'][ipindex], 'weight': 25},
            'ip1_alphax': {'type': 'equalto', 'value': twiss['alpha_x'][ipindex1], 'limit': 0., 'weight': 5},
            'ip1_alphay': {'type': 'equalto', 'value': twiss['alpha_y'][ipindex1], 'limit': 0., 'weight': 5},
            'ip1_etax': {'type': 'equalto', 'value': twiss['eta_x'][ipindex1], 'limit': 0., 'weight': 5000},
            'ip1_etaxp': {'type': 'equalto', 'value': twiss['eta_xp'][ipindex1], 'limit': 0., 'weight': 5000},
            'ip2_sigmax': {'type': 'lessthan', 'value': 1e3*twiss['sigma_x'][ipindex2], 'limit': 0.05, 'weight': 15},
            'ip2_sigmay': {'type': 'lessthan', 'value': 1e3*twiss['sigma_y'][ipindex2], 'limit': 0.05, 'weight': 15},
            # 'ip_sigmaxy': {'type': 'equalto', 'value': 1e3*twiss['sigma_y'][ipindex], 'limit': 1e3*twiss['sigma_x'][ipindex], 'weight': 25},
            'ip2_alphax': {'type': 'equalto', 'value': twiss['alpha_x'][ipindex2], 'limit': 0., 'weight': 5},
            'ip2_alphay': {'type': 'equalto', 'value': twiss['alpha_y'][ipindex2], 'limit': 0., 'weight': 5},
            'ip2_etax': {'type': 'equalto', 'value': twiss['eta_x'][ipindex2], 'limit': 0., 'weight': 5000},
            'ip2_etaxp': {'type': 'equalto', 'value': twiss['eta_xp'][ipindex2], 'limit': 0., 'weight': 5000},
        }
        constraintsList = merge_two_dicts(constraintsList, constraintsListFEBE)

        # twiss.read_elegant_twiss_files( [ self.dirname+'/FEBE600.twi' ])
        constraintsListFEBE600 = {
            'max_betax_600': {'type': 'lessthan', 'value': max(twiss['beta_x']), 'limit': 25, 'weight': 150},
            'max_betay_600': {'type': 'lessthan', 'value': max(twiss['beta_y']), 'limit': 25, 'weight': 150},
            'dump_etax_600': {'type': 'equalto', 'value': twiss['eta_x'][-1], 'limit': 0., 'weight': 5000},
        }
        constraintsList = merge_two_dicts(constraintsList, constraintsListFEBE600)

        self.constraintsList = constraintsList
        fitness = self.cons.constraints(constraintsList)
        if self.verbose:
            print(self.cons.constraintsList(constraintsList))
        return fitness


if __name__ == "__main__":
        fit = FEBE_Transverse('./FEBE_Single.def', scaling=6)
        fit.setChangesFile(['./nelder_mead_best_changes.yaml', './transverse_best_changes_upto_S07.yaml', './S07_transverse_best_changes.yaml'])
        fit.verbose = False
        fit.Nelder_Mead(best, step=0.1)
        # fit.Simplex(best)
