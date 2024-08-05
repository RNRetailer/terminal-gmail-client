# terminal gmail client

Access GMail in the Linux terminal easily and safely!

Boasting an extremely simple and streamlined user interface and every feature a normal email user would ever need, Terminal Webmail is your solution to the laggy browser based experience that we've been taught to accept.

Features:

- Print email in terminal including inline images and gifs

- Print attachments in terminal

- Download attachments

- Mark email as read / unread or spam / not spam

- Reply to email using the default EDITOR on your system

- Write email

- Set to, cc, and bcc for any reply or written email

# installation
 First, make a virtual env to put the files from this repo into.\
 Then, source the virtual env.\
 Next, install requirements with ```pip3 install -r requirements.txt```\
 Then, install viu using cargo with the instructions from https://github.com/atanunq/viu \
 Next, install w3m. On Debian based distributions, you might use this command: ```sudo apt install w3m```\
 Now you need to get a client secret file from https://console.developers.google.com/ and save it as client_secret.json\
 Also, please enable reading emails, marking them as read / unread, and sending emails in the Google API.\
 Finally, run the program with ```python3 terminal_gmail_client.py```\
 If it throws an error regarding distutils, run this command: ```pip3 install setuptools```\
 The program will open a web browser for you to authorize the oauth authentication with Gmail if you are not already authorized.\
 Then, just follow the instructions in the terminal.\
 You can safely close the terminal window whenver you want.\
 The program will exit once it completes the task you've selected.\
 So, you must run it every time you want to check your unread mail or write an email.\
 Check out our paid edition here: https://terminalwebmail.com/
 
 # usage notes
  Animated .gif images will loop infinitely until you end the animation with Control + C.\
  This includes .gif inline images and attachments.
  
 # screenshots
![1](https://github.com/user-attachments/assets/198d4bbd-8c6d-4925-acae-87d7b7e64df8)
![2](https://github.com/user-attachments/assets/08401dff-6355-48b4-b97e-6bfdbe9bc2c7)
![3](https://github.com/user-attachments/assets/5196d1e1-3160-4b1e-8de7-2df3aa40b230)\
![8931-0ee8-4b92-b542-4a814c7ab35f-ezgif com-optimize](https://github.com/user-attachments/assets/e8ae1f2d-b58e-46ba-9fc7-b8a70e78cdb4)
![8931-0ee8-4b92-b542-4a814c7ab35f-ezgif com-optimize](https://github.com/user-attachments/assets/e8ae1f2d-b58e-46ba-9fc7-b8a70e78cdb4)\
![8931-0ee8-4b92-b542-4a814c7ab35f-ezgif com-optimize](https://github.com/user-attachments/assets/e8ae1f2d-b58e-46ba-9fc7-b8a70e78cdb4)
![8931-0ee8-4b92-b542-4a814c7ab35f-ezgif com-optimize](https://github.com/user-attachments/assets/e8ae1f2d-b58e-46ba-9fc7-b8a70e78cdb4)
