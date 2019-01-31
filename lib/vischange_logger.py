import time


class VisChangeLogger(object):
    def __init__(self, log_path, host_name, values):
        timestamp = time.strftime("%Y-%m-%d_%H-%M")
        log = open(log_path, "a")
        log.write(
            host_name + ' | ' + timestamp + 'Logging visual changes detected' + '\n')
        log.write("x    y")

        for i in values:
            #log.write("" + str(i[0]) + + str(i[1]))
            pass

        log.close()
