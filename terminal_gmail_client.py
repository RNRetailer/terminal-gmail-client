import google_workspace
import re
import editor
from typing import Iterable
import sys
from termcolor import cprint
import os
import errno
import tempfile
import subprocess
from PIL import Image
from PIL import UnidentifiedImageError
import uuid
import shutil
import io

##############################################################################################################################################

# CONFIG

# set terminal size
TERMINAL_ROWS = 32
TERMINAL_COLS = 64

# set number of characters at which an email is considered long
LONG_PRINTED_STRING_MINIMUM_LENGTH = 5000

##############################################################################################################################################

# magic number
ERROR_INVALID_NAME = 123

# set terminal size
print('\x1b[8;{0};{1}t'.format(TERMINAL_ROWS, TERMINAL_COLS), end='', flush=True)

EMAIL_VALIDATION_REGEX = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

# pretty print
def pprint(text):
    cprint(text, "black", "on_white")

print = pprint

##############################################################################################################################################

# USER INPUT FUNCTIONS

def ask_for_user_input(prompt: str, valid_options: Iterable):
    """
        Gets user input from the terminal and checks it against an Iterable of valid options.
    """

    while True:
        print(prompt)

        user_input = input().strip().upper()

        if user_input in valid_options:
            return user_input
        else:
            print('Invalid input')

def ask_for_user_input_regex(prompt: str, regex_pattern: re.Pattern, return_on_blank=False, regex_failure_message='Input failed validation'):
    """
        Gets user input from the terminal and checks it against a regular expression.
    """

    while True:
        print(prompt)

        user_input = input().strip()

        if return_on_blank and not user_input:
            return

        if not re.fullmatch(regex_pattern, user_input):
            print(regex_failure_message)
            continue

        return user_input

def ask_for_non_blank_user_input(prompt: str, use_editor: bool = False):
    """
        Gets user input from the terminal and makes sure that is is not blank.
        Supports input from the system EDITOR as well as standard Python input.
    """

    while True:
        print(prompt)

        if use_editor:
            user_input = editor.edit().decode('utf8')
        else:
            user_input = input().strip()

        if not user_input:
            print('Input cannot be blank')
            continue

        return user_input

def gather_to_cc_bcc_email_recipients(actual_recipients: list, actual_cc: list, actual_bcc: list, is_reply=False):
    """
        Gets recipient email addresses from user input and adds them to the recipients, CC, and BCC lists in-place.
    """
    
    choice_to_verbose_name_dict = {
        'R': 'Reply to',
        'T': 'To',
        'C': 'CC',
        'B': 'BCC',
    }

    if is_reply:
        query = '(R)eply to, (C)c, (B)cc, (S)kip'
        recipient_type_choices = ('R', 'C', 'B', 'S')
    else:
        query = '(T)o, (C)c, (B)cc, (S)kip'
        recipient_type_choices = ('T', 'C', 'B', 'S')
        
    to_choice = recipient_type_choices[0]
    
    choice_to_list_dict = {
        to_choice: actual_recipients,
        'C': actual_cc,
        'B': actual_bcc,
    }
    
    while True:
        user_input_email = ask_for_user_input_regex(
            'Enter an email address to add as a recipient, or press Enter',
            EMAIL_VALIDATION_REGEX,
            True,
            'Email Invalid'
        )

        if not user_input_email:
            return

        recipient_type_input_validated = ask_for_user_input(
            query,
            recipient_type_choices
        )

        if recipient_type_input_validated == 'S':
            continue
        
        applicable_email_address_list = choice_to_list_dict[recipient_type_input_validated]
        
        if recipient_type_input_validated in applicable_email_address_list:
            verbose_name = choice_to_verbose_name_dict[recipient_type_input_validated]
            print(f'That email address is already in the list of {verbose_name} email addresses')
            continue
            
        applicable_email_address_list.append(user_input_email)
        
        
