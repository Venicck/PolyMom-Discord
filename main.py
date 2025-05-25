import discord, os, json, time, asyncio, re, firebase_admin, random, requests, datetime, math
from bs4 import BeautifulSoup
from firebase_admin import credentials, firestore
from discord.ext import tasks
from discord import app_commands
from discord.ext import commands

#region 初期変数

cred_dict = json.loads(os.environ["FIREBASE"])
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()
bot = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(bot)
yahoo_url = "https://weather.yahoo.co.jp/weather/13/4410/13208.html"
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
msglogmode = False

#region ファイル操作

def Load():
    global data
    doc = db.collection("bot").document("data").get()
    if doc.exists:
        data = doc.to_dict()
        LogSys(0,"json loaded")
    Initialize()
    # if not os.path.exists(path_json):
    #     with open(path_json, "w", encoding="utf-8_sig") as f:
    #         json.dump({}, f, indent=4, ensure_ascii=False)
    #         LogSys(0,"json file created")
    # try:
    #     with open(path_json, "r", encoding="utf-8_sig") as f:
    #         data = json.load(f)
    #         Initialize()
    #         LogSys(0,"json loaded")
    # except Exception as e:
    #     LogSys(2,"json load failed")
    #     print(f"{type(e)} : {str(e)}")

def Save():
    global data
    db.collection("bot").document("data").set(data)
    LogSys(0,"json saved")
    # try:
    #     with open(path_json, "w", encoding="utf-8_sig") as f:
    #         json.dump(data, f, indent=4, ensure_ascii=False)
    #         LogSys(0,"json saved")
    # except Exception as e:
    #     LogSys(2,"json file save failed")
    #     print(f"{type(e)} : {str(e)}")

def Initialize(): # 変数の初期化
    global data
    dists={
        "notice_group": {},
        "weather": {
            "mention": ["", "", ""], # [0]: 朝 [1]: 昼 [2]: 夜 通知するメンション
            "notify_time": [21600, 43200, 64800], # [0]: 朝 [1]: 昼 [2]: 夜 通知する時間
            "day": ["today", "today", "tomorrow"], # [0]: 朝 [1]: 昼 [2]: 夜 今日の天気予報か明日の天気予報か
            "greetings": ["おはようございます。", "午後も頑張りましょう。", "こんばんは。"], #挨拶
            "msg_channel": "", # 通知を送信するチャンネル
            "last_noticed": 0 # 最後に通知したUnix時間
        }
    }
    vars=["target_forum", "log_channel", "cmd_channel"]
    for d in dists:
        if d not in data:
            data[d] = dists[d]
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
    colors = ["Success", "Info", "Error", "Other"]
    print(f"{time.strftime('%Y/%m/%d %H:%M:%S')} | {colors[type]} | {string} ")

def DaytimeToList(time : int):
    hours = time // 3600
    minutes = (time % 3600) // 60
    seconds = time % 60
    return [hours, minutes, seconds]

def Get_weather_yahoo():
    global yahoo_url
    weather_data = {}
    req = requests.get(yahoo_url)
    if req.status_code != 200:
        return {}
    else:
        soup = BeautifulSoup(req.text, "html.parser")
        weather_data["today"] = {}
        weather_tb = soup.select('#yjw_pinpoint_today > table > tbody > tr:nth-of-type(2)')
        temp_tb = soup.select('#yjw_pinpoint_today > table > tbody > tr:nth-of-type(3)')
        humid_tb = soup.select('#yjw_pinpoint_today > table > tbody > tr:nth-of-type(4)')
        rain_tb = soup.select('#yjw_pinpoint_today > table > tbody > tr:nth-of-type(5)')
        wind_tb = soup.select('#yjw_pinpoint_today > table > tbody > tr:nth-of-type(6)')
        for i in range(0, 8):
            weather_data["today"][f"{i*3} - {(i+1) * 3}"] = {
                "weather": weather_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "temp": temp_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "humidity": humid_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "rain": rain_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "wind": wind_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
            }
        weather_data["tomorrow"] = {}
        weather_tb = soup.select('#yjw_pinpoint_tomorrow > table > tbody > tr:nth-of-type(2)')
        temp_tb = soup.select('#yjw_pinpoint_tomorrow > table > tbody > tr:nth-of-type(3)')
        humid_tb = soup.select('#yjw_pinpoint_tomorrow > table > tbody > tr:nth-of-type(4)')
        rain_tb = soup.select('#yjw_pinpoint_tomorrow > table > tbody > tr:nth-of-type(5)')
        wind_tb = soup.select('#yjw_pinpoint_tomorrow > table > tbody > tr:nth-of-type(6)')
        for i in range(0, 8):
            weather_data["tomorrow"][f"{i*3} - {(i+1) * 3}"] = {
                "weather": weather_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "temp": temp_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "humidity": humid_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "rain": rain_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
                "wind": wind_tb[0].find_all('td')[i+1].text.replace("\n", "").replace(" ", ""),
            }
        return weather_data

