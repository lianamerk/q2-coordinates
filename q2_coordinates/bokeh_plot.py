# ----------------------------------------------------------------------------
# Copyright (c) 2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os

import numpy as np
import pandas as pd

import bokeh.io

import panel as pn
import datetime as dt

from bokeh.tile_providers import CARTODBPOSITRON, get_provider

tile_provider = get_provider(CARTODBPOSITRON)


from ._utilities import (save_bokeh_map)


########################## Helper fxns, can eventually go in utilities
def mercator_creator(df, lat='lat', lon='lon'):
    # from https://www.youtube.com/watch?v=BojxegBh9_4

    k = 6378137
    df['x'] = k * np.radians(df[lon])
    df['y'] = np.log(np.tan((90 + df[lat]) * np.pi / 360)) * k

    return df


def extract_sub_df(df, ferm_class_list, country_list, date_range):
    """Extract sub data frame for country and class over a date range."""
    inds = (
            (df["Class"].isin(ferm_class_list))
            & (df["Country_made"].isin(country_list))
            & (df["Acquisition_date"] >= date_range[0])
            & (df["Acquisition_date"] <= date_range[1])
    )

    return df.loc[inds, :]


def plot_bokeh_map(output_dir: str):
    ########################## Clean and prep our data
    # Load in the metadata
    ferm_locations = pd.read_csv("/Users/lianamerk/git/q2-coordinates/q2_coordinates/assets/bokeh_plot/ferm.csv")

    # Split the Lat-Long column into two columns, Lat and Long
    ferm_locations[['Lat', 'Long']] = ferm_locations['Lat-Long'].str.split(', ', 1, expand=True)

    # Create a new dataframe only if the point has a valid Lat and Long
    ferm_locations_final = ferm_locations[ferm_locations['Lat'].notna()].copy()

    # Convert from a string, and put in columns called Latitude and Longitude
    ferm_locations_final.loc[:, 'Latitude1'] = pd.to_numeric(ferm_locations_final['Lat'], errors='coerce')
    ferm_locations_final.loc[:, 'Longitude1'] = pd.to_numeric(ferm_locations_final['Long'], errors='coerce')

    # Add x, y for lat long
    ferm_locations_final = mercator_creator(ferm_locations_final, lat='Latitude1', lon='Longitude1')

    class_options = list(ferm_locations_final.Class.unique())
    country_options = list(ferm_locations_final.Country_obtained.unique())

    ferm_locations_final.Acquisition_date = pd.to_datetime(ferm_locations_final.Acquisition_date)
    ferm_locations_final.Extract_date = pd.to_datetime(ferm_locations_final.Extract_date)
    ferm_locations_final.Arrival_date = pd.to_datetime(ferm_locations_final.Arrival_date)

    ########################## Build Sliders
    country_choice = pn.widgets.MultiChoice(name='Country', value=country_options,
                                            options=country_options, solid=False)

    class_choice = pn.widgets.MultiChoice(name='Choose Ferment Class:', value=class_options,
                                          options=class_options, css_classes=[])

    colors = bokeh.palettes.Category20[15]

    color_map = dict(zip(class_options, colors))

    ferm_locations_final['color'] = ferm_locations_final['Class'].map(color_map)
    ferm_locations_final['url'] = [
                                      "https://github.com/lianamerk/hovercal/blob/main/examples/fruit_hovercal_1.png?raw=true"] * len(
        ferm_locations_final)

    ########################## Make the plot

    p = bokeh.plotting.figure(
        frame_height=400,
        frame_width=700,
        x_axis_label="Latitude",
        y_axis_label="Longitude",
        tools=['wheel_zoom', 'pan', 'reset', 'tap'],
        x_axis_type='mercator',
        y_axis_type='mercator',
        x_range=[ferm_locations_final.x.min() - 100000, ferm_locations_final.x.max() + 100000],
        y_range=[ferm_locations_final.y.min() - 100000, ferm_locations_final.y.max() + 100000]
    )

    p.toolbar_location = 'above'
    p.add_tile(tile_provider)
    p.add_tools(bokeh.models.BoxZoomTool(match_aspect=True))

    ########################## Hover

    hover = bokeh.models.HoverTool()

    hover.tooltips = """
        <div>
            <div>
                <img
                    src="@imgs" height="42" alt="@imgs" width="42"
                    style="float: left; margin: 0px 15px 15px 0px;"
                    border="2"
                ></img>
            </div>
            <div>
                <span style="font-size: 17px; font-weight: bold;">@Class</span>
                <span style="font-size: 15px; color: #966;">@Sample_ID</span>
            </div>
            <div>
                <span><b>bold</b></span>
            </div>
            <div>
                <span style="font-size: 15px;">Location</span>
                <span style="font-size: 10px; color: #696;">@x</span>
            </div>
        </div>
    """
    p.add_tools(hover)

    url = "https://github.com/lianamerk/hovercal/blob/main/examples/fruit_hovercal_1.png?raw=true"
    taptool = p.select(type=bokeh.models.TapTool)
    taptool.callback = bokeh.models.OpenURL(url=url)

    ########################## Set up CDS

    # point visible
    chosen_cds = bokeh.models.ColumnDataSource(
        {
            "x": ferm_locations_final["x"],
            "y": ferm_locations_final["y"],
            "color": ferm_locations_final['color'],
            "Country_obtained": ferm_locations_final['Country_obtained'],
            "Class": ferm_locations_final['Class'],
            "Sample_ID": ferm_locations_final['Sample_ID'],
            "Type": ferm_locations_final['Type'],
            "url": ferm_locations_final['url'],
        }
    )

    # point available
    cds = bokeh.models.ColumnDataSource(
        {
            "x": ferm_locations_final["x"],
            "y": ferm_locations_final["y"],
            "color": ferm_locations_final['color'],
            "Country_obtained": ferm_locations_final['Country_obtained'],
            "Class": ferm_locations_final['Class'],
            "Sample_ID": ferm_locations_final['Sample_ID'],
            "Type": ferm_locations_final['Type'],
            "url": ferm_locations_final['url'],
        }
    )

    circle = p.circle(
        source=chosen_cds, x="x", y="y", fill_color="color", line_color="color",
    )

    ########################## JS

    # JavaScript code for the callback stored as a string
    # JavaScript code for the callback stored as a string
    jscode = """
    let selected_class = class_choice.value;
    let selected_country = country_choice.value;
    
    let point_visible = source_visible.data;
    let point_available = source_available.data;
    
    point_visible.x = []
    point_visible.y = []
    point_visible.color = []
    point_visible.Country_obtained = []
    point_visible.Class = []
    point_visible.Sample_ID = []
    point_visible.Type = []
    point_visible.url = []
    
    for (let i = 0; i < point_available.x.length; i++) {
        if (selected_class.includes(point_available.Class[i]) && selected_country.includes(point_available.Country_obtained[i])) {
            point_visible.x.push(point_available.x[i]);
            point_visible.y.push(point_available.y[i]);
            point_visible.color.push(point_available.color[i]);
            point_visible.Country_obtained.push(point_available.Country_obtained[i]);
            point_visible.Class.push(point_available.Class[i]);
            point_visible.Sample_ID.push(point_available.Sample_ID[i]);
            point_visible.Type.push(point_available.Type[i]);
            point_visible.url.push(point_available.url[i]);
        }
    }
    
    source_visible.change.emit(); 
    """

    # Link widget to the JS
    class_choice.jscallback(value=jscode,
                            args=dict(source_available=cds, source_visible=chosen_cds, class_choice=class_choice,
                                      country_choice=country_choice))

    country_choice.jscallback(value=jscode,
                              args=dict(source_available=cds, source_visible=chosen_cds, class_choice=class_choice,
                                        country_choice=country_choice))

    ########################## Set up the Panes
    map_panel = pn.Row(p, pn.Spacer(width=15), pn.Column(class_choice, country_choice))
    map_panel.save(filename=os.path.join(output_dir, 'plot.html'), embed=True)
    save_bokeh_map(output_dir)
