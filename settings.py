import asyncio
import copy
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os

DATABASE_FILE = "database.json"
HP_OPTIONS = [1, 2, 3, 4, 5, 6, 8, 10]
BULLET_OPTIONS = [2, 4, 6, 8, 10, 12, 14]
ITEM_COUNT_OPTIONS = [0, 1, 2, 4, 5, 6, 8]
RATIO_OPTIONS = [
    "🛑 Только один боевой 🛑",
    "🛑 10-20% / 80-90% ⚪️",
    "🛑 20-40% / 60-80% ⚪️",
    "🛑 40-60% / 40-60% ⚪️",
    "🛑 60-80% / 20-40% ⚪️",
    "🛑 80-90% / 10-20% ⚪️",
    "⚪️ Только один холостой ⚪️"
]
ITEMS_ORDER = "🪚🔍🚬🔗🍺💉🧲💊📞📟"

DEFAULT_SETTINGS = {
    "r": [
        {"h": [1, 1], "b": [2, 2], "ic": [0, 0], "br": 2, "i": "1111111111"},
        {"h": [3, 3], "b": [3, 6], "ic": [2, 4], "br": 2, "i": "1111111111"},
        {"h": [5, 5], "b": [4, 8], "ic": [3, 6], "br": 2, "i": "1111111111"}
    ]
}


def get_default_settings():
    return copy.deepcopy(DEFAULT_SETTINGS)


def load_database():
    if not os.path.exists(DATABASE_FILE):
        return {"players": {}}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"players": {}}


def save_database(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_player_settings(user_id: int):
    db = load_database()
    user_id_str = str(user_id)
    
    if user_id_str not in db["players"]:
        db["players"][user_id_str] = {"sg": get_default_settings()}
        save_database(db)
    
    return db["players"][user_id_str]["sg"]


def update_player_settings(user_id: int, settings: dict):
    db = load_database()
    user_id_str = str(user_id)
    
    if "players" not in db:
        db["players"] = {}
    
    db["players"][user_id_str] = {"sg": settings}
    save_database(db)


async def check_settings_access(callback: CallbackQuery, games: dict) -> tuple:
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id if callback.message.is_topic_message else None
    game_key = f"{chat_id}|{thread_id}" if thread_id else str(chat_id)
    
    user_id = callback.from_user.id
    user_settings = get_player_settings(user_id)
    
    if game_key in games:
        game = games[game_key]
        
        if game["st"] != "lobby":
            await callback.answer("⚠️ Нельзя менять настройки во время игры!", show_alert=True)
            return False, False, game, user_settings
        
        creator_id = list(game["p"].keys())[0]
        if callback.from_user.id != creator_id:
            await callback.answer("⚠️ Только создатель может менять настройки!", show_alert=True)
            return False, False, game, user_settings
        
        return True, False, game, user_settings
    else:
        return True, True, None, user_settings


def format_main_settings_message(is_personal: bool) -> str:
    msg = "⚙️ Настройки игры:"
    if is_personal:
        msg += "\n\n⚠️ В этом чате нет активных игр, поэтому сейчас вы настраиваете ваши личные настройки для будущих игр."
    return msg


def get_main_settings_keyboard(is_personal: bool) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🧩 Геймплей", callback_data="sg_game")],
        [InlineKeyboardButton(text="1️⃣ Раунд 1", callback_data="sg_r0")],
        [InlineKeyboardButton(text="2️⃣ Раунд 2", callback_data="sg_r1")],
        [InlineKeyboardButton(text="3️⃣ Раунд 3", callback_data="sg_r2")],
        [InlineKeyboardButton(text="🔄 По умолчанию", callback_data="sg_reset")]
    ]
    
    if not is_personal:
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="sg_back")])
    else:
        kb.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="sg_close")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_round_menu_message(settings: dict, round_idx: int, is_personal: bool) -> str:
    r = settings["r"][round_idx]
    msg = f"{('1️⃣','2️⃣','3️⃣')[round_idx]} Раунд {round_idx + 1}:\n\n"
    msg += f"❤️ Здоровье: {r['h'][0]}-{r['h'][1]}\n"
    msg += f"🔢 Патроны: {r['b'][0]}-{r['b'][1]}\n"
    msg += f"🧳 Предметы: {r['ic'][0]}-{r['ic'][1]}\n"
    msg += f"📊 Соотношение: {RATIO_OPTIONS[r['br']]}\n"
    
    enabled = [ITEMS_ORDER[i] for i, c in enumerate(r['i']) if c == '1']
    msg += f"🎁 Включено: {' '.join(enabled) if enabled else 'нет'}"
    
    if is_personal:
        msg += "\n\n⚠️ В этом чате нет активных игр, поэтому сейчас вы настраиваете ваши личные настройки для будущих игр."
    
    return msg