def add_attachments():
    """
        Add attachments to an email by putting their filepaths into a list.
    """
    
    attachments = []

    while True:
        print('Please enter the filename of your attachment or press Enter if you have nothing to attach')
        
        filepath = input().strip()
        
        if not filepath:
            break
            
        if not os.path.isfile(filepath):
            print('Invalid filename, failed to attach the file.')
            continue
            
        if filepath in attachments:
            print('You already attached this file. Skipping.')
            continue
            
        attachments.append(filepath)
        
    return attachments

def accept_any_input(prompt: str):
    """
        Get input from the user without checking it.
    """
    
    print(prompt)
    return input()
    
def ask_for_integer_input(prompt: str, maximum: int, minimum: int = 0, maximum_on_blank: bool = True):
    """
        Gets user input from the terminal and checks if it is an integer in the correct range.
    """

    while True:
        print(prompt)

        user_input = input().strip()
        
        if not user_input:
            return maximum
            
        try:
            user_input = int(user_input)
        except ValueError:
            print('Incorrect value. Please enter an integer.')
            continue
             
        if user_input < minimum:
            print(f'Value must be at least {minimum}')
            continue
             
        if user_input > maximum:
            print(f'Value must be at most {maximum}')
            continue
            
        return user_input
    
# below from https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta
# /start 

