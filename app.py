"""Iesniegumi — minimāls skelets. Visu pārējo būvē komanda kopā ar Claude (skat. BACKLOG.md)."""
import os
import re
import sqlite3
import uuid
from ai import ieteikums, paligs
from flask import Flask, abort, g, jsonify, render_template, send_file, session, redirect, url_for, request

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

app = Flask(__name__, template_folder=os.path.dirname(__file__), static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "macibu-uzdevums-nav-drosa-atslega")

LOMAS = {"iedzivotajs": "Iedzīvotājs", "darbinieks": "Darbinieks", "vaditajs": "Vadītājs"}
LOMU_APRAKSTI = {
    "iedzivotajs": "Iesniedz iesniegumus un seko to statusam",
    "darbinieks": "Apstrādā iesniegumus un sagatavo atbildes",
    "vaditajs": "Skata statistiku un pārskatus",
}
# Galvenā izvēlne pēc lomas: (endpoint, teksts). Bez lomas — tikai «Sākums»
NAVIGACIJA = {
    None: [("index", "Sākums")],
    "iedzivotajs": [("index", "Sākums"), ("iesniegt", "Iesniegt iesniegumu"),
                    ("mans_iesniegums", "Mans iesniegums")],
    "darbinieks": [("index", "Sākums"), ("iesniegumu_saraksts", "Iesniegumu saraksts")],
    "vaditajs": [("index", "Sākums"), ("parskats", "Pārskats")],
}
STATUSI = ("Jauns", "Apstrādē", "Atbildēts", "Noraidīts")
STATUSU_KLASES = {
    "Jauns": "statuss-jauns",
    "Apstrādē": "statuss-apstrade",
    "Atbildēts": "statuss-atbildets",
    "Noraidīts": "statuss-noraidits",
}
# Atļautās statusa pārejas: Jauns → Apstrādē → Atbildēts / Noraidīts
STATUSU_PAREJAS = {
    "Jauns": ("Apstrādē",),
    "Apstrādē": ("Atbildēts", "Noraidīts"),
    "Atbildēts": (),
    "Noraidīts": (),
}
NOTIKUMU_VEIDI = {
    "statuss": "Statusa maiņa",
    "komentars": "Komentārs",
    "atbilde": "Atbilde",
    "mi_ieteikums": "MI ieteikums",
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.create_function("casefold", 1, lambda value: value.casefold() if value else "")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Izveido tabulas un sākumdatus, ja datubāzes vēl nav; esošai pievieno jaunās tabulas."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()
    with sqlite3.connect(DB_PATH) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'iesniegumi'").fetchone():
            # Esošā datubāzē izpilda tikai «CREATE TABLE IF NOT EXISTS» daļu (vēlāk pievienotās tabulas)
            db.executescript(schema[schema.index("CREATE TABLE IF NOT EXISTS"):])
        else:
            db.executescript(schema)


@app.context_processor
def inject_globals():
    loma = session.get("loma")
    paligs_zinas = []
    if session.get("paligs_saruna"):
        paligs_zinas = get_db().execute(
            "SELECT jautajums, atbilde FROM (SELECT id, jautajums, atbilde FROM paligs_zinas "
            "WHERE saruna_id = ? ORDER BY id DESC LIMIT 10) ORDER BY id",
            (session["paligs_saruna"],),
        ).fetchall()
    return {"loma": loma, "lomas_nosaukums": LOMAS.get(loma), "LOMAS": LOMAS,
            "navigacija": NAVIGACIJA.get(loma, NAVIGACIJA[None]),
            "paligs_zinas": paligs_zinas, "paligs_atverts": session.pop("paligs_atverts", False)}


def aizstat_personas_datus(teksts):
    """Pirms saglabāšanas žurnālā aizstāj e-pastus un garas ciparu virknes (tālrunis, personas kods)."""
    teksts = re.sub(r"[^@\s,;]+@[^@\s,;]+", "[dzēsts]", teksts)
    # Iesnieguma numuru (2026-0001) atstāj, lai palīgs varētu par to runāt
    return re.sub(r"\b(?!\d{4}-\d{4}\b)(?:\d[\s-]?){8,}", "[dzēsts]", teksts)


@app.route("/")
def index():
    if session.get("loma") not in LOMAS:
        # Landing lapa: vienīgais uzdevums — izvēlēties lomu
        return render_template("landing.html", lomu_apraksti=LOMU_APRAKSTI, errors={})
    db = get_db()
    skaiti = dict(db.execute("SELECT statuss, COUNT(*) FROM iesniegumi GROUP BY statuss").fetchall())
    biezakas_temas = db.execute(
        "SELECT t.nosaukums, COUNT(*) AS skaits FROM iesniegumi i JOIN temas t ON t.id = i.temas_id "
        "GROUP BY t.id ORDER BY skaits DESC, t.nosaukums LIMIT 3"
    ).fetchall()
    return render_template(
        "index.html", skaiti=skaiti, kopa=sum(skaiti.values()), statusi=STATUSI,
        biezakas_temas=biezakas_temas,
    )


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

        try:
            temas_id = int(values["temas_id"])
            tema = db.execute("SELECT id FROM temas WHERE id = ?", (temas_id,)).fetchone()
            if tema is None:
                errors["temas_id"] = "Izvēlieties tēmu no saraksta."
        except ValueError:
            errors["temas_id"] = "Izvēlieties tēmu no saraksta."
        if not values["apraksts"]:
            errors["apraksts"] = "Ievadiet iesnieguma aprakstu."
        if not values["vards"]:
            errors["vards"] = "Ievadiet vārdu."
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values["epasts"]):
            errors["epasts"] = "Ievadiet derīgu e-pasta adresi."
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


