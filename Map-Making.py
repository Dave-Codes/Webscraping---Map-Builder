

#!pip install adjustText nbstripout nbformat
from adjustText import adjust_text

import numpy as np 
import pandas as pd 
import seaborn as sns
import matplotlib.pyplot as plt

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

from IPython.display import display, HTML, Markdown
display(HTML("<style>.container { width:100% !important;} div.output_scroll { height: 1000px; }</style>"))

plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
state_name = input("Enter a U.S. State Name to explore: ")
us_states_gdb = geopandas.read_file('/kaggle/input/us-state-shapefiles/tl_2012_us_state/tl_2012_us_state.shp')

#state_name = 'California'
us_states_gdb['centroid'] = us_states_gdb.centroid

us_states_gdb['center'] = list(zip(us_states_gdb.INTPTLAT.astype(float), us_states_gdb.INTPTLON.astype(float)))
state_row = us_states_gdb[us_states_gdb.NAME == state_name]

clipping_box = state_row.geometry.to_crs(epsg=4269)
state_center = state_row.center.values[0]
print(state_center)
print(clipping_box)

eco_provinces = geopandas.read_file("../input/usda-forest-service-eco-provinces/S_USA.EcoMapProvinces.gdb", mask=clipping_box)

#Examining the first few rows
#eco_provinces.head(10)

# Inspecting columns.
#eco_provinces.info()

#Dropping a column that contains only null values, and verifying the change.
eco_provinces = eco_provinces.drop(columns=['S_USA_EcoMapProvinces_AREA'])
eco_provinces = eco_provinces[eco_provinces.MAP_UNIT_NAME != 'Water']
#eco_provinces.info()

# The descriptions of the Eco Provinces as described in the data:

#Examining the crs attribute of the ecological provinces
#print(eco_provinces.crs)
#Converting the crs of the GeoDataFrame to EPSG:3857 to align with the map tiles

eco_provinces = eco_provinces.to_crs(epsg=3857)
#eco_provinces.crs
num_provs = eco_provinces.shape[0]

color_range = cm.tab20c(range(num_provs))
eco_prov_names = eco_provinces.MAP_UNIT_NAME.unique()
eco_colors = [(r,g,b) for r, g, b, a in [color for color in color_range]]
color_dict = dict(zip(eco_prov_names, eco_colors))
eco_cmap = ListedColormap(eco_colors)
#print(color_dict)

# Concatenating series to create a feature in df of formatted legend label data
eco_provinces['LEG_LABELS'] = eco_provinces['PROVINCE_ID'].map(str).str.cat(eco_provinces['MAP_UNIT_NAME'], sep=" ")
#print(eco_provinces['LEG_LABELS'])
eco_provinces['colors'] = eco_colors
#print(eco_provinces['colors'])

polygon_lists = [list(multipol.geoms) for multipol in eco_provinces.geometry]

#polygon_lists

#centroids = [polygon.centroid for polygon in plist for plist in [list(multipol.geoms) for multipol in eco_provinces.geometry]]

centroids = []
for plist in polygon_lists:
    num_polygons = len(plist)
    if num_polygons > 3:
        ctr = MultiPolygon(plist).representative_point()
        #if ctr.buffer(50).contains()
        centroids.append(ctr)

    else:
        for polygon in plist:
            centroids.append(polygon.representative_point())
centroids
centroid_gdf = geopandas.GeoDataFrame(data=centroids)
centroid_gdf = centroid_gdf.set_geometry(col=centroid_gdf[0])
centroid_gdf = centroid_gdf.set_crs(crs=eco_provinces.crs)
#centroid_gdf.within(eco_provinces.geometry[0])

centroids_gdf = centroid_gdf.sjoin(eco_provinces)
    
#centroids_gdf.head(20)



fig, ax = plt.subplots(layout='tight', edgecolor=(0.3, 0.5, 0.4, 0.7), linewidth=2)


