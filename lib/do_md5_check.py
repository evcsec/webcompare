import os, time, hashlib, difflib, sys, requests
from bs4 import BeautifulSoup
from pathlib import Path
from shutil import copyfile


class DoMd5Check(object):

    MAIN_DIR_NAME = 'scan_data'

