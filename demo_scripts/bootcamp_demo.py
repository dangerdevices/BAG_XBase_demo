# -*- coding: utf-8 -*-

import os
import importlib

import numpy as np
import scipy.interpolate as interp
import matplotlib.pyplot as plt

from bag import BagProject
from bag.io import read_yaml
from bag.layout.routing import RoutingGrid
from bag.layout.template import TemplateDB
from bag.data import load_sim_results, save_sim_results, load_sim_file

from xbase_demo.demo_layout.core import RoutingDemo


def make_tdb(prj, specs, impl_lib):
    grid_specs = specs['routing_grid']
    layers = grid_specs['layers']
    spaces = grid_specs['spaces']
    widths = grid_specs['widths']
    bot_dir = grid_specs['bot_dir']

    # create RoutingGrid object
    routing_grid = RoutingGrid(prj.tech_info, layers, spaces, widths, bot_dir)
    # create layout template database
    tdb = TemplateDB('template_libs.def', routing_grid, impl_lib, use_cybagoa=True)
    return tdb


def gen_pwl_data(fname):
    td = 100e-12
    tpulse = 800e-12
    tr = 20e-12
    amp = 10e-3

    tvec = [0, td, td + tr, td + tr + tpulse, td + tr + tpulse + tr]
    yvec = [-amp, -amp, amp, amp, -amp]

    dir_name = os.path.dirname(fname)
    os.makedirs(dir_name, exist_ok=True)

    with open(fname, 'w') as f:
        for t, y in zip(tvec, yvec):
            f.write('%.4g %.4g\n' % (t, y))


def routing_demo(prj, specs):
    impl_lib = 'DEMO_ROUTING'

    # create layout template database
    tdb = make_tdb(prj, specs, impl_lib)
    # compute layout
    print('computing layout')
    template = tdb.new_template(params={}, temp_cls=RoutingDemo)
    # create layout in OA database
    print('creating layout')
    tdb.batch_layout(prj, [template], ['ROUTING_DEMO'])
    # return corresponding schematic parameters
    print('layout done')


def gen_layout(prj, specs, dsn_name):
    # get information from specs
    dsn_specs = specs[dsn_name]
    impl_lib = dsn_specs['impl_lib']
    layout_params = dsn_specs['layout_params']
    lay_package = dsn_specs['layout_package']
    lay_class = dsn_specs['layout_class']
    gen_cell = dsn_specs['gen_cell']

    # get layout generator class
    lay_module = importlib.import_module(lay_package)
    temp_cls = getattr(lay_module, lay_class)

    # create layout template database
    tdb = make_tdb(prj, specs, impl_lib)
    # compute layout
    print('computing layout')
    template = tdb.new_template(params=layout_params, temp_cls=temp_cls)
    # create layout in OA database
    print('creating layout')
    tdb.batch_layout(prj, [template], [gen_cell])
    # return corresponding schematic parameters
    print('layout done')
    return template.sch_params


def gen_schematics(prj, specs, dsn_name, sch_params, check_lvs=False):
    dsn_specs = specs[dsn_name]

    impl_lib = dsn_specs['impl_lib']
    sch_lib = dsn_specs['sch_lib']
    sch_cell = dsn_specs['sch_cell']
    gen_cell = dsn_specs['gen_cell']
    testbenches = dsn_specs['testbenches']

    # create schematic generator object
    dsn = prj.create_design_module(sch_lib, sch_cell)
    # compute schematic
    print('computing %s schematics' % gen_cell)
    dsn.design(**sch_params)
    # create schematic in OA database
    print('creating %s schematics' % gen_cell)
    dsn.implement_design(impl_lib, top_cell_name=gen_cell, erase=True)

    if check_lvs:
        print('running lvs')
        lvs_passed, lvs_log = prj.run_lvs(impl_lib, gen_cell)
        if not lvs_passed:
            raise ValueError('LVS failed.  check log file: %s' % lvs_log)
        else:
            print('lvs passed')
            print('lvs log is ' + lvs_log)

    for name, info in testbenches.items():
        tb_lib = info['tb_lib']
        tb_cell = info['tb_cell']
        tb_sch_params = info['sch_params']

        tb_gen_cell = '%s_%s' % (gen_cell, name)

        if 'tran_fname' in tb_sch_params:
            tran_fname = os.path.abspath(tb_sch_params['tran_fname'])
            gen_pwl_data(tran_fname)
            tb_sch_params['tran_fname'] = tran_fname

        tb_dsn = prj.create_design_module(tb_lib, tb_cell)
        print('computing %s schematics' % tb_gen_cell)
        tb_dsn.design(dut_lib=impl_lib, dut_cell=gen_cell, **tb_sch_params)
        print('creating %s schematics' % tb_gen_cell)
        tb_dsn.implement_design(impl_lib, top_cell_name=tb_gen_cell, erase=True)

    print('schematic done')


