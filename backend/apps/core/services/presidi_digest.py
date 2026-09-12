# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL DIGEST DEI PRESIDI — legge il catalogo `dbops.presidi`, conta le
#        righe che chiedono un intervento e ne compone il messaggio per una
#        persona. E' il destinatario che alle viste di presidio mancava.
# Note: ⛔ QUI NON C'E' NESSUN ELENCO DI VISTE E NESSUN ELENCO DI SOGLIE. Che
#        cosa si guarda, con che cadenza, e che cosa significa una riga lo dice
#        il CATALOGO: il digest fa una domanda sola — «cosa guardo a questa
#        cadenza?» — e mette in fila la risposta.
#
#        ⭐ E LA CADENZA E' ANCHE IL FILTRO DEL DIGEST: il
#        `CHECK chk_presidi_fuori_digest_cadenza_mai` garantisce a database che
#        INVENTARIO e CANCELLO abbiano cadenza `MAI`, quindi non serve un elenco
#        di nature da escludere — che sarebbe la stessa regola scritta due
#        volte, e la seconda copia non conosce la natura che nascera' domani.
#
#        ⛔ IL SILENZIO E' IL CASO NORMALE, MA NON A OGNI CADENZA. Un digest che
#        ripete ogni giorno un numero che non cambia viene ignorato al secondo
#        invio — cioe' finisce come il presidio che voleva salvare. Ma «il digest
#        muto» e «il digest morto» si scrivono uguale: per questo alla cadenza
#        del BATTITO si parte comunque, con in testa le proprie ultime corse.
#        E' la firma di R-12 (`apply_storicizza_weekly`, morto ogni settimana per
#        sei mesi e scoperto per caso) applicata al presidio dei presidi.
#
#        ⛔ E UN PRESIDIO CHE NON SI E' POTUTO LEGGERE SI DICE. Se il conteggio
#        solleva — vista sparita, nome non piu' a catalogo — quella riga finisce
#        fra i «non letti» e vale come un allarme: tacere sarebbe la stessa
#        cecita' che `dbops.fn_conta_presidio` esiste per chiudere.
#
#        Brief: work-in-progress/brief-db-un-destinatario-per-i-presidi.md §5, §8.2.
# ------------------------------------------------------------

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from django.conf import settings
from django.db import connection

from apps.core.db.email_repository import EmailRepository
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.db.presidi_repository import (
    CADENZA_MAI,
    CADENZA_SETTIMANALE,
    CADENZE,
    NATURA_LAVORAZIONE,
    NATURA_REGISTRO,
    NATURA_ZERO,
    PERIMETRO_DEFINER,
    PERIMETRO_LIBERO,
    PresidiRepository,
)
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.email_constants import AMBITO_SISTEMA
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI

logger = logging.getLogger(__name__)

# Le cadenze a cui il digest gira: TUTTE quelle del catalogo tranne `MAI`.
# ⭐ SI DERIVA, non si elenca. Un elenco scritto a mano qui resterebbe indietro
#    il giorno in cui il catalogo ammette una cadenza nuova, e quella cadenza
#    non verrebbe guardata da NESSUNA corsa — cioe' le sue viste uscirebbero dal
#    digest in silenzio, che e' l'unico verso in cui un presidio marcisce senza
#    che nessuno se ne accorga.
# ⚠️ `MAI` e' l'unica esclusa, ed e' il motivo per cui quel valore esiste:
#    dichiara che quella vista dal digest resta fuori.
CADENZE_DEL_DIGEST = tuple(c for c in CADENZE if c != CADENZA_MAI)

# ⭐ LA CADENZA DEL BATTITO. A questa cadenza il digest parte e si fa vivo anche
#    quando non ha niente da dire: e' l'unico modo perche' la sua morte si veda.
# ⛔ Non e' la giornaliera, ed e' una scelta: un messaggio al giorno che dice
#    «niente da segnalare» e' esattamente la posta che si impara ad archiviare
#    senza aprire. Una volta a settimana no.
CADENZA_BATTITO = CADENZA_SETTIMANALE

# Scopo: il nome con cui una CORSIA del digest si registra sul giornale dei run.
# ⭐ La forma sta in UNA sede, ed e' quella che il battito ritrova. Comporla nel
#    command e leggerla altrove sarebbe lo stesso nome scritto due volte — e la
#    seconda copia non si accorge quando la prima cambia.
# ⚠️ Si deriva dalla CADENZA del catalogo, non dalla parola scritta sulla riga di
#    comando: un alias nuovo sull'argomento (`--cadenza daily`) cambierebbe il
#    jobname e spezzerebbe la storia del processo senza che niente fallisca.
def jobname_corsia(cadenza: str) -> str:
    return f"{PROCESSO_DIGEST_PRESIDI}:{cadenza.lower()}"


