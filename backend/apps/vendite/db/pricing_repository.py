# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per il resolver prezzi v5 (pricing v5). Wrapper su
#        `vendite.fn_resolve_prezzo_listino_v2` (resolver 3 stadi
#        bundle-aware). Gli errori di dominio sollevati dalle funzioni via
#        script.fn_log_and_raise_error (P0001) vengono propagati al service
#        che li traduce in ServiceError.
#        Note: il legacy `vendite.fn_resolve_prezzo_composito` (BoM ibrido
#        A/B1/B2 pre-modello-unificato) e' stato rimosso dal Python con
#        cleanup 2026-05-14. DROP DB pendente (brief in work-in-progress).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_manager import ErrorManager

# Invariante rotta: il nucleo deve restituire SEMPRE una riga. Il codice sta qui
# e non in `pricing_service` perche' e' il repository a poterlo constatare —
# e non si importa dal service, che importa questo modulo (ciclo).
E_VENDITE_PRICING_ESITO_ASSENTE = "E_VENDITE_PRICING_ESITO_ASSENTE"


# ── SQL condiviso dai due resolver ────────────────────────────────────────
# ⭐ Estratto il 2026-08-19 alla SECONDA occorrenza (regola del 2): guscio e
#    nucleo hanno la STESSA decorazione — 22 colonne e 6 LEFT JOIN identici —
#    e differiscono solo per la funzione chiamata e per le tre colonne di
#    esito. Tenerne due copie significa che la settima colonna decorata la
#    aggiunge qualcuno a una sola delle due, e il difetto si vede in un
#    dominio e non nell'altro.

# Le colonne che decorano gli id con codice/descrizione. Single round-trip:
# la funzione DB resta la sola source-of-truth, il JOIN espone i display.
_COLONNE_DECORATE = """
                    r.prezzo_finale,
                    r.prezzo_base_snapshot,
                    r.tipo_variazione_applicata,
                    r.valore_variazione_applicata,
                    r.origine,
                    r.listino_id,
                    l.codice                AS listino_codice,
                    l.descrizione           AS listino_descrizione,
                    r.listino_versione_id,
                    lv.codice_versione      AS listino_versione_codice,
                    r.listino_riga_id,
                    r.contratto_id,
                    c.numero                AS contratto_numero,
                    r.promo_id,
                    pa.codice               AS promo_codice,
                    pa.descrizione          AS promo_descrizione,
                    r.categoria_cliente_listino_id,
                    r.categoria_cliente_id_snapshot,
                    cc.codice               AS categoria_cliente_codice,
                    cc.descrizione          AS categoria_cliente_descrizione,
                    r.classe_utenza_id_snapshot,
                    clu.descrizione         AS classe_utenza_descrizione"""

# Le tre colonne che SOLO il nucleo espone: il prezzo puo' non esserci, e
# `esito_codice` dice perche'.
_COLONNE_ESITO = """,
                    r.esito_codice,
                    r.esito_context,
                    r.esito_valori"""

_JOIN_DECORAZIONE = """
                  LEFT JOIN vendite.listini l
                    ON l.id = r.listino_id
                  LEFT JOIN vendite.listini_versioni lv
                    ON lv.id = r.listino_versione_id
                  LEFT JOIN vendite.contratti c
                    ON c.id = r.contratto_id
                  LEFT JOIN vendite.promo_articoli pa
                    ON pa.id = r.promo_id
                  LEFT JOIN anagrafiche.categorie_clienti cc
                    ON cc.id = r.categoria_cliente_id_snapshot
                  LEFT JOIN config.classi_utenze clu
                    ON clu.id = r.classe_utenza_id_snapshot"""


# Scopo: la query decorata per uno dei due resolver.
#        ⚠️ `funzione` e' interpolata nel testo SQL, e puo' esserlo perche' e'
#        una COSTANTE DI QUESTO MODULO: non arriva da payload, query string o
#        database. Se un giorno diventasse un parametro esterno, questa riga
#        sarebbe una SQL injection — e questo commento e' il posto in cui
#        accorgersene.
def _sql_resolver(funzione: str, *, con_esito: bool) -> str:
    colonne = _COLONNE_DECORATE + (_COLONNE_ESITO if con_esito else "")
    return f"""
                SELECT{colonne}
                  FROM {funzione}(
                           %s::uuid, %s, %s, %s, %s, %s, %s, %s::uuid, %s::bigint
                       ) r{_JOIN_DECORAZIONE}
                """


# Scopo: i nove argomenti posizionali, nell'ordine che la funzione pretende.
#        Erano scritti due volte: due elenchi di nove elementi in cui invertire
#        due posizioni non da' errore di sintassi, da' un prezzo sbagliato.
def _argomenti_resolver(
    *,
    articolo_id: UUID | str,
    uom_id: int,
    data_riferimento: date,
    ba_id: int,
    utility_id: int,
    emittente_soggetto_ruolo_id: int,
    classe_utenza_id: int | None,
    articolo_padre_contesto: UUID | str | None,
    listino_versione_id_preferito: int | None,
) -> list[Any]:
    return [
        str(articolo_id),
        uom_id,
        data_riferimento,
        ba_id,
        utility_id,
        emittente_soggetto_ruolo_id,
        classe_utenza_id,
        str(articolo_padre_contesto) if articolo_padre_contesto else None,
        listino_versione_id_preferito,
    ]


