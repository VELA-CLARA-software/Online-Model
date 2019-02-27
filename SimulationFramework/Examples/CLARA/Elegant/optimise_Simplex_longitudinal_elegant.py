import numpy as np
import os, sys
sys.path.append(os.path.abspath(__file__+'/../../../../../'))
from FitnessFunc_Longitudinal_elegant import *
import operator
import random
import csv
from scipy.optimize import minimize
import yaml
from functools import partial

def saveState(args, fitness):
    with open('best_solutions_running_simplex_elegantgenesis.csv','a') as out:
        csv_out=csv.writer(out)
        args=list(args)
        args.append(fitness)
        csv_out.writerow(args)

def saveParameterFile(best, file='clara_elegantgenesis_best.yaml'):
    allparams = zip(*(injparameternames+parameternames))
    output = {}
    for p, k, v in zip(allparams[0], allparams[1], best):
        if p not in output:
            output[p] = {}
        output[p][k] = v
        with open(file,"w") as yaml_file:
            yaml.dump(output, yaml_file, default_flow_style=False)

def optfunc(inputargs, dir=None, *args, **kwargs):
    if dir == None:
        with TemporaryDirectory(dir=os.getcwd()) as tmpdir:
            fit = fitnessFunc(inputargs, tmpdir, *args, **kwargs)
            fitvalue = fit.calculateBeamParameters()
    else:
            fit = fitnessFunc(inputargs, dir, *args, **kwargs)
            fitvalue = fit.calculateBeamParameters()
    saveState(inputargs, fitvalue)
    return fitvalue

framework = Framework('longitudinal_best', overwrite=False)
framework.loadSettings('Lattices/clara400_v12_v3_elegant.def')
injparameters = []
parameters = []
injparameternames = [['CLA-HRG1-GUN-CAV', 'phase'], ['CLA-HRG1-GUN-SOL', 'field_amplitude'], ['CLA-L01-CAV', 'field_amplitude'],
                     ['CLA-L01-CAV', 'phase'], ['CLA-L01-CAV-SOL-01', 'field_amplitude'], ['CLA-L01-CAV-SOL-02', 'field_amplitude']]
parameternames = [
['CLA-L02-CAV', 'field_amplitude'], ['CLA-L02-CAV', 'phase'], ['CLA-L03-CAV', 'field_amplitude'], ['CLA-L03-CAV', 'phase'],
['CLA-L4H-CAV', 'field_amplitude'], ['CLA-L4H-CAV', 'phase'], ['CLA-L04-CAV', 'field_amplitude'], ['CLA-L04-CAV', 'phase'],
['bunch_compressor','angle']
]
for p in injparameternames:
    injparameters.append(framework.getElement(*p))

''' always '''
for p in parameternames:
    parameters.append(framework.getElement(*p))

# results = []
# with open('CLARA_longitudinal_best_solutions_simplex.csv.tmp', 'r') as csvfile:
#   reader = csv.reader(csvfile, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
#   for row in reader:
#     results.append(row)
# best = results[0]
best = [27477812.476143554,-24.149079998274154,27185718.693607226,-8.078720301316636,24326877.45572499,188.9222526372106,30434366.8035302,45.17175610232019,-0.12770679325302878]
# best = parameters

print 'starting values = ', best

''' export best results to a yaml file '''
# saveParameterFile(best)
# exit()
# print 'best fitness = ', optfunc(best, dir=os.getcwd()+'/CLARA_best_longitudinal_simplex', scaling=6, overwrite=True, verbose=True, summary=True, post_injector=False)
# exit()

''' if including injector'''
# best = injparameters + parameters
''' ELSE '''
# best = parameters

optfunc3 = partial(optfunc, dir=None, scaling=3, post_injector=True)
optfunc4 = partial(optfunc, dir=None, scaling=4, post_injector=True)
optfunc5 = partial(optfunc, dir=None, scaling=5, post_injector=True)

print 'start fitness = ', optfunc(best, dir=os.getcwd()+'/CLARA_best_longitudinal_simplex_elegant', scaling=4, overwrite=True, verbose=True, summary=True, post_injector=True)
exit()

with open('best_solutions_running_simplex_elegant.csv','w') as out:
    pass
res = minimize(optfunc4, best, method='nelder-mead', options={'xtol': 1e-3, 'disp': True})
print res.x

try:
    print 'best fitness = ', optfunc(res.x, dir=os.getcwd()+'/CLARA_best_longitudinal_simplex_elegant', scaling=6, overwrite=True, verbose=True, summary=True, post_injector=True)
except:
    pass

saveParameterFile(res.x)
