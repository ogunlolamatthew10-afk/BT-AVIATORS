import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "8654750538:AAGlG30RTn6mgIo7Ss-34hBw_EcgrWcQeyc"
COOLDOWN_MINUTES = 3

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()


@dataclass
class SessionState:
    bankroll: float = 50000.0
    initial_bankroll: float = 50000.0
    history: list[float] = field(default_factory=list)
    pending_add: bool = False
    last_report_at: datetime | None = None


sessions: dict[int, SessionState] = {}


def get_state(chat_id: int) -> SessionState:
    if chat_id not in sessions:
        sessions[chat_id] = SessionState()
    return sessions[chat_id]


def money(value: float) -> str:
    return f"₦{value:,.0f}"


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


def keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 SHOW REPORT", callback_data="report")],
            [InlineKeyboardButton(text="➕ Add Multiplier", callback_data="add")],
            [InlineKeyboardButton(text="💰 Bankroll", callback_data="bankroll")],
            [InlineKeyboardButton(text="🧹 Reset History", callback_data="reset")],
        ]
    )


def clean_recent(history: list[float]) -> list[float]:
    recent = history[-5:]
    return [x for x in recent if x > 0]


def build_report(state: SessionState) -> str:
    if len(state.history) < 5:
        return (
            "📊 Not enough data yet.\n\n"
            "Add at least 5 multipliers first."
        )

    recent = clean_recent(state.history)
    if len(recent) < 3:
        return "⚠️ Too little clean data to summarize."

    avg = sum(recent) / len(recent)
    low_count = sum(1 for x in recent if x <= 1.5)
    mid_count = sum(1 for x in recent if 1.5 < x <= 2.5)
    high_count = sum(1 for x in recent if x > 2.5)

    if avg < 1.6:
        trend = "Low activity"
    elif avg <= 2.5:
        trend = "Mixed activity"
    else:
        trend = "High activity"

    return (
        f"📈 Report\n\n"
        f"Trend: {trend}\n"
        f"Last 5: {recent}\n"
        f"Average: {avg:.2f}\n"
        f"Low rounds (≤1.5): {low_count}\n"
        f"Mid rounds (1.5–2.5): {mid_count}\n"
        f"High rounds (>2.5): {high_count}\n\n"
        f"Use this only as a log, not as a prediction."
    )


@router.message(Command("start"))
async def start(msg: types.Message):
    state = get_state(msg.chat.id)
    text = (
        "✅ Session Tracker Ready\n\n"
        f"Bankroll: {money(state.bankroll)}\n"
        f"Cooldown: {COOLDOWN_MINUTES} minutes\n"
        f"Stored multipliers: {len(state.history)}\n\n"
        "Use the buttons below."
    )
    await msg.answer(text, reply_markup=keyboard())


@router.callback_query(F.data == "add")
async def add_prompt(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    state.pending_add = True
    await c.answer()
    await c.message.answer("Send one multiplier now, like 1.45 or 2.30.")


@router.callback_query(F.data == "report")
async def report(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    now = datetime.now()

    if state.last_report_at is not None:
        next_allowed = state.last_report_at + timedelta(minutes=COOLDOWN_MINUTES)
        if now < next_allowed:
            wait = next_allowed - now
            minutes = int(wait.total_seconds()) // 60
            seconds = int(wait.total_seconds()) % 60
            await c.answer()
            await c.message.answer(
                f"⏳ Cooldown active.\n"
                f"Wait {minutes}m {seconds}s.\n"
                f"Next report at {fmt_time(next_allowed)}."
            )
            return

    state.last_report_at = now
    await c.answer()

    text = (
        f"🕒 Time: {fmt_time(now)}\n"
        f"⏳ Next report after: {fmt_time(now + timedelta(minutes=COOLDOWN_MINUTES))}\n\n"
        f"Bankroll: {money(state.bankroll)}\n"
        f"History count: {len(state.history)}\n\n"
        f"{build_report(state)}"
    )
    await c.message.answer(text, reply_markup=keyboard())


@router.callback_query(F.data == "bankroll")
async def bankroll(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    profit = state.bankroll - state.initial_bankroll
    signed = f"+{money(profit)}" if profit >= 0 else f"-{money(abs(profit))}"
    await c.answer()
    await c.message.answer(
        f"💰 Bankroll: {money(state.bankroll)}\n"
        f"Initial: {money(state.initial_bankroll)}\n"
        f"Net change: {signed}\n"
        f"Stored multipliers: {len(state.history)}"
    )


@router.callback_query(F.data == "reset")
async def reset_history(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    state.history.clear()
    state.pending_add = False
    state.last_report_at = None
    await c.answer("Reset complete")
    await c.message.answer("🧹 History cleared.", reply_markup=keyboard())


@router.message()
async def handle_text(msg: types.Message):
    state = get_state(msg.chat.id)

    if not state.pending_add:
        return

    raw = (msg.text or "").strip().replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", raw)

    if not match:
        await msg.answer("Send a valid number like 1.45")
        return

    try:
        value = float(match.group())
        if value <= 0:
            raise ValueError("Invalid multiplier")

        state.history.append(value)
        if len(state.history) > 200:
            state.history.pop(0)

        state.pending_add = False

        await msg.answer(
            f"✅ Added {value}x\n"
            f"Stored total: {len(state.history)}\n"
            f"Tap SHOW REPORT when you want a summary."
        )
    except Exception:
        await msg.answer("Send a valid number like 1.45")


async def main():
    dp.include_router(router)
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
