__version__ = (10, 0, 4)

# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/google/313/foggy_1f301.png
# meta desc: Chat administrator toolkit with everything you need and much more
# meta developer: @hikariatama

# scope: disable_onload_docs
# scope: inline
# scope: hikka_only
# requires: aiohttp

import re
import io
import abc
import time
import json
import imghdr
import logging
import asyncio
import functools
import websockets
import aiohttp


from telethon.tl.types import (
    Message,
    User,
    Channel,
    Chat,
    MessageMediaUnsupported,
    MessageEntitySpoiler,
    DocumentAttributeAnimated,
    UserStatusOnline,
    ChatBannedRights,
    ChannelParticipantCreator,
    ChatAdminRights,
)

from types import FunctionType
from typing import Union, List
from aiogram.types import CallbackQuery
from .. import loader, utils

from telethon.errors import UserAdminInvalidError, ChatAdminRequiredError

from telethon.tl.functions.channels import (
    EditBannedRequest,
    GetParticipantRequest,
    InviteToChannelRequest,
    EditAdminRequest,
    GetFullChannelRequest,
)

from math import ceil
import requests

try:
    from PIL import ImageFont, Image, ImageDraw
except ImportError:
    PIL_AVAILABLE = False
else:
    font = requests.get("https://github.com/hikariatama/assets/raw/master/EversonMono.ttf").content  # fmt: skip
    PIL_AVAILABLE = True


logger = logging.getLogger(__name__)

version = f"v{__version__[0]}.{__version__[1]}.{__version__[2]}alpha"
ver = f"<u>HikariChat {version}</u>"

FLOOD_TIMEOUT = 0.8
FLOOD_TRESHOLD = 4


def get_link(user: User or Channel) -> str:
    """Get link to object (User or Channel)"""
    return (
        f"tg://user?id={user.id}"
        if isinstance(user, User)
        else (
            f"tg://resolve?domain={user.username}"
            if getattr(user, "username", None)
            else ""
        )
    )


PROTECTS = {
    "antinsfw": "🍓 AntiNSFW",
    "antiarab": "🐻 AntiArab",
    "antitagall": "🐵 AntiTagAll",
    "antihelp": "🐺 AntiHelp",
    "antiflood": "⏱ AntiFlood",
    "antichannel": "📯 AntiChannel",
    "antispoiler": "🪙 AntiSpoiler",
    "report": "📣 Report",
    "antiexplicit": "😒 AntiExplicit",
    "antiraid": "🐶 AntiRaid",
    "antiservice": "⚙️ AntiService",
    "antigif": "🎑 AntiGIF",
    "antizalgo": "🌀 AntiZALGO",
    "antistick": "🎨 AntiStick",
    "banninja": "🥷 BanNinja",
    "welcome": "👋 Welcome",
    "antilagsticks": "⚰️ AntiLagSticks",
}


API_FEATURES = {
    "clrallwarns",
    "clrwarns",
    "delwarn",
    "dwarn",
    "fadd",
    "fban",
    "fclean",
    "fdef",
    "fdeflist",
    "fdemote",
    "feds",
    "fed",
    "fmute",
    "fnotes",
    "fpromote",
    "frename",
    "frm",
    "fsave",
    "fstop",
    "funban",
    "funmute",
    "newfed",
    "pchat",
    "protects",
    "rmfed",
    "warn",
    "warns",
    "welcome",
    "banninja",
    "antistick",
    "antizalgo",
    "antiarab",
    "antihelp",
    "antitagall",
    "antiraid",
    "antichannel",
    "antispoiler",
    "antigif",
    "antinsfw",
    "antiflood",
    "report",
    "antiexplicit",
    "antiservice",
    "antilagsticks",
}


def fit(line, max_size):
    if len(line) >= max_size:
        return line

    offsets_sum = max_size - len(line)

    return f"{' ' * ceil(offsets_sum / 2 - 1)}{line}{' ' * int(offsets_sum / 2 - 1)}"


def gen_table(t: List[List[str]]) -> bytes:
    table = ""
    header = t[0]
    rows_sizes = [len(i) + 2 for i in header]
    for row in t[1:]:
        rows_sizes = [max(len(j) + 2, rows_sizes[i]) for i, j in enumerate(row)]

    rows_lines = ["━" * i for i in rows_sizes]

    table += f"┏{('┯'.join(rows_lines))}┓\n"

    for line in t:
        table += f"┃⁣⁣ {' ┃⁣⁣ '.join([fit(row, rows_sizes[k]) for k, row in enumerate(line)])} ┃⁣⁣\n"
        table += "┠"

        for row in rows_sizes:
            table += f"{'─' * row}┼"

        table = table[:-1] + "┫\n"

    return "\n".join(table.splitlines()[:-1]) + "\n" + f"┗{('┷'.join(rows_lines))}┛\n"


def render_table(t: List[List[str]]) -> bytes:
    table = gen_table(t)

    fnt = ImageFont.truetype(io.BytesIO(font), 20, encoding="utf-8")

    def get_t_size(text, fnt):
        if "\n" not in text:
            return fnt.getsize(text)

        w, h = 0, 0

        for line in text.split("\n"):
            line_size = fnt.getsize(line)
            if line_size[0] > w:
                w = line_size[0]

            h += line_size[1]

        w += 10
        h += 10
        return (w, h)

    t_size = get_t_size(table, fnt)
    img = Image.new("RGB", t_size, (30, 30, 30))

    d = ImageDraw.Draw(img)
    d.text((5, 5), table, font=fnt, fill=(200, 200, 200))

    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format="PNG")
    imgByteArr = imgByteArr.getvalue()

    return imgByteArr


def get_first_name(user: User or Channel) -> str:
    """Returns first name of user or channel title"""
    return utils.escape_html(
        user.first_name if isinstance(user, User) else user.title
    ).strip()


def get_full_name(user: User or Channel) -> str:
    return utils.escape_html(
        user.title
        if isinstance(user, Channel)
        else (
            f"{user.first_name} "
            + (user.last_name if getattr(user, "last_name", False) else "")
        )
    ).strip()


async def get_message_link(message: Message, chat: Chat or Channel = None) -> str:
    if not chat:
        chat = await message.get_chat()

    return (
        f"https://t.me/{chat.username}/{message.id}"
        if getattr(chat, "username", False)
        else f"https://t.me/c/{chat.id}/{message.id}"
    )


BANNED_RIGHTS = {
    "view_messages": False,
    "send_messages": False,
    "send_media": False,
    "send_stickers": False,
    "send_gifs": False,
    "send_games": False,
    "send_inline": False,
    "send_polls": False,
    "change_info": False,
    "invite_users": False,
}


class HikariChatAPI:
    def __init__(self):
        pass

    async def init(
        self,
        client: "TelegramClient",  # noqa: F821
        db: "Database",  # noqa: F821
        module: "HikariChatMod",  # noqa: F821
    ):
        """Entry point"""
        self._client = client
        self._me = (await client.get_me()).id
        self._db = db
        self.module = module
        self._bot = "@hikka_userbot"

        self._queue = []
        self.feds = {}
        self.chats = {}
        self.variables = {}
        self.init_done = asyncio.Event()
        self._show_warning = True
        self._connected = False
        self._inited = False

        if not self._db.get("HikkaDL", "token"):
            await self._get_token()

        self._task = asyncio.ensure_future(self._connect())
        await self.init_done.wait()

    async def _wss(self):
        async with websockets.connect(
            f"wss://hikarichat.hikariatama.ru/ws/{self._db.get('HikkaDL', 'token')}"
        ) as wss:
            init = json.loads(await wss.recv())

            logger.debug(f"HikariChat connection debug info {init}")

            if init["event"] == "startup":
                self.variables = init["variables"]
            elif init["event"] == "license_violation":
                self.init_done.set()
                await wss.close()
                return

            self.init_done.set()

            logger.debug("HikariChat connected")
            self._show_warning = True
            self._connected = True
            self._inited = True

            while True:
                ans = json.loads(await wss.recv())

                if ans["event"] == "update_info":
                    self.chats = ans["chats"]
                    self.feds = ans["feds"]

                    await wss.send(json.dumps({"ok": True, "queue": self._queue}))
                    self._queue = []
                    for chat in self.chats:
                        if str(chat) not in self.module._linked_channels:
                            channel = (
                                await self._client(GetFullChannelRequest(int(chat)))
                            ).full_chat.linked_chat_id
                            self.module._linked_channels[str(chat)] = channel or False

                if ans["event"] == "queue_status":
                    await self._client.edit_message(
                        ans["chat_id"],
                        ans["message_id"],
                        ans["text"],
                    )

    async def _connect(self):
        while True:
            try:
                await self._wss()
            except Exception:
                logger.debug("HikariChat disconnection traceback", exc_info=True)

                if not self._inited:
                    logger.warning("HikariChatLite is active, federative functions removed")  # fmt: skip
                    self.init_done.set()
                    self._task.cancel()
                    return

                self._connected = False
                if self._show_warning:
                    logger.debug("HikariChat disconnected, retry in 5 sec")
                    self._show_warning = False

            await asyncio.sleep(5)

    def request(self, payload: dict, message: Union[Message, None] = None):
        if isinstance(message, Message):
            payload = {
                **payload,
                **{
                    "chat_id": utils.get_chat_id(message),
                    "message_id": message.id,
                },
            }

        self._queue += [payload]

    def should_protect(self, chat_id: Union[str, int], protection: str) -> bool:
        return (
            str(chat_id) in self.chats
            and protection in self.chats[str(chat_id)]
            and str(self.chats[str(chat_id)][protection][1]) == str(self._me)
        )

    async def nsfw(self, photo: bytes) -> str:
        if not self._db.get("HikkaDL", "token"):
            logger.warning("Token is not sent, NSFW check forbidden")
            return "sfw"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                "POST",
                "https://hikarichat.hikariatama.ru/check_nsfw",
                headers={"Authorization": f"Bearer {self._db.get('HikkaDL', 'token')}"},
                data={"file": photo},
            ) as resp:
                r = await resp.text()

                try:
                    r = json.loads(r)
                except Exception:
                    logger.exception("Failed to check NSFW")
                    return "sfw"

                if "error" in r and "Rate limit" in r["error"]:
                    logger.warning("NSFW checker ratelimit exceeded")
                    return "sfw"

                if "success" not in r:
                    logger.error(f"API error {json.dumps(r, indent=4)}")
                    return "sfw"

                return r["verdict"]

    async def _get_token(self):
        async with self._client.conversation(self._bot) as conv:
            m = await conv.send_message("/token")
            r = await conv.get_response()
            token = r.raw_text
            await m.delete()
            await r.delete()

            if not token.startswith("kirito_") and not token.startswith("asuna_"):
                raise loader.LoadError("Can't get token")

            self._db.set("HikkaDL", "token", token)

        await self._client.delete_dialog(self._bot)


api = HikariChatAPI()


def reverse_dict(d: dict) -> dict:
    return {val: key for key, val in d.items()}


