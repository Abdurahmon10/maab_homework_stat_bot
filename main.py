import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# ---------------- Data Handling Setup ----------------

# Define the scopes for Drive and Sheets APIs (read-only)
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = 'maabbot.json'
SHARED_FOLDER_ID = "1c8M22kmwXJD5gaW1NOiH6Z-AYxUASxoP"

# Authenticate using the service account
credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Initialize clients
drive_service = build('drive', 'v3', credentials=credentials)
sheets_client = gspread.authorize(credentials)

# Helper function to split list into chunks (rows)
def split_list(lst, chunk_size=3):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

# Get groups from the shared folder
def groups():
    query = f"'{SHARED_FOLDER_ID}' in parents"
    print(f"Attempting query: {query}")
    try:
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, shortcutDetails)"
        ).execute()
        files = results.get('files', [])
        if not files:
            print("No files found in the shared folder.")
        return files
    except Exception as e:
        print(f"Error finding sheet: {e}")
        return []

our_groups = groups()
# Exclude the 'Group_Ids' file from group selection
our_groups_names = [i['name'] for i in our_groups if i["name"] != "Group_Ids"]

# Function to open a sheet (by its target id)
def sheets(sheet_id):
    try:
        spreadsheet = sheets_client.open_by_key(sheet_id)
        worksheets = spreadsheet.worksheets()
        return worksheets
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Read a specific worksheet into a DataFrame
def read_sheet_to_dataframe(sheet_id, worksheet_name):
    try:
        spreadsheet = sheets_client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_values()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        else:
            print(f"No data found in worksheet: {worksheet_name}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# ---------------- Assignment & Leaderboard Functions ----------------

def get__assignments(df):
    assignments = [i for i in df.columns if "SCORE" in i]
    assignments.append("Leaderboard")
    assignments.append("Return")
    assignments_split = split_list(assignments)
    return assignments_split

def get_assignment(df, assignment_num):
    if assignment_num not in df.columns:
        return "Assignment not found"
    df_name_assignment = df[["First Name", "Last Name", assignment_num]]
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row[assignment_num] if not pd.isnull(row[assignment_num]) and row[assignment_num] != '' else 'Not Reached'}"
        for _, row in df_name_assignment.iterrows()
    )
    result = assignment_num + " :\n" + result
    return result

def get_lead(df):
    df_name_hw = df[["First Name", "Last Name", "Finished HW"]]
    df_name_hw = df_name_hw.sort_values(by="Finished HW", ascending=False)
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row['Finished HW']}"
        for _, row in df_name_hw.iterrows()
    )
    result = "Leaderboard :\n" + result
    return result

# ---------------- Bot Response Handling ----------------

def handle_response(text: str, request_type: int, user_data: dict):
    # Request type 1: Handle group selection and list subjects
    if request_type == 1:
        sheet_id = ""
        # Here, preserving your original behavior by looking for a specific group ("F18_test").
        # If you prefer using the text (group name) instead, replace "F18_test" with text.
        for i in our_groups:
            print(i)
            if i["name"] == "F18_test":
                sheet_id = i['shortcutDetails']['targetId']
                user_data['class_name'] = i["name"]
                user_data['class_id'] = sheet_id
                break
        print(sheet_id)
        user_data['our_sheets'] = sheets(sheet_id)
        our_sheets_names = [ws.title for ws in user_data['our_sheets']]
        user_data['our_sheets_names'] = our_sheets_names
        keyboard = [ws.title for ws in user_data['our_sheets']]
        keyboard.append("Return")
        keyboard = split_list(keyboard)  # Format rows of buttons
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        return ["Subjects:", reply_markup]
    
    # Request type 2: Handle subject selection and list assignments/leaderboard options
    elif request_type == 2:
        if text != "Return":
            user_data['subject'] = text
        user_data['class_subject_df'] = read_sheet_to_dataframe(user_data['class_id'], user_data['subject'])
        keyboard = get__assignments(user_data['class_subject_df'])
        # Save flat list of assignments for later lookup
        user_data['assignments'] = [item for sublist in keyboard for item in sublist]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        return ["Choose a specific assignment or leaderboard to view:", reply_markup]
    
    # Request type 3: Handle assignment/leaderboard viewing
    elif request_type == 3:
        if "SCORE" in text:
            return get_assignment(user_data['class_subject_df'], text)
        else:
            return get_lead(user_data['class_subject_df'])
    else:
        keyboard = split_list(our_groups_names)
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        return ["Choose a group:", reply_markup]

# ---------------- Telegram Bot Commands ----------------

BOT_USERNAME = '@maab_homework_bot'
TOKEN = '7816384022:AAH0QTdTdNc9LxHBrZWGbyS9g2muFHY8nNo'

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = split_list(our_groups_names)
    await update.message.reply_text("The bot has started.")
    await update.message.reply_text("Choose a group:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a class name==> choose the course===> choose the assignment number.")

async def custom1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 1")

async def custom2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 2")

# ---------------- Handling User Messages ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text
    user_data = context.user_data

    print(f'User({update.message.chat.id}) in ({message_type}): {text}')
    
    # Determine request type based on user input and stored state
    if text in our_groups_names:
        user_data['request_type'] = 1
    elif text == "Return":
        user_data['request_type'] = user_data.get('request_type', 0) - 1
    elif 'our_sheets_names' in user_data and text in user_data['our_sheets_names']:
        user_data['request_type'] = 2
    elif 'assignments' in user_data and text in user_data['assignments']:
        user_data['request_type'] = 3
    else:
        await update.message.reply_text("Try again, there is something wrong with your input!")
        return

    request_type = user_data['request_type']
    
    # Special handling for group messages
    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response = handle_response(new_text, 1, user_data)
        else:
            return
    else:
        response = handle_response(text, request_type, user_data)
    
    print(f'Bot: {response}')
    # For request type 3, send the response to a group and then to the user
    if request_type == 3:
        # Read the group IDs from a specific sheet
        group_ids = read_sheet_to_dataframe("16EeVxqYoco_jBN4V44JJWcse3oaGOpG6OS3oz_5GE60", "Group_Ids")
        print(group_ids)
        # Look up the target chat id using the lower-case class name
        target_ids = group_ids[group_ids["Group_name"] == user_data['class_name'].lower()]
        target_id = target_ids["GROUP_CHAT_ID"].iloc[0] if not target_ids.empty else None
        print(target_ids)
        if target_id:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=response
                )
            except Exception as e:
                print(f"Failed to send to group {target_id}: {e}") 
        else:
            print("Chat id not found")
        await update.message.reply_text(text=response)
    else:
        # For request types 1, 2, or default, the response is a list: [text, reply_markup]
        await update.message.reply_text(text=response[0], reply_markup=response[1])

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update: {context.error}')

# ---------------- Main Function ----------------

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Register command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom1', custom1_command))
    app.add_handler(CommandHandler('custom2', custom2_command))
    
    # Register message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Register error handler
    app.add_error_handler(error)
    
    print("Polling...")
    app.run_polling(poll_interval=0.1)

if __name__ == "__main__":
    print("Starting the bot.")
    main()
