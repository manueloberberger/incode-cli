import time
import sys
import logging
import requests
from datetime import datetime
from rich.prompt import Prompt
from src.config import load_credentials, update_credentials, console
from src.api import IncodeRequests

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

    def get_duties_message(self, filter_today=False):
        # Ensure login
        creds = load_credentials()
        if not self.api.header_key: # Check if logged in (simple check)
            ok, msg = self.api.login(creds['username'], creds['password'])
            if not ok: return f"Login Fehler: {msg}"

        if filter_today:
            return self.get_daily_plan_message(datetime.now())

        try:
            duties = self.api.load_future_duties()
            return self._format_duties(duties)
        except Exception as e:
            logger.exception("Fehler bei get_duties")
            return f"Fehler bei Abfrage: {str(e)}"

    def get_daily_plan_message(self, date):
        # Ensure login
        creds = load_credentials()
        if not self.api.header_key:
            ok, msg = self.api.login(creds['username'], creds['password'])
            if not ok: return f"Login Fehler: {msg}"

        try:
            plan = self.api.load_daily_plan(date)
            # Sort by begin time
            plan.sort(key=lambda x: x['begin'] if x['begin'] else datetime.max)
            
            if not plan:
                return f"📅 *Kein Tagesplan für den {date.strftime('%d.%m.%Y')} gefunden.*"
            return self._format_daily_plan(plan, date)
        except Exception as e:
            logger.exception("Fehler bei get_daily_plan")
            return f"Fehler bei Tagesplan: {str(e)}"

    def _format_duties(self, duties):
        if not duties: return "⚠️ Keine Dienste gefunden."
        msg = "🚑 *Deine Dienste:*

"
        for d in duties:
            try:
                # API returns ISO strings
                bd = datetime.strptime(d['begin'][:19], '%Y-%m-%dT%H:%M:%S')
                ed = datetime.strptime(d['end'][:19], '%Y-%m-%dT%H:%M:%S')
                
                date_str = bd.strftime('%d.%m.%Y')
                time_str = f"{bd.strftime('%H:%M')} - {ed.strftime('%H:%M')}"
                
                msg += f"📅 *{date_str} | {time_str}*
"
                msg += f"📍 {d['location']} | {d['vehicle']}
"
                if d['crew']: msg += f"👥 {', '.join(d['crew'])}
"
                msg += "
"
            except Exception as e:
                logger.error(f"Fehler beim Formatieren eines Dienstes: {e}")
                continue
        return msg

    def _format_daily_plan(self, plan, date):
        msg = f"📋 *Tagesplan {date.strftime('%d.%m.%Y')}*

"
        for d in plan:
            time_str = "??:?? - ??:??"
            if d['begin'] and d['end']:
                time_str = f"{d['begin'].strftime('%H:%M')} - {d['end'].strftime('%H:%M')}"
            
            msg += f"🕒 *{time_str}*
"
            msg += f"🚑 {d['vehicle'] if d['vehicle'] else 'Unbekanntes KFZ'}
"
            
            crew_list = []
            crew_dict = d.get('crew', {})
            # Crew is a dict in daily plan from api.py: {'FAHRER': 'Name', ...}
            if "FAHRER" in crew_dict: crew_list.append(f"👨‍✈️ {crew_dict['FAHRER']}")
            if "SANITAETER1" in crew_dict: crew_list.append(f"🩺 {crew_dict['SANITAETER1']}")
            if "SANITAETER2" in crew_dict: crew_list.append(f"🩺 {crew_dict['SANITAETER2']}")
            
            # Fallback if crew is a list (API logic varies slightly in some branches, but _parse_daily_plan_raw uses dict)
            
            if crew_list:
                msg += " | ".join(crew_list) + "
"
            msg += "
"
        return msg

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
                        reply = (
                            "✨ *Incode CLI Bot v1.0* ✨

"
                            "📌 *Befehle:*
"
                            "🚀 /start — Hilfe
"
                            "📅 /dienste — Deine Dienste
"
                            "📋 /tagesplan — Tagesplan HEUTE
"
                        )
                    elif any(x in text.lower() for x in ["/tagesplan", "/heute", "tagesplan"]):
                        self.telegram_request("sendChatAction", {"chat_id": chat_id, "action": "typing"})
                        reply = self.get_duties_message(filter_today=True)
                    elif any(x in text.lower() for x in ["/dienste", "plan", "dienst"]):
                        self.telegram_request("sendChatAction", {"chat_id": chat_id, "action": "typing"})
                        reply = self.get_duties_message()
                    else:
                        reply = "Unbekannter Befehl. /dienste oder /tagesplan"
                    
                    self.telegram_request("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"})
            
            except KeyboardInterrupt:
                logger.info("👋 Bot vom Benutzer beendet.")
                break
            except Exception as e:
                logger.exception("Fehler im Loop")
                time.sleep(5)
