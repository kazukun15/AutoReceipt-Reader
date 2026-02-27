import streamlit as st
import pandas as pd
from PIL import Image, ImageOps

# 自作モジュールのインポート（既存のパスを維持）
from ocr.preprocess import preprocess_image
from ocr.reader import extract_text
from ocr.parser import parse_receipt_text
from utils.csv_export import convert_to_csv

# ==========================================
# 🎨 ページ設定・カスタムデザイン
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Smart Scanner",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if "parsed_items" not in st.session_state: 
    st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: 
    st.session_state.ocr_completed = False

# ==========================================
# ⚙️ サイドバー（操作パネル）
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/receipt.png", width=80)
    st.header("⚙️ Control Center")
    st.write("画像をアップロードして解析を開始してください。")
    
    st.divider()
    
    # ファイルアップローダー
    uploaded_file = st.file_uploader(
        "📸 レシート画像を選択", 
        type=['png', 'jpg', 'jpeg'],
        help="JPG, PNG, JPEG形式に対応しています。"
    )
    
    # 画像回転オプション
    st.subheader("🔄 Image Adjustment")
    rotation_angle = st.select_slider(
        "画像の回転 (度)",
        options=[-90, 0, 90],
        value=0,
        help="文字が横向きの場合は、縦向きになるよう調整してください。"
    )
    
    st.divider()
    
    # アクションボタン
    analyze_btn = st.button("✨ 解析を実行する", use_container_width=True, type="primary")
    
    if st.button("🗑️ データをクリア", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 🏛️ メインエリア
# ==========================================
st.title("ReceiptFlow")
st.caption("Advanced AI Receipt Recognition & Structured Data Export")
st.markdown("最新のAI Vision技術を活用し、レシートから情報を瞬時に抽出します。")

st.divider()

col1, col2 = st.columns([1, 1.4], gap="large")

# --- 左カラム：画像プレビュー ---
with col1:
    st.subheader("📸 Preview")
    preview_container = st.container(border=True)
    
    if uploaded_file:
        try:
            # 画像の安全な読み込み
            image = Image.open(uploaded_file).convert('RGB')
            image = ImageOps.exif_transpose(image)
            
            # 回転処理
            if rotation_angle != 0:
                image = image.rotate(rotation_angle, expand=True)
            
            # リサイズ（メモリ保護）
            image.thumbnail((1200, 1200))
            
            # プレビュー表示
            preview_container.image(image, use_container_width=True, caption="Scan Target")
            
        except Exception as e:
            st.error(f"画像の読み込みに失敗しました: {e}")
    else:
        preview_container.info("👈 サイドバーから画像をアップロードしてください。")
        preview_container.image("https://img.icons8.com/ios/100/cccccc/image-gallery.png", width=100)

# --- 右カラム：解析結果 ---
with col2:
    st.subheader("📊 Extraction Result")
    
    # 解析実行時の処理
    if analyze_btn:
        if uploaded_file is None:
            st.warning("⚠️ まずは画像をアップロードしてください。")
        else:
            with st.status("🤖 AIがレシートを解析中...", expanded=True) as status:
                try:
                    # OCRパイプライン実行
                    st.write("1. 画像を最適化しています...")
                    processed_img = preprocess_image(image)
                    
                    st.write("2. 文字を抽出しています...")
                    raw_text = extract_text(processed_img)
                    
                    if not raw_text:
                        status.update(label="❌ 解析失敗", state="error")
                        st.error("文字を読み取れませんでした。向きを確認してください。")
                    else:
                        st.write("3. データを構造化しています...")
                        parsed_data = parse_receipt_text(raw_text)
                        
                        st.session_state.parsed_items = parsed_data["商品一覧"]
                        st.session_state.ocr_completed = True
                        
                        if not parsed_data["整合性OK"]:
                            status.update(label="⚠️ 解析完了（要確認）", state="error")
                            st.warning("合計金額が一致しません。手動で修正してください。")
                        else:
                            status.update(label="✅ 解析完了！", state="complete")
                            st.success("全ての情報を正確に抽出しました。")
                except Exception as e:
                    status.update(label="🚨 エラー発生", state="error")
                    st.error(f"システムエラー: {e}")

    # テーブル表示とデータ編集
    if st.session_state.ocr_completed or len(st.session_state.parsed_items) > 0:
        with st.container(border=True):
            df = pd.DataFrame(st.session_state.parsed_items)
            if df.empty:
                df = pd.DataFrame(columns=["日付", "店舗名", "商品名", "金額"])
                st.info("ℹ️ 商品が抽出されませんでした。行を追加して入力してください。")

            # モダンなデータエディタ
            edited_df = st.data_editor(
                df, 
                num_rows="dynamic", 
                use_container_width=True,
                column_config={
                    "金額": st.column_config.NumberColumn(
                        "金額 (円)", 
                        min_value=0, 
                        step=1, 
                        format="%d",
                        help="数値を入力してください"
                    ),
                    "商品名": st.column_config.TextColumn("商品名", width="medium"),
                    "日付": st.column_config.TextColumn("日付", width="small"),
                }
            )
            
            # ステート更新
            st.session_state.parsed_items = edited_df.to_dict('records')
            
            st.divider()
            
            # CSVダウンロードボタン
            try:
                csv_data = convert_to_csv(st.session_state.parsed_items)
                st.download_button(
                    label="💾 データをCSVでエクスポート", 
                    data=csv_data, 
                    file_name="receipt_data.csv", 
                    mime="text/csv", 
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"CSV生成に失敗しました: {e}")
    else:
        st.empty()

# ==========================================
# 🏁 フッター
# ==========================================
st.divider()
st.caption("© 2026 ReceiptFlow Pro | Powered by Gemini & Streamlit")
