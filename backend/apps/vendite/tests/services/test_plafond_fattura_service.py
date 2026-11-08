# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi di `PlafondFatturaService` (`F3-b2`) — il consumo del plafond
#        e la riga di fattura che si spezza. Repository e risolutore mockati:
#        qui si prova la REGOLA (l'ordine, l'autorita' del lock, la quantita'
#        derivata), non che l'SQL leghi.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) PlafondFatturaServiceTests.test_lotto_non_valido_solleva
2) PlafondFatturaServiceTests.test_lotto_senza_fatture_non_fa_niente
3) PlafondFatturaServiceTests.test_senza_emittente_si_ferma
4) PlafondFatturaServiceTests.test_nessun_titolo_non_consuma_e_non_tocca
5) PlafondFatturaServiceTests.test_copertura_piena_resta_una_riga
6) PlafondFatturaServiceTests.test_copertura_parziale_spezza_in_due
7) PlafondFatturaServiceTests.test_le_due_parti_sommano_esattamente_la_riga
8) PlafondFatturaServiceTests.test_la_capofila_porta_iva_titolo_la_parte_ordinaria
9) PlafondFatturaServiceTests.test_ordine_fatture_per_data_non_per_id
10) PlafondFatturaServiceTests.test_il_risolutore_e_chiesto_nella_domanda_di_consumo
11) PlafondFatturaServiceTests.test_frazione_zero_scrive_l_ordinario
12) PlafondFatturaServiceTests.test_titolo_senza_tetto_non_chiama_la_madre
13) PlafondFatturaServiceTests.test_prezzo_effettivo_zero_divide_con_la_frazione
14) PlafondFatturaServiceTests.test_lo_sconto_entra_nel_prezzo_effettivo
15) PlafondFatturaServiceTests.test_la_capofila_ricalcola_la_quota_anche_con_imponibile_arrotondato
16) PlafondFatturaServiceTests.test_origine_arriva_dal_risolutore_anche_quando_e_assente
17) PlafondFatturaServiceTests.test_meta_assente_non_rompe
18) PlafondKitTests.test_kit_misto_spezzato_come_unita_sola
19) PlafondKitTests.test_titolo_giudicato_sul_padre_del_kit
20) PlafondKitTests.test_una_chiamata_alla_madre_per_titolo
21) PlafondKitTests.test_componente_a_imponibile_zero_passa_alla_madre_e_si_spezza
22) PlafondKitTests.test_copertura_piena_del_kit_non_spezza_e_tiene_kit_qta
23) PlafondKitTests.test_due_titoli_due_chiamate
24) PlafondKitTests.test_riga_sciolta_spezzata_senza_kit_qta
25) PlafondKitTests.test_kit_qta_per_riga_quando_il_componente_ha_due_righe
26) PlafondKitTests.test_ripartizione_incompleta_si_ferma
27) PlafondKitTests.test_due_frazioni_nello_stesso_kit_si_ferma
28) PlafondKitTests.test_frazione_fuori_da_zero_uno_si_ferma
29) PlafondNettoTests.test_sconto_su_merce_restituisce_al_titolo
30) PlafondNettoTests.test_kit_con_componente_negativo
31) PlafondNettoTests.test_kit_a_netto_zero_resta_al_titolo
32) PlafondNettoTests.test_riga_negativa_senza_positivi_va_all_ordinario
33) PlafondKitTests.test_titoli_consumati_in_ordine_di_id
34) PlafondKitTests.test_quota_assente_si_ferma
35) PlafondFatturaServiceTests.test_prezzo_assente_si_ferma_invece_di_valere_zero
"""

from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.plafond_fattura_service import PlafondFatturaService

ART = "019d53f6-58ca-7cb7-b77b-86d201ce9787"
PADRE = "019d53f6-58ca-7cb7-b77b-000000000001"
IVA_TITOLO = 44
IVA_ORD = 22


# Scopo: riga di fattura fittizia, con quanto serve a spezzarla.
def _riga(riga_id=1, qta="10", prezzo="10.00", sconto="0", imponibile="100.00"):
    return {
        "id": riga_id,
        "riga_nr": riga_id,
        "articolo_id": ART,
        "descrizione": "Articolo test",
        "uom_id": 3,
        "qta": Decimal(qta),
        "prezzo_unitario": Decimal(prezzo),
        "sconto_percentuale": Decimal(sconto),
        "iva_id": IVA_ORD,
        "imponibile_riga": Decimal(imponibile),
        "dest_billing_account_id": 200,
        "kit_key": None,
        "kit_esposizione": None,
        "kit_articolo_padre_id": None,
        "kit_descrizione_padre": None,
        "kit_qta": None,
        "kit_uom_id": None,
        "meta": {},
    }


# Scopo: componente di kit fittizio: una riga di fattura con le colonne kit.
def _componente(riga_id, *, qta, prezzo, imponibile, kit_qta="3", kit_key="K1"):
    riga = _riga(riga_id=riga_id, qta=qta, prezzo=prezzo, imponibile=imponibile)
    riga.update({
        "articolo_id": f"019d53f6-58ca-7cb7-b77b-0000000001{riga_id:02d}",
        "kit_key": kit_key,
        "kit_esposizione": "NASCOSTO",
        "kit_articolo_padre_id": PADRE,
        "kit_descrizione_padre": "Kit installazione",
        "kit_qta": Decimal(kit_qta),
        "kit_uom_id": 3,
    })
    return riga


# Scopo: esito della madre per una riga. `frazione` e' quella del SUO gruppo:
# la madre la calcola sul netto, qui la si dichiara.
def _quota(coperta, frazione, movimento=5):
    return {"quota_coperta": Decimal(coperta), "frazione": Decimal(frazione),
            "residuo_dopo": Decimal(0), "movimento_id": movimento}


# Scopo: repository fittizio — registra ciò che il servizio scrive, così ogni
# caso può interrogare l'esito invece del percorso.
class _RepoMock:
    def __init__(self, *, fatture=None, righe=None, esiti=None, senza_emittente=False):
        self._fatture = fatture if fatture is not None else [500]
        self._righe = righe if righe is not None else {500: [_riga()]}
        # esito della madre per riga_id: la ripartizione SOTTO LOCK. Senza
        # esito dichiarato: copertura piena (quota = imponibile, frazione 1).
        self._esiti = esiti or {}
        self._senza_emittente = senza_emittente
        self.consumi = []
        self.capofila_aggiornate = []
        self.parti_inserite = []
        self.prossimo_nr = 9

    def list_fatture_by_lotto_ordinate(self, lotto_id, *, limit=50000):
        return list(self._fatture)

    def batch_get_fattura_iva_context(self, fattura_ids):
        return {
            fid: {
                "billing_account_id": 200,
                "emittente_fiscale_id": None if self._senza_emittente else 77,
                "data_riferimento": date(2026, 1, 31),
            }
            for fid in fattura_ids
        }

    def list_righe_per_plafond(self, fattura_id):
        return list(self._righe.get(fattura_id, []))

    # ⚠️ Come la madre vera: una riga per riga passata.
    def consuma_plafond_titolo_righe(self, *, titolo_iva_id, fattura_id,
                                     fattura_riga_ids, imponibili, data_movimento):
        self.consumi.append(
            (fattura_id, titolo_iva_id, list(fattura_riga_ids), list(imponibili))
        )
        esiti = []
        for rid, imp in zip(fattura_riga_ids, imponibili, strict=True):
            e = dict(self._esiti.get(rid, _quota(imp, "1")))
            e["quota_ordinaria"] = imp - e["quota_coperta"]
            e["fattura_riga_id"] = rid
            e["imponibile"] = imp
            esiti.append(e)
        return esiti

    def aggiorna_capofila_plafond(self, *, riga_id, qta, iva_id, kit_qta, meta):
        self.capofila_aggiornate.append(
            {"riga_id": riga_id, "qta": qta, "iva_id": iva_id, "kit_qta": kit_qta,
             "meta": meta}
        )

    def insert_parte_plafond(self, *, riga_capofila_id, riga_nr, qta, iva_id,
                             kit_qta, meta):
        self.parti_inserite.append(
            {"capofila": riga_capofila_id, "riga_nr": riga_nr, "qta": qta,
             "iva_id": iva_id, "kit_qta": kit_qta, "meta": meta}
        )
        return 999

    def get_next_fattura_riga_nr(self, fattura_id):
        self.prossimo_nr += 1
        return self.prossimo_nr


# Scopo: risolutore fittizio, nella domanda di CONSUMO: quale titolo e i suoi
# due trattamenti. `per_articolo` da' una risposta diversa per articolo (due
# titoli sulla stessa fattura); altrimenti la stessa per tutti.
class _ResolverMock:
    def __init__(self, parti, per_articolo=None):
        self._parti = parti
        self._per_articolo = per_articolo or {}
        self.articoli = []
        self.chiamate = []

    def risolvi(self, *, consumo, articolo_id, billing_account_id,
                emittente_fiscale_id, data_riferimento):
        self.chiamate.append({"consumo": consumo})
        self.articoli.append(articolo_id)
        return list(self._per_articolo.get(articolo_id, self._parti))


def _parte(iva_id, titolo_id=None, origine="ARTICOLO"):
    return {"quota": None, "iva_id": iva_id, "titolo_iva_id": titolo_id,
            "origine": origine}


# Le tre risposte del consumo: titolo a tetto (due parti), titolo senza tetto
# (una parte col titolo), nessun titolo (una parte senza).
TETTO = [_parte(IVA_TITOLO, 7, "TITOLO"), _parte(IVA_ORD)]
SENZA_TETTO = [_parte(IVA_TITOLO, 7, "TITOLO")]
NESSUN_TITOLO = [_parte(IVA_ORD)]


# Scopo: esegue il giro neutralizzando la transazione e il risolutore.
def _consuma(repo, parti=TETTO, *, lotto_id=99, per_articolo=None):
    resolver = _ResolverMock(parti, per_articolo=per_articolo)
    service = PlafondFatturaService(repository=repo)
    with patch(
        "apps.vendite.services.plafond_fattura_service.transaction.atomic",
        return_value=nullcontext(),
    ), patch(
        "apps.vendite.services.iva_resolver_service.IvaResolverService",
        return_value=resolver,
    ):
        return service.consuma_lotto(lotto_id), resolver


class PlafondFatturaServiceTests(SimpleTestCase):
    """`I4` / `P5`: il consumo del plafond e la riga che si spezza."""

    def test_lotto_non_valido_solleva(self):
        with self.assertRaises(ServiceError) as exc:
            PlafondFatturaService(repository=_RepoMock()).consuma_lotto(0)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")

    def test_lotto_senza_fatture_non_fa_niente(self):
        repo = _RepoMock(fatture=[])
        esito, _ = _consuma(repo)
        self.assertEqual(esito, {"fatture": 0, "righe_spezzate": 0, "movimenti": 0})
        self.assertEqual(repo.consumi, [])

    # Scopo: ⛔ `P3`. La funzione DB è `SECURITY INVOKER` e legge una tabella con
    # RLS: senza contesto emittente legge zero titoli e risponde con l'aliquota
    # ordinaria SENZA sollevare — cioè nessun plafond consumato, su un documento
    # che nessuno segnalerà. Ci si ferma, non si ripiega.
    def test_senza_emittente_si_ferma(self):
        repo = _RepoMock(senza_emittente=True)
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.consumi, [])

    # Scopo: nessun titolo ⇒ l'IVA è quella già scritta alla generazione. ⛔ Non
    # si consuma e non si riscrive niente: un movimento a vuoto sporcherebbe il
    # registro che l'Agenzia guarda.
    def test_nessun_titolo_non_consuma_e_non_tocca(self):
        repo = _RepoMock()
        _consuma(repo, NESSUN_TITOLO)
        self.assertEqual(repo.consumi, [])
        self.assertEqual(repo.capofila_aggiornate, [])
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: copertura piena ⇒ UNA riga, con l'IVA del titolo. ⭐ È il gemello
    # negativo della spezzatura: senza, un'implementazione che spezza sempre
    # passerebbe il caso parziale.
    def test_copertura_piena_resta_una_riga(self):
        repo = _RepoMock()
        esito, _ = _consuma(repo)
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_TITOLO)
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("10"))

    # Scopo: ⛔ copertura parziale ⇒ DUE righe. Non è una scelta: una riga
    # FatturaPA porta UNA `AliquotaIVA` e UNA `Natura`, quindi due trattamenti
    # sullo stesso imponibile sono due `DettaglioLinee`, per obbligo di formato.
    def test_copertura_parziale_spezza_in_due(self):
        repo = _RepoMock(esiti={1: _quota("60.00", "0.6")})
        esito, _ = _consuma(repo)
        self.assertEqual(esito["righe_spezzate"], 1)
        self.assertEqual(len(repo.parti_inserite), 1)
        self.assertEqual(repo.parti_inserite[0]["capofila"], 1)

    # Scopo: ⭐ IL CASO CHE VALE PIÙ DI TUTTI. La quantità si deriva
    # dall'imponibile (`quota / prezzo effettivo`), quindi può non essere
    # tonda; ma le due parti devono sommare ESATTAMENTE la riga di partenza, o
    # il documento fiscale perde o guadagna merce. Il centesimo sta sulla parte
    # residua per costruzione: `qta_residua = qta_totale - qta_coperta`.
    def test_le_due_parti_sommano_esattamente_la_riga(self):
        repo = _RepoMock(
            righe={500: [_riga(qta="10", prezzo="7.00", imponibile="70.00")]},
            esiti={1: _quota("33.33", "0.476142857142857142857142857")},
        )
        _consuma(repo)
        somma = repo.capofila_aggiornate[0]["qta"] + repo.parti_inserite[0]["qta"]
        self.assertEqual(somma, Decimal("10"))
        # ⛔ E la quantità NON è passata per l'arrotondamento di riga: se lo
        #    facesse, la somma cadrebbe e il plafond risulterebbe consumato per
        #    meno di quanto copre — cioè un diritto del cliente ridotto in
        #    silenzio.
        self.assertNotEqual(repo.capofila_aggiornate[0]["qta"], Decimal("4.762"))

    # Scopo: la capofila porta l'IVA del titolo, la parte quella ordinaria.
    # ⚠️ Invertirle non darebbe nessun errore: darebbe l'esenzione alla quota
    # che il plafond NON copre.
    def test_la_capofila_porta_iva_titolo_la_parte_ordinaria(self):
        repo = _RepoMock(esiti={1: _quota("60.00", "0.6")})
        _consuma(repo)
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_TITOLO)
        self.assertEqual(repo.capofila_aggiornate[0]["meta"]["iva_titolo_id"], 7)
        self.assertEqual(repo.parti_inserite[0]["iva_id"], IVA_ORD)
        self.assertIsNone(repo.parti_inserite[0]["meta"]["iva_titolo_id"])

    # Scopo: ⛔ `P5` / `D15-bis` — l'ordine è un REQUISITO FISCALE. Il lock
    # impedisce a due transazioni di andare sotto zero insieme, ma non sa che
    # esiste una fattura ANTERIORE non ancora arrivata: senza l'ordine, a
    # plafond quasi esaurito è la fortuna a decidere quale cliente resta
    # scoperto. Qui il repository consegna 501 prima di 500, e il giro deve
    # rispettarlo — non ri-ordinare per id.
    def test_ordine_fatture_per_data_non_per_id(self):
        repo = _RepoMock(
            fatture=[501, 500],
            righe={501: [_riga(riga_id=11)], 500: [_riga(riga_id=1)]},
        )
        _consuma(repo)
        self.assertEqual([c[0] for c in repo.consumi], [501, 500])

    # Scopo: ⭐ decisione C. Il giro chiede al risolutore QUALE titolo vale
    # (domanda di consumo), mai quanto copre: la proiezione per riga sul
    # residuo e' sbagliata per costruzione col netto, che sa solo la madre.
    def test_il_risolutore_e_chiesto_nella_domanda_di_consumo(self):
        repo = _RepoMock()
        _, resolver = _consuma(repo)
        self.assertEqual(resolver.chiamate, [{"consumo": True}])

    # Scopo: ⚠️ frazione 0 (il titolo non copre piu' niente, o un negativo che
    # avanza) ⇒ l'ordinario si SCRIVE. La riga e' nata con l'anteprima, che a
    # plafond capiente era il titolo: lasciarla com'e' darebbe l'esenzione a
    # una quota che il plafond non copre, senza nessun sintomo.
    def test_frazione_zero_scrive_l_ordinario(self):
        riga = _riga()
        riga["iva_id"] = IVA_TITOLO
        repo = _RepoMock(righe={500: [riga]}, esiti={1: _quota("0", "0", None)})
        esito, _ = _consuma(repo)
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(esito["movimenti"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_ORD)
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("10"))
        self.assertIsNone(repo.capofila_aggiornate[0]["meta"]["iva_titolo_id"])

    # Scopo: titolo senza tetto ⇒ copre tutto e non c'e' un registro da
    # scrivere: la madre non si chiama, le righe prendono il titolo.
    def test_titolo_senza_tetto_non_chiama_la_madre(self):
        repo = _RepoMock()
        esito, _ = _consuma(repo, SENZA_TETTO)
        self.assertEqual(repo.consumi, [])
        self.assertEqual(esito["movimenti"], 0)
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_TITOLO)
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: a prezzo effettivo zero non c'e' una quota da invertire (e' zero):
    # la riga si divide con la frazione del gruppo. ⛔ Non ci si ferma piu': il
    # modello ammette la riga a zero, e la madre la ripartisce.
    def test_prezzo_effettivo_zero_divide_con_la_frazione(self):
        repo = _RepoMock(
            righe={500: [_riga(prezzo="0", imponibile="0.00")]},
            esiti={1: _quota("0", "0.4", None)},
        )
        _consuma(repo)
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("4.0"))
        self.assertEqual(repo.parti_inserite[0]["qta"], Decimal("6.0"))

    # Scopo: ⛔ un prezzo ASSENTE non e' un prezzo zero: la colonna e' NOT
    # NULL, quindi un NULL e' una proiezione rotta. Trattarlo come zero
    # dividerebbe la riga con la frazione invece che con la quota.
    def test_prezzo_assente_si_ferma_invece_di_valere_zero(self):
        riga = _riga()
        riga["prezzo_unitario"] = None
        repo = _RepoMock(righe={500: [riga]}, esiti={1: _quota("60.00", "0.6")})
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: ⚠️ lo sconto di riga entra nel divisore, perché è dentro la formula
    # con cui il DB calcola `imponibile_riga`. Ignorarlo darebbe una quantità
    # più bassa del vero e la somma delle due parti non tornerebbe.
    def test_lo_sconto_entra_nel_prezzo_effettivo(self):
        # 10 pezzi a 10,00 con sconto 20% ⇒ prezzo effettivo 8,00, imponibile 80.
        repo = _RepoMock(
            righe={500: [_riga(qta="10", prezzo="10.00", sconto="20",
                               imponibile="80.00")]},
            esiti={1: _quota("40.00", "0.5")},
        )
        _consuma(repo)
        # 40 / 8,00 = 5 pezzi, non 40 / 10,00 = 4.
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("5"))
        self.assertEqual(repo.parti_inserite[0]["qta"], Decimal("5"))

    # Scopo: ⛔ la capofila deve ricalcolare PROPRIO la quota, che e' il
    # movimento nel registro. `imponibile_riga` e' arrotondato: 3 × 3,333 =
    # 9,999 diventa 10,00. Con `qta × quota / imponibile` la capofila
    # varrebbe 4,9995 (cioe' 5,00 o 4,99 a seconda del metodo); con l'inverso
    # del prezzo vale 5 esatti.
    def test_la_capofila_ricalcola_la_quota_anche_con_imponibile_arrotondato(self):
        repo = _RepoMock(
            righe={500: [_riga(qta="3", prezzo="3.333", imponibile="10.00")]},
            esiti={1: _quota("5.00", "0.5")},
        )
        _consuma(repo)
        qta = repo.capofila_aggiornate[0]["qta"]
        self.assertEqual((qta * Decimal("3.333")).quantize(Decimal("0.000001")),
                         Decimal("5.000000"))

    # Scopo: ⛔ l'ORIGINE la dice il risolutore, non il servizio. Il vocabolario
    # e' del DB ed e' APERTO: qui la parte residua torna `ASSENTE` — il caso in
    # cui il titolo copriva una quota e sul resto nessuno sa dire l'aliquota — e
    # sulla riga deve finire `ASSENTE`, perche' e' il cancello all'emissione a
    # doverla fermare. Scrivendo `ARTICOLO` a mano gliela faremmo passare.
    def test_origine_arriva_dal_risolutore_anche_quando_e_assente(self):
        repo = _RepoMock(esiti={1: _quota("60.00", "0.6")})
        _consuma(repo, [_parte(IVA_TITOLO, 7, "TITOLO"), _parte(None, None, "ASSENTE")])
        self.assertEqual(repo.capofila_aggiornate[0]["meta"]["iva_origine"], "TITOLO")
        self.assertEqual(repo.parti_inserite[0]["meta"]["iva_origine"], "ASSENTE")
        self.assertIsNone(repo.parti_inserite[0]["iva_id"])

    # Scopo: ⛔ il `meta` che arriva dal driver puo' essere una STRINGA jsonb.
    # Il repository lo coercizza, ma il servizio non deve comunque rompersi su
    # un `meta` assente o vuoto — ed e' il caso di ogni riga nata prima di `I4`.
    def test_meta_assente_non_rompe(self):
        riga = _riga()
        riga["meta"] = None
        repo = _RepoMock(righe={500: [riga]})
        _consuma(repo)
        self.assertEqual(repo.capofila_aggiornate[0]["meta"]["iva_titolo_id"], 7)


# Scopo: il kit misto del §10 — caldaia PZ, tubo MT, manodopera ORE — venduto
# in 3, imponibile 510. Su un plafond che lascia 204 la frazione e' 0,4: la
# madre ripartisce 120, 36 e 48.
def _kit_misto():
    return [
        _componente(1, qta="3", prezzo="100.00", imponibile="300.00"),
        _componente(2, qta="9", prezzo="10.00", imponibile="90.00"),
        _componente(3, qta="12", prezzo="10.00", imponibile="120.00"),
    ]


_ESITI_KIT_MISTO = {
    1: _quota("120.00", "0.4"),
    2: _quota("36.00", "0.4"),
    3: _quota("48.00", "0.4"),
}


class PlafondKitTests(SimpleTestCase):
    """D-5 / D-5.1: il kit si spezza come un'unita' sola (brief-db-bom-flag-
    quantita-e-kit-in-fattura §11, R-BE-P1…P6)."""

    # Scopo: ⭐ R-BE-P6, il caso del brief. Il kit da 3 su un plafond che ne
    # copre 1,2: ogni componente si spezza con la stessa frazione, e ogni meta'
    # dice lo stesso numero di kit — 1,2 al titolo, 1,8 all'ordinaria. Le parti
    # restano NEL kit (R-BE-P5): e' cio' che fa uscire due righe padre.
    def test_kit_misto_spezzato_come_unita_sola(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        esito, _ = _consuma(repo)

        self.assertEqual(esito["righe_spezzate"], 3)
        self.assertEqual(esito["movimenti"], 3)
        capofile = {c["riga_id"]: c for c in repo.capofila_aggiornate}
        parti = {p["capofila"]: p for p in repo.parti_inserite}
        self.assertEqual(
            [capofile[i]["qta"] for i in (1, 2, 3)],
            [Decimal("1.2"), Decimal("3.6"), Decimal("4.8")],
        )
        self.assertEqual(
            [parti[i]["qta"] for i in (1, 2, 3)],
            [Decimal("1.8"), Decimal("5.4"), Decimal("7.2")],
        )
        # Lo stesso numero di kit su ogni componente, per ciascuna meta'.
        self.assertEqual({capofile[i]["kit_qta"] for i in (1, 2, 3)}, {Decimal("1.2")})
        self.assertEqual({parti[i]["kit_qta"] for i in (1, 2, 3)}, {Decimal("1.8")})
        self.assertEqual({capofile[i]["iva_id"] for i in (1, 2, 3)}, {IVA_TITOLO})
        self.assertEqual({parti[i]["iva_id"] for i in (1, 2, 3)}, {IVA_ORD})
        # Totale invariato: ogni componente somma la sua quantita' di partenza.
        for riga in _kit_misto():
            i = riga["id"]
            self.assertEqual(capofile[i]["qta"] + parti[i]["qta"], riga["qta"])

    # Scopo: ⛔ D-5.1 (a). Il titolo si giudica sull'articolo PADRE, una volta
    # per kit: chiesto componente per componente, un ambito che comprende la
    # caldaia e non la manodopera darebbe righe discordi e un kit senza
    # quantita'.
    def test_titolo_giudicato_sul_padre_del_kit(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        _, resolver = _consuma(repo)
        self.assertEqual(resolver.articoli, [PADRE])

    # Scopo: ⭐ R-BE-C3. UNA chiamata alla madre PER TITOLO, con tutte le righe
    # del suo secchio — il kit e la riga sciolta insieme: il netto si fa sulla
    # fattura intera sotto quel titolo, non gruppo per gruppo.
    def test_una_chiamata_alla_madre_per_titolo(self):
        sciolta = _riga(riga_id=9)
        repo = _RepoMock(righe={500: _kit_misto() + [sciolta]})
        _, resolver = _consuma(repo)
        self.assertEqual(len(repo.consumi), 1)
        self.assertEqual(repo.consumi[0][2], [1, 2, 3, 9])
        self.assertEqual(
            repo.consumi[0][3],
            [Decimal("300.00"), Decimal("90.00"), Decimal("120.00"), Decimal("100.00")],
        )
        self.assertEqual(resolver.articoli, [PADRE, ART])

    # Scopo: ⭐ R-BE-C5. Il componente a imponibile zero (un omaggio nel kit)
    # PASSA alla madre — un kit si passa intero, o lei lo rifiuta — e si spezza
    # con la frazione del gruppo che lei restituisce. Rimasto intero, la sua
    # `kit_qta` direbbe 3 kit sulla meta' del titolo e la vista darebbe NULL.
    def test_componente_a_imponibile_zero_passa_alla_madre_e_si_spezza(self):
        righe = _kit_misto() + [
            _componente(4, qta="6", prezzo="0.00", imponibile="0.00"),
        ]
        repo = _RepoMock(righe={500: righe}, esiti={
            **_ESITI_KIT_MISTO, 4: _quota("0.00", "0.4", None),
        })
        esito, _ = _consuma(repo)
        self.assertEqual(repo.consumi[0][2], [1, 2, 3, 4])
        self.assertEqual(esito["movimenti"], 3)
        capofila = next(c for c in repo.capofila_aggiornate if c["riga_id"] == 4)
        parte = next(p for p in repo.parti_inserite if p["capofila"] == 4)
        self.assertEqual(capofila["qta"], Decimal("2.4"))
        self.assertEqual(parte["qta"], Decimal("3.6"))
        self.assertEqual(capofila["kit_qta"], Decimal("1.2"))
        self.assertEqual(parte["kit_qta"], Decimal("1.8"))
        self.assertEqual(capofila["iva_id"], IVA_TITOLO)

    # Scopo: copertura piena del kit ⇒ nessuna parte, tutti i componenti
    # all'IVA del titolo, `kit_qta` invariata. Gemello negativo del caso
    # parziale.
    def test_copertura_piena_del_kit_non_spezza_e_tiene_kit_qta(self):
        repo = _RepoMock(righe={500: _kit_misto()})
        esito, _ = _consuma(repo)
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(len(repo.capofila_aggiornate), 3)
        self.assertEqual({c["kit_qta"] for c in repo.capofila_aggiornate}, {Decimal("3")})
        self.assertEqual({c["iva_id"] for c in repo.capofila_aggiornate}, {IVA_TITOLO})

    # Scopo: due gruppi sotto due titoli diversi ⇒ due secchi, due chiamate,
    # ognuna col suo titolo. Il plafond di un titolo non paga le righe
    # dell'altro.
    def test_due_titoli_due_chiamate(self):
        sciolta = _riga(riga_id=9)
        repo = _RepoMock(righe={500: _kit_misto() + [sciolta]})
        _consuma(repo, per_articolo={
            ART: [_parte(IVA_TITOLO, 8, "TITOLO"), _parte(IVA_ORD)],
        })
        self.assertEqual(
            [(c[1], c[2]) for c in repo.consumi], [(7, [1, 2, 3]), (8, [9])]
        )

    # Scopo: ⚠️ i secchi si consumano in ordine di TITOLO, non di apparizione:
    # ogni chiamata tiene il lock del suo titolo fino a fine transazione, e un
    # ordine fisso evita lock presi in versi opposti nello stesso giro.
    def test_titoli_consumati_in_ordine_di_id(self):
        sciolta = _riga(riga_id=9)
        repo = _RepoMock(righe={500: _kit_misto() + [sciolta]})
        _consuma(repo, [_parte(IVA_TITOLO, 8, "TITOLO"), _parte(IVA_ORD)],
                 per_articolo={ART: TETTO})
        self.assertEqual([c[1] for c in repo.consumi], [7, 8])

    # Scopo: ⛔ una quota NULL non e' una quota zero: letta come zero darebbe
    # una capofila vuota con tutta la merce sulla parte. Ci si ferma.
    def test_quota_assente_si_ferma(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        originale = repo.consuma_plafond_titolo_righe

        def _senza_quota(**kw):
            esiti = originale(**kw)
            esiti[1]["quota_coperta"] = None
            return esiti

        repo.consuma_plafond_titolo_righe = _senza_quota
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.capofila_aggiornate, [])

    # Scopo: la parte di una riga sciolta resta sciolta: `kit_qta` None, che
    # col resto delle colonne kit NULL (copiate dalla capofila) e' cio' che il
    # CHECK `chk_fatture_righe_kit_coerente` vuole.
    def test_riga_sciolta_spezzata_senza_kit_qta(self):
        repo = _RepoMock(esiti={1: _quota("60.00", "0.6")})
        _consuma(repo)
        self.assertIsNone(repo.capofila_aggiornate[0]["kit_qta"])
        self.assertIsNone(repo.parti_inserite[0]["kit_qta"])

    # Scopo: ⚠️ `kit_qta` e' PER RIGA: un componente fatturato a due prezzi
    # nel tempo ha due righe, ciascuna con la quota di kit delle sue attivita',
    # e la vista le somma per componente. Ognuna si divide con la stessa
    # frazione, cosi' la somma per componente resta uguale a quella degli altri.
    def test_kit_qta_per_riga_quando_il_componente_ha_due_righe(self):
        righe = [
            _componente(1, qta="3", prezzo="100.00", imponibile="300.00"),
            _componente(2, qta="2", prezzo="10.00", imponibile="20.00", kit_qta="1"),
            _componente(3, qta="4", prezzo="12.50", imponibile="50.00", kit_qta="2"),
        ]
        # Le righe 2 e 3 sono lo STESSO componente (il tubo), a due prezzi.
        righe[2]["articolo_id"] = righe[1]["articolo_id"]
        # Frazione 92,50 / 370 = 0,25, detta dalla madre.
        repo = _RepoMock(righe={500: righe}, esiti={
            1: _quota("75.00", "0.25"),
            2: _quota("5.00", "0.25"),
            3: _quota("12.50", "0.25"),
        })
        _consuma(repo)
        capofile = {c["riga_id"]: c["kit_qta"] for c in repo.capofila_aggiornate}
        parti = {p["capofila"]: p["kit_qta"] for p in repo.parti_inserite}
        # La caldaia dice 0,75 kit, il tubo 0,25 + 0,5 = 0,75 — lo stesso numero.
        self.assertEqual(capofile[1], capofile[2] + capofile[3])
        self.assertEqual(parti[1], parti[2] + parti[3])
        self.assertEqual(capofile[1], Decimal("0.75"))

    # Scopo: ⛔ la madre deve ripartire TUTTE le righe passate. Una riga senza
    # esito resterebbe col trattamento dell'anteprima: ci si ferma.
    def test_ripartizione_incompleta_si_ferma(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        originale = repo.consuma_plafond_titolo_righe
        repo.consuma_plafond_titolo_righe = (
            lambda **kw: originale(**kw)[:2]
        )
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: ⛔ la frazione e' UNA per il gruppo. Se la madre ne dicesse due, il
    # kit uscirebbe come due kit diversi: ci si ferma, invece di fidarsi della
    # prima riga.
    def test_due_frazioni_nello_stesso_kit_si_ferma(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti={
            **_ESITI_KIT_MISTO, 3: _quota("48.00", "0.5"),
        })
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: ⛔ una frazione fuori da [0, 1] e' una quota che supera
    # l'imponibile o che ne cambia il segno: ci si ferma.
    def test_frazione_fuori_da_zero_uno_si_ferma(self):
        repo = _RepoMock(esiti={1: _quota("120.00", "1.2")})
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.capofila_aggiornate, [])


class PlafondNettoTests(SimpleTestCase):
    """Decisione C (brief-db-bom-flag-quantita-e-kit-in-fattura §13): il
    plafond si consuma sul NETTO. Le risposte della madre sono quelle che il
    pgTAP `test-consuma-plafond-titolo-iva-righe-v1` prova sul DB; qui si
    prova che il giro le applica."""

    # Scopo: ⭐ R-BE-C7, il caso del brief. Plafond 500, merce 1000 e sconto
    # −100: netto 900, coperti 500. Merce 600 al titolo e 400 all'ordinaria,
    # sconto −100 al titolo. Una chiamata sola con ENTRAMBE le righe: lo sconto
    # passato da solo non restituirebbe niente.
    def test_sconto_su_merce_restituisce_al_titolo(self):
        merce = _riga(riga_id=1, qta="10", prezzo="100.00", imponibile="1000.00")
        sconto = _riga(riga_id=2, qta="1", prezzo="-100.00", imponibile="-100.00")
        repo = _RepoMock(righe={500: [merce, sconto]}, esiti={
            1: _quota("600.00", "0.6", 11),
            2: _quota("-100.00", "1", 12),
        })
        esito, _ = _consuma(repo)

        self.assertEqual(len(repo.consumi), 1)
        self.assertEqual(repo.consumi[0][2], [1, 2])
        self.assertEqual(repo.consumi[0][3], [Decimal("1000.00"), Decimal("-100.00")])
        self.assertEqual(esito["movimenti"], 2)
        self.assertEqual(esito["righe_spezzate"], 1)
        capofile = {c["riga_id"]: c for c in repo.capofila_aggiornate}
        self.assertEqual(capofile[1]["qta"], Decimal("6"))
        self.assertEqual(capofile[1]["iva_id"], IVA_TITOLO)
        self.assertEqual(repo.parti_inserite[0]["qta"], Decimal("4"))
        self.assertEqual(repo.parti_inserite[0]["iva_id"], IVA_ORD)
        # Lo sconto resta UNA riga, al titolo.
        self.assertEqual(capofile[2]["iva_id"], IVA_TITOLO)
        self.assertEqual(capofile[2]["qta"], Decimal("1"))
        self.assertEqual(len(repo.parti_inserite), 1)

    # Scopo: kit con un componente negativo (+50 / −15, netto 35) spezzato a
    # meta': frazione 0,5, quote 25 e −7,50. Ogni componente si spezza col
    # suo segno — −7,50 / −15 = 0,5 pezzi — e il kit dice 0,5 su ogni meta'.
    def test_kit_con_componente_negativo(self):
        righe = [
            _componente(1, qta="1", prezzo="50.00", imponibile="50.00", kit_qta="1"),
            _componente(2, qta="1", prezzo="-15.00", imponibile="-15.00", kit_qta="1"),
        ]
        repo = _RepoMock(righe={500: righe}, esiti={
            1: _quota("25.00", "0.5", 11),
            2: _quota("-7.50", "0.5", 12),
        })
        esito, _ = _consuma(repo)
        self.assertEqual(repo.consumi[0][3], [Decimal("50.00"), Decimal("-15.00")])
        self.assertEqual(esito["righe_spezzate"], 2)
        capofile = {c["riga_id"]: c for c in repo.capofila_aggiornate}
        parti = {p["capofila"]: p for p in repo.parti_inserite}
        self.assertEqual(capofile[1]["qta"], Decimal("0.5"))
        self.assertEqual(capofile[2]["qta"], Decimal("0.5"))
        self.assertEqual(parti[2]["qta"], Decimal("0.5"))
        self.assertEqual({capofile[i]["kit_qta"] for i in (1, 2)}, {Decimal("0.5")})
        self.assertEqual({parti[i]["kit_qta"] for i in (1, 2)}, {Decimal("0.5")})

    # Scopo: kit a netto zero (+50 / −50): non consuma niente, quindi il
    # titolo non ha motivo di lasciarlo — frazione 1, nessuna spezzatura,
    # nessun movimento.
    def test_kit_a_netto_zero_resta_al_titolo(self):
        righe = [
            _componente(1, qta="1", prezzo="50.00", imponibile="50.00", kit_qta="1"),
            _componente(2, qta="1", prezzo="-50.00", imponibile="-50.00", kit_qta="1"),
        ]
        repo = _RepoMock(righe={500: righe}, esiti={
            1: _quota("50.00", "1", None),
            2: _quota("-50.00", "1", None),
        })
        esito, _ = _consuma(repo)
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(esito["movimenti"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual({c["iva_id"] for c in repo.capofila_aggiornate}, {IVA_TITOLO})
        self.assertEqual({c["kit_qta"] for c in repo.capofila_aggiornate}, {Decimal("1")})

    # Scopo: una riga negativa senza positivi da nettizzare non restituisce
    # niente (restituire il plafond di un ALTRO documento e' della nota di
    # credito, P4): frazione 0, la riga va all'ordinario, scritto.
    def test_riga_negativa_senza_positivi_va_all_ordinario(self):
        sconto = _riga(riga_id=1, qta="1", prezzo="-100.00", imponibile="-100.00")
        repo = _RepoMock(righe={500: [sconto]}, esiti={1: _quota("0", "0", None)})
        esito, _ = _consuma(repo)
        self.assertEqual(repo.consumi[0][3], [Decimal("-100.00")])
        self.assertEqual(esito["movimenti"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_ORD)
