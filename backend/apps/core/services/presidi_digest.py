# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#        Brief: work-done/brief-db-un-destinatario-per-i-presidi.md §5, §8.2.
# ------------------------------------------------------------

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field, replace
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
    CHI_AGISCE,
    CHI_AGISCE_AMMINISTRATORE,
    CHI_AGISCE_SISTEMISTA,
    CHI_AGISCE_SVILUPPO,
    NATURA_LAVORAZIONE,
    NATURA_REGISTRO,
    NATURA_ZERO,
    PERIMETRO_DEFINER,
    PERIMETRO_LIBERO,
    CausaPresidio,
    PresidiRepository,
)
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.email_constants import AMBITO_SISTEMA
from apps.core.services.locale_formatters import format_datetime
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
    # ⭐ IL TESTO PER CHI AGISCE (`dbops.presidi_testi`, 2026-10-06): cosa vuol
    #    dire una riga e cosa fare. Nel messaggio viene PRIMA della `nota`, che
    #    resta come dettaglio tecnico: la nota e' scritta per chi mantiene il
    #    presidio, e chi apre la mail ha due domande sole — cosa vuol dire, cosa
    #    faccio.
    # ⚠️ `None` = presidio senza testo: il messaggio ripiega sulla sola nota,
    #    com'era prima, e non scrive una riga vuota.
    significato: str | None = None
    azione: str | None = None
    # ⭐ Decide il GRUPPO in cui la voce finisce (`_per_chi_agisce`).
    chi_agisce: str | None = None
    # ⭐ LE CAUSE ACCESE, ognuna col suo conteggio, il suo rimedio, il suo «chi
    #    agisce» e le sue righe di esempio (`PresidiRepository.cause_del_presidio`,
    #    dal 2026-10-10): vuoto dove il presidio ha un testo solo. Quando c'e', il
    #    testo del presidio e' quello neutro («segui il rimedio accanto alla
    #    causa») e il messaggio rende una voce PER CAUSA (`_voci_per_causa`).
    cause: list[CausaPresidio] = field(default_factory=list)
    # ⭐ Valorizzata solo sulla voce di UNA causa, derivata da `_voci_per_causa`:
    #    conteggio, testo, «chi agisce» e righe sono allora quelli della causa.
    #    ⚠️ Non e' `str | None`: la causa NULL («non indicata») e' una causa
    #    anche lei, e va distinta da «voce del presidio intero».
    causa_resa: CausaPresidio | None = None
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
# ⭐ `corse` e' un dict `jobname -> {last_run_at, attivo, in_corso,
#    ultima_conclusa}`, cioe' cio' che `MaintenanceRepository.job_liveness`
#    risponde: la riga PIU' RECENTE come segno di vita (`last_run_at`, `attivo`,
#    e `in_corso` se e' ancora aperta) e l'ultima corsa CONCLUSA a parte, con la
#    sua data e il suo esito insieme (`{started_at, ended_at, ok}`, `None` se
#    non ne esiste una). `attivo` e' il confronto con la tolleranza del
#    contratto a catalogo, fatto in SQL col clock del DATABASE. ⛔ Non si
#    confrontano timestamp in Python: sarebbero due orologi, e su una macchina
#    con l'ora storta il battito direbbe «morto» su un digest vivo — il falso
#    allarme che fa smettere di guardare un presidio.
# ⛔ Per la corsia che sta componendo la mail la riga piu' recente e' SEMPRE
#    aperta, e l'esito e' sempre quello di un'altra corsa. Fino al 2026-09-14 i
#    due arrivavano in due campi piatti (`last_run_at`, `last_ok`) e la mail li
#    scriveva come uno: «09:47:32 (ok)», dove l'ora era della corsa in
#    esecuzione e l'ok di quella delle 07:30 (nota del team DB). Sul modello,
#    con la precedente fallita, lunedi' si sarebbe letto «<adesso> (FALLITA)»
#    con la mail in mano. Ora la riga dice «in corso» e la precedente sta a
#    parte, con la sua data.
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
        cause: list[CausaPresidio] = []
        try:
            # ⭐ Una lettura sola: il totale e, se il presidio ha cause, i loro
            #    conteggi (`PresidiRepository.conta_presidio`).
            conteggio, conteggi = repo.conta_presidio(riga)
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
                # ⭐ Le cause partono dai conteggi: arrivano anche quelle oltre
                #    il campione, e su una vista che non si elenca.
                cause = repo.cause_del_presidio(riga, righe, conteggi)
        except Exception as exc:  # isolamento per presidio voluto
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
            significato=riga["significato"],
            azione=riga["azione"],
            chi_agisce=riga["chi_agisce"],
            registro=riga["registro"],
            perimetro=riga["perimetro"],
            righe=righe,
            cause=cause,
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
    except Exception as exc:  # il battito non affonda il digest
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

