import google_workspace
import re
import editor
from typing import Iterable
import sys
from termcolor import cprint
import os

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

            for attachment in message.attachments:
                content = attachment.payload

                if is_binary_string(content):
                    continue

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
