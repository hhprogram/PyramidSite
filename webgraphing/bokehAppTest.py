from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider
from bokeh.plotting import figure, curdoc
from bokeh.server.server import Server
from bokeh.themes import Theme
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server

from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature

def modify_doc(doc):
    df = sea_surface_temperature.copy()
    source = ColumnDataSource(data=df)

    plot = figure(x_axis_type='datetime', y_range=(0, 25), y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    plot.line('time', 'temperature', source=source)

    def callback(attr, old, new):
        if new == 0:
            data = df
        else:
            data = df.rolling('{0}D'.format(new)).mean()
        source.data = ColumnDataSource(data=data).data

    slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing by N Days")
    slider.on_change('value', callback)

    doc.add_root(column(slider, plot))

    # doc.theme = Theme(filename="theme.yaml")

graphing_App = Application(FunctionHandler(modify_doc))

def startBokehServer():
    bokeh_server = Server({"/app": graphing_App}, allow_websocket_origin=["localhost:6543"])
    bokeh_server.start()
    bokeh_server.io_loop.start()