# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB all'EMITTENTE ATTIVO di un utente — la scelta «dentro
#        quale emittente sto lavorando» dell'impersonazione di scope
#        (brief-db-impersonazione-scope-emittente §8.2).
#
#        Due sorgenti, una semantica:
#          - OPERATORE → `config.user_emittenti_fiscali`, che è un PERMESSO
#            (fissato nella sua configurazione, non modificabile da lui);
#          - SUPER_ADMIN → `config.user_emittente_attivo`, che è una
#            PREFERENZA (scelta al primo login, riproposta, modificabile).
#
#        ⚠️ La preferenza NON è un permesso: non allarga niente. Il DB
#        restringe leggendo la GUC `app.current_emittente_id`, e la regola
#        «solo restringente, mai allargante» vive nelle funzioni di scope
#        (`fn_check_user_emittente_scope` & c.), non qui.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.db import connection, transaction


# Scopo: Un cursore che vede lo scope di DIRITTO dell'utente: la GUC
#        dell'emittente attivo e' vuota finche' il blocco e' aperto, e torna
#        quella di prima alla sua chiusura.
#
#        ⛔ Il ripristino e' esplicito, e non e' un di piu': `SET LOCAL` si
#        annulla al commit della transazione ESTERNA, non all'uscita di
#        `transaction.atomic()`, che dentro una richiesta e' un savepoint.
#        Dal 2026-09-25 `SolaLetturaMiddleware` apre una transazione attorno a
#        ogni GET: in `/me/` la GUC restava vuota per il resto della
#        richiesta, e il perimetro calcolato dopo diceva «tutti gli emittenti»
#        a chi ne aveva scelto uno.
#        Su un errore non serve ripristinare: il rollback del blocco annulla
#        anche il `SET LOCAL`.
@contextmanager
def _cursore_scope_di_diritto() -> Iterator[Any]:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_setting('app.current_emittente_id', true), "
                "set_config('app.current_emittente_id', '', true)"
            )
            precedente = cursor.fetchone()[0]
            yield cursor
            cursor.execute(
                "SELECT set_config('app.current_emittente_id', %s, true)",
                [precedente or ""],
            )


