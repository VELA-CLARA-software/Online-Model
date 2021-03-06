# SAM to Python Conversion
# DJS August 2017
# Version 0.1
#
import numpy
import math
from ComponentBase import ComponentBase


class BeamPositionMonitor(ComponentBase):
    def __init__(self, length=0, name="", aperture=[]):
        ComponentBase.__init__(self, length, name, aperture)
        # super(ComponentBase, self).__init__(length, name, aperture)
        self.dummy = 0
        self.x = None
        self.y = None

    def Track(self, beam):
        # print 'BPM_TRACK'
        # First apply a drift through ds/2
        d1 = numpy.sqrt(1 - beam.px * beam.px
                        - beam.py * beam.py
                        + 2 * beam.dp / beam.beta
                        + beam.dp * beam.dp)
        beam.x = beam.x + (self.length * beam.px) / d1
        # beam.y  = beam.y  + self.length*numpy.divide(beam.py,d1)
        beam.y = beam.y + self.length * beam.py / d1

        beam.ct = beam.ct + self.length * (1 - (1 + beam.beta * beam.dp) / d1) / beam.beta
        # Next, Calc Y and Y in the middle of the BPM (TP added this)
        self.x = numpy.mean(beam.x)
        self.y = numpy.mean(beam.y)

        # save
        self.lastTrackedBeam = beam

#
# classdef BeamPositionMonitor < handle
#     % BeamPositionMonitor class
#     %
#     % Properties:
#     %   name
#     %   buffer
#     %   aperture
#     %
#     % Methods:
#     %   Track
#     %   ResetBuffer
#
#     properties (Constant)
#         length = 0; % length = 0 metres (constant)
#     end % properties (Constant)
#
#     properties (Access='private')
#         bufferpointer = 1;
#     end % properties (Access='private')
#
#     properties
#         name     = ''; % string
#         buffer   = zeros(3,1024); % 2 x Nturns matrix recording beam centroid
#         aperture = []; % 1x2 array of elliptical aperture half-axes, in metres
#     end % properties
#
#     methods
#
#         function beam = Track(bpm,beam)
#             % Tracking method for a beam position monitor
#
#             [x, ~, y] = beam.GetParticles();
#             bpm.buffer(1:2,bpm.bufferpointer) = mean([x; y],2);
#             bpm.buffer(  3,bpm.bufferpointer) = sum(beam.distance(2,:));
#             buffersize = size(bpm.buffer);
#             bpm.bufferpointer = mod(bpm.bufferpointer,buffersize(2)) + 1;
#
#         end % function Track
#
#         function TrackLibrary(bpm,trackingMethod,libroutine)
#
#             bpm1.apertureX = 0;
#             bpm1.apertureY = 0;
#
#             if(~isempty(bpm.aperture))
#                bpm1.apertureX = bpm.aperture(1);
#                bpm1.apertureY = bpm.aperture(2);
#             end
#
#             bpmXPtr  = libpointer('doublePtr',0);
#             bpmYPtr  = libpointer('doublePtr',0);
#             nptclPtr = libpointer('int32Ptr',0);
#
#             calllib(trackingMethod,[libroutine 'BPM'],bpm1,bpmXPtr,bpmYPtr,nptclPtr);
#
#             bpm.buffer(:,bpm.bufferpointer) = [bpmXPtr.Value; bpmYPtr.Value; nptclPtr.Value];
#             buffersize = size(bpm.buffer);
#             bpm.bufferpointer = mod(bpm.bufferpointer,buffersize(2)) + 1;
#
#         end % function TrackLibrary
#
#         function buffersize = ResetBuffer(bpm,buffersize)
#             % Clears the BPM buffer
#
#             bpm.bufferpointer = 1;
#             bpm.buffer = zeros(3,buffersize);
#
#         end % function ClearBuffer
#
#     end % methods
#
# end  % classdef BeamPositionMonitor