# Scopo: il titolo di ogni gruppo di presidi accesi, per CHI LO SPEGNE.
# ⭐ Sono le stesse tre risposte dei badge del pannello
#    (`amministrazione.processi.chi_agisce.*`), dette per una mail: il digest va
#    per posta e non ha i locali del frontend — ed e' il motivo per cui il testo
#    dei presidi sta a DB e non in i18n (brief D-1).
# ⛔ Una chiave per ogni valore del mirror `CHI_AGISCE`: lo presidia
#    `test_ogni_chi_agisce_ha_il_suo_titolo`, perche' un valore nuovo senza
#    titolo finirebbe nel gruppo «senza indicazione» senza che niente fallisca.
TITOLI_CHI_AGISCE: dict[str, str] = {
    CHI_AGISCE_AMMINISTRATORE: "Puoi sistemarlo tu, dall'applicazione",
    CHI_AGISCE_SISTEMISTA: "Da segnalare a chi gestisce il server",
    CHI_AGISCE_SVILUPPO: "Da segnalare allo sviluppo",
}
TITOLO_CHI_AGISCE_ASSENTE = "Senza indicazione di chi agisce"


# Scopo: le voci di un elenco, raggruppate per chi le spegne, nell'ordine del
#        mirror `CHI_AGISCE` — prima cio' che si sistema dall'applicazione, poi
#        cio' che va inoltrato — e in fondo quelle senza indicazione.
# ⭐ Una sede sola per le due rese: testo e HTML ricevono gli stessi gruppi
#    nello stesso ordine, e non possono raccontare la stessa mail in due modi.
# ⚠️ Un gruppo vuoto non si restituisce: un titolo senza voci sotto si legge
#    come «qui c'era qualcosa e si e' perso».
def _per_chi_agisce(
    voci: list[VocePresidio],
) -> list[tuple[str, list[VocePresidio]]]:
    # ⭐ Prima si aprono le voci per causa: e' la causa a dire a chi tocca
    #    (§5.4.4 del brief-db-presidio-processi-testo-per-causa), e un presidio
    #    con una causa dello sviluppo e una del sistemista finisce, per le sue
    #    due parti, in due gruppi.
    voci = [voce for v in voci for voce in _voci_per_causa(v)]
    gruppi: list[tuple[str, list[VocePresidio]]] = [
        (TITOLI_CHI_AGISCE[chi], dentro)
        for chi in CHI_AGISCE
        if (dentro := [v for v in voci if v.chi_agisce == chi])
    ]
    # ⛔ «Fuori vocabolario» e «assente» finiscono INSIEME in fondo, e non si
    #    perdono: una voce che non trova il suo gruppo e' ancora un allarme.
    resto = [v for v in voci if v.chi_agisce not in CHI_AGISCE]
    if resto:
        gruppi.append((TITOLO_CHI_AGISCE_ASSENTE, resto))
    return gruppi


# Scopo: una voce di presidio, aperta in una voce PER CAUSA quando il presidio
#        ne ha (`VocePresidio.cause`); altrimenti la voce com'e'.
# ⭐ La voce di una causa ha il conteggio, il testo, il «chi agisce» e le righe
#    della causa; nota, registro, perimetro e cecita' restano quelli del
#    presidio, che e' la stessa vista.
# ⚠️ Gli elenchi del Digest (`allarmi`, `registri`) restano PER PRESIDIO, e cosi'
#    oggetto e riepilogo: si apre solo la RESA. Contare le cause come presidi
#    direbbe «3 in allarme» con due viste accese.
# ⚠️ «Troncato» vale solo se le righe sono state chieste: la voce del presidio
#    ne ha (`v.righe`) e la causa ne conta piu' di quante ne mostra. Una causa
#    con zero righe nel campione e' troncata anche lei, e lo dice
#    `_riga_troncamento`.
def _voci_per_causa(v: VocePresidio) -> list[VocePresidio]:
    if not v.cause:
        return [v]
    return [
        replace(
            v,
            conteggio=c["conteggio"],
            significato=c["significato"],
            azione=c["azione"],
            chi_agisce=c["chi_agisce"],
            righe=c["righe"],
            cause=[],
            causa_resa=c,
            troncato=bool(v.righe) and c["conteggio"] > len(c["righe"]),
        )
        for c in v.cause
    ]


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
    quando = _ora_locale(digest.quando, secondi=False)
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
        r.extend(_gruppi_testo(digest.allarmi))
        r.append("")

    if digest.registri:
        r.append(
            f"REGISTRI ({len(digest.registri)}) — voci che nessuno ha dichiarato"
        )
        r.extend(_gruppi_testo(digest.registri))
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


