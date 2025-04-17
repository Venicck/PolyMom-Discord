import discord, os, json, time
from discord.ext import tasks
from discord import app_commands

# 初期変数

bot = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(bot)
path_json = "./data.json"
admins = ["302957994675535872", "711540575043715172", "747726536844771350"]
data={}

def Load():
    global data
    with open(path_json, "r", encoding="utf-8_sig") as f:
        data = json.load(f)
        Initialize()
        print("json file loaded")

def Save():
    global data 
    with open(path_json, "w", encoding="utf-8_sig") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        print("json file saved")

def Initialize():
    global data
    dists=["notice_group"]
    vars=["target_forum"]
    for dist in dists:

        if dist not in data:
            data[dist] = {}
    for var in vars:
        if var not in data:
            data[var] = ""
    Save()

Load()

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    activity = "元気に動いてるわよ"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name=activity))
    await tree.sync()

@bot.event
async def on_reaction_add(reaction, user):
    print()

@tree.command(name='add_thread', description="絵文字に対応するスレッドを作成します")
async def add_thread(interaction: discord.Interaction, emoji: str, thread_name: str):
    global data
    if data["target_forum"] == "":
        await interaction.response.send_message("スレッドを作成するためのフォーラムが設定されていません")
    else:
        if emoji in data["notice_group"]:
            await interaction.response.send_message("その絵文字は既に使われています")
        else:
            forum = bot.get_channel(int(data["target_forum"]))
            if not isinstance(forum, discord.ForumChannel):
                await interaction.response.send_message("設定で指定されているフォーラムidが適切ではありません")
            else:
                thread = await forum.create_thread(name="テスト")
                if forum is None:
                    await interaction.response.send_message("フォーラムが見つかりませんでした")
                else:  
                    data["notice_group"][emoji] = {}
                    _temp ={"owner": str(interaction.user.id),
                            "thread_id": str(thread.id)
                           }
                    await interaction.response.send_message("")
@tree.command(name='remove_thread', description="絵文字に対応するスレッドを削除します")
async def remove_thread(interaction: discord.Interaction, emoji: str):
    await interaction.response.send_message("")
@tree.command(name='expire', description="スレッド内のメッセージの有効期限を設定できます")
async def expire(interaction: discord.Interaction, message_link: str, expire_at: str):
    await interaction.response.send_message("")
@tree.command(name='stats', description="指定されたチャンネルの状態を確認できます")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message("")
@tree.command(name='set_forum',description="このボットがメインで動くフォーラムを指定します")
async def set_forum(interaction: discord.Interaction):
    await interaction.response.send_message("")

@tasks.loop(seconds=15)
async def Check_expires():
    print()

token = os.getenv("DISCORD_TOKEN")
if token is not None:
    bot.run(token)