eco_provinces.plot(ax = ax, color=eco_provinces['colors'], legend=True,legend_kwds={'loc':(0.0, 0.0),'shadow':True},alpha=0.6, edgecolor='black', linewidth=0.5, figsize=(5, 7),zorder=1)
cx.add_basemap(ax=ax, zoom=7)
ax.set_axis_off()
ax.set_title(label="Ecological Provinces Present in {}".format(state_name), fontstyle='oblique',color='white',path_effects=[pe.Stroke(linewidth=1.20, foreground='green'),pe.Normal()],fontsize=15,position=(0.4,1.3), va='baseline',pad=7, ha='left')

eco_provinces['CENTER'] = eco_provinces.geometry.representative_point()

centroids_gdf.apply(lambda x: ax.annotate(text=x['PROVINCE_ID'], bbox=dict(boxstyle='circle,pad=0.2',facecolor='black',alpha=0.85), xy=(x.geometry.x, x.geometry.y), color='white',  backgroundcolor=(0, 0, 0, 0.05),ha='center', va='center',fontsize=6), axis=1)

circle = mpath.Path.circle(center=(0,0), radius=100)

patches=[]
for color, i in zip(eco_colors,eco_provinces.PROVINCE_ID.unique()):
       
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

        
legend_labels = [re.sub('\d', '', re.sub('- ', '-\n', re.sub(' and ', ' &\n', re.sub(' Province', '', i)))).lstrip() for i in eco_provinces['LEG_LABELS']]



edge_color = [(0.6, 0, 0, 1)]
state_color = [(0.3, 0, 0, 0.0)]
us_states_gdb[us_states_gdb.NAME == state_name].plot(ax=ax, edgecolors='black', color=state_color, linestyle='--')
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

plt.show()


#Using a bbox when reading in the data includes all eco provinces that exist in the state, but these extend far outside the borders of the state, so here I cut the eco province polygons off at the edges of the state. I utilize a bounding box, which works if the data is in CRS epsg:4269, so I convert it before I cut the provinces at the border of Colorado.


eco_provinces_state = eco_provinces.to_crs(epsg=4269).clip(mask=clipping_box)
eco_provinces_state = eco_provinces_state.to_crs(epsg=3857)
polygon_lists_state = [list(province.geoms) if province.type == 'MultiPolygon' else province for province in eco_provinces_state.geometry ]


state_centroids = []

for province in eco_provinces_state.geometry:
    if province.type == 'Polygon':
        state_centroids.append(province.representative_point())
    elif (province.type == 'MultiPolygon') & (len(province.geoms) > 3):
            ctr = province.representative_point()
            state_centroids.append(ctr)
    else:
        for p in province.geoms:
            state_centroids.append(p.representative_point())
            

patches.pop()
legend_labels.pop()



fig, ax = plt.subplots(layout='tight', edgecolor=(0.3, 0.5, 0.4, 0.7), linewidth=2)

eco_provinces_state = eco_provinces_state.sort_values('PROVINCE_ID')
# Plotting the data on matplotlib ax
eco_provinces_state.plot(ax = ax ,color=eco_provinces_state['colors'],legend=True,cmap=eco_cmap,legend_kwds={'loc':(1, 1),'shadow':True},alpha=0.35, linewidth=0.5, edgecolor='black', figsize=(7,7))
cx.add_basemap(ax, zoom=8, source=cx.providers.Stamen.TonerLite)
ax.set_axis_off()
ax.set_title('{} Ecological Provinces'.format(state_name), position=(0.45, 0.75), fontstyle='oblique',color='white',path_effects=[pe.Stroke(linewidth=1.25, foreground='green'),pe.Normal()],fontsize=15, va='baseline',pad=7, ha='left')

patches=[]
for color, i in zip(eco_colors,eco_provinces.PROVINCE_ID.unique()):
    if len(str(i)) < 2:
        i = " {}".format(i)
    else:
        i=i
        #number = mpltext.TextPath(xy=(-0.70,-0.57), s="{}".format(i), size=1)
    number= mpltext.TextPath(xy=(-4,-3.5),s="{}".format(i), size=5,prop={'weight':'bold'})
    circle = mpath.Path.circle(center=(-0.50,-2.0), radius=5)
        
    marker = mpath.Path(vertices=np.concatenate([circle.vertices, number.vertices]),
                            codes=np.concatenate([circle.codes, number.codes]))
    
        
    color_patch = mpatches.Patch(facecolor = color, alpha=0.6, edgecolor='black',linewidth=0.2)
   
    line2 = Line2D([], [], ls='',color="black", marker=marker,alpha=0.9,markersize=18, markeredgewidth=0.25,antialiased=True)
   
    legend_tuple = tuple((color_patch, line2))
    patches.append(legend_tuple)


        
