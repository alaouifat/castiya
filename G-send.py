import os
import random
import time
import smtplib
import string
import re
import datetime
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import dns.resolver  # Ensure you have dnspython installed

# Configuration Parameters
BCC_COUNT = 100
WAIT_BETWEEN_BATCHES = 3
FIXED_DOMAIN = 'kinderroller.org'  # Set the fixed domain for return path
FROM_NAME = "AARP Services"
FROM_EMAIL = "service@[customerservicehealth.com]"
SUBJECT = "Confirms - Your April AARP Membership: The Smart Choice for 50+"
TO_ADDR = ''  # Add a valid recipient email address

# Semaphore for controlling concurrent threads
max_concurrent_threads = 1
semaphore = threading.Semaphore(max_concurrent_threads)

# Function to generate random strings
def generate_random_string(length, char_type):
    char_sets = {
        'an': string.ascii_letters + string.digits,
        'n': string.digits,
        'a': string.ascii_letters
    }
    return ''.join(random.choices(char_sets[char_type], k=length))

# Function to add spaces to a string
def add_spaces(random_string, num_spaces):
    positions = random.sample(range(len(random_string)), num_spaces)
    spaced_string = list(random_string)

    for pos in sorted(positions, reverse=True):
        spaced_string.insert(pos, ' ')

    return ''.join(spaced_string)

# Function to replace tags in text
def replace_tags(text):
    date_string = datetime.date.today().strftime('%Y-%m-%d')
    text = re.sub(r'\[mail_date\]', date_string, text)

    pattern = r'\[(an|n|a)_(\d+)\]'
    while match := re.search(pattern, text):
        char_type, length_str = match.groups()
        length = int(length_str)
        replacement = generate_random_string(length, char_type)
        text = text[:match.start()] + replacement + text[match.end():]

    return text

# Function to get MX record for a domain
def get_mx_record(domain):
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return str(mx_records[0].exchange).rstrip('.')
    except Exception as e:
        print(f"Failed to resolve MX record for {domain}: {e}")
        return None

# Function to read file content
def read_file_content(file_path, encoding='utf-8'):
    if not os.path.exists(file_path):
        sys.exit(f"Error: {file_path} does not exist")
    with open(file_path, 'r', encoding=encoding) as file:
        return file.readlines()

# Function to send emails
def send_emails(bcc_emails_array):
    if not bcc_emails_array:
        return

    domain = bcc_emails_array[0].split('@')[1]
    mx_record = get_mx_record(domain)
    if mx_record is None:
        print(f"Cannot send emails, no MX record for domain: {domain}")
        return

    random_string = generate_random_string(10, 'n')
    random_string_with_spaces = add_spaces(random_string, 0)  # Adjust the number of spaces here
    random_return_path = random_string_with_spaces + '@' + FIXED_DOMAIN

    msg = MIMEMultipart()
    msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['To'] = TO_ADDR
    msg['Bcc'] = ', '.join(bcc_emails_array)
    msg['Subject'] = SUBJECT
    msg['Importance'] = 'high'
    msg['X-Priority'] = '1'
    msg['X-EN-OrigIP'] = '4.172.241.144'
    msg['List-Unsubscribe'] = '<https://www.tumblr.com/account/optout/relay%40akitsana.shop?type=ask_answer&hash=X9RY7rHjpGYrvEMHjWyp3RrmYU>'


    # Combine header and HTML content
    full_message = header_content + "\n\n" + html_content
    msg.attach(MIMEText(full_message, 'html'))

    with semaphore:
        try:
            random_subdomain = generate_random_string(16, 'an')
            local_hostname = f'{random_subdomain}.msn.com'
            with smtplib.SMTP(mx_record, local_hostname=local_hostname) as smtp_server:
                smtp_server.sendmail(random_return_path, [TO_ADDR] + bcc_emails_array, msg.as_string())
            print(f'Email sent successfully to: {bcc_emails_array}')
        except Exception as e:
            print(f"Failed to send email to {bcc_emails_array}: {e}")

# Main Execution
header_lines = read_file_content('header.txt')
header_content = ''.join(replace_tags(line) for line in header_lines)

html_content_match = re.search(r'(?s)(?<=<html>)(.*?)(?=</html>)', ''.join(header_lines))
html_content = html_content_match.group(0) if html_content_match else ""

data = read_file_content('data.txt')
data_count = 0

while data_count < len(data):
    bcc_emails_array = [data[i].strip() for i in range(data_count, min(data_count + BCC_COUNT, len(data))) ]
    data_count += BCC_COUNT

    threading.Thread(target=send_emails, args=(bcc_emails_array,)).start()
    print(f'Waiting for {WAIT_BETWEEN_BATCHES} seconds between batches...')
    time.sleep(WAIT_BETWEEN_BATCHES)

print("All emails sent.")
