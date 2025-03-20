import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd



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



def sheets(sheet_name):
    try:
        # Find the sheet ID via shortcut
        sheet_id = find_sheet_by_name(sheet_name)
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
        print(f"Worksheet  not found in sheet '{sheet_name}'.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



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
    

if __name__=="__main__":
    print(sheets("F18_test")[0].title)