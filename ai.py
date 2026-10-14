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
