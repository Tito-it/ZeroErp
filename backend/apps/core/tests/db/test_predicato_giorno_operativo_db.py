# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il filtro per giorno (BB `predicato_giorno_operativo`) sul database
#        vero: il giorno e' quello dell'AZIENDA, il fuso della sessione non
#        conta, il predicato e' servibile da un indice sulla colonna, e ogni
#        sede che lo usa si attraversa coi filtri di data accesi.
#        Brief un-solo-fuso-aziendale B-4.
# Note: ⛔ Gli istanti si COSTRUISCONO a ±30 minuti dalla mezzanotte
#        aziendale, d'estate e d'inverno, in una tabella temporanea: un test
#        che leggesse le righe di oggi passerebbe a vuoto su un DB nuovo. Il
#        fuso e' quello vero del parametro, qualunque sia.
#        ⚠️ La prova dell'indice NON e' una scelta del planner sulla
#        popolazione: con `enable_seqscan = off` si chiede se il predicato
#        PUO' usare l'indice (struttura), con la controprova della forma
#        vecchia, `col::date`, che non puo'.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

SemanticaTests
 1. test_il_giorno_e_quello_dell_azienda            estate e inverno, da=a=D
 2. test_un_confine_solo                             solo da, solo a, nessuno
 3. test_il_fuso_della_sessione_non_conta            sessione a +14
 4. test_il_predicato_puo_usare_l_indice             + controprova col::date
GiunturaSediTests
 5. test_ogni_sede_si_attraversa_coi_filtri_di_data  le 12 sedi di §4.2 a
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest import TestCase

from django.db import connection

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.catalogo.db.catalogo_repository import CatalogoRepository
from apps.core.db._helpers import predicato_giorno_operativo
from apps.core.db.dbops_repository import DbopsRepository
from apps.core.db.email_repository import EmailRepository
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.db.permissions_audit_repository import PermissionsAuditRepository
from apps.core.services.coda_lavori.repository import CodaLavoriRepository
from apps.core.services.fuso_aziendale import fuso_aziendale, oggi_aziendale
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)
from apps.magazzino.db.magazzino_repository import MagazzinoRepository
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.db.vendite_repository import VenditeRepository

_ESTATE = date(2026, 7, 15)
_INVERNO = date(2026, 1, 15)


# Scopo: la mezzanotte AZIENDALE del giorno, come istante UTC.
def _mezzanotte(giorno: date) -> datetime:
    return datetime(giorno.year, giorno.month, giorno.day, tzinfo=fuso_aziendale()).astimezone(UTC)


