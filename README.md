# srt-macro

SRT 취소표 자동 예매 + 예약대기 매크로. 매진된 열차를 반복 조회해서 빈자리가 나오면 즉시 예매하거나, 매진 열차에 예약대기를 신청합니다. 슬랙 알림도 옵션으로 지원.

> ⚠️ **주의**: SRT 약관상 자동화 도구 사용은 권장되지 않습니다. 본 스크립트는 개인 학습/편의 목적이며, 사용에 따른 책임은 본인에게 있습니다. 너무 짧은 조회 간격(`--interval`)은 IP 차단을 유발할 수 있으니 5초 이상을 권장합니다.

## 기능

- 🎯 **취소표 매크로** — 매진 열차를 폴링, 빈자리 즉시 예매
- ⏳ **예약대기 모드** (`--standby`) — 매진 열차에 자동 예약대기 신청 (결제 불필요)
- 🔢 **인원 / 열차번호 / 시간대 필터**
- ⏱ **최대 실행시간 제한** (`--duration`)
- 💬 **슬랙 알림** (선택) — 예매 성공/실패 시 webhook 전송

## 설치

```bash
git clone https://github.com/<your-username>/srt-macro.git
cd srt-macro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` 파일 생성:

```bash
cp .env.example .env
# .env 파일 열어서 SRT_ID, SRT_PW 입력
```

## 사용법

### 취소표 매크로 (빈자리 잡으면 즉시 예매)

```bash
python srt_macro.py \
  --dep 수서 --arr 부산 \
  --date 20260601 \
  --from 18 --to 21 \
  --interval 5 --duration 60
```

| 옵션 | 설명 |
|---|---|
| `--dep`, `--arr` | 출발역 / 도착역 (예: `수서`, `부산`) |
| `--date` | 날짜 `YYYYMMDD` |
| `--from`, `--to` | 시작/종료 시간 (HH, 예: 18~21) |
| `--interval` | 조회 간격(초). 기본 1.0 — **5초 이상 권장** |
| `--duration` | 최대 실행시간(분). 미지정 시 무제한 |
| `--passengers` | 인원 수 (기본 1) |
| `--trains` | 특정 열차번호만 (콤마 구분, 예: `321,323`) |
| `--standby` | 예약대기 모드 |
| `--id`, `--pw` | 직접 입력 (없으면 `.env`에서 읽음) |

### 예약대기 모드

빈 좌석이 없어도 매진 열차에 예약대기를 신청합니다. 결제 의무 없음.

```bash
python srt_macro.py \
  --dep 수서 --arr 부산 \
  --date 20260601 \
  --from 18 --to 21 \
  --interval 5 --duration 120 \
  --standby
```

### 슬랙 알림 (선택)

`.env`에 `SLACK_WEBHOOK_URL` 추가하면 예매 성공/종료 시 슬랙으로 알림. [Webhook URL 생성 방법](https://api.slack.com/messaging/webhooks).

### cron으로 매일 돌리기

매일 자정~새벽 2시 취소표 매크로 + 새벽 3~5시 예약대기:

```cron
0 0 * * * /path/to/.venv/bin/python /path/to/srt_macro.py --dep 수서 --arr 부산 --date 20260601 --from 18 --to 21 --interval 5 --duration 120 >> /tmp/srt.log 2>&1
0 3 * * * /path/to/.venv/bin/python /path/to/srt_macro.py --dep 수서 --arr 부산 --date 20260601 --from 18 --to 21 --interval 5 --duration 120 --standby >> /tmp/srt.log 2>&1
```

## 동작 원리

[ryanking13/SRT](https://github.com/ryanking13/SRT) (SRTrain 패키지) 라이브러리를 이용해 SRT 모바일 앱이 사용하는 내부 API에 로그인 → 조회 → 예매 흐름을 자동화합니다. 자체 API 호출이라 셀레늄 같은 브라우저 자동화가 불필요합니다.

## 라이선스

MIT
