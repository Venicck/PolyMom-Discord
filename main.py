import discord, os, json, time, asyncio, re, sys
from discord.ext import tasks
from discord import app_commands
from discord.ext import commands

#region 初期変数

bot = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(bot)
path_json = "./data.json"
admins = ["302957994675535872", "711540575043715172", "747726536844771350"]
data={}
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # 顔の絵文字
    "\U0001F300-\U0001F5FF"  # 記号・天気・物
    "\U0001F680-\U0001F6FF"  # 乗り物
    "\U0001F1E6-\U0001F1FF"  # 国旗
    "\U00002700-\U000027BF"  # その他記号
    "\U0001F900-\U0001F9FF"  # 装飾的な顔など
    "\U00002600-\U000026FF"  # 太陽など
    "]+"
)
time.timezone = 32400 # JST

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
    vars=["target_forum", "log_channel", "cmd_channel"]
    for dist in dists:
        if dist not in data:
            data[dist] = {}
    for var in vars:
        if var not in data:
            data[var] = ""
    Save()

#region 絵文字の判定
def is_discord_emoji(s: str) -> bool:
    # Discordのカスタム絵文字（静止 or アニメ）
    return bool(re.fullmatch(r"<a?:\w+:\d+>", s))

def is_unicode_emoji(s: str) -> bool:
    return bool(emoji_pattern.fullmatch(s))

#region 便利関数

async def Reply(itr: discord.Interaction, type:int, title: str, message: str, private: bool = False):
    """type: {0:成功,1:情報,2:エラー}"""
    colors = [discord.Color.green(), discord.Color.blue(), discord.Color.red()]
    emb = discord.Embed(title=title, description=message, color=colors[type])
    return await itr.response.send_message(embed=emb, ephemeral=private)

async def Thread_Refresh():
    global data
    for emoji in data["notice_group"]:
        channel = bot.get_channel(int(data["notice_group"][emoji]["thread_id"]))
        if channel is None:
            del data["notice_group"][emoji]
            Save()
            LogCh(data["log_channel"], f"{emoji} のスレッドが見つかりませんでした。\n不具合を防ぐためコマンドから削除するようにしてください。")

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
    colors = ["\033[32m", "\033[36m", "\033[31m", "\033[37m"]
    print(f"[{time.strftime('%Y/%m/%d %H:%M:%S')}] {colors[type]} {string} \033[0m")

#region イベント
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    activity = "元気に動いてるわよ"
    await bot.change_presence(activity=discord.CustomActivity(name=activity))
    await tree.sync()
    await Thread_Refresh()
    Check_expires.start()


@bot.event
async def on_message(msg):
    if (msg.author.id == 302957994675535872):
        if msg.content == "--stop":
            await msg.add_reaction("💤")
            Check_expires.stop()
            await bot.close()
            await asyncio.sleep(2)
    
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    em = str(payload.emoji)
    if em in data["notice_group"]:
        channel = bot.get_channel(int(data["notice_group"][em]["thread_id"]))
        msg: discord.Message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if (channel is not None) and str(payload.message_id) not in data["notice_group"][em]["messages"]:
            embed = discord.Embed(title="", description = msg.content, color=discord.Color.blue())
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar.url)
            forward = await channel.send(embed=embed, view=ViewForForward(msg.jump_url), files=msg.attachments)
            data["notice_group"][em]["messages"][str(payload.message_id)] = {
                "forwarded_msg_id": str(forward.id),
                "msg_channel_id": str(payload.channel_id),
                "user_id": str(payload.user_id),
                "created_at": str(time.time())
            }
            Save()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドは管理者のみ使用できます")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"このコマンドは{int(error.retry_after)}秒後に再実行できます")
    else:
        await bot.get_user(302957994675535872).send(f"エラーが発生しました: \n```{str(error)}```")

@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(title="サーバーへの追加ありがとう！", description="やることリストを提供するね！", color=discord.Color.green())
    embed.add_field(name="1.フォーラムを作成", value="このボットがメインで動くフォーラムを作成してね！")
    embed.add_field(name="2. フォーラムを指定", value="`/set_forum` を使って1.のフォーラムを指定してね！")
    embed.add_field(name="これで完了！", value="自動的にフォーラムに`コマンドライン`と`ログ`スレッドを追加するよ！")
    await guild.owner.send(embed=embed)
    
#region UI系

