# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `perimetro_emittente` — la domanda
#        «questa persona sta guardando un emittente solo, o piu' di uno?» e il
#        rifiuto che ne discende per le liste non certificate.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
#
# ⚠️ Il caso che si sbaglia scrivendo questi test e' lo scope a UN elemento:
#        e' quello del 99% degli utenti, quindi un file che provasse solo
#        «multi -> rifiuta» sarebbe verde anche se il cancello scattasse
#        sempre. I due versi si asseriscono entrambi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) scope_universo_e_multi                    — None (tutti) -> True
 2) scope_due_emittenti_e_multi               — [a, b] -> True
 3) scope_singolo_non_e_multi                 — [a] -> False
 4) scope_vuoto_non_e_multi                   — [] (nessun accesso) -> False
 5) per_codice_non_legge_il_catalogo_se_lo_scope_e_singolo  — zero query
 6) per_codice_rifiuta_su_flag_falso          — codice e messaggio giusti
 7) per_codice_tace_su_flag_vero              — la lista certificata passa
 8) per_codice_lista_sconosciuta_e_errore_tecnico — non e' un rifiuto di perimetro
 9) per_codice_tace_se_la_richiesta_fissa_un_emittente — il tab nel drawer
10) per_codice_risolve_lo_scope_una_volta_sola — le due domande condividono la cache
11-13) richiede_scelta_emittente nei suoi tre termini
13-bis) la lista SENZA perimetro non chiede niente — e per un'altra ragione
14-18) emittente_esplicito_da_query: uno / nessuno / due / vuoto / non numerico
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.lista_catalogo_repository import FlagPerimetroLista
from apps.core.services import perimetro_emittente as pe
from apps.core.services.service_errors import ServiceError

_SCOPE = "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids"
_CATALOGO = "apps.core.services.perimetro_emittente.fetch_flag_perimetro"


# Scopo: i due flag di perimetro come li consegna il catalogo.
# ⚠️ Nominati e non una tupla nuda: sono due booleani adiacenti con significati
#    opposti, e scambiarli non solleverebbe niente.
def _flag(*, multi=False, perimetro=True):
    return FlagPerimetroLista(multi_emittente=multi, perimetro_emittente=perimetro)


def _user(user_id: int = 42):
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


class ScopeMultiEmittenteTests(TestCase):
    """La cardinalita' dello scope, nei suoi tre stati."""

    @patch(_SCOPE, return_value=None)
    def test_scope_universo_e_multi(self, _m) -> None:
        """`None` = nessuna restrizione = TUTTI gli emittenti."""
        self.assertTrue(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[72, 159])
    def test_scope_due_emittenti_e_multi(self, _m) -> None:
        self.assertTrue(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[72])
    def test_scope_singolo_non_e_multi(self, _m) -> None:
        """Il caso normale: operatore, o super admin con emittente attivo."""
        self.assertFalse(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[])
    def test_scope_vuoto_non_e_multi(self, _m) -> None:
        """`[]` = nessun accesso.

        ⚠️ Non e' un'ambiguita' da sciogliere: chi non vede niente non ha due
        emittenti fra cui scegliere, e il cancello gli offrirebbe una tendina
        vuota. Il suo problema — configurazione mancante, dopo P-2a — si vede
        dalla lista vuota e da `dbops.vw_operatori_senza_emittente`.
        """
        self.assertFalse(pe.scope_multi_emittente(_user()))


