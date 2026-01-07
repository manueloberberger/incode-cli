import os
import sys
import logging
import asyncio
from datetime import datetime
from rich.prompt import Prompt
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
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
        await update.message.reply_text(
            f"✨ *Incode CLI Bot v{VERSION}* ✨\n\n📌 *Befehle:*\n🚀 /start — Hilfe\n📅 /dienste — Deine Dienste (PDF)\n📋 /tagesplan — Tagesplan HEUTE (PDF)",
            parse_mode='Markdown'
        )

    async def unauthorized(self, update: Update):
        uid = update.effective_user.id
        logger.warning(f"Unauthorized access attempt from {uid}")
        # Silent drop or minimal info
        # await update.message.reply_text("⛔ Zugriff verweigert.") 

    async def send_duties(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        if str(user_id) != str(self.config["allowed_user_id"]):
            await self.unauthorized(update)
            return

        await context.bot.send_chat_action(chat_id=chat_id, action='upload_document')
        
        # Determine request type
        cmd = update.message.text.lower()
        filter_today = "/tagesplan" in cmd or "/heute" in cmd

        try:
            # Run sync API calls in a thread to not block the async loop
            duties = await asyncio.to_thread(self._fetch_duties_sync, filter_today)

            if not duties:
                await update.message.reply_text("⚠️ Keine Dienste gefunden.")
                return

            if filter_today:
                date = datetime.now()
                title = f"Tagesplan {date.strftime('%d.%m.%Y')}"
                filename = f"Tagesplan_{date.strftime('%Y-%m-%d')}_{date.strftime('%H-%M')}.pdf"
            else:
                title = "Meine Dienste"
                filename = f"Mein_Dienstplan_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf"

            # Generate PDF (Sync operation, run in thread)
            success = await asyncio.to_thread(export_to_pdf, duties, filename, title)

            if success:
                await update.message.reply_document(document=open(filename, 'rb'), caption=f"📄 {title}")
                os.remove(filename)
            else:
                await update.message.reply_text("❌ Fehler beim Erstellen der PDF.")

        except Exception as e:
            logger.exception("Error in duties handler")
            await update.message.reply_text(f"❌ Ein Fehler ist aufgetreten: {e}")

    def _fetch_duties_sync(self, filter_today: bool):
        """Helper to run blocking API calls."""
        # Ensure login if needed
        creds = load_credentials()
        if not self.api.header_key:
            ok, msg = self.api.login(creds['username'], creds['password'])
            if not ok:
                raise Exception(f"Login fehlgeschlagen: {msg}")

        if filter_today:
            duties = self.api.load_daily_plan(datetime.now())
            # Convert datetime objects to string for PDF generator or keep objects?
            # api.load_daily_plan returns dicts with datetime objects (rehydrated by cache or fixed_datetime).
            # api.load_future_duties returns strings (from cache) or strings (from parser).
            # Wait, my api.py changes made load_future_duties return strings because of cache.
            # But the PDF generator expects strings usually or needs adaptation.
            # Let's check pdf.py if needed. Assuming it handles what api returns.
            return duties
        else:
            return self.api.load_future_duties()

    def run(self):
        """Starts the bot."""
        token = self.config['telegram_token']
        application = ApplicationBuilder().token(token).build()

        start_handler = CommandHandler('start', self.start)
        duties_handler = CommandHandler(['dienste', 'plan', 'dienst'], self.send_duties)
        today_handler = CommandHandler(['tagesplan', 'heute'], self.send_duties)

        application.add_handler(start_handler)
        application.add_handler(duties_handler)
        application.add_handler(today_handler)
        
        # Filter for all other messages to check auth strictly?
        # The handlers above already check auth.

        console.print("[bold green]Bot läuft! Drücke Strg + C zum Beenden.[/bold green]")
        application.run_polling()
