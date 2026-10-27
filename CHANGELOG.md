# Historial de cambios

Todos los cambios que se notan desde afuera se anotan acá. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y la versión sigue
[Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

Nada todavía.

## [1.0.1] - 2026-10-27

Actualización recomendada: la 1.0.0 entrega la etiqueta más chica de lo que debe.

### Corregido

- **El recorte del espacio muerto ya no se bloquea por el borde del propio marco.**
  El borde contaba como contenido, así que la línea de corte quedaba pegada al
  fondo del marco y el rótulo no se recortaba nunca. Ahora el borde se excluye y
  **la etiqueta vuelve a salir a 89,1 × 150,0 mm en vez de 79,1 mm**, con los
  códigos de barras más grandes y legibles.
- **Los documentos describen la regla real** del recorte: qué cuenta como
  contenido (texto, dibujos internos e imágenes, sin el borde del marco), la línea
  de corte a 2 mm del contenido y el mínimo de 5 mm de aire para recortar. Se
  sacaron las menciones al aviso que ya no existe.

### Cambiado

- **Ventana rediseñada con la identidad de Ardamir**: isotipo, paleta navy, dorado
  y crema, y jerarquía visual nueva.
- **Los resultados se muestran como tarjetas** con el estado en palabras
  (**Listo** / **Revisá** / **Error**), en lugar de una grilla de columnas.
- **Bloque «Cómo se usa»** visible mientras no hay resultados, para que la
  primera vez no haya que adivinar el paso siguiente.
- **El detalle técnico quedó oculto detrás de un enlace**: la superficie principal
  habla en castellano llano y las medidas finas aparecen sólo si las pedís.

## [1.0.0] - 2026-10-27

Primera versión publicable, con código fuente y con ejecutable de Windows.

### Agregado

- Conversión de un PDF de rótulo a un PDF de **100 × 150 mm exactos**, con una
  página de salida por cada página de entrada.
- Detección del rótulo por su **marco vectorial**, con respaldo al área con tinta
  cuando el marco no aparece. En ese caso la app lo avisa en pantalla en vez de
  fallar en silencio.
- **Escala uniforme**: el rótulo se agranda o se achica lo mismo en ancho y en
  alto, y se centra en la etiqueta. Nunca se estira, para no deformar los códigos
  de barras.
- **Recorte del aire del final** cuando hay 5 mm o más de blanco, con **2 mm de
  margen** entre el contenido y el borde de la etiqueta.
- **Guarda conservadora del recorte**: si hay una imagen o un dibujo ancho fuera
  del área calculada, no recorta y avisa que hay que revisar el resultado.
- Aviso de proporción cuando el rótulo de origen no tiene forma 10 × 15, con las
  medidas y el blanco que va a quedar a los costados.
- Escritura de un archivo nuevo `<nombre>_10x15.pdf`: **el PDF original nunca se
  modifica ni se borra**. Si el nombre ya existe, agrega `(2)`, `(3)`, etc.
- Ventana en español (`app_etiquetas.pyw`) con selección de varios PDFs a la vez,
  detalle por página y botones para abrir el PDF convertido o su carpeta.
- Alternativa sin ventana para arrastrar PDFs sobre un `.bat` o llamar al motor
  desde la línea de comandos.
- `verificar.py`: control de calidad de un PDF convertido (tamaño de página,
  tamaño de la tinta, alto, centrado y desbordes).
- Errores visibles: aviso en pantalla y detalle completo en `errores.log`, aun
  ejecutando sin consola. El log se puede redirigir con la variable de entorno
  `ETIQUETAS_10X15_LOG`.
- **Ejecutable de Windows** (`--onedir --windowed`, 64 bits) y el procedimiento
  reproducible para construirlo en `empaquetar/`.
- Documentación en español: `README.md`, `LEEME.md` y esta guía de contribución.
- Pruebas automáticas con `unittest` (biblioteca estándar) sobre PDFs sintéticos
  generados por las propias pruebas, y CI en Windows con Python 3.12.
- Licencia **AGPL-3.0** completa, más `NOTICE` con el aviso de PyMuPDF/MuPDF de
  Artifex y los enlaces a su código fuente.

### Notas

- El ejecutable **no está firmado digitalmente**, así que Windows puede mostrar el
  aviso de "Windows protegió tu PC" la primera vez que se abre.
- La app no imprime: genera el PDF y lo abre. La impresión la hacés vos, con papel
  de 100 × 150 mm y escala "Tamaño real".

[Sin publicar]: https://github.com/arespaqui/etiquetas-10x15/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/arespaqui/etiquetas-10x15/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/arespaqui/etiquetas-10x15/releases/tag/v1.0.0
