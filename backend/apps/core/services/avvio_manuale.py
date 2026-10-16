# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «ESEGUI ORA» su una sveglia di deploy — la sede unica di cio' che il
#        verbo, la capability nel dettaglio del processo e l'handler del
#        drenatore devono sapere INSIEME: il tipo di coda, l'handler, la chiave
#        di idempotenza, il tetto del sottoprocesso.
# Note: ⭐ Il disegno (brief-db-avvio-manuale-di-un-processo.md §1 e §8,
#        piano-be-fe-avvio-manuale-di-un-processo.md §1): una persona
#        autorizzata preme «Esegui ora» su una sveglia; il web NON esegue
#        niente — accoda un lavoro `ESEGUI_PROCESSO` su `dbops.coda_lavori`
#        con l'identita' di chi ha premuto; il drenatore lo prende e lancia
#        `bin/run-command.sh <comando>` come sottoprocesso, la STESSA riga che
#        il timer esegue, meno l'orario. Il comando si registra sul giornale
#        sotto il proprio processo con `origine = COMMAND` e l'utente di chi
#        ha premuto (`job_run.py`, dall'ambiente).
#        ⛔ Nessuna unit e nessun comando arrivano dal client: il client manda
#        `processo_codice` e `unit`, e tutto il resto si risolve dal dichiarato
#        di deploy (`sveglie.py`), che e' la whitelist.
#        ⭐ Il PREDICATO «questa sveglia si puo' lanciare a mano?» e' la
#        `fn_check_*` di questo verbo, in Python perche' la whitelist e' del
#        deploy. Risponde con un array ORDINATO di motivi (il primo e' quello
#        che si mostra) letto da TRE consumatori — la capability nel dettaglio
#        del processo, il rifiuto dell'endpoint, il ricontrollo dell'handler —
#        cosi' tooltip e rifiuto non «coincidono oggi»: non possono divergere
#        (api.md §Capability di riga, «il backend trasporta, non deduce»).
#        ⛔ Il motivo «gia' in coda» NON lo valuta l'handler (lui E' il lavoro
#        vivo): il predicato lo riceve come parametro, e chi non lo sa passa
#        `None`. «Vivo» e' `STATI_VIVI` del repository, letto con
#        `lavori_vivi_per_chiave` — mai ricopiato qui.
#        ⚠️ Le `reason_key` le ha fissate il FE (piano §2.5, `locales/it.json`):
#        qui si emettono ESATTAMENTE quelle. Il presidio e' il test che legge
#        il drawer e i locales (`test_processi_esegui_ora`).
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.core.services.service_errors import E_CONFIG_MANCANTE, ServiceError
from apps.core.services.sveglie import Sveglia

# Il tipo di coda seminato in `dbops.coda_lavori_tipi` (brief §4.2) e il suo
# `handler_code`: il registry Python lega il secondo alla funzione al boot
# (`CoreConfig.ready()`), mai per auto-discovery.
JOB_TYPE_ESEGUI_PROCESSO = "ESEGUI_PROCESSO"
HANDLER_CODE = "esegui_processo_default"

# ⭐ IL TETTO DEL SOTTOPROCESSO, in secondi — decisione 2a di Tid (brief §8.5):
#    a mano si lanciano SOLO comandi brevi. Il drenatore e' un timer oneshot
#    ogni minuto e, mentre aspetta il sottoprocesso, non drena altro (un giro
#    di fatturazione dal cockpit, l'avviso del guardiano): un tetto largo
#    farebbe dire «worker fermo» al badge e `MUTO` al panorama su un sistema
#    che sta facendo cio' che gli e' stato chiesto.
# ⛔ Il numero non e' libero, e lo pinna `test_avvio_manuale_tetto` su due
#    limiti letti dal repo: sotto la META' della tolleranza del drenatore a
#    catalogo (`draina_coda_lavori`, `processi.csv`) — una corsa che dura il
#    tetto intero lascia il segno di vita in tempo — e sotto
#    `STALE_MINUTI_DEFAULT` del reaper, che con `max_tentativi = 1` manderebbe
#    in ERRORE un lavoro il cui comando sta ancora finendo (brief §8.2.3).
# ⚠️ Un comando che lo supera va in ERRORE terminale con un messaggio che dice
#    «troppo lungo per «Esegui ora»», non in silenzio; e una sveglia lunga per
#    natura non e' candidata (`avvio_manuale = false` nel dichiarato).
TETTO_SOTTOPROCESSO_SECONDI = 300


