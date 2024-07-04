import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
import visualization
import main
#非同步獲取網頁內容
async def fetch_page(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            else:
                print(f'無法獲取頁面: {url}, 狀態碼: {response.status}')
                return None

#解析單個產品資訊
def parse_product(item, low_price, high_price):
    try:
        title = item.h2.text.strip()
        price = int(item.find('span', class_='price ellipsis xlarge').text.replace(',', ''))

        # 價格範圍檢查
        if not int(low_price) <= price <= int(high_price):
            return None

        store = item.find('span', class_='shop').text.strip().split(' - ')[0]
        link = item.a['href']
        return store, title, price, link
    except AttributeError:
        return None

#輸入檢查
def input_check(low_price, high_price):
    try:
        low_price = int(low_price)
        high_price = int(high_price)
    except ValueError:
        print("價格輸入須為整數")
        return False

    if low_price > high_price:
        print("最低價格不得大於最高價格")
        return False
    if low_price < 0 or high_price < 0:
        print("價格輸入不得為負數")
        return False
    if high_price == 0:
        print("最高價格不得為0")
        return False

    return True

#短網址製作
async def shorten_url(url):
    api_url = f"http://tinyurl.com/api-create.php?url={url}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                short_url = await response.text()
                return short_url
            else:
                return url  # 如果失敗，返回原始網址

# 爬取 feebee 網站資訊
async def scrape_feebee(product, min_price, max_price, user_text, pages=3):
    if not input_check(min_price, max_price):
        return f"價格輸入錯誤或範圍不合理。請檢查最低價格和最高價格是否合理。"
    else:
        min_price, max_price = int(min_price), int(max_price)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }

    cheapest_products = {}

    for page in range(1, pages + 1):
        url = f'https://feebee.com.tw/s/{product}/?sort=p&pl={min_price}&ph={max_price}&ptab=1&page={page}'
        html_source = await fetch_page(url, headers)

        if html_source is None:
            continue

        soup = BeautifulSoup(html_source, 'lxml')
        try:
            items = soup.find('ol', id='list_view').find_all(
                'span', class_='pure-u items_container'
            )

            for item in items:
                result = parse_product(item, min_price, max_price)

                if result:
                    store, title, price, link = result

                    if store not in cheapest_products or price < cheapest_products[store]["price"]:
                        # 縮短網址
                        short_link = await shorten_url(link)
                        cheapest_products[store] = {
                            'title': title,
                            'price': price,
                            'link': short_link,
                        }

        except AttributeError:
            continue
    if not cheapest_products:
        return f'沒有找到符合條件的商品。\n商品名稱: {product}\n價格範圍: {min_price}-{max_price}'
    
    data = [
        {
            '商品標題': product['title'],
            '通路': store,
            '價錢': product['price'],
            '連結': product['link'],
        }
        for store, product in cheapest_products.items()
    ]

    df = pd.DataFrame(data)
    sorted_df = df.sort_values(by='價錢').reset_index(drop=True)
    print('商品資訊儲存成功')
    
    
    if user_text == "查詢":
        cheapest_items = find_cheapest_items(cheapest_products)
        message = create_message(product, min_price, max_price, cheapest_items)# 回傳給用戶
        return message
    
    elif user_text == "各平台分析圖":
        font_path = r"C:\Users\user\Desktop\Python\ccClub 2024 Spring期末專案\YuPearl-Light .ttf" # 字體路徑
        image_url = visualization.price_chart(sorted_df, font_path, product, output_path='price_chart.png')
        return image_url


# 初始化最便宜的三個商品列表
def find_cheapest_items(cheapest_products):
    
    cheapest_items = []

    # 爬取所有的商品，並尋找最便宜的三個
    for store, product in cheapest_products.items():
        item_info = {
            "商品標題": product['title'],
            "通路": store,
            "價錢": product['price'],
            "連結": product['link']
        }
        # 如果目前列表中的商品少於三個，直接加入
        if len(cheapest_items) < 3:
            cheapest_items.append(item_info)
        else:
            # 如果目前列表中已有三個商品，則需要找出是否有更便宜的商品替換之
            for idx, item in enumerate(cheapest_items):
                if item_info["價錢"] < item["價錢"]:
                    # 如果找到更便宜的商品，則替換該商品
                    cheapest_items[idx] = item_info
                    break

    return cheapest_items


def create_message(product, min_price, max_price, cheapest_items):
    # 回傳三項價格訊息給用戶
    header = f"找到符合條件的商品如下：\n商品名稱: {product}\n價格範圍: {min_price} - {max_price}\n"
    message = [header]

    header_cheapest = "找到最便宜的三個商品如下：\n"
    message.append(header_cheapest)

    for item in cheapest_items:
        item_info = (
            f"商品標題: {item['商品標題']}\n"
            f"通路: {item['通路']}\n"
            f"價錢: {item['價錢']}\n"
            f"連結: {item['連結']}\n"
            "------------------------\n"
        )
        message.append(item_info)

    return "\n".join(message)

