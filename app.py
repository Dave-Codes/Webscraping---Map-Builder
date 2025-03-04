from adjustText import adjust_text
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import zipfile
import io
import matplotlib.pyplot as plt
import os
import geopandas
import requests
import time
import re
import contextily as cx
from shapely.geometry import Point, Polygon, MultiPolygon, box
from matplotlib.colors import ListedColormap
import matplotlib.colors as mcolors
import matplotlib.path as mpath
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.text as mpltext
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.legend import Legend
from matplotlib.legend_handler import HandlerTuple, HandlerLine2D
from matplotlib.figure import Figure
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from itables import init_notebook_mode, show, to_html_datatable, JavascriptCode
from webscrape import extract
from functions import set_dpi, data_transform, map_utilities, map_color_utils, centroids, build_map
from shapely.validation import make_valid
import shutil #Import shutil to delete folder.

url = 'https://data.fs.usda.gov/geodata/edw/datasets.php'
table_attribs = ['Feature Class', 'Description', 'ESRI GDB', 'Shapefile']

app = Flask(__name__)

# --- Global Variables ---
# Shapefile download location.
SHAPEFILE_DIR = os.path.join(app.root_path, 'temp_shapefiles')
if not os.path.exists(SHAPEFILE_DIR):
    os.makedirs(SHAPEFILE_DIR)

#Map image save location
MAP_IMAGE_PATH = os.path.join(app.static_folder, 'images', 'map.png')

# ------------------------


def get_df():
    df = extract(url, table_attribs)
    table_html = to_html_datatable(df, display_logo_when_loading=False, classes="display compact", max_width='400px',
                                   max_height='30px', \
                                   columnDefs=[
                                       {
                                           "targets": 2,
                                       }
                                   ],
                                   )
    return df, table_html


@app.route('/')
def index():
    df, table_html = get_df()
    # Create a list of dictionaries where each dictionary contains the dataset name and url
    dataset_choices = [{'name': row['Feature Class'], 'url': row['ESRI GDB']} for index, row in df.iterrows() if
                       not pd.isna(row['ESRI GDB'])]
    return render_template('index.html', table_html=table_html, dataset_choices=dataset_choices)

def download_and_extract_zip(url, extract_to=SHAPEFILE_DIR):
    """Downloads a zip file from a URL and extracts it to a specified directory.

    Args:
        url: The URL of the zip file.
        extract_to: The directory to extract the contents to (default is current directory).
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(extract_to)
        print(f"Successfully extracted to {extract_to}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except zipfile.BadZipFile as e:
         print(f"Zip file error: {e}. The URL might not point to a valid zip file.")
    except Exception as e:
        print(f"An error occurred: {e}")

def find_gdb(root_dir):
    gdb_path = ""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            if dirname.endswith(".gdb"):
                gdb_path = os.path.join(root_dir, dirname)
                print(gdb_path)
                return gdb_path  # Return immediately when the first .gdb is found
    return gdb_path

def map_utilities(state_row, gdb):
    #state_row.geometry = state_row.geometry.apply(lambda x: make_valid(x))
    
    clipping_box = state_row.geometry.to_crs(epsg=4269)

    clipped_dataset = geopandas.clip(gdb, clipping_box)
    clipped_dataset = clipped_dataset.to_crs(epsg=3857)
    
    return clipped_dataset


# Modified: Integrated actual map generation logic
def generate_map_with_progress(state_name, dataset_url):
    """Generates a map with progress updates, using build_map logic."""
    print(dataset_url)

    # --- Cleanup: Delete Old Files ---
    if os.path.exists(SHAPEFILE_DIR):
        shutil.rmtree(SHAPEFILE_DIR)  # Delete the entire directory and its contents
        os.makedirs(SHAPEFILE_DIR) #Recreate the directory
    if os.path.exists(MAP_IMAGE_PATH):
        os.remove(MAP_IMAGE_PATH)
    # -----------------------------------

    us_states_gdb = geopandas.read_file('tl_2012_us_state/tl_2012_us_state.shp')
    us_states_gdb = data_transform(us_states_gdb)
    set_dpi()
    dataset_url = re.findall(r'"(.*?)"', dataset_url)[0]
    print(dataset_url)
    # Check if the dataset_url is valid before reading it
    try:
        url = f"{dataset_url}"
        download_and_extract_zip(url, SHAPEFILE_DIR)
        gdb_file_path = find_gdb(SHAPEFILE_DIR)
        print(gdb_file_path)
        #response = requests.get(url)
        #data = response.json()
        #eco_provinces = pd.io.json.json_normalize(data['features'])
        #geom_column = eco_provinces
        gdb = geopandas.read_file(gdb_file_path)
        
    except Exception as e:
        print(f"Error reading dataset: {e}")
        yield "data: Error reading dataset \n\n"
        return

    #Validate the GeoDataFrame
    #gdb.geometry = gdb.geometry.apply(lambda x: make_valid(x))

    mpl.use('agg')  # Ensure non-interactive backend for server use
    

    state_name = state_name.title()

    # --- Step 1: Prepare State Data --- (Approx. 10% of total work)
    yield "data: 10\n\n"
    state_row = us_states_gdb[us_states_gdb.NAME == state_name]

    # --- Step 2: Clip Dataset --- (Approx. 20% of total work)
    yield "data: 20\n\n"
    # Use map_utilities to clip the user-selected dataset
    clipped_dataset = map_utilities(state_row, gdb)

    # --- Step 3: Calculate Colors --- (Approx. 10% of total work)
    yield "data: 30\n\n"
    dataset_colors = map_color_utils(clipped_dataset)

    # --- Step 4: Calculate Centroids --- (Approx. 10% of total work)
    yield "data: 40\n\n"
    centroids_gdf = centroids(clipped_dataset)

    # --- Step 5: Start Plotting --- (Approx. 10% of total work)
    yield "data: 50\n\n"
    fig, ax = plt.subplots(layout='tight', edgecolor=(0.3, 0.5, 0.4, 0.7), linewidth=2)

    # --- Step 6: Plot the selected Dataset --- (Approx. 15% of total work)
    yield "data: 65\n\n"
    # Use the new clipped dataset to plot instead of clipped_eco_provinces
    clipped_dataset.plot(ax=ax, color=clipped_dataset['colors'], legend=True,
                               legend_kwds={'loc': (0.0, 0.0), 'shadow': True}, alpha=0.6, edgecolor='black',
                               linewidth=0.5, figsize=(5, 7), zorder=1)
    cx.add_basemap(ax=ax, zoom=7)
    ax.set_axis_off()
    ax.set_title(label="{} Overlaid on {}".format(os.path.basename(gdb_file_path).split('.')[0], state_name), fontstyle='oblique', color='white',
                 path_effects=[pe.Stroke(linewidth=1.20, foreground='green'), pe.Normal()], fontsize=15,
                 position=(0.4, 1.3), va='baseline', pad=7, ha='left')

    # --- Step 7: Plot Centroids --- (Approx. 10% of total work)
    yield "data: 75\n\n"
    """centroids_gdf.apply(
        lambda x: ax.annotate(text=x['PROVINCE_ID'], bbox=dict(boxstyle='circle,pad=0.2', facecolor='black', alpha=0.85),
                              xy=(x.geometry.x, x.geometry.y), color='white', backgroundcolor=(0, 0, 0, 0.05),
                              ha='center', va='center', fontsize=6), axis=1)
