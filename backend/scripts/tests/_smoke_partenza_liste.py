# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il corpo di `smoke-test-ui-partenza-liste.sh`: LA PARTENZA DI OGNI
#        LISTA CONFIGURABILE, provata rotta per rotta sul DB vero
#        (brief-be-collaudo-partenza-liste-dal-preset §2). Per ogni rotta GET
#        che dichiara `lista_codice`, chiamata come la chiama il FE alla prima
#        apertura (senza `order_by`, senza `limit`):
#          1. risponde 200;
#          2. `meta.ordinamento` e' la prima voce dell'ordinamento che il DB
#             risolve per l'utente (`ui.fn_ordinamento_lista`), oppure manca
#             se il preset non ne dichiara: e' cio' che accende l'intestazione;
#          3. le righe sono quante ne dice la misura (`ui.fn_misura_lista`),
#             o tutte se sono meno;
#          4. le righe sono davvero in quell'ordine;
#          5. il clic sulla stessa colonna, con lo stesso verso, da' le stesse
#             righe nello stesso ordine (BE30: stessa richiesta, stesso
#             spareggio), e col verso opposto le rovescia.
# Note: ⭐ IN-PROCESS, COL TOKEN VERO. Lo smoke bash fa il login di `dev.smoke`
#       (`smoke_login`) e passa il token in `PARTENZA_TOKEN`; qui le richieste
#       passano dal client di Django con quel token, quindi per
#       l'autenticazione, le GUC, i middleware e la base view: e' il codice
#       del working tree, senza aspettare il reload di Gunicorn.
#       ⭐ L'ORACOLO e' il DB, letto con le stesse due letture della base view
#       (`ordinamento_risolto`, `misura_risolta`), per lo stesso utente. Lo
#       smoke non prova la regola del preset (la provano i pgTAP di `ui`): prova
#       che la risposta la porti fino al FE.
#       ⭐ Le rotte vengono da `rotte_servite` (BB): una lista nuova entra nel
#       giro da sola. Le rotte con parametri si risolvono dalla lista madre
#       (il prefisso della rotta): le prime righe della madre danno l'id.
#       ⚠️ I SALTI SONO COPERTURA ZERO, e si contano: una rotta che non si
#       raggiunge (madre assente o vuota), che non ha righe o che non porta il
#       campo ordinato e' «SKIP» col motivo, e il riepilogo li somma.
#       ⚠️ L'ordine dei TESTI si confronta senza maiuscole e accenti, che e'
#       un'approssimazione della collation del DB: un'inversione lì e' un
#       AVVISO da guardare, non un FAIL. Numeri e date si confrontano esatti.
#       I vuoti (`null`) non si giudicano: dove va il vuoto quando una lista
#       ordina e' una decisione ancora aperta (brief DB del 2026-11-24).
#       ⛔ Solo letture (GET), che il BE fa girare in sola lettura.
#       Uso: lo lancia lo smoke bash, non si lancia da solo. Il trattino basso
#       lo tiene fuori dalla scoperta di `smoke-baseline.sh`.
#       Filtro facoltativo: `PARTENZA_FILTRO=<testo>` prova solo le rotte o le
#       liste che lo contengono.
# ------------------------------------------------------------

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.api.rotte import rotte_servite
from apps.core.services.ordinamento_di_partenza import misura_risolta, ordinamento_risolto

TOKEN = os.environ.get("PARTENZA_TOKEN", "").strip()
FILTRO = os.environ.get("PARTENZA_FILTRO", "").strip()
PARAMETRO = re.compile(r"<(?:\w+:)?(\w+)>")
# Quante righe della madre si provano per trovare una lista figlia con righe.
CANDIDATI_MADRE = 3

conteggi = {"OK": 0, "FAIL": 0, "SKIP": 0, "AVVISO": 0}


