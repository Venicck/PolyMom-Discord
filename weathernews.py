# -*- coding: utf-8 -*-
import requests, japanize_matplotlib, math, time, os
# japanize_matplotlibは日本語を表示するためのライブラリ なので消さない
from bs4 import BeautifulSoup
from matplotlib import pyplot as pyp
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime as dt

"""注意！ このクラスを使用するときはタイムロケールが日本であるか確認すること！"""
class WeatherNews(Exception):
    def __init__(self, template_img_path = "img_make/img-template.png"):
        self.day = None
        color = {"晴れ":"#F39C12FF", "曇り":"#7F8C8DFF", "雨あり":"#44CED8FF", "雪あり":"#A6A6A6FF"}
        self.exported_graph_path = None
        self.exported_image_path = None
        self.RESOLUTION = (1650, 1080) # 画像の解像度
        self.TEMPLATE_PATH = template_img_path
        self.do_mention = False
        self.url = "https://weathernews.jp/onebox/35.655580/139.543914/"
        self.weather_data = {}
        self.requested_day = None
        self.footer = ""

        # グラフ作成後の変数
        self.max_temp = None
        self.min_temp = None
        self.avg_temp = None
        self.overall_weather = None

        # 画像作成用の変数
        self.color = {"晴れ":"#F39C12FF", "曇り":"#7F8C8DFF", "雨あり":"#44CED8FF", "雪あり":"#A6A6A6FF"}

    def Judge_weather(self, link):
        imgs = {'https://gvs.weathernews.jp/onebox/img/wxicon/500.png': '晴れ','https://gvs.weathernews.jp/onebox/img/wxicon/100.png': '晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/550.png': '猛暑', 'https://gvs.weathernews.jp/onebox/img/wxicon/101.png': '晴れ時々くもり', 'https://gvs.weathernews.jp/onebox/img/wxicon/102.png': '晴れ一時雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/104.png': '晴れ一時雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/110.png': '晴れのちくもり', 'https://gvs.weathernews.jp/onebox/img/wxicon/112.png': '晴れのち雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/115.png': '晴れのち雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/200.png': 'くもり', 'https://gvs.weathernews.jp/onebox/img/wxicon/201.png': 'くもり時々晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/202.png': 'くもり時々雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/204.png': 'くもり時々雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/210.png': 'くもりのち晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/212.png': 'くもりのち雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/215.png': 'くもりのち雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/650.png': '小雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/300.png': '雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/850.png': '大雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/301.png': '雨時々晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/302.png': '雨時々止む', 'https://gvs.weathernews.jp/onebox/img/wxicon/303.png': '雨一時雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/311.png': '雨のち晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/313.png': '雨のちくもり', 'https://gvs.weathernews.jp/onebox/img/wxicon/314.png': '雨のち雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/430.png': 'みぞれ', 'https://gvs.weathernews.jp/onebox/img/wxicon/400.png': '雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/950.png': '大雪', 'https://gvs.weathernews.jp/onebox/img/wxicon/401.png': '雪時々晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/402.png': '雪時々止む', 'https://gvs.weathernews.jp/onebox/img/wxicon/403.png': '雪時々雨', 'https://gvs.weathernews.jp/onebox/img/wxicon/411.png': '雪のち晴れ', 'https://gvs.weathernews.jp/onebox/img/wxicon/413.png': '雪のちくもり', 'https://gvs.weathernews.jp/onebox/img/wxicon/414.png': '雪のち雨'}
        if link in imgs:
            return imgs[link]
        else:
            return "不明"
    
    def Check_mention(self, istoday, hour):
        if istoday and hour >= time.localtime().tm_hour:
            self.do_mention = True
        elif not istoday:
            self.do_mention = True
        
    def Get_weather(self, day : int):
        today = dt.now().timestamp()
        self.day = day
        
        """
        今日の日付をtimeから取得して
        -3 -2 -1 0 +1 +2 +3 日をそれぞれ足したtime_structを作れば
        それぞれtime.tm_dayを拾うことができ、何月何日かわかる。
        """
        times = list(map(float, [today-86400*3, today-86400*2, today-86400, today, today+86400, today+86400*2, today+86400*3]))
        dates = list(map(lambda t: dt.fromtimestamp(t).strftime('%Y-%m-%d'), times))
        for i in dates:
            if i[-2:] == f"{self.day:02}":
                self.requested_day = i
        
        req = requests.get(self.url)
        self.footer = f"{time.strftime('%Y/%m/%d %H:%M:%S')} 現在に取得"
        Soup = BeautifulSoup(req.text, "html.parser")
        weather_data = {}
        day_found = False
        pointer = 1
        
        for i in range(1, 7):
            table = Soup.select(f'#flick_list_1hour > div:nth-child({i}) > div.date')
            date = table[0].text
            if int(date[:(len(date) - 5)]) == self.day: # 1日(月)のようなとこから数字を抽出して日付と照合
                day_found = True
                pointer = i
                break
        if not day_found:
            raise DayNotFoundOnWeatherNews(f"Selected Day '{self.day}' is not found on WeatherNews.")
        
        table = Soup.select(f'#flick_list_1hour > div:nth-child({pointer}) > div.wx1h_content')
        times = table[0].find_all("ul")
        for time in times:
            hour = time.select('li.time')[0].text.replace('\n','')
            weather_data[hour] = {}
            weather_data[hour]["weather"] = self.Judge_weather(time.select('li.weather > figure')[0].find('img')['src']) # 画像リンクによる条件式が必要
            weather_data[hour]["rain"] = time.select('li.rain')[0].text.replace('\n', '')
            weather_data[hour]["temp"] = time.select('li.temp')[0].text.replace('\n', '').replace('℃', '')
            weather_data[hour]["wind"] = time.select('li.wind > p')[0].text.replace('\n', '')
        self.weather_data = weather_data
        if len(self.weather_data) != 24:
            raise FullDataNotFoundOnWeatherNews("Weather data is not enough. Expected 24 hours data, but got less.")
        
    def Make_graph(self): 
        color = [(230, 126, 34), (153, 153, 153), (52, 152, 219), (229, 229, 229)] # 晴れ, くもり, 雨, 雪
        color_normalized = [(r/255, g/255, b/255) for r, g, b in color]
        c_rainy, c_snowy = color_normalized[2], color_normalized[3] # Matplotlibの色は0-1の範囲なので255で割る
        # グラフの描画
        x = range(24)
        y = [int(self.weather_data[f"{i}"]["temp"]) for i in self.weather_data]
        fig, ax = pyp.subplots(figsize=(15, 7))
        ax.set_xlim(-0.5, 23.5)
        ax.set_ylim(math.floor(min(y) / 5 ) * 5 - 0.5, math.ceil(max(y) / 5 ) * 5 + 0.5)
        ax.set_xticks([i for i in range(0, 24)])
        ax.set_title("", {"fontsize":10})
        ax.set_xlabel("時間 (時)", {"fontsize":10})
        ax.set_ylabel("気温 (℃)", {"fontsize":10})
        ax.plot(x, y)
        ax.grid(axis='y')
        
        # 枠線の設定
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        for i in range(24):
            ax.annotate(f"{y[i]}", (x[i], y[i]), textcoords="offset points", xytext=(0, 20), ha="center", va="top")
        
        # 表を下につける
        summary_data = [[], [], []] # 上から 天気、気温、降水量
        col_labels = [f'{i}時' for i in range(24)]
        sunny, cloudy, rainy, snowy = 0, 0, 0, 0
        for i in range(24):
            if "雪" in self.weather_data[f"{i}"]["weather"]:
                snowy += 1
                summary_data[0].append("雪")
                self.Check_mention(self.requested_day == time.strftime('%Y-%m-%d'), i)
            elif "雨" in self.weather_data[f"{i}"]["weather"]:
                rainy += 1
                summary_data[0].append("雨")
                self.Check_mention(self.requested_day == time.strftime('%Y-%m-%d'), i)
            elif "くもり" in self.weather_data[f"{i}"]["weather"]:
                cloudy += 1
                summary_data[0].append("くもり")
            else:
                sunny += 1
                summary_data[0].append("晴れ")

            summary_data[1].append(self.weather_data[f"{i}"]["temp"])
            summary_data[2].append(self.weather_data[f"{i}"]["rain"].replace('ミリ', ''))
        cell_text = summary_data
        # 2. ax.table()で表を追加
        # loc='bottom'でグラフの下側に配置
        the_table = ax.table(cellText=cell_text,
                            colLabels=col_labels,
                            loc='bottom',
                            cellLoc='center', # セル内の文字を中央揃え
                            bbox=[0.0, -0.4, 1.0, 0.25]) # 位置とサイズを微調整 [左, 下, 幅, 高さ]
        
        for i in range(24):
            weather = summary_data[0][i]
            cell = the_table.get_celld()[1, i]
            if "雪" in weather:
                cell.set_facecolor(c_snowy)
                cell.set_text_props(weight='bold')
            elif "雨" in weather:
                cell.set_facecolor(c_rainy)
                cell.set_text_props(color='white', weight='bold') # 雨のセルの文字色を白に
                

        # 表のフォントサイズを調整
        the_table.auto_set_font_size(False)
        the_table.set_fontsize(12)

        # グラフと表が重ならないようにレイアウトを調整
        fig.subplots_adjust(bottom=0.2)
        fig.tight_layout()
        
        # 画像の保存と返り値の決定
        if os.path.exists("created_images") is False:
            os.mkdir("created_images")
        filename = f"created_images/graph-{self.requested_day}.png"
        pyp.savefig(filename)
        temps = [int(self.weather_data[f"{i}"]["temp"]) for i in range(24)]
        wet = ""
        if snowy > 0:
            wet = "雪あり"
        elif rainy > 0:
            wet = "雨あり"
        elif cloudy > sunny:
            wet = "曇り"
        else:
            wet = "晴れ"
            
        self.max_temp = max(temps)
        self.min_temp = min(temps)
        self.avg_temp = round(sum(temps) / len(temps))
        self.overall_weather = wet
        self.exported_graph_path = filename
    
    def Make_image(self):
        bg = Image.new('RGBA', self.RESOLUTION, self.color[self.overall_weather])
        temp_img = Image.open(self.TEMPLATE_PATH, 'r').convert('RGBA') # 画像をRGBAモードに変換
        img = Image.alpha_composite(bg, temp_img)
        graph_img = Image.open(self.exported_graph_path)
        img.paste(graph_img, (70, 200)) # グラフを配置
        head_font = ImageFont.truetype("img_make/MPLUSRounded.ttf", 80)
        text_font = ImageFont.truetype("img_make/MPLUSRounded.ttf", 50)
        legend_font = ImageFont.truetype("img_make/MPLUSRounded.ttf", 20)
        draw = ImageDraw.Draw(img)
        _sps = self.requested_day.split("-")
        draw.text((800, 100), f"{_sps[0]} / {_sps[1]} / {_sps[2]} の天気", "#FFFFFF", font=head_font, anchor="mm")
        draw.text((97, 845), f"天気\n気温\n降水量", "#404040", font=legend_font, anchor="mm", align="right")
        draw.text((500, 1000), f"最低:{self.min_temp}℃ 平均:{self.avg_temp}℃ 最高:{self.max_temp}℃", "#4C4C4C", font=text_font, anchor="mm")
        WETPOS = (1370, 1000)
        draw.text(WETPOS, self.overall_weather, self.color[self.overall_weather], font=text_font, anchor="mm")

        img.save(f"created_images/forecast-{self.requested_day}.png", "PNG")
        self.exported_image_path = f"created_images/forecast-{self.requested_day}.png"

class DayIsNotSet(WeatherNews):
    pass
class DayNotFoundOnWeatherNews(WeatherNews):
    pass
class FullDataNotFoundOnWeatherNews(WeatherNews):
    pass