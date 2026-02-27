import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import google.generativeai as genai
import json
import time

# ==========================================
# 🎨 UI設定 (モダンなミニマルデザイン)
# ==========================================
st.set_page_config(
    page_title="ReceiptFlow | Smart Scanner",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッションステートの初期化
if "parsed_items" not in st.session_state:
    st.session_state.parsed_items = []
if "receipt_meta" not in st.session_state:
    st.session_state.receipt_meta = {"store": "", "date": "", "total": 0}

# ==========================================
# 🔑 Gemini APIの初期設定
# ==========================================
# StreamlitのSecretsからAPIキーを安全に取得
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("🚨 Streamlit Cloudの Settings > Secrets に `GEMINI_API_KEY` を設定してください。")
    st.stop()

genai.configure(api_key=api_key)
# 無料で使えて最高性能・最速のモデルを指定
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# 🧠 AIプロンプト (JSON形式で確実に返すように指示)
# ==========================================
SYSTEM_PROMPT = """
あなたは世界最高レベルのデータ入力アシスタントです。
提供されたレシート画像から、以下の情報を抽出し、必ず指定されたJSONフォーマットのみで出力してください。
マークダウンのコードブロック(```json ... ```)は付けず、純粋なJSON文字列のみを返してください。

【必須フォーマット】
{
  "store_name": "店舗名（不明な場合は空文字）",
  "date": "日付（YYYY/MM/DD形式、不明な場合は空文字）",
  "total_price": 1000, 
  "items": [
    {"name": "商品名1", "price": 100},
    {"name": "商品名2", "price": 200}
  ]
}
※金額はカンマや円マークを除去した数値(数値型)にしてください。
"""

# ==========================================
# 🖥️ メイン画面 UI
# ==========================================
st.title("🧾 ReceiptFlow | Powered by Gemini")
st.markdown("最新のAI Visionモデルを活用し、画像からレシート情報を超高精度に自動抽出・構造化します。")
st.divider()

# サイドバー
with st.sidebar:
    st.header("⚙️ 操作パネル")
    uploaded_file = st.file_uploader("📸 レシート画像を選択", type=['png', 'jpg', 'jpeg'])
    
    st.markdown("---")
    analyze_btn = st.button("✨ AI解析を実行", use_container_width=True, type="primary")
    if st.button("🗑️ データをクリア", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.receipt_meta = {"store": "", "date": "", "total": 0}
        st.rerun()

col1, col2 = st.columns([1, 1.5])

# 🖼️ 左カラム：画像プレビュー
with col1:
    st.subheader("📸 Preview")
    if uploaded_file:
        try:
            # 画像を安全に読み込み、スマホの回転を補正
            image = Image.open(uploaded_file).convert('RGB')
            image = ImageOps.exif_transpose(image)
            st.image(image, use_container_width=True, caption="アップロードされたレシート")
        except Exception as e:
            st.error(f"画像の読み込みに失敗しました: {e}")
            image = None
    else:
        st.info("👈 サイドバーから画像をアップロードしてください。")
        image = None

# 📊 右カラム：解析結果
with col2:
    st.subheader("📊 抽出結果 (編集可能)")
    
    if analyze_btn:
        if image is None:
            st.warning("⚠️ 画像が選択されていません。")
        else:
            with st.spinner("🤖 Gemini AIがレシートを解析中..."):
                try:
                    # 通信量削減のため、リサイズしたコピー画像をAIに渡す
                    ai_image = image.copy()
                    ai_image.thumbnail((1024, 1024))
                    
                    # Gemini API呼び出し
                    response = model.generate_content([SYSTEM_PROMPT, ai_image])
                    res_text = response.text.strip()
                    
                    # Markdownのコードブロック記号が含まれていたら除去
                    if res_text.startswith("```json"):
                        res_text = res_text[7:]
                    if res_text.startswith("```"):
                        res_text = res_text[3:]
                    if res_text.endswith("```"):
                        res_text = res_text[:-3]
                        
                    # JSONとしてパース
                    data = json.loads(res_text.strip())
                    
                    # セッションステートに保存
                    st.session_state.receipt_meta = {
                        "store": data.get("store_name", ""),
                        "date": data.get("date", ""),
                        "total": data.get("total_price", 0)
                    }
                    st.session_state.parsed_items = data.get("items", [])
                    st.success("✅ 解析が完了しました！")
                    
                except json.JSONDecodeError:
                    st.error("❌ AIからの応答を正しく読み取れませんでした。もう一度お試しください。")
                except Exception as e:
                    error_msg = str(e).lower()
                    # 429エラー (クォータ超過) のハンドリング
                    if "429" in error_msg or "quota" in error_msg:
                        st.error("⏳ 無料枠の制限(連続リクエスト)に達しました。約1分待ってから再度お試しください。")
                    else:
                        st.error(f"🚨 予期せぬエラーが発生しました: {e}")

    # テーブルの表示処理
    if len(st.session_state.parsed_items) > 0:
        meta = st.session_state.receipt_meta
        st.markdown(f"**🏢 店舗名:** {meta['store']}　｜　**📅 日付:** {meta['date']}　｜　**💰 記載合計:** {meta['total']}円")
        
        # DataFrame化
        df = pd.DataFrame(st.session_state.parsed_items)
        # カラム名が英語なので日本語に変換
        if not df.empty and "name" in df.columns and "price" in df.columns:
            df = df.rename(columns={"name": "商品名", "price": "金額"})
            # 日付と店舗名を追加
            df.insert(0, "店舗名", meta["store"])
            df.insert(0, "日付", meta["date"])
            
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={"金額": st.column_config.NumberColumn("金額 (円)", min_value=0, step=1, format="%d")}
        )
        
        st.markdown("---")
        try:
            # CSVダウンロード
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 CSVでダウンロード", 
                data=csv_data, 
                file_name="receipt_data.csv", 
                mime="text/csv", 
                type="primary"
            )
        except Exception as e:
            st.error(f"🚨 CSV生成失敗: {e}")
