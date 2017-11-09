from pyramid.view import view_config
from bokeh.embed import server_document
from .. import bokehAppTest

@view_config(route_name='bokeh_app', renderer='../templates/plot.jinja2')
def bokeh_view(request):
    script = server_document('http://localhost:5006/app')
    return {'script': script, 'framework': "Pyramid"}