def Make_embed_forecast(when = "today"):
    global yahoo_url
    weather_data = Get_weather_yahoo()
    if not weather_data:
        return None
    
    forecast_date = time.strftime("%Y/%m/%d") if when == "today" else time.strftime("%Y/%m/%d", time.localtime(time.time() + 86400))
    
    """サイドバーのカラーを天気で設定する"""
    do_mention = False
    sunny = 0
    rainy = 0
    snowy = 0
    cloudy = 0
    data = weather_data[when]
    for t in data:
        if data[t]["weather"] == "晴れ":
            sunny += 1
        elif "曇り" in data[t]["weather"]:
            cloudy += 1
        elif "雨" in data[t]["weather"]:
            rainy += 1
        elif "雪" in data[t]["weather"]:
            snowy += 1
    if (rainy == 0 and snowy == 0 and cloudy == 0):
        color = discord.Colour.orange()
    elif (rainy == 0 and snowy == 0 and cloudy > 0):
        color = discord.Colour.light_gray()
    elif (rainy > snowy):
        color = discord.Colour.blue()
        do_mention = True
    else:
        color = discord.Colour.from_rgb(255, 255, 255)
        do_mention = True
    embed = discord.Embed(title=f"{forecast_date} の天気予報 (東京都調布市)", color=color, description=f"3時間ごとの天気予報を[Yahoo!天気](<{yahoo_url}>)からお知らせします。")
    embed.set_footer(text=f"<t:{math.floor(time.time())}> 現在に取得")
    for t in data:
        embed.add_field(name=f"{t} 時", value=f"天気:{"晴れ" if weather_data[when][t]["weather"] == "晴れ" else f"**{weather_data[when][t]["weather"]}**"} \n気温: {weather_data[when][t]['temp']}℃\n湿度: {weather_data[when][t]['humidity']}%\n降水量: {weather_data[when][t]['rain']}\n風速: {weather_data[when][t]['wind']} [m/s]", inline=True)
    return (embed, do_mention)

#region イベント
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    activity = "元気に動いてるわよ"
    await bot.change_presence(activity=discord.CustomActivity(name=activity))
    await tree.sync()
    await Thread_Refresh()
    bot.add_view(ViewForForward())
    bot.add_view(WaitingExpire())
    bot.add_view(ExpireModal())
    Auto_Forecast.start()
    Check_expires.start()


@bot.event
async def on_message(msg):
    global data, msglogmode
    for mention in msg.mentions:
        if mention.id == bot.user.id:
            await msg.add_reaction("👀")
            break
    if (msg.author.id == 302957994675535872):
        if msg.content == "--stop":
            await msg.add_reaction("💤")
            Check_expires.stop()
            await bot.close()
            await asyncio.sleep(2)
        elif msg.content == "--msglog":
            msglogmode = not msglogmode
            if msglogmode:
                await msg.add_reaction("✅")
            else:
                await msg.add_reaction("❌")
        elif msg.content == "--export":
            file = open('data_temp.json', 'w', encoding='utf-8')
            file.write(json.dumps(data, indent=4, ensure_ascii=False))
            file.close()
            await msg.channel.send(f"jsonデータをエクスポートしました。", file=discord.File(fp='data_temp.json', filename=f"{time.strftime('%Y%m%d_%H%M%S')}-Polymom-Data.json"))
            os.remote('data_temp.json')
    if msglogmode:
        print(f"{time.strftime('%Y/%m/%d %H:%M:%S')} | {msg.author.display_name}({msg.author.id}) | {msg.content}")

