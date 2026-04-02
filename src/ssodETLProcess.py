#!/usr/bin/python

import os.path, sys, getopt, traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_PATH)

from lib.Exceptions import *
from lib.ETLFile import *
from lib.Validators import FileExistsValidator


# @author: owhoyt
# used to validate ETL files preemptively
# example python ssodETLProcess.py -i tests/test1.csv -d tests/etlJsonDescriptor1.json
# example help: python ssodETLProcess.py -h


def print_usage():
    """ This method will print the usage of the ssodETLProcess.py file
    :return: none
    """
    print '[USAGE1] ssodETLProcess -i <input_file> -j <descriptor_file>'
    print '[USAGE2] ssodETLProcess --ifile=<input_file> --jfile=<descriptor_file>'
    print '[DEBUG-USAGE1] ssodETLProcess -i <input_file> -j <descriptor_file> -d true'
    print '[DEBUG-USAGE2] ssodETLProcess --ifile <input_file> --jfile <descriptor_file> --debug true'
    print "[NOTE1] when numbering columns in the descriptor file, start with the number 0 for the first column."
    sys.exit(2)


def main(argv):
    """ This is the main run process for ssodETLProcess.py to validate an ETL file.
    :param argv: array
    :return: none
    """

    # set some defaults for file paths.
    input_file = ''
    descriptor_file = ''
    debug = False

    # try to determine the input arguments.
    try:
        opts, args = getopt.getopt(argv, "hi:j:d:", ["ifile=", "jfile=", "debug="])
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt in ("-i", "--ifile"):
                input_file = arg
            elif opt in ("-j", "--jfile"):
                descriptor_file = arg
            elif opt in ("-d", "--debug") and str(arg).lower() == 'true':
                debug = True

    except getopt.GetoptError:
        # throw error on any get options error.
        print_usage()

    # check if the input or the descriptor file has not been defined.
    if not input_file or not descriptor_file:
        print '[INFO]Input file is: ', input_file
        print '[INFO]Descriptor file is: ', descriptor_file
        print_usage()

    # validate that both input file and descriptor file are real files
    file_validator = FileExistsValidator(True)
    if not (file_validator.validate(input_file)) or not (file_validator.validate(descriptor_file)):
        print file_validator.format_errors()
        sys.exit(2)

    # our files have been passed in and we have ensured that they exist and they are readable.
    # now we need create a File object and kick off the fun.
    try:
        File(input_file, descriptor_file, debug)
        print('[SUCCESS] File passed validations.')
        sys.exit(0)
    except StopBatchTriggerZabbixBatchDelayException as e:
        print('[ERROR] ' + str(e))
    except SuccessfulStopValidationException as e:
        print('[SUCCESS] ' + str(e))
        sys.exit(0)
    except Exception as e:
        print('[Error][Unknown] ' + str(e))
        traceback.print_exc()

    sys.exit(1)


# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])
