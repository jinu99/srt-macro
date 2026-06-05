#!/usr/bin/env python3
"""SRT 취소표 매크로 — 매진 열차를 반복 조회하여 빈자리 발생 시 즉시 예매 + 슬랙 알림"""

import argparse
import json
import os
import time
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from SRT import SRT
from SRT.passenger import Adult

# .env 로드 (python-dotenv 없이)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def slack_notify(msg):
    """Slack 알림 (SLACK_WEBHOOK_URL이 설정된 경우만 동작)"""
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    try:
        data = json.dumps({"text": msg}).encode()
        req = Request(webhook, data=data, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=5)
    except Exception as e:
        print(f"슬랙 알림 실패: {e}", flush=True)


def run_macro(srt_id, srt_pw, dep, arr, date, time_from, time_to, interval=1.0, duration=None, standby=False, passengers=1, train_filter=None):
    mode = "예약대기" if standby else "취소표 매크로"
    filter_str = f" 열차번호={','.join(train_filter)}" if train_filter else ""
    print(f"🚄 SRT {mode} 시작: {dep}→{arr} {date} {time_from}~{time_to} ({passengers}명){filter_str}")
    pax = [Adult() for _ in range(passengers)]
    if duration:
        print(f"⏱ 최대 {duration}분간 실행")
    srt = SRT(srt_id, srt_pw)
    print("로그인 성공")

    start = time.time()
    attempt = 0
    standby_done = set()  # 이미 예약대기 신청한 열차

    while True:
        if duration and (time.time() - start) > duration * 60:
            msg = f"⏱ {duration}분 경과, {mode} 종료"
            if standby:
                msg += f" (예약대기 {len(standby_done)}건 신청됨)"
            else:
                msg += " (빈자리 없음)"
            print(msg, flush=True)
            slack_notify(msg)
            return None
        attempt += 1
        try:
            trains = srt.search_train(dep, arr, date, f"{time_from}0000", available_only=False)
            for t in trains:
                if t.dep_time >= f"{time_to}0000":
                    break
                if train_filter and t.train_number not in train_filter:
                    continue

                if standby:
                    # 예약대기 가능한 열차에 신청
                    train_key = t.train_number
                    if train_key in standby_done:
                        continue
                    if "예약대기 가능" in str(t):
                        print(f"[{train_key}] 예약대기 신청 중... {t}", flush=True)
                        try:
                            reservation = srt.reserve_standby(t, passengers=pax, special_seat="GENERAL_ONLY")
                            standby_done.add(train_key)
                            print(f"✅ 예약대기 신청 완료! {reservation}", flush=True)
                            slack_notify(f"🚄 SRT 예약대기 신청 완료!\n{t}\n{reservation}")
                        except Exception as e:
                            print(f"[{train_key}] 예약대기 실패: {e}", flush=True)
                else:
                    # 일반 예매 모드
                    if "일반실 예약가능" in str(t):
                        print(f"[시도 {attempt}] 빈자리 발견! {t}", flush=True)
                        reservation = srt.reserve(t, passengers=pax, special_seat="GENERAL_ONLY")
                        print(f"✅ 예매 성공! {reservation}", flush=True)
                        slack_notify(f"🚄 SRT 예매 성공!\n{t}\n예약 정보: {reservation}")
                        return reservation

            if standby and len(standby_done) == len([t for t in trains if t.dep_time < f"{time_to}0000"]):
                msg = f"✅ 모든 열차 예약대기 완료 ({len(standby_done)}건)"
                print(msg, flush=True)
                slack_notify(msg)
                return None

            if not standby:
                print(f"[시도 {attempt}] 매진 — 재시도 중...", flush=True)
        except Exception as e:
            print(f"[시도 {attempt}] 오류: {e}", flush=True)
            if "로그인" in str(e) or "session" in str(e).lower():
                try:
                    srt = SRT(srt_id, srt_pw)
                    print("재로그인 완료", flush=True)
                except Exception as login_err:
                    print(f"재로그인 실패: {login_err}", flush=True)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="SRT 취소표 매크로")
    parser.add_argument("--id", default=os.environ.get("SRT_ID"), help="SRT 회원번호 (기본: .env)")
    parser.add_argument("--pw", default=os.environ.get("SRT_PW"), help="SRT 비밀번호 (기본: .env)")
    parser.add_argument("--dep", required=True, help="출발역 (예: 천안아산)")
    parser.add_argument("--arr", required=True, help="도착역 (예: 수서)")
    parser.add_argument("--date", required=True, help="날짜 YYYYMMDD (예: 20260412)")
    parser.add_argument("--from", dest="time_from", required=True, help="시작 시간 HH (예: 17)")
    parser.add_argument("--to", dest="time_to", required=True, help="종료 시간 HH (예: 18)")
    parser.add_argument("--interval", type=float, default=1.0, help="조회 간격 초 (기본 1.0)")
    parser.add_argument("--duration", type=int, default=None, help="최대 실행 시간 분 (예: 120)")
    parser.add_argument("--standby", action="store_true", help="예약대기 모드 (매진 열차에 대기 신청)")
    parser.add_argument("--passengers", type=int, default=1, help="인원 수 (기본 1)")
    parser.add_argument("--trains", default=None, help="특정 열차번호만 (콤마 구분, 예: 321,323)")

    args = parser.parse_args()
    if not args.id or not args.pw:
        parser.error("--id/--pw가 필요합니다 (또는 .env에 SRT_ID, SRT_PW를 설정하세요)")
    train_filter = set(args.trains.split(",")) if args.trains else None
    run_macro(args.id, args.pw, args.dep, args.arr, args.date, args.time_from, args.time_to, args.interval, args.duration, args.standby, args.passengers, train_filter)


if __name__ == "__main__":
    main()
