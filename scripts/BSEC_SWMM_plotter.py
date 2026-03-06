# By: Ava Spangler
# Date: 01/31/2026
# Description: This code takes in processed and analyzed data and creates visualizations
# from Spangler-etal_2026_SustainableCitiesandSociety

# IMPORTS --------------------------------------------------------------------------------------------------------------
inport os
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scripts.config import scenarios, storms


# FIGURE 5 -------------------------------------------------------------------------------------------------------------
# Processes SWMM simulation output for GIS export.
def process_scenarios_to_gis(input_csv, coords_file, output_dir, base_scenario_name='Base'):

    # Set up output directories
    processed_dir = os.path.join(output_dir, 'GIS_exports')
    relative_dir = os.path.join(processed_dir, 'relative_depth')
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(relative_dir, exist_ok=True)

    # Load data
    df = pd.read_csv(input_csv, parse_dates=['timestamp'])
    coords = pd.read_excel(coords_file)
    coords['node_id'] = coords['node_id'].astype(float)

    depth_cols = [c for c in df.columns if c.endswith('_depth')]

    # clean node_id strings
    def clean_node_id(series):
        return (
            series
            .str.replace('_depth', '', regex=False)
            .str.replace(r'^J', '', regex=True)
            .str.replace(r'-S$', '', regex=True)
            .astype(float)
        )

    # Build base long-form df for relative depth calculations
    base_df = df[df['scenario'] == base_scenario_name].copy()
    if base_df.empty:
        raise ValueError(f"Base scenario '{base_scenario_name}' not found in CSV.")

    base_long = (
        base_df[['timestamp'] + depth_cols]
        .rename(columns={'timestamp': '24dt'})
        .melt(id_vars='24dt', var_name='node_id', value_name='depth_m_base')
    )
    base_long['node_id'] = clean_node_id(base_long['node_id'])

    # Process all scenarios
    for scenario, scen_df in df.groupby('scenario'):
        print(f'Formatting scenario: {scenario}')

        long_df = (
            scen_df[['timestamp'] + depth_cols]
            .copy()
            .rename(columns={'timestamp': '24dt'})
            .melt(id_vars='24dt', var_name='node_id', value_name='depth_m')
        )
        long_df['node_id'] = clean_node_id(long_df['node_id'])

        # Merge coordinates
        formatted = long_df.merge(coords, on='node_id', how='left')

        # Save per-scenario processed file
        out_file = os.path.join(processed_dir, f'{scenario}_results_processed.csv')
        formatted.to_csv(out_file, index=False, date_format='%Y-%m-%d %H:%M:%S')
        print(f'  → saved processed file: {out_file}')

        # Skip relative depth for base scenario
        if scenario == base_scenario_name:
            continue

        # Compute and save relative depth vs. base
        merged = formatted.merge(base_long, on=['24dt', 'node_id'], how='left')
        merged['relative_depth_m'] = merged['depth_m'] - merged['depth_m_base']
        merged = merged[['24dt', 'node_id', 'depth_m', 'depth_m_base', 'relative_depth_m', 'x', 'y']]

        relative_file = os.path.join(relative_dir, f'{scenario}_relative_depth.csv')
        merged.to_csv(relative_file, index=False, date_format='%Y-%m-%d %H:%M:%S')
        print(f'  → saved relative depth file: {relative_file}')

    print(f'\nDone. Outputs saved to: {processed_dir}')






