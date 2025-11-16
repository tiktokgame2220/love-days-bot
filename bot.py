import sqlite3
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден!")
    print("ℹ️ Проверь файл .env")
    exit(1)

# Праздники мира
HOLIDAYS = {
    # 🇷🇺 Российские праздники
    "Новый год": "01.01",
    "Рождество": "07.01",
    "Старый Новый год": "14.01",
    "День защитника Отечества": "23.02",
    "Международный женский день": "08.03",
    "День весны и труда": "01.05",
    "День Победы": "09.05",
    "День России": "12.06",
    "День народного единства": "04.11",

    # 🌍 Международные праздники
    "День святого Валентина": "14.02",
    "День смеха": "01.04",
    "Хэллоуин": "31.10",
    "День рождения бота": "15.11",

    # 🇺🇸 Американские праздники
    "День независимости США": "04.07",
    "День благодарения": "28.11",
    "Хэллоуин в США": "31.10",
    "День памяти": "27.05",

    # 🇪🇺 Европейские праздники
    "День Европы": "09.05",
    "Октоберфест": "16.09",
    "День святого Патрика": "17.03",

    # 🇨🇳 Китайские праздники
    "Китайский Новый год": "29.01",
    "Праздник луны": "15.08",
    "День образования КНР": "01.10",

    # 🇧🇷 Бразильские праздники
    "Карнавал в Рио": "24.02",
    "День независимости Бразилии": "07.09",

    # 🇮🇳 Индийские праздники
    "Дивали": "01.11",
    "День независимости Индии": "15.08",
    "Холи": "25.03",

    # 🇲🇽 Мексиканские праздники
    "День мёртвых": "02.11",
    "День независимости Мексики": "16.09",

    # 🇯🇵 Японские праздники
    "Ханами": "27.03",
    "День основания государства": "11.02",
    "День рождения императора": "23.02",

    # 🇰🇷 Корейские праздники
    "Лунный Новый год": "10.02",
    "День освобождения Кореи": "15.08",

    # 🌐 Другие международные
    "Международный день мира": "21.09",
    "День Земли": "22.04",
    "День защиты детей": "01.06",
    "Всемирный день туризма": "27.09",
    "Международный день музыки": "01.10",
    "День космонавтики": "12.04",
    "День учителя": "05.10"
}


def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'relationships.db')


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relationships (
            user_id INTEGER PRIMARY KEY,
            start_date TEXT,
            partner_name TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            user_id INTEGER,
            name TEXT,
            date TEXT,
            PRIMARY KEY (user_id, name)
        )
    ''')
    conn.commit()
    conn.close()


def get_relationship_data(user_id):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT start_date, partner_name FROM relationships WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def set_relationship_data(user_id, start_date, partner_name=None):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO relationships (user_id, start_date, partner_name)
        VALUES (?, ?, ?)
    ''', (user_id, start_date.isoformat(), partner_name))
    conn.commit()
    conn.close()


