# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `NOTIFICA_DIGEST_MUTO`: avvisa una persona che il
#        DIGEST DEI PRESIDI ha smesso di girare.
#
#        ⭐ E' LA GUARDIA RECIPROCA (brief `brief-db-quattro-processi-senza-presidio.md`
#        §10.2, Q2 decisa da Tid il 2026-09-11). Il digest guarda tutti gli
#        altri processi; se muore LUI, l'unica cosa che lo direbbe e' il battito
#        — che sta dentro di lui. Un digest morto non manda il messaggio che
#        dice che e' morto, e l'assenza di una mail non si nota. ⇒ Qualcosa
#        FUORI dal backend deve guardarlo: il job pgAgent `guardiano_digest`
#        (ogni ora al minuto 20) legge il panorama a catalogo e, se
#        `digest_presidi` e' `MUTO`, accoda UN lavoro al giorno su
#        `dbops.coda_lavori` (`fn_guardiano_digest`, chiave
#        `guardiano_digest:<giorno>`). Lo esegue `draina_coda_lavori` — il
#        processo piu' vivo del backend, ogni minuto, con badge in topbar — che
#        e' questo handler.
#
#        ⛔ IL DESTINATARIO RESTA DEL BACKEND. pgAgent non spedisce e non
#        conosce nessun indirizzo: quello e' un fatto di deploy
#        (`PRESIDI_DIGEST_DESTINATARIO`, da `.env.systemd`), e nel database non
#        entra. E' lo stesso destinatario del digest, scritto con la stessa
#        funzione (`presidi_digest.accoda_email_presidi`): chi aspetta gli
#        allarmi e' la persona giusta a cui dire che gli allarmi non arrivano piu'.
#
#        ⚠️ `run_as = SISTEMA`: il lavoro non ha un'azienda, e il drenatore lo
#        esegue sul ruolo applicativo normale con `scope=None`. L'email esce
#        con `ambito = SISTEMA`, cioe' dalla porta `fn_accoda_email_sistema`
#        dentro `EmailRepository.insert_log` — su `config.email_log` c'e' la
#        RLS, e un INSERT diretto senza identita' verrebbe rifiutato.
#
#        ⛔ SENZA DESTINATARIO IL LAVORO FALLISCE, e fallisce TERMINALE: e'
#        `E_CONFIG_MANCANTE` con `terminale` nel context, cosi' il motore non
#        consuma tre tentativi su un esito che non cambia. Fallire e' la scelta
#        giusta e non un ripiego: «ho visto e non ho potuto dirlo» deve restare
#        visibile, e un job in ERRORE lo e' — in `vw_coda_lavori_da_guardare`,
#        cioe' nel pannello. Un `return {"inviato": False}` sarebbe un FATTO
#        verde su un avviso che nessuno ha ricevuto.
# Note: Il tipo `NOTIFICA_DIGEST_MUTO` e' seedato `attivo = false` finche'
#        questo handler non e' in release (regola del binding): a tipo spento
#        il guardiano SOLLEVA `E_JOB_TYPE_NON_ATTIVO` — corsa rossa nel
#        giornale, voluta. Accenderlo e' una riga del CSV `coda_lavori_tipi`,
#        a carico del team DB, DOPO il deploy di questo file.
# ------------------------------------------------------------

from __future__ import annotations

import html
import logging
from typing import Any

from apps.core.services.coda_lavori.drain_engine import CONTEXT_KEY_TERMINALE
from apps.core.services.presidi_digest import accoda_email_presidi
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.services.service_errors import ServiceError
from apps.core.services.sveglie import sveglie_di_processo

logger = logging.getLogger(__name__)

# handler_code seedato in `dbops.coda_lavori_tipi` per il tipo NOTIFICA_DIGEST_MUTO.
HANDLER_CODE = "notifica_digest_muto_default"