def esito(tipo: str, lista: str, percorso: str, dettaglio: str) -> None:
    conteggi[tipo] += 1
    etichetta = {"OK": "OK  ", "FAIL": "FAIL", "SKIP": "SKIP", "AVVISO": "AVVISO"}[tipo]
    print(f"  {etichetta} {lista}  /{percorso} — {dettaglio}")


if not TOKEN:
    print("  Setup fallito: nessun token (PARTENZA_TOKEN). Lo lancia smoke-test-ui-partenza-liste.sh.")
    sys.exit(1)

utente = get_user_model().objects.get(pk=AccessToken(TOKEN)["user_id"])
client = Client(HTTP_AUTHORIZATION=f"Bearer {TOKEN}", HTTP_HOST="localhost")


# Scopo: una GET come la fa il FE; rende (status, corpo JSON o None).
def chiedi(url: str, **query: Any) -> tuple[int, Any]:
    risposta = client.get("/" + url, query, secure=True)
    try:
        return risposta.status_code, json.loads(risposta.content or b"null")
    except ValueError:
        return risposta.status_code, None


# Scopo: le righe e il totale di una risposta di lista, qualunque sia la forma
#        (`data` elenco, `data.results` + `count`, o il primo elenco di oggetti
#        dentro `data`). (None, None) se non e' una lista.
def righe_di(corpo: Any) -> tuple[list[dict] | None, int | None]:
    dati = corpo.get("data") if isinstance(corpo, dict) else None
    if isinstance(dati, list):
        return dati, None
    if isinstance(dati, dict):
        totale = dati.get("count") if isinstance(dati.get("count"), int) else None
        if isinstance(dati.get("results"), list):
            return dati["results"], totale
        for valore in dati.values():
            if isinstance(valore, list) and (not valore or isinstance(valore[0], dict)):
                return valore, totale
    return None, None


# Scopo: la chiave approssimata di un testo: senza accenti, maiuscole, spazi e
#        punteggiatura, che la collation del DB non pesa al primo livello
#        («ACIREALE» prima di «ACI SANT'ANTONIO»).
def _senza_accenti(testo: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", testo).casefold()
        if c.isalnum() and not unicodedata.combining(c)
    )


def _data(valore: str) -> datetime | None:
    try:
        return datetime.fromisoformat(valore.replace("Z", "+00:00"))
    except ValueError:
        return None


# Scopo: la chiave di confronto dei valori di una colonna, e se e' esatta.
#        Numeri (anche come stringa) e date: esatta. Testi: approssimata.
def chiave_di(valori: list[Any]) -> tuple[Any, bool]:
    if all(isinstance(v, bool) for v in valori):
        return (lambda v: v), True
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in valori):
        return (lambda v: v), True
    if all(isinstance(v, str) for v in valori):
        try:
            [Decimal(v) for v in valori]
            return Decimal, True
        except InvalidOperation:
            pass
        date = [_data(v) for v in valori]
        if all(d is not None for d in date) and all(re.match(r"\d{4}-\d{2}-\d{2}", v) for v in valori):
            con_fuso = {d.tzinfo is not None for d in date}
            if len(con_fuso) == 1:
                return _data, True
        return _senza_accenti, False
    return str, False


# Scopo: la prima inversione dell'ordine in `righe` sul campo, o None.
#        Rende (None, esatta) se l'ordine regge.
def inversione(righe: list[dict], campo: str, verso: str) -> tuple[str | None, bool]:
    valori = [r.get(campo) for r in righe if r.get(campo) is not None]
    if len(valori) < 2:
        return None, True
    chiave, esatta = chiave_di(valori)
    for a, b in zip(valori, valori[1:], strict=False):
        ka, kb = chiave(a), chiave(b)
        if (verso == "asc" and ka > kb) or (verso == "desc" and ka < kb):
            return f"{a!r} prima di {b!r}", esatta
    return None, esatta


rotte = rotte_servite()
percorsi_get = {r.percorso for r in rotte if r.view is not None and hasattr(r.view, "get")}