# FIGURE 6 ----------------------------------------------------------------------------------------------------------
def depth_stackplot(relative_depth_df, name):
    fig, ax = plt.subplots(figsize=(10, 4))
    plot_cols = ['V', 'I', 'V&I']

    # X positions for each scenario
    x_positions = list(range(1, len(plot_cols) + 1))
    bar_width = 0.3
    bar_height = 0.0025

    # plot only broadway east as color
    unique_neighborhoods = sorted(relative_depth_df['neighborhood'].unique())
    num_neigh = len(unique_neighborhoods)
    colors = ['mediumpurple' if n == 'Broadway East' or n == 'Dunbar-Broadway' or n == 'Eager Park' else 'lightgrey' for
              n in unique_neighborhoods]

    for idx, scenario in enumerate(plot_cols):
        depth_changes = relative_depth_df[scenario]
        neighborhoods = relative_depth_df['neighborhood']

        # Plot each change value as a horizontal stripe
        for depth, neigh in zip(depth_changes, neighborhoods):
            # Determine color for this specific neighborhood
            color = 'mediumpurple' if neigh in ['Broadway East', 'Dunbar-Broadway', 'Eager Park'] else 'lightgrey'

            rect = plt.Rectangle((x_positions[idx] - bar_width / 2, depth - bar_height / 2),
                                 bar_width, bar_height,
                                 facecolor=color, alpha=0.5, linewidth=1)
            ax.add_patch(rect)

    # Add a horizontal line at y=0 for reference
    ax.axhline(y=0, color='grey', linestyle='dotted', linewidth=1, alpha=0.5, label='No change')

    # labels
    ax.set_xlabel('Scenario')
    ax.set_ylabel('change in depth (m)')
    ax.set_ylim(-0.15,0.05)
    ax.set_title(f'{name} Storm: Depth of Flooding')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(plot_cols)
    ax.set_xlim(0.5, len(plot_cols) + 0.5)

    plt.tight_layout()
    #plt.show()
    save_path = f'../figures/{name}_relative_stackplot_depth_V23.png'
    plt.savefig(save_path)
    

# Fig 6 supplementary version
def volume_stackplot(relative_vol_df, name):
    fig, ax = plt.subplots(figsize=(10, 4))
    plot_cols = ['V', 'I', 'V&I']

    # X positions for each scenario
    x_positions = list(range(1, len(plot_cols) + 1))
    bar_width = 0.3
    bar_height = 0.65

    # plot only broadway east as color
    unique_neighborhoods = sorted(relative_vol_df['neighborhood'].unique())
    num_neigh = len(unique_neighborhoods)
    colors = ['mediumpurple' if n == 'Broadway East' or n == 'Dunbar-Broadway' or n == 'Eager Park' else 'lightgrey' for
              n in unique_neighborhoods]

    for idx, scenario in enumerate(plot_cols):
        vol_changes = relative_volume_df[scenario]
        neighborhoods = relative_volume_df['neighborhood']

        # Plot each change value as a horizontal stripe
        for vol, neigh in zip(vol_changes, neighborhoods):
            # Determine color for this specific neighborhood
            color = 'yellowgreen' if neigh in ['Broadway East', 'Dunbar-Broadway', 'Eager Park'] else 'lightgrey'

            rect = plt.Rectangle((x_positions[idx] - bar_width / 2, vol - bar_height / 2),
                                 bar_width, bar_height,
                                 facecolor=color, alpha=0.5, linewidth=1)
            ax.add_patch(rect)

    # Add a horizontal line at y=0 for reference
    ax.axhline(y=0, color='grey', linestyle='dotted', linewidth=1, alpha=0.5, label='No change')

    # Customize the plot
    ax.set_xlabel('Scenario')
    ax.set_ylabel('change in volume (m\u00b3)')
    ax.set_ylim(-40,10)
    ax.set_title(f'{name} Storm: volume of flooding')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(plot_cols)
    ax.set_xlim(0.5, len(plot_cols) + 0.5)

    plt.tight_layout()
    #plt.show()
    save_path = f'../figures/{name}_relative_stackplot_volume_V23.png'
    plt.savefig(save_path)






# EXECUTION ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    for selected_storm in storms.keys():
        process_scenarios_to_gis(
            input_csv=f'../processed/nodes/{selected_storm}_simV23_AllNodes.csv',
            coords_file='../inputdata/Node_Coords.xlsx',
            output_dir='../figures')

        relative_depth_df = pd.read_csv(
            f'../outputdata/{selected_storm}_V23_AllNodes_RelativeDepth.csv').drop(columns=['Unnamed: 0'], errors='ignore')

        relative_volume_df = pd.read_csv(
            f'../outputdata/{selected_storm}_V23_AllNodes_RelativeVolume.csv').drop(columns=['Unnamed: 0'], errors='ignore')

        depth_stackplot(relative_depth_df, selected_storm)
        volume_stackplot(relative_volume_df, selected_storm)