# Scopo: un elenco di voci, a gruppi per chi le spegne (`_per_chi_agisce`).
def _gruppi_testo(voci: list[VocePresidio]) -> list[str]:
    r: list[str] = []
    for titolo, dentro in _per_chi_agisce(voci):
        r.append(f"  ▸ {titolo}")
        for v in dentro:
            r.extend(_voce_testo(v))
    return r


# Scopo: le righe di un presidio in allarme — il numero, cosa vuol dire, cosa
#        fare, il motivo tecnico, un esempio.
# ⭐ Prima il testo per chi agisce, poi quello per chi mantiene il presidio.
#    ⚠️ Senza testo resta la sola nota, com'era prima del 2026-10-06.
def _voce_testo(v: VocePresidio) -> list[str]:
    r = [f"  · {_nome_voce(v)}: {v.conteggio}"]
    if (avviso := _avviso_causa(v)):
        r.append(f"      ⚠️ {avviso}")
    if v.significato:
        r.append(f"      {v.significato}")
    if v.azione:
        r.append(f"      → {v.azione}")
    if v.registro:
        r.append(f"      registro delle voci note: {v.registro}")
    if v.nota:
        r.append(f"      {_prefisso_nota(v)}{v.nota}")
    for riga in v.righe:
        r.append("      - " + _riga_compatta(riga))
    if v.troncato:
        r.append(f"      {_riga_troncamento(v)}")
    elif v.cieco:
        # ⛔ Il numero c'e' e l'elenco no, su una vista che il catalogo dichiara
        #    elencabile. Le cause sono DUE, e il messaggio le nomina entrambe:
        #    fino al 2026-09-14 diceva solo «la riga di catalogo va corretta»,
        #    e il 14-09 la riga era giusta — era la vista a rispondere diverso
        #    per ruolo (`pg_stat_activity` maschera `backend_start` alle
        #    sessioni altrui; sanato lato DB con `20260914-01`).
        r.append(
            "      ⚠️ il conteggio dice " + str(v.conteggio) + " ma da qui la "
            "vista risponde VUOTA: o il perimetro e' dichiarato male (LIBERO), "
            "o la vista risponde diverso a seconda di chi legge. Confrontare "
            "la lettura come definer e come app prima di correggere la riga "
            "di catalogo."
        )
    elif v.perimetro == PERIMETRO_DEFINER:
        # ⭐ Perimetro DEFINER: il numero c'e', le righe no. Dirlo evita che
        #    l'assenza si legga come un difetto del digest.
        # ⚠️ Su un REGISTRO invece non si dice niente, ed e' giusto: li' le righe
        #    non mancano — non sono state chieste, e la notizia e' il numero.
        r.append("      (righe non elencabili da qui: la vista ha un perimetro)")
    return r


# Scopo: il nome di una voce: la vista, e per la voce di una causa la causa.
def _nome_voce(v: VocePresidio) -> str:
    if v.causa_resa is None:
        return v.vista
    causa = v.causa_resa["causa"]
    return f"{v.vista} — {causa if causa is not None else 'causa non indicata'}"


# Scopo: cosa manca alla voce di una causa per essere azionabile, o None.
# ⛔ Causa senza testo, o che il catalogo delle cause non conosce: si dice, e non
#    si prende in prestito il rimedio del presidio, che sarebbe quello di un
#    altro guasto (§5.4.2 del brief-db-presidio-processi-testo-per-causa).
# ⚠️ `chi_agisce` e' NOT NULL in `dbops.presidi_cause`: None vuol dire che la
#    causa non e' a catalogo (o la riga non la dice), e la voce finisce fra
#    quelle senza indicazione di chi agisce.
def _avviso_causa(v: VocePresidio) -> str | None:
    if v.causa_resa is None:
        return None
    if v.causa_resa["causa"] is None:
        return "la riga non dice la sua causa: nessun testo e nessuna indicazione di chi agisce"
    if v.chi_agisce is None:
        return "causa non a catalogo: nessun testo e nessuna indicazione di chi agisce"
    if not (v.significato or v.azione):
        return "nessun testo per questa causa nel catalogo"
    return None


