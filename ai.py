"""MI ieteikums darbiniekam: tēma un atbildes projekts (US-7).

Noklusēti — atslēgvārdu imitācija bez tīkla. Ja ir ANTHROPIC_API_KEY, izmanto Claude API
(modelis no AI_MODEL); jebkuras kļūdas gadījumā atgriežas uz imitāciju. Līgums nemainās:
ieteikums(apraksts) -> {"tema": str, "atbildes_projekts": str, "avots": str}.
"""
import json
import os

TEMAS = ("Ielas un ceļi", "Apgaismojums", "Atkritumi un vide", "Bērnudārza rinda",
         "Sociālā palīdzība", "Cits")

ATSLEGVARDI = {
    "Ielas un ceļi": ("bedr", "ceļ", "ietv", "bruģ", "asfalt", "ceļa zīm", "iela"),
    "Apgaismojums": ("latern", "apgaismoj", "nedeg", "gaism", "spuldz"),
    "Atkritumi un vide": ("atkritum", "konteiner", "maisi", "piesārņ", "sakopt", "miskast"),
    "Bērnudārza rinda": ("bērnudārz", "pirmsskol", "rind"),
    "Sociālā palīdzība": ("sociāl", "pabalst", "palīdzīb"),
}

PROJEKTI = {
    "Ielas un ceļi": "Paldies par ziņojumu par ceļa vai ietves stāvokli. Informāciju esam nodevuši "
                     "par ceļu uzturēšanu atbildīgajam speciālistam, kurš novērtēs situāciju dabā "
                     "un plānos remontdarbus.",
    "Apgaismojums": "Paldies par ziņojumu par ielu apgaismojumu. Bojājumu esam nodevuši apgaismojuma "
                    "apkalpojošajam dienestam, kas to pārbaudīs un novērsīs.",
    "Atkritumi un vide": "Paldies par ziņojumu. Informāciju esam nodevuši atkritumu apsaimniekotājam "
                         "un teritorijas uzturēšanas dienestam, lai situāciju novērstu.",
    "Bērnudārza rinda": "Paldies par jautājumu par bērnudārza rindu. Informāciju par rindu un vietām "
                        "sniedz pašvaldības izglītības speciālists; precizēsim datus un sazināsimies ar jums.",
    "Sociālā palīdzība": "Paldies par jautājumu. Informāciju par sociālajiem pakalpojumiem un "
                         "konsultāciju laikiem sniedz pašvaldības sociālais dienests; precizēsim un atbildēsim.",
    "Cits": "Paldies par iesniegumu. Esam to saņēmuši un nodevuši atbildīgajam speciālistam izskatīšanai.",
}


def _imitacija(apraksts: str) -> dict:
    teksts = apraksts.casefold()
    tema = max(ATSLEGVARDI, key=lambda t: sum(v in teksts for v in ATSLEGVARDI[t]))
    if not any(v in teksts for v in ATSLEGVARDI[tema]):
        tema = "Cits"
    return {"tema": tema, "atbildes_projekts": PROJEKTI[tema], "avots": "imitācija (atslēgvārdi)"}


def _claude(apraksts: str) -> dict:
    import anthropic

    model = os.environ.get("AI_MODEL", "claude-opus-5-5")
    schema = {
        "type": "object",
        "properties": {
            "tema": {"type": "string", "enum": list(TEMAS)},
            "atbildes_projekts": {"type": "string"},
        },
        "required": ["tema", "atbildes_projekts"],
        "additionalProperties": False,
    }
    response = anthropic.Anthropic(timeout=30.0).messages.create(
        model=model,
        max_tokens=2048,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        system="Tu palīdzi pašvaldības darbiniekam. Izvēlies iesnieguma tēmu no saraksta un uzraksti "
               "īsu, pieklājīgu atbildes projektu latviešu valodā (2–4 teikumi). Neizdomā faktus, "
               "termiņus vai personas datus. Projektu pārbaudīs un rediģēs cilvēks.",
        messages=[{"role": "user", "content": f"Iesnieguma apraksts:\n{apraksts}"}],
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"Negaidīts stop_reason: {response.stop_reason}")
    dati = json.loads(next(b.text for b in response.content if b.type == "text"))
    if dati.get("tema") not in TEMAS or not str(dati.get("atbildes_projekts", "")).strip():
        raise ValueError("Atbilde neatbilst līgumam")
    return {"tema": dati["tema"], "atbildes_projekts": dati["atbildes_projekts"].strip(),
            "avots": f"Claude API ({model})"}


def ieteikums(apraksts: str) -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _claude(apraksts)
        except Exception:
            pass  # kļūdas gadījumā — imitācija
    return _imitacija(apraksts)


# --- US-10: čata palīgs iedzīvotājam. Atbild tikai no BUJ; ja nezina — to pasaka. ---

