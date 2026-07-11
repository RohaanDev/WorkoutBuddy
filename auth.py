import bcrypt
from database import supabase


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def sign_up(email, password):
    existing = supabase.table("users").select("id").eq("email", email).execute()
    if existing.data:
        return None, "That email is already registered"

    hashed = hash_password(password)
    result = supabase.table("users").insert({"email": email, "password": hashed}).execute()
    return result.data[0]["id"], None


def sign_in(email, password):
    result = supabase.table("users").select("id, password").eq("email", email).execute()
    if not result.data:
        return None, "No account found for that email"

    user = result.data[0]
    if not check_password(password, user["password"]):
        return None, "Incorrect password"

    return user["id"], None