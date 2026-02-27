import pandas as pd

def convert_to_csv(data_list: list) -> bytes:
    # データをExcelで文字化けしないCSV(utf-8-sig)に変換
    df = pd.DataFrame(data_list)
    expected_columns = ["日付", "店舗名", "商品名", "金額"]
    
    if not df.empty:
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_columns]
    else:
        df = pd.DataFrame(columns=expected_columns)

    return df.to_csv(index=False).encode('utf-8-sig')
