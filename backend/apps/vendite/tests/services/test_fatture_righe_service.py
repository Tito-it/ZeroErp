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
9) FattureRigheServiceAggregazioneTests.test_riga_nr_ordina_per_codice_articolo
9b) FattureRigheServiceAggregazioneTests.test_riga_nr_stabile_al_variare_dell_ordine_di_arrivo
9c) FattureRigheServiceAggregazioneTests.test_riga_senza_codice_resta_in_testa
10) FattureRigheServiceAggregazioneTests.test_marca_running_prima_di_generare
11) FattureRigheServiceKitTests.test_snapshot_kit_congelato_sulla_riga
12) FattureRigheServiceKitTests.test_componente_senza_padre_solleva
13) FattureRigheServiceKitTests.test_kit_diversi_non_si_fondono
14) FattureRigheServiceKitTests.test_coefficienti_diversi_non_fermano_la_generazione
15) FattureRigheServiceKitTests.test_riga_normale_senza_colonne_kit
16) FattureRigheServiceKitTests.test_kit_con_iva_diverse_non_e_falso_positivo
16b) FattureRigheServiceKitTests.test_esposizione_congelata_col_suo_codice
16c) FattureRigheServiceKitTests.test_chiave_esposizione_assente_vale_nascosto
16d) FattureRigheServiceKitTests.test_kit_qta_somma_le_attivita_del_gruppo
16e) FattureRigheServiceKitTests.test_kit_uom_e_la_uom_del_padre
16f) FattureRigheServiceKitTests.test_qta_padre_assente_solleva
16g) FattureRigheServiceKitTests.test_uom_padre_assente_solleva
16h) FattureRigheServiceKitTests.test_rettifica_kit_con_qta_padre_ereditata_solleva
16i) FattureRigheServiceKitTests.test_rettifica_kit_porta_la_quantita_accreditata
16j) FattureRigheServiceKitTests.test_uom_padre_diverse_non_si_fondono
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
30) FattureRigheServiceContrattoTests.test_contratti_diversi_non_si_fondono
31) FattureRigheServiceContrattoTests.test_stesso_contratto_resta_una_riga
32) FattureRigheServiceContrattoTests.test_senza_contratto_il_raggruppamento_non_cambia
33) FattureRigheServiceContrattoTests.test_il_contratto_sopravvive_nel_meta_della_riga
34) FattureRigheServiceContrattoTests.test_riga_nr_stabile_fra_contratti
35) FattureRigheServiceContrattoTests.test_rettifiche_della_stessa_riga_non_si_spezzano_per_contratto
36) FattureRigheServiceIvaRisoltaTests.test_iva_della_riga_viene_dal_risolutore
37) FattureRigheServiceIvaRisoltaTests.test_senza_emittente_si_ferma
38) FattureRigheServiceIvaRisoltaTests.test_rettifica_non_passa_dal_risolutore
39) FattureRigheServiceIvaRisoltaTests.test_una_sola_risoluzione_per_articolo_e_fattura
40) FattureRigheServiceIvaRisoltaTests.test_fatture_diverse_risolvono_separatamente
41) FattureRigheServiceIvaRisoltaTests.test_meta_porta_origine_e_titolo
42) FattureRigheServiceIvaRisoltaTests.test_iva_risolta_diversa_produce_due_righe
43) FattureRigheServicePeriodoTests.test_periodo_vero_dalla_chiave
44) FattureRigheServicePeriodoTests.test_puntuale_porta_la_data_piu_recente
45) FattureRigheServicePeriodoTests.test_rettifica_copia_il_periodo_della_riga_rettificata
46) FattureRigheServicePeriodoTests.test_rettifica_senza_periodo_della_riga_solleva
47) FattureRigheServicePeriodoTests.test_periodi_diversi_non_si_fondono
48) FattureRigheServicePeriodoTests.test_kit_puntuale_spezzato_porta_una_data_sola
49) FattureRigheServiceKitTests.test_padre_a_zero_con_componente_non_nullo_solleva
"""

import json
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

# ⭐ I codici sono in ordine INVERSO rispetto agli UUID, e non e' un caso: ART_A
# ha l'UUID minore ma il codice maggiore. E' l'unico modo di distinguere «ordina
# per codice» da «ordina per id» — con codici concordi all'ordine degli UUID
# entrambe le implementazioni passerebbero, e il test non proverebbe niente.
CODICE_A = "ZZZ-001"
CODICE_B = "AAA-001"
_CODICI = {ART_A: CODICE_A, ART_B: CODICE_B}


# Scopo: Repository fittizio parametrizzabile — le attività e i loro group input
# sono iniettati dal test, così ogni caso descrive solo lo scenario che verifica.
class _RepoMock:
    # Scopo: Inizializza la istanza.
    def __init__(self, attivita=None, prezzi=None, fatture=None, iva=None,
                 rettifiche=None, contratti=None, senza_emittente=False,
                 competenze=None):
        self.batch_insert_and_mark_calls = 0
        self.running_calls = 0
        # L'ordine delle chiamate che contano (natura dal segno fra «in
        # lavorazione» e testate, D-1).
        self.ordine_chiamate: list[str] = []
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
        # contratto per attivita_id: l'ATTO a cui l'attivita' appartiene.
        # Assente = `None`, che e' il caso di tutto cio' che nasce fuori da un
        # contratto ed e' la maggior parte del traffico.
        self._contratti = contratti or {}
        # ⛔ `P3`: senza emittente il calcolo si FERMA, non ripiega
        #    sull'aliquota ordinaria.
        self._senza_emittente = senza_emittente
        # competenza per attivita_id: (dal, al, data_attivita). Default: un
        # periodo vero (gennaio), che entra nella chiave.
        self._competenze = competenze or {}

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
            competenza_dal=self._competenza(attivita_id)[0],
            competenza_al=self._competenza(attivita_id)[1],
            data_attivita=self._competenza(attivita_id)[2],
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
            contratto_id=self._contratti.get(attivita_id),
            rett_competenza_dal=rett.get("dal"),
            rett_competenza_al=rett.get("al"),
        )

    def _competenza(self, attivita_id):
        return self._competenze.get(
            attivita_id, (date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 10))
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
        self.ordine_chiamate.append("group_inputs")
        return {aid: self._make_group_input(aid) for aid in attivita_ids}

    # Scopo: Restituisce elenco `attivita_da_fatturare` in base ai filtri disponibili.
    def list_attivita_da_fatturare(self, lotto_id):
        return list(self._attivita)

    # Scopo: Marca RUNNING le attività lockate sul lotto.
    def mark_attivita_running(self, lotto_id):
        self.running_calls += 1
        self.ordine_chiamate.append("running")
        return len(self._attivita)

    # Scopo: il verbo DB della natura dal segno (D-1): qui solo la traccia.
    def applica_natura_dal_segno(self, lotto_id):
        self.ordine_chiamate.append("natura_dal_segno")
        return 0

    # Scopo: Batch header creation per lista di attivita_id.
    def batch_get_or_create_fattura_headers(self, lotto_id, attivita_ids):
        self.ordine_chiamate.append("testate")
        return {aid: self._fatture.get(aid, 500) for aid in attivita_ids}

    # Scopo: il contesto di testata che il risolutore IVA vuole.
    # ⚠️ `emittente_fiscale_id` e' la PK di `emittenti_fiscali`, non il
    #    `soggetto_ruolo_id`: qui e' un numero finto, ma il nome dice quale.
    def batch_get_fattura_iva_context(self, fattura_ids):
        if self._senza_emittente:
            return {fid: {"billing_account_id": 200, "emittente_fiscale_id": None,
                          "data_riferimento": date(2026, 1, 31)} for fid in fattura_ids}
        return {
            fid: {"billing_account_id": 200, "emittente_fiscale_id": 77,
                  "data_riferimento": date(2026, 1, 31)}
            for fid in fattura_ids
        }

    # Scopo: mappa articolo -> iva che il risolutore finto restituira'.
    #        I test parlano per `attivita_id` (piu' leggibile); il risolutore
    #        vero e' interrogato per ARTICOLO, e la traduzione sta qui.
    def iva_per_articolo(self):
        mappa = {}
        for aid, iva in self._iva.items():
            mappa[self._articolo_di(aid)] = iva
        return mappa

    # Scopo: Restituisce MAX(riga_nr) per lista di fattura_id.
    def get_max_riga_nrs(self, fattura_ids):
        return dict.fromkeys(fattura_ids, 0)

    # Scopo: Batch INSERT righe + UPDATE attivita in un solo round-trip.
    def batch_insert_righe_and_mark(self, **kwargs):
        self.batch_insert_and_mark_calls += 1
        self.last_kwargs = kwargs
        return len(kwargs.get("att_ids", []))


# Scopo: Attività "normale" (non componente di kit) con quantità parametrica.
def _attivita_base(attivita_id, quantita="2.0", articolo_id=ART_A, meta=None,
                   articolo_codice=None):
    return AttivitaDaFatturare(
        id=attivita_id,
        articolo_id=articolo_id,
        articolo_codice=(
            articolo_codice if articolo_codice is not None
            else _CODICI.get(articolo_id, "ART-000")
        ),
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
    esposizione="DESCRITTIVO",
    qta_padre="2",
    uom_padre=5,
):
    meta = {
        kit_meta.META_KEY_SEGMENT_KEY: kit_meta.segment_key_componente(
            f"ORDINE_VENDITA:019f7c7b-c434-735e-98b7-9564eb6a9626:R:{kit_riga}", articolo_id
        ),
    }
    # `None` = chiave assente: il meta di un'attivita' scritta prima del push
    # che porta il modo.
    if esposizione is not None:
        meta[kit_meta.META_KEY_ESPOSIZIONE] = esposizione
    if padre is not None:
        meta[kit_meta.META_KEY_COMPONENTE_DI] = padre
    # `None` = chiave assente: il meta di un'attivita' scritta prima del push
    # che porta quantita' e UoM del padre (e non corretta dallo script).
    if qta_padre is not None:
        meta[kit_meta.META_KEY_QTA_PADRE] = qta_padre
    if uom_padre is not None:
        meta[kit_meta.META_KEY_UOM_PADRE] = uom_padre
    return _attivita_base(
        attivita_id, quantita=quantita, articolo_id=articolo_id, meta=meta
    )


# Scopo: risolutore IVA finto — risponde per ARTICOLO, come quello vero.
# ⚠️ `risolvi_anteprima` e non `risolvi`: sulla generazione delle righe l'IVA si
#    chiede SENZA imponibile. Se il servizio passasse all'altra il mock non
#    risponderebbe, ed e' voluto — la differenza fra le due e' se la riga puo'
#    tornare spezzata in due parti.
class _ResolverMock:
    def __init__(self, mappa):
        self._mappa = mappa
        self.chiamate = []

    def risolvi_anteprima(self, *, articolo_id, billing_account_id,
                          emittente_fiscale_id, data_riferimento):
        self.chiamate.append((articolo_id, billing_account_id, emittente_fiscale_id))
        return {
            "iva_id": self._mappa.get(articolo_id, 22),
            "origine": "TITOLO" if articolo_id in self._mappa else "ARTICOLO",
            "titolo_iva_id": 900 if articolo_id in self._mappa else None,
        }

    def meta_riga(self, parte):
        return {"iva_origine": parte.get("origine"),
                "iva_titolo_id": parte.get("titolo_iva_id")}


# Scopo: Esegue la generazione neutralizzando la transazione (test senza DB) e
#        il risolutore IVA (che altrimenti aprirebbe una connessione vera).
def _genera(repo, *, dry_run=False, resolver=None):
    service = FattureRigheService(repository=repo)
    fake = resolver or _ResolverMock(repo.iva_per_articolo())
    with patch(
        "apps.vendite.services.fatture_righe_service.transaction.atomic",
        return_value=nullcontext(),
    ), patch(
        "apps.vendite.services.iva_resolver_service.IvaResolverService",
        return_value=fake,
    ):
        return service.generate_fatture_righe(99, dry_run=dry_run)


class FattureRigheServiceUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_group_attivita_returns_group_key`.
    # ⚠️ La facade risolve l'IVA come il giro vero: senza mockare il risolutore e
    #    il lookup dell'emittente aprirebbe una connessione, e in CI fallirebbe
    #    per un motivo che col grouping non c'entra.
    @patch("apps.vendite.services.iva_resolver_service.IvaResolverService")
    @patch("apps.anagrafiche.db.billing_account_repository.BillingAccountRepository")
    def test_group_attivita_returns_group_key(self, mock_ba_cls, mock_resolver_cls):
        mock_ba_cls.return_value.get_emittente_fiscale_id.return_value = 77
        mock_resolver_cls.return_value = _ResolverMock({})
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
    # ⛔ E ORDINA PER CODICE, NON PER UUID (decisione di Tid, 2026-08-31): qui
    # ART_A ha l'UUID minore ma il codice MAGGIORE, quindi le due regole danno
    # risposte opposte e il test sa distinguerle. Ordinare per UUID è
    # deterministico e illeggibile: per chi guarda la fattura è rumore.
    def test_riga_nr_ordina_per_codice_articolo(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, articolo_id=ART_A),   # codice ZZZ-001
                _attivita_base(12, articolo_id=ART_B),   # codice AAA-001
            ],
            prezzi={11: Decimal("10.50"), 12: Decimal("10.50")},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_articolo_ids"], [ART_B, ART_A])
        self.assertEqual(kw["righe_nrs"], [1, 2])

    # Scopo: ⭐ l'altra metà dello scopo di questa chiave, e va tenuta: il
    # `riga_nr` non deve dipendere dall'ordine in cui le attività arrivano.
    # Senza questo caso, un'implementazione che non ordinasse affatto
    # passerebbe quello sopra a seconda di come è scritto il mock.
    def test_riga_nr_stabile_al_variare_dell_ordine_di_arrivo(self):
        def _ordine(attivita):
            repo = _RepoMock(attivita=attivita,
                             prezzi={11: Decimal("10.50"), 12: Decimal("10.50")})
            _genera(repo)
            return repo.last_kwargs["righe_articolo_ids"]

        diretto = _ordine([_attivita_base(11, articolo_id=ART_A),
                           _attivita_base(12, articolo_id=ART_B)])
        inverso = _ordine([_attivita_base(12, articolo_id=ART_B),
                           _attivita_base(11, articolo_id=ART_A)])
        self.assertEqual(diretto, inverso)

    # Scopo: ℹ️ le righe SENZA articolo (rettifiche, oneri) restano in testa —
    # chiave vuota. È il comportamento di prima, e non deve cambiare.
    def test_riga_senza_codice_resta_in_testa(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, articolo_id=ART_B),
                _attivita_base(12, articolo_id=ART_A, articolo_codice=""),
            ],
            prezzi={11: Decimal("10.50"), 12: Decimal("10.50")},
        )
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_articolo_ids"], [ART_A, ART_B])

    # Scopo: Le attività entrano in lavorazione prima di produrre righe.
    def test_marca_running_prima_di_generare(self):
        repo = _RepoMock()
        _genera(repo)
        self.assertEqual(repo.running_calls, 1)

    # Scopo: la natura dal segno (D-1, §7.9) gira una volta, dopo «in
    #        lavorazione» e PRIMA di group input e testate: la natura entra
    #        nella chiave della testata.
    def test_natura_dal_segno_prima_delle_testate(self):
        repo = _RepoMock()
        _genera(repo)
        self.assertEqual(
            repo.ordine_chiamate, ["running", "natura_dal_segno", "group_inputs", "testate"],
        )


class FattureRigheServiceKitTests(SimpleTestCase):
    """Requisito D5: snapshot di esposizione kit congelato sulla riga."""

    # Scopo: Le 4 colonne kit arrivano dal `meta` già risolto dal push.
    def test_snapshot_kit_congelato_sulla_riga(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(
            kw["righe_kit_keys"],
            ["ORDINE_VENDITA:019f7c7b-c434-735e-98b7-9564eb6a9626:R:608"],
        )
        self.assertEqual(kw["righe_kit_articolo_padre_ids"], [ART_PADRE])
        self.assertEqual(kw["righe_kit_esposizioni"], ["DESCRITTIVO"])

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

    # Scopo: R10 e' ritirata (R-BE-B3, 2026-10-02): con quantita' e UoM del
    # padre congelate sulla riga, coefficienti diversi (la sedia con 8 viti)
    # non sono piu' un errore. Ogni componente porta la sua quantita', e la
    # quantita' del kit e' la stessa su tutte e due le righe.
    def test_coefficienti_diversi_non_fermano_la_generazione(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, articolo_id=ART_A, quantita="2.0"),
                _attivita_kit(12, kit_riga=608, articolo_id=ART_B, quantita="6.0"),
            ]
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(sorted(kw["righe_qtas"]), [Decimal("2.0"), Decimal("6.0")])
        self.assertEqual(kw["righe_kit_qtas"], [Decimal("2"), Decimal("2")])

    # Scopo: Una riga non di kit non porta nessuna delle 4 colonne (CHECK
    # `chk_fatture_righe_kit_coerente`: tutte o nessuna).
    def test_riga_normale_senza_colonne_kit(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_kit_keys"], [None])
        self.assertEqual(kw["righe_kit_esposizioni"], [None])
        self.assertEqual(kw["righe_kit_articolo_padre_ids"], [None])
        self.assertEqual(kw["righe_kit_qtas"], [None])
        self.assertEqual(kw["righe_kit_uom_ids"], [None])

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

    # Scopo: il modo arriva sulla riga com'e' nel meta, codice e non booleano:
    # i valori li giudica la FK su `fatture_righe.kit_esposizione`.
    def test_esposizione_congelata_col_suo_codice(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, articolo_id=ART_A, esposizione="VALORIZZATO"),
                _attivita_kit(12, kit_riga=608, articolo_id=ART_B, esposizione="NASCOSTO"),
            ]
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(
            sorted(kw["righe_kit_esposizioni"]), ["NASCOSTO", "VALORIZZATO"]
        )

    # Scopo: un meta senza la chiave vale il default della colonna di
    # distinta (NASCOSTO), non NULL — che il CHECK `kit_coerente` rifiuterebbe.
    def test_chiave_esposizione_assente_vale_nascosto(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, esposizione=None)])
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_kit_esposizioni"], ["NASCOSTO"])

    # Scopo: `kit_qta` somma la quantita' padre delle attivita' aggregate,
    # come `qta` somma quella del componente: due mesi puntuali dello stesso
    # kit nella stessa riga sono due kit.
    def test_kit_qta_somma_le_attivita_del_gruppo(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, quantita="3.0", qta_padre="1"),
                _attivita_kit(12, kit_riga=608, quantita="3.0", qta_padre="1"),
            ]
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_qtas"], [Decimal("6.0")])
        self.assertEqual(kw["righe_kit_qtas"], [Decimal("2")])

    # Scopo: la UoM della riga del kit e' quella del PADRE, non quella del
    # componente (che sulla riga sta in `uom_id`).
    def test_kit_uom_e_la_uom_del_padre(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, uom_padre=41)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_kit_uom_ids"], [41])
        self.assertEqual(kw["righe_uom_ids"], [3])

    # Scopo: ⛔ nessun ripiego sulla quantita' del componente: senza la chiave
    # la riga del kit avrebbe una quantita' inventata.
    def test_qta_padre_assente_solleva(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, qta_padre=None)])
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn(kit_meta.META_KEY_QTA_PADRE, exc.exception.detail)

    # Scopo: ⛔ nessun ripiego sulla UoM del componente: su un kit misto
    # darebbe unita' discordanti nello stesso kit (D-4).
    def test_uom_padre_assente_solleva(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, uom_padre=None)])
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn(kit_meta.META_KEY_UOM_PADRE, exc.exception.detail)

    # Scopo: la rettifica di un componente EREDITA il meta della riga
    # rettificata (`fn_accredita_riga_reso`, P-7): se la quantita' padre
    # ereditata e' quella dell'originale, la nota di credito direbbe «+2 kit»
    # su componenti negativi. Si ferma invece di scriverlo.
    def test_rettifica_kit_con_qta_padre_ereditata_solleva(self):
        repo = _RepoMock(
            attivita=[_attivita_kit(11, kit_riga=608, quantita="-2.0", qta_padre="2")],
            rettifiche={11: _rettifica(7001)},
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn("segno opposto", exc.exception.detail)

    # Scopo: il rovescio — con la quantita' padre accreditata (negativa, come
    # quella del componente) la riga della nota porta il suo numero di kit.
    def test_rettifica_kit_porta_la_quantita_accreditata(self):
        repo = _RepoMock(
            attivita=[_attivita_kit(11, kit_riga=608, quantita="-2.0", qta_padre="-1")],
            rettifiche={11: _rettifica(7001)},
        )
        _genera(repo)
        self.assertEqual(repo.last_kwargs["righe_kit_qtas"], [Decimal("-1")])

    # Scopo: quantita' componente = quantita' padre × coeff: un componente non
    # nullo con il padre a zero e' una catena rotta, non un kit «da zero».
    def test_padre_a_zero_con_componente_non_nullo_solleva(self):
        repo = _RepoMock(attivita=[_attivita_kit(11, kit_riga=608, quantita="2.0", qta_padre="0")])
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")

    # Scopo: la UoM padre e' del kit: due attivita' che la dichiarano diversa
    # non finiscono nella stessa riga, che porterebbe una UoM sola.
    def test_uom_padre_diverse_non_si_fondono(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, uom_padre=5),
                _attivita_kit(12, kit_riga=608, uom_padre=6),
            ]
        )
        _genera(repo)
        self.assertEqual(sorted(repo.last_kwargs["righe_kit_uom_ids"]), [5, 6])


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
def _rettifica(riga_fattura_id, prezzo="12.00", sconto="5.00", iva=4,
               dal=date(2025, 12, 1), al=date(2025, 12, 31)):
    return {
        "tipo_movimento": "RETTIFICA",
        "riga_id": riga_fattura_id,
        "prezzo": None if prezzo is None else Decimal(prezzo),
        "sconto": None if sconto is None else Decimal(sconto),
        "iva": iva,
        # Il periodo della riga rettificata: diverso da quello dell'attivita'
        # (gennaio), per la stessa ragione dei tre valori sopra.
        "dal": dal,
        "al": al,
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


class FattureRigheServiceContrattoTests(SimpleTestCase):
    """L'ATTO nella chiave di aggregazione (`I4`, brief Fase 3 IVA §4.3)."""

    # Scopo: il difetto vivo che questa voce corregge. Due attività identiche in
    # TUTTO — articolo, prezzo, uom, IVA, competenza — tranne il contratto
    # collassavano in una riga sola. Su quella riga aggregata nessuna domanda
    # per atto ha una risposta: il CIG del primo contratto e quello del secondo
    # pretenderebbero la stessa riga, e la FatturaPA vuole un blocco
    # `DatiContratto` per atto.
    # ⚠️ Il caso NON è di nicchia e non produce nessun errore: la fattura esce,
    # i totali tornano, e a mancare è solo la distinzione.
    def test_contratti_diversi_non_si_fondono(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")],
            contratti={11: 3001, 12: 3002},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 2)
        self.assertEqual(sorted(kw["righe_qtas"]), [Decimal("3.0"), Decimal("5.0")])

    # Scopo: ⭐ IL GEMELLO, e senza di lui il test precedente non discrimina —
    # un'implementazione che spezzasse SEMPRE (per esempio mettendo
    # `attivita_id` nella chiave) lo passerebbe. Stesso contratto ⇒ una riga
    # sola, sommata: l'aggregazione resta quella di prima.
    def test_stesso_contratto_resta_una_riga(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")],
            contratti={11: 3001, 12: 3001},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 1)
        self.assertEqual(kw["righe_qtas"], [Decimal("8.0")])

    # Scopo: la promessa scritta nel brief — «non sposta nessun raggruppamento
    # esistente». Fuori da un contratto il valore è `None` per tutte le
    # attività, ed è la maggior parte del traffico: se questo caso si spezzasse,
    # la voce avrebbe cambiato il comportamento di TUTTE le fatture invece che
    # delle sole che mescolano due atti.
    def test_senza_contratto_il_raggruppamento_non_cambia(self):
        repo = _RepoMock(attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")])
        _genera(repo)
        self.assertEqual(len(repo.last_kwargs["righe_nrs"]), 1)
        self.assertEqual(repo.last_kwargs["righe_qtas"], [Decimal("8.0")])

    # Scopo: ⭐ finché `vendite.fatture_atti` non esiste, `fatture_righe` non ha
    # una colonna per l'atto — quindi l'unica sede in cui il contratto della
    # riga sopravvive è lo `meta`, dove la `group_key` finisce per intero. È ciò
    # che rende la spezzatura RICOSTRUIBILE oggi: senza, si vedrebbero due righe
    # separate e nessuno saprebbe perché.
    def test_il_contratto_sopravvive_nel_meta_della_riga(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, "5.0"), _attivita_base(12, "3.0")],
            contratti={11: 3001, 12: 3002},
        )
        _genera(repo)
        contratti = sorted(
            json.loads(m)["group_key"]["contratto_id"]
            for m in repo.last_kwargs["righe_metas"]
        )
        self.assertEqual(contratti, [3001, 3002])

    # Scopo: il `riga_nr` deve restare stabile fra due generazioni dello stesso
    # lotto anche quando i gruppi differiscono SOLO per il contratto. ⚠️ È il
    # caso che una voce aggiunta alla sola chiave di raggruppamento, e non
    # all'ordinamento, romperebbe in silenzio: i due gruppi risulterebbero
    # equivalenti all'ordinamento e prenderebbero il numero nell'ordine in cui
    # le attività sono arrivate.
    def test_riga_nr_stabile_fra_contratti(self):
        def _ordine(attivita):
            repo = _RepoMock(attivita=attivita, contratti={11: 3002, 12: 3001})
            _genera(repo)
            return [
                json.loads(m)["group_key"]["contratto_id"]
                for m in repo.last_kwargs["righe_metas"]
            ]

        diretto = _ordine([_attivita_base(11, "5.0"), _attivita_base(12, "3.0")])
        inverso = _ordine([_attivita_base(12, "3.0"), _attivita_base(11, "5.0")])
        self.assertEqual(diretto, inverso)
        self.assertEqual(diretto, [3001, 3002])

    # Scopo: ⛔ LA DECISIONE CHE VA PRESIDIATA, e senza questo test si perde.
    # Su una RETTIFICA il contratto NON entra nella chiave: l'identità di una
    # riga di nota di credito è la riga di fattura che rettifica, che è
    # strettamente più specifica. Qui le due attività rettificano la STESSA riga
    # e dichiarano contratti DIVERSI: devono restare una riga sola, o
    # l'invariante «due rettifiche della stessa riga restano aggregabili» si
    # romperebbe in silenzio su un dato incoerente a monte.
    def test_rettifiche_della_stessa_riga_non_si_spezzano_per_contratto(self):
        repo = _RepoMock(
            attivita=[
                _attivita_base(11, quantita="-2.0"),
                _attivita_base(12, quantita="-3.0"),
            ],
            rettifiche={11: _rettifica(7001), 12: _rettifica(7001)},
            contratti={11: 3001, 12: 3002},
        )
        _genera(repo)
        self.assertEqual(len(repo.last_kwargs["righe_nrs"]), 1)
        self.assertEqual(repo.last_kwargs["righe_qtas"], [Decimal("-5.0")])


