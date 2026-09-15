# Sveglie dei processi — il dichiarato di deploy (`apps.core.services.sveglie`)

## Scopo

Dire **chi sveglia ogni processo automatico del backend**, con quale cadenza e
**con quale riga di comando** — da una sede sola, leggibile da due programmi.

⚠️ Fino al 2026-09-11 questa riga diceva anche *«entro quanto il suo ultimo run
vale ancora come segno di vita»*: la tolleranza è il **contratto** del processo
e vive in `dbops.processi.tolleranza_minuti`, non qui (vedi Regole).

## Contesto

I processi su canale `COMMAND` di `dbops.processi` li fa partire systemd, non
pgAgent. ⇒ Il database non può sapere se stiano partendo, e infatti
`dbops.vw_processi_programmazione` li classifica `FUORI_PORTATA` — *«il database
non può saperlo»*, che è tutto ciò che può onestamente dire.

🔴 **Chi poteva saperlo non guardava.** Il 2026-09-06, **tre processi su sei**
(`send_pending_emails`, `sync_auth_user_active`, `listen_cambio_reparto`) erano
a catalogo, si registravano su `maintenance.job_run_log`, e **non avevano nessun
artefatto di deploy**: su un host nuovo non partivano mai, e non c'era niente
che potesse accorgersene.

⛔ **E lo stesso fatto era già scritto in due posti** che non si conoscevano:
l'`OnCalendar` cablato dentro `install-timers.sh` e
`WORKER_ATTIVO_SOGLIA_MINUTI = 10` in `coda_lavori/gestione_service.py` (due
processi su sei, margine 10× e 5× sulle rispettive cadenze, senza il perché
scritto da nessuna parte). Due scritture prima o poi dissentono, e lì la
divergenza sarebbe stata **muta**: un pallino verde su un worker fermo.

Brief: [brief-db-sveglia-dei-processi](../../../dev/work-done/brief-db-sveglia-dei-processi.md).

## Input

`backend/deploy/sveglie.json`, un elenco di sveglie. Una voce per **unit**, non
per processo: `run_fatturazione_batch` ne ha due, una per corsia.

| Campo | Tipo | Significato |
| --- | --- | --- |
| `unit` | string | nome dell'unit systemd, senza estensione |
| `processo_codice` | string | `dbops.processi.codice` — l'attore che comparirà sul giornale dei run |
| `forma` | `timer` \| `servizio` | un timer ha una cadenza; un servizio è sempre acceso |
| `comando` | string[] | **dal 2026-09-14** — l'argv dopo `bin/run-command.sh` (`["digest_presidi", "--cadenza", "settimanale"]`), reso nel template come `__COMANDO__`. **Obbligatorio per ogni forma**, una lista non vuota, primo token = nome di un management command |
| `oncalendar` | string \| null | cadenza default (`null` per i servizi) |
| `abilita` | bool | se l'installer lo accende — **obbligatorio** |
| `avvio_manuale` | bool | **dal 2026-09-15** — «Esegui ora» è un gesto sensato su questa sveglia? **Obbligatorio** (anche sui servizi, dove vale `false` per natura e un `true` è rifiutato). ⛔ Non è `abilita`: quella dice se il *timer* è acceso su questa installazione, questa se il *pulsante* ha senso — un comando lungo per natura resta `false` anche il giorno in cui il suo timer si accende |
| `nota` | string | il perché delle scelte, mostrato dall'installer per gli spenti |

⛔ **`tolleranza_minuti` non è un campo**, e se compare il caricamento
**fallisce**: dal 2026-09-11 il contratto di liveness vive in
`dbops.processi.tolleranza_minuti` (seed `80_data/sql/dbops/processi.csv`) e lo
legge `ProcessiRepository.contratti_liveness`. Fino a quel giorno la riga stava
in questa tabella.

## Output

```python
from apps.core.services.sveglie import (
    carica_sveglie,        # tuple[Sveglia, ...] — tutto il dichiarato, validato
    sveglie_di_processo,   # (processo_codice) -> tuple[Sveglia, ...]
    DEPLOY_DIR,            # backend/deploy/
    TEMPLATE_DIR,          # backend/deploy/systemd/
    RUN_COMMAND,           # backend/bin/run-command.sh — il wrapper che systemd
                           # esegue e che «Esegui ora» lancia come sottoprocesso
)
```