# Scopo: le URL concrete di un percorso con parametri. Si risolve l'ULTIMO
#        parametro dalla lista madre (il pattern fino a quel parametro, che
#        porta i parametri precedenti e si risolve allo stesso modo). Rende al
#        piu' CANDIDATI_MADRE URL, oppure ([], motivo).
# ⚠️ Il valore e' l'`id` della riga madre, e solo se manca il campo col nome
#    del parametro: una riga di DDT porta anche un `sorgente_id`, che e' un'altra
#    cosa dal `<sorgente_id>` della rotta dei documenti.
def concrete(percorso: str) -> tuple[list[str], str]:
    parametri = list(PARAMETRO.finditer(percorso))
    if not parametri:
        return [percorso], ""
    m = parametri[-1]
    madre = percorso[: m.start()]
    if madre not in percorsi_get:
        return [], f"la lista madre /{madre} non e' una rotta GET"
    madri, motivo = concrete(madre)
    if not madri:
        return [], motivo
    risultato: list[str] = []
    for url_madre in madri:
        status, corpo = chiedi(url_madre, limit=CANDIDATI_MADRE)
        if status == 400:
            status, corpo = chiedi(url_madre)
        righe, _ = righe_di(corpo) if status == 200 else (None, None)
        for riga in (righe or [])[:CANDIDATI_MADRE]:
            valore = riga.get("id", riga.get(m.group(1)))
            if valore is not None:
                risultato.append(url_madre + str(valore) + percorso[m.end():])
        if len(risultato) >= CANDIDATI_MADRE:
            break
    if not risultato:
        return [], f"la lista madre /{madre} non da' righe (con «id» o «{m.group(1)}»)"
    return risultato[:CANDIDATI_MADRE], ""


