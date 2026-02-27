import streamlit as st
import pandas as pd
from PIL import Image, ImageOps

# 自作モジュールのインポート
from ocr.preprocess import preprocess_image
from ocr.reader import extract_text
from ocr.parser import parse_receipt_text
from utils.csv_export import convert_to_csv

# ==========================================
# UI設定
# ==========================================
st.set_page_config(page_title="レシート読取アプリ", page_icon="🧾", layout="wide", initial_sidebar_state="expanded")

if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

st.title("🧾 レシート自動読取・CSV出力ツール")
st.markdown("画像からレシートの情報を自動抽出し、データ化します。修正後はCSVでダウンロード可能です。")
st.divider()

with st.sidebar:
    st.header("⚙️ 操作パネル")
    uploaded_file = st.file_uploader("📸 レシート画像を選択", type=['png', 'jpg', 'jpeg'])
    
    # 【追加】画像回転スライダー
    rotation_angle = st.slider("🔄 画像の回転 (横向きの場合は調整)", min_value=-90, max_value=90, value=0, step=90)
    
    st.markdown("---")
    analyze_btn = st.button("✨ 解析を実行する", use_container_width=True, type="primary")
    if st.button("🗑️ データをクリア", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

col1, col2 = st.columns([1, 1.5])
with col1:
    st.subheader("🖼️ 画像プレビュー")
    if uploaded_file:
        # 画像を開き、スマホのEXIF情報（自動回転設定）を補正
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        
        # ユーザーがスライダーで設定した角度に回転
        if rotation_angle != 0:
            image = image.rotate(rotation_angle, expand=True)
            
        st.image(image, caption="解析対象のレシート", use_container_width=True)
    else:
        st.info("👈 サイドバーから画像をアップロードしてください。")

with col2:
    st.subheader("📊 抽出結果 (編集可能)")
    if analyze_btn:
        if uploaded_file is None:
            st.warning("⚠️ 画像が選択されていません。")
        else:
            with st.spinner("🤖 AIがレシートを解析中..."):
                try:
                    # サーバーパンク防止のリサイズ
                    image.thumbnail((1200, 1200))
                    
                    processed_img = preprocess_image(image)
                    raw_text = extract_text(processed_img)
                    
                    if not raw_text:
                        st.error("❌ 文字を読み取れませんでした。プレビュー画面で文字が横向きになっていないか確認してください。")
                    else:
                        parsed_data = parse_receipt_text(raw_text)
                        st.session_state.parsed_items = parsed_data["商品一覧"]
                        st.session_state.ocr_completed = True
                        if not parsed_data["整合性OK"]:
                            st.warning("⚠️ 商品合計と記載の合計金額が一致しませんでした。")
                        else:
                            st.success("✅ 解析が完了しました！")
                except Exception as e:
                    st.error(f"🚨 エラーが発生しました: {e}")

    if st.session_state.ocr_completed or len(st.session_state.parsed_items) > 0:
        df = pd.DataFrame(st.session_state.parsed_items)
        if df.empty:
            df = pd.DataFrame(columns=["日付", "店舗名", "商品名", "金額"])
            st.info("ℹ️ 商品をうまく抽出できませんでした。手動で追加できます。")

        edited_df = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config={"金額": st.column_config.NumberColumn("金額 (円)", min_value=0, step=1, format="%d")}
        )
        st.session_state.parsed_items = edited_df.to_dict('records')
        st.markdown("---")
        try:
            csv_data = convert_to_csv(st.session_state.parsed_items)
            st.download_button(label="💾 CSVでダウンロード", data=csv_data, file_name="receipt_data.csv", mime="text/csv", type="primary")
        except Exception as e:
            st.error(f"🚨 CSV生成失敗: {e}")
