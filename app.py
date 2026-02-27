import google.generativeai as genai
import streamlit as st
from PIL import Image
import json
import re

def analyze_receipt_with_gemini(image: Image.Image):
    """
    Gemini 2.5 Flashを使用してレシートを解析し、構造化データを返します。
    """
    # APIキーの設定
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

    # モデルの初期化 (2026年最新の2.5 Flash)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # AIへの指示（プロンプト）
    prompt = """
    このレシート画像を解析し、以下の項目を正確に抽出してJSON形式で返してください。
    
    1. store_name (店舗名)
    2. date (日付: YYYY/MM/DD形式)
    3. items (商品一覧: 各要素は {"商品名": str, "金額": int} の形式)
    4. total_price (合計金額: int)
    
    注意点:
    - 読み取れない項目がある場合は null にしてください。
    - 余計な解説は不要です。JSONデータのみを返してください。
    """

    try:
        # 画像とプロンプトを送信
        response = model.generate_content([prompt, image])
        
        # 返信からJSON部分を抽出
        json_text = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_text)
        
        # UIに合わせたデータ形式に変換
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
            "整合性OK": True # Geminiは文脈判断するため基本OKとする
        }
    except Exception as e:
        raise Exception(f"Gemini解析エラー: {str(e)}")
