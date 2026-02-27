import re
from typing import Dict, Any

def clean_price(price_str: str) -> float:
    cleaned = re.sub(r'[¥￥,円\s]', '', price_str)
    try: return float(cleaned)
    except ValueError: return 0.0

def parse_receipt_text(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    date_pattern = r'\d{4}[年/.-]\d{1,2}[月/.-]\d{1,2}[日]?'
    price_pattern = r'[¥￥]?\s*([0-9,]+)[円]?'

    store_name, date_str, total_price = "不明な店舗", "日付不明", 0.0
    items = []

    date_match = re.search(date_pattern, text)
    if date_match: date_str = date_match.group(0)

    if lines:
        for line in lines[:3]:
            if not re.search(r'\d{2,}', line) and len(line) > 2:
                store_name = line
                break

    for line in lines:
        if "合計" in line or "total" in line.lower() or "合 計" in line:
            match = re.search(price_pattern, line)
            if match: total_price = clean_price(match.group(1))
            continue
            
        match = re.match(r'^(.*?)\s+[¥￥]?\s*([0-9,]+)[円]?$', line)
        if match:
            item_name = match.group(1).strip()
            ignore_words = ["おつり", "現金", "クレジット", "釣銭", "小計", "税"]
            if len(item_name) > 1 and not any(word in item_name for word in ignore_words):
                items.append({
                    "日付": date_str, "店舗名": store_name,
                    "商品名": item_name, "金額": clean_price(match.group(2))
                })

    calculated_sum = sum(item["金額"] for item in items)
    is_valid_sum = (calculated_sum == total_price) if total_price > 0 else True
    if total_price == 0.0: total_price = calculated_sum

    return {
        "店舗名": store_name, "日付": date_str,
        "商品一覧": items, "合計金額": total_price, "整合性OK": is_valid_sum
    }
