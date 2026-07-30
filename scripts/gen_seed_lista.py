# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Generatore delle righe di seed per una lista configurabile
#        (`ui.lista_definizione`, `lista_colonna`, `lista_preset`,
#        `lista_preset_colonna`), a partire dalla vista DB che la alimenta e
#        dal componente .vue che oggi la disegna con una DataTable grezza.
#
#        Nasce dalla migrazione delle 34 liste del Gruppo A
#        (docs/it/dev/work-in-progress/piano-migrazione-primevue-5.md §8-bis):
#        269 colonne da configurare a mano sono un lavoro meccanico, e il
#        meccanico si genera.
#
#        Il modello supporta nativamente il disegno «carica tutte le colonne,
#        mostrane alcune»: il catalogo sta in `ui.lista_colonna` (che NON ha
#        flag di visibilita'), la visibilita' sta in `ui.lista_preset_colonna`.
#        E' gia' la convenzione in uso: `vendite.ddt` ha 24 colonne configurate
#        e 12 visibili, `anagrafiche.clienti` 14 e 10.
#
# Note: NON scrive sul DB e NON applica migrazioni. Emette righe CSV da
#       rivedere e da far confluire in un changeset Liquibase dal team DB
#       (regola: le azioni DB non partono dall'agente).
#       Quello che genera e' una BOZZA: i campi curati (priorita, gruppo,
#       larghezza, sensibile) escono con i default e vanno decisi a mano —
#       lo script li elenca nel report finale invece di far finta di saperli.
# ------------------------------------------------------------
"""Genera le righe di seed per una lista configurabile.

Uso tipico (dalla root del repo):

    backend/.venv/bin/python scripts/gen_seed_lista.py \\
        --codice vendite.fatture \\
        --descrizione "Elenco Fatture" \\
        --vista vendite.vw_fatture_lista \\
        --vue frontend/src/vendite/views/FattureListView.vue

Autoverifica (rigenera una lista gia' configurata e confronta col DB):

    backend/.venv/bin/python scripts/gen_seed_lista.py --verifica vendite.ddt
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg non disponibile: usa backend/.venv/bin/python")

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "db/changelog/migrations_v2/80_data/sql/ui"
LOCALES = ROOT / "frontend/src/locales/it.json"

# Mappa tipo PostgreSQL -> ui.tipo_dato (enum: string|numeric|date|datetime|boolean|enum).
# Le voci non mappate finiscono a 'string' e vengono segnalate nel report: e'
# preferibile un default onesto e visibile a un'inferenza silenziosa.
TIPO_DATO = {
    "character varying": "string", "text": "string", "character": "string",
    "uuid": "string", "jsonb": "string", "json": "string",
    "integer": "numeric", "bigint": "numeric", "smallint": "numeric",
    "numeric": "numeric", "double precision": "numeric", "real": "numeric",
    "date": "date",
    "timestamp without time zone": "datetime",
    "timestamp with time zone": "datetime",
    "boolean": "boolean",
}

# Formatter FE riconosciuti nei template di cella -> ui.lista_colonna.formato.
FORMATO_DA_TEMPLATE = {
    "displayDate": "date_short",
    "displayDateTime": "datetime_short",
    "formatCurrency": "currency_eur",
    "formatNumber": "number_2",
}


# Scopo: apre la connessione al DB leggendo backend/.env (stesse variabili del BE).
def connetti():
    env = {}
    percorso = ROOT / "backend/.env"
    if percorso.exists():
        for riga in percorso.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Z_]+)=(.*)", riga)
            if m:
                env[m.group(1)] = m.group(2).strip().strip("'\"")
    g = lambda k, d=None: os.environ.get(k) or env.get(k) or d  # noqa: E731
    return psycopg.connect(
        host=g("DB_HOST", "localhost"), port=g("DB_PORT", "5432"),
        dbname=g("DB_NAME"), user=g("DB_USER"), password=g("DB_PASSWORD"),
    )


# Scopo: colonne della vista che alimenta la lista, in ordine di definizione.
#        E' la fonte dell'insieme COMPLETO: le colonne che il .vue non mostra
#        entrano comunque nel catalogo, invisibili nel preset.
def colonne_vista(conn, schema: str, vista: str) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, vista),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


# Scopo: tipo_dato inferito dal NOME della colonna, cercandolo fra tutte le
#        tabelle e viste del DB. Serve quando la lista non ha una sorgente
#        dichiarata (il caso normale per il Gruppo A: una `vw_*` dedicata in
#        genere non esiste), perche' l'alternativa era far uscire tutto `string`.
#
#        Regola di sicurezza: si accetta l'inferenza **solo se non ambigua**.
#        Misurato sul DB il 2026-07-30: dopo la mappatura a `ui.tipo_dato`,
#        1567 nomi su 1588 (98.7%) risolvono a un tipo solo — l'ambiguita' dei
#        tipi PG (`descrizione` e' varchar, text e char) sparisce perche' tutti
#        e tre mappano su `string`. I 21 casi residui (`id`, `numero`,
#        `data_evento`, `split_payment`...) restano `string` e vengono segnalati:
#        un tipo sbagliato non da' errore, da' una colonna che non ordina.
#
#        Lo schema della lista ha la precedenza: `codice` dentro `catalogo` vale
#        piu' di `codice` trovato altrove.
def tipi_per_nome(conn, nomi: list[str], schema_pref: str) -> tuple[dict, dict]:
    if not nomi:
        return {}, {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, table_schema, data_type
            FROM information_schema.columns
            WHERE column_name = ANY(%s)
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            """,
            (list(nomi),),
        )
        righe = cur.fetchall()

    per_nome: dict[str, dict[str, set]] = {}
    for nome, schema, tipo_pg in righe:
        td = TIPO_DATO.get(tipo_pg)
        if td is None:
            continue  # tipo esotico (PostGIS, enum applicativi): non inferisce
        per_nome.setdefault(nome, {"pref": set(), "tutti": set()})
        per_nome[nome]["tutti"].add(td)
        if schema == schema_pref:
            per_nome[nome]["pref"].add(td)

    risolti, ambigui = {}, {}
    for nome, dati in per_nome.items():
        candidati = dati["pref"] or dati["tutti"]
        if len(candidati) == 1:
            risolti[nome] = (next(iter(candidati)),
                             "schema della lista" if dati["pref"] else "altro schema")
        else:
            ambigui[nome] = sorted(candidati)
    return risolti, ambigui


