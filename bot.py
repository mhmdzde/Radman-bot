import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from database import (
    init_db, get_tasks, get_task, get_members, get_phases,
    get_statuses, get_dashboard, update_task_status, add_task,
    update_task_notes, update_task_doc, delete_task,
    get_notify_ids, set_member_tg_id
)
from finance_bot import finance_menu, finance_button_handler, get_finance_conversations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "6819753947:AAHa366GI99NYAqsm6L271UqQlYdw9Y8y8Q")

# ════════════════════════════════════════════════════════════════
# نوتیفیکیشن
# ════════════════════════════════════════════════════════════════
async def notify_all(ctx: ContextTypes.DEFAULT_TYPE, text: str, exclude_id: int = None):
    """پیام رو به همه اعضایی که tg_id دارن می‌فرسته (غیر از فرستنده)."""
    for tg_id in get_notify_ids():
        if exclude_id and tg_id == exclude_id:
            continue
        try:
            await ctx.bot.send_message(chat_id=tg_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"notify failed for {tg_id}: {e}")


async def register_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """هر عضو با /register باید این دستور رو بزنه تا tg_id ش ثبت بشه."""
    tg_id = update.effective_user.id
    members = get_members()
    kb = [
        [InlineKeyboardButton(f"👤 {m['name']}", callback_data=f"reg:{m['id']}")]
        for m in members
    ]
    await update.message.reply_text(
        "اسمت رو انتخاب کن تا نوتیف‌ها برات فعال بشه:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def register_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    member_id = int(q.data.split(":")[1])
    tg_id     = q.from_user.id
    set_member_tg_id(member_id, tg_id)
    members   = get_members()
    name      = next((m["name"] for m in members if m["id"] == member_id), "")
    await q.message.reply_text(f"✅ {name} ثبت شد. از این به بعد نوتیف‌ها برات می‌آد.")

# ── مراحل مکالمه ──
ASK_TITLE, ASK_MEMBER, ASK_PHASE, ASK_STATUS, ASK_DEADLINE = range(5)
ASK_NOTES, ASK_DOC = range(5, 7)


def _status_label(status_id: int, statuses) -> str:
    for s in statuses:
        if s["id"] == status_id:
            return f"{s['emoji']} {s['name']}"
    return "⚪"


# ════════════════════════════════════════════════════════════════
# /start
# ════════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("داشبورد",            callback_data="menu:dashboard")],
        [InlineKeyboardButton("همه تسک‌ها",         callback_data="menu:tasks:all")],
        [
            InlineKeyboardButton("🔵 در جریان",     callback_data="menu:tasks:s:2"),
            InlineKeyboardButton("🔴 فوری",         callback_data="menu:tasks:s:5"),
        ],
        [
            InlineKeyboardButton("✅ انجام شده",    callback_data="menu:tasks:s:3"),
            InlineKeyboardButton("⏸ معلق",          callback_data="menu:tasks:s:4"),
        ],
        [InlineKeyboardButton("فیلتر بر اساس فاز", callback_data="menu:filter:phase")],
        [InlineKeyboardButton("فیلتر بر اساس فرد", callback_data="menu:filter:member")],
        [InlineKeyboardButton("➕ افزودن تسک",      callback_data="menu:add")],
        [InlineKeyboardButton("💼 بخش مالی",        callback_data="fin:menu")],
    ]
    await _send_or_edit(update, "🔋 *پروژه توسعه زیرساخت شارژ خودروی برقی*\n\nیک گزینه انتخاب کنید:", kb)

