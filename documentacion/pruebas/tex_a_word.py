"""Genera la versión Word (.docx) de pruebas-del-proyecto.tex.

El documento fuente es el .tex (de ahí sale el PDF). Este script lo convierte a HTML entendiendo solo
los comandos que usa ese documento y le pide a Microsoft Word que lo guarde como .docx, así las dos
versiones dicen exactamente lo mismo.

    python tex_a_word.py              # crea pruebas-del-proyecto.html y pruebas-del-proyecto.docx

Requiere Windows con Microsoft Word (se usa por COM desde PowerShell).
"""
import html
import os
import re
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, "pruebas-del-proyecto.tex")
SALIDA_HTML = os.path.join(AQUI, "pruebas-del-proyecto.html")
SALIDA_DOCX = os.path.join(AQUI, "pruebas-del-proyecto.docx")

AZUL = "#1F3A68"
ESTILO = f"""
body {{ font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #1d1d1f; }}
h1 {{ color: {AZUL}; font-size: 26pt; margin-bottom: 0; }}
h2 {{ color: {AZUL}; font-size: 16pt; border-bottom: 1px solid #C9CDD3; margin-top: 18pt; }}
h3 {{ color: {AZUL}; font-size: 13pt; }}
code {{ font-family: Consolas, monospace; font-size: 9.5pt; }}
pre {{ font-family: Consolas, monospace; font-size: 8.5pt; padding: 6pt; white-space: pre-wrap; }}
pre.comando {{ background: #1E1F24; color: #FFFFFF; }}
pre.salida {{ background: #F4F5F7; color: #000000; }}
div.nota {{ background: #F4F5F7; border-left: 4px solid {AZUL}; padding: 6pt 10pt; margin: 8pt 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 6pt 0; }}
th {{ text-align: left; border-bottom: 1.5px solid #000; padding: 3pt; font-family: Arial; }}
td {{ vertical-align: top; border-bottom: 0.5px solid #C9CDD3; padding: 3pt; }}
.ok {{ color: #1B7F3B; font-weight: bold; font-family: Arial; }}
.portada {{ color: #3D5AFE; font-family: Arial; }}
"""


def leer_archivo(ruta_relativa):
    with open(os.path.join(AQUI, ruta_relativa), encoding="utf-8") as f:
        return f.read()


def en_linea(texto):
    """Convierte los comandos de una línea de LaTeX a HTML."""
    # Los caracteres escapados (\{ \} \$ \_ ...) se guardan aparte para que no los toquen las reglas
    escapados = {"\\{": "\x01", "\\}": "\x02", "\\$": "\x03", "\\_": "\x04", "\\&": "\x05", "\\%": "\x06", "\\#": "\x07"}
    t = texto
    for original, marca in escapados.items():
        t = t.replace(original, marca)
    t = html.escape(t, quote=False)
    reglas = [
        (r"\\cod\{((?:[^{}]|\{[^{}]*\})*)\}", r"<code>\1</code>"),
        (r"\\url\{([^}]*)\}", r'<a href="\1">\1</a>'),
        (r"\\textbf\{([^}]*)\}", r"<b>\1</b>"),
        (r"\\emph\{([^}]*)\}", r"<i>\1</i>"),
        (r"\\textsf\{([^}]*)\}", r"\1"),
        (r"\\ok\{\}|\\ok\b", r'<span class="ok">Cumple</span>'),
        (r"\\hfill", ""),
        (r"\$\\rightarrow\$", "→"),
        (r"\\times|×", "×"),
        (r"\\textbackslash\s?", "\\\\"),
        (r"\\queria", "<b>Qué queríamos comprobar.</b>"),
        (r"\\observado", "<b>Qué se observó.</b>"),
        (r"``", "“"), (r"''", "”"), (r"~", " "),
        (r"\\ldots", "…"),
    ]
    for patron, cambio in reglas:
        t = re.sub(patron, cambio, t)
    t = re.sub(r"\\[a-zA-Z]+\*?", "", t).replace("{", "").replace("}", "")   # comandos que sobran
    for original, marca in escapados.items():
        t = t.replace(marca, original[1])
    return t


def tabla(lineas):
    """Las filas de un tabularx: encabezado antes de \\midrule, cuerpo hasta \\bottomrule."""
    filas, encabezado = [], None
    actual = ""
    for linea in lineas:
        s = linea.strip()
        if s.startswith("\\toprule"):
            continue
        if s.startswith("\\midrule"):
            encabezado, filas = filas, []
            continue
        if s.startswith("\\bottomrule"):
            break
        actual += " " + s
        if actual.rstrip().endswith("\\\\"):
            filas.append([c.strip() for c in actual.strip()[:-2].split("&")])
            actual = ""
    partes = ["<table>"]
    for f in encabezado or []:
        partes.append("<tr>" + "".join(f"<th>{en_linea(c)}</th>" for c in f) + "</tr>")
    for f in filas:
        partes.append("<tr>" + "".join(f"<td>{en_linea(c)}</td>" for c in f) + "</tr>")
    partes.append("</table>")
    return "\n".join(partes)


