# Verificación de la primera versión

Fecha: 2026-10-27. Entorno local: Windows, Node.js v24.12.0 y Python 3.12.7 según el proyecto.

`python -m unittest discover -s tests -v`: **25 pruebas aprobadas** con datos ficticios. Las pruebas ejercitan la biblioteca y la interfaz de comandos. No se usaron credenciales válidas, datos de ciudadanos o llamadas a servicios de IA.

CI está configurado para Python 3.11, 3.12 y 3.13. El resultado vigente se consulta en Actions; configurar un flujo no equivale por sí solo a una ejecución aprobada. Las acciones están fijadas por SHA y usan permisos de lectura.

Las comprobaciones de archivos y los tests son limitados: no certifican ausencia de toda vulnerabilidad, datos sensibles, conformidad normativa o impacto social. Los límites específicos figuran en README.md. No hay métricas de adopción, pilotos o usuarios verificados.
