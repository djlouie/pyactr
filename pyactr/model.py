"""
ACT-R Model.
"""


import warnings

import simpy

import pyactr.chunks as chunks
import pyactr.goals as goals
import pyactr.productions as productions
import pyactr.utilities as utilities
import pyactr.declarative as declarative
import pyactr.motor as motor
import pyactr.vision as vision
import pyactr.simulation as simulation

class ACTRModel(object):
    """
    ACT-R model, running ACT-R simulations.
    """

    MODEL_PARAMETERS = {"subsymbolic": False,
                "rule_firing": 0.05,
                "latency_factor": 0.1,
                "decay": 0.5,
                "baselevel_learning": True,
                "instantaneous_noise" : 0,
                "retrieval_threshold" : 0,
                "buffer_spreading_activation" : {},
                "strength_of_association": 0,
                "partial_matching": False,
                "activation_trace": False,
                "utility_noise": 0,
                "utility_learning": False,
                "utility_alpha": 0.2,
                "motor_prepared": False,
                "strict_harvesting": False,
                "automatic_visual_search": True,
                "emma": True,
                "emma_noise": True,
                "eye_mvt_angle_parameter": 1, #in LispACT-R: 1
                "eye_mvt_scaling_parameter": 0.01, #in LispACT-R: 0.01, but dft frequency -- 0.01 -- 0.05 would roughly correspond to their combination in EMMA
                }

    def __init__(self, environment=None, **kwargs):

        self.chunktype = chunks.chunktype
        self.DecMem = declarative.DecMem
        self.Chunk = chunks.Chunk
        self.chunkstring = chunks.chunkstring

        self.__buffers = {}
        self._visbuffers = {}

        self.__productions = productions.Productions()
        self.__similarities = {}

        self.model_parameters = self.MODEL_PARAMETERS.copy()

        try:
            assert set(kwargs.keys()).issubset(set(self.MODEL_PARAMETERS.keys())), "Incorrect model parameter(s) %s. The only possible model parameters are: '%s'" % (set(kwargs.keys()).difference(set(self.MODEL_PARAMETERS.keys())), set(self.MODEL_PARAMETERS.keys()))
            self.model_parameters.update(kwargs)
        except TypeError:
            pass

        self.__env = environment
    
    def dmBuffer(self, name, declarative_memory, data=None, finst=0):
        """
        Creates and returns declarative memory buffer for ACTRModel.
        """
        dmb = declarative.DecMemBuffer(declarative_memory, data, finst)
        self.__buffers[name] = dmb
        return dmb

    def goal(self, name, data=None, default_harvest=None, set_delay=0):
        """
        Creates and returns goal buffer for ACTRModel.
        """
        g = goals.Goal(data, default_harvest, set_delay)
        self.__buffers[name] = g
        return g
    
    def visualBuffer(self, name_visual, name_visual_location, default_harvest=None):
        """
        Creates and returns visual buffers for ACTRModel. Two buffers are present in vision: visual What buffer, called just visual buffer (encoding seen objects) and visual Where buffer, called visual_location buffer (encoding positions). Both are created and returned.
        """
        v1 = vision.Visual(self.__env, default_harvest)
        v2 = vision.VisualLocation(self.__env, default_harvest)
        self._visbuffers[name_visual] = v1
        self._visbuffers[name_visual_location] = v2
        return v1, v2

    def productions(self, *rules):
        """
        Creates production rules out of functions. One or more functions can be inserted.
        """
        self.__productions = productions.Productions(*rules)
        return self.__productions

    def productionstring(self, name='', string='', utility=0, reward=None):
        """
        Returns a production rule when given a string. The string is specified in the form: LHS ==> RHS
        """
        if not name:
            name = "unnamedrule" + productions.Productions._undefinedrulecounter
            productions.Productions._undefinedrulecounter += 1
        temp_dictRHS = {v: k for k, v in utilities._RHSCONVENTIONS.items()}
        temp_dictLHS = {v: k for k, v in utilities._LHSCONVENTIONS.items()}
        rule_reader = utilities.getrule()
        rule = rule_reader.parseString(string, parseAll=True)
        lhs, rhs = {}, {}
        def func():
            for each in rule[0]:
                if each[0] == temp_dictLHS["query"]:
                    lhs[each[0]+each[1]] = {x[0]:x[1] for x in each[3]}
                else:
                    type_chunk, chunk_dict = chunks.createchunkdict(each[3])
                    lhs[each[0]+each[1]] = chunks.makechunk("", type_chunk, **chunk_dict)
            yield lhs
            for each in rule[2]:
                if each[0] == temp_dictRHS["extra_test"]:
                    rhs[each[0]+each[1]] = {x[0]:x[1] for x in each[3]}
                elif each[0] == temp_dictRHS["clear"]:
                    rhs[each[0]+each[1]] = None
                elif each[0] == temp_dictRHS["execute"]:
                    rhs[each[0]+each[1]] = each[3][0]
                else:
                    type_chunk, chunk_dict = chunks.createchunkdict(each[3])
                    rhs[each[0]+each[1]] = chunks.makechunk("", type_chunk, **chunk_dict)
            yield rhs
        self.__productions.update({name: {"rule": func, "utility": utility, "reward": reward}})
        return self.__productions

    def set_similarities(self, chunk, otherchunk, value):
        """
        Sets similarities between chunks. By default, different chunks have the value of -1. This can be changed.
        """
        if value > 0:
            raise utilities.ACTRError("Values in similarities must be 0 or smaller than 0")
        self.__similarities[tuple((chunk, otherchunk))] = value
        self.__similarities[tuple((otherchunk, chunk))] = value

    def simulation(self, realtime=False, trace=True, gui=True, environment_process=None, **kwargs):
        """
        Returns a simulation that has to be run with simulation.run(max_time) command.
        """
        decmem = {name: self.__buffers[name].dm for name in self.__buffers\
                if self.__buffers[name].dm != None} #dict of declarative memories used

        if not decmem:
            decmem = {"default_dm": self.DecMem()}

        self.__buffers["manual"] = motor.Motor() #adding motor buffer

        if self.__env:
            if self._visbuffers:
                self.__buffers.update(self._visbuffers)
            else:
                dm = next(iter(decmem.values()))
                self.__buffers["visual"] = vision.Visual(self.__env, dm) #adding vision buffers
                self.__buffers["visual_location"] = vision.VisualLocation(self.__env, dm) #adding vision buffers

        used_productions = productions.ProductionRules(self.__productions, self.__buffers, decmem, self.model_parameters)

        chunks.Chunk._similarities = self.__similarities

        return simulation.Simulation(self.__env, realtime, trace, gui, self.__buffers, used_productions, environment_process, **kwargs)
