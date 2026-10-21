# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione bozze email (outbox): preparazione da template,
#        modifica, conferma invio, annullamento, allegati.
#        Le bozze sono editabili prima dell'invio effettivo.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_allegati_storage import percorso_allegato, radice_allegati
from apps.core.services.email_service import CANALE_CONSOLE, EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.service_errors import ServiceError
from apps.core.services.testata_guard import o_not_found

logger = logging.getLogger("zeroerp.email")

E_OUTBOX = "E_OUTBOX"
# La mail ha gia' il numero massimo di allegati: il file va bene, e' la mail a
# essere piena — uno stato, non un campo (409; R-7 di
# brief-db-codici-non-trovato-email-e-permessi). Tipo e dimensione del file
# restano `E_OUTBOX`: quelli sono dati errati.
E_EMAIL_ALLEGATI_LIMITE = "E_EMAIL_ALLEGATI_LIMITE"

# Campi della bozza che l'operatore puo' modificare (PATCH outbox). Coincide
# oggi con `EmailRepository._OUTBOX_UPDATE_COLS`, ma e' il contratto
# dell'operatore: puo' essere piu' stretto delle colonne scrivibili.
DRAFT_EDITABILI: frozenset[str] = frozenset({
    "oggetto", "corpo_html", "corpo_testo", "destinatario", "destinatari_cc",
})

# ⭐ «Gli allegati si toccano solo in bozza» e' una regola del DATABASE
#    (`config.trgfn_email_allegato_guard_solo_bozza`, 2026-09-25): il pre-check
#    qui sotto la dice PRIMA di scrivere il file su disco, e per questo usa il
#    codice del database (api.md, «un pre-check Python di una regola che il DB
#    fa rispettare usa il codice del DB»).
E_EMAIL_ALLEGATO_NON_BOZZA = "E_EMAIL_ALLEGATO_NON_BOZZA"

# ⭐ Le condizioni che `E_OUTBOX` accumulava e che non sono dati errati
#    (brief-db-codici-non-trovato-email-e-permessi §2 e §4, 2026-10-08):
#    `E_OUTBOX` resta per i soli dati errati (campi, tipo e dimensione file).
#    Fuori perimetro RLS e inesistente escono uguali: il 404 non rivela le
#    bozze degli altri.
E_EMAIL_BOZZA_NOT_FOUND = "E_EMAIL_BOZZA_NOT_FOUND"
E_EMAIL_NON_BOZZA = "E_EMAIL_NON_BOZZA"

ALLOWED_MIME_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/msword",
    "image/jpeg",
    "image/png",
    "image/gif",
    "text/plain",
    "text/csv",
})


# Scopo: «La mail e' ancora in bozza», o 409 `E_EMAIL_NON_BOZZA`. Una sede
#        per i tre verbi che la chiedono (modifica, invio, annullo: regola del
#        2, ok Tid 2026-10-09). Gli allegati hanno il loro codice, quello del
#        database (`E_EMAIL_ALLEGATO_NON_BOZZA`), e non passano di qui.
def _richiedi_bozza(outbox: dict[str, Any]) -> None:
    ErrorManager.require(
        outbox["stato"] == "DRAFT",
        code=E_EMAIL_NON_BOZZA,
        message=USER_MESSAGE_FALLBACK[E_EMAIL_NON_BOZZA],
        detail=f"email_outbox_id={outbox.get('id')} stato={outbox['stato']}",
    )


def _get_max_size_bytes() -> int:
    """Scopo: Ritorna la dimensione massima allegato in bytes, leggendo da settings a runtime."""
    mb = getattr(settings, "EMAIL_ATTACHMENT_MAX_SIZE_MB", 10)
    return mb * 1024 * 1024


def _get_max_count() -> int:
    """Scopo: Ritorna il numero massimo allegati per email, leggendo da settings a runtime."""
    return getattr(settings, "EMAIL_ATTACHMENT_MAX_COUNT", 10)


