from bokeh.layouts import column, widgetbox, row
from bokeh.models import ColumnDataSource, Slider
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

# denoted this as table_name. I create sqlite table separately in another program
# should change to be more dynamic
table_name = 'temperatures'
# using sqlalchemy to connect to it, easier to leverage pandas sql to df and back functions this way
# if have more queries might be an easier way to interface with db
# get path of the underlying projec root folder where the db is held
path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
path = os.path.join(path, 'seaSurface.sqlite')
cursor = create_engine('sqlite:///'+path)
# just get the first entry for now. even though have all data to be graphed want to
# try to simulate 'live-plotting' by only grabbing a row at a time and going back
# via a callback to retrieve new data and plot on the go
df = pd.read_sql_query('SELECT * FROM {} LIMIT 1'.format(table_name), cursor)
#need to translate to datetime or else bokeh graph doesn't handle it correctly
df['time'] = pd.to_datetime(df['time'])
dfDict = df.to_dict(orient='list')
source = ColumnDataSource(data=dfDict)
dfStatic = pd.read_sql_query('SELECT * FROM {}'.format(table_name), cursor)
dfStatic['time'] = pd.to_datetime(dfStatic['time'])
print(dfStatic['time'][0].tz, " time zone")
staticSource = ColumnDataSource(data=dfStatic.to_dict(orient='list'))
# NOTE: initialize data source with empty dict that has the dict keys
# that I know are in the database - should maybe make more dynamic and just initialize to empty data source?
batchSource = ColumnDataSource(data={'time': [], 'temperature': [], 'id': []})
epochDate = pd.to_datetime("1/1/1970")

