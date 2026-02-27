import os

# 作成するディレクトリ
os.makedirs("ocr", exist_ok=True)
os.makedirs("utils", exist_ok=True)

# 空の初期化ファイル（モジュールとして認識させるため必須）
open("ocr/__init__.py", "w", encoding="utf-8").close()
open("utils/__init__.py", "w", encoding="utf-8").close()

# 1. ocr/preprocess.py
with open("ocr/preprocess.py", "w", encoding="utf-8") as f:
    f.write("""import cv2
import numpy as np
from PIL import Image

def preprocess_image(image_pil: Image.Image) -> np.ndarray:
    # 画像をOpenCV形式に変換し、グレースケール化・ノイズ除去・二値化・傾き補正を行う
    img_array = np.array(image_pil)
    if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_cv = img_array

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(cv2.bitwise_not(binary) > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = binary.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        return rotated
    return binary
""")

# 2. ocr/reader.py
with open("ocr/reader.py", "w", encoding="utf-8") as f:
    f.write("""import easyocr
import pytesseract
import numpy as np
import streamlit as st

@st.cache_resource
def get_easyocr_reader():
    return easyocr.Reader(['ja', 'en'], gpu=False)

def extract_text(preprocessed_img: np.ndarray) -> str:
    # EasyOCRで読み取り、失敗時はTesseractへフォールバック
    reader = get_easyocr_reader()
    extracted_text = []
    try:
        results = reader.readtext(preprocessed_img)
        for (bbox, text, prob) in results:
            if prob > 0.3:
                extracted_text.append(text)
        final_text = "\\n".join(extracted_text)
        if not final_text.strip():
            raise ValueError("抽出結果が空です。")
        return final_text
    except Exception as e:
        print(f"EasyOCRエラー: {e} -> Tesseractへフォールバック")
        try:
            return pytesseract.image_to_string(preprocessed_img, lang='jpn+eng')
        except Exception:
            return ""
""")

# 3. ocr/parser.py
with open("ocr/parser.py", "w", encoding="utf-8") as f:
    f.write("""import re
from typing import Dict, Any

def clean_price(price_str: str) -> float:
    cleaned = re.sub(r'[¥￥,円\\s]', '', price_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def parse_receipt_text(text: str) -> Dict[str, Any]:
    # 正規表現を用いて店舗名、日付、商品名、金額を構造化して抽出
    lines = [line.strip() for line in text.split('\\n') if line.strip()]
    date_pattern = r'\\d{4}[年/.-]\\d{1,2}[月/.-]\\d{1,2}[日]?'
    price_pattern = r'[¥￥]?\\s*([0-9,]+)[円]?'

    store_name, date_str, total_price = "不明な店舗", "日付不明", 0.0
    items = []

    date_match = re.search(date_pattern, text)
    if date_match:
        date_str = date_match.group(0)

    if lines:
        for line in lines[:3]:
            if not re.search(r'\\d{2,}', line) and len(line) > 2:
                store_name = line
                break

    for line in lines:
        if "合計" in line or "total" in line.lower() or "合 計" in line:
            match = re.search(price_pattern, line)
            if match:
                total_price = clean_price(match.group(1))
            continue
            
        match = re.match(r'^(.*?)\\s+[¥￥]?\\s*([0-9,]+)[円]?$', line)
        if match:
            item_name = match.group(1).strip()
            ignore_words = ["おつり", "現金", "クレジット", "釣銭", "小計", "税"]
            if len(item_name) > 1 and not any(word in item_name for word in ignore_words):
                items.append({
                    "日付": date_str, "店舗名": store_name,
                    "商品名": item_name, "金額": clean_price(match.group(2))
                })

    calculated_sum = sum(item["金額"] for item in items)
    is_valid_sum = (calculated_sum == total_price) if total_price > 0 else True
    if total_price == 0.0: total_price = calculated_sum

    return {
        "店舗名": store_name, "日付": date_str,
        "商品一覧": items, "合計金額": total_price, "整合性OK": is_valid_sum
    }
""")

# 4. utils/csv_export.py
with open("utils/csv_export.py", "w", encoding="utf-8") as f:
    f.write("""import pandas as pd

def convert_to_csv(data_list: list) -> bytes:
    # データをExcelで文字化けしないCSV(utf-8-sig)に変換
    df = pd.DataFrame(data_list)
    expected_columns = ["日付", "店舗名", "商品名", "金額"]
    
    if not df.empty:
        for col in expected_columns:
            if col not in df.columns: df[col] = ""
        df = df[expected_columns]
    else:
        df = pd.DataFrame(columns=expected_columns)

    return df.to_csv(index=False).encode('utf-8-sig')
""")

print("✨ 足りなかったフォルダとファイルの作成が完了しました！")