# Scopo: colonne oggi disegnate dal .vue, nell'ordine in cui l'operatore le vede.
#        Restituisce (codice, chiave_i18n|None, formato|None, allineato_destra).
#        E' cio' che rende il preset di default gia' "quello di prima" invece di
#        un elenco alfabetico da risistemare a mano.
def colonne_vue(percorso: Path) -> list[tuple[str, str | None, str | None, bool]]:
    if not percorso.exists():
        return []
    testo = percorso.read_text(encoding="utf-8")
    fuori = []
    # Ogni <Column ...> con il suo eventuale corpo, per leggere il template cella.
    for m in re.finditer(r"<Column\b(.*?)(?:/>|>(.*?)</Column>)", testo, re.S):
        attr, corpo = m.group(1), m.group(2) or ""
        campo = re.search(r'\bfield="([^"]+)"', attr)
        if not campo:
            continue  # colonna azione o solo-template: non ha un campo dati
        chiave = re.search(r""":header="t\(['"]([^'"]+)['"]\)""", attr)
        formato = next(
            (v for k, v in FORMATO_DA_TEMPLATE.items() if k + "(" in corpo), None
        )
        destra = "text-align: right" in attr or "text-align:right" in attr
        fuori.append((campo.group(1), chiave.group(1) if chiave else None, formato, destra))
    return fuori


# Scopo: etichetta leggibile a partire dalla chiave i18n, cercata in it.json.
#        Se non si risolve si ripiega sul codice colonna umanizzato, e la riga
#        viene segnalata: un'etichetta sbagliata a video e' peggio di una da rivedere.
def etichetta_da_i18n(chiave: str | None, codice: str, dizionario: dict) -> tuple[str, bool]:
    if chiave:
        nodo = dizionario
        for pezzo in chiave.split("."):
            if isinstance(nodo, dict) and pezzo in nodo:
                nodo = nodo[pezzo]
            else:
                nodo = None
                break
        if isinstance(nodo, str):
            return nodo, True
    return codice.replace("_", " ").capitalize(), False


