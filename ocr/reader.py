import easyocr
import pytesseract
import numpy as np
import streamlit as st

@st.cache_resource
def get_easyocr_reader():
    return easyocr.Reader(['ja', 'en'], gpu=False)

def extract_text(preprocessed_img: np.ndarray) -> str:
    reader = get_easyocr_reader()
    extracted_text = []
    try:
        results = reader.readtext(preprocessed_img)
        for (bbox, text, prob) in results:
            if prob > 0.3: extracted_text.append(text)
        final_text = "\n".join(extracted_text)
        if not final_text.strip(): raise ValueError("抽出結果が空です。")
        return final_text
    except Exception as e:
        print(f"EasyOCRエラー: {e} -> Tesseractへフォールバック")
        try:
            return pytesseract.image_to_string(preprocessed_img, lang='jpn+eng')
        except Exception:
            return ""
