# Arquitectura de DownloadYTLocalWeb

Guía visual de cómo está construida la app, pensada para quien empieza. Si un término en **negrita** no te suena, búscalo en el [glosario](../GLOSSARY.md).

> **Estado:** diseño acordado, implementación en curso. Cada sección indica qué tickets la hacen realidad. Este documento se actualiza junto con el código.

---

## 1. Vista general: las piezas

La app se divide en piezas con una responsabilidad cada una. Cada pieza solo habla con la de al lado.

```mermaid
flowchart LR
    U(["Tú"]) --> N["Navegador"]
    N -->|"pide la web"| V["Frontend Vue<br/>lo que ves y pulsas"]
    V -->|"peticiones HTTP /api"| A["API HTTP<br/>FastAPI"]
    A --> G["Gestor de Descargas<br/>estados, cola, limpieza"]
    A --> AN["Análisis<br/>interpreta el enlace y decide las Opciones de calidad"]
    AN --> F["Fuente de vídeo<br/>único punto que habla con YouTube"]
    G -->|"obtener archivo"| F
    F --> Y[("YouTube")]
    F --> FF["ffmpeg<br/>convierte y une"]
    G --> T[("Carpeta temporal")]
```

| Pieza | Qué hace | Qué NO hace |
|---|---|---|
| **Frontend Vue** | Muestra el formulario, las Opciones de calidad y la lista de Descargas. Pregunta a la API cada segundo cómo van. | No sabe nada de YouTube ni de ffmpeg. |
| **API HTTP** | Recibe las peticiones del navegador y las traduce en llamadas a las otras piezas. Es una capa fina. | No contiene lógica de negocio. |
| **Análisis** | Interpreta el enlace pegado, pide los datos del Vídeo a la Fuente de vídeo y decide qué Opciones de calidad ofrecer (y cuál va preseleccionada). | No habla con YouTube directamente. |
| **Gestor de Descargas** | El cerebro: crea Descargas, controla sus estados, limita a 3 en paralelo, cancela, reintenta y borra temporales. | No sabe cómo se baja un vídeo; se lo pide a la Fuente de vídeo. |
| **Fuente de vídeo** | Envuelve yt-dlp y ffmpeg. Consulta los datos de un Vídeo y obtiene el archivo final. | No sabe qué es una Descarga, ni sus estados, ni qué Opciones de calidad se ofrecen. |

**¿Por qué el Análisis no está dentro de la Fuente de vídeo?** Porque interpretar el enlace y decidir las Opciones de calidad son reglas de *esta* app, no de YouTube. Así, en los tests (que sustituyen la Fuente de vídeo por una falsa) esas reglas siguen probándose.

**¿Por qué separar así?** Porque YouTube cambia a menudo y yt-dlp se rompe. Si todo lo que toca YouTube vive en una sola pieza (la Fuente de vídeo), los arreglos quedan ahí y el resto no se entera. Además, en los tests se cambia la Fuente de vídeo por una **falsa** que no usa internet, y así se prueba todo lo demás en milisegundos (ver sección 6).

---

## 2. Recorrido completo: de pegar un enlace a tener el archivo

Un diagrama de secuencia se lee de arriba abajo: cada flecha es un mensaje entre piezas, en orden temporal.

