from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM
import os
import json
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/fitness", tags=["Fitness"])

# Define LLM
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    max_retries=5
)

class FitnessRequest(BaseModel):
    age: str
    weight: str
    height: str
    goal: str
    equipment: str
    diet_pref: str

@router.post("/chat")
async def fitness_chat(request: dict):
    user_message = request.get("message", "")
    if not user_message: return {}
    
    # Simple intent parsing for fitness
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = f"""Extract fitness details from: '{user_message}' into JSON: goal, age, weight, height, equipment, diet_pref. 
    Also add a boolean 'is_plan_request' if the user specifically wants a full workout/diet plan. 
    Return ONLY JSON."""
    
    try:
        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        parsed = json.loads(comp.choices[0].message.content)
        
        # If it's not a plan request, just give a general answer
        if not parsed.get("is_plan_request", False):
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an elite Senior Fitness Coach. Answer the user's query concisely and professionally."},
                    {"role": "user", "content": user_message}
                ]
            )
            return {"response": resp.choices[0].message.content, "parsed": parsed}
        
        return {"parsed": parsed}
    except Exception as e:
        print(f"Chat Error: {e}")
        return {"response": "I'm having a bit of trouble connecting. Can you try again?", "parsed": {}}

@router.post("/generate_plan")
async def generate_plan(request: FitnessRequest):
    try:
        # 1. Define Agents
        trainer = Agent(
            role='Senior Fitness Coach',
            goal='Design a personalized {goal} workout plan.',
            backstory="Expert in strength training and biomechanics.",
            llm=llm,
            verbose=True
        )

        nutritionist = Agent(
            role='Certified Nutritionist',
            goal='Create a meal plan supporting {goal} and {diet_pref}.',
            backstory="Specialist in macros and metabolic health.",
            llm=llm,
            verbose=True
        )

        health_advisor = Agent(
            role='Wellness Consultant',
            goal='Provide 5 essential health and recovery tips for {goal}.',
            backstory="Expert in sports science, recovery, and holistic health.",
            llm=llm,
            verbose=True
        )

        manager = Agent(
            role='Fitness Program Manager',
            goal='Compile a comprehensive, well-formatted fitness and nutrition guide.',
            backstory="Expert in professional health reporting and document formatting.",
            llm=llm,
            verbose=True
        )

        # 2. Define Tasks
        workout_task = Task(
            description="Create a 7-day workout routine for a {age}yr old, {weight}, {height} for {goal} using {equipment}.",
            expected_output="A structured 7-day workout routine.",
            agent=trainer
        )

        nutrition_task = Task(
            description="Create a daily meal plan for {goal} and {diet_pref}.",
            expected_output="A detailed daily meal guide with macros.",
            agent=nutritionist,
            context=[workout_task]
        )

        tips_task = Task(
            description="Provide 5 practical health, recovery, and lifestyle tips for someone with the goal of {goal}.",
            expected_output="A list of 5 actionable health and recovery tips.",
            agent=health_advisor
        )

        summary_task = Task(
            description="""Compile all findings into a single, professional fitness document. 
            Include:
            1. Personal Info Summary.
            2. 7-Day Workout Plan (detailed exercises).
            3. Daily Meal Plan (macros and meals).
            4. Expert Health & Recovery Tips.
            Use professional Markdown formatting with headers, tables, and lists.""",
            expected_output="A complete, professional fitness program document.",
            agent=manager,
            context=[workout_task, nutrition_task, tips_task]
        )

        # 3. Assemble and Run
        crew = Crew(
            agents=[trainer, nutritionist, health_advisor, manager],
            tasks=[workout_task, nutrition_task, tips_task, summary_task],
            process=Process.sequential,
            max_rpm=1,
            verbose=True
        )

        result = crew.kickoff(inputs={
            'age': request.age,
            'weight': request.weight,
            'height': request.height,
            'goal': request.goal,
            'equipment': request.equipment,
            'diet_pref': request.diet_pref
        })
        
        return {"final_plan": str(result.raw) if hasattr(result, 'raw') else str(result)}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
