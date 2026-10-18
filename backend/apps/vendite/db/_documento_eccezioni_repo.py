# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le letture del DB comuni ai due documenti di vendita con listino ed
#        eccezioni (contratto, offerta commerciale): la versione di listino che
#        li governa, le combinazioni erogazione/fonte di una riga e la scheda
#        di fornitura che l'anagrafica da' a un cliente.
# Note: brief-db-offerta-emissione-ed-erogazione (§C.6.4, §C.9.6), 2026-10-07;
#       la scheda: brief-db-indirizzi-documento-seguono-il-cliente (R-BE-5).
# ------------------------------------------------------------

# PERCHE' ESISTE (regola del 2). Le due domande hanno la stessa risposta sui due
# documenti, e il DB la da' con UNA funzione che prende il documento come
# selettore (`p_documento` = 'CONTRATTO' | 'OFFERTA_COMMERCIALE', i codici di
# `config.sorgenti`). Il backend la legge una
# volta sola, qui; i due service la chiamano col proprio selettore.
#
# ⛔ NON sono regole di dominio: sono le LETTURE di regole che vivono nel DB.
#   · la versione di listino: `vendite.fn_documento_listino_operativo` — la
#     fissata se c'e', altrimenti quella in vigore oggi. La stessa che governa
#     le righe a video e che i guard congelano all'emissione dell'offerta e
#     all'attivazione del contratto. Fino al 2026-10-07 ne vivevano due copie in
#     Python (`ListiniRepository.get_versione_attiva_alla_data`,
#     `ContrattiRepository.get_listino_versione_attiva_alla_data`), gia'
#     divergenti dal DB: cercavano la versione alla data d'inizio del
#     documento, le righe quella di oggi;
#   · le combinazioni: `vendite.fn_documento_riga_erogazioni` — quelle che una
#     riga con quell'articolo puo' avere, col default che erediterebbe. Prende il
#     posto della matrice ricopiata nel frontend (`fontiQuantitaErogazione.js`) e
#     in `contratti_service` (`_FONTE_VIETATE_PER_TIPO_EROGAZIONE`).

from typing import Any, Literal

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list

# Il selettore del DB: i due documenti con listino ed eccezioni, coi codici di
# `config.sorgenti` (brief-db-grammatica-unica-documenti, lotto 1: il DB rifiuta
# `OFFERTA` con E_DOC_TIPO_NON_GESTITO). I chiamanti passano le costanti di
# `apps.config.sorgenti`, che sono `Final`: mypy le confronta con questo elenco.
DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA_COMMERCIALE"]


# Scopo: La versione di listino che governa il documento: quella fissata se
#        c'e', altrimenti quella in vigore oggi; None senza listino, senza
#        versione in vigore, o se il documento non c'e' (o non si vede).
def listino_versione_operativa(
    documento: DocumentoEccezioni, documento_id: int,
) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT listino_versione_id"
            "  FROM vendite.fn_documento_listino_operativo(%s, %s)",
            [documento, int(documento_id)],
        )
        row = cursor.fetchone()
    if not row or row[0] is None:
        return None
    return int(row[0])


# Scopo: Le combinazioni (tipo_erogazione, fonte_quantita_attesa) che una riga
#        con questo articolo puo' avere sul documento, col default in testa
#        (`e_default`), la `generazione_canone` da proporre sulle CANONE e
#        l'`origine` (TIPOLOGIA | NATURA | DISTINTA). Lista vuota se la
#        tipologia dell'articolo e' fuori dalla utility del documento, o se
#        documento o articolo non si vedono: chi chiama verifica PRIMA il
#        documento, cosi' «non lo vedi» resta un 404 e non una lista vuota.
def list_erogazioni_riga(
    documento: DocumentoEccezioni, documento_id: int, articolo_id: str,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tipo_erogazione, fonte_quantita_attesa, e_default,
                   generazione_canone, origine
              FROM vendite.fn_documento_riga_erogazioni(%s, %s, %s::uuid)
            """,
            [documento, int(documento_id), str(articolo_id)],
        )
        return rows_to_list(cursor)


# Scopo: La scheda di fornitura che l'anagrafica da' alla coppia (istanza,
#        utility): `vendite.fn_get_fornitura_da_anagrafica`, la sede unica che
#        scrive anche il BB della nascita del contratto e del cambio di cliente
#        in bozza (D-5, D-7 di Tid). Il drawer la mostra PRIMA della creazione,
#        perche' l'operatore veda cosa verra' scritto e lo corregga.
#        None = la coppia non ha dati precontrattuali (zero righe; al piu' una
#        per `uq_istanze_dati_precontrattuali_id_utility_id`).
# ⛔ Nessuna copia della derivazione qui (tipo d'uso dalla classe): la fa il DB.
#    La coppia NULL il DB la rifiuta (`E_DOC_FORNITURA_PARAMETRO_MANCANTE`):
#    chi chiama la passa intera.
def fornitura_da_anagrafica(istanza_utility_id: int, utility_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT istanza_dati_precontrattuali_id, classe_utenza_id, tipo_utenza_id,
                   param_1_num, param_2_txt, meta
              FROM vendite.fn_get_fornitura_da_anagrafica(%s, %s)
            """,
            [int(istanza_utility_id), int(utility_id)],
        )
        return row_to_dict(cursor)
