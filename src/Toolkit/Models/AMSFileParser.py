from Toolkit.Models.AbstractAMSBase import AbstractAMSBase
from Toolkit.Lib.FileParser.AMSFileParser import AMSFileParser

class AMSFileParserModel(AbstractAMSBase):

    def __init__(self, ams_config, parser_name):

        AbstractAMSBase.__init__(self, ams_config)

        self.ams_config = ams_config
        self.file_parser_obj = None
        self.parser_name = parser_name

    def execute_file_parser(self):
        self.file_parser_obj = AMSFileParser(self.ams_config, self.parser_name)
        self.file_parser_obj.evaluate_file_parser()