```mermaid
sequenceDiagram
    actor U as Tú
    participant V as Frontend Vue
    participant A as API HTTP
    participant AN as Análisis
    participant G as Gestor de Descargas
    participant F as Fuente de vídeo
    participant Y as YouTube

    Note over U,Y: Paso 1 · Análisis (no descarga nada)
    U->>V: Pega el enlace
    V->>A: POST /api/analysis
    A->>AN: analizar enlace
    AN->>F: datos del Vídeo
    F->>Y: ¿qué es este vídeo?
    Y-->>F: título, miniatura, duración, formatos
    F-->>AN: datos del Vídeo
    alt Enlace y Vídeo válidos
        AN-->>A: Vídeo + Opciones de calidad
        A-->>V: 200 datos + Opciones de calidad
        V-->>U: Muestra el Vídeo y las Opciones
    else Enlace o Vídeo rechazado
        AN-->>A: error con código
        A-->>V: 422 o 502 con el código
        V-->>U: Mensaje explicando el motivo
    end

    Note over U,Y: Paso 2 · Descarga (en segundo plano)
    U->>V: Elige una Opción de calidad
    V->>A: POST /api/downloads
    A->>G: crear Descarga
    G->>AN: volver a analizar el Vídeo
    AN-->>G: título + Opciones (¿existe la elegida?)
    G-->>A: Descarga Pendiente (id 7)
    A-->>V: 201 Descarga creada
    G->>F: obtener archivo (en un hilo aparte)
    F->>Y: baja solo el audio
    F-->>G: progreso (Descargando 40 %…, Convirtiendo)

    loop Polling cada ~1 segundo, mientras alguna Descarga no haya terminado
        V->>A: GET /api/downloads
        A-->>V: lista con estado y % de cada Descarga
    end

    F-->>G: archivo MP3 listo (con carátula y etiquetas)
    Note over G: la Descarga pasa a Lista

    Note over U,Y: Paso 3 · Entrega
    V->>A: GET /api/downloads/7/file
    Note over G: el archivo queda reservado: otra petición recibiría 410
    A-->>V: el archivo
    V-->>U: Se guarda en tu carpeta de descargas
    Note over G: al terminar el envío, el temporal se borra
```

**Rechazos del Análisis.** Cada motivo tiene un código que la web traduce a un mensaje en español:

| Código | Quién lo detecta | Cuándo |
|---|---|---|
| `unsupported_link` | Análisis | El enlace no es de un Vídeo de YouTube. |
| `playlist_not_supported` | Análisis | El enlace es de una Lista de reproducción sin Vídeo concreto. |
| `live_not_supported` | Fuente de vídeo | Directo en curso o estreno que aún no ha empezado. |
| `video_unavailable` | Fuente de vídeo | Privado, eliminado, con restricción de edad, bloqueado en tu país… |
| `source_failed` (HTTP 502) | Fuente de vídeo | Falla YouTube o yt-dlp, no el Vídeo: sin conexión o yt-dlp desactualizado. |

Los cuatro primeros responden 422 (el problema es lo que se pidió); `source_failed` responde 502 (el problema está en un servicio del que dependemos).

**Errores de Descarga.** Siguen el mismo formato `{"code": …}`:

| Código | HTTP | Cuándo |
|---|---|---|
| `unknown_quality_option` | 422 | La Opción de calidad elegida no existe para ese Vídeo. |
| `download_not_found` | 404 | No hay ninguna Descarga con ese número (p. ej. tras reiniciar la app). |
| `download_not_ready` | 409 | Se pide el archivo de una Descarga que aún no está Lista. |
| `file_already_collected` | 410 | El archivo ya se entregó (y se borró del servidor). |
| `download_not_cancellable` | 409 | Se intenta cancelar una Descarga que ya terminó (Lista, Fallida o Cancelada). |

**Varios hilos a la vez.** Cada Descarga se ejecuta en un hilo aparte mientras otros hilos atienden las peticiones del navegador. Para que no se pisen, cada Descarga solo cambia a través de sus propios métodos, protegidos con un *lock* (un candado que solo un hilo puede tener a la vez), y hacia fuera se entregan copias coherentes. Por eso, por ejemplo, si llegan dos peticiones del archivo a la vez, solo la primera lo recibe.

**Idea clave:** la petición del paso 2 responde **al instante** ("Descarga creada"), aunque la Descarga tarde minutos. El trabajo real sigue en segundo plano y el navegador pregunta periódicamente cómo va (**polling**). Ver [ADR 0001](adr/0001-descarga-como-trabajo-en-memoria-con-polling.md) para el porqué.

