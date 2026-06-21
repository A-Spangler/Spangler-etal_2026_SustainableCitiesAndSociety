# By: Ava Spangler
# Date: 8/12/2025
# Description: This script runs SWMM simulations using pyswmm, processes the results into dataframes, and analyzes them.
# note: To simulate different storm conditions, update selected_storm in the EXECUTION block with a storm name already existing in the inp.
# Storm name MUST exist in .inp to run here.

# IMPORTS --------------------------------------------------------------------------------------------------------------
import os
import pandas as pd
import swmmio
import pyswmm
import datetime as dt
from pyswmm import Simulation, Nodes, Links, Subcatchments, LidControls, LidGroups
from scripts.config import scenarios, storms
from scripts.utils import clean_rpt_encoding, storm_timeseries
import tempfile

# DEFINITIONS ----------------------------------------------------------------------------------------------------------
cfs_to_cms = 0.0283168
ft_to_m = 12*2.54*(1/100)
inchperhour_to_cmpersec = (2.54)*(1/3600)

##### Run SWMM and save functions #####
def list_street_nodes(model): #separate out above ground storage nodes from below ground junctions
    nodes_df = model.nodes.dataframe
    nodes_df = nodes_df.reset_index()
    node_names = nodes_df['Name'].tolist()
    street_node_names = [k for k in node_names if '-S' in k]
    return street_node_names

def run_pyswmm(inp_path, node_ids):
    output_nodes = {node: {'depth': [], 'flow': [], 'volume': []} for node in node_ids}
    time_stamps = []
    with Simulation(inp_path) as sim:
        nodes = {node_id: Nodes(sim)[node_id] for node_id in node_ids}
        sim.step_advance(300) #lets python access sim during run (300 sec = 5min intervals)

        for step in enumerate(sim):
            time_stamps.append(sim.current_time)
            for node_id, node in nodes.items():
                output_nodes[node_id]['depth'].append(node.depth*ft_to_m) # ft to m
                output_nodes[node_id]['flow'].append(node.total_inflow*cfs_to_cms) #m**3/s
                output_nodes[node_id]['volume'].append(node.volume * cfs_to_cms) #m**3

        node_data = {'timestamp': time_stamps}
        for node_id in node_ids:
            node_data[f'{node_id}_depth'] = output_nodes[node_id]['depth']
            node_data[f'{node_id}_flow'] = output_nodes[node_id]['flow']
            node_data[f'{node_id}_volume'] = output_nodes[node_id]['volume']

        df_node_data = pd.DataFrame(node_data).copy()
        numeric_cols = df_node_data.columns.drop('timestamp')
        df_node_data[numeric_cols] = df_node_data[numeric_cols].apply(pd.to_numeric, errors='coerce')
        return df_node_data

# define node neighborhood tuple
node_neighborhood_df = pd.read_excel(f'../inputdata/Node_Neighborhoods.xlsx')
node_neighborhood = dict(zip(node_neighborhood_df['street_node_id'],zip(node_neighborhood_df['neighborhood'], node_neighborhood_df['historic_stream'])))

