# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — GENERA `apps/core/services/error_policies_generated.py`
#        dal catalogo dei codici errore. E' il passo B-5 del
#        `piano-be-classe-codici-errore.md`: toglie la scrittura a mano
#        all'unico elenco che restava, non ne aggiunge uno.
#
#        USO:
#          ./manage-env.sh genera_error_policies            # riscrive il modulo
#          ./manage-env.sh genera_error_policies --check    # non scrive: dice se diverge
#
#        LA SORGENTE E' UNA VISTA, E NON E' UN DETTAGLIO.
#        `config.vw_codici_errore_identita` ha **una riga per codice**.
#        ⛔ NON usare `config.vw_codici_errore`: e' la vista di *revisione*, ha una
#        riga per (codice, lingua) e — essendo un LEFT JOIN — un codice senza
#        messaggio ci compare con `lingua IS NULL`. Filtrarla per `lingua = 'it'`
#        perderebbe proprio quei codici, e li perderebbe **in silenzio**: non un
#        errore, righe che spariscono. E' la forma di guasto contro cui e'
#        costruito tutto questo filone.
#
#        L'`ORDER BY codice` c'e' **due volte**, qui e dentro la vista, e non e'
#        una ridondanza da togliere: un requisito che vive in un posto solo si
#        dimentica. Senza, PostgreSQL non promette niente fra due esecuzioni
#        identiche, il file produce **diff spurii da riordino**, diventa un file
#        che nessuno rilegge — e da li' a non accorgersi di una CLASSE CAMBIATA
#        e' un passo solo.
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from django.core.management.base import CommandError
from apps.core.management.comando_aziendale import ComandoAziendale
from django.db import connection

# Il modulo prodotto. Sta accanto al registro che lo legge.
DESTINAZIONE = (
    Path(__file__).resolve().parents[3] / "core" / "services" / "error_policies_generated.py"
)

# Una riga per codice, nessun join, nessun filtro lingua da sbagliare.
QUERY = """
    SELECT codice, classe, obsoleto_dal, note
      FROM config.vw_codici_errore_identita
     ORDER BY codice
"""

_INTESTAZIONE = '''\
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la mappa `codice errore -> classe`. E' l'identita' di ogni codice: che
#        COSA e' l'errore (non esiste / conflitto di stato / dato sbagliato /
#        guasto...), non come si risponde. Lo status HTTP e la ui_action si
#        derivano dalla classe in `error_policies.py`.
# Generato da: `manage.py genera_error_policies`, da
#        `config.vw_codici_errore_identita`.
#        ⛔ NON MODIFICARE A MANO: la prossima rigenerazione butta via tutto.
#        Per cambiare la classe di un codice si cambia il CATALOGO
#        (`db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv`) e si
#        rigenera. Il commento sopra ogni voce e' la sua `note` a catalogo.
# Note: ⚠️ Le voci sono {n_codici}, di cui {n_ritirati} RITIRATE. Un codice
#        ritirato resta qui e continua a risolvere, ed e' voluto: il diario
#        (`dbops.error_log`) contiene le sue righe e devono restare leggibili.
#        `obsoleto_dal` non e' `attivo = false`.
#        ⚠️ L'ordine e' alfabetico per codice — lo stesso `ORDER BY` della vista.
#        Un riordino qui e' un diff spurio, e un file con diff spurii non lo
#        rilegge piu' nessuno.
# ------------------------------------------------------------


# Una riga per codice. Il valore e' una classe di `config.classi_errore`.
CLASSE_PER_CODICE: dict[str, str] = {{
'''

_CODA_RITIRATI = '''\

# I codici che il catalogo ha ritirato. Risolvono ancora — il diario li contiene
# — ma NESSUN punto di chiamata nuovo deve nominarli: lo presidia
# `test_error_codes_declared_guardrail`.
CODICI_RITIRATI: frozenset[str] = frozenset(
    {{
{righe}
    }}
)
'''


# Scopo: la stringa Python per un valore di testo. Doppi apici quando si puo',
#        `repr` quando il testo ne contiene: il file lo si rilegge a mano.
def _lit(testo: str) -> str:
    return f'"{testo}"' if '"' not in testo else repr(testo)


