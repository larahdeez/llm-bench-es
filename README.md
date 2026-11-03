# llm-bench-es

Benchmark reproducible para comparar modelos de lenguaje abiertos en preguntas técnicas en español, con foco en ciberseguridad e ingeniería informática. Incluye un estudio del efecto de la cuantización en calidad y eficiencia.

> **Estado:** en desarrollo. Los resultados se añadirán cuando termine la fase de evaluación.

## Pregunta de investigación

1. ¿Qué modelo abierto de tamaño mediano responde mejor preguntas técnicas en español?
2. ¿Cuánta precisión se pierde al cuantizar (4, 8 y 16 bits) y compensa el ahorro de memoria?

## Metodología (resumen)

- **Conjunto de evaluación:** preguntas propias en cuatro tipos (opción múltiple, respuesta corta, extracción y razonamiento en varios pasos). Ver [`docs/annotation_guide.md`](docs/annotation_guide.md) y [`data/README.md`](data/README.md).
- **Modelos:** familias abiertas de tamaño comparable. Las versiones exactas se fijan en `configs/default.yaml`.
- **Protocolo:** temperatura 0, mismo prompt, mismo contexto máximo y mismo formato de salida para todos los modelos.
- **Métricas de calidad:** precisión (opción múltiple), *exact match* y F1 (respuesta corta).
- **Métricas de eficiencia:** tokens por segundo, latencia del primer token, memoria de vídeo y tamaño en disco.
- **Estadística:** repetición con varias semillas o prompts parafraseados e intervalos de confianza por *bootstrap*.

## Resultados

_Pendiente. Aquí irán las tablas principales, las gráficas y el enlace al informe completo en `reports/`._

## Limitaciones

_Pendiente. Se documentarán el tamaño del conjunto, el sesgo de las preguntas, los posibles solapamientos con datos de entrenamiento y las limitaciones del hardware usado._

## Reproducir los experimentos

```bash
# 1. Crear el entorno
uv sync

# 2. Descargar los modelos indicados en configs/default.yaml (vía Ollama o Hugging Face)

# 3. Ejecutar la evaluación
uv run python -m llm_bench.run --config configs/default.yaml

# 4. Generar tablas y gráficas
uv run python -m llm_bench.report --results reports/results.csv
```

Los pesos de los modelos no se incluyen en el repositorio. Cada uno se descarga desde su fuente oficial.

## Estructura

```
llm-bench-es/
├── configs/          # configuración de modelos y experimentos
├── data/             # conjunto de preguntas y su esquema
├── docs/             # guía de anotación y decisiones de diseño
├── reports/          # resultados, tablas y gráficas
├── src/llm_bench/    # arnés de evaluación y análisis
├── tests/            # pruebas del esquema y del arnés
├── pyproject.toml
└── README.md
```

## Licencia

Código bajo licencia MIT. El conjunto de preguntas tiene su propia licencia, indicada en `data/README.md`.
