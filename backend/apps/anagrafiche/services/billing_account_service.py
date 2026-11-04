# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per il lookup billing_account riutilizzabile cross-dominio.
#        Valida i parametri di ricerca, applica le regole di dominio
#        (min lunghezza query, cap risultati) e delega al repository.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.api.payload_validators import qp_int_optional
from apps.core.db.lookup_repository import LookupRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.service_errors import ServiceError

_MIN_QUERY_LENGTH = 2
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20

# Codici ruolo soggetto ammessi per l'endpoint utilities-per-BA.
# Allineato con il dominio del param p_ruolo_codice_soggetto della
# funzione SQL anagrafiche.fn_lookup_utilities_per_ba.
_ALLOWED_RUOLI_BA = frozenset({"CL", "FO", "GE"})


class BillingAccountService:
    """Facade per operazioni di lookup billing_account."""

    # Scopo: Esegue lookup billing_account per autocomplete con regole di dominio.
    #        Valida query min 2 char, cap limit a 50, risolve lo scope
    #        emittente dell'utente e delega al repository.
    # ⛔ Lo scope lo risolve il SERVICE, non il chiamante (2026-09-24). Fino a
    #    quel giorno lo passavano la view e il tool dell'AI, ciascuno per conto
    #    suo, e l'avevano risolto in due modi: la view coi soggetto_ruolo_id, il
    #    tool con le PK — numeri di due tabelle diverse, confrontati in silenzio.
    #    Quale id vuole la query e' un fatto della QUERY
    #    (`script.fn_check_ba_visible_for_emittenti` confronta col soggetto-ruolo
    #    dell'emittente): per questo si decide qui, accanto a lei, e il
    #    chiamante passa solo l'utente.
    # Perimetro: sola lettura. Ritorna lista arricchita + total_count per
    #        gestione UI "affina la ricerca" quando total > limit.
    # Risultato: dict {results, total_count} pronto per success_response.
    def search_lookup(
        self,
        *,
        user: Any,
        q: str,
        utility_id: int | None = None,
        solo_validi: bool = True,
        valid_at: date | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.search_lookup"
        cleaned_q = q.strip() if isinstance(q, str) else ""
        ErrorManager.require(
            len(cleaned_q) >= _MIN_QUERY_LENGTH,
            code="E_ANAG_VALIDAZIONE",
            message="Parametro di ricerca troppo corto.",
            detail=f"q deve avere almeno {_MIN_QUERY_LENGTH} caratteri.",
            context={"q_len": len(cleaned_q)},
            function_name=function_name,
            log_to_db=False,
        )

        # Cap di sicurezza sul limit — il default e' 20, max 50.
        if limit is None or limit <= 0:
            effective_limit = _DEFAULT_LIMIT
        else:
            effective_limit = min(int(limit), _MAX_LIMIT)

        # Scope emittente: None = nessuna restrizione (superuser), [] = nessun
        # emittente autorizzato (nessun BA), altrimenti i soggetto_ruolo_id.
        emittente_ids = PermissionResolver.get_emittenti_sr_ids(user, cache={})

        repository = BillingAccountRepository()
        results, total_count = repository.search_lookup(
            q=cleaned_q,
            utility_id=utility_id,
            solo_validi=solo_validi,
            valid_at=valid_at,
            emittente_ids=emittente_ids,
            limit=effective_limit,
        )

        return {
            "results": results,
            "total_count": total_count,
            "limit": effective_limit,
        }

    # Scopo: Lista utility "guidate da emittente" per un billing account
    #        (refactor operatore-emittenti, sez. 3 del WIP).
    #        Applica scope check sull'emittente fiscale del BA prima di
    #        delegare al lookup repository:
    #          - superuser → bypass scope
    #          - user_emittente_id NULL (admin globale o "0 emittenti")
    #            → no check, vede tutto
    #          - operatore con emittente assegnato → BA deve appartenere
    #            allo stesso emittente, altrimenti E_PERMESSO_NEGATO (403)
    # Perimetro: sola lettura.
    # Risultato: dict {results: [...]} pronto per success_response.
    def list_utilities_for_ba(
        self,
        *,
        billing_account_id: int,
        ruolo_codice_soggetto: str,
        user_emittente_id: int | None,
        is_superuser: bool = False,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.list_utilities_for_ba"

        # billing_account_id arriva sempre dall'URL converter <int:...>
        # nelle view: nessuna validazione manuale qui.
        # Validazione ruolo: whitelist a 3 valori. Il ruolo e' il `codice_interno`,
        # chiave tecnica: si confronta ESATTA, niente maiuscolo (Tid, 2026-11-04, brief-be-codice-maiuscolo §7.2).
        cleaned_ruolo = (ruolo_codice_soggetto or "").strip()
        ErrorManager.require(
            cleaned_ruolo in _ALLOWED_RUOLI_BA,
            code="E_ANAG_VALIDAZIONE",
            message="Ruolo soggetto non valido per BA utilities.",
            detail=f"ruolo deve essere uno di {sorted(_ALLOWED_RUOLI_BA)}.",
            context={"ruolo": ruolo_codice_soggetto},
            function_name=function_name,
            log_to_db=False,
        )

        repository = BillingAccountRepository()

        # 404 esplicito su BA inesistente per non leakare 403 sugli id
        # non validi (la fn_get_emittente_fiscale_pk farebbe fallback al
        # default globale e maschererebbe l'errore).
        if not repository.exists(billing_account_id):
            raise ServiceError(
                code="E_ANAG_NOT_FOUND",
                message="Billing account non trovato.",
                detail=f"Nessun billing_account con id={billing_account_id}.",
            )

        # Scope check sull'emittente del BA. Bypass per superuser e per
        # admin globale / "0 emittenti" (user_emittente_id is None).
        if not is_superuser and user_emittente_id is not None:
            ba_emittente_id = repository.get_emittente_fiscale_id(billing_account_id)
            if ba_emittente_id != user_emittente_id:
                raise ServiceError(
                    code="E_PERMESSO_NEGATO",
                    message=(
                        "Billing account fuori dallo scope emittente "
                        "dell'utente corrente."
                    ),
                )

        results = LookupRepository().list_utilities_per_billing_account(
            billing_account_id=billing_account_id,
            ruolo_codice_soggetto=cleaned_ruolo,
        )
        return {"results": results}

    # Scopo: Recupera un singolo billing_account per restore dell'AutoComplete
    #        in modalita' edit (evita round-trip aggiuntivi nel frontend).
    # Perimetro: sola lettura. Solleva E_ANAG_NOT_FOUND se inesistente.
    # Risultato: dict riga arricchita pronta per success_response.
    def get_lookup_by_id(self, billing_account_id: int) -> dict[str, Any]:
        function_name = "anagrafiche.billing_account_service.get_lookup_by_id"
        # Esclude bool (sottoclasse di int in Python): True/False non sono id validi.
        valid_id = (
            isinstance(billing_account_id, int)
            and not isinstance(billing_account_id, bool)
            and billing_account_id > 0
        )
        ErrorManager.require(
            valid_id,
            code="E_ANAG_VALIDAZIONE",
            message="billing_account_id non valido.",
            detail="billing_account_id deve essere un intero positivo.",
            context={"billing_account_id": billing_account_id},
            function_name=function_name,
            log_to_db=False,
        )
        repository = BillingAccountRepository()
        result = repository.get_lookup_by_id(billing_account_id)
        ErrorManager.require(
            result is not None,
            code="E_ANAG_NOT_FOUND",
            message="Billing account non trovato.",
            detail=f"Nessun billing_account con id={billing_account_id}.",
            context={"billing_account_id": billing_account_id},
            function_name=function_name,
            log_to_db=False,
        )
        assert result is not None
        return result


# Scopo: BB — categoria cliente del billing account indicato nel query param
#        `billing_account_id`, per alimentare il livello `categoria_cliente`
#        della cascata parametri (F-6 di analisi-be-difetti-emersi-verifica-doc-api-core).
#        Consumatori: `/core/parameters/settings/` e
#        `/vendite/pricing/limiti-utente/` (regola del 2, ok Tid 2026-10-08).
# Perimetro: sola lettura. Assente o vuoto → None (livello categoria saltato).
#        Non numerico o <= 0 → ValueError (400 E_VALIDATION_INPUT).
#        BA che non risulta → 404 E_ANAG_NOT_FOUND.
# ⭐ «Non risulta» copre due casi, e di proposito non li distingue: il BA che
#    non esiste e quello fuori dallo scope dell'operatore, che la RLS di
#    `anagrafiche.billing_account` (policy `rls_billing_account_ef_whitelist`)
#    non restituisce. Prima il `None` passava in silenzio: categoria NULL, e
#    l'utente vedeva soglie senza livello categoria senza nessun segnale.
# ⚠️ `None` dal repository vuol dire «non risulta» SOLO perche'
#    `billing_account.categoria_cliente_id` e' NOT NULL: se la colonna
#    diventasse nullable, un BA visibile senza categoria uscirebbe 404, e
#    qui andrebbe distinta l'esistenza dalla categoria.
# Risultato: int (categoria) oppure None se il parametro non c'e'.
def categoria_cliente_da_query(raw: str | None) -> int | None:
    billing_account_id = qp_int_optional(raw, "billing_account_id")
    if billing_account_id is None:
        return None
    if billing_account_id <= 0:
        raise ValueError("billing_account_id_invalid")
    categoria_cliente_id = BillingAccountRepository().get_categoria_cliente_id(
        billing_account_id,
    )
    ErrorManager.require(
        categoria_cliente_id is not None,
        code="E_ANAG_NOT_FOUND",
        message="Billing account non trovato.",
        detail=f"Nessun billing_account visibile con id={billing_account_id}.",
        context={"billing_account_id": billing_account_id},
        function_name="anagrafiche.billing_account_service.categoria_cliente_da_query",
        log_to_db=False,
    )
    return categoria_cliente_id


# Scopo: BB — l'ISTANZA del billing account che un payload indica, per chi
#        scrive un documento o una pratica col BA (regola del 2, ok Tid
#        2026-10-09). Il BA porta la sua istanza (FK NOT NULL, immutabile:
#        E_BA_ISTANZA_IMMUTABILE): se il payload porta anche l'istanza, deve
#        essere quella.
#        Consumatori: `pratiche_service.crea_pratica`,
#        `preventivi_service._risolvi_cliente_preventivo`,
#        `commesse_service.aggiungi_onere_commessa`.
# Perimetro: sola lettura. `code` e' il codice di validazione del dominio
#        chiamante (400); `campo` e' quello che l'operatore deve correggere:
#        il BA quando lo sceglie lui (pratica, preventivo), l'istanza quando il
#        BA e' gia' scritto sul documento (l'onere: il BA e' della commessa).
#        - BA che non risulta (inesistente o fuori RLS) → errore;
#        - `istanza_utility_id` None → l'istanza del BA;
#        - `istanza_utility_id` diversa da quella del BA → errore.
#        Un BA ASSENTE non e' affare di questo BB: cosa significa lo decide il
#        chiamante (per la commessa, un onere senza istanza a cui agganciarsi).
# ⛔ Prima erano tre copie, e gia' divergenti: la pratica e la commessa
#    controllavano la coincidenza, il preventivo no — un'istanza diversa da
#    quella del BA usciva «Utility non coerente» sul campo `utility_id`, o
#    arrivava alla FK composta.
# Risultato: id dell'istanza del BA.
def istanza_del_billing_account(
    billing_account_id: int,
    istanza_utility_id: int | None,
    *,
    code: str,
    function_name: str,
    campo: str = "billing_account_id",
) -> int:
    istanza_del_ba = BillingAccountRepository().get_istanza_utility_id(int(billing_account_id))
    ErrorManager.require(
        istanza_del_ba is not None,
        code=code,
        message="Billing account non trovato.",
        detail=f"billing_account_id={billing_account_id}",
        context={"field": campo, "billing_account_id": billing_account_id},
        function_name=function_name,
    )
    assert istanza_del_ba is not None
    ErrorManager.require(
        istanza_utility_id is None or int(istanza_utility_id) == istanza_del_ba,
        code=code,
        message="L'istanza indicata non e' quella del billing account.",
        detail=(
            f"billing_account_id={billing_account_id} e' dell'istanza "
            f"{istanza_del_ba}, indicata {istanza_utility_id}."
        ),
        context={
            "field": campo,
            "billing_account_id": billing_account_id,
            "istanza_utility_id": istanza_utility_id,
        },
        function_name=function_name,
    )
    return istanza_del_ba
