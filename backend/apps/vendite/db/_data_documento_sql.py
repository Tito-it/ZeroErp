# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

# Scopo: i lotti che l'atto «Rendi definitive competenza» numererebbe davvero.
# ⚠️ Deve restare identico al `WHERE` di `list_lotti_numerabili`: un pavimento
#    calcolato su un insieme diverso da quello che verra' numerato sarebbe un
#    suggerimento sbagliato — piu' alto o piu' basso, ma comunque un'altra
#    domanda. `{lotti}` = alias della tabella `vendite.fatturazione_lotti`.
SQL_PERIMETRO_LOTTI_NUMERABILI = """
    {lotti}.competenza_mese = %s
    AND {lotti}.stato_doc_fiscale_id = %s
"""
