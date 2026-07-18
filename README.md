# WorkoutBuddy

A small web app that generates a personalized workout plan using an LLM. Built with NiceGUI on the frontend and Groq for generation, with Supabase handling auth and storage.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat)
![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-1976D2?style=flat)
![Groq](https://img.shields.io/badge/LLM-Groq-F55036?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

## About

WorkoutBuddy asks the user a short series of questions (goal, session length, age, height, weight, days per week, equipment, experience level) and then sends that information to an LLM, which returns a structured multi day workout plan. The plan gets rendered as cards on the page and saved to the user's account.

The interesting part isn't really the UI. It's the prompt and JSON handling. The app forces the model to return valid JSON matching a fixed schema, then parses and displays it, with a fallback that shows the raw model output if parsing fails.

## Features

- Sign up and sign in with email and password
- A short multi step form that walks the user through their profile and goals
- Light and dark mode toggle
- Workout plans generated through Groq's llama-3.3-70b-versatile model
- Plans are saved per user in Supabase so they aren't lost on refresh
- Basic input validation on each step (required fields, numeric fields, minimum password length)
- Graceful handling of malformed JSON coming back from the model

## Tech stack

| Piece | Role |
|---|---|
| NiceGUI | Frontend and page routing |
| Groq (AsyncGroq client) | Generates the workout plan |
| Supabase | Auth and storage for saved workouts |
| python-dotenv | Loads environment variables from a .env file |

## Requirements

- Python 3.10 or newer
- A Groq API key
- A Supabase project (for the `auth` and `database` modules this app imports)

## Environment variables

Create a `.env` file in the project root with the following:

```
GROQ_API_KEY=your_groq_api_key
STORAGE_SECRET=some_random_secret_string
```

`STORAGE_SECRET` is used by NiceGUI to sign the browser storage session, so it should be a random string you keep private, not the placeholder value.

## Installation

Clone the repository and move into it:

```bash
git clone https://github.com/your-username/workoutbuddy.git
cd workoutbuddy
```

Install dependencies:

```bash
pip install nicegui groq python-dotenv supabase
```

Add your `.env` file as described above, then run the app:

```bash
python main.py
```

By default it starts without automatically opening a browser window (`show=False`). Open the address it prints in your terminal to view it.

## How it works

1. The user signs up or signs in. Successful auth stores a `user_id` in `app.storage.user`.
2. The main page is gated behind that `user_id`. If it's missing, the user gets redirected to the sign in page.
3. The user answers each question one at a time. Each step validates its input before letting you continue.
4. On the last step, the app builds a prompt containing the user's answers and a strict JSON schema, then sends it to Groq.
5. The response is parsed with a helper that strips markdown code fences if the model added them, since models don't always follow "no markdown" instructions perfectly.
6. If parsing succeeds, the plan is rendered as a set of day cards, each with a warm up, the main workout, and a cool down. If parsing fails, the raw response is shown so you can see what went wrong.
7. The plan is saved to a `workouts` table in Supabase, tied to the current user.

## Project structure

```
.
├── main.py          # NiceGUI pages, form flow, and generation logic (this file)
├── auth.py          # sign_up and sign_in functions
├── database.py       # Supabase client setup
└── .env              # API keys and secrets (not committed)
```

## Known limitations

- There's no email verification or password reset flow, just basic sign up and sign in.
- The multi step form doesn't let you go back a step once you move forward.
- If the model returns a plan with more or fewer days than requested, there's no check catching that before it gets saved.
- Validation is minimal. Height and weight fields accept any non empty text, not just numbers.

## Roadmap

- Add a way to go back and edit earlier answers before generating
- Let users view and revisit past saved plans
- Add stricter validation on numeric fields like height and weight
- Handle the case where the model returns the wrong number of days

## License

Licensed under the MIT License.