class EmittenteAttivoRepository:
    """Preferenza «emittente attivo» + validazione della scelta."""

    # Scopo: Emittente che l'utente ha per PERMESSO (riga in
    #        `config.user_emittenti_fiscali`), o None se non ne ha — il caso
    #        del super admin, che infatti sceglie.
    #
    #        ⚠️ Lettura DIRETTA della tabella, non `fn_resolve_emittente_for_user`:
    #        dal 2026-08-04 quel resolver guarda PRIMA la GUC dell'emittente
    #        attivo, che è esattamente il valore che stiamo per calcolare. Usarlo
    #        qui sarebbe circolare — risponderebbe «il tuo emittente è quello che
    #        hai già attivo», e al login (GUC vuota) direbbe None a chiunque.
    #        Stessa scelta, e stesso motivo di indipendenza, di
    #        `ParameterRepository.get_emittente_fiscale_id_for_user`.
    def get_emittente_di_permesso(self, auth_user_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT emittente_fiscale_id
                  FROM config.user_emittenti_fiscali
                 WHERE auth_user_id = %s
                 LIMIT 1
                """,
                [auth_user_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Emittente preferito persistito per l'utente (super admin), o None
    #        se non ha mai scelto. Nessun filtro di validità qui: la riga può
    #        puntare a un emittente nel frattempo disattivato, e distinguere
    #        «non ha mai scelto» da «la scelta è decaduta» è compito del
    #        service (la prima impone la scelta, la seconda la ripropone).
    def get_preferenza(self, auth_user_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT emittente_fiscale_id
                  FROM config.user_emittente_attivo
                 WHERE auth_user_id = %s
                """,
                [auth_user_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Salva (o aggiorna) la preferenza. UPSERT sull'UNIQUE auth_user_id.
    #        L'UPDATE tocca la riga anche quando il valore non cambia: è
    #        voluto — la storicizzazione registra così ogni conferma esplicita
    #        della scelta, non solo i cambi di valore.
    def set_preferenza(self, auth_user_id: int, emittente_fiscale_id: int) -> None:
        # Dal 2026-10-18 (2b-2, lotto 9) la madre del DB
        # `config.fn_imposta_emittente_attivo`: lo stesso UPSERT, una sede.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT config.fn_imposta_emittente_attivo(%s::integer, %s::bigint)",
                [auth_user_id, emittente_fiscale_id],
            )

    # Scopo: Rimuove la preferenza — la scelta è decaduta (emittente
    #        disattivato o uscito dallo scope) e va rifatta al prossimo login.
    def delete_preferenza(self, auth_user_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_emittente_attivo WHERE auth_user_id = %s",
                [auth_user_id],
            )
            return cursor.rowcount > 0

    # Scopo: L'utente può lavorare dentro questo emittente? Due condizioni:
    #        l'emittente esiste ed è ATTIVO, e rientra nello scope di diritto
    #        dell'utente (super admin: qualunque; operatore: la sua whitelist).
    #
    #        ⚠️ Lo scope di DIRITTO, col cursore `_cursore_scope_di_diritto`:
    #        dal 2026-08-04 `fn_check_user_emittente_scope` **legge la GUC** e
    #        nega tutto ciò che non coincide con l'emittente corrente. Senza
    #        azzerarla, un super admin dentro A che chiede «posso passare ad
    #        B?» si sentirebbe rispondere di no — e resterebbe prigioniero
    #        della sua stessa scelta.
    #
    #        La canonica resta l'unica sede della regola: qui si toglie di
    #        mezzo il filtro di sessione per interrogare lo scope di DIRITTO,
    #        non si riscrive il criterio.
    def is_scelta_valida(self, auth_user_id: int, emittente_fiscale_id: int) -> bool:
        with _cursore_scope_di_diritto() as cursor:
            cursor.execute(
                """
                SELECT ef.attivo
                   AND script.fn_check_user_emittente_scope(%s, ef.id)
                  FROM anagrafiche.emittenti_fiscali ef
                 WHERE ef.id = %s
                """,
                [auth_user_id, emittente_fiscale_id],
            )
            row = cursor.fetchone()
        return bool(row[0]) if row else False

    # Scopo: Emittenti fra cui l'utente può scegliere — alimenta la combo di
    #        topbar e il dialog della scelta iniziale. Stesso criterio della
    #        validazione (scope di diritto + attivo), quindi ciò che è
    #        proposto è per costruzione accettato da `is_scelta_valida`.
    #        Nome e codice arrivano dal soggetto, coerenti con il resto
    #        dell'app (`brief-emittente-ragione-sociale-dal-soggetto`).
    #
    #        `solo_id`: la sola voce di quell'emittente — i dati dell'emittente
    #        ATTIVO per `/me/` (ruolo e nome) passano da qui, con lo stesso
    #        criterio di scope, invece che da una seconda query.
    def list_selezionabili(
        self, auth_user_id: int, solo_id: int | None = None
    ) -> list[dict[str, Any]]:
        with _cursore_scope_di_diritto() as cursor:
            cursor.execute(
                """
                SELECT ef.id,
                       ef.codice,
                       s.ragione_sociale_completa,
                       ef.soggetto_ruolo_id
                  FROM anagrafiche.emittenti_fiscali ef
                  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
                  JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
                 WHERE ef.attivo
                   AND script.fn_check_user_emittente_scope(%s, ef.id)
                   AND (%s::bigint IS NULL OR ef.id = %s::bigint)
                 ORDER BY s.ragione_sociale_completa, ef.codice
                """,
                [auth_user_id, solo_id, solo_id],
            )
            rows = cursor.fetchall()
        return [
            {
                "emittente_fiscale_id": int(r[0]),
                "codice": r[1],
                "ragione_sociale": r[2],
                # Il ruolo dell'emittente (`soggetti_ruoli.id`), NON la PK:
                # e' la chiave dei listini (`emittente_soggetto_ruolo_id`).
                "soggetto_ruolo_id": int(r[3]),
            }
            for r in rows
        ]
