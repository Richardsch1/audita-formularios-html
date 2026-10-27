# Audita Formularios HTML

Revisión estática y local de problemas básicos en formularios HTML, con Python estándar. No ejecuta scripts, abre un navegador ni hace conexiones de red. Versión inicial 0.1.0; no se afirma adopción o validación con usuarios reales.

## Ejecutar

Python 3.11, 3.12 o 3.13. No necesita instalar dependencias.

```sh
git clone https://github.com/Richardsch1/audita-formularios-html.git
cd audita-formularios-html
python -m audita_formularios examples/correcto.html
python -m audita_formularios examples/con-problemas.html --json
python -m unittest discover -s tests -v
```

Solo recibe archivos HTML locales en UTF-8, de hasta un MiB, cinco mil elementos y cien niveles de profundidad. No modifica archivos. La salida informa códigos, severidad, elemento y línea, sin copiar etiquetas, valores, identificadores o texto del documento. El archivo sigue siendo privado y debe custodiarse por separado.

## Comprobaciones

- Nombres básicos de controles: etiqueta explícita o implícita, `aria-label`, referencias de `aria-labelledby`, texto de botones y alternativas de imagen.
- Etiquetas sin destino, identificadores duplicados y referencias ARIA no resueltas.
- Controles que dependen solo de `title`, grupos sin leyenda y radios relacionados sin agrupación nombrada.
- Controles con `aria-hidden` que podrían seguir recibiendo foco.
- Idioma del documento no declarado y atributos repetidos.

`placeholder` y `value` de un campo de texto no cuentan como etiqueta. Inputs hidden y controles dentro de `hidden` o `inert` no se revisan. Las referencias a texto oculto pueden aportar un nombre mediante `aria-labelledby`.

Códigos de salida: **0** sin errores en estas comprobaciones; **1** si encuentra errores; **2** para problemas de entrada o análisis. `--fail-on warning` también devuelve 1 ante advertencias. Un cero **no significa que la página sea accesible**.

## Biblioteca

```python
from audita_formularios import audit_html
report = audit_html('<html lang="es"><label>Zona <input></label></html>')
print(report['issues'])
```

## Alcance y fuentes

Las reglas se inspiran en las guías oficiales de W3C WAI sobre [etiquetas de controles](https://www.w3.org/WAI/tutorials/forms/labels/) y [agrupación](https://www.w3.org/WAI/tutorials/forms/grouping/), consultadas el 27 de octubre de 2026. La interpretación del código y sus severidades son propias de esta herramienta; no constituyen una herramienta certificada ni implementan una auditoría normativa completa.

Usa `html.parser`, que no reproduce todas las reparaciones de HTML que hace un navegador. La resolución de nombres es parcial; no implementa íntegramente Accessible Name and Description Computation. No calcula CSS, visibilidad efectiva, contraste, orden de foco, estados dinámicos, mensajes de error o experiencia con lector de pantalla. Una referencia o etiqueta existente puede tener un texto inadecuado que la herramienta no reconoce. Puede haber falsos positivos y negativos.

**No certifica conformidad WCAG.** Completa los resultados con revisión del navegador, teclado, tecnologías de asistencia y pruebas con personas. No analiza URLs, sigue enlaces o envía el HTML a servicios externos.

## Colaborar y seguridad

Pruebas con HTML ficticio y CI en Python 3.11–3.13. Aporta casos mínimos ficticios y una explicación del comportamiento esperado. No publiques formularios con información personal o credenciales en issues. Las contribuciones se reciben bajo [MIT](LICENSE).

Para vulnerabilidades, usa Report a vulnerability si está disponible; de lo contrario, solicita un canal privado sin detalles sensibles. No se ofrece un plazo de respuesta. Crear este repositorio no garantiza elegibilidad para Claude for OSS.
