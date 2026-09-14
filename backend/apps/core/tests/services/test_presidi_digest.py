# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
18. test_una_corsia_in_corso_si_dice_in_corso_non_fallita   ⭐ 14-09
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.db.presidi_repository import (
    CADENZA_GIORNALIERA,
    CADENZA_SETTIMANALE,
    NATURA_LAVORAZIONE,
    NATURA_REGISTRO,
    NATURA_ZERO,
    PERIMETRO_DEFINER,
    PERIMETRO_LIBERO,
    RigaPresidio,
)
from apps.core.services import presidi_digest
from apps.core.services.presidi_digest import (
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
    ) -> None:
        self._righe = righe
        self._conteggi = conteggi
        self._righe_esempio = righe_esempio or {}
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


class PresidiDigestTests(SimpleTestCase):
    """La forma del digest: cosa entra, cosa si spedisce, cosa si dichiara."""

    def setUp(self) -> None:
        # ⛔ La connessione non deve MAI essere toccata da questi test: se lo
        #    fosse, un mock dimenticato parlerebbe col DB di sviluppo.
        patcher = patch.object(presidi_digest, "connection")
        self.connessione = patcher.start()
        self.addCleanup(patcher.stop)

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
        corse = {"digest_presidi:giornaliera": {
            "last_run_at": "2026-09-10T07:00:00+02:00", "attivo": True,
            "last_ok": True,
        }}
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
            "digest_presidi:giornaliera": {
                "last_run_at": "2026-09-03T07:00:00+02:00",
                "attivo": False, "last_ok": True,
            },
            "digest_presidi:settimanale": {
                "last_run_at": "2026-09-10T07:30:00+02:00",
                "attivo": True, "last_ok": True,
            },
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
            "digest_presidi:giornaliera": {
                "last_run_at": "2026-09-03T07:00:00+02:00",
                "attivo": False, "last_ok": True,
            },
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
            "digest_presidi:settimanale": {
                "last_run_at": "2026-09-10T07:30:00+02:00",
                "attivo": True, "last_ok": True,
            },
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

    # 18. ⛔ `last_ok` ha TRE facce, e la mail ne mostrava due. `None` non e'
    #     un fallimento: e' «nessuna corsa conclusa» — e per la corsia che sta
    #     componendo la mail e' la normalita', perche' la sua riga sul giornale
    #     e' aperta (ok NULL). Il settimanale del 2026-09-14 ha scritto
    #     «digest_presidi:settimanale (FALLITA)» su una corsa che il giornale
    #     dava ok = true mezzo minuto dopo. Da qui: «in corso».
    def test_una_corsia_in_corso_si_dice_in_corso_non_fallita(self) -> None:
        repo = _RepoFinto(
            [_riga("dbops.vw_zero", NATURA_ZERO, cadenza=CADENZA_SETTIMANALE)],
            {"dbops.vw_zero": 0},
        )
        giornale = _MaintenanceFinto({
            "digest_presidi:giornaliera": {
                "last_run_at": "2026-09-14T07:00:00+02:00",
                "attivo": True, "last_ok": True,
            },
            # La corsia che sta girando ADESSO: viva, e senza esito.
            "digest_presidi:settimanale": {
                "last_run_at": "2026-09-14T07:30:49+02:00",
                "attivo": True, "last_ok": None,
            },
        })
        digest = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo, html = componi_messaggio(digest)
        # ⚠️ L'esito si legge SULLA RIGA della corsia: «in corso» da qualche
        #    parte nel corpo non dice a quale corsia appartiene, e uno scambio
        #    fra le due passerebbe. La finestra si chiude alla prima parentesi
        #    — l'HTML e' una riga sola, e un match pigro salterebbe alla corsia
        #    dopo; il `</code>` opzionale e' l'unica differenza fra le due rese.
        for corpo in (testo, html):
            self.assertNotIn("FALLITA", corpo)
            self.assertRegex(corpo, r"digest_presidi:settimanale(?:</code>)?:[^()]*\(in corso\)")
            self.assertRegex(corpo, r"digest_presidi:giornaliera(?:</code>)?:[^()]*\(ok\)")
        # ⚠️ E `False` resta FALLITA: la terza faccia non ha ammorbidito le
        #    altre due.
        giornale_ko = _MaintenanceFinto({
            "digest_presidi:settimanale": {
                "last_run_at": "2026-09-07T07:30:00+02:00",
                "attivo": False, "last_ok": False,
            },
        })
        digest_ko = calcola_digest(
            CADENZA_SETTIMANALE, repo=repo, maintenance=giornale_ko,
            processi=_ProcessiFinto(11520),
        )
        _oggetto, testo_ko, html_ko = componi_messaggio(digest_ko)
        self.assertIn("FALLITA", testo_ko)
        self.assertIn("<strong>FALLITA</strong>", html_ko)