# Suffissi fisici che le liste configurate tolgono per ottenere il nome logico
# della colonna (`stato_descrizione` -> `stato`, `valuta_codice` -> `valuta`).
# Ricavati dalle 61 colonne su 204 che hanno `codice != campo_sorgente`.
SUFFISSI_FISICI = ("_descrizione", "_codice", "_numero", "_denominazione", "_completa")


# Scopo: nome logico proposto per una colonna, a partire dal campo fisico.
#        E' una PROPOSTA: viene sempre segnalata nel report, perche' il nome di
#        una colonna e' una scelta di presentazione, non una regola.
def nome_logico(campo: str) -> str:
    for s in SUFFISSI_FISICI:
        if campo.endswith(s) and len(campo) > len(s) + 1:
            return campo[: -len(s)]
    return campo


# Scopo: rileva se il .vue ha una colonna di azioni di riga (kebab
#        `RowActionsMenu`): va tradotta in una colonna `tipo_colonna='azione'`
#        senza `campo_sorgente`, che l'introspezione della vista non puo' vedere.
def ha_colonna_azioni(percorso: Path) -> bool:
    if not percorso.exists():
        return False
    testo = percorso.read_text(encoding="utf-8")
    for m in re.finditer(r"<Column\b(.*?)(?:/>|>(.*?)</Column>)", testo, re.S):
        attr, corpo = m.group(1), m.group(2) or ""
        if not re.search(r'\bfield="', attr) and "RowActionsMenu" in corpo:
            return True
    return False


# Scopo: ultimo id occupato in un CSV di seed, per continuare la numerazione
#        senza collidere con le righe gia' committate.
def ultimo_id(nome_csv: str, campo: str = "id") -> int:
    percorso = SEED_DIR / nome_csv
    if not percorso.exists():
        return 0
    with percorso.open(newline="", encoding="utf-8") as fh:
        return max((int(r[campo]) for r in csv.DictReader(fh) if r.get(campo)), default=0)


