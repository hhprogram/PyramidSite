from bokeh.layouts import column, widgetbox, row
from bokeh.models import ColumnDataSource, Slider
from bokeh.models.sources import AjaxDataSource
from bokeh.plotting import figure, curdoc
from bokeh.server.server import Server
from bokeh.themes import Theme
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server
from bokeh.models.widgets import Panel, Tabs, DateRangeSlider, DatePicker, TextInput, Button
import sqlite3
from sqlalchemy import create_engine
import pandas as pd
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from datetime import datetime, timedelta
import os
from pyramid.view import view_config
from bokeh.embed import components

# denoted this as table_name. I create sqlite table separately in another program
# should change to be more dynamic
table_name = 'temperatures'
# using sqlalchemy to connect to it, easier to leverage pandas sql to df and back functions this way
# if have more queries might be an easier way to interface with db
# get path of the underlying projec root folder where the db is held
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
path = os.path.join(path, 'seaSurface.sqlite')
cursor2 = create_engine('sqlite:///' + path)
dfLabels = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", cursor2)
# just get the first entry for now. even though have all data to be graphed want to
# try to simulate 'live-plotting' by only grabbing a row at a time and going back
# via a callback to retrieve new data and plot on the go
df = pd.read_sql_query('SELECT * FROM {} LIMIT 1'.format(table_name), cursor2)
#need to translate to datetime or else bokeh graph doesn't handle it correctly
df['time'] = pd.to_datetime(df['time'])
dfDict = df.to_dict(orient='list')
# source = ColumnDataSource(data=dfDict)
dfStatic = pd.read_sql_query('SELECT * FROM {}'.format(table_name), cursor2)
dfStatic['time'] = pd.to_datetime(dfStatic['time'])
# NOTE: initialize data source with empty dict that has the dict keys
# that I know are in the database - should maybe make more dynamic and just initialize to empty data source?
epochDate = pd.to_datetime("1/1/1970")
source = AjaxDataSource(data=dfDict,
                        data_url='http://localhost:6543/data',
                        polling_interval=1000)
manualId = 1

@view_config(route_name='bokeh_AJAX', renderer='../templates/plot2.jinja2')
def bokeh_ajax(request):
    startDt = dfDict['time'][0].to_pydatetime()
    endDt = dfStatic['time'].iloc[-1].to_pydatetime()
    # plot used for continually adding points to graph
    # note: if want to manipulate axis ranges later on need to set some sort of starting range or else when
    # try to change via figure.x_range.start or figure.x_range.end will get weird incorrect behavior
    livePlot = figure(x_axis_type='datetime',
                      x_range=[startDt, endDt],
                      y_range=(0,25),
                      y_axis_label='Temperature (Celsius)',
                      title="Sea Surface Temperature at 43.18, -70.43",
                      plot_width=800)
    livePlot.line('time', 'temperature', source=source)
    script, div = components(livePlot)
    return {'script': script, 'div': div, 'someword': "hello"}


@view_config(route_name='data', renderer='json')
def data_route(request):
    global manualId, cursor
    df = pd.read_sql_query('SELECT * FROM {} WHERE id>= {} LIMIT 10'.format(table_name, manualId), cursor)
    manualId += 10
    df['time'] = pd.to_datetime(df['time'])
    x = df['time']
    y = df['temperature']
    return {'time': x, 'temperature': y}