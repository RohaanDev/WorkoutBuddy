from nicegui import ui
from groq import AsyncGroq
import json
import re
import os
from dotenv import load_dotenv
load_dotenv()
client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY")
)


def dark():
    ui.dark_mode().enable()


def light():
    ui.dark_mode().disable()


def change(e):
    if e.value == "Dark":
        dark()
    elif e.value == "Light":
        light()


def extract_json(raw: str) -> dict:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)


ui.query("body").classes("flex justify-center")
ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">')

ui.toggle(["Light", "Dark"], value="Light", on_change=change) \
    .props("rounded elevated dense").classes("fixed top-2 left-2 z-50")

with ui.column().classes("w-full max-w-sm sm:max-w-md items-center mx-auto gap-4 px-4 pt-16 pb-8"):

    ui.label("Workout Generator").classes("text-3xl sm:text-4xl font-bold text-center")

    containers = []

    def show(i):
        for index, c in enumerate(containers, start=1):
            c.visible = (index == i)

    def step(label_text, next_step, button_text="Next"):
        with ui.column().classes("w-full items-center gap-2") as col:
            field = ui.input(label_text).classes("w-full max-w-xs text-center").props("outlined dense")
            if next_step is not None:
                action = lambda: show(next_step)
            else:
                action = lambda: generate()
            field.on("keyup.enter", action)
            ui.button(button_text, on_click=action).classes("w-full max-w-xs")
        containers.append(col)
        return field

    goal = step("Goal", 2)
    time = step("Session length", 3)
    age = step("Age", 4)
    height = step("Height", 5)
    weight = step("Weight", 6)
    inv = step("Days/week", 7)
    equipments = step("Equipment", 8)
    lvl = step("Level", None, button_text="Generate")

    for i, c in enumerate(containers, start=1):
        c.visible = (i == 1)

    output_column = ui.column().classes("w-full items-center gap-3")


def render_plan(data: dict):
    output_column.clear()
    days = data.get("days", [])
    with output_column:
        for d in days:
            with ui.card().classes("w-full"):
                ui.label(f"Day {d.get('day', '?')} — {d.get('focus', '')}").classes("text-lg sm:text-xl font-bold")

                if d.get("warmup"):
                    ui.label("Warm-up").classes("font-semibold mt-2")
                    for w in d["warmup"]:
                        ui.label(f"• {w}").classes("text-sm sm:text-base")

                if d.get("workout"):
                    ui.label("Workout").classes("font-semibold mt-2")
                    for ex in d["workout"]:
                        ui.label(
                            f"{ex.get('name', '')} — {ex.get('sets', '')} sets x {ex.get('reps', '')} reps (rest {ex.get('rest', '')})"
                        ).classes("text-sm sm:text-base")

                if d.get("cooldown"):
                    ui.label("Cool-down").classes("font-semibold mt-2")
                    for cd in d["cooldown"]:
                        ui.label(f"• {cd}").classes("text-sm sm:text-base")


async def generate():
    output_column.clear()
    with output_column:
        ui.spinner(size="lg")
        ui.label("Generating...")

    try:
        num_days = int(inv.value)
    except (ValueError, TypeError):
        num_days = 3

    prompt = f"""
You are a certified strength and conditioning coach generating a workout plan.

Return ONLY valid JSON, no markdown fences, no commentary, no notes.

You MUST generate EXACTLY {num_days} entries in the "days" array — one per training day.
Each entry must have a different "day" number (1 to {num_days}) and a distinct
"focus" (e.g. Push, Pull, Legs, Full Body, Upper, Lower — vary it sensibly
for the goal and number of days). Do not repeat the same single day.

Schema (top level object):
{{
  "days": [
    {{
      "day": 1,
      "focus": "",
      "warmup": ["...", "..."],
      "workout": [
        {{"name": "", "sets": "", "reps": "", "rest": ""}}
      ],
      "cooldown": ["...", "..."]
    }}
  ]
}}

User data:
Goal: {goal.value}
Session length: {time.value}
Age: {age.value}
Height: {height.value}
Weight: {weight.value}
Days per week: {num_days}
Equipment: {equipments.value}
Experience level: {lvl.value}

Make exercise selection appropriate to the equipment and level given.
Do not add any notes, explanations, or text outside the JSON object.
"""

    res = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
        max_tokens=4000,
    )
    raw = res.choices[0].message.content

    try:
        data = extract_json(raw)
    except Exception as e:
        output_column.clear()
        with output_column:
            ui.label(f"JSON ERROR: {e}").classes("text-red-500")
            ui.label(raw).classes("whitespace-pre-wrap text-xs")
        return

    render_plan(data)


ui.run(show=False, reload=False, title="WorkoutBuddy")