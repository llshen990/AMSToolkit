import subprocess
from datetime import datetime
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
from email.header import Header
from os.path import basename
from sked import smtp_server,cfglogpath,send_email_type,cfgconfpath,print2,prselogprint,email_string_to_list,createReplacements,validate_email,recipients_checked, suppress_further_emails
from sked import notify_start, notify_finish,email_string,sender_email
import configparser

saslogpath='/col/projects/default/colrun/logs'

def on_job_error(filename, check_schedule, x, schedule_status, config_file):

    erc = suppress_further_emails
    tmstr=datetime.now().strftime("%Y%m%d%H%M")
    tarfilename=str(os.path.basename(filename))+'_'+tmstr+'.tar.gz'

    cmd_str="zsh -c 'tar -czf  " + tarfilename + " "+ cfglogpath+'/'+"*.log(.om[1,10])'"
    print(cmd_str)
    subprocess.call(cmd_str,shell=True)
    subprocess.call('sleep 5',shell=True)

    if x.email_ini is not None:
        emConfig = configparser.ConfigParser()
        emConfig.read(cfgconfpath + x.email_ini)
        send_email_yn = emConfig.get('Error', 'notify', fallback=None)
        if send_email_yn is None:
            print2(datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + 'Info: Custom email ini ' \
                   + x.email_ini + ' either isn\'t found or doesn\'t have notify set for this group (' \
                   + 'Error' + ')')
            prselogprint(level='Schedule',
                         level2=None,
                         status='Info',
                         fullrunfile=x.runfile,
                         ops_label=None,
                         message=x.email_ini + ' either isn\'t found or doesn\'t have notify set for this group (' \
                         + 'Error' + ')'
                         )
        elif send_email_yn == '1':

            recipients_str = emConfig.get('Error', 'recipients', fallback=None)
            sender = emConfig.get('Error', 'sender', fallback=None)
            subject = emConfig.get('Error', 'subject', fallback=None)
            body = emConfig.get('Error', 'body', fallback=None)

            recipients_checked2 = []
            if recipients_str is not None:
                recipients_checked2 = email_string_to_list(createReplacements(recipients_str.strip(), x))
            if sender is not None:
                sender = createReplacements(sender.strip(), x)
                if validate_email(sender) is None:
                    sender = None

            if smtp_server is not None \
                    and len(recipients_checked2) > 0 \
                    and sender is not None \
                    and body is not None \
                    and subject is not None:
                # stdprint('Trying to send email (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
                body = createReplacements(body, x, allow_breaks='Y')
                subject = createReplacements(subject.strip(), x)

                # message = 'Subject: ' + subject + '\n\n' + body  # original message had no To in received emails
                # message = 'To: ' + ','.join(recipients_checked2) + '\nSubject: ' + subject + '\n\n' + body
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = formataddr((str(Header('SAS', 'utf-8')), sender))
                msg['To'] = ','.join(recipients_checked2)
                msg.attach(MIMEText(body))
                # to_addr = recipients_checked2

                with open(tarfilename,'rb') as fil:
                    part = MIMEApplication(fil.read(), Name=basename(tarfilename))
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(tarfilename)
                msg.attach(part)
                erc = send_email_type(sender, recipients_checked2, msg.as_string())
            return erc
    else:

        subject='Error: '+str(filename)+' failed'
        body='''
        Hi BBL,
        
        Batch failed, please see attached log.
        
        Thanks
        '''
        if smtp_server is not None \
                and len(recipients_checked) > 0 \
                and sender_email is not None \
                and body is not None \
                and subject is not None:
            # stdprint('Trying to send email (send_email_notify_custom()) - ' + x.runfile + ' - ' + which_email)
            body = createReplacements(body, x, allow_breaks='Y')
            subject = createReplacements(subject.strip(), x)

            # message = 'Subject: ' + subject + '\n\n' + body  # original message had no To in received emails
            # message = 'To: ' + ','.join(recipients_checked2) + '\nSubject: ' + subject + '\n\n' + body
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((str(Header('SAS', 'utf-8')), sender_email))
            msg['To'] = ','.join(recipients_checked)
            msg.attach(MIMEText(body))
            # to_addr = recipients_checked2

            with open(tarfilename, 'rb') as fil:
                part = MIMEApplication(fil.read(), Name=basename(tarfilename))
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(tarfilename)
            msg.attach(part)
            erc = send_email_type(sender_email, recipients_checked, msg.as_string())
        return erc

def on_schedule_error_stop(filename, check_schedule, config_file):

    erc = suppress_further_emails
    tmstr = datetime.now().strftime("%Y%m%d%H%M")
    tarfilename = str(os.path.basename(filename)) + '_' + tmstr + '.tar.gz'

    # cmd_str = "zsh -c 'tar -czf  " + tarfilename + " " + cfglogpath + '/' + "*.log(.om[1,10])'"
    # cmd_str = "zsh -c 'tar -C " + saslogpath+ " -czf  " + tarfilename + " " + saslogpath + '/' + "*.log(.om[1,7)" + " "+ cfglogpath+"/"+"*(.om[1,3])'"
    # cmd_str = "tar --transform 's/.*\///g' -czf " + tarfilename + " " + saslogpath + "/" + "*.log(.om[1,7)" + " " + cfglogpath + "/" + "*(.om[1,3])"

    cmd_str = '''zsh -c "tar --transform 's/.*\///g' -czf ''' \
              + tarfilename + " " + saslogpath + "/" + "*.log(.om[1,7])" + " " + cfglogpath + "/" + '''*(.om[1,3])" '''
    print(cmd_str)
    subprocess.call(cmd_str, shell=True)
    subprocess.call('sleep 5', shell=True)

    subject='Schedule '+filename+' failed'
    body='''
    Hi BBL,
    
    Batch failed, please see attached log.
        
    Thanks
    SAS ETL team
    '''
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr((str(Header('SAS', 'utf-8')), sender_email))
    msg['To'] = ','.join(recipients_checked)
    msg.attach(MIMEText(body))
    # to_addr = recipients_checked2

    with open(tarfilename, 'rb') as fil:
        part = MIMEApplication(fil.read(), Name=basename(tarfilename))
    part['Content-Disposition'] = 'attachment; filename="%s"' % basename(tarfilename)
    msg.attach(part)
    erc = send_email_type(sender_email, recipients_checked, msg.as_string())

    return erc


