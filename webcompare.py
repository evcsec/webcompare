import requests, time, configparser, os, smtplib, difflib, sys, arrow, argparse, hashlib
from bs4 import BeautifulSoup
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw
from selenium import webdriver
import selenium as se
from pathlib import Path


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

    def __init__(self):
        print('  ____  _____ ______          __  _     _____       _            _   ')
        print(' Web Compare, created by @snags141 and @evcsec ')

        if os.getuid() == 0:
            self.init_ini()  # initialise config

            args = self.parse_args()

            if args.addtargets:
                self.add_targets()  # run add targets
            else:
                if args.listtargets:
                    self.print_all_targets()
                else:  # Run as normal
                    self.start_monitor()  # start the monitoring process
        else:
            print('*Error: Not runnning as root*')



    def parse_args(self):
        parser = argparse.ArgumentParser(description='Use -a to easily add targets to the config file')
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

        while flag != 'n' and 'N':
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
        tmp = int(usrInput) * 60  # convert minutes string input to seconds
        usrInput = '%d' % tmp

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

    def send_alert(self):  # Changes have been detected, compare current and previous soup, then send alert

        with open('prev_soup', 'r') as prev_soup:
            with open('current_soup', 'r') as current_soup:
                diff = difflib.unified_diff(
                    prev_soup.readlines(),
                    current_soup.readlines(),
                    fromfile='prev_soup',
                    tofile='current_soup',
                )
                for line in diff:
                    sys.stdout.write(line)

    def get_web_contents(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}  # set the headers like we are a browser

        response = requests.get(url, headers=headers)  # download the homepage

        return response.text  # .content

    def get_md5(self, file):
        md5 = hashlib.md5(file.encode('utf-8')).hexdigest()

        return md5

    def print_differences(self, prev_soup, current_soup):
        with open(prev_soup, 'r') as prev_soup:
            with open(current_soup, 'r') as current_soup:
                diff = difflib.unified_diff(
                    prev_soup.readlines(),
                    prev_soup.readlines(),  # prev_soup test
                    fromfile='prev_soup',
                    tofile='current_soup',
                )
                for line in diff:
                    sys.stdout.write(line)
                    print('\n')

    def do_md5_check(self, host_name, url):

        # Get contents, write to txt
        hash_compare_dir = './' + self.main_dir_name + '/' + host_name + '/hashcompare'
        if not os.path.exists(hash_compare_dir):
            os.mkdir(hash_compare_dir)

        file_dir = hash_compare_dir + '/web_contents_'+time.strftime("%Y-%m-%d_%H-%M")+'.txt'
        fmain = open(file_dir, 'w')
        fmain.write(self.get_web_contents(url))


        # Generate md5
        new_md5 = self.get_md5(file_dir)

        # compare with prev if exists, if not write to prev_md5.txt and soup (for future comparison)
        hash_match = False
        hash_file_dir = hash_compare_dir + '/prev_hash.txt'
        if not Path(hash_file_dir).is_file():
            print('DEBUG: prev_md5 does not exist, creating')
            f = open(hash_file_dir, 'w')
            f.write(new_md5)
            f.close()
            print('DEBUG: creating soup: prev_soup.txt')
            soup = BeautifulSoup(fmain.read, "lxml")  # parse the downloaded homepage and grab all text
            f = open(hash_compare_dir + '/prev_soup.txt', 'w')
            f.write(soup.text)
            f.close()
        else:
            print('DEBUG: prev_md5 already exists, comparing')
            f = open(hash_file_dir, 'r')
            if new_md5 == f.read():
                print('DEBUG: md5\'s are the same')
                hash_match = True
            else:
                print('DEBUG: md5\'s are NOT the same')
            f.close()

        # If different, beautify & difflib differences
        if not hash_match:
            soup = BeautifulSoup(file_dir, "lxml")  # parse the downloaded homepage and grab all text
            f = open(hash_compare_dir+"/current_soup", "w")
            f.write(soup.text)
            f.close()
            self.print_differences(hash_compare_dir+'/prev_soup.txt', hash_compare_dir+'/current_soup')

        fmain.close()

    def send_email(self):
        '''
                        # create an email message with just a subject line,
                        msg = 'Subject: Blah blah blah'
                        # set the 'from' address,
                        fromaddr = 'YOUR_EMAIL_ADDRESS'
                        # set the 'to' addresses,
                        toaddrs = ['AN_EMAIL_ADDRESS', 'A_SECOND_EMAIL_ADDRESS', 'A_THIRD_EMAIL_ADDRESS']

                        # setup the email server,
                        # server = smtplib.SMTP('smtp.gmail.com', 587)
                        # server.starttls()
                        # add my account login name and password,
                        # server.login("YOUR_EMAIL_ADDRESS", "YOUR_PASSWORD")

                        # Print the email's contents
                        print('From: ' + fromaddr)
                        print('To: ' + str(toaddrs))
                        print('Message: ' + msg)

                        # send the email
                        # server.sendmail(fromaddr, toaddrs, msg)
                        # disconnect from the server
                        # server.quit()

                        break
        '''

    def start_scan(self, host_name, url):  # Initiate a scan on the given URL

        self.do_md5_check(host_name, url)  # Compare hashes
        ScreenAnalysis(host_name, url, self.main_dir_name)  # start screen analysis

    def start_monitor(self):  # Start monitoring the target URL

        while 1 == 1:

            print('*Monitor started: running every 10 seconds*')
            time.sleep(10)

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

                if last_scan == '':  # OR if difference between last scan and current time is greater than interval
                    self.start_scan(each_section, target_url)

                # Compare previous timestamp with current time, if difference is greater than the scan interval then scan again
                # start_scan(the_hostname_to_scan)
                # Update timestamp

            print('Waiting ...')


