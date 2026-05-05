# Diseño del Sistema - Ejecutor de Lotes

## 1. Descripción General

El sistema simula un ejecutor de procesos por lotes, similar a los encontrados en sistemas operativos de mainframe. Está compuesto por cinco procesos independientes que se comunican entre sí mediante tuberías nombradas (FIFOs).

### Componentes

| Componente | Función |
|------------|---------|
| **cliente** | Interfaz de usuario. Envía peticiones al sistema (no se implementa en la primera entrega). |
| **ctrllt** | Control de Lotes. Pasarela que recibe peticiones y las redirige al servicio adecuado. |
| **gesfich** | Gestor de Ficheros. CRUD sobre ficheros almacenados en `aralmac`. |
| **gesprog** | Gestor de Programas. CRUD sobre programas registrados en `aralmac`. |
| **ejecutor** | Ejecutor de procesos de lotes a partir de programas y ficheros registrados. |
| **aralmac** | Área de almacenamiento (directorio en disco). |

### Diagrama de Arquitectura

```
                         ┌──────────┐
                         │  cliente  │
                         └────┬─────┘
                    FIFO c/a  │
                         ┌────▼─────┐
                         │  ctrllt   │
                         └──┬──┬──┬─┘
                FIFO f/b    │  │  │   FIFO e/d
               ┌────────────┘  │  └────────────┐
               ▼               │               ▼
         ┌──────────┐   FIFO p/q         ┌──────────┐
         │ gesfich   │         │         │ ejecutor  │
         └─────┬────┘         ▼         └─────┬────┘
               │        ┌──────────┐          │
               │        │ gesprog   │          │
               │        └─────┬────┘          │
               │              │               │
               ▼              ▼               ▼
         ┌─────────────────────────────────────────┐
         │              aralmac (directorio)        │
         │  ficheros/   programas/                  │
         └─────────────────────────────────────────┘
```

## 2. Comunicación - Tuberías Nombradas

### Tipo de comunicación

En Linux, las tuberías nombradas (FIFOs) son **half-duplex**, por lo tanto cada enlace entre dos procesos requiere **dos FIFOs**: una para enviar y otra para recibir.

### Convención de nombres

Cada FIFO tiene un nombre único siguiendo esta convención:

| Enlace | FIFO de peticiones (envío) | FIFO de respuestas (recepción) |
|--------|---------------------------|-------------------------------|
| cliente ↔ ctrllt | `/tmp/fifo_ctrllt_req` | `/tmp/fifo_ctrllt_res` |
| ctrllt ↔ gesfich | `/tmp/fifo_gesfich_req` | `/tmp/fifo_gesfich_res` |
| ctrllt ↔ gesprog | `/tmp/fifo_gesprog_req` | `/tmp/fifo_gesprog_res` |
| ctrllt ↔ ejecutor | `/tmp/fifo_ejecutor_req` | `/tmp/fifo_ejecutor_res` |

### Creación de FIFOs

Cada servicio crea sus FIFOs al iniciar si no existen:

```bash
mkfifo /tmp/fifo_gesfich_req 2>/dev/null
mkfifo /tmp/fifo_gesfich_res 2>/dev/null
```

## 3. Protocolo de Mensajes (JSON)

Todos los mensajes entre componentes usan formato JSON, separados por salto de línea (`\n`) como delimitador.

### Formato de petición

```json
{
  "id": "req-0001",
  "servicio": "gesfich",
  "operacion": "crear",
  "parametros": {}
}
```

### Formato de respuesta

```json
{
  "id": "req-0001",
  "estado": "ok",
  "datos": {},
  "mensaje": "Fichero creado exitosamente"
}
```

### Formato de respuesta de error

```json
{
  "id": "req-0001",
  "estado": "error",
  "datos": null,
  "mensaje": "El fichero f-0001 no existe"
}
```

## 4. Especificación de Servicios

---

### 4.1 gesfich - Gestor de Ficheros

#### Sinopsis

```bash
gesfich -f <fifo-peticiones> [-b <fifo-respuestas>] -x <ruta-aralmac>
```

#### Máquina de estados

```
              ┌──────────────────────────────────┐
              ▼                                  │
  [Inicio] → [Corriendo] ──Suspender──→ [Suspendido]
                  │                          │
                  │──Terminar──→ [Terminado] ◄┘
                                 Terminar
```

- **Corriendo**: acepta todas las operaciones (Crear, Leer, Actualizar, Borrar, Suspender, Terminar).
- **Suspendido**: solo acepta Reasumir y Terminar.
- **Terminado**: el proceso finaliza.

#### Operaciones

**Crear** — Crea un fichero vacío en `aralmac/ficheros/`.

