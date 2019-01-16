#!/usr/bin/python

from lib.input import ArgumentHandler
import sys
from lib.config import Config
from lib.monitor import Monitor


class WebCompare:

    '''

        [current] Standard Process flow:

        ScrapeTheWorld()
            -> __init__
                -> start_monitor()                      | Starts the monitoring process, loops through each host
                    -> start_scan()                     | If a host passes their set last scan interval, invoke scans
                        -> do_md5_check()               | ** First main scan, compares current hash to last hash **
                            -> get_web_contents()       | Saves web contents similarly to curl
                            -> get_md5()                | Calculate md5 for comparison
                            -> print_differences()        | Uses difflib to compare differences in soup,
                                                                Purely for alert report (soup is more human readable)

                        -> ScreenAnalysis()             | ** Second main scan, compares before/after screenshots **
                            -> setup()                  | Set up selenium webdriver
                            -> capture_screens()
                                -> screenshot()         | Take a screenshot with the defined settings
                            -> analyse()                | Analyse each image (define grid)
                                -> process_region()     | Process defined regions (grids)

    '''

    def __init__(self):

        self.print_banner()

        Config()  # init config

        parser = ArgumentHandler()

        arguments = parser.parse(sys.argv[1:])

        if arguments is not None:
            if arguments.a:
                Config.set_targets()  # run add targets
            else:
                if arguments.l:
                    Config.print_all_targets()
                else:  # Run as normal
                    Monitor()  # start the monitoring process

    def print_banner(self):
        print("""                                                                                         
                                            _/    _/                                    
       _/_/_/  _/_/      _/_/    _/_/_/        _/_/_/_/    _/_/_/  _/    _/  _/  _/_/   
      _/    _/    _/  _/    _/  _/    _/  _/    _/      _/    _/  _/    _/  _/_/        
     _/    _/    _/  _/    _/  _/    _/  _/    _/      _/    _/  _/    _/  _/           
    _/    _/    _/    _/_/    _/    _/  _/      _/_/    _/_/_/    _/_/_/  _/            

        A web monitoring tool created by @snags141 and @evcsec
        """)


WebCompare()