@bot.event
async def on_command(ctx):
    if msglogmode:
        print(f"{time.strftime('%Y/%m/%d %H:%M:%S')} | {ctx.author.display_name}({ctx.author.id}) : command | {ctx.command} {str(ctx.kwargs)}")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    em = str(payload.emoji)
    if em in data["notice_group"]:
        for emoji in data["notice_group"]: # 絵文字スレッドにあるメッセージにリアクションされたら無視
            if str(payload.channel_id) == data["notice_group"][emoji]["thread_id"]:
                return
        channel = bot.get_channel(int(data["notice_group"][em]["thread_id"]))
        msg: discord.Message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if (channel is not None) and str(payload.message_id) not in data["notice_group"][em]["messages"]:
            embed = discord.Embed(title="", description = msg.content, color=discord.Color.blue())
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar.url)
            embed.set_footer(text=f"<t:{msg.created_at.timestamp()}> | #{msg.channel.name}")
            _is_image_set = False
            attachments_str = []
            attachments_dict = {}
            for attachment in msg.attachments:
                if (attachment.filename.endswith(".png") or attachment.filename.endswith(".jpg") or attachment.filename.endswith(".jpeg") or attachment.filename.endswith(".gif") or attachment.filename.endswith(".webp")) and not _is_image_set:
                    embed.set_image(url=attachment.url)
                    _is_image_set = True
                else:
                    attachments_str.append(f"[{attachment.filename}]({attachment.url})")
                attachments_dict[str(attachment.filename)] = str(attachment.url)
            if len(attachments_str) > 0:
                embed.add_field(name="`添付ファイル`", value="\n".join(attachments_str), inline=False)
            
            forward = await channel.send(embed=embed, view=ViewForForward(msg.jump_url))
            data["notice_group"][em]["messages"][str(payload.message_id)] = {
                "forwarded_msg_id": str(forward.id),
                "msg_channel_id": str(payload.channel_id),
                "user_id": str(payload.user_id),
                "sent_at": str(msg.created_at.timestamp()),
                "created_at": str(forward.created_at.timestamp()),
                "attachments": attachments_dict
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

@bot.event
async def on_guild_channel_delete(channel):
    if isinstance(channel, discord.TextChannel):
        for emoji in data["notice_group"]:
            if "ignore_channels" in data["notice_group"][emoji]:
                if str(channel.id) in data["notice_group"][emoji]["ignore_channels"]:
                    data["notice_group"][emoji]["ignore_channels"].remove(str(channel.id))
                    Save()
                    await bot.get_channel(int(data["log_channel"])).send(f"テキストチャンネルが削除されたため、 {emoji} の無視チャンネルリストから #{channel.name} を削除しました。")

@bot.event
async def on_message_delete(msg):
    if msg.author.id == bot.user.id: # ボットが転送したメッセージが削除されたらDataから削除
        for emoji in data["notice_group"]:
            msg_to_delete = ""
            for message in data["notice_group"][emoji]["messages"]:
                if data["notice_group"][emoji]["messages"][message]["forwarded_msg_id"] == str(msg.id):
                    msg_to_delete = message
            if msg_to_delete != "":
                del data["notice_group"][emoji]["messages"][msg_to_delete]
                Save()
    else: # 転送されたメッセージの元メッセージが削除されたらDataから削除 + スレッド内も削除
        for emoji in data["notice_group"]:
            if str(msg.id) in data["notice_group"][emoji]["messages"]:
                await bot.get_channel(int(data["notice_group"][emoji]["thread_id"])).fetch_message(int(data["notice_group"][emoji]["messages"][str(msg.id)]["forwarded_msg_id"])).delete()
                del data["notice_group"][emoji]["messages"][str(msg.id)]
                Save()
    
#region UI系

class ExpireModal(discord.ui.Modal, title="有効期限を設定してください"):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None, *args, **kwargs)
        self.add_item(discord.ui.TextInput(label="日付を入力", placeholder="YYYY/MM/DD (1月1日なら 01/01)", required=False, min_length=10,max_length=10, custom_id="date_input"))
        self.add_item(discord.ui.TextInput(label="時間を入力", placeholder="HH:MM (未入力の場合はその日の23:59)", required=False, min_length=5,max_length=5, custom_id="time_input"))
    
    async def on_submit(self, itr: discord.Interaction):
        expire_at = f"{self.children[0].value} {self.children[1].value}" if self.children[1].value != "" else self.children[0].value
        try:
            if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at) or re.fullmatch(r"\d{4}/\d{2}/\d{2}", expire_at) or re.fullmatch(r"\d{2}:\d{2}", expire_at):
                if re.fullmatch(r"\d{2}:\d{2}", expire_at):
                    expire = time.time() + (int(expire_at.split(":")[0]) * 3600) + (int(expire_at.split(":")[1]) * 60)
                elif re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at):
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
    def __init__(self, jump_url: str = ""):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="メッセージを開く", style=discord.ButtonStyle.link, url=jump_url))
        
    @discord.ui.button(label="有効期限を設定", style=discord.ButtonStyle.primary, custom_id="BtnSetExpire")
    async def SetExpire(self, itr: discord.Interaction, button: discord.ui.Button):
        await itr.response.send_modal(ExpireModal())