def get_round_menu_keyboard(round_idx: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="❤️ Количество здоровья", callback_data=f"sg_r{round_idx}_hp")],
        [InlineKeyboardButton(text="🔢 Количество патронов", callback_data=f"sg_r{round_idx}_b")],
        [InlineKeyboardButton(text="🧳 Количество предметов", callback_data=f"sg_r{round_idx}_ic")],
        [InlineKeyboardButton(text="📊 Соотношение патронов", callback_data=f"sg_r{round_idx}_br")],
        [InlineKeyboardButton(text="🎁 Предметы", callback_data=f"sg_r{round_idx}_i")],
	#[InlineKeyboardButton(text="🔄 По умолчанию", callback_data=f"sg_r{round_idx}_reset")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="sg_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_minmax_message(emoji: str, title: str, current_min: int, current_max: int, is_personal: bool) -> str:
    msg = f"{emoji} {title}:\n\nТекущее: {current_min}-{current_max}"
    if is_personal:
        msg += "\n\n⚠️ В этом чате нет активных игр, поэтому сейчас вы настраиваете ваши личные настройки для будущих игр."
    return msg


def get_minmax_keyboard(round_idx: int, key: str, options: list, current_min: int, current_max: int) -> InlineKeyboardMarkup:
    emoji = "❤️" if key == "hp" else "🧳" if key == "ic" else "🔘"
    kb = [[InlineKeyboardButton(text="🔽 Мин.", callback_data="empty"), 
           InlineKeyboardButton(text="🔼 Макс.", callback_data="empty")]]
    
    for opt in reversed(options):
        min_text = f"{emoji} {opt}" + (" ✅" if opt == current_min else "")
        max_text = f"{emoji} {opt}" + (" ✅" if opt == current_max else "")
        kb.append([
            InlineKeyboardButton(text=min_text, callback_data=f"sg_r{round_idx}_{key}_min_{opt}"),
            InlineKeyboardButton(text=max_text, callback_data=f"sg_r{round_idx}_{key}_max_{opt}")
        ])
    
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"sg_r{round_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_ratio_message(current_ratio: int, is_personal: bool) -> str:
    msg = "📊 Соотношение патронов:\n\nВыберите баланс боевых/холостых:"
    if is_personal:
        msg += "\n\n⚠️ В этом чате нет активных игр, поэтому сейчас вы настраиваете ваши личные настройки для будущих игр."
    return msg


