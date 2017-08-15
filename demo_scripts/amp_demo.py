# -*- coding: utf-8 -*-

import os
import importlib

import matplotlib.pyplot as plt

from bag import BagProject
from bag.io import read_yaml
from bag.layout.routing import RoutingGrid
from bag.layout.template import TemplateDB
from bag.data import load_sim_results, save_sim_results, load_sim_file


def make_tdb(prj, specs, impl_lib):
    # type: () -> TemplateDB
    """Create and return a new TemplateDB object."""
    grid_specs = specs['routing_grid']
    layers = grid_specs['layers']
    spaces = grid_specs['spaces']
    widths = grid_specs['widths']
    bot_dir = grid_specs['bot_dir']

    routing_grid = RoutingGrid(prj.tech_info, layers, spaces, widths, bot_dir)
    tdb = TemplateDB('template_libs.def', routing_grid, impl_lib, use_cybagoa=True)
    return tdb


def gen_layout(prj, specs, dsn_name):
    dsn_specs = specs[dsn_name]
    impl_lib = dsn_specs['impl_lib']
    layout_params = dsn_specs['layout_params']
    lay_package = dsn_specs['layout_package']
    lay_class = dsn_specs['layout_class']
    gen_cell = dsn_specs['gen_cell']

    tdb = make_tdb(prj, specs, impl_lib)
    lay_module = importlib.import_module(lay_package)
    temp_cls = getattr(lay_module, lay_class)
    print('computing layout')
    template = tdb.new_template(params=layout_params, temp_cls=temp_cls)
    print('creating layout')
    tdb.batch_layout(prj, [template], [gen_cell])
    print('layout done')
    return template.sch_params


def gen_schematics(prj, specs, dsn_name, sch_params):
    dsn_specs = specs[dsn_name]

    impl_lib = dsn_specs['impl_lib']
    sch_lib = dsn_specs['sch_lib']
    sch_cell = dsn_specs['sch_cell']
    gen_cell = dsn_specs['gen_cell']
    testbenches = dsn_specs['testbenches']

    dsn = prj.create_design_module(sch_lib, sch_cell)
    dsn.design(**sch_params)
    dsn.implement_design(impl_lib, top_cell_name=gen_cell, erase=True)

    for name, info in testbenches.items():
        tb_lib = info['tb_lib']
        tb_cell = info['tb_cell']
        tb_sch_params = info['sch_params']

        tb_gen_cell = '%s_%s' % (gen_cell, name)

        if 'tran_fname' in tb_sch_params:
            tb_sch_params['tran_fname'] = os.path.abspath(tb_sch_params['tran_fname'])

        tb_dsn = prj.create_design_module(tb_lib, tb_cell)
        tb_dsn.design(dut_lib=impl_lib, dut_cell=gen_cell, **tb_sch_params)
        tb_dsn.implement_design(impl_lib, top_cell_name=tb_gen_cell, erase=True)


def simulate(prj, specs, dsn_name):
    view_name = specs['view_name']
    sim_env = specs['sim_env']
    dsn_specs = specs[dsn_name]

    data_dir = dsn_specs['data_dir']
    impl_lib = dsn_specs['impl_lib']
    gen_cell = dsn_specs['gen_cell']
    testbenches = dsn_specs['testbenches']

    results_dict = {}
    for name, info in testbenches.items():
        tb_params = info['tb_params']
        tb_gen_cell = '%s_%s' % (gen_cell, name)

        tb = prj.configure_testbench(impl_lib, tb_gen_cell)

        for key, val in tb_params.items():
            tb.set_parameter(key, val)
        tb.set_simulation_view(impl_lib, gen_cell, view_name)
        tb.set_simulation_environments(sim_env)
        tb.update_testbench()
        tb.run_simulation()
        results = load_sim_results(tb.save_dir)
        save_sim_results(results, os.path.join(data_dir, '%s.hdf5' % tb_gen_cell))
        results_dict[name] = results

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
        results_dict[name] = load_sim_file(fname)

    return results_dict


def plot_data(results_dict):
    dc_results = results_dict['tb_dc']
    vin = dc_results['vin']
    vout = dc_results['vout']

    plt.figure(1)
    plt.title('DC Transfer function')
    plt.plot(vin, vout)
    plt.xlabel('Vin (V)')
    plt.xlabel('Vout (V)')
    plt.show()


if __name__ == '__main__':
    spec_fname = 'demo_specs/demo.yaml'

    bprj = BagProject()
    top_specs = read_yaml(spec_fname)

    gen_layout(bprj, top_specs, 'amp_cs')
