import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import google.generativeai as genai
import json

from utils.csv_export import convert_to_csv

# ==========================================
# ✨ UI設定 (モダン・ミニマル)
# ==========================================
st.set_page_config(page_title="レシート自動読取アプリ", page_icon="🧾", layout="wide", initial_sidebar_state="expanded")

if "parsed_items" not in st.session_state: st.session_state.parsed_items = []
if "ocr_completed" not in st.session_state: st.session_state.ocr_completed = False

st.title("🧾 レシート自動読取・CSV出力ツール")
st.markdown("最新のVision AIモデルを活用し、画像からレシートの情報を超高精度に自動抽出します。")
st.divider()

# ==========================================
# 🔐 APIキーの読み込み
# ==========================================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🔑 エラー: Streamlit Cloudの設定(Secrets)に `GEMINI_API_KEY` が登録されていません。")
    st.stop()

# ==========================================
# 🎛️ サイドバー (操作パネル)
# ==========================================
with st.sidebar:
    st.header("⚙️ 操作パネル")
    uploaded_file = st.file_uploader("📸 レシート画像を選択", type=['png', 'jpg', 'jpeg'])
    
    # ユーザーが目視確認しやすいように回転スライダーは残します
    rotation_angle = st.slider("🔄 画像のプレビュー回転", min_value=-90, max_value=90, value=0, step=90, help="※AIは横向きでも自動補正して読み取ります")
    
    st.markdown("---")
    analyze_btn = st.button("✨ 高精度AI解析を実行", use_container_width=True, type="primary")
    if st.button("🗑️ データをクリア", use_container_width=True):
        st.session_state.parsed_items = []
        st.session_state.ocr_completed = False
        st.rerun()

# ==========================================
# 🖥️ メイン画面
# ==========================================
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("🖼️ 画像プレビュー")
    if uploaded_file:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image) # スマホ特有の回転バグを修正
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
            with st.spinner("🧠 Gemini 2.5 Flashが超高速解析中..."):
                try:
                    # サーバー保護のため解像度を調整（AIが読める十分な画質を維持）
                    image.thumbnail((1600, 1600))
                    
                    # 常に最新・最速・高精度なモデルを指定
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    # 🎯 AIの精度を極限まで高めるための「システムプロンプト」
                    prompt = """
                    あなたは世界最高レベルのレシート解析AIです。
                    提供された画像はレシートです。文字が「横向き」や「逆さま」になっていたり、
                    「かすれ」「影」があっても、脳内で画像を補正して完璧に読み取ってください。

                    以下のルールに従い、厳密にJSONフォーマットのみで出力してください。
                    Markdownのコードブロック(```json ... ```)は絶対に付けないでください。

                    【出力JSONフォーマット】
                    {
                      "店舗名": "文字列",
                      "日付": "YYYY/MM/DD",
                      "商品一覧": [
                        {"商品名": "文字列", "金額": 数値}
                      ],
                      "合計金額": 数値
                    }

                    【抽出ルール】
                    1. 金額は「¥」「円」「, (カンマ)」を除外し、純粋な数値(整数)に変換すること。
                    2. 「合計」「小計」「おつり」「消費税」「クレジット決済」などのシステム行は「商品一覧」に絶対に含めないこと。純粋な購入商品のみをリスト化すること。
                    3. 読み取れない項目は空文字列("")または0にすること。
                    """
                    
                    response = model.generate_content([prompt, image])
                    raw_json = response.text.strip()
                    
                    # AIが気を利かせてMarkdown装飾をつけてしまった場合の除去処理
                    if raw_json.startswith("```json"): raw_json = raw_json[7:]
                    if raw_json.startswith("```"): raw_json = raw_json[3:]
                    if raw_json.endswith("```"): raw_json = raw_json[:-3]
                        
                    result_dict = json.loads(raw_json.strip())
                    
                    # テーブル表示用にデータを整理
                    formatted_items = []
                    store_name = result_dict.get("店舗名", "")
                    date_str = result_dict.get("日付", "")
                    
                    for item in result_dict.get("商品一覧", []):
                        formatted_items.append({
                            "日付": date_str,
                            "店舗名": store_name,
                            "商品名": item.get("商品名", ""),
                            "金額": item.get("金額", 0)
                        })
                        
                    st.session_state.parsed_items = formatted_items
                    st.session_state.ocr_completed = True
                    st.success("✅ AIによる高精度な解析が完了しました！")
                    
                except json.JSONDecodeError:
                    st.error("❌ AIの回答フォーマットが乱れました。お手数ですがもう一度「解析」を押してください。")
                except Exception as e:
                    st.error(f"🚨 予期せぬエラーが発生しました: {e}")

    # テーブルの表示とCSVダウンロード
    if st.session_state.ocr_completed or len(st.session_state.parsed_items) > 0:
        df = pd.DataFrame(st.session_state.parsed_items)
        if df.empty:
            df = pd.DataFrame(columns=["日付", "店舗名", "商品名", "金額"])

        # モダンなデータエディタで直接修正可能に
        edited_df = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            column_config={"金額": st.column_config.NumberColumn("金額 (円)", min_value=0, step=1, format="%d")}
        )
        st.session_state.parsed_items = edited_df.to_dict('records')
        st.markdown("---")
        
        try:
            csv_data = convert_to_csv(st.session_state.parsed_items)
            st.download_button(label="💾 編集データをCSVでダウンロード", data=csv_data, file_name="receipt_data.csv", mime="text/csv", type="primary")
        except Exception as e:
            st.error(f"🚨 CSV生成失敗: {e}")
