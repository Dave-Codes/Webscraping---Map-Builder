from adjustText import adjust_text

import numpy as np 
import pandas as pd 
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import os
import geopandas 

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
from flask import Flask, render_template
from itables import init_notebook_mode, show, to_html_datatable, JavascriptCode
from webscrape import extract
from functions import set_dpi, data_transform, map_utilities, map_color_utils, centroids, build_map


url = 'https://data.fs.usda.gov/geodata/edw/datasets.php'
table_attribs = ['Feature Class', 'Description','ESRI GDB', 'Shapefile']

app = Flask(__name__)


def get_df():
    df = extract(url, table_attribs)
    #init_notebook_mode(all_interactive=True, connected=True)
    #table_html = show(df)
    table_html = to_html_datatable(df, display_logo_when_loading=False, classes="display compact", max_width='400px', max_height='30px',\
                                       columnDefs=[
        {
            "targets": 2,
            #"render": JavascriptCode(ellipsis_func_js)
        }
    ],
    )
    return table_html

@app.route('/')
def index():
    table_html = get_df()
    map = build_map()
    map.savefig(os.path.join('static','images', 'map.png'))
    return render_template('index.html', table_html=table_html)

if __name__ == '__main__':
    app.run(debug=True)