class FattureRigheServiceIvaRisoltaTests(SimpleTestCase):
    """`I4`: l'IVA della riga di fattura viene dal RISOLUTORE (piano Fase 3 §4.3)."""

    # Scopo: ⭐ l'auto-fill è morto. Fino al 2026-08-31 la proiezione leggeva
    # `art.iva_id` e quella era la risposta: la nona risposta autonoma alla
    # domanda «che IVA ha questa riga», che scavalcava l'uso della fornitura e i
    # titoli documentati del cliente. Ora risponde il risolutore, e questo test
    # lo prova facendogli dire un valore che nessun'altra fonte direbbe.
    def test_iva_della_riga_viene_dal_risolutore(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo, resolver=_ResolverMock({ART_A: 4}))
        self.assertEqual(repo.last_kwargs["righe_iva_ids"], [4])

    # Scopo: ⛔ IL PRESIDIO PIÙ IMPORTANTE DEL PIANO (`P3`), e il difetto che
    # previene non ha NESSUN sintomo. La funzione DB è `SECURITY INVOKER` e
    # legge una tabella con RLS: senza contesto emittente legge zero titoli e
    # risponde con l'aliquota ORDINARIA senza sollevare — cioè l'IVA piena a un
    # esportatore abituale, su una fattura che nessuno segnalerà.
    # ⇒ Senza emittente ci si FERMA. Mai una riga scritta con un ripiego.
    def test_senza_emittente_si_ferma(self):
        repo = _RepoMock(attivita=[_attivita_base(11)], senza_emittente=True)
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")
        self.assertIn("emittente", (exc.exception.detail or "").lower())
        # ⛔ E non ha scritto NIENTE: fermarsi a metà lascerebbe una fattura con
        #    alcune righe risolte e altre no, che è peggio del rifiuto.
        self.assertEqual(repo.batch_insert_and_mark_calls, 0)

    # Scopo: N-1 — «la nota di credito non può differire da quanto fatturato».
    # ⛔ Su una RETTIFICA il risolutore NON viene interrogato: l'IVA è quella
    # della riga di fattura rettificata. Qui il risolutore direbbe 4 e la riga
    # rettificata dice 9: a vincere deve essere la seconda, e il risolutore non
    # deve nemmeno essere chiamato.
    def test_rettifica_non_passa_dal_risolutore(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-2.0")],
            rettifiche={11: _rettifica(7001, iva=9)},
        )
        resolver = _ResolverMock({ART_A: 4})
        _genera(repo, resolver=resolver)
        self.assertEqual(repo.last_kwargs["righe_iva_ids"], [9])
        self.assertEqual(resolver.chiamate, [])

    # Scopo: ⭐ la cache per (fattura, articolo). Non è un'ottimizzazione
    # opzionale: un lotto massivo arriva a 50.000 attività, e senza cache
    # sarebbero 50.000 round-trip. Qui tre attività dello stesso articolo sulla
    # stessa fattura devono produrre UNA sola interrogazione.
    def test_una_sola_risoluzione_per_articolo_e_fattura(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11), _attivita_base(12), _attivita_base(13)]
        )
        resolver = _ResolverMock({})
        _genera(repo, resolver=resolver)
        self.assertEqual(len(resolver.chiamate), 1)

    # Scopo: ⚠️ il gemello: fatture DIVERSE sono contesti diversi (cliente,
    # emittente, data), quindi la cache NON deve fonderle. Senza questo caso una
    # cache sul solo articolo passerebbe il test sopra ed applicherebbe a una
    # fattura il trattamento di un altro cliente.
    def test_fatture_diverse_risolvono_separatamente(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11), _attivita_base(12)],
            fatture={11: 500, 12: 501},
        )
        resolver = _ResolverMock({})
        _genera(repo, resolver=resolver)
        self.assertEqual(len(resolver.chiamate), 2)

    # Scopo: `P2` — nel `meta` della riga sopravvivono i due fatti che nessuno
    # può ricostruire dopo: da DOVE viene l'aliquota e quale titolo l'ha decisa.
    # ⚠️ Aliquota, natura e riferimento normativo NON si copiano: si derivano da
    # `iva_id`, e copiarli produrrebbe una frase che invecchia.
    def test_meta_porta_origine_e_titolo(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo, resolver=_ResolverMock({ART_A: 4}))
        meta = json.loads(repo.last_kwargs["righe_metas"][0])
        self.assertEqual(meta["iva_origine"], "TITOLO")
        self.assertEqual(meta["iva_titolo_id"], 900)
        self.assertNotIn("aliquota_iva", meta)

    # Scopo: ⛔ l'IVA risolta entra nella CHIAVE, quindi due articoli che il
    # risolutore tratta diversamente non si fondono — e questo è il verso in cui
    # il difetto vecchio si vedeva: con `art.iva_id` uguale per entrambi, due
    # righe che l'Agenzia vuole distinte finivano in una sola.
    def test_iva_risolta_diversa_produce_due_righe(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, articolo_id=ART_A),
                      _attivita_base(12, articolo_id=ART_B)],
        )
        _genera(repo, resolver=_ResolverMock({ART_B: 4}))
        self.assertEqual(sorted(repo.last_kwargs["righe_iva_ids"]), [4, 22])


