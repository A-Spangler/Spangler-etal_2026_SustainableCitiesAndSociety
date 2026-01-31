# By: Ava Spangler
# Date: 01/31/2026
# Description: This code takes in processed and analyzed data and creates visualizations
# from Spangler-etal_2026_SustainableCitiesandSociety

# IMPORTS --------------------------------------------------------------------------------------------------------------
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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

def volume_stackplot(relative_vol_df, name):
    fig, ax = plt.subplots(figsize=(10, 4))
    plot_cols = ['V', 'I', 'V&I']

    # X positions for each scenario
    x_positions = list(range(1, len(plot_cols) + 1))
    bar_width = 0.3
    bar_height = 0.65

    # plot only broadway east as color
    unique_neighborhoods = sorted(relative_depth_df['neighborhood'].unique())
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

# FIGURE 5 -------------------------------------------------------------------------------------------------------------
# write files for importing to GIS here

# EXECUTION ------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # load dfs
    relative_depth_df = pd.read_csv('../outputdata/0.5x_fullstorm_6_27_23_V23_AllNodes_RelativeDepth.csv').drop(['Unnamed: 0'],axis=1)
    relative_volume_df = pd.read_csv('../outputdata/0.5x_fullstorm_6_27_23_V23_AllNodes_RelativeVolume.csv').drop(['Unnamed: 0'], axis=1)

    storm_name = '0.5x_fullstorm_6_27_23'
    #execute, note 'relative' functions means the result is relative to base case
    depth_stackplot(relative_depth_df, storm_name)
    volume_stackplot(relative_volume_df, storm_name)

