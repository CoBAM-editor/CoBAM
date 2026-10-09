# Prototipo de buscador CoBAM

Buscador experimental de la correspondencia de Benito Arias Montano, inspirado en la búsqueda facetada de Clusius Correspondence, la búsqueda avanzada y navegación por entidades de EMLO y las prácticas de interoperabilidad de correspSearch. Se mantiene separado de WordPress y de `main`.

**La búsqueda actual de WordPress basada en Zotero está activa y debe seguir funcionando.** Este prototipo es una vía paralela de evaluación: no desactiva, sustituye ni modifica Zotero. Cualquier futura integración se decidirá después de validar los resultados y la interfaz.

## Interfaz

- Diseño en dos columnas: facetas y refinamiento a la izquierda; lista de cartas a la derecha.
- Búsqueda de texto en todos los campos, transcripción, traducción, resumen, incipit, notas/aparato o solo metadatos.
- Consultas con AND, OR, NOT, frases entre comillas y comodines `*` y `?`.
- Rango cronológico por año, conservando los intervalos de fecha cuando constan en el XML.
- Facetas con recuentos dinámicos: remitente, destinatario, corresponsales (combinados), lugares de origen/destino, idioma, personas y lugares mencionados, archivos/instituciones y signaturas.
- Disponibilidad documental: cartas con facsímil, con transcripción y con traducción.
- Ordenación y paginación; los resultados muestran el resumen, incipit, disponibilidad y metadatos bibliográficos/manuscritos desplegables.
- Enlaces al XML original y a los facsímiles disponibles.

## Campos derivados de TEI-XML

El generador lee los encabezados TEI y las capas textuales que ya están codificadas: `correspAction` (remitente, destinatario, lugares y fecha), `langUsage`, notas `abstract` e `incipit`, cuerpos `text[@type='source']` y `text[@type='translation']`, nombres y lugares mencionados, testimonios manuscritos, signaturas, bibliografía, `facsimile/graphic`, estado editorial y fecha de revisión.

No se inventan metadatos que no estén disponibles; los campos ausentes quedan vacíos. El buscador usa la fecha como intervalo de años cuando los datos permiten recuperarlo. Las fechas incompletas requieren revisión editorial para poder filtrar con mayor precisión.

## Generar catálogo completo

Requiere Python 3, sin instalar dependencias. Desde la raíz del repositorio:

```bash
python prototipo-buscador/generar_catalogo.py
```

El programa escribe `prototipo-buscador/catalogo.json` y muestra cuántas cartas tienen transcripción, traducción y facsímil. Lee los XML de la raíz del repositorio sin modificarlos.

La acción de GitHub genera un `catalog-data.js` para que GitHub Pages pueda cargar el catálogo completo sin depender de llamadas `fetch` bloqueadas cuando la página se abre como sitio estático.

## Probar localmente

Tras ejecutar el generador, crea el archivo JavaScript del catálogo:

```bash
python -c "import json,pathlib; p=pathlib.Path('prototipo-buscador/catalogo.json'); pathlib.Path('prototipo-buscador/catalog-data.js').write_text('window.COBAM_CATALOG = '+json.dumps(json.loads(p.read_text(encoding='utf-8')),ensure_ascii=False)+';\\n',encoding='utf-8')"
python -m http.server 8000 --directory prototipo-buscador
```

Abre `http://localhost:8000`.

## Validación e integración

GitHub Actions comprueba la sintaxis del generador, genera y valida el catálogo, comprueba la sintaxis JavaScript y publica la vista previa de Pages en la rama de pruebas. El ZIP de prueba se conserva como artefacto de Actions.

Antes de integrar en WordPress:
1. Revisar una muestra de resultados con criterios históricos y filológicos.
2. Validar la extracción de nombres, localizaciones, signaturas y fuentes.
3. Revisar el tratamiento de fechas parciales e intervalos.
4. Ajustar enlaces desde los resultados a las ediciones publicadas.
5. Probar accesibilidad, navegación móvil y rendimiento del catálogo.
6. Aprobar explícitamente el diseño antes de cambiar la búsqueda de la web pública.