class GuardListaPerCodiceTests(TestCase):
    """La catena completa: perimetro, poi catalogo, poi rifiuto.

    ⚠️ Qui c'erano anche tre test su un helper interno che prendeva il flag
    gia' risolto. Sono stati tolti con l'helper: verificavano gli STESSI due
    versi (flag acceso -> passa, flag spento + perimetro multiplo -> rifiuta)
    che i test qui sotto coprono passando dalla porta vera. Un test in piu' su
    una funzione in meno non aggiungeva copertura: aggiungeva un secondo posto
    da cambiare.
    """

    @patch(_CATALOGO)
    @patch(_SCOPE, return_value=[72])
    def test_per_codice_non_legge_il_catalogo_se_lo_scope_e_singolo(
        self, _m_scope, m_catalogo
    ) -> None:
        """⭐ L'ordine delle due domande e' la ragione per cui la funzione esiste.

        Nel 99% dei casi il perimetro e' singolo e la query al catalogo NON
        deve nemmeno partire: invertire le due domande costerebbe un
        round-trip su ogni apertura di lista per un cancello che non scatta.
        """
        pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")
        m_catalogo.assert_not_called()

    @patch(_CATALOGO, return_value=_flag(multi=False))
    @patch(_SCOPE, return_value=None)
    def test_per_codice_rifiuta_su_flag_falso(self, _m_scope, m_catalogo) -> None:
        with self.assertRaises(ServiceError) as ctx:
            pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")
        # ⚠️ Il codice si asserisce per NOME, non «un errore qualunque»: un
        # rifiuto generico verrebbe tradotto in 400 e direbbe all'operatore che
        # ha sbagliato a scrivere qualcosa.
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE")
        self.assertIn("emittente", ctx.exception.message.lower())
        m_catalogo.assert_called_once_with("vendite.x")

    @patch(_CATALOGO, return_value=_flag(multi=True))
    @patch(_SCOPE, return_value=None)
    def test_per_codice_tace_su_flag_vero(self, _m_scope, _m_catalogo) -> None:
        pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")

    @patch(_CATALOGO, return_value=None)
    @patch(_SCOPE, return_value=None)
    def test_per_codice_lista_sconosciuta_e_errore_tecnico(
        self, _m_scope, _m_catalogo
    ) -> None:
        """Una view che dichiara un `lista_codice` inesistente e' un difetto NOSTRO.

        ⚠️ Non si traduce in «scegli un emittente»: manderebbe l'operatore a
        risolvere un problema che non lo riguarda, e per giunta senza effetto.
        Non si tace nemmeno, o il presidio resterebbe spento in silenzio.
        """
        with self.assertRaises(ServiceError) as ctx:
            pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.inesistente")
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_NON_TROVATA")

    @patch(_CATALOGO, return_value=_flag(multi=False))
    @patch(_SCOPE, return_value=None)
    def test_per_codice_tace_se_la_richiesta_fissa_un_emittente(
        self, _m_scope, _m_catalogo
    ) -> None:
        """⭐ Lista NON certificata + perimetro multiplo: rifiuterebbe. Ma se la
        richiesta fissa un emittente, l'ambiguita' non c'e' — e' il tab-lista
        dentro il drawer di un emittente, dove sbarrare significherebbe chiedere
        di scegliere cio' che l'operatore ha gia' aperto davanti."""
        pe.guard_lista_per_codice(
            user=_user(), lista_codice="vendite.x", emittente_esplicito=72
        )

    @patch(_CATALOGO, return_value=_flag(multi=False))
    @patch(_SCOPE, return_value=None)
    def test_per_codice_risolve_lo_scope_una_volta_sola(
        self, m_scope, _m_catalogo
    ) -> None:
        """⚠️ La domanda sullo scope viene posta DUE volte — qui e dentro
        `richiede_scelta_emittente`, che e' la sede unica della conclusione — e
        costa una query. Le due devono condividere la stessa cache: senza, ogni
        lista non certificata pagherebbe il doppio, e sarebbe il prezzo di aver
        tolto una duplicazione."""
        with self.assertRaises(ServiceError):
            pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")
        cache_usate = [c.kwargs.get("cache") for c in m_scope.call_args_list]
        self.assertEqual(len(cache_usate), 2, "lo scope non e' stato richiesto due volte")
        self.assertIsNotNone(cache_usate[0], "nessuna cache: la seconda e' una query vera")
        self.assertIs(cache_usate[0], cache_usate[1])


class GuardListaSenzaPerimetroTests(TestCase):
    """⭐ Il terzo stato (§12.1, 2026-09-02): la lista che un perimetro non ce l'ha."""

    @patch(_CATALOGO, return_value=_flag(multi=False, perimetro=False))
    @patch(_SCOPE, return_value=None)
    def test_lista_senza_perimetro_non_sbarra_nessuno(self, _m_scope, _m_cat) -> None:
        """Catalogo GLOBALE: nessuna riga appartiene a un emittente.

        ⛔ E il flag `multi_emittente` resta FALSE, ed e' corretto: dichiarare
        `true` avrebbe significato «so dire da quale emittente arriva ogni
        riga» — falso, e per giunta con due pgTAP che lo verificano. Le due
        domande sono diverse, e questa lista risponde «non c'e' niente da
        dire», non «so dirlo».
        """
        pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.famiglie_documento")


