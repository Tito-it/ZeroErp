# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i service di `pagamenti` condividono — i codici del
#        dominio e l'involucro paginato.
# Note: Nati dentro `pagamenti_service`, spostati qui alla SECONDA occorrenza
#       (il giro delle sistemazioni). ⛔ Non e' un building block di progetto:
#       e' materiale interno di questo dominio, e sta qui perche' importare i
#       nomi privati di un altro modulo e' un legame che non regge il primo
#       riordino.
#       ⭐ La lettura di un importo (`decimal_da_payload`) NON sta piu' qui
#       (2026-09-18): era la prima di cinque copie nel progetto ed e' diventata
#       `PayloadValidator.require_decimal` / `optional_decimal` in core — con
#       lo stesso rigore (bool e NaN rifiutati), per tutti.
# ------------------------------------------------------------


# Codice di validazione del payload di questo dominio. ⭐ Seminato dal team DB
# il 2026-08-25 su richiesta del backend: fino ad allora si usava il generico
# `E_VALIDATION_INPUT`.
# ⚠️ Il nome e' `..._VALIDATION` (come `E_VENDITE_VALIDATION`), non
# `..._VALIDAZIONE`: il catalogo tiene le due forme e questa e' quella scelta.
E_VALIDAZIONE = "E_PAGAMENTI_VALIDATION"

# La fattura indicata non c'e' — o il perimetro non la lascia vedere, e i due
# restano volutamente indistinguibili. ⭐ A catalogo (NON_TROVATO, 404); e'
# il codice che i tre service del dominio sollevano da se' quando leggono un
# documento per id: era scritto in ognuno dei tre, e una stringa ripetuta e'
# gia' divergente il giorno in cui una delle copie cambia.
E_FATTURA_NON_TROVATA = "E_FATTURA_NON_TROVATA"

# La rata indicata non c'e' — o il perimetro non la lascia vedere. ⭐ A catalogo
# (NON_TROVATO, 404). Stava in `saldi_service` finche' era l'unico a sollevarla;
# dal 2026-09-17 la solleva anche «righe da rate» (`pagamenti_service`), e una
# stringa ripetuta e' gia' divergente il giorno in cui una delle copie cambia.
E_RATA_NON_TROVATA = "E_RATA_NON_TROVATA"
