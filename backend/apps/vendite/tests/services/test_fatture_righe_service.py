"""
Indice test eseguiti:
1) FattureRigheServiceUnitTests.test_group_attivita_returns_group_key
2) FattureRigheServiceUnitTests.test_group_attivita_requires_id
3) FattureRigheServiceUnitTests.test_generate_fatture_righe_dry_run_counts_only
4) FattureRigheServiceUnitTests.test_generate_fatture_righe_writes_rows
5) FattureRigheServiceAggregazioneTests.test_stessa_chiave_produce_una_riga_sommata
6) FattureRigheServiceAggregazioneTests.test_prezzo_diverso_produce_due_righe
7) FattureRigheServiceAggregazioneTests.test_quantita_aggregata_non_arrotondata
8) FattureRigheServiceAggregazioneTests.test_sorgente_non_scritta_su_riga_aggregata
9) FattureRigheServiceAggregazioneTests.test_riga_nr_deterministico
10) FattureRigheServiceAggregazioneTests.test_marca_running_prima_di_generare
11) FattureRigheServiceKitTests.test_snapshot_kit_congelato_sulla_riga
12) FattureRigheServiceKitTests.test_componente_senza_padre_solleva
13) FattureRigheServiceKitTests.test_kit_diversi_non_si_fondono
14) FattureRigheServiceKitTests.test_quantita_kit_disomogenee_solleva
15) FattureRigheServiceKitTests.test_riga_normale_senza_colonne_kit
16) FattureRigheServiceKitTests.test_kit_con_iva_diverse_non_e_falso_positivo
17) FattureRigheServiceRobustezzaTests.test_prezzo_mancante_solleva_con_attivita_identificata
18) FattureRigheServiceRobustezzaTests.test_ordinamento_per_prezzo_e_numerico
"""

from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import AttivitaDaFatturare, GroupAttivitaInput
from apps.vendite.services import _kit_meta as kit_meta
from apps.vendite.services.fatture_righe_service import FattureRigheService

ART_A = "019d53f6-58ca-7cb7-b77b-86d201ce9787"
ART_B = "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa"
ART_PADRE = "019e2234-001d-72a4-bae6-308aba680e07"


# Scopo: Repository fittizio parametrizzabile — le attività e i loro group input
# sono iniettati dal test, così ogni caso descrive solo lo scenario che verifica.
class _RepoMock:
    # Scopo: Inizializza la istanza.
    def __init__(self, attivita=None, prezzi=None, fatture=None, iva=None):
        self.insert_calls = 0
        self.mark_calls = 0
        self.batch_insert_and_mark_calls = 0
        self.running_calls = 0
        self.last_kwargs: dict = {}
        self._attivita = attivita if attivita is not None else [_attivita_base(11)]
        # prezzo per attivita_id: consente di far divergere la chiave di gruppo.
        self._prezzi = prezzi or {}
        # fattura per attivita_id: default tutte sulla stessa testata.
        self._fatture = fatture or {}
        # iva per attivita_id: consente di far divergere la riga padre kit.
        self._iva = iva or {}

    def _make_group_input(self, attivita_id):
        return GroupAttivitaInput(
            attivita_id=attivita_id,
            articolo_id=self._articolo_di(attivita_id),
            dest_billing_account_id=200,
            uom_id=3,
            prezzo_unitario=(
                self._prezzi[attivita_id] if attivita_id in self._prezzi
                else Decimal("10.50")
            ),
            iva_id=self._iva.get(attivita_id, 22),
            competenza_dal=date(2026, 1, 1),
            competenza_al=date(2026, 1, 31),
            data_attivita=date(2026, 1, 10),
            calcolo_qta_padre="fissa",
            arrotondamento_importi_dec=2,
            arrotondamento_quantita_dec=3,
            metodo_arrotondamento_importi="HALF_UP",
            metodo_arrotondamento_quantita="HALF_UP",
        )

    def _articolo_di(self, attivita_id):
        for a in self._attivita:
            if a.id == attivita_id:
                return a.articolo_id
        return ART_A

    # Scopo: Recupera `group_attivita_input` dal contesto applicativo o dal database.
    def get_group_attivita_input(self, attivita_id):
        return self._make_group_input(attivita_id)

    # Scopo: Batch fetch di GroupAttivitaInput per lista di attivita_id.
    def batch_get_group_attivita_inputs(self, attivita_ids):
        return {aid: self._make_group_input(aid) for aid in attivita_ids}

    # Scopo: Restituisce elenco `attivita_da_fatturare` in base ai filtri disponibili.
    def list_attivita_da_fatturare(self, lotto_id):
        return list(self._attivita)

    # Scopo: Marca RUNNING le attività lockate sul lotto.
    def mark_attivita_running(self, lotto_id):
        self.running_calls += 1
        return len(self._attivita)

    # Scopo: Batch header creation per lista di attivita_id.
    def batch_get_or_create_fattura_headers(self, lotto_id, attivita_ids):
        return {aid: self._fatture.get(aid, 500) for aid in attivita_ids}

    # Scopo: Restituisce MAX(riga_nr) per lista di fattura_id.
    def get_max_riga_nrs(self, fattura_ids):
        return {fid: 0 for fid in fattura_ids}

    # Scopo: Gestisce `insert_fattura_riga` nel flusso applicativo del modulo.
    def insert_fattura_riga(self, **kwargs):
        self.insert_calls += 1
        return 900

    # Scopo: Gestisce `mark_attivita_fatturata` nel flusso applicativo del modulo.
    def mark_attivita_fatturata(self, attivita_id, fattura_riga_id):
        self.mark_calls += 1

    # Scopo: Batch INSERT righe + UPDATE attivita in un solo round-trip.
    def batch_insert_righe_and_mark(self, **kwargs):
        self.batch_insert_and_mark_calls += 1
        self.last_kwargs = kwargs
        return len(kwargs.get("att_ids", []))


