# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
10) PlafondFatturaServiceTests.test_autorita_e_la_madre_non_il_risolutore
11) PlafondFatturaServiceTests.test_copertura_azzerata_dalla_concorrenza_non_spezza
12) PlafondFatturaServiceTests.test_riga_a_imponibile_zero_non_consuma
13) PlafondFatturaServiceTests.test_prezzo_effettivo_nullo_solleva
14) PlafondFatturaServiceTests.test_lo_sconto_entra_nel_prezzo_effettivo
15) PlafondFatturaServiceTests.test_senza_parte_ordinaria_si_ferma_invece_di_ripiegare
16) PlafondFatturaServiceTests.test_origine_arriva_dal_risolutore_anche_quando_e_assente
17) PlafondFatturaServiceTests.test_meta_assente_non_rompe
18) PlafondKitTests.test_kit_misto_spezzato_come_unita_sola
19) PlafondKitTests.test_titolo_giudicato_sul_padre_e_sul_kit_intero
20) PlafondKitTests.test_una_chiamata_alla_madre_per_kit_nell_ordine_di_riga
21) PlafondKitTests.test_componente_a_imponibile_zero_si_spezza_senza_consumare
22) PlafondKitTests.test_copertura_piena_del_kit_non_spezza_e_tiene_kit_qta
23) PlafondKitTests.test_kit_e_riga_sciolta_sono_due_gruppi
24) PlafondKitTests.test_riga_sciolta_spezzata_senza_kit_qta
25) PlafondKitTests.test_kit_qta_per_riga_quando_il_componente_ha_due_righe
26) PlafondKitTests.test_ripartizione_incompleta_si_ferma
27) PlafondKitTests.test_due_frazioni_nello_stesso_kit_si_ferma
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
        "sorgente_tipo_id": 1,
        "sorgente_uid": None,
        "sorgente_riga": 1,
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


# Scopo: repository fittizio — registra ciò che il servizio scrive, così ogni
# caso può interrogare l'esito invece del percorso.
class _RepoMock:
    def __init__(self, *, fatture=None, righe=None, esiti=None, senza_emittente=False):
        self._fatture = fatture if fatture is not None else [500]
        self._righe = righe if righe is not None else {500: [_riga()]}
        # esito della madre per riga_id: la ripartizione SOTTO LOCK.
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

    # ⚠️ Come la madre vera: una riga per riga passata, nell'ordine, con la
    #    frazione EFFETTIVA del gruppo (somma delle quote / totale).
    def consuma_plafond_titolo_righe(self, *, titolo_iva_id, fattura_id,
                                     fattura_riga_ids, imponibili, data_movimento):
        self.consumi.append((fattura_id, list(fattura_riga_ids), list(imponibili)))
        esiti = []
        for rid, imp in zip(fattura_riga_ids, imponibili, strict=True):
            e = dict(self._esiti.get(
                rid,
                {"quota_coperta": imp, "quota_ordinaria": Decimal(0),
                 "residuo_dopo": Decimal(0), "movimento_id": 1},
            ))
            e["fattura_riga_id"] = rid
            e["imponibile"] = imp
            esiti.append(e)
        frazione = sum(e["quota_coperta"] for e in esiti) / sum(imponibili)
        for e in esiti:
            e["frazione"] = frazione
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


# Scopo: risolutore fittizio. `parti` è ciò che PROIETTA — e il punto di più
# di un test è che la proiezione e la realtà sotto lock possono divergere.
class _ResolverMock:
    # ⚠️ `poi` e' la risposta della SECONDA interrogazione, quella sul residuo:
    #    a plafond ormai esaurito il risolutore vero risponde con lo stadio A,
    #    ed e' diverso dalla prima risposta. Un mock che ripetesse sempre la
    #    stessa lista fingerebbe un risolutore che non guarda il plafond.
    def __init__(self, parti, poi=None):
        self._parti = parti
        self._poi = poi
        self.chiamate = []
        self.articoli = []

    def risolvi(self, *, imponibile, articolo_id, billing_account_id,
                emittente_fiscale_id, data_riferimento):
        self.chiamate.append(imponibile)
        self.articoli.append(articolo_id)
        if self.chiamate[:-1] and self._poi is not None:
            return list(self._poi)
        return list(self._parti)


def _parte(quota, iva_id, titolo_id=None, origine="ARTICOLO"):
    return {"quota": quota, "iva_id": iva_id, "titolo_iva_id": titolo_id,
            "origine": origine}


