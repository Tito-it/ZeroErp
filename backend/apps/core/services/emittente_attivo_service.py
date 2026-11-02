# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Regole dell'EMITTENTE ATTIVO — «dentro quale emittente sto
#        lavorando» (impersonazione di scope, brief-db-impersonazione-scope-
#        emittente). Unico posto che decide QUALE emittente finisce nel claim
#        JWT, e quindi nella GUC `app.current_emittente_id` da cui il DB
#        restringe liste, RLS e write-guard.
#
#        Tre verbi, una regola per ciascuno:
#          - `risolvi_per_login`  → cosa proporre a chi entra;
#          - `imposta`            → cosa succede quando l'utente sceglie;
#          - `descrivi`           → cosa vede il frontend (`/me/`).
#
#        ⚠️ Confine con il DB. Qui non si decide MAI cosa un utente può
#        vedere: si decide solo quale emittente dichiarare. La restrizione la
#        applicano le funzioni di scope, e valgono per costruzione anche se
#        questo modulo sbagliasse — l'emittente attivo è solo restringente,
#        mai allargante (§2 del brief). Ne discende che un bug qui produce al
#        più «vedo meno di quanto dovrei», mai «vedo ciò che non è mio».
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db.emittente_attivo_repository import EmittenteAttivoRepository
from apps.core.services import perimetro_emittente
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver

# Errore di dominio: la scelta non è (più) percorribile per questo utente.
# Copre entrambi i casi — emittente inesistente/disattivato e fuori scope —
# di proposito: distinguerli direbbe a un operatore quali emittenti esistono
# fuori dal suo perimetro (enumeration), e non gli servirebbe a nulla.
E_EMITTENTE_ATTIVO_NON_VALIDO = "E_EMITTENTE_ATTIVO_NON_VALIDO"

# Modalità «Tutti gli emittenti»: nessun emittente attivo. È SOLA LETTURA per
# costruzione, non per scelta nostra — `emittente_fiscale_id` è NOT NULL su
# contratti, DDT, ordini e preventivi, e senza emittente attivo il DB non ha
# con cosa riempirlo (§8.2.2 della risposta DB). Il FE spegne i verbi di
# creazione; il DB comunque rifiuta, con `E_EMITTENTE_NON_RISOLTO` (un codice
# solo dal 2026-09-15: `script.trgfn_default_emittente_fiscale`).
MODALITA_GLOBALE = None


