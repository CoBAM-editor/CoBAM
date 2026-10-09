# Prototipo de buscador CoBAM

Esta carpeta contiene un prototipo **independiente** para validar la interfaz antes de integrarla en WordPress.

## Estado actual
- Interfaz responsive en español.
- Filtros combinables por texto, remitente, destinatario, año, lugar e idioma.
- Normalización de acentos en las consultas.
- Una carta de ejemplo tomada de los metadatos del XML `1560 02 01-60 05 05 CoBAM.xml`.
- Enlace al archivo XML del repositorio.

## Importante
El catálogo aún contiene solo un registro de demostración. El siguiente paso es implementar y probar un generador de catálogo que lea todos los XML-TEI del repositorio y extraiga de forma robusta `teiHeader` (título, fechas, acciones de correspondencia, lugares, idioma, resumen e incipit), además de texto de la carta. Las fechas incompletas o intervalos deberán tratarse sin asumir un día concreto.

No modifica la web pública, los XML existentes, `format.xsl` ni la rama `main`.

## Prueba
Abre `index.html` en un navegador. En esta etapa funciona sin servidor y sin dependencias externas.
