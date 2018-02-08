from bokeh.models.sources import AjaxDataSource
from bokeh.plotting import figure, curdoc
from sqlalchemy import create_engine
import pandas as pd
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from datetime import datetime, date
import os
from pyramid.view import view_config
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.layouts import widgetbox
from bokeh.models.widgets import TextInput
from bokeh.models.callbacks import CustomJS

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
dfStatic = pd.read_sql_query('SELECT * FROM {}'.format(table_name), cursor2)
dfStatic['time'] = pd.to_datetime(dfStatic['time'])
# NOTE: initialize data source with empty dict that has the dict keys
# that I know are in the database - should maybe make more dynamic and just initialize to empty data source?
epochDate = datetime.utcfromtimestamp(0)
# NOTE: the data_url needs to be the 'pattern of the route' ie needs to match the second argument in the
# config.add_route() method within the routes.py file. If not we get a HTTP not found error
manualId = 1
manualId2 = 5000
dateFmt = "%m/%d/%Y"

@view_config(route_name='bokeh_AJAX', renderer='../templates/plot2.jinja2')
def bokeh_ajax(request):
    startDt = dfDict['time'][0].to_pydatetime()
    endDt = dfStatic['time'].iloc[-1].to_pydatetime()
    # plot used for continually adding points to graph
    # note: if want to manipulate axis ranges later on need to set some sort of starting range or else when
    # try to change via figure.x_range.start or figure.x_range.end will get weird incorrect behavior
    source = AjaxDataSource(data={"time": [], "temperature": [], "id": []},
                            data_url='http://localhost:6543/AJAXdata',
                            polling_interval=100,
                            mode='append')
    livePlot = figure(x_axis_type="datetime",
                      x_range=[startDt, endDt],
                      y_range=(0,25),
                      y_axis_label='Temperature (Celsius)',
                      title="Sea Surface Temperature at 43.18, -70.43",
                      plot_width=800)
    livePlot.line("time", "temperature", source=source)
    script, div = components(livePlot)
    # note: need the below in order to display the bokeh plot
    jsResources = INLINE.render_js()
    # need the below in order to be able to properly interact with the plot and have the default bokeh plot
    # interaction tool to display
    cssResources = INLINE.render_css()
    source2 = AjaxDataSource(data={"time": [], "temperature": [], "id": []},
                            data_url='http://localhost:6543/AJAXdata2',
                            polling_interval=100,
                            mode='append')
    livePlot2 = figure(x_axis_type="datetime",
                      x_range=[startDt, endDt],
                      y_range=(0,25),
                      y_axis_label='Temperature (Celsius)',
                      title="Sea Surface Temperature at 43.18, -70.43",
                      plot_width=800)
    livePlot2.line("time", "temperature", source=source2)
    # script2 = None
    # div2 = None
    script2, div2 = components(livePlot2)

    updateStartJS = CustomJS(args=dict(xrange=livePlot.x_range), code="""
        var startStr = cb_obj.value
        alert(startStr)
        var newStartMilliSeconds = Date.parse(startStr)
        alert(newStartMilliSeconds)
        alert(xrange)
        alert(xrange.start)
        xrange.start = newStartMilliSeconds
        alert(xrange.start)
        xrange.change.emit();
    """)
    updateStart = CustomJS(args=dict(xrange=livePlot.x_range), code="""
        alert(xrange.start);
    """)
    startInput = TextInput(value=startDt.strftime(dateFmt), callback=updateStartJS)
    endInput = TextInput(value=endDt.strftime(dateFmt))
    livePlot.x_range.js_on_change('start', updateStart)
    widgets = widgetbox([startInput, endInput])
    componentScript, componentDiv = components(widgets)
    return {'script': script,
            'div': div,
            'someword': "hello",
            'jsResources': jsResources,
            'cssResources': cssResources,
            'script2': script2,
            'div2': div2,
            'componentScript': componentScript,
            'componentDiv': componentDiv}

# the data url that is polled to adopt the AJAXDATASOURCE. No template rendering as this isn't a page to be viewed
# just a page to post new data to in JSON format
@view_config(route_name='data', renderer='json')
def data_route(request):
    global manualId, cursor2
    # NOTE: change later but for now just getting 10 entries at a time and adding that to the graph after each poll
    df = pd.read_sql_query('SELECT * FROM {} WHERE id >= {} LIMIT 10'.format(table_name, manualId), cursor2)
    manualId += 10
    # first convert the column to datetime from strings
    df['time'] = pd.to_datetime(df['time'])
    # then apply the unixTimeFromEpoch method to every entry to convert it to milli seconds from epoch which bokeh
    # uses when plotting datetime
    df['time'] = df['time'].apply(unixTimeFromEpoch)
    # convert it to a dictionary in form of {'column name': [list of values],..} so then I can take each list
    # of values and then return a dictionary with the keys that I originally assigned to the AJAXDatasource
    # to the list of values that I now have in DFDICT
    dfDict = df.to_dict(orient='list')
    return {'id': dfDict['id'], 'time': dfDict['time'], 'temperature': dfDict['temperature']}

@view_config(route_name='data2', renderer='json')
def data_route2(request):
    global manualId, cursor2, manualId2
    # NOTE: change later but for now just getting 10 entries at a time and adding that to the graph after each poll
    df = pd.read_sql_query('SELECT * FROM {} WHERE id >= {} LIMIT 50'.format(table_name, manualId2), cursor2)
    manualId2 += 50
    # first convert the column to datetime from strings
    df['time'] = pd.to_datetime(df['time'])
    # then apply the unixTimeFromEpoch method to every entry to convert it to milli seconds from epoch which bokeh
    # uses when plotting datetime
    df['time'] = df['time'].apply(unixTimeFromEpoch)
    # convert it to a dictionary in form of {'column name': [list of values],..} so then I can take each list
    # of values and then return a dictionary with the keys that I originally assigned to the AJAXDatasource
    # to the list of values that I now have in DFDICT
    dfDict = df.to_dict(orient='list')
    return {'id': dfDict['id'], 'time': dfDict['time'], 'temperature': dfDict['temperature']}

def unixTimeFromEpoch(dt: datetime, milli=True):
    """helper function that takes a datetime object and then returns the milli-seconds from epoch by default
    if milli is false then returns the seconds from epoch"""
    scalar = 1
    if milli:
        scalar = 1000
    return (dt - epochDate).total_seconds()*scalar