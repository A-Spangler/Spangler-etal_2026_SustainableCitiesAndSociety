# By: Ava Spangler
# Date: 8/12/2025
# Description: This script runs SWMM simulations using pyswmm, processes the results into dataframes,
# and analyzes them — all in a single execution. Results from the simulation are passed directly
# into the analysis functions without intermediate CSV loading.
# To simulate different storm conditions, update selected_storm in the EXECUTION block.

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

    # Transform: Scenarios become columns, Nodes become rows
    max_depth_df = max_depth_df.reset_index()
    max_depth_df = max_depth_df.set_index('scenario').T
    max_depth_df = max_depth_df.reset_index().rename(columns={'index': 'node_name'})
    max_depth_df = max_depth_df.reset_index(drop=True)

    # 2. Add Metadata
    max_depth_df['node_id'] = max_depth_df['node_name'].str.extract(r'([^_]+)')[0]
    max_depth_df['neighborhood'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_depth_df['historic_stream'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][1])

    # 3. DYNAMIC COLUMN IDENTIFICATION
    metadata_cols = ['node_name', 'node_id', 'neighborhood', 'historic_stream']
    scenario_names = [col for col in max_depth_df.columns if col not in metadata_cols]

    # 4. Scenario Summary (Absolute Maxes) — all scenarios including Base
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

    # 5. Relative Change (Scenario - Base)
    relative_change_in_depth = max_depth_df[scenario_names].copy()

    if 'Base' in relative_change_in_depth.columns:
        relative_change_in_depth = relative_change_in_depth.sub(max_depth_df['Base'], axis=0)
    else:
        print("Warning: 'Base' scenario not found. Relative changes will be scenario values.")

    for col in metadata_cols:
        relative_change_in_depth[col] = max_depth_df[col]

    # 6. Relative Summary — exclude Base (Base - Base = 0 everywhere, metrics are meaningless)
    non_base_scenarios = [s for s in scenario_names if s != 'Base']

    print("Scenarios in relative_change_in_depth:", relative_change_in_depth.columns.tolist())
    print("Non-base scenarios:", non_base_scenarios)

    for scenario in non_base_scenarios:
        print(f"\n--- {scenario} ---")
        print("dtype:", relative_change_in_depth[scenario].dtype)
        print("non-zero count:", (relative_change_in_depth[scenario] != 0).sum())
        print("abs max value:", relative_change_in_depth[scenario].abs().max())
        print("abs max index:", relative_change_in_depth[scenario].abs().idxmax())
        print("node at that index:",
              relative_change_in_depth.loc[relative_change_in_depth[scenario].abs().idxmax(), 'node_name'])
        print(relative_change_in_depth[scenario].abs().nlargest(5))

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
            'avg_peak_change_m': avg_change,
            'peak_abs_change_m': max_val,
            'peak_abs_change_node': max_node,
            'base_depth_abs_m': base_depth_abs,
            'pct_change_abs': pct_change_abs,
            'peak_increase_m': incr,
            'peak_increase_node': incr_node,
            'base_depth_incr_m': base_depth_incr,
            'pct_change_incr': pct_change_incr,
        })
    rel_depth_summary = pd.DataFrame(rel_depth_rows)

    # 7. Save Files
    output_dir = f'../outputdata'
    os.makedirs(output_dir, exist_ok=True)

    max_depth_df.to_csv(f'{output_dir}{storm_name}_V24_AllNodes_MaxDepth.csv', index=False)
    relative_change_in_depth.to_csv(f'{output_dir}{storm_name}_V24_AllNodes_RelativeDepth.csv', index=False)
    peak_depth_summary.merge(avg_depth_summary, on='scenario').to_csv(
        f'{output_dir}{storm_name}_V24_AllNodes_DepthSummary.csv', index=False)
    rel_depth_summary.to_csv(f'{output_dir}{storm_name}_V24_AllNodes_RelativeDepthSummary.csv', index=False)

    return max_depth_df, relative_change_in_depth

