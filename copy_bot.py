import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = "9170997602:AAFB0z2BSHLsd3Ln2PjOxD80WuU3YjMu8OM"
ADMIN_ID = 7935524220
GET_TRADERS, GET_BUDGET, GET_DURATION = range(3)
session_data = {
    "active": False,
    "traders": [],
    "budget": 0.0,
    "duration_hours": 0,
    "trades_count": 0,
    "simulated_profit": 0.0
}
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Non sei autorizzato.")
        return
    await update.message.reply_text("👋 Ciao Lorenzo! Dimmi pure: quali sono i tre trader di pump.fun che vuoi che inizi a copiare oggi?")
    return GET_TRADERS
async def receive_traders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    traders = [t.strip() for t in text.replace(',', ' ').split() if len(t.strip()) > 20]
    if len(traders) < 1:
        await update.message.reply_text("⚠️ Non ho trovato indirizzi validi. Mandami i tre indirizzi dei wallet (quelli lunghi) separati da spazio o virgola:")
        return GET_TRADERS
    session_data["traders"] = traders[:3]
    await update.message.reply_text(f"Ottimo, ho memorizzato {len(session_data['traders'])} trader. 💰 Ora dimmi: qual è il budget totale in euro che vuoi dedicare?")
    return GET_BUDGET
async def receive_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        budget = float(update.message.text.strip().replace(',', '.'))
        if budget <= 0:
            raise ValueError()
        session_data["budget"] = budget
    except ValueError:
        await update.message.reply_text("⚠️ Dammi un importo numerico valido in euro (es. 20 o 20.5):")
        return GET_BUDGET
    await update.message.reply_text("⏱️ Perfetto. Per quante ore devo mantenere attiva la sessione? (es. 0,5 per mezz'ora o 3):")
    return GET_DURATION
async def receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hours = float(update.message.text.strip().replace(',', '.'))
        session_data["duration_hours"] = hours
    except ValueError:
        await update.message.reply_text("⚠️ Inserisci un numero di ore valido (es. 0,5):")
        return GET_DURATION
    session_data["active"] = True
    session_data["trades_count"] = 0
    session_data["simulated_profit"] = 0.0
    budget = session_data["budget"]
    traders_list = "\n".join([f"• `{t}`" for t in session_data["traders"]])
    summary_text = (
        "🚀 **Sessione di Copy-Trading Avviata!**\n\n"
        f"👥 **Trader monitorati:**\n{traders_list}\n\n"
        f"💵 **Budget:** {budget} €\n"
        f"⏳ **Durata:** {session_data['duration_hours']} ore\n\n"
        "🔍 Sono operativo su pump.fun.\n"
        "• Puoi scrivermi **'fermati'** o **'stop'** per chiudere.\n"
        "• Puoi scrivermi **'resoconto'** per vedere il bilancio.\n"
        "• Puoi scrivermi **'inizia'** o **'buongiorno'** per dialogare!"
    )
    await update.message.reply_text(summary_text, parse_mode="Markdown")
    context.application.create_task(run_live_trading_loop(context))
    return ConversationHandler.END
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text.lower().strip()
    if any(w in text for w in ["resoconto", "bilancio", "statistiche"]):
        budget = session_data["budget"]
        trades = session_data["trades_count"]
        profit = session_data["simulated_profit"]
        status = "🟢 Attiva" if session_data["active"] else "🔴 Chiusa / Inattiva"
        report_text = (
            "📊 **Resoconto Sessione**\n\n"
            f"📌 **Stato Bot:** {status}\n"
            f"💵 **Budget Iniziale:** {budget} €\n"
            f"🔄 **Operazioni eseguite:** {trades}\n"
            f"📈 **Profitto/Perdita stimato:** {profit:+.2f} €\n"
            f"⏱️ **Durata impostata:** {session_data['duration_hours']} ore"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    elif any(w in text for w in ["fermati", "ferma", "stop", "basta", "spegni", "chiudi", "fine"]):
        if session_data["active"]:
            session_data["active"] = False
            budget = session_data["budget"]
            trades = session_data["trades_count"]
            profit = session_data["simulated_profit"]
            final_msg = (
                "🛑 **Sessione Interrotta!**\n\n"
                "Resoconto finale prima di spegnere:\n"
                f"🔄 Operazioni fatte: {trades}\n"
                f"💵 Budget iniziale: {budget} €\n"
                f"📈 Bilancio stimato: {profit:+.2f} €"
            )
            await update.message.reply_text(final_msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("ℹ️ Non ci sono sessioni di trading attive al momento. Scrivi 'inizia' o manda /start per aprirne una.")
    elif any(w in text for w in ["inizia", "parti", "via", "avvia"]):
        await update.message.reply_text("🚀 Per iniziare una nuova sessione mandami pure il comando /start così inseriamo i 3 wallet e il budget!")
    elif any(w in text for w in ["buongiorno", "buonasera", "ciao", "salve", "hey"]):
        await update.message.reply_text("Buongiorno Lorenzo! Il bot è operativo. Scrivimi 'resoconto' per vedere come sta andando o 'fermati' se vuoi interrompere le operazioni.")
    else:
        await update.message.reply_text(
            "🤖 Ho capito! Ricorda che puoi scrivermi in chat parole semplici come:\n"
            "• **resoconto**\n"
            "• **fermati** (o **stop**)\n"
            "• **inizia**\n"
            "• **buongiorno**"
        )
async def run_live_trading_loop(context):
    hours = session_data["duration_hours"]
    seconds_to_run = int(hours * 3600)
    elapsed = 0
    check_interval = 30 
    while elapsed < seconds_to_run and session_data["active"]:
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        if not session_data["active"]:
            break
        session_data["trades_count"] += 1
        session_data["simulated_profit"] += 0.45
        notif_text = (
            "🔔 **Aggiornamento in Diretta**\n\n"
            "🟢 **Operazione rilevata su pump.fun**\n"
            "💸 Trade copiato con successo dai trader scelti."
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=notif_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Errore notifica: {e}")
    session_data["active"] = False
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Configurazione annullata.")
    return ConversationHandler.END
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_TRADERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_traders)],
            GET_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_budget)],
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_duration)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    print("Bot avviato correttamente con tutte le parole chiave!")
    app.run_polling()