# Chi ha VISTO, per il contesto dell'email: il job pgAgent che accoda questo
# lavoro. ⚠️ MIRROR DICHIARATO di `coda_lavori_tipi.processo_codice` per il tipo
# `NOTIFICA_DIGEST_MUTO` — non sta in `processi.py` perche' quel modulo elenca
# solo i processi che il BACKEND avvia, e questo lo avvia pgAgent. Serve a una
# riga di `contesto_json`, non a una decisione: se un giorno il produttore
# cambia nome, cambia qui e nel CSV insieme, e nulla si rompe nel frattempo.
_PROCESSO_GUARDIANO = "guardiano_digest"


# Scopo: Compone oggetto, testo e HTML dell'avviso dal payload del guardiano
#        (`processo_codice`, `tolleranza_minuti`, `ultimo_segno_di_vita`,
#        `muto_da`). Pura: si prova senza database.
# ⭐ L'OGGETTO DICE DA QUANTO, e non e' cosmesi: e' l'unica riga che si legge
#    senza aprire, ed e' quella che decide se il messaggio viene aperto.
# ⚠️ I valori del payload vengono dal database (scritti da `fn_guardiano_digest`)
#    e finiscono in un HTML: si escapano comunque — e' la regola, non la fiducia.
def componi_avviso_digest_muto(payload: dict[str, Any]) -> tuple[str, str, str]:
    processo = str(payload.get("processo_codice") or PROCESSO_DIGEST_PRESIDI)
    tolleranza = payload.get("tolleranza_minuti")
    ultimo = payload.get("ultimo_segno_di_vita")
    muto_da = payload.get("muto_da")

    da_quanto = f" da {muto_da}" if muto_da else ""
    oggetto = f"[ZeroERP] Il digest dei presidi e' MUTO{da_quanto}"

    contratto = (
        f"un segno di vita almeno ogni {tolleranza} minuti"
        if tolleranza is not None else "nessun contratto dichiarato"
    )
    ultimo_txt = str(ultimo) if ultimo else "— (mai registrato)"
    muto_txt = str(muto_da) if muto_da else "—"
    comandi = _comandi_da_lanciare(processo)

    testo = "\n".join([
        "IL DIGEST DEI PRESIDI NON GIRA — avviso del guardiano (pgAgent)",
        "",
        f"Processo:              {processo}",
        f"Ultimo segno di vita:  {ultimo_txt}",
        f"Contratto:             {contratto}",
        f"Muto da:               {muto_txt}",
        "",
        "Che cosa vuol dire: il digest e' il processo che segnala tutti gli",
        "altri. Finche' tace, nessun allarme dei presidi arriva a nessuno —",
        "compreso questo, se non fosse per il guardiano che lo accoda dall'altra",
        "parte del muro.",
        "",
        "Che cosa guardare, sull'host del backend:",
        *(f"  {c}" for c in comandi),
        "",
        "Chi lo dice: dbops.fn_guardiano_digest (job pgAgent guardiano_digest,",
        "ogni ora) legge dbops.vw_processi_programmazione e accoda su",
        "dbops.coda_lavori al massimo UN avviso al giorno; lo spedisce",
        "draina_coda_lavori. Il digest tornera' da solo alla prossima corsa",
        "utile del suo timer, se il timer e' acceso.",
    ])

    e = html.escape
    corpo_html = "".join([
        "<h2>Il digest dei presidi non gira</h2>",
        "<p>Avviso del <strong>guardiano</strong> (pgAgent): il processo che ",
        "segnala tutti gli altri ha smesso di lasciare un segno di vita.</p>",
        "<table>",
        f"<tr><td>Processo</td><td><code>{e(processo)}</code></td></tr>",
        f"<tr><td>Ultimo segno di vita</td><td>{e(ultimo_txt)}</td></tr>",
        f"<tr><td>Contratto</td><td>{e(contratto)}</td></tr>",
        f"<tr><td>Muto da</td><td><strong>{e(muto_txt)}</strong></td></tr>",
        "</table>",
        "<p>Finch&eacute; tace, <strong>nessun allarme dei presidi arriva a ",
        "nessuno</strong>.</p>",
        "<p>Che cosa guardare, sull'host del backend:</p>",
        "<pre>" + e("\n".join(comandi)) + "</pre>",
        "<p style=\"color:#666\">Lo accoda <code>dbops.fn_guardiano_digest</code> ",
        "(job pgAgent <code>guardiano_digest</code>, ogni ora), al massimo uno al ",
        "giorno; lo spedisce <code>draina_coda_lavori</code>.</p>",
    ])
    return oggetto, testo, corpo_html