# ════════════════════════════════════════════════════════════════
# داشبورد
# ════════════════════════════════════════════════════════════════
async def show_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    s = get_dashboard()
    total    = s["total"] or 1
    done_cnt = s.get("انجام شده", 0)
    pct      = round(done_cnt / total * 100)
    filled   = round(pct / 10)
    bar      = "█" * filled + "░" * (10 - filled)

    lines = [
        "📊 *داشبورد پروژه*\n",
        f"پیشرفت کلی: `{bar}` *{pct}٪*",
        f"کل تسک‌ها: *{s['total']}*\n",
        f"✅ انجام شده: {s.get('انجام شده',0)}   🟡 باز: {s.get('باز',0)}",
        f"🔵 در جریان: {s.get('در جریان',0)}   ⏸ معلق: {s.get('معلق',0)}   🔴 فوری: {s.get('فوری',0)}\n",
        "─────────────────",
        "*وضعیت فازها:*",
    ]
    for p in s["phases"]:
        done_pct = round((p["done"] or 0) / (p["total"] or 1) * 100)
        lines.append(
            f"  *{p['name']}*  ✅{p['done']} 🟡{p['open']} 🔵{p['inprogress']} ⏸{p['pending']} 🔴{p['urgent']}"
            f"  ({done_pct}٪)"
        )
    lines += ["─────────────────", "*وضعیت اعضا:*"]
    for m in s["members"]:
        lines.append(
            f"  👤 *{m['name']}*\n"
            f"     ✅{m['done']} 🟡{m['open']} 🔵{m['inprogress']} ⏸{m['pending']} 🔴{m['urgent']}"
        )

    kb = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]]
    await _send_or_edit(update, "\n".join(lines), kb)


# ════════════════════════════════════════════════════════════════
# لیست تسک‌ها
# ════════════════════════════════════════════════════════════════
async def show_task_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                         member_id=None, phase_id=None, status_id=None, title="همه تسک‌ها"):
    tasks = get_tasks(member_id=member_id, phase_id=phase_id, status_id=status_id)
    if not tasks:
        kb = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]]
        await _send_or_edit(update, "هیچ تسکی یافت نشد.", kb)
        return

    kb = []
    for t in tasks:
        emoji = t["status_emoji"]
        role_short = t["role"][:6] if t["role"] != "—" else "تیم"
        title_short = t["title"][:24] + "…" if len(t["title"]) > 24 else t["title"]
        label = f"{emoji} {title_short}  [{role_short}]"
        kb.append([InlineKeyboardButton(label, callback_data=f"task:{t['id']}")])

    kb.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    await _send_or_edit(update, f"📋 *{title}* — {len(tasks)} تسک:", kb)


# ════════════════════════════════════════════════════════════════
# جزئیات تسک
# ════════════════════════════════════════════════════════════════
async def show_task_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE, task_id: int):
    t, team_members = get_task(task_id)
    if not t:
        await update.callback_query.answer("تسک یافت نشد!")
        return

    lines = [f"📌 *{t['title']}*\n",
             f"وضعیت: {t['status_emoji']} {t['status']}",
             f"فاز: {t['phase_name']}"]

    if team_members:
        names = "، ".join(f"{m['name']}" for m in team_members)
        lines.append(f"مسئولان: 👥 *تیم* ({names})")
    else:
        lines.append(f"مسئول: {t['member_name']} ({t['role']})")

    if t["deadline"]:  lines.append(f"سررسید: {t['deadline']}")
    if t["completed"]: lines.append(f"تاریخ تکمیل: {t['completed']}")
    if t["notes"]:     lines.append(f"\n📝 یادداشت:\n{t['notes']}")
    if t["doc_link"]:  lines.append(f"\n🔗 [مستندات]({t['doc_link']})")

    # دکمه‌های تغییر وضعیت از جدول statuses
    statuses = get_statuses()
    current_status_id = t["status_id"]
    status_btns = [
        InlineKeyboardButton(f"{s['emoji']} {s['name']}", callback_data=f"setstatus:{task_id}:{s['id']}")
        for s in statuses if s["id"] != current_status_id
    ]
    kb = [status_btns[i:i+2] for i in range(0, len(status_btns), 2)]
    kb += [
        [
            InlineKeyboardButton("📝 ویرایش یادداشت", callback_data=f"editnotes:{task_id}"),
            InlineKeyboardButton("🔗 ویرایش لینک",    callback_data=f"editdoc:{task_id}"),
        ],
        [InlineKeyboardButton("🗑 حذف تسک", callback_data=f"deltask:{task_id}")],
        [InlineKeyboardButton("◀ برگشت",   callback_data="menu:tasks:all")],
    ]
    await _send_or_edit(update, "\n".join(lines), kb, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════════
# فیلترها
# ════════════════════════════════════════════════════════════════
async def filter_by_phase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    phases = get_phases()
    kb = [[InlineKeyboardButton(p["name"], callback_data=f"phase:{p['id']}")] for p in phases]
    kb.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    await _send_or_edit(update, "یک فاز انتخاب کنید:", kb)


async def filter_by_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    members = get_members()
    kb = [[InlineKeyboardButton(f"👤 {m['name']}", callback_data=f"member:{m['id']}")] for m in members]
    kb.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    await _send_or_edit(update, "یک عضو انتخاب کنید:", kb)


# ════════════════════════════════════════════════════════════════
# افزودن تسک
# ════════════════════════════════════════════════════════════════
async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "➕ *افزودن تسک جدید*\n\nعنوان تسک را بنویسید:",
        parse_mode="Markdown"
    )
    return ASK_TITLE


