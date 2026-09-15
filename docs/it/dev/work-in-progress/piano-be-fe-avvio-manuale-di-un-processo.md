# Piano BE/FE — «Esegui ora» su una sveglia: analisi e lavoro a valle dell'apply DB

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-15.
> **Origine:** [brief-db-avvio-manuale-di-un-processo.md](brief-db-avvio-manuale-di-un-processo.md)
> §8 (risposta DB del 14-09, con le due decisioni di Tid in §8.5) e
> [analisi-riavvio-processi-da-interfaccia.md](analisi-riavvio-processi-da-interfaccia.md)
> §4.1-bis / §7-bis / §9-bis.
> **Stato:** 🟡 **piano approvato, nessuna riga di codice scritta** — le cinque
> decisioni di §3 sono **confermate da Tid il 2026-09-15**; il difetto di §7.1
> entra nel perimetro per sua decisione lo stesso giorno. Si parte dopo i
> prerequisiti di §4.1 (merge del lato DB, seed dei codici).
>
> **In una riga:** il DB ha consegnato le tre righe (processo `avvio_manuale`,
> tipo `ESEGUI_PROCESSO` **spento**, azione `processo_avvia`) e il deploy ha già
> `comando` in `sveglie.json`. Restano **cinque pezzi BE** (l'ambiente letto da
> `registered_job`, il predicato «si può lanciare?», l'handler, il verbo, la
> capability nel dettaglio), **un pezzo FE** (il tab «Sveglie» nel drawer) e
> **una richiesta al DB** che il brief non aveva previsto: i codici errore del
> verbo, senza i quali il backend non può nominare nessun rifiuto.

---

## 0. Che cosa c'è già, riverificato sul repo e sul dbdev (2026-09-15)

| Pezzo | Dove | Stato |
| --- | --- | --- |
| Le tre righe di catalogo | `80_data/sql/dbops/processi.csv` (id 45), `dbops/coda_lavori_tipi.csv` (`ESEGUI_PROCESSO`, `attivo=false`), `config/azioni_processo.csv` (id 35) + pgTAP `test-coda-tipi-canale-e-run-as.sql` | ✅ **applicate sul dbdev** (brief §8.4). ⚠️ Il commit `53d5ca923` sta su `origin/dev/db-tid` e **non è ancora su Tito-dev** — vedi §4.1 |
| `comando` nel dichiarato + `__COMANDO__` nei template | `deploy/sveglie.json`, `deploy/systemd/*.service`, `install-timers.sh`, `sveglie.py` (`Sveglia.comando`, whitelist token), `test-install-timers.sh` 6-7, `test_sveglie.py` 11-13 | ✅ fatto il 14-09 (commit `311862f90`) |
| Il drenatore e il registry | `coda_lavori/drain_engine.py`, `drainer_service.py` (`_dispatch_item`: `OPERATORE` → `operator_identity_context` con la terna), `handler_registry.py`, `CoreConfig.ready()` | ✅ in servizio; il precedente è `notifica_digest_muto_handler.py` |
| La registrazione run | `job_run.py::registered_job(job_name, *, processo_codice, origine=ORIGINE_CRON, …, auth_user_id=None)` | ✅ esiste. ⚠️ Il brief la chiama `job_run()`: **il nome vero è `registered_job`**, e oggi legge origine e attore **solo dagli argomenti** — i sei command passano tutti `ORIGINE_CRON` |
| Le view dei processi | `amm_software/api/views.py` (`ProcessiListView`, `ProcessiDetailView`, `ProcessiRunView`, …), tutte `AdminAPIView`; `core/services/processi_service.py`; `core/db/processi_repository.py` | ✅ in servizio. `list_run_processo` proietta già `origine` e `auth_username`: il run a mano si vedrà nel tab «Ultimi run» **senza toccare la query** |
| La cattura dello scope OPERATORE all'enqueue | `vendite/api/views.py::_accoda_job_fatturazione` (terna + `emittente_attivo_id` + `emittente_ids` + `scope_key`) | ✅ **una** occorrenza. Questo cantiere è la **seconda** → §3.3 |
| Il drawer | `frontend/src/amministrazione/components/ProcessoDrawer.vue` (3 tab: bersagli, identità, run) + `api/amministrazione.js` | ✅; il tab «Sveglie» non esiste |
| Il BB FE per la frase di un'azione spenta | `core/utils/bloccoMotivo.js` (`motivoBloccoRiga(t, te, riga, prefisso)`, `bloccoAttivo`) | ✅ legge `<prefisso>_reason` / `_reason_key` / `_dettaglio` |

**Le due cose del brief che questo piano cambia, e perché:**

