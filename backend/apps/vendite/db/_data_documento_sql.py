# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I due frammenti SQL della DATA DOCUMENTO che servono a piu' chiamanti,
#        in un posto solo: «la data che i documenti ancora da numerare portano
#        oggi» e «quali lotti l'atto di numerazione toccherebbe».
# ------------------------------------------------------------

# PERCHE' ESISTE (regola del 2, cantiere numerazione 2026-08-25). Gli stessi due
# predicati servono a chiamanti che stanno in DUE moduli diversi e che devono
# raccontare la stessa cosa:
#
#   VenditeRepository.list_lotti_numerabili
#       → ORDINA i lotti per data documento, cosi' i numeri escono in ordine di
#         data e il cancello di `fn_get_next_progressivo` non deve intervenire;
#   VenditePipelineRepository.get_data_documento_corrente
#       → dice al dialog DA QUALE data i documenti stanno per spostarsi;
#   VenditePipelineRepository.get_data_minima_numerabile_competenza
#       → calcola il pavimento sui lotti che l'atto toccherebbe DAVVERO.
#
# ⚠️ Scritti due volte, il giorno in cui uno cambia il dialog dice «i documenti
# portano il 03/08» e il giro li numera in un altro ordine — e nessun test lo
# intercetta, perche' ognuna delle copie e' coerente con se' stessa. E' la
# stessa classe di divergenza di `_coda_documento_filtro`.
#
# ⛔ NON e' una regola di dominio: e' la LETTURA di una regola che vive nel DB.
# Il pavimento vero lo calcola `vendite.fn_get_data_minima_numerabile_lotto`, e
# nessuno lo ricopia qui — quello che sta qui e' solo «quali righe guardare».

# Scopo: la data piu' VECCHIA fra i documenti di un lotto che non hanno ancora
#        un numero — quella che il cancello incontrera' per prima. Si compone
#        come sotto-query correlata su un alias esterno del lotto.
# ⚠️ `min` e non `max`: se il lotto contiene documenti di date diverse, quello
#    che rischia il rifiuto e' il piu' vecchio.
# ⚠️ Il filtro e' `numero IS NULL` e non lo stato: una fattura viene numerata
#    MENTRE e' in EMESSA, quindi una soglia per stato includerebbe una gia'
#    numerata — la cui data non e' piu' in gioco. Stesso criterio di
#    `vendite.fn_get_data_minima_numerabile_lotto`.
# `{lotto}` = alias/espressione dell'id del lotto nel contesto del chiamante.
SQL_DATA_DOCUMENTO_CORRENTE = """
    SELECT min(f_dd.data)
      FROM vendite.fatturazione_lotti_fatture lf_dd
      JOIN vendite.fatture f_dd ON f_dd.id = lf_dd.fattura_id
     WHERE lf_dd.lotto_id = {lotto}
       AND f_dd.numero IS NULL
"""

# Scopo: i lotti che l'atto di numerazione toccherebbe davvero, nelle sue DUE
#        forme — «tutti quelli di un mese» oppure «questi qui».
#
# ⚠️ Deve restare la stessa domanda per tutti e tre i chiamanti: un pavimento
#    calcolato su un insieme diverso da quello che verra' numerato sarebbe un
#    suggerimento sbagliato — piu' alto o piu' basso, ma comunque un'altra
#    domanda.
#
# ⛔ RESTITUISCE SQL **E** PARAMETRI INSIEME, e non e' pignoleria: finche' erano
#    due cose separate — un `format()` qui e una lista di parametri scritta dal
#    chiamante — l'ordine dei segnaposto e quello dei valori erano due verita'
#    da tenere allineate a mano. Su una query con due perimetri e' esattamente
#    l'errore che e' gia' successo (2026-08-26, cantiere facet): invertiti, non
#    danno errore — confrontano il valore sbagliato e tornano numeri
#    plausibili.
#
# ⛔ LO STATO SI APPLICA SEMPRE, anche sulla forma a lista. Un lotto scelto a
#    mano dall'operatore non e' per questo numerabile: se non e' EMESSA, l'atto
#    non deve toccarlo. La selezione decide il PERIMETRO, non le regole — e
#    l'interfaccia che spegne la casella e' una comodita', non un presidio.
#
# ⛔ Guard su lista VUOTA. `= ANY('{}')` non trova niente e l'atto risponderebbe
#    «nessun lotto da numerare»: un errore di chiamante uscirebbe travestito da
#    dato. Chi non ha selezionato nulla non deve arrivare fin qui.
#
# `lotti_alias` = alias della tabella `vendite.fatturazione_lotti` nel contesto
# del chiamante.
def costruisci_perimetro_lotti_numerabili(
    *,
    lotti_alias: str,
    # `| None`: l'assenza la rifiuta il guard qui sotto, con la frase che la nomina.
    stato_doc_fiscale_id: int | None,
    competenza_mese=None,
    lotti_ids=None,
) -> tuple[str, list]:
    # ⛔ Lo stato e' OBBLIGATORIO su entrambe le forme: senza, il perimetro
    #    diventa «tutti i lotti» invece che «quelli che l'atto numera». Niente
    #    `or 0` — normalizzare in silenzio un parametro mancante e' il modo in
    #    cui una risposta sbagliata sembra una risposta.
    if not stato_doc_fiscale_id:
        raise ValueError(
            "perimetro dei lotti numerabili: `stato_doc_fiscale_id` "
            "obbligatorio (e' cio' che distingue i lotti numerabili dagli altri)."
        )
    if (competenza_mese is None) == (lotti_ids is None):
        raise ValueError(
            "perimetro dei lotti numerabili: indicare `competenza_mese` OPPURE "
            f"`lotti_ids`, non entrambi ne' nessuno dei due "
            f"(competenza_mese={competenza_mese!r}, lotti_ids={lotti_ids!r})."
        )
    if lotti_ids is not None:
        ids = [int(x) for x in lotti_ids]
        if not ids:
            raise ValueError(
                "perimetro dei lotti numerabili: `lotti_ids` e' vuoto. Un "
                "perimetro senza lotti non e' «niente da numerare», e' una "
                "chiamata sbagliata."
            )
        return (
            f"{lotti_alias}.id = ANY(%s)\n    AND {lotti_alias}.stato_doc_fiscale_id = %s",
            [ids, int(stato_doc_fiscale_id)],
        )
    return (
        f"{lotti_alias}.competenza_mese = %s\n    AND {lotti_alias}.stato_doc_fiscale_id = %s",
        [competenza_mese, int(stato_doc_fiscale_id)],
    )
