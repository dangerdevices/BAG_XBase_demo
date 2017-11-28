# -*- coding: utf-8 -*-
########################################################################################################################
#
# Copyright (c) 2014, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################################################################

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'amp_cs.yaml'))


# noinspection PyPep8Naming
class demo_templates__amp_cs(Module):

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent,
                        prj=prj, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            lch='channel length in meters.',
            w_dict='Dictionary of transistor widths.',
            intent_dict='Dictionary of transistor threshold flavors.',
            fg_dict='Dictionary of transistor number of fingers.',
        )
        
    def design(self, lch=18e-9, w_dict=None, intent_dict=None, fg_dict=None):
        # populate self.parameters dictionary
        wp = w_dict['load']
        wn = w_dict['amp']
        intentp = intent_dict['load']
        intentn = intent_dict['amp']

        fg_amp = fg_dict['amp']
        fg_load = fg_dict['load']
        fg_dump = fg_dict['dump']
        fg_dumn_list = fg_dict['dumn_list']

        # set transistor parameters
        self.instances['XP'].design(w=wp, l=lch, intent=intentp, nf=fg_load)
        self.instances['XPD'].design(w=wp, l=lch, intent=intentp, nf=fg_dump)
        self.instances['XN'].design(w=wn, l=lch, intent=intentn, nf=fg_amp)

        if len(fg_dumn_list) == 1:
            self.instances['XND'].design(w=wn, l=lch, intent=intentn, nf=fg_dumn_list[0])
        else:
            # we have two types of dummies.  Use array_instance to add a new
            # dummy transistor.
            name_list = ['XND0', 'XND1']
            term_list = [{}, dict(D='vout')]
            self.array_instance('XND', name_list, term_list=term_list)
            self.instances['XND'][0].design(w=wn, l=lch, intent=intentn, nf=fg_dumn_list[0])
            self.instances['XND'][1].design(w=wn, l=lch, intent=intentn, nf=fg_dumn_list[1])
