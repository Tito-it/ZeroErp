# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Permission classes DRF per ZeroErp.
# IsAdminZeroERP: check binding SUPER_ADMIN (multi-face) per endpoint amministrazione.
# ZeroERPPermission: risoluzione completa area funzionale + livello accesso.
# valuta_accesso_endpoint: la stessa decisione, chiesta per una view e un
# metodo senza una richiesta HTTP (la usano i tool dell'assistente AI).
# PassaggioDocumento: l'azione di un cambio di stato, letta dalla riga della
# matrice invece che dichiarata a mano (`<metodo>_passaggio`).
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.core.api.payload_validators import corpo_oggetto
from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.services.auth_constants import (
    RUOLI_PORTALE,
    RUOLI_SHOP,
    RUOLO_APPLICATIVO_OPERATORE,
)
from apps.core.services.permissions_cache import load_user_cache, save_user_cache
from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger(__name__)

# Il messaggio del 403 quando il diniego non ha una spiegazione piu' precisa.
_MSG_PERMESSO_NEGATO = "Non hai i permessi per questa operazione."


# Scopo: Perche' una decisione di permesso nega. Il valore e' il `reason=`
#        del log di sicurezza: cambiarlo cambia i log, non solo il codice.
# ⛔ Un solo vocabolario per chi decide (`valuta`) e chi comunica
#    (`_registra_diniego`): con due stringhe scritte a mano, un refuso da una
#    parte faceva cadere il diniego nel ramo generico senza errore — e
#    l'utente disabilitato riceveva il messaggio generico.
class MotivoDiniego(StrEnum):
    NON_AUTENTICATO = "non_autenticato"
    NESSUNA_PERMISSION_CLASS = "nessuna_permission_class"
    PERMISSION_CLASS_NON_VALUTABILE = "permission_class_non_valutabile"
    ADMIN_NEGATO = "admin_negato"
    AZIONE_NEGATA = "azione_negata"
    AZIONE_SCONOSCIUTA = "azione_sconosciuta"
    AREA_NON_DEFINITA = "area_non_definita"
    LIVELLO_INSUFFICIENTE = "livello_insufficiente"
    OGGETTO_SENZA_RICHIESTA = "oggetto_senza_richiesta"
    PASSAGGIO_SENZA_RICHIESTA = "passaggio_senza_richiesta"


# Scopo: L'esito di una decisione di permesso, con cio' che serve a chi la
#        comunica (log di sicurezza, messaggio del 403). La decisione non
#        scrive log e non sceglie messaggi: lo fa chi la chiede, perche' la
#        classe DRF li deve al client e il filtro dei tool no.
# Note: `motivo` e' None se e solo se l'accesso e' consentito.
@dataclass(frozen=True)
class EsitoPermesso:
    consentito: bool
    motivo: MotivoDiniego | None = None
    azione: str | None = None
    area: str | None = None
    livello: str | None = None
    richiesto: str | None = None
    ruolo_app: str | None = None


_CONSENTITO = EsitoPermesso(consentito=True)