async def add_got_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_title"] = update.message.text.strip()
    members = get_members()
    kb = [[InlineKeyboardButton(m["name"], callback_data=f"nm:{m['id']}")] for m in members]
    kb.append([InlineKeyboardButton("👥 همه اعضا (تیمی)", callback_data="nm:0")])
    await update.message.reply_text("مسئول تسک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_MEMBER


async def add_got_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    val = int(q.data.split(":")[1])
    ctx.user_data["new_member"] = val   # 0 = تیمی
    phases = get_phases()
    kb = [[InlineKeyboardButton(p["name"], callback_data=f"np:{p['id']}")] for p in phases]
    await q.message.reply_text("فاز را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_PHASE


async def add_got_phase(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["new_phase"] = int(q.data.split(":")[1])
    statuses = get_statuses()
    kb = [[InlineKeyboardButton(f"{s['emoji']} {s['name']}", callback_data=f"ns:{s['id']}")] for s in statuses]
    await q.message.reply_text("وضعیت اولیه:", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_STATUS


async def add_got_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["new_status"] = int(q.data.split(":")[1])
    await q.message.reply_text(
        "سررسید تسک را بنویسید (مثلاً: خرداد ۱۴۰۵)\n"
        "یا /skip برای رد شدن:"
    )
    return ASK_DEADLINE


async def add_got_deadline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    deadline = None if update.message.text == "/skip" else update.message.text.strip()
    is_team = ctx.user_data["new_member"] == 0
    task_id = add_task(
        title=ctx.user_data["new_title"],
        member_id=ctx.user_data["new_member"] if not is_team else None,
        phase_id=ctx.user_data["new_phase"],
        status_id=ctx.user_data["new_status"],
        deadline=deadline,
        team=is_team,
    )
    await update.message.reply_text(
        f"✅ تسک #{task_id} با موفقیت اضافه شد!\n\n*{ctx.user_data['new_title']}*",
        parse_mode="Markdown"
    )
    await notify_all(ctx,
        f"➕ *تسک جدید اضافه شد*\n\n📌 {ctx.user_data['new_title']}",
        exclude_id=update.effective_user.id)
    ctx.user_data.clear()
    return ConversationHandler.END


async def add_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ افزودن تسک لغو شد.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# ویرایش یادداشت
# ════════════════════════════════════════════════════════════════
async def edit_notes_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["editing_task"] = int(q.data.split(":")[1])
    await q.message.reply_text("📝 یادداشت جدید را بنویسید:")
    return ASK_NOTES


async def edit_notes_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    task_id = ctx.user_data.pop("editing_task", None)
    if task_id:
        update_task_notes(task_id, update.message.text.strip())
        await update.message.reply_text("✅ یادداشت ذخیره شد.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# ویرایش لینک مستندات
# ════════════════════════════════════════════════════════════════
async def edit_doc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["editing_doc"] = int(q.data.split(":")[1])
    await q.message.reply_text("🔗 لینک مستندات را بفرستید:")
    return ASK_DOC


async def edit_doc_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    task_id = ctx.user_data.pop("editing_doc", None)
    if task_id:
        update_task_doc(task_id, update.message.text.strip())
        await update.message.reply_text("✅ لینک ذخیره شد.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# callback_query dispatcher
# ════════════════════════════════════════════════════════════════
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    data = q.data

    # ── بخش مالی ──
    if data.startswith("fin:"):
        if await finance_button_handler(update, ctx):
            return

    if data == "menu:main":
        await start(update, ctx)
    elif data == "menu:dashboard":
        await show_dashboard(update, ctx)
    elif data == "menu:tasks:all":
        await show_task_list(update, ctx)
    elif data.startswith("menu:tasks:s:"):
        sid = int(data.split(":")[-1])
        statuses = get_statuses()
        label = next((s["name"] for s in statuses if s["id"] == sid), "")
        await show_task_list(update, ctx, status_id=sid, title=f"تسک‌های {label}")
    elif data == "menu:filter:phase":
        await filter_by_phase(update, ctx)
    elif data == "menu:filter:member":
        await filter_by_member(update, ctx)
    elif data.startswith("task:"):
        await show_task_detail(update, ctx, int(data.split(":")[1]))
    elif data.startswith("phase:"):
        phase_id = int(data.split(":")[1])
        ph_name  = next((p["name"] for p in get_phases() if p["id"] == phase_id), "فاز")
        await show_task_list(update, ctx, phase_id=phase_id, title=ph_name)
    elif data.startswith("member:"):
        member_id = int(data.split(":")[1])
        mb_name   = next((m["name"] for m in get_members() if m["id"] == member_id), "عضو")
        await show_task_list(update, ctx, member_id=member_id, title=mb_name)
    elif data.startswith("setstatus:"):
        _, task_id, new_sid = data.split(":")
        task_id_int = int(task_id)
        new_sid_int = int(new_sid)
        update_task_status(task_id_int, new_sid_int)
        t, _ = get_task(task_id_int)
        statuses = get_statuses()
        s_label = next((f"{s['emoji']} {s['name']}" for s in statuses if s["id"] == new_sid_int), "")
        await notify_all(ctx,
            f"🔄 *تغییر وضعیت تسک*\n\n📌 {t['title']}\nوضعیت جدید: {s_label}",
            exclude_id=update.effective_user.id)
        await show_task_detail(update, ctx, task_id_int)
    elif data.startswith("deltask:"):
        task_id = int(data.split(":")[1])
        t, _ = get_task(task_id)
        title = t["title"] if t else f"#{task_id}"
        delete_task(task_id)
        await notify_all(ctx,
            f"🗑 *تسک حذف شد*\n\n📌 {title}",
            exclude_id=update.effective_user.id)
        await _send_or_edit(update, "🗑 تسک حذف شد.", [
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ])


# ════════════════════════════════════════════════════════════════
# ابزار کمکی
# ════════════════════════════════════════════════════════════════
async def _send_or_edit(update: Update, text: str, kb_rows: list, parse_mode="Markdown"):
    markup = InlineKeyboardMarkup(kb_rows)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=parse_mode)
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=parse_mode)


# ════════════════════════════════════════════════════════════════
# main
# ════════════════════════════════════════════════════════════════
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern="^menu:add$")],
        states={
            ASK_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_title)],
            ASK_MEMBER:   [CallbackQueryHandler(add_got_member, pattern="^nm:")],
            ASK_PHASE:    [CallbackQueryHandler(add_got_phase,  pattern="^np:")],
            ASK_STATUS:   [CallbackQueryHandler(add_got_status, pattern="^ns:")],
            ASK_DEADLINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_got_deadline),
                CommandHandler("skip", add_got_deadline),
            ],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )
    notes_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_notes_start, pattern="^editnotes:")],
        states={ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_notes_save)]},
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )
    doc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_doc_start, pattern="^editdoc:")],
        states={ASK_DOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_doc_save)]},
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_cmd))
    app.add_handler(CallbackQueryHandler(register_confirm, pattern="^reg:"))
    app.add_handler(add_conv)
    app.add_handler(notes_conv)
    app.add_handler(doc_conv)
    for fin_conv in get_finance_conversations():
        app.add_handler(fin_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 بات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
