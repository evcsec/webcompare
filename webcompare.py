import requests, time, configparser, os, difflib, sys, argparse, hashlib, pickle
from datetime import datetime
import datetime as regDatetime
from bs4 import BeautifulSoup
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw
from selenium import webdriver
import selenium as se
from pathlib import Path
from shutil import copyfile
from emailAlert import EmailAlert


class ScrapeTheWorld:

    '''

        [current] Standard Process flow:

        ScrapeTheWorld()
            -> __init__
                -> start_monitor()                      | Starts the monitoring process, loops through each host
                    -> start_scan()                     | If a host passes their set last scan interval, invoke scans
                        -> do_md5_check()               | ** First main scan, compares current hash to last hash **
                            -> get_web_contents()       | Saves web contents similarly to curl
                            -> get_md5()                | Calculate md5 for comparison
                            -> get_differences()        | Uses difflib to compare differences in soup,
                                                                Purely for alert report (soup is more human readable)

                        -> ScreenAnalysis()             | ** Second main scan, compares before/after screenshots **
                            -> setup()                  | Set up selenium webdriver
                            -> capture_screens()
                                -> screenshot()         | Take a screenshot with the defined settings
                            -> analyse()                | Analyse each image (define grid)
                                -> process_region()     | Process defined regions (grids)

    '''

    CONFIG = configparser.ConfigParser()  # init config
    main_dir_name = 'scan_data'
    DEBUG = True
    visscan_timestamp = None
    before_scrn_location = None
    result_scrn_location = None
    detected_change = None
    soup_changes_detected = []
    alert_sens = 20  # Define the visual percent change before sending email alert

    def __init__(self):

        print(' __      __      ___.   _________                                            ')
        print('/  \    /  \ ____\_ |__ \_   ___ \  ____   _____ ___________ _______   ____  ')
        print('\   \/\/   // __ \| __ \/    \  \/ /  _ \ /     \\\____ \__  \\\_  __ \_/ __ \ ')
        print(' \        /\  ___/| \_\ \     \___(  <_> )  Y Y  \  |_> > __ \|  | \/\  ___/ ')
        print('  \__/\  /  \___  >___  /\______  /\____/|__|_|  /   __(____  /__|    \___  >')
        print('       \/       \/    \/        \/             \/|__|       \/            \/ ')
        print('created by @snags141 and @evcsec')

        self.init_ini()  # initialise config

        args = self.parse_args()

        if args.addtargets:
            self.add_targets()  # run add targets
        else:
            if args.listtargets:
                self.print_all_targets()
            else:  # Run as normal
                self.start_monitor()  # start the monitoring process

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Use -a to quickly add targets to the config file')
        parser.add_argument('-a', '--addtargets', action='store_true', help='Add host targets to the config file')
        parser.add_argument('-l', '--listtargets', action='store_true', help='List current target host names')
        args = parser.parse_args()

        return args

    # write config file
    def write_file(self):
        self.CONFIG.write(open('config.ini', 'w'))

    def init_ini(self):

        if not os.path.exists("./" + self.main_dir_name):  # Check for main directory
            os.mkdir('./' + self.main_dir_name)

        # if doesnt exist, write default
        if not os.path.exists('config.ini'):
            self.add_targets()
        else:
            self.CONFIG.read("config.ini")

    def print_all_targets(self):
        print('\nCurrent Targets:')
        # Loop through CONFIG and print section titles
        for each_section in self.CONFIG.sections():
            print(' - '+each_section)

    def add_targets(self):

        flag = 'y'

        while flag == 'y' or flag == 'Y':
            host_name = self.set_host_name()

            url = self.set_url()

            interval = self.set_interval()

            self.CONFIG[host_name] = {'target_url': url, 'interval_time': interval, 'last_scan': ""}
            self.write_file()

            print('\nAdd another target? y/n')
            flag = input('> ')

    def set_url(self):

        valid = False

        url = input('Please enter a target URL (incl. http(s)://)\n> ')

        while valid is False:

            val = URLValidator()

            try:
                val(url)
                if val:
                    valid = True

            except ValidationError:
                if url == '':
                    url = input('Please enter a target URL (incl. http(s)://)\n> ')
                else:
                    print('URL is not valid\n')
                    url = input('Please enter a valid URL (incl. http(s)://)\n> ')

        return url

    def validate_url(self, url):
        valid = False

        val = URLValidator()

        try:
            val(url)
            if val:
                valid = True
        except ValidationError:
            if url == '':
                print('URL is blank\n')
            else:
                print('URL is not valid\n')

        return valid

    def set_interval(self):  # Set the interval_time (int minutes) to check the site
        usrInput = input("How long between scans? (minutes):\n> ")

        return usrInput

    def get_target_count(self):

        count = 0

        for each_section in self.CONFIG.sections():
            count += 1

        return count

    def set_host_name(self):

        valid = False

        host_name = input('Enter a name for this host\n> ')

        while not valid:

            # check if host_name already exists
            if self.CONFIG.has_section(host_name):
                print('A host with this name already exists\nPlease enter something else\n> ')
            # If not, proceed, if so, do nothing
            else:
                valid = True

        if not os.path.exists('./' + self.main_dir_name + '/' + host_name):  # check for host folder
            os.mkdir('./' + self.main_dir_name + '/' + host_name)

        return host_name

    def get_current_datetime(self):
        today = regDatetime.datetime.today()
        current_time = today.strftime('%Y-%m-%d %H:%M:%S')

        return current_time

    def get_time_diff(self, last_scan):

        current_time = self.get_current_datetime()

        fmt = '%Y-%m-%d %H:%M:%S'
        d1 = datetime.strptime(last_scan, fmt)  # '2018-11-09 6:00:00'
        d2 = datetime.strptime(current_time, fmt)

        # Convert to Unix timestamp
        d1_ts = time.mktime(d1.timetuple())
        d2_ts = time.mktime(d2.timetuple())

        # They are now in seconds, subtract and then divide by 60 to get minutes.
        time_difference = int(d2_ts - d1_ts) / 60  # Time difference in minutes

        return time_difference

    def get_web_contents(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}  # set the headers like we are a browser

        response = requests.get(url, headers=headers)  # download the homepage

        return response.text  # content

    def get_md5(self, file_path):

        with open(file_path, "r") as f:
            md5 = hashlib.md5(f.read().encode('utf-8')).hexdigest()
            # md5 = hashlib.md5(file_path.encode('utf-8')).hexdigest()

        return md5

    def print_differences(self, prev_soup, current_soup):
        print('prev_soup: ' + prev_soup)
        print('current_soup: ' + current_soup)

        with open(prev_soup, 'r') as prev_soup:
            with open(current_soup, 'r') as current_soup:
                diff = difflib.unified_diff(
                    prev_soup.readlines(),
                    current_soup.readlines(),
                    fromfile='prev_soup',
                    tofile='current_soup',
                )
                for line in diff:
                    sys.stdout.write(line)
                    changes = self.soup_changes_detected
                    if changes is not None:
                        changes.append(line)
                    pass

    def do_md5_check(self, host_name, url):

        # Get contents, write to txt
        hash_compare_dir = './' + self.main_dir_name + '/' + host_name + '/hashcompare'
        host_dir_check = './' + self.main_dir_name + '/' + host_name
        # Check that directories exists, if not create
        if not os.path.exists(host_dir_check):
            os.mkdir(host_dir_check)
        if not os.path.exists(hash_compare_dir):
            os.mkdir(hash_compare_dir)

        file_dir = hash_compare_dir + '/web_contents_'+time.strftime("%Y-%m-%d_%H-%M")+'.txt'
        fmain = open(file_dir, 'w')
        fmain.write(self.get_web_contents(url))
        fmain.close()
        # Generate md5
        new_md5 = self.get_md5(file_dir)
        print('Getting MD5 of ' + file_dir)

        # compare with prev if exists, if not write to prev_md5.txt and soup (for future comparison)
        hash_file_dir = hash_compare_dir + '/prev_hash.txt'
        if not Path(hash_file_dir).is_file():
            if self.DEBUG: print('DEBUG: prev_md5 does not exist, creating')
            f = open(hash_file_dir, 'w')
            f.write(new_md5)
            f.close()
            if self.DEBUG: print('DEBUG: creating soup: prev_soup')
            soup = BeautifulSoup(open(file_dir), "html.parser")  # parse the downloaded homepage and grab all text
            f = open(hash_compare_dir + '/prev_soup', 'w')
            f.write(soup.text)
            f.close()
        else:
            if self.DEBUG: print('DEBUG: prev_md5 already exists, comparing')
            f = open(hash_file_dir, 'r')
            prev_hash = f.readline()
            if new_md5 == prev_hash:
                if self.DEBUG:
                    print('DEBUG: md5\'s are the same')
            else:
                if self.DEBUG:
                    print('DEBUG: md5\'s are NOT the same')

                    self.get_soup_differences(file_dir, hash_compare_dir)

                    # alert and now update the prev_md5
                    f = open(hash_file_dir, 'w')
                    f.write(new_md5)
                    f.close()
            f.close()

    def get_soup_differences(self, file_dir, hash_compare_dir):
        soup = BeautifulSoup(open(file_dir), "html.parser")  # parse the downloaded homepage and grab all text, was lxml
        f = open(hash_compare_dir + "/current_soup", "w")
        f.write(soup.text)
        f.close()
        soup_diff = self.print_differences(hash_compare_dir + '/prev_soup', hash_compare_dir + '/current_soup')

        # Now make current_soup prev_soup for next comparison
        copyfile(hash_compare_dir + '/current_soup', hash_compare_dir + '/prev_soup')

    def update_config_section(self, section,target_url, interval_time, last_scan):
        self.CONFIG[section] = {'target_url': target_url, 'interval_time': interval_time,
                                     'last_scan': last_scan}
        self.write_file()

    def start_scan(self, host_name, url):  # Initiate a scan on the given URL

        self.do_md5_check(host_name, url)  # Compare hashes, returns soup_diff

        ScreenAnalysis(self, host_name, url, self.main_dir_name)  # start screen analysis

        if self.detected_change is not None:
            if self.detected_change > self.alert_sens:
                EmailAlert.send_email_alert(self, host_name, self.soup_changes_detected, self.visscan_timestamp,
                                            self.detected_change, self.result_scrn_location)
                # Reset all for next scan
                self.soup_changes_detected = None
                self.visscan_timestamp = None
                self.detected_change = None
                self.before_scrn_location = None
                self.result_scrn_location = None
            else:
                print("detected change is less than 20: "+str(self.detected_change))

    def set_percent_change(self, perc_change, prev_scrn, result_scrn, timestamp):

        if self.DEBUG: print("passed % change to main class: " + str(perc_change))

        self.detected_change = perc_change
        self.before_scrn_location = prev_scrn
        self.result_scrn_location = result_scrn
        self.visscan_timestamp = timestamp


    def start_monitor(self):  # Start monitoring the target URL

        while 1 == 1:

            print('*Monitor started: running every 5 seconds*')
            time.sleep(5)

            for each_section in self.CONFIG.sections():

                target_url = self.CONFIG.get(each_section, 'target_url')

                interval_time = self.CONFIG.get(each_section, 'interval_time')

                last_scan = self.CONFIG.get(each_section, 'last_scan')

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
                    if self.DEBUG: print('Doing first time scan')
                    self.start_scan(each_section, target_url)
                    self.update_config_section(each_section, target_url, interval_time, self.get_current_datetime())
                else:
                    if int(self.get_time_diff(last_scan)) >= int(interval_time):
                        self.start_scan(each_section, target_url)
                        self.update_config_section(each_section, target_url, interval_time, self.get_current_datetime())
                    else:
                        if self.DEBUG: print('not doing scan')


            print('Waiting ...\n')


