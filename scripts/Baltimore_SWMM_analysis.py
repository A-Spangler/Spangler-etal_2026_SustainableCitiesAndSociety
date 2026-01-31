# By: Ava Spangler
# Date: 01/31/2026
# Description: This code is from Spangler-etal_2026_SustainableCitiesandSociety
# this script executes 1 run of the Baltimore SWMM model using pyswmm.
# then processes and stores the results in a dataframe

# to simulate different storm conditions, SWMM .inp must be updated with storm data and name

# IMPORTS --------------------------------------------------------------------------------------------------------------
import os
import pandas as pd
import swmmio
import pyswmm
import datetime as dt
from pyswmm import Simulation, Nodes, Subcatchments, LidControls, LidGroups
from scripts.config import scenarios, storms
from scripts.utils import clean_rpt_encoding, storm_timeseries
import tempfile

# DEFINITIONS ----------------------------------------------------------------------------------------------------------
# Initialize dictionaries for storing data from each node in each scenario
# function to run pyswmm and save outputs as dict
cfs_to_cms = (12**3)*(2.54**3)*(1/(100**3))
ft_to_m = 12*2.54*(1/100)
inchperhour_to_cmpersec = (2.54)*(1/3600)

def list_street_nodes(model): #separate out above ground storage nodes from below ground junctions
    nodes_df = model.nodes.dataframe
    nodes_df = nodes_df.reset_index()
    node_names = nodes_df['Name'].tolist()
    street_node_names = [k for k in node_names if '-S' in k]
    return street_node_names

# TODO: restructure so separate Dfs come out for depth and flow, not combined df

def run_pyswmm(inp_path, node_ids):
    output_nodes = {node: {'depth': [], 'flow': [], 'volume': []} for node in node_ids}

# run inp_path simulation, instantiate BE nodes
    time_stamps = []
    with Simulation(inp_path) as sim:
        nodes = {node_id: Nodes(sim)[node_id] for node_id in node_ids} #dictionary with nodes
        sim.step_advance(300) #lets python access sim during run (300 sec = 5min inetervals)

        # Launch inp_path simulation
        for step in enumerate(sim):
            time_stamps.append(sim.current_time)
            for node_id, node in nodes.items(): # store node flow and depth data in node dictionary
                output_nodes[node_id]['depth'].append(node.depth*ft_to_m) # ft to m
                output_nodes[node_id]['flow'].append(node.total_inflow*cfs_to_cms) #m**3/s
                output_nodes[node_id]['volume'].append(node.volume * cfs_to_cms) #m**3

        # construct df
        node_data = {'timestamp': time_stamps} #dictionary of timestamps
        for node_id in node_ids:
            node_data[f'{node_id}_depth'] = output_nodes[node_id]['depth']
            node_data[f'{node_id}_flow'] = output_nodes[node_id]['flow']
            node_data[f'{node_id}_volume'] = output_nodes[node_id]['volume']

        df_node_data = pd.DataFrame(node_data).copy()
        return df_node_data


# define node neighborhood tuple
node_neighborhood_df = pd.read_excel(
        'r../inputdata/Node_Neighborhoods.xlsx')
node_neighborhood = dict(zip(node_neighborhood_df['street_node_id'],zip(node_neighborhood_df['neighborhood'], node_neighborhood_df['historic_stream'])))