# Scopo: i comandi da suggerire a chi legge, per l'host del backend. Le unit
#        si LEGGONO dal dichiarato di deploy (`sveglie.json`) — sono le sveglie
#        del processo muto — non si ricopiano qui: un nome scritto a mano in
#        una mail e' la seconda sede, e una mail con l'unit sbagliata manda la
#        persona a guardare la cosa sbagliata alle sette di mattina.
# ⚠️ `run-command.sh` e' il wrapper che systemd stesso usa (`ExecStart`), quindi
#    lanciarlo a mano riproduce l'ambiente della corsa vera — `manage.py`
#    diretto no (env non caricato).
def _comandi_da_lanciare(processo: str) -> list[str]:
    unit = [s.unit for s in sveglie_di_processo(processo)]
    comandi = [f"systemctl list-timers '{u}.timer'" for u in unit]
    comandi += [f"journalctl -u {u}.service -n 50" for u in unit]
    # `--secco` e' un'opzione del SOLO command del digest: si suggerisce solo
    # se il processo muto e' lui (e' il perimetro del guardiano, ma il payload
    # lo dice e qui lo si legge, non lo si assume).
    if processo == PROCESSO_DIGEST_PRESIDI:
        comandi.append(f"backend/bin/run-command.sh {processo} --secco")
    return comandi


# Scopo: Esegue il lavoro: compone l'avviso e lo accoda a chi aspetta i
#        presidi (`accoda_email_presidi`: destinatario dal setting, email di
#        SISTEMA su `config.email_log`). Ritorna l'esito (riga scritta,
#        destinatario, copie, di che cosa si e' avvisato).
#        `scope` e' `None` per costruzione (`run_as = SISTEMA`) e non si usa.
def notifica_digest_muto_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    riguarda = str(payload.get("processo_codice") or PROCESSO_DIGEST_PRESIDI)
    oggetto, testo, corpo_html = componi_avviso_digest_muto(payload)
    accodata = accoda_email_presidi(
        oggetto=oggetto,
        testo=testo,
        corpo_html=corpo_html,
        # Due processi nel contesto: chi ha VISTO e di chi si PARLA.
        contesto_json={
            "processo": _PROCESSO_GUARDIANO,
            "riguarda": riguarda,
            "muto_da": payload.get("muto_da"),
            "ultimo_segno_di_vita": payload.get("ultimo_segno_di_vita"),
            "tolleranza_minuti": payload.get("tolleranza_minuti"),
        },
    )
    if accodata is None:
        # ⛔ Terminale: riprovare fra dieci minuti non fa comparire un indirizzo.
        raise ServiceError(
            code="E_CONFIG_MANCANTE",
            message=(
                "Il digest dei presidi e' MUTO ma non c'e' nessuno a cui dirlo: "
                "ZEROERP_PRESIDI_DIGEST_DESTINATARIO non e' configurato "
                "(backend/.env.systemd, per-host)."
            ),
            detail=f"riguarda={riguarda!r} muto_da={payload.get('muto_da')!r}",
            context={CONTEXT_KEY_TERMINALE: True, "setting": "ZEROERP_PRESIDI_DIGEST_DESTINATARIO"},
        )
    logger.warning(
        "notifica_digest_muto.accodata destinatario=%s copie=%d muto_da=%s",
        accodata.destinatario, len(accodata.copie), payload.get("muto_da"),
    )
    return {
        "email_log_id": accodata.email_log_id,
        "destinatario": accodata.destinatario,
        "copie": len(accodata.copie),
        "riguarda": riguarda,
        "muto_da": payload.get("muto_da"),
    }


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `CoreConfig.ready()`: registrazione esplicita al boot, mai
#        auto-discovery — stesso patto degli altri handler di coda.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, notifica_digest_muto_handler)
