import os
import time
import asyncio
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --------------------------
# Global shared variables
# --------------------------
# These values are shared among all users and set once when the bot starts.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]
SERVICE_ACCOUNT_FILE = 'maabbot.json'
SHARED_FOLDER_ID = "1c8M22kmwXJD5gaW1NOiH6Z-AYxUASxoP"

# Authenticate using the service account
credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)
sheets_client = gspread.authorize(credentials)

# Shared groups data; loaded once during startup.
our_groups = []
our_groups_names = []

# These globals below are for data that is intended to be shared
# (e.g. assignment names) but note that user-specific state like
# selected class or subject is now moved to context.user_data.
our_sheets = []
our_sheets_names = []
assignments = []

# Bot token (store it as an environment variable for security)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = '@maab_homework_bot'


# --------------------------
# Utility Functions
# --------------------------
def split_list(lst, chunk_size=3):
    #Splits a list into chunks for keyboard layout.
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_api_call(func, retries=3, delay=2):
    #Retry wrapper for API calls
    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            print(f"API Error: {e}, retrying in {delay} seconds...")
            time.sleep(delay)
    return None


def groups():
    # Get files (groups) from the shared folder.
    # These groups are shared across all users.
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
            return []
        return files
    except Exception as e:
        print(f"Error finding groups: {e}")
        return []


def sheets(sheet_id):
    #Return the worksheets of a given Google Sheet ID.
    try:
        if not sheet_id:
            return None
        spreadsheet = sheets_client.open_by_key(sheet_id)
        worksheets = spreadsheet.worksheets()
        return worksheets
    except Exception as e:
        print(f"An error occurred in sheets(): {e}")
        return None


def find_sheet_by_name(sheet_name):
 
    # Find a Google Sheet by its shortcut name in the shared folder.
    # This function returns the target sheet ID if found.
 
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
            return None

        # Look for a shortcut with the given name
        for file in files:
            if (file['name'] == sheet_name and 
                file['mimeType'] == 'application/vnd.google-apps.shortcut'):
                target_id = file.get('shortcutDetails', {}).get('targetId')
                if not target_id:
                    print(f"Shortcut found but no target ID: {file['name']} (ID: {file['id']})")
                    return None

                # Verify target is a Google Sheet
                target_file = drive_service.files().get(
                    fileId=target_id,
                    fields="id, name, mimeType"
                ).execute()
                if target_file.get('mimeType') != 'application/vnd.google-apps.spreadsheet':
                    print(f"Target of shortcut is not a Google Sheet: {target_file['name']}")
                    return None

                print(f"Found sheet via shortcut: {target_file['name']} (ID: {target_id})")
                return target_id

        print(f"No shortcut found for '{sheet_name}' in the shared folder.")
        return None

    except Exception as e:
        print(f"Error finding sheet: {e}")
        return None


def read_sheet_to_dataframe(sheet_id, worksheet_name):
    #Read a specific worksheet from a Google Sheet into a DataFrame.
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
        print(f"Error reading worksheet '{worksheet_name}' from sheet '{sheet_id}': {e}")
        return None


def get__assignments(df):
    
    #Get a list of assignment columns from the DataFrame.
    global assignments
    assignments = [i for i in df.columns if "SCORE" in i]
    assignments.append("Leaderboard")
    assignments.append("Return")
    return split_list(assignments)


def get_assignment(df, assignment_num):
    if assignment_num not in df.columns:
        return "Assignment not found"
    df_name_assignment = df[["First Name", "Last Name", assignment_num]]
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row[assignment_num] if row[assignment_num] else 'Not Reached'}"
        for _, row in df_name_assignment.iterrows()
    )
    return result


def get_lead(df):
    df_name_hw = df[["First Name", "Last Name", "Finished HW"]]
    df_name_hw = df_name_hw.sort_values(by="Finished HW", ascending=False)
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row['Finished HW']}"
        for _, row in df_name_hw.iterrows()
    )
    return result

# Bot Command Handlers-
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Shared global groups are used here to build the keyboard.
    keyboard = split_list(our_groups_names)  # rows of buttons
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("The bot has started.")
    await update.message.reply_text("Choose a group:", reply_markup=reply_markup)
    
    # Initialize user-specific state in context.user_data if not already set.
    user_data = context.user_data
    if "request_type" not in user_data:
        user_data["request_type"] = 0  # initial step
    # We'll store per-user selections: class_id, subject, and class_subject_df as needed.


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a class name ==> choose the course ==> choose the assignment number.")


