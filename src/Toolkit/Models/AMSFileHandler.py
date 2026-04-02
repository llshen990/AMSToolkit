from Toolkit.Lib.FileHandler.AMSFileHandler import AMSFileHandler
from Toolkit.Models.AbstractAMSBase import AbstractAMSBase

class AMSFileHandlerModel(AbstractAMSBase):

    def __init__(self, ams_config, file_handler_name):

        AbstractAMSBase.__init__(self, ams_config)
        self.ams_config = ams_config
        self.ams_file_handler = None
        self.ams_file_handler_config = self.AMSConfig.get_file_handler_by_name(file_handler_name)  # type:AMSFileHandler

    def execute_file_handler(self):
        self.ams_file_handler = AMSFileHandler(self.ams_file_handler_config, self.ams_config)
        self.ams_file_handler.evaluate_file_handler()
