# Etiquetas 10 × 15 — guía corta

Convierte un PDF de rótulo (A4, oficio, lo que venga) en un PDF de **100 × 150 mm
exactos**, listo para imprimir en una etiqueta térmica de 10 × 15 cm.

Este archivo es lo indispensable. Todo lo demás —cuándo usarla y cuándo no,
cómo leer cada aviso, problemas frecuentes, licencia— está en el
[manual completo](docs/manual.md). La instalación desde el código fuente, cómo
detecta el rótulo y las preguntas frecuentes están en el
[README del repositorio](https://github.com/arespaqui/etiquetas-10x15#readme).

## Uso

1. Abrí la app: doble clic en `Etiquetas 10x15.exe` (versión descargada) o en
   `1 - Abrir Etiquetas 10x15.bat` (código fuente).
2. Botón verde **"Elegir PDF y convertir"**.
3. Elegí el PDF del rótulo. Podés elegir varios a la vez.
4. La ventana te cuenta qué hizo. **Si hay un renglón con `!` en naranja, leelo
   antes de imprimir**: dice algo que tenés que saber.
5. Tocá **"Abrir el PDF convertido"** e imprimí.

Sale un archivo nuevo `<nombre>_10x15.pdf` al lado del original. **El original
nunca se toca.**

## Cómo imprimir

| Campo | Valor |
|---|---|
| Impresora | tu impresora de etiquetas térmica de 100 × 150 mm |
| Tamaño del papel | `Etiquetas 100x150` |
| **Escala** | **`Tamaño real`** (nunca "Ajustar al área de impresión") |
| Páginas por hoja | 1 |

Si la etiqueta sale corrida, es la escala.

## Cómo leer la ventana

```
OK  rotulo.pdf  ->  rotulo_10x15.pdf
   página 1: origen 86.0 x 163.0 mm  →  79.1 x 150.0 mm  (escala 92 %)
   ! El rótulo de origen no tiene forma 10×15: quedó con 10 mm de blanco a cada
     lado, a escala 92 % y sin deformar los códigos. Conviene pedir el rótulo en
     formato 10×15 al origen.
```

- **`origen`** → lo que mide el rótulo en el PDF que elegiste.
- **`impreso`** → lo que va a medir en tu etiqueta.
- **`escala`** → cuánto se agrandó o achicó. Siempre es la misma en ancho y alto,
  así los códigos no se deforman.
- **"recorté N mm de blanco del final"** → sólo aparece si había aire de sobra y
  se pudo sacar, por ejemplo `recorté 13 mm de blanco del final: el rótulo entra
  más grande`. Deja siempre 2 mm de margen para que la térmica no corte las letras.
- **`!` en naranja** → hay algo que tenés que saber antes de imprimir.

## Qué hace y qué no

Hace: recorta el aire que sobra al final, deja 2 mm de margen, escala sin
deformar y avisa cuando el rótulo de origen no tiene forma 10 × 15.

No hace: no estira para llenar la etiqueta, no borra contenido, no imprime solo y
**no garantiza que el código escanee en todos los lectores**.

Si el recorte encuentra una imagen o un dibujo ancho que no puede ver, **no
recorta** y muestra un aviso: en ese caso abrí el PDF convertido y miralo antes de
imprimir.

## Si algo falla

Nada falla en silencio. El aviso aparece en la ventana y el detalle completo queda
en `errores.log`:

| Cómo abrís la app | Dónde queda `errores.log` |
|---|---|
| `Etiquetas 10x15.exe` | `Etiquetas 10x15\errores.log`, junto al `.exe` |
| Código fuente | al lado de `app_etiquetas.pyw` |
| Con `ETIQUETAS_10X15_LOG` definida | en la ruta que indique esa variable |

Si la ventana no abre, arrastrá el PDF sobre
`2 - Arrastrar PDF (alternativa).bat`: los errores se ven en la consola.

## Aviso

Proyecto independiente: **no es software oficial de Correo Argentino** ni está
afiliado a Correo Argentino. Se ofrece sin garantía de ningún tipo. Licencia
**AGPL-3.0** (ver `LICENSE` y `NOTICE`).
