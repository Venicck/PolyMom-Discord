import weathernews as WN

wn = WN.WeatherNews()

wn.Get_weather(16)
wn.Make_graph()
wn.Make_image()
print(f"graph:{wn.exported_graph_path} img:{wn.exported_image_path}")