# Scopo: BB — il permesso di un CAMBIO DI STATO di un documento portato al
#        modello (guida `modello-documento-di-vendita.md` §6, M-3): l'azione
#        di processo non si dichiara sulla view, si legge dalla riga del
#        passaggio (stato corrente -> stato chiesto), la stessa che leggono il
#        verbo e le capability. La view dichiara `<metodo>_passaggio =
#        PassaggioDocumento(...)` al posto di `<metodo>_permission`.
# ⭐ Il backend CHIEDE, non decide una seconda volta (guida dei permessi §7.4):
#    il 403 arriva prima della transazione, il verbo controlla di nuovo.
# Campi: testata — la testata nella mappa del modello (`vendite.ddt`);
#        documento_kwarg — il parametro di percorso con l'id del documento;
#        stato_chiesto — il codice dello stato di arrivo, fisso per le rotte
#        di un verbo (`CONFERMATO`, `EMESSO`); None = dal corpo, campo
#        `campo_stato` (il cambio stato generico);
#        campo_stato — il campo del corpo con lo stato chiesto (`stato_codice`;
#        il preventivo usa `nuovo_stato`);
#        risolvi_documento — per una rotta il cui parametro non e' l'id del
#        documento (il preventivo ROOT di una pratica, dal `pratica_id`): la
#        funzione che lo ricava, None = documento che non c'e' (decide il
#        livello, e il 404 lo da' il service).
@dataclass(frozen=True)
class PassaggioDocumento:
    testata: str
    documento_kwarg: str
    stato_chiesto: str | None = None
    campo_stato: str = "stato_codice"
    risolvi_documento: Callable[[int], int | None] | None = None

    # Scopo: L'azione che il passaggio chiede in questa richiesta, o None (riga
    #        senza azione, o nessuna riga: decide il livello sul documento, e il
    #        resto lo rifiuta il service o il verbo col suo codice).
    # ⚠️ Un corpo illeggibile e' il 400 di sempre (`corpo_oggetto`), sollevato
    #    qui invece che nell'handler: lo stesso codice, un passo prima.
    def azione(self, view: Any) -> str | None:
        parametro = view.kwargs.get(self.documento_kwarg)
        stato = self.stato_chiesto
        if stato is None:
            valore = corpo_oggetto(view.request).get(self.campo_stato)
            stato = valore.strip() if isinstance(valore, str) else None
        if parametro is None or not stato:
            return None
        documento_id: int | None = int(parametro)
        if self.risolvi_documento is not None:
            documento_id = self.risolvi_documento(int(parametro))
        if documento_id is None:
            return None
        return DocumentoModelloRepository().azione_del_passaggio(
            self.testata, documento_id, stato,
        )

# I tipi di accesso CRUD che la catena conosce: quelli che il livello piu'
# alto concede. Un `<chiave>_accesso` o un `accesso` fuori da qui si nega.
_TIPI_ACCESSO: frozenset[str] = LIVELLO_MAP["TUTTO"]


# Scopo: «Questo utente puo' fare questa chiamata a questa view?», senza una
#        richiesta HTTP. Applica, in ordine e con la semantica AND di DRF, le
#        `permission_classes` della view: ciascuna decide con lo STESSO metodo
#        `valuta` che usa il suo `has_permission`.
# ⭐ E' la regola unica per UI e AI (brief-db-area-funzionale-assistente-ai
#    §5.2): i tool dell'assistente chiamano service e repository senza passare
#    dagli endpoint, e fino al 2026-09-24 ne ricopiavano i permessi a mano in
#    `required_area` / `required_level` / `required_action` — con due copie che
#    gia' dicevano cose diverse. Ora un tool dichiara il suo endpoint gemello, e
#    il permesso lo decide questa funzione.
# ⛔ Fail-closed: una permission class senza `valuta` non si sa valutare fuori
#    da una richiesta, e l'accesso si nega. Aggiungerne una a una view che ha un
#    tool gemello vuol dire darle anche il suo `valuta`.
# Parametri: view — classe o istanza; si leggono solo attributi dichiarativi
#            (`permission_classes`, `area_funzionale`, `<metodo>_permission`,
#            `queryset`, `model_permission`, `skip_area_check`).
#            method — metodo HTTP ("GET", "POST", ...); action — l'action di un
#            ViewSet, se c'e'. cache — la cache permessi per-richiesta.
#            accesso — il tipo di accesso da chiedere AL POSTO di quello che
#            il metodo dichiara (vedi `ZeroERPPermission.valuta`).
def valuta_accesso_endpoint(
    user: Any,
    view: Any,
    *,
    method: str,
    action: str | None = None,
    accesso: str | None = None,
    cache: dict[str, Any],
) -> EsitoPermesso:
    if not user or not user.is_authenticated:
        return EsitoPermesso(consentito=False, motivo=MotivoDiniego.NON_AUTENTICATO)
    classi = list(getattr(view, "permission_classes", None) or ())
    if not classi:
        return EsitoPermesso(consentito=False, motivo=MotivoDiniego.NESSUNA_PERMISSION_CLASS)
    for classe in classi:
        valuta = getattr(classe, "valuta", None)
        if valuta is None:
            return EsitoPermesso(
                consentito=False, motivo=MotivoDiniego.PERMISSION_CLASS_NON_VALUTABILE,
            )
        esito = valuta(
            user, view, method=method, action=action, accesso=accesso, cache=cache,
        )
        if not esito.consentito:
            return esito
    return _CONSENTITO


