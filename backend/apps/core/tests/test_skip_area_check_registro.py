# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio sulle view che dichiarano `skip_area_check = True` — l'unico
#        attributo che SALTA la catena dei permessi d'area. Due cose che
#        nessuno guardava, e nessuna delle due da' un errore:
#
#        1. `skip_area_check` e' MUTO se la view dichiara anche `area_funzionale`.
#           `ZeroERPPermission.has_permission` lo consulta solo nel ramo
#           «area non risolta» (`area_schema_db is None`): con un'area dichiarata
#           il controllo d'area gira comunque, e lo skip non fa niente. Una view
#           che li dichiara entrambi dice due cose opposte, e vince quella che
#           chi legge il codice non si aspetta — in `pagamenti` un commento di
#           otto righe spiegava PERCHE' serviva lo skip, e lo skip non c'era.
#
#        2. Una view con lo skip che SCRIVE (post/patch/put/delete) senza un
#           `<metodo>_permission` e' aperta a qualunque identita' autenticata:
#           dopo lo skip la catena non guarda piu' niente. E' legittimo solo se
#           il perimetro e' l'identita' stessa (cambio password, le proprie
#           preferenze) — e allora va DETTO, qui, con la ragione.
#
#        I registri sono a cricchetto: rosso se crescono, rosso anche se calano
#        senza che la riga venga tolta — un registro che non cala smette di
#        essere un elenco di eccezioni e diventa il posto in cui si mettono le
#        cose per farle passare.
#
# Note: ⭐ Legge le view DAL PERCORSO REALE: le classi instradate nell'URLconf,
#       con `getattr` — esattamente come le legge la catena — e solo quelle
#       che usano `ZeroERPPermission`, l'unica che lo skip lo consulta.
#       ⛔ La prima stesura (2026-09-12, mattina) leggeva il CORPO delle classi
#       con `ast`, ed era cieca su tre cose che la catena vede: un'area o un
#       `post` EREDITATI (`_ArchiviazioneCodaBaseView` ha quattro figlie cosi'),
#       e le classi fabbricate da una factory (`make_note_views`,
#       `build_documenti_sorgente_views`). E contava una view portale, la cui
#       catena lo skip non lo legge affatto. Un presidio che guarda una cosa
#       diversa da quella che presidia e' verde per il motivo sbagliato.
#       Nessun DB: l'URLconf e' gia' importato dai system check del runner.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_la_scansione_vede_le_view_che_deve_vedere
 1. test_lo_skip_non_convive_con_un_area_dichiarata
 2. test_chi_scrive_con_lo_skip_dichiara_un_permesso
 3. test_chi_e_in_attesa_e_ancora_coperto_dall_area
