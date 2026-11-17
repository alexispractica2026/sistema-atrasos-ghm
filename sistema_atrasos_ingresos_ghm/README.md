# Sistema de Atrasos e Ingresos — Colegio García Hurtado de Mendoza

Proyecto listo para desplegar en **Render (Static Site)** conectado a **Supabase (PostgreSQL)**.

---

## Contenido del paquete
- `index.html`: Aplicación web completa con todas las mejoras (conexión a Supabase, reloj sincronizado, normalización de nombres sin tildes, autocompletado de alumnos, filtros por fecha/curso/nombre, exportación a Excel CSV e impresión de pases).
- `schema.sql`: Script SQL para crear las tablas `atrasos` y `retiros` en Supabase.
- `README.md`: Esta guía de instalación y despliegue.

---

## Paso 1: Configurar la base de datos en Supabase
1. Entra a [supabase.com](https://supabase.com) y crea un nuevo proyecto (por ejemplo: `asistencia-ghm`).
2. En el menú lateral izquierdo, ve a **SQL Editor** > **New query**.
3. Copia todo el contenido del archivo `schema.sql`, pégalo y presiona **Run**.
4. Ve a **Project Settings** (ícono de engranaje abajo a la izquierda) > **API** y copia:
   - **Project URL**
   - **anon public** key

*(Opcional)*: Si quieres que la app ya venga conectada sin tener que ingresar las claves en el navegador, abre `index.html` y pégalas en las líneas 244-245:
```javascript
const SUPABASE_URL_DEFAULT = "https://tu-proyecto.supabase.co";
const SUPABASE_ANON_KEY_DEFAULT = "tu-anon-key-aqui";
```

---

## Paso 2: Subir el proyecto a GitHub
1. Crea un repositorio nuevo en GitHub (por ejemplo `sistema-atrasos-ghm`).
2. Sube los archivos `index.html`, `schema.sql` y `README.md` a la rama `main`.

---

## Paso 3: Desplegar en Render (Gratis)
Como es una aplicación web estática (HTML + JS + Tailwind CDN), en Render debes publicarla como **Static Site** (es gratuito, ultra rápido y no se "duerme" como los Web Services gratuitos):

1. Entra a [dashboard.render.com](https://dashboard.render.com).
2. Haz clic en **New +** > **Static Site**.
3. Conecta tu repositorio de GitHub `sistema-atrasos-ghm`.
4. Configura los siguientes campos:
   - **Name:** `asistencia-ghm` (tu URL será `https://asistencia-ghm.onrender.com`)
   - **Branch:** `main`
   - **Build Command:** *(déjalo vacío)*
   - **Publish Directory:** `.` *(un punto, indicando la raíz del repositorio)*
5. Haz clic en **Create Static Site**.

---

## Paso 4: Primer uso en Inspectoría
1. Abre la URL entregada por Render.
2. Si no dejaste las claves fijas en el código, haz clic en el botón superior **⚙️ Configurar BD**, pega tu **Project URL** y tu **Anon Public Key** de Supabase y guarda.
3. ¡Listo! Todos los equipos de inspectoría o portería que ingresen esas credenciales verán los registros sincronizados en tiempo real.
