from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from rustplus import (
    RustSocket,
    ServerDetails,
    EntityEventPayload,
    TeamEventPayload,
    ChatEventPayload,
    ProtobufEvent,
    ChatEvent,
    EntityEvent,
    TeamEvent
)
import deepl

COMMANDS = {
    "TIME": ["!time", "!t"],
    "JAPANESE": ["!ja"],
    "ENGLISH": ["!us"],
    "POPULATION": ["!pop"],
    "MEMBER": ["!member"],
    "HELP": ["!help", "!command", "!commands"]
}

BOT_PREFIX = "[RUSTBOT]"
DISCORD_PREFIX = "[DISCORD]"
TRANS_SUFFIX = "[TRANSED]"


@dataclass
class ChatMessage:
    name: str
    message: str


class RustClient:

    def __init__(self, ip: str, port: str, player_id: str, player_token: str):
        self.talk_buffer: List[Dict[str, str]] = []
        self.server_details = ServerDetails(
            ip=ip,
            port=port,
            player_id=player_id,
            player_token=player_token
        )
        self.rust_socket = RustSocket(server_details=self.server_details)
        self.translator = deepl.Translator("dc062da7-fedd-4a04-a86e-0acf9ff6fe29:fx")

        self._setup_chat_event()

    def _setup_chat_event(self) -> None:

        @ChatEvent(self.server_details)
        async def chat(event: ChatEventPayload):
            message = ChatMessage(
                name=event.message.name,
                message=event.message.message
            )

            if self._should_process_message(message.message):
                await self._handle_commands(message)

    def _should_process_message(self, message: str) -> bool:
        return not (DISCORD_PREFIX in message or BOT_PREFIX in message)

    async def _handle_commands(self, chat_message: ChatMessage) -> None:
        message = chat_message.message

        if any(cmd in message for cmd in COMMANDS["TIME"]):
            await self._handle_time_command()
        elif any(cmd in message for cmd in COMMANDS["JAPANESE"]):
            await self._handle_translation_command(message, "JA", "!ja ")
        elif any(cmd in message for cmd in COMMANDS["ENGLISH"]):
            await self._handle_translation_command(message, "EN-US", "!us ")
        elif any(cmd in message for cmd in COMMANDS["POPULATION"]):
            await self._handle_population_command()
        elif any(cmd in message for cmd in COMMANDS["MEMBER"]):
            await self._handle_member_command()
        elif any(cmd in message for cmd in COMMANDS["HELP"]):
            await self._handle_help_command()
        else:
            self._add_to_buffer(chat_message)

    async def _handle_time_command(self) -> None:
        server_time = await self.get_server_time()
        await self.send_team_chat(
            f"{BOT_PREFIX} TIME: {server_time.time}, 日出: {server_time.sunrise}, 日没: {server_time.sunset}"
        )

    async def _handle_translation_command(self, message: str, target_lang: str, prefix: str) -> None:
        text = message.replace(prefix, "")
        result = self.translator.translate_text(text, target_lang=target_lang)

        if target_lang == "EN-US":
            result = self.translator.translate_text(
                self.translator.translate_text(text, target_lang="JA").text,
                target_lang=target_lang
            )

        await self.send_team_chat(f"{BOT_PREFIX} {target_lang}: {result.text}")
        self._add_to_buffer(ChatMessage(name="", message=f"{result.text} {TRANS_SUFFIX}"))

    async def _handle_population_command(self) -> None:
        server_info = await self.get_server_info()
        await self.send_team_chat(
            f"{BOT_PREFIX} Online Players: {server_info.players}/{server_info.max_players}"
        )

    async def _handle_member_command(self) -> None:
        team_info = await self.get_team_info()
        online_members = []
        offline_members = []

        for member in team_info.members:
            if member.is_online:
                online_members.append(member.name)
            else:
                offline_members.append(member.name)

        await self.send_team_chat(
            f"{BOT_PREFIX} Team Online: {len(online_members)} Offline: {', '.join(offline_members)}"
        )

    async def _handle_help_command(self) -> None:
        await self.send_team_chat(
            f"{BOT_PREFIX} COMMANDS: !time(!t), !ja text, !us text, !pop, !member"
        )

    def _add_to_buffer(self, chat_message: ChatMessage) -> None:
        self.talk_buffer.append({
            "name": chat_message.name,
            "message": chat_message.message
        })

    async def connect_session(self) -> bool:
        if self.rust_socket:
            await self.rust_socket.connect()
            return True
        return False

    async def disconnect_session(self) -> bool:
        if self.rust_socket:
            await self.rust_socket.disconnect()
            return True
        return False

    async def get_server_info(self) -> Any:
        return await self.rust_socket.get_info()

    async def get_server_time(self) -> Any:
        return await self.rust_socket.get_time()

    async def get_server_markers(self) -> Any:
        return await self.rust_socket.get_markers()

    async def get_team_info(self) -> Any:
        return await self.rust_socket.get_team_info()

    async def send_team_chat(self, content: str) -> None:
        await self.rust_socket.send_team_message(content)

    def get_talk_buffer(self) -> List[Dict[str, str]]:
        talk_buffer = self.talk_buffer
        self.talk_buffer = []
        return talk_buffer