class WaitingExpire(discord.ui.View):
    def __init__(self, expire_at: str = "N/A", jump_url: str = ""):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label=f"{expire_at} に削除されます", style=discord.ButtonStyle.grey, disabled=True, custom_id="ExpireTime"))
        self.add_item(discord.ui.Button(label="メッセージを開く", style=discord.ButtonStyle.link, url=jump_url))
    
#region コマンド

@tree.command(name='forecast', description="天気予報を表示します")
@app_commands.describe(is_tomorrow = "False:今日 True:明日")
async def forecast(itr: discord.Interaction, is_tomorrow: bool = False):
    emb = Make_embed_forecast("tomorrow" if is_tomorrow else "today")
    await itr.response.send_message(embed=emb[0])

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

@tree.command(name="auto_forecast", description="天気予報の自動通知を設定します")
@app_commands.describe(reset = "自動通知をリセットするか", channel = "通知を送信するチャンネル", times = "通知する時間をカンマ区切りで指定 (例: 21600,43200,64800)", mentions = "メンションをカンマ区切りで指定 (例: @user1,@user2,@user3)", greeting = "挨拶をカンマ区切りで指定 (例: おはよう,こんにちは,こんばんは)")
async def auto_forecast(itr: discord.Interaction, reset: bool = False, channel: int = None, times: str = None, mentions: str = None, greeting: str = None):
    global data
    if str(itr.user.id) not in admins:
        itr.command_failed = True
        await Reply(itr, 2, "エラー", "このコマンドは管理者のみ使用できます", True)
        return
    else:
        if reset:
            data["weather"]["mention"] = ["", "", ""]
            data["weather"]["notify_time"] = [21600, 43200, 64800]
            data["weather"]["day"] = ["today", "today", "tomorrow"]
            data["weather"]["greetings"] = ["おはようございます。", "午後も頑張りましょう。", "こんばんは。"]
            data["weather"]["msg_channel"] = ""
            data["weather"]["last_noticed"] = 0
            Save()
            await Reply(itr, 0, "完了", "天気予報の自動通知をリセットしました", True)
        else:
            if channel is not None:
                try:
                    a = bot.get_channel(channel)
                    data["weather"]["msg_channel"] = str(a.id)
                except:
                    itr.command_failed = True
                    await Reply(itr, 2, "エラー", "指定されたチャンネルが見つかりませんでした", True)
                    return
            if times is not None:
                ls = times.split(",")
                if len(ls) != 3:
                    itr.command_failed = True
                    await Reply(itr, 2, "エラー", "時間の指定が不正です。3つの時間をカンマ区切りで指定してください。 ex) 6:00 → 21600", True)
                    return
                else:
                    try:
                        timelists = [int(ls[0]), int(ls[1]), int(ls[2])]
                        if not (timelists[0] < timelists[1]) and (timelists[1] < timelists[2]):
                            itr.command_failed = True
                            await Reply(itr, 2, "エラー", "時間の指定が不正です。昇順で指定してください。 ex) 6:00 → 21600", True)
                            return
                        data["weather"]["notify_time"] = timelists
                    except:
                        itr.command_failed = True
                        await Reply(itr, 2, "エラー", "時間の指定が不正です。整数で指定してください。 ex) 6:00 → 21600", True)
                        return
            if mentions is not None:
                ls = mentions.split(",")
                if len(ls) != 3:
                    itr.command_failed = True
                    await Reply(itr, 2, "エラー", "メンションの指定が不正です。3つのメンションをカンマ区切りで指定してください。 ex) @user1,@user2,@user3", True)
                    return
                else:
                    data["weather"]["mention"] = [ls[0], ls[1], ls[2]]
            if greeting is not None:
                ls = greeting.split(",")
                if len(ls) != 3:
                    itr.command_failed = True
                    await Reply(itr, 2, "エラー", "挨拶の指定が不正です。3つの挨拶をカンマ区切りで指定してください。 ex) おはよう,こんにちは,こんばんは", True)
                    return
                else:
                    data["weather"]["greetings"] = [ls[0], ls[1], ls[2]]
            Save()
            await Reply(itr, 0, "完了", "変更を適用しました。\n通知時間の変更はBotを再起動すると適用されます。", True)


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

