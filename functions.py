from adjustText import adjust_text
import base64
from io import BytesIO
import numpy as np 
import pandas as pd 
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl

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
from shapely.validation import make_valid



def set_dpi():
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300



def data_load(url):
    #web_scrape
    return 

def data_transform(df):
    #add features, format, crs convert, 
    #df['centroid'] = df.centroid
    df['center'] = list(zip(df['INTPTLAT'].astype(float), df['INTPTLON'].astype(float)))
    
    return df

def map_utilities(state_row, eco_provinces):
    #state_row.geometry = state_row.geometry.apply(lambda x: make_valid(x))
    
    clipping_box = state_row.geometry.to_crs(epsg=4269)

    clipped_eco_provinces = geopandas.clip(eco_provinces, clipping_box)
    clipped_eco_provinces = clipped_eco_provinces.to_crs(epsg=3857)
    eco_prov_names = clipped_eco_provinces.MAP_UNIT_NAME.unique()
    clipped_eco_provinces['LEG_LABELS'] = clipped_eco_provinces['PROVINCE_ID'].map(str).str.cat(clipped_eco_provinces['MAP_UNIT_NAME'], sep=" ")
    clipped_eco_provinces['CENTER'] = clipped_eco_provinces.geometry.representative_point()
    return clipped_eco_provinces, eco_prov_names



def map_color_utils(clipped_eco_provinces):
    num_provs = clipped_eco_provinces.shape[0]
    color_range = cm.tab20c(range(num_provs))
    eco_colors = [(r,g,b) for r, g, b, a in [color for color in color_range]]
    clipped_eco_provinces['colors'] = eco_colors
    #color_dict = dict(zip(prov_names, eco_colors))
    #eco_cmap = ListedColormap(eco_colors)
    return eco_colors



#polygon_lists

#centroids = [polygon.centroid for polygon in plist for plist in [list(multipol.geoms) for multipol in eco_provinces.geometry]]
def centroids(clipped_eco_provinces):
    polygon_lists = [list(multipol.geoms) if multipol.geom_type == 'MultiPolygon' else [multipol] for multipol in clipped_eco_provinces.geometry]
    centroids = []
    for plist in polygon_lists:
        num_polygons = len(plist)
        if num_polygons > 3:
            ctr = MultiPolygon(plist).representative_point()
            #if ctr.buffer(50).contains()
            centroids.append(ctr)
        elif num_polygons == 1:
            centroids.append(plist[0].representative_point())

        else:
            for polygon in plist:
                centroids.append(polygon.representative_point())

    centroids_gdf = geopandas.GeoDataFrame(data=centroids)
    centroids_gdf = centroids_gdf.set_geometry(col=centroids_gdf[0])
    centroids_gdf = centroids_gdf.set_crs(crs=clipped_eco_provinces.crs)
    
    centroids_gdf = centroids_gdf.sjoin(clipped_eco_provinces)

    return centroids_gdf



def build_map(us_states_gdb, eco_provinces, state_name=''):
    mpl.use('agg')
    set_dpi()
    #state_name = input("Enter a U.S. State Name to explore: ")
    
    state_name = state_name.title()

    state_row = us_states_gdb[us_states_gdb.NAME == state_name]
    

    clipped_eco_provinces, eco_prov_names = map_utilities(state_row, eco_provinces)

    eco_colors = map_color_utils(clipped_eco_provinces)
    centroids_gdf = centroids(clipped_eco_provinces)
    

    fig, ax = plt.subplots(layout='tight', edgecolor=(0.3, 0.5, 0.4, 0.7), linewidth=2)


    clipped_eco_provinces.plot(ax = ax, color=clipped_eco_provinces['colors'], legend=True,legend_kwds={'loc':(0.0, 0.0),'shadow':True},alpha=0.6, edgecolor='black', linewidth=0.5, figsize=(5, 7),zorder=1)
    cx.add_basemap(ax=ax, zoom=7)
    ax.set_axis_off()
    ax.set_title(label="Ecological Provinces Present in {}".format(state_name), fontstyle='oblique',color='white',path_effects=[pe.Stroke(linewidth=1.20, foreground='green'),pe.Normal()],fontsize=15,position=(0.4,1.3), va='baseline',pad=7, ha='left')

    

    centroids_gdf.apply(lambda x: ax.annotate(text=x['PROVINCE_ID'], bbox=dict(boxstyle='circle,pad=0.2',facecolor='black',alpha=0.85), xy=(x.geometry.x, x.geometry.y), color='white',  backgroundcolor=(0, 0, 0, 0.05),ha='center', va='center',fontsize=6), axis=1)

    circle = mpath.Path.circle(center=(0,0), radius=100)

    patches=[]

    for color, i in zip(eco_colors,  clipped_eco_provinces.PROVINCE_ID.unique()):
        
            number = mpltext.TextPath(xy=(-2.5,-3.75), s="{}".format(i), size=6)
            #marker = circle.
            
            #marker = mpath.Path(vertices=np.concatenate([circle.vertices, number.vertices[::-1, ...]]),
                                #codes=np.concatenate([circle.codes, number.codes]))
            
            color_patch = mpatches.Patch(facecolor = color, alpha=0.6, edgecolor='black',linewidth=0.2)
            #number_circle = mpatches.Patch(facecolor='blue', joinstyle='round',alpha=0.5)
            line2 = Line2D([], [], ls='',color="#cef0d8", marker=number, alpha=0.6,markerfacecolor=color, markeredgecolor='black',markersize=17, markeredgewidth=0.25)
            #num_patch = mpatches.PathPatch(number_path)
            legend_tuple = tuple((color_patch, line2))
            patches.append(legend_tuple)

    #patches = list(map(lambda x, y:(x, str(y)), patches, eco_provinces.PROVINCE_ID.unique()))

            
    legend_labels = [re.sub('\d', '', re.sub('- ', '-\n', re.sub(' and ', ' &\n', re.sub(' Province', '', i)))).lstrip() for i in clipped_eco_provinces['LEG_LABELS']]



    edge_color = [(0.6, 0, 0, 1)]
    state_color = [(0.3, 0, 0, 0.0)]
    state_row.plot(ax=ax, edgecolors='black', color=state_color, linestyle='--')
    patches.append(mpatches.Patch(facecolor=(0.0,0.0,0.0, 0.0), edgecolor='black', linestyle='--', joinstyle='round'))
    legend_labels.append(state_name)

    """star = mpath.Path.unit_regular_star(6)
    circle = mpath.Path.unit_circle()
    # concatenate the circle with an internal cutout of the star
    cut_star = mpath.Path(
        vertices=np.concatenate([circle.vertices, star.vertices[::-1, ...]]),
        codes=np.concatenate([circle.codes, star.codes]))"""

    plt.legend(handles=patches,labels=legend_labels, handler_map={tuple: HandlerTuple(ndivide=None)},handletextpad=1, bbox_to_anchor=(1, 1, 0, 0),loc='upper left', handleheight=3, handlelength=4.5, labelspacing=1.1, fontsize='x-small', facecolor='#cef0d8', framealpha=0.20)
    ax.set_frame_on(True)


    #fig.set_path_effects(path_effects=[pe.Normal(),pe.SimpleLineShadow(shadow_color='k'),])

    fig.set_facecolor(((252 / 255), (244 / 255), (222/255), 0.3))

    annotations = [child for child in ax.get_children() if isinstance(child, mpltext.Annotation)]
    adjust_text(annotations, avoid_self=False)

    ax.get_children()[2].set(fontsize=4, alpha=0.3)

    return fig
