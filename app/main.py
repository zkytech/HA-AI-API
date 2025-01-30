from fastapi import FastAPI
from .config import load_config
from .router import router
from .services.openai_service import OpenAIService

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    config = load_config()
    app.state.openai_service = OpenAIService(config.upstream_services)
    app.state.settings = config.settings

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 