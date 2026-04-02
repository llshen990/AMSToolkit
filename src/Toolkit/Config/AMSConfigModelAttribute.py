import os, sys

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../"))
sys.path.append(APP_PATH)

from Toolkit.Exceptions import AMSConfigModelAttributeException
from lib.Helpers import OutputFormatHelper



class AMSConfigModelAttribute(object):

    def __init__(self):
        self.required = True  # type: bool
        self.default = None
        self.share_value = False
        self.label = None  # type: str
        self.type = None  # type: str
        self.options = None  # type: dict or list
        self.new_value = None
        self.num_required_entries = 0
        self.max_allowed_entries = -1
        self.allow_edit = True
        self.linked_label = None  # type: str
        self.linked_object = None  # type: str
        self.linked_type = None  # type: str
        self.return_map_to_variable = None  # type: str
        self.mapped_class_variable = None  # type: str
        self.return_transform = None  # type: str
        self.include_in_config_file = True
        self.is_config_dict_key = False
        self.__allowed_return_transforms = [
            'str_to_list',
            'str_to_tuple',
            'abspath',
            'encrypt'
        ]
        self.dependent_variable = None  # type: str
        self.hide_from_user_display = False
        self.dependent_value = []

    def set_required(self, val):
        """
        This method validates input and sets the required member variable.
        :param val: The value that should set required member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """
        if not isinstance(val, bool):
            raise AMSConfigModelAttributeException('required attribute is expecting a bool type: True|False.')

        self.required = val

        return True

    def set_default(self, val):
        """
        This method validates input and sets the default member variable.  Since the default could be anything, there is not validation currently.
        :param val: The value that should set default member variable.
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        self.default = val

        return True

    def set_label(self, val):
        """
        This method validates input and sets the label member variable.
        :param val: The value that should set label member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('label attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('label attribute is expecting a str type.')

        self.label = str(val).strip()

        return True

    def set_linked_label(self, val):
        """
        This method validates input and sets the linked_label member variable.
        :param val: The value that should set linked_label member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('linked_label attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('linked_label attribute is expecting a str type.')

        self.linked_label = str(val).strip()

        return True

    def set_type(self, val):
        """
        This method validates input and sets the type member variable.
        :param val: The value that should set type member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('type attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('type attribute is expecting a str type.')

        self.type = str(val).strip()

        return True

    def set_options(self, val):
        """
        This method validates input and sets the options member variable.
        :param val: The value that should set options member variable.
        :type val: dict|list
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('options attribute value required.')

        if not isinstance(val, dict) and not isinstance(val, list):
            raise AMSConfigModelAttributeException('options attribute is expecting a dict or list type.')

        self.options = val

        return True

    def set_num_required_entries(self, val):
        """
        This method validates input and sets the num_required_entries member variable.
        :param val: The value that should set num_required_entries member variable.
        :type val: int
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not isinstance(val, int):
            raise AMSConfigModelAttributeException('num_required_entries attribute is expecting a int type.')

        if val < 0:
            raise AMSConfigModelAttributeException('num_required_entries attribute is expecting an int >= 0.')

        self.num_required_entries = val

        return True

    def set_max_allowed_entries(self, val):
        """
        This method validates input and sets the max_allowed_entries member variable.
        :param val: The value that should set max_allowed_entries member variable.
        :type val: int
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not isinstance(val, int):
            raise AMSConfigModelAttributeException('max_allowed_entries attribute is expecting a int type.')

        if val < 0:
            raise AMSConfigModelAttributeException('max_allowed_entries attribute is expecting an int >= 0.')

        self.max_allowed_entries = val

        return True

    def set_linked_object(self, val):
        """
        This method validates input and sets the linked_object member variable.
        :param val: The value that should set linked_object member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('linked_object attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('linked_object attribute is expecting a str type.')

        self.linked_object = str(val).strip()

        return True

    def set_linked_type(self, val):
        """
        This method validates input and sets the linked_type member variable.
        :param val: The value that should set linked_type member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('linked_type attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('linked_type attribute is expecting a str type.')

        self.linked_type = str(val).strip()

        return True

    def set_return_map_to_variable(self, val):
        """
        This method validates input and sets the return_map_to_variable member variable.
        :param val: The value that should set return_map_to_variable member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('return_map_to_variable attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('return_map_to_variable attribute is expecting a str type.')

        self.return_map_to_variable = str(val).strip()

        return True

    def set_allow_edit(self, val):
        """
        This method validates input and sets the required allow_edit variable.
        :param val: The value that should set allow_edit member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """
        if not isinstance(val, bool):
            raise AMSConfigModelAttributeException('allow_edit attribute is expecting a bool type: True|False.')

        self.allow_edit = val

        return True

    def set_share_value(self, val):
        """
        This method validates input and sets the optional share_value variable.
        :param val: The value that should set share_value member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """
        if not isinstance(val, bool):
            raise AMSConfigModelAttributeException('share_value attribute is expecting a bool type: True|False.')

        self.share_value = val

        return True

    def set_mapped_class_variable(self, val):
        """
        This method validates input and sets the mapped_class_variable member variable.
        :param val: The value that should set mapped_class_variable member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('mapped_class_variable attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('mapped_class_variable attribute is expecting a str type.')

        self.mapped_class_variable = str(val).strip()

        return True

    def set_include_in_config_file(self, val):
        """
        This method validates input and sets the include_in_config_file member variable.
        :param val: The value that should set include_in_config_file member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not isinstance(val, bool):
            raise AMSConfigModelAttributeException('include_in_config_file attribute is expecting a bool type.')

        self.include_in_config_file = val

        return True

    def set_return_transform(self, val):
        """
        This method validates input and sets the return_transform member variable.
        :param val: The value that should set return_transform member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('return_transform attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('return_transform attribute is expecting a str type.')

        return_transform_tmp = str(val).strip()
        if return_transform_tmp not in self.__allowed_return_transforms:
            raise AMSConfigModelAttributeException('return_transform attribute can be: ' + OutputFormatHelper.join_output_from_list(self.__allowed_return_transforms))

        self.return_transform = str(val).strip()

        return True

    def set_dependent_variable(self, val):
        """
        This method validates input and sets the dependent_variable member variable.
        :param val: The value that should set dependent_variable member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('dependent_variable attribute value required.')

        if not isinstance(val, str):
            raise AMSConfigModelAttributeException('dependent_variable attribute is expecting a str type.')

        self.dependent_variable = str(val).strip()

        return True

    def set_dependent_value(self, val):
        """
        This method validates input and sets the dependent_value member variable.
        :param val: The value that should set dependent_value member variable.
        :type val: str
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if not val:
            raise AMSConfigModelAttributeException('dependent_value attribute value required.')

        val = str(val).strip()

        if val not in self.dependent_value:
            self.dependent_value.append(val)

        return True

    def set_is_config_dict_key(self, val):
        """
        This method validates input and sets the is_config_dict_key member variable.
        :param val: The value that should set is_config_dict_key member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """

        if val:
            self.is_config_dict_key = True
        else:
            self.is_config_dict_key = False

        return True

    def is_dependent_variable(self):
        """
        This method will validate whether or not this property is dependent on another variable and it's cooresponding value.
        :return: True upon dependent, False if not dependent.
        :rtype: bool
        """

        if self.dependent_variable:
            return True

        return False

    def is_dependency_met(self, dependent_val):
        """
        This method will determine if the dependent value has met the conditions set as a dependency.
        :type dependent_val: str
        :rtype: bool
        """
        if dependent_val in self.dependent_value:
            return True

        return False

    def set_hide_from_user_display(self, val):
        """
        This method validates input and sets the hide_from_user_display variable.
        :param val: The value that should set hide_from_user_display member variable.
        :type val: bool
        :return: True upon success, exception upon error.
        :rtype: bool
        """
        if not isinstance(val, bool):
            raise AMSConfigModelAttributeException('hide_from_user_display attribute is expecting a bool type: True|False.')

        self.hide_from_user_display = val

        return True