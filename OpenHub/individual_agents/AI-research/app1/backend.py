from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Research & Blog API")

# Define LLM
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

import requests
import json

# Custom Search Tool for Serper.dev
def serper_search(query: str):
    """Search the web for a given query using Serper.dev."""
    try:
        print(f"🔍 Searching for: {query}")
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query})
        headers = {
            'X-API-KEY': os.getenv("SERPER_API_KEY"),
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        results = response.json()
        
        snippets = []
        for result in results.get("organic", [])[:5]:
            snippets.append(f"Title: {result.get('title')}\nSnippet: {result.get('snippet')}\n---")
        
        if not snippets:
            return "No search results found for this query."
        return "\n".join(snippets)
    except Exception as e:
        print(f"❌ Search Tool Error: {e}")
        return f"Error during search: {str(e)}"

class ResearchRequest(BaseModel):
    topic: str

@app.post("/generate_blog")
async def generate_blog(request: ResearchRequest):
    print(f"🚀 Received request for topic: {request.topic}")
    try:
        # 1. Define Agents
        researcher = Agent(
            role='Senior Research Analyst',
            goal='Uncover cutting-edge developments in {topic}',
            backstory="Expert at finding and synthesizing information from the web.",
            tools=[serper_search],
            llm=llm,
            verbose=True,
            max_iter=3
        )

        writer = Agent(
            role='Tech Content Strategist',
            goal='Craft a compelling blog post about {topic}',
            backstory="Professional writer specializing in technical topics.",
            llm=llm,
            verbose=True
        )

        # 2. Define Tasks
        research_task = Task(
            description="Conduct a thorough search on the latest developments in {topic}.",
            expected_output="A detailed summary of the latest research findings.",
            agent=researcher
        )

        write_task = Task(
            description="Using the research provided, write a blog post about {topic} in Markdown.",
            expected_output="A full blog post in markdown format.",
            agent=writer,
            context=[research_task]
        )

        # 3. Assemble and Run
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            process=Process.sequential,
            verbose=True
        )

        print("⚡ Crew is starting execution...")
        result = crew.kickoff(inputs={'topic': request.topic})
        print("✅ Crew finished execution.")
        
        # Ensure we get the raw string output
        final_text = str(result.raw) if hasattr(result, 'raw') else str(result)
        
        return {"blog_post": final_text}

    except Exception as e:
        print(f"💥 Backend Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
