from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed
from rust import rust_client
import json
import datetime


class Main(commands.Cog):
    def __init__(self, bot):
        self.config_json = json.load(open('./config.json', 'r'))
        self.channel_id = self.config_json["channel_id"]
        self.talk_channel_id = self.config_json["talk_channel_id"]
        self.bot = bot
        self.size = 4000
        self.server_event = []
        self.dead_list = []
        self.send_events = True

    def dump_config(self):
        with open("./config.json", "w", encoding="utf-8") as f:
            json.dump(self.config_json, f, indent=2)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[Cogs] Maincogs is ready.")
        if self.channel_id:
            self.channel_message = await self.get_channel_message()
        server_details = self.config_json["server_details"]
        self.rust_client = rust_client(server_details["ip"], server_details["port"], server_details["player_id"], server_details["player_token"])
        result = await self.rust_client.connect_session()
        if result:
            # 定期リスナーを実行します。
            self.refresh_message.start()
            self.event_listener.start()
        else:
            print("Failed Server Connection")

    @app_commands.command(name="setup_channel", description="チャンネルを設定します")
    async def setup_channel(self, interaction: Interaction):
        await interaction.response.send_message(f"チャンネルを{interaction.channel.name}に設定しました", ephemeral=True)
        self.config_json["channel_id"] = interaction.channel_id
        self.dump_config()
        self.channel_id = interaction.channel_id
        self.channel_message = await self.get_channel_message()

    @app_commands.command(name="setup_talk_channel", description="トークチャンネルを設定します")
    async def setup_talk_channel(self, interaction: Interaction):
        await interaction.response.send_message(f"トークチャンネルを{interaction.channel.name}に設定しました", ephemeral=True)
        self.config_json["talk_channel_id"] = interaction.channel_id
        self.dump_config()
        self.talk_channel_id = interaction.channel_id

    @app_commands.command(name="toggle_event", description="イベントの送信を切り替えます")
    async def toggle_event(self, interaction: Interaction):
        self.send_events = not self.send_events
        status = "enabled" if self.send_events else "disabled"
        await interaction.response.send_message(f"Event sending is now {status}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        # DiscordChatに書かれた内容をチームチャットに送信します。
        if int(message.channel.id) == self.talk_channel_id:
            await self.rust_client.send_team_chat(f"[DISCORD] {message.author.global_name}: {message.content}")

    async def get_channel_message(self):
        channel = self.bot.get_channel(self.channel_id)
        messages = channel.history(limit=100)
        async for message in messages:
            if message.author == self.bot.user:
                return message
        message = await channel.send("Not Found Message")
        return message

    @tasks.loop(seconds=1)
    async def event_listener(self):
        try:
            # 一秒おきにTeamChatを取得しDiscordに送信します。
            talk_channel = self.bot.get_channel(self.talk_channel_id)
            talk_buffer = self.rust_client.get_talk_buffer()
            for talk in reversed(talk_buffer):
                await talk_channel.send(f"{talk['name']}: {talk['message']}")
            # チームメンバーが死んださいにメッセージを送信します
            team_info = await self.rust_client.get_team_info()
            for member in team_info.members:
                if member.is_alive is False:
                    if member.steam_id not in self.dead_list:
                        self.dead_list.append(member.steam_id)
                        grid = await self.getGrid(member.x, member.y)
                        if self.send_events:
                            await talk_channel.send(f"{member.name} is dead ({grid})")
                            await self.rust_client.send_team_chat(f"[RUSTBOT] {member.name} is dead ({grid})")
                else:
                    if member.steam_id in self.dead_list:
                        self.dead_list.remove(member.steam_id)
        except Exception as e:
            print("Return Error: " + str(e))

    @tasks.loop(seconds=10)
    async def refresh_message(self):
        try:
            # 10秒おきにデータを取得しEmbedを更新します。
            embed = await self.get_embed()
            await self.channel_message.edit(content="", embed=embed)
        except Exception as e:
            print("Return Error: " + str(e))

    async def get_server_data(self):
        data = {}
        try:
            server_info = await self.rust_client.get_server_info()
            server_time = await self.rust_client.get_server_time()
            team_info = await self.rust_client.get_team_info()

            # サーバーMapサイズを取得します(Get mapsize)
            self.size = server_info.size

            # チーム情報を取得します(Get team info)
            online_member = []
            offline_member = []
            team_leader = None
            for member in team_info.members:
                if member.steam_id == team_info.leader_steam_id:
                    team_leader = member.name
                if member.is_online:
                    online_member.append(f"{member.name}({await self.getGrid(member.x, member.y)})")
                else:
                    offline_member.append(f"{member.name}({await self.getGrid(member.x, member.y)})")

            # サーバーイベントを取得します(Get Server event)
            server_markers = await self.rust_client.get_server_markers()
            server_events = []
            for marker in server_markers:
                if marker.type == 2:
                    server_events.append(f"Explosion({await self.getGrid(marker.x, marker.y)})")
                # elif marker.type == 4:
                #     server_events.append(f"CH-47({await self.getGrid(marker.x, marker.y)})")
                elif marker.type == 5:
                    server_events.append(f"CargoShip({await self.getGrid(marker.x, marker.y)})")
                elif marker.type == 6:
                    server_events.append(f"Crate({await self.getGrid(marker.x, marker.y)})")
                elif marker.type == 8:
                    server_events.append(f"PatrolHelicopter({await self.getGrid(marker.x, marker.y)})")

            data["server_name"] = server_info.name
            data["server_players"] = str(server_info.players) + "/" + str(server_info.max_players) + "(" + str(server_info.queued_players) + ")"
            data["server_time"] = server_time.time
            data["server_sun_time"] = server_time.sunrise + " - " + server_time.sunset
            data["team_leader"] = team_leader
            data["online_member"] = online_member
            data["offline_member"] = offline_member
            data["server_events"] = server_events
        except:
            return
        return data

    async def getGrid(self, loc_x, loc_y):
        text = ""
        x = int(loc_x / 146.28571428571428)
        y = int((self.size - loc_y) / 146.28571428571428)

        x1 = int(x / 26)
        x2 = x % 26

        if x1 > 0:
            for x in range(x1):
                text += chr(65 + x)

        text += chr(65 + x2) + str(y)

        return str(text)

    async def get_embed(self):
        data = await self.get_server_data()
        if data:
            self.retry_count = 0
            talk_channel = self.bot.get_channel(self.talk_channel_id)
            embed = Embed(title=data["server_name"], description="")
            embed.add_field(name="プレイヤー数 現在/最大(待機)", value=data["server_players"], inline=False)
            embed.add_field(name="サーバー内時間", value=data["server_time"], inline=True)
            embed.add_field(name="日の出 - 日没", value=data["server_sun_time"], inline=True)
            embed.add_field(name="サーバーイベント", value=', '.join(map(str, data["server_events"])), inline=False)
            embed.add_field(name="チームリーダー", value=data["team_leader"], inline=False)
            embed.add_field(name="オンライン", value=', '.join(map(str, data["online_member"])), inline=False)
            embed.add_field(name="オフライン", value=', '.join(map(str, data["offline_member"])), inline=False)
            embed.add_field(name="更新時間", value=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
            if self.send_events:
                for event in data["server_events"]:
                    if event not in self.server_event:
                        await talk_channel.send(f"[RUSTBOT] {event}")
                        await self.rust_client.send_team_chat(f"[RUSTBOT] {event}")
            self.server_event = data["server_events"]
            return embed
        else:
            self.retry_count += 1
            embed = Embed(title=f"接続に失敗しました。({self.retry_count} 回目)", description="")
            await self.rust_client.connect_session()
            return embed

async def setup(bot):
    await bot.add_cog(Main(bot))
