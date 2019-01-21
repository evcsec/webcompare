import time
from lib.scanner import start_scan
from lib.date import Date
from lib.config import Config
import re


class Monitor(object):

    each_section = None
    target_url = None

    def __init__(self):
        self.start_monitor()

    def start_monitor(self):  # Start monitoring the target URL

        config = Config.get_config(self)

        while 1 == 1:

            print('*Monitor started: running every 5 seconds*')
            time.sleep(5)

            for each_section in config.sections():

                target_url = config.get(each_section, 'target_url')

                interval_time = config.get(each_section, 'interval_time')

                last_scan = config.get(each_section, 'last_scan')

                # debug
                print('Target URL:')
                print(target_url)
                print('Interval Time:')
                print(interval_time)
                print('Last Scan:')
                print(last_scan)

                if not self.validate_url(target_url):
                    print('Error: URL %s' % target_url + ' is not valid')
                    break  # Quit program, config must have been changed outside of program

                if interval_time == '':
                    print('Error: not configured properly for %s' % target_url)
                    print('Missing interval_time')
                    break  # Quit program, config must have been changed outside of program

                if last_scan == '':
                    print('Doing first time scan')
                    start_scan(each_section, target_url)
                    Config.update_config_section(each_section, target_url, interval_time, Date.get_current_datetime())
                else:
                    if int(Date.get_time_diff(last_scan)) >= int(interval_time):
                        start_scan(each_section, target_url)
                        Config.update_config_section(each_section, target_url, interval_time, Date.get_current_datetime())

            print('Waiting ...\n')

    def validate_url(self, url):

        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if re.match(regex, url) is not None:
            valid = True
            
        return valid

    def get_each_section(self):
        return self.each_section

    def get_target_url(self):
        return self.target_url
