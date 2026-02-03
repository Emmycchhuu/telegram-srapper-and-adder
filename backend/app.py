from telethon.sync import TelegramClient
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, UserBotError
from telethon.tl.functions.channels import InviteToChannelRequest, GetFullChannelRequest
import csv
import time
import logging
import traceback

# Configure logging
logging.basicConfig(filename='telegram_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Prompt for user inputs
api_id = input("Enter your API ID: ")
api_hash = input("Enter your API Hash: ")
phone_numbers = [input("Enter your phone number (with country code): ")]  # Add all your accounts' phone numbers here
group_username = input("Enter the group username (e.g., @yourgroup): ")
target_group_link = input("Enter the target group link (e.g., https://t.me/targetgroup): ")
csv_file = 'members.csv'  # The CSV file containing the members to be added
num_users_per_account = 50  # Number of users to add per account before taking a break
delay_between_adds = 30  # Delay between each add action in seconds
delay_between_batches = 900  # Delay between batches of adding users

# Function to scrape users from a group
def scrape_users(client, target_group_link):
    try:
        target_group = client(GetFullChannelRequest(target_group_link)).chats[0]
        participants = client.get_participants(target_group, aggressive=True)
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'username', 'access_hash', 'name'])
            for user in participants:
                if user.username:
                    username = user.username
                else:
                    username = ""
                writer.writerow([user.id, username, user.access_hash, user.first_name])
        logging.info(f"Successfully scraped users from {target_group_link}")
        print(f"Successfully scraped users from {target_group_link}")
    except Exception as e:
        logging.error(f"Failed to scrape users from {target_group_link}: {e}")
        traceback.print_exc()
        print(f"Failed to scrape users from {target_group_link}: {e}")

# Function to add users to your group
def add_users(client, target_group, num_users_per_account=50):
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            users = list(csv.reader(f))[1:]  # Skip the header
        
        for i, user in enumerate(users):
            if i % num_users_per_account == 0 and i > 0:
                logging.info("Sleeping for a while to avoid rate limiting...")
                print("Sleeping for a while to avoid rate limiting...")
                time.sleep(delay_between_batches)  # Avoid rate limiting by taking a break every batch of adds
            
            try:
                user_to_add = client.get_input_entity(int(user[0]))  # Get the user entity
                client(InviteToChannelRequest(target_group, [user_to_add]))  # Add user to group
                logging.info(f"Added {user[1]} (ID: {user[0]})")
                print(f"Added {user[1]} (ID: {user[0]})")
                time.sleep(delay_between_adds)  # Sleep to avoid flood errors
            except PeerFloodError:
                logging.error("Getting Flood Error from Telegram. Script is stopping now. Try again later.")
                print("Getting Flood Error from Telegram. Script is stopping now. Try again later.")
                break
            except UserPrivacyRestrictedError:
                logging.warning(f"User {user[1]} has privacy restrictions")
                print(f"User {user[1]} has privacy restrictions")
            except UserBotError:
                logging.error("Bots cannot perform this action. Please use a user account.")
                print("Bots cannot perform this action. Please use a user account.")
                break
            except Exception as e:
                logging.error(f"Error: {e}")
                traceback.print_exc()
                print(f"Error: {e}")
    except Exception as e:
        logging.error(f"Failed to read CSV file or add users: {e}")
        traceback.print_exc()
        print(f"Failed to read CSV file or add users: {e}")

# Function to handle OTP-based login
def login_with_otp(client, phone):
    try:
        client.connect()
        if not client.is_user_authorized():
            try:
                client.send_code_request(phone)
                otp_code = input(f'Enter the OTP for {phone}: ')  # Prompt the user for the OTP
                client.sign_in(phone, otp_code)
            except Exception as e:
                logging.error(f"Failed to login for {phone}: {e}")
                print(f"Failed to login for {phone}: {e}")
        return client
    except Exception as e:
        logging.error(f"Failed to connect with {phone}: {e}")
        print(f"Failed to connect with {phone}: {e}")
        traceback.print_exc()

# Main Function
def main():
    for phone in phone_numbers:
        client = TelegramClient(phone, api_id, api_hash)
        client = login_with_otp(client, phone)  # Login with OTP
        if client.is_user_authorized():
            try:
                scrape_users(client, target_group_link)  # Scrape users from target group
                add_users(client, group_username, num_users_per_account)  # Add users to your group
            finally:
                client.disconnect()
        else:
            logging.warning(f"Could not authorize {phone}. Skipping...")
            print(f"Could not authorize {phone}. Skipping...")

if __name__ == '__main__':
    main()
