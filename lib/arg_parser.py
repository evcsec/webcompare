import sys, argparse


class ParseArgs(object):

    def __init__(self):
        parser = ArgumentHandler()
        arguments = parser.parse(sys.argv[1:])

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