# Scopo: rende il modulo a partire dalle righe della vista. Funzione PURA — non
#        tocca il database e non scrive niente — perche' e' quella che il
#        controllo di divergenza (B-6) deve poter eseguire per confrontare.
def rendi_modulo(righe: list[tuple]) -> str:
    ritirati = [r[0] for r in righe if r[2] is not None]
    fuori = [
        _INTESTAZIONE.format(n_codici=len(righe), n_ritirati=len(ritirati))
    ]
    for codice, classe, obsoleto_dal, note in righe:
        if note:
            # La `note` a catalogo e' su una riga sola (D18, e c'e' un CHECK che
            # lo impone): qui non serve avvolgerla, serve non spezzarla.
            fuori.append(f"    # {note}")
        if obsoleto_dal is not None:
            fuori.append(f"    # ⚠️ RITIRATO il {obsoleto_dal.isoformat()}")
        fuori.append(f'    {_lit(codice)}: "{classe}",')
    fuori.append("}")
    righe_ritirati = "\n".join(f"        {_lit(c)}," for c in ritirati)
    fuori.append(_CODA_RITIRATI.format(righe=righe_ritirati))
    return "\n".join(fuori)


# Scopo: ⭐ IL COLLAUDO DEL PRODOTTO, PRIMA DI SCRIVERLO. Esegue il testo reso in
#        uno spazio dei nomi isolato e verifica che contenga davvero i due
#        dizionari, con i conti giusti.
#
#        ⚠️ NON E' PRUDENZA GENERICA, e' un difetto gia' pagato: alla prima
#        esecuzione questo generatore ha scritto un `frozenset(...)` con 79
#        argomenti invece di un insieme. Il file non si importava piu' — e siccome
#        e' `apps.core.services` a importarlo, **Django non partiva**, quindi
#        nemmeno questo comando: il generatore si era murato fuori dalla stanza,
#        e per rientrare serviva ripristinare il file a mano.
#
#        Un `compile()` non sarebbe bastato: quello era un errore di RUNTIME, non
#        di sintassi. Bisogna eseguirlo davvero — ed e' sicuro, il modulo e' fatto
#        di soli letterali.
def verifica_prodotto(testo: str, righe: list[tuple]) -> None:
    spazio: dict = {}
    try:
        exec(compile(testo, str(DESTINAZIONE), "exec"), spazio)  # noqa: S102
    except Exception as exc:  # pragma: no cover — difende da una regressione del renderer
        raise CommandError(
            f"il modulo generato non si importa ({type(exc).__name__}: {exc}). "
            "NON e' stato scritto: un file rotto qui impedisce l'avvio di Django, "
            "e quindi anche di questo comando."
        ) from exc

    classi = spazio.get("CLASSE_PER_CODICE")
    ritirati = spazio.get("CODICI_RITIRATI")
    attesi_ritirati = sum(1 for r in righe if r[2] is not None)
    if not isinstance(classi, dict) or len(classi) != len(righe):
        raise CommandError(
            f"il modulo generato ha {len(classi) if isinstance(classi, dict) else '?'} "
            f"voci invece di {len(righe)}: il renderer ha perso righe per strada."
        )
    if not isinstance(ritirati, frozenset) or len(ritirati) != attesi_ritirati:
        raise CommandError(
            f"CODICI_RITIRATI ha {len(ritirati) if isinstance(ritirati, frozenset) else '?'} "
            f"voci invece di {attesi_ritirati}."
        )


# Scopo: legge la vista di identita'. Separata dal rendering perche' e' l'unico
#        pezzo che vuole un database.
def leggi_identita() -> list[tuple]:
    with connection.cursor() as cur:
        cur.execute(QUERY)
        righe = cur.fetchall()
    if not righe:
        raise CommandError(
            "config.vw_codici_errore_identita e' VUOTA. Un generatore che scrive "
            "un file vuoto cancella 689 decisioni senza dire niente: meglio "
            "fermarsi. Verificare che il seed (DB D-5) sia applicato."
        )
    return righe


class Command(ComandoAziendale):
    help = (
        "Genera apps/core/services/error_policies_generated.py da "
        "config.vw_codici_errore_identita. Con --check non scrive: esce 1 se il "
        "file sul disco diverge dal catalogo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Non scrive: confronta il file esistente col catalogo e fallisce "
                 "se divergono. E' la forma usata in CI.",
        )

    def handle(self, *args, **options):
        righe = leggi_identita()
        atteso = rendi_modulo(righe)
        verifica_prodotto(atteso, righe)
        attuale = DESTINAZIONE.read_text(encoding="utf-8") if DESTINAZIONE.exists() else ""

        if options["check"]:
            if atteso == attuale:
                self.stdout.write(self.style.SUCCESS("error_policies_generated.py allineato al catalogo."))
                return
            raise CommandError(
                "error_policies_generated.py DIVERGE dal catalogo. "
                "Rigenerare con `manage.py genera_error_policies` e committare il "
                "risultato — oppure, se la divergenza non ci si aspettava, "
                "guardare cosa e' cambiato a catalogo prima di rigenerare."
            )

        if atteso == attuale:
            self.stdout.write("Nessuna modifica: era gia' allineato.")
            return
        DESTINAZIONE.write_text(atteso, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Scritto {DESTINAZIONE}"))
