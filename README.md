# Sistema de Gestión de Indicadores Académicos (SGIA) - Colegio San Agustín

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Una aplicación web robusta construida con Django para centralizar, gestionar y visualizar los Indicadores Clave de Rendimiento del Colegio San Agustín.

![Dashboard Principal del SGIA](https://i.ibb.co/b5FWfbBM/fig-main-dashboard.png)

---

### Tabla de Contenidos

1.  [Acerca del Proyecto](#acerca-del-proyecto)
2.  [Construido Con](#construido-con)
3.  [Empezando](#empezando)
    * [Prerrequisitos](#prerrequisitos)
    * [Instalación Local](#instalación-local)
4.  [Configuración](#configuración)
5.  [Uso](#uso)
6.  [Despliegue](#despliegue)
7.  [Hoja de Ruta](#hoja-de-ruta)
8.  [Contacto](#contacto)

---

## Acerca del Proyecto

El Sistema de Gestión de Indicadores Académicos (SGIA) fue desarrollado para modernizar y optimizar el seguimiento de los indicadores del Colegio San Agustín. La plataforma reemplaza los flujos de trabajo manuales basados en hojas de cálculo por una solución web centralizada, segura e interactiva.

**Funcionalidades Clave:**
* **Gestión Segura de Usuarios:** Sistema de registro por invitación y autenticación.
* **Dashboard de Indicadores:** Visualización centralizada y filtrado dinámico de todos los indicadores.
* **Administración Detallada:** Formularios para la gestión completa de cada indicador y sus metadatos.
* **Introducción de Datos Automatizada:** Módulo de carga de archivos (Excel) con un flujo de previsualización y confirmación para garantizar la integridad de los datos.
* **Visualización de Datos:** Dashboards nativos e interactivos (construidos con Chart.js) para el análisis de datos específicos, como los Reportes Académicos de Alerta Temprana (Indicador N° 6).
* **Trazabilidad:** Historial de cambios para cada indicador.

## Construido Con

Esta sección lista las principales tecnologías y librerías utilizadas en el proyecto.

* **Backend:**
    * ![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white)
    * ![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white)
    * ![Django REST Framework](https://img.shields.io/badge/DRF-3.14+-A30000?style=flat-square&logo=django)
* **Frontend:**
    * ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
    * ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
    * ![HTMX](https://img.shields.io/badge/HTMX-3498DB?style=flat-square)
    * ![Alpine.js](https://img.shields.io/badge/Alpine.js-8BC0D0?style=flat-square&logo=alpine.js&logoColor=black)
    * ![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chart.js&logoColor=white)
* **Base de Datos:**
    * ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
    * ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white) (para desarrollo local)
* **Procesamiento de Datos:**
    * ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
* **Despliegue:**
    * ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

## Empezando

Siga estos pasos para configurar una copia del proyecto en su máquina local para desarrollo y pruebas.

### Prerrequisitos

Asegúrese de tener instalado Python 3.11 o superior y Git.

* **Python:**
    ```sh
    python --version
    ```
* **Git:**
    ```sh
    git --version
    ```

### Instalación Local

1.  **Clone el repositorio**
    ```sh
    git clone https://github.com/gustavomarinovando/isa
    cd isa
    ```
2.  **Cree y active un entorno virtual**
    ```sh
    # Windows
    python -m venv myenv
    myenv\Scripts\activate

    # macOS / Linux
    python3 -m venv myenv
    source myenv/bin/activate
    ```
3.  **Instale las dependencias**
    ```sh
    pip install -r requirements.txt
    ```

## Configuración

La configuración del proyecto se gestiona mediante variables de entorno.

1.  **Cree un archivo `.env`**
    En la raíz del proyecto (junto a `manage.py`), cree un archivo llamado `.env`. Puede copiar el archivo de ejemplo:
    ```sh
    # En macOS/Linux:
    cp .env.example .env

    # En Windows:
    copy .env.example .env
    ```
2.  **Edite el archivo `.env`**
    Abra el archivo `.env` y configure las siguientes variables:

    ```ini
    # .env
    
    # Clave secreta de Django. Genere una nueva para producción.
    # Puede usar [https://djecrety.ir/](https://djecrety.ir/)
    SECRET_KEY='su-clave-secreta-larga-y-aleatoria-aqui'
    
    # Ponga esto en False para producción
    DEBUG=True

    # Configurado para uso local y despligue en Vercel 
    ALLOWED_HOSTS=127.0.0.1,.vercel.app

    # Database 
    DB_ENGINE=django.db.backends.mysql
    DB_PORT=3306
    DB_HOST=Direccion_de_su_base_de_datos
    DB_NAME=Nombre_de_su_base_de_datos
    DB_USER=*******
    DB_PASSWORD=*******
    ```

## Uso

Una vez que el proyecto está configurado, siga estos pasos para ejecutarlo:

1.  **Aplique las migraciones de la base de datos**
    Este comando crea todas las tablas necesarias en la base de datos.
    ```sh
    python manage.py migrate
    ```

2.  **Cree un superusuario**
    Este comando le permitirá acceder al Panel de Administración de Django en `/admin/`.
    ```sh
    python manage.py createsuperuser
    ```
    Siga las instrucciones para establecer un nombre de usuario, correo y contraseña.

3.  **Inicie el servidor de desarrollo**
    ```sh
    python manage.py runserver
    ```
    La aplicación estará disponible en `http://127.0.0.1:8000/`.

4.  **Genere un código de invitación (Opcional, para crear nuevos usuarios)**
    * Vaya al panel de admin (`/admin/`).
    * En la sección `INDICATOR_MANAGER`, vaya a `Invitaciones de Registro` y cree una nueva invitación para un correo electrónico específico.
    * Use ese código y correo para registrar una nueva cuenta en la página `/signup/`.

## Despliegue

La aplicación está configurada para un despliegue sencillo en **Vercel**. Para una guía detallada paso a paso, consulte la **Documentación Técnica y Guía de Despliegue** completa del proyecto.

Los puntos clave para el despliegue son:
* Conectar su repositorio de Git a Vercel.
* Configurar las variables de entorno en el panel de Vercel (especialmente `SECRET_KEY`, `DEBUG=False`, y las variables relacionadas a la base de datos `DB_VARS` de producción).
* Vercel utilizará los archivos `vercel.json` y `build.sh` del repositorio para construir y desplegar la aplicación automáticamente.

## Hoja de Ruta

El proyecto tiene un gran potencial de crecimiento. Las próximas fases planificadas incluyen:

* **Módulo de Seguimiento de Presentaciones:** Para registrar cuándo se presenta cada indicador.
* **Dashboards Nativos Configurables:** Permitir a los usuarios crear sus propias visualizaciones básicas.
* **Notificaciones Proactivas:** Alertar a los usuarios sobre fechas de revisión importantes.

Consulte la "Propuesta de Continuidad y Expansión" para una hoja de ruta más detallada.

## Contacto

Gustavo Marin Ovando - gustavomarinovando@gmail.com

Enlace del Proyecto: [SGIA](https://github.com/gustavomarinovando/isa)
