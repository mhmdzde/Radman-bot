"""
finance_bot.py — هندلرهای مالی برای بات تلگرام
این فایل رو import کن و handler هاش رو به Application اضافه کن.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler, MessageHandler, ConversationHandler,
    CommandHandler, filters, ContextTypes
)
from database import (
    add_transaction, get_balance, get_transactions,
    get_dept_budget, get_departments, delete_transaction,
    get_notify_ids
)
import logging
_logger = logging.getLogger(__name__)

async def _notify_all(ctx, text: str, exclude_id: int = None):
    for tg_id in get_notify_ids():
        if exclude_id and tg_id == exclude_id:
            continue
        try:
            await ctx.bot.send_message(chat_id=tg_id, text=text, parse_mode="Markdown")
        except Exception as e:
            _logger.warning(f"fin notify failed for {tg_id}: {e}")

# ── مراحل مکالمه ──
FIN_TYPE, FIN_AMOUNT, FIN_DESC, FIN_DEPT, FIN_DATE = range(10, 15)
FIN_FILTER_TYPE, FIN_FILTER_FROM, FIN_FILTER_TO    = range(15, 18)


# ════════════════════════════════════════════════════════════════
# کمکی
# ════════════════════════════════════════════════════════════════
async def _reply(update: Update, text: str, kb_rows: list, parse_mode="Markdown"):
    markup = InlineKeyboardMarkup(kb_rows)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=parse_mode)
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)


def _back_btn():
    return [InlineKeyboardButton("◀ برگشت به منوی مالی", callback_data="fin:menu")]


# ════════════════════════════════════════════════════════════════
# منوی مالی
# ════════════════════════════════════════════════════════════════
async def finance_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    kb = [
        [InlineKeyboardButton("💰 موجودی کل",        callback_data="fin:balance")],
        [InlineKeyboardButton("📊 داشبورد بخش‌ها",   callback_data="fin:deptdash")],
        [
            InlineKeyboardButton("➕ ثبت درآمد",     callback_data="fin:add:income"),
            InlineKeyboardButton("➖ ثبت هزینه",     callback_data="fin:add:expense"),
        ],
        [
            InlineKeyboardButton("📋 لیست درآمدها",  callback_data="fin:list:income"),
            InlineKeyboardButton("📋 لیست هزینه‌ها", callback_data="fin:list:expense"),
        ],
        [InlineKeyboardButton("🏠 منوی اصلی",        callback_data="menu:main")],
    ]
    await _reply(update, "💼 *بخش مالی*\n\nیک گزینه انتخاب کنید:", kb)


# ════════════════════════════════════════════════════════════════
# موجودی کل
# ════════════════════════════════════════════════════════════════
async def show_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    income, expense, balance = get_balance()
    sign  = "+" if balance >= 0 else ""
    emoji = "🟢" if balance >= 0 else "🔴"
    text = (
        "💰 *موجودی کل*\n\n"
        f"📥 کل درآمد:   `{income:,.0f}` تومان\n"
        f"📤 کل هزینه:   `{expense:,.0f}` تومان\n"
        f"──────────────────\n"
        f"{emoji} موجودی:   `{sign}{balance:,.0f}` تومان"
    )
    await _reply(update, text, [_back_btn()])


# ════════════════════════════════════════════════════════════════
# داشبورد بخش‌ها
# ════════════════════════════════════════════════════════════════
async def show_dept_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    depts = get_dept_budget()
    total_spent = sum(d["spent"] for d in depts)

    lines = ["📊 *داشبورد هزینه بخش‌ها*\n"]
    for d in depts:
        pct = round(d["spent"] / total_spent * 100) if total_spent else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(
            f"*{d['name']}*\n"
            f"  📤 هزینه: `{d['spent']:,.0f}` تومان\n"
            f"  `{bar}` {pct}٪\n"
        )

    lines.append(f"──────────────────\n💸 جمع هزینه‌ها: `{total_spent:,.0f}` تومان")

    kb = [
        [InlineKeyboardButton(f"📋 هزینه‌های {d['name']}", callback_data=f"fin:list:expense:dept:{d['id']}")]
        for d in depts
    ]
    kb.append(_back_btn())
    await _reply(update, "\n".join(lines), kb)


# ════════════════════════════════════════════════════════════════
# لیست تراکنش‌ها
# ════════════════════════════════════════════════════════════════
async def show_tx_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                       type_=None, dept_id=None, date_from=None, date_to=None):
    txs = get_transactions(type_=type_, dept_id=dept_id, date_from=date_from, date_to=date_to)
    type_label = "درآمدها" if type_ == "income" else "هزینه‌ها" if type_ == "expense" else "تراکنش‌ها"
    emoji_map  = {"income": "📥", "expense": "📤"}

    if not txs:
        await _reply(update, f"هیچ {type_label}ی یافت نشد.", [_back_btn()])
        return

    total = sum(t["amount"] for t in txs)
    lines = [f"📋 *{type_label}* — {len(txs)} مورد\n"]
    for t in txs:
        em = emoji_map.get(t["type"], "💳")
        lines.append(f"{em} `{t['amount']:,.0f}` — {t['description']}\n    🏢 {t['dept_name']}  📅 {t['date']}")

    lines.append(f"\n──────────────────\nجمع: `{total:,.0f}` تومان")

    # دکمه فیلتر بازه زمانی
    filter_cb = f"fin:filter:{type_ or 'all'}"
    kb = [
        [InlineKeyboardButton("🗓 فیلتر بازه زمانی", callback_data=filter_cb)],
        _back_btn(),
    ]
    await _reply(update, "\n".join(lines), kb)


# ════════════════════════════════════════════════════════════════
# افزودن تراکنش — مکالمه چند مرحله‌ای
# ════════════════════════════════════════════════════════════════
async def add_tx_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # fin:add:income یا fin:add:expense
    tx_type = q.data.split(":")[-1]          # income / expense
    ctx.user_data["fin_type"] = tx_type
    label = "درآمد" if tx_type == "income" else "هزینه"
    await q.message.reply_text(
        f"➕ *ثبت {label} جدید*\n\nمبلغ را به تومان وارد کنید (فقط عدد):",
        parse_mode="Markdown"
    )
    return FIN_AMOUNT


async def add_tx_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip().replace(",", "").replace("،", "")
    if not raw.isdigit():
        await update.message.reply_text("❌ فقط عدد وارد کنید:")
        return FIN_AMOUNT
    ctx.user_data["fin_amount"] = float(raw)
    await update.message.reply_text("توضیح / علت را بنویسید:")
    return FIN_DESC


async def add_tx_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["fin_desc"] = update.message.text.strip()
    depts = get_departments()
    kb = [[InlineKeyboardButton(d["name"], callback_data=f"fd:{d['id']}")] for d in depts]
    kb.append([InlineKeyboardButton("بدون بخش (عمومی)", callback_data="fd:0")])
    await update.message.reply_text("بخش مرتبط را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb))
    return FIN_DEPT


async def add_tx_dept(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    val = int(q.data.split(":")[1])
    ctx.user_data["fin_dept"] = val if val != 0 else None
    await q.message.reply_text(
        "تاریخ را وارد کنید (مثلاً: 1404-03-15)\n"
        "یا /skip برای تاریخ امروز:"
    )
    return FIN_DATE


async def add_tx_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    date = None if update.message.text.strip() == "/skip" else update.message.text.strip()
    tx_type = ctx.user_data["fin_type"]
    add_transaction(
        type_=tx_type,
        amount=ctx.user_data["fin_amount"],
        description=ctx.user_data["fin_desc"],
        dept_id=ctx.user_data["fin_dept"],
        date=date,
    )
    label  = "درآمد" if tx_type == "income" else "هزینه"
    emoji  = "📥" if tx_type == "income" else "📤"
    amount = ctx.user_data['fin_amount']
    desc   = ctx.user_data['fin_desc']
    await update.message.reply_text(
        f"✅ {label} `{amount:,.0f}` تومان با موفقیت ثبت شد.",
        parse_mode="Markdown"
    )
    await _notify_all(ctx,
        f"{emoji} *{label} جدید ثبت شد*\n\n💰 مبلغ: `{amount:,.0f}` تومان\n📝 علت: {desc}",
        exclude_id=update.effective_user.id)
    ctx.user_data.clear()
    return ConversationHandler.END


async def fin_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# فیلتر بازه زمانی
# ════════════════════════════════════════════════════════════════
async def filter_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # fin:filter:income / fin:filter:expense / fin:filter:all
    parts = q.data.split(":")
    ctx.user_data["filter_type"] = parts[2] if parts[2] != "all" else None
    await q.message.reply_text("از تاریخ (مثلاً: 1404-01-01) یا /skip:")
    return FIN_FILTER_FROM


async def filter_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    ctx.user_data["filter_from"] = None if val == "/skip" else val
    await update.message.reply_text("تا تاریخ (مثلاً: 1404-06-31) یا /skip:")
    return FIN_FILTER_TO


async def filter_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    date_to = None if val == "/skip" else val
    # ساخت update مصنوعی برای show_tx_list
    await show_tx_list(
        update, ctx,
        type_=ctx.user_data.get("filter_type"),
        date_from=ctx.user_data.get("filter_from"),
        date_to=date_to,
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# button handler مالی — داخل button_handler اصلی صدا بزن
# ════════════════════════════════════════════════════════════════
async def finance_button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    True برمی‌گردونه اگه callback رو handle کرده باشه.
    داخل button_handler اصلی:
        if await finance_button_handler(update, ctx): return
    """
    data = update.callback_query.data

    if data == "fin:menu":
        await finance_menu(update, ctx); return True
    if data == "fin:balance":
        await show_balance(update, ctx); return True
    if data == "fin:deptdash":
        await show_dept_dashboard(update, ctx); return True
    if data == "fin:list:income":
        await show_tx_list(update, ctx, type_="income"); return True
    if data == "fin:list:expense":
        await show_tx_list(update, ctx, type_="expense"); return True
    if data.startswith("fin:list:expense:dept:"):
        dept_id = int(data.split(":")[-1])
        await show_tx_list(update, ctx, type_="expense", dept_id=dept_id); return True

    return False


# ════════════════════════════════════════════════════════════════
# conversation handlers — به main اضافه کن
# ════════════════════════════════════════════════════════════════
def get_finance_conversations():
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_tx_start, pattern="^fin:add:(income|expense)$")],
        states={
            FIN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tx_amount)],
            FIN_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tx_desc)],
            FIN_DEPT:   [CallbackQueryHandler(add_tx_dept, pattern="^fd:")],
            FIN_DATE:   [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_tx_date),
                CommandHandler("skip", add_tx_date),
            ],
        },
        fallbacks=[CommandHandler("cancel", fin_cancel)],
    )
    filter_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(filter_start, pattern="^fin:filter:")],
        states={
            FIN_FILTER_FROM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_from),
                CommandHandler("skip", filter_from),
            ],
            FIN_FILTER_TO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_to),
                CommandHandler("skip", filter_to),
            ],
        },
        fallbacks=[CommandHandler("cancel", fin_cancel)],
    )
    return [add_conv, filter_conv]
