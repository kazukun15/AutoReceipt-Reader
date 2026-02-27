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
    page_title="ReceiptFlow | Batch Scanner",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッションステートの初期化
if "parsed_items" not in st.session_state:
    st.session_state.parsed_items = []

# ==========================================
# 🔑 Gemini APIの初期設定
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("🚨 Streamlit Cloudの Settings > Secrets に `GEMINI_API_KEY` を設定してください。")
    st.stop()

genai.configure(api_key=api_key)
# 無料枠で最大パフォーマンスを発揮する最新のFlashモデルを使用
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
st.title("🧾 ReceiptFlow | Batch Scanner Powered by AI")
st.markdown("複数枚のレシートを一括でアップロードし、すべてのデータを1つのテーブルに自動集約します。")
st.divider()

# サイドバー
with st.sidebar:
    st.header("⚙️ 操作パネル")
    # 【変更点】accept_multiple_files=True で複数選択を可能に
    uploaded_files = st.file_uploader(
        "📸 レシート画像を選択（複数可）", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True,
        help="一度に20枚程度まで一括解析可能です。"
    )
    
    st.markdown("---")
    analyze_btn = st.button("✨ 一括解析を実行", use_container_width=True, type="primary")
    if st.button("🗑️ データをクリア", use_container_width=True):
        st.session_state.parsed_items = []
        st.rerun()

# カラム分割
col1, col2 = st.columns([1, 1.8])

# 🖼️ 左カラム：画像プレビュー（複数対応）
with col1:
    st.subheader("📸 Preview")
    if uploaded_files:
        st.info(f"📂 **{len(uploaded_files)}枚** の画像が選択されています。")
        # 画面が縦に長くなりすぎないよう、Expander（折りたたみ）の中にサムネイルを表示
        with st.expander("プレビュー画像一覧を確認する", expanded=False):
            for file in uploaded_files:
                try:
                    img = Image.open(file).convert('RGB')
                    img = ImageOps.exif_transpose(img)
                    st.image(img, caption=file.name, use_container_width=True)
                except Exception:
                    st.error(f"{file.name} はプレビューできません。")
    else:
        st.info("👈 サイドバーから画像を複数アップロードしてください。")

# 📊 右カラム：解析結果
with col2:
    st.subheader("📊 抽出結果 (編集可能)")
    
    if analyze_btn:
        if not uploaded_files:
            st.warning("⚠️ 画像が選択されていません。")
        else:
            # 複数枚のデータをまとめるための空リスト
            all_parsed_data = []
            
            # UI用のプログレスバーとテキストを用意
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, file in enumerate(uploaded_files):
                status_text.markdown(f"**⏳ 解析中 ({i+1}/{len(uploaded_files)}枚目)...** `{file.name}`")
                
                try:
                    # 1. 画像の読み込みとリサイズ
                    image = Image.open(file).convert('RGB')
                    image = ImageOps.exif_transpose(image)
                    ai_image = image.copy()
                    ai_image.thumbnail((1024, 1024))
                    
                    # 2. Gemini API呼び出し
                    response = model.generate_content([SYSTEM_PROMPT, ai_image])
                    res_text = response.text.strip()
                    
                    # 3. JSONクレンジング
                    if res_text.startswith("```json"): res_text = res_text[7:]
                    if res_text.startswith("```"): res_text = res_text[3:]
                    if res_text.endswith("```"): res_text = res_text[:-3]
                        
                    # 4. JSONパース
                    data = json.loads(res_text.strip())
                    store = data.get("store_name", "")
                    date = data.get("date", "")
                    
                    # 5. 全データリストへ追加（後で分かりやすいよう、元のファイル名も追加）
                    for item in data.get("items", []):
                        all_parsed_data.append({
                            "ファイル名": file.name,
                            "日付": date,
                            "店舗名": store,
                            "商品名": item.get("name", ""),
                            "金額": item.get("price", 0)
                        })
                        
                except Exception as e:
                    st.error(f"🚨 `{file.name}` の処理中にエラーが発生しました: {e}")
                
                # プログレスバーの更新
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                # 【重要】無料APIのレートリミット（1分間15回）を回避するための待機時間
                if i < len(uploaded_files) - 1:
                    time.sleep(4.5) 
            
            # すべて終わったらセッションステートに保存して完了通知
            st.session_state.parsed_items = all_parsed_data
            status_text.success(f"✨ 全 {len(uploaded_files)} 枚の解析が完了しました！")

    # テーブルの表示処理
    if len(st.session_state.parsed_items) > 0:
        df = pd.DataFrame(st.session_state.parsed_items)
        
        # カラムの順番を整理
        expected_columns = ["ファイル名", "日付", "店舗名", "商品名", "金額"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_columns]
            
        edited_df = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "金額": st.column_config.NumberColumn("金額 (円)", min_value=0, step=1, format="%d"),
                "ファイル名": st.column_config.TextColumn("ファイル名", disabled=True) # ファイル名は編集不可にする
            }
        )
        
        st.session_state.parsed_items = edited_df.to_dict('records')
        st.markdown("---")
        
        try:
            # CSVダウンロード
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 結合されたデータをCSVで一括ダウンロード", 
                data=csv_data, 
                file_name="receipt_batch_data.csv", 
                mime="text/csv", 
                type="primary"
            )
        except Exception as e:
            st.error(f"🚨 CSV生成失敗: {e}")
