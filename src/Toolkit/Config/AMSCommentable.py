import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSConfigException
from Toolkit.Config import AbstractAMSConfig, AMSConfigModelAttribute

class AMSCommentable(AbstractAMSConfig):
    """
       This class defines a comment
       """

    def __init__(self):
        AbstractAMSConfig.__init__(self)
        self.confluence_comment = None  # type: str
        self.details = None  # type: str
        self.runbook_sub_link = None  # type: str

    def _set_config_model_attributes(self):
        """
        This method sets the configuration attributes for each applicable member variable as an instance of AMSConfigModelAttribute
        :return: Returns true upon success or Exception upon error.
        :rtype: bool
        """
        AbstractAMSConfig._set_config_model_attributes(self)

        # Comment for documentation
        confluence_comment_attrs = AMSConfigModelAttribute()
        confluence_comment_attrs.set_required(False)
        confluence_comment_attrs.set_default(None)
        confluence_comment_attrs.set_label('Comment for Confluence documentation')
        confluence_comment_attrs.set_type('str')
        confluence_comment_attrs.set_mapped_class_variable('confluence_comment')
        self.config_model_attributes['confluence_comment'] = confluence_comment_attrs

        # Comment for documentation
        details_attrs = AMSConfigModelAttribute()
        details_attrs.set_required(False)
        details_attrs.set_default(None)
        details_attrs.set_label('Details for JIRA tickets')
        details_attrs.set_type('str')
        details_attrs.set_mapped_class_variable('details')
        self.config_model_attributes['details'] = details_attrs

        # Runbook Sub Link
        runbook_sub_link_attrs = AMSConfigModelAttribute()
        runbook_sub_link_attrs.set_required(False)
        runbook_sub_link_attrs.set_default(None)
        runbook_sub_link_attrs.set_label('Specific runbook link?')
        runbook_sub_link_attrs.set_type('str')
        runbook_sub_link_attrs.set_mapped_class_variable('runbook_sub_link')
        self.config_model_attributes['runbook_sub_link'] = runbook_sub_link_attrs

    def load(self, *args):
        """
        :param config_dict: List of strings to search for
        :type config_dict: dict
        :return: True on success, exception on failure.
        :rtype: bool
        """

        try:
            AbstractAMSConfig.load(self, args)
            self._read_string('confluence_comment')
            self._read_string('details')
            self._read_string('runbook_sub_link')
        except Exception as e:
            raise AMSConfigException(e)
