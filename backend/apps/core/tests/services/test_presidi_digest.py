# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I presidi del DIGEST DEI PRESIDI (`apps.core.services.presidi_digest`).
# Note: ⭐ IL TEST 1 E' QUELLO PER CUI QUESTO FILE ESISTE (§5.5 del brief): un
#        presidio stabile NON produce un invio. E' la sola prova che impedisce al
#        digest di diventare la posta che si archivia senza aprire — cioe' di
#        finire come il presidio che voleva salvare.
#        ⛔ Nessun database: il catalogo e i conteggi arrivano da un repository
#        finto, cosi' i casi si COSTRUISCONO invece di dipendere dalle righe che
#        il dbdev per caso contiene oggi.
# ------------------------------------------------------------

"""Indice test previsti (nessun database).

1. test_un_presidio_stabile_non_produce_un_invio        ⭐ §5.5
2. test_una_vista_zero_con_righe_e_un_allarme
3. test_un_registro_con_voci_non_dichiarate_si_riferisce
4. test_la_lavorazione_entra_sempre_ma_non_fa_scattare_un_invio
5. test_alla_cadenza_del_battito_si_invia_anche_senza_niente_da_dire
6. test_un_presidio_che_non_si_legge_diventa_un_allarme_a_se
7. test_un_presidio_caduto_non_porta_via_gli_altri
8. test_il_conteggio_non_lo_calcola_il_digest
9. test_le_righe_di_esempio_si_chiedono_solo_alle_viste_zero
10. test_una_vista_elencabile_che_risponde_vuota_viene_dichiarata_cieca
11. test_una_cadenza_fuori_vocabolario_viene_rifiutata
12. test_il_messaggio_porta_il_numero_nell_oggetto_e_scappa_l_html
13. test_il_battito_usa_la_tolleranza_del_contratto_a_catalogo   ⭐
14. test_senza_tolleranza_dichiarata_nessuna_corsia_e_ferma
15. test_le_due_composizioni_nominano_le_stesse_viste
16. test_il_nome_della_corsia_viene_dalla_cadenza_non_dalla_riga_di_comando
17. test_una_corsia_mai_girata_non_sparisce_dal_battito   ⭐
18. test_una_corsia_in_corso_si_dice_in_corso_e_la_conclusa_sta_a_parte   ⭐ 14-09
19. test_l_esito_viaggia_con_la_sua_data_anche_quando_e_fallito   ⭐ 14-09, il lunedi'
20. test_le_date_delle_corse_sono_in_ora_locale_come_la_testata   14-09, cosmesi
21. test_una_corsa_conclusa_senza_esito_scritto_si_dice
22. test_il_testo_per_chi_agisce_viene_prima_della_nota   ⭐ 06-10
23. test_senza_testo_resta_la_sola_nota
24. test_i_presidi_accesi_si_raggruppano_per_chi_agisce   ⭐ 06-10
25. test_ogni_chi_agisce_ha_il_suo_titolo
26. RigaCompattaTests.test_un_istante_della_riga_si_scrive_nell_ora_dell_azienda   B-6 un-solo-fuso
27. test_le_righe_di_un_presidio_a_varianti_si_rendono_per_causa   ⭐ 10-10
     brief-db-presidio-processi-testo-per-causa §5.4.3: ogni causa col suo
     rimedio e il suo «chi agisce»; il nome della colonna dal catalogo.
28. test_una_causa_senza_testo_non_prende_il_rimedio_del_presidio   ⛔ 10-10
29. test_ogni_causa_va_a_chi_la_deve_spegnere_anche_oltre_il_campione   ⭐ 10-10, R-2
     §6.4.3: una voce per (presidio, causa) nel gruppo del «chi agisce» della
     causa; la causa che il campione non contiene arriva dal suo conteggio.
     Oggetto e riepilogo restano per presidio.
30. test_una_causa_con_piu_righe_del_campione_dice_quante_ne_mancano   10-10, R-2
"""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.db.presidi_repository import (
    CADENZA_GIORNALIERA,
    CADENZA_SETTIMANALE,
    CHI_AGISCE,
    CHI_AGISCE_AMMINISTRATORE,
    CHI_AGISCE_SISTEMISTA,
    CHI_AGISCE_SVILUPPO,
    NATURA_LAVORAZIONE,
    NATURA_REGISTRO,
    NATURA_ZERO,
    PERIMETRO_DEFINER,
    PERIMETRO_LIBERO,
    PresidiRepository,
    RigaPresidio,
)
from apps.core.services import presidi_digest
from apps.core.services.fuso_aziendale import fuso_aziendale_forzato
from apps.core.services.locale_formatters import in_ora_locale
from apps.core.services.presidi_digest import (
    TITOLI_CHI_AGISCE,
    TITOLO_CHI_AGISCE_ASSENTE,
    calcola_digest,
    componi_messaggio,
    jobname_corsia,
)


# Scopo: una riga di catalogo di prova.
def _riga(vista: str, natura: str, **override: Any) -> RigaPresidio:
    base: dict[str, Any] = {
        "vista": vista,
        "natura": natura,
        "colonna_stato": None,
        "stato_atteso": None,
        "registro": None,
        "presidiato_da": None,
        "cadenza": CADENZA_GIORNALIERA,
        "perimetro": PERIMETRO_LIBERO,
        "nota": f"nota di {vista}",
        "colonna_variante": None,
        # ⚠️ Senza testo per chi agisce, di default: e' il ripiego, e i casi
        #    col testo se lo costruiscono.
        "chi_agisce": None,
        "significato": None,
        "azione": None,
        "descrizione": f"commento di {vista}",
        "esiste": True,
        "a_catalogo": True,
    }
    base.update(override)
    return base  # type: ignore[return-value]