# Scopo: la riga che dice che le righe mostrate non sono tutte. Una sede per le
#        due rese.
# ⚠️ La voce di una causa puo' non avere nessuna riga nel campione (la causa sta
#    oltre le prime righe lette): «e altre N» sotto un elenco vuoto si leggerebbe
#    male, e si dice com'e'.
def _riga_troncamento(v: VocePresidio) -> str:
    if not v.righe:
        return f"… nessuna fra le righe di esempio ({v.conteggio} in tutto)"
    return f"… e altre {v.conteggio - len(v.righe)}"


# Scopo: l'etichetta della nota quando sopra c'e' il testo per chi agisce: la
#        nota diventa il DETTAGLIO TECNICO, e va detto, o due frasi di fila si
#        leggerebbero come una spiegazione sola.
def _prefisso_nota(v: VocePresidio) -> str:
    return "dettaglio tecnico: " if (v.significato or v.azione) else ""


# Scopo: una riga di una vista, compatta e leggibile — `chiave=valore`.
# ⚠️ Un istante si scrive nell'ora dell'azienda e nel formato del BB, come il
#    resto del messaggio: fino al 2026-10-09 era `str()` del valore, cioe' UTC
#    con `+00:00` (brief un-solo-fuso-aziendale B-6).
def _riga_compatta(riga: dict[str, Any]) -> str:
    return ", ".join(f"{k}={_valore_compatto(v)}" for k, v in riga.items())


