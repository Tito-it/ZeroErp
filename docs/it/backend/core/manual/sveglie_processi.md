# Sveglie dei processi — il dichiarato di deploy (`apps.core.services.sveglie`)

## Scopo

Dire **chi sveglia ogni processo automatico del backend**, con quale cadenza, e
entro quanto il suo ultimo run vale ancora come segno di vita — da una sede
sola, leggibile da due programmi.

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

Brief: [brief-db-sveglia-dei-processi](../../../dev/work-in-progress/brief-db-sveglia-dei-processi.md).

## Input

`backend/deploy/sveglie.json`, un elenco di sveglie. Una voce per **unit**, non
per processo: `run_fatturazione_batch` ne ha due, una per corsia.

| Campo | Tipo | Significato |
| --- | --- | --- |
| `unit` | string | nome dell'unit systemd, senza estensione |
| `processo_codice` | string | `dbops.processi.codice` — l'attore che comparirà sul giornale dei run |
| `forma` | `timer` \| `servizio` | un timer ha una cadenza; un servizio è sempre acceso |
| `oncalendar` | string \| null | cadenza default (`null` per i servizi) |
| `abilita` | bool | se l'installer lo accende — **obbligatorio** |
| `tolleranza_minuti` | int \| null | entro quanto l'ultimo run vale «vivo»; `null` = non si presidia da qui |
| `nota` | string | il perché delle scelte, mostrato dall'installer per gli spenti |

## Output

```python
from apps.core.services.sveglie import (
    carica_sveglie,        # tuple[Sveglia, ...] — tutto il dichiarato, validato
    sveglie_di_processo,   # (processo_codice) -> tuple[Sveglia, ...]
    tolleranza_minuti,     # (processo_codice) -> int | None
    TEMPLATE_DIR,          # backend/deploy/systemd/
)
```

Consumer: `coda_lavori.gestione_service._liveness_worker` (la soglia del badge
code) e — dall'altro lato — `backend/bin/install-timers.sh`, che dallo stesso
file prende l'`OnCalendar` da sostituire nei template e la lista di cosa
abilitare.

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
- ⚠️ **`tolleranza_minuti: null` non è zero**: significa «non si presidia la
  liveness da qui», e il lettore lo distingue con `is None` (un `or` li
  confonderebbe). Per un processo con più sveglie si prende la tolleranza **più
  larga**: basta che una corsia abbia girato perché il processo sia vivo, e la
  più stretta darebbe un falso allarme.
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
| `test_worker_del_badge_hanno_una_tolleranza` | che il ripiego da 10 minuti diventi la strada normale in silenzio |
| `scripts/tests/test-install-timers.sh` | che si accendano unit diversi da quelli dichiarati (vedi sotto) |
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

- **Aggiungere una sveglia** = una voce in `sveglie.json` + la coppia di
  template in `deploy/systemd/` (solo il `.service` per un servizio sempre
  acceso) + `sudo backend/bin/install-timers.sh`. Niente altro.
- `WORKER_ATTIVO_SOGLIA_MINUTI` **non esiste più**: era pubblico nel modulo
  `gestione_service` e non aveva altri consumatori. Il numero a video non
  cambia — 10 minuti per entrambi i drainer — cambia chi lo dichiara.
- ⚠️ Il ramo `systemctl enable` è ora **provato**, ma il caso «`enable`
  fallisce» no: lo stub esce sempre `0`. Vuole uno stub parametrico ed è un test
  suo.
- Playbook operativo: §17 di
  [play-book-operativo-backend](../../../dev/backend/play-book-operativo-backend.md).
