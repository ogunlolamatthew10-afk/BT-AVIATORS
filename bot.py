import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "PASTE_YOUR_TOKEN_HERE"
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
    last_check_at: datetime | None = None


sessions: dict[int, SessionState] = {}


def get_state(chat_id: int) -> SessionState:
    if chat_id not in sessions:
        sessions[chat_id] = SessionState()
    return sessions[chat_id]


def money(value: float) -> str:
    return f"₦{value:,.0f}"


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


def build_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📈 GET STATUS", callback_data="status")],
            [InlineKeyboardButton(text="➕ Add Multiplier", callback_data="add")],
            [InlineKeyboardButton(text="💰 Bankroll", callback_data="bankroll")],
            [InlineKeyboardButton(text="🧹 Reset History", callback_data="reset")],
        ]
    )


def summarize(history: list[float]) -> str:
    if len(history) < 5:
        return "📊 Add at least 5 multipliers first."

    recent = history[-5:]
    avg = sum(recent) / len(recent)
    low_count = sum(1 for x in recent if x <= 1.5)
    high_count = sum(1 for x in recent if x >= 2.0)

    return (
        f"Last 5: {recent}\n"
        f"Average: {avg:.2f}\n"
        f"Low rounds (≤1.5): {low_count}\n"
        f"Higher rounds (≥2.0): {high_count}"
    )


def cooldown_text(state: SessionState) -> str:
    now = datetime.now()

    if state.last_check_at is None:
        next_time = now
    else:
        next_time = state.last_check_at + timedelta(minutes=COOLDOWN_MINUTES)

    return fmt_time(next_time)


@router.message(Command("start"))
async def start(msg: types.Message):
    state = get_state(msg.chat.id)
    text = (
        "🚀 Bot ready\n\n"
        f"Bankroll: {money(state.bankroll)}\n"
        f"Cooldown: {COOLDOWN_MINUTES} minutes\n\n"
        "Tap a button below."
    )
    await msg.answer(text, reply_markup=build_keyboard())


@router.callback_query(F.data == "add")
async def add_prompt(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    state.pending_add = True
    await c.answer()
    await c.message.answer("Send one multiplier now, like 1.45 or 2.30.")


@router.callback_query(F.data == "status")
async def status(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    now = datetime.now()

    if state.last_check_at is not None:
        next_allowed = state.last_check_at + timedelta(minutes=COOLDOWN_MINUTES)
        if now < next_allowed:
            wait_seconds = int((next_allowed - now).total_seconds())
            minutes = wait_seconds // 60
            seconds = wait_seconds % 60
            await c.answer("Cooldown active", show_alert=False)
            await c.message.answer(
                f"⏳ Please wait {minutes}m {seconds}s.\n"
                f"Next check time: {fmt_time(next_allowed)}"
            )
            return

    state.last_check_at = now
    await c.answer()

    text = (
        f"🕒 Time: {fmt_time(now)}\n"
        f"⏳ Next check allowed after: {fmt_time(now + timedelta(minutes=COOLDOWN_MINUTES))}\n\n"
        f"Bankroll: {money(state.bankroll)}\n"
        f"History count: {len(state.history)}\n\n"
        f"{summarize(state.history)}\n\n"
        "Use the cooldown to add fresh data calmly."
    )
    await c.message.answer(text, reply_markup=build_keyboard())


@router.callback_query(F.data == "bankroll")
async def bankroll(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    await c.answer()
    await c.message.answer(
        f"💰 Bankroll: {money(state.bankroll)}\n"
        f"Initial: {money(state.initial_bankroll)}\n"
        f"Stored multipliers: {len(state.history)}"
    )


@router.callback_query(F.data == "reset")
async def reset_history(c: types.CallbackQuery):
    state = get_state(c.message.chat.id)
    state.history.clear()
    state.last_check_at = None
    state.pending_add = False
    await c.answer("Reset done")
    await c.message.answer("🧹 History cleared.")


@router.message()
async def handle_text(msg: types.Message):
    state = get_state(msg.chat.id)

    if not state.pending_add:
        return

    text = (msg.text or "").strip().lower().replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)

    if not match:
        await msg.answer("Send a valid number like 1.45")
        return

    try:
        value = float(match.group())
        if value <= 0:
            raise ValueError("Multiplier must be positive")

        state.history.append(value)
        if len(state.history) > 200:
            state.history.pop(0)

        state.pending_add = False

        await msg.answer(
            f"✅ Added {value}x\n"
            f"Stored total: {len(state.history)}\n"
            f"Now tap GET STATUS when you want the next timed check."
        )
    except Exception:
        await msg.answer("Send a valid number like 1.45")


async def main():
    dp.include_router(router)
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
