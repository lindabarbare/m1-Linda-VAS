"""Iesniegumi — minimāls skelets. Visu pārējo būvē komanda kopā ar Claude (skat. BACKLOG.md)."""
import os
import re
import sqlite3
from flask import Flask, g, render_template, send_file, session, redirect, url_for, request

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

app = Flask(__name__, template_folder=os.path.dirname(__file__), static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "macibu-uzdevums-nav-drosa-atslega")

LOMAS = {"iedzivotajs": "Iedzīvotājs", "darbinieks": "Darbinieks", "vaditajs": "Vadītājs"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Izveido tabulas un sākumdatus, ja datubāzes vēl nav."""
    if os.path.exists(DB_PATH):
        return
    with sqlite3.connect(DB_PATH) as db, open(SCHEMA_PATH, encoding="utf-8") as f:
        db.executescript(f.read())


@app.context_processor
def inject_globals():
    loma = session.get("loma")
    return {"loma": loma, "lomas_nosaukums": LOMAS.get(loma), "LOMAS": LOMAS}


@app.route("/")
def index():
    temas = get_db().execute("SELECT id, nosaukums FROM temas ORDER BY nosaukums").fetchall()
    return render_template("index.html", temas=temas)


@app.route("/iesniegt", methods=["GET", "POST"])
def iesniegt():
    db = get_db()
    temas = db.execute("SELECT id, nosaukums FROM temas ORDER BY nosaukums").fetchall()
    values = {
        "vards": "",
        "epasts": "",
        "temas_id": "",
        "adrese": "",
        "apraksts": "",
        "piekritu": False,
    }
    errors = {}

    if request.method == "POST":
        values.update({
            "vards": request.form.get("vards", "").strip(),
            "epasts": request.form.get("epasts", "").strip(),
            "temas_id": request.form.get("temas_id", ""),
            "adrese": request.form.get("adrese", "").strip(),
            "apraksts": request.form.get("apraksts", "").strip(),
            "piekritu": request.form.get("piekritu") == "1",
        })

        if not values["vards"]:
            errors["vards"] = "Ievadiet vārdu."
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values["epasts"]):
            errors["epasts"] = "Ievadiet derīgu e-pasta adresi."
        try:
            temas_id = int(values["temas_id"])
            tema = db.execute("SELECT id FROM temas WHERE id = ?", (temas_id,)).fetchone()
            if tema is None:
                errors["temas_id"] = "Izvēlieties tēmu no saraksta."
        except ValueError:
            errors["temas_id"] = "Izvēlieties tēmu no saraksta."
        if not values["apraksts"]:
            errors["apraksts"] = "Ievadiet iesnieguma aprakstu."
        if request.form.get("piekritu") != "1":
            errors["piekritu"] = "Lai iesniegtu iesniegumu, apstipriniet piekrišanu datu apstrādei."

        if not errors:
            year = db.execute("SELECT strftime('%Y', 'now', 'localtime')").fetchone()[0]
            last_number = db.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(numurs, 6) AS INTEGER)), 0) "
                "FROM iesniegumi WHERE numurs LIKE ?",
                (f"{year}-%",),
            ).fetchone()[0]
            numurs = f"{year}-{last_number + 1:04d}"
            piekritis_laiks = db.execute("SELECT datetime('now', 'localtime')").fetchone()[0]
            cursor = db.execute(
                "INSERT INTO iesniegumi "
                "(numurs, temas_id, vards, epasts, datu_apstrade_piekrita, piekritis_laiks, adrese, apraksts) "
                "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                (numurs, temas_id, values["vards"], values["epasts"], piekritis_laiks,
                 values["adrese"] or None, values["apraksts"]),
            )
            db.execute(
                "INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES (?, 'statuss', 'sistema', ?)",
                (cursor.lastrowid, "Iesniegums reģistrēts ar statusu «Jauns»."),
            )
            db.commit()
            session["apstiprinajuma_numurs"] = numurs
            return redirect(url_for("apstiprinajums"))

    return render_template("iesniegt.html", temas=temas, values=values,
                           errors=errors), 400 if errors else 200


@app.route("/apstiprinajums")
def apstiprinajums():
    numurs = session.get("apstiprinajuma_numurs")
    if not numurs:
        return redirect(url_for("iesniegt"))
    return render_template("apstiprinajums.html", numurs=numurs)


@app.route("/static/style.css")
def style():
    return send_file(os.path.join(os.path.dirname(__file__), "style.css"), mimetype="text/css")


@app.post("/loma")
def izveleties_lomu():
    loma = request.form.get("loma")
    if loma in LOMAS:
        session["loma"] = loma
    return redirect(url_for("index"))


@app.route("/pieklustamiba")
def pieklustamiba():
    # US-6: aizpildiet pēc testēšanas (veidne docs/PIEEJAMIBAS-PRASIBAS.md, 5. sadaļa)
    return render_template("pieklustamiba.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
