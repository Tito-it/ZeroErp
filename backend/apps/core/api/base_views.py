# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Base classes per view API.
#        DomainAPIView: view di dominio con JWT + permessi area.
#        AdminAPIView: view admin con JWT + check SUPER_ADMIN.
#        PortaleAPIView: view portale clienti/fornitori.
#        ShopAPIView: view shop online (catalogo pubblico + clienti).
#        Ref: docs/it/dev/api.md
# ------------------------------------------------------------

from rest_framework.views import APIView

from apps.core.api.jwt_audit_authentication import JwtAuditAuthentication
from apps.core.api.permissions import (
    IsAdminZeroERP,
    PassaggioDocumento,
    PortaleBasePermission,
    ShopBasePermission,
    ZeroERPPermission,
    chiamata_in_scrittura,
)
from apps.core.services import perimetro_emittente
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.ordinamento_di_partenza import (
    applica_misura_di_partenza,
    applica_ordinamento_di_partenza,
    applica_vuoti_come_massimo,
    ritira_ordinamento_di_partenza,
)
from apps.core.services.request_context import (
    OrdinamentoPropostoRifiutato,
    get_idempotency_key,
)
from apps.core.services.service_errors import ServiceError


class _ApiViewBase(APIView):
    """Le regole comuni alle quattro porte (dominio, admin, portale, shop).

    ⛔ **Una POST che scrive porta l'`Idempotency-Key`** (decisione Tid del
    2026-10-20, brief-be-verifica-documentazione-api §A5). Una POST di
    creazione o di azione non e' idempotente: ripetuta, crea o agisce due
    volte. PATCH, PUT e DELETE lo sono per semantica HTTP, e restano senza.
    Una POST che LEGGE lo dichiara con `post_accesso = "view"` (lo stesso
    attributo che abbassa il permesso alla lettura) e resta fuori.

    Fino a quel giorno la key era una scelta della singola view
    (`handle_post_json(require_idempotency_key=True)`): 82 scritture su 457 la
    chiedevano, senza un criterio — il cambio stato in cinque documenti si' e
    in cinque no. Un controllo che ogni view deve ricordarsi e' quello che la
    centesima dimentica: qui vale per costruzione, anche per le view nuove.

    ⚠️ Vive in `initial()`, DOPO autenticazione e permessi: chi non e'
    autenticato o non ha il permesso riceve 401/403, non un 400 sulla key.
    `handle_post_json(require_idempotency_key=True)` resta per la modalita'
    forte (claim/replay su `dbops.idempotency_keys`), che il controllo di
    presenza da solo non fa.
    """

    # ⭐ «Questa POST scrive?» lo decide il BB `chiamata_in_scrittura`, la
    #    stessa regola dei permessi (`post_accesso`, le `action` dei ViewSet,
    #    fail-closed su un tipo non valido): una seconda lettura dell'attributo
    #    qui divergeva da quella al primo refuso.
    # ⚠️ Una view senza `post` risponde 405, non un 400 sulla key: `initial()`
    #    gira prima che DRF cerchi l'handler.
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if (
            request.method == "POST"
            and hasattr(self, "post")
            and chiamata_in_scrittura(
                self, method="POST", action=getattr(self, "action", None),
            )
            and not get_idempotency_key()
        ):
            raise ServiceError(
                code="E_IDEMPOTENCY_KEY_REQUIRED",
                message=USER_MESSAGE_FALLBACK["E_IDEMPOTENCY_KEY_REQUIRED"],
                detail="Header Idempotency-Key mancante: una POST che scrive la porta sempre.",
            )
        if self.lista_codice and request.user and request.user.is_authenticated:
            # Prima il cancello della porta (solo `DomainAPIView` ne ha uno),
            # poi la partenza: una lista che non si puo' leggere non si ordina.
            self._cancello_di_lista(request, lista_codice=self.lista_codice)
            # ⭐ L'ordinamento di partenza della lista, quando la richiesta non
            #    ne porta uno (BE25 (2) di brief-db-revisione-ui). Il perche'
            #    della sede sta nel BB.
            applica_ordinamento_di_partenza(request, lista_codice=self.lista_codice)
            # E la misura di partenza, quando la richiesta non porta `limit`
            # (BE10): la legge `pagina_da_query` solo se pagina davvero.
            applica_misura_di_partenza(request, lista_codice=self.lista_codice)
        if self.lista_codice:
            # Dove va il vuoto quando la lista ordina, dichiarato nel catalogo
            # (brief-db-lista-colonna-vuoto-in-ordine): la legge il BB
            # dell'ordinamento solo se risolve una colonna.
            # ⭐ FUORI dal gate dell'utente autenticato (Tid, 2026-11-24): e' un
            #    fatto del CATALOGO, uguale per ogni utente, anonimo dello shop
            #    compreso. Ordinamento e misura restano dentro: dipendono da chi
            #    legge. Sta dopo il cancello: una lista che non si puo' leggere
            #    non arriva qui.
            applica_vuoti_come_massimo(request, lista_codice=self.lista_codice)

    # Codice stabile della lista di catalogo servita da questo endpoint, quando
    # ne serve UNA (`"vendite.dash_competenza_gruppi"`). `None` = l'endpoint non
    # alimenta una lista di catalogo.
    # ⭐ Su OGNI porta accende la PARTENZA della lista: l'ordinamento e la misura
    #    della sua configurazione quando la richiesta non li porta
    #    (`apps.core.services.ordinamento_di_partenza`), e dove va il vuoto
    #    delle colonne che lo dichiarano quando la lista ordina. Sta qui, e non in
    #    `DomainAPIView`, dal 2026-11-22 (residuo di BE25 (2) di
    #    brief-db-revisione-ui, ok Tid): le liste dell'amministrazione
    #    (`AdminAPIView`) non la ricevevano, e il FE ne teneva le copie.
    # ⚠️ Su `DomainAPIView` accende ANCHE il cancello di perimetro emittente
    #    (`_cancello_di_lista`, la' il perche'). Le altre porte ne sono esenti
    #    per decisione (brief perimetro-emittente, passo C-2): dichiarare la
    #    lista su una `AdminAPIView` non lo accende. Registro delle esenzioni:
    #    `test_perimetro_emittente_copertura`.
    lista_codice: str | None = None

    # Scopo: il cancello della PORTA sulla lista, prima della partenza. Nessuno
    #        sulla base: lo ha `DomainAPIView` (perimetro emittente).
    def _cancello_di_lista(self, request, *, lista_codice: str) -> None:
        return None

    # Scopo: il repository ha rifiutato la chiave dell'ordinamento di partenza
    #        (BE25 (2) di brief-db-revisione-ui): si ritira la proposta e si
    #        rilegge la lista con lo STESSO handler, una volta sola, come se la
    #        richiesta fosse arrivata senza `order_by`.
    # ⭐ Si rilegge invece di ripiegare dentro il repository perche' molti
    #    compongono l'`ORDER BY` a mano e leggono `order_dir` per conto loro:
    #    un ripiego sulla sola colonna terrebbe il verso del preset sul default.
    #    Rileggere e' sicuro: la proposta vive solo su GET/HEAD, che non
    #    scrivono (girano in sola lettura).
    # ⚠️ Ogni altra eccezione, e un secondo rifiuto, seguono la strada di sempre.
    def handle_exception(self, exc):
        if (
            isinstance(exc, OrdinamentoPropostoRifiutato)
            and self.lista_codice
            and not getattr(self, "_ordinamento_di_partenza_ritirato", False)
        ):
            self._ordinamento_di_partenza_ritirato = True
            ritira_ordinamento_di_partenza(self.request, lista_codice=self.lista_codice)
            metodo = (self.request.method or "").lower()
            handler = getattr(self, metodo, self.http_method_not_allowed)
            try:
                return handler(self.request, *self.args, **self.kwargs)
            except Exception as altro:
                return super().handle_exception(altro)
        return super().handle_exception(exc)


