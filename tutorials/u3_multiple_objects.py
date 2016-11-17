"""
A model for extended visual interface: multiple objects at the same time, vision checks them all and stores them.
"""

import string
import random
import warnings

import pyactr as actr


class Model(object):
    """
    Model pressing the right key.
    """

    def __init__(self, env, **kwargs):
        self.m = actr.ACTRModel(environment=env, **kwargs)

        actr.chunktype("pair", "probe answer")
        
        actr.chunktype("goal", "state")

        self.dm = self.m.DecMem()

        retrieval = self.m.dmBuffer("retrieval", self.dm)

        g = self.m.goal("g")
        self.m.goal("g2", set_delay=0.2)
        start = actr.makechunk(nameofchunk="start", typename="chunk", value="start")
        actr.makechunk(nameofchunk="attending", typename="chunk", value="attending")
        actr.makechunk(nameofchunk="done", typename="chunk", value="done")
        g.add(actr.makechunk(typename="read", state=start))

        self.m.productionstring(name="find_probe", string="""
        =g>
        isa     goal
        state   start
        ?visual_location>
        buffer  empty
        ==>
        =g>
        isa     goal
        state   attend
        ?visual_location>
        attended False
        +visual_location>
        isa _visuallocation
        screen_x closest""") #this rule is used if automatic visual search does not put anything in the buffer


        self.m.productionstring(name="check_probe", string="""
        =g>
        isa     goal
        state   start
        ?visual_location>
        buffer  full
        ==>
        =g>
        isa     goal
        state   attend""")  #this rule is used if automatic visual puts something in the buffer

        self.m.productionstring(name="attend_probe", string="""
        =g>
        isa     goal
        state   attend
        =visual_location>
        isa    _visuallocation
        ?visual>
        state   free
        ==>
        =g>
        isa     goal
        state   reading
        +visual>
        isa     _visual
        cmd     move_attention
        screen_pos =visual_location
        ~visual_location>""")


        self.m.productionstring(name="encode_probe", string="""
        =g>
        isa     goal
        state   reading
        =visual>
        isa     _visual
        value   =val
        ==>
        =g>
        isa     goal
        state   start
        ~visual>""")


if __name__ == "__main__":
    text = [{1: {'text': 'X', 'position': (10, 10)}, 2: {'text': 'Y', 'position': (10, 20)}, 3:{'text': 'Z', 'position': (10, 30)}},{1: {'text': 'A', 'position': (50, 10)}, 2: {'text': 'B', 'position': (50, 180)}, 3:{'text': 'C', 'position': (400, 180)}}]
    environ = actr.Environment(focus_position=(0,0))
    m = Model(environ, subsymbolic=True, latency_factor=0.4, decay=0.5, retrieval_threshold=-2, instantaneous_noise=0, automatic_visual_search=True, eye_mvt_angle_parameter=1) #If you don't want to use the EMMA model, specify emma=False in here
    sim = m.m.simulation(realtime=True, trace=True,  gui=True, environment_process=environ.environment_process, stimuli=text, triggers='X', times=2)
    sim.run(4)
    print(m.dm)