def modify_doc(doc):
    id = 0
    manualId = 0
    startDt = dfDict['time'][0].to_pydatetime()
    endDt = dfStatic['time'].iloc[-1].to_pydatetime()
    # plot used for continually adding points to graph
    # note: if want to manipulate axis ranges later on need to set some sort of starting range or else when
    # try to change via figure.x_range.start or figure.x_range.end will get weird incorrect behavior
    livePlot = figure(x_axis_type='datetime', x_range=[startDt, endDt], y_range=(0,25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    livePlot.line('time', 'temperature', source=source)
    # plot that just loads all sample data in at once
    staticPlot = figure(x_axis_type='datetime', x_range=[startDt, endDt], y_range=(0,25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    staticPlot.line(x='time',y='temperature', source=staticSource)
    manualUpdatePlot = figure(x_axis_type='datetime', x_range=[startDt, endDt], y_range=(0,1),y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43", sizing_mode='stretch_both')
    manualUpdatePlot.line(x='time', y='temperature', source=batchSource)
    # currently not using DatePicker as seems to give weird error (potentially browser related. Come back
    # to fix potentially. Also not using DaterangeSlider becuse couldn't get the increments to be
    # small enough to make sense to use
    # note: the value attribute must be of type string
    textStart = TextInput(value=str(startDt), title='Month/Date/year HH:MM')
    textEnd = TextInput(value=str(endDt), title='Month/Date/year HH:MM')
    nextButton = Button(label='Go to Next Period')
    jumpInput = TextInput(value=str(startDt), title='Type Month/Date/year HH:MM to jump to')
    manualUpdateButton = Button(label='update graph')

    def updateStartDate(attr, old, new):
        # updates the static plot's beginning x axis range. Note even though the plot is a datetime plot
        # I need to convert it to a float whose value is the microseconds since the epoch 1/1/1970. (microseconds
        # required as this is rendered using javascript and that uses microseconds
        newDate = pd.to_datetime(new)
        msecondsFromEpoch = float((newDate-epochDate).total_seconds()*1000)
        if msecondsFromEpoch > staticPlot.x_range.end:
            pass
        else:
            staticPlot.x_range.start = float(msecondsFromEpoch)

    def updateEndDate(attr, old, new):
        # same logic as updateStartDate
        newDate = pd.to_datetime(new)
        msecondsFromEpoch = float((newDate-epochDate).total_seconds()*1000)
        if msecondsFromEpoch < staticPlot.x_range.start:
            pass
        else:
            staticPlot.x_range.end = float(msecondsFromEpoch)

    def nextPeriod():
        """Button onclick method that shifts the graph to the next 'period'. A 'period' is determined
        by the dates seen in the beginning and end date text inputs. The next 'period' starts one microsecond
        after the current end of xaxis range. Also, updates the textinputs of all relevant textinputs that
        have dates to match what the user is seeing"""
        newStartFloat = staticPlot.x_range.end + 1
        periodDuration = staticPlot.x_range.end - staticPlot.x_range.start
        newEndFloat = newStartFloat + periodDuration
        staticPlot.x_range.start = newStartFloat
        staticPlot.x_range.end = newEndFloat
        # note: need to do integer divison by 1000 since we multiplied by 1000 to make into microseconds
        # to make it compatible for the javascript needed for the bokeh graph ranges but now
        # datetime python only does seconds so need to convert back
        # note: using utcfromtimestamp vs just fromtimestamp to stay consistent with pandas converting to utc
        textStart.value = datetime.utcfromtimestamp(newStartFloat // 1000).strftime("%Y-%m-%d %H:%M:%S")
        textEnd.value = datetime.utcfromtimestamp(newEndFloat // 1000).strftime("%Y-%m-%d %H:%M:%S")
        jumpInput.value = textStart.value

    def jumpTo(attr, old, new):
        """on change method for the 'jump to' input text box. Used to jumped to desired date
        maintains current time interval duration"""
        newDate = pd.to_datetime(new)
        msecondsFromEpoch = float((newDate-epochDate).total_seconds()*1000)
        currentTimeRange = staticPlot.x_range.end - staticPlot.x_range.start
        newEndFloat = msecondsFromEpoch + currentTimeRange
        staticPlot.x_range.start = msecondsFromEpoch
        staticPlot.x_range.end = newEndFloat
        # note: using utcfromtimestamp vs just fromtimestamp to stay consistent with pandas converting to utc
        textStart.value = datetime.utcfromtimestamp(msecondsFromEpoch // 1000).strftime("%Y-%m-%d %H:%M:%S")
        textEnd.value = datetime.utcfromtimestamp(newEndFloat // 1000).strftime("%Y-%m-%d %H:%M:%S")

    def callback():
        # periodic callback method. just adds one piece of new data from data base
        nonlocal id
        id += 1
        updateDf = pd.read_sql_query('SELECT * from {} WHERE id={};'.format(table_name, id), cursor)
        updateDf['time'] = pd.to_datetime(updateDf['time'])
        newDataDict = updateDf.to_dict(orient='list')
        source.stream(newDataDict)

    def manualUpdate():
        # the onclick method when the manual update button is pressed read the DB and get the next 10 rows
        nonlocal manualId
        global batchSource
        df = pd.read_sql_query('SELECT * FROM {} WHERE id>= {} LIMIT 10'.format(table_name, manualId), cursor)
        # need to translate to datetime or else bokeh graph doesn't handle it correctly
        df['time'] = pd.to_datetime(df['time'])
        dfDict = df.to_dict(orient='list')
        someKey = list(batchSource.data.keys())[0]
        print(batchSource.data[someKey])
        manualUpdatePlot.y_range.start = 0
        manualUpdatePlot.y_range.end = 25
        manualUpdatePlot.x_range.start = staticPlot.x_range.start
        manualUpdatePlot.x_range.end = staticPlot.x_range.end
        batchSource.stream(dfDict)

        manualId += 10

    textStart.on_change('value', updateStartDate)
    textEnd.on_change('value', updateEndDate)
    nextButton.on_click(nextPeriod)
    jumpInput.on_change('value', jumpTo)
    manualUpdateButton.on_click(manualUpdate)
    widget = widgetbox(textStart)
    widget2 = widgetbox(textEnd)
    widget3 = widgetbox(nextButton)
    widget4 = widgetbox(jumpInput)
    widget5 = widgetbox(manualUpdateButton)
    realTimeTab = Panel(child=livePlot, title="Real Time")
    staticTab = Panel(child=column(row(widget, widget2, widget3, widget4), staticPlot), title="Static")
    manualTab = Panel(child=column(widget5, manualUpdatePlot), title='Manual', sizing_mode='stretch_both')
    # uncomment out the below 2 lines to get the 'live plotting' tab to work (given that you have also
    # downloaded the seaSurface.sqlite file)
    # doc.add_root(livePlot)
    # doc.add_periodic_callback(callback, 10)
    tabs = Tabs(tabs=[realTimeTab, staticTab, manualTab], sizing_mode='stretch_both')
    doc.add_root(tabs)

graphing_App = Application(FunctionHandler(modify_doc))

def startBokehServer():
    bokeh_server = Server({"/app": graphing_App}, allow_websocket_origin=["localhost:6543"])
    bokeh_server.start()
    bokeh_server.io_loop.start()