def find_max_depth(processed_df, node_neighborhood, storm_name):
    # find maxes for each node depth across entire runtime, for each scenario
    grouped_df = processed_df.groupby(level=0).max()

    # select depth cols
    depth_cols = [col for col in grouped_df.columns if col.endswith('_depth')]
    max_depth_df = grouped_df[depth_cols]

    # make scenarios into column headers
    max_depth_df = max_depth_df.reset_index()
    max_depth_df = max_depth_df.set_index('scenario').T
    max_depth_df = max_depth_df.reset_index().rename(columns={'index': 'node_name'})
    max_depth_df = max_depth_df.reset_index(drop = True)
    # assign neighborhoods to node name by extracting node name and mapping dict
    max_depth_df['node_id'] = max_depth_df['node_name'].str.extract(r'([^_]+)')[0] # extract all ccharacters before the underscore (drop _depth)
    max_depth_df['neighborhood'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_depth_df['historic_stream'] = max_depth_df['node_id'].map(lambda x: node_neighborhood[x][1])

    #determine and print peak change in flood depth
    print("\nPeak Depths by Scenario:")
    for scenario in max_depth_df.columns[1:-3]:  # Skip node naming cols
        max_val = max_depth_df[scenario].max() # find the deepest 1 node reached
        max_node = max_depth_df.loc[max_depth_df[scenario].idxmax(), 'node_name'] #name of node
        print(f"Scenario: {scenario}, Node: {max_node}, Peak Depth: {max_val:.3f} m")

    # determine and print avg change in flood depth
    print("\nAverage Depths by Scenario:")
    for scenario in max_depth_df.columns[1:-3]:
        avg_val = max_depth_df[scenario].mean() # average for all nodes, max depth of all timesteps
        print(f"Scenario: {scenario}, Average Depth: {avg_val:.3f} m")

    # define new df showing relative change from base case
    # drop node names and neighborhoods for subtraction, then add back in
    relative_change_in_depth = max_depth_df.iloc[:, 1:5].copy() # TODO: fix hardcoding in the column indicies, changes 2 + number of scenarios processed
    relative_change_in_depth = relative_change_in_depth.sub(max_depth_df['Base'], axis = 0)
    relative_change_in_depth['node_name'] = max_depth_df['node_name']
    relative_change_in_depth['node_id'] = max_depth_df['node_id']
    relative_change_in_depth['neighborhood'] = max_depth_df['neighborhood']
    relative_change_in_depth['historic_stream'] = max_depth_df['historic_stream']

    #determine and print peak change in flood depth
    print("\nPeak Relative Change by Scenario:")
    for scenario in relative_change_in_depth.columns[0:-4]:
        # Find peak increase
        incr = relative_change_in_depth[scenario].max()
        incr_idx = relative_change_in_depth[scenario].idxmax()
        incr_node = relative_change_in_depth.loc[incr_idx, 'node_name']

        # Find base depth at that node for percentage calculation
        base_depth_incr = max_depth_df.loc[incr_idx, 'Base']
        pct_change_incr = (incr / base_depth_incr * 100) if base_depth_incr > 0 else float('inf')

        # Find peak absolute change
        abs_vals = relative_change_in_depth[scenario].abs()
        idx_abs_max = abs_vals.idxmax()
        max_val = relative_change_in_depth.loc[idx_abs_max, scenario]
        max_node = relative_change_in_depth.loc[idx_abs_max, 'node_name']

        # Find base depth for peak absolute change node
        base_depth_abs = max_depth_df.loc[idx_abs_max, 'Base']
        pct_change_abs = (max_val / base_depth_abs * 100) if base_depth_abs > 0 else float('inf')

        print(f"Scenario: {scenario}")
        print(f"  Peak Absolute Change: {max_val:.3f} m at {max_node} (Base: {base_depth_abs:.3f} m, Change: {pct_change_abs:.1f}%)")
        print(f"  Peak Increase: {incr:.3f} m at {incr_node} (Base: {base_depth_incr:.3f} m, Change: {pct_change_incr:.1f}%)")

    savepath1 = f'../outputdata{storm_name}_V23_AllNodes_MaxDepth.csv'
    savepath2 = f'../outputdata/{storm_name}_V23_AllNodes_RelativeDepth.csv'
    max_depth_df.to_csv(savepath1)
    relative_change_in_depth.to_csv(savepath2)
    return max_depth_df, relative_change_in_depth  # relative means relative to base case

def find_max_flow(processed_df, node_neighborhood_df, storm_name):
    # find maxes for each node flowrate depth, each scenario
    grouped_df = processed_df.groupby(level=0).max()

    # select flow cols
    flow_cols = [col for col in grouped_df.columns if col.endswith('_flow')]
    max_flow_df = grouped_df[flow_cols]

    # make scenarios be column headers, keep node names
    max_flow_df = max_flow_df.reset_index()
    max_flow_df = max_flow_df.set_index('scenario').T
    max_flow_df = max_flow_df.reset_index().rename(columns={'index': 'node_name'})
    # assign neighborhoods to node name by extracting node name and mapping dict
    max_flow_df['node_id'] = max_flow_df['node_name'].str.extract(r'([^_]+)')[0] # extract all characters before the underscore to drop _flow
    max_flow_df['neighborhood'] = max_flow_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_flow_df['historic_stream'] = max_flow_df['node_id'].map(lambda x: node_neighborhood[x][1])

    # define new df showing relative change from base case
    # drop node names for subtraction, then add back in
    relative_change_in_flow = max_flow_df.iloc[:, 1:5].copy() #TODO fix harcoding in the column indicies for subtraction, changes w scenarios
    relative_change_in_flow = relative_change_in_flow.sub(max_flow_df['Base'], axis = 0)
    relative_change_in_flow['node_name'] = max_flow_df['node_name']
    relative_change_in_flow['node_id'] = max_flow_df['node_id']
    relative_change_in_flow['neighborhood'] = max_flow_df['neighborhood']

    savepath1 = f'../outputdata/{storm_name}_V23_AllNodes_MaxFlow.csv'
    savepath2 = f'../outputdata/{storm_name}_V23_AllNodes_RelativeFlow.csv'
    max_flow_df.to_csv(savepath1)
    relative_change_in_flow.to_csv(savepath2)
    return max_flow_df, relative_change_in_flow  # relative means relative to base case

def find_max_vol(processed_df, node_neighborhood_df, storm_name):
    # find maxes for each node flowrate depth, each scenario
    grouped_df = processed_df.groupby(level=0).max()

    # select flow cols
    vol_cols = [col for col in grouped_df.columns if col.endswith('_volume')]
    max_vol_df = grouped_df[vol_cols]

    # make scenarios be column headers, keep node names
    max_vol_df = max_vol_df.reset_index()
    max_vol_df = max_vol_df.set_index('scenario').T
    max_vol_df = max_vol_df.reset_index().rename(columns={'index': 'node_name'})
    # assign neighborhoods to node name by extracting node name and mapping dict
    max_vol_df['node_id'] = max_vol_df['node_name'].str.extract(r'([^_]+)')[0] # extract all characters before the underscore drop _vol
    max_vol_df['neighborhood'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][0])
    max_vol_df['historic_stream'] = max_vol_df['node_id'].map(lambda x: node_neighborhood[x][1])

    # determine and print peak change in flood depth
    print("\nPeak Vol by Scenario:")
    for scenario in max_vol_df.columns[1:-3]:
        max_val = max_vol_df[scenario].max()
        max_node = max_vol_df.loc[max_vol_df[scenario].idxmax(), 'node_name']
        print(f"Scenario: {scenario}, Node: {max_node}, Peak Vol: {max_val:.3f} m^3")

    # determine and print avg change in flood depth
    print("\nAverage Vol by Scenario:")
    for scenario in max_vol_df.columns[1:-3]:
        avg_val = max_vol_df[scenario].mean()
        print(f"Scenario: {scenario}, Average Vol: {avg_val:.3f} m^3")

    # define new df showing relative change from base case
    # drop node names for subtraction, then add back in
    relative_change_in_vol = max_vol_df.iloc[:, 1:5].copy() #TODO fix harcoding in the column indicies for subtraction, changes w scenarios
    relative_change_in_vol = relative_change_in_vol.sub(max_vol_df['Base'], axis = 0)
    relative_change_in_vol['node_name'] = max_vol_df['node_name']
    relative_change_in_vol['node_id'] = max_vol_df['node_id']
    relative_change_in_vol['neighborhood'] = max_vol_df['neighborhood']

    # determine peak change in flood depth
    print("\nPeak Relative Vol Change by Scenario:")
    for scenario in relative_change_in_vol.columns[0:-3]:
        # Find peak increase
        incr = relative_change_in_vol[scenario].max()
        incr_idx = relative_change_in_vol[scenario].idxmax()
        incr_node = relative_change_in_vol.loc[incr_idx, 'node_name']

        # Find base depth at that node for percentage calculation
        base_depth_incr = max_vol_df.loc[incr_idx, 'Base']
        pct_change_incr = (incr / base_depth_incr * 100) if base_depth_incr > 0 else float('inf')

        # Find peak absolute change
        abs_vals = relative_change_in_vol[scenario].abs()
        idx_abs_max = abs_vals.idxmax()
        max_val = relative_change_in_vol.loc[idx_abs_max, scenario]
        max_node = relative_change_in_vol.loc[idx_abs_max, 'node_name']

        # Find base depth for peak absolute change node
        base_vol_abs = max_vol_df.loc[idx_abs_max, 'Base']
        pct_change_abs = (max_val / base_vol_abs * 100) if base_vol_abs > 0 else float('inf')

        print(f"Scenario: {scenario}")
        print(f"  Peak Absolute Vol Change: {max_val:.3f} m^3 at {max_node} (Base: {base_vol_abs:.3f} m^3, Change: {pct_change_abs:.1f}%)")
        print(f"  Peak Vol Increase: {incr:.3f} m^3 at {incr_node} (Base: {base_depth_incr:.3f} m^3, Change: {pct_change_incr:.1f}%)")

    savepath1 = f'../outputdata/{storm_name}_V23_AllNodes_MaxVolume.csv'
    savepath2 = f'../outputdata/{storm_name}_V23_AllNodes_RelativeVolume.csv'
    max_vol_df.to_csv(savepath1)
    relative_change_in_vol.to_csv(savepath2)
    return max_vol_df, relative_change_in_vol  # relative means relative to base case

