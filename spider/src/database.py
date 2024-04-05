from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import  MetaData
import yaml
import os
path_to_config = os.getenv('CONFIG_DIRECTORY')+'/'+'config.yaml'
with open(path_to_config, 'r') as file:
    config = yaml.safe_load(file)


class DBManager:
    def __init__(self):
        self.SQLALCHEMY_DATABASE_URL = None
        self.engine = None
        self.session_factory = None
        self.Base = None 

    def initialize(self):

        self.SQLALCHEMY_DATABASE_URL = f"postgresql://{config['DATABASE']['db_user']}:{config['DATABASE']['db_password']}@{config['DATABASE']['local_db_ip']}:{config['DATABASE']['port_db']}/{config['DATABASE']['db_name']}"
        self.engine = create_engine(self.SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_size=30,
                                          max_overflow=30, echo_pool=True, echo=False,
                                          pool_recycle=3600)  # recycle every hour

        metadata = MetaData()
        metadata.reflect(self.engine)
        Base = automap_base(metadata=metadata)
        Base.prepare()
        self.Base =  Base
        self.Session = sessionmaker(bind=self.engine)