# Scopo: un repository finto — il catalogo e i conteggi li decide il test.
class _RepoFinto:
    def __init__(
        self,
        righe: list[RigaPresidio],
        conteggi: dict[str, Any],
        righe_esempio: dict[str, list[dict[str, Any]]] | None = None,
        testi_cause: dict[str, dict[str, dict[str, Any]]] | None = None,
        per_causa: dict[str, list[tuple[str | None, int]]] | None = None,
    ) -> None:
        self._righe = righe
        self._conteggi = conteggi
        self._righe_esempio = righe_esempio or {}
        self._testi_cause = testi_cause or {}
        # ⚠️ Quello che risponderebbe `dbops.fn_conta_presidio_per_variante`:
        #    lo decide il test. Su un presidio con `colonna_variante` e' anche il
        #    suo totale (`conta_presidio`): `conteggi` li' non si legge.
        self._per_causa = per_causa or {}
        self.viste_contate: list[str] = []
        self.viste_elencate: list[str] = []

    def list_catalogo(self, *, cadenze: tuple[str, ...] | None = None):
        if cadenze is None:
            return list(self._righe)
        return [r for r in self._righe if r["cadenza"] in cadenze]

    def conta(self, riga: RigaPresidio) -> int:
        self.viste_contate.append(riga["vista"])
        valore = self._conteggi[riga["vista"]]
        if isinstance(valore, Exception):
            raise valore
        return valore

    def prime_righe(self, riga: RigaPresidio, *, limite: int = 5):
        self.viste_elencate.append(riga["vista"])
        if riga["perimetro"] != PERIMETRO_LIBERO:
            return []
        return self._righe_esempio.get(riga["vista"], [])[:limite]

    # ⭐ Il raggruppamento per causa e' quello VERO del repository: finti sono
    #    solo i conteggi per causa e il catalogo delle cause, che il test decide.
    cause_del_presidio = PresidiRepository.cause_del_presidio
    # ⭐ Vero anche lui: decide QUALE lettura conta (il totale, o la somma per
    #    causa), sopra i due lettori finti.
    conta_presidio = PresidiRepository.conta_presidio

    def conta_per_variante(self, riga: RigaPresidio) -> list[dict[str, Any]]:
        return [
            {"variante": v, "conteggio": n}
            for v, n in self._per_causa.get(riga["vista"], [])
        ]

    def testi_delle_cause(self, vista: str) -> dict[str, dict[str, Any]]:
        return self._testi_cause.get(vista, {})


# Scopo: un lettore del giornale dei run finto, per il battito. Risponde nella
#        forma di `MaintenanceRepository.job_liveness`: un dict per jobname.
class _MaintenanceFinto:
    def __init__(self, corse: dict[str, dict[str, Any]] | None = None) -> None:
        self._corse = corse or {}
        self.soglia_chiesta: int | None = None

    def job_liveness(self, jobnames=None, *, soglia_minuti, processo_codice=None):
        self.soglia_chiesta = soglia_minuti
        return dict(self._corse)


# Scopo: il catalogo dei processi, finto: risponde la tolleranza del contratto
#        per il codice chiesto (`None` = nessun contratto). E' la stessa forma
#        di `ProcessiRepository.tolleranza_minuti`, che dal 2026-09-11 e' la
#        sede del numero (prima era `sveglie.json`).
class _ProcessiFinto:
    def __init__(self, tolleranza: int | None) -> None:
        self._tolleranza = tolleranza
        self.codice_chiesto: str | None = None

    def tolleranza_minuti(self, processo_codice: str) -> int | None:
        self.codice_chiesto = processo_codice
        return self._tolleranza


# Scopo: una corsia nella forma di `job_liveness` (2026-09-14) — la riga piu'
#        recente come segno di vita e l'ultima CONCLUSA a parte, con la sua
#        data e il suo esito insieme. Due costruttori perche' sono due casi:
#        - `_corsa_chiusa`: la riga piu' recente e' chiusa, quindi E' l'ultima
#          conclusa (una data sola);
#        - `_corsa_aperta`: la riga piu' recente sta girando, e la conclusa e'
#          un'ALTRA corsa (o non c'e').
# ⛔ Costruire qui un dict con `last_ok` sarebbe una forma che il repository
#    non emette piu': il test resterebbe verde provando un messaggio che in
#    esercizio non si compone mai (il difetto del test 18 fino al 14-09).
def _corsa_chiusa(quando: str, *, attivo: bool = True, ok: bool | None = True) -> dict[str, Any]:
    return {
        "last_run_at": quando, "attivo": attivo, "in_corso": False,
        "ultima_conclusa": {"started_at": quando, "ended_at": quando, "ok": ok},
    }


def _corsa_aperta(
    avviata: str, *, conclusa: tuple[str, bool | None] | None, attivo: bool = True,
) -> dict[str, Any]:
    return {
        "last_run_at": avviata, "attivo": attivo, "in_corso": True,
        "ultima_conclusa": (
            {"started_at": conclusa[0], "ended_at": conclusa[0], "ok": conclusa[1]}
            if conclusa else None
        ),
    }


