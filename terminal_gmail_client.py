import google_workspace
import re
import editor
from typing import Iterable
import sys
from termcolor import cprint
import os
import errno
import tempfile

ERROR_INVALID_NAME = 123

# set terminal size
rows = 32
cols = 64
print('\x1b[8;{0};{1}t'.format(rows, cols), end='', flush=True)

EMAIL_VALIDATION_REGEX = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

def pprint(text):
    cprint(text, "black", "on_white")

print = pprint

##############################################################################################################################################

# USER INPUT FUNCTIONS

def ask_for_user_input(prompt: str, valid_options: Iterable):
    """
        Gets user input from the terminal and checks it against an Iterable of valid options
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
        Gets user input from the terminal and checks it against a regular expression
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
        Supports input from the system EDITOR as well as standard Python input
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
        Gets recipient email addresses from user input and adds them to the recipients, CC, and BCC lists in-place
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
        Get input from the user without checking it
    """
    print(prompt)
    return input()
    
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
    
def get_valid_filepath(prompt: str):
    """
        Get vaild filename from user
    """    
    while True:
        print(prompt)
            
        filepath = input().strip()
        
        if not is_path_exists_or_creatable_portable(filepath):
            print('That is not a valid path. Try again.')
            continue
            
        return filepath

##############################################################################################################################################

# SETUP FUNCTIONS

def connect():
    """
        Connects to the GMail API via OAUTH
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

def read_new_messages():
    """
        Get all unread messages from GMail and allow the user to read the message content, mark the message as read, and send threaded reply emails
    """

    for message in gmail_client.get_messages(seen=False):
        print('----------------------------------------')
        print(message.date.strftime('%x %-H:%-M UTC'))
        print(f'From: {message.from_}')
        print(f"To: {', '.join(message.to)}")
        print(f"CC: {', '.join(message.cc)}")
        print(f"BCC: {', '.join(message.bcc)}")
        print(f'Subject: {message.subject}\n') 

        user_input_validated = ask_for_user_input(
            '(R)ead, (M)ark read, (S)kip:',
            ('R', 'M', 'S')
        )

        if user_input_validated == 'R':
            message_text = message.text if message.text else message.html_text

            for line in message_text.split('\n'):
                print(line)
                
            if len(message.attachments):
                print('---- Attachments ----')

                for index, attachment in enumerate(message.attachments):
                    content = attachment.payload
                    filename = attachment.filename
                    
                    one_index = index + 1
                    
                    should_download = ask_for_user_input(f'Do you want to (D)ownload or (S)kip attachment #{one_index} with filename "{filename}"', ('D', 'S'))
                    
                    if should_download == 'D':
                        filepath = get_valid_filepath('Please enter the path you want to download this file to:')
                        attachment.download(filepath)

                    if is_binary_string(content):
                        print(f'Can\'t print attachment #{one_index} with filename "{filename}" because it is a binary file')
                        continue
                        
                    should_display = ask_for_user_input(f'Do you want to (P)rint or (S)kip attachment #{one_index} with filename "{filename}"', ('P', 'S'))
                        
                    if should_display == 'P':
                        print(f'--- Printing Attachment #{one_index} with filename "{filename}" ---')
                            
                        for line in content.decode('utf8').split('\n'):
                            print(line)

        elif user_input_validated == 'M':
            message.mark_read()
            continue       

        elif user_input_validated == 'S':
            continue

        user_input_validated = ask_for_user_input(
            '(M)ark read, (R)eply, (S)kip:',
            ('M', 'R', 'S')
        )

        if user_input_validated == 'M':
            message.mark_read()

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

            gather_to_cc_bcc_email_recipients(actual_recipients, actual_cc, actual_bcc, True)
                
            reply_body = ask_for_non_blank_user_input('Type your reply:', True)

            reply_body, _ = google_workspace.gmail.utils.create_replied_message(message, reply_body, None)

            attachments = add_attachments()            

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

            message.mark_read()

def write_email():
    """
        Allow the user to write an email
    """

    subject = ask_for_non_blank_user_input('Subject:')

    accept_any_input('Press Enter to write the email body')

    body = ask_for_non_blank_user_input('Subject:', True)

    actual_recipients = []
    actual_cc = []
    actual_bcc = []

    gather_to_cc_bcc_email_recipients(
        actual_recipients,
        actual_cc,
        actual_bcc
    )
        
    attachments = add_attachments()

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
    operation = ask_for_user_input(
        'Do you want to (R)ead your new emails or (W)rite an email?',
        ('R', 'W')
    )

    if operation == 'R':
        read_new_messages()
    elif operation == 'W':
        write_email()
