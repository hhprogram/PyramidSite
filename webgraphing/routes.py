def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('DataPage','/DataPage')
    config.add_route('bokeh_app', '/bokehGraph')
    config.add_route('bokeh_AJAX', '/bokehAJAX')
    config.add_route('bokeh_AJAX2', '/bokehAJAX2')
    config.add_route('data', '/AJAXdata')
    config.add_route('data2', '/AJAXdata2')