# ⭐ PIU' DI UN DESTINATARIO SI SCRIVE COME SI SCRIVE OVUNQUE: separati da
#    virgola (o punto e virgola). Il primo e' il destinatario, gli altri vanno in
#    copia — `config.fn_accoda_email_sistema` ha il parametro apposta.
# ⛔ Senza questo, «a@x.it, b@y.it» finirebbe INTERO nel campo destinatario e
#    l'invio fallirebbe a valle, dentro la coda email: un guasto che si scopre
#    guardando `config.email_log`, cioe' tardi e per caso. Il modo naturale di
#    scrivere due indirizzi non deve produrre un difetto.
# ⚠️ Vive QUI e non nel command (dal 2026-09-11) perche' ha due lettori: il
#    command del digest e l'handler `notifica_digest_muto`, che avvisa la stessa
#    persona quando il digest tace. Stesso setting, stessa lettura.
_SEPARATORI_DESTINATARI = str.maketrans({";": ",", "\n": ","})


# Scopo: dal valore configurato (`PRESIDI_DIGEST_DESTINATARIO`) alla coppia
#        (destinatario, copie). `("", [])` se non c'e' nessun indirizzo.
def separa_destinatari(raw: str | None) -> tuple[str, list[str]]:
    indirizzi = [
        pezzo.strip()
        for pezzo in (raw or "").translate(_SEPARATORI_DESTINATARI).split(",")
        if pezzo.strip()
    ]
    if not indirizzi:
        return "", []
    return indirizzi[0], indirizzi[1:]


# Scopo: l'esito di `accoda_email_presidi`: la riga scritta e a chi.
@dataclass(frozen=True)
class EmailPresidiAccodata:
    email_log_id: int | None
    destinatario: str
    copie: tuple[str, ...]


# Scopo: Accoda UN'email di SISTEMA a chi aspetta i presidi
#        (`PRESIDI_DIGEST_DESTINATARIO`). `None` se non c'e' nessun
#        destinatario configurato: che cosa farne lo decide il chiamante — il
#        digest lo dichiara come esito (`NON_CONFIGURATO`), l'handler del
#        guardiano FALLISCE, perche' un avviso che nessuno riceve non e' un FATTO.
#
# ⭐ E' UNA SEDE SOLA per «scrivo alla persona dei presidi» (2026-09-11):
#    prima stava dentro il command del digest, e alla seconda occorrenza —
#    l'handler `notifica_digest_muto` — la stessa chiamata a `insert_log` con
#    gli stessi otto argomenti sarebbe stata ricopiata. Due copie del modo in cui
#    si parla alla stessa persona divergono alla prima modifica (un `cc` in
#    piu', un `contesto` in meno), e la seconda persona a non ricevere e' quella
#    che serve di piu'.
# ⛔ NON SI SCRIVE UNA CHIAMATA NUOVA a `config.fn_accoda_email_sistema`: la
#    porta di sistema e' gia' dentro `EmailRepository.insert_log`, che instrada
#    da se' sull'ambito.
# ⚠️ `ambito = SISTEMA` non e' una comodita': `config.email_log` ha la row
#    level security, e ne' il command ne' il drenatore in `run_as = SISTEMA`
#    hanno un'identita' — un INSERT diretto verrebbe rifiutato.
def accoda_email_presidi(
    *,
    oggetto: str,
    testo: str,
    corpo_html: str,
    contesto_json: dict[str, Any],
) -> EmailPresidiAccodata | None:
    destinatario, copie = separa_destinatari(settings.PRESIDI_DIGEST_DESTINATARIO)
    if not destinatario:
        return None
    email_log_id = EmailRepository().insert_log(
        email_account_id=None,
        email_template_id=None,
        destinatario=destinatario,
        # ⚠️ `None` e non `[]`: la colonna e' un `text[]` nullable, e una lista
        #    vuota direbbe «copie: nessuna» invece di «non si applica».
        destinatari_cc=copie or None,
        oggetto=oggetto,
        corpo_inviato_html=corpo_html,
        corpo_inviato_testo=testo,
        ambito=AMBITO_SISTEMA,
        # ⭐ Il contesto viaggia con la riga: chi legge il giornale delle email
        #    deve poter dire QUALE processo l'ha prodotta senza aprirla.
        contesto_json=contesto_json,
    )
    return EmailPresidiAccodata(
        email_log_id=email_log_id, destinatario=destinatario, copie=tuple(copie),
    )


# Quante righe di esempio entrano nel corpo del messaggio.
# ⚠️ E' un ESEMPIO, non l'elenco: il conteggio accanto dice quante sono davvero,
#    e senza quel numero «cinque righe» si leggerebbe come «sono cinque».
RIGHE_NEL_MESSAGGIO = 5


