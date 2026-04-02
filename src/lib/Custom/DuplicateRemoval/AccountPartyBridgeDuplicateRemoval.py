# @author owhoyt

import os.path, sys, subprocess

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../../../"))
sys.path.append(APP_PATH)

from lib.Exceptions import DuplicateRemovalException
from lib.Custom.Models import AccountPartyBridge

from AbstractDuplicateRemoval import AbstractDuplicateRemoval

class AccountPartyBridgeDuplicateRemoval(AbstractDuplicateRemoval):
    # noinspection PyUnresolvedReferences
    """
    This class removes duplicates from the Account Party Bridge File.
    :type objects_to_remove: list[AccountPartyBridge]
    """

    def __init__(self, debug=False):
        """ Instantiates an AccountPartyBridgeDuplicateRemoval object
        :param debug: bool
        :return: AccountPartyBridgeDuplicateRemoval
        """
        AbstractDuplicateRemoval.__init__(self, debug)
        self.set_new_data_object('AccountPartyBridge')
        self.set_duplicate_removal_routine_friendly_name('account party bridge primary owner')

    def set_new_data_object(self, data_object_str):
        self.data_object = str(data_object_str).strip()
        return True

    def set_duplicate_removal_routine_friendly_name(self, name):
        self.duplicate_removal_routine_friendly_name = name.strip()

    def _execute_remove_duplicates(self):
        for duplicate_value, dup_dict in self.duplicates_found.iteritems():
            for line_number in dup_dict['lines']:
                if duplicate_value not in self.object_dict:
                    self.object_dict[duplicate_value] = []
                apb = self.get_new_data_object()
                apb.init_from_row(self.get_line_from_file(line_number), line_number)
                self._print_msg('apb.get_str_to_remove(): ' + apb.get_str_to_remove())
                self.strings_to_grep.append(apb.get_str_to_remove())
                self.object_dict[duplicate_value].append(apb)

        self.generate_grep_string()
        self.find_supp_acct()
        self.generate_dup_remove_grep_string()
        self._execute_dup_removal()
        # 1.  grep -n "637221|748406|99|SUPP ACCT\|637221|716536|99|SUPP ACCT\|2253244|2555523|99|SUPP ACCT\|2253244|2698478|99|SUPP ACCT\|1377157|1559430|99|SUPP ACCT\|1377157|1638771|99|SUPP ACCT\|1881162|2134007|99|SUPP ACCT\|1881162|2998382|99|SUPP ACCT\|3896286|4408942|99|SUPP ACCT\|3896286|4954351|99|SUPP ACCT\|1740498|2017418|99|SUPP ACCT\|1740498|1974521|99|SUPP ACCT\|539015|669699|99|SUPP ACCT\|539015|603778|99|SUPP ACCT" file.20161217.2001.prod.can.wmcb.acct_party_bridge_20161216.txt | cut -d ':' -f 1
        # 2. figure out how to find which supp accounts match up with primary owners
        # 3. generate new grep string to remove the appropriate primary accunts
        # 4. remove accounts by createing new file as grep -v new grep string > new file.
        # 5. regenerate manifest, throw new type of exception to skip the file
        # 6. next time around, it should pick up new file.
        # 7. generate diff report
        # 8. put diff report in outbound folder
        # 9. send email on diff report.

    def find_supp_acct(self):
        grep_list = ['grep', '-n', self.grep_string, self.orig_file]
        grep = subprocess.Popen(grep_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        grep_std_out, grep_std_err = grep.communicate()
        if grep_std_err:
            raise DuplicateRemovalException('Error in find_supp_act(): ' + grep_std_err.strip())
        grep_std_out = grep_std_out.strip()
        self._print_msg('grep_std_out: ' + grep_std_out)
        supp_account_lines_list = grep_std_out.split("\n")
        if len(supp_account_lines_list) < 1 or not grep_std_out:
            raise DuplicateRemovalException('['+str(self)+'] No Supp Account info found for duplicates - cannot remove automatically')

        for supp_account_line in supp_account_lines_list:
            line_number, supp_account_info = supp_account_line.strip().split(':')
            self._print_msg('supp_account_info: ' + supp_account_info)
            self._print_msg('line_number: ' + str(line_number))
            if not supp_account_info or not line_number:
                raise DuplicateRemovalException('Invalid Supp Account info found for duplicates - cannot remove automatically')
            apb = self.get_new_data_object()  # type: AccountPartyBridge
            apb.init_from_row(supp_account_info, line_number)

            dup_key_info = apb.get_dupe_key_info()
            if dup_key_info not in self.object_dict:
                self.add_error(dup_key_info, 'Invalid dupe key found when searching for Supp Account info')
            dupe_found = False
            for primary_apb in self.object_dict[dup_key_info]:  # type: AccountPartyBridge
                # if primary_apb.party_number =
                if primary_apb.party_number == apb.party_number:
                    dupe_found = True
                    self.objects_to_remove.append(primary_apb)

            if not dupe_found:
                self.add_error(dup_key_info, 'Could not find matching primary party record to remove')

        if len(self.objects_to_remove) < 1:
            raise DuplicateRemovalException('Could not find any appropriate duplicates to remove.')

        if len(self.get_errors()) > 0:
            raise DuplicateRemovalException('Found errors when trying to remove duplicates:' + os.linesep + self.format_errors())

    def generate_grep_string(self):
        if len(self.strings_to_grep) < 1:
            self.grep_string = ''
            return self.grep_string

        self.grep_string = "\\|".join(self.strings_to_grep)
        return self.grep_string

    def generate_dup_remove_grep_string(self):
        self.grep_string_dup_remove = ''
        for apb in self.objects_to_remove:
            if self.grep_string_dup_remove == '':
                pass
            else:
                self.grep_string_dup_remove += '\\|'
            self.grep_string_dup_remove += apb.create_row_from_obj()

        return self.grep_string_dup_remove