class ExpireModal(discord.ui.Modal, title="有効期限を設定してください"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="日付を入力", placeholder="YYYY/MM/DD (1月1日なら 01/01)", required=True, min_length=10,max_length=10))
        self.add_item(discord.ui.TextInput(label="時間を入力", placeholder="HH:MM (未入力の場合はその日の23:59)", required=False, min_length=5,max_length=5))
    
    async def on_submit(self, itr: discord.Interaction):
        expire_at = f"{self.children[0].value} {self.children[1].value}" if self.children[1].value != "" else self.children[0].value
        try:
            if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at) or re.fullmatch(r"\d{4}/\d{2}/\d{2}", expire_at):
                if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at):
                    expire = time.mktime(time.strptime(expire_at, "%Y/%m/%d %H:%M"))
                else:
                    expire = time.mktime(time.strptime(expire_at, "%Y/%m/%d"))
                    expire += 86400 # 1日後に設定(翌日になったら削除)
                
                if expire < time.time():
                    itr.command_failed = True
                    await Reply(itr,2, "エラー", "有効期限が過去の時間です", True)
                else:
                    is_found = False
                    for emoji in data["notice_group"]:
                        for message in data["notice_group"][emoji]["messages"]:
                            if data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"] == str(itr.message.id):
                                data["notice_group"][emoji]["messages"][message]["expire_at"] = expire
                                is_found = True
                                Save()
                                msg = await bot.get_channel(int(data["notice_group"][emoji]["messages"][message]["msg_channel_id"])).fetch_message(int(message))
                                await itr.message.edit(view=WaitingExpire(expire_at, msg.jump_url))
                                await Reply(itr, 0, "成功", f"{expire_at} に有効期限を設定しました", True)
                                break
                    if not is_found:
                        itr.command_failed = True
                        await Reply(itr,2, "エラー", "そのメッセージは転送されたものではありません\nスレッドに転送されたメッセージのリンクを指定してください", True)
            else:
                itr.command_failed = True
                await Reply(itr,2, "エラー", "有効期限の書式が間違っています\nYYYY/MM/DD HH:MM または YYYY/MM/DD の書式で指定してください", True)
                
        except commands.MessageNotFound:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "メッセージの取得に失敗しました", True)

class ViewForForward(discord.ui.View):
    def __init__(self, jump_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="メッセージを開く", style=discord.ButtonStyle.link, url=jump_url))
        
    @discord.ui.button(label="有効期限を設定", style=discord.ButtonStyle.primary)
    async def SetExpire(self, itr: discord.Interaction, button: discord.ui.Button):
        await itr.response.send_modal(ExpireModal())

class WaitingExpire(discord.ui.View):
    def __init__(self, expire_at: str, jump_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="メッセージを開く", style=discord.ButtonStyle.link, url=jump_url))
        self.add_item(discord.ui.Button(label=f"{expire_at} に削除されます", style=discord.ButtonStyle.grey, disabled=True))
    
#region コマンド

@tree.command(name='help', description="このボットの使い方を表示します")
async def help(itr: discord.Interaction):
    await Reply(itr, 1, "このボットの使い方！", "このボットがある絵文字リアクションがついたメッセージをスレッドに転送する便利ボット！\n\n`/add_thread` で絵文字とスレッドを連携させてね！\n`/remove_thread` で絵文字とスレッドの連携を解除できるよ！\n`/expire` でスレッド内のメッセージの有効期限を設定できるよ！\n\n`/stats` でボイチャの状態を確認できるよ！", False)

@tree.command(name='reload', description="jsonファイルを再読み込みします")
async def reload(itr: discord.Interaction):
    if str(itr.user.id) in admins:
        await Thread_Refresh()
        Load()
        await Reply(itr, 0, "完了", "jsonファイルを再読み込みしました", True)
    else:
        itr.command_failed = True
        await Reply(itr, 2, "エラー", "このコマンドは管理者のみ使用できます", True)

