# Guía de anotación

Esta guía define cómo redactar y revisar las preguntas del benchmark. El objetivo es que dos personas distintas, con el mismo material, produzcan preguntas comparables.

## Principios

1. **Una respuesta correcta y verificable.** Si dos expertos pueden discrepar, la pregunta no sirve.
2. **Sin ambigüedad en el enunciado.** Define los términos que puedan interpretarse de varias formas.
3. **Independiente del contexto.** La pregunta debe entenderse sin haber leído ningún otro material.
4. **Escrita en español neutro.** Evita regionalismos y anglicismos innecesarios, salvo los términos técnicos habituales.

## Tipos de tarea

### Opción múltiple (`multiple_choice`)
- Cuatro opciones como mínimo, una correcta.
- Los distractores deben ser plausibles: errores típicos o confusiones conceptuales, no opciones absurdas.
- La posición de la respuesta correcta se distribuye al azar.
- Evita opciones del tipo "todas las anteriores" o "ninguna de las anteriores".

### Respuesta corta (`short_answer`)
- La respuesta cabe en una o dos frases y admite pocas formas correctas.
- Registra en `answer_aliases` las variantes aceptadas (sinónimos, siglas y forma completa).

### Extracción (`extraction`)
- Se da un texto corto y se pide un dato concreto que aparece en él.
- Sirve para medir si el modelo lee bien, no si sabe el tema.

### Razonamiento (`reasoning`)
- Requiere al menos dos pasos: por ejemplo, calcular un tiempo de respuesta o deducir una configuración de red.
- La respuesta final debe ser un valor o una opción unívoca, para que la evaluación sea automática.

## Dificultad

- **Fácil:** conocimiento básico del tema, lo estudia cualquier alumno del grado en el primer curso de la asignatura.
- **Media:** requiere haber entendido el concepto y aplicarlo a un caso.
- **Difícil:** exige combinar conceptos o razonar en varios pasos.

## Proceso de revisión

1. El autor redacta la pregunta y completa todos los campos.
2. Un revisor la responde sin ver la respuesta de referencia.
3. Si la respuesta del revisor no coincide, se discute y se corrige el enunciado o la referencia.
4. Solo entran al conjunto final las preguntas aprobadas por ambos.

Se anota en `annotator` la persona que redactó y la que revisó.

## Errores frecuentes

- Preguntas cuya respuesta depende de la versión de un producto o de una norma que cambia.
- Enunciados que mencionan la respuesta de forma implícita.
- Distractores que son correctos en otro contexto.
- Temas demasiado populares, con mucho contenido en la web, sin una variante menos conocida.
