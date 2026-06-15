from fastapi import FastAPI
from pydantic import BaseModel
from agents.graph import build_graph
import json

app = FastAPI(title="Quant AI Server")

# Spring에서 받는 입력 형태
class AgentRequest(BaseModel):
    user_id: int
    risk_level: str           # AGGRESSIVE / NEUTRAL / CONSERVATIVE
    investment_amount: int    # 투자 가능 금액 (원)
    # 17일 확정 후 추가 예정
    # investment_goal: str
    # risk_score: int
    # investment_period: str
    # risk_type: str

# Spring으로 돌려주는 응답 형태
class PortfolioResponse(BaseModel):
    portfolio: dict
    backtest_result: dict
    portfolio_reason: str
    risk_type: str

class ReportResponse(BaseModel):
    sentiment_scores: dict
    portfolio_reason: str

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Quant AI Server Running"}

@app.post("/agent/run")
def run_agent(request: AgentRequest):
    graph = build_graph()
    result = graph.invoke({
        "user_id": request.user_id,
        "risk_level": request.risk_level,
        "investment_amount": request.investment_amount,
        "price_data": {},
        "indicators": {},
        "strategy_result": {},
        "backtest_result": {},
        "orders": [],
        "news_articles": [],
        "sentiment_scores": {},
        "portfolio": {},
        "portfolio_reason": "",
        "risk_ok": False,
        "error_log": []
    })
    return PortfolioResponse(
        portfolio=result.get("portfolio", {}),
        backtest_result=result.get("backtest_result", {}),
        portfolio_reason=result.get("portfolio_reason", ""),
        risk_type=request.risk_level
    )

@app.post("/report/generate")
def generate_report():
    graph = build_graph()
    result = graph.invoke({
        "user_id": 0,
        "risk_level": "NEUTRAL",
        "investment_amount": 0,
        "price_data": {},
        "indicators": {},
        "strategy_result": {},
        "backtest_result": {},
        "orders": [],
        "news_articles": [],
        "sentiment_scores": {},
        "portfolio": {},
        "portfolio_reason": "",
        "risk_ok": False,
        "error_log": []
    })
    return ReportResponse(
        sentiment_scores=result.get("sentiment_scores", {}),
        portfolio_reason=result.get("portfolio_reason", "")
    )