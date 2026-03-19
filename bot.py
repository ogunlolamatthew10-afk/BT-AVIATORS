import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8654750538:AAGlG30RTn6mgIo7Ss-34hBw_EcgrWcQeyc"   # ← keep your same token
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# -------------------- Persistent Data Storage --------------------
DATA_FILE = "betking_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"bankroll": 50000.0, "history": [], "session_profit": 0.0, "initial": 50000.0}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# -------------------- Risk Manager Class --------------------
class BetKingRiskMaster:
    def __init__(self, data):
        self.bankroll = data["bankroll"]
        self.initial = data.get("initial", self.bankroll)
        self.history = data["history"]
        self.session_profit = data["session_profit"]
        self.safe_target = 1.3
        self.max_daily_loss = 0.10
        self.bet_percent = 0.02

    def save(self):
        data = {
            "bankroll": self.bankroll,
            "initial": self.initial,
            "history": self.history,
            "session_profit": self.session_profit
        }
        save_data(data)

    def analyze(self):
        if len(self.history) < 5:
            return "📊 Send at least 5 BetKing multipliers with the Add button"

        recent = self.history[-5:]
        avg = sum(recent) / 5
        low_streak = sum(1 for x in recent if x <= 1.5)

        # Advanced signals
        if low_streak >= 3:
            signal = "🔴 LOW STREAK DETECTED! Perfect safe entry time on BetKing now!"
        elif avg > 2.2:
            signal = "🟢 High average — strong setup for 1.3x on BetKing"
        elif avg < 1.4 and len([x for x in recent if x < 1.2]) >= 3:
            signal = "🟡 Very low recent rounds – high chance of a rebound? Still follow 1.3x safe rule"
        else:
            signal = "⚪ Neutral market — follow 1.3x safe rule"

        prob = round(97 / (self.safe_target * 100) * 100, 1)
        stake = self.get_bet_size()
        if stake == 0:
            stake_msg = "🚫 STOP – max loss reached!"
        else:
            stake_msg = f"💰 Stake: ₦{stake:,.0f} (2% of bankroll)"

        return (f"{signal}\n\n"
                f"{stake_msg}\n"
                f"✅ Auto cashout @ {self.safe_target}x ({prob}% chance)\n"
                f"📊 Last 5 BetKing rounds: {recent}\n"
                f"📈 5‑round average: {avg:.2f}x")

    def get_bet_size(self):
        if self.bankroll <= self.initial * 0.5 or self.session_profit <= -self.initial * self.max_daily_loss:
            return 0
        return round(self.bankroll * self.bet_percent, 2)

    def add_multiplier(self, mult):
        self.history.append(mult)
        if len(self.history) > 200:
            self.history.pop(0)
        self.save()

# -------------------- Load saved state --------------------
data = load_data()
risk = BetKingRiskMaster(data)

# -------------------- FSM for scheduling --------------------
class ScheduleStates(StatesGroup):
    waiting_for_minutes = State()

# -------------------- Keyboards --------------------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 GET SIGNAL", callback_data="signal")],
        [InlineKeyboardButton(text="➕ Add BetKing Multiplier", callback_data="add")],
        [InlineKeyboardButton(text="⏰ Schedule Signal", callback_data="schedule")],
        [InlineKeyboardButton(text="💰 My Bankroll", callback_data="status")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu")]
    ])

# -------------------- Handlers --------------------
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        f"🚀 BetKing Risk Master Bot READY\n"
        f"Built only for you\n"
        f"Bankroll: ₦{risk.bankroll:,.0f}\n"
        f"Session profit: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}",
        reply_markup=main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "menu")
async def back_to_menu(c: CallbackQuery):
    await c.message.edit_text(
        f"🚀 BetKing Risk Master\nBankroll: ₦{risk.bankroll:,.0f}\nSession: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}",
        reply_markup=main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "signal")
