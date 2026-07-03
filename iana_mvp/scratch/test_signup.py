import os
import sys
from dotenv import load_dotenv

# Añadir el directorio iana_mvp al path de python para poder importar app.db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import sign_up_user, get_supabase_client

load_dotenv()

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

# Intentar inspeccionar los últimos registros de auth.users o logs si es posible
try:
    client = get_supabase_client()
    print("\nVerificando si se insertó en auth.users...")
    # NOTA: auth.users no se puede consultar directamente por API a menos que sea a través de la DB
    # Pero podemos intentar consultar public.users
    users_res = client.table("users").select("*").execute()
    print("Usuarios en public.users:", users_res.data)
except Exception as e:
    print("Error consultando la base de datos:", e)
