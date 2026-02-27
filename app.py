import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
from utils.gemini_engine import analyze_receipt_with_gemini
from utils.csv_export import convert_to_csv

# ==========================================
# 1. ページ設定
# ==========================================
st.set_page_config(page_title="ReceiptFlow | Gemini Edition", page_icon="🧾", layout="wide")

if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

# ==========================================
# 2. サイドバー
# ==========================================
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.markdown("---")
    uploaded_file = st.file_uploader("📸 レシートをアップロード", type=['png', 'jpg', 'jpeg'])
    
    st.info("💡 Gemini 2.5 Flash搭載。画像が横向きでも自動で補正して解析します。")
    
    st.markdown("---")
    analyze_btn = st.button("✨ Geminiで解析を実行", use_container_width=True, type="primary")
    
    if st.button("🗑️ データをリセット", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 3. メインコンテンツ
# ==========================================
st.title("ReceiptFlow")
st.caption("Powered by Gemini 2.5 Flash Vision API")

col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.subheader("📸 Preview")
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        image = ImageOps.exif_transpose(image)
        st.image(image, use_container_width=True, caption="Target Image")
    else:
        st.info("👈 サイドバーから画像をアップロードしてください。")

with col_right:
    st.subheader("📊 Extraction Result")
    
    if analyze_btn:
        if not uploaded_file:
            st.warning("⚠️ 画像をアップロードしてください。")
        else:
            with st.spinner("🤖 Geminiが画像を読み取っています..."):
                try:
                    # Gemini解析の実行
                    result = analyze_receipt_with_gemini(image)
                    
                    st.session_state.parsed_items = result["商品一覧"]
                    st.session_state.ocr_completed = True
                    st.success("✅ Geminiによる高度解析が完了しました！")
                except Exception as e:
                    st.error(f"🚨 解析エラー: {e}")
                    st.info("Tips: StreamlitのSecretsにAPIキーが設定されているか確認してください。")

    if st.session_state.ocr_completed or st.session_state.parsed_items:
        df = pd.DataFrame(st.session_state.parsed_items)
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額 (円)", format="%d"),
            }
        )
        st.session_state.parsed_items = edited_df.to_dict('records')
        
        csv_bytes = convert_to_csv(st.session_state.parsed_items)
        st.download_button(
            label="💾 CSVでダウンロード",
            data=csv_bytes,
            file_name="receipt_gemini_data.csv",
            mime="text/csv",
            use_container_width=True
        )

st.markdown("---")
st.caption("Next Generation Receipt Scanning System | 2026 Model")
