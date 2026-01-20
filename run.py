import os
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image

def get_valid_url(url_template_func, time_offset_hours=0):
    """
    嘗試尋找有效的圖片網址。
    規則: 當前時間 - 30分，取10的倍數，若失敗則往前推，最多1小時。
    time_offset_hours: 0 for UTC, 8 for UTC+8
    """
    # 設定基準時區與時間
    tz = timezone(timedelta(hours=time_offset_hours))
    now = datetime.now(tz)
    
    # 起始尋找時間: 現在 - 30分鐘
    search_time = now - timedelta(minutes=30)
    
    # 分鐘數取整數 (00, 10, 20, 30, 40, 50)
    minute = (search_time.minute // 10) * 10
    search_time = search_time.replace(minute=minute, second=0, microsecond=0)
    
    # 最多往前推 1 小時 (6次 * 10分鐘)
    for _ in range(7):
        url = url_template_func(search_time)
        try:
            # 使用 stream=True 只讀取檔頭以確認連結有效性，減少流量
            r = requests.head(url, timeout=5)
            if r.status_code == 200:
                return url
        except:
            pass
        # 往前推 10 分鐘
        search_time -= timedelta(minutes=10)
    
    return None

def download_image(url, filename):
    if not url:
        return False
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except:
        return False
    return False

# URL 生成模板函數
def template_img1(t):
    # t is UTC+8
    ym = t.strftime("%Y%m")
    ymdhm = t.strftime("%Y%m%d%H%M")
    return f"https://watch.ncdr.nat.gov.tw/00_Wxmap/7R1_KRID_RAINMAP/{ym}/{ymdhm}/raingauge_24_{ymdhm}.png"

def template_img2(t):
    # t is UTC
    ym = t.strftime("%Y%m")
    ymd = t.strftime("%Y%m%d")
    ymdhm = t.strftime("%Y%m%d%H%M")
    return f"https://watch.ncdr.nat.gov.tw/00_Wxmap/7F13_NOWCAST/{ym}/{ymd}/{ymdhm}/examp6hr_{ymdhm}_s06_rain.png"

def template_img3(t):
    # t is UTC
    ym = t.strftime("%Y%m")
    ymd = t.strftime("%Y%m%d")
    ymdhm = t.strftime("%Y%m%d%H%M")
    return f"https://watch.ncdr.nat.gov.tw/00_Wxmap/7F13_NOWCAST/{ym}/{ymd}/{ymdhm}/examp6hr_{ymdhm}_s12_rain.png"

def process_layer(base_canvas, img_path, enlarge_coords, crop_coords):
    """
    base_canvas: 底圖 (PIL Image Object)
    img_path: 圖片路徑
    enlarge_coords: (x1, y1, x2, y2) 圖片應該被縮放並放置的完整區域
    crop_coords: (x1, y1, x2, y2) 最終要保留顯示的區域
    """
    if not os.path.exists(img_path):
        return

    try:
        # 載入 overlay 圖片
        src_img = Image.open(img_path).convert("RGBA")
        
        # 1. 依照 Enlarge 座標計算目標大小與位置
        ex1, ey1, ex2, ey2 = enlarge_coords
        target_w = ex2 - ex1
        target_h = ey2 - ey1
        
        # 縮放圖片
        resized_img = src_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # 2. 建立一個與底圖一樣大的暫存透明圖層，將縮放後的圖貼在指定位置 (enlarge 左上角)
        temp_layer = Image.new("RGBA", base_canvas.size, (0, 0, 0, 0))
        temp_layer.paste(resized_img, (ex1, ey1))
        
        # 3. 依照 Crop 座標進行裁切 (取得該區域的圖片)
        cx1, cy1, cx2, cy2 = crop_coords
        cropped_part = temp_layer.crop((cx1, cy1, cx2, cy2))
        
        # 4. 將裁切後的圖片貼回底圖的對應位置 (使用其自身 alpha 通道做遮罩)
        base_canvas.paste(cropped_part, (cx1, cy1), cropped_part)
        
    except Exception:
        pass

def main():
    # 檔案路徑 (相對路徑)
    base_path = "rainfore.png"
    img1_path = "img1.png"
    img2_path = "img2.png"
    img3_path = "img3.png"
    output_path = "result.png"

    # 1. 下載底圖 (固定網址)
    base_url = "https://raw.githubusercontent.com/gyrreegr/think2/main/rainfore.png"
    download_image(base_url, base_path)

    # 2. 下載動態圖片
    # 圖一: UTC+8
    url1 = get_valid_url(template_img1, time_offset_hours=8)
    download_image(url1, img1_path)

    # 圖二: UTC+0
    url2 = get_valid_url(template_img2, time_offset_hours=0)
    download_image(url2, img2_path)

    # 圖三: UTC+0
    url3 = get_valid_url(template_img3, time_offset_hours=0)
    download_image(url3, img3_path)

    # 3. 圖片處理
    if os.path.exists(base_path):
        # 載入底圖
        base_img = Image.open(base_path).convert("RGBA")
        
        # 強制調整底圖尺寸為 4570x2571 以符合座標系統
        # (若原圖已是此尺寸則不影響，若為 2048x1582 則會被放大以匹配座標)
        base_img = base_img.resize((4570, 2571), Image.Resampling.LANCZOS)

        # 處理圖一
        # Enlarge: 400,466 到 1366,2100
        # Crop:    400,548 到 1366,2100
        process_layer(base_img, img1_path, 
                      (400, 466, 1366, 2100), 
                      (400, 548, 1366, 2100))

        # 處理圖二
        # Enlarge: 814,41 到 3764,2319
        # Crop:    1914,550 到 3033,2101
        process_layer(base_img, img2_path, 
                      (814, 41, 3764, 2319), 
                      (1914, 550, 3033, 2101))

        # 處理圖三
        # Enlarge: 2200,41 到 4950,2320 (超版)
        # Crop:    3303,549 到 4421,2101
        process_layer(base_img, img3_path, 
                      (2200, 41, 4950, 2320), 
                      (3303, 549, 4421, 2101))

        # 儲存結果
        base_img.save(output_path)

if __name__ == "__main__":
    main()