# Scopo: un presidio dopo la lettura — che cosa dice il catalogo di lui, quante
#        righe chiedono un intervento e (dove si possono mostrare) le prime.
@dataclass(frozen=True)
class VocePresidio:
    vista: str
    natura: str
    conteggio: int
    # ⭐ La `nota` del CATALOGO e non il `COMMENT` della vista, ed e' una scelta:
    #    la nota e' la frase che il team DB scrive PER ESSERE LETTA — «perche'
    #    quella natura, e su un debito che cosa lo chiuderebbe» — mentre il
    #    commento e' il contratto della vista, lungo il doppio e scritto per chi
    #    ci lavora dentro. In un messaggio di posta il secondo affoga il primo.
    #    Il pannello, che ha spazio, continua a rendere il commento.
    nota: str
    registro: str | None
    perimetro: str
    righe: list[dict[str, Any]] = field(default_factory=list)
    troncato: bool = False
    # ⭐ IL CONTEGGIO DICE N E L'ELENCO E' VUOTO, su una vista che il catalogo
    #    dichiara elencabile. Non e' un dettaglio: vuol dire che da qui quella
    #    vista non si legge — il numero arriva solo perche' passa dalla funzione
    #    `SECURITY DEFINER` — e che la riga di catalogo va corretta.
    # ⛔ Senza questo campo il digest stamperebbe «779» seguito da niente, e si
    #    leggerebbe come un difetto del digest invece che come un perimetro
    #    dichiarato male. Misurato il 2026-09-10 su due viste: vedi il §9.3 del
    #    brief.
    cieco: bool = False


# Scopo: un presidio che NON si e' potuto leggere. ⛔ Non e' un caso di
#        frontiera da inghiottire: e' il difetto che il digest deve riferire per
#        primo, perche' nessun altro se ne accorgerebbe.
@dataclass(frozen=True)
class PresidioNonLetto:
    vista: str
    errore: str


# Scopo: il battito — le ultime corse del digest stesso, corsia per corsia, e se
#        valgono ancora come segno di vita.
#
# ⭐ `corse` e' un dict `jobname -> {last_run_at, attivo, last_ok}`, cioe' cio'
#    che `MaintenanceRepository.job_liveness` risponde: `attivo` e' il confronto
#    con la tolleranza del contratto a catalogo, fatto in SQL col clock del
#    DATABASE. ⛔ Non si confrontano timestamp in Python: sarebbero due orologi,
#    e su una macchina con l'ora storta il battito direbbe «morto» su un digest
#    vivo — il falso allarme che fa smettere di guardare un presidio.
# ⚠️ `corse` VUOTO non e' «vecchio», e' PEGGIO: nessuna corsa registrata, cioe'
#    il digest non ha mai girato oppure non si registra.
@dataclass(frozen=True)
class Battito:
    corse: dict[str, dict[str, Any]]
    # ⚠️ `None` = il processo non ha un contratto a catalogo
    #    (`dbops.processi.tolleranza_minuti` NULL). Allora `attivo` non si puo'
    #    calcolare, e il messaggio dice le date senza giudicarle.
    tolleranza_minuti: int | None
    # ⭐ Le corsie che DOVREBBERO esserci, cioe' una per cadenza del digest.
    # ⛔ Senza, una corsia MAI GIRATA sparirebbe dal battito e si leggerebbe come
    #    «nessun problema»: `job_liveness` non elenca i jobname che il giornale
    #    non conosce — e' scritto nel suo contratto, ed e' la stessa confusione
    #    fra «zero» e «non ho visto» che il catalogo dei presidi combatte.
    # ⚠️ I nomi vengono da `jobname_corsia`, la stessa funzione con cui il
    #    comando si registra: e' una sede sola, non una derivazione che puo'
    #    sfilarsi.
    attese: tuple[str, ...] = ()

    # Scopo: le corsie che tacciono da piu' della tolleranza del contratto.
    # ⭐ E' UN LETTORE di `tolleranza_minuti` (l'altro e' il panorama a DB):
    #    senza qualcuno che la CONFRONTI, quella colonna del catalogo sarebbe
    #    dichiarata e mai usata — cioe' sembrerebbe un presidio senza esserlo,
    #    che e' il difetto contro cui nasce questo cantiere.
    # ⛔ Senza tolleranza dichiarata NESSUNA corsia e' ferma, e la garanzia sta
    #    QUI e non nella disciplina di chi legge: `job_liveness` pretende una
    #    soglia per rispondere, quindi in quel caso `attivo` e' calcolato su un
    #    numero che non vuol dire niente. Lasciarlo passare riempirebbe questo
    #    elenco di falsi allarmi.
    @property
    def corsie_ferme(self) -> list[str]:
        if self.tolleranza_minuti is None:
            return []
        return sorted(
            jobname for jobname, corsa in self.corse.items()
            if corsa.get("attivo") is False
        )

    # Scopo: le corsie dichiarate che sul giornale non compaiono affatto.
    # ⛔ «Mai girata» e' PEGGIO di «ferma»: una corsia ferma ha almeno un
    #    passato, questa no — o il timer non e' mai stato installato, o il
    #    comando non arriva a registrarsi. E senza questo elenco sarebbe
    #    invisibile, perche' cio' che non c'e' non compare.
    @property
    def corsie_mai_girate(self) -> list[str]:
        return sorted(set(self.attese) - set(self.corse))


