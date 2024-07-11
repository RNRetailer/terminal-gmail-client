# terminal gmail client
 Gmail client in the Linux terminal. Written in Python3.\
 First, make a virtual env to put the files from this repo into.\
 Then, source the virtual env.\
 Next, install requirements with ```pip3 install -r requirements.txt```\
 Then, install viu using cargo with the instructions from https://github.com/atanunq/viu \
 Now you need to get a client secret file from https://console.developers.google.com/ and save it as client_secret.json\
 Also, please enable reading emails, marking them as read, and sending emails in the Google API.\
 Finally, run the program with ```python3 terminal_gmail_client.py```\
 The program will open a web browser for you to authorize the oauth authentication with Gmail if you are not already authorized.\
 Then, just follow the instructions in the terminal.\
 You can safely close the terminal window whenver you want.\
 The program will exit once it completes the task you've selected.\
 So, you must run it every time you want to check your unread mail or write an email.\
 Check out our paid edition here: https://terminalwebmail.com/
