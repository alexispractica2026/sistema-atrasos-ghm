# Sistema de Atrasos e Ingresos v2 (Python + Flask + Supabase)
**Colegio García Hurtado de Mendoza**

Versión mejorada con backend en **Python (Flask)**, identificación y validación de **RUT chileno (Módulo 11)**, **catálogo de alumnos** con carga masiva desde Excel y **chips de sugerencias rápidas de motivos**.

---

## Contenido del proyecto
- `app.py`: Servidor web y API REST en Python (Flask + Gunicorn) con validación oficial de RUT chileno y conexión segura a Supabase.
- `templates/index.html`: Interfaz web con búsqueda por RUT, pestaña **🎓 Registro de Alumnos** y sugerencias rápidas de motivos.
- `requirements.txt`: Dependencias de Python para Render.
- `schema_v2.sql`: Script SQL para actualizar Supabase (crea la tabla `estudiantes` y agrega la columna `rut` a `atrasos` y `retiros` sin borrar tus datos actuales).
- `.env.example`: Ejemplo de variables de entorno.

---

## Paso 1: Actualizar la base de datos en Supabase
1. Entra a tu proyecto en **Supabase** > **SQL Editor** > **New query**.
2. Pega el contenido de `schema_v2.sql` y haz clic en **Run**.

---

## Paso 2: Subir el proyecto a GitHub
Sube todos estos archivos a tu repositorio de GitHub (`app.py`, `requirements.txt`, `schema_v2.sql`, `README.md` y la carpeta `templates/index.html`).

---

## Paso 3: Desplegar en Render como Web Service (Python)
Como ahora usamos servidor Python, en Render debes crear un **Web Service**:

1. En Render haz clic en **New +** > **Web Service** y selecciona tu repositorio.
2. Configura estos campos:
   - **Language / Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
3. Baja a la sección **Environment Variables** y agrega:
   - `SUPABASE_URL`: `https://zfunatqqrvndmlcnbgkb.supabase.co`
   - `SUPABASE_KEY`: *(tu clave anon/public de Supabase)*
   - `ADMIN_PASSWORD`: `1234` *(o la clave que elijas para eliminar registros)*
4. Haz clic en **Deploy Web Service**.
