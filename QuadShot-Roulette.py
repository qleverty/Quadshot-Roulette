print("loading...")
import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import *
from settings import handle_settings, get_default_settings, ITEMS_ORDER, get_player_settings, format_main_settings_message, get_main_settings_keyboard
from bottoken import BOT_TOKEN
import json
import os
import sys
import re
print("starting...")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def save_games():
    try:
        with open("games.json", 'w', encoding='utf-8') as f:
            json.dump(games, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"error saving games: {e}")
        return False


def load_games():
    try:
        if not os.path.exists("games.json"):
            return {}
        with open("games.json", 'r', encoding='utf-8') as f:
            data = json.load(f)

        for game_key, game in data.items():
            if "p" in game and isinstance(game["p"], dict):
                game["p"] = {int(uid): player for uid, player in game["p"].items()}
            
            if "tp" in game and game["tp"] is not None:
                game["tp"] = int(game["tp"])
        
        return data
    except Exception as e:
        print(f"error loading games: {e}")
        return {}


if os.path.exists("games.json"):
    print("save file found")
    games = load_games()
    print(f"successfully loaded {len(games)} games")
    try:
        if os.path.exists("games_.json"):
            os.remove("games_.json")
        os.rename("games.json", "games_.json")
    except Exception as e:
        print(f"error renaming file: {e}")
else:
    games = dict()


ITEMS_POOL = "🪚🔍🚬🔗🍺💉🧲💊📞📟"
INVENTORY_SIZE = 8
STAT_KEYS = {
    "k": ("Убийств", 500),
    "sh": ("Попаданий", 150),
    "sb": ("Холостых в себя", 70),
    "iu": ("Предметов использовано", 40),
    "rw": ("Побед в раунде", 1000),
    "sr": ("Раундов выжил", 200),
    "sdk": ("Убийств с пилой", 1000),
    "ch": ("Исцелений сигаретами", 150),
    "mh": ("Исцелений лекарством", 200),
    "cw": ("Побед при 1 HP", 1500),
}
ITEM_NAMES = {
    "🔍": "Лупа",
    "🍺": "Пиво",
    "🚬": "Сигареты",
    "🔗": "Наручники",
    "💉": "Адреналин",
    "🧲": "Инвертор",
    "💊": "Лекарство",
    "📞": "Телефон",
    "🪚": "Пила",
    "📟": "Пульт"
}

def format_guide_rules() -> str:
    return """<b>📖 Правила</b>

Игра состоит из 3 раундов. Задача — выжить.

В начале раунда дробовик заряжается несколькими патронами: боевыми (🛑) и холостыми (⚪). Их количество и соотношение случайны.

В свой ход вы стреляете в себя или в противника:
- Холостой в себя — ход остаётся за вами
- Боевой в себя — теряете HP и передаёте ход
- Боевой в противника — противник теряет HP

Когда патронник опустеет, происходит перезарядка. Вместе с ней игроки получают новые предметы.

Раунд завершается, когда остаётся один выживший. После этого начинается следующий раунд — все воскрешают, предметы очищаются.

Победитель игры определяется по итогам всех трёх раундов."""

def format_guide_items() -> str:
    return """<b>🎁 Предметы</b>

Предметы используются в свой ход перед выстрелом. У каждого игрока может быть до 8 предметов одновременно.

🪚 <b>Пила</b> — укорачивает ствол. Следующий выстрел наносит удвоенный урон

🔍 <b>Лупа</b> — показывает, какой патрон сейчас в стволе (боевой или холостой)

🚬 <b>Сигареты</b> — восстанавливают 1 единицу здоровья

🔗 <b>Наручники</b> — сковывают противника, заставляя его пропустить следующий его ход

🍺 <b>Пиво</b> — перезаряжает дробовик, выбрасывая текущий патрон из патронника

💉 <b>Адреналин</b> — позволяет использовать любой предмет из инвентаря противника

🧲 <b>Инвертор</b> — меняет тип текущего патрона на противоположный (боевой ⇆ холостой)

💊 <b>Просроченное лекарство</b> — 50/50 шанс восстановить 2 HP, либо потерять 1 HP

📞 <b>Телефон</b> — показывает случайный патрон из всего патронника (не только текущий)

📟 <b>Пульт</b> — меняет порядок ходов на противоположный (работает только в играх с 3+ игроками)"""

def format_guide_settings() -> str:
    return """<b>⚙️ Настройки</b>

Команда /settings открывает меню настроек. Настройки уникальны для каждого из трёх раундов и сохраняются в базе данных между играми.

Вы можете задать диапазоны для случайной генерации:

<b>❤️ Здоровье (1-10 HP)</b> — определяет, с каким количеством HP начинают игроки в раунде

<b>🔘 Патроны (2-14)</b> — сколько патронов будет загружено в патронник при (пере)зарядке

<b>🧳 Предметы (0-8)</b> — сколько предметов получит каждый игрок при раздаче

<b>📊 Соотношение</b> — баланс между боевыми и холостыми патронами (от "только один боевой" до "только один холостой")

<b>🎁 Выбор предметов</b> — какие предметы могут выпадать в этом раунде. Можно включить или отключить любой предмет

Для каждого параметра задаётся минимум и максимум. При генерации бот случайно выбирает значение в этом диапазоне."""

def get_guide_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Правила", callback_data="guide_rules"),
         InlineKeyboardButton(text="🎁 Предметы", callback_data="guide_items")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="guide_settings")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="nsng")]
    ])


def safe_randint(min_val: int, max_val: int) -> int:
    if min_val >= max_val:
        return min_val
    return random.randint(min_val, max_val)

def add_stat(player: dict, stat_key: str, amount: int = 1):
    if stat_key not in player["s"]:
        player["s"][stat_key] = 0
    player["s"][stat_key] += amount

def calculate_score(player: dict) -> int:
    return sum(player["s"].get(k, 0) * STAT_KEYS[k][1] for k in STAT_KEYS.keys())

def get_game_key(message: Message) -> str:
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None
    return f"{chat_id}|{thread_id}" if thread_id else str(chat_id)

async def check_player_turn(callback: CallbackQuery, game: dict, user_id: int, require_turn: bool = True, require_alive: bool = False) -> bool:
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return False
    
    if require_turn and game.get("tp") != user_id:
        await callback.answer("⚠️ Не ваш ход!", show_alert=True)
        return False
    
    if require_alive and game["p"][user_id]["h"] <= 0:
        await callback.answer("⚠️ Вы мертвы!", show_alert=True)
        return False
    
    return True

