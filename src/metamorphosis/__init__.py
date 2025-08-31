
from svlearn.config.configuration import ConfigurationMixin

from dotenv import load_dotenv
load_dotenv()

config = ConfigurationMixin().load_config()