@dataclass(frozen=True)
class Digest:
    cadenza: str
    quando: datetime
    allarmi: list[VocePresidio]
    registri: list[VocePresidio]
    lavorazioni: list[VocePresidio]
    non_letti: list[PresidioNonLetto]
    battito: Battito | None

    # Scopo: c'e' qualcosa che chiede un intervento adesso?
    @property
    def ha_da_dire(self) -> bool:
        return bool(self.allarmi or self.registri or self.non_letti)

    # Scopo: si spedisce? ⭐ La regola in una riga: si spedisce se c'e' qualcosa
    #        da dire, OPPURE se questa e' la cadenza del battito — dove il
    #        messaggio stesso e' il segno di vita.
    @property
    def da_inviare(self) -> bool:
        return self.ha_da_dire or self.cadenza == CADENZA_BATTITO

    # Scopo: il riepilogo che finisce nel `meta` del run e nel contesto della
    #        mail. Numeri, non righe.
    # ⛔ Non contiene l'esito dell'INVIO, ed e' una scelta: qui non si spedisce.
    #    Tenerci una chiave `inviato: None` che il chiamante sovrascrive
    #    significava spedire un contesto email che dice «non inviato» proprio
    #    mentre l'invio sta avvenendo — un campo che si contraddice da solo.
    def riepilogo(self) -> dict[str, Any]:
        return {
            "cadenza": self.cadenza,
            "allarmi": len(self.allarmi),
            "righe_in_allarme": sum(v.conteggio for v in self.allarmi),
            "registri": len(self.registri),
            "lavorazioni": len(self.lavorazioni),
            "non_letti": len(self.non_letti),
            # ⭐ Le corsie ferme entrano nel `meta` del run: e' cio' che dice a
            #    chi scorre il giornale che una delle due sveglie e' morta.
            "corsie_ferme": (self.battito.corsie_ferme if self.battito else []),
            "corsie_mai_girate": (
                self.battito.corsie_mai_girate if self.battito else []
            ),
        }