# Scopo: La cache permessi DELLA RICHIESTA (L1 per-richiesta, pre-popolata
#        dalla L2 Redis), da usare in un `with`: all'uscita, anche su
#        eccezione, le voci aggiunte si salvano in Redis.
# ⭐ Una sede sola per la coppia `_get_cache` / `_save_cache_to_redis`: chi
#    decide un permesso fuori da `has_permission` (una view che chiede in
#    anticipo l'esito di un'altra, un check di azione nel corpo) usa la STESSA
#    cache della catena, invece di un `{}` che ririsolve tutto sul DB.
@contextmanager
def cache_permessi_richiesta(request: Request) -> Iterator[dict[str, Any]]:
    cache = ZeroERPPermission._get_cache(request)
    try:
        yield cache
    finally:
        ZeroERPPermission._save_cache_to_redis(request)


# Scopo: «Questa chiamata a questa view scrive?». Si DERIVA dal tipo di accesso
#        che la catena chiede per la chiamata (`ZeroERPPermission.tipo_accesso`):
#        scrive tutto cio' che non e' `view`.
# ⭐ Una sede sola (brief-db-area-funzionale-assistente-ai §5.3 punto 2): la
#    usano il livello sull'assistente (un tool che scrive chiede `TUTTO`), la
#    conferma dei tool e la sola lettura a DB. Prima era un flag scritto a mano
#    su ogni tool, piu' una terza copia nel test che lo ricalcolava dal metodo.
# ⚠️ Un `<metodo>_permission` NON rende la chiamata una scrittura: decide CHI
#    la fa, non COSA fa. Una `GET` protetta da un'azione resta una lettura.
# ⛔ Fail-closed: una chiamata di cui la catena non sa dire il tipo si tratta
#    come una scrittura — chiede di piu', non di meno.
def chiamata_in_scrittura(
    view: Any, *, method: str, action: str | None = None,
) -> bool:
    return ZeroERPPermission.tipo_accesso(view, method=method, action=action) != "view"


class IsAdminZeroERP(BasePermission):
    """Permission class per endpoint riservati agli amministratori.

    Verifica che l'utente abbia il binding SUPER_ADMIN attivo
    (`script.fn_is_super_admin`). Non passa dal sistema profili area /
    override (check diretto). Nome classe invariato per retrocompatibilita'
    con le view esistenti; la semantica "ADMIN" diventa "SUPER_ADMIN".
    """

    # Scopo: La decisione, senza richiesta: SUPER_ADMIN o superuser Django
    #        (coerenza con ZeroERPPermission). Metodo, action e tipo di
    #        accesso non contano.
    @classmethod
    def valuta(
        cls,
        user: Any,
        view: Any,
        *,
        method: str,
        action: str | None = None,
        accesso: str | None = None,
        cache: dict[str, Any],
    ) -> EsitoPermesso:
        if user.is_superuser:
            return _CONSENTITO
        if PermissionResolver.is_super_admin(user, cache=cache):
            return _CONSENTITO
        return EsitoPermesso(consentito=False, motivo=MotivoDiniego.ADMIN_NEGATO)

    # Scopo: Verifica che l'utente sia SUPER_ADMIN (decisione in `valuta`).
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        with cache_permessi_richiesta(request) as cache:
            esito = self.valuta(
                user, view, method=request.method or "", cache=cache,
            )
        if esito.consentito:
            return True

        logger.warning(
            "security.admin_denied user_id=%s path=%s",
            user.id, request.path,
        )
        # ⭐ Il codice viaggia con `self.code` fino all'envelope (E-5, come
        #    `E_REPARTO_SENZA_PROFILO`): senza, usciva `E_PERMISSION_DENIED`
        #    e la frase mirata non arrivava (brief-db-codici-non-trovato-
        #    email-e-permessi R-2).
        self.code = "E_ACCESSO_RISERVATO_ADMIN"
        self.message = "Accesso riservato agli amministratori."
        return False


