# QuantAI - AI 서버

> Multi-Agent 기반 퀀트 투자·리포팅 서비스의 AI 서버 파트입니다.
> 수치(주가) 분석과 언어(뉴스) 분석을 분리된 노드로 구성하고, LangGraph StateGraph로 하나의 파이프라인으로 연결합니다.

---

## 담당자

| 이름 | 담당 영역 |
|------|-----------|
| 이주원 | Multi-Agent 파이프라인 설계, LLM 엔진, 가상 매매 |
| 권희재 | 퀀트 엔진, 주가 수집, 백테스트 |

---

## 역할 분담

### 이주원 (AI 서버 · LLM 엔진)
- FastAPI 서버 구조 설계 및 엔드포인트 구현
- LangGraph StateGraph 기반 Multi-Agent 파이프라인 설계
- `safe_node` 장애 격리 래퍼 구현 (노드 실패 시 error_log 기록 후 계속 진행)
- 뉴스 수집 파이프라인 (네이버 뉴스 API 5건 + DART 전자공시 2건)
- Gemini 기반 감성 분석 (−1.0 ~ +1.0 채점, 종목별 평균값 산출)
- 시장 리포트 생성 (3섹션 구조: 요약 / 종목별 흐름 / 주의 종목)
- 투자 성향·기간 조합별 포트폴리오 비중 계산 로직
- 개인화 추천 근거 텍스트 생성 (Gemini 프롬프트 설계)
- 가상 매매 체결 로직 (평균단가 재계산, 트랜잭션 처리, 롤백)
- 커스텀 예외 처리 (`InsufficientBalanceError`, `InsufficientHoldingError`, `InvalidStockError`)
- DB 스키마 설계 (V3 뉴스 기사 · V4 감성 결과 · V6 가상 잔고 · V7 보유 종목 · V8 거래 내역)

### 권희재 (퀀트 엔진)
- yfinance 주가 데이터 수집 및 안정화 (지수 백오프, ±30% 이상치 감지)
- 기술 지표 계산 (MA, RSI, MACD, 볼린저밴드, 거래량 급등)
- 모멘텀 전략 계산 (0.5·R3 + 0.3·R6 + 0.2·R12)
- 롤링 백테스트 구현 (누적 수익률, MDD, Sharpe)
- Redis 현재가 캐시 저장
- DB 스키마 설계 (V5 주가 데이터 · V9 종목 마스터 테이블 및 초기 데이터 삽입)

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| 웹 프레임워크 | FastAPI |
| AI 파이프라인 | LangGraph |
| LLM | Gemini 1.5 Flash |
| 주가 데이터 | yfinance |
| DB 연결 | psycopg2 |
| 캐시 | Redis |

---

## 파이프라인 구조

8개 노드가 하나의 `AgentState`를 공유하며 순서대로 실행됩니다.

```
Node 1. 주가 수집     →  Node 2. 지표 계산     →  Node 3. 뉴스 수집  →  Node 4. 감성 분석
Node 5. 전략          →  Node 6. 백테스트       →  Node 7. 비중 계산  →  Node 8. 리포트 생성
```

- **퀀트 엔진** (Node 1·2·5·6): 수치 기반 계산 담당
- **뉴스·LLM 엔진** (Node 3·4·7·8): 언어 처리 담당
- 모든 노드는 `safe_node` 래퍼로 장애 격리 — 부분 실패 시에도 파이프라인 전체가 중단되지 않음

---

## 주요 기능

### AGENT1 - 시장 리포트
- 네이버 뉴스 API + DART 전자공시에서 종목별 뉴스 수집
- Gemini가 각 기사를 −1.0(악재) ~ +1.0(호재)으로 채점
- 수집된 뉴스 흐름을 바탕으로 3섹션 시장 리포트 자동 생성
- 매일 08:00 Spring 스케줄러에 의해 자동 실행

### AGENT2 - 포트폴리오 추천
- 모멘텀 점수 기반 종목 순위 결정 및 롤링 백테스트 검증
- 투자 성향(AGGRESSIVE / NEUTRAL / STABLE)과 투자 기간(OVER_5Y 등) 조합에 따라 비중 배분
- Gemini가 사용자 목표·성향을 반영한 개인화 추천 근거 생성
- 매월 1일 09:00 Spring 스케줄러에 의해 자동 실행

### AGENT3 - 가상 매매
- Spring 백엔드에서 리스크 검사 통과 후 AI 서버로 주문 전달
- yfinance로 현재가 조회 후 체결 금액 계산
- `portfolios` / `holdings` / `orders` 3개 테이블을 하나의 트랜잭션으로 업데이트
- 중간 오류 발생 시 전체 롤백으로 데이터 정합성 보장

---

## API 엔드포인트

| 메서드 | 경로 | 설명 | 호출 주체 |
|--------|------|------|-----------|
| POST | `/report/generate` | 시장 리포트 생성 | Spring 스케줄러 (매일 08:00) |
| POST | `/api/portfolio/recommend` | 포트폴리오 추천 | Spring 스케줄러 (매월 1일 09:00) |
| POST | `/api/portfolio/execute` | 가상 매매 체결 | Spring 백엔드 |

---

## 실행 방법

### 1. 가상환경 설정

```bash
python -m venv venv
source venv/Scripts/activate  # Windows
source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env.example`을 복사해 `.env` 파일 생성 후 값 입력

```bash
cp .env.example .env
```

```
GEMINI_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
DART_API_KEY=
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
REDIS_HOST=
REDIS_PORT=
```

### 3. 서버 실행

```bash
uvicorn main:app --reload
```

### 4. 파이프라인 단독 실행 (테스트용)

```bash
python -m agents.graph
```
