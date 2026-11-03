# Conjunto de evaluación

Este directorio contiene las preguntas del benchmark. Cada pregunta es una línea de `questions.jsonl` que cumple el esquema definido en `schema.json`.

## Campos

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único, por ejemplo `sec-0001`. |
| `task_type` | string | `multiple_choice`, `short_answer`, `extraction` o `reasoning`. |
| `topic` | string | Tema, por ejemplo `redes`, `criptografia`, `sistemas`, `programacion`. |
| `difficulty` | string | `facil`, `media` o `dificil`, según la guía de anotación. |
| `question` | string | Enunciado en español. |
| `choices` | lista | Solo para `multiple_choice`. Mínimo 4 opciones. |
| `answer` | string | Respuesta de referencia. Para opción múltiple, la letra correcta. |
| `answer_aliases` | lista | Formas aceptadas de la respuesta para `short_answer` (sinónimos, variantes). |
| `source` | string | Origen de la pregunta: `propia` o la referencia de un material con licencia abierta. |
| `annotator` | string | Quién la redactó y quién la revisó. |

## Reglas de construcción

- Las preguntas se redactan a partir de material propio o de fuentes con licencia que permita reutilizarlo. No se incluyen fragmentos de libros, diapositivas ni enunciados protegidos.
- Cada pregunta la revisa una segunda persona antes de entrar en el conjunto final.
- Se comprueba que ninguna pregunta esté duplicada ni casi duplicada.
- Se registra si el tema es muy común en la web, porque aumenta el riesgo de contaminación.

## Licencia

_Pendiente de decidir. Recomendación: CC BY 4.0 si todas las preguntas son propias._