class PricingRepository:
    """Accesso DB al resolver prezzi v5."""

    # Scopo: Invoca `vendite.fn_resolve_prezzo_listino_v2` e restituisce la
    #        riga risolta come dict. La funzione DB ritorna 1 riga per match;
    #        se non esiste prezzo risolvibile solleva P0001 che bubble-a al
    #        service chiamante.
    # `articolo_padre_contesto`: UUID opzionale per attivare lo STADIO BUNDLE
    # bundle-aware (modello unificato BoM 2026-05-13). Se NOT NULL, la fn DB
    # cerca prima in `listini_righe_componenti` per la coppia (padre, figlio)
    # nella versione listino determinata, poi fallback su `listini_righe`
    # standalone del componente. Quando NULL, comportamento standalone
    # tradizionale (resolver 3 stadi promo/contratto/categoria).
    # `listino_versione_id_preferito`: bigint opzionale (refactor 2026-05-20).
    # Se NOT NULL, il fast path "CONTRATTO_LISTINO" usa direttamente quella
    # versione listino come fonte (skip lookup contratto-via-BA). Usato dal
    # pricing gate L2 contratti per evitare drift cascata CATEGORIA quando si
    # lavora dentro un contratto specifico. Output quando fast path attivo:
    # `contratto_id`/`tipo_eccezione` = NULL (nessun contratto lookuppato),
    # `tipo_variazione_applicata` = 'NESSUNA'. NULL = comportamento legacy.
    def resolve_prezzo_listino_v2(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
        articolo_padre_contesto: UUID | str | None = None,
        listino_versione_id_preferito: int | None = None,
    ) -> dict[str, Any]:
        # Wrapper LEFT JOIN sulle 4 entita' referenziate dal return della
        # funzione (listino, listino_versione, contratto, promo, categoria
        # cliente) per esporre codice/descrizione denormalizzati. Single
        # round-trip: la funzione DB resta unica source-of-truth, il JOIN
        # decora le colonne id senza alterare la semantica.
        with connection.cursor() as cursor:
            cursor.execute(
                _sql_resolver("vendite.fn_resolve_prezzo_listino_v2", con_esito=False),
                _argomenti_resolver(
                    articolo_id=articolo_id,
                    uom_id=uom_id,
                    data_riferimento=data_riferimento,
                    ba_id=ba_id,
                    utility_id=utility_id,
                    emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                    classe_utenza_id=classe_utenza_id,
                    articolo_padre_contesto=articolo_padre_contesto,
                    listino_versione_id_preferito=listino_versione_id_preferito,
                ),
            )
            result = row_to_dict(cursor)
        assert result is not None
        return result

    # Scopo: Invoca il NUCLEO `vendite.fn_resolve_prezzo_listino_v2_esito` e
    #        restituisce la riga come dict, con in piu' le tre colonne di esito
    #        (`esito_codice`, `esito_context`, `esito_valori`).
    #
    #        DIFFERENZA COL METODO SOPRA, ed e' tutta qui: il guscio
    #        `fn_resolve_prezzo_listino_v2` SOLLEVA quando non risolve; il
    #        nucleo NON solleva — torna una riga col prezzo a NULL e il motivo
    #        in `esito_codice`. Serve al DDT, che e' l'unico documento dove il
    #        prezzo mancante non e' un errore (brief-ddt-righe-senza-prezzo).
    #        Gli altri domini continuano a chiamare il guscio: perdere il RAISE
    #        li farebbe proseguire con un prezzo NULL come se fosse risolto.
    #
    #        ⛔ IL GUARD SULLE ZERO RIGHE NON E' PRUDENZA. Il contratto della
    #        funzione e' «una riga esce sempre»: se non esce, l'invariante e'
    #        rotta e `row_to_dict` torna `None` — e il chiamante leggerebbe un
    #        prezzo assente dove in realta' non ha letto niente. Va sollevato
    #        `E_VENDITE_PRICING_ESITO_ASSENTE`, lo STESSO codice che il guscio
    #        DB usa per lo stesso invariante: due lati, un significato.
    #        ⚠️ E non un `assert` nudo: con `python -O` sparisce e il `None`
    #        prosegue (BE-A2 del brief).
    def resolve_prezzo_listino_v2_esito(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
        articolo_padre_contesto: UUID | str | None = None,
        listino_versione_id_preferito: int | None = None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                _sql_resolver(
                    "vendite.fn_resolve_prezzo_listino_v2_esito", con_esito=True,
                ),
                _argomenti_resolver(
                    articolo_id=articolo_id,
                    uom_id=uom_id,
                    data_riferimento=data_riferimento,
                    ba_id=ba_id,
                    utility_id=utility_id,
                    emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                    classe_utenza_id=classe_utenza_id,
                    articolo_padre_contesto=articolo_padre_contesto,
                    listino_versione_id_preferito=listino_versione_id_preferito,
                ),
            )
            result = row_to_dict(cursor)

        ErrorManager.require(
            result is not None,
            code=E_VENDITE_PRICING_ESITO_ASSENTE,
            message="Errore interno del calcolo prezzi: il resolver non ha restituito un esito.",
            detail=(
                "fn_resolve_prezzo_listino_v2_esito ha restituito zero righe: "
                "il contratto «una riga esce sempre» e' rotto."
            ),
            context={"articolo_id": str(articolo_id), "ba_id": ba_id},
            function_name="vendite.pricing_repository.resolve_prezzo_listino_v2_esito",
            log_to_db=True,
        )
        assert result is not None
        return result
