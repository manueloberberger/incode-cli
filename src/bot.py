import os
import sys
import logging
import asyncio
import re
from datetime import datetime, timedelta
from rich.prompt import Prompt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from src.config import load_credentials, update_credentials, console, VERSION
from src.api import IncodeRequests
from src.pdf import export_to_pdf

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Silent httpx logger slightly
logging.getLogger("httpx").setLevel(logging.WARNING)

# States for ConversationHandler
WAITING_FOR_DATE = 1

class IncodeBot:
    def __init__(self, api: IncodeRequests):
        self.api = api
        self.config = load_credentials()
        self.ensure_config()

    def ensure_config(self):
        """Ensures Telegram config exists."""
        if not self.config or not self.config.get("telegram_token") or not self.config.get("allowed_user_id"):
            console.print("[bold yellow]Telegram Konfiguration fehlt.[/bold yellow]")
            token = Prompt.ask("Telegram Bot Token")
            try:
                user_id = int(Prompt.ask("Deine Telegram User ID (Zahlen)"))
            except ValueError:
                console.print("[red]User ID muss eine Zahl sein.[/red]")
                sys.exit(1)
            
            update_credentials({"telegram_token": token, "allowed_user_id": user_id})
            self.config = load_credentials()
            console.print("[green]Telegram Konfiguration gespeichert.[/green]")

    def send_document(self, chat_id: int, file_path: str, caption: str = None) -> bool:
        """Synchronous wrapper to send a document (for CLI usage)."""
        try:
            return asyncio.run(self._send_document_async(chat_id, file_path, caption))
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            return False

    async def _send_document_async(self, chat_id: int, file_path: str, caption: str) -> bool:
        try:
            from telegram import Bot
            bot = Bot(token=self.config['telegram_token'])
            async with bot:
                with open(file_path, 'rb') as f:
                    await bot.send_document(chat_id=chat_id, document=f, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Async send error: {e}")
            return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Start command received from {update.effective_user.id}")
        keyboard = [
            [InlineKeyboardButton("📅 Meine Dienste (PDF)", callback_data='my_duties')],
            [InlineKeyboardButton("🚑 Tagesplan (PDF)", callback_data='today_plan')],
            [InlineKeyboardButton("📆 Anderes Datum", callback_data='custom_date')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✨ *Incode CLI Bot v{VERSION}* ✨\n\n"
            f"Hallo! Was möchtest du tun?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parses button clicks."""
        query = update.callback_query
        user_id = query.from_user.id
        logger.info(f"Button clicked: {query.data} by user {user_id}")
        
        allowed_id = str(self.config.get("allowed_user_id", ""))
        if str(user_id) != allowed_id:
            logger.warning(f"Access denied for user {user_id} (Allowed: {allowed_id})")
            await query.answer("Kein Zugriff.", show_alert=True)
            return

        await query.answer() 
        
        if query.data == 'custom_date':
            # Ask for date
            await query.message.reply_text(
                "📅 Bitte gib das Datum ein (Format: TT.MM. oder TT.MM.JJJJ).\n"
                "Oder klicke hier:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Morgen", callback_data='date_tomorrow')],
                    [InlineKeyboardButton("Übermorgen", callback_data='date_after_tomorrow')]
                ])
            )
            return WAITING_FOR_DATE

        filter_today = (query.data == 'today_plan')
        await self._process_duties_request(query.message, context, filter_today, chat_id=user_id)
        return ConversationHandler.END

    async def date_button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quick date selection buttons."""
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer() 
        
        target_date = datetime.now()
        if query.data == 'date_tomorrow':
            target_date += timedelta(days=1)
        elif query.data == 'date_after_tomorrow':
            target_date += timedelta(days=2)
            
        await self._process_duties_request(query.message, context, True, chat_id=user_id, custom_date=target_date)
        return ConversationHandler.END

    async def manual_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manual text input for date."""
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        try:
            # Try parsing DD.MM. or DD.MM.YYYY
            current_year = datetime.now().year
            
            # Auto-append year if missing
            if re.match(r'^\d{1,2}\.\d{1,2}\.?$', text):
                text = text.rstrip('.') + f".{current_year}"
            
            target_date = datetime.strptime(text, '%d.%m.%Y')
            await self._process_duties_request(update.message, context, True, chat_id=user_id, custom_date=target_date)
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ Ungültiges Format. Bitte nutze TT.MM. (z.B. 15.01.)")
            return WAITING_FOR_DATE

    async def unauthorized(self, update: Update):
        uid = update.effective_user.id
        logger.warning(f"Unauthorized access attempt from {uid}")

    async def send_duties(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for text commands like /dienste"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logger.info(f"Text command received: {update.message.text} from {user_id}")
        
        allowed_id = str(self.config.get("allowed_user_id", ""))
        if str(user_id) != allowed_id:
            await self.unauthorized(update)
            return

        cmd = update.message.text.lower()
        filter_today = "/tagesplan" in cmd or "/heute" in cmd
        
        await self._process_duties_request(update.message, context, filter_today, chat_id)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Vorgang abgebrochen.")
        return ConversationHandler.END

    async def _process_duties_request(self, message_obj, context, filter_today, chat_id, custom_date=None):
        """Shared logic for processing duty requests."""
        try:
            date_label = "Heute"
            if custom_date:
                date_label = custom_date.strftime('%d.%m.%Y')
                
            logger.info(f"Processing request for chat {chat_id} (Date={date_label})")
            await context.bot.send_chat_action(chat_id=chat_id, action='upload_document')
            
            duties = await asyncio.to_thread(self._fetch_duties_sync, filter_today, custom_date)

            if not duties:
                logger.info("No duties found to send.")
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Keine Dienste gefunden für {date_label}.")
                return

            if filter_today or custom_date:
                d_obj = custom_date if custom_date else datetime.now()
                title = f"Tagesplan {d_obj.strftime('%d.%m.%Y')}"
                filename = f"Tagesplan_{d_obj.strftime('%Y-%m-%d')}_{datetime.now().strftime('%H-%M')}.pdf"
            else:
                title = "Meine Dienste"
                filename = f"Mein_Dienstplan_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf"

            logger.info(f"Generating PDF: {filename}")
            success = await asyncio.to_thread(export_to_pdf, duties, filename, title)

            if success:
                logger.info(f"Uploading PDF {filename}...")
                with open(filename, 'rb') as f:
                    await context.bot.send_document(chat_id=chat_id, document=f, caption=f"📄 {title}")
                
                if os.path.exists(filename):
                    os.remove(filename)
                logger.info("Upload complete and cleanup done.")
                
                # UX Improvement: Show menu again
                keyboard = [
                    [InlineKeyboardButton("📅 Meine Dienste (PDF)", callback_data='my_duties')],
                    [InlineKeyboardButton("🚑 Tagesplan (PDF)", callback_data='today_plan')],
                    [InlineKeyboardButton("📆 Anderes Datum", callback_data='custom_date')]
                ]
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="Was möchtest du als nächstes tun?", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                logger.error("PDF Export returned False.")
                await context.bot.send_message(chat_id=chat_id, text="❌ Fehler beim Erstellen der PDF.")

        except Exception as e:
            logger.exception(f"Exception in _process_duties_request: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Ein Fehler ist aufgetreten: {e}")

    def _fetch_duties_sync(self, filter_today: bool, custom_date: datetime = None):
        """Helper to run blocking API calls."""
        # Ensure login if needed
        creds = load_credentials()
        if not self.api.header_key:
            ok, msg = self.api.login(creds['username'], creds['password'])
            if not ok:
                raise Exception(f"Login fehlgeschlagen: {msg}")

        if custom_date:
             return self.api.load_daily_plan(custom_date)
        elif filter_today:
            return self.api.load_daily_plan(datetime.now())
        else:
            return self.api.load_future_duties()

    def run(self):
        """Starts the bot."""
        token = self.config['telegram_token']
        application = ApplicationBuilder().token(token).build()

        # Conversation Handler for Date Selection
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start),
                CommandHandler(['dienste', 'plan', 'dienst'], self.send_duties),
                CommandHandler(['tagesplan', 'heute'], self.send_duties),
                CallbackQueryHandler(self.button_handler, pattern='^(my_duties|today_plan|custom_date)$')
            ],
            states={
                WAITING_FOR_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.manual_date_input),
                    CallbackQueryHandler(self.date_button_handler, pattern='^(date_tomorrow|date_after_tomorrow)$')
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel), CommandHandler('start', self.start)],
            per_message=True
        )

        application.add_handler(conv_handler)
        
        console.print("[bold green]Bot läuft! Drücke Strg + C zum Beenden.[/bold green]")
        logger.info("Bot is polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
