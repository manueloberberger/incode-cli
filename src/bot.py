import os
import sys
import logging
import asyncio
import re
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, cast
from dataclasses import asdict



from rich.align import Align
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from telegram.error import Conflict
from telegram.warnings import PTBUserWarning

# Suppress specific PTB warning about CallbackQueryHandler tracking
warnings.filterwarnings("ignore", category=PTBUserWarning, message="If 'per_message=False', 'CallbackQueryHandler' will not be tracked")

from src.config import load_credentials, update_credentials, console, VERSION
from src.api import IncodeRequests
from src.db import db
from src.utils import centered_input, get_key, KEY_ESC
from src.pdf import export_to_pdf
from src.exceptions import LoginError, ApiError

# Logging Configuration
logger = logging.getLogger(__name__)

class ConflictFilter(logging.Filter):
    """
    Logging filter to catch and handle Telegram conflict errors.
    
    Detects 'Conflict' errors (when another bot instance logs in) and 
    triggers a callback to shut down gracefully.
    """
    def __init__(self, on_conflict_callback: Optional[Callable[[], None]] = None):
        super().__init__()
        self.on_conflict = on_conflict_callback

    def filter(self, record: logging.LogRecord) -> bool:
        # Check tracebacks for Conflict
        is_conflict = False
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type and "Conflict" in str(exc_type):
                is_conflict = True
        
        msg = str(record.getMessage())
        if "Conflict" in msg or "Exception happened while polling for updates" in msg:
             is_conflict = True

        if is_conflict:
            if self.on_conflict:
                try:
                    self.on_conflict()
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"Conflict callback error: {e}")
            return False
            
        return True

# States for ConversationHandler
WAITING_FOR_DATE = 1