`Sveglia` porta `unit`, `processo_codice`, `forma`, **`comando`**
(`tuple[str, ...]`), `oncalendar`, `abilita`, **`avvio_manuale`**, `nota` e la
proprietà `e_timer`.
⚠️ `tolleranza_minuti(...)` **non esiste più** dal 2026-09-11 (sopra).

Consumer: `notifica_digest_muto_handler` (le unit del processo muto, per la
mail), `test_contratto_liveness_vs_deploy` (la cadenza contro il contratto) e —
dall'altro lato — `backend/bin/install-timers.sh`, che dallo stesso file prende
l'`OnCalendar` **e il comando** da sostituire nei template e la lista di cosa
abilitare. ⭐ **Dal 2026-09-15 `comando` ha il consumer per cui è nato**:
`esegui_processo_handler` (il drenatore) lancia `[RUN_COMMAND, *comando]` come
sottoprocesso — la stessa riga del timer, per costruzione — e
`avvio_manuale.py` legge `forma`, `avvio_manuale` e `abilita` per il predicato
«si può lanciare a mano?» (capability `can_esegui_ora` nel dettaglio del
processo, rifiuto dell'endpoint `esegui-ora/`, ricontrollo dell'handler).
Brief [brief-db-avvio-manuale-di-un-processo](../../../dev/work-in-progress/brief-db-avvio-manuale-di-un-processo.md),
piano [piano-be-fe-avvio-manuale-di-un-processo](../../../dev/work-in-progress/piano-be-fe-avvio-manuale-di-un-processo.md).

## Regole

- ⛔ **La chiave è l'`unit`, non il processo.** Chiavare sul processo avrebbe
  fatto sparire in silenzio una delle due corsie della fatturazione.
- ⛔ **Non va su `dbops.processi`.** Il registro dice quali processi esistono, di
  che classe e su quale canale; *come li si sveglia è un fatto di deploy* e vive
  dove vive il deploy. È la stessa ragione per cui il team DB ha rifiutato di
  dichiarare su quella tabella la cadenza dei job pgAgent: pgAgent la sa già.
- ⛔ **`abilita` si dichiara, non si omette.** Con un default il silenzio
  varrebbe «spento» — cioè un processo che non parte, il guasto-per-assenza per
  cui questo file esiste, reintrodotto dalla porta di servizio.
- ⛔ **La tolleranza NON sta qui** (dal 2026-09-11, brief
  `brief-db-quattro-processi-senza-presidio.md` D5). Cadenza e tolleranza sono
  due fatti: la cadenza è *come il deploy onora* il processo e resta nel JSON;
  la tolleranza è il *contratto* del processo, uguale su ogni installazione, e
  il lettore che ne ha più bisogno è il database (`vw_processi_programmazione`,
  il guardiano pgAgent). `carica_sveglie` **rifiuta** il campo se ricompare.
  Il confronto fra la cadenza di qui e quel contratto è
  `test_contratto_liveness_vs_deploy`.
