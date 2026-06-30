import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()
port = int(os.environ.get('PORT', 0))

if not os.environ.get('GOOGLE_CLIENT_ID') and not os.environ.get('GITHUB_CLIENT_ID'):
    print()
    print("!" * 50)
    print("!  OAuth no configurado")
    print("!  Para activar login con Google/GitHub:")
    print(f"!    py setup_oauth.py")
    print("!" * 50)
    print()

app.run(host='0.0.0.0', port=port, debug=False)
