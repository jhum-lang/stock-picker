# 공공데이터포털(금융위원회 주식시세정보)에서 최근 1년 시세를 받아 docs/data.json으로 저장합니다.
import json, os, sys, time, statistics, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta, timezone

KEY = urllib.parse.unquote(os.environ.get("DATA_GO_KR_KEY", "").strip()).strip()
URL = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
# 보고 싶은 종목 이름을 여기에 추가/삭제하세요 (종목명은 정확히 입력)
STOCKS = ["삼성전자", "KT&G", "SK텔레콤", "KB금융", "신한지주", "한국전력",
          "SK하이닉스", "NAVER", "카카오", "셀트리온", "알테오젠", "에코프로",
          "HLB", "두산에너빌리티", "한화에어로스페이스", "크래프톤"]

now = datetime.now(timezone(timedelta(hours=9)))
END = now.strftime("%Y%m%d")
BEGIN = (now - timedelta(days=365)).strftime("%Y%m%d")

def fetch(name):
    q = urllib.parse.urlencode({"serviceKey": KEY, "resultType": "json", "numOfRows": 400,
                                "pageNo": 1, "itmsNm": name, "beginBasDt": BEGIN, "endBasDt": END})
    try:
        with urllib.request.urlopen(URL + "?" + q, timeout=30) as r:
            txt = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError("서버 응답: " + e.read().decode("utf-8", "ignore")[:300])
    try:
        body = json.loads(txt)["response"]["body"]
    except Exception:
        raise RuntimeError("응답 오류: " + txt[:300])
    items = body.get("items") or {}
    items = items.get("item", []) if isinstance(items, dict) else []
    return [items] if isinstance(items, dict) else items

if not KEY:
    sys.exit("인증키(DATA_GO_KR_KEY)가 없어요. GitHub Secrets 설정을 확인하세요.")
print("키 길이:", len(KEY))

result = []
for name in STOCKS:
    try:
        rows = [r for r in fetch(name) if r.get("itmsNm", "").strip() == name]
        rows.sort(key=lambda r: r["basDt"])
        if len(rows) < 20:
            print("건너뜀(데이터 부족):", name); continue
        closes = [float(r["clpr"]) for r in rows]
        rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
        last = rows[-1]
        result.append({"name": name, "code": last.get("srtnCd", ""), "market": last.get("mrktCtg", ""),
                       "date": last["basDt"], "close": closes[-1], "chg": float(last.get("fltRt", 0)),
                       "ret1y": round((closes[-1] / closes[0] - 1) * 100, 1),
                       "vol": round(statistics.stdev(rets) * (250 ** 0.5) * 100, 1),
                       "mcap": float(last.get("mrktTotAmt", 0))})
        print("완료:", name)
    except Exception as e:
        print("실패:", name, type(e).__name__, str(e)[:300])
    time.sleep(0.3)

if not result:
    sys.exit("받아온 종목이 없어요. 인증키/승인 상태를 확인하세요.")
os.makedirs("docs", exist_ok=True)
with open("docs/data.json", "w", encoding="utf-8") as f:
    json.dump({"updated": now.strftime("%Y-%m-%d %H:%M"), "stocks": result}, f, ensure_ascii=False)
print("저장 완료:", len(result), "종목")
