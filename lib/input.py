from argparse import ArgumentParser

class ArgumentHandler(object):
    def __init__(self):
        self._parser = self.set_parser()

    def parse(self, argv):
        return self._parser.parse_args(argv)

    @staticmethod
    def set_parser():
        parser = ArgumentParser()

        parser.add_argument(
           "-a",
           action="store_true",
           help="Add host targets to the config file.") 
        
        parser.add_argument(
           "-l",
           action="store_true",
           help="List current target host names.")
        
        return parser