def convertir(tex):
    cuerpo = tex.split("\\begin{document}", 1)[1].split("\\end{document}", 1)[0]
    lineas = cuerpo.split("\n")
    salida, parrafo, i = [], [], 0

    def cerrar_parrafo():
        if parrafo:
            salida.append("<p>" + en_linea(" ".join(parrafo)) + "</p>")
            parrafo.clear()

    while i < len(lineas):
        linea = lineas[i]
        s = linea.strip()
        if s.startswith("\\portada"):
            titulo = re.findall(r"\{([^}]*)\}", "".join(lineas[i:i + 3]))
            salida.append(f'<p class="portada">DIDISTRIBUIDORES · {html.escape(titulo[0].upper())}</p>')
            salida.append(f"<h1>{html.escape(titulo[1])}</h1><p>{html.escape(titulo[2])}</p>")
            salida.append("<p>Sistemas Distribuidos 2027-1, Grupo 2, FI-UNAM · Equipo: Erick Isaac Echeverria "
                          "Goicochea (@ErickI07) y Yukioayax Canek Gabriel Hernández (@YukiGab) · "
                          "https://github.com/YukiGab/sd-2027-1-didistribuidores · 18 de noviembre de 2026</p>")
            i += 3
            continue
        if s.startswith(("\\tableofcontents", "\\newpage", "%")):
            i += 1
            continue
        m = re.match(r"\\(sub)?section\*?\{(.*)\}", s)
        if m:
            cerrar_parrafo()
            nivel = "h3" if m.group(1) else "h2"
            salida.append(f"<{nivel}>{en_linea(m.group(2))}</{nivel}>")
            i += 1
            continue
        if s.startswith("\\begin{comando}"):
            cerrar_parrafo()
            fin = lineas.index("\\end{comando}", i)
            salida.append('<pre class="comando">' + html.escape("\n".join(lineas[i + 1:fin])) + "</pre>")
            i = fin + 1
            continue
        m = re.match(r"\\lstinputlisting\[style=salida\]\{(.*)\}", s)
        if m:
            cerrar_parrafo()
            salida.append('<pre class="salida">' + html.escape(leer_archivo(m.group(1)).rstrip()) + "</pre>")
            i += 1
            continue
        if s.startswith("\\begin{nota}"):
            cerrar_parrafo()
            titulo = re.match(r"\\begin\{nota\}(?:\[(.*)\])?", s).group(1) or "Nota"
            fin = next(k for k in range(i, len(lineas)) if lineas[k].strip().startswith("\\end{nota}"))
            texto = " ".join(l.strip() for l in lineas[i + 1:fin])
            salida.append(f'<div class="nota"><b>{en_linea(titulo)}.</b> {en_linea(texto)}</div>')
            i = fin + 1
            continue
        if "\\begin{tabularx}" in s:
            cerrar_parrafo()
            fin = next(k for k in range(i, len(lineas)) if "\\end{tabularx}" in lineas[k])
            salida.append(tabla(lineas[i + 1:fin]))
            i = fin + 1
            continue
        if s.startswith("\\begin{itemize}"):
            cerrar_parrafo()
            fin = lineas.index("\\end{itemize}", i)
            elementos = " ".join(l.strip() for l in lineas[i + 1:fin]).split("\\item")
            salida.append("<ul>" + "".join(f"<li>{en_linea(e)}</li>" for e in elementos if e.strip()) + "</ul>")
            i = fin + 1
            continue
        if not s:
            cerrar_parrafo()
        else:
            parrafo.append(s)
        i += 1
    cerrar_parrafo()
    return ("<html><head><meta charset='utf-8'><title>Pruebas del proyecto</title>"
            f"<style>{ESTILO}</style></head><body>" + "\n".join(salida) + "</body></html>")


def guardar_docx():
    """Abre el HTML con Word (sin ventana ni avisos) y lo guarda como .docx con todo incrustado."""
    script = f"""
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
try {{
  $d = $w.Documents.Open('{SALIDA_HTML}', $false, $true)
  $d.PageSetup.TopMargin = 60; $d.PageSetup.BottomMargin = 60
  $d.PageSetup.LeftMargin = 60; $d.PageSetup.RightMargin = 60
  $d.SaveAs2('{SALIDA_DOCX}', 16)
  $d.Close($false)
}} finally {{ $w.Quit() }}
"""
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], check=True, timeout=180)


if __name__ == "__main__":
    with open(FUENTE, encoding="utf-8") as f:
        documento = convertir(f.read())
    with open(SALIDA_HTML, "w", encoding="utf-8") as f:
        f.write(documento)
    guardar_docx()
    print("Listo:", SALIDA_DOCX)