---

## 3. Los estados de una Descarga

Una **máquina de estados** describe en qué situaciones puede estar algo y qué caminos hay entre ellas. Una Descarga solo avanza: nunca vuelve atrás.

```mermaid
stateDiagram-v2
    [*] --> Pendiente: se crea
    Pendiente --> Descargando: hay hueco (máx. 3)
    Descargando --> Convirtiendo: contenido bajado
    Convirtiendo --> Lista: archivo final preparado
    Lista --> [*]

    Descargando --> Fallida: error
    Convirtiendo --> Fallida: error
    Fallida --> [*]

    Pendiente --> Cancelada: botón Cancelar
    Descargando --> Cancelada: botón Cancelar
    Convirtiendo --> Cancelada: botón Cancelar
    Cancelada --> [*]
```

- **Lista, Fallida y Cancelada** son estados **terminales**: ya no cambian.
- **Reintentar** no "resucita" una Descarga Fallida o Cancelada: crea una **Descarga nueva** con el mismo Vídeo y la misma Opción de calidad. Así cada Descarga tiene una historia simple y lineal.
- Cuando una Descarga deja de trabajar (llega a Lista o Fallida, o aborta tras cancelarla), libera su hueco y la Pendiente más antigua arranca.
- **Cancelar** (`POST /api/downloads/{id}/cancel`) la deja Cancelada al momento:
  - si estaba **Pendiente**, cuando le toque el turno el hilo se la salta sin descargar nada;
  - si estaba **en curso**, la Fuente de vídeo pregunta "¿me han cancelado?" (`is_cancelled()`) antes de empezar y en cada aviso de progreso de yt-dlp, y aborta;
  - **la conversión de ffmpeg no se puede cortar a medias**: si se cancela mientras convierte, la Descarga aparece Cancelada al momento, pero su hilo termina ese paso, descarta el resultado y solo entonces libera el hueco. Convertir una canción tarda unos segundos (y unir un MP4 es casi instantáneo, porque no recomprime); solo en sesiones de horas se nota la espera;
  - en todos los casos se borran los archivos parciales.
- Por dentro, el Gestor de Descargas tiene un grupo fijo de 3 hilos trabajadores con una cola por orden de llegada. En cuanto un hilo coge una Descarga, esta pasa a Descargando, aunque todavía no se sepa el porcentaje: Pendiente significa solo "esperando turno".

---

## 4. Dos formas de arrancar la app: desarrollo y uso

Vue hay que **compilarlo** (convertirlo en HTML, JS y CSS que el navegador entiende). Por eso hay dos modos.

```mermaid
flowchart TB
    subgraph DEV["Modo desarrollo · en tu PC, sin Docker"]
        direction LR
        N1["Navegador<br/>localhost:5173"] --> VITE["Vite<br/>sirve Vue y recarga al guardar"]
        VITE -->|"reenvía /api"| API1["FastAPI<br/>puerto 8000"]
    end

    subgraph USO["Modo uso · docker compose up"]
        direction LR
        N2["Navegador<br/>localhost:8000"] --> API2["FastAPI<br/>sirve la web compilada<br/>y también la API"]
    end
```

| | Desarrollo | Uso |
|---|---|---|
| Programas en marcha | 2 (Vite + FastAPI) | 1 (FastAPI dentro de Docker) |
| Necesitas instalado | Python, Node, ffmpeg | Solo Docker |
| Cambios en el código | Se ven al instante | Hay que reconstruir la imagen |
| Accesible desde | Tu PC | Solo tu PC (`127.0.0.1`) |

Ver [ADR 0002](adr/0002-docker-para-uso-desarrollo-nativo.md).

### Cómo se construye la imagen Docker

