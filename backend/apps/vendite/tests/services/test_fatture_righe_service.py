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
19) FattureRigheServiceRettificaTests.test_rettifiche_di_righe_diverse_non_si_fondono
20) FattureRigheServiceRettificaTests.test_rettifiche_della_stessa_riga_di_fattura_si_sommano
21) FattureRigheServiceRettificaTests.test_prezzo_sconto_iva_copiati_dalla_riga_di_fattura
22) FattureRigheServiceRettificaTests.test_sconto_arriva_solo_dalla_riga_di_fattura
23) FattureRigheServiceRettificaTests.test_riga_rettificata_id_scritto_sulla_riga
24) FattureRigheServiceRettificaTests.test_rettifica_senza_puntatore_solleva
25) FattureRigheServiceRettificaTests.test_prezzo_mancante_sulla_riga_rettificata_solleva
26) FattureRigheServiceRettificaTests.test_riga_normale_non_porta_sconto_ne_puntatore
27) FattureRigheServiceRettificaTests.test_riga_nr_stabile_fra_due_generazioni
28) FattureRigheServiceRettificaTests.test_array_nuovi_allineati_agli_altri
29) FattureRigheServiceRettificaTests.test_puntatore_senza_etichetta_solleva
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
    def __init__(self, attivita=None, prezzi=None, fatture=None, iva=None,
                 rettifiche=None):
        self.insert_calls = 0
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
        # rettifiche per attivita_id: dict con la riga di fattura rettificata e
        # i tre valori COPIATI da quella riga (prezzo, sconto, iva). Sono
        # deliberatamente DIVERSI da quelli dell'attivita' nei test, perche' e'
        # l'unico modo di distinguere «li ha copiati» da «ha usato i suoi».
        self._rettifiche = rettifiche or {}

    def _make_group_input(self, attivita_id):
        rett = self._rettifiche.get(attivita_id) or {}
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
            tipo_movimento=rett.get("tipo_movimento", "NORMALE"),
            fattura_riga_rettificata_id=rett.get("riga_id"),
            rett_prezzo_unitario=rett.get("prezzo"),
            rett_sconto_percentuale=rett.get("sconto"),
            rett_iva_id=rett.get("iva"),
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


# Scopo: attività di RETTIFICA (nota di credito). La quantità è NEGATIVA a
# monte (D-NC-2: il segno sta nel numero, non in un'etichetta da tradurre) e i
# valori della riga di fattura rettificata sono DIVERSI da quelli dell'attività
# — è l'unico modo di distinguere «li ha copiati dal documento» da «ha usato i
# suoi», visto che in esercizio i due coincidono per costruzione.
def _rettifica(riga_fattura_id, prezzo="12.00", sconto="5.00", iva=4):
    return {
        "tipo_movimento": "RETTIFICA",
        "riga_id": riga_fattura_id,
        "prezzo": None if prezzo is None else Decimal(prezzo),
        "sconto": None if sconto is None else Decimal(sconto),
        "iva": iva,
    }