class RichiedeSceltaEmittenteTests(TestCase):
    """La conclusione unica, nei suoi tre termini."""

    @patch(_SCOPE, return_value=None)
    def test_lista_certificata_non_chiede_niente(self, _m) -> None:
        self.assertFalse(
            pe.richiede_scelta_emittente(user=_user(), multi_emittente=True)
        )

    @patch(_SCOPE, return_value=None)
    def test_lista_non_certificata_con_perimetro_multiplo_chiede(self, _m) -> None:
        self.assertTrue(
            pe.richiede_scelta_emittente(user=_user(), multi_emittente=False)
        )

    @patch(_SCOPE, return_value=None)
    def test_emittente_esplicito_scioglie_l_ambiguita(self, m_scope) -> None:
        """⭐ E la domanda sullo scope non parte nemmeno: e' l'unica dei tre
        termini che costa una query, e va per ultima."""
        self.assertFalse(
            pe.richiede_scelta_emittente(
                user=_user(), multi_emittente=False, emittente_esplicito=72
            )
        )
        m_scope.assert_not_called()


class EmittenteEsplicitoDaQueryTests(TestCase):
    """Cosa vale come «la richiesta fissa un emittente», e cosa no."""

    def _q(self, querystring: str):
        from django.http import QueryDict

        return QueryDict(querystring)

    def test_un_valore_numerico_vale(self) -> None:
        self.assertEqual(
            pe.emittente_esplicito_da_query(self._q("e=72"), nome="e"), 72
        )

    def test_assente_non_vale(self) -> None:
        self.assertIsNone(pe.emittente_esplicito_da_query(self._q(""), nome="e"))

    def test_due_valori_non_valgono(self) -> None:
        """⛔ `?e=1&e=2` e' ESATTAMENTE l'ambiguita' che il cancello rifiuta:
        leggerne uno solo la trasformerebbe in un lasciapassare."""
        self.assertIsNone(
            pe.emittente_esplicito_da_query(self._q("e=1&e=2"), nome="e")
        )

    def test_valore_vuoto_non_vale(self) -> None:
        self.assertIsNone(pe.emittente_esplicito_da_query(self._q("e="), nome="e"))

    def test_valore_non_numerico_non_vale(self) -> None:
        self.assertIsNone(
            pe.emittente_esplicito_da_query(self._q("e=pippo"), nome="e")
        )

    def test_senza_nome_dichiarato_non_si_legge(self) -> None:
        """La query da sola non conta: e' la view a dire quale parametro fissa
        l'emittente, perche' il progetto ne usa piu' d'uno (soggetto-ruolo e PK
        dell'emittente fiscale non sono la stessa cosa)."""
        self.assertIsNone(pe.emittente_esplicito_da_query(self._q("e=72"), nome=""))

    @patch(_SCOPE, return_value=None)
    def test_lista_senza_perimetro_non_chiede_e_non_interroga_lo_scope(self, m_scope) -> None:
        """⭐ Apre come `multi_emittente`, ma NON per la stessa ragione: li' un
        emittente c'e' e la riga lo dice, qui non c'e' niente da dire. I due
        rami restano separati perche' il giorno che uno dei due cambia si deve
        poter toccare quello, non una condizione che li ha fusi."""
        self.assertFalse(
            pe.richiede_scelta_emittente(
                user=_user(), multi_emittente=False, perimetro_emittente=False,
            ),
        )
        m_scope.assert_not_called()

    @patch(_SCOPE, return_value=None)
    def test_perimetro_omesso_vale_TRUE_ed_e_il_verso_prudente(self, _m) -> None:
        """⚠️ Il default del parametro e' quello della colonna: chi non dichiara
        niente ha un perimetro. Un default `False` avrebbe aperto il cancello su
        tutte le liste insieme, in silenzio."""
        self.assertTrue(
            pe.richiede_scelta_emittente(user=_user(), multi_emittente=False),
        )