# Scopo: costruisce le quattro liste di righe CSV per una lista configurabile.
#        Ritorna anche l'elenco dei punti che richiedono una decisione umana.
def genera(codice, descrizione, schema, vista, cols_vista, cols_vue, dizionario, utente,
           data_insert, azioni=False, tipi_nome=None, tipi_ambigui=None):
    avvisi: list[str] = []
    ordine_vue = {c[0]: i for i, c in enumerate(cols_vue)}
    meta_vue = {c[0]: c for c in cols_vue}

    # FONTE = il .vue, non la vista. Verificato sulle 11 liste gia' configurate:
    # `ui.lista_colonna.codice` e' un nome LOGICO curato e `campo_sorgente` la
    # colonna fisica (`stato` -> `stato_descrizione`), e 61 colonne su 204
    # differiscono. In piu' esistono colonne senza sorgente (`azioni`,
    # tipo_colonna='azione'). Una generazione 1:1 dalla vista produrrebbe per
    # `vendite.ddt` 63 colonne coi nomi sbagliati invece di 24 coi nomi giusti.
    # La vista serve a due cose oneste: validare i campi e PROPORRE candidati.
    tipi_vista = dict(cols_vista)
    for c in ordine_vue:
        if tipi_vista and c not in tipi_vista:
            avvisi.append(f"campo `{c}` del .vue non esiste nella vista: verificare il nome")

    ordinate = [(c, tipi_vista.get(c, "character varying")) for c in ordine_vue]

    tipi_nome = tipi_nome or {}
    tipi_ambigui = tipi_ambigui or {}
    if not tipi_vista and tipi_nome:
        avvisi.append(
            f"nessuna sorgente dichiarata: {len(tipi_nome)} tipi su {len(ordine_vue)} "
            "dedotti dal NOME della colonna cercandolo nel DB (accettati solo se non "
            "ambigui). Restano una deduzione: verificarli"
        )
    for _n, _cand in (tipi_ambigui or {}).items():
        avvisi.append(
            f"tipo di `{_n}` AMBIGUO nel DB ({', '.join(_cand)}) -> lasciato `string`: "
            "va deciso a mano, altrimenti la colonna non ordina come dovrebbe"
        )

    if tipi_vista:
        candidati = sorted(set(tipi_vista) - set(ordine_vue))
        if candidati:
            avvisi.append(
                f"la vista espone altri {len(candidati)} campi non usati dal .vue: NON sono "
                "stati aggiunti automaticamente (sarebbero rumore). Vanno scelti a mano "
                "quelli che meritano una colonna configurabile invisibile: "
                + ", ".join(candidati[:12]) + ("..." if len(candidati) > 12 else "")
            )

    id_lista = ultimo_id("lista_definizione.csv") + 1
    id_col = ultimo_id("lista_colonna.csv")
    id_preset = ultimo_id("lista_preset.csv") + 1

    righe_col, righe_pc = [], []
    for pos, (nome, tipo_pg) in enumerate(ordinate, start=1):
        id_col += 1
        visibile = nome in ordine_vue
        logico = nome_logico(nome)
        if logico != nome:
            avvisi.append(f"`{nome}` -> codice logico proposto `{logico}` "
                          "(campo_sorgente conservato): confermare il nome")
        if nome in tipi_vista:
            tipo_dato = TIPO_DATO.get(tipo_pg)
            if tipo_dato is None:
                tipo_dato = "string"
                avvisi.append(
                    f"tipo PG `{tipo_pg}` (colonna `{nome}`) non mappato -> string, da verificare")
        elif nome in tipi_nome:
            tipo_dato = tipi_nome[nome][0]
        else:
            tipo_dato = "string"
            if nome not in tipi_ambigui:
                avvisi.append(
                    f"`{nome}` non trovata in nessuna tabella o vista -> `string`: "
                    "campo calcolato dal BE? va tipizzato a mano")
        chiave_i18n, formato, destra = (None, None, False)
        if visibile:
            _, chiave_i18n, formato, destra = meta_vue[nome]
        etichetta, risolta = etichetta_da_i18n(chiave_i18n, nome, dizionario)
        if visibile and not risolta:
            avvisi.append(f"etichetta di `{nome}` non risolta da it.json: e' un segnaposto")
        allineamento = "right" if (destra or tipo_dato == "numeric") else (
            "center" if tipo_dato == "boolean" else "left"
        )
        righe_col.append({
            "id": id_col, "lista_id": id_lista, "codice": logico, "etichetta": etichetta,
            "etichetta_estesa": "", "campo_sorgente": nome,
            "tipo_colonna": "informazione", "tipo_dato": tipo_dato,
            "formato": formato or "", "larghezza_default": "",
            "ordine_default": pos * 10, "allineamento": allineamento,
            "gruppo": "", "gruppo_ordine": "",
            "filtrabile": "t", "ordinabile": "t", "esportabile": "t",
            "ricercabile_full": "f", "sensibile": "f", "attivo": "t",
            "data_insert": data_insert, "user_insert": utente,
            "etichetta_i18n_key": chiave_i18n or "", "priorita": 50,
        })
        righe_pc.append({
            "preset_id": id_preset, "colonna_id": id_col, "ordine": pos * 10,
            "visibile": "t" if visibile else "f", "fissata": "f",
        })

    # Colonna azioni: senza campo_sorgente, sempre visibile e in coda. E' il
    # kebab di riga, che nel .vue e' una <Column> senza `field`.
    if azioni:
        id_col += 1
        pos = len(ordinate) + 1
        righe_col.append({
            "id": id_col, "lista_id": id_lista, "codice": "azioni", "etichetta": "Azioni",
            "etichetta_estesa": "", "campo_sorgente": "",
            "tipo_colonna": "azione", "tipo_dato": "string", "formato": "",
            "larghezza_default": "", "ordine_default": pos * 10, "allineamento": "center",
            "gruppo": "", "gruppo_ordine": "",
            "filtrabile": "f", "ordinabile": "f", "esportabile": "f",
            "ricercabile_full": "f", "sensibile": "f", "attivo": "t",
            "data_insert": data_insert, "user_insert": utente,
            "etichetta_i18n_key": "", "priorita": 50,
        })
        righe_pc.append({"preset_id": id_preset, "colonna_id": id_col,
                         "ordine": pos * 10, "visibile": "t", "fissata": "f"})

    riga_def = {
        "id": id_lista, "codice": codice, "descrizione": descrizione,
        "schema_dati": schema, "vista_sql": vista or "", "attivo": "t",
        "data_insert": data_insert, "user_insert": utente,
    }
    breve = codice.split(".")[-1]
    riga_preset = {
        "id": id_preset, "lista_id": id_lista, "codice": f"{breve}_default",
        "descrizione": f"Vista standard {breve}", "ambito": "sistema",
        "profilo_accesso_id": "", "emittente_fiscale_id": "", "is_default": "t",
        "pagina_dimensione": 25, "ordinamento_default": "", "attivo": "t",
        "data_insert": data_insert, "user_insert": utente,
    }

    avvisi.append("`priorita` (ritiro responsive), `gruppo`/`gruppo_ordine`, "
                  "`larghezza_default`, `sensibile` e `ricercabile_full` escono coi "
                  "default: sono decisioni curate, vanno riviste a mano")
    if not cols_vue:
        avvisi.append("nessun .vue letto: TUTTE le colonne risultano visibili=f, "
                      "il preset di default va composto a mano")
    return riga_def, righe_col, riga_preset, righe_pc, avvisi