# Scopo: Calcola il digest di una cadenza: legge il catalogo, conta ogni
#        presidio e lo smista nei tre elenchi. NON spedisce e non registra
#        niente — cosi' `--secco` e l'invio guardano lo stesso oggetto.
#
# ⚠️ Il conteggio passa SEMPRE dal repository (`dbops.fn_conta_presidio`): qui
#    non si scrive nessun `count(*)`, o il filtro «diverso dallo stato atteso»
#    avrebbe una seconda sede e le tre viste in row level security tornerebbero
#    zero per cecita'.
# ⛔ Un errore su UN presidio non porta via gli altri: si registra fra i non
#    letti e il giro continua. Un digest che muore a meta' non riferisce niente
#    di cio' che veniva dopo, e nessuno saprebbe che manca.
def calcola_digest(
    cadenza: str,
    *,
    repo: PresidiRepository | None = None,
    maintenance: MaintenanceRepository | None = None,
    processi: ProcessiRepository | None = None,
    righe_nel_messaggio: int = RIGHE_NEL_MESSAGGIO,
) -> Digest:
    if cadenza not in CADENZE_DEL_DIGEST:
        raise ValueError(
            f"cadenza non ammessa per il digest: {cadenza!r} "
            f"(attese: {', '.join(CADENZE_DEL_DIGEST)})"
        )
    repo = repo or PresidiRepository()

    allarmi: list[VocePresidio] = []
    registri: list[VocePresidio] = []
    lavorazioni: list[VocePresidio] = []
    non_letti: list[PresidioNonLetto] = []

    for riga in repo.list_catalogo(cadenze=(cadenza,)):
        # ⛔ L'ISOLAMENTO COPRE TUTTA LA LETTURA DI QUEL PRESIDIO — conteggio E
        #    righe — e non il solo conteggio. Scritto con il `try` sul primo
        #    pezzo soltanto, il 2026-09-10 la lettura delle righe di
        #    `vw_riferimenti_morti_da_sanare` si e' portata via il giro intero:
        #    l'isolamento c'era, e passava accanto al punto che falliva.
        righe: list[dict[str, Any]] = []
        try:
            conteggio = repo.conta(riga)
            # ⭐ LE RIGHE DI ESEMPIO SI CHIEDONO SOLO ALLE VISTE `ZERO`, e non e'
            #    una scorciatoia. Su una ZERO qualunque riga e' un guasto di
            #    ADESSO: l'esempio e' azionabile, e le righe sono poche per
            #    definizione. Su un REGISTRO la notizia e' il NUMERO — «ce n'e'
            #    una che nessuno aveva dichiarato» — e il lavoro sta nel
            #    registro, che il messaggio nomina gia'.
            # ⚠️ E una seconda lettura costa una seconda SCANSIONE: su
            #    `vw_riferimenti_morti_da_sanare` — l'unica REGISTRO — ogni
            #    SELECT ricompila circa cinquecento funzioni, ed e' il motivo per
            #    cui il catalogo le da' cadenza SETTIMANALE. Pagarlo due volte
            #    per cinque righe di esempio sarebbe ignorare cio' che la riga di
            #    catalogo dice di se'.
            if conteggio and riga["natura"] == NATURA_ZERO:
                righe = repo.prime_righe(riga, limite=righe_nel_messaggio)
        except Exception as exc:  # noqa: BLE001 — isolamento per presidio voluto
            logger.warning(
                "presidi_digest.presidio_non_letto vista=%s errore=%s",
                riga["vista"], exc, exc_info=True,
            )
            non_letti.append(PresidioNonLetto(vista=riga["vista"], errore=str(exc)))
            # ⛔ E SI CHIUDE LA CONNESSIONE, che e' la parte che non si vede.
            #    Un presidio puo' non limitarsi a fallire: puo' portarsi via la
            #    connessione (osservato due volte il 2026-09-10 leggendo
            #    `vw_riferimenti_morti_da_sanare`, che ricompila circa
            #    cinquecento funzioni a ogni lettura, con «SSL error: unexpected
            #    eof»). Da li' in poi OGNI query successiva fallisce, e
            #    l'isolamento per presidio diventa «tutto quello che veniva dopo
            #    non e' stato guardato» — senza che il messaggio lo dica.
            # ⚠️ `close_if_unusable_or_obsolete` e non `close()`: e' l'API che
            #    Django ha per questo, e chiude SOLO se la connessione e' andata
            #    in errore. Chiuderla comunque sarebbe corretto qui (nessuna
            #    transazione aperta) e sbagliato altrove, e questa funzione la
            #    chiama anche il pannello dentro una richiesta web.
            connection.close_if_unusable_or_obsolete()
            continue

        voce = VocePresidio(
            vista=riga["vista"],
            natura=riga["natura"],
            conteggio=conteggio,
            # ⚠️ Si dichiara cieco solo dove le righe si sono CHIESTE davvero
            #    (natura ZERO): altrove l'elenco e' vuoto perche' non e' stato
            #    domandato, e chiamarlo cecita' sarebbe un allarme inventato.
            cieco=bool(
                conteggio
                and riga["natura"] == NATURA_ZERO
                and riga["perimetro"] == PERIMETRO_LIBERO
                and not righe
            ),
            nota=riga["nota"],
            registro=riga["registro"],
            perimetro=riga["perimetro"],
            righe=righe,
            # ⚠️ «Troncato» vuol dire «ce ne sono altre OLTRE a quelle che
            #    vedi», quindi presuppone che le righe siano state CHIESTE. Su
            #    un REGISTRO — dove non si chiedono — un `conteggio > 0` lo
            #    renderebbe vero con l'elenco vuoto, cioe' direbbe «e altre 779»
            #    sotto un elenco che non c'e'.
            troncato=bool(righe) and conteggio > len(righe),
        )

        # ⚠️ Lo smistamento e' l'unico punto in cui il digest NOMINA le nature, e
        #    lo fa per decidere COME si legge un numero, non se guardarlo:
        #    su ZERO qualunque riga e' un guasto di adesso, su REGISTRO e' una
        #    voce che nessuno aveva dichiarato, su LAVORAZIONE e' una tendenza.
        # ⛔ Una natura NUOVA non cade in nessun elenco, e il presidio che se ne
        #    accorge e' `test_presidi_catalogo.test_i_mirror_delle_nature_seguono_il_check`:
        #    farla cadere in silenzio negli allarmi sarebbe peggio, perche'
        #    nessuno saprebbe come leggerla.
        if riga["natura"] == NATURA_ZERO:
            if conteggio:
                allarmi.append(voce)
        elif riga["natura"] == NATURA_REGISTRO:
            if conteggio:
                registri.append(voce)
        elif riga["natura"] == NATURA_LAVORAZIONE:
            # ⭐ La lavorazione entra SEMPRE, anche a zero: e' una tendenza, e
            #    una coda che si e' svuotata e' un'informazione quanto una che
            #    cresce. ⚠️ Ma non fa scattare un invio da sola.
            lavorazioni.append(voce)

    return Digest(
        cadenza=cadenza,
        quando=datetime.now(UTC),
        allarmi=allarmi,
        registri=registri,
        lavorazioni=lavorazioni,
        non_letti=non_letti,
        battito=(
            _leggi_battito(
                maintenance or MaintenanceRepository(),
                processi or ProcessiRepository(),
            )
            if cadenza == CADENZA_BATTITO else None
        ),
    )


