from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai.tools import tool
import os
from dotenv import load_dotenv
import json
import requests
import traceback

load_dotenv()

router = APIRouter(prefix="/placement", tags=["Placement"])

# Define LLMs
api_key = os.getenv("GROQ_API_KEY")
llm_speed = LLM(model="groq/llama-3.1-8b-instant", api_key=api_key)
llm_pro = LLM(model="groq/llama-3.1-8b-instant", api_key=api_key)

class PlacementRequest(BaseModel):
    resume_text: str
    jd_text: str = ""
    requirement: str = ""

# Custom Search Tool for Resources
@tool("search_resources")
def search_resources(query: str):
    """Search for specific YouTube tutorials, official documentation, and free courses for a technical skill."""
    print(f"🔍 Technical Search: {query}")
    url = "https://google.serper.dev/search"
    # Append specific modifiers to force resource links
    payload = json.dumps({"q": f"{query} official documentation youtube tutorial free course"})
    headers = {
        'X-API-KEY': os.getenv("SERPER_API_KEY"),
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        results = response.json()
        # Return specific link format
        snippets = [f"📖 {r.get('title')}: {r.get('link')}" for r in results.get("organic", [])[:3]]
        return "\n".join(snippets) if snippets else "No resources found. Suggest searching on YouTube."
    except Exception as e:
        return f"Search error: {e}"

@router.post("/analyze_resume")
async def analyze_resume(request: PlacementRequest):
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

        crew = Crew(agents=[analyzer], tasks=[task1], verbose=True, max_rpm=1)
        result = crew.kickoff(inputs={'resume_text': request.resume_text})
        return {"analysis": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skill_gap")
async def skill_gap(request: PlacementRequest):
    try:
        gap_analyst = Agent(
            role='Chief Technology Strategist',
            goal='Map the precise skill bridge between a candidate and their dream job.',
            backstory="""You oversee technical hiring for Fortune 500 companies. 
            You know the 'hidden' skills that aren't on the JD but are required to pass the interview.""",
            tools=[search_resources],
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

        crew = Crew(agents=[gap_analyst], tasks=[task2], verbose=True, max_rpm=1)
        result = crew.kickoff(inputs={'resume_text': request.resume_text, 'jd_text': request.jd_text})
        return {"gap_report": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def general_chat(request: PlacementRequest):
    try:
        response = llm_speed.call([{"role": "user", "content": request.requirement}])
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/career_roadmap")
async def career_roadmap(request: PlacementRequest):
    try:
        # Determine if this is a general query or a roadmap request
        is_roadmap_request = any(word in request.requirement.lower() for word in ["roadmap", "plan", "path", "6 month", "schedule"])
        
        mentor = Agent(
            role='Elite Career Architect',
            goal='Provide high-velocity career guidance and execution plans.',
            backstory="""You are a world-class career coach. You provide strategic, actionable advice. 
            When suggesting resources, use the search_resources tool. 
            IMPORTANT: Use tools ONE AT A TIME and wait for the output before continuing.""",
            tools=[search_resources],
            llm=llm_pro,
            verbose=True
        )

        if is_roadmap_request:
            desc = f"""Based on the Goal: {request.requirement}. 
            Design a 6-Month Elite Career Roadmap.
            For EACH MONTH, you MUST provide:
            1. 📅 **Monthly Focus**: The primary theme.
            2. 🛠️ **Weekly Mastery Tasks**: A breakdown of what to learn.
            3. 🔗 **Curated Resources**: Use your search_resources tool to find and provide 2-3 specific links.
            4. 🏗️ **The 'Portfolio Killer' Project**: A unique project idea.
            5. 📜 **Target Certification**: A specific free or paid certification.
            6. 🤝 **Networking Goal**: One specific action for LinkedIn."""
        else:
            desc = f"""Answer this career query: {request.requirement}.
            Provide a strategic response. If you recommend learning a specific skill, use your search_resources tool to provide links."""

        task = Task(
            description=desc,
            expected_output="A professional response with actionable advice and verified resource links.",
            agent=mentor
        )

        crew = Crew(agents=[mentor], tasks=[task], verbose=True, max_rpm=1)
        result = crew.kickoff()
        return {"roadmap": str(result.raw) if hasattr(result, 'raw') else str(result)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