"""
    # --- Step 8: Create Legend --- (Approx. 10% of total work)
    yield "data: 85\n\n"
    circle = mpath.Path.circle(center=(0, 0), radius=100)
    patches = []
    """for color, i in zip(dataset_colors, clipped_dataset.PROVINCE_ID.unique()):
        number = mpltext.TextPath(xy=(-2.5, -3.75), s="{}".format(i), size=6)
        color_patch = mpatches.Patch(facecolor=color, alpha=0.6, edgecolor='black', linewidth=0.2)
        line2 = Line2D([], [], ls='', color="#cef0d8", marker=number, alpha=0.6, markerfacecolor=color,
                       markeredgecolor='black', markersize=17, markeredgewidth=0.25)
        legend_tuple = tuple((color_patch, line2))
        patches.append(legend_tuple)"""

    """legend_labels = [re.sub('\d', '', re.sub('- ', '-\n', re.sub(' and ', ' &\n', re.sub(' Province', '', i)))).lstrip() for
                     i in clipped_dataset['LEG_LABELS']]"""
    edge_color = [(0.6, 0, 0, 1)]
    state_color = [(0.3, 0, 0, 0.0)]
    state_row.plot(ax=ax, edgecolors='black', color=state_color, linestyle='--')
    #patches.append(mpatches.Patch(facecolor=(0.0, 0.0, 0.0, 0.0), edgecolor='black', linestyle='--', joinstyle='round'))
    legend_labels = []
    legend_labels.append(state_name)

    plt.legend(handles=patches, labels=legend_labels, handler_map={tuple: HandlerTuple(ndivide=None)}, handletextpad=1,
               bbox_to_anchor=(1, 1, 0, 0), loc='upper left', handleheight=3, handlelength=4.5, labelspacing=1.1,
               fontsize='x-small', facecolor='#cef0d8', framealpha=0.20)
    ax.set_frame_on(True)
    fig.set_facecolor(((252 / 255), (244 / 255), (222 / 255), 0.3))
    """annotations = [child for child in ax.get_children() if isinstance(child, mpltext.Annotation)]
    adjust_text(annotations, avoid_self=False)
    ax.get_children()[2].set(fontsize=4, alpha=0.3)"""

    # --- Step 9: Save Figure --- (Approx. 5% of total work)
    yield "data: 90\n\n"
    # Save the plot to the 'static/images' directory
    static_img_dir = os.path.join(app.static_folder, 'images')
    if not os.path.exists(static_img_dir):
        os.makedirs(static_img_dir)

    map_filename = os.path.join(static_img_dir, 'map.png')
    fig.savefig(map_filename, bbox_inches='tight', dpi=300)  # added bbox_inches so that the figure saves properly.
    print(f"Map saved to: {map_filename}")

    # --- Step 10: Finalization --- (Approx. 10% of total work)
    yield "data: 100\n\n"
    plt.close(fig)

    return


@app.route('/map', methods=['GET', 'POST'])
def map_page():
    if request.method == 'POST':
        state_name = request.form.get('state_name')
        dataset_url = request.form.get('dataset_url')  # Get the selected dataset URL
        # Pass the state name variable to the generator function.
        return Response(generate_map_with_progress(state_name, dataset_url), mimetype='text/event-stream')

    # When the page is first loaded, render the map.html page.
    return render_template('map.html')


if __name__ == '__main__':
    app.run(debug=True)
