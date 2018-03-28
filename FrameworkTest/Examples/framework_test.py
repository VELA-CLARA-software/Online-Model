import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname( os.path.abspath(__file__)))))
from FrameworkTest.framework import *

lattice = framework('CLARA')
lattice.loadSettings('Lattices/clara400_v12_elegant.def')
# print lattice.elements
# print lattice.getElement('CLA-S02-MAG-QUAD-01').type
# print lattice.getElement('CLA-HRG1-GUN-CAV').properties
# print lattice['injector400'].writeElements_ASTRA()
# print lattice['injector400'].write_Lattice()
lattice.track()#files=['injector400'])
# for i, q in enumerate(lattice.dipoles,1):
#     print q.write_ASTRA(i)
# for i, q in enumerate(lattice.cavities,1):
#     print q.write_ASTRA(i)

# lattice.writeElements_ASTRA()
# print lattice.getElementType('quadrupole')
