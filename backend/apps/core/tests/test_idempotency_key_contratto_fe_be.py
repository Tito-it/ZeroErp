# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio TRASVERSALE del contratto `Idempotency-Key` fra i due lati:
#        una rotta che dichiara `require_idempotency_key=True` e un chiamante
#        frontend che l'header non lo manda.
#
# 🔴 NASCE DA UN DIFETTO REALE, visto a video il 2026-09-08 e da nessun test.
#    Il verbo «togli dal giro» era completo — servizio, rotta, permesso, dialog,
#    esito a tre stati, 11 test verdi — e `escludiDocumentiDaGiro` non passava
#    l'header. Il backend rispondeva `E_IDEMPOTENCY_KEY_REQUIRED` e il verbo NON
#    PARTIVA: l'operatore scopriva il guasto dopo aver scritto il motivo, cioe'
#    dopo l'unico lavoro che quella dialog gli chiede.
#
# ⚠️ E PERCHE' NESSUN TEST LO VEDEVA, che e' la parte da ricordare: i test del
#    servizio chiamano la funzione Python, quelli della vista costruiscono la
#    richiesta a mano. L'header vive nel client `.js`, due strati piu' su di
#    entrambi — l'unico punto che nessuna delle due batterie attraversa. Un
#    difetto di CUCITURA non si trova stringendo i test dei pezzi.
#
# ⛔ IL PRESIDIO STA QUI E NON NEL FRONTEND, come il gemello sullo slot
#    `#actions` in `test_liste_configurabili_seed`: la meta' che sa QUALI rotte
#    pretendono l'header e' Python, e un cancello che vive dove sta solo meta'
#    del contratto non e' un cancello.
#
# ⭐ DAL 2026-10-20 IL CONTRATTO E' CAMBIATO DI FORMA (Tid, brief-be-verifica-
#    documentazione-api §A5): ogni POST che scrive pretende l'header per
#    costruzione (`_ApiViewBase.initial`), e il frontend lo mette su ogni
#    scrittura nell'interceptor di `core/api.js` (`applicaIdempotencyKey`).
#    Le 69 copie per chiamata sono ritirate. La cucitura che puo' rompersi
#    adesso e' un'altra: una scrittura che NON passa dall'istanza `api` (axios
#    diretto, `fetch`) parte senza interceptor, quindi senza header. Il
#    presidio guarda quella, e che l'interceptor ci sia e copra i quattro metodi.
#
# ⚠️ Nessun database: legge i sorgenti, quindi gira in CI.
# ------------------------------------------------------------
"""Indice test:

1. test_l_interceptor_mette_la_key_su_ogni_scrittura
   `core/api.js` registra `applicaIdempotencyKey` nell'interceptor di
   richiesta, e il BB copre POST, PUT, PATCH e DELETE.

2. test_nessuna_scrittura_aggira_l_istanza_api
   Una scrittura con axios diretto o `fetch` non passa dall'interceptor: il
   backend risponde `E_IDEMPOTENCY_KEY_REQUIRED` e il verbo non parte.

3. test_il_rilevamento_non_e_rotto
   ⛔ Un presidio che non trova niente PASSA, e passa per sempre: si pretende
   di aver visto davvero le scritture del frontend.
"""

from __future__ import annotations

import re
from unittest import TestCase

from apps.core.tests._repo import repo_root

_FRONTEND = repo_root() / "frontend/src"
_API_JS = _FRONTEND / "core/api.js"


# Scopo: i sorgenti del frontend che contano (niente spec).
def _sorgenti():
    for sorgente in [*_FRONTEND.rglob("*.js"), *_FRONTEND.rglob("*.vue")]:
        if ".spec." in sorgente.name:
            continue
        yield sorgente


class IdempotencyKeyContrattoFeBe(TestCase):
    """Il contratto dell'header, guardato dove si cuce."""

    def test_l_interceptor_mette_la_key_su_ogni_scrittura(self) -> None:
        testo = _API_JS.read_text()
        interceptor = testo[testo.index("api.interceptors.request.use"):]
        interceptor = interceptor[:interceptor.index("\n})") + 3]
        self.assertIn("applicaIdempotencyKey(config)", interceptor)
        metodi = re.search(r"METODI_CHE_SCRIVONO = new Set\(\[([^\]]*)\]\)", testo)
        self.assertIsNotNone(metodi)
        assert metodi is not None
        self.assertEqual(
            set(re.findall(r"'(\w+)'", metodi.group(1))), {"post", "put", "patch", "delete"},
        )

    def test_nessuna_scrittura_aggira_l_istanza_api(self) -> None:
        aggiranti = re.compile(
            r"axios\.(post|put|patch|delete|request)\s*\(|axios\s*\(\s*\{|"
            r"\bfetch\s*\([^)]*method\s*:",
        )
        colpevoli = sorted(
            f"{s.relative_to(_FRONTEND)}:{testo[:m.start()].count(chr(10)) + 1}"
            for s in _sorgenti()
            for testo in [s.read_text(errors="ignore")]
            for m in aggiranti.finditer(testo)
        )
        self.assertEqual(
            colpevoli, [],
            "scrittura che non passa dall'istanza `api` di `core/api.js`: niente "
            "interceptor, niente `Idempotency-Key`, e il backend rifiuta la POST "
            f"con `E_IDEMPOTENCY_KEY_REQUIRED`: {colpevoli}",
        )

    # ⚠️ Soglia BASSA di proposito: dice che il rilevamento e' vivo, non conta.
    def test_il_rilevamento_non_e_rotto(self) -> None:
        scritture = sum(
            len(re.findall(r"\bapi\.(post|put|patch|delete)\s*\(", s.read_text(errors="ignore")))
            for s in _sorgenti()
        )
        self.assertGreater(
            scritture, 100,
            "quasi nessuna scrittura del frontend trovata: il rilevamento e' "
            "rotto, e in quello stato il test 2 passerebbe sempre.",
        )
