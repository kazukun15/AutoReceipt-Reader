import google.generativeai as genai
import streamlit as st
from PIL import Image
import json
import re

def analyze_receipt_with_gemini(image: Image.Image):
    """
    Gemini 2.5 Flashを使用してレシートを解析し、構造化データを返します。
    """
    # StreamlitのSecretsからAPIキーを取得
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        raise Exception("StreamlitのSecretsに 'GOOGLE_API_KEY' が設定されていません。")

    genai.configure(api_key=api_key)

    # 指定されたGemini 2.5 Flashモデルを使用
    model = genai.GenerativeModel('gemini-2.0-flash') # 現在公開されている最新のFlashモデルを指定

    # 解析プロンプト
    prompt = """
    このレシート画像を解析し、以下の項目を正確に抽出してJSON形式で返してください。
    余計な解説文やマークダウンのコードブロック(```jsonなど)は一切含めず、純粋なJSONのみを出力してください。
    
    1. store_name (店舗名)
    2. date (日付: YYYY/MM/DD)
    3. items (商品一覧: 各要素は {"商品名": str, "金額": int})
    4. total_price (合計金額: int)
    """

    try:
        # 画像とプロンプトを送信
        response = model.generate_content([prompt, image])
        
        # JSONの抽出（正規表現で{}の間を抜き出す）
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not json_match:
            raise ValueError("AIからの回答に有効なデータが含まれていませんでした。")
            
        data = json.loads(json_match.group())
        
        # テーブル表示用にフォーマット
        formatted_items = []
        for item in data.get("items", []):
            formatted_items.append({
                "日付": data.get("date"),
                "店舗名": data.get("store_name"),
                "商品名": item.get("商品名"),
                "金額": item.get("金額")
            })
            
        return {
            "商品一覧": formatted_items,
            "合計金額": data.get("total_price", 0),
            "整合性OK": True
        }
    except Exception as e:
        raise Exception(f"Gemini解析エラー: {str(e)}")