def find_max_flow(processed_df, node_neighborhood_df, storm_name):
    grouped_df = processed_df.groupby(level=0).max()

    flow_cols = [col for col in grouped_df.columns if col.endswith('_flow')]
    max_flow_df = grouped_df[flow_cols]

    max_flow_df = max_flow_df.reset_index()
    max_flow_df = max_flow_df.set_index('scenario').T
    max_flow_df = max_flow_df.reset_index().rename(columns={'index': 'node_name'})
    max_flow_df['node_id'] = max_flow_df['node_name'].str.extract(r'([^_]+)')[0]
    max_flow_df['neighborhood'] = max_flow_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_flow_df['historic_stream'] = max_flow_df['node_id'].map(lambda x: node_neighborhood[x][1])

    relative_change_in_flow = max_flow_df.iloc[:, 1:5].copy() #TODO fix hardcoding in the column indices for subtraction, changes w scenarios
    relative_change_in_flow = relative_change_in_flow.sub(max_flow_df['Base'], axis = 0)
    relative_change_in_flow['node_name'] = max_flow_df['node_name']
    relative_change_in_flow['node_id'] = max_flow_df['node_id']
    relative_change_in_flow['neighborhood'] = max_flow_df['neighborhood']

    savepath1 = f'../outputdata/{storm_name}_V24_AllNodes_MaxFlow.csv'
    savepath2 = f'../outputdata/{storm_name}_V24_AllNodes_RelativeFlow.csv'
    max_flow_df.to_csv(savepath1)
    relative_change_in_flow.to_csv(savepath2)
    return max_flow_df, relative_change_in_flow

def find_max_vol(processed_df, node_neighborhood_df, storm_name):
    grouped_df = processed_df.groupby(level=0).max()

    vol_cols = [col for col in grouped_df.columns if col.endswith('_volume')]
    max_vol_df = grouped_df[vol_cols]

    max_vol_df = max_vol_df.reset_index()
    max_vol_df = max_vol_df.set_index('scenario').T
    max_vol_df = max_vol_df.reset_index().rename(columns={'index': 'node_name'})
    max_vol_df['node_id'] = max_vol_df['node_name'].str.extract(r'([^_]+)')[0]
    max_vol_df['neighborhood'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_vol_df['historic_stream'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][1])

    peak_vol_rows = []
    for scenario in max_vol_df.columns[1:-3]:
        max_val = max_vol_df[scenario].max()
        max_node = max_vol_df.loc[max_vol_df[scenario].idxmax(), 'node_name']
        peak_vol_rows.append({'scenario': scenario, 'node_name': max_node, 'peak_vol_m3': max_val})
    peak_vol_summary = pd.DataFrame(peak_vol_rows)

    avg_vol_rows = []
    for scenario in max_vol_df.columns[1:-3]:
        avg_val = max_vol_df[scenario].mean()
        avg_vol_rows.append({'scenario': scenario, 'avg_vol_m3': avg_val})
    avg_vol_summary = pd.DataFrame(avg_vol_rows)

    relative_change_in_vol = max_vol_df.iloc[:, 1:5].copy() #TODO fix hardcoding in the column indices for subtraction, changes w scenarios
    relative_change_in_vol = relative_change_in_vol.sub(max_vol_df['Base'], axis = 0)
    relative_change_in_vol['node_name'] = max_vol_df['node_name']
    relative_change_in_vol['node_id'] = max_vol_df['node_id']
    relative_change_in_vol['neighborhood'] = max_vol_df['neighborhood']

    rel_vol_rows = []
    for scenario in relative_change_in_vol.columns[0:-3]:
        incr = relative_change_in_vol[scenario].max()
        incr_idx = relative_change_in_vol[scenario].idxmax()
        incr_node = relative_change_in_vol.loc[incr_idx, 'node_name']

        base_depth_incr = max_vol_df.loc[incr_idx, 'Base']
        pct_change_incr = (incr / base_depth_incr * 100) if base_depth_incr > 0 else float('inf')

        abs_vals = relative_change_in_vol[scenario].abs()
        idx_abs_max = abs_vals.idxmax()
        max_val = relative_change_in_vol.loc[idx_abs_max, scenario]
        max_node = relative_change_in_vol.loc[idx_abs_max, 'node_name']

        base_vol_abs = max_vol_df.loc[idx_abs_max, 'Base']
        pct_change_abs = (max_val / base_vol_abs * 100) if base_vol_abs > 0 else float('inf')

        avg_change_vol = relative_change_in_vol[scenario].mean()

        rel_vol_rows.append({
            'scenario': scenario,
            'avg_peak_change_m3': avg_change_vol,
            'peak_abs_vol_change_m3': max_val, 'peak_abs_change_node': max_node,
            'base_vol_abs_m3': base_vol_abs, 'pct_change_abs': pct_change_abs,
            'peak_vol_increase_m3': incr, 'peak_increase_node': incr_node,
            'base_vol_incr_m3': base_depth_incr, 'pct_change_incr': pct_change_incr,
        })
    rel_vol_summary = pd.DataFrame(rel_vol_rows)

    savepath1 = f'../outputdata/{storm_name}_V24_AllNodes_MaxVolume.csv'
    savepath2 = f'../outputdata/{storm_name}_V24_AllNodes_RelativeVolume.csv'
    savepath3 = f'../outputdata/{storm_name}_V24_AllNodes_VolSummary.csv'
    savepath4 = f'../outputdata/{storm_name}_V24_AllNodes_RelativeVolSummary.csv'
    max_vol_df.to_csv(savepath1)
    relative_change_in_vol.to_csv(savepath2)
    peak_vol_summary.merge(avg_vol_summary, on='scenario').to_csv(savepath3, index=False)
    rel_vol_summary.to_csv(savepath4, index=False)
    return max_vol_df, relative_change_in_vol

