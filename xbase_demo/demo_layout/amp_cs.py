# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from abs_templates_ec.analog_core import AnalogBase


class Transistor(AnalogBase):
    """A template of a single transistor with dummies.

    This class is mainly used for transistor characterization or
    design exploration with config views.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    kwargs : dict[str, any]
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AnalogBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            mos_type="transistor type, either 'pch' or 'nch'.",
            lch='channel length, in meters.',
            w='transistor width, in meters/number of fins.',
            threshold='transistor threshold flavor.',
            stack='number of transistors to stack',
            fg='number of fingers.',
            fg_dum='number of dummies on each side.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            tr_w_dict='track width dictionary.',
            tr_sp_dict='track space dictionary.',
        )

    def draw_layout(self):
        """Draw the layout of a transistor for characterization.
        """

        mos_type = self.params['mos_type']
        lch = self.params['lch']
        w = self.params['w']
        threshold = self.params['threshold']
        stack = self.params['stack']
        fg = self.params['fg']
        fg_dum = self.params['fg_dum']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        tr_w_dict = self.params['tr_w_dict']
        tr_sp_dict = self.params['tr_sp_dict']

        g_tr_w = tr_w_dict['g']
        d_tr_w = tr_w_dict['d']
        s_tr_w = tr_w_dict['s']
        gs_tr_sp = tr_sp_dict['gs']
        gd_tr_sp = tr_sp_dict['gd']
        sb_tr_sp = tr_sp_dict['sb']
        db_tr_sp = tr_sp_dict['db']

        fg_tot = (fg * stack) + 2 * fg_dum
        w_list = [w]
        th_list = [threshold]
        g_tracks = [sb_tr_sp + s_tr_w + gs_tr_sp + g_tr_w]
        ds_tracks = [gd_tr_sp + d_tr_w + db_tr_sp]

        nw_list = pw_list = []
        nth_list = pth_list = []
        ng_tracks = pg_tracks = []
        nds_tracks = pds_tracks = []
        if mos_type == 'nch':
            nw_list = w_list
            nth_list = th_list
            ng_tracks = g_tracks
            nds_tracks = ds_tracks
        else:
            pw_list = w_list
            pth_list = th_list
            pg_tracks = g_tracks
            pds_tracks = ds_tracks

        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list,
                       nth_list, pw_list, pth_list,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks,
                       pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       )

        if mos_type == 'pch':
            sdir, ddir = 2, 0
        else:
            sdir, ddir = 0, 2

        mos_ports = self.draw_mos_conn(mos_type, 0, fg_dum, fg * stack, sdir, ddir, stack=stack)
        tr_id = self.make_track_id(mos_type, 0, 'g', sb_tr_sp + (s_tr_w - 1) / 2, width=s_tr_w)
        warr = self.connect_to_tracks(mos_ports['s'], tr_id)
        self.add_pin('s', warr, show=True)
        tr_id = self.make_track_id(mos_type, 0, 'g', sb_tr_sp + s_tr_w + gs_tr_sp + (g_tr_w - 1) / 2, width=g_tr_w)
        warr = self.connect_to_tracks(mos_ports['g'], tr_id)
        self.add_pin('g', warr, show=True)
        tr_id = self.make_track_id(mos_type, 0, 'd', gd_tr_sp + (d_tr_w - 1) / 2, width=d_tr_w)
        warr = self.connect_to_tracks(mos_ports['d'], tr_id)
        self.add_pin('d', warr, show=True)

        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()
        # export body
        self.add_pin('b', ptap_wire_arrs, show=True)
        self.add_pin('b', ntap_wire_arrs, show=True)
