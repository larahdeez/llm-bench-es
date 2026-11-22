# Resumen de `reports/results_60preguntas_revisadas.csv`

Generado con `python -m llm_bench.report`. No edites este fichero a mano.

Preguntas: 60 · Modelos: 3 · Repeticiones: 3 · Remuestreos bootstrap: 1000

## Acierto por modelo

| modelo | acierto | IC 95 % | preguntas | repeticiones | no interpretables |
|---|---|---|---|---|---|
| qwen3-8b | 78% | 68% - 86% | 60 | 3 | 0 |
| qwen2.5-7b | 67% | 57% - 77% | 60 | 3 | 0 |
| llama3.1-8b | 60% | 49% - 71% | 60 | 3 | 0 |

![Acierto por modelo](figures/results_60preguntas_revisadas/accuracy.png)

## Acierto por tema

| tema | llama3.1-8b | qwen2.5-7b | qwen3-8b |
|---|---|---|---|
| basesdatos | 57% | 52% | 86% |
| criptografia | 78% | 67% | 67% |
| programacion | 71% | 75% | 83% |
| redes | 53% | 68% | 74% |
| seguridad | 75% | 88% | 100% |
| sistemas | 37% | 52% | 67% |

![Acierto por tema](figures/results_60preguntas_revisadas/accuracy_by_topic.png)

## Acierto por dificultad

| dificultad | llama3.1-8b | qwen2.5-7b | qwen3-8b |
|---|---|---|---|
| facil | 98% | 100% | 100% |
| media | 61% | 70% | 87% |
| dificil | 25% | 33% | 42% |

![Acierto por dificultad](figures/results_60preguntas_revisadas/accuracy_by_difficulty.png)

## Sesgo de posición

Proporción de respuestas que van a cada letra. La fila `(correctas)` indica con qué frecuencia cada letra es la correcta.

| modelo | A | B | C | D |
|---|---|---|---|---|
| llama3.1-8b | 18% | 36% | 19% | 27% |
| qwen2.5-7b | 30% | 29% | 20% | 21% |
| qwen3-8b | 29% | 26% | 21% | 24% |
| (correctas) | 27% | 27% | 21% | 26% |

![Letra elegida](figures/results_60preguntas_revisadas/position_bias.png)

## Consistencia entre repeticiones

| modelo | misma opción en todas las repeticiones |
|---|---|
| llama3.1-8b | 63% |
| qwen2.5-7b | 63% |
| qwen3-8b | 78% |

## Preguntas más falladas

Acierto medio de todos los modelos por debajo del 50 %. Conviene revisar que la clave y el enunciado sean correctos.

| pregunta | acierto medio |
|---|---|
| basesdatos-0007 | 0% |
| criptografia-0009 | 0% |
| sistemas-0008 | 0% |
| criptografia-0006 | 11% |
| redes-0013 | 11% |
| programacion-0007 | 11% |
| programacion-0002 | 22% |
| criptografia-0007 | 22% |
| redes-0015 | 22% |
| redes-0016 | 22% |
| sistemas-0009 | 22% |
| sistemas-0006 | 22% |
| redes-0009 | 33% |
| redes-0014 | 33% |
| basesdatos-0004 | 33% |
| redes-0019 | 33% |
| redes-0018 | 33% |
| seguridad-0007 | 44% |
| sistemas-0003 | 44% |
| redes-0010 | 44% |