class EmittenteAttivoService:
    """Risoluzione, cambio e descrizione dell'emittente attivo di sessione."""

    def __init__(self, repo: EmittenteAttivoRepository | None = None) -> None:
        self._repo = repo or EmittenteAttivoRepository()

    # Scopo: Emittente da mettere nel claim al LOGIN.
    #
    #        Ordine, e perché:
    #        1. l'operatore ha il suo emittente per permesso — la whitelist
    #           vince sempre, non è una preferenza e lui non la sceglie;
    #        2. il super admin usa la preferenza salvata, se ancora valida;
    #        3. se la preferenza è decaduta (emittente disattivato o uscito
    #           dallo scope) la si CANCELLA e si entra in modalità globale:
    #           il FE chiederà di scegliere di nuovo. Meglio ripartire dalla
    #           scelta che trascinare in silenzio un emittente spento.
    #
    #        Risultato `None` = modalità globale (nessun claim emesso).
    def risolvi_per_login(self, auth_user_id: int) -> int | None:
        proprio = self._repo.get_emittente_di_permesso(auth_user_id)
        if proprio is not None:
            return proprio
        preferito = self._repo.get_preferenza(auth_user_id)
        if preferito is None:
            return MODALITA_GLOBALE
        if not self._repo.is_scelta_valida(auth_user_id, preferito):
            self._repo.delete_preferenza(auth_user_id)
            return MODALITA_GLOBALE
        return preferito

    # Scopo: L'utente sceglie. `emittente_fiscale_id=None` = «Tutti gli
    #        emittenti».
    #
    #        La modalità globale NON cancella la preferenza: è uno stato di
    #        SESSIONE, e al prossimo login si torna dentro l'emittente
    #        abituale. Cancellarla significherebbe che una sbirciata
    #        d'insieme costa la riconfigurazione — e la tabella, avendo
    #        `emittente_fiscale_id NOT NULL`, non saprebbe comunque
    #        registrare «tutti».
    #
    #        Ritorna l'emittente da mettere nel nuovo claim.
    def imposta(self, auth_user_id: int, emittente_fiscale_id: int | None) -> int | None:
        if emittente_fiscale_id is None:
            return MODALITA_GLOBALE
        ErrorManager.require(
            self._repo.is_scelta_valida(auth_user_id, int(emittente_fiscale_id)),
            code=E_EMITTENTE_ATTIVO_NON_VALIDO,
            message="Emittente non selezionabile: inesistente, disattivato o fuori dal tuo perimetro.",
            detail=f"emittente_fiscale_id={emittente_fiscale_id}",
        )
        self._repo.set_preferenza(auth_user_id, int(emittente_fiscale_id))
        return int(emittente_fiscale_id)

    # Scopo: Blocco `emittente_attivo` di `/me/`. Dice al frontend tre cose
    #        che non può dedurre da solo:
    #          - `emittente_fiscale_id`: dentro cosa sto lavorando ORA (dal
    #            claim della sessione, non dalla tabella: sono due valori
    #            diversi appena si passa a «Tutti»);
    #          - `puo_scegliere`: mostrare o no la combo — l'operatore non
    #            sceglie, il suo emittente è un permesso;
    #          - `deve_scegliere`: forzare il dialog iniziale.
    #        `modalita_globale` è ridondante rispetto a `emittente_fiscale_id`
    #        ma esplicito: è lo stato in cui i verbi di creazione vanno spenti,
    #        e leggerlo per nome evita che ogni componente reinventi il test.
    #
    #        ⚠️ «Non ha mai scelto» e «ha scelto Tutti» sono **due stati
    #        diversi** che dal claim si vedono uguali (assente in entrambi).
    #        A distinguerli è la preferenza salvata: chi ha scelto «Tutti» ha
    #        comunque un emittente abituale in tabella. Senza questa
    #        distinzione il dialog bloccante ricomparirebbe a ogni caricamento
    #        proprio a chi ha appena deciso di vedere tutto — trasformando una
    #        scelta legittima in un fastidio ricorrente.
    def descrivi(
        self,
        auth_user_id: int,
        attivo_da_claim: int | None,
        *,
        user: Any = None,
        con_perimetro: bool = True,
        cache: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        proprio = self._repo.get_emittente_di_permesso(auth_user_id)
        # Chi sceglie l'emittente di lavoro: **il super admin senza un emittente
        # proprio**. Due condizioni, e servono entrambe.
        #
        # ⚠️ Il solo `proprio is None` non basta, ed e' il difetto che questa
        #    riga chiude: dopo P-2a descrive anche l'OPERATORE NON CONFIGURATO
        #    — uno che il database non fa piu' vedere niente (scope `'{}'`) e a
        #    cui l'interfaccia offriva comunque la combo, con dentro zero
        #    opzioni. Il bypass `SUPER_ADMIN` lo distingue, ed e' la stessa
        #    fonte di verita' che usa la catena dei permessi.
        #
        # ⛔ E NON si guarda la cardinalita' dello SCOPE — correzione proposta
        #    e ritirata il 2026-08-18 (BE-5): `fn_get_emittenti_scope_pk_ids`
        #    INTERSECA con `app.current_emittente_id`, quindi il super admin
        #    che ha gia' scelto un emittente ha cardinalita' 1 e si sarebbe
        #    visto SPARIRE la combo — cioe' non avrebbe piu' potuto cambiare
        #    idea. Qui la domanda giusta e' «chi sei», non «cosa stai
        #    guardando»: la prima non si muove quando scegli, la seconda si'.
        #
        # ⚠️ Senza `user` (nessun oggetto utente) resta il calcolo storico: e'
        #    l'unico dato disponibile, e restringere al buio sarebbe peggio —
        #    toglierebbe la combo a un super admin per mancanza di informazioni.
        #
        # ⚠️ `cache` non e' un'ottimizzazione facoltativa: `/me/` pubblica gia'
        #    `is_super_admin` nel profilo, e senza la cache condivisa questa
        #    riga interrogherebbe `script.fn_is_super_admin` una SECONDA volta
        #    nella stessa richiesta — due risposte che possono anche divergere,
        #    e la stessa schermata direbbe due cose sullo stesso utente.
        puo_scegliere = proprio is None
        if user is not None:
            puo_scegliere = puo_scegliere and PermissionResolver.is_super_admin(
                user, cache
            )
        mai_scelto = puo_scegliere and self._repo.get_preferenza(auth_user_id) is None
        descrizione: dict[str, Any] = {
            "emittente_fiscale_id": attivo_da_claim,
            "modalita_globale": attivo_da_claim is None,
            "puo_scegliere": puo_scegliere,
            "deve_scegliere": attivo_da_claim is None and mai_scelto,
        }
        # Chi e' l'emittente ATTIVO: nome e RUOLO (`soggetti_ruoli.id`).
        # Servono al FE per scrivere dentro l'emittente scelto dal super admin
        # — un listino si lega al ruolo dell'emittente, non alla sua PK — e per
        # dire all'operatore dove sta creando. Prima il FE li aveva solo per
        # l'emittente di PERMESSO (`emittente` di /me/), cioe' mai per il
        # super admin: il listino gli restava non creabile anche dopo la
        # scelta (2026-09-26). Chiavi additive; assenti in modalita' globale.
        if attivo_da_claim is not None:
            voci = self._repo.list_selezionabili(auth_user_id, solo_id=attivo_da_claim)
            if voci:
                descrizione["ragione_sociale"] = voci[0]["ragione_sociale"]
                descrizione["soggetto_ruolo_id"] = voci[0]["soggetto_ruolo_id"]
        # Perimetro EFFETTIVO della sessione: sta guardando piu' di un
        # emittente? Alimenta le etichette di perimetro su contatori e ricerca
        # (P-2c): «Da fatturare: 240.000 € — tutti gli emittenti» e'
        # informazione completa, mentre lo stesso numero senza etichetta non lo
        # e'. Chiave additiva.
        #
        # ⚠️ E' lo scope EFFETTIVO, cioe' gia' intersecato con l'emittente
        #    attivo: un super admin che ne ha scelto uno sta guardando UN
        #    perimetro, e l'etichetta non deve comparire. Da non confondere con
        #    `puo_scegliere`, che riguarda lo scope DI DIRITTO (vedi sotto).
        #
        # ⚠️ `user=None` -> chiave assente invece che `False`: senza l'oggetto
        #    utente non si puo' risolvere lo scope, e scrivere `False` direbbe
        #    «un solo emittente» a chi magari li ha tutti. Meglio non dire
        #    niente che dire una cosa non verificata.
        if user is not None and con_perimetro:
            descrizione["perimetro_multi_emittente"] = (
                perimetro_emittente.scope_multi_emittente(user, cache=cache)
            )
        return descrizione

    # Scopo: Opzioni della combo. Delega diretta: la lista è già filtrata dal
    #        DB sullo scope di diritto, quindi non serve nulla qui sopra.
    def opzioni(self, auth_user_id: int) -> list[dict[str, Any]]:
        return self._repo.list_selezionabili(auth_user_id)
