from fastapi import FastAPI
from backend.agents.fitness import router as fitness_router
from backend.agents.placement import router as placement_router
from backend.agents.research import router as research_router
from backend.agents.travel import router as travel_router
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI(title="Unified AI Agent Hub API", version="1.0.0")

# Include Routers
app.include_router(fitness_router)
app.include_router(placement_router)
app.include_router(research_router)
app.include_router(travel_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Unified AI Agent Hub API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