class DomainAPIView(_ApiViewBase):
    """Base per view di dominio con JWT + permessi area.

    Ogni sottoclasse DEVE definire `area_funzionale`.
    Opzionalmente: `is_search_endpoint = True` per throttling ricerca.
    Opzionalmente: `lista_codice = "<schema>.<lista>"` per il cancello di
    perimetro emittente (vedi sotto).

    Usa `JwtAuditAuthentication` (subclass di JWTAuthentication) per
    propagare l'identita utente come GUC PG dopo authenticate().
    Vedi guida risorse-umane-e-accessi.md sezione "Propagazione
    identita utente al database (GUC)".
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [ZeroERPPermission]

    # Gli attributi DICHIARATIVI che le sottoclassi — e le fabbriche di view —
    # impostano, e che `ZeroERPPermission` legge. ⚠️ Sono SOLO annotazioni, senza
    # valore: la classe base NON li ha, quindi `getattr(view, ..., None)` e il
    # fail-closed sull'area (`AREA_NON_DEFINITA`) restano esattamente quelli di
    # prima. Servono al type checker: senza, una fabbrica che scrive
    # `classe.model_permission = ...` assegna un attributo «sconosciuto».
    area_funzionale: str
    model_permission: tuple[str, str] | None
    get_permission: str
    post_permission: str
    post_passaggio: PassaggioDocumento
    put_permission: str
    patch_permission: str
    delete_permission: str

    # `lista_codice` (dichiarato su `_ApiViewBase`, la' la partenza): QUI
    # accende anche il cancello di perimetro emittente. `None` = il cancello
    # resta inerte.
    #
    # ⚠️ E' DICHIARATIVO come `area_funzionale` e `post_permission`: la view
    #    dichiara COSA SERVE, non cosa controllare. La forma alternativa —
    #    chiamare il guard riga per riga dentro ogni `get` — e' quella che
    #    qualcuno dimentica alla settima lista, e una regola che si dimentica
    #    non e' un presidio.
    #
    # ⚠️ **Lo dichiara anche la view di EXPORT della stessa lista**, ed e' la
    #    meta' che si dimentica: l'export e' la porta piu' larga (una richiesta
    #    porta via fino a 10.000 righe), e rifiutare a video quel che si
    #    concede in un file e' il modo peggiore di avere un presidio.
    #    Presidiato da `test_perimetro_emittente_copertura`, che pretende lista
    #    ed export coerenti nei DUE versi.
    #
    # ⚠️ **Il perche' sta QUI e non sulle ~50 view che lo usano**: e' una
    #    proprieta' del meccanismo, non di ognuna di esse. Copiarlo accanto a
    #    ogni dichiarazione produceva 243 righe di commento identico per 65 di
    #    codice — e nessuno commenta `area_funzionale = "vendite"`.

    # Nome del parametro di QUERY con cui questo endpoint riceve l'emittente
    # gia' fissato dal contesto che lo apre — tipicamente un tab-lista dentro
    # il drawer di un emittente, dove l'emittente e' l'oggetto stesso che si
    # sta guardando. `None` = l'endpoint non ne ha uno, e il cancello decide
    # come ha sempre deciso.
    #
    # ⚠️ Il nome lo dichiara la VIEW perche' e' l'unica a saperlo: il progetto
    #    ne usa piu' d'uno (`emittente_soggetto_ruolo_id` e' il soggetto-ruolo,
    #    `emittente_fiscale_id` e' la PK — non sono la stessa cosa), e un nome
    #    cablato nella base view sceglierebbe al posto delle sottoclassi.
    #
    # ⚠️ Si legge SOLO dalla query string, mai dal payload: sulle scritture
    #    l'emittente e' gia' verificato dalla view che lo riceve (e li' e' un
    #    controllo di scope, non di leggibilita'), e leggere il corpo dentro
    #    `initial()` significherebbe consumarlo prima del `post`.
    lista_emittente_param: str | None = None

    # Scopo: applica il cancello di perimetro emittente PRIMA di servire i
    #        dati, per le view che dichiarano `lista_codice`.
    # Perimetro: solo lettura del perimetro; il rifiuto e' un errore di dominio
    #        registrato (`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`, 422) sollevato dal
    #        building block `apps.core.services.perimetro_emittente`.
    #
    # ⚠️ Non e' un permesso e non sta fra le `permission_classes`: una
    #    `PermissionDenied` direbbe 403 «non hai il diritto», che qui e' falso —
    #    il diritto c'e', manca una precondizione che l'utente scioglie da se'.
    #    Vive in `initial()` perche' e' il punto in cui autenticazione e
    #    permessi sono gia' risolti e nessun `get`/`post` e' ancora partito.
    #
    # ⚠️ Vale per OGNI metodo HTTP, non solo per il `get`: un endpoint di lista
    #    che espone anche un'azione massiva sulla stessa selezione la
    #    eseguirebbe sullo stesso perimetro ambiguo che il cancello sta
    #    rifiutando di mostrare.
    # ⭐ Lo chiama `_ApiViewBase.initial()` prima della partenza della lista.
    def _cancello_di_lista(self, request, *, lista_codice: str) -> None:
        perimetro_emittente.guard_lista_per_codice(
            user=request.user,
            lista_codice=lista_codice,
            emittente_esplicito=self._emittente_esplicito(request),
        )

    # Scopo: l'emittente che la richiesta FISSA, quando questo endpoint ne
    #        dichiara il parametro. `None` se non lo dichiara.
    # ⭐ La REGOLA (un valore solo, numerico) sta nel building block, non qui:
    #    la stessa lettura la fa l'endpoint di config della lista, e due letture
    #    gemelle sono il modo classico di farle divergere.
    def _emittente_esplicito(self, request) -> int | None:
        if not self.lista_emittente_param:
            return None
        return perimetro_emittente.emittente_esplicito_da_query(
            request.query_params, nome=self.lista_emittente_param
        )


class AdminAPIView(_ApiViewBase):
    """Base per view riservate ad amministratori (Amm. Software).

    Check diretto binding SUPER_ADMIN tramite
    `PermissionResolver.is_super_admin`. skip_area_check implicito
    perche' `IsAdminZeroERP` bypassa il resolver aree.

    Usa `JwtAuditAuthentication` (vedi DomainAPIView).
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True


class PortaleAPIView(_ApiViewBase):
    """Base per view del portale clienti/fornitori (`/api/portale/*`).

    Richiede autenticazione JWT + `ruolo_applicativo` in
    `RUOLI_PORTALE` (CLIENTE_PORTALE, FORNITORE_PORTALE).

    Le view portale NON dichiarano `area_funzionale`: il set di
    endpoint portale e' deliberatamente ristretto (lettura propri
    dati) e non passa per la catena livello area. Lo scope dati e'
    applicato a livello DB (scope_policy + RLS).

    Ref: WIP sviluppo-multi-face-auth.md §13.4.13-14.
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [PortaleBasePermission]
    skip_area_check = True


class ShopAPIView(_ApiViewBase):
    """Base per view del negozio online (`/api/shop/*`).

    Ammette richieste anonime (catalogo pubblico) e autenticate con
    `ruolo_applicativo = SHOP_CUSTOMER`. Le view che richiedono
    autenticazione obbligatoria (checkout, ordini, profilo) devono
    verificare `request.user.is_authenticated` esplicitamente o usare
    un sotto-mixin dedicato.

    Ref: WIP sviluppo-multi-face-auth.md §13.4.13-14.
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [ShopBasePermission]
    skip_area_check = True
