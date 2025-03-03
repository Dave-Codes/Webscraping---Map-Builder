from adjustText import adjust_text
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import geopandas
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

url = 'https://data.fs.usda.gov/geodata/edw/datasets.php'
table_attribs = ['Feature Class', 'Description', 'ESRI GDB', 'Shapefile']

app = Flask(__name__)

# --- Global Variables ---

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
    return table_html


@app.route('/')
def index():
    table_html = get_df()
    return render_template('index.html', table_html=table_html)

# Modified: Integrated actual map generation logic
def generate_map_with_progress(state_name):
    """Generates a map with progress updates, using build_map logic."""
    us_states_gdb = geopandas.read_file('tl_2012_us_state/tl_2012_us_state.shp')
    eco_provinces = geopandas.read_file("S_USA.EcoMapProvinces.gdb")
    us_states_gdb = data_transform(us_states_gdb)

    if not eco_provinces.geometry.is_valid.all():
        print("Error: eco_provinces contains invalid geometries.")
        eco_provinces.geometry = eco_provinces.geometry.apply(lambda x: make_valid(x))
        print(f"Fixed {sum(~eco_provinces.geometry.is_valid)} rows in eco_provinces.")
    else:
        print('eco_provinces has valid geometries')

    mpl.use('agg')  # Ensure non-interactive backend for server use
    set_dpi() #Set figure dpi

    state_name = state_name.title()
    
    # --- Step 1: Prepare State Data --- (Approx. 10% of total work)
    yield "data: 10\n\n"
    state_row = us_states_gdb[us_states_gdb.NAME == state_name]
    
    # --- Step 2: Clip Eco Provinces --- (Approx. 20% of total work)
    yield "data: 20\n\n"
    clipped_eco_provinces, eco_prov_names = map_utilities(state_row, eco_provinces)
    
    # --- Step 3: Calculate Colors --- (Approx. 10% of total work)
    yield "data: 30\n\n"
    eco_colors = map_color_utils(clipped_eco_provinces)
    
    # --- Step 4: Calculate Centroids --- (Approx. 10% of total work)
    yield "data: 40\n\n"
    centroids_gdf = centroids(clipped_eco_provinces)
    
    # --- Step 5: Start Plotting --- (Approx. 10% of total work)
    yield "data: 50\n\n"
    fig, ax = plt.subplots(layout='tight', edgecolor=(0.3, 0.5, 0.4, 0.7), linewidth=2)
    
    # --- Step 6: Plot Eco Provinces --- (Approx. 15% of total work)
    yield "data: 65\n\n"
    clipped_eco_provinces.plot(ax = ax, color=clipped_eco_provinces['colors'], legend=True,legend_kwds={'loc':(0.0, 0.0),'shadow':True},alpha=0.6, edgecolor='black', linewidth=0.5, figsize=(5, 7),zorder=1)
    cx.add_basemap(ax=ax, zoom=7)
    ax.set_axis_off()
    ax.set_title(label="Ecological Provinces Present in {}".format(state_name), fontstyle='oblique',color='white',path_effects=[pe.Stroke(linewidth=1.20, foreground='green'),pe.Normal()],fontsize=15,position=(0.4,1.3), va='baseline',pad=7, ha='left')

    # --- Step 7: Plot Centroids --- (Approx. 10% of total work)
    yield "data: 75\n\n"
    centroids_gdf.apply(lambda x: ax.annotate(text=x['PROVINCE_ID'], bbox=dict(boxstyle='circle,pad=0.2',facecolor='black',alpha=0.85), xy=(x.geometry.x, x.geometry.y), color='white',  backgroundcolor=(0, 0, 0, 0.05),ha='center', va='center',fontsize=6), axis=1)

    # --- Step 8: Create Legend --- (Approx. 10% of total work)
    yield "data: 85\n\n"
    circle = mpath.Path.circle(center=(0,0), radius=100)
    patches=[]
    for color, i in zip(eco_colors,  clipped_eco_provinces.PROVINCE_ID.unique()):
        number = mpltext.TextPath(xy=(-2.5,-3.75), s="{}".format(i), size=6)
        color_patch = mpatches.Patch(facecolor = color, alpha=0.6, edgecolor='black',linewidth=0.2)
        line2 = Line2D([], [], ls='',color="#cef0d8", marker=number, alpha=0.6,markerfacecolor=color, markeredgecolor='black',markersize=17, markeredgewidth=0.25)
        legend_tuple = tuple((color_patch, line2))
        patches.append(legend_tuple)

    legend_labels = [re.sub('\d', '', re.sub('- ', '-\n', re.sub(' and ', ' &\n', re.sub(' Province', '', i)))).lstrip() for i in clipped_eco_provinces['LEG_LABELS']]
    edge_color = [(0.6, 0, 0, 1)]
    state_color = [(0.3, 0, 0, 0.0)]
    state_row.plot(ax=ax, edgecolors='black', color=state_color, linestyle='--')
    patches.append(mpatches.Patch(facecolor=(0.0,0.0,0.0, 0.0), edgecolor='black', linestyle='--', joinstyle='round'))
    legend_labels.append(state_name)

    plt.legend(handles=patches,labels=legend_labels, handler_map={tuple: HandlerTuple(ndivide=None)},handletextpad=1, bbox_to_anchor=(1, 1, 0, 0),loc='upper left', handleheight=3, handlelength=4.5, labelspacing=1.1, fontsize='x-small', facecolor='#cef0d8', framealpha=0.20)
    ax.set_frame_on(True)
    fig.set_facecolor(((252 / 255), (244 / 255), (222/255), 0.3))
    annotations = [child for child in ax.get_children() if isinstance(child, mpltext.Annotation)]
    adjust_text(annotations, avoid_self=False)
    ax.get_children()[2].set(fontsize=4, alpha=0.3)
    
    # --- Step 9: Save Figure --- (Approx. 5% of total work)
    yield "data: 90\n\n"
    fig.savefig(os.path.join('static', 'images', 'map.png'), bbox_inches='tight') #added bbox_inches so that the figure saves properly.
    
    # --- Step 10: Finalization --- (Approx. 10% of total work)
    yield "data: 100\n\n"
    plt.close(fig)
    
    return

@app.route('/map', methods=['GET', 'POST'])
def map_page():
    if request.method == 'POST':
        state_name = request.form.get('state_name')
        #Pass the state name variable to the generator function.
        return Response(generate_map_with_progress(state_name), mimetype='text/event-stream')
    
    #When the page is first loaded, render the map.html page.
    return render_template('map.html')



if __name__ == '__main__':
    app.run(debug=True)


