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
from datetime import datetime

# denoted this as table_name. I create sqlite table separately in another program
# should change to be more dynamic
table_name = 'temperatures'
# using sqlalchemy to connect to it, easier to leverage pandas sql to df and back functions this way
# if have more queries might be an easier way to interface with db
cursor = create_engine('sqlite:///path/to/the/sqlite/db/with/sea_surface_temperature_data')
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
epochDate = pd.to_datetime("1/1/1970")

def modify_doc(doc):
    id = 0
    # plot used for continually adding points to graph
    livePlot = figure(x_axis_type='datetime', y_range=(0, 25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    livePlot.line('time', 'temperature', source=source)
    realTimeTab = Panel(child=livePlot, title="Real Time")
    startDt = dfDict['time'][0].to_pydatetime()
    endDt = dfStatic['time'].iloc[-1].to_pydatetime()
    # plot that just loads all sample data in at once
    staticPlot = figure(x_axis_type='datetime', x_range=[startDt, endDt], y_range=(0,25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    staticPlot.line(x='time',y='temperature', source=staticSource)
    # currently not using DatePicker as seems to give weird error (potentially browser related. Come back
    # to fix potentially. Also not using DaterangeSlider becuse couldn't get the increments to be
    # small enough to make sense to use
    # note: the value attribute must be of type string
    textStart = TextInput(value=str(startDt), title='Month/Date/year HH:MM')
    textEnd = TextInput(value=str(endDt), title='Month/Date/year HH:MM')
    nextButton = Button(label='Go to Next Period')
    jumpInput = TextInput(value=str(startDt), title='Type Month/Date/year HH:MM to jump to')

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

    textStart.on_change('value', updateStartDate)
    textEnd.on_change('value', updateEndDate)
    nextButton.on_click(nextPeriod)
    jumpInput.on_change('value', jumpTo)
    widget = widgetbox(textStart)
    widget2 = widgetbox(textEnd)
    widget3 = widgetbox(nextButton)
    widget4 = widgetbox(jumpInput)
    staticTab = Panel(child=column(row(widget, widget2, widget3, widget4), staticPlot), title="Static")

    def callback():
        nonlocal id
        id += 1
        updateDf = pd.read_sql_query('SELECT * from {} WHERE id={};'.format(table_name, id), cursor)
        updateDf['time'] = pd.to_datetime(updateDf['time'])
        newDataDict = updateDf.to_dict(orient='list')
        source.stream(newDataDict)
    # uncomment out the below 2 lines to get the 'live plotting' tab to work (given that you have also
    # downloaded the seaSurface.sqlite file)
    # doc.add_root(livePlot)
    # doc.add_periodic_callback(callback, 10)
    tabs = Tabs(tabs=[realTimeTab, staticTab])
    doc.add_root(tabs)


graphing_App = Application(FunctionHandler(modify_doc))

def startBokehServer():
    bokeh_server = Server({"/app": graphing_App}, allow_websocket_origin=["localhost:6543"])
    bokeh_server.start()
    bokeh_server.io_loop.start()