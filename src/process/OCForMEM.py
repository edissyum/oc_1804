# This file is part of Open-Capture For MEM Courrier.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture For MEM Courrier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture For MEM Courrier.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import sys
import json
import shutil
from .FindDate import FindDate
from .OCForForms import process_form
from .FindSubject import FindSubject
from .FindChrono import FindChrono


def get_process_name(args, config):
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        _process = args['process']
    else:
        if args['process'] in config.cfg['OCForMEM']['processavailable'].split(','):
            _process = 'OCForMEM_' + args['process'].lower()
        else:
            _process = 'OCForMEM_' + config.cfg['OCForMEM']['defaultprocess'].lower()

    return _process


def process(args, file, log, separator, config, image, ocr, locale, web_service, tmp_folder, config_mail=None):
    log.info('Processing file : ' + file)

    # Check if the choosen process mode if available. If not take the default one
    _process = args['process_name']
    log.info('Using the following process : ' + _process)

    destination = ''

    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args.get('RDFF') not in [None, False]:
        log.info('RDFF is enabled')
        file_name = os.path.basename(file)
        if separator.divider not in file_name:
            destination = config.cfg[_process]['destination']
        else:
            try:
                destination = int(file_name.split(separator.divider)[0])
            except ValueError:
                destination = file_name.split(separator.divider)[0]
    # Or from the destination arguments
    elif args.get('destination') is not None:
        destination = args['destination']
    elif args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        destination = args['data']['destination']

    if not destination:
        # Put default destination
        destination = config.cfg[_process]['destination']
        log.info("Destination can't be found, using default destination : " + destination)

    if args.get('isMail') is not None and args.get('isMail') is True:
        if args['isForm']:
            log.info('Start searching form into e-mail')
            form = process_form(args, config, config_mail, log, web_service, _process, file)
            if form and form[1] != 'default':
                return form

    if os.path.splitext(file)[1].lower() == '.pdf':  # Open the pdf and convert it to JPG
        res = image.pdf_to_jpg(file, True)
        if res is False:
            exit(os.EX_IOERR)
        # Check if pdf is already OCR and searchable
        check_ocr = os.popen('pdffonts ' + file, 'r')
        tmp = ''
        for line in check_ocr:
            tmp += line

        if len(tmp.split('\n')) > 3:
            is_ocr = True
        else:
            is_ocr = False
    elif os.path.splitext(file)[1].lower() == '.html':
        res = image.html_to_txt(file)
        if res is False:
            sys.exit(os.EX_IOERR)
        ocr.text = res
        is_ocr = True
    elif os.path.splitext(file)[1].lower() == '.txt':
        ocr.text = open(file, 'r').read()
        is_ocr = True
    else:  # Open the picture
        image.open_img(file)
        is_ocr = False

    if 'reconciliation' not in _process and config.cfg['GLOBAL']['disablelad'] == 'False':
        # Get the OCR of the file as a string content
        if args.get('isMail') is None or args.get('isMail') is False and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
            ocr.text_builder(image.img)

        # Find subject of document
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True:
            subject_thread = ''
        else:
            subject_thread = FindSubject(ocr.text, locale, log)

        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and 'chronoregex' not in config_mail.cfg[_process]:
            chrono_thread = ''
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread = FindChrono(ocr.text, config_mail.cfg[_process])
        elif _process in config.cfg and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread = FindChrono(ocr.text, config.cfg[_process])
        else:
            chrono_thread = ''

        # Find date of document
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True:
            date_thread = ''
        else:
            date_thread = FindDate(ocr.text, locale, log, config)

        # Launch all threads
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date_thread.start()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject_thread.start()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']) and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread.start()
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread.start()

        # Wait for end of threads
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date_thread.join()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject_thread.join()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']) and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread.join()
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread.join()

        # Get the returned values
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date = date_thread.date
        else:
            date = ''

        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and 'chronoregex' not in config_mail.cfg[_process]:
            chrono_number = ''
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_number = chrono_thread.chrono
        elif _process in config.cfg and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_number = chrono_thread.chrono
        else:
            chrono_number = ''

        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject = subject_thread.subject
        else:
            subject = ''
    else:
        date = ''
        subject = ''
        chrono_number = ''
        contact = {}

    try:
        os.remove(image.jpg_name)  # Delete the temp file used to OCR'ed the first PDF page
    except FileNotFoundError:
        pass

    # Create the searchable PDF if necessary
    if is_ocr is False:
        log.info('Start OCR on document before send it')
        ocr.generate_searchable_pdf(file, tmp_folder, separator)
        file_to_send = ocr.searchablePdf
    else:
        if separator.convert_to_pdfa == 'True' and os.path.splitext(file)[1].lower() == '.pdf' and (args.get('isMail') is None or args.get('isMail') is False):
            output_file = file.replace(separator.output_dir, separator.output_dir_pdfa)
            separator.convert_to_pdfa_function(output_file, file, log)
            file = output_file
        file_to_send = open(file, 'rb').read()

    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        if date != '':
            args['data']['documentDate'] = date
        if subject != '':
            args['data']['subject'] = subject
        if contact:
            args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]

        if args.get('isMail') == 'attachments':
            args['data']['file'] = args['file']
            args['data']['format'] = args['format']

        res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[_process])
        if res:
            log.info('Insert email OK : ' + str(res))
            if chrono_number:
                chrono_res_id = web_service.retrieve_document_by_chrono(chrono_number)
                if chrono_res_id:
                    web_service.link_documents(res[1]['resId'], chrono_res_id['resId'])
            else:
                chrono_class = FindChrono(args['msg']['subject'], config_mail.cfg[_process])
                chrono_class.run()
                chrono_number = chrono_class.chrono
                if chrono_number:
                    chrono_res_id = web_service.retrieve_document_by_chrono(chrono_number)
                    if chrono_res_id:
                        web_service.link_documents(res[1]['resId'], chrono_res_id['resId'])
            return res
        try:
            shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
        except shutil.Error as _e:
            log.error('Moving file ' + file + ' error : ' + str(_e))
        return False, res
    elif 'is_attachment' in config.cfg[_process] and config.cfg[_process]['is_attachment'] != '':
        if args['isinternalnote']:
            res = web_service.insert_attachment(file_to_send, config, args['resid'], _process)
        else:
            res = web_service.insert_attachment_reconciliation(file_to_send, args['chrono'], _process, config)
    else:
        res = web_service.insert_with_args(file_to_send, config, subject, date, destination, config.cfg[_process])

    if res:
        log.info("Insert OK : " + str(res))
        if chrono_number:
            chrono_res_id = web_service.retrieve_document_by_chrono(chrono_number)
            if chrono_res_id:
                web_service.link_documents(json.loads(res)['resId'], chrono_res_id['resId'])
        # BEGIN OBR01
        # If reattach is active and the origin document already exist,  reattach the new one to it
        if config.cfg['REATTACH_DOCUMENT']['active'] == 'True' and config.cfg[_process].get('reconciliation') is not None:
            log.info("Reattach document is active : " + config.cfg['REATTACH_DOCUMENT']['active'])
            if args['chrono']:
                check_document_res = web_service.check_document(args['chrono'])
                log.info("Reattach check result : " + str(check_document_res))
                if check_document_res['resources']:
                    res_id_origin = check_document_res['resources'][0]['res_id']
                    res_id_signed = json.loads(res)['resId']

                    log.info("Reattach res_id : " + str(res_id_origin) + " to " + str(res_id_signed))
                    # Get ws user id and reattach the document
                    list_of_users = web_service.retrieve_users()
                    for user in list_of_users['users']:
                        if config.cfg['OCForMEM']['user'] == user['user_id']:
                            typist = user['id']
                            reattach_res = web_service.reattach_to_document(res_id_origin, res_id_signed, typist, config)
                            log.info("Reattach result : " + str(reattach_res))

                    # Change status of the document
                    change_status_res = web_service.change_status(res_id_origin, config)
                    log.info("Change status : " + str(change_status_res))
        # END OBR01
        if args.get('isMail') is None:
            try:
                if args.get('keep_pdf_debug').lower() != 'true':
                    os.remove(file)
            except FileNotFoundError as _e:
                log.error('Unable to delete ' + file + ' after insertion : ' + str(_e))
        return True, res
    try:
        shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
    except shutil.Error as _e:
        log.error('Moving file ' + file + ' error : ' + str(_e))
    return False
