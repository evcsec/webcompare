class Logger(object):
    def __init__(self, log_path, host_name, timestamp, message1, message2):
        log = open(log_path, "a")
        log.write(
            host_name + ' | ' + timestamp + ' | ' + message1 + ' | ' + message2 + '\n')
        log.close()