# EXECUTION ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    #clean all rpt files
    for name, inp_path in scenarios.items():
        rpt_path = os.path.splitext(inp_path)[0] + '.rpt'
        if os.path.isfile(rpt_path):
            print(f"Cleaning report file: {rpt_path}")
            clean_rpt_encoding(rpt_path)

    #find street node names
    model_path = scenarios['Base']
    model = swmmio.Model(model_path)
    node_ids = list_street_nodes(model)
    node_ids.remove('J509-S')  # exclude unwanted (patterson park) node

    # run simulations
    scenario_node_results = {}

    # change named storm being simulated
    selected_storm = '6_27_23'
    storm_ts = storms[selected_storm]

    for scenario_name, inp_path in scenarios.items():
        print(f"Running scenario: {scenario_name} with storm {selected_storm}")

        # Create temp inp file
        tmp_inp = os.path.join(
            tempfile.gettempdir(),
            f'{scenario_name}_{selected_storm}.inp')

        # Swap storm
        storm_timeseries(inp_path, storm_ts, tmp_inp)

        df_nodes = run_pyswmm(tmp_inp, node_ids)
        scenario_node_results[scenario_name] = df_nodes

    # SAVE AND EXPORT ------------------------------------------------------------------------------------------------------
    # NOTE: name files according to storm condition being simulated in SWMM interface
    # combine and save nodes as a multiindex df
    processed_nodes_df = pd.concat(scenario_node_results, names=['scenario'])
    processed_nodes_df.index.set_names(['scenario', 'row'], inplace=True)
    processed_nodes_df.to_csv(f'../outputdata/{selected_storm}_simV23_AllNodes.csv')

# DATA ANLYSIS ----------------------------------------------------------------------------------------------------------

# EXECUTION ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    #load processed data
    processed_df = pd.read_csv('../outputdata/6_27_23_simV23_AllNodes.csv', index_col=[0, 1])

    storm_name = '6_27_23'

    #execute find max fxns
    find_max_depth(processed_df, node_neighborhood, storm_name)
    find_max_flow(processed_df, node_neighborhood, storm_name)
    find_max_vol(processed_df, node_neighborhood, storm_name)


