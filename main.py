import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from telegram import Bot
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

#data handling part

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



#obtaining groups
def groups():
    """
    Find a Google Sheet by its name via a shortcut in the shared folder.
    Returns the sheet ID if found, None otherwise.
    """
    # Query: List all files in the shared folder
    query = f"'{SHARED_FOLDER_ID}' in parents"
    print(f"Attempting query: {query}")
    
    try:
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, shortcutDetails)"
        ).execute()
        
        files = results.get('files', [])
        #print(files)
        if not files:
            print(f"No files found in the shared folder.")
            return None
        return files
    except Exception as e:
        print(f"Error finding sheet: {e}")
        return None


#groups obtaining
our_groups=[]
our_groups_names=[]


#ibtaining worksheet

def sheets(sheet_id):
    try:
        # Find the sheet ID via shortcut
        #sheet_id = find_sheet_by_name(sheet_name)
        if not sheet_id:
            return None

        # Open the sheet using its ID
        spreadsheet = sheets_client.open_by_key(sheet_id)
        
        # Get the specific worksheet
        worksheets = spreadsheet.worksheets();
        return worksheets
        
        # # Get all data as a list of lists
        # data = worksheet.get_all_values()
        
        # # Convert to DataFrame (assuming first row is headers)
        # if data:
        #     df = pd.DataFrame(data[1:], columns=data[0])
        #     return df
        # else:
        #     print(f"No data found in worksheet: {worksheet_name}")
        #     return None

    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet  not found in sheet '{sheet_id}'.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
our_sheets=[]
our_sheets_names=[]
class_id=""
subject=""
class_subject_df=pd.DataFrame()
assignments=[]

request_type = -1

def split_list(lst, chunk_size=3):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


#find sheet by name
def find_sheet_by_name(sheet_name):
    """
    Find a Google Sheet by its name via a shortcut in the shared folder.
    Returns the sheet ID if found, None otherwise.
    """
    # Query: List all files in the shared folder
    query = f"'{SHARED_FOLDER_ID}' in parents"
    print(f"Attempting query: {query}")
    
    try:
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, shortcutDetails)"
        ).execute()
        
        files = results.get('files', [])
        if not files:
            print(f"No files found in the shared folder.")
            return None
        
        # Filter for the shortcut with the given name
        for file in files:
            if (file['name'] == sheet_name and 
                file['mimeType'] == 'application/vnd.google-apps.shortcut'):
                target_id = file.get('shortcutDetails', {}).get('targetId')
                if not target_id:
                    print(f"Shortcut found but no target ID: {file['name']} (ID: {file['id']})")
                    return None
                
                # Verify the target is a Google Sheet
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
    """
    Read a specific worksheet from a Google Sheet into a Pandas DataFrame.
    Args:
        sheet_name (str): Name of the Google Sheet (shortcut name).
        worksheet_name (str): Name of the worksheet (tab) within the sheet.
    Returns:
        pd.DataFrame: Data from the worksheet, or None if not found.
    """
    try:
        # # Find the sheet ID via shortcut
        # sheet_id = find_sheet_by_name(sheet_name)
        # if not sheet_id:
        #     return None

        # # Open the sheet using its ID
        spreadsheet = sheets_client.open_by_key(sheet_id)
        
        # Get the specific worksheet
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Get all data as a list of lists
        data = worksheet.get_all_values()
        
        # Convert to DataFrame (assuming first row is headers)
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        else:
            print(f"No data found in worksheet: {worksheet_name}")
            return None

    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{worksheet_name}' not found in sheet '{sheet_id}'.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

#getting the assignments

def get__assignments(df):
    global assignments
    assignments=[i for i in df.columns if "SCORE" in i]
    assignments.append("Leaderboard")
    assignments_split=split_list(assignments)
    return assignments_split


# def get_assignment(df,assignment_num):
#     df_name_assignment=df[["First Name","Last Name",assignment_num]]
#     print(assignment_num)
#     return df_name_assignment.to_string()

# def get_lead(df):
#     df_name_hw=df[["First Name","Last Name","Finished HW"]]
#     df_name_hw=df_name_hw.sort_values(by="Finished HW")
#     return df_name_hw.to_string()

