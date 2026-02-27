import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
from utils.gemini_engine import analyze_receipt_with_gemini
from utils.csv_export import convert_to_csv

# ==========================================
# 🎨 UI設定（モダンデザイン）
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Gemini 2.5 Flash",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション管理
if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

# ==========================================
# ⚙️ サイドバー（操作パネル）
# ==========================================
with st.sidebar:
    st.image("[https://img.icons8.com/fluency/96/artificial-intelligence.png](https://img.icons8.com/fluency/96/artificial-intelligence.png)", width=60)
    st.header("Control Center")
    st.caption("Gemini 2.5 Flash Edition")
    
    st.divider()
    
    uploaded_file = st.file_uploader(
        "📸 レシート画像をアップロード", 
        type=['png', 'jpg', 'jpeg'],
        help="スマホで撮影したレシート写真を選択してください。"
    )
    
    st.divider()
    
    # 解析実行ボタン
    analyze_btn = st.button("✨ Geminiで解析を開始", use_container_width=True, type="primary")
    
    if st.button("🗑️ データをリセット", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 🏛️ メインコンテンツ
# ==========================================
st.title("ReceiptFlow")
st.markdown("次世代AI **Gemini 2.5 Flash** を活用した超高精度レシートスキャナー。")

st.divider()

col_img, col_res = st.columns([1, 1.4], gap="large")

# --- 左：プレビュー ---
with col_img:
    st.subheader("📸 Preview")
    container = st.container(border=True)
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        image = ImageOps.exif_transpose(image) # 向きを自動補正
        container.image(image, use_container_width=True)
    else:
        container.info("サイドバーから画像をアップロードしてください。")

# --- 右：解析結果 ---
with col_res:
    st.subheader("📊 Extraction Result")
    
    if analyze_btn:
        if not uploaded_file:
            st.warning("⚠️ 画像が選択されていません。")
        else:
            with st.status("🤖 Geminiが解析中...", expanded=True) as status:
                try:
                    # AI解析実行
                    result = analyze_receipt_with_gemini(image)
                    
                    st.session_state.parsed_items = result["商品一覧"]
                    st.session_state.ocr_completed = True
                    status.update(label="✅ 解析が完了しました！", state="complete")
                    
                except Exception as e:
                    status.update(label="🚨 エラー発生", state="error")
                    st.error(f"解析中にエラーが起きました: {e}")

    # 結果表示
    if st.session_state.ocr_completed or st.session_state.parsed_items:
        with st.container(border=True):
            df = pd.DataFrame(st.session_state.parsed_items)
            
            # 編集可能なモダンテーブル
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "金額": st.column_config.NumberColumn("金額 (円)", format="%d"),
                    "商品名": st.column_config.TextColumn("商品名", width="medium"),
                }
            )
            st.session_state.parsed_items = edited_df.to_dict('records')
            
            st.divider()
            
            # ダウンロードボタン
            csv_bytes = convert_to_csv(st.session_state.parsed_items)
            st.download_button(
                label="💾 データをCSVでエクスポート",
                data=csv_bytes,
                file_name="receipt_data.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

st.divider()
st.caption("© 2026 ReceiptFlow Pro | Powered by Google Gemini 2.5 Flash")
