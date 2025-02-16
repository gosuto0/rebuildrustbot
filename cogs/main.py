from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed
from .constants import *
from .event_handler import EventHandler
from rust import RustClient
import json
import datetime
from typing import Optional, Dict, List


class Main(commands.Cog):
    def __init__(self, bot):
        self._load_config()
        self.bot = bot
        self.size = DEFAULT_MAP_SIZE
        self.event_handler = EventHandler()
        self.send_events = True
        self.channel_message = None
        self.rust_client = None
        self.retry_count = 0

    def _load_config(self):
        with open('./config.json', 'r') as f:
            self.config_json = json.load(f)
        self.channel_id = self.config_json["channel_id"]
        self.talk_channel_id = self.config_json["talk_channel_id"]

    def _save_config(self):
        with open("./config.json", "w", encoding="utf-8") as f:
            json.dump(self.config_json, f, indent=2)

    async def initialize_rust_client(self) -> bool:
        server_details = self.config_json["server_details"]
        self.rust_client = RustClient(
            server_details["ip"],
            server_details["port"],
            server_details["player_id"],
            server_details["player_token"]
        )
        return await self.rust_client.connect_session()

    @commands.Cog.listener()
    async def on_ready(self):
        print("[Cogs] Maincogs is ready.")
        if self.channel_id:
            self.channel_message = await self._get_channel_message()

        if await self.initialize_rust_client():
            self.refresh_message.start()
            self.event_listener.start()
        else:
            print("Failed Server Connection")

    @app_commands.command(name="setup_channel", description="チャンネルを設定します")
    async def setup_channel(self, interaction: Interaction):
        await interaction.response.send_message(
            f"チャンネルを{interaction.channel.name}に設定しました",
            ephemeral=True
        )
        self.config_json["channel_id"] = interaction.channel_id
        self._save_config()
        self.channel_id = interaction.channel_id
        self.channel_message = await self._get_channel_message()

    @app_commands.command(name="setup_talk_channel", description="トークチャンネルを設定します")
    async def setup_talk_channel(self, interaction: Interaction):
        await interaction.response.send_message(
            f"トークチャンネルを{interaction.channel.name}に設定しました",
            ephemeral=True
        )
        self.config_json["talk_channel_id"] = interaction.channel_id
        self._save_config()
        self.talk_channel_id = interaction.channel_id

    @app_commands.command(name="toggle_event", description="イベントの送信を切り替えます")
    async def toggle_event(self, interaction: Interaction):
        self.send_events = not self.send_events
        status = "enabled" if self.send_events else "disabled"
        await interaction.response.send_message(
            f"Event sending is now {status}",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if int(message.channel.id) == self.talk_channel_id:
            await self.rust_client.send_team_chat(
                f"[DISCORD] {message.author.global_name}: {message.content}"
            )

    async def _get_channel_message(self):
        channel = self.bot.get_channel(self.channel_id)
        async for message in channel.history(limit=100):
            if message.author == self.bot.user:
                return message
        return await channel.send("Not Found Message")

    @tasks.loop(seconds=EVENT_CHECK_INTERVAL)
    async def event_listener(self):
        try:
            talk_channel = self.bot.get_channel(self.talk_channel_id)

            for talk in reversed(self.rust_client.get_talk_buffer()):
                await talk_channel.send(f"{talk['name']}: {talk['message']}")

            team_info = await self.rust_client.get_team_info()
            for member in team_info.members:
                grid = await self.get_grid(member.x, member.y)
                death_message = self.event_handler.handle_death_event(member, grid)
                if death_message and self.send_events:
                    await talk_channel.send(death_message)
                    await self.rust_client.send_team_chat(f"[RUSTBOT] {death_message}")

        except Exception as e:
            print(f"Event listener error: {str(e)}")

    @tasks.loop(seconds=REFRESH_INTERVAL)
    async def refresh_message(self):
        try:
            embed = await self._create_status_embed()
            await self.channel_message.edit(content="", embed=embed)
        except Exception as e:
            print(f"Refresh error: {str(e)}")

    async def _get_server_data(self) -> Optional[Dict]:
        try:
            server_info = await self.rust_client.get_server_info()
            server_time = await self.rust_client.get_server_time()
            team_info = await self.rust_client.get_team_info()

            self.size = server_info.size

            online_members = []
            offline_members = []
            team_leader = None

            for member in team_info.members:
                grid = await self.get_grid(member.x, member.y)
                member_info = f"{member.name}({grid})"

                if member.steam_id == team_info.leader_steam_id:
                    team_leader = member.name

                if member.is_online:
                    online_members.append(member_info)
                else:
                    offline_members.append(member_info)

            server_markers = await self.rust_client.get_server_markers()
            events = await self.event_handler.handle_server_events(
                server_markers,
                self.get_grid
            )

            return {
                "server_name": server_info.name,
                "server_players": f"{server_info.players}/{server_info.max_players}({server_info.queued_players})",
                "server_time": server_time.time,
                "server_sun_time": f"{server_time.sunrise} - {server_time.sunset}",
                "team_leader": team_leader,
                "online_member": online_members,
                "offline_member": offline_members,
                "server_events": [f"{e.type}({e.location})" for e in events]
            }

        except Exception:
            return None

    async def get_grid(self, loc_x: float, loc_y: float) -> str:
        x = int(loc_x / MAP_GRID_SIZE)
        y = int((self.size - loc_y) / MAP_GRID_SIZE)

        x1, x2 = divmod(x, 26)
        grid = ''.join(chr(65 + i) for i in range(x1))
        grid += chr(65 + x2) + str(y)

        return grid

    async def _create_status_embed(self) -> Embed:
        data = await self._get_server_data()
        if not data:
            self.retry_count += 1
            embed = Embed(
                title=f"接続に失敗しました。({self.retry_count} 回目)",
                description=""
            )
            await self.rust_client.connect_session()
            return embed

        self.retry_count = 0
        talk_channel = self.bot.get_channel(self.talk_channel_id)

        embed = Embed(title=data["server_name"], description="")
        embed.add_field(name="プレイヤー数 現在/最大(待機)", value=data["server_players"], inline=False)
        embed.add_field(name="サーバー内時間", value=data["server_time"], inline=True)
        embed.add_field(name="日の出 - 日没", value=data["server_sun_time"], inline=True)
        embed.add_field(name="サーバーイベント", value=', '.join(data["server_events"]), inline=False)
        embed.add_field(name="チームリーダー", value=data["team_leader"], inline=False)
        embed.add_field(name="オンライン", value=', '.join(data["online_member"]), inline=False)
        embed.add_field(name="オフライン", value=', '.join(data["offline_member"]), inline=False)
        embed.add_field(name="更新時間", value=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)

        if self.send_events:
            current_events = set(data["server_events"])
            previous_events = set(getattr(self, 'server_event', []))
            new_events = current_events - previous_events

            for event in new_events:
                await talk_channel.send(f"[RUSTBOT] {event}")
                await self.rust_client.send_team_chat(f"[RUSTBOT] {event}")

        self.server_event = data["server_events"]
        return embed


async def setup(bot):
    await bot.add_cog(Main(bot))
