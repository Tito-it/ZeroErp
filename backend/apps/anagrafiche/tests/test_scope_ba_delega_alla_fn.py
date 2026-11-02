# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello sulla regola «di quale emittente e' questo billing
#        account?». La regola vive in UN posto — `script.fn_get_ba_emittente_sr_id`,
#        interrogata dal backend attraverso `script.fn_check_ba_visible_for_emittenti`
#        — e questo test vieta di riscriverla a mano in una query Python.
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

1. test_nessuna_query_decide_da_sola_di_chi_e_un_ba
   Nessun sorgente applicativo legge `emittenti_fiscali_billing_account` per
   confrontare l'emittente del mapping con la whitelist `= ANY(...)`. Registro
   a ZERO.
2. test_i_quattro_repository_delegano_ancora
   Il verso opposto: i quattro repository con uno scope BA nominano la fn. Se
   uno smettesse — togliendo il filtro invece di riscriverlo — il test 1
   resterebbe verde su uno scope sparito.

⛔ PERCHE' ESISTE. Fino al 2026-09-13 la regola stava INLINE in TRE query —
   `clienti_repository.list_clienti` e due punti di `soggetti_repository` —
   nella forma «mapping specifico, altrimenti il default se il BA non ha
   mapping», con un commento che la dichiarava «identica alla fn canonica».
   Quel giorno il DB (changeSet `20260913-01`, D13) ha dato alla regola un
   terzo livello: in sessione un BA senza legame e' dell'OPERATORE che sta
   agendo, non del default. Le tre copie sarebbero rimaste alla regola
   vecchia, e nessuna lista avrebbe mentito **oggi** — divergono solo su un BA
   senza legame in sessione, un istante o un seed — cioe' la forma esatta in
   cui due regole si sfilano in silenzio. Le tre sono state portate sulla fn,
   come gia' facevano `billing_account_repository` e
   `istanze_utility_repository` dal 2026-07-13.
   Brief: brief-db-ba-riserva-emittente-operatore-d13.md §6.2.

⚠️ La forma vietata e' STRETTA di proposito, e va detto cosa NON vieta:
   - `parameter_repository` legge il mapping con `billing_account_id IS NULL
     AND is_default = true`: cerca il GESTORE GLOBALE, non decide di un BA;
   - `registri_repository` confronta `registri_numerazione.emittente_soggetto_ruolo_id`
     con la whitelist: il registro ha il SUO emittente, non passa dal BA;
   - `emittenti_fiscali_repository` e' il CRUD del mapping stesso.
   Nessuna di queste confronta l'emittente DEL MAPPING con la whitelist: e'
   quel confronto — e solo quello — la regola ricopiata.
"""

import re
from unittest import TestCase

from apps.core.tests._repo import repo_root, sorgente_senza_commenti

# ⛔ I sorgenti si leggono SENZA commenti (`sorgente_senza_commenti`): la prosa
#    che racconta la regola vecchia sta proprio nei file che questo test
#    scandisce — `#` in Python e `--` dentro le stringhe SQL.

# La forma vietata: leggere `anagrafiche.emittenti_fiscali_billing_account` e,
# entro poche righe, confrontare il SUO `emittente_soggetto_ruolo_id` con la
# whitelist `= ANY(` — cioe' «questo mapping e' verso uno dei MIEI emittenti?»,
# deciso a mano. Due forme, perche' SQL ammette entrambe:
#  A) con alias — catturato e ri-usato (`\1`), cosi' il divieto non dipende da
#     come si chiama e non scatta su due letture indipendenti nello stesso file;
#  B) senza alias — la colonna nuda (nessun `.` davanti) dopo il `WHERE`.
_FORME_VIETATE = (
    ("A", re.compile(
        r"emittenti_fiscali_billing_account\s+(?:AS\s+)?(?!WHERE\b|JOIN\b|ON\b)(\w+)\b"
        r"[\s\S]{0,400}?"
        r"\b\1\.emittente_soggetto_ruolo_id\s*=\s*ANY\s*\(",
        re.IGNORECASE,
    )),
    ("B", re.compile(
        r"emittenti_fiscali_billing_account\s+WHERE\b"
        r"[\s\S]{0,400}?"
        r"(?<![\w.])emittente_soggetto_ruolo_id\s*=\s*ANY\s*\(",
        re.IGNORECASE,
    )),
)

# ⛔ REGISTRO DEL DEBITO — **zero voci**, e deve restare tale.
_DEBITO: dict[str, int] = {}

# I repository che portano uno scope BA e lo delegano alla fn. Se ne nasce un
# quinto, si aggiunge qui: la lista e' cio' che il test 2 pretende.
_DELEGANO = (
    "backend/apps/anagrafiche/db/billing_account_repository.py",
    "backend/apps/anagrafiche/db/clienti_repository.py",
    "backend/apps/anagrafiche/db/istanze_utility_repository.py",
    "backend/apps/anagrafiche/db/soggetti_repository.py",
)
_FN = "script.fn_check_ba_visible_for_emittenti("


class ScopeBaDelegaAllaFnTests(TestCase):

    # Scopo: I sorgenti applicativi da scandire. ⚠️ I `tests/` restano FUORI.
    def _sorgenti(self):
        root = repo_root()
        for percorso in sorted((root / "backend" / "apps").rglob("*.py")):
            rel = percorso.relative_to(root).as_posix()
            if "/tests/" in rel:
                continue
            yield rel, percorso

    # 1. Il cancello.
    def test_nessuna_query_decide_da_sola_di_chi_e_un_ba(self):
        trovate: dict[str, int] = {}
        dettaglio: list[str] = []
        for rel, percorso in self._sorgenti():
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            for nome, rx in _FORME_VIETATE:
                for m in rx.finditer(testo):
                    trovate[rel] = trovate.get(rel, 0) + 1
                    riga = testo.count("\n", 0, m.start()) + 1
                    dettaglio.append(f"  {rel}:{riga} [forma {nome}] mapping confrontato con ANY(...)")

        nuove = {k: n for k, n in trovate.items() if n > _DEBITO.get(k, 0)}
        self.assertFalse(
            nuove,
            "Una query decide a mano di quale emittente e' un billing account"
            " (mapping confrontato con la whitelist). La regola vive nel DB e"
            " ha TRE livelli: usare `script.fn_check_ba_visible_for_emittenti("
            "<ba_id>, %s::bigint[])` come gli altri quattro repository.\n"
            + "\n".join(dettaglio),
        )

    # 2. ⚠️ Il verso opposto: togliere il filtro non e' delegarlo.
    def test_i_quattro_repository_delegano_ancora(self):
        root = repo_root()
        for rel in _DELEGANO:
            testo = sorgente_senza_commenti((root / rel).read_text(encoding="utf-8"))
            self.assertIn(
                _FN,
                testo,
                f"{rel} non chiama piu' `{_FN}`: o lo scope emittente sui BA e'"
                " sparito da quella query, o e' stato riscritto altrove. In"
                " entrambi i casi non e' questo il modo.",
            )
