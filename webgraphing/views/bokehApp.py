from pyramid.view import view_config
from bokeh.embed import server_document
from .. import bokehAppTest
from threading import Thread

@view_config(route_name='bokeh_app', renderer='../templates/plot.jinja2')
def bokeh_view(request):
    # note: starting the thread in the view each time will restart the
    # bokeh server. Ok for now, it does fix the fact that when I previously had the thread.start()
    # in the init file when I refreshed the bokeh_app webpage there would be a bokeh error
    # i think due to fact bokeh was trying to create another doc on the same localhost location
    Thread(target=bokehAppTest.startBokehServer).start()
    script = server_document('http://localhost:5006/app')
    return {'script': script, 'framework': "Pyramid"}