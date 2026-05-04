from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import tool
import os
from dotenv import load_dotenv
import json
import requests
import traceback

# Explicitly load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

app = FastAPI(title="AI Placement Hub API")

# Define LLMs
api_key = os.getenv("GROQ_API_KEY")
llm_speed = LLM(model="groq/llama-3.1-8b-instant", api_key=api_key)
llm_pro = LLM(model="groq/llama-3.3-70b-versatile", api_key=api_key)

class PlacementRequest(BaseModel):
    resume_text: str
    jd_text: str = ""
    requirement: str = ""

# Custom Search Tool for Resources
@tool("placement_search")
def placement_search(query: str):
    """Search for elite learning resources, high-authority courses, and certifications."""
    print(f"🔍 Elite Search for: {query}")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} professional course documentation roadmap"})
    headers = {
        'X-API-KEY': os.getenv("SERPER_API_KEY"),
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        results = response.json()
        snippets = [f"🚀 {r.get('title')}\n🔗 {r.get('link')}\n---" for r in results.get("organic", [])[:4]]
        return "\n".join(snippets) if snippets else "No elite resources found."
    except Exception as e:
        print(f"❌ Search Error: {e}")
        return "Search service temporarily unavailable."

@app.post("/analyze_resume")
async def analyze_resume(request: PlacementRequest):
    print(f"👑 Starting Elite Resume Audit...")
    try:
        analyzer = Agent(
            role='Elite Silicon Valley Executive Recruiter',
            goal='Provide a high-stakes audit of the resume to guarantee interviews at top-tier firms.',
            backstory="""You are the legendary recruiter who helped build teams at Google, OpenAI, and NVIDIA. 
            You don't just 'check' resumes; you transform them into career-defining documents. 
            You are ruthless, precise, and highly strategic.""",
            llm=llm_pro,
            verbose=True
        )

        task1 = Task(
            description="""Perform a high-level strategic audit of this resume: {resume_text}
            
            Strictly provide an 'Elite Pro' report with:
            1. 📈 **Executive Scorecard**: ATS Score, Readability, and Impact Score.
            2. 🎯 **Industry Dominance**: 3 high-growth sectors for this profile.
            3. 🏗️ **Projects Deep Dive**: Analysis of project complexity and 'production-readiness'.
            4. 🛠️ **Skill Inventory**: 'Core Stack', 'Soft Skills', and 'Missing Skills'.
            5. 🔥 **Keyword Heatmap**: Missing critical keywords.
            6. ✍️ **The STAR Transformation**: Rewriting 3 bullets for massive impact.
            7. 📝 **Resume Rewriting Tips**: 5 expert tips to instantly improve the document's layout and flow.
            8. 💻 **Technical Interview Prep**: 30 technical questions based on the resume's skills.
            9. 🤝 **HR & Behavioral Prep**: 30 high-impact HR questions to test soft skills and culture fit.
            10. 🏁 **Final Feedback Summary**: A concise, hard-hitting wrap-up of what needs to change immediately.""",
            expected_output="An elite, hyper-detailed markdown report with 10 distinct sections.",
            agent=analyzer
        )

        crew = Crew(agents=[analyzer], tasks=[task1], verbose=True)
        result = crew.kickoff(inputs={'resume_text': request.resume_text})
        return {"analysis": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        print(f"💥 Analysis Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/skill_gap")
async def skill_gap(request: PlacementRequest):
    try:
        gap_analyst = Agent(
            role='Chief Technology Strategist',
            goal='Map the precise skill bridge between a candidate and their dream job.',
            backstory="""You oversee technical hiring for Fortune 500 companies. 
            You know the 'hidden' skills that aren't on the JD but are required to pass the interview.""",
            tools=[placement_search],
            llm=llm_pro,
            verbose=True
        )

        task2 = Task(
            description="""Compare Resume: {resume_text} with Job Description: {jd_text}.
            Provide a Pro-Level Gap Analysis:
            1. 📊 **Match Matrix**: A sophisticated table showing Match/Missing status.
            2. 💰 **Salary Gap**: What is the estimated salary difference between knowing and NOT knowing these missing skills?
            3. 📚 **The Master Syllabus**: For EVERY missing skill, find the ONE definitive YouTube 'Deep Dive' and the official Documentation/Certification link.
            4. ⚡ **Interview Deal-Breakers**: Which missing skills will cause an instant rejection?""",
            expected_output="A high-authority technical report with actionable learning paths.",
            agent=gap_analyst
        )

        crew = Crew(agents=[gap_analyst], tasks=[task2], verbose=True)
        result = crew.kickoff(inputs={'resume_text': request.resume_text, 'jd_text': request.jd_text})
        return {"gap_report": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def general_chat(request: PlacementRequest):
    try:
        response = llm_speed.call([{"role": "user", "content": request.requirement}])
        return {"response": response}
    except Exception as e:
        print(f"💥 Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/career_roadmap")
async def career_roadmap(request: PlacementRequest):
    try:
        mentor = Agent(
            role='Elite Career Architect & Venture Partner',
            goal='Design a high-velocity 6-month career roadmap to reach the top 1% of the industry.',
            backstory="""You coach future CTOs and Founders. You don't just give 'tips'; 
            you provide a brutal, efficient, and world-class execution plan.""",
            tools=[placement_search],
            llm=llm_pro,
            verbose=True
        )

        task3 = Task(
            description="""Based on Goal: {requirement} and Resume: {resume_text}.
            Design a 6-Month Elite Career Roadmap.
            For EACH MONTH, you MUST provide:
            1. 📅 **Monthly Focus**: The primary theme (e.g. Month 1: Systems Design).
            2. 🛠️ **Weekly Mastery Tasks**: A breakdown of what to learn each week.
            3. 🔗 **Curated Resources**: 2-3 specific YouTube/Documentation links for the month's topics.
            4. 🏗️ **The 'Portfolio Killer' Project**: A unique, impressive project idea to build THIS month.
            5. 📜 **Target Certification**: A specific free or paid certification to complete this month.
            6. 🤝 **Networking Goal**: One specific action for LinkedIn or industry outreach.""",
            expected_output="A comprehensive 6-month roadmap with clear headings for Projects and Certifications in every month.",
            agent=mentor
        )

        crew = Crew(agents=[mentor], tasks=[task3], verbose=True)
        result = crew.kickoff(inputs={'resume_text': request.resume_text, 'requirement': request.requirement})
        return {"roadmap": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