# Scopo: Le ultime corse del digest stesso, corsia per corsia, e se valgono
#        ancora come segno di vita.
#
# ⭐ E' il pezzo che rende visibile la morte del digest, e la chiave e' il
#    PROCESSO (`processo_codice`, FK dura verso `dbops.processi`), non il nome
#    del job: un processo con due corsie si registra come `<codice>:<corsia>`, e
#    comporre quei nomi qui sarebbe una SECONDA sede della loro forma — il
#    giorno in cui cambia, il battito guarderebbe nomi che non esistono e
#    risponderebbe «mai girato» invece di «non lo so».
# ⚠️ La tolleranza e' quella del PROCESSO — il contratto a catalogo,
#    `dbops.processi.tolleranza_minuti` via `ProcessiRepository` (dal
#    2026-09-11; prima era la piu' larga fra le corsie di `sveglie.json`, e il
#    numero e' lo stesso: 11520). Il confronto lo si fa PER CORSIA, perche' e'
#    li' che si vede la morte di una sola delle due — ma contro l'unico numero
#    del processo: la giornaliera e' «ferma» dopo otto giorni, non dopo 26 ore.
#    E' il limite «grana processo vs grana corsia» accettato da Tid (brief
#    `brief-db-quattro-processi-senza-presidio.md` §11.2); «mai girata» invece
#    non ha bisogno di una tolleranza, e resta per corsia.
# ⛔ Senza contratto a catalogo NON si inventa un ripiego: le corse si mostrano
#    con le loro date e nessuna viene giudicata «ferma». Un numero preso a caso
#    darebbe un falso allarme, che e' il modo piu' rapido di far smettere di
#    guardare un presidio.
# ⛔ E se il giornale non risponde non si affonda il digest: il battito diventa
#    `None` e il messaggio lo dice.
def _leggi_battito(
    maintenance: MaintenanceRepository, processi: ProcessiRepository,
) -> Battito | None:
    tolleranza = processi.tolleranza_minuti(PROCESSO_DIGEST_PRESIDI)
    try:
        corse = maintenance.job_liveness(
            processo_codice=PROCESSO_DIGEST_PRESIDI,
            # ⚠️ `job_liveness` pretende una soglia per calcolare `attivo`.
            #    Senza dichiarato si passa un valore che non giudica nessuno:
            #    il messaggio ignora `attivo` quando la tolleranza e' `None`.
            soglia_minuti=tolleranza if tolleranza is not None else 0,
        )
    except Exception as exc:  # noqa: BLE001 — il battito non affonda il digest
        logger.warning("presidi_digest.battito_non_letto errore=%s", exc, exc_info=True)
        return None
    return Battito(
        corse=corse,
        tolleranza_minuti=tolleranza,
        attese=tuple(jobname_corsia(c) for c in CADENZE_DEL_DIGEST),
    )


# ══════════════════════════════════════════════════════════
#  Il messaggio
# ══════════════════════════════════════════════════════════

# Scopo: Compone oggetto, corpo testo e corpo HTML del digest.
#
# ⭐ L'OGGETTO PORTA IL NUMERO, e non e' cosmesi: e' l'unica parte che si legge
#    senza aprire, ed e' quella che decide se il messaggio viene aperto.
# ⚠️ Nel corpo entrano le righe dei soli presidi a perimetro LIBERO — il guard
#    e' nel repository — e sono dati tecnici (nomi di job, di viste, di ruoli).
#    Le viste che attraversano una tabella con la row level security consegnano
#    il NUMERO e non le righe, e in un messaggio di posta non finisce niente
#    fuori perimetro.
def componi_messaggio(digest: Digest) -> tuple[str, str, str]:
    quando = digest.quando.astimezone().strftime("%d/%m/%Y %H:%M")
    cadenza = digest.cadenza.lower()
    if digest.non_letti:
        oggetto = (
            f"[ZeroERP] Presidi {cadenza}: {len(digest.non_letti)} non letti, "
            f"{len(digest.allarmi)} in allarme"
        )
    elif digest.allarmi:
        righe = sum(v.conteggio for v in digest.allarmi)
        oggetto = (
            f"[ZeroERP] Presidi {cadenza}: {len(digest.allarmi)} in allarme "
            f"({righe} righe)"
        )
    elif digest.registri:
        oggetto = (
            f"[ZeroERP] Presidi {cadenza}: {len(digest.registri)} voci non dichiarate"
        )
    else:
        oggetto = f"[ZeroERP] Presidi {cadenza}: nessun allarme"

    return oggetto, _corpo_testo(digest, quando), _corpo_html(digest, quando)