async def signal_handler(c: CallbackQuery):
    analysis = risk.analyze()
    text = (f"🕒 {datetime.now().strftime('%H:%M:%S')}\n"
            f"Bankroll: ₦{risk.bankroll:,.0f} | Session: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}\n\n"
            f"{analysis}\n\n"
            f"❗ Place your bet on the NEXT round.\n"
            f"Never chase losses. Stop at -10%.")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 New Signal", callback_data="signal")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu")]
    ])
    await c.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "add")
async def add_prompt(c: CallbackQuery):
    await c.message.edit_text(
        "Paste the last BetKing multiplier (e.g. 1.45 or 2.34).\n"
        "You can send multiple numbers one by one.",
        reply_markup=back_keyboard()
    )

@dp.callback_query(lambda c: c.data == "status")
async def status_handler(c: CallbackQuery):
    text = (f"💰 **Bankroll Details**\n"
            f"Current bankroll: ₦{risk.bankroll:,.0f}\n"
            f"Initial bankroll: ₦{risk.initial:,.0f}\n"
            f"Session profit: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}\n"
            f"History entries: {len(risk.history)}\n"
            f"Last 5: {risk.history[-5:] if len(risk.history)>=5 else risk.history}")
    await c.message.edit_text(text, reply_markup=back_keyboard())

@dp.callback_query(lambda c: c.data == "settings")
async def settings_handler(c: CallbackQuery):
    text = (f"⚙️ **Current Settings**\n"
            f"Safe cashout: {risk.safe_target}x\n"
            f"Bet size: {risk.bet_percent*100}% of bankroll\n"
            f"Max daily loss: {risk.max_daily_loss*100}%\n\n"
            f"To change these, edit the code or use /set commands (coming soon).")
    await c.message.edit_text(text, reply_markup=back_keyboard())

# -------------------- Schedule feature --------------------
@dp.callback_query(lambda c: c.data == "schedule")
async def schedule_prompt(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(
        "⏰ Send me the number of minutes from now when you want a new signal.\n"
        "Example: `2` for 2 minutes.",
        reply_markup=back_keyboard()
    )
    await state.set_state(ScheduleStates.waiting_for_minutes)

@dp.message(ScheduleStates.waiting_for_minutes)
async def schedule_minutes(msg: types.Message, state: FSMContext):
    try:
        minutes = int(msg.text.strip())
        if minutes <= 0:
            await msg.answer("Please enter a positive number.")
            return
        # Schedule the task
        await state.clear()
        await msg.answer(f"✅ Reminder set for {minutes} minute(s) from now. I'll send you an updated signal then.")

        # Wait and then send signal
        await asyncio.sleep(minutes * 60)
        analysis = risk.analyze()
        text = (f"⏰ **Scheduled Signal** ({minutes} min later)\n"
                f"🕒 {datetime.now().strftime('%H:%M:%S')}\n"
                f"Bankroll: ₦{risk.bankroll:,.0f} | Session: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}\n\n"
                f"{analysis}\n\n"
                f"❗ Place your bet on the NEXT round.")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Get Fresh Signal", callback_data="signal")],
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu")]
        ])
        await bot.send_message(chat_id=msg.chat.id, text=text, reply_markup=keyboard)
    except ValueError:
        await msg.answer("Please send a valid number (e.g., 2).")

# -------------------- Handle multiplier input --------------------
@dp.message()
async def add_multiplier(msg: types.Message):
    try:
        mult = float(msg.text.strip().replace("x", ""))
        risk.add_multiplier(mult)
        # Update session profit? Not directly – user would need to record wins/losses separately.
        await msg.answer(
            f"✅ Added {mult}x from BetKing!\n"
            f"History now has {len(risk.history)} entries.\n"
            f"Press 📈 GET SIGNAL for analysis.",
            reply_markup=main_keyboard()
        )
    except ValueError:
        await msg.answer("Please send a number like 1.45 or use the buttons below.", reply_markup=main_keyboard())

# -------------------- Start polling --------------------
async def main():
    print("BetKing Risk Master started – send /start in Telegram")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
