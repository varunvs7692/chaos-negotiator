from chaos_negotiator.agent.agent import ChaosNegotiatorAgent
from chaos_negotiator.agent.api import _build_demo_context

if __name__ == '__main__':
    agent = ChaosNegotiatorAgent()
    ctx = _build_demo_context()
    risk = agent.risk_predictor.predict(ctx)
    print('risk assessment:', risk)
    print('score', risk.risk_score, 'level', risk.risk_level, 'confidence', risk.confidence_percent)
    contract = agent.process_deployment(ctx)
    print('contract risk object:', contract.risk_assessment)
    print('contract risk score field:', getattr(contract.risk_assessment, 'risk_score', None))