async def get_user_name(user_id: int) -> str:
    try:
        user = await bot.get_chat(user_id)
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        return name or f"User{user_id}"
    except:
        return f"User{user_id}"


async def assign_player(game: dict, user_id: int):
    name = await get_user_name(user_id)
    name = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001FA00-\U0001FAFF]+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > 20:
        name = name[:17] + "..."
    
    colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚫️", "⚪️"]
    used_colors = {player["n"][0] for player in game["p"].values() if player.get("n")}
    available_colors = [c for c in colors if c not in used_colors]
    player_color = random.choice(available_colors or colors)
    
    game["p"][user_id] = {
        "n": f"{player_color} {name}",
        "h": 2,
        "i": "x" * INVENTORY_SIZE,
        "s": {}
    }
    
    if len(game["p"]) == 1 and "sg" not in game:
        game["sg"] = get_player_settings(user_id)


def generate_bullets(r: int) -> list:
    print("generate_bullets")
    return [True, False]


def generate_bullets_with_settings(total: int, ratio_idx: int) -> list:
    if ratio_idx == 0:  # single live
        return [True] + [False] * (total - 1)
    elif ratio_idx == 6:  # single blank
        return [False] + [True] * (total - 1)
    
    ranges = [(10, 20), (20, 40), (40, 60), (60, 80), (80, 90)]
    min_pct, max_pct = ranges[ratio_idx - 1]
    
    min_live = max(1, int(total * min_pct / 100))
    max_live = min(total - 1, int(total * max_pct / 100))
    live = safe_randint(min_live, max_live)
    
    bullets = [True] * live + [False] * (total - live)
    random.shuffle(bullets)
    return bullets


def generate_items(r: int, player_count: int = 2, bullets_count: int = 0) -> str:
    print("generate_items")
    return "x"


def generate_items_with_settings(item_count: int, enabled_items: str, player_count: int = 2) -> str:
    pool = enabled_items
    
    if player_count <= 2 and "📟" in pool:
        pool = pool.replace("📟", "")
    
    if not pool or item_count == 0:
        return "x" * INVENTORY_SIZE
    
    items = "".join(random.choices(pool, k=item_count))
    return items + "x" * (INVENTORY_SIZE - len(items))


def add_items_to_inventory(inventory: str, new_items: str) -> str:
    inv_list = list(inventory)
    for item in new_items:
        if item == 'x':
            continue
        for i in range(INVENTORY_SIZE):
            if inv_list[i] == 'x':
                inv_list[i] = item
                break
    return "".join(inv_list)


def init_round(game: dict, r: int):
    settings = game.get("sg", {}).get("r", [None, None, None])[r]
    
    if settings is None:
        if "sg" not in game:
            game["sg"] = get_default_settings()
        settings = game["sg"]["r"][r]
    
    hp = safe_randint(settings["h"][0], settings["h"][1])
    game["mh"] = hp
    
    for p in game["p"].values():
        p["h"] = hp
        p["i"] = "x" * INVENTORY_SIZE
        if "hc" in p:
            del p["hc"]
        if "sw" in p:
            del p["sw"]
    
    game["r"] = r
    
    bullets_count = safe_randint(settings["b"][0], settings["b"][1])
    game["b"] = generate_bullets_with_settings(bullets_count, settings["br"])
    
    game["o"] = True
    game["sm"] = 0
    
    player_count = len(game["p"])
    enabled_items = "".join([ITEMS_ORDER[i] for i, c in enumerate(settings["i"]) if c == '1'])
    item_count = safe_randint(settings["ic"][0], settings["ic"][1])
    
    for p in game["p"].values():
        p["i"] = generate_items_with_settings(item_count, enabled_items, player_count)
    
    alive = list(game["p"].keys())
    game["tp"] = random.choice(alive)
    

async def show_final_results(game: dict):
    scores = [(uid, p, calculate_score(p)) for uid, p in game["p"].items()]
    scores.sort(key=lambda x: x[2], reverse=True)
    
    winner_uid, winner, winner_score = scores[0]
    
    msg = "🏆 ИГРА ЗАВЕРШЕНА! 🏆\n\n"
    msg += f"🥇 Победитель: {winner['n']}\n"
    
    stat_icons = {
        "k": "🔪", "sh": "🎯", "sb": "⚪", "iu": "🛠️",
        "rw": "🏆", "sr": "🛡️", "sdk": "🪚", "ch": "🚬",
        "mh": "💊", "cw": "❤️",
    }
    
    for key, (name, points) in STAT_KEYS.items():
        count = winner["s"].get(key, 0)
        if count > 0:
            msg += f"{stat_icons.get(key, '')} {name}: {count} (+{count * points:,})\n"
    
    msg += f"\n💎 Всего: {winner_score:,} очков\n\n"
    
    msg += "📜 Остальные:\n"
    medals = ["🥈", "🥉"]
    for i, (uid, p, score) in enumerate(scores[1:], 2):
        medal = medals[i-2] if i <= 3 else f"{i}."
        msg += f"{medal} {p['n']} — {score:,}\n"
    
    empty_kb = InlineKeyboardMarkup(inline_keyboard=[])
    await update_game_msg(game, msg, empty_kb)

    parts = game["k"].split("|")
    chat_id = int(parts[0])
    thread_id = None
    if len(parts) > 1 and parts[1] != 'None':
        try:
            thread_id = int(parts[1])
        except ValueError:
            thread_id = None
    message_id = game["m"]

    game_key = game["k"]
    if game_key in games:
        del games[game_key]

    async def unpin_after_delay():
        await asyncio.sleep(30)
        try:
            await bot.unpin_chat_message(
                chat_id=chat_id,
                message_id=message_id
            )
        except TelegramBadRequest as e:
            if "message to unpin not found" not in str(e).lower():
                print(f"error unpinning: {e}")
        except Exception as e:
            print(f"unexpected error unpinning: {e}")

    asyncio.create_task(unpin_after_delay())


def count_bullets(b: list) -> tuple:
    live = sum(1 for x in b if x)
    blank = len(b) - live
    return live, blank, len(b) 