BUJ = [
    ("Kā iesniegt iesniegumu?",
     ("iesniegt", "iesniegum", "pieteikt", "ziņot", "forma", "kā rakstīt"),
     "Atveriet sadaļu «Iesniegt iesniegumu», norādiet vārdu, e-pastu, tēmu un aprakstu, apstipriniet "
     "piekrišanu datu apstrādei un nospiediet «Iesniegt iesniegumu». Pēc tam saņemsiet iesnieguma numuru."),
    ("Kādi dokumenti jāpievieno?",
     ("dokument", "pielikum", "pievienot", "fail", "foto", "attēl"),
     "Šajā formā dokumenti nav jāpievieno — pietiek ar aprakstu. Ja izskatīšanai būs vajadzīgi dokumenti, "
     "pašvaldības darbinieks ar jums sazināsies pa norādīto e-pastu."),
    ("Kā uzzināt iesnieguma statusu?",
     ("statuss", "status", "numur", "pārbaudīt", "kur ir", "kas notiek"),
     "Atveriet sadaļu «Mans iesniegums» un ievadiet numuru, ko saņēmāt pēc iesniegšanas, piemēram, 2026-0001. "
     "Redzēsiet statusu un atbildi, ja tā jau ir."),
    ("Ko nozīmē statusi?",
     ("jauns", "apstrād", "atbildēts", "noraidīt", "nozīmē"),
     "«Jauns» — iesniegums saņemts. «Apstrādē» — darbinieks to izskata. «Atbildēts» — atbilde sagatavota. "
     "«Noraidīts» — iesniegumu nevar izpildīt; iemesls norādīts atbildē."),
    ("Cik ilgi jāgaida atbilde?",
     ("cik ilgi", "termiņ", "kad", "gaidīt", "ilgi"),
     "Pašvaldība uz iesniegumu atbild saprātīgā termiņā, parasti viena mēneša laikā. Statusu varat sekot "
     "sadaļā «Mans iesniegums»."),
    ("Par kādām tēmām var iesniegt?",
     ("tēm", "par ko", "kādos jautājumos", "bedr", "latern", "atkritum", "bērnudārz", "sociāl"),
     "Var iesniegt par ielām un ceļiem, apgaismojumu, atkritumiem un vidi, bērnudārza rindu, sociālo "
     "palīdzību un citiem jautājumiem (tēma «Cits»)."),
    ("Kā tiek apstrādāti mani dati?",
     ("dati", "datu", "privāt", "e-past", "personas"),
     "Glabājam tikai iesnieguma izskatīšanai vajadzīgos datus. E-pastu redz tikai pašvaldības darbinieks; "
     "statusa lapā pēc numura vārds un e-pasts netiek rādīti."),
]

NEZINU = ("Uz šo jautājumu nevaru droši atbildēt. Lūdzu, sazinieties ar pašvaldību vai iesniedziet "
          "jautājumu sadaļā «Iesniegt iesniegumu» ar tēmu «Cits».")


def _paligs_imitacija(jautajums: str) -> dict:
    teksts = jautajums.casefold()
    punkti = [sum(v in teksts for v in atslegas) for _, atslegas, _ in BUJ]
    labakais = max(range(len(BUJ)), key=lambda i: punkti[i])
    atbilde = BUJ[labakais][2] if punkti[labakais] else NEZINU
    return {"atbilde": atbilde, "avots": "imitācija (BUJ)"}


def _paligs_claude(jautajums: str) -> dict:
    import anthropic

    model = os.environ.get("AI_MODEL", "claude-opus-5-5")
    buj_teksts = "\n\n".join(f"J: {j}\nA: {a}" for j, _, a in BUJ)
    response = anthropic.Anthropic(timeout=30.0).messages.create(
        model=model,
        max_tokens=1024,
        output_config={"effort": "low"},
        system="Tu esi pašvaldības iesniegumu sistēmas palīgs iedzīvotājiem. Atbildi latviešu valodā, "
               "vienkāršā valodā, 1–3 teikumos, TIKAI izmantojot zemāk doto BUJ. Neizdomā dokumentus, "
               "termiņus, likumus, kontaktus vai faktus, kuru BUJ nav. Ja BUJ atbildes nav, atbildi tieši: "
               f"«{NEZINU}»\n\nBUJ:\n{buj_teksts}",
        messages=[{"role": "user", "content": jautajums}],
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"Negaidīts stop_reason: {response.stop_reason}")
    atbilde = "".join(b.text for b in response.content if b.type == "text").strip()
    if not atbilde:
        raise ValueError("Tukša atbilde")
    return {"atbilde": atbilde, "avots": f"Claude API ({model})"}


def paligs(jautajums: str) -> dict:
    """Čata palīga atbilde: {"atbilde": str, "avots": str}."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _paligs_claude(jautajums)
        except Exception:
            pass  # kļūdas gadījumā — imitācija
    return _paligs_imitacija(jautajums)
