# Prototipo de buscador CoBAM

Esta carpeta contiene un prototipo **independiente** para validar el mecanismo de búsqueda antes de integrarlo en WordPress. Se trabaja en la rama `prototipo-buscador`; la rama `main` y la web pública no se modifican.

## Qué incluye

- Interfaz adaptable a ordenador y móvil, en español.
- Búsqueda por texto libre en título, resumen, incipit y texto de la carta.
- Filtros combinables por remitente, destinatario, intervalo de años, lugar e idioma.
- Búsqueda que no distingue mayúsculas ni acentos.
- Generador de catálogo a partir de los XML-TEI que tengan `tei:correspDesc`.
- Enlace de cada resultado al XML original de GitHub.
- Una carta incorporada como ejemplo de reserva para probar la interfaz sin catálogo.

## Generar el catálogo completo

Se necesita Python 3, sin instalar paquetes adicionales. Desde la carpeta raíz del repositorio, ejecuta:

```bash
python prototipo-buscador/generar_catalogo.py
```

El script lee los XML de la raíz del repositorio y crea `prototipo-buscador/catalogo.json`. Los XML originales se abren en modo lectura y no se alteran.

Para probar la interfaz con el catálogo generado, inicia un servidor local:

```bash
python -m http.server 8000 --directory prototipo-buscador
```

Después abre [http://localhost:8000](http://localhost:8000). Si abres el HTML directamente con doble clic, el navegador puede bloquear la lectura del JSON por seguridad; en ese caso la página muestra la carta de ejemplo.

## Validación automática

La acción de GitHub en `.github/workflows/prototipo-buscador.yml` comprueba la sintaxis del generador, crea y valida el catálogo, comprueba el JavaScript y prepara un ZIP de prueba como artefacto de la ejecución. El artefacto se conserva durante 14 días.

Para descargarlo: entra en **Actions** del repositorio, abre la ejecución de «Validar prototipo del buscador CoBAM» y descarga `prototipo-buscador-CoBAM` en la sección de artefactos.

## Pendiente antes de integrar en WordPress

1. Revisar resultados frente a una muestra de cartas.
2. Confirmar tratamiento de fechas parciales e intervalos cronológicos.
3. Verificar cómo construir enlaces a las ediciones publicadas, no solo a los XML.
4. Estimar tamaño y rendimiento del catálogo completo.
5. No integrar en la página pública hasta aprobar el prototipo.