# Scopo: Il corpo in testo semplice — quello che si legge davvero.
def _corpo_testo(digest: Digest, quando: str) -> str:
    r: list[str] = [
        f"DIGEST DEI PRESIDI — cadenza {digest.cadenza} — {quando}",
        "",
    ]
    if digest.battito is not None:
        r.extend(_battito_testo(digest.battito))
        r.append("")

    if digest.non_letti:
        r.append(f"NON LETTI ({len(digest.non_letti)}) — un presidio cieco non presidia")
        for nl in digest.non_letti:
            r.append(f"  · {nl.vista}: {nl.errore}")
        r.append("")

    if digest.allarmi:
        r.append(f"ALLARMI ({len(digest.allarmi)}) — queste viste devono restare vuote")
        for v in digest.allarmi:
            r.extend(_voce_testo(v))
        r.append("")

    if digest.registri:
        r.append(
            f"REGISTRI ({len(digest.registri)}) — voci che nessuno ha dichiarato"
        )
        for v in digest.registri:
            r.extend(_voce_testo(v))
        r.append("")

    if digest.lavorazioni:
        r.append("IN LAVORAZIONE (tendenza)")
        for v in digest.lavorazioni:
            r.append(f"  · {v.vista}: {v.conteggio}")
        r.append("")

    if not digest.ha_da_dire:
        r.append("Nessun presidio chiede un intervento a questa cadenza.")
        r.append("")

    r.append(
        "Che cosa significa una riga lo dice il catalogo dbops.presidi; "
        "la natura la scrive chi ha scritto la vista."
    )
    return "\n".join(r)


# Scopo: le righe di un presidio in allarme — il numero, il motivo, un esempio.
def _voce_testo(v: VocePresidio) -> list[str]:
    r = [f"  · {v.vista}: {v.conteggio}"]
    if v.registro:
        r.append(f"      registro delle voci note: {v.registro}")
    if v.nota:
        r.append(f"      {v.nota}")
    for riga in v.righe:
        r.append("      - " + _riga_compatta(riga))
    if v.troncato:
        r.append(f"      … e altre {v.conteggio - len(v.righe)}")
    elif v.cieco:
        # ⛔ Il numero c'e' e l'elenco no, su una vista che il catalogo dichiara
        #    elencabile: e' il perimetro a essere dichiarato male, e va detto —
        #    non lasciato leggere come un difetto del digest.
        r.append(
            "      ⚠️ il conteggio dice " + str(v.conteggio) + " ma da qui la "
            "vista risponde VUOTA: il perimetro dichiarato (LIBERO) non regge, "
            "la riga di catalogo va corretta."
        )
    elif v.perimetro == PERIMETRO_DEFINER:
        # ⭐ Perimetro DEFINER: il numero c'e', le righe no. Dirlo evita che
        #    l'assenza si legga come un difetto del digest.
        # ⚠️ Su un REGISTRO invece non si dice niente, ed e' giusto: li' le righe
        #    non mancano — non sono state chieste, e la notizia e' il numero.
        r.append("      (righe non elencabili da qui: la vista ha un perimetro)")
    return r


# Scopo: una riga di una vista, compatta e leggibile — `chiave=valore`.
def _riga_compatta(riga: dict[str, Any]) -> str:
    return ", ".join(
        f"{k}={'—' if v is None else v}" for k, v in riga.items()
    )


# Scopo: il battito in testo: quando ho girato, corsia per corsia.
def _battito_testo(b: Battito) -> list[str]:
    if not b.corse:
        return [
            "ULTIME CORSE: nessuna corsa registrata sul giornale.",
            "  ⛔ E' il caso peggiore: il digest non ha mai girato, oppure non "
            "si registra. Guardare l'unit systemd.",
        ]
    r = ["ULTIME CORSE DEL DIGEST:"]
    ferme = set(b.corsie_ferme)
    for jobname, corsa in sorted(b.corse.items()):
        esito = "ok" if corsa.get("last_ok") else "FALLITA"
        # ⭐ Il giudizio sta accanto alla data, non in fondo: chi legge un elenco
        #    di date non sa da solo quale sia «troppo vecchia».
        ferma = "  ⛔ FERMA da piu' della tolleranza" if jobname in ferme else ""
        r.append(
            f"  · {jobname}: {corsa.get('last_run_at') or '—'} ({esito}){ferma}"
        )
    for jobname in b.corsie_mai_girate:
        r.append(f"  · {jobname}: ⛔ MAI GIRATA — nessuna corsa sul giornale")
    if b.tolleranza_minuti is None:
        # ⚠️ Si dichiara, invece di lasciar credere che le date siano state
        #    guardate: il processo non ha un contratto a catalogo, quindi qui
        #    nessuno puo' dire se una corsia sia ferma.
        r.append(
            "  ⚠️ nessuna tolleranza dichiarata a catalogo: le date non sono "
            "state giudicate"
        )
    else:
        r.append(f"  tolleranza dichiarata a catalogo: {b.tolleranza_minuti} minuti")
    return r


