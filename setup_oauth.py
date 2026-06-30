"""
Helper para configurar OAuth localmente.

1. Crea credenciales en Google Cloud Console
2. Crea OAuth App en GitHub Developer Settings
3. Copia los valores al .env
"""

GOOGLE_REDIRECT = "http://127.0.0.1:5050/auth/callback/google"
GITHUB_REDIRECT = "http://127.0.0.1:5050/auth/callback/github"

print("=" * 60)
print("CONFIGURACION DE OAuth - Google")
print("=" * 60)
print()
print("1. Ve a: https://console.cloud.google.com/apis/credentials")
print("2. Crea un proyecto nuevo o selecciona uno existente")
print("3. Haz clic en 'CREAR CREDENCIALES' > 'ID de cliente de OAuth'")
print("4. Tipo: 'Aplicación web'")
print("5. Nombre: 'PDF Tools Local'")
print("6. Orígenes autorizados: http://127.0.0.1:5050")
print(f"7. URI de redireccion: {GOOGLE_REDIRECT}")
print("8. Copia el Client ID y Client Secret al .env:")
print()
print("   GOOGLE_CLIENT_ID=tu-client-id")
print("   GOOGLE_CLIENT_SECRET=tu-client-secret")
print()

print("=" * 60)
print("CONFIGURACION DE OAuth - GitHub")
print("=" * 60)
print()
print("1. Ve a: https://github.com/settings/developers")
print("2. 'OAuth Apps' > 'New OAuth App'")
print("3. Nombre: 'PDF Tools Local'")
print("4. Homepage URL: http://127.0.0.1:5050")
print(f"5. Callback URL: {GITHUB_REDIRECT}")
print("6. Copia el Client ID y Client Secret al .env:")
print()
print("   GITHUB_CLIENT_ID=tu-client-id")
print("   GITHUB_CLIENT_SECRET=tu-client-secret")
print()

print("=" * 60)
print("ARCHIVO .env RESULTANTE")
print("=" * 60)
print()
print("GOOGLE_CLIENT_ID=xxx")
print("GOOGLE_CLIENT_SECRET=xxx")
print("GITHUB_CLIENT_ID=xxx")
print("GITHUB_CLIENT_SECRET=xxx")
print(f"OAUTH_REDIRECT_URI=http://127.0.0.1:5050")
print()
print("Luego reinicia el servidor y los botones apareceran en login/register.")
