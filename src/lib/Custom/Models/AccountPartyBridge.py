import json

class AccountPartyBridge(object):
    """
    This class is an object for the account party bridge file.
    """

    def __init__(self):
        """
        :return: AccountPartyBridge
        """
        self.account_number = None
        self.party_number = None
        self.role_key = None
        self.role_description = None
        self.row_number = None
        self.separator = '|'
        self.inited = False
        self.primary_role_key = 1

    def init_from_row(self, row_data, row_number):
        """
        inits object from row of data.
        :param row_data: separator delimited row of data
        :param row_number: int row number
        :return:
        """
        row_list = row_data.split(self.separator)
        if len(row_list) < 4:
            raise Exception('Invalid data row')
        self.row_number = int(row_number)
        self.account_number = str(row_list[0]).strip()
        self.party_number = str(row_list[1]).strip()
        self.role_key = str(row_list[2]).strip()
        self.role_description = str(row_list[3]).strip()
        self.inited = True

    def get_dupe_key_info(self):
        return self.account_number + self.separator + str(self.primary_role_key)

    def get_str_to_remove(self):
        if not self.inited:
            raise Exception('Need to init ' + self.__class__.__name__ + ' before calling get_str_to_remove() method')

        return self.account_number + self.separator + self.party_number + self.separator + '99' + self.separator + 'SUPP ACCT'

    def create_row_from_obj(self):
        return self.account_number + self.separator + self.party_number + self.separator + self.role_key + self.separator + self.role_description

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)