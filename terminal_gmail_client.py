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
import datetime
from typing import Optional
import base64
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import urllib3
import concurrent.futures

##############################################################################################################################################

# CONFIG

# email options
MAXIMUM_RETURNED_EMAILS_FROM_SEARCH = 10

# set terminal size
SHOULD_SET_TERMINAL_SIZE = False
TERMINAL_ROWS = 32
TERMINAL_COLS = 64

# set number of characters at which an email is considered long
LONG_PRINTED_STRING_MINIMUM_LENGTH = 5000

# seperator when printing to the terminal
print_line_seperator = '\n------------------------------------------------------------\n'

##############################################################################################################################################

# magic number
ERROR_INVALID_NAME = 123

# set terminal size
if SHOULD_SET_TERMINAL_SIZE and TERMINAL_ROWS and TERMINAL_COLS:
    print('\x1b[8;{0};{1}t'.format(TERMINAL_ROWS, TERMINAL_COLS), end='', flush=True)

EMAIL_VALIDATION_REGEX = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

# pretty print
def pprint(text) -> None:
    cprint(text, "black", "on_white")

print = pprint

##############################################################################################################################################

# USER INPUT FUNCTIONS

def ask_for_user_input(prompt: str, valid_options: Iterable) -> str:
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
            
def map_user_input(prompt: str, valid_options_map: dict) -> str:
    """
        Gets user input from the terminal and checks it against an Iterable of valid options, then maps it to a specified output.
    """

    user_input = ask_for_user_input(prompt, valid_options_map.keys())
    
    return valid_options_map[user_input]


def ask_for_user_input_regex(prompt: str, regex_pattern: re.Pattern, return_on_blank=False, regex_failure_message='Input failed validation') -> Optional[str]:
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

def ask_for_non_blank_user_input(prompt: str, use_editor: bool = False) -> str:
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

def gather_to_cc_bcc_email_recipients(actual_recipients: list, actual_cc: list, actual_bcc: list, is_reply=False) -> None:
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
        
        
def add_attachments() -> list:
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

def accept_any_input(prompt: str, blank_is_none: bool = False) -> Optional[str]:
    """
        Get input from the user without checking it.
    """
    
    print(prompt)
    
    user_input = input().strip()
    
    if not user_input and blank_is_none:
        return None
        
    return user_input
    
def accept_any_input_blank_is_none(prompt: str) -> Optional[str]:
    return accept_any_input(prompt, True)
    
def ask_for_integer_input(prompt: str, maximum: int, minimum: int = 0, maximum_on_blank: bool = True) -> int:
    """
        Gets user input from the terminal and checks if it is an integer in the correct range.
    """

    while True:
        print(prompt)

        user_input = input().strip()
        
        if maximum_on_blank and not user_input:
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
        
def date_input(yes_no_prompt: str) -> Optional[datetime.date]:
    """
        Asks the user if they want to input a date and, if so, accepts the date as three separate integers and converts it to a datetime.date object.
    """
    
    user_wants_to_input_date = ask_for_user_input(yes_no_prompt, ('Y', 'N'))
    
    if user_wants_to_input_date == 'N':
        return
        
    day = ask_for_integer_input('Day?', maximum=31, minimum=1, maximum_on_blank=False)
    month = ask_for_integer_input('Month?', maximum=12, minimum=1, maximum_on_blank=False)
    year = ask_for_integer_input('Year?', maximum=9999, minimum=0, maximum_on_blank=False)
    
    return datetime.date(year, month, day)
    
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
    
def get_valid_filepath(prompt: str, return_on_blank: bool = True) -> Optional[str]:
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

def connect() -> google_workspace.gmail.GmailClient:
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
inline_image_regex_gmail = re.compile(r"\[?image: .*\]?")
inline_image_regex_outlook = re.compile(r"\[?cid:.*\]?")
html_img_tag_regex = re.compile(r'<img[^>]*src="([^"]+)"[^>]*>')

