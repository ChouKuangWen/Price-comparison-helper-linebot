import os
from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, ImageSendMessage, QuickReply, QuickReplyButton, MessageAction, TextSendMessage

from imgurpython import ImgurClient
import asyncio
import crawler
import visualization

app = Flask(__name__)

# 設定 Channel access token 和 Channel secret
line_bot_api = LineBotApi(os.getenv("YOUR_LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("YOUR_LINE_CHANNEL_SECRET"))

# 設定 LIFF ID
liffid = os.getenv("YOUR_LIFF_ID")

# Imgur 設定
client_id = os.getenv("YOUR_IMGUR_CLIENT_ID")
client_secret = os.getenv("YOUR_IMGUR_CLIENT_SECRET")
imgur_client = ImgurClient(client_id, client_secret)


# linebot回應樣板表單 (LIFF Flex訊息樣板)
def create_liff_flex_message(liffid):
    liff_url = f"https://liff.line.me/{liffid}"
    flex_message = FlexSendMessage(
        alt_text='查詢頁面',
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "查詢頁面",
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "點擊查詢",
                            "uri": liff_url
                        },
                        "style": "primary"
                    }
                ]
            }
        }
    )
    return flex_message

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_text  #宣告全域變數

    if event.message.text == "查詢":
        user_text = '查詢'  #將event.message.text存為user_text
        flex_message = create_liff_flex_message(liffid)
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif event.message.text == "各平台分析圖":
        user_text = '各平台分析圖'  #將event.message.text存為user_text
        flex_message = create_liff_flex_message(liffid)
        line_bot_api.reply_message(event.reply_token, flex_message)
    
    elif event.message.text == "優惠券查詢":
        try:
            message = TextSendMessage(
                text="請選擇平台",
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(action=MessageAction(label="蝦皮", text="蝦皮")),
                        QuickReplyButton(action=MessageAction(label="露天", text="露天")),
                        QuickReplyButton(action=MessageAction(label="PChome", text="PChome")),
                        QuickReplyButton(action=MessageAction(label="momo", text="momo")),
                        QuickReplyButton(action=MessageAction(label="博客來", text="博客來"))
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="發生錯誤"))
     #建立字典coupons，如果event.message.text在coupons.get()找的到就回傳對應之字典，否則傳"請點選圖文選單"
    else:
        coupons = {
            "蝦皮": "蝦皮優惠券:https://liff.line.me/2005730520-aM2Le0R3",
            "露天": "露天優惠券:https://liff.line.me/2005730526-qwbV6vyd",
            "PChome": "PChome優惠券:https://liff.line.me/2005730530-nKLyKv9A",
            "momo": "momo:https://liff.line.me/2005730546-Jv38qOOz",
            "博客來": "博客來優惠券:https://liff.line.me/2005730551-5b0VZvva"
        }
        response_message = coupons.get(event.message.text, "請點選圖文選單")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_message))

# 函式：處理表單提交(內嵌javascript網頁表單)
@app.route("/submit", methods=['POST'])
def submit():
    try:
        data = request.get_json()
        product_name = data.get('product_name')
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        line_user_id = data.get('line_user_id')
        print(product_name, min_price, max_price, line_user_id)

        # 觸發爬蟲並取得用戶消息

        if user_text == '查詢':
            user_message = asyncio.run(crawler.scrape_feebee(product_name, min_price, max_price, user_text))
        elif user_text == '各平台分析圖':
            chart_path =asyncio.run(crawler.scrape_feebee(product_name, min_price, max_price, user_text))
            if chart_path:
                img_url = visualization.upload_image_to_imgur(imgur_client, chart_path)

                if img_url:
                    line_user_id,
                    ImageSendMessage(
                        original_content_url=img_url,
                        preview_image_url=img_url
                    )

                    # 刪除本地保存的圖像
                    os.remove(chart_path)
                    response_message = "圖片已成功發送到 LINE"
                else:
                    response_message = "無法上傳圖片到 Imgur"
            else:
                response_message = "無法生成圖表"

        # 發送消息到 LINE 用戶
        if line_user_id and user_text == "查詢":
           line_bot_api.push_message(line_user_id, TextSendMessage(text=user_message ))
           response_message = "資料已成功發送到 LINE"
        elif line_user_id and user_text == "各平台分析圖":
            line_bot_api.push_message(line_user_id, ImageSendMessage(original_content_url = img_url, preview_image_url = img_url))
            response_message = "資料已成功發送到 LINE"
        else:
            response_message = "未提供有效的 LINE ID。"

        return jsonify({"message": response_message})
    except Exception as e:
        print(f"發生錯誤: {e}")
        return jsonify({"message": "伺服器內部錯誤"}), 500

# LIFF 內嵌網頁路徑
@app.route("/hello")
def hello():
    return render_template("ccClub2024Spring_linebot.html", liffid=liffid)

if __name__ == "__main__":
    app.run(port=5000)
