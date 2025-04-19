import discord, os, json, time, asyncio, sys, re
from discord.ext import tasks
from discord import app_commands
from discord.ext import commands

#region 初期変数

bot = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(bot)
path_json = "./data.json"
admins = ["302957994675535872", "711540575043715172", "747726536844771350"]
data={}

#region ファイル操作

def Load():
    global data
    if not os.path.exists(path_json):
        with open(path_json, "w", encoding="utf-8_sig") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
            LogSys(0,"json file created")
    try:
        with open(path_json, "r", encoding="utf-8_sig") as f:
            data = json.load(f)
            Initialize()
            LogSys(0,"json loaded")
    except Exception as e:
        LogSys(2,"json load failed")
        print(f"{type(e)} : {str(e)}")

def Save():
    global data 
    try:
        with open(path_json, "w", encoding="utf-8_sig") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            LogSys(0,"json saved")
    except Exception as e:
        LogSys(2,"json file save failed")
        print(f"{type(e)} : {str(e)}")

def Initialize():
    global data
    dists=["notice_group"]
    vars=["target_forum", "log_channel"]
    for dist in dists:
        if dist not in data:
            data[dist] = {}
    for var in vars:
        if var not in data:
            data[var] = ""
    Save()

Load()
time.timezone = 32400 # JST

#region 絵文字の判定
def is_discord_emoji(s: str) -> bool:
    # Discordのカスタム絵文字（静止 or アニメ）
    return bool(re.fullmatch(r"<a?:\w+:\d+>", s))

def is_unicode_emoji(s: str) -> bool:
    # Unicode絵文字（ざっくり判定：1〜2文字＋emoji判定）
    import emoji
    return s in emoji.EMOJI_DATA

#region 便利関数

async def Reply(itr: discord.Integration, type:int, title: str, message: str, public: bool = True):
    """type: {0:成功,1:情報,2:エラー}"""
    colors = [discord.Color.green(), discord.Color.blue(), discord.Color.red()]
    emb = discord.Embed(title=title, description=message, color=colors[type])
    await Reply(itr, 2, "エラー", embed=emb, ephemeral=not public)

async def LogCh(channel_id, string: str):
    """指定されたスレッドにメッセージを送信します"""
    channel = await bot.get_channel(int(channel_id))
    if channel is not None:
        try:
            await channel.send(string)
        except discord.Forbidden:
            pass

def LogSys(type:int, string: str):
    """type: {0:成功, 1:情報, 2:エラー, 3:その他}"""
    colors = ["\033[32", "\033[36", "\033[31", "\033[37"]
    print(f"[{time.strftime('%Y/%m/%d %H:%M:%S')}] {str(type)} | {colors[type]}{string}\033[0m")

#region イベント
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    activity = "元気に動いてるわよ"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=activity))
    await tree.sync()


@bot.event
async def on_message(msg):
    if (msg.author.id == 302957994675535872) and (bot.user in msg.mentions) and ("おやすみ" in msg.content):
        await msg.add_reaction("💤")
        await bot.close()
        await asyncio.sleep(2)
    
@bot.event
async def on_reaction_add(reaction, user):
    if reaction.emoji in data["notice_group"]:
        channel = await bot.get_channel(int(data["notice_group"][reaction.emoji]["thread_id"]))
        if channel is not None and reaction.message.id not in data["notice_group"][reaction.emoji]["messages"]:
            forward = await reaction.message.forward(channel)
            data["notice_group"][reaction.emoji]["messages"][reaction.message.id] = {
                "forwarded_msg_id": str(forward.id),
                "user_id": str(user.id),
                "created_at": str(time.time())
            }
            Save()
    await bot.process_commands(reaction)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドは管理者のみ使用できます")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"このコマンドは{int(error.retry_after)}秒後に再実行できます")
    else:
        await ctx.send(f"エラーが発生しました: {str(error)}")
    
#region コマンド

@tree.command(name='add_thread', description="絵文字に対応するスレッドを作成します")
@app_commands.describe(emoji = "絵文字1文字", thread_name = "スレッド名")
async def add_thread(itr: discord.Interaction, emoji: str, thread_name: str):
    global data
    if data["target_forum"] == "":
        await Reply(itr, 2, "エラー", "スレッドを作成するためのフォーラムが設定されていません")
    else:
        if emoji in data["notice_group"]:
            await Reply(itr, 2, "エラー", "その絵文字は既に使われています")
        elif not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
            await Reply(itr, 2, "エラー", "絵文字が適正ではありません")
        else:
            forum = bot.get_channel(int(data["target_forum"]))
            if not isinstance(forum, discord.ForumChannel):
                await Reply(itr, 2, "エラー", "設定で指定されているフォーラムidが適切ではありません")
            else:
                thread = await forum.create_thread(name=thread_name, reason="絵文字と連携したスレッドを作成", content=f"このスレッドには {emoji} のリアクションがつけられたメッセージが自動で転送されます。\nスレッドの作成者: {itr.user.mention}")
                if forum is None:
                    await Reply(itr, 2, "エラー", "フォーラムが見つかりませんでした")
                else:  
                    data["notice_group"][emoji] = {
                        "owner": str(itr.user.id),
                        "thread_id": str(thread.id),
                        "created_at": str(time.time()),
                        "messages":{}
                    }
                    await Reply(itr, 2, "エラー", "")