class PresidiDigestTests(SimpleTestCase):
    """La forma del digest: cosa entra, cosa si spedisce, cosa si dichiara."""

    def setUp(self) -> None:
        # ⛔ La connessione non deve MAI essere toccata da questi test: se lo
        #    fosse, un mock dimenticato parlerebbe col DB di sviluppo.
        patcher = patch.object(presidi_digest, "connection")
        self.connessione = patcher.start()
        self.addCleanup(patcher.stop)
        # Il fuso dell'azienda e' un'ipotesi del test, dichiarata: le ore attese
        # nei messaggi (07:30, 09:47…) sono di Roma. Fino al 2026-10-09 la classe
        # le supponeva senza dirlo, e col parametro ostile della CI (T-5) tre
        # test erano rossi.
        self.enterContext(fuso_aziendale_forzato("Europe/Rome"))

    # 1. ⭐ IL TEST DELLA FORMA (§5.5). Tutto a posto ⇒ niente invio. Senza
    #    questo, il digest diventa un messaggio quotidiano che ripete lo stesso
    #    numero, e viene ignorato al secondo — cioe' muore come il presidio che
    #    voleva salvare.
    def test_un_presidio_stabile_non_produce_un_invio(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_zero", NATURA_ZERO),
                _riga("dbops.vw_registro", NATURA_REGISTRO, registro="dbops.reg"),
            ],
            {"dbops.vw_zero": 0, "dbops.vw_registro": 0},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertFalse(digest.ha_da_dire)
        self.assertFalse(digest.da_inviare)
        self.assertEqual(digest.allarmi, [])
        self.assertEqual(digest.registri, [])

    # 2. Su una ZERO qualunque riga e' un allarme di adesso.
    def test_una_vista_zero_con_righe_e_un_allarme(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO)],
            {"dbops.vw_zero": 3},
            {"dbops.vw_zero": [{"chi": "job_a"}, {"chi": "job_b"}]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(len(digest.allarmi), 1)
        voce = digest.allarmi[0]
        self.assertEqual(voce.conteggio, 3)
        self.assertEqual(len(voce.righe), 2)
        # ⚠️ `troncato` dice che le righe mostrate non sono tutte: senza, due
        #    righe su tre si leggerebbero come «sono due».
        self.assertTrue(voce.troncato)
        self.assertTrue(digest.da_inviare)

    # 3. Su un REGISTRO l'allarme e' la voce che nessuno ha dichiarato: la vista
    #    sottrae gia' quelle note, quindi qualunque riga chiede una decisione.
    def test_un_registro_con_voci_non_dichiarate_si_riferisce(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_registro", NATURA_REGISTRO, registro="dbops.reg")],
            {"dbops.vw_registro": 12},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(len(digest.registri), 1)
        self.assertEqual(digest.registri[0].registro, "dbops.reg")
        self.assertTrue(digest.da_inviare)

    # 4. La lavorazione e' una TENDENZA: entra sempre, anche a zero (una coda che
    #    si e' svuotata e' un'informazione), ma non fa partire un messaggio.
    def test_la_lavorazione_entra_sempre_ma_non_fa_scattare_un_invio(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_coda_a", NATURA_LAVORAZIONE),
                _riga("dbops.vw_coda_b", NATURA_LAVORAZIONE),
            ],
            {"dbops.vw_coda_a": 0, "dbops.vw_coda_b": 57},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(len(digest.lavorazioni), 2)
        self.assertFalse(digest.ha_da_dire)
        self.assertFalse(digest.da_inviare)

    # 5. ⭐ IL BATTITO. Alla cadenza dichiarata il messaggio parte comunque: un
    #    digest muto e un digest morto si scrivono uguale.
    def test_alla_cadenza_del_battito_si_invia_anche_senza_niente_da_dire(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        corse = {"digest_presidi:giornaliera": _corsa_chiusa("2026-09-10T07:00:00+02:00")}
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=_MaintenanceFinto(corse),
            # Il contratto del seed (`processi.csv`): 11520 minuti.
            processi=_ProcessiFinto(11520),
        )
        self.assertFalse(digest.ha_da_dire)
        self.assertTrue(digest.da_inviare)
        self.assertIsNotNone(digest.battito)
        _oggetto, testo, _html = componi_messaggio(digest)
        self.assertIn("digest_presidi:giornaliera", testo)

    # 6. ⛔ Un presidio che non si e' potuto contare NON e' un silenzio: e' un
    #    allarme a se'. Tacerlo sarebbe la stessa cecita' che `fn_conta_presidio`
    #    esiste per chiudere.
    def test_un_presidio_che_non_si_legge_diventa_un_allarme_a_se(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_sparita", NATURA_ZERO)],
            {"dbops.vw_sparita": RuntimeError("la vista non esiste piu'")},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(len(digest.non_letti), 1)
        self.assertIn("non esiste", digest.non_letti[0].errore)
        self.assertTrue(digest.ha_da_dire)
        # ⛔ E la connessione si rimette a posto: un presidio puo' portarsi
        #    via la connessione, e da li' in poi ogni lettura successiva
        #    fallirebbe. ⚠️ `close_if_unusable_or_obsolete` e non `close`: chiude
        #    SOLO se e' andata in errore, perche' la stessa funzione la chiama
        #    anche il pannello dentro una richiesta web.
        self.connessione.close_if_unusable_or_obsolete.assert_called_once()

    # 7. L'isolamento e' per presidio: quello caduto non porta via gli altri —
    #    ed e' il difetto che il 2026-09-10 ha fatto perdere un giro intero,
    #    perche' il `try` copriva il solo conteggio e non la lettura delle righe.
    def test_un_presidio_caduto_non_porta_via_gli_altri(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_prima", NATURA_ZERO),
                _riga("dbops.vw_cade", NATURA_ZERO),
                _riga("dbops.vw_dopo", NATURA_ZERO),
            ],
            {
                "dbops.vw_prima": 1,
                "dbops.vw_cade": RuntimeError("connessione persa"),
                "dbops.vw_dopo": 2,
            },
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(
            [v.vista for v in digest.allarmi], ["dbops.vw_prima", "dbops.vw_dopo"],
        )
        self.assertEqual([n.vista for n in digest.non_letti], ["dbops.vw_cade"])

    # 8. Il digest non conta da se': chiede al repository, che passa dalla
    #    funzione del database. Se un giorno qualcuno ci scrivesse un `count(*)`,
    #    il filtro «diverso dallo stato atteso» avrebbe una seconda sede.
    def test_il_conteggio_non_lo_calcola_il_digest(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_a", NATURA_ZERO), _riga("dbops.vw_b", NATURA_ZERO)],
            {"dbops.vw_a": 0, "dbops.vw_b": 0},
        )
        calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(repo.viste_contate, ["dbops.vw_a", "dbops.vw_b"])

    # 9. ⭐ Le righe di esempio si chiedono SOLO alle ZERO con qualcosa da
    #    mostrare: su un REGISTRO la notizia e' il numero, e una seconda lettura
    #    costa una seconda scansione — su `vw_riferimenti_morti_da_sanare` sono
    #    cinquecento funzioni ricompilate, cioe' il motivo della sua cadenza.
    def test_le_righe_di_esempio_si_chiedono_solo_alle_viste_zero(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_zero_vuota", NATURA_ZERO),
                _riga("dbops.vw_zero_piena", NATURA_ZERO),
                _riga("dbops.vw_registro", NATURA_REGISTRO),
                _riga("dbops.vw_coda", NATURA_LAVORAZIONE),
            ],
            {
                "dbops.vw_zero_vuota": 0,
                "dbops.vw_zero_piena": 2,
                "dbops.vw_registro": 779,
                "dbops.vw_coda": 4,
            },
            {"dbops.vw_zero_piena": [{"x": 1}, {"x": 2}]},
        )
        calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(repo.viste_elencate, ["dbops.vw_zero_piena"])

    # 10. ⭐ IL CONTEGGIO DICE N E L'ELENCO E' VUOTO su una vista dichiarata
    #     elencabile: si DICE, invece di stampare un numero seguito da niente.
    #     Misurato il 2026-09-10 su due viste vere (`vw_riferimenti_morti_*`),
    #     dove `zeroerp_app` legge zero e il proprietario 779.
    def test_una_vista_elencabile_che_risponde_vuota_viene_dichiarata_cieca(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_cieca", NATURA_ZERO),
                _riga("dbops.vw_definer", NATURA_ZERO, perimetro=PERIMETRO_DEFINER),
            ],
            {"dbops.vw_cieca": 779, "dbops.vw_definer": 5},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        cieca = next(v for v in digest.allarmi if v.vista == "dbops.vw_cieca")
        definer = next(v for v in digest.allarmi if v.vista == "dbops.vw_definer")
        self.assertTrue(cieca.cieco)
        # ⛔ Su una DEFINER l'elenco vuoto e' il contratto, non un difetto:
        #    chiamarla cieca sarebbe un allarme inventato.
        self.assertFalse(definer.cieco)
        _oggetto, testo, html = componi_messaggio(digest)
        self.assertIn("il conteggio dice 779", testo)
        self.assertIn("perimetro", html)

    # 11. Una cadenza fuori vocabolario non produce un digest vuoto — che si
    #     leggerebbe come «tutto a posto» — ma un rifiuto.
    def test_una_cadenza_fuori_vocabolario_viene_rifiutata(self) -> None:
        with self.assertRaises(ValueError):
            calcola_digest("MAI", repo=_RepoFinto([], {}))
        with self.assertRaises(ValueError):
            calcola_digest("giornaliera", repo=_RepoFinto([], {}))

    # 12. L'oggetto porta il numero (e' l'unica parte che si legge senza aprire)
    #     e i valori delle righe finiscono ESCAPATI nell'HTML.
    def test_il_messaggio_porta_il_numero_nell_oggetto_e_scappa_l_html(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO)],
            {"dbops.vw_zero": 2},
            {"dbops.vw_zero": [{"chi": "<script>cattivo</script>"}]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        oggetto, testo, html = componi_messaggio(digest)
        self.assertIn("1 in allarme", oggetto)
        self.assertIn("2 righe", oggetto)
        self.assertIn("nota di dbops.vw_zero", testo)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    # 13. ⭐ IL LETTORE DELLA TOLLERANZA. `tolleranza_minuti` e' il contratto
    #     del processo a catalogo (`dbops.processi`, dal 2026-09-11 — prima
    #     stava in `deploy/sveglie.json`), e senza qualcuno che la CONFRONTI
    #     sarebbe una colonna che sembra un presidio senza esserlo. Qui si prova
    #     che il battito la chiede al catalogo PER IL PROCESSO GIUSTO, la passa
    #     al giornale, e che una corsia ferma esce col nome.
    def test_il_battito_usa_la_tolleranza_del_contratto_a_catalogo(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:giornaliera": _corsa_chiusa(
                "2026-09-03T07:00:00+02:00", attivo=False,
            ),
            "digest_presidi:settimanale": _corsa_chiusa("2026-09-10T07:30:00+02:00"),
        })
        catalogo = _ProcessiFinto(1560)
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=catalogo,
        )
        assert digest.battito is not None
        self.assertEqual(catalogo.codice_chiesto, "digest_presidi")
        self.assertEqual(giornale.soglia_chiesta, 1560)
        self.assertEqual(
            digest.battito.corsie_ferme, ["digest_presidi:giornaliera"],
        )
        # ⭐ E il giudizio esce nel messaggio accanto alla data: un elenco di
        #    date non dice da solo quale sia «troppo vecchia».
        _oggetto, testo, html = componi_messaggio(digest)
        self.assertIn("FERMA", testo)
        self.assertIn("FERMA", html)
        # ⭐ E finisce anche nel `meta` del run, dove lo vede chi scorre le corse.
        self.assertEqual(
            digest.riepilogo()["corsie_ferme"], ["digest_presidi:giornaliera"],
        )

    # 14. ⛔ Senza tolleranza dichiarata NESSUNA corsia e' ferma: `job_liveness`
    #     pretende una soglia per rispondere, quindi `attivo` sarebbe calcolato
    #     su un numero che non vuol dire niente. La garanzia sta nell'oggetto,
    #     non nella disciplina di chi legge.
    def test_senza_tolleranza_dichiarata_nessuna_corsia_e_ferma(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:giornaliera": _corsa_chiusa(
                "2026-09-03T07:00:00+02:00", attivo=False,
            ),
        })
        catalogo = _ProcessiFinto(None)
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=catalogo,
        )
        assert digest.battito is not None
        self.assertEqual(digest.battito.corsie_ferme, [])
        _oggetto, testo, _html = componi_messaggio(digest)
        # E lo si DICE, invece di lasciar credere che le date siano state
        # guardate.
        self.assertIn("nessuna tolleranza dichiarata", testo)

    # 15. ⭐ LE DUE COMPOSIZIONI SONO DUE SEDI DELLA STESSA COSA, e il modo in
    #     cui divergono e' sempre lo stesso: si aggiunge una sezione a una e ci
    #     si dimentica dell'altra. Nessuno se ne accorge — l'email si legge in
    #     HTML, e il testo lo guarda chi non puo'.
    def test_le_due_composizioni_nominano_le_stesse_viste(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_zero", NATURA_ZERO),
                _riga("dbops.vw_registro", NATURA_REGISTRO, registro="dbops.reg"),
                _riga("dbops.vw_coda", NATURA_LAVORAZIONE),
                _riga("dbops.vw_rotta", NATURA_ZERO),
            ],
            {
                "dbops.vw_zero": 3,
                "dbops.vw_registro": 12,
                "dbops.vw_coda": 57,
                "dbops.vw_rotta": RuntimeError("vista sparita"),
            },
            {"dbops.vw_zero": [{"x": 1}]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        _oggetto, testo, html = componi_messaggio(digest)
        for vista in ("dbops.vw_zero", "dbops.vw_registro",
                      "dbops.vw_coda", "dbops.vw_rotta"):
            with self.subTest(vista=vista):
                self.assertIn(vista, testo)
                self.assertIn(vista, html)
        # Anche il motivo del non letto sta in tutte e due.
        self.assertIn("vista sparita", testo)
        self.assertIn("vista sparita", html)

    # 16. Il nome della corsia si deriva dalla CADENZA del catalogo, non dalla
    #     parola scritta sulla riga di comando: un alias nuovo sull'argomento
    #     cambierebbe il jobname e spezzerebbe la storia del processo — e il
    #     battito, che la ritrova per `processo_codice`, non lo direbbe.
    def test_il_nome_della_corsia_viene_dalla_cadenza_non_dalla_riga_di_comando(self) -> None:
        self.assertEqual(
            jobname_corsia(CADENZA_GIORNALIERA), "digest_presidi:giornaliera",
        )
        self.assertEqual(
            jobname_corsia(CADENZA_SETTIMANALE), "digest_presidi:settimanale",
        )

    # 17. ⭐ UNA CORSIA MAI GIRATA NON SPARISCE. `job_liveness` non elenca i
    #     jobname che il giornale non conosce — sta nel suo contratto — quindi
    #     senza le corsie ATTESE una corsia mai partita non comparirebbe affatto,
    #     e il battito si leggerebbe come «nessun problema». E' la stessa
    #     confusione fra «zero» e «non ho visto» che il catalogo combatte.
    def test_una_corsia_mai_girata_non_sparisce_dal_battito(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        # Il giornale conosce SOLO la settimanale: la giornaliera non e' mai
        # partita.
        giornale = _MaintenanceFinto({
            "digest_presidi:settimanale": _corsa_chiusa("2026-09-10T07:30:00+02:00"),
        })
        catalogo = _ProcessiFinto(11520)
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=catalogo,
        )
        assert digest.battito is not None
        self.assertEqual(
            digest.battito.corsie_mai_girate, ["digest_presidi:giornaliera"],
        )
        _oggetto, testo, html = componi_messaggio(digest)
        self.assertIn("MAI GIRATA", testo)
        self.assertIn("MAI GIRATA", html)
        self.assertIn("digest_presidi:giornaliera", testo)
        # ⭐ E finisce nel `meta` del run: chi scorre le corse lo vede senza
        #    aprire la mail.
        self.assertEqual(
            digest.riepilogo()["corsie_mai_girate"],
            ["digest_presidi:giornaliera"],
        )

    # 18. ⛔ LA RIGA DI UNA CORSIA NON CUCE DUE CORSE. Per la corsia che sta
    #     componendo la mail la riga piu' recente e' SEMPRE aperta, e l'esito e'
    #     sempre di un'altra corsa. Fino al 2026-09-14 (sera) la mail scriveva
    #     «09:47:32 (ok)»: l'ora della corsa 122445 in esecuzione, l'ok di
    #     quella delle 07:30 (nota del team DB). Da qui: «in corso (avviata …)
    #     — ultima conclusa … (ok)», con la data di CIASCUNA accanto al suo fatto.
    # ⚠️ Fino a quel giorno questo test costruiva `last_ok: None` per la corsia
    #     in corso — una forma che il repository (gia' corretto la mattina) non
    #     emetteva piu': verde, provando un messaggio che non si componeva mai.
    #     Ora la corsia si costruisce nella forma vera: riga aperta + conclusa a
    #     parte, ed e' la forma che `test_job_liveness_due_chiavi` fabbrica sul
    #     database con `fn_job_run_start`.
    def test_una_corsia_in_corso_si_dice_in_corso_e_la_conclusa_sta_a_parte(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:giornaliera": _corsa_chiusa("2026-09-14T07:00:12+02:00"),
            # La corsia che sta girando ADESSO (09:47), con la precedente
            # conclusa alle 07:30.
            "digest_presidi:settimanale": _corsa_aperta(
                "2026-09-14T09:47:32+02:00",
                conclusa=("2026-09-14T07:30:49+02:00", True),
            ),
        })
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo, html = componi_messaggio(digest)
        # ⚠️ L'esito si legge SULLA RIGA della corsia: la finestra si chiude al
        #    primo a capo (testo) o al `</li>` (HTML, una riga sola), cosi' uno
        #    scambio fra le due corsie non passa. Il `</code>` opzionale e'
        #    l'unica differenza fra le due rese.
        for corpo in (testo, html):
            self.assertNotIn("FALLITA", corpo)
            riga = re.search(
                r"digest_presidi:settimanale(?:</code>)?:(.*?)(?:</li>|$)", corpo, re.M,
            )
            assert riga is not None
            riga_settimanale = riga.group(1)
            # In corso, con l'ora dell'avvio; e la conclusa a parte, con la SUA.
            self.assertIn("in corso (avviata 14-09-2026 09:47:32)", riga_settimanale)
            self.assertIn("ultima conclusa 14-09-2026 07:30:49 (ok)", riga_settimanale)
            # ⛔ La cucitura: l'ora della corsa in esecuzione seguita da un esito.
            self.assertNotIn("09:47:32 (ok)", riga_settimanale)
            self.assertRegex(
                corpo, r"digest_presidi:giornaliera(?:</code>)?: 14-09-2026 07:00:12 \(ok\)",
            )

    # 19. ⭐ IL LUNEDI' DEL TEAM DB: la settimanale precedente e' finita male, e
    #     la mail in mano la sta scrivendo la corsa nuova. La riga deve dire
    #     «in corso» adesso e «FALLITA» sulla corsa di UNA SETTIMANA FA, con la
    #     sua data — non «<adesso> (FALLITA)», che e' la frase che il team DB
    #     ha previsto e che questo test rende impossibile.
    def test_l_esito_viaggia_con_la_sua_data_anche_quando_e_fallito(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:settimanale": _corsa_aperta(
                "2026-09-21T07:30:12+02:00",
                conclusa=("2026-09-14T07:30:49+02:00", False),
            ),
        })
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo, html = componi_messaggio(digest)
        self.assertIn(
            "in corso (avviata 21-09-2026 07:30:12) — ultima conclusa "
            "14-09-2026 07:30:49 (FALLITA)",
            testo,
        )
        self.assertNotIn("07:30:12 (FALLITA)", testo)
        # In HTML il fallimento e' marcato, e resta accanto alla SUA data.
        self.assertIn("14-09-2026 07:30:49 (<strong>FALLITA</strong>)", html)
        # ⚠️ E una corsia che gira per la PRIMA volta non ha niente da
        #    raccontare sul passato, e lo dice: non inventa un esito.
        giornale_prima = _MaintenanceFinto({
            "digest_presidi:settimanale": _corsa_aperta(
                "2026-09-21T07:30:12+02:00", conclusa=None,
            ),
        })
        digest_prima = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale_prima,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo_prima, _html = componi_messaggio(digest_prima)
        self.assertIn("in corso (avviata 21-09-2026 07:30:12) — nessuna corsa conclusa", testo_prima)
        self.assertNotIn("(ok)", testo_prima)
        self.assertNotIn("FALLITA", testo_prima)

    # 20. La testata era in ora locale e le corse in UTC («cosmesi» nella nota
    #     del team DB): il giornale risponde nel fuso della connessione, cioe'
    #     UTC. Ora tutte le date del messaggio passano dallo stesso punto, nel
    #     fuso dell'azienda — non in quello dell'host, che su un'unit systemd
    #     puo' mancare, ne' in `TIME_ZONE` ('UTC', neutro dal 2026-10-09).
    @fuso_aziendale_forzato("Europe/Rome")
    def test_le_date_delle_corse_sono_in_ora_locale_come_la_testata(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            # Come le consegna il repository: `isoformat()` di un timestamptz
            # letto da una connessione in UTC.
            "digest_presidi:giornaliera": _corsa_chiusa("2026-09-14T05:00:12+00:00"),
        })
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo, html = componi_messaggio(digest)
        for corpo in (testo, html):
            self.assertIn("14-09-2026 07:00:12 (ok)", corpo)
            self.assertNotIn("05:00:12", corpo)
        # E la testata: stesso fuso, senza secondi (e' un'ora di lettura, non
        # una corsa da distinguere).
        testata = in_ora_locale(digest.quando).strftime("%d-%m-%Y %H:%M")
        self.assertIn(testata, testo)

    # 21. `job_run_log.ok` e' nullable e nessun CHECK lo lega a `ended_at`: una
    #     corsa chiusa senza esito scritto e' un caso che il modello ammette.
    #     Si dice com'e' — ne' «ok» ne' «FALLITA» sarebbero veri.
    def test_una_corsa_conclusa_senza_esito_scritto_si_dice(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:giornaliera": _corsa_chiusa("2026-09-14T07:00:12+02:00", ok=None),
        })
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo, _html = componi_messaggio(digest)
        self.assertIn("14-09-2026 07:00:12 (esito non scritto)", testo)
        self.assertNotIn("(ok)", testo)
        self.assertNotIn("FALLITA", testo)

    # 22. ⭐ IL TESTO PER CHI AGISCE (brief-db-presidi-cosa-significa-cosa-fare
    #     §6). Chi apre la mail ha due domande — cosa vuol dire, cosa faccio — e
    #     la risposta viene PRIMA della nota, che e' scritta per chi mantiene il
    #     presidio. Si prova sulle DUE rese: il testo e l'HTML.
    def test_il_testo_per_chi_agisce_viene_prima_della_nota(self) -> None:
        repo = _RepoFinto(
            [_riga(
                "dbops.vw_zero", NATURA_ZERO,
                chi_agisce=CHI_AGISCE_AMMINISTRATORE,
                significato="Ci sono lotti fermi.",
                azione="Rilancia o annulla i lotti.",
            )],
            {"dbops.vw_zero": 1},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        voce = digest.allarmi[0]
        self.assertEqual(
            (voce.significato, voce.azione, voce.chi_agisce),
            ("Ci sono lotti fermi.", "Rilancia o annulla i lotti.",
             CHI_AGISCE_AMMINISTRATORE),
        )
        _oggetto, testo, html = componi_messaggio(digest)
        for resa in (testo, html):
            with self.subTest(resa=resa[:20]):
                self.assertLess(resa.index("Ci sono lotti fermi."),
                                resa.index("Rilancia o annulla i lotti."))
                self.assertLess(resa.index("Rilancia o annulla i lotti."),
                                resa.index("nota di dbops.vw_zero"))
                self.assertIn("dettaglio tecnico", resa)

    # 23. Senza testo (un presidio che il catalogo non ha ancora tradotto per
    #     chi agisce) resta la nota com'era: nessuna riga vuota, nessuna
    #     etichetta «dettaglio tecnico» sopra una frase che e' l'unica.
    def test_senza_testo_resta_la_sola_nota(self) -> None:
        repo = _RepoFinto([_riga("dbops.vw_zero", NATURA_ZERO)], {"dbops.vw_zero": 1})
        _oggetto, testo, html = componi_messaggio(
            calcola_digest(CADENZA_GIORNALIERA, repo=repo),
        )
        for resa in (testo, html):
            with self.subTest(resa=resa[:20]):
                self.assertIn("nota di dbops.vw_zero", resa)
                self.assertNotIn("dettaglio tecnico", resa)
                self.assertNotIn("→", resa)
        # ⚠️ E finisce nel gruppo «senza indicazione», non sparisce.
        self.assertIn(TITOLO_CHI_AGISCE_ASSENTE, testo)

    # 24. ⭐ I GRUPPI. Prima cio' che si sistema dall'applicazione, poi cio' che
    #     va inoltrato, in fondo cio' che non dice a chi tocca. L'ordine del
    #     catalogo (alfabetico per vista) qui e' apposta il CONTRARIO, cosi' un
    #     raggruppamento dimenticato non passa per caso.
    def test_i_presidi_accesi_si_raggruppano_per_chi_agisce(self) -> None:
        repo = _RepoFinto(
            [
                _riga("dbops.vw_a", NATURA_ZERO),
                _riga("dbops.vw_b", NATURA_ZERO, chi_agisce=CHI_AGISCE_SVILUPPO),
                _riga("dbops.vw_c", NATURA_ZERO, chi_agisce=CHI_AGISCE_SISTEMISTA),
                _riga("dbops.vw_d", NATURA_ZERO, chi_agisce=CHI_AGISCE_AMMINISTRATORE),
            ],
            {"dbops.vw_a": 1, "dbops.vw_b": 1, "dbops.vw_c": 1, "dbops.vw_d": 1},
        )
        _oggetto, testo, html = componi_messaggio(
            calcola_digest(CADENZA_GIORNALIERA, repo=repo),
        )
        attesi = [
            (TITOLI_CHI_AGISCE[CHI_AGISCE_AMMINISTRATORE], "dbops.vw_d"),
            (TITOLI_CHI_AGISCE[CHI_AGISCE_SISTEMISTA], "dbops.vw_c"),
            (TITOLI_CHI_AGISCE[CHI_AGISCE_SVILUPPO], "dbops.vw_b"),
            (TITOLO_CHI_AGISCE_ASSENTE, "dbops.vw_a"),
        ]
        for resa in (testo, html.replace("&#x27;", "'")):
            with self.subTest(resa=resa[:20]):
                posizioni = []
                for titolo, vista in attesi:
                    posizioni += [resa.index(titolo), resa.index(vista)]
                self.assertEqual(posizioni, sorted(posizioni))

    # 25. ⛔ Un valore del mirror senza titolo finirebbe fra i «senza
    #     indicazione» in silenzio: il dizionario segue il mirror, che segue il
    #     CHECK (`test_presidi_catalogo`).
    def test_ogni_chi_agisce_ha_il_suo_titolo(self) -> None:
        self.assertEqual(set(TITOLI_CHI_AGISCE), set(CHI_AGISCE))

    # 27. ⭐ PER CAUSA (brief-db-presidio-processi-testo-per-causa §5.4.3). Le
    #     righe di un presidio con `colonna_variante` sono guasti diversi: ognuna
    #     sta sotto la sua causa, col rimedio e il «chi agisce» di quella causa.
    #     ⚠️ La colonna si chiama apposta `motivo` e non `causa`: il nome si
    #     legge dal catalogo, e uno scritto nel codice qui non lo troverebbe.
    def test_le_righe_di_un_presidio_a_varianti_si_rendono_per_causa(self) -> None:
        repo = _RepoFinto(
            [_riga(
                "dbops.vw_zero", NATURA_ZERO, colonna_variante="motivo",
                chi_agisce=CHI_AGISCE_SISTEMISTA,
                significato="Segui il rimedio accanto alla causa.",
            )],
            {"dbops.vw_zero": 3},
            {"dbops.vw_zero": [
                {"processo": "p1", "motivo": "TIMER_FERMO"},
                {"processo": "p2", "motivo": "NON_PROGRAMMATO"},
                {"processo": "p3", "motivo": "TIMER_FERMO"},
            ]},
            {"dbops.vw_zero": {
                "TIMER_FERMO": {
                    "causa": "TIMER_FERMO", "chi_agisce": CHI_AGISCE_SISTEMISTA,
                    "significato": "Il timer e' fermo.", "azione": "Riaccendi il timer.",
                },
                "NON_PROGRAMMATO": {
                    "causa": "NON_PROGRAMMATO", "chi_agisce": CHI_AGISCE_SVILUPPO,
                    "significato": "Nessun job lo sveglia.", "azione": "Completa il catalogo.",
                },
            }},
            per_causa={"dbops.vw_zero": [("TIMER_FERMO", 2), ("NON_PROGRAMMATO", 1)]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        cause = digest.allarmi[0].cause
        self.assertEqual(
            [(c["causa"], [r["processo"] for r in c["righe"]]) for c in cause],
            [("TIMER_FERMO", ["p1", "p3"]), ("NON_PROGRAMMATO", ["p2"])],
        )
        _oggetto, testo, html = componi_messaggio(digest)
        for resa in (testo, html.replace("&#x27;", "'")):
            with self.subTest(resa=resa[:20]):
                # Ogni rimedio sta sopra le SUE righe, non sopra quelle dell'altra.
                self.assertLess(resa.index("Riaccendi il timer."), resa.index("processo=p1"))
                self.assertLess(resa.index("processo=p3"), resa.index("Completa il catalogo."))
                self.assertLess(resa.index("Completa il catalogo."), resa.index("processo=p2"))
                self.assertIn("dbops.vw_zero — NON_PROGRAMMATO", resa)
                # ⛔ Il testo NEUTRO del presidio non si ripete sopra le cause:
                #    ognuna porta il suo rimedio, e quello non dice niente.
                self.assertNotIn("Segui il rimedio accanto alla causa.", resa)

    # 28. ⛔ Una causa senza testo NON prende il rimedio del presidio: sarebbe il
    #     rimedio di un altro guasto, cioe' il difetto del brief §1. Si dice.
    def test_una_causa_senza_testo_non_prende_il_rimedio_del_presidio(self) -> None:
        repo = _RepoFinto(
            [_riga(
                "dbops.vw_zero", NATURA_ZERO, colonna_variante="motivo",
                chi_agisce=CHI_AGISCE_SISTEMISTA, azione="Rimedio del presidio.",
            )],
            {"dbops.vw_zero": 2},
            {"dbops.vw_zero": [{"motivo": "INVENTATA"}, {"motivo": None}]},
            per_causa={"dbops.vw_zero": [("INVENTATA", 1), (None, 1)]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(
            [(c["causa"], c["azione"], c["chi_agisce"]) for c in digest.allarmi[0].cause],
            [("INVENTATA", None, None), (None, None, None)],
        )
        _oggetto, testo, html = componi_messaggio(digest)
        for resa in (testo, html):
            with self.subTest(resa=resa[:20]):
                self.assertNotIn("Rimedio del presidio.", resa)
                self.assertIn("dbops.vw_zero — INVENTATA", resa)
                self.assertIn("dbops.vw_zero — causa non indicata", resa)
                self.assertEqual(resa.count("causa non a catalogo"), 1)
                self.assertIn("la riga non dice la sua causa", resa)
        # ⚠️ Senza «chi agisce» le due voci finiscono fra le «senza
        #    indicazione», non nel gruppo del presidio (SISTEMISTA).
        self.assertNotIn(TITOLI_CHI_AGISCE[CHI_AGISCE_SISTEMISTA], testo)
        self.assertIn(TITOLO_CHI_AGISCE_ASSENTE, testo)

    # 29. ⭐ R-2 (§6.4.3). Il presidio e' del sistemista; la causa dello sviluppo
    #     sta OLTRE il campione (nessuna sua riga fra quelle lette) e arriva lo
    #     stesso, dal suo conteggio, nel gruppo dello sviluppo. Prima di R-2 non
    #     sarebbe arrivata da nessuna parte.
    def test_ogni_causa_va_a_chi_la_deve_spegnere_anche_oltre_il_campione(self) -> None:
        repo = _RepoFinto(
            [_riga(
                "dbops.vw_zero", NATURA_ZERO, colonna_variante="motivo",
                chi_agisce=CHI_AGISCE_SISTEMISTA,
            )],
            {"dbops.vw_zero": 9},
            {"dbops.vw_zero": [{"processo": "p1", "motivo": "TIMER_FERMO"}]},
            {"dbops.vw_zero": {
                "TIMER_FERMO": {
                    "causa": "TIMER_FERMO", "chi_agisce": CHI_AGISCE_SISTEMISTA,
                    "significato": "s-t", "azione": "Riaccendi il timer.",
                },
                "NON_PROGRAMMATO": {
                    "causa": "NON_PROGRAMMATO", "chi_agisce": CHI_AGISCE_SVILUPPO,
                    "significato": "s-n", "azione": "Completa il catalogo.",
                },
            }},
            per_causa={"dbops.vw_zero": [("NON_PROGRAMMATO", 7), ("TIMER_FERMO", 2)]},
        )
        digest = calcola_digest(CADENZA_GIORNALIERA, repo=repo)
        self.assertEqual(
            [(c["causa"], c["conteggio"], len(c["righe"])) for c in digest.allarmi[0].cause],
            [("NON_PROGRAMMATO", 7, 0), ("TIMER_FERMO", 2, 1)],
        )
        oggetto, testo, html = componi_messaggio(digest)
        # ⚠️ Oggetto e riepilogo contano PRESIDI: uno, con nove righe.
        self.assertIn("1 in allarme (9 righe)", oggetto)
        self.assertEqual(digest.riepilogo()["allarmi"], 1)
        for resa in (testo, html):
            with self.subTest(resa=resa[:20]):
                sistemista = resa.index(TITOLI_CHI_AGISCE[CHI_AGISCE_SISTEMISTA])
                sviluppo = resa.index(TITOLI_CHI_AGISCE[CHI_AGISCE_SVILUPPO])
                self.assertLess(sistemista, resa.index("dbops.vw_zero — TIMER_FERMO"))
                self.assertLess(resa.index("dbops.vw_zero — TIMER_FERMO"), sviluppo)
                self.assertLess(sviluppo, resa.index("dbops.vw_zero — NON_PROGRAMMATO"))
                self.assertLess(sviluppo, resa.index("Completa il catalogo."))
                self.assertIn("nessuna fra le righe di esempio (7 in tutto)", resa)

    # 30. La voce di una causa con piu' righe di quelle mostrate lo dice col
    #     numero della CAUSA, non del presidio.
    def test_una_causa_con_piu_righe_del_campione_dice_quante_ne_mancano(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, colonna_variante="motivo")],
            {"dbops.vw_zero": 10},
            {"dbops.vw_zero": [{"motivo": "A"}, {"motivo": "A"}]},
            per_causa={"dbops.vw_zero": [("A", 6), ("B", 4)]},
        )
        _oggetto, testo, html = componi_messaggio(
            calcola_digest(CADENZA_GIORNALIERA, repo=repo),
        )
        self.assertIn("dbops.vw_zero — A: 6", testo)
        for resa in (testo, html):
            with self.subTest(resa=resa[:20]):
                self.assertIn("dbops.vw_zero — A", resa)
                self.assertIn("… e altre 4", resa)
                self.assertIn("nessuna fra le righe di esempio (4 in tutto)", resa)
                self.assertNotIn("… e altre 8", resa)


class RigaCompattaTests(SimpleTestCase):
    """Le righe di esempio di una vista nel messaggio (B-6)."""

    # 26. Un istante della riga si scrive nell'ora dell'azienda e nel formato
    #     del BB, come il resto del messaggio: fino al 2026-10-09 era `str()`,
    #     cioe' UTC con `+00:00`.
    @fuso_aziendale_forzato("Europe/Rome")
    def test_un_istante_della_riga_si_scrive_nell_ora_dell_azienda(self) -> None:
        from datetime import UTC, datetime

        riga = {"id": 7, "quando": datetime(2026, 9, 14, 23, 30, 5, tzinfo=UTC), "nota": None}
        self.assertEqual(
            presidi_digest._riga_compatta(riga), "id=7, quando=15-09-2026 01:30:05, nota=—",
        )