@loader.tds
class HikariChatMod(loader.Module):
    """
    Advanced chat admin toolkit
    """

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "ChatTools",
        "args": "🦊 <b>Аргументы неверны</b>",
        "no_reason": "Не указана",
        "antitagall_on": "🐵 <b>В этом чате теперь включена функция AntiTagAll\nДействие: {}</b>",
        "antitagall_off": "🐵 <b>AntiTagAll теперь отключен в этом чате</b>",
        "antiarab_on": "🐻 <b>АнтиАраб теперь включен в этом чате\nДействие: {}</b>",
        "antiarab_off": "🐻 <b>АнтиАраб теперь отключен в этом чате</b>",
        "antilagsticks_on": "🚫 <b>В этом чате теперь включена защита от деструктивных стикеров</b>",
        "antilagsticks_off": "🚫 <b>Защита от деструктивных стикеров в этом чате теперь отключена</b>",
        "antizalgo_on": "🌀 <b>AntiZALGO \nДействие: {}</b>",
        "antizalgo_off": "🌀 <b>AntiZALGO теперь отключён в этом чате</b>",
        "antistick_on": "🎨 <b>AntiStick теперь включен в этом чате\nДействие: {}</b>",
        "antistick_off": "🎨 <b>AntiStick теперь отключён в этом чате</b>",
        "antihelp_on": "🐺 <b>AntiHelp теперь включен в этом чате</b>",
        "antihelp_off": "🐺 <b>AntiHelp теперь отключён в этом чате</b>",
        "antiraid_on": "🐶 <b>AntiRaid теперь включен в этом чате\nДействие: {}</b>",
        "antiraid_off": "🐶 <b>AntiRaid теперь отключён в этом чате</b>",
        "antiraid": '🐶 <b>Включен АнтиРейд. I {} <a href="{}">{}</ a> в чате {}</b>',
        "antichannel_on": "📯 <b>AntiChannel теперь включен в этом чате</b>",
        "antichannel_off": "📯 <b>AntiChannel теперь отключён в этом чате</b>",
        "report_on": "📣 <b>Report теперь включен в этом чате</b>",
        "report_off": "📣 <b>Report теперь отключён в этом чате</b>",
        "antiflood_on": "⏱ <b>AntiFlood теперь включен в этом чате\nДействие: {}</b>",
        "antiflood_off": "⏱ <b>AntiFlood теперь отключён в этом чате</b>",
        "antispoiler_on": "🪙 <b>AntiSpoiler теперь включен в этом чате</b>",
        "antispoiler_off": "🪙 <b>AntiSpoiler теперь отключён в этом чате</b>",
        "antigif_on": "🎑 <b>AntiGIF теперь включен в этом чате</b>",
        "antigif_off": "🎑 <b>AntiGIF теперь отключён в этом чате</b>",
        "antiservice_on": "⚙️ <b>AntiService теперь включен в этом чате</b>",
        "antiservice_off": "⚙️ <b>AntiService теперь отключён в этом чате</b>",
        "banninja_on": "🥷 <b>BanNinja теперь включен в этом чате</b>",
        "banninja_off": "🥷 <b>BanNinja теперь отключён в этом чате</b>",
        "antiexplicit_on": "😒 <b>AntiExplicit теперь включен в этом чате\nДействие: {}</b>",
        "antiexplicit_off": "😒 <b>AntiExplicit теперь отключён в этом чате</b>",
        "antinsfw_on": "🍓 <b>AntiNSFW теперь включен в этом чате\nДействие: {}</b>",
        "antinsfw_off": "🍓 <b>AntiNSFW теперь отключён в этом чате</b>",
        "arabic_nickname": '🐻 <b>Похоже, <a href="{}">{}</ a> является арабским.\n👊 Действие: I {}</b>',
        "zalgo": '🌀 <b>Похоже, <a href="{}">{}</ у a> есть ЗАЛГО в его нике.\n👊 Действие: I {}</b>',
        "stick": '🎨 <b>Похоже, <a href="{}">{}</ a> наводняет стикеры.\n👊 Действие: I {}</b>',
        "explicit": '😒 <b>Похоже, <a href="{}">{}</ a> отправлено явное содержимое.\n👊 Действие: I {}</b>',
        "destructive_stick": '🚫 <b>Похоже, <a href="{}">{}</ a> отправил деструктивную наклейку.\n👊 Действие: I {}</b>',
        "nsfw_content": '🍓 <b>Похоже, <a href="{}">{}</ a> отправлено содержимое NSFW.\n👊 Действие: I {}</b>',
        "flood": '⏱ <b>Похоже, <a href="{}">{}</ a> - это наводнение.\n👊 Действие: I {}</b>',
        "tagall": '🐵 <b>Похоже, <a href="{}">{}</ a> используется TagAll.\n👊 Действие: I {}</b>',
        "sex_datings": '🔞 <b><a href="{}">{}</ a> является подозрительным 🧐\n👊 Действие: I {}</b>',
        "fwarn": '👮‍♂️💼 <b><a href="{}">{}</a></b> получил {}/{} федеральное предупреждение\nПрчина: <b>{}</b>\n\n{}',
        "no_fed_warns": "👮‍♂️ <b>У этой федерации пока нет предупреждений</b>",
        "no_warns": '👮‍♂️ <b><a href="{}">{}</a> еще не получил никаких предупреждений</b>',
        "warns": '👮‍♂️ <b><a href="{}">{}</a> имеет {}/{} предупреждений</b>\n<i>{}</i>',
        "warns_adm_fed": "👮‍♂️ <b>Предупреждает в этой федерации</b>:\n",
        "dwarn_fed": '👮‍♂️ <b>Простил последнее федеративное предупреждение о <a href="tg://user?id={}">{}</a></b>',
        "clrwarns_fed": '👮‍♂️ <b>Простил все федеративные предупреждения о <a href="tg://user?id={}">{}</a></b>',
        "warns_limit": '👮‍♂️ <b><a href="{}">{}</a> достиг предела предупреждений.\nДействие: I {}</b>',
        "welcome": "👋 <b><Теперь я буду приветствовать людей в этом чате</b>\n{}",
        "unwelcome": "👋 <b>Теперь я не буду здороваться с людьми в этом чате</b>",
        "chat404": "🔓 <b>Я пока не защищаю этот чат.</b>\n",
        "protections": (
            "<b>🐻 <code>.AntiArab</code> - Запрещает спамить арабам\n"
            "<b>🐺 <code>.AntiHelp</code> - Удаляет частые команды пользовательского бота\n"
            "<b>🐵 <code>.AntiTagAll</code> - Ограничивает пометку всех участников\n"
            "<b>👋 <code>.Welcome</code> - Приветствует новых участников\n"
            "<b>🐶 <code>.AntiRaid</code> - Запрещает всем новым участникам\n"
            "<b>📯 <code>.AntiChannel</code> - Ограничивает запись от имени каналов\n"
            "<b>🪙 <code>.AntiSpoiler</code> - Ограничивает спойлеры\n"
            "<b>🎑 <code>.AntiGIF</code> - Ограничивает GIF-файлы\n"
            "<b>🍓 <code>.AntiNSFW</code> - Ограничивает фотографии и стикеры NSFW\n"
            "<b>⏱ <code>.AntiFlood</code> - Предотвращает затопление\n"
            "<b>😒 <code>.AntiExplicit</code> - Ограничивает явный контент\n"
            "<b>⚙️ <code>.AntiService</code> - Удаляет служебные сообщения\n"
            "<b>🌀 <code>.AntiZALGO</code> - Штраф для пользователей с именем ZALGO в нике\n"
            "<b>🎨 <code>.AntiStick</code> - Предотвращает затопление стикеров\n"
            "<b>🥷 <code>.BanNinja</code> - Автоматическая версия антирейда\n"
            "<b>⚰️ <code>.AntiLagSticks</code> - Запрещает запаздывающие стикеры\n"
            "<b>👾 Admin: </b><code>.ban</code> <code>.kick</code> <code>.mute</code>\n"
            "<code>.unban</code> <code>.unmute</code> <b>- Инструменты администрирования</b>\n"
            "<b>👮‍♂️ Warns:</b> <code>.warn</code> <code>.warns</code>\n"
            "<code>.dwarn</code> <code>.clrwarns</code> <b>- Система предупреждения</b>\n"
            "<b>💼 Federations:</b> <code>.fadd</code> <code>.frm</code> <code>.newfed</code>\n"
            "<code>.namefed</code> <code>.fban</code> <code>.rmfed</code> <code>.feds</code>\n"
            "<code>.fpromote</code> <code>.fdemote</code>\n"
            "<code>.fdef</code> <code>.fdeflist</code> <b>- Управление несколькими чатами</b>\n"
            "<b>🗒 Notes:</b> <code>.fsave</code> <code>.fstop</code> <code>.fnotes</code> <b>- Федеративные ноты</b>"
        ),
        "not_admin": "🤷‍♂️ <b>Я здесь не администратор или у меня недостаточно прав</b>",
        "mute": '🔇 <b><a href="{}">{}</a> в муте {}. Причина: </b><i>{}</i>\n\n{}',
        "mute_log": '🔇 <b><a href="{}">{}</a> в муте {} в <a href="{}">{}</ а>. Причина: </b><i>{}</i>\n\n{}',
        "запрет": '🔒 <b><a href="{}">{}</ a> запрещен {}. Причина: </b><i>{}</i>\n\n{}',
        "ban_log": '🔒 <b><a href="{}">{}</ a> запрещен {} в <a href="{}">{}</a>. Причина: </b><i>{}</i>\n\n{}',
        "kick": '🚪 <b><a href="{}">{}</ a> пнул ногой. Причина: </b><i>{}</i>\n\n{}',
        "kick_log": '🚪 <b><a href="{}">{}</ a> введен в действие <a href="{}">{}</a>. Причина: </b><i>{}</i>\n\n{}',
        "unmuted": '🔊 <b><a href="{}">{}</ a> теперь без мута</b>',
        "unmuted_log": '🔊 <b><a href="{}">{}</ a> отключен в <a href="{}">{}</ a></b>',
        "unban": '🧙♂️ <b><a href="{}">{}</a> unbanned</b>',
        "unban_log": '🧙♂️ <b><a href="{}">{}</ a> не привязан к <a href="{}">{}</ a></b>',
        "defense": '🛡 <b>Щит для <a href="{}">{}</ a> теперь {}</b>',
        "no_defense": "🛡 <b>Список федеральной защиты пуст</b>",
        "defense_list": "🛡 <b>Список федеративной обороны:</b>\n{}",
        "fadded": "💼 <b>Текущий чат добавлен в федерацию "{}"</b>",
        "newfed": "💼 <b>Созданная федерация "{}"</b>",
        "rmfed": "💼 <b>Удалена федерация "{}"</b>",
        "fed404": "💼 <b>Федерация не найдена</b>",
        "frem": "💼 <b>Текущий чат удален из федерации "{}"</b>',
        "f404": '💼 <b>Текущий чат не входит в федерацию "{}"</b>',
        "fexists": '💼 <b>Текущий чат уже находится в федерации "{}"</b>',
        "fedexists": "💼 <b>Федерация существует</b>",
        "joinfed": "💼 <b>Федерация присоединилась</b>",
        "namedfed": "💼 <b>Федерация переименована в {}</b>",
        "nofed": "💼 <b>Текущий чат не находится ни в одной федерации</b>",
        "fban": '💼 <b><a href="{}">{}</ a> запрещен в федерации {} {}\n Причина: </b><i>{}</i>\n\n{}',
        "fmute": '💼 <b><a href="{}">{}</ a> отключено в федерации {} {}\n Причина: </b><i>{}</i>\n\n{}',
        "funban": '💼 <b><a href="{}">{}</ a> незарегистрированный в федерации </b><i>{}</i>',
        "funmute": '💼 <b><a href="{}">{}</ a> отключено в федерации </b><i>{}</i>',
        "feds_header": "💼 <b>Федерации:</b>\n\n",
        "fed": (
            '💼 <b>Федерация "{}" информация:</b>\n'
            "🔰 <b>Чаты:</b>\n"
            "<b>{}</b>\n"
            "🔰 <b>Каналы:</b>\n"
            "<b>{}</b>\n"
            "🔰 <b>Администраторы:</b>\n"
            "<b>{}</b>\n"
            "🔰 <b>Предупреждений: {}</b>\n"
        ),
        "no_fed": "💼 <b>Этот чат не входит ни в одну федерацию</b>",
        "fpromoted": '💼 <b><a href="{}">{}</ a> повышен в федерации {}</b>',
        "fdemoted": '💼 <b><a href="{}">{}</ a> понижен в должности в федерации {}</b>',
        "api_error": "🚫 <b>api.hikariatama.ru Ошибка!</b>\n<код>{}</code>",
        "fsave_args": "💼 <b>Использование: .fsave короткое имя &lt;ответ &gt;</b>",
        "fstop_args": "💼 <b>Использование: .fstop короткое имя</b>",
        "fsave": "💼 <b>Федеративная записка </b><код>{}</code><b> сохранено!</b>",
        "fstop": "💼 <b>Федеративная записка </b><код>{}</code><b> удалено!</b>",
        "fnotes": "💼 <b>Федеральные примечания:</b>\n{}",
        "usage": "ℹ️ <b>Использование: .{} &lt;вкл/выкл&gt;</b>",
        "chat_only": "ℹ️ <b>Эта команда предназначена только для чатов</b>",
        "version": (
            "<b>🌊 {}</b>\n\n"
            "<b>😌 Автор: @hikariatama</b>\n"
            "<b>📥 Загружено с @hikarimods</b>\n"
            "<b>Статус: {}</b>"
        ),
        "error": "😵 <b>ChatTools Выдал ошибку</b>",
        "reported": '💼 <b><a href="{}">{}</a> сообщил об этом сообщении администраторам\nПричина: </b><i>{}</i>',
        "no_federations": "💼 <b>У вас нет активных федераций</b>",
        "clrallwarns_fed": "👮‍♂️ <b>Простил все федеративные предупреждения о федерации</b>",
        "cleaning": "🧹 <b>Ищу удаленные учетные записи...</b>",
        "deleted": "🧹 <b>Удалено {} Удаленные учетные записи</b>",
        "fcleaning": "🧹 <b>Ищу удаленные учетные записи в федерации...</b>",
        "btn_unban": "🔓 Разбанить (ADM)",
        "btn_unmute": "🔈 Снять мут (ADM)",
        "btn_unwarn": "♻️ Снять предупреждение (ADM)",
        "inline_unbanned": '🔓 Пользователю <b><a href="{}">{}</a> был снят бан. Бан снял <a href="{}">{}</a></b>',
        "inline_unmuted": '🔈 Пользователю <b><a href="{}">{}</a> был снят мут. Мут снял <a href="{}">{}</a></b>',
        "inline_unwarned": '♻️ <b>Пользователю <a href="{}">{}</a> было снято посление предупреждение. Снял <a href="{}">{}</a></b>',
        "inline_funbanned": '🔓 <b><a href="{}">{}</a> был снят бан в федерации. Снял <a href="{}">{}</a></b>',
        "inline_funmuted": '🔈 <b><a href="{}">{}</a> был снят мут в федерации. Снял<a href="{}">{}</a></b>',
        "btn_funmute": "🔈 Снять мут в фед. (ADM)",
        "btn_funban": "🔓 Снять бан в фед. (ADM)",
        "btn_mute": "🙊 Мут",
        "btn_ban": "🔒 Бан",
        "btn_fban": "💼 Бан в фед.",
        "btn_del": "🗑 Удалить",
        "inline_fbanned": '💼 <b><a href="{}">{}</a> banned in federation by <a href="{}">{}</a></b>',
        "inline_muted": '🙊 <b><a href="{}">{}</a> получил(а) мут. Мут дал <a href="{}">{}</a></b>',
        "inline_banned": '🔒 <b><a href="{}">{}</a> получил(а) бан. Бан дал <a href="{}">{}</a></b>',
        "inline_deleted": '🗑 <b> <a href="{}">{}</a> удалил</b>',
        "sync": "🔄 <b>Синхронизация чатов и федералов с сервером в принудительном режиме...</b>",
        "sync_complete": "😌 <b>Успешно синхронизирован</b>",
        "rename_noargs": "🚫 <b>Укажите новое имя федерации</b>",
        "rename_success": '😇 <b>Федерация переименована в "</b><code>{}</code><b>"</b>',
        "suffix_removed": "📼 <b>Суффикс наказания удален</b>",
        "suffix_updated": "📼 <b>Сохранен новый суффикс наказания</b>\n\n{}",
        "processing_myrights": "😌 <b>Обработка чатов</b>",
        "logchat_removed": "📲 <b>Вход в чат отключен</b>",
        "logchat_invalid": "🚫 <b>Войти в чат недопустимо</b>",
        "logchat_set": "📲 <b>Журнал чата обновлен до </b><code>{}</code>",
        "clnraid_args": "🥷 <b>Пример использования: </b><code>.clnraid 10</code>",
        "clnraid_admin": "🥷 <b>Ошибка произошла при продвижении cleaner. Пожалуйста, убедитесь, что у вас достаточно прав в чате</b>",
        "clnraid_started": "🥷 <b>RaidCleaner находится в процессе разработки... Найдено {} пользователей для пинка...</b>",
        "clnraid_confirm": "🥷 <b>Пожалуйста, подтвердите, что вы хотите запустить RaidCleaner для пользователей {}</b>",
        "clnraid_yes": "🥷 Старт",
        "clnraid_cancel": "🚫 Отмена",
        "clnraid_stop": "🚨 Стоп",
        "clnraid_complete": "🥷 <b>RaidCleaner завершен! Удалено: {} пользователь(-ы)</b>",
        "clnraid_cancelled": "🥷 <b>RaidCleaner отменен. Удалено: {} пользователь(-ы)</b>",
        "confirm_rmfed": (
            "⚠️ <b>Предупреждение! Эта операция не может быть отменена! Вы уверены,"
            "вы хотите удалить федерацию </b><code>{}</code><b>?</b>"
        ),
        "confirm_rmfed_btn": "🗑 Удалить",
        "decline_rmfed_btn": "🚫 Отмена",
        "pil_unavailable": "🚫 <b>Пакет подушек недоступен</b>",
        "action": "<action>",
        "configure": "Конфигурировать",
        "toggle": "Тумблер",
        "no_protects": "🚫 <b>В этом чате нет активных средств защиты, которые можно было бы показать</b>",
        "from_where": "🚫 <b>Ответить на сообщение для удаления из</b>",
    }

    strings_ru = {
        "from_where": "🚫 <b>Ответь на сообщение, начиная с которого надо удалить.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "silent",
            False,
            lambda: "Do not notify about protections actions",
            "join_ratelimit",
            15,
            lambda: "How many users per minute need to join until ban starts",
        )

    async def on_unload(self):
        self.api._task.cancel()

    def lookup(self, modname: str):
        return next(
            (
                mod
                for mod in self.allmodules.modules
                if mod.name.lower() == modname.lower()
            ),
            False,
        )

    def save_join_ratelimit(self):
        """
        Saves BanNinja ratelimit to fs
        """
        with open("join_ratelimit.json", "w") as f:
            f.write(json.dumps(self._join_ratelimit))

    def save_flood_cache(self):
        """
        Saves AntiFlood ratelimit to fs
        """
        with open("flood_cache.json", "w") as f:
            f.write(json.dumps(self.flood_cache))

    async def check_admin(
        self,
        chat_id: Union[Chat, Channel, int],
        user_id: Union[User, int],
    ) -> bool:
        """
        Checks if user is admin in target chat
        """
        try:
            return (await self._client.get_permissions(chat_id, user_id)).is_admin
            # We could've ignored only ValueError to check
            # entity for validity, but there are many errors
            # possible to occur, so we ignore all of them, bc
            # actually we don't give a fuck about 'em
        except Exception:
            return (
                user_id in self._client.dispatcher.security._owner
                or user_id in self._client.dispatcher.security._sudo
            )

    def chat_command(func) -> FunctionType:
        """
        Decorator to allow execution of certain commands in chat only
        """

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) < 2 or not isinstance(args[1], Message):
                return await func(*args, **kwargs)

            if args[1].is_private:
                await utils.answer(args[1], args[0].strings("chat_only"))
                return

            return await func(*args, **kwargs)

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    def error_handler(func) -> FunctionType:
        """
        Decorator to handle functions' errors and send reports to @hikariatama
        """

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception("Exception caught in HikariChat")

                if func.__name__.startswith("p__"):
                    return

                # await api.report_error(traceback.format_exc())
                if func.__name__ == "watcher":
                    return

                try:
                    await utils.answer(args[1], args[0].strings("error"))
                except Exception:
                    pass

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    async def get_config(self, chat: Union[str, int]) -> tuple:
        info = self.api.chats[str(chat)]
        cinfo = await self._client.get_entity(int(chat))

        answer_message = (
            f"🌊 <b>HikariChat protection</b>\n<b>{get_full_name(cinfo)}</b>\n\n"
        )

        btns = []
        for protection, style in PROTECTS.items():
            answer_message += (
                f"    <b>{style}</b>: {info[protection][0]}\n"
                if protection in info
                else ""
            )
            style = style if protection in info else style[2:]
            btns += [
                {
                    "text": style,
                    "callback": self._change_protection_state,
                    "args": (chat, protection),
                }
            ]

        fed = None
        for federation, info in self.api.feds.items():
            if str(chat) in info["chats"]:
                fed = info

        answer_message += f"\n💼 <b>{fed['name']}</b>" if fed else ""

        btns = utils.chunks(btns, 3) + [[{"text": "❌ Close", "callback": self._inline_close}]]

        return {"text": answer_message, "reply_markup": btns}

    async def _inline_config(self, call: CallbackQuery, chat: Union[str, int]):
        await call.edit(**(await self.get_config(chat)))

    async def _inline_close(self, call: CallbackQuery):
        await call.delete()

    async def _change_protection_state(
        self,
        call: CallbackQuery,
        chat: Union[str, int],
        protection: str,
        state: Union[str, None] = None,
    ):
        if protection == "welcome":
            await call.answer("Используйте .welcome, чтобы настроить этот параметр!", show_alert=True)
            return

        if protection in self.api.variables["argumented_protects"]:
            if state is None:
                cinfo = await self._client.get_entity(int(chat))
                markup = utils.chunks(
                    [
                        {
                            "text": "🔒 Ban",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "ban"),
                        },
                        {
                            "text": "🔊 Mute",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "mute"),
                        },
                        {
                            "text": "🤕 Warn",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "warn"),
                        },
                        {
                            "text": "🚪 Kick",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "kick"),
                        },
                        {
                            "text": "😶‍🌫️ Delmsg",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "delmsg"),
                        },
                        {
                            "text": "🚫 Off",
                            "callback": self._change_protection_state,
                            "args": (chat, protection, "off"),
                        },
                    ],
                    3,
                ) + [
                    [
                        {
                            "text": "🔙 Back",
                            "callback": self._inline_config,
                            "args": (chat,),
                        }
                    ]
                ]
                current_state = (
                    "off"
                    if protection not in self.api.chats[str(chat)]
                    else self.api.chats[str(chat)][protection][0]
                )
                await call.edit(
                    f"🌁 <b>{get_full_name(cinfo)}</b>: <code>{PROTECTS[protection]}</code> (now: {current_state})",
                    reply_markup=markup,
                )
            else:
                self.api.request(
                    {
                        "action": "update protections",
                        "args": {
                            "chat": chat,
                            "protection": protection,
                            "state": state,
                        },
                    }
                )
                await call.answer("Сохраненное значение конфигурации")
                if state != "off":
                    self.api.chats[str(chat)][protection] = [state, str(self._me)]
                else:
                    del self.api.chats[str(chat)][protection]

                await self._inline_config(call, chat)
        else:
            current_state = protection in self.api.chats[str(chat)]
            self.api.request(
                {
                    "action": "update protections",
                    "args": {
                        "chat": chat,
                        "protection": protection,
                        "state": "on" if not current_state else "off",
                    },
                }
            )
            await call.answer(
                f"{PROTECTS[protection]} -> {'on' if not current_state else 'off'}"
            )
            if current_state:
                del self.api.chats[str(chat)][protection]
            else:
                self.api.chats[str(chat)][protection] = ["on", str(self._me)]
            await self._inline_config(call, chat)

    @error_handler
    async def protect(self, message: Message, protection: str):
        """
        Protection toggle handler
        """
        args = utils.get_args_raw(message)
        chat = utils.get_chat_id(message)
        if protection in self.api.variables["argumented_protects"]:
            if args not in self.api.variables["protect_actions"] or args == "off":
                args = "off"
                await utils.answer(message, self.strings(f"{protection}_off"))
            else:
                await utils.answer(
                    message,
                    self.strings(f"{protection}_on").format(args),
                )
        elif args == "on":
            await utils.answer(message, self.strings(f"{protection}_on"))
        elif args == "off":
            await utils.answer(
                message,
                self.strings(f"{protection}_off").format(args),
            )
        else:
            await utils.answer(message, self.strings("usage").format(protection))
            return

        self.api.request(
            {
                "action": "update protections",
                "args": {"protection": protection, "state": args, "chat": chat},
            },
            message,
        )

    def protection_template(self, protection: str) -> FunctionType:
        """
        Template for protection toggler
        For internal use only
        """
        comments = self.api.variables["named_protects"]
        func_name = f"{protection}cmd"
        func = functools.partial(self.protect, protection=protection)
        func.__module__ = self.__module__
        func.__name__ = func_name
        func.__self__ = self

        args = (
            self.strings("action")
            if protection in self.api.variables["argumented_protects"]
            else "<on/off>"
        )

        action = (
            self.strings("configure")
            if protection in self.api.variables["argumented_protects"]
            else self.strings("toggle")
        )

        func.__doc__ = f"{args} - {action} {comments[protection]}"
        return func

    @staticmethod
    def convert_time(t: str) -> int:
        """
        Tries to export time from text
        """
        try:
            if not str(t)[:-1].isdigit():
                return 0

            if "d" in str(t):
                t = int(t[:-1]) * 60 * 60 * 24

            if "h" in str(t):
                t = int(t[:-1]) * 60 * 60

            if "m" in str(t):
                t = int(t[:-1]) * 60

            if "s" in str(t):
                t = int(t[:-1])

            t = int(re.sub(r"[^0-9]", "", str(t)))
        except ValueError:
            return 0

        return t

    async def ban(
        self,
        chat: Union[Chat, int],
        user: Union[User, Channel, int],
        period: int = 0,
        reason: str = None,
        message: Union[None, Message] = None,
        silent: bool = False,
    ):
        """Ban user in chat"""
        if str(user).isdigit():
            user = int(user)

        if reason is None:
            reason = self.strings("no_reason")

        await self._client.edit_permissions(
            chat,
            user,
            until_date=(time.time() + period) if period else 0,
            **BANNED_RIGHTS,
        )

        if silent:
            return

        msg = self.strings("ban").format(
            get_link(user),
            get_full_name(user),
            f"for {period // 60} min(-s)" if period else "forever",
            reason,
            self.get("punish_suffix", ""),
        )

        if self._is_inline:
            if self.get("logchat"):
                if not isinstance(chat, (Chat, Channel)):
                    chat = await self._client.get_entity(chat)

                await self.inline.form(
                    message=self.get("logchat"),
                    text=self.strings("ban_log").format(
                        get_link(user),
                        get_full_name(user),
                        f"for {period // 60} min(-s)" if period else "forever",
                        get_link(chat),
                        get_full_name(chat),
                        reason,
                        "",
                    ),
                    reply_markup=[
                        [
                            {
                                "text": self.strings("btn_unban"),
                                "data": f"ub/{chat.id if isinstance(chat, (Chat, Channel)) else chat}/{user.id}",
                            }
                        ]
                    ],
                )

                if isinstance(message, Message):
                    await utils.answer(message, msg)
                else:
                    await self._client.send_message(chat.id, msg)
            else:
                await self.inline.form(
                    message=message
                    if isinstance(message, Message)
                    else getattr(chat, "id", chat),
                    text=msg,
                    reply_markup=[
                        [
                            {
                                "text": self.strings("btn_unban"),
                                "data": f"ub/{chat.id if isinstance(chat, (Chat, Channel)) else chat}/{user.id}",
                            }
                        ]
                    ],
                )
        else:
            await (utils.answer if message else self._client.send_message)(
                message or chat.id, msg
            )

    async def mute(
        self,
        chat: Union[Chat, int],
        user: Union[User, Channel, int],
        period: int = 0,
        reason: str = None,
        message: Union[None, Message] = None,
        silent: bool = False,
    ):
        """Mute user in chat"""
        if str(user).isdigit():
            user = int(user)

        if reason is None:
            reason = self.strings("no_reason")

        await self._client.edit_permissions(
            chat,
            user,
            until_date=time.time() + period,
            send_messages=False,
        )

        if silent:
            return

        msg = self.strings("mute").format(
            get_link(user),
            get_full_name(user),
            f"for {period // 60} min(-s)" if period else "forever",
            reason,
            self.get("punish_suffix", ""),
        )

        if self._is_inline:
            if self.get("logchat"):
                if not isinstance(chat, (Chat, Channel)):
                    chat = await self._client.get_entity(chat)

                await self.inline.form(
                    message=self.get("logchat"),
                    text=self.strings("mute_log").format(
                        get_link(user),
                        get_full_name(user),
                        f"for {period // 60} min(-s)" if period else "forever",
                        get_link(chat),
                        get_full_name(chat),
                        reason,
                        "",
                    ),
                    reply_markup=[
                        [
                            {
                                "text": self.strings("btn_unmute"),
                                "data": f"um/{chat.id if isinstance(chat, (Chat, Channel)) else chat}/{user.id}",
                            }
                        ]
                    ],
                )

                if isinstance(message, Message):
                    await utils.answer(message, msg)
                else:
                    await self._client.send_message(chat.id, msg)
            else:
                await self.inline.form(
                    message=message
                    if isinstance(message, Message)
                    else getattr(chat, "id", chat),
                    text=msg,
                    reply_markup=[
                        [
                            {
                                "text": self.strings("btn_unmute"),
                                "data": f"um/{chat.id if isinstance(chat, (Chat, Channel)) else chat}/{user.id}",
                            }
                        ]
                    ],
                )
        else:
            await (utils.answer if message else self._client.send_message)(
                message or chat.id, msg
            )

    async def actions_callback_handler(self, call: CallbackQuery):
        """
        Handles unmute\\unban button clicks
        @allow: all
        """
        if not re.match(r"[fbmudw]{1,3}\/[-0-9]+\/[-#0-9]+", call.data):
            return

        action, chat, user = call.data.split("/")

        msg_id = None

        try:
            user, msg_id = user.split("#")
            msg_id = int(msg_id)
        except Exception:
            pass

        chat, user = int(chat), int(user)

        if not await self.check_admin(chat, call.from_user.id):
            await call.answer("You are not admin")
            return

        try:
            user = await self._client.get_entity(user)
        except Exception:
            await call.answer("Unable to resolve entity")
            return

        try:
            adm = await self._client.get_entity(call.from_user.id)
        except Exception:
            await call.answer("Unable to resolve admin entity")
            return

        p = (
            await self._client(GetParticipantRequest(chat, call.from_user.id))
        ).participant

        owner = isinstance(p, ChannelParticipantCreator)

        if action == "ub":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            await self._client.edit_permissions(
                chat,
                user,
                until_date=0,
                **{right: True for right in BANNED_RIGHTS.keys()},
            )
            msg = self.strings("inline_unbanned").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "um":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            await self._client.edit_permissions(
                chat, user, until_date=0, send_messages=True
            )
            msg = self.strings("inline_unmuted").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "dw":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            fed = await self.find_fed(chat)

            self.api.request(
                {
                    "action": "forgive user warn",
                    "args": {"uid": self.api.feds[fed]["uid"], "user": user.id},
                }
            )

            msg = self.strings("inline_unwarned").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )

            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "ufb":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            m = await self._client.send_message(chat, f"{self.get_prefix()}funban {user.id}")
            await self.funbancmd(m)
            await m.delete()
            msg = self.strings("inline_funbanned").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "ufm":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            m = await self._client.send_message(
                chat, f"{self.get_prefix()}funmute {user.id}"
            )
            await self.funmutecmd(m)
            await m.delete()
            msg = self.strings("inline_funmuted").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "fb":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            m = await self._client.send_message(chat, f"{self.get_prefix()}fban {user.id}")
            await self.fbancmd(m)
            await m.delete()
            msg = self.strings("inline_fbanned").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "m":
            if not owner and not p.admin_rights.ban_users:
                await call.answer("Not enough rights!")
                return

            await self.mute(chat, user, 0, silent=True)
            msg = self.strings("inline_muted").format(
                get_link(user),
                get_full_name(user),
                get_link(adm),
                get_full_name(adm),
            )
            try:
                await self.inline.bot.edit_message_text(
                    msg,
                    inline_message_id=call.inline_message_id,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception:
                await self._client.send_message(chat, msg)
        elif action == "d":
            if not owner and not p.admin_rights.delete_messages:
                await call.answer("Not enough rights!")
                return

            msg = self.strings("inline_deleted").format(
                get_link(adm),
                get_full_name(adm),
            )

            await self.inline.bot.edit_message_text(
                msg,
                inline_message_id=call.inline_message_id,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
        else:
            return

        if msg_id is not None:
            await self._client.delete_messages(chat, message_ids=[msg_id])

    async def args_parser(self, message: Message) -> tuple:
        """Get args from message"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply and not args:
            return (
                (await self._client.get_entity(reply.sender_id)),
                0,
                utils.escape_html(self.strings("no_reason")).strip(),
            )

        try:
            a = args.split()[0]
            if str(a).isdigit():
                a = int(a)
            user = (
                (await self._client.get_entity(reply.sender_id))
                if reply
                else (await self._client.get_entity(a))
            )
        except Exception:
            return False

        t = ([_ for _ in args.split() if self.convert_time(_)] or ["0"])[0]
        args = args.replace(t, "").replace("  ", " ")
        t = self.convert_time(t)

        if not reply:
            try:
                args = " ".join(args.split(" ")[1:])
            except Exception:
                pass

        if time.time() + t >= 2208978000:  # 01.01.2040 00:00:00
            t = 0

        return user, t, utils.escape_html(args or self.strings("no_reason")).strip()

    async def find_fed(self, message: Union[Message, int]) -> None or str:
        """Find if chat belongs to any federation"""
        return next(
            (
                federation
                for federation, info in self.api.feds.items()
                if str(
                    utils.get_chat_id(message)
                    if isinstance(message, Message)
                    else message
                )
                in list(map(str, info["chats"]))
            ),
            None,
        )

    @error_handler
    async def punish(
        self,
        chat_id: int,
        user: Union[int, Channel, User],
        violation: str,
        action: str,
        user_name: str,
    ):
        """
        Callback, called if the protection is triggered
        Queue is being used to prevent spammy behavior
        It is being processed in a loop `_punish_queue_handler`
        """
        self._punish_queue += [[chat_id, user, violation, action, user_name]]

    @error_handler
    async def purgecmd(self, message: Message):
        """[user(-s)] - Clean message history starting from replied one"""
        if not message.is_reply:
            await utils.answer(message, self.strings("from_where", message))
            return

        from_users = set()
        args = utils.get_args(message)

        for arg in args:
            try:
                entity = await message.client.get_entity(arg)

                if isinstance(entity, User):
                    from_users.add(entity.id)
            except ValueError:
                pass

        messages = []
        from_ids = set()

        async for msg in self._client.iter_messages(
            entity=message.peer_id,
            min_id=message.reply_to_msg_id - 1,
            reverse=True,
        ):
            if from_users and msg.sender_id not in from_users:
                continue

            messages += [msg.id]
            from_ids.add(msg.sender_id)

            if len(messages) >= 99:
                logger.debug(messages)
                await self._client.delete_messages(message.peer_id, messages)
                messages.clear()

        if messages:
            logger.debug(messages)
            await self._client.delete_messages(message.peer_id, messages)

    @loader.loop(interval=0.5, autostart=True)
    async def _punish_queue_handler(self):
        while self._punish_queue:
            chat_id, user, violation, action, user_name = self._punish_queue.pop()
            if str(chat_id) not in self._flood_fw_protection:
                self._flood_fw_protection[str(chat_id)] = {}

            if self._flood_fw_protection[str(chat_id)].get(str(user.id), 0) >= time.time():
                continue

            if action == "ban":
                comment = "banned him"
                await self.ban(chat_id, user, 0, violation)
            elif action == "fban":
                comment = "f-banned him"
                await self.fbancmd(
                    await self._client.send_message(
                        chat_id,
                        f"{self.get_prefix()}fban {user.id} {violation}",
                    )
                )
            elif action == "delmsg":
                continue
            elif action == "kick":
                comment = "kicked him"
                await self._client.kick_participant(chat_id, user)
            elif action == "mute":
                comment = "muted him for 1 hour"
                await self.mute(chat_id, user, 60 * 60, violation)
            elif action == "warn":
                comment = "warned him"
                warn_msg = await self._client.send_message(
                    chat_id, f".warn {user.id} {violation}"
                )
                await self.allmodules.commands["warn"](warn_msg)
                await warn_msg.delete()
            else:
                comment = "just chill 😶‍🌫️"

            if not self.config["silent"]:
                self._flood_fw_protection[str(chat_id)][str(user.id)] = round(time.time() + 10)
                await self._client.send_message(
                    chat_id,
                    self.strings(violation).format(
                        get_link(user),
                        user_name,
                        comment,
                    ),
                )

    @error_handler
    async def versioncm_(self, message: Message):
        """Get module info"""
        await utils.answer(
            message,
            self.strings("version").format(
                ver,
                "✅ Connected"
                if self.api._connected
                else ("🔁 Connecting..." if self.api._inited else "💔 Lite version"),
            ),
        )

    @error_handler
    @chat_command
    async def deletedcm_(self, message: Message):
        """Remove deleted accounts from chat"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        kicked = 0

        message = await utils.answer(message, self.strings("cleaning"))
        if not isinstance(message, Message):
            message = message[0]

        async for user in self._client.iter_participants(chat):
            if user.deleted:
                try:
                    await self._client.kick_participant(chat, user)
                    await self._client.edit_permissions(
                        chat,
                        user,
                        until_date=0,
                        **{right: True for right in BANNED_RIGHTS.keys()},
                    )
                    kicked += 1
                except Exception:
                    pass

        await utils.answer(message, self.strings("deleted").format(kicked))

    @error_handler
    @chat_command
    async def fcleancm_(self, message: Message):
        """Remove deleted accounts from federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        chats = self.api.feds[fed]["chats"]
        cleaned_in = []
        cleaned_in_c = []

        message = await utils.answer(message, self.strings("fcleaning"))

        if isinstance(message, list):
            message = message[0]

        overall = 0

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self._client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                kicked = 0
                async for user in self._client.iter_participants(chat):
                    if user.deleted:
                        try:
                            await self._client.kick_participant(chat, user)
                            await self._client.edit_permissions(
                                chat,
                                user,
                                until_date=0,
                                **{right: True for right in BANNED_RIGHTS.keys()},
                            )
                            kicked += 1
                        except Exception:
                            pass

                overall += kicked
                cleaned_in += [f'👥 <a href="{get_link(chat)}">{utils.escape_html(chat.title)}</a> - {kicked}']  # fmt: skip
            except UserAdminInvalidError:
                pass

            if str(c) in self._linked_channels:
                channel = await self._client.get_entity(self._linked_channels[str(c)])
                kicked = 0
                try:
                    async for user in self._client.iter_participants(
                        self._linked_channels[str(c)]
                    ):

                        if user.deleted:
                            try:
                                await self._client.kick_participant(
                                    self._linked_channels[str(c)],
                                    user,
                                )
                                await self._client.edit_permissions(
                                    self._linked_channels[str(c)],
                                    user,
                                    until_date=0,
                                    **{right: True for right in BANNED_RIGHTS.keys()},
                                )
                                kicked += 1
                            except Exception:
                                pass
                    # fmt: skip

                    overall += kicked
                    cleaned_in_c += [f'📣 <a href="{get_link(channel)}">{utils.escape_html(channel.title)}</a> - {kicked}']  # fmt: skip
                except ChatAdminRequiredError:
                    pass

        await utils.answer(
            message,
            self.strings("deleted").format(overall)
            + "\n\n<b>"
            + "\n".join(cleaned_in)
            + "</b>"
            + "\n\n<b>"
            + "\n".join(cleaned_in_c)
            + "</b>",
        )

    @error_handler
    @chat_command
    async def newfedcm_(self, message: Message):
        """<shortname> <name> - Create new federation"""
        args = utils.get_args_raw(message)
        if not args or args.count(" ") == 0:
            await utils.answer(message, self.strings("args"))
            return

        shortname, name = args.split(maxsplit=1)
        if shortname in self.api.feds:
            await utils.answer(message, self.strings("fedexists"))
            return

        self.api.request(
            {
                "action": "create federation",
                "args": {"shortname": shortname, "name": name},
            },
            message,
        )

        await utils.answer(message, self.strings("newfed").format(name))

    async def inline__confirm_rmfed(self, call: CallbackQuery, args: str):
        name = self.api.feds[args]["name"]

        self.api.request(
            {"action": "delete federation", "args": {"uid": self.api.feds[args]["uid"]}}
        )

        await call.edit(self.strings("rmfed").format(name))

    async def inline__close(self, call: CallbackQuery):
        await call.delete()

    @error_handler
    @chat_command
    async def rmfedcm_(self, message: Message):
        """<shortname> - Remove federation"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args"))
            return

        if args not in self.api.feds:
            await utils.answer(message, self.strings("fed404"))
            return

        await self.inline.form(
            self.strings("confirm_rmfed").format(
                utils.escape_html(self.api.feds[args]["name"])
            ),
            message=message,
            reply_markup=[
                [
                    {
                        "text": self.strings("confirm_rmfed_btn"),
                        "callback": self.inline__confirm_rmfed,
                        "args": (args,),
                    },
                    {
                        "text": self.strings("decline_rmfed_btn"),
                        "callback": self.inline__close,
                    },
                ]
            ],
        )

    @error_handler
    @chat_command
    async def fpromotecm_(self, message: Message):
        """<user> - Promote user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        if not reply and not args:
            await utils.answer(message, self.strings("args"))
            return

        user = reply.sender_id if reply else args
        try:
            try:
                if str(user).isdigit():
                    user = int(user)
                obj = await self._client.get_entity(user)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

            name = get_full_name(obj)
        except Exception:
            await utils.answer(message, self.strings("args"))
            return

        self.api.request(
            {
                "action": "promote user in federation",
                "args": {"uid": self.api.feds[fed]["uid"], "user": obj.id},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("fpromoted").format(
                get_link(obj),
                name,
                self.api.feds[fed]["name"],
            ),
        )

    @error_handler
    @chat_command
    async def fdemotecm_(self, message: Message):
        """<shortname> <reply|user> - Demote user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        if not reply and not args:
            await utils.answer(message, self.strings("args"))
            return

        user = reply.sender_id if reply else args
        try:
            try:
                if str(user).isdigit():
                    user = int(user)
                obj = await self._client.get_entity(user)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

            user = obj.id

            name = get_full_name(obj)
        except Exception:
            logger.exception("Parsing entity exception")
            name = "User"

        self.api.request(
            {
                "action": "demote user in federation",
                "args": {"uid": self.api.feds[fed]["uid"], "user": obj.id},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("fdemoted").format(
                user,
                name,
                self.api.feds[fed]["name"],
            ),
        )

    @error_handler
    @chat_command
    async def faddcm_(self, message: Message):
        """<fed name> - Add chat to federation"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args"))
            return

        if args not in self.api.feds:
            await utils.answer(message, self.strings("fed404"))
            return

        chat = utils.get_chat_id(message)

        self.api.request(
            {
                "action": "add chat to federation",
                "args": {"uid": self.api.feds[args]["uid"], "cid": chat},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("fadded").format(
                self.api.feds[args]["name"],
            ),
        )

    @error_handler
    @chat_command
    async def frmcm_(self, message: Message):
        """Remove chat from federation"""
        fed = await self.find_fed(message)
        if not fed:
            await utils.answer(message, self.strings("fed404"))
            return

        chat = utils.get_chat_id(message)

        self.api.request(
            {
                "action": "delete chat from federation",
                "args": {"uid": self.api.feds[fed]["uid"], "cid": chat},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("frem").format(
                self.api.feds[fed]["name"],
            ),
        )

    @error_handler
    @chat_command
    async def fbancm_(self, message: Message):
        """<reply | user> [reason] - Ban user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        chats = self.api.feds[fed]["chats"]

        banned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self._client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.ban(chat, user, t, reason, message, silent=True)
                banned_in += [f'<a href="{get_link(chat)}">{get_full_name(chat)}</a>']
            except Exception:
                pass

        msg = (
            self.strings("fban").format(
                get_link(user),
                get_first_name(user),
                self.api.feds[fed]["name"],
                f"for {t // 60} min(-s)" if t else "forever",
                reason,
                self.get("punish_suffix", ""),
            )
            + "\n\n<b>"
            + "\n".join(banned_in)
            + "</b>"
        )

        if self._is_inline:
            punishment_info = {
                "reply_markup": [
                    [
                        {
                            "text": self.strings("btn_funban"),
                            "data": f"ufb/{utils.get_chat_id(message)}/{user.id}",
                        }
                    ]
                ],
                "ttl": 15,
            }

            if self.get("logchat"):
                await utils.answer(message, msg)
                await self.inline.form(
                    text=self.strings("fban").format(
                        get_link(user),
                        get_first_name(user),
                        self.api.feds[fed]["name"],
                        f"for {t // 60} min(-s)" if t else "forever",
                        reason,
                        "",
                    )
                    + "<b>"
                    + "\n".join(banned_in)
                    + "</b>",
                    message=self.get("logchat"),
                    **punishment_info,
                )
            else:
                await self.inline.form(text=msg, message=message, **punishment_info)
        else:
            await utils.answer(message, msg)

        self.api.request(
            {
                "action": "clear all user warns",
                "args": {
                    "uid": self.api.feds[fed]["uid"],
                    "user": user.id,
                    "silent": True,
                },
            },
            message,
        )

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def punishsuffcm_(self, message: Message):
        """Set new punishment suffix"""
        if not utils.get_args_raw(message):
            self.set("punish_suffix", "")
            await utils.answer(message, self.strings("suffix_removed"))
        else:
            suffix = utils.get_args_raw(message)
            self.set("punish_suffix", suffix)
            await utils.answer(message, self.strings("suffix_updated").format(suffix))

    @error_handler
    @chat_command
    async def sethclogcm_(self, message: Message):
        """Set logchat"""
        if not utils.get_args_raw(message):
            self.set("logchat", "")
            await utils.answer(message, self.strings("logchat_removed"))
        else:
            logchat = utils.get_args_raw(message)
            if logchat.isdigit():
                logchat = int(logchat)

            try:
                logchat = await self._client.get_entity(logchat)
            except Exception:
                await utils.answer(message, self.strings("logchat_invalid"))
                return

            self.set("logchat", logchat.id)
            await utils.answer(
                message,
                self.strings("logchat_set").format(utils.escape_html(logchat.title)),
            )

    @error_handler
    @chat_command
    async def funbancm_(self, message: Message):
        """<user> [reason] - Unban user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        chats = self.api.feds[fed]["chats"]

        unbanned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self._client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self._client.edit_permissions(
                    chat,
                    user,
                    until_date=0,
                    **{right: True for right in BANNED_RIGHTS.keys()},
                )
                unbanned_in += [chat.title]
            except UserAdminInvalidError:
                pass

        m = (
            self.strings("funban").format(
                get_link(user),
                get_first_name(user),
                self.api.feds[fed]["name"],
            )
            + "<b>"
            + "\n".join(unbanned_in)
            + "</b>"
        )

        if self.get("logchat"):
            await self._client.send_message(self.get("logchat"), m)

        await utils.answer(message, m)

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def fmutecm_(self, message: Message):
        """<reply | user> [reason] - Mute user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        chats = self.api.feds[fed]["chats"]

        muted_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self._client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.mute(chat, user, t, reason, message, silent=True)
                muted_in += [f'<a href="{get_link(chat)}">{get_full_name(chat)}</a>']
            except Exception:
                pass

        msg = (
            self.strings("fmute").format(
                get_link(user),
                get_first_name(user),
                self.api.feds[fed]["name"],
                f"for {t // 60} min(-s)" if t else "forever",
                reason,
                self.get("punish_suffix", ""),
            )
            + "\n\n<b>"
            + "\n".join(muted_in)
            + "</b>"
        )

        if self._is_inline:
            punishment_info = {
                "reply_markup": [
                    [
                        {
                            "text": self.strings("btn_funmute"),
                            "data": f"ufm/{utils.get_chat_id(message)}/{user.id}",
                        }
                    ]
                ],
                "ttl": 15,
            }

            if self.get("logchat"):
                await utils.answer(message, msg)
                await self.inline.form(
                    text=self.strings("fmute").format(
                        get_link(user),
                        get_first_name(user),
                        self.api.feds[fed]["name"],
                        f"for {t // 60} min(-s)" if t else "forever",
                        reason,
                        "",
                    )
                    + "\n\n<b>"
                    + "\n".join(muted_in)
                    + "</b>",
                    message=self.get("logchat"),
                    **punishment_info,
                )
            else:
                await self.inline.form(text=msg, message=message, **punishment_info)
        else:
            await utils.answer(message, msg)

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def funmutecm_(self, message: Message):
        """<user> [reason] - Unban user in federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        chats = self.api.feds[fed]["chats"]

        unbanned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self._client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self._client.edit_permissions(
                    chat,
                    user,
                    until_date=0,
                    **{right: True for right in BANNED_RIGHTS.keys()},
                )
                unbanned_in += [chat.title]
            except UserAdminInvalidError:
                pass

        msg = (
            self.strings("funmute").format(
                get_link(user),
                get_first_name(user),
                self.api.feds[fed]["name"],
            )
            + "\n\n<b>"
            + "\n".join(unbanned_in)
            + "</b>"
        )

        await utils.answer(message, msg)

        if self.get("logchat"):
            await self._client.send_message(self.get("logchat"), msg)

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def kickcm_(self, message: Message):
        """<user> [reason] - Kick user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user, reason = None, None

        try:
            if reply:
                user = await self._client.get_entity(reply.sender_id)
                reason = args or self.strings
            else:
                uid = args.split(maxsplit=1)[0]
                if str(uid).isdigit():
                    uid = int(uid)
                user = await self._client.get_entity(uid)
                reason = (
                    args.split(maxsplit=1)[1]
                    if len(args.split(maxsplit=1)) > 1
                    else self.strings("no_reason")
                )
        except Exception:
            await utils.answer(message, self.strings("args"))
            return

        try:
            await self._client.kick_participant(utils.get_chat_id(message), user)
            msg = self.strings("kick").format(
                get_link(user),
                get_first_name(user),
                reason,
                self.get("punish_suffix", ""),
            )
            await utils.answer(message, msg)

            if self.get("logchat"):
                await self._client.send_message(
                    self.get("logchat"),
                    self.strings("kick_log").format(
                        get_link(user),
                        get_first_name(user),
                        get_link(chat),
                        get_first_name(chat),
                        reason,
                        "",
                    ),
                )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def bancm_(self, message: Message):
        """<user> [reason] - Ban user"""
        chat = await message.get_chat()

        a = await self.args_parser(message)
        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        try:
            await self.ban(chat, user, t, reason, message)
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def mutecm_(self, message: Message):
        """<user> [time] [reason] - Mute user"""
        chat = await message.get_chat()

        a = await self.args_parser(message)
        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason = a

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        try:
            await self.mute(chat, user, t, reason, message)
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def unmutecm_(self, message: Message):
        """<reply | user> - Unmute user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user = None

        try:
            if args.isdigit():
                args = int(args)
            user = await self._client.get_entity(args)
        except Exception:
            try:
                user = await self._client.get_entity(reply.sender_id)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        try:
            await self._client.edit_permissions(
                chat, user, until_date=0, send_messages=True
            )
            msg = self.strings("unmuted").format(get_link(user), get_first_name(user))
            await utils.answer(message, msg)

            if self.get("logchat"):
                await self._client.send_message(
                    self.get("logchat"),
                    self.strings("unmuted_log").format(
                        get_link(user),
                        get_first_name(user),
                        get_link(chat),
                        get_first_name(chat),
                    ),
                )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def unbancm_(self, message: Message):
        """<user> - Unban user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user = None

        try:
            if args.isdigit():
                args = int(args)
            user = await self._client.get_entity(args)
        except Exception:
            try:
                user = await self._client.get_entity(reply.sender_id)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        try:
            await self._client.edit_permissions(
                chat,
                user,
                until_date=0,
                **{right: True for right in BANNED_RIGHTS.keys()},
            )
            msg = self.strings("unban").format(get_link(user), get_first_name(user))
            await utils.answer(message, msg)

            if self.get("logchat"):
                await self._client.send_message(
                    self.get("logchat"),
                    self.strings("unban_log").format(
                        get_link(user),
                        get_first_name(user),
                        get_link(chat),
                        get_first_name(chat),
                    ),
                )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    async def protectscm_(self, message: Message):
        """List available filters"""
        await utils.answer(message, self.strings("protections"))

    @error_handler
    async def fedscm_(self, message: Message):
        """List federations"""
        res = self.strings("feds_header")

        if not self.api.feds:
            await utils.answer(message, self.strings("no_federations"))
            return

        for shortname, config in self.api.feds.copy().items():
            res += f"    ☮️ <b>{config['name']}</b> (<code>{shortname}</code>)"
            for chat in config["chats"]:
                try:
                    if str(chat).isdigit():
                        chat = int(chat)
                    c = await self._client.get_entity(chat)
                except Exception:
                    continue

                res += f"\n        <b>- <a href=\"tg://resolve?domain={getattr(c, 'username', '')}\">{c.title}</a></b>"

            res += f"\n        <b>👮‍♂️ {len(config.get('warns', []))} warns</b>\n\n"

        await utils.answer(message, res)

    @error_handler
    @chat_command
    async def fedcm_(self, message: Message):
        """<shortname> - Info about federation"""
        args = utils.get_args_raw(message)
        chat = utils.get_chat_id(message)

        fed = await self.find_fed(message)

        if (not args or args not in self.api.feds) and not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        if not args or args not in self.api.feds:
            args = fed

        res = self.strings("fed")

        fed = args

        admins = ""
        for admin in self.api.feds[fed]["admins"]:
            try:
                if str(admin).isdigit():
                    admin = int(admin)
                user = await self._client.get_entity(admin)
            except Exception:
                continue
            name = get_full_name(user)
            status = (
                "<code> 🧃 online</code>"
                if isinstance(getattr(user, "status", None), UserStatusOnline)
                else ""
            )
            admins += f' <b>👤 <a href="{get_link(user)}">{name}</a></b>{status}\n'

        chats = ""
        channels = ""
        for chat in self.api.feds[fed]["chats"]:
            try:
                if str(chat).isdigit():
                    chat = int(chat)
                c = await self._client.get_entity(chat)
            except Exception:
                continue

            if str(chat) in self._linked_channels:
                try:
                    channel = await self._client.get_entity(
                        self._linked_channels[str(chat)]
                    )
                    channels += f' <b>📣 <a href="{get_link(channel)}">{utils.escape_html(channel.title)}</a></b>\n'
                except Exception:
                    pass

            chats += (
                f' <b>🫂 <a href="{get_link(c)}">{utils.escape_html(c.title)}</a></b>\n'
            )

        await utils.answer(
            message,
            res.format(
                self.api.feds[fed]["name"],
                chats or "-",
                channels or "-",
                admins or "-",
                len(self.api.feds[fed].get("warns", [])),
            ),
        )

    @error_handler
    @chat_command
    async def pchatcm_(self, message: Message):
        """List protection for current chat"""
        chat_id = utils.get_chat_id(message)
        try:
            await self.inline.form(
                message=message,
                **(await self.get_config(chat_id)),
                **({"manual_security": True} if hasattr(self, "hikka") else {}),
            )
        except KeyError:
            await utils.answer(message, self.strings("no_protects"))

    @error_handler
    @chat_command
    async def warncm_(self, message: Message):
        """<user> - Warn user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self._client.get_entity(reply.sender_id)
            reason = args or self.strings("no_reason")
        else:
            try:
                u = args.split(maxsplit=1)[0]
                if u.isdigit():
                    u = int(u)

                user = await self._client.get_entity(u)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

            try:
                reason = args.split(maxsplit=1)[1]
            except IndexError:
                reason = self.strings("no_reason")

        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        self.api.request(
            {
                "action": "warn user",
                "args": {
                    "uid": self.api.feds[fed]["uid"],
                    "user": user.id,
                    "reason": reason,
                },
            },
            message,
        )
        warns = self.api.feds[fed]["warns"].get(str(user.id), []) + [reason]

        if len(warns) >= 7:
            user_name = get_first_name(user)
            chats = self.api.feds[fed]["chats"]
            for c in chats:
                await self._client(
                    EditBannedRequest(
                        c,
                        user,
                        ChatBannedRights(
                            until_date=time.time() + 60**2 * 24,
                            send_messages=True,
                        ),
                    )
                )

                await self._client.send_message(
                    c,
                    self.strings("warns_limit").format(
                        get_link(user), user_name, "muted him for 24 hours"
                    ),
                )

            await message.delete()

            self.api.request(
                {
                    "action": "clear all user warns",
                    "args": {"uid": self.api.feds[fed]["uid"], "user": user.id},
                },
                message,
            )
        else:
            msg = self.strings("fwarn", message).format(
                get_link(user),
                get_first_name(user),
                len(warns),
                7,
                reason,
                self.get("punish_suffix", ""),
            )

            if self._is_inline:
                punishment_info = {
                    "reply_markup": [
                        [
                            {
                                "text": self.strings("btn_unwarn"),
                                "data": f"dw/{utils.get_chat_id(message)}/{user.id}",
                            }
                        ]
                    ],
                    "ttl": 15,
                }

                if self.get("logchat"):
                    await utils.answer(message, msg)
                    await self.inline.form(
                        text=self.strings("fwarn", message).format(
                            get_link(user),
                            get_first_name(user),
                            len(warns),
                            7,
                            reason,
                            "",
                        ),
                        message=self.get("logchat"),
                        **punishment_info,
                    )
                else:
                    await self.inline.form(text=msg, message=message, **punishment_info)
            else:
                await utils.answer(message, msg)

    @error_handler
    @chat_command
    async def warnscm_(self, message: Message):
        """[user] - Show warns in chat \\ of user"""
        chat_id = utils.get_chat_id(message)

        fed = await self.find_fed(message)

        async def check_member(user_id):
            try:
                await self._client.get_permissions(chat_id, user_id)
                return True
            except Exception:
                return False

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        warns = self.api.feds[fed]["warns"]

        if not warns:
            await utils.answer(message, self.strings("no_fed_warns"))
            return

        async def send_user_warns(usid):
            try:
                if int(usid) < 0:
                    usid = int(str(usid)[4:])
            except Exception:
                pass

            if not warns:
                await utils.answer(message, self.strings("no_fed_warns"))
                return

            if str(usid) not in warns or not warns[str(usid)]:
                user_obj = await self._client.get_entity(usid)
                await utils.answer(
                    message,
                    self.strings("no_warns").format(
                        get_link(user_obj), get_full_name(user_obj)
                    ),
                )
            else:
                user_obj = await self._client.get_entity(usid)
                _warns = ""
                processed = []
                for warn in warns[str(usid)].copy():
                    if warn in processed:
                        continue
                    processed += [warn]
                    _warns += (
                        "<code>   </code>🏴󠁧󠁢󠁥󠁮󠁧󠁿 <i>"
                        + warn
                        + (
                            f" </i><b>[x{warns[str(usid)].count(warn)}]</b><i>"
                            if warns[str(usid)].count(warn) > 1
                            else ""
                        )
                        + "</i>\n"
                    )
                await utils.answer(
                    message,
                    self.strings("warns").format(
                        get_link(user_obj),
                        get_full_name(user_obj),
                        len(warns[str(usid)]),
                        7,
                        _warns,
                    ),
                )

        if not await self.check_admin(chat_id, message.sender_id):
            await send_user_warns(message.sender_id)
        else:
            reply = await message.get_reply_message()
            args = utils.get_args_raw(message)
            if not reply and not args:
                res = self.strings("warns_adm_fed")
                for user, _warns in warns.copy().items():
                    try:
                        user_obj = await self._client.get_entity(int(user))
                    except Exception:
                        continue

                    if isinstance(user_obj, User):
                        try:
                            name = get_full_name(user_obj)
                        except TypeError:
                            continue
                    else:
                        name = user_obj.title

                    res += f'🐺 <b><a href="{get_link(user_obj)}">' + name + "</a></b>\n"
                    processed = []
                    for warn in _warns.copy():
                        if warn in processed:
                            continue
                        processed += [warn]
                        res += (
                            "<code>   </code>🏴󠁧󠁢󠁥󠁮󠁧󠁿 <i>"
                            + warn
                            + (
                                f" </i><b>[x{_warns.count(warn)}]</b><i>"
                                if _warns.count(warn) > 1
                                else ""
                            )
                            + "</i>\n"
                        )

                await utils.answer(message, res)
                return
            elif reply:
                await send_user_warns(reply.sender_id)
            elif args:
                await send_user_warns(args)

    @error_handler
    @chat_command
    async def delwarncm_(self, message: Message):
        """<user> - Forgave last warn"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None

        if reply:
            user = await self._client.get_entity(reply.sender_id)
        else:
            if args.isdigit():
                args = int(args)

            try:
                user = await self._client.get_entity(args)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        self.api.request(
            {
                "action": "forgive user warn",
                "args": {"uid": self.api.feds[fed]["uid"], "user": user.id},
            },
            message,
        )

        msg = self.strings("dwarn_fed").format(get_link(user), get_first_name(user))

        await utils.answer(message, msg)

        if self.get("logchat", False):
            await self._client.send_message(self.get("logchat"), msg)

    @error_handler
    @chat_command
    async def clrwarnscm_(self, message: Message):
        """<reply | user_id | username> - Remove all warns from user"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self._client.get_entity(reply.sender_id)
        else:
            if args.isdigit():
                args = int(args)

            try:
                user = await self._client.get_entity(args)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        self.api.request(
            {
                "action": "clear all user warns",
                "args": {"uid": self.api.feds[fed]["uid"], "user": user.id},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("clrwarns_fed").format(get_link(user), get_first_name(user)),
        )

    @error_handler
    @chat_command
    async def clrallwarnscm_(self, message: Message):
        """Remove all warns from current federation"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        self.api.request(
            {
                "action": "clear federation warns",
                "args": {"uid": self.api.feds[fed]["uid"]},
            },
            message,
        )

        await utils.answer(message, self.strings("clrallwarns_fed"))

    @error_handler
    @chat_command
    async def welcomecm_(self, message: Message):
        """<text> - Change welcome text"""
        chat_id = utils.get_chat_id(message)
        args = utils.get_args_raw(message) or "off"

        self.api.request(
            {
                "action": "update protections",
                "args": {"protection": "welcome", "state": args, "chat": chat_id},
            },
            message,
        )

        if args and args != "off":
            await utils.answer(message, self.strings("welcome").format(args))
        else:
            await utils.answer(message, self.strings("unwelcome"))

    @error_handler
    @chat_command
    async def fdefcm_(self, message: Message):
        """<user> - Toggle global user invulnerability"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self._client.get_entity(reply.sender_id)
        else:
            if str(args).isdigit():
                args = int(args)

            try:
                user = await self._client.get_entity(args)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        self.api.request(
            {
                "action": "protect user",
                "args": {"uid": self.api.feds[fed]["uid"], "user": user.id},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("defense").format(
                get_link(user),
                get_first_name(user),
                "on" if str(user.id) not in self.api.feds[fed]["fdef"] else "off",
            ),
        )

    @error_handler
    @chat_command
    async def fsavecm_(self, message: Message):
        """<note name> <reply> - Save federative note"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not reply or not args or not reply.text:
            await utils.answer(message, self.strings("fsave_args"))
            return

        self.api.request(
            {
                "action": "new note",
                "args": {
                    "uid": self.api.feds[fed]["uid"],
                    "shortname": args,
                    "note": reply.text,
                },
            },
            message,
        )

        await utils.answer(message, self.strings("fsave").format(args))

    @error_handler
    @chat_command
    async def fstopcm_(self, message: Message):
        """<note name> - Remove federative note"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("fstop_args"))
            return

        self.api.request(
            {
                "action": "delete note",
                "args": {"uid": self.api.feds[fed]["uid"], "shortname": args},
            },
            message,
        )

        await utils.answer(message, self.strings("fstop").format(args))

    @error_handler
    @chat_command
    async def fnotescm_(self, message: Message, from_watcher: bool = False):
        """Show federative notes"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        res = {}
        cache = {}

        for shortname, note in self.api.feds[fed].get("notes", {}).items():
            if int(note["creator"]) != self._me and from_watcher:
                continue

            try:
                if int(note["creator"]) not in cache:
                    obj = await self._client.get_entity(int(note["creator"]))
                    cache[int(note["creator"])] = obj.first_name or obj.title
                key = f'<a href="{get_link(obj)}">{cache[int(note["creator"])]}</a>'
                if key not in res:
                    res[key] = ""
                res[key] += f"  <code>{shortname}</code>\n"
            except Exception:
                key = "unknown"
                if key not in res:
                    res[key] = ""
                res[key] += f"  <code>{shortname}</code>\n"

        notes = "".join(f"\nby {owner}:\n{note}" for owner, note in res.items())
        if not notes:
            return

        await utils.answer(message, self.strings("fnotes").format(notes))

    @error_handler
    @chat_command
    async def fdeflistcm_(self, message: Message):
        """Show global invulnerable users"""
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        if not self.api.feds[fed].get("fdef", []):
            await utils.answer(message, self.strings("no_defense"))
            return

        res = ""
        for user in self.api.feds[fed].get("fdef", []).copy():
            try:
                u = await self._client.get_entity(int(user))
            except Exception:
                self.api.request(
                    {
                        "action": "protect user",
                        "args": {"uid": self.api.feds[fed]["uid"], "user": user},
                    },
                    message,
                )
                await asyncio.sleep(0.2)
                continue

            tit = get_full_name(u)

            res += f'  🇻🇦 <a href="{get_link(u)}">{tit}</a>\n'

        await utils.answer(message, self.strings("defense_list").format(res))
        return

    @error_handler
    @chat_command
    async def dmutecm_(self, message: Message):
        """Delete and mute"""
        reply = await message.get_reply_message()
        await self.mutecmd(message)
        await reply.delete()

    @error_handler
    @chat_command
    async def dbancm_(self, message: Message):
        """Delete and ban"""
        reply = await message.get_reply_message()
        await self.bancmd(message)
        await reply.delete()

    @error_handler
    @chat_command
    async def dwarncm_(self, message: Message):
        """Delete and warn"""
        reply = await message.get_reply_message()
        await self.warncmd(message)
        await reply.delete()

    @error_handler
    @chat_command
    async def frenamecm_(self, message: Message):
        """Rename federation"""
        args = utils.get_args_raw(message)
        fed = await self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        if not args:
            await utils.answer(message, self.strings("rename_noargs"))
            return

        self.api.request(
            {
                "action": "rename federation",
                "args": {"uid": self.api.feds[fed]["uid"], "name": args},
            },
            message,
        )

        await utils.answer(
            message,
            self.strings("rename_success").format(utils.escape_html(args)),
        )

    @error_handler
    async def myrightscm_(self, message: Message):
        """List your admin rights in all chats"""
        if not PIL_AVAILABLE:
            await utils.answer(message, self.strings("pil_unavailable"))
            return

        message = await utils.answer(message, self.strings("processing_myrights"))
        if isinstance(message, (list, tuple, set)):
            message = message[0]

        rights = []
        async for chat in self._client.iter_dialogs():
            ent = chat.entity

            if (
                not (
                    isinstance(ent, Chat)
                    or (isinstance(ent, Channel) and getattr(ent, "megagroup", False))
                )
                or not ent.admin_rights
                or ent.participants_count < 5
            ):
                continue

            r = ent.admin_rights

            rights += [
                [
                    ent.title if len(ent.title) < 30 else f"{ent.title[:30]}...",
                    "YES" if r.change_info else "-----",
                    "YES" if r.delete_messages else "-----",
                    "YES" if r.ban_users else "-----",
                    "YES" if r.invite_users else "-----",
                    "YES" if r.pin_messages else "-----",
                    "YES" if r.add_admins else "-----",
                ]
            ]

        await self._client.send_file(
            message.peer_id,
            render_table(
                [
                    [
                        "Chat",
                        "change_info",
                        "delete_messages",
                        "ban_users",
                        "invite_users",
                        "pin_messages",
                        "add_admins",
                    ]
                ]
                + rights
            ),
        )

        if message.out:
            await message.delete()

    @error_handler
    async def p__antiservice(self, chat_id: Union[str, int], message: Message):
        if self.api.should_protect(chat_id, "antiservice") and getattr(
            message, "action_message", False
        ):
            await message.delete()

    @error_handler
    async def p__banninja(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
        chat: Union[Chat, Channel],
    ) -> bool:
        if not (
            self.api.should_protect(chat_id, "banninja")
            and (
                getattr(message, "user_joined", False)
                or getattr(message, "user_added", False)
            )
        ):
            return False

        chat_id = str(chat_id)

        if chat_id in self._ban_ninja:
            if self._ban_ninja[chat_id] > time.time():
                await self.inline.bot.kick_chat_member(f"-100{chat_id}", user_id)
                logger.warning(f"BanNinja is active in chat {chat.title}, I kicked {get_full_name(user)}")  # fmt: skip
                return True

            del self._ban_ninja[chat_id]

        if chat_id not in self._join_ratelimit:
            self._join_ratelimit[chat_id] = []

        self._join_ratelimit[chat_id] += [(user_id, round(time.time()))]

        processed = []

        for u, t in self._join_ratelimit[chat_id].copy():
            if u in processed or t + 60 < time.time():
                self._join_ratelimit[chat_id].remove((u, t))
            else:
                processed += [u]

        if len(self._join_ratelimit) > int(self.config["join_ratelimit"]):
            if not await self.check_admin(
                utils.get_chat_id(message),
                f"@{self.inline.bot_username}",
            ):
                try:
                    await self._client(
                        InviteToChannelRequest(
                            utils.get_chat_id(message),
                            [self.inline.bot_username],
                        )
                    )
                except Exception:
                    logger.warning(
                        "Unable to invite cleaner to chat. Maybe he's already there?"
                    )

                try:
                    await self._client(
                        EditAdminRequest(
                            channel=utils.get_chat_id(message),
                            user_id=self.inline.bot_username,
                            admin_rights=ChatAdminRights(ban_users=True),
                            rank="Ban Ninja",
                        )
                    )
                except Exception:
                    logger.exception("Cleaner promotion failed!")
                    return False

            self._ban_ninja[chat_id] = round(time.time()) + (10 * 60)
            await self.inline.form(
                self.strings("smart_anti_raid_active"),
                message=chat.id,
                reply_markup=[
                    [
                        {
                            "text": self.strings("smart_anti_raid_off"),
                            "callback": self.disable_smart_anti_raid,
                            "args": (chat_id,),
                        }
                    ]
                ],
            )

        return False

    @error_handler
    async def p__antiraid(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
        chat: Union[Chat, Channel],
    ) -> bool:
        if self.api.should_protect(chat_id, "antiraid") and (
            getattr(message, "user_joined", False)
            or getattr(message, "user_added", False)
        ):
            action = self.api.chats[str(chat_id)]["antiraid"]
            if action == "kick":
                await self._client.send_message(
                    "me",
                    self.strings("antiraid").format(
                        "kicked", user.id, get_full_name(user), chat.title
                    ),
                )

                await self._client.kick_participant(chat_id, user)
            elif action == "ban":
                await self._client.send_message(
                    "me",
                    self.strings("antiraid").format(
                        "banned", user.id, get_full_name(user), chat.title
                    ),
                )

                await self.ban(chat, user, 0, "antiraid")
            elif action == "mute":
                await self._client.send_message(
                    "me",
                    self.strings("antiraid").format(
                        "muted", user.id, get_full_name(user), chat.title
                    ),
                )

                await self.mute(chat, user, 0, "antiraid")

            return True

        return False

    @error_handler
    async def p__welcome(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
        chat: Chat,
    ) -> bool:
        if self.api.should_protect(chat_id, "welcome") and (
            getattr(message, "user_joined", False)
            or getattr(message, "user_added", False)
        ):
            await self._client.send_message(
                chat_id,
                self.api.chats[str(chat_id)]["welcome"][0]
                .replace("{user}", get_full_name(user))
                .replace("{chat}", utils.escape_html(chat.title))
                .replace(
                    "{mention}", f'<a href="{get_link(user)}">{get_full_name(user)}</a>'
                ),
                reply_to=message.action_message.id,
            )

            return True

        return False

    @error_handler
    async def p__report(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ):
        if not self.api.should_protect(chat_id, "report") or not getattr(
            message, "reply_to_msg_id", False
        ):
            return

        reply = await message.get_reply_message()
        if (
            str(user_id) not in self._ratelimit["report"]
            or self._ratelimit["report"][str(user_id)] < time.time()
        ) and (
            (
                message.raw_text.startswith("#report")
                or message.raw_text.startswith("/report")
            )
            and reply
        ):
            chat = await message.get_chat()

            reason = (
                message.raw_text.split(maxsplit=1)[1]
                if message.raw_text.count(" ") >= 1
                else self.strings("no_reason")
            )

            self.api.request(
                {
                    "action": "report",
                    "args": {
                        "chat": chat_id,
                        "reason": reason,
                        "link": await get_message_link(reply, chat),
                        "user_link": get_link(user),
                        "user_name": get_full_name(user),
                        "text_thumbnail": (getattr(reply, "raw_text", "") or "")[:1024]
                        or "<media>",
                    },
                },
                message,
            )

            msg = self.strings("reported").format(
                get_link(user),
                get_full_name(user),
                reason,
            )

            if self._is_inline:
                await self.inline.form(
                    message=chat.id,
                    text=msg,
                    reply_markup=[
                        [
                            {
                                "text": self.strings("btn_mute"),
                                "data": f"m/{chat.id}/{reply.sender_id}#{reply.id}",
                            },
                            {
                                "text": self.strings("btn_ban"),
                                "data": f"b/{chat.id}/{reply.sender_id}#{reply.id}",
                            },
                        ],
                        [
                            {
                                "text": self.strings("btn_fban"),
                                "data": f"fb/{chat.id}/{reply.sender_id}#{reply.id}",
                            },
                            {
                                "text": self.strings("btn_del"),
                                "data": f"d/{chat.id}/{reply.sender_id}#{reply.id}",
                            },
                        ],
                    ],
                    ttl=15,
                )
            else:
                await (utils.answer if message else self._client.send_message)(
                    message or chat.id, msg
                )

            self._ratelimit["report"][str(user_id)] = time.time() + 30

            await message.delete()

    @error_handler
    async def p__antiflood(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if self.api.should_protect(chat_id, "antiflood"):
            if str(chat_id) not in self.flood_cache:
                self.flood_cache[str(chat_id)] = {}

            if str(user_id) not in self.flood_cache[str(chat_id)]:
                self.flood_cache[str(chat_id)][str(user_id)] = []

            for item in self.flood_cache[str(chat_id)][str(user_id)].copy():
                if time.time() - item > self.flood_timeout:
                    self.flood_cache[str(chat_id)][str(user_id)].remove(item)

            self.flood_cache[str(chat_id)][str(user_id)].append(round(time.time(), 2))
            self.save_flood_cache()

            if (
                len(self.flood_cache[str(chat_id)][str(user_id)])
                >= self.flood_threshold
            ):
                return self.api.chats[str(chat_id)]["antiflood"][0]

        return False

    @error_handler
    async def p__antichannel(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            self.api.should_protect(chat_id, "antichannel")
            and getattr(message, "sender_id", 0) < 0
        ):
            await self.ban(chat_id, user_id, 0, "", None, True)
            await message.delete()
            return True

        return False

    @error_handler
    async def p__antigif(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if self.api.should_protect(chat_id, "antigif"):
            try:
                if (
                    message.media
                    and DocumentAttributeAnimated() in message.media.document.attributes
                ):
                    await message.delete()
                    return True
            except Exception:
                pass

        return False

    @error_handler
    async def p__antispoiler(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if self.api.should_protect(chat_id, "antispoiler"):
            try:
                if any(isinstance(_, MessageEntitySpoiler) for _ in message.entities):
                    await message.delete()
                    return True
            except Exception:
                pass

        return False

    @error_handler
    async def p__antiexplicit(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if self.api.should_protect(chat_id, "antiexplicit"):
            text = getattr(message, "raw_text", "")
            P = "пПnPp"
            I = "иИiI1uІИ́Їіи́ї"  # noqa: E741
            E = "еЕeEЕ́е́"
            D = "дДdD"
            Z = "зЗ3zZ3"
            M = "мМmM"
            U = "уУyYuUУ́у́"
            O = "оОoO0О́о́"  # noqa: E741
            L = "лЛlL1"
            A = "аАaAА́а́@"
            N = "нНhH"
            G = "гГgG"
            K = "кКkK"
            R = "рРpPrR"
            H = "хХxXhH"
            YI = "йЙyуУY"
            YA = "яЯЯ́я́"
            YO = "ёЁ"
            YU = "юЮЮ́ю́"
            B = "бБ6bB"
            T = "тТtT1"
            HS = "ъЪ"
            SS = "ьЬ"
            Y = "ыЫ"

            occurrences = re.findall(
                rf"""\b[0-9]*(\w*[{P}][{I}{E}][{Z}][{D}]\w*|(?:[^{I}{U}\s]+|{N}{I})?(?<!стра)[{H}][{U}][{YI}{E}{YA}{YO}{I}{L}{YU}](?!иг)\w*|\w*[{B}][{L}](?:[{YA}]+[{D}{T}]?|[{I}]+[{D}{T}]+|[{I}]+[{A}]+)(?!х)\w*|(?:\w*[{YI}{U}{E}{A}{O}{HS}{SS}{Y}{YA}][{E}{YO}{YA}{I}][{B}{P}](?!ы\b|ол)\w*|[{E}{YO}][{B}]\w*|[{I}][{B}][{A}]\w+|[{YI}][{O}][{B}{P}]\w*)|\w*(?:[{P}][{I}{E}][{D}][{A}{O}{E}]?[{R}](?!о)\w*|[{P}][{E}][{D}][{E}{I}]?[{G}{K}])|\w*[{Z}][{A}{O}][{L}][{U}][{P}]\w*|\w*[{M}][{A}][{N}][{D}][{A}{O}]\w*|\w*[{G}][{O}{A}][{N}][{D}][{O}][{N}]\w*)""",
                text,
            )

            occurrences = [
                word
                for word in occurrences
                if all(
                    excl not in word for excl in self.api.variables["censor_exclusions"]
                )
            ]

            if occurrences:
                return self.api.chats[str(chat_id)]["antiexplicit"][0]

        return False

    @error_handler
    async def p__antinsfw(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if not self.api.should_protect(chat_id, "antinsfw"):
            return False

        media = False

        if getattr(message, "sticker", False):
            media = message.sticker
        elif getattr(message, "media", False):
            media = message.media

        if not media:
            return False

        photo = io.BytesIO()
        await self._client.download_media(message.media, photo)
        photo.seek(0)

        if imghdr.what(photo) not in self.api.variables["image_types"]:
            return False

        response = await self.api.nsfw(photo)
        if response != "nsfw":
            return False

        todel = []
        async for _ in self._client.iter_messages(
            message.peer_id,
            reverse=True,
            offset_id=message.id - 1,
        ):
            todel += [_]
            if _.sender_id != message.sender_id:
                break

        await self._client.delete_messages(
            message.peer_id,
            message_ids=todel,
            revoke=True,
        )

        return self.api.chats[str(chat_id)]["antinsfw"][0]

    @error_handler
    async def p__antitagall(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        return (
            self.api.chats[str(chat_id)]["antitagall"][0]
            if self.api.should_protect(chat_id, "antitagall")
            and getattr(message, "text", False)
            and message.text.count("tg://user?id=") >= 5
            else False
        )

    @error_handler
    async def p__antihelp(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if not self.api.should_protect(chat_id, "antihelp") or not getattr(
            message, "text", False
        ):
            return False

        search = message.text
        if "@" in search:
            search = search[: search.find("@")]

        if (
            not search.split()
            or search.split()[0][1:] not in self.api.variables["blocked_commands"]
        ):
            return False

        await message.delete()
        return True

    @error_handler
    async def p__antiarab(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        return (
            self.api.chats[str(chat_id)]["antiarab"][0]
            if (
                self.api.should_protect(chat_id, "antiarab")
                and (
                    getattr(message, "user_joined", False)
                    or getattr(message, "user_added", False)
                )
                and (
                    len(re.findall("[\u4e00-\u9fff]+", get_full_name(user))) != 0
                    or len(re.findall("[\u0621-\u064A]+", get_full_name(user))) != 0
                )
            )
            else False
        )

    @error_handler
    async def p__antizalgo(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        return (
            self.api.chats[str(chat_id)]["antizalgo"][0]
            if (
                self.api.should_protect(chat_id, "antizalgo")
                and (
                    getattr(message, "user_joined", False)
                    or getattr(message, "user_added", False)
                )
                and len(
                    re.findall(
                        "[\u200f\u200e\u0300-\u0361\u0316-\u0362\u0334-\u0338\u0363-\u036F\u3164\ud83d\udd07\u0020\u00A0\u2000-\u2009\u200A\u2028\u205F]",
                        get_full_name(user),
                    )
                )
                / len(get_full_name(user))
                >= 0.5
            )
            else False
        )

    @error_handler
    async def p__antistick(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if not self.api.should_protect(chat_id, "antistick") or not (
            getattr(message, "sticker", False)
            or getattr(message, "media", False)
            and isinstance(message.media, MessageMediaUnsupported)
        ):
            return False

        sender = user.id
        if sender not in self._sticks_ratelimit:
            self._sticks_ratelimit[sender] = []

        self._sticks_ratelimit[sender] += [round(time.time())]

        for timing in self._sticks_ratelimit[sender].copy():
            if time.time() - timing > 60:
                self._sticks_ratelimit[sender].remove(timing)

        if len(self._sticks_ratelimit[sender]) > self._sticks_limit:
            return self.api.chats[str(chat_id)]["antistick"][0]

    @error_handler
    async def p__antilagsticks(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        res = (
            self.api.should_protect(chat_id, "antilagsticks")
            and getattr(message, "sticker", False)
            and getattr(message.sticker, "id", False)
            in self.api.variables["destructive_sticks"]
        )
        if res:
            await message.delete()

        return res

    @error_handler
    async def watcher(self, message: Message):
        if not isinstance(getattr(message, "chat", 0), (Chat, Channel)):
            return

        chat_id = utils.get_chat_id(message)

        if (
            isinstance(getattr(message, "chat", 0), Channel)
            and not getattr(message, "megagroup", False)
            and int(chat_id) in reverse_dict(self._linked_channels)
        ):
            actual_chat = str(reverse_dict(self._linked_channels)[int(chat_id)])
            await self.p__antiservice(actual_chat, message)
            return

        await self.p__antiservice(chat_id, message)

        try:
            user_id = (
                getattr(message, "sender_id", False)
                or message.action_message.action.users[0]
            )
        except Exception:
            try:
                user_id = message.action_message.action.from_id.user_id
            except Exception:
                try:
                    user_id = message.from_id.user_id
                except Exception:
                    try:
                        user_id = message.action_message.from_id.user_id
                    except Exception:
                        try:
                            user_id = message.action.from_user.id
                        except Exception:
                            logger.debug(f"Can't extract entity from event {type(message)}")  # fmt: skip
                            return
        user_id = int(str(user_id)[4:]) if str(user_id).startswith("-100") else int(user_id)  # fmt: skip

        fed = await self.find_fed(message)

        if fed in self.api.feds:
            if (
                getattr(message, "raw_text", False)
                and (
                    str(user_id) not in self._ratelimit["notes"]
                    or self._ratelimit["notes"][str(user_id)] < time.time()
                )
                and not (
                    message.raw_text.startswith(self.get_prefix())
                    and len(message.raw_text) > 1
                    and message.raw_text[1] != self.get_prefix()
                )
            ):
                logger.debug("Checking message for notes...")
                if message.raw_text.lower().strip() in ["#заметки", "#notes", "/notes"]:
                    self._ratelimit["notes"][str(user_id)] = time.time() + 3
                    if any(
                        str(note["creator"]) == str(self._me)
                        for _, note in self.api.feds[fed]["notes"].items()
                    ):
                        await self.fnotescmd(
                            await message.reply(f"<code>{self.get_prefix()}fnotes</code>"),
                            True,
                        )

                for note, note_info in self.api.feds[fed]["notes"].items():
                    if str(note_info["creator"]) != str(self._me):
                        continue

                    if note.lower() in message.raw_text.lower():
                        txt = note_info["text"]
                        self._ratelimit["notes"][str(user_id)] = time.time() + 3

                        if not txt.startswith("@inline"):
                            await utils.answer(message, txt)
                            break

                        txt = "\n".join(txt.splitlines()[1:])
                        buttons = []
                        button_re = r"\[(.+)\]\((https?://.*)\)"
                        txt_r = []
                        for line in txt.splitlines():
                            if re.match(button_re, re.sub(r"<.*?>", "", line).strip()):
                                match = re.search(
                                    button_re, re.sub(r"<.*?>", "", line).strip()
                                )
                                buttons += [
                                    [{"text": match.group(1), "url": match.group(2)}]
                                ]
                            else:
                                txt_r += [line]

                        if not buttons:
                            await utils.answer(message, txt)
                            break

                        await self.inline.form(
                            message=message,
                            text="\n".join(txt_r),
                            reply_markup=buttons,
                        )

            if int(user_id) in (
                list(map(int, self.api.feds[fed]["fdef"]))
                + list(self._linked_channels.values())
            ):
                return

        if str(chat_id) not in self.api.chats or not self.api.chats[str(chat_id)]:
            return

        try:
            if (
                await self._client.get_permissions(chat_id, message.sender_id)
            ).is_admin:

                return
        # fmt: skip
        except Exception:
            pass

        user = await self._client.get_entity(user_id)
        chat = await message.get_chat()
        user_name = get_full_name(user)

        args = (chat_id, user_id, user, message)

        if await self.p__banninja(*args, chat):
            return

        if await self.p__antiraid(*args, chat):
            return

        r = await self.p__antiarab(*args)
        if r:
            await self.punish(chat_id, user, "arabic_nickname", r, user_name)
            return

        r = await self.p__antizalgo(*args)
        if r:
            await self.punish(chat_id, user, "zalgo", r, user_name)
            return

        if await self.p__welcome(*args, chat):
            return

        if getattr(message, "action", ""):
            return

        await self.p__report(*args)

        r = await self.p__antiflood(*args)
        if r:
            await self.punish(chat_id, user, "flood", r, user_name)
            await message.delete()
            return

        if await self.p__antichannel(*args):
            return

        if await self.p__antigif(*args):
            return

        r = await self.p__antilagsticks(*args)
        if r:
            await self.punish(chat_id, user, "destructive_stick", "ban", user_name)
            return

        r = await self.p__antistick(*args)
        if r:
            await self.punish(chat_id, user, "stick", r, user_name)
            return

        if await self.p__antispoiler(*args):
            return

        r = await self.p__antiexplicit(*args)
        if r:
            await self.punish(chat_id, user, "explicit", r, user_name)
            await message.delete()
            return

        r = await self.p__antinsfw(*args)
        if r:
            await self.punish(chat_id, user, "nsfw_content", r, user_name)
            return

        r = await self.p__antitagall(*args)
        if r:
            await self.punish(chat_id, user, "tagall", r, user_name)
            await message.delete()
            return

        await self.p__antihelp(*args)

    _punish_queue = []
    _raid_cleaners = []

    flood_timeout = FLOOD_TIMEOUT
    flood_threshold = FLOOD_TRESHOLD

    _my_protects = {}
    _linked_channels = {}
    _sticks_ratelimit = {}
    _flood_fw_protection = {}
    _ratelimit = {"notes": {}, "report": {}}

    async def client_ready(
        self,
        client: "TelegramClient",  # noqa
        db: "hikka.database.Database",  # noqa
    ):
        """Entry point"""
        global api

        self._db = db
        self._client = client

        self._me = (await client.get_me()).id

        self._is_inline = self.inline.init_complete

        self._sticks_limit = 7

        try:
            with open("flood_cache.json", "r") as f:
                self.flood_cache = json.loads(f.read())
        except Exception:
            self.flood_cache = {}

        try:
            with open("join_ratelimit.json", "r") as f:
                self._join_ratelimit = json.loads(f.read())
        except Exception:
            self._join_ratelimit = {}

        self._ban_ninja = db.get("HikariChat", "ban_ninja", {})

        self.api = api
        await api.init(client, db, self)

        if self.api._inited:
            for protection in self.api.variables["protections"]:
                setattr(self, f"{protection}cmd", self.protection_template(protection))
        else:
            if not hasattr(self, "hikka"):
                raise loader.LoadError("This module is supported only by Hikka")

        for method_name in dir(self):
            if (
                callable(getattr(self, method_name))
                and method_name.endswith("cm_")
                and (self.api._inited or method_name[:-3] not in API_FEATURES)
            ):
                setattr(self, f"{method_name[:-3]}cmd", getattr(self, method_name))

        # We can override class docstings because of abc meta
        self.__doc__ = (
            "Расширенный инструментарий администратора чата\n"
            + f"Версия: {version}\n"
            + ("💔 Lite" if not self.api._inited else "😈 Full")
        )