class ScreenAnalysis:

    BEFORE_URL = 'http://www.yahoo.com'
    AFTER_URL = 'http://www.yahoo.com'
    before_filepath = None
    after_filepath = None
    driver = None
    MAIN_DIR_NAME = None
    host_name = None

    def __init__(self, host_name, target_url, main_dir_name):
        self.MAIN_DIR_NAME = main_dir_name
        self.host_name = host_name
        self.BEFORE_URL = target_url
        self.AFTER_URL = target_url  # Before and after in-case we want to compare two different targets

        self.set_up()
        self.capture_screens(self.host_name)
        self.analyse()
        self.clean_up()

    def set_up(self):
        web_options = se.webdriver.ChromeOptions()
        web_options.add_argument('headless')
        se.driver = se.webdriver.Chrome(options=web_options)

    def clean_up(self):
        se.driver.close()

    def capture_screens(self, host_name):
        self.screenshot(self.BEFORE_URL, 'BEFORE_'+time.strftime("%Y-%m-%d_%H-%M")+'.png', host_name, 'before')
        self.screenshot(self.AFTER_URL, 'AFTER_'+time.strftime("%Y-%m-%d_%H-%M")+'.png', host_name, 'after')

    def screenshot(self, url, file_name, host_name, scrn_order):
        print("\nCapturing", url, "screenshot as", file_name, "...")
        se.driver.get(url)
        se.driver.set_window_size(1024, 768)

        scrn_compare_dir = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare'

        if not os.path.exists(scrn_compare_dir):
            os.mkdir(scrn_compare_dir)

        if scrn_order == 'before':
            self.before_filepath = scrn_compare_dir + '/' + file_name
            se.driver.save_screenshot(self.before_filepath)
        else:
            if scrn_order == 'after':
                self.after_filepath = scrn_compare_dir + '/' + file_name
                se.driver.save_screenshot(self.after_filepath)

        print("Done.")

    def analyse(self):

        screenshot_staging = Image.open(self.before_filepath)
        screenshot_production = Image.open(self.after_filepath)

        columns = 60
        rows = 80
        screen_width, screen_height = screenshot_staging.size

        block_width = ((screen_width - 1) // columns) + 1 # this is just a division ceiling
        block_height = ((screen_height - 1) // rows) + 1

        for y in range(0, screen_height, block_height+1):
            for x in range(0, screen_width, block_width+1):
                region_staging = self.process_region(screenshot_staging, x, y, block_width, block_height)
                region_production = self.process_region(screenshot_production, x, y, block_width, block_height)

                if region_staging is not None and region_production is not None and region_production != region_staging:
                    draw = ImageDraw.Draw(screenshot_staging)
                    draw.rectangle((x, y, x+block_width, y+block_height), outline = "red")

        screenshot_staging.save('./' + self.MAIN_DIR_NAME + '/' + self.host_name + '/scrncompare/result_' + time.strftime("%Y-%m-%d_%H-%M") + '.png')

    def process_region(self, image, x, y, width, height):
        region_total = 0

        # This can be used as the sensitivity factor, the larger it is the less sensitive the comparison
        factor = 100

        for coordinateY in range(y, y+height):
            for coordinateX in range(x, x+width):
                try:
                    pixel = image.getpixel((coordinateX, coordinateY))
                    region_total += sum(pixel)/4
                except:
                    return

        return region_total/factor


ScrapeTheWorld()