# Scopo: un valore di una riga di vista nel messaggio: `None` -> «—», un
#        istante -> ora dell'azienda coi secondi, il resto com'e'.
def _valore_compatto(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return format_datetime(v, with_seconds=True)
    return str(v)


# Scopo: un istante del messaggio, nel formato e nel fuso del BB
#        `locale_formatters` (ora dell'azienda, non quella dell'host ne' del
#        processo) — con i secondi per le
#        corse, dove due corse dello stesso minuto vanno distinte, senza per la
#        testata. `None` si scrive «—», non stringa vuota: in una riga di
#        elenco il vuoto si legge come un difetto di resa.
# ⛔ Fino al 2026-09-14 la testata era in ora locale e le corse in UTC: il
#    giornale risponde nel fuso della connessione (`USE_TZ`, cioe' UTC) e
#    `isoformat()` lo consegna con `+00:00`, che a video si legge come un'ora
#    sbagliata di uno o due — «cosmesi» nella nota del team DB, ma della stessa
#    famiglia: una data senza il suo contesto. La conversione ora sta nel BB,
#    per decisione di Tid dello stesso giorno: vale per gli export e per i
#    documenti, non solo per questa mail.
def _ora_locale(quando: datetime | str | None, *, secondi: bool) -> str:
    if quando is None:
        return "—"
    return format_datetime(quando, with_seconds=secondi)


# Scopo: la parola per l'esito di una corsa CONCLUSA. Tre facce anche qui:
#        `True` ok, `False` FALLITA, `None` = la corsa e' chiusa ma nessuno ha
#        scritto l'esito (`job_run_log.ok` e' nullable e nessun CHECK lo lega a
#        `ended_at`: e' un caso che il modello ammette, e si dice).
# ⚠️ Le parole sono costanti perche' la resa HTML ne riconosce una per
#    marcarla: un confronto con un letterale ricopiato sarebbe la seconda sede.
ESITO_OK = "ok"
ESITO_FALLITA = "FALLITA"
ESITO_NON_SCRITTO = "esito non scritto"
# ⭐ E la corsa APERTA non ha un esito: ha una parola sua, che dice cosa sta
#    succedendo invece di prendere in prestito l'esito di un'altra corsa.
IN_CORSO = "in corso"


def _esito_conclusa(conclusa: dict[str, Any]) -> str:
    ok = conclusa.get("ok")
    if ok is None:
        return ESITO_NON_SCRITTO
    return ESITO_OK if ok else ESITO_FALLITA


# Scopo: la riga di una corsia, come SEQUENZA di pezzi (parola, marcata?): il
#        testo li concatena, l'HTML li escapa e mette in grassetto quelli
#        marcati. Una sola composizione per le due rese, cosi' non possono
#        raccontare la stessa corsia in due modi.
#
# ⭐ Due forme, e la differenza e' il punto:
#    - riga piu' recente APERTA → «in corso (avviata 14-09-2026 09:47:32) —
#      ultima conclusa 14-09-2026 07:30:49 (ok)», o «— nessuna corsa conclusa»;
#    - riga piu' recente CHIUSA → «14-09-2026 07:00:12 (ok)»: la data e'
#      quella dell'ultima conclusa, con l'esito suo. Di solito coincide con la
#      riga piu' recente; non quando questa e' una corsa SALTATA (lock
#      occupato, dal 2026-10-10 chiusa e senza esito): la skip e' segno di vita
#      e non lavoro, e la data che accompagna l'esito resta quella della corsa
#      vera (`_cte_corse` di MaintenanceRepository).
def _pezzi_corsa(corsa: dict[str, Any]) -> list[tuple[str, bool]]:
    conclusa = corsa.get("ultima_conclusa")
    if corsa.get("in_corso"):
        pezzi = [
            (f"{IN_CORSO} (avviata {_ora_locale(corsa.get('last_run_at'), secondi=True)})", False),
        ]
        if conclusa:
            esito = _esito_conclusa(conclusa)
            pezzi.append((
                f" — ultima conclusa {_ora_locale(conclusa.get('started_at'), secondi=True)} (",
                False,
            ))
            pezzi.append((esito, esito == ESITO_FALLITA))
            pezzi.append((")", False))
        else:
            pezzi.append((" — nessuna corsa conclusa", False))
        return pezzi
    if conclusa:
        esito = _esito_conclusa(conclusa)
        return [
            (f"{_ora_locale(conclusa.get('started_at'), secondi=True)} (", False),
            (esito, esito == ESITO_FALLITA),
            (")", False),
        ]
    # ⚠️ Riga piu' recente chiusa e nessuna conclusa: dal repository succede
    #    quando la corsia ha solo corse SALTATE (una skip e' chiusa ma non e'
    #    una conclusa); da un dict costruito altrove pure. Si dice, invece di
    #    sollevare dentro il messaggio.
    return [
        (f"{_ora_locale(corsa.get('last_run_at'), secondi=True)} (nessuna corsa conclusa)", False),
    ]


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
        descrizione = "".join(parola for parola, _marcata in _pezzi_corsa(corsa))
        # ⭐ Il giudizio sta accanto alla data, non in fondo: chi legge un elenco
        #    di date non sa da solo quale sia «troppo vecchia».
        ferma = "  ⛔ FERMA da piu' della tolleranza" if jobname in ferme else ""
        r.append(f"  · {jobname}: {descrizione}{ferma}")
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
                descrizione = "".join(
                    f"<strong>{e(parola)}</strong>" if marcata else e(parola)
                    for parola, marcata in _pezzi_corsa(corsa)
                )
                ferma = (
                    " — <strong>⛔ FERMA da più della tolleranza</strong>"
                    if jobname in ferme else ""
                )
                p.append(f"<li><code>{e(jobname)}</code>: {descrizione}{ferma}</li>")
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
        p.append(f"<h3>{titolo} ({len(voci)})</h3><p>{sottotitolo}</p>")
        # ⭐ A gruppi per chi le spegne, come il testo (`_per_chi_agisce`).
        for chi, dentro in _per_chi_agisce(voci):
            p.append(f"<h4 style=\"margin:.6rem 0 .2rem\">{e(chi)}</h4><ul>")
            for v in dentro:
                p.append(
                    f"<li><code>{e(_nome_voce(v))}</code>: <strong>{e(v.conteggio)}</strong>"
                )
                if (avviso := _avviso_causa(v)):
                    p.append(f"<br><strong>⚠️ {e(avviso)}</strong>")
                if v.significato:
                    p.append(f"<br>{e(v.significato)}")
                if v.azione:
                    p.append(f"<br><strong>→ {e(v.azione)}</strong>")
                if v.registro:
                    p.append(f"<br><span style=\"color:#666\">registro: <code>{e(v.registro)}</code></span>")
                if v.nota:
                    p.append(
                        f"<br><span style=\"color:#666\">{e(_prefisso_nota(v))}{e(v.nota)}</span>"
                    )
                # ⭐ UN elenco solo, come la resa testo (`_voce_testo`): le righe,
                #    poi la riga di troncamento dalla sua sede.
                if v.righe or v.troncato:
                    p.append("<ul>")
                    for riga in v.righe:
                        p.append(f"<li>{e(_riga_compatta(riga))}</li>")
                    if v.troncato:
                        p.append(f"<li>{e(_riga_troncamento(v))}</li>")
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