# Scopo: la chiave di idempotenza di business di un lavoro «Esegui ora»: una
#        per unit, sui lavori VIVI (`uq_coda_lavori_vivo_idem`). Due click, un
#        lavoro; un lavoro finito, e si puo' premere di nuovo.
# ⛔ La forma sta QUI e basta: la scrive chi accoda, la legge chi guarda se
#    «c'e' gia'» (capability) — due sedi della forma divergerebbero alla
#    prima modifica e la capability guarderebbe una chiave che nessuno scrive.
def chiave_idempotenza(unit: str) -> str:
    return f"esegui:{unit}"


# I motivi del predicato (a catalogo dal 2026-09-15, brief §9.2) e i due
# esiti dell'handler. Le CLASSI stanno nel file generato dal catalogo, non
# qui: il 2 e' `NON_DISPONIBILE` (501) per decisione del DB — «esiste ma e'
# spenta», la famiglia di `E_JOB_TYPE_NON_ATTIVO` — e il 1 `NON_ESEGUIBILE`
# (422): non e' spenta, e' per natura non candidata.
# ⭐ Dal 2026-10-16 il 2 vuol dire «il PROCESSO e' spento su questa
#    installazione» (brief-db-processi-accensione-per-ambiente P-2): fino ad
#    allora era `abilita = false` di `sveglie.json`. Il codice resta, il
#    significato e' lo stesso gesto — non parte ne' dal timer ne' a mano.
#    Il 2-bis e' l'accensione NON decidibile (ambiente non dichiarato):
#    `E_CONFIG_MANCANTE`, lo stesso codice con cui il DB la rifiuta alla
#    sveglia (`maintenance.fn_sveglia_accesa`).
E_SVEGLIA_NON_AVVIABILE_A_MANO = "E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO"
E_PROCESSO_SPENTO = "E_PROCESSO_SVEGLIA_NON_ABILITATA"
E_ACCENSIONE_NON_DECIDIBILE = E_CONFIG_MANCANTE
E_AVVIO_GIA_IN_CODA = "E_PROCESSO_AVVIO_GIA_IN_CODA"
E_AVVIO_TROPPO_LUNGO = "E_PROCESSO_AVVIO_TROPPO_LUNGO"
E_AVVIO_FALLITO = "E_PROCESSO_AVVIO_FALLITO"

# ⭐ La chiave i18n del tooltip, per motivo: e' la forma gia' in uso per le
#    check del DB (`amministrazione.<risorsa>.<verbo>_blocco.<motivo>`), e i
#    tre indirizzi ESISTONO nei locales perche' li ha scritti il FE per primo.
# ⛔ Non e' un template `f"...{codice.lower()}"`: un indirizzo derivato per
#    convenzione da un nome di codice si rompe in silenzio alla prima
#    rinomina, e a video si vede il codice macchina invece della frase.
_PREFISSO_REASON_KEY = "amministrazione.processi.esegui_ora_blocco."
REASON_KEY_PER_CODICE: dict[str, str] = {
    E_SVEGLIA_NON_AVVIABILE_A_MANO: _PREFISSO_REASON_KEY + "non_avviabile_a_mano",
    E_PROCESSO_SPENTO: _PREFISSO_REASON_KEY + "non_abilitata",
    E_ACCENSIONE_NON_DECIDIBILE: _PREFISSO_REASON_KEY + "non_decidibile",
    E_AVVIO_GIA_IN_CODA: _PREFISSO_REASON_KEY + "gia_in_coda",
}

# I nomi con cui la capability viaggia nel dettaglio del processo — famiglia 1
# di `api.md` (motivo e chiave discendono dal flag). ⚠️ Sono i nomi che il
# drawer LEGGE (`bloccoAttivo(riga, 'can_esegui_ora', 'can_esegui_ora')`):
# cambiarne uno qui senza cambiarlo la' non fallisce, spegne il tooltip.
CAPABILITY_FLAG = "can_esegui_ora"
CAPABILITY_REASON = "can_esegui_ora_reason"
CAPABILITY_REASON_KEY = "can_esegui_ora_reason_key"
CAPABILITY_DETTAGLIO = "can_esegui_ora_dettaglio"