@tree.command(name='add_ignore_ch', description="転送を無視するチャンネルを追加します")
@app_commands.describe(channels = "無視対象のチャンネル (メンション, 複数可)", emoji = "絵文字1文字")
async def add_ignore_ch(itr: discord.Interaction, emoji: str, channels: str):
    global data
    if not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
        itr.command_failed = True
        await Reply(itr,2, "エラー", "絵文字が適正ではありません")
    else:
        ch_mentions = re.findall(r"<#(\d{17,20})>", channels)
        if len(ch_mentions) == 0:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "テキストチャンネルを指定してください。")
        else:
            chs = []
            for channel in ch_mentions:
                try:
                    chs.append(bot.get_channel(int(channel)).id)
                except:
                    pass
            if len(chs) == 0:
                itr.command_failed = True
                await Reply(itr,2, "エラー", "指定されたテキストチャンネルはどれも見つかりませんでした。")
            else:
                embed = discord.Embed(title="無視チャンネルリストに追加", description=f"以下のチャンネルでは {emoji} のメッセージを無視するようになります。", color=discord.Color.blue())
                if not "ignore_channels" in data["notice_group"][emoji]:
                    data["notice_group"][emoji]["ignore_channels"] = []
                for ch in chs:
                    if str(ch) in data["notice_group"][emoji]["ignore_channels"]:
                        embed.add_field(name=f"<#{ch}>", value=f"既に追加されています。", inline=False)
                    else:
                        data["notice_group"][emoji]["ignore_channels"].append(str(ch))
                        embed.add_field(name=f"<#{ch}>", value=f"追加されました。", inline=False)
                Save()
                await itr.response.send_message(embed=embed)

@tree.command(name='remove_ignore_ch', description="転送を無視するチャンネルを削除します")
@app_commands.describe(channels = "無視対象のチャンネル (メンション, 複数可)", emoji = "絵文字1文字")
async def remove_ignore_ch(itr: discord.Interaction, emoji: str, channels: str):
    global data
    if not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
        itr.command_failed = True
        await Reply(itr,2, "エラー", "絵文字が適正ではありません")
    else:
        if not emoji in data["notice_group"]:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "その絵文字で登録されているスレッドはありません。")    
            return
        ch_mentions = re.findall(r"<#(\d{17,20})>", channels)
        if len(ch_mentions) == 0:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "テキストチャンネルを指定してください。")
        else:
            chs = []
            for channel in ch_mentions:
                try:
                    chs.append(bot.get_channel(int(channel)).id)
                except:
                    pass
            if len(chs) == 0:
                itr.command_failed = True
                await Reply(itr,2, "エラー", "指定されたテキストチャンネルはどれも見つかりませんでした。")
            else:
                embed = discord.Embed(title="無視チャンネルリストから削除", description=f"以下のチャンネルでは {emoji} のメッセージを無視しなくなります。", color=discord.Color.blue())
                if not "ignore_channels" in data["notice_group"][emoji]:
                    data["notice_group"][emoji]["ignore_channels"] = []
                for ch in chs:
                    if str(ch) in data["notice_group"][emoji]["ignore_channels"]:
                        data["notice_group"][emoji]["ignore_channels"].remove(str(ch))
                        embed.add_field(name=f"<#{ch}>", value=f"無視リストから削除しました。", inline=False)
                    else:
                        
                        embed.add_field(name=f"<#{ch}>", value=f"無視リストにないチャンネルです。", inline=False)
                Save()
                await itr.response.send_message(embed=embed)