# Scopo: BB — una lettura sui dati di UN utente (`user_id` dal percorso) e'
#        ammessa a lui stesso o a un amministratore; altrimenti 403
#        `E_PERMESSO_NEGATO`. Regola del 2 (ok Tid, 2026-10-08): la
#        scrivevano per conto loro permessi effettivi e audit permessi.
# ⭐ «Amministratore» non si riscrive qui: lo decide `IsAdminZeroERP.valuta`
#    (superuser Django o SUPER_ADMIN), la sede di quel significato.
# ⚠️ Serve alle view con `skip_area_check`, dove la catena non guarda piu'
#    niente: il controllo sta nel corpo, e il presidio
#    `test_skip_area_check_registro` (che legge gli attributi) non lo vede.
#    `detail` dice al chiamante CHE COSA non si puo' consultare.
def richiedi_se_stesso_o_amministratore(
    user: Any, user_id: int, *, cache: dict[str, Any], detail: str,
) -> None:
    if user_id == user.id:
        return
    if IsAdminZeroERP.valuta(user, None, method="", cache=cache).consentito:
        return
    raise ServiceError(
        code="E_PERMESSO_NEGATO",
        message="Non hai i permessi per questa operazione.",
        detail=detail,
    )


class ZeroERPPermission(BasePermission):
    """Permission class centrale di Zero ERP.

    Risolve automaticamente l'area funzionale dallo schema del model
    e verifica il livello di accesso tramite PermissionResolver.

    Per ViewSet usa ``view.action`` (list, retrieve, create, ...).
    Per APIView usa ``request.method`` (GET, POST, PUT, ...).

    Le view possono dichiarare:
    - ``area_funzionale = "vendite"`` per indicare l'area quando non c'e' queryset
    - ``<action>_permission = "codename"`` per azioni di processo custom
      (es. ``post_permission = "genera_fatture_lotti"``)
    - ``<action>_passaggio = PassaggioDocumento(...)`` per un cambio di stato
      di un documento sul modello: l'azione la dice la riga del passaggio
    - ``<action>_accesso = "view"`` per il tipo di accesso che il metodo chiede,
      quando non e' quello del suo verbo HTTP (es. ``post_accesso = "view"``
      per una lettura che viaggia in una POST)
    - ``oggetto_permesso_da_richiesta(self) -> (app_label, model_name) | None``
      quando l'oggetto dipende dalla richiesta (una tabella nel path): il
      livello si chiede su quell'oggetto e sulla sua area; ``None`` ricade
      sull'area della classe. Valutata sulla classe, senza richiesta, nega
    """

    # Codice del 403, scritto a ogni diniego (DRF lo legge con getattr):
    # solo annotazione, nessun valore di classe.
    code: str | None

    # Mapping azione ViewSet -> tipo di accesso CRUD richiesto
    ACTION_REQUIRES: dict[str, str] = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }

    # Mapping metodo HTTP -> tipo di accesso (fallback per APIView)
    METHOD_REQUIRES: dict[str, str] = {
        "GET": "view",
        "HEAD": "view",
        "OPTIONS": "view",
        "POST": "add",
        "PUT": "change",
        "PATCH": "change",
        "DELETE": "delete",
    }

    # Scopo: Il tipo di accesso CRUD (`view`/`add`/`change`/`delete`) che una
    #        chiamata chiede al livello d'area. Per APIView dal metodo HTTP, per
    #        ViewSet dall'action — salvo che la view dichiari
    #        `<chiave>_accesso`, con la stessa chiave di `<chiave>_permission`.
    # ⭐ Il verbo HTTP dice come VIAGGIA la chiamata, non sempre cosa FA. Una
    #    domanda all'assistente e' una POST (il corpo non sta in una query
    #    string) ed e' una lettura: senza la dichiarazione chiederebbe `add`, e
    #    un operatore in `LETTURA` non potrebbe nemmeno fare una domanda
    #    (brief-db-area-funzionale-assistente-ai §5.3 punto 1). E' una regola
    #    generale, non un caso speciale per quella view.
    # ⛔ Un valore dichiarato fuori dai quattro tipi rende `None`, cioe' nega:
    #    un refuso non deve cadere sul default del metodo in silenzio.
    # Ritorna: il tipo, o None se la catena non sa tradurre la chiamata.
    @classmethod
    def tipo_accesso(
        cls, view: Any, *, method: str, action: str | None = None,
    ) -> str | None:
        chiave = action if action else (method.lower() if method else None)
        if chiave:
            dichiarato = getattr(view, f"{chiave}_accesso", None)
            if dichiarato is not None:
                return cls._tipo_valido(dichiarato)
        if action:
            return cls.ACTION_REQUIRES.get(action)
        return cls.METHOD_REQUIRES.get(method or "")

    # Scopo: Un tipo di accesso DICHIARATO (`<chiave>_accesso`) o PASSATO
    #        (`valuta(accesso=...)`): se stesso se e' uno dei quattro, None
    #        (cioe' nega) altrimenti. Una sede sola per le due porte.
    @staticmethod
    def _tipo_valido(tipo: str) -> str | None:
        return tipo if tipo in _TIPI_ACCESSO else None

    # Scopo: La decisione, senza richiesta HTTP: tutto cio' che
    #        `has_permission` decide, e niente di cio' che comunica.
    #        Per APIView usa il metodo HTTP, per ViewSet l'action. Per azioni
    #        custom con attributo `<action>_permission` (o `<metodo>_permission`)
    #        verifica l'azione di processo, e il livello d'area non si guarda.
    # ⭐ La chiamano `has_permission` (UI) e `valuta_accesso_endpoint` (tool
    #    dell'AI): una regola sola, non due copie.
    # Parametri: view — classe o istanza; se ne leggono solo attributi
    #            dichiarativi, quindi va bene anche la classe.
    #            accesso — il tipo di accesso da chiedere al posto di quello
    #            della chiamata (`tipo_accesso`). Lo usa il filtro dei tool: il
    #            livello sull'assistente si misura sul tipo del TOOL, non sulla
    #            POST della domanda. ⚠️ Vale solo per il ramo CRUD: un
    #            `<metodo>_permission` decide comunque da solo.
    @classmethod
    def valuta(
        cls,
        user: Any,
        view: Any,
        *,
        method: str,
        action: str | None = None,
        accesso: str | None = None,
        cache: dict[str, Any],
    ) -> EsitoPermesso:
        # Django superuser bypass
        if user.is_superuser:
            return _CONSENTITO

        # ⛔ Niente piu' «ruolo DISABILITATO => negato» (ritirato il 2026-10-02,
        #    brief-db-be-fe-area-accessi R-DB-1): una veste spenta tiene il suo
        #    tipo e ha `attivo = false`, e la tabella rifiuta DISABILITATO. Chi
        #    ha solo vesti spente non ha un'identita' attiva: niente GUC di
        #    veste, niente SUPER_ADMIN, e il livello d'area lo nega piu' sotto.
        # Il ruolo serve ancora al messaggio del diniego d'area (`_esito_livello`).
        ruolo_app = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
        # SUPER_ADMIN bypass — single source of truth per il privilegio admin.
        if PermissionResolver.is_super_admin(user, cache=cache):
            return _CONSENTITO

        # Azione custom con permesso esplicito
        # (es. run_pipeline_permission = 'genera_fatture_lotti')
        # Per APIView (nessuna action): <method>_permission.
        chiave = action if action else (method.lower() if method else None)
        if chiave:
            azione = getattr(view, f"{chiave}_permission", None)
            if azione:
                if PermissionResolver.check_azione(user, azione, cache=cache):
                    return _CONSENTITO
                return EsitoPermesso(
                    consentito=False, motivo=MotivoDiniego.AZIONE_NEGATA, azione=azione,
                )
            # Il cambio di stato di un documento sul modello: l'azione dalla
            # riga del passaggio. Con l'azione decide lei (come sopra); senza,
            # si ricade sul livello sul documento qui sotto.
            # ⛔ Sulla sola classe (i tool dell'assistente) stato corrente e
            #    stato chiesto non ci sono: si nega.
            # La dichiarazione si riconosce dal TIPO: un attributo qualunque con
            # quel nome (una view finta, un refuso) non apre il ramo.
            passaggio = getattr(view, f"{chiave}_passaggio", None)
            if isinstance(passaggio, PassaggioDocumento):
                if isinstance(view, type):
                    return EsitoPermesso(
                        consentito=False, motivo=MotivoDiniego.PASSAGGIO_SENZA_RICHIESTA,
                    )
                azione = passaggio.azione(view)
                if azione:
                    if PermissionResolver.check_azione(user, azione, cache=cache):
                        return _CONSENTITO
                    return EsitoPermesso(
                        consentito=False, motivo=MotivoDiniego.AZIONE_NEGATA, azione=azione,
                    )

        # CRUD standard: determina il tipo di accesso richiesto
        if accesso is not None:
            required = cls._tipo_valido(accesso)
        else:
            required = cls.tipo_accesso(view, method=method, action=action)

        if required is None:
            # Fail-closed: azione sconosciuta senza *_permission -> nega.
            return EsitoPermesso(consentito=False, motivo=MotivoDiniego.AZIONE_SCONOSCIUTA)

        # L'oggetto che la RICHIESTA nomina (una rotta con la tabella nel path):
        # se la view lo dichiara, decide lui oggetto e area (D-P7 del
        # brief-db-pannello-config-verbo-generico).
        # ⛔ Sulla sola classe — i tool dell'assistente — la richiesta non c'e',
        #    e l'area della classe non e' quella dell'oggetto: si nega.
        risolvi_oggetto = getattr(view, "oggetto_permesso_da_richiesta", None)
        if risolvi_oggetto is not None:
            if isinstance(view, type):
                return EsitoPermesso(
                    consentito=False, motivo=MotivoDiniego.OGGETTO_SENZA_RICHIESTA,
                )
            oggetto = risolvi_oggetto()
            if oggetto is not None:
                app_label_r, model_name_r = oggetto
                area_r = PermissionResolver.get_area_schema_db(app_label_r, model_name_r)
                livello = PermissionResolver.get_livello_oggetto(
                    user, app_label_r, model_name_r, area_r, cache=cache
                )
                return cls._esito_livello(livello, required, area_r, ruolo_app)

        # Determina area funzionale dal model o dall'attributo della view
        area_schema_db = cls._resolve_area(view, cache)
        if area_schema_db is None:
            # Fail-closed: nessun model collegato e nessun area_funzionale.
            # Le view che intenzionalmente non richiedono area devono
            # dichiarare skip_area_check = True.
            if getattr(view, "skip_area_check", False):
                return _CONSENTITO
            return EsitoPermesso(consentito=False, motivo=MotivoDiniego.AREA_NON_DEFINITA)

        # Risolvi livello (oggetto o area).
        # Fonti model: 1) queryset ORM, 2) attributo model_permission
        # dichiarato sulla view (per DomainAPIView con raw SQL).
        # Se presente, fn_resolve_livello_oggetto fa fallback
        # automatico al livello area se non c'e' override.
        app_label, model_name = cls._get_model_meta(view)
        if not app_label:
            mp = getattr(view, "model_permission", None)
            if mp:
                app_label, model_name = mp
        if app_label and model_name:
            livello = PermissionResolver.get_livello_oggetto(
                user, app_label, model_name, area_schema_db, cache=cache
            )
        else:
            livello = PermissionResolver.get_livello_area(
                user, area_schema_db, cache=cache
            )

        return cls._esito_livello(livello, required, area_schema_db, ruolo_app)

    # Scopo: Il livello risolto concede il tipo di accesso richiesto? Una sede
    #        per i due rami di `valuta` (oggetto della richiesta, area/model
    #        della classe).
    @staticmethod
    def _esito_livello(
        livello: str, required: str, area: str, ruolo_app: str | None,
    ) -> EsitoPermesso:
        allowed_actions = LIVELLO_MAP.get(livello, frozenset())
        if required not in allowed_actions:
            return EsitoPermesso(
                consentito=False,
                motivo=MotivoDiniego.LIVELLO_INSUFFICIENTE,
                area=area,
                livello=livello,
                richiesto=required,
                ruolo_app=ruolo_app,
            )
        return _CONSENTITO

    # Scopo: Verifica i permessi di accesso per la richiesta corrente.
    #        La decisione e' `valuta`; qui si registra il diniego (log di
    #        sicurezza + messaggio del 403) e si gestisce la cache.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Django superuser bypass (prima della cache: non serve caricarla)
        if user.is_superuser:
            return True

        # Cache per-request (pre-popolata da Redis L2 se disponibile)
        with cache_permessi_richiesta(request) as cache:
            esito = self.valuta(
                user,
                view,
                method=request.method or "",
                action=getattr(view, "action", None),
                cache=cache,
            )
            if not esito.consentito:
                self._registra_diniego(request, view, esito, cache)
            return esito.consentito

    # Scopo: Log di sicurezza e messaggio del 403 per un diniego di `valuta`.
    def _registra_diniego(
        self,
        request: Request,
        view: Any,
        esito: EsitoPermesso,
        cache: dict[str, Any],
    ) -> None:
        user = request.user
        motivo = esito.motivo
        self.message = _MSG_PERMESSO_NEGATO
        self.code = None
        if motivo is MotivoDiniego.AZIONE_NEGATA:
            logger.warning(
                "security.permission_denied user_id=%s reason=azione_negata azione=%s path=%s",
                user.id, esito.azione, request.path,
            )
        elif motivo is MotivoDiniego.AZIONE_SCONOSCIUTA:
            logger.warning(
                "security.permission_denied user_id=%s reason=azione_sconosciuta "
                "action=%s method=%s path=%s",
                user.id, getattr(view, "action", None), request.method, request.path,
            )
        elif motivo is MotivoDiniego.AREA_NON_DEFINITA:
            logger.warning(
                "security.permission_denied user_id=%s reason=area_non_definita "
                "view=%s path=%s",
                user.id, type(view).__name__, request.path,
            )
        elif motivo is MotivoDiniego.LIVELLO_INSUFFICIENTE and esito.area:
            logger.warning(
                "security.permission_denied user_id=%s reason=livello_insufficiente "
                "area=%s livello=%s required=%s path=%s",
                user.id, esito.area, esito.livello, esito.richiesto, request.path,
            )
            self._set_deny_message(user, esito.ruolo_app, esito.area, cache)
        else:
            logger.warning(
                "security.permission_denied user_id=%s reason=%s path=%s",
                user.id, motivo, request.path,
            )

    # Scopo: Imposta il messaggio di errore specifico per il diniego.
    # Distingue tra reparto senza profilo e permesso negato generico.
    # Il messaggio "reparto senza profilo" si applica solo agli OPERATORI
    # interni (utenti portale/shop hanno profili bindati sul ruolo
    # applicativo, non sul reparto).
    def _set_deny_message(
        self,
        user: Any,
        ruolo_app: str | None,
        area_schema_db: str,
        cache: dict[str, Any],
    ) -> None:
        if ruolo_app == RUOLO_APPLICATIVO_OPERATORE and not PermissionResolver.has_profilo_applicabile_per_area(
            user, area_schema_db, cache=cache
        ):
            # ⭐ Il codice viaggia con `self.code` (DRF lo mette in
            #    `detail.code`, e `drf_exception_handler` lo legge): senza,
            #    usciva `E_PERMISSION_DENIED` col messaggio generico e questa
            #    frase non arrivava mai al client (E-5, 2026-10-08).
            self.code = "E_REPARTO_SENZA_PROFILO"
            self.message = (
                "Il reparto non ha ancora un profilo permessi configurato."
            )
        else:
            self.code = None
            self.message = _MSG_PERMESSO_NEGATO

    @staticmethod
    def _get_cache(request: Request) -> dict[str, Any]:
        """Scopo: Restituisce o crea la cache permessi per-request.
        Tenta di pre-popolare da Redis (L2) se la cache L1 non esiste.

        ⛔ La L2 si usa solo col contesto di sessione (identita' + emittente
        effettivo) che `set_jwt_gucs` segna sulla richiesta: i valori
        dipendono dalle GUC, e una voce per il solo utente servirebbe a una
        veste o a un emittente i permessi dell'altro. Senza contesto si
        lavora sulla sola L1."""
        if not hasattr(request, "_zeroerp_perms_cache"):
            user = request.user
            contesto = getattr(request, "_zeroerp_perms_contesto", None)
            valori, generazioni = (
                load_user_cache(user.id, contesto)
                if isinstance(contesto, str) and user and user.is_authenticated
                else (None, None)
            )
            request._zeroerp_perms_cache = valori or {}  # type: ignore[attr-defined]
            # Il contesto si fissa QUI, con i valori che la L1 conterra': se
            # la richiesta riaprisse le GUC in un altro contesto, il
            # salvataggio non deve scrivere sotto la chiave nuova valori
            # calcolati nella vecchia.
            request._zeroerp_perms_cache_contesto = contesto  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_generazioni = generazioni  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_voci_iniziali = len(request._zeroerp_perms_cache)  # type: ignore[attr-defined]
        return request._zeroerp_perms_cache  # type: ignore[attr-defined]

    @staticmethod
    def _save_cache_to_redis(request: Request) -> None:
        """Scopo: Persiste la cache per-request su Redis se e' stata arricchita.

        ⚠️ Solo se la richiesta ha AGGIUNTO voci: riscrivere una voce letta e
        invariata ne rinnoverebbe il TTL a ogni richiesta, e per un utente
        attivo la voce non scadrebbe mai (era cosi' fino al 2026-09-24)."""
        user = request.user
        if not user or not user.is_authenticated:
            return
        cache_dict = getattr(request, "_zeroerp_perms_cache", None)
        contesto = getattr(request, "_zeroerp_perms_cache_contesto", None)
        generazioni = getattr(request, "_zeroerp_perms_cache_generazioni", None)
        if not cache_dict or not isinstance(contesto, str) or generazioni is None:
            return
        voci_iniziali = getattr(request, "_zeroerp_perms_cache_voci_iniziali", 0)
        if len(cache_dict) > voci_iniziali:
            save_user_cache(user.id, contesto, cache_dict, generazioni)
            request._zeroerp_perms_cache_voci_iniziali = len(cache_dict)  # type: ignore[attr-defined]

    @staticmethod
    def _get_model_meta(view: Any) -> tuple[str | None, str | None]:
        """Scopo: Estrae app_label e model_name dal queryset della view."""
        qs = getattr(view, "queryset", None)
        if qs is not None:
            model = qs.model
            return model._meta.app_label, model._meta.model_name
        return None, None

    @classmethod
    def _resolve_area(
        cls, view: Any, cache: dict[str, Any]
    ) -> str | None:
        """Scopo: Determina l'area funzionale dalla view.
        1. Prova dal queryset model (schema DB)
        2. Fallback all'attributo area_funzionale della view."""
        app_label, model_name = cls._get_model_meta(view)
        if app_label and model_name:
            return PermissionResolver.get_area_schema_db(app_label, model_name)

        # Fallback: attributo esplicito sulla view
        return getattr(view, "area_funzionale", None)