- ⭐ **La riga di comando sta qui, e il template porta `__COMANDO__`** (dal
  2026-09-14). Il motivo è «Esegui ora»: il pulsante lancia **lo stesso**
  comando del timer, meno l'orario, e il backend non può leggerlo da un file
  `.service`. Una sede sola: la riga che il timer esegue *è* quella che il
  pulsante esegue, e non possono divergere. ⛔ Un `comando` ricopiato nel JSON
  *accanto* a una riga cablata nel template sarebbe la seconda sede — quella
  che resta indietro, e qui «indietro» vuol dire un pulsante che lancia una
  cosa diversa dal timer. Lo prova `test-install-timers.sh` (test 6: nessun
  `ExecStart` cablato; test 7: l'unit reso porta l'argv del JSON).
  - **Una lista di token, mai una stringa**: systemd spezza l'`ExecStart`
    sugli spazi, `subprocess` passa ogni token intero — «come si spezza»
    sarebbe una regola scritta due volte.
  - **Whitelist stretta sui token** (`_ARGOMENTO_AMMESSO`): niente spazi,
    quote, `%` (specifier systemd), `$` (ambiente), `|`/`&`/`\` (il `sed`
    dell'installer). Si allarga quando un comando *vero* ne ha bisogno: un
    cancello che boccia un carattere di troppo si vede in CI, uno che ne
    lascia passare uno di meno si vede sull'host.
  - **Il primo token è un management command che esiste** nel backend
    (`test_sveglie.py`, test 13): un refuso non fallirebbe in CI ma sull'host,
    alla prima corsa, con un `Unknown command` nel journal che nessuno legge.
  - **Obbligatorio anche per `forma = servizio`**: ogni `.service` ha un
    `ExecStart`, e una regola con un'eccezione sono due regole. Che «Esegui
    ora» valga solo per i timer lo decide chi rende il pulsante, sulla `forma`.
- ⚠️ **Il dichiarato è il default di progetto, non lo stato di un host.** Un host
  può avere un `OnCalendar` diverso o un timer spento a mano: per sapere cosa
  gira davvero c'è `maintenance.job_run_log`. Il valore sta nel **confronto** —
  una promessa senza verifica invecchia come tutte.
- ⛔ **Il nome dell'unit passa da una regex.** Finisce interpolato in un percorso
  e passato a `systemctl`: un refuso con una barra scriverebbe fuori da
  `/etc/systemd/system`. Stesso presidio degli identificatori SQL interpolati.
- ⛔ **Ritirare una sveglia è un gesto in TRE pezzi, e vanno insieme**: la voce
  qui, la coppia di template, e la costante `PROCESSO_*` in
  `apps/core/services/processi.py`. Lasciarne uno fa dissentire
  `test_ogni_processo_del_backend_ha_una_sveglia` e `test_nessun_template_orfano`,
  che guardano lo stesso fatto dai due versi.
  ⭐ **Ed è successo**: `zeroerp-sync-auth-user-active`, ritirata il 2026-09-07
  perché `dbops.processi` aveva due righe per lo stesso lavoro e il team DB ha
  scelto il gemello pgAgent (brief §8.5). L'assenza è **dichiarata** nella chiave
  `_ritirate` di `sveglie.json`: un'assenza non scritta si rilegge come una
  dimenticanza, e qualcuno la «ripara».
  ⚠️ Il management command sopravvive come attrezzo a mano e **non registra più
  un run**: registrarsi sotto il codice superstite sposterebbe avanti
  `giornale_ultima_corsa` e spegnerebbe il confronto `GIRA_E_NON_REGISTRA` su
  quel job — la LATERAL del panorama legge il giornale **senza filtrare
  `origine`**. Playbook §17.3.

### I presidi

| Presidio | Cosa impedisce |
| --- | --- |
| `test_ogni_processo_del_backend_ha_una_sveglia` | ⭐ un processo che il backend dichiara di eseguire e che **nessun unit fa partire** — nomina il processo scoperto |
| `test_nessun_template_orfano` | un unit su disco che il dichiarato non nomina: non lo installa nessuno |
| `test_cartella_template_esiste_e_non_e_vuota` | che i due sopra passino **a vuoto** se il layout cambia |
| `test_worker_del_badge_hanno_un_contratto` | che il ripiego da 10 minuti diventi la strada normale in silenzio (legge il seed `processi.csv`) |
| `test_comando_obbligatorio_lista_non_vuota` · `test_comando_con_spazi_o_metacaratteri_e_rifiutato` | un `comando` assente, stringa, o con token che systemd e `subprocess` leggerebbero in due modi |
| `test_il_comando_dichiarato_esiste_nel_backend` | ⭐ un `comando` che nomina un management command inesistente: fallirebbe sull'host, non in CI |
| `test_avvio_manuale_obbligatorio_e_bool` · `test_un_servizio_non_si_avvia_a_mano` · `test_il_drenatore_non_e_candidato_e_almeno_un_timer_si` (`test_sveglie.py` 14-16) | «Esegui ora» dal drenatore, o su un servizio, nato da una dimenticanza: `avvio_manuale` si dichiara, e la unit del drenatore si legge da `sveglie_di_processo`, non ricopiata |
| `test_avvio_manuale_tetto` | un tetto del sottoprocesso più largo della metà della tolleranza del drenatore o della soglia del reaper: `MUTO` a video, o un lavoro in `ERRORE` mentre il comando sta finendo |
| `scripts/tests/test-install-timers.sh` (test 0-5) | che si accendano unit diversi da quelli dichiarati (vedi sotto) |
| `scripts/tests/test-install-timers.sh` (test 6-7) | una **seconda sede** del comando: un template con `ExecStart` cablato, o un unit reso che non porta l'argv del JSON |
| `systemd-analyze verify` (CI) | un unit sintatticamente invalido |

⭐ **Le ultime due sono due metà distinte**: `systemd-analyze verify` dice che
gli unit **sono validi**, il test con lo stub dice che **si accendono quelli
giusti**. Fino al 2026-09-06 c'era solo la prima, e il difetto è passato proprio
di lì: `install-timers.sh` leggeva i campi con `IFS=$'\t'`, che collassa i TAB
consecutivi — quindi su un `oncalendar` vuoto (il caso normale di un servizio
sempre acceso) `abilita` diventava il testo della nota e
`zeroerp-listen-cambio-reparto` veniva **installato e mai avviato**. La CI
renderizzava sette unit corretti e non poteva vederlo, perché `--render-only`
esce prima del ramo che accende.

⇒ Il test mette un `systemctl` **finto** in testa al `PATH` (lo script lo invoca
senza percorso assoluto) e sposta la destinazione con `ZEROERP_SYSTEMD_DIR`,
così cade anche il requisito di root — che serve a scrivere in
`/etc/systemd/system`, non «perché è la modalità install». ⛔ **Non è un
`--dry-run`**: quello avrebbe provato il ramo che *non* accende, cioè proprio
quello che non interessa. Le righe eseguite sono le stesse della produzione.

## Dipendenze DB

Nessuna: è un file di progetto, e il modulo non apre connessioni.

- `dbops.processi.codice` è referenziato **per valore** dal campo
  `processo_codice`. Il legame lo tiene il presidio, non una FK: `sveglie.json`
  non è una tabella.
- A valle, `maintenance.job_run_log` è ciò con cui il dichiarato si confronta
  (`MaintenanceRepository.job_liveness`).

## Note di migrazione

- **Aggiungere una sveglia** = una voce in `sveglie.json` (con il suo
  `comando`) + la coppia di template in `deploy/systemd/` (solo il `.service`
  per un servizio sempre acceso; l'`ExecStart` è
  `__APP_DIR__/bin/run-command.sh __COMANDO__`, mai la riga scritta a mano) +
  `sudo backend/bin/install-timers.sh`. Niente altro.
- **2026-09-14 — `comando` nel JSON, `__COMANDO__` nei template.** Gli otto
  `ExecStart` resi sono **identici** a prima (il campo è nato dalla riga che
  ogni template eseguiva): sugli host cambia il template, non l'unit
  installato. Prerequisito di deploy di «Esegui ora» (analisi
  `analisi-riavvio-processi-da-interfaccia.md` §9-bis, punto 2); l'handler,
  `registered_job` con origine e attore dall'ambiente, l'endpoint e il
  pulsante sono arrivati il 15-09 (voce sotto).
- **2026-09-15 — `avvio_manuale` nel JSON, `RUN_COMMAND` nel modulo, e i
  consumer di `comando` in servizio.** Otto voci: `false` su drenatore
  (`zeroerp-coda-lavori`: «Esegui ora» lo esegue lui), sui due giri di
  fatturazione (lunghi per natura: terrebbero fermo il drenatore, decisione 2a
  di Tid — brief §8.5) e sul listener (servizio); `true` su digest ×2,
  `send-pending-emails`, `coda-stampa`. `install-timers.sh` **non** legge il
  campo — non è un fatto di systemd — e `test-install-timers.sh` non cambia.
  Chi lo legge: `avvio_manuale.py` (predicato), `esegui_processo_handler`
  (drenatore), `ProcessiService` (capability nel dettaglio, verbo).
- `WORKER_ATTIVO_SOGLIA_MINUTI` **non esiste più**: era pubblico nel modulo
  `gestione_service` e non aveva altri consumatori. Il numero a video non
  cambia — 10 minuti per entrambi i drainer — cambia chi lo dichiara.
- ⚠️ Il ramo `systemctl enable` è ora **provato**, ma il caso «`enable`
  fallisce» no: lo stub esce sempre `0`. Vuole uno stub parametrico ed è un test
  suo.
- Playbook operativo: §17 di
  [play-book-operativo-backend](../../../dev/backend/play-book-operativo-backend.md).
