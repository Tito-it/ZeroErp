# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Contratto condiviso dello snapshot kit che viaggia da push commessa
#        a riga di fattura (`segment_key` + chiavi `meta`).
# ------------------------------------------------------------

# PERCHE' ESISTE. La parentela padre/componente di un kit non ha colonne
# dedicate: vive dentro la stringa `segment_key` e dentro tre chiavi del `meta`.
# Il contratto ha due estremi lontani fra loro —
#   scrittura: `BoMComponentExpander` (commesse_source_handlers), al push;
#   lettura:   `FattureRigheService`, alla generazione delle righe fattura —
# e in mezzo passa per commesse_attivita e attivita_fatturabili senza che nulla
# lo verifichi. Con i literal ripetuti ai due capi, un refuso da una parte
# produce righe che non si agganciano al kit e spariscono dall'esposizione in
# fattura *senza un errore*: la vista `vw_fattura_righe_esposte` le tratta come
# righe normali e i totali tornano lo stesso.
# Vedi brief-fix-importi-riga-fattura-zero §4.7-bis (D5).

from decimal import Decimal, InvalidOperation
from typing import Any

# Separatore che, dentro `segment_key`, marca una riga come componente di kit:
#   padre:      ORDINE_VENDITA:<uid>:R:<riga>
#   componente: ORDINE_VENDITA:<uid>:R:<riga>#CMP:<articolo_componente_uid>
# ⭐ La chiave del padre la costruisce il DB (`script.fn_segment_key`, dal
#    2026-10-20 col codice della sorgente nel prefisso: era `ORD:`, G-8 di
#    brief-db-grammatica-unica-documenti) e arriva dal lister: qui si APPENDE
#    solo il suffisso, e non si legge mai il prefisso.
# Il prefisso a sinistra identifica l'ISTANZA di kit, non l'articolo: lo stesso
# kit puo' comparire due volte sulla stessa fattura da righe sorgente diverse.
SEP_COMPONENTE = "#CMP:"

# Chiavi `meta` del contratto. Il push le risolve una volta sola: a valle non
# si risale mai alla distinta base, perche' lo stesso componente puo'
# appartenere a piu' kit e solo il documento sorgente sa quale e' stato venduto.
META_KEY_COMPONENTE_DI = "componente_di"
# Il modo di esposizione in fattura: un CODICE di `config.esposizioni_componente`
# (NASCOSTO / DESCRITTIVO / VALORIZZATO), letto dalla distinta al push e
# congelato su `fatture_righe.kit_esposizione`. Fino al 2026-10-01 era il
# booleano `esposto_in_fattura` (brief-db-esposizione-componenti-kit-in-fattura).
META_KEY_ESPOSIZIONE = "esposizione"
META_KEY_SEGMENT_KEY = "segment_key"
META_KEY_COEFF_QTA = "coeff_qta"
# Quantita' e UoM della RIGA PADRE del documento sorgente, congelate al push e
# copiate su `fatture_righe.kit_qta` / `kit_uom_id` (dal 2026-10-02,
# brief-db-bom-flag-quantita-e-kit-in-fattura R-BE-B2). Prima la fattura le
# ricavava dai componenti — `avg(qta)` e `max(uom_id)` —, cioe' una media fra
# metri, pezzi e ore e un'unita' a caso su un kit misto.
# ⚠️ La quantita' e' quella che l'attivita' rappresenta, col SUO segno: su una
#    rettifica e' negativa come la quantita' del componente (D-NC-2).
META_KEY_QTA_PADRE = "qta_padre"
META_KEY_UOM_PADRE = "uom_padre_id"

# Il modo quando la chiave manca: lo stesso DEFAULT della colonna
# `articoli_componenti.esposizione_in_fattura`, e la stessa lettura della
# correzione una tantum del meta vecchio (chiave assente -> NASCOSTO). Non e'
# una copia del vocabolario: i valori ammessi li giudica la FK su
# `fatture_righe.kit_esposizione`, e un codice sconosciuto si ferma li'.
ESPOSIZIONE_DEFAULT = "NASCOSTO"


# Scopo: Il modo di esposizione di un valore letto (meta o distinta). Assente
#        o vuoto -> il default; altrimenti il codice com'e', senza giudicarlo.
def esposizione_o_default(valore: object) -> str:
    if valore is None:
        return ESPOSIZIONE_DEFAULT
    testo = str(valore).strip()
    return testo or ESPOSIZIONE_DEFAULT


# Scopo: La quantita' padre scritta nel meta, come `Decimal`; None se la chiave
#        manca o non e' un numero. Il push la scrive come stringa canonica, la
#        correzione una tantum come stringa SQL: si leggono entrambe.
#        ⛔ Nessun ripiego qui: decidere che fare dell'assenza e' del chiamante.
def qta_padre_da_meta(meta: dict[str, Any]) -> Decimal | None:
    valore = meta.get(META_KEY_QTA_PADRE)
    if valore is None or isinstance(valore, bool):
        return None
    try:
        numero = Decimal(str(valore).strip())
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


# Scopo: La UoM padre scritta nel meta, come intero; None se manca o non e' un
#        intero.
def uom_padre_da_meta(meta: dict[str, Any]) -> int | None:
    valore = meta.get(META_KEY_UOM_PADRE)
    if valore is None or isinstance(valore, bool):
        return None
    try:
        return int(str(valore).strip())
    except ValueError:
        return None


# Scopo: Compone il `segment_key` di un componente a partire da quello del
#        padre. Unico punto in cui il suffisso viene costruito.
def segment_key_componente(segment_key_padre: str, componente_id: object) -> str:
    return f"{segment_key_padre}{SEP_COMPONENTE}{componente_id}"


# Scopo: Vero se il `segment_key` descrive un componente di kit.
def is_segment_componente(segment_key: object) -> bool:
    return isinstance(segment_key, str) and SEP_COMPONENTE in segment_key


# Scopo: Estrae dal `segment_key` di un componente la chiave dell'istanza di
#        kit (il prefisso a sinistra del separatore). None se non e' un
#        componente.
def kit_key_da_segment(segment_key: object) -> str | None:
    if not is_segment_componente(segment_key):
        return None
    assert isinstance(segment_key, str)
    return segment_key.split(SEP_COMPONENTE, 1)[0]
