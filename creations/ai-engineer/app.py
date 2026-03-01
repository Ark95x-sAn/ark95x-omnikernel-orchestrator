from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime
import json

app = FastAPI(title="ARK95X AI Engineer Ignition")

ROADMAP = {
    "month_1": {"title": "Core Foundations", "status": "complete", "topics": ["Python mastery", "Git/GitHub", "Linux CLI", "Data structures", "SQL fundamentals"]},
    "month_2": {"title": "ML Core", "status": "complete", "topics": ["NumPy/Pandas", "Scikit-learn", "Feature engineering", "Model evaluation", "Statistical foundations"]},
    "month_3": {"title": "Deep Learning Systems", "status": "complete", "topics": ["PyTorch", "CNNs", "RNNs/LSTMs", "Transfer learning", "GPU optimization"]},
    "month_4": {"title": "LLMs & Generative AI", "status": "complete", "topics": ["Transformers", "Fine-tuning", "RAG pipelines", "LangChain/CrewAI", "Prompt engineering"]},
    "month_5": {"title": "AI Systems & MLOps", "status": "active", "topics": ["Docker", "Kubernetes", "FastAPI", "CI/CD pipelines", "Model serving"]},
    "month_6": {"title": "Real-World Engineering", "status": "pending", "topics": ["Portfolio projects", "System design", "Production deployment", "Monitoring", "Scale architecture"]},
}

@app.get("/", response_class=HTMLResponse)
async def home():
    html = "<html><head><title>ARK95X AI Engineer Roadmap</title>"
    html += "<style>body{background:#0d1117;color:#c9d1d9;font-family:monospace;padding:20px;}"
    html += ".complete{color:#3fb950;} .active{color:#d29922;} .pending{color:#8b949e;}"
    html += "h1{color:#58a6ff;} .card{border:1px solid #30363d;padding:15px;margin:10px 0;border-radius:6px;}</style></head><body>"
    html += "<h1>ARK95X — Zero to AI Engineer in 6 Months</h1>"
    html += f"<p>Pipeline active | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
    for key, month in ROADMAP.items():
        status_class = month['status']
        icon = '✓' if status_class == 'complete' else '→' if status_class == 'active' else '○'
        html += f"<div class='card'><h3 class='{status_class}'>{icon} {month['title']}</h3>"
        html += "<ul>" + "".join(f"<li>{t}</li>" for t in month['topics']) + "</ul></div>"
    html += "<p>Progress tracked in Legacy Vault. Data pipelines routed through Neuro-Nura.</p>"
    html += "</body></html>"
    return html

@app.get("/api/roadmap")
async def roadmap_api():
    return {"roadmap": ROADMAP, "generated": datetime.now().isoformat(), "version": "v3.0"}

@app.get("/api/status")
async def status():
    total = len(ROADMAP)
    complete = sum(1 for m in ROADMAP.values() if m['status'] == 'complete')
    return {"progress": f"{complete}/{total}", "percent": round(complete/total*100), "current_month": 5}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