def make_sure_images_are_on_seperate_lines(message_content) -> str:
    """
        Puts breaklines around inline images in email text.
    """
    
    image_tags = inline_image_regex_gmail.findall(message_content) + inline_image_regex_outlook.findall(message_content)

    for image_tag in image_tags:
        if image_tag.startswith('['):
            message_content = message_content.replace(image_tag, f'\n{image_tag}\n')
        else:
            message_content = message_content.replace(image_tag, f'\n[{image_tag}]\n')
            
    return message_content

def download_images_in_parallel(indices_and_image_urls, images):
    def download_image(index_and_image_url):
        index, img_url = index_and_image_url

        try:
            r = requests.get(img_url, allow_redirects=True)
            filepath = str(uuid.uuid4())

            with open(filepath, 'wb') as f:
                f.write(r.content)

            images[index] = filepath
        except (requests.exceptions.InvalidURL, requests.exceptions.ConnectionError, urllib3.exceptions.MaxRetryError, urllib3.exceptions.NameResolutionError):
            images[index] = None

    with concurrent.futures.ThreadPoolExecutor() as exector: 
        exector.map(download_image, indices_and_image_urls)


def display_html_email(message, downloaded_attachment_location_map, seperator='~$%$~[[', sentinel='*&^%$#@!') -> None:
    """
        Prints HTML email and optionally downloads inline images
    """
    
    html = message.html
    image_tag_indexes = [(i.start(), i.end()) for i in re.finditer(html_img_tag_regex, html)]
    images = []
    cid_indexes = []
    indices_and_image_urls = []
    attachment_filepaths = set()
    sentinel_prefix_length = len(sentinel) + 1
    ask_to_save_inline_images = False
    last_domain_accessed = ''

    for (start, end) in image_tag_indexes:
        image_tag = message.html[start: end]

        try:
            image_index = images.index(image_tag)
        except ValueError:
            image_index = len(images)
            images.append(image_tag)

        html = html.replace(image_tag, f'{seperator}{sentinel}-{image_index}{seperator}')

    for index, image in enumerate(images):
        soup = BeautifulSoup(image, 'html.parser')
        img_src = soup.find_all('img')[0]['src']

        if img_src.startswith('cid'):
            cid = ':'.join(img_src.split(':')[1:]).strip()
            filename, filepath = download_attachment(cid, message.attachments, use_cid=True)

            if filename and filepath:
                downloaded_attachment_location_map[filename] = filepath
                attachment_filepaths.add(filepath)
            
            images[index] = filepath
            cid_indexes.append(index)
                
        elif img_src.startswith('data:'):
            # base64 encoded: decode and save as file

            base_64_string = img_src.split(',')[1:].strip()
            decoded_img_data = base64.b64decode(base_64_string)
            filepath = str(uuid.uuid4())

            with open(filepath, 'wb') as f:
                f.write(decoded_img_data)

            images[index] = filepath
        else:
            # probably points to URL

            domain = urlparse(img_src).netloc

            if domain:
                last_domain_accessed = domain
            else:
                img_src = f'https://{last_domain_accessed}{img_src}'

            indices_and_image_urls.append(
                   (index, img_src)
            )
   
    download_images_in_parallel(indices_and_image_urls, images)

    temp_html_filepath = 'temp_html.html'

    for html_chunk in html.split(seperator):
        if html_chunk.startswith(sentinel):
            image_index = int(html_chunk[sentinel_prefix_length:])

            image_to_display = images[image_index]
            
            if not image_to_display:
                continue

            is_image = display_if_image(image_to_display)

            if is_image and (image_index not in cid_indexes):
                ask_to_save_inline_images = True
        else:
            with open(temp_html_filepath, 'w') as f:
                f.write(html_chunk)
                f.flush()

            subprocess.run(['w3m', '-dump', '-o', 'color=true', temp_html_filepath])

    inline_images = [image for image in (set(images) - attachment_filepaths) if image]

    if ask_to_save_inline_images:
        should_download_inline_images = ask_for_user_input('Do you want to download inline images? (Y or N)', ('Y', 'N'))

        if should_download_inline_images == 'Y':
            for index, image in enumerate(inline_images):
                if not display_if_image(image):
                    os.remove(image)
                    continue

                should_download = ask_for_user_input(f'Do you want to (D)ownload or (S)kip the above image?', ('D', 'S'))

                default_download_location = f'inline-image-{index}'

                # download attachment
                if should_download == 'D':
                    requested_filepath = get_valid_filepath(f'Please enter the path you want to download this file to. Press Enter for {default_download_location}')

                    requested_filepath = requested_filepath if requested_filepath else default_download_location

                    shutil.move(image, requested_filepath)
                else:
                    os.remove(image)

        else:
            for image in inline_images:
                os.remove(image)

    os.remove(temp_html_filepath)