##### data analysis functions #####
def find_max_depth(processed_df, node_neighborhood, storm_name):
    # 1. Group and Pivot Logic
    grouped_df = processed_df.groupby(level=0).max()
    depth_cols = [col for col in grouped_df.columns if col.endswith('_depth')]
    max_depth_df = grouped_df[depth_cols]

    # Scenarios become columns, nodes become rows
    max_depth_df = max_depth_df.reset_index()
    max_depth_df = max_depth_df.set_index('scenario').T
    max_depth_df = max_depth_df.reset_index().rename(columns={'index': 'node_name'})
    max_depth_df = max_depth_df.reset_index(drop=True)

    # Add metadata
    max_depth_df['node_id'] = max_depth_df['node_name'].str.extract(r'([^_]+)')[0]
    max_depth_df['neighborhood'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_depth_df['historic_stream'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][1])

    # ID columns
    metadata_cols = ['node_name', 'node_id', 'neighborhood', 'historic_stream']
    scenario_names = [col for col in max_depth_df.columns if col not in metadata_cols]

    # evaluate max depths of all scenarios
    peak_depth_rows = []
    avg_depth_rows = []
    for scenario in scenario_names:
        max_val = max_depth_df[scenario].max()
        max_node = max_depth_df.loc[max_depth_df[scenario].idxmax(), 'node_name']
        peak_depth_rows.append({'scenario': scenario, 'node_name': max_node, 'peak_depth_m': max_val})

        avg_val = max_depth_df[scenario].mean()
        avg_depth_rows.append({'scenario': scenario, 'avg_depth_m': avg_val})

    peak_depth_summary = pd.DataFrame(peak_depth_rows)
    avg_depth_summary = pd.DataFrame(avg_depth_rows)

    # compute relative change (Scenario - Base)
    relative_change_in_depth = max_depth_df[scenario_names].copy()

    if 'Base' in relative_change_in_depth.columns:
        relative_change_in_depth = relative_change_in_depth.sub(max_depth_df['Base'], axis=0)

    for col in metadata_cols:
        relative_change_in_depth[col] = max_depth_df[col]

    # summarize depth results
    non_base_scenarios = [s for s in scenario_names if s != 'Base']

    print("Scenarios in relative_change_in_depth:", relative_change_in_depth.columns.tolist())
    print("Non-base scenarios:", non_base_scenarios)

    rel_depth_rows = []
    for scenario in non_base_scenarios:
        avg_change = relative_change_in_depth[scenario].mean()

        incr = relative_change_in_depth[scenario].max()
        incr_idx = relative_change_in_depth[scenario].idxmax()
        incr_node = relative_change_in_depth.loc[incr_idx, 'node_name']
        base_depth_incr = max_depth_df.loc[incr_idx, 'Base']
        pct_change_incr = (incr / base_depth_incr * 100) if base_depth_incr > 0 else float('inf')

        abs_vals = relative_change_in_depth[scenario].abs()
        idx_abs_max = abs_vals.idxmax()
        max_val = relative_change_in_depth.loc[idx_abs_max, scenario]
        max_node = relative_change_in_depth.loc[idx_abs_max, 'node_name']
        base_depth_abs = max_depth_df.loc[idx_abs_max, 'Base']
        pct_change_abs = (max_val / base_depth_abs * 100) if base_depth_abs > 0 else float('inf')

        rel_depth_rows.append({
            'scenario': scenario,
            'avg_peak_change_m': avg_change, # change in average depth (flood reduction) at moment of peak flooding
            'peak_abs_change_m': max_val, # single largest change in depth at moment of peak flooding, new scenario
            'peak_abs_change_node': max_node, # location of single largest change in depth at moment of peak flooding
            'base_depth_abs_m': base_depth_abs, # single largest change in depth at moment of peak flooding, base scenario
            'pct_change_abs': pct_change_abs, # % change largest flood depth
            'peak_increase_m': incr, # single largest deterioration (deeper flooding) in depth at moment of peak flooding
            'peak_increase_node': incr_node, # location of deterioration
            'base_depth_incr_m': base_depth_incr, # depths at deterioration location in base scenariio
            'pct_change_incr': pct_change_incr, # % change in deterioration in depth at moment of peak flooding
        })
    rel_depth_summary = pd.DataFrame(rel_depth_rows)

    # save
    max_depth_df.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_MaxDepth.csv', index=False)
    relative_change_in_depth.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_RelativeDepth.csv', index=False)
    peak_depth_summary.merge(avg_depth_summary, on='scenario').to_csv(f'../outputdata/{storm_name}_V24_AllNodes_DepthSummary.csv', index=False)
    rel_depth_summary.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_RelativeDepthSummary.csv', index=False)

    return max_depth_df, relative_change_in_depth

