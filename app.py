import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import google.generativeai as genai
import json
import re

# ==========================================
# 🎨 1. ページ設定 & デザイン
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Gemini 2.5",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

# ==========================================
# 🧠 2. Gemini 解析エンジン (Secrets: GEMINI_API_KEY を使用)
# ==========================================
def run_gemini_analysis(image):
    """ご指定の GEMINI_API_KEY を使用して解析を実行します"""
    # ここを GEMINI_API_KEY に変更しました
    api_key = st.secrets["GEMINI_API_KEY"]
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash') 

    prompt = """
    レシートを解析し、JSONで返してください。
    項目: store_name, date(YYYY/MM/DD), items(商品名, 金額), total_price
    JSONデータのみを出力し、余計な説明や装飾は省いてください。
    """
    
    response = model.generate_content([prompt, image])
    
    # AIの回答からJSON部分のみを抽出
    json_text = re.search(r'\{.*\}', response.text, re.DOTALL).group()
    data = json.loads(json_text)
    
    return [{
        "日付": data.get("date"),
        "店舗名": data.get("store_name"),
        "商品名": item.get("商品名"),
        "金額": item.get("金額")
    } for item in data.get("items", [])]

# ==========================================
# ⚙️ 3. サイドバー (操作パネル)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.header("Control Center")
    st.caption("Next-Gen Vision Analysis")
    st.divider()
    
    uploaded_file = st.file_uploader("📸 画像を選択", type=['png', 'jpg', 'jpeg'])
    
    st.subheader("🛠️ 調整")
    rotation = st.select_slider("画像の向きを調整 (度)", options=[-90, 0, 90], value=0)
    
    st.divider()
    
    analyze_btn = st.button("✨ 解析を実行する", use_container_width=True, type="primary")
    
    if st.button("🗑️ リセット", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 🏛️ 4. メインエリア
# ==========================================
st.title("ReceiptFlow")
st.markdown("### **Smart Scanner Powered by Gemini 2.5 Flash**")
st.caption("画像をアップロードするだけで、AIが自動的に項目を仕分けしデータ化します。")
st.divider()

col_left, col_right = st.columns([1, 1.4], gap="large")

# --- 左カラム：プレビュー ---
with col_left:
    st.subheader("📸 Preview")
    with st.container(border=True):
        if uploaded_file:
            image = Image.open(uploaded_file).convert("RGB")
            image = ImageOps.exif_transpose(image)
            if rotation != 0:
                image = image.rotate(rotation, expand=True)
            st.image(image, use_container_width=True, caption="Target Image")
        else:
            st.info("サイドバーから画像をアップロードしてください。")

# --- 右カラム：解析結果 ---
with col_right:
    st.subheader("📊 Extraction Result")
    
    if analyze_btn:
        if not uploaded_file:
            st.warning("⚠️ 画像を先にアップロードしてください。")
        else:
            with st.status("🤖 Gemini 2.5 Flashがスキャン中...", expanded=True) as status:
                try:
                    # Gemini解析実行
                    st.session_state.parsed_items = run_gemini_analysis(image)
                    st.session_state.ocr_completed = True
                    status.update(label="✅ 解析が完了しました！", state="complete")
                except Exception as e:
                    status.update(label="🚨 エラーが発生しました", state="error")
                    st.error(f"詳細: {e}")

    # 結果テーブル
    if st.session_state.ocr_completed or st.session_state.parsed_items:
        with st.container(border=True):
            df = pd.DataFrame(st.session_state.parsed_items)
            
            # 編集可能なモダンテーブル
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={"金額": st.column_config.NumberColumn("金額 (円)", format="%d")}
            )
            st.session_state.parsed_items = edited_df.to_dict('records')
            
            st.divider()
            
            # CSVダウンロード
            from utils.csv_export import convert_to_csv
            csv_bytes = convert_to_csv(st.session_state.parsed_items)
            st.download_button(
                label="💾 データをCSVでエクスポート",
                data=csv_bytes,
                file_name="receipt_data.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
    else:
        st.empty()

st.divider()
st.caption("© 2026 ReceiptFlow Pro | Integrated with Gemini AI")