class EmailOutboxService:
    """Gestione bozze email: preparazione, modifica, invio, annullamento, allegati."""

    def __init__(self) -> None:
        self._repo = EmailRepository()
        self._dispatch = EmailDispatchService()

    # Scopo: La bozza per id, o 404 `E_EMAIL_BOZZA_NOT_FOUND` (id inesistente
    #        o fuori perimetro RLS: per il client la stessa cosa). ⭐ Sede unica
    #        della lettura «bozza o non trovato» (regola del 2, ok Tid
    #        2026-10-09): la usano i verbi qui sotto e le view che leggono la
    #        bozza senza un verbo (dettaglio, lista allegati). ⛔ Una view che
    #        chiama un verbo NON la rilegge prima: il controllo lo fa il verbo.
    def get_bozza(self, outbox_id: int) -> dict[str, Any]:
        return o_not_found(
            self._repo.get_outbox(outbox_id),
            code=E_EMAIL_BOZZA_NOT_FOUND,
            message=USER_MESSAGE_FALLBACK[E_EMAIL_BOZZA_NOT_FOUND],
            detail=f"email_outbox_id={outbox_id}",
        )

    # Scopo: Prepara una bozza email risolvendo template e account, pre-compilando
    #        oggetto e corpo con le variabili fornite. La bozza e' editabile.
    def prepare_draft(
        self,
        *,
        codice_template: str,
        destinatario: str,
        variabili: dict[str, Any],
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        lingua: str = "it",
        # ⛔ Senza default, ed e' il punto: `SISTEMA` come ripiego rendeva
        #    indistinguibile «non dichiarato» da «di sistema», proprio sulla
        #    colonna su cui il database decide chi puo' leggere.
        ambito: str,
        emittente_fiscale_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        creato_da_user_id: int | None = None,
        destinatari_cc: list[str] | None = None,
    ) -> dict[str, Any]:
        # Risolvi template + account + renderizza (metodo condiviso con EmailDispatchService)
        template, account, oggetto, corpo_html, corpo_testo = self._dispatch.resolve_and_render(
            codice_template=codice_template,
            variabili=variabili,
            unita_organizzativa_id=unita_organizzativa_id,
            tipo_prestazione_id=tipo_prestazione_id,
            lingua=lingua,
        )

        # Crea bozza
        outbox_id = self._repo.create_outbox(
            destinatario=destinatario,
            destinatari_cc=destinatari_cc,
            oggetto=oggetto,
            corpo_html=corpo_html,
            corpo_testo=corpo_testo,
            email_account_id=account["id"],
            email_template_id=template["id"],
            ambito=ambito,
            emittente_fiscale_id=emittente_fiscale_id,
            unita_organizzativa_id=unita_organizzativa_id,
            pratica_id=pratica_id,
            auth_user_id=auth_user_id,
            creato_da_user_id=creato_da_user_id,
            contesto_json=variabili,
        )

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Aggiorna campi editabili di una bozza DRAFT.
    # ⛔ Dal 2026-09-26 una chiave fuori `DRAFT_EDITABILI` e' un 400
    #    (`E_OUTBOX`), non piu' uno scarto silenzioso: un PATCH che «riesce»
    #    senza aver scritto il campo e' il difetto che non da' errore. Il
    #    repository, dietro, e' RIGIDO (RuntimeError): la regola dell'operatore
    #    si dice qui, prima. `destinatari_cc` va a una colonna `text[]`: lista
    #    di stringhe o null, altrimenti il cast del DB sarebbe un 500.
    # ⚠️ `outbox_id` e' positional-only: il corpo arriva come `**kwargs`, e un
    #    corpo `{"outbox_id": 1}` dava `TypeError: multiple values` — un 500 —
    #    invece del 400 delle chiavi fuori contratto.
    def update_draft(self, outbox_id: int, /, **kwargs: Any) -> dict[str, Any]:
        outbox = self.get_bozza(outbox_id)
        _richiedi_bozza(outbox)

        PayloadValidator(validation_code=E_OUTBOX).validate_allowed_keys(
            kwargs, allowed=DRAFT_EDITABILI, message="Campi della bozza non modificabili.",
        )
        cc = kwargs.get("destinatari_cc")
        ErrorManager.require(
            cc is None or (isinstance(cc, list) and all(isinstance(x, str) for x in cc)),
            code=E_OUTBOX,
            message="I destinatari in copia devono essere una lista di indirizzi.",
            detail=f"destinatari_cc={cc!r}",
        )
        # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
        #    2026-10-20, brief-be-verifica-documentazione-api §A2).
        PayloadValidator(validation_code=E_OUTBOX).require_campi_da_aggiornare(kwargs)
        self._repo.update_outbox(outbox_id, **kwargs)

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Conferma e invia una bozza via send_raw pubblico di EmailDispatchService.
    #        Crea email_log, copia allegati, aggiorna stato outbox.
    def confirm_and_send(self, outbox_id: int) -> dict[str, Any]:
        outbox = self.get_bozza(outbox_id)
        _richiedi_bozza(outbox)

        # Risolvi account per invio.
        # ⛔ PRIMA di portare a READY, non dopo: READY e' committato subito
        #    (autocommit, vedi sotto), e `cancel_draft` accetta solo DRAFT.
        #    Fino al 2026-09-28 l'ordine era inverso, e una bozza senza account
        #    restava READY — ne' rinviabile ne' annullabile (analisi difetti
        #    doc API core, F-1).
        account = self._dispatch.account_di_invio(outbox.get("unita_organizzativa_id"))

        # Porta a READY
        self._repo.update_outbox_stato(outbox_id, "READY")

        # Invio via metodo pubblico send_raw — crea log + invia
        log_id, success = self._dispatch.send_raw(
            account=account,
            destinatario=outbox["destinatario"],
            destinatari_cc=outbox.get("destinatari_cc"),
            oggetto=outbox["oggetto"],
            corpo_html=outbox["corpo_html"],
            corpo_testo=outbox.get("corpo_testo"),
            email_account_id=outbox["email_account_id"],
            email_template_id=outbox["email_template_id"],
            ambito=outbox["ambito"],
            unita_organizzativa_id=outbox.get("unita_organizzativa_id"),
            pratica_id=outbox.get("pratica_id"),
            auth_user_id=outbox.get("auth_user_id"),
            contesto_json=outbox.get("contesto_json"),
            # ⭐ La mail spedita resta dell'azienda e dell'AUTORE della bozza
            #    (D-5): chi preme «invia» non ne diventa l'autore — un super
            #    admin che spedisce la bozza di un altro non se la prende.
            emittente_fiscale_id=outbox.get("emittente_fiscale_id"),
            creato_da_user_id=outbox.get("creato_da_user_id"),
            allegati=outbox.get("allegati") or None,
        )

        # Fix analisi-fix-transazioni #16 (Classe C — saga/outbox). Lo stato READY
        # e' gia' committato PRIMA dello SMTP (autocommit sopra): l'invio esterno
        # sta fuori da qualunque transazione DB. I tre write POST-invio (link
        # outbox↔log + copia allegati + stato finale) vanno pero' fusi in UNA
        # transazione: prima erano autocommit separati, quindi un fallimento di
        # `copy_allegati_to_log` lasciava outbox READY + log linkato + allegati
        # mancanti (stato parziale). Ora o tutti e tre o nessuno: se il blocco
        # fallisce l'outbox resta READY "pulito". La riconciliazione dei READY
        # fantasma residui e' un follow-up (§Classe C, step 4): va progettata per
        # NON ri-inviare (lo SMTP e' gia' partito) — recupero idempotente, non
        # re-send. NB: l'email_log e' creato da send_raw (side-effect gia'
        # avvenuto) e non fa parte di questa tx.
        now = datetime.now(timezone.utc).isoformat()
        with transaction.atomic():
            self._repo.update_log_outbox_link(log_id, outbox_id)
            self._repo.copy_allegati_to_log(outbox_id, log_id)
            if success:
                # ⭐ La bozza segue l'esito della MAIL, non il fatto che la
                #    chiamata sia andata a buon fine: in console mode `send_raw`
                #    torna `True` ma la posta non e' partita, e scrivere `SENT`
                #    qui sarebbe **la stessa bugia una tabella piu' in la'** —
                #    con le due righe legate da `email_log_id`, quindi la
                #    divergenza si leggerebbe a occhio nudo (brief §7.1).
                # ⛔ E non vale dire «l'outbox parla del ciclo della bozza, non
                #    della consegna»: lo smentisce il ramo `else` qui sotto, che
                #    su fallimento riporta la bozza a `DRAFT` perche' l'operatore
                #    riprovi. Quella colonna parla di consegna.
                # ⚠️ LA DECISIONE E' PRESA DUE VOLTE, e va saputo: `send_raw`
                #    l'ha gia' presa per scrivere l'`email_log`, e qui si
                #    ri-deriva per la bozza. Oggi non possono divergere —
                #    `canale_invio` e' deterministico su (account, DEBUG) e le
                #    due chiamate stanno nella stessa richiesta — ma sono due
                #    sedi, e al primo canale nuovo che non spedisce andranno
                #    allineate insieme.
                # ⛔ **Leggere indietro lo stato scritto sarebbe PEGGIO**, ed e'
                #    la strada che sembra ovvia: `config.email_log` ha la RLS, e
                #    la policy sull'ambito `SISTEMA` pretende `fn_is_super_admin`
                #    — un operatore normale che conferma una bozza di sistema
                #    rileggerebbe **zero righe** e cadrebbe nel ramo sbagliato,
                #    cioe' uno zero per cecita' al posto di un dato.
                # ⇒ Il contratto che toglierebbe il doppione e' un `send_raw`
                #    che dice COSA HA SCRITTO invece di un booleano: `success`
                #    non basta a rappresentare tre esiti. E' un cambio di firma
                #    con due chiamanti, fuori dal perimetro di questo cantiere.
                if self._dispatch.canale_invio(account) == CANALE_CONSOLE:
                    # `inviato_at` non si passa: niente e' stato consegnato.
                    self._repo.update_outbox_stato(
                        outbox_id, "SIMULATA", email_log_id=log_id,
                    )
                else:
                    self._repo.update_outbox_stato(
                        outbox_id, "SENT", email_log_id=log_id, inviato_at=now,
                    )
            else:
                # Torna a DRAFT per permettere all'operatore di riprovare
                self._repo.update_outbox_stato(outbox_id, "DRAFT", email_log_id=log_id)

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Annulla una bozza DRAFT, togliendo i suoi allegati (righe e file).
    # ⛔ Le righe si tolgono PRIMA di scrivere `CANCELLED`, nella stessa
    #    transazione: il database ammette di toccare un allegato solo a bozza
    #    DRAFT (`config.trgfn_email_allegato_guard_solo_bozza`), quindi dopo
    #    l'annullo non si potrebbero piu' togliere. Fino al 2026-09-25 si
    #    cancellavano i soli file, e le righe restavano a puntare a file che
    #    non esistevano piu'.
    # ⚠️ I file si cancellano DOPO il commit: se la transazione fallisce le
    #    righe restano, e devono trovare il loro file.
    def cancel_draft(self, outbox_id: int) -> dict[str, Any]:
        outbox = self.get_bozza(outbox_id)
        _richiedi_bozza(outbox)

        with transaction.atomic():
            file_paths = self._repo.delete_allegati_by_outbox(outbox_id)
            self._repo.update_outbox_stato(outbox_id, "CANCELLED")
            transaction.on_commit(lambda: _delete_files(file_paths))

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Aggiunge un allegato a una bozza DRAFT, salvando il file su storage.
    def add_attachment(
        self,
        outbox_id: int,
        file_name: str,
        file_content: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        outbox = self.get_bozza(outbox_id)
        ErrorManager.require(
            outbox["stato"] == "DRAFT",
            code=E_EMAIL_ALLEGATO_NON_BOZZA,
            message=USER_MESSAGE_FALLBACK[E_EMAIL_ALLEGATO_NON_BOZZA],
            detail=f"stato={outbox['stato']}",
            context={"email_outbox_id": outbox_id, "stato": outbox["stato"], "operazione": "INSERT"},
        )

        # Validazioni
        ErrorManager.require(
            mime_type in ALLOWED_MIME_TYPES,
            code=E_OUTBOX, message=f"Tipo file '{mime_type}' non consentito.",
        )
        size = len(file_content)
        max_bytes = _get_max_size_bytes()
        ErrorManager.require(
            size <= max_bytes,
            code=E_OUTBOX, message=f"File troppo grande ({size} bytes, max {max_bytes}).",
        )
        current_count = len(outbox.get("allegati", []))
        max_count = _get_max_count()
        ErrorManager.require(
            current_count < max_count,
            code=E_EMAIL_ALLEGATI_LIMITE,
            message=USER_MESSAGE_FALLBACK[E_EMAIL_ALLEGATI_LIMITE],
            detail=f"allegati={current_count} max={max_count}",
        )

        # Salva file su storage
        root = radice_allegati()
        now = datetime.now(timezone.utc)
        sub_dir = os.path.join(str(now.year), f"{now.month:02d}")
        abs_dir = os.path.join(root, sub_dir)
        os.makedirs(abs_dir, exist_ok=True)

        ext = os.path.splitext(file_name)[1] or ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        abs_path = os.path.join(abs_dir, unique_name)
        rel_path = os.path.join(sub_dir, unique_name)

        with open(abs_path, "wb") as f:
            f.write(file_content)

        # ⚠️ Se il database rifiuta la riga (la bozza e' stata spedita fra il
        #    pre-check e l'INSERT: `E_EMAIL_ALLEGATO_NON_BOZZA`) il file appena
        #    scritto non ha piu' chi lo punta: si toglie, e l'errore risale.
        try:
            allegato_id = self._repo.create_allegato(
                email_outbox_id=outbox_id,
                nome_file=file_name,
                mime_type=mime_type,
                dimensione_bytes=size,
                file_path=rel_path,
                origine="UPLOAD",
            )
        except Exception:
            _delete_file(rel_path)
            raise

        return self._repo.get_allegato(allegato_id) or {}

    # Scopo: Rimuove un allegato (file + record DB).
    # ⚠️ Nessun controllo di stato qui, di proposito: «solo a bozza DRAFT» lo
    #    applica il database (`E_EMAIL_ALLEGATO_NON_BOZZA`, 409), e il rifiuto
    #    arriva prima che il file venga toccato. Fino al 2026-09-25 non lo
    #    controllava nessuno, e togliere un allegato da una mail spedita lo
    #    cancellava dalla storia del log.
    # ⚠️ Il file si cancella DOPO il commit, come in `cancel_draft`: se la
    #    transazione di chi chiama fallisce la riga torna, e deve trovare il
    #    suo file.
    def remove_attachment(self, allegato_id: int) -> bool:
        file_path = self._repo.delete_allegato(allegato_id)
        if file_path:
            transaction.on_commit(lambda: _delete_file(file_path))
            return True
        return False


# Scopo: Elimina file fisico da storage (ignora errori se non esiste).
# ⛔ Il percorso si risolve col BB `percorso_allegato`, come il download e
#    l'invio: con un `os.path.join` nudo un `file_path` assoluto o con `..`
#    (il valore viene dal database) faceva cancellare un file FUORI dalla radice.
#    Un percorso rifiutato non si cancella: si scrive nel log e si prosegue,
#    come per un file gia' assente.
def _delete_file(rel_path: str | None) -> None:
    if not rel_path or not rel_path.strip():
        return
    try:
        abs_path = percorso_allegato(rel_path)
    except ServiceError:
        logger.warning("Allegato non cancellato, percorso fuori radice: %r", rel_path)
        return
    try:
        os.remove(abs_path)
    except OSError:
        pass


# Scopo: cancella i file di una lista di percorsi (dopo il commit della
#        cancellazione delle righe), uno per uno e best-effort come `_delete_file`.
def _delete_files(rel_paths: Iterable[str | None]) -> None:
    for rel_path in rel_paths:
        _delete_file(rel_path)