class PortaleBasePermission(BasePermission):
    """Permission class per endpoint `/api/portale/*` (clienti + fornitori).

    Richiede autenticazione JWT. Il ruolo applicativo dell'identita
    deve appartenere a `RUOLI_PORTALE`. Gli operatori interni e shop
    customer sono respinti con 403.

    Non applica scope dati (RLS + `script.fn_scope_*` lato DB sono i
    guardiani autorevoli). Non verifica livello area: il set di
    endpoint portale e' deliberatamente ristretto.
    """

    # Scopo: Verifica autenticazione + ruolo applicativo portale.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        with cache_permessi_richiesta(request) as cache:
            ruolo = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
        if ruolo in RUOLI_PORTALE:
            return True

        logger.warning(
            "security.portale_denied user_id=%s ruolo=%s path=%s",
            user.id, ruolo, request.path,
        )
        # Codice nell'envelope: vedi `IsAdminZeroERP` (R-2).
        self.code = "E_ACCESSO_RISERVATO_PORTALE"
        self.message = "Accesso riservato agli utenti portale."
        return False


class ShopBasePermission(BasePermission):
    """Permission class per endpoint `/api/shop/*` (negozio online).

    Ammette utenti anonimi (catalogo pubblico) e utenti autenticati
    con ruolo applicativo `SHOP_CUSTOMER`. Altri ruoli applicativi
    autenticati vengono respinti per evitare che un operatore o un
    cliente portale usi per errore gli endpoint shop.

    Le singole view che richiedono autenticazione obbligatoria (es.
    checkout, storico ordini) devono comunque verificare
    `request.user.is_authenticated` esplicitamente.
    """

    # Scopo: Ammette anonimo OR SHOP_CUSTOMER. Altri ruoli -> 403.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            # Scopo: Endpoint pubblici (catalogo) ammettono anonimo.
            return True

        with cache_permessi_richiesta(request) as cache:
            ruolo = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
        if ruolo in RUOLI_SHOP:
            return True

        logger.warning(
            "security.shop_denied user_id=%s ruolo=%s path=%s",
            user.id, ruolo, request.path,
        )
        # Codice nell'envelope: vedi `IsAdminZeroERP` (R-2).
        self.code = "E_ACCESSO_RISERVATO_SHOP"
        self.message = "Accesso riservato ai clienti shop."
        return False