class ScreenAnalysis:

    BEFORE_URL = None
    scrn_filepath = None
    driver = None
    MAIN_DIR_NAME = None
    host_name = None
    DEBUG = True

    # Used to for alert check
    detected_change = None
    result_dir = None

    def __init__(self, original_self, host_name, target_url, main_dir_name):
        self.MAIN_DIR_NAME = main_dir_name
        self.HOST_NAME = host_name
        self.BEFORE_URL = target_url
        self.AFTER_URL = 'No longer in use'  # Before and after in-case we want to compare two different targets
        self.SCRN_COMPARE_DIR = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare'  # Path to current work dir
        self.PREV_SCRN = self.SCRN_COMPARE_DIR + '/prev_scrn.png'  # The last screenshot taken in history
        self.current_scan_directory = ''
        self.current_scan_timestamp = ''
        self.stw_original_self = original_self  # store reference to original self for returning vars

        self.set_up()
        prev_file_name = self.capture_screen()

        if Path(self.PREV_SCRN).is_file():
            self.analyse(self.HOST_NAME)

        if Path(self.PREV_SCRN).is_file():
            copyfile(self.PREV_SCRN, self.SCRN_COMPARE_DIR + '/' + self.current_scan_timestamp + '/' + 'PREV_' + prev_file_name)
        copyfile(self.SCRN_COMPARE_DIR + '/' + self.current_scan_timestamp + '/'+prev_file_name, self.PREV_SCRN)  # copy current to prev_scrn for next cmp

        self.check_for_alert()

        self.clean_up()

    def set_up(self):
        web_options = se.webdriver.ChromeOptions()
        web_options.add_argument('headless')
        se.driver = se.webdriver.Chrome(options=web_options)

    def clean_up(self):
        se.driver.close()

    def capture_screen(self):
        if not os.path.exists(self.SCRN_COMPARE_DIR):
            os.mkdir(self.SCRN_COMPARE_DIR)

        self.current_scan_timestamp = time.strftime("%Y-%m-%d_%H-%M")
        self.current_scan_directory = './' + self.MAIN_DIR_NAME + '/' + self.HOST_NAME + '/scrncompare/' + self.current_scan_timestamp
        os.mkdir(self.current_scan_directory)

        file_name = 'SCRN_'+time.strftime("%Y-%m-%d_%H-%M")+'.png'
        self.screenshot(self.BEFORE_URL, file_name)
        # self.screenshot(self.AFTER_URL, 'AFTER_'+time.strftime("%Y-%m-%d_%H-%M")+'.png', host_name, 'after')

        return file_name

    def screenshot(self, url, file_name):
        print("\nCapturing", url, "screenshot as", file_name, "...")
        se.driver.set_window_size(1024, 768)
        se.driver.get(url)
        # se.driver.set_window_size(1920, 1080)

        self.scrn_filepath = self.SCRN_COMPARE_DIR + '/' + self.current_scan_timestamp + '/' + file_name
        time.sleep(2)  # Delay screenshot due to load times & animations on some sites
        se.driver.save_screenshot(self.scrn_filepath)

        print("Done.")

    def analyse(self, host_name):

        screenshot_current = Image.open(self.scrn_filepath)  # staging
        screenshot_prev = Image.open(self.PREV_SCRN)  # production

        columns = 60
        rows = 80
        screen_width, screen_height = screenshot_current.size

        block_width = ((screen_width - 1) // columns) + 1  # this is just a division ceiling
        block_height = ((screen_height - 1) // rows) + 1

        arr = []

        for y in range(0, screen_height, block_height+1):
            for x in range(0, screen_width, block_width+1):
                region_staging = self.process_region(screenshot_current, x, y, block_width, block_height)
                region_production = self.process_region(screenshot_prev, x, y, block_width, block_height)

                if region_staging is not None and region_production is not None and region_production != region_staging:
                    draw = ImageDraw.Draw(screenshot_current)
                    draw.rectangle((x, y, x+block_width, y+block_height), outline = "red")
                    arr.append([x, y])

        selenium_last_dir = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/selenium_last'

        if not Path(selenium_last_dir).is_file():
            if self.DEBUG: print('Writing file dump...')
            with open(selenium_last_dir, 'wb') as f:
                pickle.dump(arr, f)
                if self.DEBUG: print("Wrote arr to file with len of: "+str(len(arr)))

                log_file = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'
                log = open(log_file, "a")
                log.write(host_name + ' | ' + self.current_scan_timestamp + ' | ' + 'selenium file does not exist, creating...' +' | ' + 'Wrote to file with length:' + str(len(arr)) + '\n')
                log.close()
        else:
            if self.DEBUG: print('Reading file dump...')
            with open(selenium_last_dir, 'rb') as f:
                selenium_prev_arr = pickle.load(f)

                totalcount = len(selenium_prev_arr)
                if self.DEBUG: print('Read totalcount: '+str(totalcount))
                pod = [filter(lambda x: x in selenium_prev_arr, sublist) for sublist in arr] # compare points of difference

                changed_points_vs_prev = str(len(pod))+'/'+str(totalcount)
                print('Changed points detected vs prev scan: '+ changed_points_vs_prev)

                if self.DEBUG: print('Deleting file dump...')
                os.remove(selenium_last_dir)

                if self.DEBUG: print('Saving new file dump...')
                with open(selenium_last_dir, 'wb') as f:
                    pickle.dump(arr, f)
                    if self.DEBUG: print('Saved new pickle dump with len: '+str(len(arr)))

                increase = abs(len(pod) - totalcount)  # len(pod) = current change detect points, totalcount = previous
                if totalcount != 0:
                    self.detected_change = (increase / totalcount) * 100
                else:
                    # If previous count == 0 due to no previous change, we cannot calculate change %'age.
                    # Thus we are using a rough calculation that will result in a huge %'age, but will easily indicate this activity
                    if increase != 0:
                        self.detected_change = increase * 10

                if self.detected_change is None:
                    print("detected change is 'None'")
                else:
                    print("detected change is: "+ str(self.detected_change))

                # Append results to master log (per host)
                log_file = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'
                log = open(log_file, "a")
                log.write(host_name + ' | ' + str(self.current_scan_timestamp) + ' | ' + 'Points Changed: ' + str(changed_points_vs_prev) + ' | ' + 'Change %: ' + str(self.detected_change) + '\n')
                log.close()



        #  New result save in current dir
        self.result_dir = self.current_scan_directory + '/result_' + time.strftime(
            "%Y-%m-%d_%H-%M") + '.png'

        screenshot_current.save(self.result_dir)

        ScrapeTheWorld.set_percent_change(self.stw_original_self, self.detected_change, self.PREV_SCRN, self.result_dir, self.current_scan_timestamp)

    def process_region(self, image, x, y, width, height):
        region_total = 0

        # This can be used as the sensitivity factor, the larger it is the less sensitive the comparison
        factor = 250  # Default 100

        for coordinateY in range(y, y+height):
            for coordinateX in range(x, x+width):
                try:
                    pixel = image.getpixel((coordinateX, coordinateY))
                    region_total += sum(pixel)/4
                except:
                    return

        return region_total/factor

    def check_for_alert(self):
        # Check if over a threshold
        print('\nChecking for alert')
        print('Found:'+str(self.detected_change)+'% difference')
        print('***\n\n')

        pass



ScrapeTheWorld()
