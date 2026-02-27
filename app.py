import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import google.generativeai as genai
import json

# 自作モジュールのインポート
from utils.csv_export import convert_to_csv

# ==========================================
# ✨ UI設定 (モダン・ミニマルデザイン)
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Smart Scanner", 
    page_icon="✨", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# セッション状態の初期化（UIをリッチにするため保持項目を追加）
if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "store_name" not in st.session_state: st.session_state.store_name = ""
if "receipt_date" not in st.session_state: st.session_state.receipt_date = ""
if "total_price" not in st.session_state: st.session_state.total_price = 0
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

# ヘッダーデザイン
st.title("✨ ReceiptFlow")
st.markdown("#### Smart Receipt Scanner Powered by AI")
st.markdown("最新のAI Visionモデルを活用し、画像からレシート情報を超高精度に自動抽出・構造化します。")
st.divider()

# ==========================================
# 🔐 APIキーの読み込み
# ==========================================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🔑 エラー: Streamlit Cloudの Secrets に `GEMINI_API_KEY` が登録されていません。")
    st.stop()

# ==========================================
# 🎛️ サイドバー (操作パネル)
# ==========================================
with st.sidebar:
    st.header("⚙️ Control Panel")
    uploaded_file = st.file_uploader("📸 レシート画像をアップロード", type=['png', 'jpg', 'jpeg'])
    
    rotation_angle = st.slider(
        "🔄 プレビューの回転調整", 
        min_value=-90, max_value=90, value=0, step=90, 
        help="※AIは画像が横向きでも自動補正して読み取ります"
    )
    
    st.markdown("---")
    analyze_btn = st.button("🚀 AI解析を実行 (Scan)", use_container_width=True, type="primary")
    if st.button("🗑️ データをクリア (Clear)", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.store_name = ""
        st.session_state.receipt_date = ""
        st.session_state.total_price = 0
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 🖥️ メイン画面レイアウト
# ==========================================
col1, col2 = st.columns([1, 1.6])

# 🖼️ 左カラム：プレビュー
with col1:
    st.markdown("### 📸 Preview")
    if uploaded_file:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image) # スマホ画像の回転バグを自動補正
        if rotation_angle != 0:
            image = image.rotate(rotation_angle, expand=True)
        st.image(image, use_container_width=True, style="border-radius: 10px;")
    else:
        st.info("👈 サイドバーから画像をアップロードしてください")

# 📊 右カラム：抽出結果
with col2:
    st.markdown("### 📊 Extracted Data")
    
    if analyze_btn:
        if uploaded_file is None:
            st.warning("⚠️ 画像がアップロードされていません。")
        else:
            with st.spinner("🧠 優秀なAIがレシートを解析中... (数秒お待ちください)"):
                try:
                    # サーバー保護とパフォーマンス最大化のためのリサイズ
                    image.thumbnail((1600, 1600))
                    
                    # 常に最新で高速・高精度なモデルを選択
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = """
                    あなたは世界最高レベルのレシート解析AIです。
                    提供された画像はレシートです。文字が「横向き」や「逆さま」になっていたり、かすれがあっても、完璧に読み取ってください。
                    以下のルールに従い、厳密にJSONフォーマットのみで出力してください。Markdown装飾は不要です。

                    {
                      "店舗名": "文字列",
                      "日付": "YYYY/MM/DD",
                      "商品一覧": [
                        {"商品名": "文字列", "金額": 数値}
                      ],
                      "合計金額": 数値
                    }

                    ルール:
                    1. 金額は「¥」「,」を除外し、純粋な数値(整数)に変換。
                    2. 「合計」「おつり」「クレジット」等のシステム行は「商品一覧」に含めない。
                    3. 読み取れない項目は空文字列("")または0とする。
                    """
                    
                    response = model.generate_content([prompt, image])
                    raw_json = response.text.strip()
                    
                    # 余分なMarkdownの除去
                    if raw_json.startswith("```json"): raw_json = raw_json[7:]
                    if raw_json.startswith("```"): raw_json = raw_json[3:]
                    if raw_json.endswith("```"): raw_json = raw_json[:-3]
                        
                    result_dict = json.loads(raw_json.strip())
                    
                    # データの保持
                    st.session_state.store_name = result_dict.get("店舗名", "不明な店舗")
                    st.session_state.receipt_date = result_dict.get("日付", "日付不明")
                    st.session_state.total_price = result_dict.get("合計金額", 0)
                    
                    formatted_items = []
                    for item in result_dict.get("商品一覧", []):
                        formatted_items.append({
                            "日付": st.session_state.receipt_date,
                            "店舗名": st.session_state.store_name,
                            "商品名": item.get("商品名", ""),
                            "金額": item.get("金額", 0)
                        })
                        
                    st.session_state.parsed_items = formatted_items
                    st.session_state.ocr_completed = True
                    st.success("✅ スキャンが完了しました！")
                    
                except json.JSONDecodeError:
                    st.error("❌ データの形式変換に失敗しました。もう一度スキャンをお試しください。")
                except Exception as e:
                    st.error(f"🚨 予期せぬエラーが発生しました: {e}")

    # 解析完了後、またはデータが存在する場合のUI描画
    if st.session_state.ocr_completed or len(st.session_state.parsed_items) > 0:
        
        # 💳 サマリーカードの表示 (モダンなUI要素)
        st.markdown("##### 📝 Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("🏪 店舗名 (Store)", st.session_state.store_name)
        m2.metric("📅 日付 (Date)", st.session_state.receipt_date)
        m3.metric("💸 合計金額 (Total)", f"¥ {st.session_state.total_price:,}")
        
        st.markdown("---")
        st.markdown("##### 🛒 Item Details (編集可能)")
        
        df = pd.DataFrame(st.session_state.parsed_items)
        if df.empty:
            df = pd.DataFrame(columns=["日付", "店舗名", "商品名", "金額"])

        # モダンなテーブルエディタ
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額 (円)", min_value=0, step=1, format="¥ %d"),
                "商品名": st.column_config.TextColumn("商品名", max_chars=100)
            }
        )
        st.session_state.parsed_items = edited_df.to_dict('records')
        
        st.write("") # スペーサー
        
        try:
            csv_data = convert_to_csv(st.session_state.parsed_items)
            st.download_button(
                label="💾 CSV形式でエクスポート (Download CSV)", 
                data=csv_data, 
                file_name="receipt_data.csv", 
                mime="text/csv", 
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"🚨 CSV生成失敗: {e}")
