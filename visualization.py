import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
import seaborn as sns


# 上傳分析圖到 Imgur
def upload_image_to_imgur(client, chart_path):
    try:
        uploaded_image = client.upload_from_path(chart_path, anon=True)
        return uploaded_image['link']
    except Exception as e:
        print("Error occurred while uploading image to Imgur:", e)
        return None


#繪製價格圖表
def price_chart(sorted_df, font_path, product, output_path='price_chart.png'):
    
    
    #使用中文字體：要先下載字體檔案，font_path 為字型檔路徑
    font = FontProperties(fname="YuPearl-Light.ttf")
    
    top_10_df = sorted_df.head(10)
    
    # 限制 Y 軸每筆資料名稱最多顯示前 10 個字
    top_10_df['通路'] = top_10_df['通路'].apply(lambda x: x[:10] + '...' if len(x) > 10 else x)
    
    # 設定繪圖風格
    sns.set(style="whitegrid")

    # 建立長條圖
    plt.figure(figsize=(12, 12))

    # 使用自定義的顏色漸層
    custom_palette = sns.color_palette("terrain", 10)
    bar_plot = sns.barplot(x='價錢', y='通路', data=top_10_df, palette=custom_palette, hue='通路', legend=False)

    # 添加資料標籤
    for index, row in top_10_df.iterrows():
        plt.text(row['價錢'], index, f'{row["價錢"]}', color = 'White', ha = "right", va = "center", fontproperties = font, fontsize = 40)

    # 設定標題和標籤，並設定中文字體
    plt.title(f"{product} \n價錢最低的銷售通路 TOP10", fontproperties=font, fontsize=60, y=1.05)  # 設定標題字體大小
    plt.xlabel(" ", fontsize=5, labelpad=5)
    plt.ylabel(" ", fontsize=5, labelpad=5)

    # 隱藏 x 軸資料標籤
    plt.xticks([])

    # 設定資料標籤字體
    plt.yticks(fontproperties=font, fontsize=45)  # 增大 y 軸資料標籤的字體大小

    # 為 Y 軸前三筆資料名稱加上底色
    ytick_labels = bar_plot.get_yticklabels()
    for i in range(3):
        ytick_labels[i].set_bbox(dict(facecolor='yellow', edgecolor='none', pad=3))
    

    # 移除邊框
    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_edgecolor('none')  # 設定邊框顏色為透明

    # 調整四周留白
    plt.subplots_adjust(left = 0.15, right = 0.85, top = 0.85, bottom = 0.15)

    # 保存為 PNG 圖檔
    plt.savefig(output_path, bbox_inches = 'tight', pad_inches = 1, facecolor = (0.9608, 0.9725, 0.9804))  # 設置背景顏色
    

    # 關閉圖表以釋放記憶體
    plt.close()

    # 重新打開圖像並添加彩色邊框
    from PIL import Image, ImageOps
    img = Image.open(output_path)
    border_color = (211, 211, 211)  # 邊框顏色
    img_with_border = ImageOps.expand(img, border = 30, fill = border_color)
    img_with_border.save(output_path)
    
    return output_path