# Scopo: un motivo per cui «Esegui ora» NON si puo' fare adesso, con tutto
#        cio' che i tre consumatori ne devono sapere: il codice (classe e
#        status dal catalogo), la chiave i18n del tooltip, i parametri con
#        NOME per la frase del client (`dettaglio`, come pretende
#        `bloccoMotivo.js`) e la frase gia' composta per il rifiuto (unit e id
#        DENTRO, mai il nome di un parametro — AGENTS.md §tre canali).
@dataclass(frozen=True)
class MotivoEseguiOra:
    codice: str
    messaggio: str
    dettaglio: dict[str, Any] | None = None

    # Scopo: la chiave i18n del motivo, dal registro qui sopra.
    @property
    def reason_key(self) -> str:
        return REASON_KEY_PER_CODICE[self.codice]

    # Scopo: il `ServiceError` con cui endpoint e handler RIFIUTANO questo
    #        motivo. Il `context` porta i parametri con nome (gli stessi del
    #        `dettaglio`) piu' l'`extra` del chiamante — l'handler ci mette il
    #        marcatore «terminale», l'endpoint niente.
    def come_errore(self, **extra: Any) -> ServiceError:
        return ServiceError(
            code=self.codice,
            message=self.messaggio,
            context={**(self.dettaglio or {}), **extra},
        )


# Scopo: ⭐ IL PREDICATO. «Questa sveglia si puo' lanciare a mano, adesso?»
#        Ritorna i motivi per cui NO, nell'ordine in cui si leggono (il primo
#        e' quello che si mostra e con cui si rifiuta); lista vuota = si puo'.
#        Puro: nessun database, si prova senza.
#
#        I motivi, nell'ordine del piano §2.2:
#          1. `forma = servizio`, oppure `avvio_manuale = false` nel dichiarato
#             — non e' un candidato: e' NATURA (il servizio non ha una corsa da
#             lanciare; il comando lungo terrebbe fermo il drenatore, decisione
#             2a di Tid). Sul servizio il client non mostra nemmeno il pulsante;
#             sul timer non candidato lo mostra spento con questa frase;
#          2. il PROCESSO e' spento su questa installazione (`acceso` False,
#             dal DB: la scelta a mano o il default per ambiente) — P-2 di
#             Tid: spento vuol dire spento anche a mano, prima lo si
#             riaccende. `acceso` None (ambiente non dichiarato) e' il 2-bis:
#             non si sa, e non si lancia;
#          3. c'e' GIA' un lavoro vivo con la stessa chiave — ricevuto come
#             parametro (`{"id", "stato"}` da `lavori_vivi_per_chiave`, o
#             `None` per «non lo so / non lo guardo»).
# ⚠️ Un servizio e' anche `avvio_manuale = false` per costruzione (lo impone
#    `carica_sveglie`): la disgiunzione e' scritta per intero lo stesso, perche'
#    il predicato non deve dipendere da cio' che il caricatore impone oggi.
# ⭐ `acceso` lo legge il CHIAMANTE dal DB, sempre da
#    `dbops.fn_processo_acceso_dichiarato` (`ProcessiRepository.acceso_processo`
#    per rifiuto e ricontrollo, `accensione_processo` per il dettaglio che lo
#    descrive), con la stessa risposta per i tre consumatori: il
#    predicato resta puro, e tooltip, rifiuto e ricontrollo non divergono.
#    E' obbligatorio e senza default: un chiamante che lo dimentica non deve
#    far passare un processo spento.
def motivi_esegui_ora(
    sveglia: Sveglia, *, acceso: bool | None, lavoro_vivo: dict[str, Any] | None,
) -> list[MotivoEseguiOra]:
    motivi: list[MotivoEseguiOra] = []
    if not sveglia.e_timer or not sveglia.avvio_manuale:
        motivi.append(MotivoEseguiOra(
            codice=E_SVEGLIA_NON_AVVIABILE_A_MANO,
            messaggio=(
                f"La sveglia {sveglia.unit} non e' avviabile a mano: e' un "
                f"servizio sempre acceso oppure un comando dichiarato non "
                f"candidato a «Esegui ora»."
            ),
        ))
    if acceso is False:
        motivi.append(MotivoEseguiOra(
            codice=E_PROCESSO_SPENTO,
            messaggio=(
                f"Il processo {sveglia.processo_codice} e' spento su questa "
                f"installazione: il comando non parte ne' dalla sveglia ne' a "
                f"mano. Riaccendilo prima di eseguirlo."
            ),
            dettaglio={"processo": sveglia.processo_codice},
        ))
    elif acceso is None:
        motivi.append(MotivoEseguiOra(
            codice=E_ACCENSIONE_NON_DECIDIBILE,
            messaggio=(
                f"Non si sa se il processo {sveglia.processo_codice} sia acceso: "
                f"l'ambiente di questa installazione non e' dichiarato."
            ),
            dettaglio={"processo": sveglia.processo_codice},
        ))
    if lavoro_vivo is not None:
        job_id = int(lavoro_vivo["id"])
        motivi.append(MotivoEseguiOra(
            codice=E_AVVIO_GIA_IN_CODA,
            messaggio=(
                f"Un avvio della sveglia {sveglia.unit} e' gia' in coda "
                f"(lavoro {job_id}): attendi che finisca prima di chiederne "
                f"un altro."
            ),
            dettaglio={"job_id": job_id},
        ))
    return motivi