def simulate(prj, specs, dsn_name):
    view_name = specs['view_name']
    sim_envs = specs['sim_envs']
    dsn_specs = specs[dsn_name]

    data_dir = dsn_specs['data_dir']
    impl_lib = dsn_specs['impl_lib']
    gen_cell = dsn_specs['gen_cell']
    testbenches = dsn_specs['testbenches']

    results_dict = {}
    for name, info in testbenches.items():
        tb_params = info['tb_params']
        tb_gen_cell = '%s_%s' % (gen_cell, name)

        # setup testbench ADEXL state
        print('setting up %s' % tb_gen_cell)
        tb = prj.configure_testbench(impl_lib, tb_gen_cell)
        # set testbench parameters values
        for key, val in tb_params.items():
            tb.set_parameter(key, val)
        # set config view, i.e. schematic vs extracted
        tb.set_simulation_view(impl_lib, gen_cell, view_name)
        # set process corners
        tb.set_simulation_environments(sim_envs)
        # commit changes to ADEXL state back to database
        tb.update_testbench()
        # start simulation
        print('running simulation')
        tb.run_simulation()
        # import simulation results to Python
        print('simulation done, load results')
        results = load_sim_results(tb.save_dir)
        # save simulation data as HDF5 format
        save_sim_results(results, os.path.join(data_dir, '%s.hdf5' % tb_gen_cell))

        results_dict[name] = results

    print('all simulation done')

    return results_dict


def load_sim_data(specs, dsn_name):
    dsn_specs = specs[dsn_name]
    data_dir = dsn_specs['data_dir']
    gen_cell = dsn_specs['gen_cell']
    testbenches = dsn_specs['testbenches']

    results_dict = {}
    for name, info in testbenches.items():
        tb_gen_cell = '%s_%s' % (gen_cell, name)
        fname = os.path.join(data_dir, '%s.hdf5' % tb_gen_cell)
        print('loading simulation data for %s' % tb_gen_cell)
        results_dict[name] = load_sim_file(fname)

    print('finish loading data')

    return results_dict


def plot_data(results_dict):
    dc_results = results_dict['tb_dc']
    vin = dc_results['vin']
    vout = dc_results['vout']

    vin_arg = np.argsort(vin)
    vin = vin[vin_arg]
    vout = vout[vin_arg]
    vout_fun = interp.InterpolatedUnivariateSpline(vin, vout)
    vout_diff_fun = vout_fun.derivative(1)

    f, (ax1, ax2) = plt.subplots(2, sharex='all')
    ax1.set_title('Vout vs Vin')
    ax1.set_ylabel('Vout (V)')
    ax1.plot(vin, vout)
    ax2.set_title('Gain vs Vin')
    ax2.set_ylabel('Gain (V/V)')
    ax2.set_xlabel('Vin (V)')
    ax2.plot(vin, vout_diff_fun(vin))

    ac_tran_results = results_dict['tb_ac_tran']
    tvec = ac_tran_results['time']
    freq = ac_tran_results['freq']
    vout_ac = ac_tran_results['vout_ac']
    vout_tran = ac_tran_results['vout_tran']

    f, (ax1, ax2) = plt.subplots(2, sharex='all')
    ax1.set_title('Magnitude vs Frequency')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.semilogx(freq, 20 * np.log10(np.abs(vout_ac)))
    ax2.set_title('Phase vs Frequency')
    ax2.set_ylabel('Phase (Degrees)')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.semilogx(freq, np.angle(vout_ac, deg=True))

    plt.figure()
    plt.title('Vout vs Time')
    plt.ylabel('Vout (V)')
    plt.xlabel('Time (s)')
    plt.plot(tvec, vout_tran)

    plt.show()

def run_flow(prj, specs, dsn_name):
    run_lvs = True

    # generate layout, get schematic parameters from layout
    dsn_sch_params = gen_layout(prj, specs, dsn_name)
    # generate design/testbench schematics
    gen_schematics(prj, specs, dsn_name, dsn_sch_params, check_lvs=run_lvs)
    # run simulation and import results
    simulate(prj, specs, dsn_name)

    # load simulation results from save file
    res_dict = load_sim_data(specs, dsn_name)
    # post-process simulation results
    plot_data(res_dict)


if __name__ == '__main__':
    spec_fname = 'demo_specs/demo.yaml'

    # load specifications from file
    top_specs = read_yaml(spec_fname)

    # create BagProject object
    local_dict = locals()
    if 'bprj' in local_dict:
        print('using existing BagProject')
        bprj = local_dict['bprj']
    else:
        print('creating BagProject')
        bprj = BagProject()

    # routing_demo(bprj, top_specs)
    run_flow(bprj, top_specs, 'amp_cs')
    # gen_layout(bprj, top_specs, 'amp_sf')
    # run_flow(bprj, top_specs, 'amp_sf')
    # gen_layout(bprj, top_specs, 'amp_chain')
    # run_flow(bprj, top_specs, 'amp_chain')
