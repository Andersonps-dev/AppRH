import sys

path = '/home/appLuftextrema/AppRH'
if path not in sys.path:
    sys.path.append(path)
from app import app as application