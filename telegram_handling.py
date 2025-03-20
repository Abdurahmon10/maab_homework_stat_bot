from telegram import Bot
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

BOT_USERNAME='@maab_homework_bot'
TOKEN = '7816384022:AAH0QTdTdNc9LxHBrZWGbyS9g2muFHY8nNo'




#bot commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [groups]  # Rows of buttons
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("The bot has started.")
    await update.message.reply_text("Choose a programming language:", reply_markup=reply_markup)
    


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose a class name==> choose the course===> choose the assignment number.")

async def custom1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 1")

async def custom2_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("custom 2")



#handling responses


def handle_response(text:str)-> str:
    text=text.lower()
    return "i got you"
#message

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE,):
    message_type: str = update.message.chat.type
    text: str = update.message.text


    print(f'User({update.message.chat.id}) in ({message_type}):"{text}')

    if(message_type=='group'):
        if BOT_USERNAME in text:
            new_text: str= text.replace(BOT_USERNAME,'').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response:str=handle_response(text)
    
    print(f'Bot:{response}')
    await update.message.reply_text(response)


async def error (update:Update,context:ContextTypes.DEFAULT_TYPE):
    print(f'Update:{context.error}')



def main():
    

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
    app.run_polling(poll_interval=5)






    
if __name__ == "__main__":
    print("Starting the bot.")
    main()