@app.route("/mans-iesniegums")
def mans_iesniegums():
    numurs = request.args.get("numurs", "").strip()[:20]
    errors = {}
    iesniegums = None
    pedejais = None
    status_code = 200

    if "numurs" in request.args:
        if not numurs:
            errors["numurs"] = "Ievadiet iesnieguma numuru, piemēram, 2026-0001."
            status_code = 400
        else:
            db = get_db()
            # Iedzīvotājam nerāda vārdu, e-pastu un aprakstu
            iesniegums = db.execute(
                "SELECT i.id, i.numurs, i.izveidots, i.statuss, i.atbilde, t.nosaukums AS tema "
                "FROM iesniegumi i JOIN temas t ON t.id = i.temas_id WHERE i.numurs = ?",
                (numurs,),
            ).fetchone()
            if iesniegums is None:
                errors["numurs"] = f"Iesniegums ar numuru «{numurs}» nav atrasts. Pārbaudiet numuru, piemēram, 2026-0001."
                status_code = 404
            else:
                # Rāda tikai statusa maiņas; komentāri, atbilžu melnraksti un MI ieraksti ir iekšēji
                pedejais = db.execute(
                    "SELECT laiks, teksts FROM notikumi WHERE iesnieguma_id = ? AND veids = 'statuss' "
                    "ORDER BY laiks DESC, id DESC LIMIT 1",
                    (iesniegums["id"],),
                ).fetchone()

    return render_template(
        "mans_iesniegums.html", numurs=numurs, errors=errors, iesniegums=iesniegums,
        pedejais=pedejais,
        statusu_klase=STATUSU_KLASES.get(iesniegums["statuss"]) if iesniegums else None,
    ), status_code


@app.route("/iesniegumi")
def iesniegumu_saraksts():
    if session.get("loma") != "darbinieks":
        return redirect(url_for("index"))

    db = get_db()
    temas = db.execute("SELECT id, nosaukums FROM temas ORDER BY nosaukums").fetchall()
    status = request.args.get("statuss", "")
    if status not in STATUSI:
        status = ""
    tema_id = request.args.get("temas_id", "")
    if not any(str(tema["id"]) == tema_id for tema in temas):
        tema_id = ""
    meklet = request.args.get("meklet", "").strip()[:100]

    nosacijumi = []
    parametri = []
    if status:
        nosacijumi.append("i.statuss = ?")
        parametri.append(status)
    if tema_id:
        nosacijumi.append("i.temas_id = ?")
        parametri.append(int(tema_id))
    if meklet:
        nosacijumi.append(
            "(casefold(i.numurs) LIKE casefold(?) OR casefold(t.nosaukums) LIKE casefold(?) "
            "OR casefold(i.vards) LIKE casefold(?) OR casefold(i.adrese) LIKE casefold(?) "
            "OR casefold(i.apraksts) LIKE casefold(?))"
        )
        parametri.extend([f"%{meklet}%"] * 5)

    where = f"WHERE {' AND '.join(nosacijumi)}" if nosacijumi else ""
    iesniegumi = db.execute(
        "SELECT i.id, i.numurs, i.izveidots, t.nosaukums AS tema, i.vards, i.statuss "
        "FROM iesniegumi i JOIN temas t ON t.id = i.temas_id "
        f"{where} ORDER BY i.izveidots DESC, i.id DESC",
        parametri,
    ).fetchall()
    return render_template(
        "iesniegumu_saraksts.html", iesniegumi=iesniegumi, temas=temas,
        statusi=STATUSI, status=status, tema_id=tema_id, meklet=meklet,
        statusu_klases=STATUSU_KLASES,
    )