# Scopo: serializza righe come CSV senza intestazione, pronte da appendere.
def csv_righe(righe: list[dict], campi: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campi, lineterminator="\n")
    for r in righe:
        w.writerow(r)
    return buf.getvalue()


CAMPI_DEF = ["id", "codice", "descrizione", "schema_dati", "vista_sql", "attivo",
             "data_insert", "user_insert"]
CAMPI_COL = ["id", "lista_id", "codice", "etichetta", "etichetta_estesa", "campo_sorgente",
             "tipo_colonna", "tipo_dato", "formato", "larghezza_default", "ordine_default",
             "allineamento", "gruppo", "gruppo_ordine", "filtrabile", "ordinabile",
             "esportabile", "ricercabile_full", "sensibile", "attivo", "data_insert",
             "user_insert", "etichetta_i18n_key", "priorita"]
CAMPI_PRESET = ["id", "lista_id", "codice", "descrizione", "ambito", "profilo_accesso_id",
                "emittente_fiscale_id", "is_default", "pagina_dimensione",
                "ordinamento_default", "attivo", "data_insert", "user_insert"]
CAMPI_PC = ["preset_id", "colonna_id", "ordine", "visibile", "fissata"]


# Scopo: autoverifica — rigenera una lista GIA' configurata dalla sua vista e
#        confronta l'insieme delle colonne con quello reale nel DB. Serve a
#        sapere se il generatore e' credibile PRIMA di usarlo su liste nuove:
#        senza questa controprova i CSV avrebbero la forma giusta e contenuto
#        ignoto.
def verifica(conn, codice: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, schema_dati, vista_sql FROM ui.lista_definizione WHERE codice = %s",
            (codice,),
        )
        riga = cur.fetchone()
        if not riga:
            print(f"[X] lista `{codice}` non registrata")
            return 1
        id_lista, schema, vista = riga
        if not vista:
            print(f"[i] lista `{codice}` non ha vista_sql: non verificabile per introspezione")
            return 0
        cur.execute(
            "SELECT codice FROM ui.lista_colonna WHERE lista_id = %s ORDER BY codice",
            (id_lista,),
        )
        reali = {r[0] for r in cur.fetchall()}

    dalla_vista = {c for c, _ in colonne_vista(conn, schema, vista)}
    solo_db = sorted(reali - dalla_vista)
    solo_vista = sorted(dalla_vista - reali)

    print(f"lista `{codice}`  vista {schema}.{vista}")
    print(f"  colonne configurate nel DB : {len(reali)}")
    print(f"  colonne esposte dalla vista: {len(dalla_vista)}")
    print(f"  in comune                  : {len(reali & dalla_vista)}")
    if solo_db:
        print(f"  [!] configurate ma NON nella vista ({len(solo_db)}): {', '.join(solo_db)}")
    if solo_vista:
        print(f"  [i] nella vista ma non configurate ({len(solo_vista)}): {', '.join(solo_vista)}")
    # Le colonne configurate senza corrispondenza nella vista sono il segnale
    # che conta: vorrebbero dire che l'introspezione non basta come fonte.
    return 1 if solo_db else 0


