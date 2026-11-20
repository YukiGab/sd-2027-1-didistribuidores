# Documentación de DiDistribuidores

Todos los documentos están escritos en LaTeX con un estilo común (`estilo/didistribuidores.sty`) y se
entregan ya compilados en PDF. Las capturas y las salidas de las pruebas viven junto a cada documento.

| Carpeta | Contenido |
|---|---|
| `bitacora-1/` | Etapa 1, monolito modular (rama `01-monolito`): `bitacora-etapa-1.tex`, `.pdf` y capturas en `img/` |
| `bitacora-2/` | Etapa 2, notificaciones como servicio aparte (`02-separacion`) |
| `bitacora-3/` | Etapa 3, repartidores como servicio, gateway y réplicas (`03-separacion`) |
| `bitacora-4/` | Etapa 4, resiliencia (`04-resiliencia`). Las pruebas son scripts en `pruebas/` (`comun.sh`, `prueba-0.sh` a `prueba-7.sh`) y su salida real está en `pruebas/evidencia/` |
| `pruebas/` | Plan y resultados de todas las pruebas: `pruebas-del-proyecto.pdf` y `.docx`, la regresión final (`regresion.sh` y `evidencia/regresion.txt`) y `tex_a_word.py`, que genera el `.docx` a partir del `.tex` |
| `manual-de-usuario/` | Cómo levantar el sistema y usar la aplicación de escritorio, el panel web y la API |
| `documentacion-final/` | Reporte final (`reporte-final.tex` y `.pdf`, con sus diagramas). Una copia del PDF está en `docs/reporte-final.pdf`, que es donde lo pide la rúbrica |
| `estilo/` | Estilo LaTeX compartido |

## Cómo recompilar

Con una distribución de LaTeX (MiKTeX o TeX Live), desde la carpeta de cada documento, dos veces para que
salga el índice:

```bash
pdflatex bitacora-etapa-4.tex
pdflatex bitacora-etapa-4.tex
```

La versión Word de las pruebas se regenera en Windows con Microsoft Word instalado:

```bash
cd pruebas
python tex_a_word.py
```

## Cómo repetir las pruebas de la etapa 4

Desde `Proyecto/`, en bash o Git Bash, con el sistema levantado:

```bash
source ../documentacion/bitacora-4/pruebas/comun.sh
source ../documentacion/bitacora-4/pruebas/prueba-2.sh      # o cualquier otra
source ../documentacion/pruebas/regresion.sh                # regresión de las etapas 1 a 3
```

Las bitácoras de las etapas 1 a 3 son la versión revisada de las originales en Word (mismas capturas,
texto corregido y ordenado). Cada bitácora describe el código de su etapa; lo que cambió después se
señala en notas.