@app.route("/iesniegumi/<numurs>", methods=["GET", "POST"])
def iesnieguma_detalas(numurs):
    if session.get("loma") != "darbinieks":
        return redirect(url_for("index"))
    db = get_db()
    iesniegums = db.execute(
        "SELECT i.id, i.numurs, i.izveidots, i.vards, i.epasts, i.adrese, i.apraksts, i.statuss, "
        "i.atbilde, t.nosaukums AS tema FROM iesniegumi i JOIN temas t ON t.id = i.temas_id "
        "WHERE i.numurs = ?",
        (numurs,),
    ).fetchone()
    if iesniegums is None:
        abort(404)

    atlautie_statusi = STATUSU_PAREJAS[iesniegums["statuss"]]
    values = {"jauns_statuss": "", "komentars": "", "atbilde": iesniegums["atbilde"] or ""}
    errors = {}
    mi = None
    mi_projekts = False
    mi_pazinojums = None

    if request.method == "POST":
        darbiba = request.form.get("darbiba")
        pazinojums = None

        if darbiba == "statuss":
            values["jauns_statuss"] = request.form.get("jauns_statuss", "")
            if values["jauns_statuss"] not in atlautie_statusi:
                errors["jauns_statuss"] = "Izvēlieties jauno statusu no saraksta."
            elif values["jauns_statuss"] == "Atbildēts" and not iesniegums["atbilde"]:
                errors["jauns_statuss"] = "Pirms statusa «Atbildēts» saglabājiet atbildes tekstu."
            else:
                db.execute(
                    "UPDATE iesniegumi SET statuss = ?, atjaunots = datetime('now', 'localtime') WHERE id = ?",
                    (values["jauns_statuss"], iesniegums["id"]),
                )
                teksts = f"Statuss mainīts no «{iesniegums['statuss']}» uz «{values['jauns_statuss']}»."
                db.execute(
                    "INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES (?, 'statuss', ?, ?)",
                    (iesniegums["id"], session["loma"], teksts),
                )
                pazinojums = teksts
        elif darbiba == "komentars":
            values["komentars"] = request.form.get("komentars", "").strip()
            if not values["komentars"]:
                errors["komentars"] = "Ievadiet komentāra tekstu."
            else:
                db.execute(
                    "INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES (?, 'komentars', ?, ?)",
                    (iesniegums["id"], session["loma"], values["komentars"]),
                )
                pazinojums = "Komentārs pievienots."
        elif darbiba == "atbilde":
            values["atbilde"] = request.form.get("atbilde", "").strip()
            if not values["atbilde"]:
                errors["atbilde"] = "Ievadiet atbildes tekstu."
            else:
                db.execute(
                    "UPDATE iesniegumi SET atbilde = ?, atjaunots = datetime('now', 'localtime') WHERE id = ?",
                    (values["atbilde"], iesniegums["id"]),
                )
                db.execute(
                    "INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES (?, 'atbilde', ?, ?)",
                    (iesniegums["id"], session["loma"], values["atbilde"]),
                )
                pazinojums = "Atbilde saglabāta."
        elif darbiba == "mi_ieteikums":
            mi = ieteikums(iesniegums["apraksts"])
        elif darbiba == "mi_izmantot":
            # MI projekts tikai ievietots rediģējamā laukā; saglabā darbinieks ar «Saglabāt atbildi»
            projekts = request.form.get("atbildes_projekts", "").strip()
            if not projekts:
                abort(400)
            values["atbilde"] = projekts
            mi_projekts = True
            db.execute(
                "INSERT INTO notikumi (iesnieguma_id, veids, loma, teksts) VALUES (?, 'mi_ieteikums', ?, ?)",
                (iesniegums["id"], session["loma"],
                 "MI atbildes projekts ievietots atbildes laukā (vēl nav saglabāts)."),
            )
            db.commit()
            mi_pazinojums = ("MI atbildes projekts ievietots laukā «Atbildes teksts». "
                             "Pārbaudiet un rediģējiet to, tad saglabājiet.")
        else:
            abort(400)

        if pazinojums:
            db.commit()
            session["pazinojums"] = pazinojums
            return redirect(url_for("iesnieguma_detalas", numurs=numurs, _anchor="pazinojums"))

    notikumi = db.execute(
        "SELECT laiks, veids, loma, teksts FROM notikumi WHERE iesnieguma_id = ? ORDER BY laiks, id",
        (iesniegums["id"],),
    ).fetchall()
    return render_template(
        "iesnieguma_detalas.html", iesniegums=iesniegums, notikumi=notikumi,
        statusu_klase=STATUSU_KLASES[iesniegums["statuss"]], atlautie_statusi=atlautie_statusi,
        values=values, errors=errors, pazinojums=mi_pazinojums or session.pop("pazinojums", None),
        mi=mi, mi_projekts=mi_projekts,
        notikumu_veidi=NOTIKUMU_VEIDI, lomu_nosaukumi={**LOMAS, "sistema": "Sistēma"},
    ), 400 if errors else 200