def is_filename_an_image(attachment_file_path) -> bool:
    """
        Checks if a filepath points to an image.
    """
    
    try:
        image = Image.open(attachment_file_path)

        if image.size == (1, 1):
            return False

        return True
    except UnidentifiedImageError:
        return False

def is_attachment_an_image(attachment) -> bool:
    """
        Checks if an attachment file is an image.
    """
    
    try:
        image = Image.open(
            io.BytesIO(
                attachment.payload
            )
        )

        if image.size == (1, 1):
            return False

        return True
    except UnidentifiedImageError:
        return False
    
def display_if_image(image_file_path) -> bool:
    """
        Prints a file to the terminal if it is an image.
    """
    
    if not is_filename_an_image(image_file_path):
        return False
        
    try:
        subprocess.call(
            f'~/.cargo/bin/viu "{image_file_path}"',
            shell=True
        )
    except KeyboardInterrupt:
        pass

    return True
        
def display_first_image_attachment_you_can_find(attachments) -> tuple:
    """
        Displays the first image found in the attachments.
        This is used when a malformed image tag is found in the message text.
    """
    
    for attachment in attachments:
        if is_attachment_an_image(attachment):
            return display_attachment(attachment)
            
    return None, None
        
def display_inline_image(attachment_identifier, attachments, use_cid=False) -> tuple:
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

def download_attachment(attachment_identifier, attachments, use_cid=False) -> tuple:
    """
        Download an attachment and return the filepath
    """

    matched_attachment = None

    if use_cid:
        for attachment in attachments:
            if attachment.content_id[1:-1] == attachment_identifier:
                matched_attachment = attachment
                break
    else:
        for attachment in attachments:
            if attachment.filename == attachment_identifier:
                matched_attachment = attachment
                break

    if matched_attachment:
        filepath = str(uuid.uuid4())
        attachment.download(filepath)

        return matched_attachment.filename, filepath
    else:
        return None, None

def display_attachment(attachment, downloaded_attachment_location_map=None) -> tuple:
    """
        Prints an image to the terminal identified by an inline image tag in the email.
    """
    
    if downloaded_attachment_location_map and attachment.filename in downloaded_attachment_location_map:
        filepath = downloaded_attachment_location_map[attachment.filename]
    else:
        filepath = str(uuid.uuid4())
        attachment.download(filepath)

    return filepath, display_if_image(filepath)
    
def read_new_messages() -> None:
    """
        Read messages that have not been read yet.
    """
   
    message_ids_encountered = set()

    while True:
        message_ids_encountered_this_batch = read_messages(gmail_client.get_messages(seen=False, limit=MAXIMUM_RETURNED_EMAILS_FROM_SEARCH), message_ids_encountered)

        if not message_ids_encountered_this_batch:
            return

        message_ids_encountered = message_ids_encountered.union(set(message_ids_encountered_this_batch))

def empty_trash() -> None:
    """
        Deletes all messages from the trash
    """
   
    message_ids_encountered = set()
    messages_deleted = 0

    while True:
        messages = gmail_client.get_messages(
            label_name='trash', 
            include_spam_and_trash=True, 
            limit=MAXIMUM_RETURNED_EMAILS_FROM_SEARCH
        )

        message_ids_encountered_this_batch = delete_messages(messages, message_ids_encountered)

        if not message_ids_encountered_this_batch:
            break

        messages_deleted += len(message_ids_encountered_this_batch)

        print(f'{messages_deleted} messages deleted')

        message_ids_encountered = message_ids_encountered.union(set(message_ids_encountered_this_batch))

    print('trash emptied')