class IncodeBot:
    """
    Telegram Bot implementation for Incode CLI.
    
    Handles the interactive chat flow, command processing, and PDF delivery.
    Uses 'python-telegram-bot' library.
    """
    def __init__(self, api: IncodeRequests):
        self.api = api
        self.config = load_credentials()
        self.user_config = self._get_active_user_config()
        self.ensure_config()

    def _get_active_user_config(self) -> Dict[str, Any]:
        """Helper to get current user config."""
        target = self.api.username or self.config.get('last_active')
        for u in self.config.get('users', []):
            if u['username'] == target:
                return cast(Dict[str, Any], u)
        return {}

    def ensure_config(self) -> None:
        """Ensures Telegram config exists for current user."""
        if not self.user_config.get("telegram_token") or not self.user_config.get("allowed_user_id"):
            console.print(Align.center("[bold yellow]Telegram Konfiguration fehlt.[/bold yellow]"))
            token = centered_input("Telegram Bot Token: ")
            if not token: 
                 console.print(Align.center("[yellow]Abbruch.[/yellow]"))
                 return
            
            try:
                uid_str = centered_input("Deine Telegram User ID (Zahlen): ")
                if not uid_str: 
                    console.print(Align.center("[yellow]Abbruch.[/yellow]"))
                    return
                user_id = int(uid_str)
            except ValueError:
                console.print(Align.center("[red]User ID muss eine Zahl sein.[/red]"))
                sys.exit(1)
            
            update_credentials({"telegram_token": token, "allowed_user_id": user_id}, username=self.api.username)
            self.config = load_credentials()
            self.user_config = self._get_active_user_config()
            console.print(Align.center("[green]Telegram Konfiguration gespeichert.[/green]"))

    def send_document(self, chat_id: int, file_path: str, caption: Optional[str] = None) -> bool:
        """
        Synchronous wrapper to send a document (for CLI usage).
        
        Used by the main application to send PDFs via the bot instance
        without needing to manage the async loop manually.
        """
        try:
            return asyncio.run(self._send_document_async(chat_id, file_path, caption))
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            return False

    async def _send_document_async(self, chat_id: int, file_path: str, caption: Optional[str]) -> bool:
        try:
            from telegram import Bot
            token = self.user_config.get('telegram_token')
            if not token: return False
            bot = Bot(token=token)
            async with bot:
                with open(file_path, 'rb') as f:
                    await bot.send_document(chat_id=chat_id, document=f, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Async send error: {e}")
            return False



    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /start command."""
        if not update.effective_user or not update.message: return ConversationHandler.END
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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the /help command - show available commands and usage."""
        if not update.message: return ConversationHandler.END
        help_text = (
            "📖 *Incode CLI Bot - Hilfe*\n\n"
            "*Verfügbare Befehle:*\n"
            "/start - Hauptmenü anzeigen\n"
            "/dienste - Deine Dienste als PDF\n"
            "/tagesplan - Heutigen Tagesplan als PDF\n"
            "/heute - Alias für /tagesplan\n"
            "/help - Diese Hilfe anzeigen\n"
            "/cancel - Aktuelle Aktion abbrechen\n\n"
            "*Buttons:*\n"
            "• 📅 Meine Dienste - Alle zukünftigen Dienste\n"
            "• 🚑 Tagesplan - Plan für heute\n"
            "• 📆 Anderes Datum - Datum eingeben\n\n"
            "*Datumseingabe:*\n"
            "Format: TT.MM. oder TT.MM.JJJJ\n"
            "Beispiele: 15.01. oder 15.01.2026"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return ConversationHandler.END

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Parses button clicks."""
        query = update.callback_query
        if not query or not query.from_user: return ConversationHandler.END
        user_id = query.from_user.id
        logger.info(f"Button clicked: {query.data} by user {user_id}")
        
        allowed_id = str(self.user_config.get("allowed_user_id", ""))
        if str(user_id) != allowed_id:
            logger.warning(f"Access denied for user {user_id} (Allowed: {allowed_id})")
            await query.answer("Kein Zugriff.", show_alert=True)
            return ConversationHandler.END

        await query.answer() 
        
        if query.data == 'custom_date':
            # Ask for date
            if query.message and isinstance(query.message, Message):
                await query.message.reply_text(
                    "📅 Bitte gib das Datum ein ... (Format: TT.MM. oder TT.MM.JJJJ).\n"
                    "Oder klicke hier:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Morgen", callback_data='date_tomorrow')],
                        [InlineKeyboardButton("Übermorgen", callback_data='date_after_tomorrow')]
                    ])
                )
            return WAITING_FOR_DATE

        filter_today = (query.data == 'today_plan')
        if query.message:
             await self._process_duties_request(query.message, context, filter_today, chat_id=user_id)
        return ConversationHandler.END

    async def date_button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle quick date selection buttons."""
        query = update.callback_query
        if not query or not query.from_user or not query.message: return ConversationHandler.END
        user_id = query.from_user.id
        await query.answer() 
        
        target_date = datetime.now()
        if query.data == 'date_tomorrow':
            target_date += timedelta(days=1)
        elif query.data == 'date_after_tomorrow':
            target_date += timedelta(days=2)
            
        await self._process_duties_request(query.message, context, True, chat_id=user_id, custom_date=target_date)
        return ConversationHandler.END

    async def manual_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle manual text input for date."""
        if not update.message or not update.message.text or not update.effective_user: return WAITING_FOR_DATE
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

    async def unauthorized(self, update: Update) -> None:
        if not update.effective_user: return
        uid = update.effective_user.id
        logger.warning(f"Unauthorized access attempt from {uid}")

    async def send_duties(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handler for text commands like /dienste"""
        if not update.effective_chat or not update.effective_user or not update.message or not update.message.text: return ConversationHandler.END
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logger.info(f"Text command received: {update.message.text} from {user_id}")
        
        allowed_id = str(self.user_config.get("allowed_user_id", ""))
        if str(user_id) != allowed_id:
            await self.unauthorized(update)
            return ConversationHandler.END

        cmd = update.message.text.lower()
        filter_today = "/tagesplan" in cmd or "/heute" in cmd
        
        await self._process_duties_request(update.message, context, filter_today, chat_id)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message: await update.message.reply_text("Vorgang abgebrochen.")
        return ConversationHandler.END

    async def _process_duties_request(self, message_obj: Any, context: ContextTypes.DEFAULT_TYPE, filter_today: bool, chat_id: int, custom_date: Optional[datetime] = None) -> None:
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

            try:
                if success:
                    logger.info(f"Uploading PDF {filename}...")
                    with open(filename, 'rb') as f:
                        await context.bot.send_document(chat_id=chat_id, document=f, caption=f"📄 {title}")
                    
                    logger.info("Upload complete.")
                    
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
            finally:
                # Always clean up the PDF file
                if os.path.exists(filename):
                    os.remove(filename)
                    logger.debug(f"Cleaned up PDF file: {filename}")

        except Exception as e:
            logger.exception(f"Exception in _process_duties_request: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Ein Fehler ist aufgetreten: {e}")

    def _fetch_duties_sync(self, filter_today: bool, custom_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Helper to run blocking API calls."""
        # Ensure login if needed
        if not self.api.header_key:
            # Reload config to be safe
            self.config = load_credentials()
            self.user_config = self._get_active_user_config()
            
            if not self.user_config.get('username'):
                 raise LoginError("Keine gültigen Zugangsdaten gefunden.")

            try:
                password = self.user_config.get('password')
                if not password:
                    raise LoginError("Kein Passwort in der Konfiguration gefunden.")
                self.api.login(self.user_config['username'], password)
            except LoginError:
                raise
            except Exception as e:
                raise LoginError(f"Login fehlgeschlagen: {e}") from e

        if custom_date:
             return self.api.load_daily_plan(custom_date)
        elif filter_today:
            return self.api.load_daily_plan(datetime.now())
        else:
            duties = self.api.load_future_duties()
            return [asdict(d) for d in duties]

    def run(self, debug: bool = False) -> None:
        """Starts the bot."""
        token = self.user_config.get('telegram_token')
        if not token:
            console.print("[red]Kein Bot Token gefunden![/red]")
            return
        
        if debug:
            # Configure logging to use Rich for better integration when debugging
            from rich.logging import RichHandler
            logging.basicConfig(
                level=logging.INFO,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(console=console, show_path=False)]
            )
            logger.info("Debug-Modus aktiviert. Zeige technische Meldungen ...")
        else:
            # Silence technical logs to keep UI clean
            logging.getLogger("telegram").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
            # Filter out Conflict errors from ALL telegram loggers
            # Trigger shutdown on conflict
            def shutdown_trigger() -> None:
                # We can't await here, so we set a flag
                self._stop_signal = True

            self._stop_signal = False
            conflict_filter = ConflictFilter(on_conflict_callback=shutdown_trigger)
            
            # Apply to known critical usage
            logging.getLogger("telegram").addFilter(conflict_filter)
            logging.getLogger("telegram.ext._updater").addFilter(conflict_filter)
            
            # Nuclear option: Iterate all known loggers to catch sub-modules
            for name in logging.root.manager.loggerDict:
                if name.startswith("telegram"):
                    logging.getLogger(name).addFilter(conflict_filter)
        
        application = ApplicationBuilder().token(token).build()

        # Error Handler for Conflicts
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            if isinstance(context.error, Conflict):
                console.print()
                console.print(Align.center("[bold red]⚠️  Verbindung getrennt![/bold red]"))
                console.print(Align.center("[yellow]Der Bot wurde auf einem anderen Gerät gestartet.[/yellow]"))
                console.print(Align.center("[dim]Polling gestoppt. Drücke ESC um zum Menü zurückzukehren.[/dim]"))
                # We can try to stop the updater to prevent further noise
                if context.application.updater and context.application.updater.running:
                    await context.application.updater.stop()
                if context.application.running:
                    await context.application.stop()
            else:
                logger.error(f"Update {update} caused error {context.error}")

        application.add_error_handler(error_handler)

        # Conversation Handler for Date Selection
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start),
                CommandHandler('help', self.help_command),
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
            per_user=True,
            per_chat=True,
            per_message=False
        )

        application.add_handler(conv_handler)
        
        async def main_loop() -> None:
            await application.initialize()
            await application.start()
            if application.updater:
                 # Reduce timeout to 2s to allow faster shutdown loops
                 await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, timeout=2, bootstrap_retries=0)
            
            console.print(Align.center("[dim]Bot ist aktiv. Drücke ESC um zurückzukehren.[/dim]"))

            # Periodic cache cleanup (every 15 minutes)
            last_cache_cleanup = time.time()
            CACHE_CLEANUP_INTERVAL = 900  # 15 minutes in seconds

            try:
                while True:
                    # Check if stopped by error handler (Conflict)
                    if not application.running:
                        break
                    
                    # Check our custom stop signal from the log filter
                    if getattr(self, '_stop_signal', False):
                        console.print(Align.center("\n[bold red]⚠️  Verbindung durch neue Session beendet.[/bold red]"))
                        console.print(Align.center("[yellow]Der Bot wurde auf einem anderen Gerät gestartet.[/yellow]"))
                        break

                    # Periodic cache cleanup to prevent unbounded growth
                    if time.time() - last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
                        deleted = db.clear_expired_cache()
                        if deleted > 0:
                            logger.debug(f"Cache cleanup: {deleted} expired entries removed")
                        last_cache_cleanup = time.time()
                        
                    await asyncio.sleep(0.1)
                    # Use to_thread to avoid blocking the async event loop
                    k = await asyncio.to_thread(get_key, timeout=0.05)
                    if k == KEY_ESC:
                        console.print(Align.center("\n[yellow]Beende Bot-Modus ...[/yellow]"))
                        break
            except KeyboardInterrupt:
                 console.print(Align.center("\n[yellow]Beende Bot-Modus (SIGINT) ...[/yellow]"))
            finally:
                if application.updater:
                    if application.updater.running:
                        await application.updater.stop()
                if application.running:
                    await application.stop()
                await application.shutdown()

        try:
            asyncio.run(main_loop())
        except KeyboardInterrupt:
            logger.debug("Bot stopped by keyboard interrupt")
        except Conflict:
            console.print(Align.center("\n[bold red]⚠️  Verbindung durch neue Session beendet.[/bold red]"))
            console.print(Align.center("[yellow]Der Bot wurde auf einem anderen Gerät gestartet.[/yellow]"))
        except Exception as e:
            logger.error(f"Unexpected bot error: {e}")
