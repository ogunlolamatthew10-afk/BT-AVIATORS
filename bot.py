import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8654750538:AAGlG30RTn6mgIo7Ss-34hBw_EcgrWcQeyc"   # ← Keep your same token
bot = Bot(token=TOKEN)
dp = Dispatcher()

class BetKingRiskMaster:
    def __init__(self):
        self.bankroll = 50000.0          # Change to your real BetKing bankroll
        self.initial = self.bankroll
        self.history = []
        self.session_profit = 0.0
        self.safe_target = 1.3
        self.max_daily_loss = 0.10
        self.bet_percent = 0.02

    def analyze(self):
        if len(self.history) < 5:
            return "📊 Send at least 5 BetKing multipliers with the Add button"
        
        recent = self.history[-5:]
        low_streak = sum(1 for x in recent if x <= 1.5)
        
        if low_streak >= 3:
            signal = "🔴 LOW STREAK DETECTED! Perfect safe entry time on BetKing now!"
        elif sum(recent) / 5 > 2.2:
            signal = "🟢 High average — strong setup for 1.3x on BetKing"
        else:
            signal = "🟡 Neutral market — follow 1.3x safe rule"
        
        prob = round(97 / (self.safe_target * 100) * 100, 1)
        return f"{signal}\n\n💰 Stake: 2% of bankroll\n✅ Auto cashout @ {self.safe_target}x ({prob}% chance)\nLast 5 BetKing rounds: {recent}"

    def get_bet_size(self):
        if self.bankroll <= self.initial * 0.5 or self.session_profit <= -self.initial * self.max_daily_loss:
            return 0
        return round(self.bankroll * self.bet_percent, 2)

risk = BetKingRiskMaster()

@dp.message(Command("start"))
async def start(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 GET SIGNAL", callback_data="signal")],
        [InlineKeyboardButton(text="➕ Add BetKing Multiplier", callback_data="add")],
        [InlineKeyboardButton(text="💰 My Bankroll", callback_data="status")]
    ])
    await msg.answer(f"🚀 BetKing Risk Master Bot READY\nBuilt only for you\nBankroll: ₦{risk.bankroll:,.0f}", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "signal")
async def signal(c):
    text = f"🕒 {datetime.now().strftime('%H:%M:%S')} | Bankroll ₦{risk.bankroll:,.0f} | Session {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}\n\n{risk.analyze()}\n\nNever chase losses. Stop at -10%."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 New Signal", callback_data="signal")]])
    await c.message.edit_text(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "add")
async def add_prompt(c):
    await c.message.answer("Paste the last BetKing multiplier (e.g. 1.45 or 2.34)")

@dp.callback_query(lambda c: c.data == "status")
async def status(c):
    await c.message.answer(f"Bankroll: ₦{risk.bankroll:,.0f}\nSession: {'+' if risk.session_profit >= 0 else ''}₦{risk.session_profit:,.0f}\nHistory length: {len(risk.history)}")

@dp.message()
async def add_multiplier(msg: types.Message):
    try:
        mult = float(msg.text.strip().replace("x", ""))
        risk.history.append(mult)
        if len(risk.history) > 200:
            risk.history.pop(0)
        await msg.answer(f"✅ Added {mult}x from BetKing!\nNow press 📈 GET SIGNAL")
    except:
        await msg.answer("Send a number like 1.45")

async def main():
    print("Bot started - send /start in Telegram")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