@tree.command(name='remove_thread', description="絵文字に対応するスレッドを削除します")
@app_commands.describe(emoji = "絵文字1文字")
async def remove_thread(itr: discord.Interaction, emoji: str):
    global data
    if not emoji in data["notice_group"]:
        itr.command_failed = True
        Reply(itr,2, "エラー", "その絵文字で登録されているスレッドはありません。")
    elif not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
        itr.command_failed = True
        await Reply(itr,2, "エラー", "絵文字が適正ではありません")
    elif not ((str(itr.user.id) not in admins) or str(itr.user.id) == data["notice_group"][emoji]["owner"]):
        itr.command_failed = True
        await Reply(itr,2, "エラー", "指定されたスレッドの所有者ではありません")
    else:
        try:
            thread = await bot.get_channel(int(data["notice_group"][emoji]["thread_id"]))
            await thread.delete(reason="コマンドによる削除")
            del data["notice_group"][emoji]
            Save()
            await Reply(itr,0, "成功", "スレッドを削除しました。")
        except:
            await Reply(itr,2, "エラー", "スレッドの削除に失敗しました。")
                
@tree.command(name='expire', description="スレッド内のメッセージの有効期限を設定できます")
@app_commands.describe(msg_link = "**転送された**メッセージのリンク", expire_at = "有効期限 (YYYY/MM/DD HH:MM or YYYY/MM/DD の書式)")
async def expire(itr: discord.Interaction, msg_link: str, expire_at: str):
    try:
        msg = await commands.MessageConverter(msg_link).convert(itr)
        if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at) or re.fullmatch(r"\d{4}/\d{2}/\d{2}", expire_at):
            if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at):
                expire_at = time.mktime(time.strptime(expire_at, "%Y/%m/%d %H:%M"))
            else:
                expire_at = time.mktime(time.strptime(expire_at, "%Y/%m/%d"))
                expire_at += 86400 # 1日後に設定(翌日になったら削除)
            
            if expire_at < time.time():
                itr.command_failed = True
                await Reply(itr,2, "エラー", "有効期限が過去の時間です")
            else:
                is_found = False
                for emoji in data["notice_group"]:
                    for message in data["notice_group"][emoji]["messages"]:
                        if data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"] == str(msg.id):
                            data["notice_group"][emoji]["messages"][message]["expire_at"] = str(expire_at)
                            is_found = True
                            Save()
                            break
                if is_found:
                    await Reply(itr,0, "成功", f"メッセージの有効期限を{expire_at}に設定しました")
                else:
                    itr.command_failed = True
                    await Reply(itr,2, "エラー", "そのメッセージは転送されたものではありません\nスレッドに転送されたメッセージのリンクを指定してください")
        else:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "有効期限の書式が間違っています\nYYYY/MM/DD HH:MM または YYYY/MM/DD の書式で指定してください")
            
    except commands.MessageNotFound:
        itr.command_failed = True
        await Reply(itr,2, "エラー", "メッセージの取得に失敗しました")
    except:
        itr.command_failed = True
        await Reply(itr,2, "エラー", "例外が発生しました")

@tree.command(name='stats', description="指定されたボイスチャットチャンネルの状態を確認できます")
@app_commands.describe(channel = "ボイスチャンネル")
async def stats(itr: discord.Interaction, channel: discord.VoiceChannel):
    members_with_bot = 0
    members_without_bot = 0
    members_muted = 0
    members_deafen = 0
    members_all_muted = 0
    members_bot = 0
    for user in channel.members:
        members_with_bot += 1
        if not user.bot:
            members_without_bot += 1
        else:
            members_bot += 1
        if user.voice.mute:
            members_muted += 1
        if user.voice.deaf:
            members_deafen += 1
        if user.voice.self_mute and user.voice.self_deaf:
            members_all_muted += 1
    await Reply(itr, 1, f"{channel.mention} の状態", f"通話中の人数:{members_with_bot}\n通話中の人数(Botを除く):{members_without_bot}\nBotの数:{members_bot}\nミュート中の人数:{members_muted}\nスピーカーミュート中の人数:{members_deafen}\n全ミュートの人数:{members_all_muted}")
    
@tree.command(name='set_forum', description="このボットがメインで動くフォーラムを指定します")
@app_commands.describe(forum = "フォーラムチャンネル")
async def set_forum(itr: discord.Interaction, forum: discord.ForumChannel):
    if not itr.user.id in admins:
        itr.command_failed = True
        await Reply(itr,2, "エラー", "このコマンドは管理者のみ使用できます")
    else:
        data["target_forum"] = str(forum.id)
        Save()
        await Reply(itr, 0, "成功", f"フォーラムを{forum.name}に設定しました")

#region 期限切れメッセージの動作

@tasks.loop(seconds=15)
async def Check_expires():
    global data
    now = time.time()
    for emoji in data["notice_group"]:
        for message in data["notice_group"][emoji]["messages"]:
            if "expire_at" in data["notice_group"][emoji]["messages"][message]:
                if now > float(data["notice_group"][emoji]["messages"][message]["expire_at"]):
                    try:
                        msg : discord.Message = await commands.MessageConverter(data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"]).convert(bot)
                        await msg.delete()
                        del data["notice_group"][emoji]["messages"][message]
                        Save()
                    except:
                        pass

# token = os.getenv("DISCORD_TOKEN")
import Ptoken
bot.run(Ptoken.get())