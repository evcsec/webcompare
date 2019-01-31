import pickle, os, time
from pathlib import Path
from PIL import Image, ImageDraw
from selenium import webdriver
import selenium as se
from shutil import copyfile
from lib.logger import *
from lib.vischange_logger import VisChangeLogger
driver = None


# migrated from  webcompare.py

# Used to for alert check
result_dir = None


def start_analysis(host_name, target_url):

    MAIN_DIR_NAME = 'scan_data'
    current_scan_timestamp = time.strftime("%Y-%m-%d_%H-%M")
    host_name = host_name
    before_url = target_url
    SCRN_COMPARE_DIR = './' + MAIN_DIR_NAME + '/' + host_name + '/scrncompare'  # Path to current work dir
    PREV_SCRN = SCRN_COMPARE_DIR + '/prev_scrn.png'  # The last screenshot taken in history
    set_up()
    returned_vars = capture_screen(host_name, before_url, SCRN_COMPARE_DIR, MAIN_DIR_NAME, current_scan_timestamp)
    analyse_return_vars = None
    prev_file_name = returned_vars[0]
    scrn_filepath = returned_vars[1]
    current_scan_directory = returned_vars[2]
    vars_to_return = None

    if Path(PREV_SCRN).is_file():
        analyse_return_vars = analyse(host_name, scrn_filepath, MAIN_DIR_NAME, PREV_SCRN, current_scan_directory, current_scan_timestamp)

    if Path(PREV_SCRN).is_file():
        copyfile(PREV_SCRN,
                 SCRN_COMPARE_DIR + '/' + current_scan_timestamp + '/' + 'PREV_' + prev_file_name)
    copyfile(SCRN_COMPARE_DIR + '/' + current_scan_timestamp + '/' + prev_file_name,
             PREV_SCRN)  # copy current to prev_scrn for next cmp

    clean_up()

    if analyse_return_vars is not None:
        vars_to_return = [analyse_return_vars[1], analyse_return_vars[0], analyse_return_vars[2]]

    return vars_to_return


def set_up():
    web_options = se.webdriver.ChromeOptions()
    web_options.add_argument('headless')
    se.driver = se.webdriver.Chrome(options=web_options)


def clean_up():
    se.driver.close()


def capture_screen(host_name, before_url, SCRN_COMPARE_DIR, MAIN_DIR_NAME, current_scan_timestamp):
    if not os.path.exists(SCRN_COMPARE_DIR):
        os.mkdir(SCRN_COMPARE_DIR)

    # need to add check if already exists
    current_scan_directory = './' + MAIN_DIR_NAME + '/' + host_name + '/scrncompare/' + current_scan_timestamp
    os.mkdir(current_scan_directory)

    file_name = 'SCRN_' + time.strftime("%Y-%m-%d_%H-%M") + '.png'
    scrn_filepath = screenshot(before_url, file_name, SCRN_COMPARE_DIR, current_scan_timestamp)

    return_vars = [file_name, scrn_filepath, current_scan_directory]

    return return_vars


def screenshot(url, file_name, SCRN_COMPARE_DIR, current_scan_timestamp):
    print("\nCapturing", url, "screenshot as", file_name, "...")
    se.driver.set_window_size(1024, 768)
    se.driver.get(url)
    # se.driver.set_window_size(1920, 1080)

    scrn_filepath = SCRN_COMPARE_DIR + '/' + current_scan_timestamp + '/' + file_name
    time.sleep(2)  # Delay screenshot due to load times & animations on some sites
    se.driver.save_screenshot(scrn_filepath)

    print("Done.")

    return scrn_filepath


def analyse(host_name, scrn_filepath, MAIN_DIR_NAME, PREV_SCRN, current_scan_directory, current_scan_timestamp):

    screenshot_current = Image.open(scrn_filepath)  # staging
    screenshot_prev = Image.open(PREV_SCRN)  # production
    detected_change = None
    columns = 60
    rows = 80
    screen_width, screen_height = screenshot_current.size

    block_width = ((screen_width - 1) // columns) + 1  # this is just a division ceiling
    block_height = ((screen_height - 1) // rows) + 1

    arr = []

    for y in range(0, screen_height, block_height + 1):
        for x in range(0, screen_width, block_width + 1):
            region_staging = process_region(screenshot_current, x, y, block_width, block_height)
            region_production = process_region(screenshot_prev, x, y, block_width, block_height)

            if region_staging is not None and region_production is not None and region_production != region_staging:
                draw = ImageDraw.Draw(screenshot_current)
                draw.rectangle((x, y, x + block_width, y + block_height), outline="red")
                arr.append([x, y])

    VisChangeLogger('./change-reg.txt', host_name, arr)
    selenium_last_dir = './' + MAIN_DIR_NAME + '/' + host_name + '/scrncompare/selenium_last'

    if not Path(selenium_last_dir).is_file():
        with open(selenium_last_dir, 'wb') as f:
            pickle.dump(arr, f)

            log_file = './' + MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'

            message1 = 'selenium file does not exist, creating...'
            message2 = 'Wrote to file with length:'
            Logger(log_file, host_name, current_scan_timestamp, message1, message2)
    else:
        with open(selenium_last_dir, 'rb') as f:
            selenium_prev_arr = pickle.load(f)
            detected_change = 0
            totalcount = len(selenium_prev_arr)
            pod = [filter(lambda x: x in selenium_prev_arr, sublist) for sublist in
                   arr]  # compare points of difference

            changed_points_vs_prev = str(len(pod)) + '/' + str(totalcount)
            print('Changed points detected vs prev scan: ' + changed_points_vs_prev)

            #os.remove(selenium_last_dir)

            with open(selenium_last_dir, 'wb') as f:
                pickle.dump(arr, f)

            increase = abs(len(pod) - totalcount)  # len(pod) = current change detect points, totalcount = previous
            if totalcount != 0:
                detected_change = (increase / totalcount) * 100
            else:
                # If previous count == 0 due to no previous change, we cannot calculate change %'age.
                # Thus we are using a rough calculation that will result in a huge %'age, but will easily indicate this activity
                if increase != 0:
                    detected_change = increase * 10

            if detected_change is None:
                print("detected change is 'None'")
            else:
                print("detected change is: " + str(detected_change))

            # Append results to master log (per host)
            log_file = './' + MAIN_DIR_NAME + '/' + host_name + '/scrncompare/log.txt'
            message1 = 'Points Changed: ' + str(changed_points_vs_prev)
            message2 = 'Change %: ' + str(detected_change)
            Logger(log_file, host_name, current_scan_timestamp, message1, message2)

    #  New result save in current dir
    result_dir = current_scan_directory + '/result_' + time.strftime(
        "%Y-%m-%d_%H-%M") + '.png'

    screenshot_current.save(result_dir)

    set_percent_change(detected_change, PREV_SCRN, result_dir,
                                      current_scan_timestamp)

    analyse_return_vars = [detected_change, current_scan_timestamp, result_dir]

    return analyse_return_vars

def set_percent_change(perc_change, prev_scrn, result_scrn, timestamp):

    detected_change = perc_change
    before_scrn_location = prev_scrn
    result_scrn_location = result_scrn
    visscan_timestamp = timestamp


def process_region(image, x, y, width, height):
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
