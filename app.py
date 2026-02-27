import os

PROJECT_NAME = "receipt-reader"

# アプリケーションを構成する全ファイルの完全コード
FILES = {
    "requirements.txt": r"""streamlit==1.31.0
opencv-python-headless==4.9.0.80
easyocr==1.7.1
pytesseract==0.3.10
Pillow==10.2.0
pandas==2.2.0
numpy==1.26.4
""",

    "README.md": r"""# 🧾 レシート読取・CSV出力アプリ (Receipt Reader)

高精度OCR技術を用いて、レシート画像から「店舗名」「商品名」「金額」「日付」を自動抽出し、編集可能なテーブルで確認・CSV出力ができるStreamlitアプリケーションです。

## ✨ 主な機能
- 📸 **画像アップロード**: JPG / PNG / JPEG形式に対応
- 🔍 **高精度OCR**: OpenCVによる前処理と EasyOCR + Tesseractの多段処理
- 📊 **データ編集**: 抽出されたデータをUI上で直接編集可能
- 💾 **CSVエクスポート**: 編集後のデータをExcel対応のCSV形式でダウンロード

## 🚀 実行方法
```bash
pip install -r requirements.txt
streamlit run app.py
