# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

# Separatore che, dentro `segment_key`, marca una riga come componente di kit:
#   padre:      ORD:<uid>:R:<riga>
#   componente: ORD:<uid>:R:<riga>#CMP:<articolo_componente_uid>
# Il prefisso a sinistra identifica l'ISTANZA di kit, non l'articolo: lo stesso
# kit puo' comparire due volte sulla stessa fattura da righe sorgente diverse.
SEP_COMPONENTE = "#CMP:"

# Chiavi `meta` del contratto. Il push le risolve una volta sola: a valle non
# si risale mai alla distinta base, perche' lo stesso componente puo'
# appartenere a piu' kit e solo il documento sorgente sa quale e' stato venduto.
META_KEY_COMPONENTE_DI = "componente_di"
META_KEY_ESPOSTO_IN_FATTURA = "esposto_in_fattura"
META_KEY_SEGMENT_KEY = "segment_key"
META_KEY_COEFF_QTA = "coeff_qta"


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
