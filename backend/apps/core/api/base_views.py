# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
    PortaleBasePermission,
    ShopBasePermission,
    ZeroERPPermission,
)
from apps.core.services import perimetro_emittente


class DomainAPIView(APIView):
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

    # Codice stabile della lista servita da questo endpoint, quando ne serve
    # UNA (`"vendite.dash_competenza_gruppi"`). `None` = l'endpoint non
    # alimenta una lista di catalogo, e il cancello resta inerte.
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
    lista_codice: str | None = None

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
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.lista_codice and request.user and request.user.is_authenticated:
            perimetro_emittente.guard_lista_per_codice(
                user=request.user,
                lista_codice=self.lista_codice,
            )


class AdminAPIView(APIView):
    """Base per view riservate ad amministratori (Amm. Software).

    Check diretto binding SUPER_ADMIN tramite
    `PermissionResolver.is_super_admin`. skip_area_check implicito
    perche' `IsAdminZeroERP` bypassa il resolver aree.

    Usa `JwtAuditAuthentication` (vedi DomainAPIView).
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True


class PortaleAPIView(APIView):
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


class ShopAPIView(APIView):
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