@tree.command(name='stats_thread', description="絵文字と連携されているスレッドの詳細を確認します")
async def stats_thread(itr: discord.Interaction, emoji: str):
    if not (is_discord_emoji(emoji) or is_unicode_emoji(emoji)):
        itr.command_failed = True
        await Reply(itr,2, "エラー", "絵文字が適正ではありません")
    else:
        if not emoji in data["notice_group"]:
            itr.command_failed = True
            await Reply(itr,2, "エラー", "その絵文字で登録されているスレッドはありません。")    
            return
        else:
            embed = discord.Embed(title="スレッドの詳細", description=f"絵文字: {emoji}", color=discord.Color.blue())
            embed.add_field(name="スレッド", value=f"<#{data["notice_group"][emoji]["thread_id"]}>", inline=False)
            embed.add_field(name="作成者", value=f"<@{data['notice_group'][emoji]['owner']}>", inline=False)
            embed.add_field(name="作成日時", value=time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(float(data["notice_group"][emoji]["created_at"]))), inline=False)
            if "ignore_channels" in data["notice_group"][emoji]:
                ignore_channels = "\n".join([f"<#{ch}>" for ch in data["notice_group"][emoji]["ignore_channels"]])
                embed.add_field(name="無視チャンネル", value=ignore_channels, inline=False)
            else:
                embed.add_field(name="無視チャンネル", value="なし", inline=False)
            await itr.response.send_message(embed=embed)

@tree.command(name='expire', description="スレッド内のメッセージの有効期限を設定できます")
@app_commands.describe(msg_link = "**転送された**メッセージのリンク", expire_at = "有効期限 (YYYY/MM/DD HH:MM or YYYY/MM/DD or HH:MM の書式)")
async def expire(itr: discord.Interaction, msg_link: str, expire_at: str):
    try:
        if re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at) or re.fullmatch(r"\d{4}/\d{2}/\d{2}", expire_at) or re.fullmatch(r"\d{2}:\d{2}", expire_at):
            if re.fullmatch(r"\d{2}:\d{2}", expire_at):
                expire = time.time() + (int(expire_at.split(":")[0]) * 3600) + (int(expire_at.split(":")[1]) * 60)
            elif re.fullmatch(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}", expire_at):
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

Load()

#region タスク

temp = [DaytimeToList(data["weather"]["notify_time"][0]), DaytimeToList(data["weather"]["notify_time"][1]), DaytimeToList(data["weather"]["notify_time"][2])]
forecast_times = [
    datetime.time(hour=temp[0][0], minute=temp[0][1], second=temp[0][2]),
    datetime.time(hour=temp[1][0], minute=temp[1][1], second=temp[1][2]),
    datetime.time(hour=temp[2][0], minute=temp[2][1], second=temp[2][2])
]

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

#region 天気予報
@tasks.loop(times=forecast_times)
async def Auto_Forecast():
    global data
    nt = time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60 + time.localtime().tm_sec
    if nt in data["weather"]["notify_time"]:
        return
    else:
        i = data["weather"]["notify_time"].index(nt)
    
    emb = Make_embed_forecast(data["weather"]["day"][i])
    ch = bot.get_channel(int(data["weather"]["msg_channel"]))
    if ch is not None:
        if emb[1]:
            msg = await ch.send(f"# {data["weather"]["greetings"][i]}\n{data["weather"]["mention"][i]}", embed=emb[0])
        else:
            msg = await ch.send(f"# {data["weather"]["greetings"][i]}", embed=emb[0])
        data["weather"]["last_noticed"] = msg.created_at.timestamp()

token = os.getenv("DISCORD_TOKEN")
bot.run(token)