def get_assignment(df, assignment_num):
    if assignment_num not in df.columns:
        return "Assignment not found"
    df_name_assignment = df[["First Name", "Last Name", assignment_num]]
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row[assignment_num] if not pd.isna(row[assignment_num]) else 'Not Reached'}"
        for _, row in df_name_assignment.iterrows()
    )
    return result

def get_lead(df):
    df_name_hw = df[["First Name", "Last Name", "Finished HW"]]
    df_name_hw = df_name_hw.sort_values(by="Finished HW")
    result = "\n-----------------------------------------\n".join(
        f"{row['First Name']} {row['Last Name']}: {row['Finished HW']}"
        for _, row in df_name_hw.iterrows()
    )
    return result



# Example usage with input


def request1():
    sheet_name = input("Enter the name of the Google Sheet (shortcut name): ")
    worksheet_name = input("Enter the name of the worksheet (tab): ")
    df = read_sheet_to_dataframe(sheet_name, worksheet_name)
    if df is not None:
        print(f"Data from '{worksheet_name}' in '{sheet_name}':")
        print(df)
    else:
        print("Failed to load the requested data.")
    


    df_per_hw=df[['First Name','Last Name','Finished HW']]
    print(df_per_hw)

#bot handling part


BOT_USERNAME='@maab_homework_bot'
TOKEN = '7816384022:AAH0QTdTdNc9LxHBrZWGbyS9g2muFHY8nNo'




#bot commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #print([i["name"] for i in our_groups])
    
    keyboard = split_list(our_groups_names)  # Rows of buttons
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("The bot has started.")
    await update.message.reply_text("Choose a group:", reply_markup=reply_markup)
    


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a class name==> choose the course===> choose the assignment number.")

async def custom1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 1")

async def custom2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 2")



#handling responses


def handle_response(text:str,request_type:int):

    if(request_type==1):

        global our_sheets
        global our_sheets_names
        global class_id
        global class_subject_df

        sheet_id=""
        for i in our_groups:
            print(i)
            if(i["name"]=="F18_test"):
                sheet_id=i['shortcutDetails']['targetId']
                class_id=sheet_id
                break
        print(sheet_id)
        our_sheets=sheets(sheet_id)
        print(our_sheets)
        our_sheets_names=[i.title for i in our_sheets   ]
        keyboard=[i.title for i in our_sheets]
        keyboard=split_list(keyboard) # Rows of buttons
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        return ["Subjects:", reply_markup]
    elif request_type==2:
        global class_subject_df
        class_subject_df=read_sheet_to_dataframe(class_id,text)
        keyboard=get__assignments(class_subject_df)
        return ["Choose a specific assignment or leaderboard to view:",ReplyKeyboardMarkup(keyboard,resize_keyboard=True)]
    
    elif request_type==3:
        if("SCORE" in text):
            return get_assignment(class_subject_df,text)
        else:
            return get_lead(class_subject_df)


        





#message

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE,):
    message_type: str = update.message.chat.type
    text: str = update.message.text


    print(f'User({update.message.chat.id}) in ({message_type}):{text}')
    global our_groups_names
    global our_sheets_names
    global assignments
    global request_type
    print(our_groups_names)
    if(text in our_groups_names):
        request_type=1
    elif text in our_sheets_names:
        request_type=2
    elif text in assignments:
        request_type=3

    if(message_type=='group'):
        if BOT_USERNAME in text:
            new_text: str= text.replace(BOT_USERNAME,'').strip()
            response = handle_response(new_text,1)
        else:
            return
    else:
        print(request_type)
        response=handle_response(text,request_type)
    
    print(f'Bot:{response}')
    if(request_type==3):
        await update.message.reply_text(text=response)
    else:
        await update.message.reply_text(text=response[0],reply_markup=response[1])


async def error (update:Update,context:ContextTypes.DEFAULT_TYPE):
    print(f'Update:{context.error}')



def main():

    global our_groups_names
    global our_groups
    our_groups=groups()
    our_groups_names=[i['name'] for i in our_groups]
    
    

    #commands
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start_command))
    app.add_handler(CommandHandler('help',help_command))
    app.add_handler(CommandHandler('custom1',custom1_command))
    app.add_handler(CommandHandler('custom2',custom2_command))

    #message

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #error
    
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=0.1)

    
if __name__ == "__main__":
    print("Starting the bot.")
    #print([i["name"] for i in our_groups])
    
    
    main()