class SemanticaTests(TestCase):
    """Il filtro sui confini costruiti."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: tabella temporanea con quattro istanti attorno al giorno `giorno`:
    #        1 = mezzanotte(D) − 30' (giorno prima), 2 = mezzanotte(D) + 30',
    #        3 = mezzanotte(D+1) − 30' (entrambi D), 4 = mezzanotte(D+1) + 30'.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("CREATE TEMP TABLE t_giorno (id int, quando timestamptz) ON COMMIT DROP")
            for giorno in (_ESTATE, _INVERNO):
                inizio, fine = _mezzanotte(giorno), _mezzanotte(giorno + timedelta(days=1))
                base = 10 if giorno == _ESTATE else 20
                for i, istante in enumerate((
                    inizio - timedelta(minutes=30), inizio + timedelta(minutes=30),
                    fine - timedelta(minutes=30), fine + timedelta(minutes=30),
                ), start=1):
                    cur.execute("INSERT INTO t_giorno VALUES (%s, %s)", [base + i, istante])

    # Scopo: gli id che il filtro tiene, fra quelli della stagione `base`.
    def _filtra(self, base: int, da: date | None, a: date | None) -> set[int]:
        sql, params = predicato_giorno_operativo("quando", da, a)
        with connection.cursor() as cur:
            cur.execute(
                f"SELECT id FROM t_giorno WHERE id BETWEEN %s AND %s AND {sql}",
                [base + 1, base + 4, *params],
            )
            return {r[0] for r in cur.fetchall()}

    # 1. Il giorno D tiene i due istanti di D e nessuno dei vicini, d'estate
    #    e d'inverno (offset diversi).
    def test_il_giorno_e_quello_dell_azienda(self) -> None:
        self.assertEqual(self._filtra(10, _ESTATE, _ESTATE), {12, 13})
        self.assertEqual(self._filtra(20, _INVERNO, _INVERNO), {22, 23})

    # 2. Un confine solo restringe da un lato; nessun confine non restringe.
    def test_un_confine_solo(self) -> None:
        self.assertEqual(self._filtra(10, _ESTATE, None), {12, 13, 14})
        self.assertEqual(self._filtra(10, None, _ESTATE), {11, 12, 13})
        self.assertEqual(self._filtra(10, None, None), {11, 12, 13, 14})

    # 3. ⭐ Una sessione a +14 (la mezzanotte della sessione e' 12-14 ore
    #    prima di quella aziendale) non cambia niente.
    def test_il_fuso_della_sessione_non_conta(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SET LOCAL TimeZone = 'Pacific/Kiritimati'")
        self.assertEqual(self._filtra(10, _ESTATE, _ESTATE), {12, 13})
        self.assertEqual(self._filtra(20, _INVERNO, _INVERNO), {22, 23})

    # 4. Il predicato sta sui confini: un indice sulla colonna lo serve. La
    #    forma vecchia `quando::date` no — e' la controprova che la domanda
    #    distingue.
    def test_il_predicato_puo_usare_l_indice(self) -> None:
        sql, params = predicato_giorno_operativo("quando", _ESTATE, _ESTATE)
        with connection.cursor() as cur:
            cur.execute("CREATE INDEX ix_t_giorno_quando ON t_giorno (quando)")
            cur.execute("SET LOCAL enable_seqscan = off")
            cur.execute(f"EXPLAIN SELECT id FROM t_giorno WHERE {sql}", params)
            piano = "\n".join(r[0] for r in cur.fetchall())
            cur.execute("EXPLAIN SELECT id FROM t_giorno WHERE quando::date = %s", [_ESTATE])
            piano_vecchio = "\n".join(r[0] for r in cur.fetchall())
        self.assertIn("ix_t_giorno_quando", piano)
        self.assertNotIn("ix_t_giorno_quando", piano_vecchio)


class GiunturaSediTests(TestCase):
    """Ogni sede del filtro per giorno si attraversa coi filtri accesi."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            self.user_id = apri_contesto_operatore(cur)

    # 5. ⭐ Le 12 sedi, con `da` e `a` accesi: un parametro fuori posto o una
    #    colonna sbagliata e' un errore SQL qui, non un 500 in produzione.
    #    (La semantica dei confini e' provata sopra, una volta, sul BB; il
    #    giornale la prova anche con una riga costruita in
    #    `vendite/tests/db/test_giornale_trasversale_perimetro`.)
    def test_ogni_sede_si_attraversa_coi_filtri_di_data(self) -> None:
        oggi = oggi_aziendale()
        ieri = oggi - timedelta(days=1)
        sedi: dict[str, Any] = {
            "giornale trasversale": lambda: VenditeRepository().list_giornale_trasversale(
                gravita=["ERROR"], data_da=ieri, data_a=oggi),
            "audit_log": lambda: DbopsRepository().list_audit_logs(date_from=ieri, date_to=oggi),
            "error_log": lambda: DbopsRepository().list_error_logs(
                data_da=ieri.isoformat(), data_a=oggi.isoformat()),
            "job_run_log": lambda: MaintenanceRepository().list_job_runs(date_from=ieri, date_to=oggi),
            "job_summary per mese": lambda: MaintenanceRepository().list_job_summary(
                meta_month_equals=("competenza", oggi.replace(day=1).isoformat())),
            "audit permessi": lambda: PermissionsAuditRepository().list_audit_events(
                auth_user_id=self.user_id, data_da=ieri, data_a=oggi),
            "audit amm_software": lambda: AmmSoftwareRepository().list_audit_log(data_da=ieri, data_a=oggi),
            "email log": lambda: EmailRepository().list_logs(data_da=ieri, data_a=oggi),
            "movimenti magazzino": lambda: MagazzinoRepository().list_movimenti(
                auth_user_id=self.user_id, data_da=ieri, data_a=oggi, limit=5, offset=0),
            "pratiche": lambda: PraticheRepository().list_pratiche(
                emittente_fiscale_id=0, data_da=ieri, data_a=oggi, limit=5, offset=0),
            "articoli": lambda: CatalogoRepository().list_articoli(
                attivo=None, is_composito=None, tipo_voce_id=None, gruppo_voce_id=None,
                listino_tipologia_id=None, search=None, data_da=ieri, data_a=oggi,
                order_by=None, order_dir=None, limit=5, offset=0),
            "coda lavori": lambda: CodaLavoriRepository().elenca(data_da=ieri, data_a=oggi),
            "coda stampa": lambda: VenditePipelineRepository().elenca_coda_stampa(data_da=ieri, data_a=oggi),
        }
        for nome, chiama in sedi.items():
            with self.subTest(sede=nome), connection.cursor() as cur:
                cur.execute("SAVEPOINT sede")
                try:
                    chiama()
                finally:
                    cur.execute("ROLLBACK TO SAVEPOINT sede")
