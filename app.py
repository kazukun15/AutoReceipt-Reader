import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io

# 自作モジュールのインポート
from ocr.preprocess import preprocess_image
from ocr.reader import extract_text
from ocr.parser import parse_receipt_text
from utils.csv_export import convert_to_csv

# ==========================================
# 1. プロ仕様の初期設定
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Smart Scanner", 
    page_icon="🧾", 
    layout="wide"
)

# セッション管理
if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

# ==========================================
# 2. サイドバー：操作パネル
# ==========================================
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.markdown("---")
    
    # 画像アップロード
    uploaded_file = st.file_uploader(
        "📸 レシートをアップロード", 
        type=['png', 'jpg', 'jpeg'],
        help="高解像度のスマホ写真でも自動で最適化されます"
    )
    
    # 画像補正：より直感的なスライダー
    st.subheader("🛠️ 補正オプション")
    rotation_angle = st.select_slider(
        "画像を回転（文字を水平に）",
        options=[-90, 0, 90],
        value=0,
        help="プレビュー画面で文字が正しく読める向きに調整してください"
    )
    
    st.markdown("---")
    
    # 解析実行（メインアクション）
    analyze_btn = st.button("✨ 解析を実行する", use_container_width=True, type="primary")
    
    # クリア
    if st.button("🗑️ データをリセット", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 3. メインコンテンツ
# ==========================================
st.title("ReceiptFlow")
st.caption("AI-Powered High-Precision Receipt Analysis System")

col_left, col_right = st.columns([1, 1.2], gap="large")

# --- 左側：画像プレビュー & 処理 ---
with col_left:
    st.subheader("📸 Preview")
    if uploaded_file:
        try:
            # プロの画像読み込み：EXIF補正 + RGB正規化
            raw_image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(raw_image).convert("RGB")
            
            # 回転処理
            if rotation_angle != 0:
                image = image.rotate(rotation_angle, expand=True)
            
            # プレビュー表示
            st.image(image, use_container_width=True, caption="Scan Target")
            
        except Exception as e:
            st.error(f"画像の読み込みに失敗しました。ファイル形式を確認してください。({e})")
    else:
        st.info("👈 サイドバーからレシート画像をアップロードしてください。")

# --- 右側：抽出結果 ---
with col_right:
    st.subheader("📊 Result")
    
    if analyze_btn:
        if not uploaded_file:
            st.warning("⚠️ 画像を先にアップロードしてください。")
        else:
            with st.spinner("🤖 AIが解析中..."):
                try:
                    # 1. サーバー保護：解析用にコピーを作成してリサイズ
                    process_image_target = image.copy()
                    process_image_target.thumbnail((1200, 1200)) # メモリ消費を抑制
                    
                    # 2. OCRパイプライン実行
                    # 前処理 (OpenCV)
                    processed_cv_img = preprocess_image(process_image_target)
                    
                    # テキスト抽出 (EasyOCR/Tesseract)
                    extracted_text = extract_text(processed_cv_img)
                    
                    if not extracted_text.strip():
                        st.error("❌ 文字を検出できませんでした。画像の明るさや向きを調整してください。")
                    else:
                        # 3. 構造化解析 (Regex)
                        parsed_result = parse_receipt_text(extracted_text)
                        st.session_state.parsed_items = parsed_result["商品一覧"]
                        st.session_state.ocr_completed = True
                        
                        # 4. フィードバック
                        if parsed_result["整合性OK"]:
                            st.success("✅ 解析完了！合計金額の整合性も確認されました。")
                        else:
                            st.warning("⚠️ 解析完了。合計金額が合わないため、手動で修正をお願いします。")
                            
                except Exception as e:
                    st.error(f"🚨 解析エンジンでエラーが発生しました: {e}")

    # 5. エディタ & エクスポート
    if st.session_state.ocr_completed or st.session_state.parsed_items:
        df = pd.DataFrame(st.session_state.parsed_items)
        
        # 編集可能なモダンテーブル
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額 (円)", format="%d", min_value=0),
                "商品名": st.column_config.TextColumn("商品名", help="商品名を自由に編集できます"),
                "日付": st.column_config.TextColumn("日付", width="medium"),
                "店舗名": st.column_config.TextColumn("店舗名"),
            }
        )
        
        # 編集結果を反映
        st.session_state.parsed_items = edited_df.to_dict('records')
        
        # CSV出力（Excel対応）
        csv_bytes = convert_to_csv(st.session_state.parsed_items)
        st.download_button(
            label="💾 CSV形式でダウンロード",
            data=csv_bytes,
            file_name="receipt_data.csv",
            mime="text/csv",
            use_container_width=True
        )

st.markdown("---")
st.caption("Advanced OCR Engine: Hybrid EasyOCR & Tesseract")