# Scopo: Attività "normale" (non componente di kit) con quantità parametrica.
def _attivita_base(attivita_id, quantita="2.0", articolo_id=ART_A, meta=None):
    return AttivitaDaFatturare(
        id=attivita_id,
        articolo_id=articolo_id,
        quantita=Decimal(quantita),
        prezzo_unitario=Decimal("10.50"),
        uom_id=3,
        sorgente_tipo_id=1,
        sorgente_uid=f"SRC-{attivita_id}",
        sorgente_riga=attivita_id,
        articolo_descrizione="Articolo test",
        meta=meta,
    )


# Scopo: Attività componente di kit, con lo `meta` che il push ha già risolto.
def _attivita_kit(
    attivita_id,
    kit_riga,
    articolo_id=ART_A,
    quantita="2.0",
    padre=ART_PADRE,
    esposto=True,
):
    meta = {
        kit_meta.META_KEY_SEGMENT_KEY: kit_meta.segment_key_componente(
            f"ORD:019f7c7b-c434-735e-98b7-9564eb6a9626:R:{kit_riga}", articolo_id
        ),
        kit_meta.META_KEY_ESPOSTO_IN_FATTURA: esposto,
    }
    if padre is not None:
        meta[kit_meta.META_KEY_COMPONENTE_DI] = padre
    return _attivita_base(
        attivita_id, quantita=quantita, articolo_id=articolo_id, meta=meta
    )


# Scopo: Esegue la generazione neutralizzando la transazione (test senza DB).
def _genera(repo, *, dry_run=False):
    service = FattureRigheService(repository=repo)
    with patch(
        "apps.vendite.services.fatture_righe_service.transaction.atomic",
        return_value=nullcontext(),
    ):
        return service.generate_fatture_righe(99, dry_run=dry_run)


class FattureRigheServiceUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_group_attivita_returns_group_key`.
    def test_group_attivita_returns_group_key(self):
        service = FattureRigheService(repository=_RepoMock())
        result = service.group_attivita_fatturabili(11)
        self.assertEqual(result["articolo_id"], ART_A)
        self.assertEqual(result["dest_billing_account_id"], 200)
        self.assertEqual(result["competenza_dal"], "2026-01-01")
        self.assertEqual(result["competenza_al"], "2026-01-31")
        # Prezzo come stringa canonica: la chiave di gruppo deve essere esatta.
        self.assertEqual(result["prezzo_unitario"], "10.5")
        # `visibilita_componenti` è uscita dal modello il 2026-07-28.
        self.assertNotIn("visibilita_componenti", result)

    # Scopo: Verifica il caso `test_group_attivita_requires_id`.
    def test_group_attivita_requires_id(self):
        service = FattureRigheService(repository=_RepoMock())
        with self.assertRaises(ServiceError) as exc:
            service.group_attivita_fatturabili(None)  # type: ignore[arg-type]
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_VALIDATION")

    # Scopo: Verifica il caso `test_generate_fatture_righe_dry_run_counts_only`.
    def test_generate_fatture_righe_dry_run_counts_only(self):
        repo = _RepoMock()
        result = _genera(repo, dry_run=True)
        self.assertEqual(result, 1)
        self.assertEqual(repo.insert_calls, 0)
        self.assertEqual(repo.mark_calls, 0)
        self.assertEqual(repo.batch_insert_and_mark_calls, 0)
        # Nessun effetto collaterale: nemmeno la marcatura RUNNING.
        self.assertEqual(repo.running_calls, 0)

    # Scopo: Verifica il caso `test_generate_fatture_righe_writes_rows`.
    def test_generate_fatture_righe_writes_rows(self):
        repo = _RepoMock()
        result = _genera(repo)
        # Il ritorno conta le ATTIVITÀ elaborate, non le righe prodotte.
        self.assertEqual(result, 1)
        self.assertEqual(repo.batch_insert_and_mark_calls, 1)
        self.assertEqual(repo.last_kwargs["att_ids"], [11])


class FattureRigheServiceAggregazioneTests(SimpleTestCase):
    """Requisito D4: la riga di fattura è l'aggregazione di 1..n attività."""

    # Scopo: Due attività con la stessa chiave producono una riga sola.
    def test_stessa_chiave_produce_una_riga_sommata(self):
        repo = _RepoMock(attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")])
        result = _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(result, 2)
        self.assertEqual(len(kw["righe_nrs"]), 1)
        self.assertEqual(kw["righe_qtas"], [Decimal("8.0")])
        # Entrambe le attività puntano alla stessa riga (correlazione n→1).
        self.assertEqual(kw["att_ids"], [11, 12])
        self.assertEqual(kw["att_riga_nrs"], [1, 1])

    # Scopo: Il prezzo sta nella chiave: prezzi diversi non si fondono.
    def test_prezzo_diverso_produce_due_righe(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")],
            prezzi={12: Decimal("99.00")},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 2)
        self.assertEqual(sorted(kw["righe_qtas"]), [Decimal("3.0"), Decimal("5.0")])

    # Scopo: La somma delle quantità è esatta, mai arrotondata (D4-quantità).
    def test_quantita_aggregata_non_arrotondata(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, "0.333333"),
                _attivita_base(12, "0.333333"),
            ]
        )
        _genera(repo)
        # 0.666666 e NON 0.667: arrotondamento_quantita_dec=3 non si applica
        # all'aggregato.
        self.assertEqual(repo.last_kwargs["righe_qtas"], [Decimal("0.666666")])

    # Scopo: Con n sorgenti non ne esiste una singola da dichiarare.
    def test_sorgente_non_scritta_su_riga_aggregata(self):
        repo = _RepoMock(attivita=[_attivita_base(11), _attivita_base(12)])
        _genera(repo)
        # Il repository non riceve affatto le sorgenti: le scrive NULL in SQL.
        for chiave in ("sorgente_tipo_ids", "sorgente_uids", "sorgente_righe"):
            self.assertNotIn(chiave, repo.last_kwargs)

    # Scopo: L'ordine dei gruppi non segue l'ordine di arrivo delle attività.
    def test_riga_nr_deterministico(self):
        # Articolo B arriva per primo, ma A lo precede nell'ordinamento.
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, articolo_id=ART_B),
                _attivita_base(12, articolo_id=ART_A),
            ],
            prezzi={11: Decimal("10.50"), 12: Decimal("10.50")},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_articolo_ids"], [ART_A, ART_B])
        self.assertEqual(kw["righe_nrs"], [1, 2])

    # Scopo: Le attività entrano in lavorazione prima di produrre righe.
    def test_marca_running_prima_di_generare(self):
        repo = _RepoMock()
        _genera(repo)
        self.assertEqual(repo.running_calls, 1)


class FattureRigheServiceKitTests(SimpleTestCase):
    """Requisito D5: snapshot di esposizione kit congelato sulla riga."""

    # Scopo: Le 4 colonne kit arrivano dal `meta` già risolto dal push.
    def test_snapshot_kit_congelato_sulla_riga(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(
            kw["righe_kit_keys"],
            ["ORD:019f7c7b-c434-735e-98b7-9564eb6a9626:R:608"],
        )
        self.assertEqual(kw["righe_kit_articolo_padre_ids"], [ART_PADRE])
        self.assertEqual(kw["righe_kit_esposti"], [True])

    # Scopo: R11 — senza `componente_di` il componente si fatturerebbe due volte.
    def test_componente_senza_padre_solleva(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, padre=None)])
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_ATTIVITA_KIT_SENZA_PADRE")

    # Scopo: R7 — due istanze di kit non si fondono in una riga sola.
    def test_kit_diversi_non_si_fondono(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608),
                _attivita_kit(12, kit_riga=241),
            ]
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 2)
        self.assertEqual(len(set(kw["righe_kit_keys"])), 2)

    # Scopo: R10 — la vista stampa avg(qta): su quantità disomogenee sarebbe
    # una media senza significato, con il totale che torna lo stesso.
    def test_quantita_kit_disomogenee_solleva(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, articolo_id=ART_A, quantita="2.0"),
                _attivita_kit(12, kit_riga=608, articolo_id=ART_B, quantita="6.0"),
            ]
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_KIT_QUANTITA_DISOMOGENEE")

    # Scopo: Una riga non di kit non porta nessuna delle 4 colonne (CHECK
    # `chk_fatture_righe_kit_coerente`: tutte o nessuna).
    def test_riga_normale_senza_colonne_kit(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_kit_keys"], [None])
        self.assertEqual(kw["righe_kit_esposti"], [None])
        self.assertEqual(kw["righe_kit_articolo_padre_ids"], [None])

    # Scopo: R13 — componenti dello stesso kit con IVA diverse producono DUE
    # righe padre distinte nella vista, ognuna con la propria media: le loro
    # quantità NON vanno confrontate fra loro. Il guard R10 deve raggruppare
    # come la vista, altrimenti respinge una configurazione legittima.
    def test_kit_con_iva_diverse_non_e_falso_positivo(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, articolo_id=ART_A, quantita="2.0"),
                _attivita_kit(12, kit_riga=608, articolo_id=ART_B, quantita="6.0"),
            ],
            iva={12: 4},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 2)
        self.assertEqual(sorted(kw["righe_qtas"]), [Decimal("2.0"), Decimal("6.0")])


class FattureRigheServiceRobustezzaTests(SimpleTestCase):
    """Guard su dati incoerenti a monte."""

    # Scopo: `attivita_fatturabili.prezzo_unitario` è nullable ma
    # `fatture_righe.prezzo_unitario` è NOT NULL: l'errore deve dire QUALE
    # attività, non arrivare come IntegrityError anonimo dall'INSERT.
    def test_prezzo_mancante_solleva_con_attivita_identificata(self):
        repo = _RepoMock(attivita=[_attivita_base(11)], prezzi={11: None})
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn("11", exc.exception.detail)

    # Scopo: L'ordinamento dei gruppi confronta i valori nel loro tipo. Su
    # stringa '100' precederebbe '5' e il `riga_nr` seguirebbe un ordine
    # incomprensibile — deterministico, ma sbagliato da leggere.
    def test_ordinamento_per_prezzo_e_numerico(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, articolo_id=ART_A),
                _attivita_base(12, articolo_id=ART_A),
            ],
            prezzi={11: Decimal("100.00"), 12: Decimal("5.00")},
        )
        _genera(repo)
        self.assertEqual(
            repo.last_kwargs["righe_prezzi_unitari"],
            [Decimal("5"), Decimal("100")],
        )