def get_birthdays(user_id):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name, date FROM birthdays WHERE user_id = ?', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def add_birthday(user_id, name, date):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO birthdays (user_id, name, date)
        VALUES (?, ?, ?)
    ''', (user_id, name, date.isoformat()))
    conn.commit()
    conn.close()


def delete_birthday(user_id, name):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM birthdays WHERE user_id = ? AND name = ?', (user_id, name))
    conn.commit()
    conn.close()


def calculate_days_until_date(target_date):
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    next_occurrence = target_date.replace(year=current_date.year)
    if next_occurrence < current_date:
        next_occurrence = next_occurrence.replace(year=current_date.year + 1)

    return (next_occurrence - current_date).days


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = """
💖 Привет! Я бот для подсчета дней отношений и отсчета до праздников!

📅 Отношения:
/setdate DD.MM.YYYY - установить дату начала отношений
/count - посчитать сколько дней вместе
/stats - подробная статистика

🎂 Дни рождения:
/addbirthday Имя DD.MM - добавить день рождения
/birthdays - показать все дни рождения
/delbirthday Имя - удалить день рождения

🎉 Праздники:
/holidays - ближайшие праздники
/allholidays - все праздники мира
/find праздник - найти праздник
/nextholiday - ближайший праздник
/botday - день создания бота

❓ Помощь:
/help - показать справку
    """
    await update.message.reply_text(welcome_text)


async def set_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Пожалуйста, укажи дату: /setdate DD.MM.YYYY")
        return

    try:
        date_str = context.args[0]
        start_date = datetime.strptime(date_str, "%d.%m.%Y").date()

        partner_name = " ".join(context.args[1:]) if len(context.args) > 1 else None

        moscow_tz = pytz.timezone('Europe/Moscow')
        current_date = datetime.now(moscow_tz).date()

        if start_date > current_date:
            await update.message.reply_text("❌ Дата не может быть в будущем!")
            return

        set_relationship_data(user_id, start_date, partner_name)

        response = f"✅ Дата начала отношений установлена: {start_date.strftime('%d.%m.%Y')}"
        if partner_name:
            response += f"\n💕 С: {partner_name}"
        response += "\n📅 Используй /count чтобы посчитать дни"

        await update.message.reply_text(response)

    except ValueError:
        await update.message.reply_text("❌ Неверный формат даты! Используй: DD.MM.YYYY")


async def count_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    data = get_relationship_data(user_id)

    if not data:
        await update.message.reply_text("❌ Сначала установи дату: /setdate DD.MM.YYYY")
        return

    start_date = datetime.fromisoformat(data[0]).date()
    partner_name = data[1]
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    days_together = (current_date - start_date).days

    if days_together % 10 == 1 and days_together % 100 != 11:
        days_word = "день"
    elif 2 <= days_together % 10 <= 4 and (days_together % 100 < 10 or days_together % 100 >= 20):
        days_word = "дня"
    else:
        days_word = "дней"

    months = days_together // 30
    years = days_together // 365

    message = f"💖 Вы вместе уже {days_together} {days_word}!"

    if partner_name:
        message = f"💖 Вы с {partner_name} вместе уже {days_together} {days_word}!"

    message += f"\n📅 С: {start_date.strftime('%d.%m.%Y')}"

    if years > 0:
        message += f"\n📊 Это {years} лет и {days_together % 365} дней"
    elif months > 0:
        message += f"\n📊 Это {months} месяцев и {days_together % 30} дней"

    special_dates = {
        100: "🎉 100 дней! Это так мило!",
        365: "🎉 Целый год вместе! Поздравляю!",
        500: "🎉 500 дней любви!",
        1000: "🎉 1000 дней! Невероятно! 💕"
    }

    if days_together in special_dates:
        message += f"\n\n{special_dates[days_together]}"

    await update.message.reply_text(message)


async def add_birthday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text("❌ Используй: /addbirthday Имя DD.MM\nНапример: /addbirthday Маша 15.03")
        return

    try:
        name = context.args[0]
        date_str = context.args[1]

        birthday = datetime.strptime(f"{date_str}.{datetime.now().year}", "%d.%m.%Y").date()

        add_birthday(user_id, name, birthday)

        await update.message.reply_text(f"✅ День рождения добавлен!\n🎂 {name}: {birthday.strftime('%d.%m')}")

    except ValueError:
        await update.message.reply_text("❌ Неверный формат даты! Используй: DD.MM")


async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    birthdays = get_birthdays(user_id)

    if not birthdays:
        await update.message.reply_text("📋 Нет добавленных дней рождения.\nДобавь: /addbirthday Имя DD.MM")
        return

    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    message = "🎂 Твои дни рождения:\n\n"

    for name, date_str in birthdays:
        birthday = datetime.fromisoformat(date_str).date()
        days_until = calculate_days_until_date(birthday)

        if days_until == 0:
            message += f"🎉 Сегодня день рождения у {name}!\n"
        elif days_until == 1:
            message += f"📅 {name}: завтра! ({birthday.strftime('%d.%m')})\n"
        else:
            message += f"📅 {name}: через {days_until} дней ({birthday.strftime('%d.%m')})\n"

    await update.message.reply_text(message)


async def delete_birthday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Укажи имя: /delbirthday Имя")
        return

    name = " ".join(context.args)
    delete_birthday(user_id, name)

    await update.message.reply_text(f"✅ День рождения {name} удален!")


async def list_holidays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    message = "🎉 Ближайшие праздники:\n\n"

    holidays_with_days = []

    for holiday, date_str in HOLIDAYS.items():
        holiday_date = datetime.strptime(f"{date_str}.{current_date.year}", "%d.%m.%Y").date()
        days_until = calculate_days_until_date(holiday_date)
        holidays_with_days.append((holiday, days_until, holiday_date))

    holidays_with_days.sort(key=lambda x: x[1])

    # Показываем только ближайшие 10 праздников
    for holiday, days_until, holiday_date in holidays_with_days[:10]:
        if days_until == 0:
            message += f"🎊 {holiday}: СЕГОДНЯ! 🎊\n"
        elif days_until == 1:
            message += f"🎊 {holiday}: завтра! ({holiday_date.strftime('%d.%m')})\n"
        else:
            message += f"📅 {holiday}: через {days_until} дней ({holiday_date.strftime('%d.%m')})\n"

    message += "\n✨ Используй /allholidays чтобы увидеть все праздники"

    await update.message.reply_text(message)


async def all_holidays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать все праздники сгруппированные по месяцам"""
    message = "🎊 Все праздники в боте:\n\n"

    holidays_by_month = {}

    # Группируем праздники по месяцам
    for holiday, date_str in HOLIDAYS.items():
        month = int(date_str.split('.')[1])
        if month not in holidays_by_month:
            holidays_by_month[month] = []
        holidays_by_month[month].append((holiday, date_str))

    # Месяца по порядку
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    for month_num in sorted(holidays_by_month.keys()):
        message += f"📅 **{months[month_num - 1]}**:\n"
        for holiday, date_str in sorted(holidays_by_month[month_num], key=lambda x: x[1]):
            days_until = calculate_days_until_date(datetime.strptime(f"{date_str}.2024", "%d.%m.%Y").date())
            if days_until == 0:
                message += f"  🎉 {holiday} - СЕГОДНЯ!\n"
            else:
                message += f"  📌 {holiday} ({date_str}) - через {days_until} дней\n"
        message += "\n"

    message += "✨ Используй /find чтобы найти конкретный праздник"

    await update.message.reply_text(message, parse_mode='Markdown')


async def find_holiday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Найти праздник по названию"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Используй: /find праздник\n"
            "Например: /find новый год\n"
            "Или: /find день"
        )
        return

    search_term = " ".join(context.args).lower()
    found_holidays = []

    for holiday, date_str in HOLIDAYS.items():
        if search_term in holiday.lower():
            days_until = calculate_days_until_date(datetime.strptime(f"{date_str}.2024", "%d.%m.%Y").date())
            found_holidays.append((holiday, date_str, days_until))

    if not found_holidays:
        await update.message.reply_text(f"❌ Праздники с '{search_term}' не найдены")
        return

    message = f"🔍 Найдено праздников с '{search_term}':\n\n"
    for holiday, date_str, days_until in found_holidays:
        if days_until == 0:
            message += f"🎉 {holiday} - СЕГОДНЯ! ({date_str})\n"
        elif days_until == 1:
            message += f"📌 {holiday} - ЗАВТРА! ({date_str})\n"
        else:
            message += f"📌 {holiday} - через {days_until} дней ({date_str})\n"

    await update.message.reply_text(message)


async def next_holiday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    next_holiday_info = None
    min_days = 365

    for holiday, date_str in HOLIDAYS.items():
        holiday_date = datetime.strptime(f"{date_str}.{current_date.year}", "%d.%m.%Y").date()
        days_until = calculate_days_until_date(holiday_date)

        if days_until < min_days:
            min_days = days_until
            next_holiday_info = (holiday, days_until, holiday_date)

    if next_holiday_info:
        holiday, days_until, holiday_date = next_holiday_info

        if days_until == 0:
            message = f"🎊 СЕГОДНЯ {holiday}! 🎉🎉🎉"
        elif days_until == 1:
            message = f"🎉 Ближайший праздник: {holiday} - ЗАВТРА! 🎊"
        else:
            message = f"🎉 Ближайший праздник: {holiday}\n📅 Через {days_until} дней\n🗓️ {holiday_date.strftime('%d.%m.%Y')}"

        await update.message.reply_text(message)


async def bot_birthday_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация о дне создания бота"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    bot_birthday = datetime.strptime(f"15.11.{current_date.year}", "%d.%m.%Y").date()
    days_until = calculate_days_until_date(bot_birthday)

    if days_until == 0:
        message = "🎉🎉🎉 СЕГОДНЯ День создания этого бота! 🎉🎉🎉\n\nСпасибо, что используешь меня! 💖"
    elif days_until == 1:
        message = "🎊 Завтра День создания бота! Уже готовим праздник! 🎊"
    else:
        message = f"🤖 День создания бота: 15 ноября\n📅 Осталось ждать: {days_until} дней"

    await update.message.reply_text(message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    data = get_relationship_data(user_id)

    if not data:
        await update.message.reply_text("❌ Сначала установи дату: /setdate DD.MM.YYYY")
        return

    start_date = datetime.fromisoformat(data[0]).date()
    partner_name = data[1]
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz).date()

    days_together = (current_date - start_date).days
    weeks = days_together // 7
    months = days_together // 30
    years = days_together // 365

    message = "📊 Статистика:\n\n"

    if partner_name:
        message += f"💕 Пара: Вы и {partner_name}\n"

    message += f"📅 Начало: {start_date.strftime('%d.%m.%Y')}\n"
    message += f"⏰ Вместе уже:\n"
    message += f"   • {days_together} дней\n"
    message += f"   • {weeks} недель\n"
    message += f"   • {months} месяцев\n"

    if years > 0:
        message += f"   • {years} лет\n"

    await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
💕 Бот для подсчета дней отношений и праздников

📅 Отношения:
/setdate DD.MM.YYYY - установить дату
/count - посчитать дни
/stats - статистика

🎂 Дни рождения:
/addbirthday Имя DD.MM - добавить
/birthdays - список
/delbirthday Имя - удалить

🎉 Праздники:
/holidays - ближайшие праздники
/allholidays - все праздники мира
/find праздник - найти праздник
/nextholiday - ближайший праздник
/botday - день создания бота

❓ Помощь:
/help - справка
    """
    await update.message.reply_text(help_text)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)


def main():
    # Инициализируем БД
    init_db()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setdate", set_date))
    application.add_handler(CommandHandler("count", count_days))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("addbirthday", add_birthday_cmd))
    application.add_handler(CommandHandler("birthdays", list_birthdays))
    application.add_handler(CommandHandler("delbirthday", delete_birthday_cmd))
    application.add_handler(CommandHandler("holidays", list_holidays))
    application.add_handler(CommandHandler("allholidays", all_holidays))
    application.add_handler(CommandHandler("find", find_holiday))
    application.add_handler(CommandHandler("nextholiday", next_holiday))
    application.add_handler(CommandHandler("botday", bot_birthday_info))
    application.add_handler(CommandHandler("help", help_command))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    print("🤖 Бот запущен...")
    print("🎂 День создания бота: 15 Ноября")
    print("🌍 Загружено праздников:", len(HOLIDAYS))
    application.run_polling()


if __name__ == "__main__":
    main()