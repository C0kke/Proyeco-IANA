import os
import sys
from dotenv import load_dotenv

# Añadir el directorio iana_mvp al path de python para poder importar app.db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import sign_up_user, get_supabase_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL", "")
is_safe = "localhost" in supabase_url or "gqptiihuvbdygwlouthq" in supabase_url
if not is_safe and os.getenv("FORCE_TEST") != "1":
    print(f"ERROR DE SEGURIDAD: Se detectó una URL de Supabase externa/producción: {supabase_url}")
    print("Para ejecutar en este entorno, define la variable de entorno FORCE_TEST=1.")
    sys.exit(1)

# Test variables
email = "test_user_unique@example.com"
password = "testpassword123"
name = "Test User"
phone = "+56911111111"
rut = "11.111.111-1"
role = "independent_developer"

print("Intentando registrar usuario de prueba...")
res = sign_up_user(email, password, name, phone, rut, role)
print("Resultado:", res)

# Intentar inspeccionar si el usuario específico fue guardado en public.users
try:
    client = get_supabase_client()
    print("\nVerificando si se insertó el usuario de prueba...")
    users_res = client.table("users").select("id", "email", "role", "created_at").eq("email", email).execute()
    print("Usuario en public.users:", users_res.data)
except Exception as e:
    print("Error consultando la base de datos:", e)