# Scopo: la capability di riga — i quattro campi `can_esegui_ora*` — dal
#        primo motivo. Il flag si DERIVA dal motivo (`reason is None`), mai
#        calcolato a parte: e' la regola di `api.md`, ed e' cio' che rende
#        impossibile un pulsante acceso su un gesto che l'endpoint rifiuta.
def capability_esegui_ora(
    sveglia: Sveglia, *, acceso: bool | None, lavoro_vivo: dict[str, Any] | None,
) -> dict[str, Any]:
    motivi = motivi_esegui_ora(sveglia, acceso=acceso, lavoro_vivo=lavoro_vivo)
    primo = motivi[0] if motivi else None
    return {
        CAPABILITY_FLAG: primo is None,
        CAPABILITY_REASON: primo.codice if primo else None,
        CAPABILITY_REASON_KEY: primo.reason_key if primo else None,
        CAPABILITY_DETTAGLIO: primo.dettaglio if primo else None,
    }


# Scopo: `dovuto` come viaggia al client — `ogni`, `giorno` (indice della
#        settimana, 0 = lunedi', o giorno del mese; None per ogni giorno) e
#        `dalle` (`HH:MM`, fuso dell'azienda) — o None se la sveglia lavora a
#        ogni sveglia.
def _dovuto_per_il_client(sveglia: Sveglia) -> dict[str, Any] | None:
    d = sveglia.dovuto
    if d is None:
        return None
    return {"ogni": d.ogni, "giorno": d.giorno, "dalle": d.dalle.strftime("%H:%M")}


# Scopo: la riga di una sveglia come viaggia in `sveglie[]` del dettaglio del
#        processo (piano §2.5): il dichiarato di deploy — quello che il client
#        MOSTRA — piu' la capability — quella su cui il client DECIDE.
# ⚠️ `comando` esce come lista, non joinata: chi la mostra la unisce con uno
#    spazio, ma la forma vera e' l'argv, e un client che volesse
#    evidenziare il primo token (il management command) lo puo' fare.
def riga_sveglia(
    sveglia: Sveglia, *, acceso: bool | None, lavoro_vivo: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "unit": sveglia.unit,
        "forma": sveglia.forma,
        "comando": list(sveglia.comando),
        "oncalendar": sveglia.oncalendar,
        # ⭐ Sulle sveglie calendariali `oncalendar` e' la SVEGLIA (ogni ora),
        #    non la cadenza del lavoro: quella e' `dovuto`, nel fuso
        #    dell'azienda (brief un-solo-fuso-aziendale T-9). Mostrare il solo
        #    `oncalendar` direbbe «ogni ora» a un digest settimanale.
        "dovuto": _dovuto_per_il_client(sveglia),
        # ⛔ Niente `abilita` (ritirato il 2026-10-16): l'accensione e' del
        #    PROCESSO, e viaggia una volta nel dettaglio (`accensione`).
        "avvio_manuale": sveglia.avvio_manuale,
        "nota": sveglia.nota,
        **capability_esegui_ora(sveglia, acceso=acceso, lavoro_vivo=lavoro_vivo),
    }