class FattureRigheServiceRettificaTests(SimpleTestCase):
    """La nota di credito: righe gemelle di righe di fattura (brief §12.6)."""

    # Scopo: il cuore di BE-4. Due rettifiche di righe di fattura DIVERSE non
    # devono fondersi, nemmeno quando articolo, prezzo, uom e IVA coincidono —
    # e qui coincidono tutti. La riga prodotta dalla fusione sarebbe «gemella di
    # nessuna», e l'invariante di N-1 («ogni riga di NC ha una riga di fattura
    # gemella») smetterebbe di essere vero per costruzione.
    def test_rettifiche_di_righe_diverse_non_si_fondono(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, quantita="-2.0"),
                _attivita_base(12, quantita="-3.0"),
            ],
            rettifiche={11: _rettifica(7001), 12: _rettifica(7002)},
        )
        _genera(repo)
        self.assertEqual(len(repo.last_kwargs["righe_nrs"]), 2)
        self.assertEqual(
            repo.last_kwargs["righe_rettificate"], [7001, 7002]
        )

    # Scopo: il verso opposto, ed è deliberato. Due rettifiche della STESSA riga
    # di fattura restano aggregabili: la riga prodotta è comunque la gemella di
    # quella riga, e il tetto «Σ|qta| ≤ qta rettificata» lo tiene il guard DB
    # `trgfn_resi_accrediti_guard`. Spezzarle darebbe due righe identiche sullo
    # stesso documento, che è più difficile da leggere e non più corretto.
    def test_rettifiche_della_stessa_riga_di_fattura_si_sommano(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, quantita="-2.0"),
                _attivita_base(12, quantita="-3.0"),
            ],
            rettifiche={11: _rettifica(7001), 12: _rettifica(7001)},
        )
        _genera(repo)
        self.assertEqual(len(repo.last_kwargs["righe_nrs"]), 1)
        self.assertEqual(repo.last_kwargs["righe_qtas"], [Decimal("-5.0")])
        self.assertEqual(repo.last_kwargs["righe_rettificate"], [7001])

    # Scopo: N-1 — «la nota di credito non può differire da quanto fatturato».
    # Prezzo, sconto e IVA arrivano dalla RIGA DI FATTURA, non dall'attività:
    # qui l'attività dice 10.50 / iva 22, la riga rettificata dice 12.00 /
    # sconto 5 / iva 4, e a vincere deve essere la seconda.
    def test_prezzo_sconto_iva_copiati_dalla_riga_di_fattura(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-2.0")],
            rettifiche={11: _rettifica(7001, prezzo="12.00", sconto="5.00", iva=4)},
        )
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_prezzi_unitari"], [Decimal("12.00")])
        self.assertEqual(repo.last_kwargs["righe_sconti"], [Decimal("5.00")])
        self.assertEqual(repo.last_kwargs["righe_iva_ids"], [4])

    # Scopo: lo sconto è l'unico dei tre che sull'attività NON esiste affatto —
    # la catena `commesse_attivita`/`attivita_fatturabili` non ha la colonna.
    # Se la lettura dalla riga di fattura sparisse, questo test è l'unico che se
    # ne accorgerebbe: gli altri due valori tornerebbero comunque giusti, perché
    # in esercizio coincidono.
    def test_sconto_arriva_solo_dalla_riga_di_fattura(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: _rettifica(7001, sconto="17.50")},
        )
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_sconti"], [Decimal("17.50")])

    # Scopo: BE-5 — la tracciabilità riga↔riga si scrive all'INSERT, perché
    # oltre la soglia DRAFT/EMESSA sulle righe di fattura non si può più fare
    # nulla: né UPDATE, né DELETE, né INSERT.
    def test_riga_rettificata_id_scritto_sulla_riga(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: _rettifica(7042)},
        )
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_rettificate"], [7042])

    # Scopo: una RETTIFICA senza il puntatore è una rottura di invariante, non
    # un caso da gestire con un ripiego: a valle si producono documenti fiscali,
    # e la riga nascerebbe gemella di nessuna. L'errore deve dire QUALE attività.
    def test_rettifica_senza_puntatore_solleva(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: {"tipo_movimento": "RETTIFICA", "riga_id": None}},
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn("11", exc.exception.detail)

    # Scopo: 🔴 il verso opposto della stessa coppia. Un puntatore alla riga
    # rettificata SENZA l'etichetta RETTIFICA farebbe copiare prezzo, sconto e
    # IVA dal documento su una riga che si dichiara normale — e nessuno saprebbe
    # perché quel prezzo non è quello dell'attività. Il cartellino e il puntatore
    # sono una coppia, e il guard deve essere simmetrico: la madre li scrive
    # sempre insieme, quindi se arrivano scompagnati la catena si è rotta a monte.
    def test_puntatore_senza_etichetta_solleva(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: {"tipo_movimento": "NORMALE", "riga_id": 7001,
                             "prezzo": Decimal("12.00")}},
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn("11", exc.exception.detail)

    # Scopo: il prezzo che si guarda è quello EFFETTIVO. Su una rettifica
    # l'attività può avere il suo prezzo valorizzato e la riga di fattura no:
    # guardare `gi.prezzo_unitario` lascerebbe passare proprio il caso che il
    # guard esiste per fermare, e l'INSERT cadrebbe su un NOT NULL anonimo.
    def test_prezzo_mancante_sulla_riga_rettificata_solleva(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: _rettifica(7001, prezzo=None)},
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")

    # Scopo: NON-regressione, ed è il test che protegge tutte le fatture del
    # mondo. Una riga normale non porta né sconto né puntatore: lo sconto resta
    # `None` e la INSERT lo fa collassare sul DEFAULT 0 del database, com'era
    # prima che questa colonna venisse nominata.
    def test_riga_normale_non_porta_sconto_ne_puntatore(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_sconti"], [None])
        self.assertEqual(repo.last_kwargs["righe_rettificate"], [None])

    # Scopo: il `riga_nr` deve essere lo stesso fra due generazioni dello stesso
    # lotto anche quando i gruppi si distinguono SOLO per la riga rettificata —
    # cioè quando articolo, prezzo, uom e IVA sono identici e l'unica differenza
    # è il documento che si sta rettificando. È il caso che l'ordinamento
    # precedente non sapeva discriminare.
    def test_riga_nr_stabile_fra_due_generazioni(self):
        def _ordine():
            repo = _RepoMock(
                attivita=[
                    _attivita_base(12, quantita="-3.0"),
                    _attivita_base(11, quantita="-2.0"),
                ],
                rettifiche={11: _rettifica(7001), 12: _rettifica(7002)},
            )
            _genera(repo)
            return repo.last_kwargs["righe_rettificate"]

        self.assertEqual(_ordine(), [7001, 7002])
        self.assertEqual(_ordine(), _ordine())

    # Scopo: tutti gli array passati all'INSERT devono restare allineati. Il
    # guard `E_BATCH_ARRAY_DISALLINEATI` vive nel repository (qui mockato), ma
    # se il servizio smettesse di riempire una delle due liste nuove il
    # disallineamento nascerebbe QUI — e `unnest` non lo direbbe: riempirebbe di
    # NULL le più corte, producendo righe di fattura silenziosamente sbagliate.
    def test_array_nuovi_allineati_agli_altri(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, quantita="-2.0"),
                _attivita_base(12, quantita="-3.0"),
                _attivita_base(13),
            ],
            rettifiche={11: _rettifica(7001), 12: _rettifica(7002)},
        )
        _genera(repo)
        atteso = len(repo.last_kwargs["righe_nrs"])
        for chiave in ("righe_sconti", "righe_rettificate"):
            self.assertEqual(len(repo.last_kwargs[chiave]), atteso, chiave)
