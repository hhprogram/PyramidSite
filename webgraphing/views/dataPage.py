from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from ..models import MyModel

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///C:\\Users\\Harrison\\Documents\\SqlLiteExample\\example.db')
Base = declarative_base(engine)

class DataTable(Base):
    __tablename__ = 'stocks'
    __table_args__ = {'autoload': True}


@view_config(route_name='DataPage', renderer='../templates/dataTemplate.jinja2')
def dataView(request):
    Session = sessionmaker(bind=engine) #creates an object bounded to database underlying ENGINE. But an actual active session not created until instantiation
    session = Session() #note i have to construct an instance of the Session object before I can call query on it
    result = session.query(DataTable).filter(DataTable.symbol=='RHAT').first()
    return {'label': 'Data Page!!!', 'price': result.price}