async def custom1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 1")


async def custom2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 2")


# Core Handler Logic
def handle_response(text: str, request_type: int, user_data: dict):

    # request_type values:
    # 0: Choose a group.
    # 1: Group selected, now choose a subject.
    # 2: Subject selected, now choose assignment/leaderboard.
    # 3: Assignment/leaderboard selected, show results.
    
    # We'll use the global variables our_groups, our_groups_names, our_sheets, our_sheets_names, and assignments
    if request_type == 0:
        # User selected a group from the keyboard.
        # Find the group matching the text.
        sheet_id = ""
        for group in our_groups:
            if group["name"] == text:
                sheet_id = group.get("shortcutDetails", {}).get("targetId", "")
                user_data["class_id"] = sheet_id  # save in user_data
                break
        if not sheet_id:
            return ["Group not found!", None]
        # Load subjects (worksheets) from this sheet.
        sheets_list = sheets(sheet_id)
        if not sheets_list:
            return ["No subjects found in the group.", None]
        user_data["sheets_list"] = sheets_list  # store list of worksheets in user_data
        global our_sheets, our_sheets_names
        our_sheets = sheets_list
        our_sheets_names = [ws.title for ws in sheets_list]
        keyboard = our_sheets_names + ["Return"]
        keyboard = split_list(keyboard)
        return ["Subjects:", ReplyKeyboardMarkup(keyboard, resize_keyboard=True)]
    
    elif request_type == 1:
        # User selected a subject (worksheet)
        if text != "Return":
            user_data["subject"] = text
        # Read the worksheet data into a DataFrame
        df = read_sheet_to_dataframe(user_data.get("class_id", ""), text)
        if df is None:
            return ["Failed to load subject data.", None]
        user_data["class_subject_df"] = df
        keyboard = get__assignments(df)
        return ["Choose a specific assignment or leaderboard to view:", ReplyKeyboardMarkup(keyboard, resize_keyboard=True)]
    
    elif request_type == 2:
        # User selected an assignment or leaderboard
        df = user_data.get("class_subject_df")
        if df is None:
            return ["Data not found.", None]
        if "SCORE" in text:
            result = get_assignment(df, text)
        else:
            result = get_lead(df)
        return [result, None]
    
    else:
        # Default: show groups again
        keyboard = split_list(our_groups_names)
        return ["Choose a group:", ReplyKeyboardMarkup(keyboard, resize_keyboard=True)]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    print(f'User({update.message.chat.id}): {text}')

    # Retrieve per-user state; if not present, initialize it.
    request_type = user_data.get("request_type", 0)
    
    # Update request_type based on user input:
    if text == "Return":
        # Move one step back, but don't let it go below 0
        user_data["request_type"] = max(0, request_type - 1)
        request_type = user_data["request_type"]
    else:
        # Decide new request_type based on the input text and current state.
        # Here we check if the input matches global shared lists.
        if request_type == 0 and text in our_groups_names:
            user_data["request_type"] = 1
            request_type = 1
        elif request_type == 1 and text in our_sheets_names:
            user_data["request_type"] = 2
            request_type = 2
        elif request_type == 2 and (text in assignments or "SCORE" in text or text == "Leaderboard"):
            user_data["request_type"] = 3
            request_type = 3
        # Otherwise, we leave request_type as is.
    
    response = handle_response(text, request_type, user_data)
    
    print(f'Bot response: {response}')
    if request_type == 3:
        # Final step, just send text.
        await update.message.reply_text(text=response[0])
    else:
        # Send message with a keyboard if provided.
        await update.message.reply_text(text=response[0], reply_markup=response[1])


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Error: {context.error}')


# main
def main():
    global our_groups, our_groups_names
    # Load global groups data once
    our_groups = groups()
    our_groups_names = [group['name'] for group in our_groups]
    
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("custom1", custom1_command))
    app.add_handler(CommandHandler("custom2", custom2_command))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    print("Polling...")
    app.run_polling(poll_interval=0.1)


if __name__ == "__main__":
    print("Starting the bot.")
    main()