Petición:
```json
{
  "id": "req-0001",
  "servicio": "gesfich",
  "operacion": "crear",
  "parametros": {}
}
```

Respuesta:
```json
{
  "id": "req-0001",
  "estado": "ok",
  "datos": { "id_fichero": "f-0001" },
  "mensaje": "Fichero creado"
}
```

**Leer (con id)** — Retorna el contenido de un fichero específico.

Petición:
```json
{
  "id": "req-0002",
  "servicio": "gesfich",
  "operacion": "leer",
  "parametros": { "id_fichero": "f-0001" }
}
```

Respuesta:
```json
{
  "id": "req-0002",
  "estado": "ok",
  "datos": { "id_fichero": "f-0001", "contenido": "datos del fichero..." },
  "mensaje": ""
}
```

**Leer (sin id)** — Lista todos los ficheros registrados.

Petición:
```json
{
  "id": "req-0003",
  "servicio": "gesfich",
  "operacion": "leer",
  "parametros": {}
}
```

Respuesta:
```json
{
  "id": "req-0003",
  "estado": "ok",
  "datos": {
    "ficheros": [
      { "id_fichero": "f-0001", "tamaño": 0 },
      { "id_fichero": "f-0002", "tamaño": 1024 }
    ]
  },
  "mensaje": ""
}
```

**Actualizar** — Copia el contenido de un archivo externo al fichero registrado.

Petición:
```json
{
  "id": "req-0004",
  "servicio": "gesfich",
  "operacion": "actualizar",
  "parametros": { "id_fichero": "f-0001", "ruta": "/home/user/datos.txt" }
}
```

**Borrar** — Elimina un fichero del aralmac.

Petición:
```json
{
  "id": "req-0005",
  "servicio": "gesfich",
  "operacion": "borrar",
  "parametros": { "id_fichero": "f-0001" }
}
```

**Suspender / Reasumir / Terminar** — Control de estado del servicio.

```json
{
  "id": "req-0006",
  "servicio": "gesfich",
  "operacion": "suspender",
  "parametros": {}
}
```

---

### 4.2 gesprog - Gestor de Programas

#### Sinopsis

```bash
gesprog -p <fifo-peticiones> [-c <fifo-respuestas>] -x <ruta-aralmac>
```

#### Máquina de estados

```
              ┌──────────────────────────────────┐
              ▼                                  │
  [Inicio] → [Corriendo] ──Suspender──→ [Suspendido]
                  │                          │
                  │──Terminar──→ [Terminado] ◄┘
                                 Terminar

Nota: En estado Suspendido, solo acepta Leer, Reasumir y Terminar.
```

#### Operaciones

**Guardar** — Registra un programa con su ejecutable, argumentos y variables de ambiente.

Petición:
```json
{
  "id": "req-0010",
  "servicio": "gesprog",
  "operacion": "guardar",
  "parametros": {
    "ejecutable": "/usr/bin/sort",
    "argumentos": ["-n", "-r"],
    "ambiente": {
      "LANG": "es_CO.UTF-8",
      "LC_ALL": "C"
    }
  }
}
```

Respuesta:
```json
{
  "id": "req-0010",
  "estado": "ok",
  "datos": { "id_programa": "p-0001" },
  "mensaje": "Programa registrado"
}
```

**Leer (con id)** — Retorna la información de un programa registrado.

Petición:
```json
{
  "id": "req-0011",
  "servicio": "gesprog",
  "operacion": "leer",
  "parametros": { "id_programa": "p-0001" }
}
```

Respuesta:
```json
{
  "id": "req-0011",
  "estado": "ok",
  "datos": {
    "id_programa": "p-0001",
    "ejecutable": "/usr/bin/sort",
    "argumentos": ["-n", "-r"],
    "ambiente": { "LANG": "es_CO.UTF-8" }
  },
  "mensaje": ""
}
```

**Leer (sin id)** — Lista todos los programas registrados.

**Actualizar** — Actualiza la información de un programa existente.

Petición:
```json
{
  "id": "req-0012",
  "servicio": "gesprog",
  "operacion": "actualizar",
  "parametros": {
    "id_programa": "p-0001",
    "ejecutable": "/usr/bin/sort",
    "argumentos": ["-n"],
    "ambiente": {}
  }
}
```

**Borrar** — Elimina un programa del registro.

```json
{
  "id": "req-0013",
  "servicio": "gesprog",
  "operacion": "borrar",
  "parametros": { "id_programa": "p-0001" }
}
```

**Suspender / Reasumir / Terminar** — Igual que gesfich.

---

### 4.3 ejecutor - Ejecutor de Lotes

#### Sinopsis

