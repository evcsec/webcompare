import pickle, os, time
from pathlib import Path
from PIL import Image, ImageDraw
from selenium import webdriver
import selenium as se
from shutil import copyfile
from lib.logger import *


class ScreenAnalysis(object):

    BEFORE_URL = None
    scrn_filepath = None
    driver = None
    MAIN_DIR_NAME = 'scan_data'
    host_name = None

    # migrated from  webcompare.py
    visscan_timestamp = None
    before_scrn_location = None
    result_scrn_location = None
    detected_change = None

    # Used to for alert check
    detected_change = None
    result_dir = None

    def __init__(self, host_name, target_url):
        self.HOST_NAME = host_name
        self.BEFORE_URL = target_url
        self.AFTER_URL = 'No longer in use'  # Before and after in-case we want to compare two different targets
        self.SCRN_COMPARE_DIR = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare'  # Path to current work dir
        self.PREV_SCRN = self.SCRN_COMPARE_DIR + '/prev_scrn.png'  # The last screenshot taken in history
        self.current_scan_directory = ''
        self.current_scan_timestamp = ''

        self.set_up()
        prev_file_name = self.capture_screen()

        if Path(self.PREV_SCRN).is_file():
            self.analyse(self.HOST_NAME)

        if Path(self.PREV_SCRN).is_file():
            copyfile(self.PREV_SCRN,
                     self.SCRN_COMPARE_DIR + '/' + self.current_scan_timestamp + '/' + 'PREV_' + prev_file_name)
        copyfile(self.SCRN_COMPARE_DIR + '/' + self.current_scan_timestamp + '/' + prev_file_name,
                 self.PREV_SCRN)  # copy current to prev_scrn for next cmp

        self.check_for_alert()

        self.clean_up()

        vars_to_return = [self.visscan_timestamp, self.detected_change, self.result_scrn_location]

        return vars_to_return

    def set_up(self):
        web_options = se.webdriver.ChromeOptions()
        web_options.add_argument('headless')
        se.driver = se.webdriver.Chrome(options=web_options)

    def clean_up(self):
        se.driver.close()
        # Reset all for next scan
        self.visscan_timestamp = None
        self.detected_change = None
        self.before_scrn_location = None
        self.result_scrn_location = None

    def capture_screen(self):
        if not os.path.exists(self.SCRN_COMPARE_DIR):
            os.mkdir(self.SCRN_COMPARE_DIR)

        self.current_scan_timestamp = time.strftime("%Y-%m-%d_%H-%M")
        self.current_scan_directory = './' + self.MAIN_DIR_NAME + '/' + self.HOST_NAME + '/scrncompare/' + self.current_scan_timestamp
        os.mkdir(self.current_scan_directory)

        file_name = 'SCRN_' + time.strftime("%Y-%m-%d_%H-%M") + '.png'
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

    def check_for_alert(self):
        # Check if over a threshold
        print('\nChecking for alert')
        print('Found:' + str(self.detected_change) + '% difference')
        print('***\n\n')

        pass

    def analyse(self, host_name):

        screenshot_current = Image.open(self.scrn_filepath)  # staging
        screenshot_prev = Image.open(self.PREV_SCRN)  # production

        columns = 60
        rows = 80
        screen_width, screen_height = screenshot_current.size

        block_width = ((screen_width - 1) // columns) + 1  # this is just a division ceiling
        block_height = ((screen_height - 1) // rows) + 1

        arr = []

        for y in range(0, screen_height, block_height + 1):
            for x in range(0, screen_width, block_width + 1):
                region_staging = self.process_region(screenshot_current, x, y, block_width, block_height)
                region_production = self.process_region(screenshot_prev, x, y, block_width, block_height)

                if region_staging is not None and region_production is not None and region_production != region_staging:
                    draw = ImageDraw.Draw(screenshot_current)
                    draw.rectangle((x, y, x + block_width, y + block_height), outline="red")
                    arr.append([x, y])
                    print("Points: " + str(x) + str(y))

        selenium_last_dir = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/selenium_last'

        if not Path(selenium_last_dir).is_file():
            with open(selenium_last_dir, 'wb') as f:
                pickle.dump(arr, f)

                log_file = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'
                message1 = 'selenium file does not exist, creating...'
                message2 ='Wrote to file with length: ' + str(len(arr))
                Logger(log_file, host_name, self.current_scan_timestamp, message1, message2)
        else:
            with open(selenium_last_dir, 'rb') as f:
                selenium_prev_arr = pickle.load(f)

                totalcount = len(selenium_prev_arr)
                pod = [filter(lambda x: x in selenium_prev_arr, sublist) for sublist in
                       arr]  # compare points of difference

                changed_points_vs_prev = str(len(pod)) + '/' + str(totalcount)
                print('Changed points detected vs prev scan: ' + changed_points_vs_prev)

                os.remove(selenium_last_dir)

                with open(selenium_last_dir, 'wb') as f:
                    pickle.dump(arr, f)

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
                    print("detected change is: " + str(self.detected_change))

                # Append results to master log (per host)
                log_file = './' + self.MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'
                message1 = 'Points Changed: ' + str(changed_points_vs_prev)
                message2 = 'Change %: ' + str(self.detected_change)
                Logger(log_file, host_name, self.current_scan_timestamp, message1, message2)

        #  New result save in current dir
        self.result_dir = self.current_scan_directory + '/result_' + time.strftime(
            "%Y-%m-%d_%H-%M") + '.png'

        screenshot_current.save(self.result_dir)

        self.set_percent_change(self.detected_change, self.PREV_SCRN, self.result_dir,
                                          self.current_scan_timestamp)

    def set_percent_change(self, perc_change, prev_scrn, result_scrn, timestamp):

        self.detected_change = perc_change
        self.before_scrn_location = prev_scrn
        self.result_scrn_location = result_scrn
        self.visscan_timestamp = timestamp

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
