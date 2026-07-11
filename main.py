from nicegui import ui, app
from groq import AsyncGroq
import json
import re
import os
from dotenv import load_dotenv
from auth import sign_up, sign_in

load_dotenv()
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json(raw):
    text = raw.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)


def valid_email(value):
    return None if "@" in value and "." in value else "Enter a valid email"


def min_length(n):
    return lambda value: None if len(value) >= n else f"At least {n} characters"


def not_empty(value):
    return None if value.strip() else "Required"


def is_number(value):
    return None if value.strip().isdigit() else "Enter a number"


@ui.page("/sign_up")
def sign_up_page():
    ui.label("Create Account").classes("text-2xl font-bold mt-8")
    email = ui.input("Email", validation=valid_email).props("outlined")
    password = ui.input("Password", password=True, validation=min_length(6)).props("outlined")

    def handle_sign_up():
        if valid_email(email.value) or min_length(6)(password.value):
            ui.notify("Fix the errors above", color="negative")
            return
        user_id, error = sign_up(email.value, password.value)
        if error:
            ui.notify(error, color="negative")
            return
        app.storage.user["user_id"] = user_id
        ui.navigate.to("/")

    ui.button("Sign Up", on_click=handle_sign_up)
    ui.link("Already have an account? Sign in", "/sign_in")


@ui.page("/sign_in")
def sign_in_page():
    ui.label("Sign In").classes("text-2xl font-bold mt-8")
    email = ui.input("Email").props("outlined")
    password = ui.input("Password", password=True).props("outlined")

    def handle_sign_in():
        user_id, error = sign_in(email.value, password.value)
        if error:
            ui.notify(error, color="negative")
            return
        app.storage.user["user_id"] = user_id
        ui.navigate.to("/")

    ui.button("Sign In", on_click=handle_sign_in)
    ui.link("Need an account? Sign up", "/sign_up")


@ui.page("/")
def main():
    if "user_id" not in app.storage.user:
        ui.navigate.to("/sign_in")
        return

    ui.toggle(["Light", "Dark"], value="Light",
              on_change=lambda e: ui.dark_mode().set_value(e.value == "Dark")) \
        .props("rounded elevated dense").classes("fixed top-2 left-2 z-50")

    ui.button("Log out", on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/sign_in"))) \
        .props("flat dense").classes("fixed top-2 right-2 z-50")

    with ui.column().classes("w-full max-w-sm sm:max-w-md items-center mx-auto gap-4 px-4 pt-16 pb-8"):

        ui.label("Workout Generator").classes("text-3xl font-bold text-center")

        containers = []

        def show(i):
            for index, c in enumerate(containers, start=1):
                c.visible = (index == i)

        def step(label_text, next_step, validation=not_empty, button_text="Next"):
            with ui.column().classes("w-full items-center gap-2") as col:
                field = ui.input(label_text, validation=validation).classes("w-full max-w-xs").props("outlined dense")
                action = (lambda: show(next_step)) if next_step else (lambda: generate())

                def guarded():
                    if validation(field.value or ""):
                        field.run_method("validate")
                        return
                    return action()

                field.on("keyup.enter", guarded)
                ui.button(button_text, on_click=guarded).classes("w-full max-w-xs")
            containers.append(col)
            return field

        goal = step("Goal", 2)
        time = step("Session length", 3)
        age = step("Age", 4, validation=is_number)
        height = step("Height", 5)
        weight = step("Weight", 6)
        inv = step("Days/week", 7, validation=is_number)
        equipments = step("Equipment", 8)
        lvl = step("Level", None, button_text="Generate")

        for i, c in enumerate(containers, start=1):
            c.visible = (i == 1)

        output_column = ui.column().classes("w-full items-center gap-3")

    def render_plan(data):
        output_column.clear()
        with output_column:
            for d in data.get("days", []):
                with ui.card().classes("w-full"):
                    ui.label(f"Day {d.get('day', '?')} — {d.get('focus', '')}").classes("text-lg font-bold")

                    if d.get("warmup"):
                        ui.label("Warm-up").classes("font-semibold mt-2")
                        for w in d["warmup"]:
                            ui.label(f"• {w}")

                    if d.get("workout"):
                        ui.label("Workout").classes("font-semibold mt-2")
                        for ex in d["workout"]:
                            ui.label(f"{ex.get('name', '')} — {ex.get('sets', '')} x {ex.get('reps', '')}, rest {ex.get('rest', '')}")

                    if d.get("cooldown"):
                        ui.label("Cool-down").classes("font-semibold mt-2")
                        for cd in d["cooldown"]:
                            ui.label(f"• {cd}")

    async def generate():
        output_column.clear()
        with output_column:
            ui.spinner(size="lg")
            ui.label("Generating...")

        num_days = int(inv.value)

        prompt = f"""
You are a certified strength and conditioning coach generating a workout plan.
Return ONLY valid JSON, no markdown fences, no commentary, no notes.
You MUST generate EXACTLY {num_days} entries in the "days" array, each with a
different day number and a distinct focus appropriate to the goal.

Schema:
{{
  "days": [
    {{
      "day": 1,
      "focus": "",
      "warmup": ["...", "..."],
      "workout": [{{"name": "", "sets": "", "reps": "", "rest": ""}}],
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

        from database import supabase
        supabase.table("workouts").insert({
            "user_id": app.storage.user["user_id"],
            "workout": data,
        }).execute()

        render_plan(data)


ui.run(show=False, reload=False, title="WorkoutBuddy", storage_secret=os.getenv("STORAGE_SECRET", "change-me"))