```bash
ejecutor -e <fifo-peticiones> [-d <fifo-respuestas>] -x <ruta-aralmac>
```

#### Máquina de estados

```
  [Inicio] → [Ejecutar] ──Suspender──→ [Suspendidos]
                  │                          │
                  │ Parar (si procesos=0)    Reasumir
                  ▼                          │
              [Parar] ◄─────────────────────┘
                  │
                  │ Terminar
                  ▼
              [Terminar]
```

- **Ejecutar**: acepta Ejecutar, Estado, Matar, Suspender.
- **Suspendidos**: los procesos en ejecución se pausan (SIGSTOP). Acepta Reasumir.
- **Parar**: solo si no hay procesos activos (`procesos == 0`). Acepta Terminar.

#### Operaciones

**Ejecutar** — Crea un proceso de lotes a partir de un programa y ficheros registrados.

Petición:
```json
{
  "id": "req-0020",
  "servicio": "ejecutor",
  "operacion": "ejecutar",
  "parametros": {
    "id_programa": "p-0001",
    "id_fichero_entrada": "f-0001",
    "id_fichero_salida": "f-0002"
  }
}
```

Respuesta:
```json
{
  "id": "req-0020",
  "estado": "ok",
  "datos": { "id_lote": "j-0001", "pid": 12345 },
  "mensaje": "Proceso de lotes iniciado"
}
```

Implementación interna:
1. Verificar que `id_programa` exista en `aralmac/programas/`.
2. Verificar que los ficheros de entrada/salida existan en `aralmac/ficheros/`.
3. `fork()` → proceso hijo:
   - Redirigir `stdin` al fichero de entrada.
   - Redirigir `stdout` al fichero de salida.
   - Configurar variables de ambiente del programa.
   - `exec()` el ejecutable con sus argumentos.
4. Proceso padre: registrar PID y asignar `id_lote`.

**Estado (con id)** — Retorna estado de un proceso de lotes.

```json
{
  "id": "req-0021",
  "servicio": "ejecutor",
  "operacion": "estado",
  "parametros": { "id_lote": "j-0001" }
}
```

Respuesta:
```json
{
  "id": "req-0021",
  "estado": "ok",
  "datos": {
    "id_lote": "j-0001",
    "pid": 12345,
    "estado_proceso": "corriendo"
  },
  "mensaje": ""
}
```

Los estados posibles del proceso son: `corriendo`, `suspendido`, `terminado`, `error`.

**Estado (sin id)** — Lista todos los procesos de lotes.

**Matar** — Termina un proceso de lotes.

```json
{
  "id": "req-0022",
  "servicio": "ejecutor",
  "operacion": "matar",
  "parametros": { "id_lote": "j-0001" }
}
```

Implementación: `kill(pid, SIGTERM)`.

**Suspender / Reasumir / Parar / Terminar** — Control del estado del servicio ejecutor.

- Suspender: envía `SIGSTOP` a todos los procesos activos.
- Reasumir: envía `SIGCONT` a todos los procesos suspendidos.
- Parar: solo si `procesos_activos == 0`.

---

### 4.4 ctrllt - Control de Lotes

#### Sinopsis

```bash
ctrllt -c <fifo-cliente-req> [-a <fifo-cliente-res>] \
       -f <fifo-gesfich-req> [-b <fifo-gesfich-res>] \
       -p <fifo-gesprog-req> [-q <fifo-gesprog-res>] \
       -e <fifo-ejecutor-req> [-d <fifo-ejecutor-res>]
```

#### Máquina de estados

```
  [Inicio] → [Corriendo] ──Terminar──→ [Terminado]
```

#### Lógica principal

`ctrllt` actúa como pasarela (gateway/router):

```
loop:
    1. Leer petición JSON del FIFO del cliente
    2. Extraer campo "servicio"
    3. Según servicio:
       - "gesfich"  → reenviar a FIFO de gesfich
       - "gesprog"  → reenviar a FIFO de gesprog
       - "ejecutor" → reenviar a FIFO de ejecutor
    4. Esperar respuesta del servicio correspondiente
    5. Reenviar respuesta al FIFO del cliente
```

#### Manejo de múltiples clientes

Para soportar múltiples clientes simultáneos, ctrllt puede:
- Usar el campo `id` de la petición para hacer matching de respuestas.
- Opcionalmente, crear un hilo/proceso por cliente conectado.

---

## 5. Estructura de Almacenamiento (aralmac)

```
aralmac/
├── ficheros/
│   ├── f-0001        ← contenido del fichero
│   ├── f-0002
│   └── ...
├── programas/
│   ├── p-0001.json   ← metadata (ejecutable, args, env)
│   ├── p-0001        ← copia del ejecutable (opcional)
│   └── ...
└── estado/
    ├── fichero_counter.txt   ← último ID asignado
    ├── programa_counter.txt
    └── lote_counter.txt
```