def mark_read(message: google_workspace.gmail.message.Message) -> None:
    """
        Marks message as read if it is currently marked as unread.
    """
    
    if not message.is_seen:
        message.mark_read()
        
def mark_unread(message: google_workspace.gmail.message.Message) -> None:
    """
        Marks message as unread if it is currently marked as read.
    """
    
    if message.is_seen:
        message.mark_unread()
        
def mark_as_spam(message: google_workspace.gmail.message.Message) -> None:
    if 'SPAM' not in message.label_ids:
        message.add_labels('spam')
        
def mark_as_not_spam(message: google_workspace.gmail.message.Message) -> None:
    if 'SPAM' in message.label_ids:
        message.remove_labels('spam')

def delete_messages(messages, message_ids_encountered: Iterable = tuple()) -> list:
    """
        Deletes all messages passed to it
    """

    message_ids_processed = []

    for message in messages:
        message_gmail_id = message.gmail_id

        if message_gmail_id in message_ids_encountered:
            continue

        message.delete()

        message_ids_processed.append(message_gmail_id)

    return message_ids_processed


def read_messages(messages, message_ids_encountered: Iterable = tuple()) -> list:
    """
        Get all unread messages from GMail and allow the user to read the message content, mark the message as read, and send threaded reply emails.
    """

    message_ids_processed = []

    for message in messages:
        message_gmail_id = message.gmail_id

        if message_gmail_id in message_ids_encountered:
            continue

        message_ids_processed.append(message_gmail_id)

        # print email header
        
        print(print_line_seperator)
        print(message.date.strftime('%x %-H:%-M UTC'))
        print(f'From: {message.from_}')
        print(f"To: {', '.join(message.to)}")
        print(f"CC: {', '.join(message.cc)}")
        print(f"BCC: {', '.join(message.bcc)}")
        print(f'Subject: {message.subject}\n') 

        # ask user how to react to email
        user_input_validated = ask_for_user_input(
            '(P)rint, Mark (R)ead, (U)nread, Spa(m), or (N)ot Spam, (S)kip:',
            ('P', 'R', 'U', 'M', 'N', 'S')
        )

        downloaded_attachment_location_map = {}

        # read the email
        if user_input_validated == 'P':
            print(print_line_seperator)
            
            if message.html:
                display_html_email(message, downloaded_attachment_location_map)
            else:
                # get email text
                message_text = message.text
                
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
                            
                        temp_filename, is_image = display_inline_image(attachment_filename, message.attachments)
                        
                        if temp_filename:
                            downloaded_attachment_location_map[attachment_filename] = temp_filename
                            
                    elif inline_image_regex_outlook.findall(line):
                        # [cid:FILENAME]
                        attachment_filename = line[5:-1]
                        temp_filename, is_image = display_inline_image(attachment_filename, message.attachments, use_cid=True)
                        
                        if temp_filename:
                            downloaded_attachment_location_map[attachment_filename] = temp_filename
                    else:
                        print(line)
                    
            # react to email attachments
            if len(message.attachments):
                print('\n---- Attachments ----')
                
                files_to_keep = []

                for index, attachment in enumerate(message.attachments):
                    content = attachment.payload
                    filename = attachment.filename
                    
                    one_index = index + 1
                    
                    should_download = ask_for_user_input(f'\nDo you want to (D)ownload or (S)kip attachment #{one_index} with filename "{filename}"', ('D', 'S'))

                    default_download_location = filename if filename else f'attachment-{index}'
                    
                    # download attachment
                    if should_download == 'D':
                        requested_filepath = get_valid_filepath(f'\nPlease enter the path you want to download this file to. Press Enter for {default_download_location}')

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
                        print(f'\nCan\'t print attachment #{one_index} with filename "{filename}" because it is a binary file')
                        continue
                        
                    should_display = ask_for_user_input(f'\nDo you want to (P)rint or (S)kip attachment #{one_index} with filename "{filename}"', ('P', 'S'))
                        
                    # print attachment
                    if should_display == 'P':
                        if attachment_is_image:
                            downloaded_attachment_location_map[filename], _ = display_attachment(attachment, downloaded_attachment_location_map)
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

                            print(f'\n--- Printing Attachment #{one_index} with filename "{filename}" ---\n')

                            for line in attachment_content[:length_to_print].split('\n'):
                                print(line)
                                
                # cllean up attachment temp files
                for filepath in downloaded_attachment_location_map.values():
                    if filepath not in files_to_keep:
                        os.remove(filepath)

        # mark the email as read
        elif user_input_validated == 'R':
            mark_read(message)
            continue       
            
        # mark the email as unread
        elif user_input_validated == 'U':
            mark_unread(message)
            continue
            
        # mark the email as spam
        elif user_input_validated == 'M':
            mark_as_spam(message)
            continue
            
        # mark the email as not spam
        elif user_input_validated == 'N':
            mark_as_not_spam(message)
            continue

        # skip the email
        elif user_input_validated == 'S':
            continue
            
            
        # react to the email after reading it

        print('------------------------------------------------------------\n')

        user_input_validated = ask_for_user_input(
            'Mark (R)ead or (U)nread, Spa(m) or (N)ot Spam, R(e)ply, (S)kip:',
            ('R', 'U', 'M', 'N', 'E', 'S')
        )

        # mark email as read
        if user_input_validated == 'R':
            mark_read(message)
            
        # mark the email as unread
        elif user_input_validated == 'U':
            mark_unread(message) 
            
        # mark the email as spam
        elif user_input_validated == 'M':
            mark_as_spam(message)
            
        # mark the email as not spam
        elif user_input_validated == 'N':
            mark_as_not_spam(message)

        # reply to email
        elif user_input_validated == 'E':
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
                    f'For {possible_recipient}: R(e)ply to, (C)c, (B)cc, (S)kip',
                    ('E', 'C', 'B', 'S')
                )

                if user_input_validated == 'E':
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

            # add thread history to reply_body
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
            mark_read(message)
    
    return message_ids_processed

