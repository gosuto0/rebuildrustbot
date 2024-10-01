from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed
import json
import datetime

class Main(commands.Cog):
    def __init__(self, bot):
        self.config_json = json.load(open('./config.json', 'r'))
        self.channel_id = self.config_json["channel_id"]
        self.bot = bot

    def dump_config(self):
        with open("./config.json", "w", encoding="utf-8") as f:
            json.dump(self.config_json, f, indent=2)

    @commands.Cog.listener()
    async def on_ready(self):
        print("[Cogs] Maincogs is ready.")
        if self.channel_id:
            self.channel_message = await self.get_channel_message()
        self.refresh_message.start()
    @app_commands.command(name="setup_channel", description="チャンネルを設定します")
    async def setup_channel(self, interaction: Interaction):
        await interaction.response.send_message(f"チャンネルを{interaction.channel.name}に設定しました", ephemeral=True)
        self.config_json["channel_id"] = interaction.channel_id
        self.dump_config()
        self.channel_id = interaction.channel_id
        self.channel_message = await self.get_channel_message()
        
    async def get_channel_message(self):
        channel = self.bot.get_channel(self.channel_id)
        messages = channel.history(limit=100)
        async for message in messages:
            if message.author == self.bot.user:
                return message
        message = await channel.send("Not Found Message")
        return message

    @tasks.loop(seconds=3)
    async def refresh_message(self):
        try:
            embed = await self.get_embed()
            await self.channel_message.edit(content="", embed=embed)

        except Exception as e: print("Return Error: "+str(e))

    async def refresh_data(self):
        self.server_info = await self.bot.rust_class.get_serverinfo()
        self.server_time = await self.bot.rust_class.get_servertime()
        try:
            self.server_infoorg = str(self.server_info.players)+"/"+str(self.server_info.max_players)+"("+str(self.server_info.queued_players)+")"
            self.server_nameorg = self.server_info.name
            self.server_timeorg = self.server_time.time
            self.server_sunorg = self.server_time.sunrise+" - "+self.server_time.sunset
            self.server_event = await self.organize_serverevent()
            self.server_wipe = datetime.datetime.fromtimestamp(self.server_info.wipe_time)+ datetime.timedelta(days=30)
        except Exception as e:
            self.server_infoorg = "Cant get data"
            self.server_timeorg = "Cant get data"
            self.server_nameorg = "Cant get data"
            self.server_sunorg = "Cant get data"
            self.server_event = "Cant get data"
            self.server_wipe = "Cant get data"
            self.attack_heli = "Cant get data"
            
    async def organize_serverevent(self):
        server_event = await self.bot.rust_class.get_serverevent()
        event_strlist = ""
        event_list = []
        dt_now = datetime.datetime.now()
        dt_after1 = datetime.datetime.now()+datetime.timedelta(hours=3)
        for event in server_event:
            event_list.append(str(event.type))
            if event.type == 4:
                event_strlist = event_strlist+"CH-47, "
            if event.type == 5:
                event_strlist = event_strlist+"貨物船, "
            if event.type == 8:
                event_strlist = event_strlist+"アタックヘリコプター, "
                self.now_attack_heli = True
        if "8" not in event_list:
            if self.now_attack_heli == True:
                if event.type != 8:
                    self.now_attack_heli = False
                    self.attack_heli = "アタヘリ爆発 "+str(dt_now.strftime('%H:%M:%S'))+" 再沸き "+str(dt_after1.strftime('%H:%M:%S'))
        if event_strlist == "":
            return "No Event"
        return event_strlist
                
    async def get_embed(self):
        await self.refresh_data()
        embed = Embed(title=self.server_nameorg,description="")
        embed.add_field(name="プレイヤー数 現在/最大(待機)", value=self.server_infoorg,inline=False)
        embed.add_field(name="サーバー内時間",value=self.server_timeorg,inline=False)
        embed.add_field(name="日の出 - 日没",value=self.server_sunorg,inline=False)
        embed.add_field(name="現在のイベント",value=self.server_event,inline=False)
        embed.add_field(name="ワイプ",value=self.server_wipe,inline=False)
        embed.add_field(name="アタックヘリ", value=self.attack_heli,inline=False)
        return embed
async def setup(bot):    
    await bot.add_cog(Main(bot))