# Scopo: punto d'ingresso CLI.
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codice", help="codice stabile della lista, es. vendite.fatture")
    p.add_argument("--descrizione", default=None, help="descrizione leggibile")
    p.add_argument("--vista", "--sorgente", dest="vista", default=None,
                   help="schema.oggetto che alimenta la lista: vista OPPURE tabella "
                        "(information_schema copre entrambe); fornisce i tipi reali")
    p.add_argument("--vue", default=None, help="componente .vue con le <Column> attuali")
    p.add_argument("--utente", default="mctit", help="user_insert nei CSV (default: mctit)")
    p.add_argument("--data", default=None,
                   help="data_insert nei CSV (default: oggi). Le colonne sono NOT NULL: "
                        "un valore vuoto farebbe fallire l'apply")
    p.add_argument("--verifica", metavar="CODICE",
                   help="autoverifica su una lista gia' configurata")
    args = p.parse_args()
    if not args.data:
        from datetime import date
        args.data = f"{date.today().isoformat()} 00:00:00"

    with connetti() as conn:
        if args.verifica:
            return verifica(conn, args.verifica)

        if not args.codice:
            p.error("serve --codice (oppure --verifica)")
        schema, vista = ("", "")
        cols_vista: list[tuple[str, str]] = []
        if args.vista:
            if "." not in args.vista:
                p.error("--vista va nella forma schema.vista")
            schema, vista = args.vista.split(".", 1)
            cols_vista = colonne_vista(conn, schema, vista)
            if not cols_vista:
                print(f"[X] vista {schema}.{vista} inesistente o senza colonne", file=sys.stderr)
                return 1
        else:
            schema = args.codice.split(".")[0]

        cols_vue = colonne_vue(ROOT / args.vue) if args.vue else []
        dizionario = {}
        if LOCALES.exists():
            import json
            dizionario = json.loads(LOCALES.read_text(encoding="utf-8"))

        tipi_nome, tipi_ambigui = ({}, {})
        if cols_vue:
            noti = dict(cols_vista)
            mancanti = [c[0] for c in cols_vue if c[0] not in noti]
            tipi_nome, tipi_ambigui = tipi_per_nome(conn, mancanti, schema)

        riga_def, righe_col, riga_preset, righe_pc, avvisi = genera(
            args.codice, args.descrizione or args.codice, schema, vista,
            cols_vista, cols_vue, dizionario, args.utente, args.data,
            azioni=ha_colonna_azioni(ROOT / args.vue) if args.vue else False,
            tipi_nome=tipi_nome, tipi_ambigui=tipi_ambigui,
        )

    visibili = sum(1 for r in righe_pc if r["visibile"] == "t")
    print(f"# lista `{args.codice}` — {len(righe_col)} colonne, {visibili} visibili nel preset\n")
    for nome, righe, campi in (
        ("lista_definizione.csv", [riga_def], CAMPI_DEF),
        ("lista_colonna.csv", righe_col, CAMPI_COL),
        ("lista_preset.csv", [riga_preset], CAMPI_PRESET),
        ("lista_preset_colonna.csv", righe_pc, CAMPI_PC),
    ):
        print(f"# ---- da appendere a {nome} ----")
        print(csv_righe(righe, campi), end="")
        print()

    print("# ---- da decidere a mano ----")
    for a in dict.fromkeys(avvisi):
        print(f"#  - {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