@tree.command(name='add_thread', description="絵文字に対応するスレッドを作成します")
@app_commands.describe(emoji = "絵文字1文字", thread_name = "スレッド名")
async def add_thread(itr: discord.Interaction, emoji: str, thread_name: str):
    global data
    if data["target_forum"] == "":
        await Reply(itr, 2, "エラー", "スレッドを作成するためのフォーラムが設定されていません")
    else:
        if not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
            itr.command_failed = True
            await Reply(itr, 2, "エラー", "絵文字が適正ではありません")
        elif emoji in data["notice_group"]:
            await Reply(itr, 2, "エラー", "その絵文字は既に使われています")
        else:
            forum = bot.get_channel(int(data["target_forum"]))
            if forum is None:
                await Reply(itr, 2, "エラー", "フォーラムが見つかりませんでした")
                return
            if not isinstance(forum, discord.ForumChannel):
                await Reply(itr, 2, "エラー", "設定で指定されているフォーラムidが適切ではありません")
            else:
                thread = await forum.create_thread(name=thread_name, reason="絵文字と連携したスレッドを作成", content=f"このスレッドには {emoji} のリアクションがつけられたメッセージが自動で転送されます。\nスレッドの作成者: {itr.user.mention}")
                data["notice_group"][str(emoji)] = {
                    "owner": str(itr.user.id),
                    "thread_id": str(thread.thread.id),
                    "created_at": str(time.time()),
                    "messages":{}
                }
                Save()
                await Reply(itr, 0, "スレッドを作成しました。", f"{thread.thread.mention} に {emoji} のリアクションがつけられたメッセージが自動転送されるようになりました。")
                await bot.get_channel(int(data["log_channel"])).send(f"{emoji} ➤ {thread.thread.mention} 連携スレッドが作成されました。")

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
            thread = bot.get_channel(int(data["notice_group"][emoji]["thread_id"]))
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
        if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at) or re.fullmatch(r"\d{4}/\d{2}/\d{2}", expire_at):
            if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at):
                expire = time.mktime(time.strptime(expire_at, "%Y/%m/%d %H:%M"))
            else:
                expire = time.mktime(time.strptime(expire_at, "%Y/%m/%d"))
                expire += 86400 # 1日後に設定(翌日になったら削除)
            
            if expire < time.time():
                itr.command_failed = True
                await Reply(itr,2, "エラー", "有効期限が過去の時間です")
            else:
                is_found = False
                msg = discord.Message()
                for emoji in data["notice_group"]:
                    for message in data["notice_group"][emoji]["messages"]:
                        if data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"] == msg_link.split("/")[-1]:
                            data["notice_group"][emoji]["messages"][message]["expire_at"] = expire
                            is_found = True
                            Save()
                            msg_forward = await bot.get_channel(int(data["notice_group"][emoji]["thread_id"])).fetch_message(int(data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"]))
                            msg = await bot.get_channel(int(data["notice_group"][emoji]["messages"][message]["msg_channel_id"])).fetch_message(int(message))
                            await Reply(itr,0, "成功", f"メッセージの有効期限を{expire_at}に設定しました")
                            await msg_forward.edit(view=WaitingExpire(expire_at, msg.jump_url))
                            break
                if not is_found:
                    itr.command_failed = True
                    await Reply(itr,2, "エラー", "そのメッセージは転送されたものではありません\nスレッドに転送されたメッセージのリンクを指定してください")
        else:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "有効期限の書式が間違っています\nYYYY/MM/DD HH:MM または YYYY/MM/DD の書式で指定してください")
            
    except commands.MessageNotFound:
        itr.command_failed = True
        await Reply(itr,2, "エラー", "メッセージの取得に失敗しました")

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
    if not str(itr.user.id) in admins:
        itr.command_failed = True
        await Reply(itr,2, "エラー", "このコマンドは管理者のみ使用できます", False)
    else:
        log_channel = await forum.create_thread(name="ログ", reason="コマンドによる作成", content=f"このスレッドは{bot.user.mention} のログチャンネルです\n絵文字連携の追加、削除等の通知が行われます。")
        cmd_channel = await forum.create_thread(name="コマンドライン", reason="コマンドによる作成", content=f"このスレッドは{bot.user.mention} のコマンド実行用チャンネルです\n使い方は`/help`から見ることができます。")
        data["target_forum"] = str(forum.id)
        data["log_channel"] = str(log_channel.thread.id)
        data["cmd_channel"] = str(cmd_channel.thread.id)
        Save()
        await Reply(itr, 0, "成功", f"フォーラムを{forum.mention}に設定しました", False)
        await bot.get_channel(int(data["log_channel"])).send(f"{bot.user.mention} のログが当チャンネルに送信されるようになりました。")
        await bot.get_channel(int(data["log_channel"])).send(embed=discord.Embed(title="ボットを使う時のご注意", description="このフォーラムにスレッドをコマンドを使わずにスレッドを作成しても\n絵文字リアクションとの連携機能は使用できないので\n必ずコマンドを使ってスレッドを作成してください。", color=discord.Color.blue()))

#region 期限切れメッセージの動作

@tasks.loop(seconds=5)
async def Check_expires():
    global data
    now = time.time()
    is_changed = False
    for emoji in data["notice_group"]:
        i = 0
        to_delete = []
        for message in data["notice_group"][emoji]["messages"]:
            if "expire_at" in data["notice_group"][emoji]["messages"][message]:
                if now > float(data["notice_group"][emoji]["messages"][message]["expire_at"]):
                    try:
                        msg = await bot.get_channel(int(data["notice_group"][emoji]["thread_id"])).fetch_message(int(data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"]))
                        await msg.delete()
                        i += 1
                    except:
                        pass
                    to_delete.append(message)
                    is_changed = True
        for msg in to_delete:
            del data["notice_group"][emoji]["messages"][msg]
        if i > 0:
            await  bot.get_channel(int(data["log_channel"])).send(f"{emoji} の有効期限の切れた転送メッセージを削除しました")
    await Thread_Refresh()
    if is_changed:
        Save()

Load()

# token = os.getenv("DISCORD_TOKEN")
import Ptoken
bot.run(Ptoken.get())