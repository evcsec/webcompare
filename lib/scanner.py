from lib.screen_analysis_new import start_analysis
from lib.emailAlert import send_email_alert

# imports for do_md5_check and it's functions
import os, time, hashlib, difflib, sys, requests
from bs4 import BeautifulSoup
from pathlib import Path
from shutil import copyfile


def start_scan(host_name, url):  # Initiate a scan on the given URL

    print("********************************************************************")

    MAIN_DIR_NAME = 'scan_data'

    soup_changes_detected = do_md5_check(host_name, url)  # Compare hashes, returns soup_diff

    detected_vars = start_analysis(host_name, url)  # start screen analysis
            #  main_dir_name main_dir required above

    visscan_timestamp = detected_vars[0]
    detected_change = detected_vars[1]
    result_scrn_location = detected_vars[2]

    # result_srn_loc & visscan

    if detected_change is not None and detected_change != 0:
        send_email_alert(host_name, soup_changes_detected, visscan_timestamp,
                                    detected_change, result_scrn_location)


# do_md5_check code and it's following functions
def do_md5_check(host_name, url):

    MAIN_DIR_NAME = 'scan_data'

    # Get contents, write to txt
    hash_compare_dir = './' + MAIN_DIR_NAME + '/' + host_name + '/hashcompare'
    host_dir_check = './' + MAIN_DIR_NAME + '/' + host_name
    # Check that directories exists, if not create
    if not os.path.exists(host_dir_check):
        os.mkdir(host_dir_check)
    if not os.path.exists(hash_compare_dir):
        os.mkdir(hash_compare_dir)

    file_dir = hash_compare_dir + '/web_contents_'+time.strftime("%Y-%m-%d_%H-%M")+'.txt'
    fmain = open(file_dir, 'w', encoding='Latin-1', errors='ignore')  # Encode in Latin-1 to avoid unmapped char errors
    fmain.write(str(get_web_contents(url)))
    fmain.close()
    # Generate md5
    new_md5 = get_md5(file_dir)
    print('Getting MD5 of ' + file_dir)

    # compare with prev if exists, if not write to prev_md5.txt and soup (for future comparison)
    hash_file_dir = hash_compare_dir + '/prev_hash.txt'
    if not Path(hash_file_dir).is_file():
        f = open(hash_file_dir, 'w')
        f.write(new_md5)
        f.close()
        soup = BeautifulSoup(open(file_dir), "html.parser")  # parse the downloaded homepage and grab all text
        f = open(hash_compare_dir + '/prev_soup', 'w')
        f.write(soup.text)
        f.close()
    else:
        f = open(hash_file_dir, 'r')
        prev_hash = f.readline()
        if new_md5 == prev_hash:
                print('DEBUG: md5\'s are the same')
                soup_changes_detected = "No changes"
        else:
                print('DEBUG: md5\'s are NOT the same')

                soup_changes_detected = get_soup_differences(file_dir, hash_compare_dir)

                # alert and now update the prev_md5
                f = open(hash_file_dir, 'w')
                f.write(new_md5)
                f.close()
        f.close()

    return soup_changes_detected

def get_web_contents(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}  # set the headers like we are a browser

    response = requests.get(url, headers=headers)  # download the homepage

    return str(response.text)  # content


def get_md5(file_path):

    with open(file_path, "r") as f:
        md5 = hashlib.md5(f.read().encode('utf-8')).hexdigest()
        # md5 = hashlib.md5(file_path.encode('utf-8')).hexdigest()

    return md5


def get_soup_differences(file_dir, hash_compare_dir):
    soup = BeautifulSoup(open(file_dir), "html.parser")  # parse the downloaded homepage and grab all text, was lxml
    f = open(hash_compare_dir + "/current_soup", "w")
    f.write(soup.text)
    f.close()

    soup_changes_detected = [""]

    prev_soup = hash_compare_dir + '/prev_soup'
    current_soup = hash_compare_dir + '/current_soup'
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
                soup_changes_detected.append(line)
                pass

    # Now make current_soup prev_soup for next comparison
    copyfile(hash_compare_dir + '/current_soup', hash_compare_dir + '/prev_soup')

    return soup_changes_detected
