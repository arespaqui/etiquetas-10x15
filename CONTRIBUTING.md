# Cómo contribuir

Gracias por querer mejorar esto. Este repo es chico y las reglas son pocas, pero
son firmes: casi todas existen para que el paquete se pueda publicar sin filtrar
datos de nadie y sin romper la licencia.

## Antes de escribir código

1. **Abrí un issue** contando qué querés cambiar y por qué. Si es un error,
   contá cómo reproducirlo con un PDF armado por vos, nunca con un rótulo real.
2. Esperá una respuesta antes de mandar un cambio grande. Un cambio chico y bien
   explicado se revisa rápido; uno grande sin acuerdo previo puede quedar sin
   mergear.

## Preparar el entorno

```
python -m pip install -r requirements.txt
```

Windows con Python 3.12 es el entorno de referencia. Si tocás la ventana, probala
también a mano: las pruebas cubren la lógica, no el aspecto.

## Las pruebas tienen que pasar

El runner es `unittest` de la biblioteca estándar. Nada de pytest ni de
dependencias nuevas.

```
python -m unittest discover -s tests -t .
```

- Un cambio sin pruebas que lo respalden no se acepta, salvo que sea sólo de
  documentación.
- Si arreglás un error, agregá primero la prueba que falla con el código viejo y
  después el arreglo.
- Las pruebas se corren igual en Windows (local) y en el CI
  (`.github/workflows/tests.yml`).

## Los fixtures son sintéticos

Todos los PDFs de prueba se generan dentro del propio test, en memoria o en el
directorio temporal (`tests/soporte.py` tiene las herramientas). Eso significa:

- **No se aceptan PDFs reales**, ni como fixture, ni como adjunto en un issue.
- **No se aceptan datos de personas**: nombres, direcciones, teléfonos, CUIT,
  números de seguimiento, códigos postales reales ni nada que salga de un rótulo
  de verdad.
- Si necesitás reproducir un caso raro, armá un PDF de mentira con la misma
  geometría. Alcanza para probar el motor.

## Reglas del código

1. **La escala es siempre uniforme.** Nunca estirar: un código de barras
   deformado puede no escanear. Es la razón de ser de todo esto.
2. **El original no se toca.** El resultado siempre es un archivo nuevo
   `<nombre>_10x15.pdf`.
3. **Nada de recortes a ciegas.** Si el recorte no puede ver un contenido
   (imágenes, dibujos anchos), no recorta y avisa.
4. **Ningún error en silencio.** Todo fallo se muestra en la ventana y queda en
   `errores.log`.
5. **Todo lo visible va en español**: ventana, mensajes, documentación. Los
   comentarios de código pueden quedar en inglés, como ya están.
6. **Nada de datos privados en el repo**: ni PDFs, ni ZIPs, ni `_diag/`, ni
   respaldos `.reg`, ni capturas de casos reales, ni `__pycache__`, ni
   `errores.log`.

## Licencia: la obligación AGPL

El proyecto se distribuye bajo **AGPL-3.0** (texto completo en [`LICENSE`](LICENSE),
aviso de terceros en [`NOTICE`](NOTICE)). Al mandar un cambio aceptás que se
publique bajo esa misma licencia, y eso trae dos obligaciones:

- **`LICENSE` y `NOTICE` no se modifican ni se borran.**
- **Toda versión distribuida —modificada o no— tiene que mantener el código fuente
  disponible** para quien la reciba, bajo AGPL-3.0. Si alguna vez se ofrece como
  servicio en red, quien lo use por red tiene derecho a obtener ese fuente.

No se aceptan cambios que agreguen código con licencia incompatible con AGPL-3.0,
ni dependencias nuevas sin hablarlo antes (y sin actualizar `NOTICE` si
corresponde).

## Proponer el cambio

1. Hacé un fork y una rama con nombre claro.
2. Un cambio por tema: el arreglo, su prueba y la documentación que lo explica van
   juntos; dos cosas distintas no van en el mismo cambio.
3. Actualizá lo que corresponda: `README.md` si cambia el uso, `LEEME.md` si cambia
   la guía del usuario final, `CHANGELOG.md` si es algo que se nota desde afuera.
4. Verificá antes de mandar:

   ```
   python -m unittest discover -s tests -t .
   ```

5. Abrí el pull request contando qué problema resuelve y cómo lo probaste.
   Aclaralo si tocaste el comportamiento del recorte o de la escala: esas dos
   cosas se revisan con lupa.

## Reportar un problema

Usá la plantilla de issues. **No adjuntes rótulos reales ni capturas con datos de
personas.** Si el problema es visual, alcanza con una descripción del PDF de
origen (tamaño de hoja, si tiene marco, si trae imágenes).