def find_flood_duration(processed_df, node_neighborhood, storm_name, depth_threshold=0.05):
    df = processed_df.reset_index()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    depth_cols = [col for col in df.columns if col.endswith('_depth')]

    first_timesteps = df.groupby('scenario').apply(lambda s: s.sort_values('timestamp').iloc[0])
    nodes_above_at_start = set()
    for depth_col in depth_cols:
        if (first_timesteps[depth_col] > depth_threshold).any():
            nodes_above_at_start.add(depth_col)
    depth_cols = [col for col in depth_cols if col not in nodes_above_at_start]

    duration_rows = []
    for scenario, scenario_df in df.groupby('scenario'):
        scenario_df = scenario_df.sort_values('timestamp').reset_index(drop=True)

        for depth_col in depth_cols:
            node_id = depth_col.replace('_depth', '')

            flooded_timestamps = scenario_df.loc[scenario_df[depth_col] > depth_threshold, 'timestamp']

            if flooded_timestamps.empty:
                flood_duration_min = 0.0
            else:
                flood_duration_min = flooded_timestamps.diff().dropna().dt.total_seconds().sum() / 60

            duration_rows.append({'scenario': scenario, 'node_id': node_id, 'flood_duration_min': flood_duration_min})

    flood_duration_df = pd.DataFrame(duration_rows)

    flood_duration_wide = flood_duration_df.pivot(index='node_id', columns='scenario',
                                                  values='flood_duration_min').reset_index()
    flood_duration_wide.columns.name = None
    flood_duration_wide['neighborhood'] = flood_duration_wide['node_id'].map(lambda x: node_neighborhood[x][0])
    flood_duration_wide['historic_stream'] = flood_duration_wide['node_id'].map(lambda x: node_neighborhood[x][1])

    non_base_scenarios = [col for col in flood_duration_wide.columns if
                          col not in ('node_id', 'neighborhood', 'historic_stream', 'Base')]
    peak_reduction_rows = []
    avg_reduction_rows = []
    for scenario in non_base_scenarios:
        reduction = flood_duration_wide['Base'] - flood_duration_wide[scenario]
        max_val = reduction.max()
        max_node = flood_duration_wide.loc[reduction.idxmax(), 'node_id']
        peak_reduction_rows.append(
            {'scenario': scenario, 'node_name': max_node, 'peak_duration_reduction_min': max_val})
        avg_reduction_rows.append({'scenario': scenario, 'avg_duration_reduction_min': reduction.mean()})
    avg_reduction_summary = pd.DataFrame(peak_reduction_rows).merge(pd.DataFrame(avg_reduction_rows), on='scenario')

    savepath1 = f'../outputdata/{storm_name}_V24_AllNodes_FloodDuration.csv'
    savepath2 = f'../outputdata/{storm_name}_V24_AllNodes_AvgFloodDurationReduction.csv'
    flood_duration_wide.to_csv(savepath1, index=False)
    avg_reduction_summary.to_csv(savepath2, index=False)
    return flood_duration_wide, avg_reduction_summary


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
    node_ids.remove('J509-S')  # exclude unwanted (patterson park) node

    # Change storm execution
    selected_storm = '6_27_23'
    storm_ts = storms[selected_storm]

    # Run simulations
    scenario_node_results = {}

    for scenario_name, inp_path in scenarios.items():
        print(f"Running scenario: {scenario_name} with storm {selected_storm}")

        tmp_inp = os.path.join(
            tempfile.gettempdir(),
            f'Inner_Harbor_Model_V23_{scenario_name}.inp')

        storm_timeseries(inp_path, storm_ts, tmp_inp)

        df_nodes = run_pyswmm(tmp_inp, node_ids)
        scenario_node_results[scenario_name] = df_nodes

    # Combine into multiindex dataframes
    processed_nodes_df = pd.concat(scenario_node_results, names=['scenario'])
    processed_nodes_df.index.set_names(['scenario', 'row'], inplace=True)

    # Save raw simulation outputs
    processed_nodes_df.to_csv(f'../outputdata/{selected_storm}_simV24_AllNodes.csv')

    # Run analysis directly on simulation results
    find_max_depth(processed_nodes_df, node_neighborhood, selected_storm)
    #find_max_flow(processed_nodes_df, node_neighborhood, selected_storm)
    find_max_vol(processed_nodes_df, node_neighborhood, selected_storm)
    find_flood_duration(processed_nodes_df, node_neighborhood, selected_storm)
