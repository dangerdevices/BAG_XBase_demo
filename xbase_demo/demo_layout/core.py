# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from bag.layout.routing import TrackManager

from abs_templates_ec.analog_core import AnalogBase


class AmpCS(AnalogBase):
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
        super(AmpCS, self).__init__(temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

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
            lch='channel length, in meters.',
            w_dict='width dictionary.',
            intent_dict='intent dictionary.',
            fg_dict='number of fingers dictionary.',
            ndum='number of dummies on each side.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            tr_widths='track width dictionary.',
            show_pins='True to draw pin geometries.',
        )

    def draw_layout(self):
        """Draw the layout of a transistor for characterization.
        """

        lch = self.params['lch']
        w_dict = self.params['w_dict']
        intent_dict = self.params['intent_dict']
        fg_dict = self.params['fg_dict']
        ndum = self.params['ndum']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        tr_widths = self.params['tr_widths']
        show_pins = self.params['show_pins']

        fg_amp = fg_dict['amp']
        fg_load = fg_dict['load']
        fg_ref = fg_dict['ref']

        if fg_load % 2 != 0 or fg_amp % 2 != 0:
            raise ValueError('fg_load=%d and fg_amp=%d must be even.' % (fg_load, fg_amp))

        fg_half_pmos = fg_load // 2
        fg_half_nmos = fg_amp // 2
        fg_half = max(fg_half_pmos, fg_half_nmos)
        # make sure gap between ref and load is even
        fg_gap_pmos = fg_half - fg_half_pmos
        fg_delta = 0 if fg_gap_pmos % 2 == 0 else 1
        fg_tot = fg_half * 2 + fg_ref + 2 * (ndum + fg_delta)

        nw_list = [w_dict['amp']]
        pw_list = [w_dict['load']]
        nth_list = [intent_dict['amp']]
        pth_list = [intent_dict['load']]

        tr_manager = TrackManager(self.grid, tr_widths, {})

        hm_layer = self.get_mos_conn_layer(self.grid.tech_info) + 1
        num_ng, ng_loc = tr_manager.place_wires(hm_layer, ['vin'])
        num_pds, pds_loc = tr_manager.place_wires(hm_layer, ['vout'])
        vout_nsp = tr_manager.get_space(hm_layer, 'vout')
        num_pg, pg_loc = tr_manager.place_wires(hm_layer, ['ibias'])

        ng_tracks = [num_ng]
        nds_tracks = [vout_nsp]
        pds_tracks = [num_pds]
        pg_tracks = [vout_nsp + num_pg]

        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list,
                       nth_list, pw_list, pth_list,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks,
                       pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       n_orientations=['R0'], p_orientations=['MX'],
                       )

        vin_idx = ng_loc[0]
        vout_idx = pds_loc[0]
        ibias_idx = pg_loc[0]

        ref_col = ndum
        load_col = ndum + fg_ref + fg_delta + fg_half - fg_half_pmos
        amp_col = ndum + fg_ref + fg_delta + fg_half - fg_half_nmos

        if (fg_amp - fg_load) % 4 == 0:
            ampd, amps, nsdir, nddir = 'd', 's', 0, 2
        else:
            ampd, amps, nsdir, nddir = 's', 'd', 2, 0

        amp_ports = self.draw_mos_conn('nch', 0, amp_col, fg_amp, nsdir, nddir)
        load_ports = self.draw_mos_conn('pch', 0, load_col, fg_load, 2, 0)
        ref_ports = self.draw_mos_conn('pch', 0, ref_col, fg_ref, 2, 0)

        vin_tid = self.make_track_id('nch', 0, 'g', vin_idx, width=tr_manager.get_width(hm_layer, 'vin'))
        vout_tid = self.make_track_id('pch', 0, 'ds', vout_idx, width=tr_manager.get_width(hm_layer, 'vout'))
        ibias_tid = self.make_track_id('pch', 0, 'g', ibias_idx, width=tr_manager.get_width(hm_layer, 'ibias'))

        vin_warr = self.connect_to_tracks(amp_ports['g'], vin_tid)
        vout_warr = self.connect_to_tracks([amp_ports[ampd], load_ports['d']], vout_tid)
        ibias_warr = self.connect_to_tracks([ref_ports['g'], ref_ports['d'], load_ports['g']], ibias_tid)
        self.connect_to_substrate('ptap', amp_ports[amps])
        self.connect_to_substrate('ntap', [ref_ports['s'], load_ports['s']])

        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()

        self.add_pin('VSS', ptap_wire_arrs, show=show_pins)
        self.add_pin('VDD', ntap_wire_arrs, show=show_pins)
        self.add_pin('vin', vin_warr, show=show_pins)
        self.add_pin('vout', vout_warr, show=show_pins)
        self.add_pin('ibias', ibias_warr, show=show_pins)

        sch_fg_dict = fg_dict.copy()
        sch_fg_dict['dump'] = fg_tot - fg_ref - fg_load
        if ampd == 'd':
            sch_fg_dict['dumn_list'] = [fg_tot - fg_amp]
        else:
            sch_fg_dict['dumn_list'] = [fg_tot - fg_amp - 2, 2]
        self._sch_params = dict(
            lch=lch,
            w_dict=w_dict,
            intent_dict=intent_dict,
            fg_dict=sch_fg_dict,
        )