def find_max_vol(processed_df, node_neighborhood, storm_name):
    # 1. Group and Pivot Logic
    grouped_df = processed_df.groupby(level=0).max()
    vol_cols = [col for col in grouped_df.columns if col.endswith('_volume')]
    max_vol_df = grouped_df[vol_cols]

    # Scenarios become columns, nodes become rows
    max_vol_df = max_vol_df.reset_index()
    max_vol_df = max_vol_df.set_index('scenario').T
    max_vol_df = max_vol_df.reset_index().rename(columns={'index': 'node_name'})
    max_vol_df = max_vol_df.reset_index(drop=True)

    # Add metadata
    max_vol_df['node_id'] = max_vol_df['node_name'].str.extract(r'([^_]+)')[0]
    max_vol_df['neighborhood'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_vol_df['historic_stream'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][1])

    # ID columns
    metadata_cols = ['node_name', 'node_id', 'neighborhood', 'historic_stream']
    scenario_names = [col for col in max_vol_df.columns if col not in metadata_cols]

    # evaluate max volumes of all scenarios
    peak_vol_rows = []
    avg_vol_rows = []
    for scenario in scenario_names:
        max_val = max_vol_df[scenario].max()
        max_node = max_vol_df.loc[max_vol_df[scenario].idxmax(), 'node_name']
        peak_vol_rows.append({'scenario': scenario, 'node_name': max_node, 'peak_vol_m': max_val})

        avg_val = max_vol_df[scenario].mean()
        avg_vol_rows.append({'scenario': scenario, 'avg_vol_m': avg_val})

    peak_vol_summary = pd.DataFrame(peak_vol_rows)
    avg_vol_summary = pd.DataFrame(avg_vol_rows)

    # compute relative change (Scenario - Base)
    relative_change_in_vol = max_vol_df[scenario_names].copy()

    if 'Base' in relative_change_in_vol.columns:
        relative_change_in_vol = relative_change_in_vol.sub(max_vol_df['Base'], axis=0)

    for col in metadata_cols:
        relative_change_in_vol[col] = max_vol_df[col]

    # summarize voluume results
    non_base_scenarios = [s for s in scenario_names if s != 'Base']

    print("Scenarios in relative_change_in_vol:", relative_change_in_vol.columns.tolist())
    print("Non-base scenarios:", non_base_scenarios)

    rel_vol_rows = []
    for scenario in non_base_scenarios:
        avg_change = relative_change_in_vol[scenario].mean()

        incr = relative_change_in_vol[scenario].max()
        incr_idx = relative_change_in_vol[scenario].idxmax()
        incr_node = relative_change_in_vol.loc[incr_idx, 'node_name']
        base_vol_incr = max_vol_df.loc[incr_idx, 'Base']
        pct_change_incr = (incr / base_vol_incr * 100) if base_vol_incr > 0 else float('inf')

        abs_vals = relative_change_in_vol[scenario].abs()
        idx_abs_max = abs_vals.idxmax()
        max_val = relative_change_in_vol.loc[idx_abs_max, scenario]
        max_node = relative_change_in_vol.loc[idx_abs_max, 'node_name']
        base_vol_abs = max_vol_df.loc[idx_abs_max, 'Base']
        pct_change_abs = (max_val / base_vol_abs * 100) if base_vol_abs > 0 else float('inf')

        rel_vol_rows.append({
            'scenario': scenario,
            'avg_peak_change_m': avg_change, # change in average vol (flood reduction) at moment of peak flooding
            'peak_abs_change_m': max_val, # single largest change in vol at moment of peak flooding, new scenario
            'peak_abs_change_node': max_node, # location of single largest change in vol at moment of peak flooding
            'base_vol_abs_m': base_vol_abs, # single largest change in vol at moment of peak flooding, base scenario
            'pct_change_abs': pct_change_abs, # % change largest flood vol
            'peak_increase_m': incr, # single largest deterioration (deeper flooding) in vol at moment of peak flooding
            'peak_increase_node': incr_node, # location of deterioration
            'base_vol_incr_m': base_vol_incr, # vols at deterioration location in base scenariio
            'pct_change_incr': pct_change_incr, # % change in deterioration in vol at moment of peak flooding
        })
    rel_vol_summary = pd.DataFrame(rel_vol_rows)

    # save
    max_vol_df.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_MaxVol.csv', index=False)
    relative_change_in_vol.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_RelativeVol.csv', index=False)
    peak_vol_summary.merge(avg_vol_summary, on='scenario').to_csv(f'../outputdata/{storm_name}_V24_AllNodes_VolSummary.csv', index=False)
    rel_vol_summary.to_csv(f'../outputdata/{storm_name}_V24_AllNodes_RelativeVolSummary.csv', index=False)

    return max_vol_df, relative_change_in_vol

###### EXECUTION ##### ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Clean all rpt files
    for name, inp_path in scenarios.items():
        rpt_path = os.path.splitext(inp_path)[0] + '.rpt'
        if os.path.isfile(rpt_path):
            print(f"Cleaning report file: {rpt_path}")
            clean_rpt_encoding(rpt_path)

    # Find street node names
    model_path = scenarios['Base']
    model = swmmio.Model(model_path)
    node_ids = list_street_nodes(model)
    node_ids.remove('J509-S')  # exclude patterson park pond node - don't want to measure water level in pond

    # Change storm execution
    selected_storm = '6_27_23' # CHANGE to a storm name ALREADY in your inp
    storm_ts = storms[selected_storm]

    # Run simulations
    scenario_node_results = {}

    for scenario_name, inp_path in scenarios.items():
        print(f"Running scenario: {scenario_name} with storm {selected_storm}")

        tmp_inp = os.path.join(
            tempfile.gettempdir(),
            f'Inner_Harbor_Model_V24_{scenario_name}.inp')

        storm_timeseries(inp_path, storm_ts, tmp_inp)

        df_nodes = run_pyswmm(tmp_inp, node_ids)
        scenario_node_results[scenario_name] = df_nodes

    # Combine into multiindex dataframes
    processed_nodes_df = pd.concat(scenario_node_results, names=['scenario'])
    processed_nodes_df.index.set_names(['scenario', 'row'], inplace=True)

    # Save raw simulation outputs
    processed_nodes_df.to_csv(f"../outputdata/{selected_storm}_simV24_AllNodes.csv")

    # Run analysis directly on simulation results
    find_max_depth(processed_nodes_df, node_neighborhood, selected_storm)
    find_max_vol(processed_nodes_df, node_neighborhood, selected_storm)