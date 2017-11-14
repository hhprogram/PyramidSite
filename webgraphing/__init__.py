from pyramid.config import Configurator
from webgraphing import bokehAppTest
from threading import Thread

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.include('.models')
    config.include('.routes')
    config.scan()
    Thread(target=bokehAppTest.startBokehServer).start()
    return config.make_wsgi_app()