def is_pathname_valid(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    '''
    
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)   # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError as exc:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?
    
def is_path_creatable(pathname: str) -> bool:
    '''
    `True` if the current user has sufficient permissions to create the passed
    pathname; `False` otherwise.
    '''
    
    # Parent directory of the passed path. If empty, we substitute the current
    # working directory (CWD) instead.
    dirname = os.path.dirname(pathname) or os.getcwd()
    return os.access(dirname, os.W_OK)
    
def is_path_exists_or_creatable(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname for the current OS _and_
    either currently exists or is hypothetically creatable; `False` otherwise.

    This function is guaranteed to _never_ raise exceptions.
    '''
    
    try:
        # To prevent "os" module calls from raising undesirable exceptions on
        # invalid pathnames, is_pathname_valid() is explicitly called first.
        return is_pathname_valid(pathname) and (
            os.path.exists(pathname) or is_path_creatable(pathname))
    # Report failure on non-fatal filesystem complaints (e.g., connection
    # timeouts, permissions issues) implying this path to be inaccessible. All
    # other exceptions are unrelated fatal issues and should not be caught here.
    except OSError:
        return False
    
def is_path_sibling_creatable(pathname: str) -> bool:
    '''
    `True` if the current user has sufficient permissions to create **siblings**
    (i.e., arbitrary files in the parent directory) of the passed pathname;
    `False` otherwise.
    '''
    
    # Parent directory of the passed path. If empty, we substitute the current
    # working directory (CWD) instead.
    dirname = os.path.dirname(pathname) or os.getcwd()

    try:
        # For safety, explicitly close and hence delete this temporary file
        # immediately after creating it in the passed path's parent directory.
        with tempfile.TemporaryFile(dir=dirname): pass
        return True
    # While the exact type of exception raised by the above function depends on
    # the current version of the Python interpreter, all such types subclass the
    # following exception superclass.
    except EnvironmentError:
        return False
    
def is_path_exists_or_creatable_portable(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname on the current OS _and_
    either currently exists or is hypothetically creatable in a cross-platform
    manner optimized for POSIX-unfriendly filesystems; `False` otherwise.

    This function is guaranteed to _never_ raise exceptions.    
    '''
    
    try:
        # To prevent "os" module calls from raising undesirable exceptions on
        # invalid pathnames, is_pathname_valid() is explicitly called first.
        return is_pathname_valid(pathname) and (
            os.path.exists(pathname) or is_path_sibling_creatable(pathname))
    # Report failure on non-fatal filesystem complaints (e.g., connection
    # timeouts, permissions issues) implying this path to be inaccessible. All
    # other exceptions are unrelated fatal issues and should not be caught here.
    except OSError:
        return False
        
# /end
    
def get_valid_filepath(prompt: str, return_on_blank: bool = True):
    """
        Get vaild filename from user.
    """
    
    while True:
        print(prompt)
            
        filepath = input().strip()

        if return_on_blank and not filepath:
            return
        
        if not is_path_exists_or_creatable_portable(filepath):
            print('That is not a valid path. Try again.')
            continue
            
        return filepath

##############################################################################################################################################

# SETUP FUNCTIONS

def connect():
    """
        Connects to the GMail API via OAUTH.
    """
    service = google_workspace.service.GoogleService(
        api="gmail",
        session="my-gmail",
        client_secrets="client_secret.json"
    )

    service.local_oauth()

    client = google_workspace.gmail.GmailClient(service=service)
    print(f'Logged in to GMail as {client.email_address}')
    return client

gmail_client = connect()

##############################################################################################################################################

# EMAIL READING / WRITING FUNCTIONS

textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
inline_image_regex_gmail = re.compile(r"\[image: .*\]")
inline_image_regex_outlook = re.compile(r"\[cid:.*\]")

def make_sure_images_are_on_seperate_lines(message_content):
    """
        Puts breaklines around inline images in email text.
    """
    
    image_tags = inline_image_regex_gmail.findall(message_content) + inline_image_regex_outlook.findall(message_content)

    for image_tag in image_tags:
        message_content = message_content.replace(image_tag, f'\n{image_tag}\n')

    return message_content

def is_filename_an_image(attachment_file_path):
    """
        Checks if a filepath points to an image.
    """
    
    try:
        Image.open(attachment_file_path)
        return True
    except UnidentifiedImageError:
        return False

def is_attachment_an_image(attachment):
    """
        Checks if an attachment file is an image.
    """
    
    try:
        Image.open(
            io.BytesIO(
                attachment.payload
            )
        )
        return True
    except UnidentifiedImageError:
        return False
    
def display_if_image(image_file_path):
    """
        Prints a file to the terminal if it is an image.
    """
    
    if not is_filename_an_image(image_file_path):
        return
        
    try:
        subprocess.call(
            f'~/.cargo/bin/viu "{image_file_path}"',
            shell=True
        )
    except KeyboardInterrupt:
        pass
        
def display_first_image_attachment_you_can_find(attachments):
    for attachment in attachments:
        if is_attachment_an_image(attachment):
            return display_attachment(attachment)
        
def display_inline_image(attachment_identifier, attachments, use_cid=False):
    """
        Prints an image to the terminal identified by an inline image tag in the email.
    """
    
    if use_cid:
        for attachment in attachments:
            if attachment.content_id[1:-1] == attachment_identifier:
                return display_attachment(attachment)
    else:
        for attachment in attachments:
            if attachment.filename == attachment_identifier:
                return display_attachment(attachment)
                
    return display_first_image_attachment_you_can_find(attachments)

def display_attachment(attachment, downloaded_attachment_location_map=None):
    """
        Prints an image to the terminal identified by an inline image tag in the email.
    """
    
    if downloaded_attachment_location_map and attachment.filename in downloaded_attachment_location_map:
        filepath = downloaded_attachment_location_map[attachment.filename]
    else:
        filepath = str(uuid.uuid4())
        attachment.download(filepath)

    display_if_image(filepath)
    return filepath

def read_new_messages():
    """
        Get all unread messages from GMail and allow the user to read the message content, mark the message as read, and send threaded reply emails.
    """

    for message in gmail_client.get_messages(seen=False):
        # print email header
        
        print('----------------------------------------')
        print(message.date.strftime('%x %-H:%-M UTC'))
        print(f'From: {message.from_}')
        print(f"To: {', '.join(message.to)}")
        print(f"CC: {', '.join(message.cc)}")
        print(f"BCC: {', '.join(message.bcc)}")
        print(f'Subject: {message.subject}\n') 

        # ask user how to react to email
        user_input_validated = ask_for_user_input(
            '(R)ead, (M)ark read, (S)kip:',
            ('R', 'M', 'S')
        )

        downloaded_attachment_location_map = {}

        # read the email
        if user_input_validated == 'R':
        
            # get email text
            message_text = message.text if message.text else message.html_text
            
            message_length = len(message_text)
            
            # if email is long, ask user how many characters they want to see
            if message_length >= LONG_PRINTED_STRING_MINIMUM_LENGTH:
                length_to_print = ask_for_integer_input(
                    f'This message is long at {message_length} characters. It might be a long reply chain. How many characters do you want to see (taken from the beginning)? Press enter to see them all.',
                    message_length
                )
            else:
                length_to_print = message_length

            # print the email to the terminal
            text_to_print = make_sure_images_are_on_seperate_lines(message_text[:length_to_print])

            for line in text_to_print.split('\n'):
                if inline_image_regex_gmail.findall(line):
                    if 'cid:' in line:
                        # [image: cid:FILENAME@hash]
                    
                        last_at_sign = line.rfind('@')
                        attachment_filename = line[12: last_at_sign]
                    else:
                        # [image: FILENAME]
                        attachment_filename = line[8:-1]
                        
                    temp_filename = display_inline_image(attachment_filename, message.attachments)
                    
                    if temp_filename:
                        downloaded_attachment_location_map[attachment_filename] = temp_filename
                        
                elif inline_image_regex_outlook.findall(line):
                    # [cid:FILENAME]
                    attachment_filename = line[5:-1]
                    temp_filename = display_inline_image(attachment_filename, message.attachments, use_cid=True)
                    
                    if temp_filename:
                        downloaded_attachment_location_map[attachment_filename] = temp_filename
                else:
                    print(line)
                
            # react to email attachments
            if len(message.attachments):
                print('---- Attachments ----')
                
                files_to_keep = []

                for index, attachment in enumerate(message.attachments):
                    content = attachment.payload
                    filename = attachment.filename
                    
                    one_index = index + 1
                    
                    should_download = ask_for_user_input(f'Do you want to (D)ownload or (S)kip attachment #{one_index} with filename "{filename}"', ('D', 'S'))

                    default_download_location = filename if filename else f'attachment-{index}'
                    
                    # download attachment
                    if should_download == 'D':
                        requested_filepath = get_valid_filepath(f'Please enter the path you want to download this file to. Press Enter for {default_download_location}')

                        requested_filepath = requested_filepath if requested_filepath else default_download_location

                        if filename in downloaded_attachment_location_map:
                            original_file_location = downloaded_attachment_location_map[filename]
                            shutil.move(original_file_location, requested_filepath)
                            downloaded_attachment_location_map[filename] = requested_filepath
                        else:
                            attachment.download(requested_filepath)
                            
                        files_to_keep.append(requested_filepath)

                    attachment_is_image = is_attachment_an_image(attachment)

                    if is_binary_string(content) and not attachment_is_image:
                        print(f'Can\'t print attachment #{one_index} with filename "{filename}" because it is a binary file')
                        continue
                        
                    should_display = ask_for_user_input(f'Do you want to (P)rint or (S)kip attachment #{one_index} with filename "{filename}"', ('P', 'S'))
                        
                    # print attachment
                    if should_display == 'P':
                        if attachment_is_image:
                            downloaded_attachment_location_map[filename] = display_attachment(attachment, downloaded_attachment_location_map)
                        else:
                            attachment_content = content.decode('utf8')

                            attachment_length = len(attachment_content)

                            if attachment_length >= LONG_PRINTED_STRING_MINIMUM_LENGTH:
                                length_to_print = ask_for_integer_input(
                                    f'This attachment is long at {attachment_length} characters. It might be a long reply chain. How many characters do you want to see (taken from the beginning)? Press enter to see them all.',
                                    attachment_length
                                )
                            else:
                                length_to_print = attachment_length

                            print(f'--- Printing Attachment #{one_index} with filename "{filename}" ---')

                            for line in attachment_content[:length_to_print].split('\n'):
                                print(line)
                                
                # cllean up attachment temp files
                for filepath in downloaded_attachment_location_map.values():
                    if filepath not in files_to_keep:
                        os.remove(filepath)

        # mark the email as read
        elif user_input_validated == 'M':
            message.mark_read()
            continue       

        # skip the email
        elif user_input_validated == 'S':
            continue
            
        # react to the email after reading it

        user_input_validated = ask_for_user_input(
            '(M)ark read, (R)eply, (S)kip:',
            ('M', 'R', 'S')
        )

        # mark email as read
        if user_input_validated == 'M':
            message.mark_read()

        # reply to email
        elif user_input_validated == 'R':
            possible_recipients = list(dict.fromkeys(
                [message.from_]
                + message.to
                + message.cc
                + message.bcc
            ))

            actual_recipients = []
            actual_cc = []
            actual_bcc = []

            # choose which emails to reply to
            for possible_recipient in possible_recipients:
                user_input_validated = None

                user_input_validated = ask_for_user_input(
                    f'For {possible_recipient}: (R)eply to, (C)c, (B)cc, (S)kip',
                    ('R', 'C', 'B', 'S')
                )

                if user_input_validated == 'R':
                    actual_recipients.append(possible_recipient)
                elif user_input_validated == 'C':
                    actual_cc.append(possible_recipient)
                elif user_input_validated == 'B':
                    actual_bcc.append(possible_recipient)
                    
            # ask if the user wants to add any recipients who weren't on the original email
            gather_to_cc_bcc_email_recipients(
                actual_recipients,
                actual_cc,
                actual_bcc,
                True
            )
             
            # make sure there is at least one recipient
            while not (actual_recipients or actual_cc or actual_bcc):
                gather_to_cc_bcc_email_recipients(
                    actual_recipients,
                    actual_cc,
                    actual_bcc,
                    True
                )
                
            # write reply email body
            reply_body = ask_for_non_blank_user_input('Type your reply:', True)

            reply_body, _ = google_workspace.gmail.utils.create_replied_message(message, reply_body, None)

            # add attachments to reply email
            attachments = add_attachments()            

            # send reply email
            gmail_client.send_message(
                to=actual_recipients,
                cc=actual_cc,
                bcc=actual_bcc,
                subject=f"Re: {message.subject}",
                text=reply_body,
                in_reply_to=message.message_id,
                thread_id=message.thread_id,
                attachments=attachments,
            )             
   
            # mark email as read after you reply to it
            message.mark_read()

def write_email():
    """
        Allow the user to write an email.
    """

    # get subject of email from user
    subject = ask_for_non_blank_user_input('Subject:')

    accept_any_input('Press Enter to write the email body')

    # get body of email from user
    body = ask_for_non_blank_user_input('Subject:', True)

    actual_recipients = []
    actual_cc = []
    actual_bcc = []
  
    # get recipients of email from user
    while not (actual_recipients or actual_cc or actual_bcc):
        gather_to_cc_bcc_email_recipients(
            actual_recipients,
            actual_cc,
            actual_bcc
        )
        
    # get attachments for email from user
    attachments = add_attachments()

    # send email (new thread, not a reply)
    gmail_client.send_message(
        to=actual_recipients,
        cc=actual_cc,
        bcc=actual_bcc,
        subject=subject,
        text=body,
        attachments=attachments,
    )

##############################################################################################################################################

# entry point

if __name__ == "__main__":

    # ask user what action they want to take
    operation = ask_for_user_input(
        'Do you want to (R)ead your new emails or (W)rite an email?',
        ('R', 'W')
    )

    # read emails
    if operation == 'R':
        read_new_messages()
        
    # write email
    elif operation == 'W':
        write_email()
