import time
import os
import sys
import logging
import requests
from datetime import datetime
from rich.prompt import Prompt
from src.config import load_credentials, update_credentials, console
from src.api import IncodeRequests
from src.pdf import export_to_pdf

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IncodeBot:
    def __init__(self, api: IncodeRequests):
        self.api = api
        self.offset = 0
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

    def telegram_request(self, method, params=None):
        url = f"https://api.telegram.org/bot{self.config['telegram_token']}/{method}"
        try:
            resp = requests.post(url, json=params, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Telegram Request Error ({method}): {e}")
            return {}

    def send_document(self, chat_id, file_path, caption=None):
        url = f"https://api.telegram.org/bot{self.config['telegram_token']}/sendDocument"
        data = {'chat_id': chat_id}
        if caption: data['caption'] = caption
        try:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                requests.post(url, data=data, files=files, timeout=30)
            return True
        except Exception as e:
            logger.error(f"Telegram Send Document Error: {e}")
            return False

    def handle_duties_request(self, chat_id, filter_today=False):
        # Ensure login
        creds = load_credentials()
        if not self.api.header_key:
            ok, msg = self.api.login(creds['username'], creds['password'])
            if not ok: 
                self.telegram_request("sendMessage", {"chat_id": chat_id, "text": f"Login Fehler: {msg}"})
                return

        try:
            if filter_today:
                date = datetime.now()
                duties = self.api.load_daily_plan(date)
                # Sort by begin time
                duties.sort(key=lambda x: x['begin'] if x['begin'] else datetime.max)
                title = f"Tagesplan {date.strftime('%d.%m.%Y')}"
                filename = f"tagesplan_{date.strftime('%Y%m%d')}.pdf"
            else:
                duties = self.api.load_future_duties()
                title = "Meine Dienste"
                filename = f"dienste_{datetime.now().strftime('%Y%m%d')}.pdf"

            if not duties:
                self.telegram_request("sendMessage", {"chat_id": chat_id, "text": "⚠️ Keine Dienste gefunden."})
                return

            # Generate PDF
            if export_to_pdf(duties, filename, title_text=title):
                self.send_document(chat_id, filename, caption=f"📄 {title}")
                # Clean up
                if os.path.exists(filename): os.remove(filename)
            else:
                self.telegram_request("sendMessage", {"chat_id": chat_id, "text": "Fehler beim Erstellen der PDF."})

        except Exception as e:
            logger.exception("Fehler bei Abfrage")
            self.telegram_request("sendMessage", {"chat_id": chat_id, "text": f"Fehler: {str(e)}"})

    def run(self):
        logger.info("🤖 Bot gestartet! Warte auf Nachrichten...")
        console.print("[bold green]Bot läuft! Drücke Strg + C zum Beenden.[/bold green]")
        while True:
            try:
                updates = self.telegram_request("getUpdates", {"offset": self.offset, "timeout": 5})
                for update in updates.get("result", []):
                    self.offset = update["update_id"] + 1
                    if "message" not in update: continue
                    msg = update["message"]
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    if str(chat_id) != str(self.config["allowed_user_id"]):
                        logger.warning(f"🔒 Zugriff verweigert für ID: {chat_id}")
                        continue
                    logger.info(f"📩 Nachricht von {chat_id}: {text}")
                    
                    if text.startswith("/start"):
                        reply = """✨ *Incode CLI Bot v1.0* ✨\n\n📌 *Befehle:*\n🚀 /start — Hilfe\n📅 /dienste — Deine Dienste (PDF)\n📋 /tagesplan — Tagesplan HEUTE (PDF)\n"""
                        self.telegram_request("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"})
                    elif any(x in text.lower() for x in ["/tagesplan", "/heute", "tagesplan"]):
                        self.telegram_request("sendChatAction", {"chat_id": chat_id, "action": "upload_document"})
                        self.handle_duties_request(chat_id, filter_today=True)
                    elif any(x in text.lower() for x in ["/dienste", "plan", "dienst"]):
                        self.telegram_request("sendChatAction", {"chat_id": chat_id, "action": "upload_document"})
                        self.handle_duties_request(chat_id, filter_today=False)
                    else:
                        reply = "Unbekannter Befehl. /dienste oder /tagesplan"
                        self.telegram_request("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"})
            except KeyboardInterrupt:
                logger.info("👋 Bot vom Benutzer beendet.")
                break
            except Exception as e:
                logger.exception("Fehler im Loop")
                time.sleep(5)