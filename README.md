# PDF Merger — Herramientas PDF en línea

Suite web para manipular PDFs: fusionar, comprimir, recortar, reordenar, eliminar páginas y convertir TIFF a PDF. Incluye autenticación de usuarios, panel de administración y recolección de datos para investigación.

## Características

- **Fusionar PDFs** — Insertar archivos PDF en una posición específica
- **Fusionar múltiples PDFs** — Subir varios archivos y combinarlos
- **Comprimir PDFs** — Reducir tamaño con compresión JPEG configurable
- **Recortar PDFs** — Eliminar márgenes de páginas
- **Reordenar páginas** — Cambiar el orden de las páginas
- **Eliminar páginas** — Quitar páginas específicas
- **Convertir TIFF a PDF** — Procesamiento 100% en el navegador (sin subir archivos al servidor)
- **Autenticación** — Registro, login y OAuth con Google
- **Panel admin** — Dashboard de métricas, exportación de datos, gestión de consentimiento

## Requisitos previos

- Python 3.10+
- pip
- PostgreSQL (producción) o SQLite (desarrollo)
- Docker y Docker Compose (opcional, para producción)

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta para Flask (genera una aleatoria) | `py -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | URL de conexión a PostgreSQL (usa SQLite si no se define) | `postgresql://user:pass@localhost:5432/pdfmerger` |
| `FLASK_ENV` | Entorno de ejecución | `development` o `production` |
| `SESSION_LIFETIME_DAYS` | Duración de sesiones en días | `30` |
| `MAX_CONTENT_LENGTH` | Tamaño máximo de subida en bytes (default: 500MB) | `524288000` |
| `GOOGLE_CLIENT_ID` | Client ID de Google OAuth | Ver [Configurar Google OAuth](#configurar-google-oauth) |
| `GOOGLE_CLIENT_SECRET` | Client Secret de Google OAuth | Ver [Configurar Google OAuth](#configurar-google-oauth) |
| `OAUTH_REDIRECT_URI` | URI de redirección para OAuth | `http://127.0.0.1:5050` (local) o tu dominio en producción |

## Desarrollo local (sin Docker)

```bash
# 1. Clonar el repositorio
git clone https://github.com/GermanUNAP/pdf-mrger-.tiff-manager-.git
cd pdf-mrger-.tiff-manager-

# 2. Crear entorno virtual
py -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
# Editar .env con tus valores

# 5. Ejecutar
py -m gunicorn "app:create_app()" --bind 127.0.0.1:5050 --reload
```

La app estará disponible en http://127.0.0.1:5050. Si no defines `DATABASE_URL`, usa SQLite automáticamente (`data.db`).

## Docker Compose (producción)

```bash
# 1. Configurar variables de entorno
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
# Editar .env (especialmente SECRET_KEY y POSTGRES_PASSWORD)

# 2. Levantar servicios
docker compose up -d --build

# 3. Verificar
docker compose logs app
```

Esto levanta tres servicios:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `nginx` | 80, 443 | Reverse proxy con SSL |
| `app` | interno | Flask + Gunicorn (4 workers) |
| `postgres` | interno | PostgreSQL 17 |

Para detener: `docker compose down`

Para ver logs: `docker compose logs -f app`

## Deploy en Render

El proyecto ya está desplegado en Render con Docker runtime:

**URL:** https://pdf-mrger-tiff-manager-1.onrender.com

Para desplegar tu propia instancia:

1. Crear un repositorio en GitHub con el código
2. En [Render](https://render.com), crear un nuevo **Web Service**
3. Conectar el repositorio de GitHub
4. Configurar:
   - **Runtime:** Docker
   - **Dockerfile:** `./Dockerfile`
   - ** Puerto:** 10000 (default)
5. Agregar variables de entorno en el panel de Render:
   - `SECRET_KEY` (generar una clave aleatoria)
   - `DATABASE_URL` (usar PostgreSQL de Render o externa)
   - `OAUTH_REDIRECT_URI` (tu dominio de Render)
   - `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`
6. Deploy automático al hacer push a `main`

### Nota sobre Render y archivos grandes

Render tiene un límite de ~10MB en el body de las requests (plan gratuito). Para TIFF, esto no es problema porque la conversión es 100% client-side. Para operaciones de merge/compress, los archivos se procesan en el servidor.

## Configurar Google OAuth

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un proyecto (o seleccionar uno existente)
3. Habilitar **Google+ API** y **People API**
4. Ir a **APIs & Services > Credentials**
5. Crear **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Authorized redirect URIs: agregar tu URI de callback
     - Local: `http://127.0.0.1:5050/auth/callback/google`
     - Producción: `https://tu-dominio.com/auth/callback/google`
6. Copiar el **Client ID** y **Client Secret** a tu `.env`:

```
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
```

7. Configurar `OAUTH_REDIRECT_URI` en `.env`:
   - Local: `http://127.0.0.1:5050`
   - Producción: `https://tu-dominio.com`

**Importante:** Los URIs de callback en Google Cloud Console deben coincidir exactamente con `OAUTH_REDIRECT_URI + /auth/callback/google`.

## Estructura del proyecto

```
pdf-merger/
├── app/
│   ├── __init__.py      # create_app() factory
│   ├── admin.py         # Panel de administración
│   ├── auth.py          # Autenticación y OAuth
│   ├── config.py        # Configuración desde variables de entorno
│   ├── extensions.py    # Inicialización de extensiones
│   ├── metrics.py       # Logging, hashing, middleware de métricas
│   ├── models.py        # Modelos SQLAlchemy (User, UsageLog)
│   ├── routes.py        # Rutas principales de la app
│   └── services.py      # Lógica de negocio (merge, compress, etc.)
├── static/
│   └── style.css        # Estilos CSS
├── templates/
│   ├── base.html        # Template base con sidebar
│   ├── index.html       # Página principal
│   ├── compress.html    # Compresión de PDFs
│   ├── convert.html     # Conversión TIFF a PDF (client-side)
│   ├── crop.html        # Recorte de PDFs
│   ├── find.html        # Búsqueda de texto en PDF
│   ├── merge-multi.html # Fusión de múltiples PDFs
│   ├── remove-pages.html # Eliminación de páginas
│   ├── reorder.html     # Reordenamiento de páginas
│   ├── login.html       # Inicio de sesión
│   ├── register.html    # Registro de usuarios
│   └── admin/           # Panel de administración
│       ├── dashboard.html
│       ├── consent.html
│       └── export.html
├── Dockerfile           # imagen Docker (Python 3.14 slim)
├── docker-compose.yml   # Postgres + App + Nginx
├── entrypoint.sh        # Script de inicio para Docker
├── nginx.conf           # Configuración de Nginx
├── requirements.txt     # Dependencias Python
├── Procfile             # Para deploy en Render/Heroku
└── .env.example         # Plantilla de variables de entorno
```

## Rutas / Endpoints

### Rutas principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Página principal |
| GET | `/find` | Buscar texto en PDF |
| POST | `/merge` | Fusionar PDF (insertar páginas) |
| GET | `/merge-multiple` | Interfaz de fusión múltiple |
| POST | `/merge-multi` | Fusionar múltiples PDFs |
| POST | `/page-count` | Contar páginas de un PDF |
| GET | `/convert` | Conversión TIFF a PDF |
| GET | `/crop` | Interfaz de recorte |
| POST | `/crop-pdf` | Ejecutar recorte |
| GET | `/remove-pages` | Interfaz de eliminación |
| POST | `/remove-pages-pdf` | Eliminar páginas |
| GET | `/reorder` | Interfaz de reordenamiento |
| POST | `/reorder-pdf` | Ejecutar reordenamiento |
| GET | `/compress` | Interfaz de compresión |
| POST | `/compress-pdfs` | Comprimir PDFs (devuelve ZIP) |

### Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/auth/register` | Registro de usuarios |
| GET/POST | `/auth/login` | Inicio de sesión |
| GET | `/auth/logout` | Cerrar sesión |
| GET | `/auth/login/google` | Login con Google |
| GET | `/auth/callback/google` | Callback de Google OAuth |

### Administración

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/` | Dashboard de métricas |
| GET | `/admin/export` | Exportar datos de uso |
| GET/POST | `/admin/consent` | Gestión de consentimiento |
| GET | `/admin/research/stats` | Estadísticas de investigación |
| GET | `/admin/research/export` | Exportar datos de investigación |

## Licencia

Proyecto abierto. Ver repositorio para más detalles.