def get_ratio_keyboard(round_idx: int, current_ratio: int) -> InlineKeyboardMarkup:
    kb = []
    for i, opt in enumerate(RATIO_OPTIONS):
        text = opt + (" ✅" if i == current_ratio else "")
        kb.append([InlineKeyboardButton(text=text, callback_data=f"sg_r{round_idx}_br_{i}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"sg_r{round_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def format_items_message(items_string: str, is_personal: bool) -> str:
    msg = "🎁 Предметы:\n\nНажмите, чтобы включить/выключить:"
    if is_personal:
        msg += "\n\n⚠️ В этом чате нет активных игр, поэтому сейчас вы настраиваете ваши личные настройки для будущих игр."
    return msg


def get_items_keyboard(round_idx: int, items_string: str) -> InlineKeyboardMarkup:
    kb = []
    row1, row2 = [], []
    
    for i in range(10):
        emoji = ITEMS_ORDER[i]
        status = "✅" if items_string[i] == '1' else "🚫"
        btn = InlineKeyboardButton(text=f"{emoji}{status}", callback_data=f"sg_r{round_idx}_i_{i}")
        
        if i < 5:
            row1.append(btn)
        else:
            row2.append(btn)
    
    kb.append(row1)
    kb.append(row2)
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"sg_r{round_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def handle_settings(callback: CallbackQuery, games: dict):
    has_access, is_personal, game, user_settings = await check_settings_access(callback, games)
    
    if not has_access:
        return
    
    if is_personal:
        current_settings = user_settings
    else:
        if "sg" not in game:
            game["sg"] = get_default_settings()
        current_settings = game["sg"]
    
    parts = callback.data.split("_")
    
    if callback.data == "sg_back":
        if is_personal:
            await callback.answer("Нет активной игры для возврата!", show_alert=True)
            return

        game_key = f"{callback.message.chat.id}|{callback.message.message_thread_id if callback.message.is_topic_message else 'None'}"
        if game_key.endswith("|None"):
            game_key = str(callback.message.chat.id)

        if game_key not in games or games[game_key]["st"] != "lobby":
            await callback.answer("Игра не найдена или уже идёт!", show_alert=True)
            return

        game = games[game_key]

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

        await callback.message.edit_text(
            text=format_lobby_message(game),
            reply_markup=get_lobby_keyboard(game)
        )
        await callback.answer()
        return
    
    elif parts[1] == "main":
        await callback.message.edit_text(
            format_main_settings_message(is_personal),
            reply_markup=get_main_settings_keyboard(is_personal)
        )
        await callback.answer()
    
    elif parts[1] == "game":
        await callback.answer("⚠️ Раздел в разработке!", show_alert=True)
    
    elif parts[1] == "reset":
        if not is_personal:
            game["sg"] = get_default_settings()
            current_settings = game["sg"]
            # Сохраняем для создателя
            creator_id = list(game["p"].keys())[0]
            update_player_settings(creator_id, current_settings)
        else:
            current_settings = get_default_settings()
            update_player_settings(callback.from_user.id, current_settings)
        
        await callback.answer("✅ Настройки сброшены!")
        return
    
    elif parts[1].startswith("r"):
        round_idx = int(parts[1][1])
        r = current_settings["r"][round_idx]
        
        if len(parts) == 2:
            await callback.message.edit_text(
                format_round_menu_message(current_settings, round_idx, is_personal),
                reply_markup=get_round_menu_keyboard(round_idx)
            )
            await callback.answer()
        
        elif parts[2] == "hp":
            if len(parts) == 3:
                await callback.message.edit_text(
                    format_minmax_message("❤️", "Количество здоровья", r["h"][0], r["h"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "hp", HP_OPTIONS, r["h"][0], r["h"][1])
                )
                await callback.answer()
            elif parts[3] in ["min", "max"]:
                idx = 0 if parts[3] == "min" else 1
                new_val = int(parts[4])
                
                if parts[3] == "min" and new_val > r["h"][1]:
                    await callback.answer("⚠️ Минимум не может быть больше максимума!", show_alert=True)
                    return
                if parts[3] == "max" and new_val < r["h"][0]:
                    await callback.answer("⚠️ Максимум не может быть меньше минимума!", show_alert=True)
                    return
                
                r["h"][idx] = new_val
                
                if not is_personal:
                    game["sg"] = current_settings
                    creator_id = list(game["p"].keys())[0]
                    update_player_settings(creator_id, current_settings)
                else:
                    update_player_settings(callback.from_user.id, current_settings)
                
                await callback.message.edit_text(
                    format_minmax_message("❤️", "Количество здоровья", r["h"][0], r["h"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "hp", HP_OPTIONS, r["h"][0], r["h"][1])
                )
                await callback.answer()
        
        elif parts[2] == "b":
            if len(parts) == 3:
                await callback.message.edit_text(
                    format_minmax_message("🔘", "Количество патронов", r["b"][0], r["b"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "b", BULLET_OPTIONS, r["b"][0], r["b"][1])
                )
                await callback.answer()
            elif parts[3] in ["min", "max"]:
                idx = 0 if parts[3] == "min" else 1
                new_val = int(parts[4])
                
                if parts[3] == "min" and new_val > r["b"][1]:
                    await callback.answer("⚠️ Минимум не может быть больше максимума!", show_alert=True)
                    return
                if parts[3] == "max" and new_val < r["b"][0]:
                    await callback.answer("⚠️ Максимум не может быть меньше минимума!", show_alert=True)
                    return
                
                r["b"][idx] = new_val
                
                if not is_personal:
                    game["sg"] = current_settings
                    creator_id = list(game["p"].keys())[0]
                    update_player_settings(creator_id, current_settings)
                else:
                    update_player_settings(callback.from_user.id, current_settings)
                
                await callback.message.edit_text(
                    format_minmax_message("🔘", "Количество патронов", r["b"][0], r["b"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "b", BULLET_OPTIONS, r["b"][0], r["b"][1])
                )
                await callback.answer()
        
        elif parts[2] == "ic":
            if len(parts) == 3:
                await callback.message.edit_text(
                    format_minmax_message("🧳", "Количество предметов", r["ic"][0], r["ic"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "ic", ITEM_COUNT_OPTIONS, r["ic"][0], r["ic"][1])
                )
                await callback.answer()
            elif parts[3] in ["min", "max"]:
                idx = 0 if parts[3] == "min" else 1
                new_val = int(parts[4])
                
                if parts[3] == "min" and new_val > r["ic"][1]:
                    await callback.answer("⚠️ Минимум не может быть больше максимума!", show_alert=True)
                    return
                if parts[3] == "max" and new_val < r["ic"][0]:
                    await callback.answer("⚠️ Максимум не может быть меньше минимума!", show_alert=True)
                    return
                
                r["ic"][idx] = new_val
                
                if not is_personal:
                    game["sg"] = current_settings
                    creator_id = list(game["p"].keys())[0]
                    update_player_settings(creator_id, current_settings)
                else:
                    update_player_settings(callback.from_user.id, current_settings)
                
                await callback.message.edit_text(
                    format_minmax_message("🧳", "Количество предметов", r["ic"][0], r["ic"][1], is_personal),
                    reply_markup=get_minmax_keyboard(round_idx, "ic", ITEM_COUNT_OPTIONS, r["ic"][0], r["ic"][1])
                )
                await callback.answer()
        
        elif parts[2] == "br":
            if len(parts) == 3:
                await callback.message.edit_text(
                    format_ratio_message(r["br"], is_personal),
                    reply_markup=get_ratio_keyboard(round_idx, r["br"])
                )
                await callback.answer()
            else:
                r["br"] = int(parts[3])
                
                if not is_personal:
                    game["sg"] = current_settings
                    creator_id = list(game["p"].keys())[0]
                    update_player_settings(creator_id, current_settings)
                else:
                    update_player_settings(callback.from_user.id, current_settings)
                
                await callback.message.edit_text(
                    format_ratio_message(r["br"], is_personal),
                    reply_markup=get_ratio_keyboard(round_idx, r["br"])
                )
                await callback.answer()
        
        elif parts[2] == "i":
            if len(parts) == 3:
                await callback.message.edit_text(
                    format_items_message(r["i"], is_personal),
                    reply_markup=get_items_keyboard(round_idx, r["i"])
                )
                await callback.answer()
            else:
                idx = int(parts[3])
                items_list = list(r["i"])
                items_list[idx] = '0' if items_list[idx] == '1' else '1'
                r["i"] = "".join(items_list)
                
                if not is_personal:
                    game["sg"] = current_settings
                    creator_id = list(game["p"].keys())[0]
                    update_player_settings(creator_id, current_settings)
                else:
                    update_player_settings(callback.from_user.id, current_settings)
                
                await callback.message.edit_text(
                    format_items_message(r["i"], is_personal),
                    reply_markup=get_items_keyboard(round_idx, r["i"])
                )
                await callback.answer()
