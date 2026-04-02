#!/usr/bin/python

import os.path, sys, getopt, json, collections

MY_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../"))
sys.path.append(APP_PATH)

from lib.Validators import PresenceOfValidator, IntValidator, StrValidator, FileExistsValidator


# @author: owhoyt
# used to create a template for a JSON descriptor file.
# example python create_json_descriptor_file_template.py -f <filename> -c <num_cols>
# example help: python ssodETLProcess.py -h


def print_usage():
    """ This method will print the usage of the ssodETLProcess.py file
    :return: none
    """
    print '[USAGE1] python create_json_descriptor_file_template.py -f <filename> -c <num_cols>'
    print '[USAGE2] python create_json_descriptor_file_template.py --filename=<filename> --numcols=<num_cols>'
    sys.exit(2)


def _create_default_descriptor(file_name, num_cols):
    default_file_attribute = {
        "sample": False,
        "sampleRowCount": 0,
        "numColsInFile": num_cols,
        "headerCol": True,
        "minRowCount": 0,
        "maxRowCount": 99999,
        "allowEmpty": False,
        "expectedEncoding": "UTF-8",
        "delimiter": "|",
        "locale": "en_US",
        "decryptScriptPath": "decrypt.sh"
    }

    default_col_attribute = {
        "required": True,
        "validators": []
    }

    col_attributes = {}

    col_counter = 0
    while int(col_counter) < int(num_cols):
        print 'working on col ' + str(col_counter) + " / " + num_cols
        col_attributes[col_counter] = default_col_attribute
        col_counter += 1

    json_schema = collections.OrderedDict([("file", default_file_attribute), ("cols", col_attributes)])

    fo = open(file_name, "wb")
    fo.write(json.dumps(json_schema, indent=2, sort_keys=False))
    fo.close()
    return True


def main(argv):
    filename = ''
    numcols = -1
    try:
        opts, args = getopt.getopt(argv, "hf:c:", ["filename=", "numcols="])
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt in ("-f", "--filename"):
                filename = arg
            elif opt in ("-c", "--numcols"):
                numcols = arg

        presence_of_validator = PresenceOfValidator(True)
        if not (presence_of_validator.validate(filename, 'filename')) or not (presence_of_validator.validate(numcols, 'numcols')):
            raise Exception(presence_of_validator.format_errors())

        int_validator = IntValidator(True)
        if not (int_validator.validate(numcols, {
            "min": 1
        })):
            raise Exception(int_validator.format_errors())

        str_validator = StrValidator(True)
        if not (str_validator.validate(filename)):
            raise Exception(str_validator.format_errors())

        full_file_path = MY_DIR + '/' + filename
        file_exists_validator = FileExistsValidator(True)
        if file_exists_validator.validate(full_file_path):
            raise Exception(full_file_path + ' already exists...exiting')
        print 'Creating descriptor file at: ' + full_file_path + ' with ' + numcols + ' columns...'
        _create_default_descriptor(filename, numcols)
        print 'Done!  Default JSON descriptor file must be edited to input proper validators!!'

    except getopt.GetoptError:
        # throw error on any get options error.
        print_usage()
    except Exception as e:
        print "[ERROR] " + str(e)


# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])