### Formato de metadata de programa (`p-XXXX.json`)

```json
{
  "id_programa": "p-0001",
  "ejecutable": "/usr/bin/sort",
  "argumentos": ["-n", "-r"],
  "ambiente": {
    "LANG": "es_CO.UTF-8"
  }
}
```

## 6. Ejemplo de Ejecución Completa

### Paso 1: Iniciar todos los servicios

```bash
# Terminal 1 - Iniciar gesfich
./gesfich -f /tmp/fifo_gesfich_req -b /tmp/fifo_gesfich_res -x ./aralmac

# Terminal 2 - Iniciar gesprog
./gesprog -p /tmp/fifo_gesprog_req -c /tmp/fifo_gesprog_res -x ./aralmac

# Terminal 3 - Iniciar ejecutor
./ejecutor -e /tmp/fifo_ejecutor_req -d /tmp/fifo_ejecutor_res -x ./aralmac

# Terminal 4 - Iniciar ctrllt
./ctrllt -c /tmp/fifo_ctrllt_req -a /tmp/fifo_ctrllt_res \
         -f /tmp/fifo_gesfich_req -b /tmp/fifo_gesfich_res \
         -p /tmp/fifo_gesprog_req -q /tmp/fifo_gesprog_res \
         -e /tmp/fifo_ejecutor_req -d /tmp/fifo_ejecutor_res
```

### Paso 2: Enviar peticiones (cliente de prueba)

```bash
# Crear un fichero de entrada
echo '{"id":"r1","servicio":"gesfich","operacion":"crear","parametros":{}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res
# → {"id":"r1","estado":"ok","datos":{"id_fichero":"f-0001"},...}

# Actualizar el fichero con datos
echo '{"id":"r2","servicio":"gesfich","operacion":"actualizar","parametros":{"id_fichero":"f-0001","ruta":"/home/user/input.txt"}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res

# Crear fichero de salida
echo '{"id":"r3","servicio":"gesfich","operacion":"crear","parametros":{}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res
# → f-0002

# Registrar un programa
echo '{"id":"r4","servicio":"gesprog","operacion":"guardar","parametros":{"ejecutable":"/usr/bin/sort","argumentos":["-n"],"ambiente":{}}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res
# → p-0001

# Ejecutar proceso de lotes
echo '{"id":"r5","servicio":"ejecutor","operacion":"ejecutar","parametros":{"id_programa":"p-0001","id_fichero_entrada":"f-0001","id_fichero_salida":"f-0002"}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res
# → j-0001

# Consultar estado
echo '{"id":"r6","servicio":"ejecutor","operacion":"estado","parametros":{"id_lote":"j-0001"}}' \
  > /tmp/fifo_ctrllt_req
cat /tmp/fifo_ctrllt_res
```

## 7. Decisiones de Diseño

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| Lenguaje | Python 3 / C | Python para rapidez de desarrollo; C para mayor control de procesos. |
| Tipo de FIFO | Half-duplex (Linux) | Se usan dos FIFOs por enlace. |
| Formato de mensajes | JSON + `\n` como delimitador | Legibilidad y facilidad de parsing. |
| Generación de IDs | Contador persistente en archivo | Simple y garantiza unicidad. |
| Almacenamiento | Directorio en disco (`aralmac/`) | Cumple requisito sin dependencias externas. |
| Concurrencia en ctrllt | Un hilo por petición (o secuencial) | Secuencial es más simple para la primera entrega. |

## 8. Limitaciones (Primera Entrega)

- El cliente no está implementado (se usa un script de prueba manual).
- ctrllt procesa peticiones de forma secuencial (un cliente a la vez).
- No hay persistencia de estado entre reinicios del sistema.
- El manejo de errores es básico (camino feliz prioritario).

## 9. Cómo Compilar y Ejecutar

### Requisitos

- Linux (o WSL en Windows)
- Python 3.8+ (si se usa Python) o GCC (si se usa C)
- Permisos para crear FIFOs en `/tmp/`

### Ejecución

```bash
# 1. Crear directorio de almacenamiento
mkdir -p aralmac/ficheros aralmac/programas aralmac/estado

# 2. Iniciar servicios (cada uno en una terminal diferente)
# Ver sección 6 para comandos específicos

# 3. Ejecutar pruebas
./tests/test_client.sh
```

### Limpieza

```bash
rm -f /tmp/fifo_ctrllt_* /tmp/fifo_gesfich_* /tmp/fifo_gesprog_* /tmp/fifo_ejecutor_*
rm -rf aralmac/
```