1. **Il «registro a ritiro» del §6 non serve più.** Era pensato per attendere
   l'apply; l'apply è avvenuto. Il verso di ritiro che il DB stesso ha nominato
   (`test_nessun_handler_orfano` rosso se l'handler nasce prima del seed) esiste
   già, e il cancello in avanti (`test_ogni_tipo_attivo_ha_un_handler`) presidia
   l'accensione. Resta da scrivere solo un test **su DB provvisto** che fissa le
   tre righe come le legge il backend (§5.4), perché `richiedi_db_provvisto`
   fallisce — non salta — su schema presente e oggetto assente.
2. **`post_permission = "processo_avvia"` non si scrive sulla view** (decisione
   1 di §8.5: v1 solo `SUPER_ADMIN`, `AdminAPIView`). Si scrive il **commento**
   che dice dov'è la sede della fiducia, così chi legge la view non cerca un
   presidio che non c'è — la forma «omesso e commentato» del brief, non quella
   «decorativo e commentato»: un attributo che sembra un cancello è peggio di
   nessun attributo.

---

## 1. Il disegno, in un giro

```text
[drawer]  Esegui ora ──► POST amm-software/processi/<codice>/esegui-ora/ {unit}
                            │  AdminAPIView · Idempotency-Key · scope = terna di chi preme
                            │  predicato «si può lanciare?» (§2.2) → 4xx parlante PRIMA di accodare
                            ▼
                         dbops.fn_accoda_lavoro('ESEGUI_PROCESSO', payload={processo_codice, unit},
                                                 run_as=OPERATORE, scope, idempotency_key='esegui:<unit>')
                            │  ⚠️ a tipo spento → E_JOB_TYPE_NON_ATTIVO (501): è il cancello voluto
                            ▼
[drenatore, ogni minuto]  handler esegui_processo_default
                            │  rilegge la whitelist (stesso predicato, difesa in profondità)
                            │  subprocess.run([bin/run-command.sh, *comando], env + ZEROERP_JOB_ORIGINE=COMMAND
                            │                 + ZEROERP_JOB_AUTH_USER_ID=<scope.auth_user_id>, timeout=TETTO)
                            ▼
[sottoprocesso]           manage.py <comando> → registered_job(...) legge l'ambiente:
                            origine=COMMAND, auth_user_id=<chi ha premuto>  → maintenance.job_run_log
                            sotto il processo ESEGUITO (es. digest_presidi:settimanale)
```

Due righe, due domande, come dice il brief corretto dal DB (§8.2.1): l'audit
del **gesto** è la riga di `dbops.coda_lavori` (scope, payload, esito, corsa
del drenatore); l'audit dell'**esecuzione** è il run del comando sul giornale,
con `origine = COMMAND` e l'utente di chi ha premuto. Sotto `avvio_manuale`
non si scrive nessun run.

---

## 2. Analisi: i cinque pezzi BE, e cosa decide ciascuno

### 2.1 `registered_job` legge origine e attore dall'ambiente

`apps/core/services/job_run.py`. Due variabili, `ZEROERP_JOB_ORIGINE` e
`ZEROERP_JOB_AUTH_USER_ID`: se presenti **vincono** sugli argomenti; ogni
command presente e futuro le eredita senza una riga (analisi §4.1-bis).

* ⛔ **Fail-loud sul valore**: un'origine fuori da `{PGAGENT, CRON, COMMAND}` o
  un `auth_user_id` non numerico **sollevano**, non ripiegano su `CRON` — un
  ripiego scriverebbe un run del timer per una corsa a mano, cioè il contrario
  di ciò per cui la variabile esiste.
* ⚠️ `auth_user_id` su `job_run_log` è documentato come «l'utente TECNICO, solo
  dove la risposta è UNA». Qui la risposta è una: la persona che ha premuto. Il
  brief lo accetta (§8.1 «con l'identità di chi ha premuto»); lo dice il
  commento del modulo, così la riga non sembra una violazione della regola.
* ⚠️ L'ambiente **si legge, non si pulisce**: il sottoprocesso muore con le sue
  variabili. Il drenatore le mette nell'`env` **del figlio** (dizionario
  copiato), mai nel proprio `os.environ`: altrimenti il lavoro successivo dello
  stesso giro erediterebbe l'attore del precedente.

### 2.2 Il predicato «questa sveglia si può lanciare a mano?» — una sede

È la `fn_check_*` di questo verbo, e sta in **Python** per una ragione che il
brief §2 ha già scritto: la whitelist è del deploy (`sveglie.json`), e il
database non conosce le unit. Modulo nuovo `apps/core/services/avvio_manuale.py`:

```python
motivi_esegui_ora(sveglia: Sveglia, *, lavoro_vivo: dict | None) -> list[str]
```

array **ordinato** di codici (primo motivo = quello che si mostra), letto da
**tre** consumatori — la capability nel dettaglio, il rifiuto dell'endpoint,
il ricontrollo dell'handler — così tooltip e rifiuto non «coincidono oggi»:
non possono divergere (`api.md` §Capability di riga, «il backend trasporta,
non deduce»). Contiene anche `JOB_TYPE_ESEGUI_PROCESSO`, `HANDLER_CODE`,
`chiave_idempotenza(unit) -> "esegui:<unit>"` e il **tetto** del sottoprocesso.

I motivi, nell'ordine in cui si leggono:

| # | Condizione | Codice (nuovo, §3.1) | Classe | Chi lo vede |
| --- | --- | --- | --- | --- |
| 1 | `forma = servizio`, oppure `avvio_manuale = false` nel dichiarato (§3.2) | `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` | `NON_ESEGUIBILE` (422) | pulsante **nascosto** sul servizio (è natura, non stato), **spento col motivo** sul timer dichiarato non candidato |
| 2 | `abilita = false` su questa installazione (D-A) | `E_PROCESSO_SVEGLIA_NON_ABILITATA` | `NON_ESEGUIBILE` (422) | spento col motivo *«sveglia non abilitata su questa installazione»* |
| 3 | esiste un lavoro `ESEGUI_PROCESSO` **vivo** con la stessa chiave | `E_PROCESSO_AVVIO_GIA_IN_CODA` | `CONFLITTO_STATO` (409) | spento col motivo *«già in coda (#id)»* — e l'endpoint rifiuta con lo stesso codice su una schermata invecchiata; la dedup di `fn_accoda_lavoro` resta la rete sotto (la corsa fra due click) |

⛔ Il motivo 3 **non** lo valuta l'handler (lui *è* il lavoro vivo): il
predicato lo riceve come parametro e chi non lo sa passa `None`. «Vivo» è
`stato IN ('PENDING','IN_CORSO')`, la stessa definizione dell'unique parziale
`uq_coda_lavori_vivo_idem`: la query sta in `CodaLavoriRepository`
(`lavori_vivi_per_chiave(job_type, chiavi) -> {chiave: {id, stato}}`, una
`SELECT … = ANY(%s)` per tutte le sveglie del processo), non ricopiata.

### 2.3 L'handler `esegui_processo_default`

`apps/core/services/coda_lavori/esegui_processo_handler.py`, registrato in
`CoreConfig.ready()` come i due fratelli. Fa **cinque cose**:

1. legge `processo_codice` e `unit` dal payload e risolve la `Sveglia` da
   `sveglie_di_processo(processo_codice)` — non trovata ⇒ `ServiceError`
   **terminale** (`E_VALIDATION_INPUT`, `contesto_terminale(...)`: un payload
   che nomina una unit che il deploy non ha non migliora ritentando);
2. **ricontrolla** `motivi_esegui_ora(sveglia, lavoro_vivo=None)` (difesa in
   profondità: il produttore l'ha già fatto, ma la whitelist si rilegge dove si
   esegue — analisi §8) ⇒ terminale col primo motivo;
3. lancia `subprocess.run([RUN_COMMAND, *sveglia.comando], env=…,
   capture_output=True, timeout=TETTO_SOTTOPROCESSO_SECONDI, check=False)` —
   **lista, mai shell**; `RUN_COMMAND = BACKEND_DIR / "bin" / "run-command.sh"`
   calcolato **in `sveglie.py`** accanto a `DEPLOY_DIR` (una sola aritmetica
   di percorso, come dice il suo header); file assente ⇒ `E_CONFIG_MANCANTE`
   terminale (deploy rotto, non si ritenta);
4. l'`env` è `{**os.environ, "ZEROERP_JOB_ORIGINE": "COMMAND",
   "ZEROERP_JOB_AUTH_USER_ID": str(scope["auth_user_id"])}` — il drenatore gira
   sotto systemd con `EnvironmentFile=.env.systemd`, quindi il figlio eredita
   i segreti che `run-command.sh` si aspetta, esattamente come sotto il timer;
5. l'esito: exit `0` ⇒ `result = {unit, comando, exit_code, durata_ms,
   coda_output}` (le ultime N righe di stdout+stderr, cappate); exit ≠ 0 ⇒
   `E_PROCESSO_AVVIO_FALLITO` terminale con `exit_code` e la coda nel
   `context`; `TimeoutExpired` ⇒ il figlio viene **ucciso** (`proc.kill()`,
   è ciò che `subprocess.run` fa da sé su timeout) e
   `E_PROCESSO_AVVIO_TROPPO_LUNGO` terminale con la frase *«troppo lungo per
   «Esegui ora»»* (decisione 2 di §8.5).

**Il tetto** (decisione 2a: «basso e scritto nell'handler, pochi minuti»):
`TETTO_SOTTOPROCESSO_SECONDI = 300`. Non è un numero a caso, e il test lo
pinna a due cose lette dal repo, non ricopiate: deve stare **sotto la metà**
della tolleranza del drenatore a catalogo (`draina_coda_lavori`: 10 minuti nel
seed `processi.csv` — una corsa che dura il tetto intero lascia il segno di
vita in tempo) e **sotto** `STALE_MINUTI_DEFAULT` (30) del reaper, che con
`max_tentativi = 1` manderebbe in `ERRORE` un lavoro il cui comando sta ancora
finendo (brief §8.2.3). Lo stesso test che oggi confronta cadenze e contratto
(`test_contratto_liveness_vs_deploy`) è il modello.

⚠️ **Un run del comando lanciato a mano mentre il timer sta girando**: il lock
di `fn_job_run_start` (dove il command lo usa) produce una riga di *skip* nel
giornale del comando, non due corse; il lavoro di coda esce `FATTO` con exit
`0`. Non è un caso da inventare: è ciò che succede oggi a chi lancia da shell.

### 2.4 Il verbo — `POST /api/v1/amm-software/processi/<codice>/esegui-ora/`

`amm_software/api/views.py::ProcessiEseguiOraView(AdminAPIView)` +
`ProcessiService.esegui_ora(codice, *, unit, scope)`. Nell'ordine:

1. `handle_post_json(..., require_idempotency_key=True)`; `unit` obbligatoria
   e stringa ⇒ altrimenti `E_VALIDATION_INPUT` con `fields: ["unit"]`;
2. il processo esiste (`E_PROCESSO_NON_TROVATO`, già a catalogo) **e** la unit
   è **fra le sue** sveglie (`sveglie_di_processo`) ⇒ altrimenti
   `E_VALIDATION_INPUT` con campo `unit`: il client non manda mai un comando,
   manda una unit che il backend risolve dal dichiarato (brief §2);
3. la **terna** dello scope è completa (`auth_user_id`, `username`,
   `identita_id`) ⇒ altrimenti **400 prima di accodare** con
   `E_CODA_SCOPE_OPERATORE_INVALIDO` — è lo stesso codice che il worker
   solleverebbe un minuto dopo (`operator_identity_context`), detto adesso a
   chi può fare qualcosa: un superuser Django senza identità `OPERATORE` non
   preme questo pulsante (brief §8.1, domanda 2);
4. `motivi_esegui_ora(sveglia, lavoro_vivo=…)` ⇒ primo motivo come
   `ServiceError` (422/409 dalla classe);
5. `CodaLavoriRepository().accoda(job_type=ESEGUI_PROCESSO, payload={processo_codice, unit},
   run_as=OPERATORE, scope, idempotency_key=chiave_idempotenza(unit), origine=API)`;
6. risposta `{"job_id", "stato": "PENDING", "unit"}` — la stessa forma del
   giro di fatturazione, che il drawer già sa leggere.

⚠️ Finché il tipo è `attivo = false`, il passo 5 risponde
`E_JOB_TYPE_NON_ATTIVO` (501, `NON_DISPONIBILE`): **è il cancello giusto**, e
l'endpoint non lo maschera. L'accensione la chiede il backend a handler in
servizio (§4.3).

**Lo scope** ha la stessa forma di `_accoda_job_fatturazione` — terna +
`emittente_attivo_id` + `emittente_ids` + `scope_key` — perché `scope_key` è il
token di **ownership** con cui *Strumenti → Code di lavoro* dice «è mio»: senza,
chi ha premuto non vedrebbe il proprio lavoro nella lista. È la seconda
occorrenza di quel blocco → §3.3.

### 2.5 La capability nel dettaglio — `GET processi/<codice>/` porta le sveglie

`ProcessiService.get_processo` aggiunge `sveglie: [...]`, una riga per unit
dichiarata per quel processo (zero, una o più), nella **famiglia 1** dei nomi
di `api.md` (quella coerente, dove motivo e chiave discendono dal flag):

```json
{
  "unit": "zeroerp-digest-presidi-settimanale", "forma": "timer",
  "comando": ["digest_presidi", "--cadenza", "settimanale"],
  "oncalendar": "Mon *-*-* 07:30", "abilita": true, "avvio_manuale": true,
  "nota": "…",
  "can_esegui_ora": false,
  "can_esegui_ora_reason": "E_PROCESSO_AVVIO_GIA_IN_CODA",
  "can_esegui_ora_reason_key": "amministrazione.processi.esegui_ora_blocco.gia_in_coda",
  "can_esegui_ora_dettaglio": {"job_id": 4321}
}
```

Il flag si **deriva** dal motivo (`reason is None`), mai calcolato a parte. Le
chiavi i18n seguono la forma già in uso per le check del DB
(`amministrazione.<risorsa>.<verbo>_blocco.<motivo>`); `dettaglio` porta i
parametri con nome per la frase (`{job_id}`), come pretende `bloccoMotivo.js`.

⭐ **Prima di dichiararla fatta si verifica che il client la LEGGA** (regola di
`api.md`): il test FE/BE di §5.5 pinna i tre nomi che il drawer legge sui tre
che il service emette.

### 2.6 Il pezzo FE — il tab «Sveglie» nel `ProcessoDrawer`

Quarto tab, `Sveglie (n)`, accanto ai tre esistenti (stessa scelta di forma:
elenco chiuso dal modello, consegnato col dettaglio, niente
`useDrawerTabLista`). Una riga per sveglia: unit · forma (Tag) · cadenza ·
`abilita` (Tag «attiva / spenta su questa installazione») · `comando` in
monospace · il pulsante.

* «Esegui ora» **solo su `forma = timer`** (sul servizio non compare: non è un
  candidato, non è uno stato); `disabled` da
  `bloccoAttivo(riga, 'can_esegui_ora', 'can_esegui_ora')`, tooltip da
  `motivoBloccoRiga(t, te, riga, 'can_esegui_ora')` — ⚠️ il tooltip su un
  bottone disabilitato va sull'**involucro** (`.app-action-tooltip-wrap`),
  non sul `Button`: un `<button disabled>` non emette eventi del mouse
  (catalogo FE, `useActionBar`);
* click ⇒ `useConfirmAction().confirmAction({ title, message, acceptLabel:
  «Esegui ora», onAccept })` — l'azione è `pericolosa = t` a catalogo (D-D) e
  la conferma è il minimo; il messaggio nomina unit e comando;
* dopo l'ok ⇒ toast *«lavoro #id accodato: parte alla prossima corsa del
  drenatore»* e **ricarica del dettaglio** (così la riga passa a «già in coda»
  e il pulsante si spegne da sé, senza stato locale);
* il run del comando comparirà nel tab «Ultimi run» **alla riapertura** del
  drawer, con `origine = COMMAND` e lo username: la colonna c'è già. Nessun
  polling in v1 — il gesto è asincrono per costruzione e la UI lo dice.

Chiavi i18n nuove sotto `amministrazione.processi.*` (tab, colonne, pulsante,
conferma, toast) e `amministrazione.processi.esegui_ora_blocco.*` (tre motivi).
`api/amministrazione.js` prende `eseguiOraProcesso(codice, unit)` con
`Idempotency-Key` generata, sul modello di `postIdentita`.

---

## 3. ✅ Le decisioni — confermate da Tid il 2026-09-15

### 3.1 ⛔ Cinque codici errore nuovi — richiesta al DB, che il brief non aveva

Ogni codice nominato in Python deve esistere in
`error_policies_generated.py`, che è **generato dal catalogo**
(`test_error_codes_declared_guardrail`, `genera_error_policies --check` in
CI). Quindi i rifiuti di §2.2–2.4 non si possono scrivere finché il DB non
semina i codici: è un prerequisito, e per la regola di casa si scrive e si
**aspetta** ([[feedback_be_fe_attende_prerequisiti_db]]).

| Codice | Classe | Chi lo solleva | Perché non si riusa niente |
| --- | --- | --- | --- |
| `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` | `NON_ESEGUIBILE` | predicato (capability, endpoint, handler) | «dichiarata non candidata» è una decisione di progetto; nessun codice a catalogo la nomina |
| `E_PROCESSO_SVEGLIA_NON_ABILITATA` | `NON_ESEGUIBILE` | idem | rimedio diverso dal precedente: qui il deploy **può** accenderla; due frasi, due chiavi |
| `E_PROCESSO_AVVIO_GIA_IN_CODA` | `CONFLITTO_STATO` | capability, endpoint | il lavoro esiste e sta lavorando: nessun campo da correggere, «rileggi lo stato» — il criterio del 409 |
| `E_PROCESSO_AVVIO_TROPPO_LUNGO` | `NON_ESEGUIBILE` | handler (finisce in `ultimo_errore`, non in un envelope) | un limite dichiarato dell'attrezzo, non un guasto: la strada è togliere la sveglia dai candidati |
| `E_PROCESSO_AVVIO_FALLITO` | `TECNICO` | handler | il comando è uscito ≠ 0: la diagnosi sta nel giornale **del comando**, e il messaggio manda lì |

Si riusano, perché la condizione è la stessa: `E_VALIDATION_INPUT` (payload
malformato / unit non di questo processo, con `campo = unit`),
`E_CODA_SCOPE_OPERATORE_INVALIDO` (terna incompleta — detta prima invece che
dopo), `E_CONFIG_MANCANTE` (`run-command.sh` assente), `E_PROCESSO_NON_TROVATO`,
`E_JOB_TYPE_NON_ATTIVO`. Lato BE, a seed avvenuto: `genera_error_policies` +
una frase senza segnaposto per ciascuno in `error_messages_fallback.py`
(`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`).

➡️ **Da scrivere come §9 del brief DB** («secondo giro»), con le cinque righe
sopra nella forma del CSV dei codici. ⚠️ Nel `VARIADIC` di TROPPO_LUNGO e
FALLITO entrano unit e tetto/exit code, mai un nome di parametro.

### 3.2 `avvio_manuale` come campo del dichiarato di deploy

La decisione 2a («solo comandi brevi: un comando lungo **non è candidato**, e
il pulsante non compare per lui») ha bisogno di una **sede** in cui «non
candidato» sia scritto. Oggi non c'è: `abilita = false` copre i due timer di
fatturazione **per coincidenza** — il giorno in cui `zeroerp-fatturazione-immediata`
si accende, il pulsante si accende con lui e un giro di fatturazione va in
`ERRORE` dopo cinque minuti tenendo fermo il drenatore. Il modello lo ammette
⇒ si progetta su quello, non sulle righe di oggi.

**Proposta:** `avvio_manuale: true|false` **obbligatorio** su ogni voce di
`sveglie.json`, per la stessa ragione di `abilita` («si dichiara, non si
omette: con un default il silenzio varrebbe qualcosa»). Valori al rilascio:
`false` sul drenatore (`zeroerp-coda-lavori`: «Esegui ora» dal drenatore, brief
§8.2.3), `false` sui due di fatturazione (lunghi per natura, con la nota),
`false` sul listener (è un servizio: non ha senso, ma il campo si scrive lo
stesso — una regola con un'eccezione sono due regole, come per `comando`),
`true` su digest ×2, `send-pending-emails`, `coda-stampa`.

⛔ **Non** una lista di esclusioni in Python: sarebbe la seconda sede della
whitelist, e resterebbe indietro alla prima sveglia nuova. ⚠️ `timeout_minuti`
resta fuori (§8.5: con un tetto unico non ha un lettore che lo distingua).
`install-timers.sh` **non** legge il campo — non è un fatto di systemd — e
`test-install-timers.sh` non cambia.

### 3.3 Regola del 2 — estrarre `scope_operatore_da_request(request)`

Il blocco «terna dal JWT + emittente attivo + emittenti + scope_key» di
`_accoda_job_fatturazione` va scritto una seconda volta per questo verbo.
Proposta: BB in `apps/core/services/coda_lavori/scope.py` (dove già sta
`scope_key_da_emittenti`, la fonte unica della chiave), con il guard sulla
`identita_id` risolta; `_accoda_job_fatturazione` passa a chiamarlo. Il
`ServiceError` sulla terna mancante resta nel BB con `E_CODA_SCOPE_OPERATORE_INVALIDO`
— ⚠️ oggi vendite usa `E_VALIDATION_INPUT` per la stessa condizione: allineare
è parte dell'estrazione, e va detto perché cambia un codice su un percorso vivo.

⏳ **Si dichiara e si aspetta l'ok** ([[feedback_regola_del_2_estrai_bb]]);
senza ok, il blocco si riscrive nel verbo e la seconda copia va **dichiarata**
nel commento come debito.

### 3.4 «Già in coda»: 409 dall'endpoint o silenzio della dedup?

Proposta (§2.2, motivo 3): **entrambi**, con ruoli diversi. La capability
spegne il pulsante e l'endpoint rifiuta con 409 su una schermata invecchiata;
`fn_accoda_lavoro` resta la rete per la corsa fra due click contemporanei (il
secondo trova il primo `PENDING`, stesso id). Un endpoint che assorbisse in
silenzio direbbe «accodato» a chi non ha accodato niente — la stessa ragione
del digest sui gruppi nella fatturazione mirata.

### 3.5 Il tetto: 300 secondi

Da confermare o cambiare: il numero sta in una costante sola, e il test lo
lega ai due limiti letti dal repo (§2.3). ⚠️ Con 300 s un giro lungo tiene
fermo il drenatore cinque minuti: è il costo dichiarato della (a), e si paga
solo su una sveglia dichiarata `avvio_manuale = true` che non doveva esserlo.

---

## 4. Ordine dei passi, con chi fa cosa

### 4.1 Prerequisiti (prima di aprire un file)

1. **Merge del lato DB**: `53d5ca923` (`origin/dev/db-tid`) → PR su Tito-dev
   → `git merge origin/Tito-dev` su `dev/backend-tid`. ⛔ Senza, la CI del BE
   ricostruisce il DB **senza** `ESEGUI_PROCESSO` e `test_nessun_handler_orfano`
   è rosso il giorno in cui l'handler si registra — il verso di ritiro che il
   DB ha nominato, esercitato al contrario. Sul dbdev il lavoro può partire
   subito (le righe ci sono).
2. **Richiesta DB dei cinque codici** (§3.1) — brief, §9. In attesa: i passi
   3-4 che non nominano codici nuovi.
3. Decisioni §3.2–3.5 di Tid.

### 4.2 Lavoro BE, in ordine di dipendenza

| # | Passo | File | Dipende da |
| --- | --- | --- | --- |
| 1 | `registered_job` legge `ZEROERP_JOB_ORIGINE` / `ZEROERP_JOB_AUTH_USER_ID` (fail-loud) | `core/services/job_run.py` + test | — |
| 2 | `avvio_manuale` nel dichiarato: `Sveglia.avvio_manuale`, validazione obbligatoria, otto voci del JSON, `RUN_COMMAND` accanto a `DEPLOY_DIR` | `core/services/sveglie.py`, `deploy/sveglie.json` + `test_sveglie.py` | §3.2 |
| 3 | Il predicato + costanti (`JOB_TYPE`, `HANDLER_CODE`, chiave, tetto) | `core/services/avvio_manuale.py` + test puri | §3.1 (i codici), 2 |
| 4 | `lavori_vivi_per_chiave` | `coda_lavori/repository.py` + test su DB provvisto | — |
| 5 | L'handler + registrazione in `ready()` | `coda_lavori/esegui_processo_handler.py`, `core/apps.py` + test con `subprocess.run` finto | 3, §3.1 |
| 6 | BB scope (o copia dichiarata) | `coda_lavori/scope.py`, `vendite/api/views.py` | §3.3 |
| 7 | Il verbo e la capability nel dettaglio | `processi_service.py`, `amm_software/api/views.py`, `urls_v1.py` | 3, 4, 6 |
| 7-bis | ✅ **fatto il 2026-09-15, per primo (decisione di Tid)**: `vuole_identita` nel dettaglio (§7.1), dalla **stessa** espressione SQL della lista (`_SQL_VUOLE_IDENTITA` + `_params_vuole_identita`, prima ricopiata inline nella sola lista) | `core/db/processi_repository.py` + `core/tests/db/test_processi_vuole_identita.py` (lista e dettaglio concordano su ogni processo; i tre casi del contratto per nome) | — |
| 8 | `genera_error_policies` + ripieghi | `error_policies_generated.py`, `error_messages_fallback.py` | seed DB |
| 9 | Test su DB provvisto: le tre righe del brief + accodamento reale in rollback | `core/tests/db/test_avvio_manuale_catalogo.py` | 4.1.1 |

### 4.3 Lavoro FE

| # | Passo | File |
| --- | --- | --- |
| 1 | `eseguiOraProcesso(codice, unit)` | `amministrazione/api/amministrazione.js` |
| 2 | Tab «Sveglie» con riga, conferma, toast, ricarica | `ProcessoDrawer.vue` |
| 2-bis | ✅ **fatto il 2026-09-15**: tolta la copia locale `vuoleIdentita`, il drawer legge `dettaglio.vuole_identita`; la frase `identita_non_serve` ora è vera anche per i processi di manutenzione (it/en) | `ProcessoDrawer.vue`, `locales/it.json`, `locales/en.json` |
| 3 | Chiavi i18n | `locales/it.json` (+ le altre lingue con il ripiego) |
| 4 | Presidio «il client legge la terna» | test §5.5 |

### 4.4 Chiusura

1. Handler in servizio (deploy sul backend di sviluppo, `kill -HUP` al master:
   gunicorn dev non ricarica da sé) → **richiesta al DB di `attivo = true`** su
   `ESEGUI_PROCESSO` dal CSV, come per `NOTIFICA_DIGEST_MUTO` l'11-09.
2. Collaudo in-app: «Esegui ora» su `zeroerp-digest-presidi-giornaliero`
   (finisce in secondi) — lavoro `FATTO` in *Code di lavoro*, run
   `digest_presidi:giornaliera` con `origine = COMMAND` e il mio username nel
   tab «Ultimi run», panorama `avvio_manuale | SU_RICHIESTA | f`.
3. Doc (§6) e brief in `work-done/`.

---

## 5. Test — ciascun difetto muto ha il suo presidio

| # | Test | Che cosa prova | Livello |
| --- | --- | --- | --- |
| 5.1 | `test_job_run_ambiente.py`: l'ambiente vince sugli argomenti; assente ⇒ argomenti; origine ignota o id non numerico ⇒ solleva | il run a mano non si scrive come timer | unit (`SimpleTestCase`, cursore mockato) |
| 5.2 | `test_sveglie.py`: `avvio_manuale` obbligatorio e bool; il drenatore è `false` (letto dal JSON, non ricopiato: il nome della unit del drenatore viene da `sveglie_di_processo(PROCESSO_DRAINA_CODA_LAVORI)`) | «Esegui ora» dal drenatore non può nascere da una dimenticanza | unit |
| 5.3 | `test_esegui_processo_handler.py` con `subprocess.run` finto: argv = `[run-command.sh, *comando]` senza shell; `env` porta le due variabili e NON tocca `os.environ`; exit 0 ⇒ result; exit ≠ 0 ⇒ `E_PROCESSO_AVVIO_FALLITO` terminale; `TimeoutExpired` ⇒ `E_PROCESSO_AVVIO_TROPPO_LUNGO` terminale; unit ignota / non candidata / spenta ⇒ terminale col codice del predicato; `run-command.sh` assente ⇒ `E_CONFIG_MANCANTE` | l'handler non lancia nulla fuori dal dichiarato e non ritenta mai | unit |
| 5.4 | `test_avvio_manuale_catalogo.py` (DB provvisto): le tre righe come le legge il BE (`coda_lavori_tipi.handler_code == HANDLER_CODE`, processo `MANUTENZIONE/CODA`, azione 35); `fn_accoda_lavoro` in transazione ritirata ⇒ a tipo spento `E_JOB_TYPE_NON_ATTIVO` (**dichiarato** con `skipTest` motivato finché il DB non accende), a tipo acceso l'id e la dedup sulla stessa chiave | la giuntura seed ↔ Python, che né pgTAP né unit vedono | DB provvisto |
| 5.5 | `test_processi_esegui_ora.py`: predicato (ordine dei motivi, `None` ⇒ ammesso); service (unit non del processo ⇒ 400 con campo; terna incompleta ⇒ 400 **prima** di `accoda`; motivo ⇒ 422/409 **prima** di `accoda`; ok ⇒ `accoda` chiamata con `job_type`, `run_as`, chiave, scope); view (`Idempotency-Key` obbligatoria, `AdminAPIView`); dettaglio: i tre nomi `can_esegui_ora*` emessi coincidono con quelli che `ProcessoDrawer.vue` legge (grep sul sorgente, come `test_liste_configurabili_seed` fa sui CSV) e le `reason_key` esistono in `locales/it.json` | il rifiuto sta prima dell'enqueue; la capability è letta | unit |
| 5.6 | `test_tetto_sottoprocesso.py`: `TETTO < STALE_MINUTI_DEFAULT*60` e `TETTO <= tolleranza(draina_coda_lavori)*60/2` letta da `processi.csv` | un comando al limite non fa dire `MUTO` al drenatore né `ERRORE` al reaper | unit, due file del repo |
| 5.7 | `test_nessun_handler_orfano` / `test_ogni_tipo_attivo_ha_un_handler` | esistono già: sono l'ordine DB (spento) → BE → DB (acceso) | DB provvisto |

⚠️ Cosa **non** prova nessun test automatico: che `run-command.sh` sotto il
drenatore di systemd trovi i segreti nell'ambiente. Lo prova il collaudo di
§4.4.2, ed è per questo che sta scritto lì e non qui.

---

## 6. Documentazione da toccare

* `docs/it/backend/core/manual/sveglie_processi.md` — il campo `avvio_manuale`,
  `RUN_COMMAND`, chi legge `comando` (ora c'è il consumer promesso a riga 74).
* `docs/it/backend/amm-software/manual/api_amm_software.md` §6 — il verbo
  `esegui-ora/` e le `sveglie` nel dettaglio con la terna.
* `docs/it/dev/api.md` — la riga di inventario Amm. Software + la famiglia 1
  delle capability guadagna un secondo esempio.
* `docs/it/dev/backend/catalogo-building-block-backend.md` — handler nella
  sezione «Coda lavori generica»; `avvio_manuale.py`; il BB scope se estratto.
* `docs/it/dev/backend/play-book-operativo-backend.md` §17.6 — `timeout_minuti`
  chiuso per decisione (tetto unico nell'handler), `avvio_manuale` accanto ad
  `abilita`; e una voce nuova: «come si vede a video un run lanciato a mano».
* `docs/it/dev/frontend/catalogo-building-block-frontend.md` — solo se il tab
  produce un pezzo riusabile (non previsto).
* Il brief: §9 «Risposta BE» con le decisioni prese qui, poi `work-done/`;
  l'analisi §9-bis punto 3 (nome vero `registered_job`, tetto fisso).

---

## 7. Visto facendo

1. 🔴 **`ProcessoDrawer.vue::vuoleIdentita`** legge `['PGAGENT', 'COMMAND']`:
   è una **seconda copia** nel client del mirror `_CANALI_CON_IDENTITA`, che il
   BE ha corretto il 05-09 aggiungendo `CODA_AUTOMATICA` — e che ha un test
   contro il DB; la copia FE non ce l'ha. Oggi il drawer di
   `chiusura_scadenze_daily` (`DOMINIO` / `CODA_AUTOMATICA`, riga 12 del seed)
   dice *«questo processo non vuole un utente tecnico»* e nasconde l'avviso
   delle aziende scoperte e il pulsante per crearne uno, proprio mentre ne usa
   uno per azienda — il difetto che non dà errore.
   ✅ **Entrato in questo cantiere e sistemato per primo (Tid, 2026-09-15)**,
   **togliendo la copia**, non aggiornandola
   ([[feedback_duplicazione_nasconde_il_bug]]): il dettaglio porta
   `vuole_identita` dalla stessa espressione della lista (passo 7-bis) e il
   drawer lo legge (passo FE 2-bis). Presidio: `test_processi_vuole_identita`
   (le due proiezioni non possono divergere; `chiusura_scadenze_daily` → sì,
   `FATTURAZIONE_GIRO` → no, `digest_presidi` → no, costruiti per nome). Il
   test di §5.5 pinnerà anche che il nome emesso sia quello letto dal drawer.
2. `_IDEMPOTENCY_HEADER_PARAM` esiste in `amm_software/api/views.py` e in
   `core/api/views_tracciamento.py`: il verbo nuovo riusa quello del proprio
   file, non fa la terza copia; l'estrazione resta un'occorrenza da dichiarare.
3. Il brief §8.6 lascia una domanda aperta e giusta: *non esiste un presidio
   «ogni azione di `config.azioni_processo` è valutata da almeno una view»*.
   `processo_avvia` sarà per scelta la prima riga decorativa. Un test AST che
   confronta i `post_permission`/`get_permission` del backend con il CSV delle
   azioni (con un registro delle decorative dichiarate) è piccolo e gira senza
   DB: cantiere suo, non questo.