```mermaid
flowchart LR
    subgraph E1["Etapa 1 · imagen con Node"]
        SRC["Código Vue"] -->|"npm run build"| DIST["Web compilada"]
    end
    subgraph E2["Etapa 2 · imagen final con Python"]
        PY["Python + FastAPI + yt-dlp"]
        FFM["ffmpeg"]
        DIST2["Web compilada"]
    end
    DIST -->|"se copia"| DIST2
```

La imagen final no lleva Node: solo hacía falta para compilar. Así es más pequeña.

---

## 5. Versiones fijadas (y la excepción de yt-dlp)

Todas las versiones (Python, librerías, Vue…) están **fijadas** a un número exacto, para que la app funcione igual en cualquier PC. yt-dlp también, pero como YouTube cambia a menudo, hay un comando documentado para actualizarlo en un paso cuando deje de funcionar. Ver [ADR 0003](adr/0003-yt-dlp-fijado-con-actualizacion-en-un-paso.md).

---

## 6. Cómo se prueba

Los tests entran por **un único punto** (el *seam*): la API HTTP, exactamente igual que el navegador. La única pieza que se sustituye es la Fuente de vídeo.

```mermaid
flowchart LR
    subgraph REAL["En la app real"]
        A1["API HTTP"] --> G1["Gestor de Descargas"] --> F1["Fuente de vídeo real<br/>yt-dlp + YouTube"]
    end
    subgraph TEST["En los tests"]
        T["Test"] -->|"peticiones HTTP"| A2["API HTTP"] --> G2["Gestor de Descargas"] --> F2["Fuente de vídeo falsa<br/>la controla el test"]
        T -.->|"adelanta"| R["Reloj falso"]
        R -.-> G2
    end
```

- La **Fuente falsa** puede responder al momento, quedarse "atascada" hasta que el test la libere, o fallar a propósito. Así se prueban la cola, la cancelación o los errores sin internet.
- El **reloj falso** permite probar "se borra tras 1 hora" sin esperar una hora.
- Los tests solo miran lo que se ve desde fuera (respuestas de la API, archivos que existen o no), nunca el interior del código. Así, si se reorganiza el código por dentro, los tests siguen sirviendo.

---

## 7. Mapa de la documentación

```mermaid
flowchart TB
    R["README.md<br/>cómo arrancar y desarrollar"]
    AR["docs/arquitectura.md<br/>este documento: cómo encaja todo"]
    GL["GLOSSARY.md<br/>qué significa cada palabra"]
    ADR["docs/adr/<br/>por qué se decidió cada cosa importante"]
    SPEC["Issue #1 en GitHub<br/>la spec: qué debe hacer la app"]
    TK["Issues #2 a #10<br/>los tickets: en qué orden se construye"]
    AG["CLAUDE.md y docs/agents/<br/>configuración para el agente"]

    SPEC --> TK
    AR --> GL
    AR --> ADR
    R --> AR
```

| Si te preguntas… | Mira |
|---|---|
| ¿Qué significa "Análisis" o "Descarga"? | [GLOSSARY.md](../GLOSSARY.md) |
| ¿Por qué no hay base de datos? ¿Por qué Docker? | [docs/adr/](adr/) |
| ¿Qué tiene que hacer exactamente la app? | [Issue #1](https://github.com/Kokon4/DonwloadYTLocalWeb/issues/1) |
| ¿Qué falta por construir? | [Issues abiertos](https://github.com/Kokon4/DonwloadYTLocalWeb/issues) |
| ¿Cómo encaja todo? | Este documento |

---

## Avance por tickets

| Sección | Tickets |
|---|---|
| 1 · Piezas: Frontend, API, Análisis, Fuente de vídeo | #2 (esqueleto) ✅, #3 (rechazos) ✅ |
| 2 · Recorrido completo y Gestor de Descargas | #4 (primera Descarga MP3) ✅, #5 (MP4) ✅ |
| 3 · Estados: cola, cancelar, reintentar | #6 ✅, #7 ✅, #8 |
| 3 · Limpieza y caducidad | #9 |
| 4 · Docker y modo uso | #10 |
