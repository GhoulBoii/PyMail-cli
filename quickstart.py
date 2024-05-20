import os.path
import base64

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
from bs4 import BeautifulSoup

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]

def get_credentials():
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
  return creds


def gmail_send_message(from_email,to_email,subject,body):
  creds = get_credentials()

  try:
    service = build("gmail", "v1", credentials=creds)
    message = EmailMessage()

    message.set_content(body)

    message["To"] = to_email
    message["From"] = from_email
    message["Subject"] = subject

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {"raw": encoded_message}
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Email has been sent with the following id: {send_message["id"]}')
  except HttpError as error:
    print(f"An error occurred: {error}")
    send_message = None
  return send_message

def receive_messages(message_no):
  creds = get_credentials()
  service = build("gmail", "v1", credentials=creds)
  result = service.users().messages().list(maxResults=message_no, userId='me').execute()
  messages = result.get('messages')
  for msg in messages:
    # Get the message from its id
    txt = service.users().messages().get(userId='me', id=msg['id']).execute()
    try:
        # Get value of 'payload' from dictionary 'txt'
        payload = txt['payload']
        headers = payload['headers']

        # Look for Subject and Sender Email in the headers
        for d in headers:
            if d['name'] == 'Subject':
                subject = d['value']
            if d['name'] == 'From':
                sender = d['value']

        # The Body of the message is in Encrypted format. So, we have to decode it.
        # Get the data and decode it with base 64 decoder.
        parts = payload.get('parts')[0]
        data = parts['body']['data']
        data = data.replace("-","+").replace("_","/")
        decoded_data = base64.b64decode(data)

        # Now, the data obtained is in lxml. So, we will parse
        # it with BeautifulSoup library
        soup = BeautifulSoup(decoded_data , "lxml")
        body = soup.body()

        # Printing the subject, sender's email and message
        print("\033[1;33;40mSubject: ", subject)
        print("\033[1;33;40mFrom: ", sender)
        print("Message: ", body)
        print('\n\n---------------------------------------------------------------------\n\n')

    except:
        pass

def threads():
  """Display threads with long conversations(>= 3 messages)
  Return: None
  """
  try:
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    threads = (
        service.users().threads().list(maxResults=100,userId="me").execute().get("threads", [])
    )
    for thread in threads:
      tdata = (
          service.users().threads().get(userId="me", id=thread["id"]).execute()
      )
      nmsgs = len(tdata["messages"])

      # skip if <3 msgs in thread
      if nmsgs > 2:
        msg = tdata["messages"][0]["payload"]
        subject = ""
        for header in msg["headers"]:
          if header["name"] == "Subject":
            subject = header["value"]
            break
        if subject:  # skip if no Subject line
          print(f"- {subject}, {nmsgs}")
    return threads

  except HttpError as error:
    print(f"An error occurred: {error}")


def main():
    print("Python Script to Interact with Gmail")
    print("Would you like to: ")
    print("1) Send email")
    print("2) See your inbox")
    print("3) Get your recent threads")
    choice = int(input())

    if choice == 1:
        from_email = input("Enter your email address: ")
        to_email = input("Enter the receiver's email address: ")
        subject = input("Enter the subject of the email: ")
        body = input("Enter the body of the email:\n")
        gmail_send_message(from_email,to_email,subject,body)
    elif choice == 2:
        message_no = int(input("Enter number of messages you would like to see from your inbox (latest first): "))
        receive_messages(message_no)
    elif choice == 3:
        threads()
    else:
        print("Wrong input.")

if __name__ == "__main__":
    main()