centroids_gdf = geopandas.GeoDataFrame(data=state_centroids)
centroids_gdf = centroids_gdf.set_geometry(col=centroids_gdf[0])
centroids_gdf = centroids_gdf.set_crs(crs=eco_provinces_state.crs)

centroids_gdf = centroids_gdf.sjoin(eco_provinces_state)
centroids_gdf.sort_values('PROVINCE_ID')

# Plotting the PROVINCE_ID values of df at center of provinces        
centroids_gdf.apply(lambda x: ax.annotate(text=x['PROVINCE_ID'], zorder=2,xy=(x.geometry.x, x.geometry.y), color='white',  bbox=dict(boxstyle='circle,pad=0.2',facecolor='black', alpha=0.75),ha='center', fontsize=6), axis=1)



ax.legend(handles=patches, labels=legend_labels, handler_map={tuple: HandlerTuple(ndivide=None)},bbox_to_anchor=(1, 1, 0, 0), loc='upper left', handleheight=4, handlelength=6,labelspacing=1, fontsize='x-small')
fig.set_facecolor(((252 / 255), (244 / 255), (222/255), 0.3))
ax.get_children()[2].set(fontsize=5, alpha=0.3)

fig.tight_layout()

plt.show()


# crs sanity check
eco_provinces_state = geopandas.GeoDataFrame(eco_provinces_state, geometry='geometry', crs=centroids_gdf.crs)

# generating maps of each province within each state
for i in range(eco_provinces_state.shape[0]):
    fig, ax = plt.subplots(figsize=(1,1))
    us_states_gdb[us_states_gdb.NAME == state_name].plot( ax=ax,edgecolors='black', color=state_color, linestyle='-',zorder=1, linewidth=0.2)
    eco_provinces_state.loc[[i], 'geometry'].plot( ax=ax, zorder=2, color=eco_colors[i], linewidth=0.1, linestyle='-', edgecolor=eco_colors[i])
    ax.set_axis_off()
    fig.savefig('/kaggle/working/Eco-Province-{}.png'.format(i), dpi=500)
    

# HTML formatted Names and Descriptions of Eco Provinces
display(HTML("<h1 style='text-align:center;padding:5px;' >Ecological Provinces of {}</h1>".format(state_name)))

# Programmatically generating HTML for glossary
for i, row in eco_provinces.iterrows():
    prov_id = row.PROVINCE_ID
    name = row.MAP_UNIT_NAME
    desc = row.MAP_UNIT_DESCRIPTION
    
    string = """<div style="border:5px solid green;padding:15px;">
                    <h2>{}</h2>
                        <h3>Map ID: {}</h3> \n\n 
                        <div style="display:flex;margin:10px;">
                            <p style='font-size:120%;flex:1;'>{}</p>
                            <img style="flex:1;" src="Eco-Province-{}.png" alt="Eco Province ID {}">
                        </div>
                        <div style='background:powderblue;padding:2px;'></div> \n
                </div>""".format(name, prov_id, desc, i, prov_id)

    display(HTML(string))

display(HTML("<div style='background:green;padding:20px;'></div>"))


"""from pathlib import Path
cwd = Path('.').resolve() # current working directory
output_dir = cwd
if not output_dir.exists():
    output_dir.mkpath()
with open(f"{output_dir}/index.html", mode='w') as fh:
    writers = {False: fh}  # {'without MathJax': fh} }
    from io import StringIO
   
    resources = stripoutprocess(__doc__, input=StringIO(''), write_preamble=True)
    from nbformat.v4 import tosnippet
    writer = fh.write.__self
    writer({"worksheets": [ws._asdict() for ws in resources[0].cells]})"""