@app.route("/parskats")
def parskats():
    if session.get("loma") != "vaditajs":
        return redirect(url_for("index"))
    db = get_db()
    skaiti = dict(db.execute("SELECT statuss, COUNT(*) FROM iesniegumi GROUP BY statuss").fetchall())
    pa_statusiem = [{"statuss": s, "skaits": skaiti.get(s, 0)} for s in STATUSI]
    pa_temam = db.execute(
        "SELECT t.nosaukums, COUNT(i.id) AS skaits FROM temas t "
        "LEFT JOIN iesniegumi i ON i.temas_id = t.id GROUP BY t.id ORDER BY t.nosaukums"
    ).fetchall()
    # Apstrādes laiks: no reģistrācijas līdz pēdējai statusa maiņai slēgtiem iesniegumiem
    # (ja statusa notikuma nav, izmanto lauku «atjaunots»)
    apstrade = db.execute(
        "SELECT AVG(julianday(COALESCE("
        "(SELECT MAX(n.laiks) FROM notikumi n WHERE n.iesnieguma_id = i.id AND n.veids = 'statuss'), "
        "i.atjaunots)) - julianday(i.izveidots)), COUNT(*) "
        "FROM iesniegumi i WHERE i.statuss IN ('Atbildēts', 'Noraidīts')"
    ).fetchone()
    videjais_dienas = None if apstrade[0] is None else f"{apstrade[0]:.1f}".replace(".", ",")
    return render_template(
        "parskats.html", pa_statusiem=pa_statusiem, pa_temam=pa_temam,
        kopa=sum(skaiti.values()), max_skaits=max(skaiti.values(), default=0),
        videjais_dienas=videjais_dienas, slegti=apstrade[1], statusu_klases=STATUSU_KLASES,
    )


@app.route("/static/style.css")
def style():
    return send_file(os.path.join(os.path.dirname(__file__), "style.css"), mimetype="text/css")


@app.post("/paligs")
def paligs_jautajums():
    atpakal = request.form.get("atpakal", "/")
    if not atpakal.startswith("/") or atpakal.startswith("//"):
        atpakal = "/"
    gaida_json = request.headers.get("Accept", "").startswith("application/json")

    if request.form.get("darbiba") == "notirit":
        session.pop("paligs_saruna", None)
        if gaida_json:
            return jsonify(ok=True)
        session["paligs_atverts"] = True
        return redirect(atpakal + "#paligs")

    jautajums = request.form.get("jautajums", "").strip()[:500]
    if not jautajums:
        if gaida_json:
            return jsonify(kluda="Ierakstiet jautājumu."), 400
        session["paligs_atverts"] = True
        return redirect(atpakal + "#paligs-jautajums")

    atbilde = paligs(jautajums)
    saruna_id = session.setdefault("paligs_saruna", uuid.uuid4().hex)
    db = get_db()
    db.execute(
        "INSERT INTO paligs_zinas (saruna_id, loma, jautajums, atbilde, avots) VALUES (?, ?, ?, ?, ?)",
        (saruna_id, session.get("loma"), aizstat_personas_datus(jautajums),
         atbilde["atbilde"], atbilde["avots"]),
    )
    db.commit()
    if gaida_json:
        return jsonify(jautajums=jautajums, atbilde=atbilde["atbilde"])
    session["paligs_atverts"] = True
    return redirect(atpakal + "#paligs-zinas")


@app.route("/static/paligs.js")
def paligs_js():
    return send_file(os.path.join(os.path.dirname(__file__), "paligs.js"), mimetype="text/javascript")


@app.post("/loma")
def izveleties_lomu():
    if request.form.get("darbiba") == "mainit":
        session.pop("loma", None)
        return redirect(url_for("index"))
    loma = request.form.get("loma")
    if loma not in LOMAS:
        errors = {"loma": "Izvēlieties lomu, lai turpinātu."}
        return render_template("landing.html", lomu_apraksti=LOMU_APRAKSTI, errors=errors), 400
    session["loma"] = loma
    return redirect(url_for("index"))


@app.route("/pieklustamiba")
def pieklustamiba():
    # US-6: aizpildiet pēc testēšanas (veidne docs/PIEEJAMIBAS-PRASIBAS.md, 5. sadaļa)
    return render_template("pieklustamiba.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