def format_game_message(game: dict) -> str:
    msg = f"🎮 Раунд {game['r'] + 1}\n\n"
    
    live, blank, current_total = count_bullets(game["b"])
    total_loaded = len(game["b"]) + game["sm"]
    msg += f"🔫 Патронов: 🛑 {live} | ⚪ {blank}  (из {total_loaded})\n\n"
    
    msg += "👥 Игроки:\n"
    for uid, p in game["p"].items():
        marker = "🎯" if uid == game.get("tp") else "├"
        hearts = "❤️" * p["h"]
        
        status = ""
        if p.get("hc"):
            status += " 🔗"
        if p.get("sw"):
            status += " 🪚"
        
        msg += f"{marker} {p['n']}: {hearts}{status}\n"
    
    alive_count = sum(1 for p in game["p"].values() if p["h"] > 0)
    if alive_count > 2:
        order_icon = "⬆️" if not game["o"] else "⬇️"
        msg += f"\n🔄 Порядок: {order_icon}\n"
    
    if game.get("tp") and game["tp"] in game["p"]:
        msg += f"\n⏰ Ход: {game['p'][game['tp']]['n']}\n"
    
    return msg


def has_items(inventory: str) -> bool:
    return any(c != 'x' for c in inventory)


def get_game_keyboard(game: dict, uid: int) -> InlineKeyboardMarkup:
    kb = []
    items = game["p"][uid]["i"]
    
    if has_items(items):
        for row in range(2):  # Changed from 4 to 2 rows
            row_btns = []
            for col in range(4):
                idx = row * 4 + col
                if idx < len(items):
                    emoji = items[idx]
                    if emoji != 'x':
                        row_btns.append(InlineKeyboardButton(text=emoji, callback_data=f"i_{emoji}_{idx}"))
                    else:
                        row_btns.append(InlineKeyboardButton(text=" ", callback_data="empty"))
                else:
                    row_btns.append(InlineKeyboardButton(text=" ", callback_data="empty"))
            kb.append(row_btns)
    
    kb.append([InlineKeyboardButton(text="🔫 Сделать выстрел", callback_data="shoot")])
    kb.append([
        InlineKeyboardButton(text="👁 Предметы", callback_data="p"),
        InlineKeyboardButton(text="❌ Выйти", callback_data="l")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_shoot_menu(game: dict) -> InlineKeyboardMarkup:
    kb = []

    kb.append([InlineKeyboardButton(text="🔫 В себя", callback_data="s_s")])

    alive = [uid for uid, p in game["p"].items() if p["h"] > 0 and uid != game["tp"]]
    
    for uid in alive:
        p = game["p"][uid]
        kb.append([InlineKeyboardButton(text=f"{p['n']} (❤️ {p['h']})", callback_data=f"s_{uid}")])
    
    
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"b_{game['tp']}")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_handcuffs_menu(game: dict, item_idx: int, actor_id: int) -> InlineKeyboardMarkup:
    kb = []
    alive = [uid for uid, p in game["p"].items() if p["h"] > 0 and uid != actor_id]
    for uid in alive:
        p = game["p"][uid]
        kb.append([InlineKeyboardButton(text=f"{p['n']}", callback_data=f"hc{item_idx}|{uid}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"b_{actor_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_adrenaline_player_menu(game: dict, item_idx: int) -> InlineKeyboardMarkup:
    kb = []
    alive = [uid for uid, p in game["p"].items() if p["h"] > 0 and uid != game["tp"] and has_items(p["i"])]
    
    for uid in alive:
        p = game["p"][uid]
        kb.append([InlineKeyboardButton(text=f"{p['n']}", callback_data=f"ap{item_idx}|{uid}")])
    
    kb.append([InlineKeyboardButton(text="👁 Посмотреть предметы", callback_data=f"al{item_idx}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"b_{game['tp']}")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_adrenaline_item_menu(game: dict, target_uid: int, item_idx: int, actor_id: int) -> InlineKeyboardMarkup:
    kb = []
    items = game["p"][target_uid]["i"]
    
    for row in range(2):
        row_btns = []
        for col in range(4):
            idx = row * 4 + col
            if idx < len(items):
                emoji = items[idx]
                if emoji != 'x' and emoji != '💉':
                    row_btns.append(InlineKeyboardButton(text=emoji, callback_data=f"ai{item_idx}|{target_uid}|{idx}"))
                else:
                    row_btns.append(InlineKeyboardButton(text=" ", callback_data="empty"))
            else:
                row_btns.append(InlineKeyboardButton(text=" ", callback_data="empty"))
        kb.append(row_btns)
    
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"apb{item_idx}|{actor_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_all_inventories(game: dict) -> str:
    msg = "📦 Предметы игроков:\n\n"
    
    for uid, p in game["p"].items():
        if p["h"] <= 0:
            continue
        
        msg += f"{p['n']}:\n"
        items = p["i"].replace('x', '')
        
        if items:
            for i in range(0, len(items), 4):
                chunk = items[i:i+4]
                msg += " " + "".join(chunk) + "\n"
        else:
            msg += " (нет предметов)\n"
        
        msg += "\n"
    
    return msg


async def update_game_msg(game: dict, text: str = None, kb=None):
    if text is None:
        text = format_game_message(game)
        if game.get("st") == "game" and game.get("tp") and game["tp"] in game["p"]:
            current_player = game["p"][game["tp"]]
            if has_items(current_player["i"]):
                text += "📦 Твои предметы:\n"

    if kb is None:
        if game.get("st") == "game" and game.get("tp"):
            kb = get_game_keyboard(game, game["tp"])

    chat_id, *thread_parts = game["k"].split("|")
    thread_id = int(thread_parts[0]) if thread_parts and thread_parts[0] != 'None' else None

    retries = 5
    for attempt in range(retries):
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=int(chat_id),
                message_id=game["m"],
                reply_markup=kb
            )
            return
        except Exception as e:
            error_msg = str(e).strip()
            print(f"[ERROR] update_game_msg: {error_msg}")
            
            wait_time = 5
            parts = error_msg.split()
            for i, part in enumerate(parts):
                if part.lower() in ("in", "after") and i + 1 < len(parts) and parts[i + 1].isdigit():
                    wait_time = int(parts[i + 1])
                    break
            await asyncio.sleep(wait_time)
            if attempt == retries - 1:
                raise


def next_turn(game: dict):
    alive = [uid for uid, p in game["p"].items() if p["h"] > 0]
    if len(alive) <= 1:
        return
    
    if game["tp"] not in alive:
        game["tp"] = alive[0]
        return
    
    current_idx = alive.index(game["tp"])
    next_idx = (current_idx + 1) % len(alive) if game["o"] else (current_idx - 1) % len(alive)
    game["tp"] = alive[next_idx]
    
    if game["p"][game["tp"]].get("hc"):
        game["p"][game["tp"]]["hc"] = False
        next_turn(game)


async def reload_bullets(game: dict):
    empty_kb = InlineKeyboardMarkup(inline_keyboard=[])

    await update_game_msg(game, "🔄 Патронник пуст!\n\nПерезарядка...", empty_kb)
    await asyncio.sleep(2)

    settings = game.get("sg", {}).get("r", [None, None, None])[game["r"]]
    if settings is None:
        game["b"] = generate_bullets(game["r"])
    else:
        bullets_count = safe_randint(settings["b"][0], settings["b"][1])
        game["b"] = generate_bullets_with_settings(bullets_count, settings["br"])
    
    game["sm"] = 0

    bullets_display = " ".join("🛑" if x else "⚪️" for x in game["b"])
    await update_game_msg(game, f"Патроны загружены:\n{bullets_display}", empty_kb)
    await asyncio.sleep(3.2)

    random.shuffle(game["b"])

    player_count = len(game["p"])
    items_text = ""
    
    settings = game.get("sg", {}).get("r", [None, None, None])[game["r"]]
    if settings is None:
        # Фолбэк на старую логику
        bullets_count = len(game["b"])
        for uid, p in game["p"].items():
            if p["h"] > 0:
                new_items = generate_items(game["r"], player_count, bullets_count)
                clean_items = new_items.replace('x', '')
                free_slots = p["i"].count('x')
                
                if free_slots == 0:
                    items_text += f"{p['n']}: ⚠️ Нет места!\n"
                else:
                    actual_items = clean_items[:free_slots]
                    if actual_items:
                        p["i"] = add_items_to_inventory(p["i"], actual_items + "x" * (len(clean_items) - len(actual_items)))
                        items_text += f"{p['n']}: {' '.join(actual_items)}\n"
    else:
        enabled_items = "".join([ITEMS_ORDER[i] for i, c in enumerate(settings["i"]) if c == '1'])
        item_count = safe_randint(settings["ic"][0], settings["ic"][1])
        
        for uid, p in game["p"].items():
            if p["h"] > 0:
                new_items = generate_items_with_settings(item_count, enabled_items, player_count)
                clean_items = new_items.replace('x', '')
                free_slots = p["i"].count('x')
                
                if free_slots == 0:
                    items_text += f"{p['n']}: ⚠️ Нет места!\n"
                else:
                    actual_items = clean_items[:free_slots]
                    if actual_items:
                        p["i"] = add_items_to_inventory(p["i"], actual_items + "x" * (len(clean_items) - len(actual_items)))
                        items_text += f"{p['n']}: {' '.join(actual_items)}\n"

    if items_text:
        await update_game_msg(game, f"📦 Раздача предметов:\n\n{items_text}", empty_kb)
        await asyncio.sleep(8)

    await update_game_msg(game, "🎰 Патроны загружаются\nв случайном порядке...", empty_kb)
    await asyncio.sleep(2.5)


async def check_round_end(game: dict) -> bool:
    alive = [uid for uid, p in game["p"].items() if p["h"] > 0]
    if len(alive) != 1:
        return False

    winner_uid = alive[0]
    winner = game["p"][winner_uid]
    
    # Добавляем статистику победителю
    if winner["h"] == 1:
        add_stat(winner, "cw")
    else:
        add_stat(winner, "rw")
    
    # Статистика выжившим (если были)
    for uid, p in game["p"].items():
        if p["h"] > 0 and uid != winner_uid:
            add_stat(p, "sr")

    empty_kb = InlineKeyboardMarkup(inline_keyboard=[])

    if game["r"] < 2:
        await update_game_msg(game,
            f"║ РАУНД {game['r'] + 1} ОКОНЧЕН ║\n\n🏆 Победитель раунда:\n{winner['n']}\n\n💀 Погибшие игроки\nвоскрешают!\n\n🔄 Предметы очищены\n\n⭐ Переход к раунду {game['r'] + 2}\nчерез 10 секунд...",
            empty_kb
        )
        await asyncio.sleep(10)
        init_round(game, game["r"] + 1)
        await start_round_animation(game)
    else:
        await update_game_msg(game,
            f"║ РАУНД 3 ОКОНЧЕН ║\n\n🏆 Победитель раунда:\n{winner['n']}\n\n⏳ Подсчёт итогов...",
            empty_kb
        )
        await asyncio.sleep(5)
        await show_final_results(game)

    return True


async def start_round_animation(game: dict):
    bullets_display = " ".join("🛑" if x else "⚪️" for x in game["b"])
    empty_kb = InlineKeyboardMarkup(inline_keyboard=[])

    await update_game_msg(game, f"🎮 Раунд {game['r'] + 1}\n\nПатроны загружены:\n{bullets_display}\n\n⏳ Игра начинается...", empty_kb)
    await asyncio.sleep(3)

    random.shuffle(game["b"])

    items_text = ""
    for uid, p in game["p"].items():
        clean_items = p["i"].replace('x', '')
        if clean_items:
            items_text += f"{p['n']}: {' '.join(clean_items)}\n"

    if items_text:
        await update_game_msg(game, f"🎮 Раунд {game['r'] + 1}\n\n📦 Раздача предметов:\n\n{items_text}", empty_kb)
        await asyncio.sleep(8)

    await update_game_msg(game, "🎰 Патроны загружаются\nв случайном порядке...", empty_kb)
    await asyncio.sleep(2)

    await update_game_msg(game)

def get_max_hp(game: dict) -> int:
    return game.get("mh", 6)

def get_items_view_keyboard(game: dict, user_id: int) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"pb_{user_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_all_inventories_view(game: dict) -> str:
    msg = "📦 Предметы игроков:\n\n"
    
    for uid, p in game["p"].items():
        if p["h"] <= 0:
            continue
        
        hearts = "❤️" * p["h"]
        msg += f"{p['n']} ({hearts}):\n"
        items = p["i"].replace('x', '')
        
        if items:
            for i in range(0, len(items), 4):
                chunk = items[i:i+4]
                msg += " " + "".join(chunk) + "\n"
        else:
            msg += " (нет предметов)\n"
        
        msg += "\n"
    
    return msg


def format_lobby_message(game: dict) -> str:
    msg = "🎮 Новая игра создана!\n\n"
    
    player_count = len(game["p"])
    msg += f"👥 Игроки ({player_count}/8):\n"
    
    for uid, player in game["p"].items():
        msg += f"├ {player['n']}\n"
    
    msg += "\n⏳ Ожидание игроков...\n"
    return msg


def get_lobby_keyboard(game: dict) -> InlineKeyboardMarkup:
    keyboard = []
    
    if len(game["p"]) < 8:
        keyboard.append([InlineKeyboardButton(text="🎲 Присоединиться", callback_data="j")])
    
    if len(game["p"]) >= 2:
        keyboard.append([InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_game")])
    
    keyboard.append([InlineKeyboardButton(text="⚙️ Настроить игру", callback_data="sg_main")])
    keyboard.append([InlineKeyboardButton(text="❌ Отменить / Выйти", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✅ Новая игра", callback_data=f"sng_{user_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="nsng")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("saveandquit"))
async def cmd_save_and_quit(message: Message):
    if message.from_user.id != 5932062044:
        return
    
    saved = save_games() if games else False
    count = len(games) if games else 0
    
    await message.answer(f"games saved: {saved}, active games: {count} - shutting down...")
    
    await bot.session.close()
    await dp.storage.close()
    sys.exit(0)

@dp.message(Command("guide"))
async def cmd_guide(message: Message):
    await message.answer(
        text=format_guide_rules(),
        reply_markup=get_guide_keyboard(),
        parse_mode='HTML'
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    user_id = message.from_user.id
    
    user_settings = get_player_settings(user_id)
    
    if game_key in games:
        game = games[game_key]
        
        if game["st"] != "lobby":
            await message.answer("⚠️ Нельзя менять настройки во время игры!")
            return
        
        creator_id = list(game["p"].keys())[0]
        if user_id != creator_id:
            await message.answer("⚠️ Только создатель может менять настройки игры!")
            return
        
        is_personal = False
        await message.answer(
            text=format_main_settings_message(is_personal),
            reply_markup=get_main_settings_keyboard(is_personal)
        )
    else:
        is_personal = True
        await message.answer(
            text=format_main_settings_message(is_personal),
            reply_markup=get_main_settings_keyboard(is_personal)
        )

@dp.message(Command("newshot"))
async def cmd_start_new(message: Message):
    if message.chat.type == "private":
        await message.answer("❌ Эта команда доступна только в группах!")
        return
    
    game_key = get_game_key(message)
    user_id = message.from_user.id
    
    if game_key in games:
        existing_game = games[game_key]
        first_player = list(existing_game["p"].keys())[0]
        
        if first_player == user_id:
            confirmation_msg = await message.answer(
                "⚠️ У вас уже есть активная игра в этом чате!\n\nНачало новой игры сбросит текущую.",
                reply_markup=get_confirmation_keyboard(user_id)
            )
            return
        else:
            await message.answer("⚠️ В этом чате уже идёт игра!")
            return
    
    game = {
        "st": "lobby",
        "p": {},
        "m": None,
        "k": game_key,
        "sg": get_player_settings(user_id)
    }
    
    await assign_player(game, user_id)
    
    lobby_msg = await message.answer(
        text=format_lobby_message(game),
        reply_markup=get_lobby_keyboard(game)
    )
    
    game["m"] = lobby_msg.message_id
    games[game_key] = game


@dp.callback_query(F.data == "sg_close")
async def callback_settings_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@dp.callback_query(F.data.startswith("sng_"))
async def callback_start_new_game_confirm(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    if callback.from_user.id != user_id:
        await callback.answer("⚠️ Это не ваше подтверждение!", show_alert=True)
        return
    
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key in games:
        del games[game_key]
    
    await callback.message.delete()
    
    game = {
        "st": "lobby",
        "p": {},
        "m": None,
        "k": game_key,
        "sg": get_player_settings(user_id)
    }
    
    await assign_player(game, user_id)
    
    lobby_msg = await callback.message.answer(
        text=format_lobby_message(game),
        reply_markup=get_lobby_keyboard(game)
    )
    
    game["m"] = lobby_msg.message_id
    games[game_key] = game
    
    await callback.answer("✅ Игра начата!")


@dp.callback_query(F.data.startswith("sg_"))
async def callback_settings(callback: CallbackQuery):
    await handle_settings(callback, games)


@dp.callback_query(F.data == "nsng")
async def callback_no_start_new_game(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Отменено")


@dp.callback_query(F.data == "p")
async def callback_peek(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True, require_alive=True):
        return
    
    await callback.answer()
    await update_game_msg(game, format_all_inventories_view(game), get_items_view_keyboard(game, user_id))


@dp.callback_query(F.data.startswith("pb_"))
async def callback_peek_back(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    target_id = int(callback.data[3:])
    
    if not await check_player_turn(callback, game, user_id):
        return
    
    if user_id != target_id:
        await callback.answer("⚠️ Не ваш ход!", show_alert=True)
        return
    
    await callback.answer()
    await update_game_msg(game)


@dp.callback_query(F.data == "j")
async def callback_join(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    if user_id in game["p"]:
        await callback.answer("⚠️ Вы уже в игре!", show_alert=True)
        return
    
    if len(game["p"]) >= 8:
        await callback.answer("⚠️ Лобби заполнено!", show_alert=True)
        return
    
    if game["st"] != "lobby":
        await callback.answer("⚠️ Игра уже началась!", show_alert=True)
        return
    
    await assign_player(game, user_id)
    
    await callback.message.edit_text(
        text=format_lobby_message(game),
        reply_markup=get_lobby_keyboard(game)
    )
    
    await callback.answer("✅ Вы присоединились к игре!")


@dp.callback_query(F.data == "start_game")
async def callback_start_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    first_player = list(game["p"].keys())[0]
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    if user_id != first_player:
        await callback.answer("⚠️ Только создатель может начать игру!", show_alert=True)
        return
    
    if len(game["p"]) < 2:
        await callback.answer("⚠️ Нужно минимум 2 игрока!", show_alert=True)
        return
    
    if game["st"] != "lobby":
        await callback.answer("⚠️ Игра уже началась!", show_alert=True)
        return

    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=game["m"],
            disable_notification=True
        )
    except TelegramBadRequest as e:
        print(f"error pinning: {e}")
    
    game["st"] = "game"
    init_round(game, 0)
    await start_round_animation(game)


@dp.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    first_player = list(game["p"].keys())[0]
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    if user_id == first_player:
        del games[game_key]
        await callback.message.edit_text("❌ Игра отменена.")
        await callback.answer("Игра отменена")
        return
    
    if user_id in game["p"]:
        del game["p"][user_id]
        
        if len(game["p"]) == 0:
            del games[game_key]
            await callback.message.edit_text("❌ Все игроки вышли. Игра отменена.")
            await callback.answer("Вы вышли из игры")
            return
        
        await callback.message.edit_text(
            text=format_lobby_message(game),
            reply_markup=get_lobby_keyboard(game)
        )
        await callback.answer("Вы вышли из игры")
        return
    
    await callback.answer("⚠️ Вы не в игре!", show_alert=True)


@dp.callback_query(F.data == "shoot")
async def callback_shoot(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True, require_alive=True):
        return
    
    await callback.answer()
    await update_game_msg(game, "🎯 Выберите цель:\n", get_shoot_menu(game))


@dp.callback_query(F.data.startswith("s_"))
async def callback_shoot_target(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True):
        return
    
    await callback.answer()
    
    target_str = callback.data[2:]
    target_id = user_id if target_str == "s" else int(target_str)
    
    game["tp"] = None
    
    shooter = game["p"][user_id]
    target = game["p"][target_id]
    
    await update_game_msg(game, f"🎯 {shooter['n']} целится\nв {target['n'] if target_id != user_id else 'себя'}...", None)
    await asyncio.sleep(3)
    
    bullet = game["b"].pop(0)
    game["sm"] += 1
    damage = 2 if shooter.get("sw") else 1
    was_saw = shooter.get("sw", False)
    shooter["sw"] = False
    
    extra_turn = False
    
    if bullet:
        add_stat(shooter, "sh")
        
        await update_game_msg(game, "💥 ВЫСТРЕЛ!", None)
        await asyncio.sleep(2.2)
        
        target["h"] -= damage
        
        if target["h"] <= 0:
            if was_saw and damage == 2:
                add_stat(shooter, "sdk")
            else:
                add_stat(shooter, "k")
            
            await update_game_msg(game, f"💀 {target['n']} убит!\n\n🔫 Патронов: 🛑 {count_bullets(game['b'])[0]} | ⚪ {count_bullets(game['b'])[1]}", None)
            await asyncio.sleep(3.2)
        else:
            await update_game_msg(game, f"🩸 {target['n']}\nполучает {damage} урона!\n\n{target['n']}: {'❤️' * target['h']}", None)
            await asyncio.sleep(2.5)
    else:
        await update_game_msg(game, "💨 Холостой! *щелчок*", None)
        await asyncio.sleep(2)
        
        if target_id == user_id and len(game["b"]) > 0:
            add_stat(shooter, "sb")
            await update_game_msg(game, f"{shooter['n']} получает\nдополнительный ход! 🎲", None)
            extra_turn = True
            await asyncio.sleep(2)
        else:
            await update_game_msg(game, "Ничего не произошло.", None)
            await asyncio.sleep(1.5)
    
    if await check_round_end(game):
        return
    
    if len(game["b"]) > 0 and all(not b for b in game["b"]):
        await update_game_msg(game, "⚠️ В патроннике остались\nтолько холостые!\n\nПерезарядка...", None)
        await asyncio.sleep(2)
        game["b"] = []
    
    if len(game["b"]) == 0:
        await reload_bullets(game)
    
    if game["p"][user_id]["h"] > 0:
        if extra_turn:
            game["tp"] = user_id
        else:
            game["tp"] = user_id
            next_turn(game)
    else:
        alive = [uid for uid, p in game["p"].items() if p["h"] > 0]
        game["tp"] = alive[0] if alive else None
    
    await update_game_msg(game)


@dp.callback_query(F.data.startswith("b_"))
async def callback_back(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    target_id = int(callback.data[2:])
    
    if not await check_player_turn(callback, game, user_id):
        return
    
    if user_id != target_id:
        await callback.answer("⚠️ Не ваш ход!", show_alert=True)
        return
    
    await callback.answer()
    await update_game_msg(game)


@dp.callback_query(F.data.startswith("i_"))
async def callback_item(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True, require_alive=True):
        return
    
    parts = callback.data.split("_")
    item_emoji = parts[1]
    idx = int(parts[2])
    
    player = game["p"][user_id]
    
    items_list = list(player["i"])
    if idx >= len(items_list) or items_list[idx] != item_emoji:
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    
    if item_emoji == "🔗":
        await callback.answer()
        add_stat(player, "iu")
        await update_game_msg(game, "🔗 Выберите игрока,\nна которого хотите надеть наручники:", get_handcuffs_menu(game, idx, user_id))
        return
    elif item_emoji == "💉":
        alive_with_items = [uid for uid, p in game["p"].items() if p["h"] > 0 and uid != user_id and has_items(p["i"])]
        if not alive_with_items:
            await callback.answer("⚠️ Ни у кого нет предметов!", show_alert=True)
            return
        
        await callback.answer()
        add_stat(player, "iu")
        await update_game_msg(game, "💉 Выберите игрока, чей предмет\nхотите использовать:", get_adrenaline_player_menu(game, idx))
        return
    
    items_list[idx] = 'x'
    player["i"] = "".join(items_list)
    
    game["tp"] = None
    
    if item_emoji == "🔍":
        await use_magnifying_glass(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "📞":
        await use_phone(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "🍺":
        await use_beer(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "🚬":
        await use_cigarettes(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "🪚":
        await use_saw(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "🧲":
        await use_inverter(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "💊":
        await use_medicine(game, user_id, callback, is_adrenaline=False)
    elif item_emoji == "📟":
        await use_remote(game, user_id, callback, is_adrenaline=False)
    else:
        await callback.answer("⚠️ Этот предмет пока не работает!", show_alert=True)
    
    game["tp"] = user_id
    
    if game["p"][user_id]["h"] > 0:
        await update_game_msg(game)


@dp.callback_query(F.data.startswith("hc"))
async def callback_handcuffs_target(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    parts = callback.data[2:].split("|")
    
    # Формат: hc{item_idx}|{target_uid} или hc_adr|{handcuffs_owner}|{handcuffs_idx}|{target_uid}
    if parts[0] == "_adr":
        # Наручники через адреналин - НЕ проверяем game["tp"]
        handcuffs_owner_id = int(parts[1])
        handcuffs_idx = int(parts[2])
        target_uid = int(parts[3])
        is_adrenaline = True
    else:
        if game.get("tp") != user_id:
            await callback.answer("⚠️ Не ваш ход!", show_alert=True)
            return
        
        item_idx = int(parts[0])
        target_uid = int(parts[1])
        handcuffs_owner_id = user_id
        handcuffs_idx = item_idx
        is_adrenaline = False
    
    if target_uid == user_id:
        await callback.answer("❌ Вы не можете надеть наручники на самих себя!", show_alert=True)
        return
    
    handcuffs_owner = game["p"][handcuffs_owner_id]
    
    if not is_adrenaline:
        items_list = list(handcuffs_owner["i"])
        if handcuffs_idx >= len(items_list) or items_list[handcuffs_idx] != "🔗":
            await callback.answer("❌ Предмет не найден!", show_alert=True)
            return
        
        items_list[handcuffs_idx] = 'x'
        handcuffs_owner["i"] = "".join(items_list)
    
    game["tp"] = None
    await callback.answer()
    
    target = game["p"][target_uid]
    target["hc"] = True
    
    player = game["p"][user_id]
    if is_adrenaline:
        msg = f"💉 {player['n']} использует\n🔗 Наручники {handcuffs_owner['n']} на {target['n']}.\n\n{target['n']} пропускает следующий ход."
    else:
        msg = f"🔗 {player['n']} надевает наручники\nна {target['n']}.\n\n{target['n']} пропускает следующий ход."
    await update_game_msg(game, msg, None)
    await asyncio.sleep(3)
    
    game["tp"] = user_id
    await update_game_msg(game)


@dp.callback_query(F.data.startswith("ap"))
async def callback_adrenaline_player(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True):
        return
    
    if callback.data.startswith("apb"):
        parts = callback.data[3:].split("|")
        item_idx = int(parts[0])
        if len(parts) > 1:
            actor_id = int(parts[1])
            if user_id != actor_id:
                await callback.answer("⚠️ Не ваш ход!", show_alert=True)
                return
        
        await callback.answer()
        await update_game_msg(game, "💉 Выберите игрока, чей предмет\nхотите использовать:", get_adrenaline_player_menu(game, item_idx))
        return
    
    parts = callback.data[2:].split("|")
    item_idx = int(parts[0])
    target_uid = int(parts[1])
    
    await callback.answer()
    
    target = game["p"][target_uid]
    await update_game_msg(game, f"💉 Выберите, какой предмет у {target['n']}\nвы хотите использовать:", get_adrenaline_item_menu(game, target_uid, item_idx, user_id))

@dp.callback_query(F.data.startswith("al"))
async def callback_adrenaline_look(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    if user_id != game.get("tp"):
        await callback.answer("⚠️ Не ваш ход!", show_alert=True)
        return
    
    item_idx = int(callback.data[2:])
    
    await callback.answer()
    
    inventories_text = format_all_inventories(game)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ab{item_idx}")]
    ])
    
    await update_game_msg(game, inventories_text, back_kb)

# Adrenaline look back button
@dp.callback_query(F.data.startswith("ab"))
async def callback_adrenaline_look_back(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    
    if game["m"] != callback.message.message_id:
        await callback.answer("❌ Это старое сообщение!", show_alert=True)
        return
    
    item_idx = int(callback.data[2:])
    
    await callback.answer()
    await update_game_msg(game, "💉 Выберите игрока, чей предмет\nхотите использовать:", get_adrenaline_player_menu(game, item_idx))


@dp.callback_query(F.data.startswith("ai"))
async def callback_adrenaline_item(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    
    if not await check_player_turn(callback, game, user_id, require_turn=True):
        return
    
    parts = callback.data[2:].split("|")
    adr_idx = int(parts[0])
    target_uid = int(parts[1])
    target_item_idx = int(parts[2])
    
    player = game["p"][user_id]
    target = game["p"][target_uid]
    
    player_items = list(player["i"])
    if adr_idx >= len(player_items) or player_items[adr_idx] != "💉":
        await callback.answer("❌ Адреналин не найден!", show_alert=True)
        return
    
    target_items = list(target["i"])
    if target_item_idx >= len(target_items) or target_items[target_item_idx] == 'x':
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    
    target_item = target_items[target_item_idx]
    
    if target_item == "💉":
        await callback.answer("❌ Нельзя использовать чужой адреналин!", show_alert=True)
        return
    
    player_items[adr_idx] = 'x'
    player["i"] = "".join(player_items)
    
    target_items[target_item_idx] = 'x'
    target["i"] = "".join(target_items)
    
    game["tp"] = None
    
    if target_item == "🔍":
        await use_magnifying_glass(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "🍺":
        await use_beer(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "🚬":
        await use_cigarettes(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "🪚":
        await use_saw(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "🧲":
        await use_inverter(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "📞":
        await use_phone(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "💊":
        await use_medicine(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "📟":
        await use_remote(game, user_id, callback, is_adrenaline=True, target=target, target_item=target_item)
    elif target_item == "🔗":
        await callback.answer()
        msg = f"💉 {player['n']} использует\n🔗 Наручники игрока {target['n']}!"
        await update_game_msg(game, msg, None)
        await asyncio.sleep(2)
        
        kb = []
        alive = [uid for uid, p in game["p"].items() if p["h"] > 0 and uid != user_id]
        for uid in alive:
            p = game["p"][uid]
            kb.append([InlineKeyboardButton(text=f"{p['n']}", callback_data=f"hc_adr|{target_uid}|{target_item_idx}|{uid}")])
        
        await update_game_msg(game, "🔗 Выберите игрока,\nна которого хотите надеть наручники:", InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    game["tp"] = user_id
    
    if game["p"][user_id]["h"] > 0:
        await update_game_msg(game)


async def use_magnifying_glass(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")    
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n🔍 Лупу!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    next_bullet = game["b"][0] if game["b"] else None
    if next_bullet is not None:
        await callback.answer(f"🔍 Текущий патрон:\n{'🛑 БОЕВОЙ' if next_bullet else '⚪ ХОЛОСТОЙ'}", show_alert=True)
    else:
        await callback.answer("⚠️ Патронник пуст!", show_alert=True)


async def use_phone(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n📞 Телефон!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    if not game["b"]:
        await callback.answer("📞 Патронник пуст!", show_alert=True)
    else:
        idx = random.randint(0, len(game["b"]) - 1)
        bullet = game["b"][idx]
        bullet_type = "🛑 БОЕВОЙ" if bullet else "⚪ ХОЛОСТОЙ"
        
        actual_position = game.get("sm", 0) + idx + 1
        
        await callback.answer(f"📞 Звонок:\nПатрон №{actual_position} — {bullet_type}", show_alert=True)


async def use_beer(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n🍺 Пиво!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    if not game["b"]:
        await update_game_msg(game, "⚠️ Патронник пуст!", None)
        await asyncio.sleep(1.5)
        return
    
    ejected = game["b"].pop(0)
    game["sm"] += 1
    bullet_type = "🛑 БОЕВОЙ" if ejected else "⚪ ХОЛОСТОЙ"
    
    await update_game_msg(game, f"Из патронника вылетает\n{bullet_type} патрон!", None)
    await asyncio.sleep(2)
    
    if not game["b"]:
        await reload_bullets(game)
    elif len(game["b"]) > 0 and all(not b for b in game["b"]):
        await update_game_msg(game, "⚠️ В патроннике остались\nтолько холостые!\n\nПерезарядка...", None)
        await asyncio.sleep(2)
        game["b"] = []
        await reload_bullets(game)


async def use_cigarettes(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n🚬 Сигареты!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    max_hp = get_max_hp(game)
    if player["h"] >= max_hp:
        await update_game_msg(game, "⚠️ Здоровье уже полное!", None)
        await asyncio.sleep(1.5)
    else:
        player["h"] = min(player["h"] + 1, max_hp)
        add_stat(player, "ch")
        await update_game_msg(game, f"🚬 +1 ❤️\n\n{player['n']}: {'❤️' * player['h']}", None)
        await asyncio.sleep(2)


async def use_saw(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n🪚 Пилу!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    player["sw"] = True
    
    await update_game_msg(game, "🪚 Следующий выстрел\nнанесёт x2 урон!", None)
    await asyncio.sleep(2)


async def use_inverter(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n🧲 Инвертор!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    if not game["b"]:
        await update_game_msg(game, "⚠️ Патронник пуст!", None)
        await asyncio.sleep(1.5)
        return
    
    game["b"][0] = not game["b"][0]
    
    await update_game_msg(game, "🧲 Патрон инвертирован!", None)
    await asyncio.sleep(2)


async def use_medicine(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n💊 Просроченное лекарство!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    max_hp = get_max_hp(game)
    
    if random.random() < 0.5:
        old_hp = player["h"]
        player["h"] = min(player["h"] + 2, max_hp)
        healed = player["h"] - old_hp
        
        if healed > 0:
            add_stat(player, "mh")
            await update_game_msg(game, f"💊 Повезло! +{healed} ❤️\n\n{player['n']}: {'❤️' * player['h']}", None)
        else:
            await update_game_msg(game, "💊 Повезло, но\nздоровье уже полное!", None)
        await asyncio.sleep(2)
    else:
        player["h"] -= 1
        
        if player["h"] <= 0:
            await update_game_msg(game, f"💊 Отравление!\n\n💀 {player['n']} умирает!", None)
            await asyncio.sleep(3)
            
            if await check_round_end(game):
                return
        else:
            await update_game_msg(game, f"💊 Отравление! -1 ❤️\n\n{player['n']}: {'❤️' * player['h']}", None)
            await asyncio.sleep(2)


async def use_remote(game: dict, user_id: int, callback: CallbackQuery, is_adrenaline: bool = False, target: dict = None, target_item: str = None):
    await callback.answer()
    player = game["p"][user_id]

    if not is_adrenaline:
        add_stat(player, "iu")
    
    if is_adrenaline:
        item_name = ITEM_NAMES.get(target_item, target_item)
        msg = f"💉 {player['n']} использует\n{target_item} {item_name} игрока {target['n']}!"
    else:
        msg = f"{player['n']} использует\n📟 Пульт!"
    
    await update_game_msg(game, msg, None)
    await asyncio.sleep(2)
    
    game["o"] = not game["o"]
    
    await update_game_msg(game, "📟 Порядок ходов\nизменён!", None)
    await asyncio.sleep(2)


@dp.callback_query(F.data == "sg_back")
async def callback_settings_back(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    if game_key not in games:
        await callback.answer("❌ Игра не найдена!", show_alert=True)
        return
    
    game = games[game_key]
    user_id = callback.from_user.id
    first_player = list(game["p"].keys())[0]
    
    if user_id != first_player:
        await callback.answer("⚠️ Только создатель может менять настройки!", show_alert=True)
        return
    
    if game["st"] != "lobby":
        await callback.answer("⚠️ Игра уже началась!", show_alert=True)
        return
    
    await callback.message.edit_text(
        text=format_lobby_message(game),
        reply_markup=get_lobby_keyboard(game)
    )
    await callback.answer()


@dp.callback_query(F.data == "guide_rules")
async def callback_guide_rules(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            text=format_guide_rules(),
            reply_markup=get_guide_keyboard(),
            parse_mode='HTML'
        )
    except:
        pass
    await callback.answer()

@dp.callback_query(F.data == "guide_items")
async def callback_guide_items(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            text=format_guide_items(),
            reply_markup=get_guide_keyboard(),
            parse_mode='HTML'
        )
    except:
        pass
    await callback.answer()

@dp.callback_query(F.data == "guide_settings")
async def callback_guide_settings(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            text=format_guide_settings(),
            reply_markup=get_guide_keyboard(),
            parse_mode='HTML'
        )
    except:
        pass
    await callback.answer()


@dp.callback_query(F.data == "l")
async def callback_leave(callback: CallbackQuery):
    await callback.answer("⚠️ Функция в разработке!", show_alert=True)


@dp.callback_query(F.data == "empty")
async def callback_empty(callback: CallbackQuery):
    await callback.answer()


async def main():
    print("the bot is started!")
    await bot.delete_webhook(drop_pending_updates=True)
    attempt = 0
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"[CRITICAL ERROR]: {e}")
            await asyncio.sleep(10)
            attempt += 1
            print(f"Restarting... (attempt: {attempt})...")
        

asyncio.run(main())
