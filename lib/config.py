import os, configparser, validators


class Config(object):
    CONFIG = configparser.ConfigParser()  # init config
    MAIN_DIR_NAME = 'scan_data'

    def __init__(self):
        # if doesnt exist, write default

        if not os.path.exists('./config.ini'):
            self.set_targets()
        else:
            self.CONFIG.read("./config.ini")

        if not os.path.exists("./" + self.MAIN_DIR_NAME):  # Check for main directory
            os.mkdir('./' + self.MAIN_DIR_NAME)

    def get_config(self):
        config = configparser.ConfigParser()
        config.read("./config.ini")
        return config

    def print_all_targets(self):
        print('\nCurrent Targets:')
        # Loop through CONFIG and print section titles
        for each_section in self.CONFIG.sections():
            print(' - ' + each_section)

    def add_host(self, host, target_url, interval_time, last_scan):
        self.CONFIG[host] = {'target_url': target_url, 'interval_time': interval_time, 'last_scan': last_scan}
        self.write_file()

    def set_targets(self):

        while True:
            host = input("Enter a name for this host\n> ")

            # Check if exists
            if self.CONFIG.has_section(host):
                print('A host with this name already exists\nPlease enter something else\n> ')
            else:
                # Create new entry
                url = input('Please enter a target URL://)\n> ')
                if validators.url(url):
                    interval_time = input("How long between scans? (minutes):\n> ")

            self.add_host(host, url, interval_time, "")

            add_more = input('Would you like to add another host? (y/n)')
            if add_more.lower() != "y":
                break

    def get_target_count(self):

        count = 0

        for each_section in self.CONFIG.sections():
            count += 1

        return count

    def write_file(self):
        self.CONFIG.write(open('config.ini', 'w'))

    def print_targets(self):
        print('\nCurrent Targets:')
        # Loop through CONFIG and print section titles
        for each_section in self.CONFIG.sections():
            print(' - ' + each_section)

    def update_config(self, host, target_url, interval_time, last_scan):
        var_config = configparser.ConfigParser()  # init config
        var_config[host] = {'target_url': target_url, 'interval_time': interval_time,
                               'last_scan': last_scan}
        var_config.write_file()

    def validate_url(url):
        if validators.url(url):
            return True
        else:
            return False

    def update_config_section(self, section, target_url, interval_time, last_scan):
        var_config = configparser.ConfigParser()  # init config
        var_config[section] = {'target_url': target_url, 'interval_time': interval_time,
                                     'last_scan': last_scan}
        var_config.write(open('config.ini', 'w'))
