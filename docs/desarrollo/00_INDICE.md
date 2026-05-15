# SINIA-UY — Guía de Desarrollo y Deploy

Esta carpeta contiene la documentación operativa del proyecto: cómo está construido, cómo trabajarlo en tu máquina, cómo versionarlo con Git y cómo subirlo al servidor de UTEC. Es **complementaria** a `docs/` (que contiene la defensa académica, arquitectura formal e informes EC1/EC2).

## Índice

| Doc | Propósito | Cuándo leerlo |
|-----|-----------|---------------|
| [10_EXPLICACION_PROYECTO_PASO_A_PASO.md](10_EXPLICACION_PROYECTO_PASO_A_PASO.md) | Qué hace el proyecto, capa por capa, en lenguaje claro | Primero, para entender el todo |
| [11_SETUP_LOCAL.md](11_SETUP_LOCAL.md) | Levantar Postgres + Mongo + ETL + dashboard en tu PC | Antes de tocar código |
| [12_WORKFLOW_GIT.md](12_WORKFLOW_GIT.md) | Inicializar repo, ramas, commits, push a GitHub | Apenas tengas el setup local |
| [13_DEPLOY_SERVIDOR_UTEC.md](13_DEPLOY_SERVIDOR_UTEC.md) | Cómo subir el sistema al servidor de UTEC | Cuando local funcione end-to-end |
| [14_PLAN_DOCUMENTACION_PARALELA.md](14_PLAN_DOCUMENTACION_PARALELA.md) | Estructura y plantillas para escribir la doc de desarrollo | En paralelo a todo lo demás |
| [15_CHECKLIST_DIARIO.md](15_CHECKLIST_DIARIO.md) | Checklist rápido para cada sesión de trabajo | Cada vez que abras el proyecto |

## Flujo recomendado las primeras semanas

```
Día 1  → Leer 10 + 11. Levantar Postgres y Mongo localmente. Ver el dashboard.
Día 2  → Leer 12. git init, primer commit, push a GitHub.
Día 3  → Leer 14. Crear plantillas vacías de la doc de desarrollo.
Día 4+ → Leer 13. Cuando el local esté estable, deploy a UTEC.
         Trabajar local → commit → push → pull en servidor.
Diario → Usar 15 como checklist.
```

## Convención de carpetas

```
docs/
├── (académico — NO TOCAR aquí desarrollo)
│   ├── DEFENSA.md
│   ├── ARQUITECTURA.md
│   ├── FUENTES_Y_DATOS.md
│   ├── INFORME_EC1.md
│   ├── PROYECTO_FINAL_EC1_EC2.md
│   └── figures/
│
└── desarrollo/        ← ESTA GUÍA
    ├── 00_INDICE.md
    ├── 10_EXPLICACION_PROYECTO_PASO_A_PASO.md
    ├── 11_SETUP_LOCAL.md
    ├── 12_WORKFLOW_GIT.md
    ├── 13_DEPLOY_SERVIDOR_UTEC.md
    ├── 14_PLAN_DOCUMENTACION_PARALELA.md
    └── 15_CHECKLIST_DIARIO.md
```

## Información que necesitas tener a mano

Antes de empezar el deploy reúne estos datos del servidor UTEC. Si no los tienes todavía, pídeselos al docente o al área de infraestructura:

- [ ] IP o hostname del servidor UTEC
- [ ] Usuario SSH y forma de autenticación (clave o password)
- [ ] Sistema operativo (probablemente Ubuntu Server)
- [ ] ¿Tiene Docker instalado? ¿O hay que instalar Postgres y Mongo nativos?
- [ ] Puertos abiertos hacia el exterior (5432, 27017, 8501 normalmente bloqueados desde fuera)
- [ ] Si hay un dominio o subdominio asignado para el dashboard
- [ ] Política de backups: ¿guardamos en el servidor o externos?

Esto está más detallado en `13_DEPLOY_SERVIDOR_UTEC.md`.