"""

from dataclasses import dataclass, field
from functools import lru_cache
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.anagrafiche.api.views_ruoli_config import RuoliConfigResolverView
from apps.core.api.email_views import EmailOutboxSendView
from apps.core.api.permissions import ZeroERPPermission, chiamata_in_scrittura
from apps.core.api.rotte import classi_view

# I metodi HTTP che una view puo' servire come scrittura. Se lo fa DAVVERO lo
# decide `chiamata_in_scrittura`, per view: la sede della regola — tutto cio'
# che non e' `view`, compresa la dichiarazione `<metodo>_accesso` (una POST
# che e' una lettura non e' una scrittura scoperta).
_METODI_CANDIDATI: frozenset[str] = frozenset(
    metodo.lower() for metodo in ZeroERPPermission.METHOD_REQUIRES
)


# ⛔ Registro 1 — view in cui `skip_area_check = True` e' MUTO perche' la view
#    dichiara (o eredita) anche `area_funzionale`. Sono un DEBITO, non
#    un'esenzione: per ognuna va deciso se vale l'area (e allora lo skip si
#    toglie, e il commento che lo motiva con lui) o vale lo skip (e allora si
#    toglie l'area — e prima si legge il registro 3 qui sotto, perche' senza
#    area la view resta aperta a chiunque sia autenticato).
#
#    ⭐ Erano QUINDICI il 2026-09-12, e sono cadute tutte lo stesso giorno per
#    decisione di Tid, una per famiglia:
#    - `pagamenti` (4: saldo, rate, sistemazioni, export) → vale lo SKIP: tolta
#      l'area, il commento di otto righe che lo motivava e' finalmente vero;
#    - outbox email (10) → vale l'AREA `config`: tolto lo skip, il comportamento
#      e' identico a prima e il codice adesso lo dice (nota in testa a
#      `email_views.py`). Sei di quelle scrivono senza permesso: con lo skip
#      attivo sarebbero state un relay di posta per qualunque operatore;
#    - `RuoliConfigResolverView` (1) → vale lo SKIP, come i lookup soggetti di
#      cui e' la configurazione (lo consuma `anagrafiche/components/SoggettoResolver`).
#    ⭐ A ZERO dal 2026-09-12. Resta qui perche' e' la sede in cui la prossima
#    finirebbe: una view che dichiara entrambi e' rossa il giorno stesso.
#    Chiave: `modulo.QualName` della classe.
_SKIP_MUTO: dict[str, str] = {}

# ✅ Registro 2 — view con lo skip che scrivono SENZA `<metodo>_permission`, e
#    va bene cosi': il perimetro e' l'IDENTITA' del chiamante. Verificato una
#    per una il 2026-09-12: ognuna passa `request.user` (o il suo id) al
#    service, e non c'e' un id di un altro utente da prendere dalla richiesta.
#    ⚠️ Questo registro deve restare CORTO e ogni riga deve reggere alla
#    domanda «su chi altro puo' agire?». Se la risposta e' «su qualcun altro»,
#    non e' un'esenzione: e' un buco, e la view vuole un permesso.
_SU_SE_STESSI: dict[str, str] = {
    "apps.core.api.change_password_view.ChangePasswordView": "cambia la PROPRIA password",
    "apps.core.api.emittente_attivo_views.EmittenteAttivoView": "sceglie il PROPRIO emittente attivo, fra quelli assegnati",
    "apps.core.api.logout_view.LogoutView": "chiude la PROPRIA sessione",
    "apps.core.api.secondo_fattore_views.SecondoFattoreRegistraView": "configura il PROPRIO secondo fattore",
    "apps.core.api.secondo_fattore_views.SecondoFattoreConfermaView": "conferma il PROPRIO secondo fattore",
    "apps.core.api.secondo_fattore_views.SecondoFattoreCodiciRecuperoView": "rigenera i PROPRI codici di recupero, dietro un codice dell'app",
    "apps.core.api.secondo_fattore_views.SecondoFattoreDisattivaView": "disattiva il PROPRIO secondo fattore, dietro un codice dell'app o di recupero",
    "apps.core.api.sessioni_view.SessioneRevocaView": "revoca una PROPRIA sessione (user_id dal token)",
    "apps.core.api.sessioni_view.SessioniRevocaTutteView": "revoca le PROPRIE altre sessioni",
    "apps.core.api.views_parameters.ParameterOverrideView": "override personale di un parametro (scope utente)",
    "apps.core.api.views_parameters.ParameterOverrideDeleteView": "toglie il PROPRIO override",
    "apps.ui.api.views.ApiListaPreferenzaView": "preferenza di lista dell'UTENTE",
    "apps.ui.api.views.ApiListaIgnorePresetUpdateView": "flag sulla PROPRIA preferenza di lista",
    "apps.ui.api.views_dashboard.ApiDashboardPreferenzaView": "preferenza di dashboard dell'UTENTE",
    "apps.ui.api.views_dashboard.ApiDashboardIgnorePresetUpdateView": "flag sulla PROPRIA preferenza di dashboard",
}

# ⛔ Registro 3 — view con lo skip che scrivono senza permesso e NON agiscono
#    su se' stesse: un DEBITO in attesa della decisione sul registro 1.
#    ⭐ A ZERO dal 2026-09-12: conteneva le sei view dell'outbox email, uscite
#    con la decisione «vale l'area». Resta qui perche' e' la sede in cui la
#    prossima finirebbe — e stare qui NON e' gratis: il test 3 pretende che
#    ognuna sia ANCORA coperta dall'area (cioe' ancora nel registro 1), cosi'
#    togliere l'area senza mettere il permesso fa rosso invece di aprire la
#    view a chiunque sia autenticato.
_IN_ATTESA_DI_DECISIONE: dict[str, str] = {}


@dataclass(frozen=True)
class _Vista:
    chiave: str
    skip: bool
    area_dichiarata: bool
    # Metodi di scrittura che la classe SERVE (definiti o ereditati) e per cui
    # la catena non troverebbe un `<metodo>_permission`.
    scritture_scoperte: frozenset[str] = field(default_factory=frozenset)


# Scopo: chiave stabile di una classe view. Le classi fabbricate da una
#        factory condividono `__qualname__` (`…<locals>.DocumentiList`, sei
#        volte): li' si aggiunge l'area, che e' cio' che le distingue.
def _chiave(cls: type) -> str:
    base = f"{cls.__module__}.{cls.__qualname__}"
    if "<locals>" in cls.__qualname__:
        return f"{base}[area={getattr(cls, 'area_funzionale', None)}]"
    return base


# Scopo: tutte le classi view raggiungibili dall'URLconf, una volta ciascuna,
#        comprese quelle delle rotte montate a condizione (l'assistente AI in
#        CI e' spento): e' codice che il prodotto serve. Il cammino e' il BB
#        `apps.core.api.rotte` (estratto il 2026-09-25, regola del 2).
def _classi_instradate() -> set[type]:
    return classi_view(anche_condizionali=True)


# Scopo: UNA passata sulle view instradate sotto `ZeroERPPermission`, letta con
#        gli stessi `getattr` della catena — cosi' un attributo o un metodo
#        ereditato conta, e una view fabbricata da una factory pure.
# ⚠️ L'area la risolve `ZeroERPPermission._resolve_area`, non una copia sua:
#    e' l'unico modo perche' «dichiarata» qui e «risolta» la' non divergano. Il
#    ramo del `queryset` (oggi nessuna view lo usa) chiederebbe lo schema al DB:
#    lo si tappa alla radice, perche' qui conta se un'area c'e', non quale.
@lru_cache(maxsize=1)
def _scansione() -> dict[str, _Vista]:
    viste: dict[str, _Vista] = {}
    with patch.object(ZeroERPPermission, "_get_model_meta", return_value=(None, None)) as senza_modello:
        for cls in _classi_instradate():
            if ZeroERPPermission not in getattr(cls, "permission_classes", ()):
                continue
            if getattr(cls, "queryset", None) is not None:  # pragma: no cover - nessuna view oggi
                area_dichiarata = True
            else:
                area_dichiarata = ZeroERPPermission._resolve_area(cls, cache={}) is not None
            scoperte = frozenset(
                metodo
                for metodo in _METODI_CANDIDATI
                if getattr(cls, metodo, None) is not None
                and chiamata_in_scrittura(cls, method=metodo.upper())
                and getattr(cls, f"{metodo}_permission", None) is None
            )
            vista = _Vista(
                chiave=_chiave(cls),
                skip=bool(getattr(cls, "skip_area_check", False)),
                area_dichiarata=area_dichiarata,
                scritture_scoperte=scoperte,
            )
            viste[vista.chiave] = vista
        assert senza_modello.called, "la scansione non ha risolto nessuna area: sta guardando la cosa sbagliata"
    return viste


# Scopo: le view in cui lo skip e' muto (skip + area).
def _skip_muto() -> set[str]:
    return {v.chiave for v in _scansione().values() if v.skip and v.area_dichiarata}


# Scopo: le view con lo skip che servono una scrittura senza il suo permesso.
def _scrivono_senza_permesso() -> set[str]:
    return {v.chiave for v in _scansione().values() if v.skip and v.scritture_scoperte}


# Scopo: formatta un elenco di chiavi per un messaggio di fallimento leggibile.
def _elenco(chiavi: set[str]) -> str:
    return "\n  - " + "\n  - ".join(sorted(chiavi))


class SkipAreaCheckRegistroTests(SimpleTestCase):
    def test_la_scansione_vede_le_view_che_deve_vedere(self) -> None:
        """Un presidio che scansiona zero view passa a vuoto: qui non puo'.

        ⚠️ Le due classi sono le stesse che `test_permissions_decisione_skip_area`
        importa e prova: se la scansione non le vede con gli attributi che quel
        test dimostra a runtime, sta guardando una cosa diversa dalla catena.
        """
        viste = _scansione()
        resolver = viste[_chiave(RuoliConfigResolverView)]
        self.assertTrue(resolver.skip and not resolver.area_dichiarata)
        outbox = viste[_chiave(EmailOutboxSendView)]
        self.assertTrue(outbox.area_dichiarata and not outbox.skip)

    def test_lo_skip_non_convive_con_un_area_dichiarata(self) -> None:
        """Skip + area = due dichiarazioni opposte, e vince l'area in silenzio."""
        trovate = _skip_muto()
        nuove = trovate - set(_SKIP_MUTO)
        self.assertEqual(
            nuove, set(),
            "view che dichiarano (o ereditano) `skip_area_check = True` E "
            "`area_funzionale`: lo skip e' MUTO (`ZeroERPPermission` lo legge solo "
            "se l'area non si risolve). Scegliere: o vale l'area (togliere lo "
            "skip) o vale lo skip (togliere l'area — e allora la view scrive senza "
            "cancello: vedi `test_chi_scrive_con_lo_skip_dichiara_un_permesso`)."
            + _elenco(nuove),
        )
        pagate = set(_SKIP_MUTO) - trovate
        self.assertEqual(
            pagate, set(),
            "righe di `_SKIP_MUTO` che non descrivono piu' una view (sanata o "
            "rinominata): togliere la riga, il debito e' pagato."
            + _elenco(pagate),
        )

    def test_chi_scrive_con_lo_skip_dichiara_un_permesso(self) -> None:
        """Dopo lo skip la catena non guarda piu' niente: chi scrive lo dichiara.

        ⚠️ Vale anche per le view del registro 1: la' lo skip e' muto e l'area
        le copre, ma il giorno in cui qualcuno chiude quel debito togliendo
        l'area, e' QUESTO test a dire che il permesso manca.
        """
        trovate = _scrivono_senza_permesso()
        doppie = set(_SU_SE_STESSI) & set(_IN_ATTESA_DI_DECISIONE)
        self.assertEqual(doppie, set(), "una view non puo' stare in entrambi i registri" + _elenco(doppie))
        dichiarate = set(_SU_SE_STESSI) | set(_IN_ATTESA_DI_DECISIONE)
        nuove = trovate - dichiarate
        self.assertEqual(
            nuove, set(),
            "view con `skip_area_check = True` che servono post/patch/put/delete "
            "SENZA il `<metodo>_permission` corrispondente: chiunque sia "
            "autenticato le chiama. O si dichiara l'azione di processo, o — se il "
            "perimetro e' l'identita' del chiamante — la riga va in "
            "`_SU_SE_STESSI` con la ragione."
            + _elenco(nuove),
        )
        pagate = dichiarate - trovate
        self.assertEqual(
            pagate, set(),
            "righe dei registri che non descrivono piu' una view che scrive senza "
            "permesso: togliere la riga."
            + _elenco(pagate),
        )

    def test_chi_e_in_attesa_e_ancora_coperto_dall_area(self) -> None:
        """Il debito del registro 3 regge solo finche' l'area lo copre.

        ⛔ Una view puo' stare in `_IN_ATTESA_DI_DECISIONE` solo perche' il suo
        skip e' muto e l'area la protegge. Togliere l'area senza mettere il
        permesso non chiude un debito: apre la view a chiunque sia autenticato.
        Il messaggio del test 1 direbbe soltanto «togli la riga»; questo dice
        cosa e' appena successo.
        """
        scoperte = set(_IN_ATTESA_DI_DECISIONE) - _skip_muto()
        self.assertEqual(
            scoperte, set(),
            "view in attesa di decisione che NON sono piu' coperte dall'area: "
            "scrivono senza `<metodo>_permission` e adesso lo skip e' attivo, "
            "cioe' le chiama chiunque sia autenticato. Mettere il permesso di "
            "processo PRIMA di togliere `area_funzionale`."
            + _elenco(scoperte),
        )