# Scopo: Il corpo HTML — stessa sostanza del testo, con i valori ESCAPATI.
# ⚠️ I valori vengono dalle righe delle viste (nomi di job, di ruoli, messaggi
#    d'errore): finiscono in un documento HTML e si escapano, sempre.
def _corpo_html(digest: Digest, quando: str) -> str:
    def e(v: Any) -> str:
        return html.escape("—" if v is None else str(v))

    p: list[str] = [
        "<div style=\"font-family:system-ui,sans-serif;font-size:14px\">",
        f"<h2 style=\"margin:0 0 .2rem\">Digest dei presidi — {e(digest.cadenza)}</h2>",
        f"<p style=\"margin:0 0 1rem;color:#666\">{e(quando)}</p>",
    ]

    if digest.battito is not None:
        p.append("<h3>Ultime corse del digest</h3>")
        if not digest.battito.corse:
            p.append(
                "<p><strong>Nessuna corsa registrata sul giornale.</strong> "
                "Il digest non ha mai girato, oppure non si registra.</p>"
            )
        else:
            ferme = set(digest.battito.corsie_ferme)
            p.append("<ul>")
            for jobname, corsa in sorted(digest.battito.corse.items()):
                esito = "ok" if corsa.get("last_ok") else "<strong>FALLITA</strong>"
                ferma = (
                    " — <strong>⛔ FERMA da più della tolleranza</strong>"
                    if jobname in ferme else ""
                )
                p.append(
                    f"<li><code>{e(jobname)}</code>: "
                    f"{e(corsa.get('last_run_at'))} ({esito}){ferma}</li>"
                )
            for jobname in digest.battito.corsie_mai_girate:
                p.append(
                    f"<li><code>{e(jobname)}</code>: <strong>⛔ MAI GIRATA</strong> "
                    f"— nessuna corsa sul giornale</li>"
                )
            p.append("</ul>")
            if digest.battito.tolleranza_minuti is None:
                p.append(
                    "<p style=\"color:#666\">Nessuna tolleranza dichiarata a "
                    "catalogo: le date non sono state giudicate.</p>"
                )
            else:
                p.append(
                    f"<p style=\"color:#666\">Tolleranza dichiarata a catalogo: "
                    f"{e(digest.battito.tolleranza_minuti)} minuti.</p>"
                )

    if digest.non_letti:
        p.append(f"<h3>Non letti ({len(digest.non_letti)})</h3>")
        p.append("<p>Un presidio cieco non presidia: questi non si sono potuti contare.</p><ul>")
        for nl in digest.non_letti:
            p.append(f"<li><code>{e(nl.vista)}</code>: {e(nl.errore)}</li>")
        p.append("</ul>")

    for titolo, sottotitolo, voci in (
        ("Allarmi", "Queste viste devono restare vuote.", digest.allarmi),
        ("Registri", "Voci che nessuno ha ancora dichiarato.", digest.registri),
    ):
        if not voci:
            continue
        p.append(f"<h3>{titolo} ({len(voci)})</h3><p>{sottotitolo}</p><ul>")
        for v in voci:
            p.append(
                f"<li><code>{e(v.vista)}</code>: <strong>{e(v.conteggio)}</strong>"
            )
            if v.registro:
                p.append(f"<br><span style=\"color:#666\">registro: <code>{e(v.registro)}</code></span>")
            if v.nota:
                p.append(f"<br><span style=\"color:#666\">{e(v.nota)}</span>")
            if v.righe:
                p.append("<ul>")
                for riga in v.righe:
                    p.append(f"<li>{e(_riga_compatta(riga))}</li>")
                if v.troncato:
                    p.append(f"<li>… e altre {e(v.conteggio - len(v.righe))}</li>")
                p.append("</ul>")
            elif v.cieco:
                p.append(
                    f"<br><strong>⚠️ il conteggio dice {e(v.conteggio)} ma da qui "
                    f"la vista risponde vuota</strong>: il perimetro dichiarato "
                    f"(LIBERO) non regge, la riga di catalogo va corretta."
                )
            elif v.perimetro == PERIMETRO_DEFINER:
                p.append(
                    "<br><span style=\"color:#666\">righe non elencabili da qui: "
                    "la vista ha un perimetro</span>"
                )
            p.append("</li>")
        p.append("</ul>")

    if digest.lavorazioni:
        p.append("<h3>In lavorazione (tendenza)</h3><ul>")
        for v in digest.lavorazioni:
            p.append(f"<li><code>{e(v.vista)}</code>: {e(v.conteggio)}</li>")
        p.append("</ul>")

    if not digest.ha_da_dire:
        p.append("<p>Nessun presidio chiede un intervento a questa cadenza.</p>")

    p.append(
        "<p style=\"color:#666;font-size:12px\">Che cosa significa una riga lo "
        "dice il catalogo <code>dbops.presidi</code>; la natura la scrive chi ha "
        "scritto la vista.</p></div>"
    )
    return "".join(p)