def write_email() -> None:
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
    
def search_for_emails() -> None:
    """
        Searches for messages based on user criteria.
    """
    
    from_ = accept_any_input_blank_is_none('From:')
    
    to = accept_any_input_blank_is_none('To (comma seperated):')
    
    subject = accept_any_input_blank_is_none('Subject:')
        
    seen = map_user_input(
        '(S)een, (U)nseen, or (B)oth?', 
        
        {
            'S': True,
            'U': False,
            'B': None,
        }
    )

    before = date_input('Do you want to enter a Before date? (Y or N)')
    
    after = date_input('Do you want to enter a After date? (Y or N)')
    
    label_name = accept_any_input_blank_is_none('Label name:')
    
    include_spam_and_trash = True if ask_for_user_input('Include spam and trash (Y or N)', ('Y', 'N')) == 'Y' else False
    
    limit = ask_for_integer_input(
        'Maximum returned emails?', 
        maximum=MAXIMUM_RETURNED_EMAILS_FROM_SEARCH,
        minimum=1, 
        maximum_on_blank=True
    )
     
    messages = gmail_client.get_messages(
        seen=seen, 
        from_=from_, 
        to=to, 
        subject=subject, 
        after=after, 
        before=before, 
        label_name=label_name, 
        include_spam_and_trash=include_spam_and_trash, 
        limit=limit
    )

    return read_messages(messages)

##############################################################################################################################################

# entry point

if __name__ == "__main__":

    # ask user what action they want to take
    operation = ask_for_user_input(
        '\nDo you want to:\n (R)ead your new emails\n (S)earch for emails\n (W)rite an email?\n or (E)mpty trash?\n',
        ('R', 'S', 'W', 'E')
    )

    # read emails
    if operation == 'R':
        read_new_messages()
        
    # search emails
    if operation == 'S':
        search_for_emails()
        
    # write email
    elif operation == 'W':
        write_email()

    # empty trash
    elif operation == 'E':
        empty_trash()