# Scopo: competenza di un'attivita' PUNTUALE: dal = al = data dell'attivita'.
def _puntuale(giorno):
    return (giorno, giorno, giorno)


class FattureRigheServicePeriodoTests(SimpleTestCase):
    """Il periodo della riga: `competenza_dal/_al` NOT NULL dal 2026-10-02
    (brief-db-bom-flag-quantita-e-kit-in-fattura D-3, D-3.1, R-BE-B1)."""

    # Scopo: l'attivita' con un periodo vero lo porta sulla riga, e la vista
    # lo stampera' (`dal != al`).
    def test_periodo_vero_dalla_chiave(self):
        repo = _RepoMock(attivita=[_attivita_base(11)])
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_competenze_dal"], [date(2026, 1, 1)])
        self.assertEqual(kw["righe_competenze_al"], [date(2026, 1, 31)])

    # Scopo: ⭐ D-3.1 — due attivita' puntuali di date diverse nella stessa
    # riga: dal = al = la PIU' RECENTE. ⛔ Mai min-max, che si stamperebbe
    # come un periodo che non esiste. L'ordine di arrivo e' rovesciato di
    # proposito: «l'ultima vista» non e' «la piu' recente».
    def test_puntuale_porta_la_data_piu_recente(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11), _attivita_base(12)],
            competenze={11: _puntuale(date(2026, 3, 20)), 12: _puntuale(date(2026, 3, 5))},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 1)
        self.assertEqual(kw["righe_competenze_dal"], [date(2026, 3, 20)])
        self.assertEqual(kw["righe_competenze_al"], [date(2026, 3, 20)])

    # Scopo: la nota di credito copia il periodo della riga che rettifica,
    # come ne copia prezzo e IVA (N-1) — non quello dell'attivita'.
    def test_rettifica_copia_il_periodo_della_riga_rettificata(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: _rettifica(7001)},
            competenze={11: _puntuale(date(2026, 2, 14))},
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(kw["righe_competenze_dal"], [date(2025, 12, 1)])
        self.assertEqual(kw["righe_competenze_al"], [date(2025, 12, 31)])

    # Scopo: una riga rettificata senza periodo e' una catena rotta: la
    # colonna e' NOT NULL, quindi non e' un caso da ripiegare.
    def test_rettifica_senza_periodo_della_riga_solleva(self):
        repo = _RepoMock(
            attivita=[_attivita_base(11, quantita="-1.0")],
            rettifiche={11: _rettifica(7001, dal=None, al=None)},
            competenze={11: _puntuale(date(2026, 2, 14))},
        )
        with self.assertRaises(ServiceError) as exc:
            _genera(repo)
        self.assertEqual(exc.exception.code, "E_GROUP_ATTIVITA_INVALID_DATA")

    # Scopo: due periodi veri diversi sono due righe, anche sullo stesso kit
    # (D-3, strada b): un kit da 1 su gennaio e febbraio e' «1 a X» due
    # volte, non «1 a 2X».
    def test_periodi_diversi_non_si_fondono(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, qta_padre="1"),
                _attivita_kit(12, kit_riga=608, qta_padre="1"),
            ],
            competenze={
                11: (date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31)),
                12: (date(2026, 2, 1), date(2026, 2, 28), date(2026, 2, 28)),
            },
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 2)
        self.assertEqual(kw["righe_kit_qtas"], [Decimal("1"), Decimal("1")])
        self.assertEqual(
            kw["righe_competenze_dal"], [date(2026, 1, 1), date(2026, 2, 1)]
        )

    # Scopo: 🔴 il kit non si spezza per data. Componente A: due attivita'
    # puntuali (3 e 20 marzo) allo stesso prezzo → una riga; componente B:
    # le stesse due date a prezzi diversi → due righe. Con la data piu'
    # recente PER RIGA, B del 3 marzo finirebbe su un altro padre (la vista
    # separa il kit per periodo) e la quantita' del kit uscirebbe NULL. Tutte
    # le righe puntuali del kit portano la data piu' recente del kit.
    def test_kit_puntuale_spezzato_porta_una_data_sola(self):
        repo = _RepoMock(
            attivita=[
                _attivita_kit(11, kit_riga=608, articolo_id=ART_A, qta_padre="1"),
                _attivita_kit(12, kit_riga=608, articolo_id=ART_A, qta_padre="1"),
                _attivita_kit(13, kit_riga=608, articolo_id=ART_B, qta_padre="1"),
                _attivita_kit(14, kit_riga=608, articolo_id=ART_B, qta_padre="1"),
            ],
            prezzi={13: Decimal("5.00"), 14: Decimal("6.00")},
            competenze={
                11: _puntuale(date(2026, 3, 3)), 12: _puntuale(date(2026, 3, 20)),
                13: _puntuale(date(2026, 3, 3)), 14: _puntuale(date(2026, 3, 20)),
            },
        )
        _genera(repo)
        kw = repo.last_kwargs
        self.assertEqual(len(kw["righe_nrs"]), 3)
        self.assertEqual(set(kw["righe_competenze_dal"]), {date(2026, 3, 20)})
        self.assertEqual(set(kw["righe_competenze_al"]), {date(2026, 3, 20)})

