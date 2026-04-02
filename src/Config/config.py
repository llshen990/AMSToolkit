#!/usr/bin/python

# @author owhoyt
# this file is used to create the config file the environment will use to auto-validate SSOD ETL Files

import ConfigParser
import getopt
import os
import socket
import sys

def main(argv):
    """ This is the main run process for ConfigParser.py to configure the config file for the appropriate environment
    :param argv: array
    :return: none
    """

    # set some defaults
    abs_file_dir = os.path.abspath(os.path.dirname(__file__))
    config_file_name = "ssod_validator.cfg"
    environment = ""
    market = ""
    landing_dir = ""
    archive_dir = ""
    supported_tlas = ["WPN", "WMX", "WCA", "WCL", "WZA", "WBR", "WIN", "WUK"]
    verbosity = ""  # can be empty | all | error
    email_address = ""  # can be empty | xxx@yyy.com | xxx@yyy.com, yyy@sxx.com, etc
    debug = False  # default debug to False
    # create the config object
    config = ConfigParser.RawConfigParser()
    hostname = str(socket.gethostname()).strip()

    tla = None
    runuser = os.environ.get('USER')

    # try to determine the input args
    try:

        opts, args = getopt.getopt(argv, "he:m:l:a:s:v:d:", ["environment=", "market=", "landingdir=", "archivedir=", "email=", "verbosity=", "debug="])
        for opt, arg in opts:
            if opt == '-h':
                print_usage()
            elif opt in ("-e", "--environment"):
                environment = str(arg).strip()
                config.set('', 'env', environment)
            elif opt in ("-m", "--market"):
                market = str(arg).strip()
                config.set('', 'market_config_section', market)
            elif opt in ("-l", "--landingdir"):
                landing_dir = str(arg).strip()
                config.set('', 'landingdir', landing_dir)
            elif opt in ("-a", "--archivedir"):
                archive_dir = str(arg).strip()
                config.set('', 'archivedir', archive_dir)
            elif opt in ("-s", "--email"):
                email_address = str(arg).strip()
            elif opt in ("-v", "--verbosity"):
                verbosity = str(arg).strip()
            elif opt in ("-d", "--debug"):
                debug = True if str(arg).strip().lower() == 'true' else False

    except getopt.GetoptError as e:
        # throw error on any get options error.
        print str(e)
        print_usage()

    config.set('', 'email', email_address)
    config.set('', 'automation_email_list', email_address)
    config.set('', 'verbosity', verbosity)
    config.set('', 'debug', debug)

    # below is for backing up files for utf-8 conversion
    config.set('', 'orig_file_backup_location', '/sso/transport/archive/orig_pre_encoding')
    config.set('', 'automated_duplicate_removal_backup_location', '/sso/transport/archive/orig_pre_dupe_removal')
    config.set('', 'exception_report_emails', 'owen.hoyt@sas.com')
    config.set('', 'exception_report_dir', '/sso/transport/archive/exception_reports/encoding')
    config.set('', 'exception_report_dir_outgoing', '/sso/transport/outgoing')
    config.set('', 'failed_dq_folder', '/sso/transport/incoming/failed_dq')

    config.add_section('MARKETS')
    config.set('MARKETS', 'WMX', {
        'name': 'Mexico',
        'environments': {
            'DEV': {
                'compute': 'wmt06au',
                'va': 'wmt07au'
            },
            'TEST': {
                'compute': 'wmt08au',
                'va': 'wmt09au'
            },
            'QA': {
                'compute': 'wmt10au',
                'va': 'wmt11au'
            },
            'PROD': {
                'compute': 'wmt12au',
                'va': 'wmt13au'
            },
        },
        'transaction_lag': 5,
        'reporting_lib': {
            'libname': 'fcs_rpt',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        },
        'other_meta_libs': {
            'WPN': 'libname rpt_cam META LIBRARY="rpt_cam";',
            'WCA': 'libname rpt_can META LIBRARY="rpt_can";',
            'WCL': 'libname rpt_wcl META LIBRARY="rpt_wcl";',
            'WZA': 'libname rpt_wza META LIBRARY="rpt_wza";',
            'WBR': 'libname rpt_wbr META LIBRARY="rpt_wbr";',
            'WIN': 'libname rpt_win META LIBRARY="rpt_win";',
            'WUK': 'libname rpt_wuk META LIBRARY="rpt_wuk";',
        }
    })

    config.set('MARKETS', 'WCA', {
        'name': 'Canada',
        'environments': {
            'DEV': {
                'compute': 'wmt14au',
                'va': 'wmt15au'
            },
            'TEST': {
                'compute': 'wmt16au',
                'va': 'wmt17au'
            },
            'QA': {
                'compute': 'wmt18au',
                'va': 'wmt19au'
            },
            'PROD': {
                'compute': 'wmt20au',
                'va': 'wmt21au'
            },
        },
        'transaction_lag': 1,
        'reporting_lib': {
            'libname': 'rpt_can',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WCL', {
        'name': 'Chile',
        'environments': {
            'DEV': {
                'compute': 'wmt22au',
                'va': 'wmt23au'
            },
            'TEST': {
                'compute': 'wmt24au',
                'va': 'wmt25au'
            },
            'QA': {
                'compute': 'wmt26au',
                'va': 'wmt27au'
            },
            'PROD': {
                'compute': 'wmt28au',
                'va': 'wmt29au'
            },
        },
        'transaction_lag': 1,
        'reporting_lib': {
            'libname': 'rpt_wcl',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WPN', {
        'name': 'Central America',
        'environments': {
            'DEV': {
                'compute': 'wmt30au',
                'va': 'wmt31au'
            },
            'TEST': {
                'compute': 'wmt32au',
                'va': 'wmt33au'
            },
            'QA': {
                'compute': 'wmt34au',
                'va': 'wmt35au'
            },
            'PROD': {
                'compute': 'wmt36au',
                'va': 'wmt37au'
            },
        },
        'transaction_lag': 3,
        'reporting_lib': {
            'libname': 'rpt_cam',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WBR', {
        'name': 'Argentina',
        'environments': {
            'DEV': {
                'compute': 'wbr01au',
                'va': 'wbr02au'
            },
            'TEST': {
                'compute': 'wbr03au',
                'va': 'wbr04au'
            },
            'QA': {
                'compute': 'wbr05au',
                'va': 'wbr06au'
            },
            'PROD': {
                'compute': 'wbr07au',
                'va': 'wbr08au'
            },
        },
        'transaction_lag': 5,
        'reporting_lib': {
            'libname': 'rpt_wbr',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WZA', {
        'name': 'South Africa',
        'environments': {
            'DEV': {
                'compute': 'wza03au',
                'va': 'wza04au'
            },
            'TEST': {
                'compute': 'wza01au',
                'va': 'wza02au'
            },
            'QA': {
                'compute': 'wza07au',
                'va': 'wza08au'
            },
            'PROD': {
                'compute': 'wza05au',
                'va': 'wza06au'
            },
        },
        'transaction_lag': 0,
        'reporting_lib': {
            'libname': 'rpt_wza',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WIN', {
        'name': 'China',
        'environments': {
            'DEV': {
                'compute': 'win05au',
                'va': 'win06au'
            },
            'TEST': {
                'compute': 'win03au',
                'va': 'win04au'
            },
            'QA': {
                'compute': 'win07au',
                'va': 'win08au'
            },
            'PROD': {
                'compute': 'win01au',
                'va': 'win02au'
            },
        },
        'transaction_lag': 5,
        'reporting_lib': {
            'libname': 'rpt_win',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    config.set('MARKETS', 'WUK', {
        'name': 'United Kingdom',
        'environments': {
            'DEV': {
                'compute': 'wuk03au',
                'va': 'wuk04au'
            },
            'TEST': {
                'compute': 'wuk05au',
                'va': 'wuk06au'
            },
            'QA': {
                'compute': 'wuk07au',
                'va': 'wuk08au'
            },
            'PROD': {
                'compute': 'wuk01au',
                'va': 'wuk02au'
            },
        },
        'transaction_lag': 5,
        'reporting_lib': {
            'libname': 'rpt_wuk',
            'authdomain': 'OraAuth_fcs',
            'path': '&_ORACLEHOST'
        }
    })

    # @todo, define servers for WUK and WIN

    if market not in supported_tlas:
        print "\nInvalid market: " + market + ".  Available markets are: " + ", ".join(supported_tlas)

    if not market or not environment or not landing_dir:
        print '[DEBUG]environment: ' + environment
        print '[DEBUG]market: ' + market
        print '[DEBUG]incoming_dir: ' + landing_dir
        print '[DEBUG]archive_dir: ' + archive_dir
        print '[DEBUG]email_address: ' + email_address
        print '[DEBUG]verbosity: ' + verbosity
        print_usage()

    config.add_section('ENV_HOSTNAME_LOOKUP')

    if market == "WMX":
        # #########################################################################################
        # This section will create configs for WAL-MART MEXICO
        tla = 'wmt'

        config.add_section('WMX')
        config.set('WMX', 'market_tla', 'mex')
        config.set('WMX', 'market_full', 'mexico')
        config.set('WMX', 'customer', 'wmt')
        config.set('WMX', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WMX', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WMX', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WMX', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WMX', 'files_to_validate', {
            "moneygram_wmt_mex.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s\.daily_walmart%(market_full)s\d{8}\.txt\.pgp$", ],
            "mx_wm_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wm\.mx_wm_tender_\d{8}\.txt\.pgp$"],
            "mx_wc_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wc\.mx_wc_tender_\d{8}\.txt\.pgp$"],
            "mx_wc_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wc\.mx_wc_pos_\d{8}\.txt\.pgp$"],
            "mx_wc_member.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wc\.mx_wc_member_\d{8}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "mx_wm_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wm\.mx_wm_pos_\d{8}\.txt\.pgp$"],
            "mex.vale.ecouponsas.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.vale\.ecouponsastest\d{12}\.txt\.pgp$"],
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "uniteller_wmt_mex.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.uniteller\.uniteller_\d{8}\.txt\.pgp$"],
            "western_union.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.western_union\.western_union_\d{8}\.txt\.pgp$"],
            "bts.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.bts\.wmt_act_\d{8}\.txt\.pgp$"],
            "usd_wc.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wc\.mx_wc_usd_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "usd_wm.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.mx_wm\.mx_wm_usd_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "firstdata_wc.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.giftcards\.mx_wc_b2c_\d{8}\.txt\.pgp$"],
            "firstdata_wm.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.giftcards\.mx_wm_b2c_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wmt06au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt08au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt10au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt12au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WMX-202')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WPN":
        # #########################################################################################
        # This section will create configs for WAL-MART CENTRAL AMERICA
        tla = 'wmt'

        config.add_section('WPN')
        config.set('WPN', 'market_tla', 'wpn')
        config.set('WPN', 'market_alias', 'cam')
        config.set('WPN', 'customer', 'walmart')
        config.set('WPN', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WPN', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WPN', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WPN', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WPN', 'files_to_validate', {
            "hnd_wpn.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.transnetwork_hnd\.pagoswallmarhonduras\d{2}\w+\d{2}\.txt\.pgp$", ],
            "slv_wpn.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.transnetwork_slv\.remesaspagadaselsalvadorwm\d{2}\w+\d{2}\.txt\.pgp$"],
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "motorcycle.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.motorcycle\.aml_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wmt30au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt32au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt34au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt36au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WPN-100')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WCA":
        # #########################################################################################
        # This section will create configs for WAL-MART CANADA
        tla = 'wmt'

        config.add_section('WCA')
        config.set('WCA', 'market_tla', 'wca')
        config.set('WCA', 'market_alias', 'can')
        config.set('WCA', 'market_full', 'canada')
        config.set('WCA', 'customer', 'walmart')
        config.set('WCA', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WCA', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WCA', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WCA', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WCA', 'files_to_validate', {
            "account.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.wmcb\.account_\d{8}\.txt\.pgp$"],
            "account_party_bridge.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.wmcb\.acct_party_bridge_\d{8}\.txt\.pgp$"],
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "account_party.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.wmcb\.party_\d{8}\.txt\.pgp$"],
            "cash_flow.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_alias)s\.wmcb\.cashflow_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wmt14au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt16au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt18au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt20au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WCA-206')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WCL":
        # #########################################################################################
        # This section will create configs for WAL-MART CHILE
        tla = 'wmt'

        config.add_section('WCL')
        config.set('WCL', 'market_tla', 'chl')
        config.set('WCL', 'market_full', 'chile')
        config.set('WCL', 'customer', 'wmt')
        config.set('WCL', 'customer_full', 'walmart')
        config.set('WCL', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WCL', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WCL', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WCL', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WCL', 'files_to_validate', {
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer_full)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "wcl_pos_layout.json": [
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_pos\.member_sas_aml_dat_\d{8}\.txt\.pgp$",
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_pos\.loyalty_sas_aml_dat_\d{8}\.txt\.pgp$"
            ],
            "wcl_party_loyalty_layout.json": [
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_member\.loyalty_sas_aml_dat_\d{8}\.txt\.pgp$"
            ],
            "wcl_party_layout.json": [
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_member\.member_sas_aml_dat_\d{8}\.txt\.pgp$",
            ],
            "wcl_tender_layout.json": [
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_tender\.member_sas_aml_dat_\d{8}\.txt\.pgp$",
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_tender\.loyalty_sas_aml_dat_\d{8}\.txt\.pgp$"
            ],
            "az_card.json": [
                "^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.az\.azcard_sas_aml_dat_\d{8}\.txt\.pgp$"
            ]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wmt22au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt24au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt26au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wmt28au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WCL-422')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WZA":
        # #########################################################################################
        # This section will create configs for WAL-MART AFRICA
        tla = 'wza'

        config.add_section('WZA')
        config.set('WZA', 'market_tla', 'zaf')
        config.set('WZA', 'market_full', 'south_africa')
        config.set('WZA', 'customer', 'wmt')
        config.set('WZA', 'customer_full', 'walmart')
        config.set('WZA', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WZA', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WZA', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WZA', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WZA', 'files_to_validate', {
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer_full)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "wza_party_layout.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_member.southafrica_makro\d{8}.txt.pgp$"],
            "wza_pos_layout.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_pos.southafrica_makro\d{8}.txt.pgp$"],
            "wza_tender_layout.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.%(market_full)s_tender.southafrica_makro\d{8}.txt.pgp$"],
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wza03au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wza01au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wza07au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wza05au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WZA-500')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,jehayn,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WBR":
        # #########################################################################################
        # This section will create configs for WAL-MART ARGENTINA
        tla = 'wbr'

        config.add_section('WBR')
        config.set('WBR', 'market_tla', 'arg')
        config.set('WBR', 'market_full', 'argentina')
        config.set('WBR', 'customer', 'wmt')
        config.set('WBR', 'customer_full', 'walmart')
        config.set('WBR', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WBR', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WBR', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WBR', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WBR', 'files_to_validate', {
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer_full)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "ar_bct_member.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_bct\.ar_bct_member_\d{8}\.txt\.pgp$"],
            "ar_bct_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_bct\.ar_bct_pos_\d{8}\.txt\.pgp$"],
            "ar_bct_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_bct\.ar_bct_tender_\d{8}\.txt\.pgp$"],
            "ar_wm_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_wm\.ar_wm_pos_\d{8}\.txt\.pgp$"],
            "ar_wm_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_wm\.ar_wm_tender_\d{8}\.txt\.pgp$"],
            "ar_b2b.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ar_b2b\.ar_wm_b2b_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wbr01au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wbr03au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wbr05au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wbr07au', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WBR-60')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,jehayn,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WIN":
        # #########################################################################################
        # This section will create configs for WAL-MART CHINA
        tla = 'win'

        config.add_section('WIN')
        config.set('WIN', 'market_tla', 'chn')
        config.set('WIN', 'market_full', 'china')
        config.set('WIN', 'customer', 'wmt')
        config.set('WIN', 'customer_full', 'walmart')
        config.set('WIN', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WIN', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WIN', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WIN', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WIN', 'files_to_validate', {
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer_full)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "cn_ghs_member.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ghs\.cn_wmecom_member_\d{8}\.txt\.pgp$"],
            "cn_ghs_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ghs\.cn_wmecom_pos_\d{8}\.txt\.pgp$"],
            "cn_ghs_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.ghs\.cn_wmecom_tender_\d{8}\.txt\.pgp$"],
            "cn_wc_member.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_wc\.cn_wc_member_\d{8}\.txt\.pgp$"],
            "cn_wc_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_wc\.cn_wc_pos_\d{8}\.txt\.pgp$"],
            "cn_wc_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_wc\.cn_wc_tender_\d{8}\.txt\.pgp$"],
            "cn_wm_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_wm\.cn_wm_pos_\d{8}\.txt\.pgp$"],
            "cn_wm_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_wm\.cn_wm_tender_\d{8}\.txt\.pgp$"],
            "cn_firstdata_wm.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.giftcards\.cn_wm_b2c_\d{8}\.txt\.pgp$"],
            "cn_firstdata_wc.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.giftcards\.cn_wc_b2c_\d{8}\.txt\.pgp$"],
            "cn_cul_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.cn_cul\.cn_cul_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'win01au', 'PROD')
        config.set('ENV_HOSTNAME_LOOKUP', 'win03au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'win05au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'win07au', 'DEV')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WIN-592')
        config.set('', 'dq_watchers', 'owhoyt,smxmiv,anmane,camcla,scnzzh,jehayn,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    if market == "WUK":
        # #########################################################################################
        # This section will create configs for WAL-MART GREAT BRITAIN
        tla = 'wuk'

        config.add_section('WUK')
        config.set('WUK', 'market_tla', 'gbr')
        config.set('WUK', 'market_full', 'great_britain')
        config.set('WUK', 'customer', 'wuk')
        config.set('WUK', 'customer_full', 'walmart')
        config.set('WUK', 'validated_dir', "%(landingdir)s/validated_by_ssod_cron")
        config.set('WUK', 'validation_output_dir', "%(validated_dir)s/file_output")
        config.set('WUK', 'validated_file_postfix', "_validated_by_ssod")
        config.set('WUK', 'json_descriptor_dir', abs_file_dir + "/descriptor_files/")
        config.set('WUK', 'files_to_validate', {
            "dow_jones.json": ["^csv_pfa_\d{12}_d\.zip$"],
            "global_currency_exchange.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(customer_full)s\.global\.currency_exchange_\d{2}_\d{2}_\d{4}\.txt\.pgp$"],
            "store_descriptor.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.global\.walmart\.storefile_\d{8}_\d{6}\.txt\.pgp$"],
            "gb_b2b.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.gb_b2b\.gb_b2b_\d{8}\.txt\.pgp$"],
            "gb_firstdata_wm.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.giftcards\.gb_wm_b2c_\d{8}\.txt\.pgp$"],
            "gb_george_dotcom.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.gb_dotcom\.gb_george_\d{8}\.txt\.pgp$"],
            "gb_ghs_dotcom.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.gb_dotcom\.gb_ghs_\d{8}\.txt\.pgp$"],
            "gb_wm_tender.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.gb_wm\.gb_wm_tender_\d{8}\.txt\.pgp$"],
            "gb_wm_pos.json": ["^file\.\d{8}\.\d{4}\.%(env)s\.%(market_tla)s\.gb_wm\.gb_wm_pos_\d{8}\.txt\.pgp$"]
        })

        config.set('ENV_HOSTNAME_LOOKUP', 'wuk03au', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk03au.vsp.sas.com', 'DEV')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk05au', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk05au.vsp.sas.com', 'TEST')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk07au', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk07au.vsp.sas.com', 'QA')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk01au', 'PROD')
        config.set('ENV_HOSTNAME_LOOKUP', 'wuk01au.vsp.sas.com', 'PROD')

        # DQ Errors
        config.set('', 'dq_error_assignee', 'wmt0rxr1')
        config.set('', 'dq_error_priority', 'Critical')
        config.set('', 'dq_warning_assignee', 'wmt0rxr1')
        config.set('', 'dq_warning_priority', 'Major')
        config.set('', 'dq_master_ticket_link', 'WUK-422')
        config.set('', 'dq_watchers', 'owhoyt,jechen,smxmiv,anmane,camcla,scnzzh,jehayn,wmt0ixs,wmt0bxb,wmt0pxp1,wmt0rxr1,wmt0txm,wmt0mxw,wmt0lxc,wmt0kxo,wmt0oxs,wmt0lxp')
        config.set('', 'dq_enable_auto_jira', False)

    # commands that all markets need
    if not tla or not runuser:
        raise Exception('Invalid tla or runuser variable!!')

    if hostname == 'sasdev1-centos6':
        config.set('', 'manifest_create_script', '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/manifest_create.sh')
        config.set('', 'encrypt_script', '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/encrypt.sh')
        config.set('', 'decrypt_script', '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/decrypt.sh')
        config.set('', 'sso_zabbix_wrapper_script', '/home/devshare/python/SAS/general_op_scripts/bash_scripts/utilities/sso_zabbix_wrapper.pl')
        config.set('', 'logs_dir', '/tmp')
        config.set('', 'base_automation_signal_path', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/run/signals')
        config.set('', 'ssoaid_bin_dir', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin')
        config.set('', 'file_get_trans_date', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin/file_get_trans_date.sh')
        config.set('', 'file_get_file_type', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin/file_get_file_type.sh')
        config.set('', 'file_get_trans_filename', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin/file_get_trans_filename.sh')
        config.set('', 'sso_update_batch_status', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin/sso_update_batch_status.sh')
        config.set('', 'file_validate_trans_date', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/ssoaid/bin/file_validate_trans_date.sh')
        config.set('', 'batch_delay_trigger_file', '/home/devshare/' + tla + '/' + market.lower() + '/DEV/run/signals/dailycycle_batch_cycle-tempstop.txt')
        config.set('', 'global_temp_stop_signal', "%(batch_delay_trigger_file)s")
    else:
        config.set('', 'manifest_create_script', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/manifest_create.sh')
        config.set('', 'encrypt_script', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/encrypt.sh')
        config.set('', 'decrypt_script', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/decrypt.sh')
        config.set('', 'sso_zabbix_wrapper_script', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/sso_zabbix_wrapper.pl')
        config.set('', 'logs_dir', '/' + tla + '/projects/fcs/' + runuser + '/logs')
        config.set('', 'base_automation_signal_path', '/' + tla + '/projects/fcs/' + runuser + '/run/signals')
        config.set('', 'ssoaid_bin_dir', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin')
        config.set('', 'file_get_trans_date', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/file_get_trans_date.sh')
        config.set('', 'file_get_file_type', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/file_get_file_type.sh')
        config.set('', 'file_get_trans_filename', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/file_get_trans_filename.sh')
        config.set('', 'sso_update_batch_status', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/sso_update_batch_status.sh')
        config.set('', 'file_validate_trans_date', '/' + tla + '/projects/fcs/' + runuser + '/ssoaid/bin/file_validate_trans_date.sh')
        config.set('', 'batch_delay_trigger_file', '/' + tla + '/projects/fcs/' + runuser + '/run/signals/dailycycle_batch_cycle-tempstop.txt')
        config.set('', 'global_temp_stop_signal', "%(batch_delay_trigger_file)s")

    # let's write the file now
    with open(config_file_name, 'wb') as config_file_name:
        config.write(config_file_name)

    sys.exit(0)

def print_usage():
    """ This method will print the usage of the ConfigParser.py file
    :return: none
    """
    print '[USAGE] python config.py -e <environment> -m <market> -l <landing_directory> -a <archive_directory> -s <email_address_list> -v <all|error>'
    print '[USAGE2] python config.py --environment=<environment> --market=<market> --landingdir=<landing_directory> --archivedir=<archive_directory> --email<email_address_list> --verbosity=<all|error>'
    print '[Example] python config.py -e dev -m MEX -l /sso/transport/incoming -a /sso/transport/archive -s owen.hoyt@sas.com -v all'
    sys.exit(2)

# this is how we invoke the main method to start everything off and we pass in argv from sys.
if __name__ == "__main__":
    main(sys.argv[1:])