# Scopo: esegue il giro neutralizzando la transazione e il risolutore.
def _consuma(repo, parti, *, lotto_id=99, poi=None):
    resolver = _ResolverMock(parti, poi=poi)
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
        esito, _ = _consuma(repo, [])
        self.assertEqual(esito, {"fatture": 0, "righe_spezzate": 0, "movimenti": 0})
        self.assertEqual(repo.consumi, [])

    # Scopo: ⛔ `P3`. La funzione DB è `SECURITY INVOKER` e legge una tabella con
    # RLS: senza contesto emittente legge zero titoli e risponde con l'aliquota
    # ordinaria SENZA sollevare — cioè nessun plafond consumato, su un documento
    # che nessuno segnalerà. Ci si ferma, non si ripiega.
    def test_senza_emittente_si_ferma(self):
        repo = _RepoMock(senza_emittente=True)
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.consumi, [])

    # Scopo: nessun titolo ⇒ l'IVA è quella già scritta alla generazione. ⛔ Non
    # si consuma e non si riscrive niente: un movimento a vuoto sporcherebbe il
    # registro che l'Agenzia guarda.
    def test_nessun_titolo_non_consuma_e_non_tocca(self):
        repo = _RepoMock()
        _consuma(repo, [_parte(Decimal("100"), IVA_ORD)])
        self.assertEqual(repo.consumi, [])
        self.assertEqual(repo.capofila_aggiornate, [])
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: copertura piena ⇒ UNA riga, con l'IVA del titolo. ⭐ È il gemello
    # negativo della spezzatura: senza, un'implementazione che spezza sempre
    # passerebbe il caso parziale.
    def test_copertura_piena_resta_una_riga(self):
        repo = _RepoMock()
        esito, _ = _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(repo.capofila_aggiornate[0]["iva_id"], IVA_TITOLO)
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("10"))

    # Scopo: ⛔ copertura parziale ⇒ DUE righe. Non è una scelta: una riga
    # FatturaPA porta UNA `AliquotaIVA` e UNA `Natura`, quindi due trattamenti
    # sullo stesso imponibile sono due `DettaglioLinee`, per obbligo di formato.
    def test_copertura_parziale_spezza_in_due(self):
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("60.00"), "quota_ordinaria": Decimal("40.00"),
            "residuo_dopo": Decimal(0), "movimento_id": 5,
        }})
        esito, _ = _consuma(repo, [
            _parte(Decimal("60"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("40"), IVA_ORD),
        ])
        self.assertEqual(esito["righe_spezzate"], 1)
        self.assertEqual(len(repo.parti_inserite), 1)
        self.assertEqual(repo.parti_inserite[0]["capofila"], 1)

    # Scopo: ⭐ IL CASO CHE VALE PIÙ DI TUTTI. La quantità si deriva
    # dall'imponibile (`imponibile / prezzo effettivo`), quindi può non essere
    # tonda; ma le due parti devono sommare ESATTAMENTE la riga di partenza, o
    # il documento fiscale perde o guadagna merce. Il centesimo sta sulla parte
    # residua per costruzione: `qta_residua = qta_totale - qta_coperta`.
    def test_le_due_parti_sommano_esattamente_la_riga(self):
        repo = _RepoMock(
            righe={500: [_riga(qta="10", prezzo="7.00", imponibile="70.00")]},
            esiti={1: {
                "quota_coperta": Decimal("33.33"), "quota_ordinaria": Decimal("36.67"),
                "residuo_dopo": Decimal(0), "movimento_id": 5,
            }},
        )
        _consuma(repo, [
            _parte(Decimal("33.33"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("36.67"), IVA_ORD),
        ])
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
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("60.00"), "quota_ordinaria": Decimal("40.00"),
            "residuo_dopo": Decimal(0), "movimento_id": 5,
        }})
        _consuma(repo, [
            _parte(Decimal("60"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("40"), IVA_ORD),
        ])
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
        _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual([c[0] for c in repo.consumi], [501, 500])

    # Scopo: ⭐ L'AUTORITÀ È LA MADRE CHE PRENDE IL LOCK, non il risolutore. Il
    # risolutore è `STABLE`: proietta il residuo che vede, e fra la proiezione e
    # il lock un'altra transazione può aver consumato. Qui il risolutore dice
    # «coperta tutta» (una parte sola) e la madre ne copre 30 su 100: la riga
    # deve spezzarsi lo stesso, e l'aliquota ordinaria va RICHIESTA — mai
    # inventata.
    def test_autorita_e_la_madre_non_il_risolutore(self):
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("30.00"), "quota_ordinaria": Decimal("70.00"),
            "residuo_dopo": Decimal(0), "movimento_id": 5,
        }})
        esito, resolver = _consuma(
            repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")],
            # A plafond esaurito il risolutore risponde con lo stadio A.
            poi=[_parte(Decimal("70"), IVA_ORD, None, "ARTICOLO")],
        )
        self.assertEqual(esito["righe_spezzate"], 1)
        # ⛔ E la parte scoperta prende l'aliquota ORDINARIA. Il ripiego che
        #    c'era prima («prendi la prima parte») avrebbe preso quella DEL
        #    TITOLO — cioe' un'esenzione non dovuta sulla quota che il plafond
        #    non copre, su una fattura, senza nessun sintomo.
        self.assertEqual(repo.parti_inserite[0]["iva_id"], IVA_ORD)
        # La seconda interrogazione è quella del residuo: l'aliquota ordinaria
        # si chiede alla stessa autorità, non si deduce.
        self.assertEqual(resolver.chiamate, [Decimal("100.00"), Decimal("70.00")])

    # Scopo: la concorrenza ha azzerato la capienza ⇒ nessuna spezzatura, la
    # riga resta ordinaria. ⚠️ Ed è il ramo che, sbagliato, produrrebbe una
    # capofila a quantità ZERO e una parte con tutta la merce.
    def test_copertura_azzerata_dalla_concorrenza_non_spezza(self):
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("0"), "quota_ordinaria": Decimal("100.00"),
            "residuo_dopo": Decimal(0), "movimento_id": None,
        }})
        esito, _ = _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(repo.capofila_aggiornate, [])

    # Scopo: una riga a imponibile zero non consuma capienza — chiamare la madre
    # scriverebbe un movimento vuoto nel registro fiscale.
    def test_riga_a_imponibile_zero_non_consuma(self):
        repo = _RepoMock(righe={500: [_riga(imponibile="0")]})
        _consuma(repo, [_parte(Decimal("0"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(repo.consumi, [])

    # Scopo: senza un prezzo effettivo la quantità della parte non è derivabile.
    # ⛔ Ci si ferma: dividere per zero, o tirare a indovinare la quantità, su un
    # documento fiscale non sono opzioni.
    def test_prezzo_effettivo_nullo_solleva(self):
        repo = _RepoMock(
            righe={500: [_riga(prezzo="0", imponibile="100.00")]},
            esiti={1: {
                "quota_coperta": Decimal("60.00"), "quota_ordinaria": Decimal("40.00"),
                "residuo_dopo": Decimal(0), "movimento_id": 5,
            }},
        )
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo, [
                _parte(Decimal("60"), IVA_TITOLO, 7, "TITOLO"),
                _parte(Decimal("40"), IVA_ORD),
            ])
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")

    # Scopo: ⚠️ lo sconto di riga entra nel divisore, perché è dentro la formula
    # con cui il DB calcola `imponibile_riga`. Ignorarlo darebbe una quantità
    # più bassa del vero e la somma delle due parti non tornerebbe.
    def test_lo_sconto_entra_nel_prezzo_effettivo(self):
        # 10 pezzi a 10,00 con sconto 20% ⇒ prezzo effettivo 8,00, imponibile 80.
        repo = _RepoMock(
            righe={500: [_riga(qta="10", prezzo="10.00", sconto="20",
                               imponibile="80.00")]},
            esiti={1: {
                "quota_coperta": Decimal("40.00"), "quota_ordinaria": Decimal("40.00"),
                "residuo_dopo": Decimal(0), "movimento_id": 5,
            }},
        )
        _consuma(repo, [
            _parte(Decimal("40"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("40"), IVA_ORD),
        ])
        # 40 / 8,00 = 5 pezzi, non 40 / 10,00 = 4.
        self.assertEqual(repo.capofila_aggiornate[0]["qta"], Decimal("5"))
        self.assertEqual(repo.parti_inserite[0]["qta"], Decimal("5"))

    # Scopo: ⛔ IL RIPIEGO CHE NON C'E'. Se nemmeno la seconda interrogazione
    # restituisce una parte senza titolo, ci si FERMA. Prendere «la prima
    # parte» sarebbe stato prendere quella del titolo, cioe' scrivere
    # l'aliquota agevolata sulla quota che il plafond NON copre.
    def test_senza_parte_ordinaria_si_ferma_invece_di_ripiegare(self):
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("30.00"), "quota_ordinaria": Decimal("70.00"),
            "residuo_dopo": Decimal(0), "movimento_id": 5,
        }})
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: ⛔ l'ORIGINE la dice il risolutore, non il servizio. Il vocabolario
    # e' del DB ed e' APERTO: qui la parte residua torna `ASSENTE` — il caso in
    # cui il titolo copriva una quota e sul resto nessuno sa dire l'aliquota — e
    # sulla riga deve finire `ASSENTE`, perche' e' il cancello all'emissione a
    # doverla fermare. Scrivendo `ARTICOLO` a mano gliela faremmo passare.
    def test_origine_arriva_dal_risolutore_anche_quando_e_assente(self):
        repo = _RepoMock(esiti={1: {
            "quota_coperta": Decimal("60.00"), "quota_ordinaria": Decimal("40.00"),
            "residuo_dopo": Decimal(0), "movimento_id": 5,
        }})
        _consuma(repo, [
            _parte(Decimal("60"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("40"), None, None, "ASSENTE"),
        ])
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
        _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(repo.capofila_aggiornate[0]["meta"]["iva_titolo_id"], 7)


# Scopo: esito della madre per una riga: quota coperta e ordinaria.
def _quota(coperta, ordinaria, movimento=5):
    return {"quota_coperta": Decimal(coperta), "quota_ordinaria": Decimal(ordinaria),
            "residuo_dopo": Decimal(0), "movimento_id": movimento}


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
    1: _quota("120.00", "180.00"),
    2: _quota("36.00", "54.00"),
    3: _quota("48.00", "72.00"),
}

_PARTI_PARZIALI = [
    _parte(Decimal("204"), IVA_TITOLO, 7, "TITOLO"),
    _parte(Decimal("306"), IVA_ORD),
]


class PlafondKitTests(SimpleTestCase):
    """D-5 / D-5.1: il kit si spezza come un'unita' sola (brief-db-bom-flag-
    quantita-e-kit-in-fattura §11, R-BE-P1…P6)."""

    # Scopo: ⭐ R-BE-P6, il caso del brief. Il kit da 3 su un plafond che ne
    # copre 1,2: ogni componente si spezza con la stessa frazione, e ogni meta'
    # dice lo stesso numero di kit — 1,2 al titolo, 1,8 all'ordinaria. Le parti
    # restano NEL kit (R-BE-P5): e' cio' che fa uscire due righe padre.
    def test_kit_misto_spezzato_come_unita_sola(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        esito, _ = _consuma(repo, _PARTI_PARZIALI)

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

    # Scopo: ⛔ D-5.1 (a). Il titolo si giudica sull'articolo PADRE e
    # sull'imponibile del kit intero: chiesto componente per componente, un
    # ambito che comprende la caldaia e non la manodopera darebbe righe
    # discordi e un kit senza quantita'.
    def test_titolo_giudicato_sul_padre_e_sul_kit_intero(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        _, resolver = _consuma(repo, _PARTI_PARZIALI)
        self.assertEqual(resolver.articoli, [PADRE])
        self.assertEqual(resolver.chiamate, [Decimal("510.00")])

    # Scopo: R-BE-P3. UNA chiamata alla madre per il kit, con le righe in
    # ordine di `riga_nr`: chiamarla per componente non da' una frazione unica,
    # perche' il residuo cambia a ogni chiamata.
    def test_una_chiamata_alla_madre_per_kit_nell_ordine_di_riga(self):
        righe = _kit_misto()
        repo = _RepoMock(righe={500: righe}, esiti=_ESITI_KIT_MISTO)
        _consuma(repo, _PARTI_PARZIALI)
        self.assertEqual(len(repo.consumi), 1)
        self.assertEqual(repo.consumi[0][1], [1, 2, 3])
        self.assertEqual(
            repo.consumi[0][2],
            [Decimal("300.00"), Decimal("90.00"), Decimal("120.00")],
        )

    # Scopo: un componente a imponibile zero (omaggio nel kit) non consuma —
    # la madre lo rifiuterebbe, e un movimento a zero sporcherebbe il registro
    # — ma si SPEZZA con la frazione del kit. Rimasto intero, la sua `kit_qta`
    # direbbe 3 kit sulla meta' del titolo e la vista darebbe NULL.
    def test_componente_a_imponibile_zero_si_spezza_senza_consumare(self):
        righe = _kit_misto() + [
            _componente(4, qta="6", prezzo="0.00", imponibile="0.00"),
        ]
        repo = _RepoMock(righe={500: righe}, esiti=_ESITI_KIT_MISTO)
        _consuma(repo, _PARTI_PARZIALI)
        self.assertEqual(repo.consumi[0][1], [1, 2, 3])
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
        esito, _ = _consuma(repo, [_parte(Decimal("510"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual(esito["righe_spezzate"], 0)
        self.assertEqual(repo.parti_inserite, [])
        self.assertEqual(len(repo.capofila_aggiornate), 3)
        self.assertEqual({c["kit_qta"] for c in repo.capofila_aggiornate}, {Decimal("3")})
        self.assertEqual({c["iva_id"] for c in repo.capofila_aggiornate}, {IVA_TITOLO})

    # Scopo: un kit e una riga sciolta sulla stessa fattura sono due gruppi,
    # consumati nell'ordine della loro prima riga. La riga sciolta si giudica
    # sul SUO articolo.
    def test_kit_e_riga_sciolta_sono_due_gruppi(self):
        sciolta = _riga(riga_id=9)
        sciolta["riga_nr"] = 0
        repo = _RepoMock(righe={500: [sciolta] + _kit_misto()})
        _, resolver = _consuma(repo, [_parte(Decimal("100"), IVA_TITOLO, 7, "TITOLO")])
        self.assertEqual([c[1] for c in repo.consumi], [[9], [1, 2, 3]])
        self.assertEqual(resolver.articoli, [ART, PADRE])

    # Scopo: la parte di una riga sciolta resta sciolta: `kit_qta` None, che
    # col resto delle colonne kit NULL (copiate dalla capofila) e' cio' che il
    # CHECK `chk_fatture_righe_kit_coerente` vuole.
    def test_riga_sciolta_spezzata_senza_kit_qta(self):
        repo = _RepoMock(esiti={1: _quota("60.00", "40.00")})
        _consuma(repo, [
            _parte(Decimal("60"), IVA_TITOLO, 7, "TITOLO"),
            _parte(Decimal("40"), IVA_ORD),
        ])
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
        repo = _RepoMock(righe={500: righe}, esiti={
            1: _quota("75.00", "225.00"),
            2: _quota("5.00", "15.00"),
            3: _quota("12.50", "37.50"),
        })
        _consuma(repo, _PARTI_PARZIALI)
        capofile = {c["riga_id"]: c["kit_qta"] for c in repo.capofila_aggiornate}
        parti = {p["capofila"]: p["kit_qta"] for p in repo.parti_inserite}
        # Frazione 92,50 / 370 = 0,25: la caldaia dice 0,75 kit, il tubo
        # 0,25 + 0,5 = 0,75 — lo stesso numero.
        self.assertEqual(capofile[1], capofile[2] + capofile[3])
        self.assertEqual(parti[1], parti[2] + parti[3])
        self.assertEqual(capofile[1], Decimal("0.75"))

    # Scopo: ⛔ la madre deve ripartire TUTTE le righe passate. Una riga senza
    # esito resterebbe intera a meta' di un kit spezzato: ci si ferma.
    def test_ripartizione_incompleta_si_ferma(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        originale = repo.consuma_plafond_titolo_righe
        repo.consuma_plafond_titolo_righe = (
            lambda **kw: originale(**kw)[:2]
        )
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo, _PARTI_PARZIALI)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])

    # Scopo: ⛔ la frazione e' UNA per il gruppo. Se la madre ne dicesse due, il
    # kit uscirebbe come due kit diversi: ci si ferma, invece di fidarsi della
    # prima riga.
    def test_due_frazioni_nello_stesso_kit_si_ferma(self):
        repo = _RepoMock(righe={500: _kit_misto()}, esiti=_ESITI_KIT_MISTO)
        originale = repo.consuma_plafond_titolo_righe

        def _frazioni_diverse(**kw):
            esiti = originale(**kw)
            esiti[-1]["frazione"] = Decimal("0.5")
            return esiti

        repo.consuma_plafond_titolo_righe = _frazioni_diverse
        with self.assertRaises(ServiceError) as exc:
            _consuma(repo, _PARTI_PARZIALI)
        self.assertEqual(exc.exception.code, "E_PIPELINE_VALIDATION")
        self.assertEqual(repo.parti_inserite, [])