def prova(percorso: str, lista: str) -> None:
    urls, motivo = concrete(percorso)
    if not urls:
        esito("SKIP", lista, percorso, f"non raggiunta: {motivo}")
        return
    # Fra le URL concrete, la prima con almeno due righe: l'ordine si vede.
    scelta = None
    for url in urls:
        status, corpo = chiedi(url)
        righe, totale = righe_di(corpo) if status == 200 else (None, None)
        if scelta is None or (righe is not None and len(righe) >= 2):
            scelta = (url, status, corpo, righe, totale)
        if righe is not None and len(righe) >= 2:
            break
    assert scelta is not None
    url, status, corpo, righe, totale = scelta

    if status != 200:
        errore = (corpo or {}).get("error") or {} if isinstance(corpo, dict) else {}
        dettaglio = f"HTTP {status} {errore.get('code') or ''} {errore.get('message') or ''}".strip()
        # Un 400 alla prima apertura e' una lista che vuole un filtro per
        # contratto (la competenza, l'articolo): il FE lo manda, lo smoke no.
        if status == 400:
            esito("SKIP", lista, url, f"{dettaglio} — vuole un filtro, da provare a video")
        else:
            esito("FAIL", lista, url, f"{dettaglio} alla prima apertura")
        return
    if righe is None:
        esito("FAIL", lista, url, "la risposta non e' una lista riconoscibile")
        return

    voci = ordinamento_risolto(lista, user=utente)
    prima = next((v for v in voci if v.get("campo_sorgente")), None)
    misura = misura_risolta(lista, user=utente)
    meta = (corpo.get("meta") or {}).get("ordinamento")
    difetti: list[str] = []
    note: list[str] = []
    salti: list[str] = []

    # 2. l'intestazione: meta.ordinamento == la prima voce del DB
    if prima is None:
        if meta:
            difetti.append(f"meta.ordinamento {meta} senza un ordinamento nel preset")
        else:
            note.append("senza ordinamento nel preset (intestazione spenta, default del repository)")
    else:
        atteso = {"order_by": prima["campo_sorgente"], "order_dir": prima["dir"], "col": prima["col"]}
        if meta != atteso:
            difetti.append(
                f"meta.ordinamento {meta} invece di {atteso}"
                + (" (proposta rifiutata dal repository? vedi il log)" if not meta else "")
            )
        else:
            note.append(f"{prima['col']} {prima['dir']}")

    # 3. la misura
    n = len(righe)
    atteso_n = min(misura, totale) if totale is not None else None
    if n > misura:
        difetti.append(f"{n} righe oltre la misura {misura}")
    elif atteso_n is not None and n != atteso_n:
        difetti.append(f"{n} righe su {totale}, la misura e' {misura} (tetto della view?)")
    note.append(f"misura {misura}, righe {n}" + (f"/{totale}" if totale is not None else ""))

    # 4-5. l'ordine, e il clic
    if prima is not None and meta == {"order_by": prima["campo_sorgente"], "order_dir": prima["dir"], "col": prima["col"]}:
        campo = next((c for c in (prima["campo_sorgente"], prima["col"]) if any(c in r for r in righe)), None)
        if n < 2:
            salti.append("meno di due righe: ordine non verificato")
        elif campo is None:
            salti.append(f"le righe non portano «{prima['campo_sorgente']}» né «{prima['col']}»: ordine non verificato")
        else:
            inv, esatta = inversione(righe, campo, prima["dir"])
            if inv:
                (difetti if esatta else note).append(f"ordine {prima['dir']} su «{campo}» rotto: {inv}"
                                                     + ("" if esatta else " (AVVISO: testo, collation?)"))
                if not esatta:
                    conteggi["AVVISO"] += 1
            stesso = chiedi(url, order_by=prima["campo_sorgente"], order_dir=prima["dir"])
            if stesso[0] != 200 or righe_di(stesso[1])[0] != righe:
                difetti.append("il clic sulla stessa colonna e verso non da' le stesse righe")
            opposto_dir = "desc" if prima["dir"] == "asc" else "asc"
            opposto = chiedi(url, order_by=prima["campo_sorgente"], order_dir=opposto_dir)
            if opposto[0] != 200:
                difetti.append(f"il clic col verso {opposto_dir}: HTTP {opposto[0]}")
            else:
                inv2, esatta2 = inversione(righe_di(opposto[1])[0] or [], campo, opposto_dir)
                if inv2 and esatta2:
                    difetti.append(f"il clic col verso {opposto_dir} non rovescia: {inv2}")

    if difetti:
        esito("FAIL", lista, url, "; ".join(difetti + note))
    elif salti:
        esito("SKIP", lista, url, "; ".join(note + salti))
    else:
        esito("OK", lista, url, "; ".join(note))


da_provare = sorted(
    {
        (r.percorso, r.view.lista_codice)
        for r in rotte
        if r.view is not None
        and getattr(r.view, "lista_codice", None)
        and hasattr(r.view, "get")
        and not r.percorso.endswith("export/")
        and (not FILTRO or FILTRO in r.percorso or FILTRO in r.view.lista_codice)
    },
    key=lambda c: (c[1], c[0]),
)
export = sum(1 for r in rotte if r.view is not None and getattr(r.view, "lista_codice", None)
             and r.percorso.endswith("export/"))

print(f"Utente: {utente.username} · rotte di lista: {len(da_provare)} · export fuori dal giro: {export}")
print("(gli export hanno la stessa lista della rotta base: test_export_lista_codice_pari)")
for percorso, lista in da_provare:
    try:
        prova(percorso, lista)
    except Exception as exc:  # uno smoke dice dove si e' rotto e va avanti
        esito("FAIL", lista, percorso, f"eccezione {type(exc).__name__}: {exc}")

print("")
print(f"Risultato: {conteggi['OK']} OK, {conteggi['FAIL']} FAIL, {conteggi['SKIP']} SKIP, "
      f"{conteggi['AVVISO']} AVVISI")
sys.exit(1 if conteggi["FAIL"] else 0)
