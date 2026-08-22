# Brief DB — `event_log`: la riga dice *chi*, *per chi*, *in che giro*

> **Cos'è.** Il **piano di sviluppo lato database** del **Passo 0** di
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md): rendere parlante la
> riga di `vendite.event_log` — perimetro emittente, `tx_id`, identità del giro,
> entità reale — e metterla sotto RLS, **prima** che esista qualunque endpoint.
>
> **Perché adesso e non dopo.** La tabella è append-only *per trigger*, e quel
> trigger vieta `UPDATE` **e** `DELETE`: sui campi della riga **non esiste nessun
> rimedio a posteriori**. Il lato lettura — policy, indici, endpoint, viste, UI —
> si aggiunge invece in qualunque momento senza ricostruire niente. È questa, e
> non la ripartizione DB/BE, la linea che decide cosa va per primo.
>
> **Origine.** Analisi del 2026-08-03, piano rivisto il 2026-08-22, stato
> **rimisurato sul DB e sul codice** lo stesso giorno (§0-ter dell'analisi).
> Decisioni di Tid del 2026-08-22, tutte in §2.
>
> **Stato:** ✅ **L1, L4, L2 e L5 APPLICATI E VERDI (2026-08-22).** Ventun changeSet,
> cinque CSV (L5 non ne apre di nuovi: appende ai due dei codici errore),
> **64 asserzioni pgTAP con zero skip**, baseline `vendite`+`rls` senza
> regressioni. ⭐ **La parte DB della fondamenta è posata**: §9.4 dichiarava L4
> come l'ultimo intervento strutturale su questo registro, e da qui in avanti la
> tabella si tocca solo **aggiungendo righe ai cataloghi**.
> ⭐ **L5 è la risposta a una richiesta del backend** (§5-bis): i changeSet 61 e 62
> avevano consegnato le **colonne**, e nessuna funzione le scriveva. Adesso le
> scrivono — ed è ciò che sblocca **BE-2** e **BE-3b**.
> 🔵 Resta **L3** (la vista, che si accende col Passo A) e le **consegne BE**
> del §5 — senza le quali il registro resta a **zero righe**, ed è il rischio 3
> del §9.3: l'unico che nessuna riga di documentazione può chiudere.
>
> **Correlati:**
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md) (il documento madre) ·
> [brief-db-rls-commesse.md](../work-done/brief-db-rls-commesse.md) (il cantiere
> gemello: 3 changeSet + 1 pgTAP) ·
> [brief-db-grant-batch-cleanup-note.md](../work-done/brief-db-grant-batch-cleanup-note.md)
> (il precedente del canale batch, che qui **non** si ripete) ·
> [linee-guida-sql.md](../../linee-guida-sql.md) §10 (RLS) — di cui questo brief
> propone una **precisazione**, §3.3 ·
> ⭐ [brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md) — **da esso
> questo brief ASSORBE T-1 e T-1b** (il catalogo dei tipi di entità), che di là
> non si gestiscono più: §4-bis. Tutto il resto di quel cantiere resta suo.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Regge, e non si riapre** | Il pattern RLS è in casa e collaudato (`rls_*_ef_whitelist` + `fn_scope_ef_whitelist`) · il dispatcher «di chi è questa riga» **esiste già** (`script.fn_resolve_emittente_fiscale_id`, 5 modi) · il canale batch è già coperto (`BYPASSRLS` + GRANT) | §1.1 |
| 🔴 **Cinque difetti, tutti dello stesso lato** | colonna di perimetro assente · `tx_id` assente · `correlation_id` identifica il **lotto**, non il giro · `entity_id = 0` · `actor` costante | §1.2 |
| ⛔ **Il vincolo che governa tutto** | Append-only per trigger: `UPDATE` **e** `DELETE` vietati ⇒ **nessun backfill, mai**. Unica via: `TRUNCATE` | §1.3 |
| ⛔ **Tre premesse dell'analisi cadute** | La RLS **morde già** (l'app non è owner) · il canale batch non è a rischio · B1 (il 67%) è chiuso | §1.4 |
| ✅ **Decisioni** | **D-1…D-18**, tutte applicate. D-1 e D-9 riviste in coda al rilievo sui lucchetti; **D-9 poi superata dalla D-17**, che assorbe il catalogo dei tipi dall'altro cantiere | §2 · §3.7 |
| 🧩 **Il disegno** | Derivazione nel trigger (la firma di `fn_log_event` **non cambia**) · policy a parità di famiglia · retention che convive con l'append-only · `vw_giornale_entita` | §3 |
| 📋 **Il piano** | **L1 · L4 · L2 · L5** ✅ **applicati e verdi** (21 changeSet) → resta **L3**, la vista cross-schema, che si accende col Passo A | §4 · §9.4 |
| 🔵 **A carico del BE** | 10 consegne, di cui **BE-1 è un difetto vero e vive già oggi** | §5 |
| ⭐ **La richiesta del backend** | I changeSet 61 e 62 avevano consegnato le **colonne**, e **nessuna funzione le scriveva**. L5 mette i due scrittori — e corregge una premessa della richiesta che era **falsa**, misurandola | §5-bis |
| 🧪 **Presidio** | ✅ **64 asserzioni verdi, zero skip** su 7 file — 4 nuovi/riscritti e 3 preesistenti adeguati. Un file previsto **non** è stato scritto: esisteva già | §6 |
| ✅ **Domande aperte** | **Zero.** Le sei del primo giro chiuse il 2026-08-22 | §8 |
| 🧱 **È una fondamenta?** | La risposta misurata, con l'elenco di cosa ci riporterebbe qui e i **due impegni verificabili**. ⭐ Le due volte in venti giorni sono lo **stesso difetto**: una colonna di testo che tutti scrivono e nessuno governa | §9 |
| ⭐ **Un solo documento** | Da qui in avanti chi lavora su `event_log` legge **questo** brief: T-1/T-1b di `brief-db-bersaglio-errore` sono **assorbiti** e di là non si gestiscono più | §4-bis |
| ⭐ **I due perni** | (1) «Chi» è **già nella riga** (`user_insert`): B3 non era vero — manca **il perimetro**, e serve perché `event_log` è **l'unico registro polimorfo**, l'unico senza una testata a cui ancorarsi. (2) **Un diario non si blocca mai**: rifiuta solo ciò di cui non sa dire di chi è | §3.2 · §3.3 |

---

## 1. La misura del terreno

Rimisurata il **2026-08-22** contro il database vivo, la doc auto-generata
`dbzero` e il codice BE. **Non** contro gli YAML.

### 1.1 Ciò che regge, e non si riapre

| Cosa | Verifica |
| --- | --- |
| **Il pattern RLS** | `rls_<tabella>_ef_whitelist`, `FOR ALL`, gate `app.ruolo_applicativo = 'OPERATORE'`, adapter `script.fn_scope_ef_whitelist(auth_user_id, emittente_fiscale_id)`. Applicato a 14 tabelle `vendite`. Il cantiere gemello (`commesse`) è stato **3 changeSet + 1 pgTAP** |
| **Il dispatcher del perimetro** | `script.fn_resolve_emittente_fiscale_id(p_modo, p_valore)` esiste già: `SECURITY DEFINER`, `search_path` bloccato, 5 modi (`fiscale`, `soggetto_ruolo`, `fattura`, `ente_incasso`, `contabile`), e un `ELSE` che **solleva** su un modo sconosciuto |
| **Il canale batch** | `zeroerp_batch_fatturazione` ha `BYPASSRLS` **e** i GRANT su tutte e 84 le tabelle `vendite` — su `event_log` `INSERT`+`SELECT` (`ar`). Il precedente `vendite.note` era un GRANT mancante: qui c'è |
| **L'indice della query forense** | `ix_event_log_entity_time (entity_type, entity_id, event_time DESC)` c'è già: la query del Passo A è quella per cui la tabella è stata indicizzata |
| **«Chi» è già nella riga** | `event_log.user_insert` è riempito dal trigger generico `script.trgfn_audit_data_user_generic` da `app.jwt_user`. In tabella: `tid`, `pochi`, `fara`, `BATCH_FATTURAZIONE` — **non** `zeroerp_app` |
| **Il registro polimorfo** | `config.sorgenti` esiste, ha `UNIQUE (codice_interno)`, `target_table` e `key_selector`, e già contiene `COMMESSA` e `FATTURA` |

### 1.2 I cinque difetti — tutti sul lato **scrittura**

| # | Difetto | Misura |
| --- | --- | --- |
| S1 | **Nessuna colonna di perimetro** | nessuna colonna emittente, nessuna policy, `relrowsecurity = f` |
| S2 | **`tx_id` non esiste** | è l'**unico** registro del progetto senza: ce l'hanno `dbops.error_log`, `audit_log`, `request_log`, `vendite.fatture_log`, `fatturazione_lotti_log`, `fatturazione_lotti_task_runs`, `commesse_attivita_log`, `documenti.documenti_generati_eventi`, `pratiche.giornale` |
| S3 | **`correlation_id` identifica il lotto, non il giro** | vale `fatturazione_lotti.lock_batch_id`, che nasce col lotto (`COALESCE(p_lock_batch_id, uuidv7())`) e **non cambia mai** — mentre il lotto 6260 ha **27 `task_runs`**. Duplica `entity_id`. E sul ramo push non è passato affatto |
| S4 | **`entity_id = 0`** su `PUSH_STARTED` | non è un segnaposto: è un id **che non esiste ancora**, perché la riga di `commesse_push_log` nasce a fine giro (`_run_locked`) |
| S5 | **`actor` costante** | `service:django` su 386 righe su 386; `source` vale `django` su 386 su 386. Due colonne per lo stesso mestiere, entrambe mute — mentre `user_insert` dice la verità |

E un difetto **già vivo oggi**, trovato misurando:

> ⛔ [`commesse_service.py:221`](../../../../backend/apps/vendite/services/commesse_service.py)
> scrive `severity="WARNING"`, ma `chk_event_log_severity` ammette solo
> `INFO | WARN | ERROR`. **`EMITTIBILITA_FALLITA` non è mai scrivibile**: solleva
> `23514` e — non essendo in `try` — fa saltare `pr_run_commesse_push` **proprio
> nel ramo in cui qualcosa era già andato storto**. In tabella: zero righe. Il
> test `test_pr_run_commesse_push_emittibilita_tipo_doc_mancante_osservabile`
> asserisce `severity == "WARNING"` **su un mock**, quindi blinda il valore rotto.
> È BE-1 in §5.

### 1.3 ⛔ Il vincolo che governa tutto

`vendite.trgfn_event_log_append_only` è `BEFORE UPDATE OR DELETE FOR EACH ROW` e
solleva **incondizionatamente**. Conseguenze, tutte verificate:

1. **Nessun backfill è possibile**, né oggi né mai: i cinque campi di §1.2 non si
   recuperano su una riga già scritta.
2. **Nessuna cancellazione selettiva**: l'unica via per svuotare la tabella è
   `TRUNCATE` — che non fa scattare i trigger di riga. Privilegio `D`: ce l'ha
   `titodb`, non `zeroerp_app`.
3. 🔴 **La retention standard non funziona.** `dbops.fn_apply_cleanup_at`
   valorizza `cleanup_at` con un **`UPDATE`**; `dbops.fn_purge_cleanup_expired`
   cancella con un **`DELETE`**. Entrambi vietati. E la regola `id 11` di
   `dbops.automation_rules_tbl` è `CLEANUP_AT` su **`*all` / `*all`** con
   `ttl_days: 30`: **basta aggiungere la colonna** perché il job settimanale
   inizi a fallire su questa tabella. Vedi §3.4.

> ⚠️ **Lo stesso conflitto è latente su `vendite.fatture_log` e
> `fatturazione_lotti_log`**, che hanno `script.trgfn_logs_guard_delete` (veto sul
> `DELETE` sbloccabile solo dalla GUC `zeroerp.maintenance_allow_delete_logs`) e
> **non hanno `cleanup_at`**. Il giorno in cui qualcuno gliela aggiunge, la regola
> `*all` prova a purgarle e trova il veto. **Registrato qui, non risolto qui.**

### 1.4 Tre premesse dell'analisi che non reggono

| Premessa | Realtà misurata |
| --- | --- |
| «l'owner applicativo bypassa la RLS, la protezione vera è il filtro del BE» | ⛔ **Falso.** Owner delle tabelle `vendite` = **`titodb`**; l'applicazione è `zeroerp_app`, **non** owner, **non** superuser, **senza** `BYPASSRLS`. La RLS morde già. Il caveat nasce da un commento sbagliato in `20260720-05` («l'owner (zeroerp_app)»); `20260730-05` dice la cosa giusta |
| «il canale batch potrebbe rompersi, come su `vendite.note`» | ✅ Non si ripete: `BYPASSRLS` + GRANT già presenti |
| «B3: l'audit non dice chi» | ⛔ **Falso.** `user_insert` lo dice già, da sempre (§1.1). Quello che manca è il **perimetro**, non l'identità |

---

## 2. Le decisioni — prese con Tid il 2026-08-22

| # | Decisione | Motivo |
| --- | --- | --- |
| **D-1** | ⭐ **`emittente_soggetto_ruolo_id` `NOT NULL`** *(rev. 2026-08-22, era `emittente_fiscale_id`)*, con policy `rls_event_log_ef_whitelist` (`FOR ALL`, adapter **SR** `fn_scope_ef_whitelist_via_sr`) e **`ENABLE` senza `FORCE`** | Il `FORCE` inciderebbe solo su `titodb` e **romperebbe** le `SECURITY DEFINER` di sua proprietà che leggono fuori dalla row security. Il filtro applicativo resta, come prescrive [api.md](../api.md). ⭐ **Perché SR e non PK:** è la colonna che usano già lotti, commesse, fatture, DDT, ordini, preventivi, contratti e resi; rende la derivazione una **copia** invece di una ricerca; e — decisivo — `anagrafiche.soggetti_ruoli` **non ha la colonna `attivo`**, quindi l'automazione non genera nessun lucchetto `require_attivo`. Vedi D-12 |
| **D-2** | L'emittente lo **deriva un trigger**, estendendo `script.fn_resolve_emittente_fiscale_id` coi modi `lotto` e `commessa` | Non si inventa un dispatch: si estende l'unico che il progetto ha. E il chiamante Python non deve fare una query in più per una cosa che il DB sa già (`fatturazione_lotti.emittente_soggetto_ruolo_id` è `NOT NULL`). ⭐ **Corollario: la firma di `fn_log_event` non cambia**, e si evita l'overload ambiguo |
| **D-3** | **Gli eventi senza padrone escono da `event_log`**: `PUSH_STARTED`/`PUSH_COMPLETED` restano nel loro registro di giro (`commesse_push_log`, creato **in testa**), `EMITTIBILITA_FALLITA` diventa **per commessa** | Con la colonna nullable e l'adapter standard, `fn_check_user_emittente_scope(user, NULL)` risponde **false** (regola 6; e prima ancora la regola 2 se `app.current_emittente_id` è settata): i due terzi delle righe attuali sarebbero **non scrivibili dal web e invisibili a tutti**. Così invece `event_log` resta uniformemente **per entità**: nessun NULL, nessun ramo speciale nella policy |
| **D-4** | ✅ **`TRUNCATE` autorizzato da Tid** | È l'unica via (§1.3), i dati sono di sviluppo e senza valore probatorio, e rende gratis il `NOT NULL` di D-1 |
| **D-5** | Si aggiunge **`tx_id`** | La timeline di un caso è cross-registro: senza, `event_log` non si aggancia a `error_log`. Il trigger lo attacca l'automazione |
| **D-6** | Si **eliminano `actor` e `source`** | Costanti e mute; «chi» è `user_insert`, che funziona anche sul canale batch (`app.jwt_user = 'BATCH_FATTURAZIONE'`). Siamo in `TRUNCATE`: togliere una colonna costa zero |
| **D-7** | `correlation_id` = **un `uuid` nuovo per giro**, generato dal runner, scritto **anche** su `fatturazione_lotti_task_runs` e `commesse_push_log` | Il `tx_id` non basta (un giro attraversa più transazioni, una per step) e il `task_run` è per-task. È il filo che cuce i registri nella vista di §3.6 |
| **D-8** | Retention **via (a)**: `cleanup_at` calcolato **all'INSERT**, più un'eccezione al veto sul solo `DELETE` di una riga **già scaduta** | Il volume è basso per costruzione (quattro righe per giro). Il partizionamento per `event_time` è stato **considerato e scartato**: complessità comprata su un rischio non misurato — vedi §7 |
| ~~**D-9**~~ | ~~`entity_type` con `CHECK (IN ('LOTTO','COMMESSA','FATTURA'))`~~ ⛔ **SUPERATA dalla D-17** *(2026-08-22, quinto giro)* — resta a registro perché il `CHECK` **è stato applicato** ed è ciò che la D-17 sostituisce. `entity_id` = **la PK `id` della tabella, sempre**: quella parte regge | La motivazione originale — «una FK a `config.sorgenti` genererebbe il lucchetto `require_attivo`, e permetterebbe di seedare un tipo che il trigger non sa risolvere» — era **giusta su `config.sorgenti`** e sbagliata come conclusione: il difetto stava in *quel* catalogo, non nell'idea di catalogo. Vedi D-17 |
| **D-17** | ⭐ **`entity_type` punta a un catalogo `config.tipi_entita`**, che porta il **modo di risoluzione dell'emittente**. Il vincolo diventa «un tipo del catalogo **che abbia un modo**» *(2026-08-22)* | ⭐ **Assorbe T-1/T-1b di [brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md)**, che decideva la stessa cosa sulla stessa colonna. Il catalogo nasce **senza `attivo`** (deprecazione con `obsoleto_dal`), quindi l'automazione non genera nessun lucchetto: l'obiezione (a) della D-9 cade. E portando il modo **nella stessa riga**, configurazione e trigger non possono più dissentire: l'obiezione (b) si risolve **meglio** del `CHECK`, perché aggiungere un tipo diventa **un seed** invece di tre modifiche coordinate. Disegno in §3.7 |
| **D-18** | ⭐ **Anche `domain` e `event_code` si governano** — con un catalogo `config.eventi_dominio`, ma ⛔ **senza FK**: il presidio è un **cancello di CI**, non un veto a runtime *(2026-08-22)* | Sono le **ultime due colonne di testo che nessuno governa** in questo registro, ed è la forma esatta del difetto che ci ha riportati qui due volte in venti giorni (§10). ⛔ Niente FK perché una scrittura rifiutata per un codice non ancora a catalogo **violerebbe la D-12**: il diario rifiuta solo ciò di cui non sa dire *di chi è*. Il codice ignoto entra, e a protestare è la **build** — è la stessa forma con cui il cantiere dei codici errore ha chiuso il proprio rubinetto. Disegno in §3.8 |
| **D-10** | **Nessun** `script.trgfn_guard_emittente_scope` su questa tabella | Se l'emittente lo deriva il DB dall'entità, il guard verificherebbe un valore appena calcolato dal DB stesso e direbbe la **stessa cosa** del `WITH CHECK` della policy, che sul canale web è già attivo (§1.4). Scritto qui perché il prossimo non lo aggiunga «per simmetria con DDT» |
| **D-11** | La vista **`vw_giornale_entita`** si **disegna qui** e si **implementa al Passo A** | È la vista a decidere se `event_log` deve reggere tutto da solo o solo la sua parte — e quella decisione cambia cosa scriviamo nella riga, che è l'unica cosa non rifacibile |
| **D-12** | ⭐ **Il diario non si blocca mai per lo stato di un padre.** Rifiuta una riga **solo** quando non riesce a dire *di chi è* | *Rilievo di Tid, 2026-08-22.* Un guard su un diario è autolesionista: il fatto è accaduto, e bloccare la riga distrugge l'unica prova che lo spiegherebbe. E l'anomalia temuta — attività nuova su un emittente disattivato — **è già bloccata a monte**, sui documenti (`ddt`, `ordini`, `preventivi`, `contratti`, `resi` hanno il lucchetto verso `emittenti_fiscali`): il lucchetto sul diario rifiuterebbe **solo righe legittime**, cioè la chiusura dei documenti di un emittente cessato. D-1 e D-9 sono i due modi in cui questa regola si realizza |
| **D-13** | `cleanup_at` = `event_time + 750 giorni` | *Tid, 2026-08-22.* La data si scrive nella riga e **non è più modificabile**: accorciare dopo vale solo per il nuovo, allungare dopo non salva niente. Sbagliare per eccesso è recuperabile, per difetto è definitivo — e 750 giorni coprono due chiusure annuali. I 30 giorni della regola `*all` coprivano solo il mese in corso |
| **D-14** | ➕ **`auth_user_id bigint`** accanto a `user_insert`, derivato da `app.current_user_id` | *Tid, 2026-08-22.* `user_insert` è lo **username**: un rename, o un nome riassegnato, e le righe vecchie indicano la persona sbagliata. Il numero interno no. Il nome resta (si legge senza cercare), il numero garantisce chi era davvero. È lato scrittura: adesso o mai. Stessa scelta del gemello `documenti.documenti_generati_eventi` |
| **D-15** | Un difetto del diario **non** fa fallire il lavoro, ma **non** sparisce: **fail-loud nel DB, best-effort nel BE** | *Tid, 2026-08-22.* Bloccare la fatturazione perché non si scrive l'appunto sulla fattura è assurdo; ingoiare in silenzio ricrea il difetto `EMITTIBILITA_FALLITA`, invisibile per mesi. Il DB rifiuta con un messaggio chiaro (si scopre **in test**), il BE lo avvolge nel telaio `_diagnostica_best_effort` che **lascia una riga nel log tecnico**. Quella riga è la differenza fra le due cose |
| **D-16** | La vista parte con **quattro** sorgenti: `event_log`, `fatturazione_lotti_log`, `fatturazione_lotti_task_runs`, `fatture_log` | *Tid, 2026-08-22.* `attivita_fatturabili_log` entra quando il suo padre avrà un filtro di perimetro: oggi sarebbe un buco nella vista. **Da scrivere a chiare lettere nella vista**, o fra sei mesi qualcuno lo aggiunge pensando sia una dimenticanza |

---

## 3. Il disegno

### 3.1 La tabella dopo

| Colonna | Tipo | Δ | Nota |
| --- | --- | --- | --- |
| `id` | `bigint` | = | PK |
| `event_time` | `timestamptz` | = | `DEFAULT now()` |
| ~~`domain`~~ | | ⛔ **rimossa con L4** | D-18, §3.8 — il dominio si legge dal catalogo |
| `entity_type` | `text` | **FK** *(rev. L4)* | ~~`CHECK IN ('LOTTO','COMMESSA','FATTURA')` (D-9)~~ → `fk_event_log_tipo_entita` → `config.tipi_entita(codice)`, `ON UPDATE CASCADE` (D-17). Il `CHECK` è stato tolto nello stesso changeSet **56** |
| `entity_id` | `bigint` | = | la PK `id` della tabella puntata, **sempre** |
| `event_code` | `text` | = | |
| `severity` | `text` | = | `CHECK (INFO/WARN/ERROR)` — invariato, ed è BE-1 ad adeguarsi |
| `correlation_id` | `uuid` | *(semantica)* | **l'id del giro**, non del lotto (D-7) |
| ~~`actor`~~ | | ⛔ **rimossa** | D-6 |
| ~~`source`~~ | | ⛔ **rimossa** | D-6 |
| `payload` | `jsonb` | = | |
| **`emittente_soggetto_ruolo_id`** | `bigint` | ➕ **NOT NULL** | FK → `anagrafiche.soggetti_ruoli(id)`, derivata (D-1, D-2) |
| **`auth_user_id`** | `bigint` | ➕ | da `app.current_user_id` (D-14). Nessuna FK: `django.auth_user` è fuori dal perimetro dei vincoli |
| **`tx_id`** | `uuid` | ➕ | D-5, trigger dall'automazione |
| **`cleanup_at`** | `timestamptz` | ➕ | `event_time + 750 giorni`, valorizzata **all'INSERT** (D-13) |
| `data_insert` / `user_insert` / `data_update` / `user_update` | | = | ⭐ `user_insert` è il **nome**; `auth_user_id` è **chi** |

### 3.2 La derivazione del perimetro — e l'unica cosa che il diario rifiuta

**La regola, in una frase** (D-12), e va scritta perché il prossimo sarà tentato
di «rafforzarla»:

> **Il diario rifiuta una riga solo quando non riesce a dire *di chi è*.
> Tutto il resto lo registra.**

In concreto:

| Situazione | Il diario |
| --- | --- |
| `entity_type` fuori vocabolario | ⛔ **rifiuta** — non c'è modo di ricavare il perimetro, ed è un errore di programmazione: si scopre in test |
| entità inesistente (`entity_id` che non trova niente) | ⛔ **rifiuta** — stessa ragione |
| entità reale, ma **emittente disattivato** | ✅ **registra** — il perimetro si ricava benissimo, e quella riga è **proprio** quella che serve: un emittente cessato ha ancora note di credito, incassi e stampe da chiudere |
| entità reale, ma **documento annullato** | ✅ **registra** — «qualcuno ha agito su un documento annullato» è un fatto da conservare, non da nascondere. Se quell'azione non deve essere permessa, la si blocca **sul documento**, non sul suo diario |

⭐ **Perché un lucchetto sul diario sarebbe autolesionista.** Il fatto è già
accaduto: rifiutare la riga distrugge l'unica prova che lo spiegherebbe. E
l'anomalia che verrebbe da temere — attività *nuova* su un emittente disattivato
— **è già bloccata a monte**: `vendite.ddt`, `ordini`, `preventivi`, `contratti`
e `resi` hanno il lucchetto `require_attivo` verso `anagrafiche.emittenti_fiscali`
(verificato: 7 tabelle). Quindi un lucchetto sul diario rifiuterebbe **solo righe
legittime**.
⚠️ E non si segnala l'anomalia sulla riga: un avviso che scatta sul caso
**normale** — la chiusura dei documenti di un emittente cessato — diventa rumore,
e un presidio che tutti ignorano è peggio di uno che non c'è. Il posto di quel
presidio è sul documento, ed è materia di
[analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md).

**Come si realizza, senza combattere con l'automazione.** Il lucchetto
`require_attivo` lo genera `dbops.fn_run_automations_attivo`, che gira su
`*all`/`*all` e **non ha esclusioni per tabella figlia** (l'unico override,
`dbops.automation_overrides_cols` con `col_role = 'ATTIVO_COL'`, è per tabella
**padre**, e varrebbe per tutte le 18 tabelle che puntano a `config.sorgenti`).
Quindi non si disattiva: **si evita di crearlo**, e le due decisioni D-1 e D-9
sono esattamente questo.

| Scelta | Effetto |
| --- | --- |
| `emittente_soggetto_ruolo_id` invece di `emittente_fiscale_id` | `anagrafiche.soggetti_ruoli` **non ha la colonna `attivo`** ⇒ l'automazione salta (`ATTIVO_SKIP_PARENT_NO_ATTIVO`). Verificato: **zero** trigger `*_soggetti_ruoli_require_attivo_*` in tutto il database |
| `CHECK` invece della FK a `config.sorgenti` | Nessuna FK, nessun lucchetto. E il vocabolario resta **nello stesso changeSet** del dispatch che lo risolve |

**L'oggetto nuovo: `script.fn_resolve_emittente_sr_id(p_modo, p_valore)`**

Gemello sull'altra convenzione di `fn_resolve_emittente_fiscale_id` — ed è il
pattern di casa, non una duplicazione: il progetto tiene già le coppie
`fn_scope_ef_whitelist` / `..._via_sr` e `fn_get_emittenti_scope_pk_ids` /
`_sr_ids` (decisione `refactor-emittente-id-canonico`, 2026-05-02: *il doppio
binario è corretto e va supportato*).

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_emittente_sr_id(
    p_modo   text,
    p_valore bigint
) RETURNS bigint
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_sr_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- ⭐ SECURITY DEFINER per la stessa ragione del gemello: lotti, commesse e
    --    fatture hanno la ROW SECURITY accesa. Letta da un utente fuori
    --    perimetro la riga NON C'E', e il chiamante non deve poter confondere
    --    «non lo vedo» con «non esiste».
    IF p_valore IS NULL THEN RETURN NULL; END IF;

    IF p_modo = 'lotto' THEN
        SELECT l.emittente_soggetto_ruolo_id INTO v_sr_id
          FROM vendite.fatturazione_lotti l WHERE l.id = p_valore;
    ELSIF p_modo = 'commessa' THEN
        SELECT c.emittente_soggetto_ruolo_id INTO v_sr_id
          FROM vendite.commesse c WHERE c.id = p_valore;
    ELSIF p_modo = 'fattura' THEN
        SELECT f.emittente_soggetto_ruolo_id INTO v_sr_id
          FROM vendite.fatture f WHERE f.id = p_valore;
    ELSE
        -- ⛔ Non si restituisce NULL: spegnerebbe il chiamante in silenzio.
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_resolve_emittente_sr_id',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('modo', p_modo, 'valore', p_valore),
            NULL::uuid,
            format('il modo di risoluzione «%s» non esiste: '
                   'sono ammessi lotto, commessa e fattura', p_modo));
    END IF;

    RETURN v_sr_id;
END
$function$;
```

⭐ È una **copia**, non una ricerca: le tre tabelle portano già la colonna SR.
Nessun `JOIN` a `emittenti_fiscali`, e `fn_resolve_emittente_fiscale_id` **non
va toccata**.

**Il trigger: `vendite.trgfn_event_log_deriva_scope`** — `BEFORE INSERT`

> ⚠️ **Il blocco qui sotto è il disegno del L1, e il L4 lo ha superato**
> *(allineamento 2026-08-22)*: il `CASE` scritto a mano **non c'è più** — il
> trigger legge `modo_risoluzione_emittente` **dal catalogo** (changeSet **58**,
> D-17). Il testo resta perché spiega *perché* la mappa stava lì, ed è la
> ragione per cui portarla nel catalogo è stato un guadagno e non un giro.

```sql
v_modo := CASE NEW.entity_type
              WHEN 'LOTTO'    THEN 'lotto'
              WHEN 'COMMESSA' THEN 'commessa'
              WHEN 'FATTURA'  THEN 'fattura'
          END;   -- il CHECK garantisce che una delle tre ci sia

NEW.emittente_soggetto_ruolo_id :=
    script.fn_resolve_emittente_sr_id(v_modo, NEW.entity_id);

IF NEW.emittente_soggetto_ruolo_id IS NULL THEN
  PERFORM script.fn_log_and_raise_error(
    'vendite', 'trgfn_event_log_deriva_scope', 'E_EVENT_LOG_SCOPE_NON_RISOLTO',
    jsonb_build_object('entity_type', NEW.entity_type, 'entity_id', NEW.entity_id),
    NEW.tx_id,
    format('l''evento su %s %s non si lega a nessun emittente: '
           'il giornale non accetta righe senza perimetro',
           NEW.entity_type, NEW.entity_id));
END IF;

-- Identità e scadenza, nello stesso passaggio.
NEW.auth_user_id := NULLIF(current_setting('app.current_user_id', true), '')::bigint;
NEW.cleanup_at   := COALESCE(NEW.event_time, now()) + make_interval(days => v_ttl_days);
```

⚠️ Note che valgono più del codice:

- **La mappa `entity_type` → modo sta nel trigger**, accanto al `CHECK` che
  definisce il vocabolario: sono la stessa decisione e cambiano insieme.
- **Il messaggio nomina il tipo e l'id, non un parametro PL/pgSQL.** Il codice è
  `TECNICO` (500): lo produce solo un chiamante rotto, e su un `TECNICO` la
  chiave `campo` **non** entra nel contesto.
- `v_ttl_days` si legge da `dbops.automation_rules_tbl` (§3.4), non da una
  costante: una sede sola.
- `%TYPE` su tutte le variabili che riflettono colonne.

### 3.3 La policy — e una precisazione da fare a `linee-guida-sql` §10.1

Mirror **esatto** di `rls_commesse_ef_whitelist` (`20260720-05`), che è la
gemella più vicina: stessa convenzione SR, stesso adapter.

```sql
CREATE POLICY rls_event_log_ef_whitelist ON vendite.event_log
    AS PERMISSIVE
    FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_sr(
                NULLIF(current_setting('app.current_user_id', true), '')::integer,
                emittente_soggetto_ruolo_id)
    )
    WITH CHECK ( ...la stessa condizione... );

ALTER TABLE vendite.event_log ENABLE ROW LEVEL SECURITY;   -- NO FORCE
```

⛔ **Ma `linee-guida-sql` §10.1 dice testualmente di NON abilitare la RLS su
«tabelle di sola scrittura tecnica (`dbops.*`, log, storico già filtrato a
monte)».** Va affrontato, non aggirato.

La ragione della regola è nell'ultima clausola: **«già filtrato a monte»**. È il
modello reale del progetto — 70 tabelle `vendite` su 84 non hanno RLS, e i
satelliti sono protetti dall'**ancoraggio della query alla testata**:
`fatture_log` si legge sempre via `fatture` o `fatturazione_lotti`, entrambe con
policy; `documenti.documenti_generati_eventi` — il gemello append-only meglio
riuscito — è satellite di `documenti_generati` e infatti **non ha RLS**.

`event_log` è **l'unico registro polimorfo**: non ha una testata a cui ancorarsi,
quindi **non può ereditare la protezione per join**. La precondizione della regola
è falsa, e per questo l'eccezione non si applica.

➡️ **Si chiede di aggiungere a §10.1 la precisazione**, perché generalizza: *un
registro **polimorfo** non è «filtrato a monte» — non ha un monte. Se raccoglie
righe di più emittenti, la colonna di perimetro ce l'ha lui o non ce l'ha
nessuno.*

⚠️ Sulla forma `FOR ALL`: §10.2 la sconsiglia «quando servono semantiche diverse
fra `SELECT` e scrittura». Qui la semantica è **la stessa**, e una `FOR SELECT`
sarebbe attivamente sbagliata — è la trappola già registrata: *una policy
`FOR SELECT` è deny-all in scrittura, e `INSERT ... RETURNING` passa comunque
dalla `USING`.*

### 3.4 La retention, senza litigare con l'append-only

Tre pezzi, e vanno **insieme** o il job settimanale si rompe (§1.3).

1. **`cleanup_at` valorizzata all'INSERT** dal trigger di §3.2, leggendo il TTL
   **dalla stessa sorgente che usa l'automazione** — `dbops.automation_rules_tbl`,
   regola `CLEANUP_AT` più specifica per `vendite`/`event_log`, con fallback alla
   `*all`. Una sola sede: se domani il termine cambia, cambia in un posto e vale
   per entrambi.
   ⭐ **Effetto collaterale desiderato:** con `apply_on_update: false` la regola
   `*all` costruisce `UPDATE ... WHERE cleanup_at IS NULL`. Se nessuna riga ha
   `cleanup_at` nullo, l'`UPDATE` **non tocca nessuna riga**, nessun trigger di
   riga scatta, e il conflitto sparisce da solo.
   ⭐ **E il veto sull'`UPDATE` diventa una garanzia**: la data di scadenza, una
   volta scritta, **non è più modificabile da nessuno**.

2. **Revisione di `trgfn_event_log_append_only`**, che oggi solleva un
   `RAISE EXCEPTION` nudo, senza codice registrato:

   | Operazione | Prima | Dopo |
   | --- | --- | --- |
   | `UPDATE` | eccezione senza codice | **codice registrato** |
   | `DELETE` di riga **non** scaduta | eccezione senza codice | `E_DELETE_NOT_ALLOWED` (già a catalogo) |
   | `DELETE` di riga **scaduta** (`cleanup_at <= now()`) | ⛔ vietato | ✅ **ammesso** |
   | `DELETE` con GUC `zeroerp.maintenance_allow_delete_logs` | ⛔ vietato | ✅ ammesso, **a parità** con `script.trgfn_logs_guard_delete` dei log gemelli |

   ⭐ **Il criterio non è *chi* cancella, ma *cosa*.** Niente GUC da propagare,
   niente ruolo da riconoscere: `fn_purge_cleanup_expired` funziona così com'è,
   senza toccare una funzione condivisa di `dbops` per un bisogno di `vendite`.
   La regola in una frase: *append-only vuol dire che non puoi **alterare** né
   **cancellare la storia**; non vuol dire che non puoi **ritirare ciò che ha
   passato la sua scadenza**.*

3. **Seed della regola `CLEANUP_AT`** per `vendite`/`event_log` con
   **`ttl_days: 750`** (D-13), così il registro non eredita in silenzio i **30
   giorni** della regola `*all`.

### 3.5 L'ordine dei `BEFORE ROW`

Con D-1 e D-9 le due FK «pericolose» non nascono, quindi la tabella resta con
pochi trigger e in ordine alfabetico:

```
trg_event_log_a10_deriva_scope_ins        <-- il nostro
trg_event_log_append_only_ud              (solo UPDATE/DELETE: non concorre)
trg_event_log_audit_data_user_upd
trg_event_log_gen_tx_id_ins_upd
```

⏱️ **Verifica del 2026-08-22, dopo l'apply**: in tabella i trigger sono **tre** —
`trg_event_log_a10_deriva_scope_ins`, `trg_event_log_append_only_ud`,
`trg_event_log_audit_data_user_upd`. ⚠️ **`trg_event_log_gen_tx_id_ins_upd` non
c'è ancora**, e non è un difetto: la colonna `tx_id` è nata oggi e i trigger
delle automazioni li genera il passaggio `ci_apply`, che sul migrate manuale non
gira — ci pensa il pgagent alle 21:00. **Da riverificare domani**: finché non
c'è, `tx_id` resta NULL su ogni riga scritta.

⚠️ **Resta comunque una regola da scrivere**: se un domani qualcuno aggiunge una
FK verso una tabella con `attivo`, l'automazione genererà
`trg_event_log_a10_<padre>_require_attivo_ins_upd`, e i `BEFORE ROW` scattano in
**ordine alfabetico**. `deriva` deve continuare a stare prima, o il lucchetto
troverebbe un `NULL` e si spegnerebbe da solo. **Il nome del trigger è
load-bearing**: rinominarlo `..._a10_scope_deriva_ins` lo manderebbe dopo la `s`
di `sorgenti`, e il difetto non si vedrebbe finché non si disattiva qualcosa.

### 3.6 `script.vw_giornale_entita` — il disegno (si implementa al Passo A)

**Il problema che risolve.** Una timeline letta dal solo `event_log` mostra
**quattro** codici per lotto (`PIPELINE_STARTED`, `STEP_COMPLETED`,
`PIPELINE_COMPLETED`, `PIPELINE_ERROR`). Il resto della storia di quel lotto sta
altrove: 426 righe in `fatturazione_lotti_log`, 194 in
`fatturazione_lotti_task_runs`, i log per fattura.

#### ⭐ Vive in `script`, e nasce **cross-schema** anche se parte da `vendite`

*(rev. 2026-08-22 — §10, rischio 2.)* La prima stesura la metteva in `vendite`.
Sarebbe stato il seme della terza ristrutturazione: misurato, i registri di
eventi del progetto sono **sei**, non uno —

```
vendite.event_log                     pratiche.giornale
vendite.fatture_sdi_eventi            documenti.documenti_generati_eventi
magazzino.eventi_assets               + i log funzionali di vendite
```

— e la domanda «cosa è successo a **questa** pratica / a **questo** documento»
arriverà. Se la vista nascesse come union di sole tabelle `vendite`, a doversi
rifare non sarebbe il registro: **sarebbe la vista**, cioè la cosa che tutti
avranno già in mano.

Costa zero deciderlo adesso, e sono tre scelte:

1. **vive in `script`**, che è la sede delle viste applicative riusabili — non in
   `vendite`, che è uno dei domini che vi si affacciano;
2. **l'asse delle entità è `config.tipi_entita`** (§3.7), non un elenco locale:
   è ciò che permette a un ramo `pratiche` di entrare senza toccare le colonne;
3. **la forma normalizzata è quella e non cambia** quando arrivano rami nuovi:
   un registro che non sa riempirla lascia `NULL`, non allarga la vista.

**La forma normalizzata** — sette colonne, e nient'altro:

| Colonna | Da dove |
| --- | --- |
| `quando` | `event_time` · `data_ora` · `started_at` |
| `entity_type` / `entity_id` | nativo su `event_log`; il padre sugli altri |
| `gravita` | `INFO/WARN/ERROR` — le sorgenti in `C/W/I` si mappano **una volta qui** |
| `cosa` | `event_code` · `messaggio` · `task_code` + `task_stato` |
| `tx_id` | nativo ovunque tranne `commesse_push_log` (L2 gliela aggiunge) |
| `correlation_id` | il giro (D-7) |
| `chi` | `auth_user_id` + `user_insert` |

**Le quattro sorgenti del primo giro** (D-16): `event_log`,
`fatturazione_lotti_log`, `fatturazione_lotti_task_runs`, `fatture_log`.
⭐ **Quattro rami, ma la forma è già quella dei sei**: `pratiche.giornale` e
`documenti.documenti_generati_eventi` entrano aggiungendo un `UNION ALL`, non
rinegoziando le colonne. È tutta la differenza fra allargare e rifare.

⛔ **`attivita_fatturabili_log` resta fuori, e va scritto nella vista**: né lui né
`vendite.attivita_fatturabili` hanno un filtro di perimetro, quindi quel ramo
mostrerebbe righe di altri emittenti. Entra quando il padre avrà la sua policy —
non prima, e non «per simmetria».

**Perché non si unificano le tabelle.** La specificità serve e non è ridondanza:
`disabilitato` è «chi accende il segnale lo spegne», `fase` e
`stato_doc_fiscale_id` sono del lotto. La vista normalizza la **lettura**, non la
scrittura — nessun trigger che ricopia, nessuna logica in due posti.

**Come si protegge.** `security_invoker`, e ogni ramo si ancora alla propria
testata protetta: `fatture_log` → `fatture`, `fatturazione_lotti_log` e
`task_runs` → `fatturazione_lotti`, tutte con policy. Il ramo `event_log` si
protegge da sé, sulla colonna nuova — **che è esattamente il motivo per cui quella
colonna esiste**.

**E `error_log` non entra nella vista**: non ha un'entità, solo `tx_id` e un
`context` jsonb. Ci si arriva **per `tx_id`**, come approfondimento di una riga —
ed è la ragione concreta per cui D-5 non era rinviabile.

---

### 3.7 `config.tipi_entita` — il catalogo dei tipi *(D-17, assorbito da `brief-db-bersaglio-errore`)*

> ⭐ **Questa sezione arriva da un altro cantiere.** `brief-db-bersaglio-errore`
> aveva deciso, lo stesso giorno, che `event_log.entity_type` dovesse adottare un
> catalogo chiuso (i suoi passi **T-1** e **T-1b**). Decideva sulla **nostra**
> colonna, e noi avevamo già applicato la scelta opposta. La materia è stata
> portata **qui**, dove vive l'oggetto; di là resta una dipendenza. Vedi §4-bis.

**Perché il catalogo è meglio del `CHECK` che abbiamo applicato.** Non per
uniformità: perché il `CASE` scritto a mano nel trigger di derivazione diventa
**inutile**.

Oggi aggiungere un tipo di entità al giornale costa **tre modifiche coordinate**
— il `CHECK` sulla colonna, il ramo nel `CASE` di
`trgfn_event_log_deriva_scope`, il modo in `script.fn_resolve_emittente_sr_id` —
e se una delle tre resta indietro il difetto è muto. Col catalogo costa **un
seed**, perché il modo sta nella stessa riga del tipo: **configurazione e trigger
non possono dissentire, sono lo stesso dato**.

| Colonna | Perché |
| --- | --- |
| `codice` | la chiave stabile, quella che finisce in `entity_type` e nel bersaglio di un errore |
| `etichetta_key` | chiave i18n: il nome lo scrive il frontend, non il database |
| `modo_risoluzione_emittente` | **nullable** — è la colonna che distingue le due letture (sotto) e che il trigger legge al posto del `CASE` |
| `obsoleto_dal` | ⛔ **e NON `attivo`** — vedi sotto: è la ragione per cui questo catalogo si può usare e `config.sorgenti` no |

```
codice     obsoleto_dal  modo_risoluzione_emittente
LOTTO      NULL          'lotto'      ← giornalabile: l'emittente si deriva
COMMESSA   NULL          'commessa'   ←
FATTURA    NULL          'fattura'    ←
TASK_RUN   NULL           NULL        ← puntabile da un errore, NON giornalabile
SOGGETTO   NULL           NULL        ←
```

#### ⭐ Due letture dello stesso catalogo, e perché una sola non basterebbe

È la scoperta che ha reso possibile l'unificazione: **i due vocabolari non sono
lo stesso insieme.**

| Lettura | Chi | Selezionata da | Contiene |
| --- | --- | --- | --- |
| **Giornale** | `event_log.entity_type` | *l'emittente dev'essere **derivabile** dall'entità* | solo i tipi con `modo_risoluzione_emittente NOT NULL` |
| **Bersaglio** | il `target` di un errore, e le rotte della timeline | *il frontend ha una **rotta** per arrivarci* | **tutto** il catalogo |

Il giornale è un **sottoinsieme proprio** del bersaglio. È esattamente perché
`TASK_RUN` non ha un padrone che la D-3 l'ha espulso da `event_log` — ma un
errore può benissimo puntare a un task run, ed è metà del caso d'uso del
bersaglio. Un catalogo tagliato sui soli tipi del giornale renderebbe il
bersaglio inutilizzabile; due cataloghi separati sarebbero la stessa nozione
governata in due modi.

⚠️ **Il vincolo su `event_log` non è quindi «esiste nel catalogo»**, ma «esiste
nel catalogo **e ha un modo**». Un `TASK_RUN` scritto nel giornale resta
rifiutato, come oggi — e con lo stesso messaggio.

#### ⛔ Senza `attivo`, ed è la condizione che rende tutto possibile

L'obiezione originale della D-9 era corretta: una FK verso un catalogo con la
colonna `attivo` fa generare da `dbops.fn_run_automations_attivo` il lucchetto
`trg_event_log_a10_<padre>_require_attivo_ins_upd`, e **il diario tornerebbe a
poter smettere di scrivere** perché qualcuno ha disattivato una voce di elenco.
È la D-12, che è il perno di questo cantiere.

Il difetto però stava in **quel** catalogo, non nell'idea di catalogo. Un
catalogo nuovo che deprechi con **`obsoleto_dal`** — che è già la regola di casa
per i cataloghi, non un'invenzione — l'automazione lo **salta**
(`ATTIVO_SKIP_PARENT_NO_ATTIVO`), e il lucchetto non nasce.

📌 Verificato che il meccanismo è quello: `anagrafiche.soggetti_ruoli` non ha
`attivo`, ed è per questo che la FK dell'emittente (D-1) non ha generato nessun
guard. **Zero** trigger `*_soggetti_ruoli_require_attivo_*` in tutto il database.

⚠️ **Da presidiare**: il giorno che qualcuno aggiunge `attivo` a
`config.tipi_entita`, il lucchetto nasce da solo alle 21:00 e nessuno lo collega
al diario che smette di scrivere. Il test `test-event-log-deriva-scope`
asserisce già l'**assenza** di lucchetti su `event_log`: diventerà rosso, ed è il
motivo per cui quel test esiste.

#### ⚠️ E `config.sorgenti`? La sovrapposizione si dichiara, non si linka

`config.sorgenti` **è già** un registro polimorfo: 15 righe, con `target_table` e
`key_selector`, usato dal grafo di lineage e dal push. Contiene `COMMESSA`,
`FATTURA`, `DDT_VENDITA`, `ORDINE_VENDITA`, `PREVENTIVO`… ma **non** `LOTTO`,
**non** `TASK_RUN`. Nessuno dei due insiemi contiene l'altro.

Due registri di «tipi di entità polimorfa» è una cosa da guardare in faccia, non
da lasciar succedere. Le tre vie, e perché **non** si estende `sorgenti`:

| | Via | Esito |
| --- | --- | --- |
| A | Estendere `config.sorgenti` | ⛔ **ha `attivo`**: la FK rigenererebbe il lucchetto. È il difetto della D-9, per la porta di servizio |
| **B** | Catalogo nuovo, sovrapposizione **dichiarata** | ✅ *scelta di Tid, 2026-08-22* |
| C | Catalogo nuovo con FK a `sorgenti` dove il tipo è anche sorgente | ⛔ rimette il lucchetto, un salto più in là |

⚠️ **E una regola operativa che discende dalla convivenza, misurata il
2026-08-22:** dove un codice esiste in **entrambi** i cataloghi, **deve essere
scritto identico**. Oggi coincidono `COMMESSA` e `FATTURA`; `LOTTO` e `TASK_RUN`
esistono solo qui. Il giorno che si seminasse `DDT` dove `config.sorgenti` dice
`DDT_VENDITA`, la «sovrapposizione dichiarata» diventerebbe **la stessa cosa
chiamata in due modi** — che è peggio di due cataloghi separati, perché nessuno
dei due sembrerebbe sbagliato.

⭐ **La ragione che regge, e che va lasciata scritta perché il prossimo non
«semplifichi»:** rispondono a **due domande diverse**. `config.sorgenti` dice
*«da dove nasce questo documento»* — è il lineage e il push, e per questo porta
la chiave `id`-vs-`uid`. `config.tipi_entita` dice *«che cosa è questa entità»* —
è il perimetro e il bersaglio. Vocabolari che si intersecano, domande che no.
Unirli significherebbe far dipendere il diario dalla disattivazione di una
sorgente di lineage.

---

### 3.8 `domain` e `event_code` — le ultime due colonne non governate *(D-18)*

**Misurato il 2026-08-22**, sulle colonne di testo di `vendite.event_log`:

| Colonna | Governata? |
| --- | --- |
| `severity` | ✅ `CHECK` |
| `entity_type` | ✅ `CHECK` → catalogo con **L4** |
| **`domain`** | ⛔ **niente** |
| **`event_code`** | ⛔ **niente** |

⚠️ Sono la forma **esatta** del difetto che ha già prodotto due interventi in
venti giorni (§10). E `event_code` è **l'asse su cui il Passo B raggruppa**:
chiederà un catalogo, e lo chiederà quando ci saranno dentro i dati — cioè
quando costa.

📌 Il progetto sa già farlo: `config.tipi_evento_assets` è il catalogo dei tipi
evento del magazzino. Non è un'invenzione.

#### Un catalogo solo, perché `domain` è una denormalizzazione di `event_code`

`PIPELINE_STARTED` appartiene a `PIPELINE`, `EMITTIBILITA_FALLITA` a `COMMESSE`:
il dominio è **una proprietà del codice**, non un secondo asse indipendente. Un
codice che appartenesse a due domini vorrebbe dire due cose — che è il difetto
contro cui il cantiere dei codici errore ha combattuto.

```
config.eventi_dominio(codice PK, dominio, etichetta_key, obsoleto_dal)
   PIPELINE_STARTED     PIPELINE
   STEP_COMPLETED       PIPELINE
   PIPELINE_COMPLETED   PIPELINE
   PIPELINE_ERROR       PIPELINE
   EMITTIBILITA_FALLITA COMMESSE
```

⚠️ `dominio` resta **testo governato dal catalogo**, non una seconda tabella: i
domini sono cinque parole e una tabella di cinque parole con una FK sopra è
cerimonia, non governo. Se un giorno servisse un'anagrafica dei domini — con
etichette, permessi, colori — nascerà allora, e il catalogo la referenzierà.

➡️ ⛔ **`event_log.domain` si TOGLIE**, e con lui il parametro `p_domain` di
`fn_log_event`.

⚠️ **Prima stesura di questa sezione: «la colonna non si toglie, perché
`ix_event_log_domain_time` la usa e `fn_list_lotto_segnalazioni` filtra su di
essa». Era una scelta guidata dai dati e dall'esistente, ed era sbagliata**
(rilievo di Tid, 2026-08-22: *«non abbiamo produzione, decidiamo sempre la cosa
migliore»*). Verificato:

* il filtro in `fn_list_lotto_segnalazioni` è **ridondante** — la query filtra
  già `event_code = 'PIPELINE_STARTED'`, e un codice appartiene a un dominio
  solo: si toglie **una riga**;
* `ix_event_log_domain_time` non serve a nessun accesso reale: la query forense
  passa da `ix_event_log_entity_time`, quella del giro da `ix_event_log_corr_time`;
* il BE deve comunque riscrivere le chiamate (**BE-5**), quindi un parametro in
  meno non costa niente in più.

⭐ **E tenerla sarebbe stato attivamente peggio**: una colonna derivabile scritta
su ogni riga è una copia che può **dissentire** dal catalogo, e nessun vincolo
può impedirlo. Il dominio si legge dal catalogo — nella vista (§3.6) e in
qualunque query — che è l'unico modo perché non ci siano due verità.

⚠️ Se un giorno servisse una lettura per dominio abbastanza calda da volere un
indice, l'indice va su `event_code`: il catalogo fa il resto.

#### ⛔ Niente FK su `event_code`, ed è la D-12 a imporlo

La mossa ovvia sarebbe una FK. **Sarebbe sbagliata**, e vale la pena dire perché
per non vederla riproposta:

> Una scrittura rifiutata perché il codice non è ancora a catalogo è **il diario
> che smette di scrivere per un problema di configurazione** — cioè esattamente
> ciò che la **D-12** vieta. Il diario rifiuta solo quando non sa dire *di chi è*
> la riga; un codice ignoto non gli impedisce di saperlo.

➡️ Il presidio è un **cancello di CI**: una vista ~~`dbops.vw_eventi_da_dichiarare`~~ — ⚠️ **il nome vero, applicato col changeSet 60, è `dbops.vw_eventi_non_dichiarati`** —
che elenca i codici scritti dal codice applicativo e assenti dal catalogo, più un
test che fallisce la build. È **la stessa forma** con cui il cantiere dei codici
errore ha chiuso il proprio rubinetto (`dbops.vw_codici_errore_da_dichiarare`),
ed è già in casa.

⚠️ Conseguenza operativa da mettere in conto: **BE-3 e BE-4 dovranno seminare i
propri codici**. È un costo, ed è il costo giusto — un codice che nessuno ha
dichiarato è un codice che nessuno sa leggere.

---

## 4. Il piano

> ⚠️ **Numerazione.** La sequenza `NN` è **globale per data** fra tutte le
> cartelle. Al 2026-08-22 sono occupati fino a `20260822-39`: qui si parte da
> **40**. Da **riverificare** al momento della scrittura — se nel frattempo altri
> cantieri hanno preso numeri, si slitta.
>
> ⛔ `runOnChange: false` ovunque in `00_schema` e `20_code`, `validCheckSums`
> **al plurale**, `logicalFilePath` sempre, **un changeSet per file**.

### L1 — La riga parlante — ✅ **APPLICATO il 2026-08-22, tutto verde**

**Sette changeSet più tre append a CSV.** I codici errore e la regola di
retention **non** hanno un changeSet proprio: i mirror `runOnChange` esistenti
rileggono i CSV a ogni migrate, e un loader nuovo sarebbe una seconda sorgente
di verità.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 40 | `truncate-event-log-e-riga-parlante` | `00_schema/vendite` | `TRUNCATE RESTART IDENTITY` (D-4) · `DROP` di `actor` e `source` (D-6) · `ADD emittente_soggetto_ruolo_id bigint NOT NULL` + FK `fk_event_log_emittente` → `anagrafiche.soggetti_ruoli(id)` (D-1) · `ADD auth_user_id bigint` (D-14) · `ADD tx_id uuid` (D-5) · `ADD cleanup_at timestamptz` (D-13) · `chk_event_log_entity_type` (D-9) · commenti sull'oggetto |
| 41 | `upsert-fk-index-policy-event-log` | `80_data` | La FK nuova sotto governo, a **`consentito = false`** con la ragione scritta: la query forense filtra per entità (`ix_event_log_entity_time`), il perimetro entra nel piano come **chiamata di funzione** e non come confronto indicizzabile, e il padre è un'anagrafica stabile. ⚠️ `dll_command` valorizzato lo stesso |
| 42 | `create-fn-resolve-emittente-sr-id` | `20_code/script` | Il gemello SR del risolutore, `SECURITY DEFINER` + `search_path` bloccato (§3.2). ⛔ `fn_resolve_emittente_fiscale_id` **non si tocca** |
| 43 | `create-trgfn-event-log-deriva-scope` | `20_code/vendite` | `fn_event_log_ttl_days()` (il TTL da `automation_rules_tbl`, una sede sola) + `trgfn_event_log_deriva_scope()` + `trg_event_log_a10_deriva_scope_ins`. ⚠️ Nome load-bearing (§3.5) |
| 44 | `update-trgfn-event-log-append-only` | `20_code/vendite` | Codici registrati al posto del `RAISE` nudo · `DELETE` ammesso su riga **scaduta** o con la GUC di manutenzione (§3.4.2) |
| 45 | `update-fn-log-event-senza-actor-source` | `20_code/vendite` | ⭐ **Non era nel piano.** `fn_log_event` elenca `actor` e `source` nel proprio `INSERT`: senza questa revisione fallirebbe a runtime dopo il `DROP COLUMN`. ⛔ E toglie parametri, quindi serve il **`DROP` esplicito** della firma a nove: `CREATE OR REPLACE` con meno parametri non sostituisce, e due firme con `DEFAULT` rendono ambigua ogni chiamata (precedente `20260727-25`) |
| 46 | `enable-rls-event-log-ef-whitelist` | `00_schema/vendite` | Policy + `ENABLE ROW LEVEL SECURITY` (§3.3). Mirror **esatto** di `20260720-05` |
| — | `config/codici_errore.csv` | `80_data` (CSV) | **+2**, in posizione: `E_EVENT_LOG_SCOPE_NON_RISOLTO` (**`TECNICO`**) e `E_UPDATE_NOT_ALLOWED` (**`NON_PERMESSO`**, gemello di `E_DELETE_NOT_ALLOWED`) |
| — | `config/messaggi_errore.csv` | `80_data` (CSV) | **+2** (id 978, 979), con `causa` e `soluzione` scritte per chi legge. ⚠️ Arità verificata: due `%s`, due valori nel `VARIADIC` |
| — | `dbops/automation_rules_tbl.csv` | `80_data` (CSV) | **+1** (id 15): `CLEANUP_AT` su `vendite`/`event_log`, **`ttl_days: 750`**, priority 190 |

⚠️ **Dipendenze d'ordine:** 40 prima di 43, 45 e 46 (le colonne devono
esistere); 42 prima di 43. L'autogen ordina `00_schema` e `20_code` **per
numero**, mescolandoli, quindi la sequenza regge da sé.

✅ **Verificato staticamente:** i sette file passano `yaml.safe_load`, hanno **un
solo `changeSet`** ciascuno, `logicalFilePath` sempre, `runOnChange: false` in
`00_schema`/`20_code` (guardrail verde), `validCheckSums` **al plurale** in tutti
(zero occorrenze del refuso singolare), e i tre CSV hanno arità di colonne
corretta.

✅ **Applicato il 2026-08-22**, insieme alla correzione **47** nata scrivendo i
test (§9). Le tre righe di CSV sono state rilette dai mirror `runOnChange`
esistenti, senza nessun loader nuovo.

### L2 — L'identità del giro

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 48 | `alter-task-runs-add-correlation-id` | `00_schema/vendite` | `fatturazione_lotti_task_runs.correlation_id uuid` (§1.3 dell'analisi: la colonna «assente») |
| 49 | `alter-commesse-push-log-run-in-testa` | `00_schema/vendite` | `commesse_push_log`: `correlation_id uuid` + `tx_id uuid` + lo stato `IN_ESECUZIONE` ammesso, perché la riga nasca **in testa** al giro (D-3) |

### L3 — La vista *(si accende col Passo A, non prima)*

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 50 | `create-vw-giornale-entita` | `20_code/script` | §3.6, `security_invoker` |

---

### L4 — I vocabolari: catalogo dei tipi **e** dei codici — ✅ **APPLICATO il 2026-08-22**

> Chiude le **ultime due colonne non governate** del registro: è la correzione
> che rende L4 *l'ultimo intervento strutturale* (§9.4), non il terzo di N.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 53 | `create-config-tipi-entita` | `00_schema/config` | `codice` (PK), `etichetta_key`, `modo_risoluzione_emittente` **nullable**, `obsoleto_dal`. ⛔ **Nessuna colonna `attivo`** — §3.7 |
| 54 | `create-config-eventi-dominio` | `00_schema/config` | `codice` (PK), `dominio`, `etichetta_key`, `obsoleto_dal` — §3.8 |
| 55 | `seed-tipi-entita-e-eventi-dominio` | `80_data` | I due CSV più i mirror. `TASK_RUN` entra **col modo a NULL**: puntabile da un errore, non giornalabile |
| 56 | `event-log-vocabolari` | `00_schema/vendite` | `DROP` del `CHECK` + FK a `config.tipi_entita` (`ON UPDATE CASCADE`, ⛔ non `ON DELETE`) · **`DROP COLUMN domain`** · ⛔ nessuna FK su `event_code` |
| 57 | `update-fn-log-event-senza-domain` | `20_code/vendite` | Sette parametri → **sei**, con `DROP` esplicito della firma vecchia |
| 58 | `trgfn-event-log-modo-da-catalogo` | `20_code/vendite` | Il `CASE` scritto a mano **sparisce**: il modo si legge dal catalogo. ⭐ E l'elenco dei tipi ammessi nel messaggio si legge dal catalogo, così la frase non invecchia |
| 59 | `fn-list-lotto-segnalazioni-senza-domain` | `20_code/vendite` | Via il filtro `e.domain`, **ridondante** |
| 60 | `create-vw-eventi-non-dichiarati` | `20_code/dbops` | ⚠️ **Non è il gemello di `vw_codici_errore_da_dichiarare`, e non può esserlo** — vedi sotto |
| — | `config/messaggi_errore.csv` | `80_data` (CSV) | Il messaggio **980** passa da **uno a due segnaposto**: l'elenco dei tipi ammessi arriva dal catalogo. ⚠️ Arità verificata — due `%s`, due valori nel `VARIADIC` |

⛔ **Il changeSet della `fk_index_policy` non serve, ed è la risposta giusta.**
La FK è su `entity_type`, che è **già la prima colonna di
`ix_event_log_entity_time`**: per la regola della policy è **coperta per
prefisso**. Registrarla puntando il `dll_command` su quell'indice sarebbe
attivamente dannoso — il ramo `consentito=false` ne estrae il nome per il `DROP`,
e cancellerebbe un indice **non dedicato** che serve alla query forense.

#### ⚠️ Il cancello dei codici evento non poteva essere quello dei codici errore

Scrivendo il **60** è emerso che il piano diceva una cosa impossibile:

| | Chi scrive il codice | Dove si guarda |
| --- | --- | --- |
| codici **errore** | il **database**, dentro funzioni PL/pgSQL | `pg_proc`: si vede la **sorgente**, prima che accada niente |
| codici **evento** | il **backend**, in Python | ⛔ in `pg_proc` non c'è niente da leggere |

Una vista su `pg_proc` per i codici evento tornerebbe **vuota per sempre**: il
peggior tipo di presidio, quello che dice sempre «tutto a posto» perché guarda
nel posto sbagliato.

➡️ **Il cancello vero sta lato Python (BE-9)**, dove i codici sono scritti. Il
**60** fa un lavoro diverso e complementare: i codici **già finiti nel registro**
senza essere dichiarati — la deriva che nessun controllo sul sorgente vede.
⚠️ Ed è **data-dependent**: su un ambiente senza traffico è cieca. È una spia da
guardare, non un semaforo che ferma.

#### L'ordine, e perché non serve nessuna eccezione

`80_data` gira **dopo** `00_schema`, quindi il **56** posa la FK prima che il
**55** semini il catalogo. Non è un problema: `event_log` è **vuoto**, e la FK
valida su zero righe.

⚠️ La prima stesura prevedeva un'eccezione alla regola «i dati di `80_data` si
cambiano dal CSV» *«perché su questo database `event_log` ha righe»*. **Tolta**:
il registro è vuoto, e se non lo fosse la risposta è quella già presa una volta —
azzerarlo (D-4). Nessuna riga di questo registro vale un'eccezione a una regola
di progetto.

⚠️ **Rotture temporanee dentro la stessa passata**: il `DROP COLUMN domain` del
**56** rompe `fn_log_event` e `fn_list_lotto_segnalazioni` finché il **57** e il
**59** non le riscrivono. Un corpo plpgsql non è tracciato come dipendenza dal
DDL, quindi il `DROP` riesce e il difetto si vedrebbe alla prima chiamata.

---

### L2 — L'identità del giro — ✅ **APPLICATO il 2026-08-22**

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 61 | `task-runs-correlation-id` | `00_schema/vendite` | `correlation_id` sul registro dei tentativi, più l'indice parziale |
| 62 | `commesse-push-log-run-in-testa` | `00_schema/vendite` | `correlation_id` + `tx_id` + lo stato **`IN_ESECUZIONE`** ammesso, perché la riga nasca **in testa** al giro |

⭐ **Il difetto `entity_id = 0` non era un segnaposto**, ed è la scoperta che dà
forma al **62**: la riga di `commesse_push_log` nasceva a **fine** giro, quindi
all'avvio non c'era niente da citare. Un segnaposto è una convenzione da
interpretare; un id inesistente è una **sequenza sbagliata**, e si corregge
invertendo l'ordine.

⭐ **E ne esce un guadagno che non era nel piano**: un giro **interrotto** oggi
non lascia traccia — muore e sparisce. Con la riga creata in testa, quella
rimasta a `IN_ESECUZIONE` è l'unica prova che qualcosa è partito e non è tornato.

⚠️ Il `correlation_id` di oggi vale `lock_batch_id`, che **nasce col lotto e non
cambia mai**: due corse dello stesso lotto lo condividono. Non è una deduzione —
lo asserisce già il **test 6** di `test-fn-list-lotto-segnalazioni-job`, ed è il
motivo per cui l'àncora del «job corrente» è l'`event_time` e non quel campo.

---

### L5 — I due **scrittori** delle colonne del giro — ✅ **APPLICATO il 2026-08-22**

> ⭐ **Non è un lotto del piano originale: è la risposta a una richiesta del
> backend**, che ha misurato su `pg_proc` ciò che L2 aveva lasciato a metà. Il
> perché, per intero, sta in **§5-bis**.
>
> **In una riga:** L2 aveva consegnato le **colonne**, e nessuna funzione le
> scriveva. Una colonna che nessuno riempie non è mezzo lavoro — è un buco che
> sembra chiuso.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| 67 | `update-fn-start-lotto-task-run-correlation-id` | `20_code/vendite` | `fn_start_lotto_task_run` prende `p_correlation_id` e lo scrive. ⛔ Col **`DROP` esplicito** della firma a sei — vedi §5-bis, è la premessa della richiesta che era falsa. ⚠️ E i tre guard passano da `E_PARAMETRO_INVALIDO` a `E_VENDITE_CHIAMATA_NON_VALIDA` |
| 68 | `create-fn-commessa-push-run-apri-chiudi` | `20_code/vendite` | La coppia `fn_start_commessa_push_run` / `fn_close_commessa_push_run`, sul pattern dei `task_runs`. Due rifiuti alla chiusura (stato non finale, riga non aperta) e la **descrizione della tabella** riscritta: diceva «append-only, nessuno stato inter-run», e dal 62 non è più vero |
| 69 | `drop-fn-log-commessa-push-run` | `20_code/vendite` | ⛔ Via la funzione che inseriva un giro **già finito**: con la riga che nasce in testa, quell'operazione non esiste più. Un changeSet suo perché è l'unica cosa **irreversibile per il BE** del lotto |
| — | `config/codici_errore.csv` | `80_data` (CSV) | **+3** codici, tutti **`TECNICO`**: `E_VENDITE_CHIAMATA_NON_VALIDA` (il gemello vendite di `E_PAGAMENTI_CHIAMATA_NON_VALIDA`), `E_COMMESSA_PUSH_RUN_STATO_NON_FINALE`, `E_COMMESSA_PUSH_RUN_NON_APERTO` |
| — | `config/messaggi_errore.csv` | `80_data` (CSV) | **+3** (id **983, 984, 985**). ⚠️ Arità verificata: due `%s` e due valori in ciascuno |

⚠️ **Numerazione: si parte da 67 e non da 63.** I numeri **63-66 sono prenotati
dal §6 di [brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md)**, che li
ha già scritti nel proprio piano e li cita altrove; lo stesso vale per il
messaggio **982**. Prenderli avrebbe costretto quel cantiere a rinumerare un
piano già referenziato — un buco nella sequenza costa meno di un riferimento che
mente.

⭐ **E una cosa che si vede solo qui: il difetto non era misurabile da nessuno dei
due lati.** Il changeSet 62 aveva allargato il `CHECK` a quattro stati; la
funzione che scriveva quella tabella ne ammetteva tre. *Il vincolo non sa chi lo
scrive, e la funzione non legge il vincolo* — la migrazione passa, e a fallire è
la prima scrittura. Il presidio nuovo è l'**asserzione 13** del pgTAP, che
rilegge `pg_get_constraintdef` e confronta i due insiemi: è l'unico posto dove si
guardano in faccia.

## 4-bis. ⭐ Cosa questo brief ASSORBE — e che non si gestisce più altrove

> **Serve a una cosa sola:** chi lavora su `event_log` legge **questo**
> documento e basta. E chi apre l'altro non deve chiedersi se una voce è ancora
> sua.

| Voce assorbita | Da dove | Dove vive ora | Stato |
| --- | --- | --- | --- |
| **T-1** — il catalogo chiuso dei tipi di entità | `brief-db-bersaglio-errore` §5.1 | **D-17** e **§3.7**, lotto **L4** (changeSet 53-54) | ✅ **fatto e applicato** |
| **T-1b** — `event_log.entity_type` adotta il catalogo | `brief-db-bersaglio-errore` §5.1 | **§3.7**, lotto **L4** (changeSet 55-58) | ✅ **fatto e applicato** — ⭐ il prerequisito di quel cantiere è **sciolto**: T-2…T-5 possono partire |
| **Q-1 chiusa** — «il vocabolario dei tipi: catalogo chiuso» | `brief-db-bersaglio-errore` §7 | **D-17** | ✅ decisa, invariata |

⛔ **Di là quelle voci non si gestiscono più**: restano come **dipendenza**, non
come passi. Il loro brief conserva tutto ciò che è suo — i tre strati del
messaggio, la forma `target`, il pilota 937, la trappola dei `%s`, il roll-out e
le consegne BE/FE.

### Perché il confine sta qui e non altrove

Non è una spartizione di comodo. I due cantieri hanno **mestieri diversi** — il
nostro è *«la riga del giornale dice chi, per chi, in che giro»*, il loro è
*«l'errore porta un bersaglio»* — e si toccano su **un oggetto solo**:
`event_log.entity_type`, che è **nostro**. Una decisione su una colonna deve
stare dove vive la colonna, o diventa la seconda sede che entrambi i brief
dicono di evitare.

⚠️ **Cosa NON è stato assorbito, e perché** — portare qui anche il bersaglio
farebbe di questo documento il contenitore di due mestieri: è esattamente ciò
che il §0 di [analisi-osservabilita-log.md](analisi-osservabilita-log.md) dice
di non fare con la diagnostica di produzione, e la ragione è la stessa.

### Cosa questo cantiere REGALA all'altro, senza costo

| | Cosa |
| --- | --- |
| ⛔ | ~~I due codici nati con L1 — `E_EVENT_LOG_SCOPE_NON_RISOLTO` ed `E_EVENT_LOG_ENTITY_TYPE_IGNOTO` — hanno già la forma del bersaglio: convertirli è una riga, e sono i **primi adottanti gratuiti** del loro T-5.~~ **SUPERATA il 2026-08-22**, e il regalo non era accettabile — tre ragioni indipendenti, misurate sui CSV applicati: `E_EVENT_LOG_ENTITY_TYPE_IGNOTO` porta **per definizione** un tipo **fuori catalogo**, quindi farebbe fallire il presidio che loro devono scrivere; `E_EVENT_LOG_SCOPE_NON_RISOLTO` punta a **un'entità che non esiste**, quindi il pulsante non comparirebbe **mai**; e sono entrambi **`TECNICO` (500)**, la classe in cui *noi stessi* non mettiamo `campo` nel contesto. ➡️ **Ne è uscita la regola che a quel brief mancava** — *il bersaglio si mette sugli errori rimediabili, mai sui `TECNICO`* — che è un regalo migliore di quello che avevamo offerto. Vedi `brief-db-bersaglio-errore` §5.5 |
| ⭐ | La vista `script.vw_giornale_entita` (§3.6) e le rotte del bersaglio (loro **B-2**) usano **lo stesso** vocabolario `config.tipi_entita`: la tabella tipo → schermata si scrive una volta |
| ⚠️ | Il guard `E_FATTURE_RIGHE_RETTIFICATE` di [brief-db-guard-righe-fattura-rettificate.md](brief-db-guard-righe-fattura-rettificate.md) dice «su %s righe» — un conteggio, **nessun id in prosa**, che è già la regola giusta. Ma un `target` sulle righe bloccate lo renderebbe azionabile: buon candidato **T-5** |

---

## 5. 🔵 A carico del BE — *scritto qui, non toccato da qui*

> **Perimetro DB:** questo cantiere non modifica `backend/`. Le richieste si
> scrivono, non si implementano.
>
> ✅ **Stato al 2026-08-22 (sera), scritto dal backend.** Sette consegne su nove
> sono **fatte**: BE-1, BE-3a, BE-4, BE-5, BE-6, BE-7, BE-9. Restano **BE-2** e
> **BE-3b**, ferme su un prerequisito DB — i changeSet 61 e 62 hanno consegnato
> le **colonne**, ma nessuna funzione le scrive e `fn_log_commessa_push_run`
> **rifiuta** `IN_ESECUZIONE` con un guard suo. La richiesta è in
> [brief-db-scrittori-del-giro-push-e-task-run.md](brief-db-scrittori-del-giro-push-e-task-run.md).
>
> ⭐ **Il rischio 3 del §9.3 è chiuso a metà**: il registro ha di nuovo delle
> righe scritte dal backend vero — perimetro derivato, `cleanup_at` a 750
> giorni, entrambi verificati contro il DB. Resta aperto il `correlation_id`,
> che è la parte che dipende da BE-2.
>
> ⚠️ **E una consegna che questo §5 non elencava**, trovata eseguendo i
> cancelli: i due codici nuovi (`E_EVENT_LOG_SCOPE_NON_RISOLTO`,
> `E_EVENT_LOG_ENTITY_TYPE_IGNOTO`) più `E_UPDATE_NOT_ALLOWED` mandavano in
> rosso il **cancello del terzo lato** e quello della **divergenza**, perché
> `error_policies_generated.py` non era stato rigenerato dopo il seed. Un codice
> errore nuovo costa **due** cose lato BE, non una: la policy generata **e** il
> messaggio di ripiego senza `%s`.

| # | Consegna | Blocca? |
| --- | --- | --- |
| **BE-1** | ⛔ **`severity="WARNING"` → `"WARN"`** in `commesse_service.py:221`, **e il test che asserisce il valore rotto**. È un difetto **già vivo** (§1.2) | No — **e va fatto subito, prima di L1** |
| **BE-2** | `correlation_id` = **un `uuid` nuovo per giro**, generato dal runner e dall'orchestratore push; scritto anche su `task_runs` e `commesse_push_log` (D-7). ✅ **Il DB è pronto dal 2026-08-22**: `fn_start_lotto_task_run` ha il settimo parametro e `fn_start_commessa_push_run` il terzo (L5) | ~~Sì, dopo L2~~ → **sbloccata** |
| **BE-3** | La riga di `commesse_push_log` nasce **in testa** al giro (`IN_ESECUZIONE`) e si chiude alla fine; `PUSH_STARTED`/`PUSH_COMPLETED` **escono da `event_log`** (D-3). ✅ **Il DB è pronto**: la coppia `fn_start_commessa_push_run` / `fn_close_commessa_push_run` (L5). ⛔ **E `fn_log_commessa_push_run` non esiste più**: `commesse_repository.log_push_run` va riscritto nello stesso giro, non è opzionale | ~~Sì~~ → **sbloccata, e ora è un breaking** |
| **BE-4** | `EMITTIBILITA_FALLITA` diventa **per commessa** (`entity_type = 'COMMESSA'`, `entity_id = commessa_id`), una riga per commessa fallita invece di un evento aggregato con dentro una lista di id (D-3) | Sì |
| **BE-5** | Smettere di passare `actor` e `source`: **le colonne non esistono più** (D-6). ⭐ **E con L4 anche `domain`**, che scende dalla firma: la chiamata passa da 9 a **6** parametri. ⚠️ Un solo adeguamento, se BE-5 e L4 viaggiano insieme — due se si separano | Sì |
| **BE-9** | *(da L4)* Seminare i **codici evento** nel catalogo `config.eventi_dominio`. ⚠️ Un codice non dichiarato **non blocca la scrittura** (D-12) ma fa fallire la build: il cancello è `dbops.vw_eventi_non_dichiarati` (changeSet 60) | No, ma rompe la CI |
| **BE-6** | ⚠️ **Estrarre il BB unico di `log_event`.** `pipeline_repository.log_event` e `commesse_repository.log_event` sono **copia carbone**: finché restano due, ogni modifica si scrive due volte | No, ma è il momento giusto |
| **BE-7** | Le scritture di diario passano dal telaio **`_diagnostica_best_effort`** già presente in `pipeline_runner`. ⭐ Dopo L1 una `log_event` **può fallire** (`NOT NULL`, FK, `WITH CHECK`), e un difetto del diario non deve mai diventare il messaggio che legge l'operatore — è **la stessa classe** di BE-1. Vedi **Q-3** | Sì, di fatto |
| **BE-8** | *(Passo 2, indipendente da tutto)* `request_id` nel formatter di logging — esiste già come contextvar. **E già che si è lì**: `dbops.request_log.emittente_attivo_id` e `tx_id` sono **due colonne morte** (0 valorizzate su 353.758) e il valore dell'emittente ce l'ha già il JWT: o si collegano o si tolgono | No |
| **BE-10** | ⚠️ *(da L1/L4/L5, trovata misurando)* **Rigenerare `apps/core/services/error_policies_generated.py`** (`manage.py genera_error_policies`) e committarlo. Il file mappa codice → classe, si rigenera **a ogni seed**, e misurato il 2026-08-22 è indietro di **21 codici su 776**: 3 di L5, 3 di L1/L4, 1 del cantiere delle righe rettificate e **14 di `pagamenti`**. ⭐ Non è un debito di questo cantiere — è un debito di **giornata**, e si paga in un comando solo | ⛔ **Rompe la CI**: `test_error_policies_divergenza_db` confronta il file col catalogo **letto dal database**, quindi diventa rosso appena i CSV arrivano in CI — in una PR che può non c'entrare niente |

---

## 5-bis. ⭐ La richiesta del backend, e le due cose che ha corretto

> **Cos'è.** Il 2026-08-22, applicati L1+L4+L2, il backend ha misurato su
> `pg_proc` — non sugli YAML — e ha trovato che **le colonne c'erano e nessuna
> funzione le scriveva**. La richiesta è arrivata come brief, e questo lotto (L5)
> è la risposta.
>
> ⭐ **Ha la precedenza sul resto della coda DB** (la vista L3, la retention dei
> log gemelli) per una ragione sola: è l'**unica** cosa che sblocca qualcun altro.
> Le altre due sbloccano me.

### Cosa era stato chiesto, e cosa è stato consegnato

| Chiesto | Consegnato |
| --- | --- |
| `fn_start_lotto_task_run`: un parametro `p_correlation_id uuid DEFAULT NULL` | ✅ changeSet **67** — ⚠️ ma **con** il `DROP` della firma vecchia, vedi sotto |
| `fn_start_commessa_push_run(dry_run, source_types, correlation_id)` | ✅ changeSet **68**, restituisce l'`id` del giro |
| `fn_close_commessa_push_run(id, stato, risultato, durata_ms, source_types)` | ✅ changeSet **68** |
| I due guard della chiusura, classe **`TECNICO`**, ⛔ **senza riusare `E_PARAMETRO_INVALIDO`** | ✅ `E_COMMESSA_PUSH_RUN_STATO_NON_FINALE` e `E_COMMESSA_PUSH_RUN_NON_APERTO` |
| ⛔ `fn_log_commessa_push_run` si toglie | ✅ changeSet **69**, senza `CASCADE` |

⭐ **E una cosa in più che non era chiesta, ma che riscrivere il corpo imponeva
di guardare**: i tre guard di `fn_start_lotto_task_run` sollevavano
`E_PARAMETRO_INVALIDO` con dentro la frase «p_lotto_id obbligatorio e > 0».
AGENTS.md è esplicito — *toccando una funzione vecchia il messaggio va guardato,
non dato per buono perché il codice è registrato* — e quel codice è **uno split
rimandato**, non una sede. Da qui il terzo codice nuovo,
**`E_VENDITE_CHIAMATA_NON_VALIDA`**: è il **gemello vendite** di
`E_PAGAMENTI_CHIAMATA_NON_VALIDA`, nato il giorno prima nel cantiere incassi per
la stessa identica ragione. Non è un'invenzione: è la seconda applicazione di un
criterio già deciso.

### ⛔ La premessa della richiesta che era falsa — e come si è vista

Il brief del backend diceva, in §2.1:

> «⚠️ Con `DEFAULT NULL` in coda **non serve un `DROP`** della firma vecchia e
> non nasce nessun overload ambiguo, perché nessun chiamante passa argomenti
> posizionali oltre il sesto.»

**È falso**, e non per un dettaglio di sintassi: `CREATE OR REPLACE` con un
parametro in **più** non sostituisce niente — crea una funzione **nuova** e lascia
viva la vecchia. Le due convivono, e una chiamata a sei argomenti soddisfa
**entrambe**. Misurato in transazione su questo database, prima di scrivere il
changeSet:

```text
CREATE FUNCTION f(a bigint, b bigint DEFAULT NULL) ...
CREATE FUNCTION f(a bigint, b bigint DEFAULT NULL, c uuid DEFAULT NULL) ...
SELECT f(1::bigint, 2::bigint);
  ERRORE: la funzione f(bigint, bigint) non è unica
```

⚠️ **E il chiamante rotto sarebbe stato proprio il suo**:
`pipeline_repository.start_lotto_task_run` passa **sei argomenti posizionali**.
Il migrate sarebbe passato pulito, e a rompersi sarebbe stata la prima corsa
della pipeline.

⭐ **Il ragionamento sbagliato è comprensibile, e vale la pena nominarlo**: la
regola nota in casa riguarda le firme che **perdono** parametri (`20260727-25`,
poi il changeSet 57 di questo stesso cantiere). Sembra naturale che *aggiungere*
sia il caso benigno. Non lo è: la direzione non c'entra — **conta che le firme
restino due**.

### ⚠️ La numerazione: 67-69, non 63-66

I numeri **63-66** e il messaggio **982** sono prenotati dal piano di
[brief-db-bersaglio-errore.md](brief-db-bersaglio-errore.md) §6, scritto lo
stesso giorno e già citato altrove. Prenderli avrebbe costretto quel cantiere a
rinumerare un piano referenziato: **un buco nella sequenza costa meno di un
riferimento che mente**. È lo stesso criterio con cui il quinto giro ha sciolto
la collisione su `entity_type`.

### 🔵 Cosa resta al backend, adesso

1. **BE-2** e **BE-3b** possono partire: il DB ha i due scrittori.
2. ⛔ **`commesse_repository.log_push_run` non compila più contro il DB**: la
   funzione che chiamava non esiste. Va spezzata in `start` (in testa a
   `_run_locked`) e `close` (alla fine), come dice il loro §3.
3. ⚠️ **BE-10**, che non era nel loro elenco: `error_policies_generated.py` è
   indietro di **21 codici**. Non è debito di questo lotto, ma è ciò che rende
   rossa la CI.

### 🔎 Due misure fatte scrivendo, che non erano richieste

Nessuna delle due blocca. Si scrivono perché sono state misurate.

| | Cosa |
| --- | --- |
| ⚠️ **Il ruolo batch non può aprire un giro di push** | `zeroerp_batch_fatturazione` ha su `commesse_push_log` il solo grado **`r` (SELECT)**, mentre su `fatturazione_lotti_task_runs` ha `arw`. Oggi non è un difetto — il push gira come `zeroerp_app` — ma il giorno che passasse sul canale batch, l'apertura fallirebbe sul **GRANT**, non sulla RLS. E un `BYPASSRLS` non aiuta: salta le policy, non i permessi. È lo stesso disallineamento del precedente `vendite.note` |
| ⏱️ **Il `tx_id` non è ancora attaccato** | Riverificato dopo l'apply: né `commesse_push_log` né `event_log` hanno il trigger `..._gen_tx_id_*`. È coerente con §3.5 — lo genera `dbops.fn_run_automations_tx_id`, che gira in `ci_apply`; sul migrate manuale arriva col pgagent la sera. **Finché non c'è, `tx_id` resta NULL su ogni riga**, e la D-5 è viva come colonna ma non come dato |
| ⚠️ **La baseline B-7 dei codici errore è indietro, e non la aggiorno io** | Il cancello è **verde** (`accumuli nuovi: 0`), ma `db/baseline-codici-errore-famiglie.tsv` è fermo al cantiere che l'ha creata: rigenerarla oggi farebbe entrare **9 righe di tre cantieri diversi** — le mie due (`E_VENDITE_CHIAMATA_NON_VALIDA` → `PARAMETRO`, `E_COMMESSA_PUSH_RUN_NON_APERTO` → `NOT_FOUND`), quelle di `pagamenti` e quella del pricing. ⭐ Il file dice di sé che aggiornarlo *«è una DECISIONE, non una formalità: ogni riga che cambia dice che un codice ha cambiato significato»*: prendere quella decisione per conto di altri due cantieri sarebbe il modo di svuotarla di senso. Va fatta in **una passata sola e deliberata** |

---

## 6. Il presidio pgTAP — ✅ **64 asserzioni verdi, zero skip**

Verificato leggendo il TAP riga per riga, non solo l'esito: un file verde per
sottrazione — con le asserzioni finite nei rami `skip` — sarebbe indistinguibile
da uno verde davvero se ci si ferma al `Result: PASS`.

| File | Test | Nota |
| --- | ---: | --- |
| `db/pgtap/rls/test-rls-event-log-ef-whitelist-write.sql` | 5 | ⭐ **Senza DDL**, a differenza dei gemelli in `rls/`: là il test gira come owner e deve accendere `FORCE` per farsi mordere dalle policy, qui il runner è `zeroerp_app`, che **non** è owner — si collauda la configurazione di esercizio |
| `db/pgtap/vendite/test-event-log-deriva-scope.sql` | 7 | Include il presidio dell'**assenza** del lucchetto `require_attivo` (D-12): una regressione che non introdurrebbe una persona ma un'automazione, alle 21:00 |
| `db/pgtap/vendite/test-event-log-append-only.sql` | 5 | Include la prova che `cleanup_at` è **immutabile** — senza, il veto sul `DELETE` si aggirerebbe portando la scadenza nel passato |
| `db/pgtap/vendite/test-event-log-function-v1.sql` | 8 | **Adeguato**: chiamava la firma a nove e usava `entity_id` inventati, che ora la derivazione rifiuta |
| `db/pgtap/vendite/test-fn-list-lotto-segnalazioni-job.sql` | 8 | **Adeguato**: inseriva `actor`/`source` |
| `db/pgtap/vendite/test-commesse-push-log-function-v1.sql` | 13 | *(L5)* **Riscritto, non adeguato**: il soggetto è cambiato — prima era «una riga di log si scrive», ora è «un giro si apre e si chiude una volta sola». Era a 7 |
| `db/pgtap/vendite/test-fatturazione-pipeline-task-runtime.sql` | 18 | *(L5)* **Esteso di una**: il `correlation_id` passato all'apertura arriva sulla riga del tentativo. Era a 17 |

⭐ **L'asserzione che vale più delle altre dodici è la 13**, e non collauda una
funzione: rilegge `chk_commesse_push_log_stato` dalla tabella e lo confronta con
l'elenco che la chiusura conosce. È l'unico posto in cui i **due** vocabolari si
guardano in faccia — il difetto che ha prodotto il lotto è esattamente che non lo
facevano. ⚠️ Se diventa rossa non si aggiorna l'atteso: si guarda prima se
`fn_close_commessa_push_run` sa cosa farsene del valore nuovo.

⛔ **Il file sul canale batch non è stato scritto, ed è la scelta giusta.**
Duplicava `db/pgtap/rls/test-role-batch-fatturazione-postura.sql`, che già
presidia il ruolo, il `BYPASSRLS`, il **grado `i` (INSERT-only)** su `event_log`
e la controprova «nessun `DELETE`» — con 18 asserzioni, meglio di quanto avrei
scritto. La regola del 2 vale anche per i test: una seconda sede si sarebbe
disallineata alla prima modifica.

⚠️ Regole rispettate e verificate col cancello: le tre righe di preambolo
(`BEGIN;`, contesto, `SET CONSTRAINTS ALL IMMEDIATE`), `throws_ok` sempre con lo
SQLSTATE **oppure** `throws_like` sulla frase dove il punto è *quale* errore, e
`LIMIT 1` sempre con `ORDER BY`.

## 7. Cosa NON si fa

| Non si fa | Perché |
| --- | --- |
| **Estendere emittente e RLS alle altre 6 tabelle di log** | Hanno una testata protetta a cui la query si ancora (§3.3). Triplicherebbe il cantiere senza chiudere un buco reale |
| **Partizionare `event_log` per `event_time`** | Considerato: sarebbe la retention per `DROP PARTITION`, che con l'append-only non litiga, ed è **l'unica delle tre vie che diventa cara dopo**. Scartato perché il volume è basso per costruzione (quattro righe per giro) e la PK dovrebbe diventare `(id, event_time)`: complessità comprata su un rischio non misurato |
| **Spostare `event_log` in uno schema neutro** | Con la vista di §3.6 come cucitura, la domanda smette di essere un now-or-never: quando `pagamenti` vorrà il suo registro, la vista lo aggiunge |
| **Toccare `E_PARAMETRO_INVALIDO`** | 126 funzioni in 7 schemi, e la sostituzione **non è meccanica**: il codice si sceglie parametro per parametro. **Brief suo** (analisi §5, Aperte #14) |
| **Il recinto test/esercizio su `error_log`** | Difetto vero, ma `error_log` non è append-only e ha retention: una colonna aggiunta domani inizia a popolarsi domani. Non è un now-or-never |
| **Un `trgfn_guard_emittente_scope` su questa tabella** | D-10 |
| **Estendere `script.fn_resolve_emittente_fiscale_id`** | Con la colonna SR la derivazione è una **copia** dal padre: nasce il gemello `fn_resolve_emittente_sr_id` e la funzione esistente **non si tocca** (D-1) |
| **Seedare `LOTTO` in `config.sorgenti`** | Serviva alla FK, che non c'è più (D-9). Se un domani il lineage vorrà il lotto come nodo, sarà una decisione sua |
| **Segnalare come anomalia un evento su un padre disattivato** | L'avviso scatterebbe sul caso **normale** (la chiusura dei documenti di un emittente cessato) e diventerebbe rumore. Il presidio giusto sta **sul documento** — [analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md) |

---

## 8. Domande — tutte chiuse il 2026-08-22

| # | Era | Come si è chiusa |
| --- | --- | --- |
| **Q-1** | Il `ttl_days` di `event_log` (i 30 giorni della regola `*all` coprivano solo il mese in corso) | ✅ **750 giorni** — D-13. La data si scrive nella riga e non è più modificabile: sbagliare per eccesso è recuperabile, per difetto no |
| **Q-2** | «Chi»: il nome (`user_insert`) o il numero? | ✅ **Tutti e due** — D-14. Il nome si legge senza cercare, il numero regge a un rename |
| **Q-3** | Un difetto del diario può far fallire il lavoro? | ✅ **Fail-loud nel DB, best-effort nel BE** — D-15. E la riga nel log tecnico è la differenza fra «best-effort» e «silenzio» |
| **Q-4 · Q-5** | I lucchetti `require_attivo` verso `config.sorgenti` e `emittenti_fiscali` spegnerebbero il diario | ✅ **Rovesciata da un rilievo di Tid**: *«invece di smettere di scrivere, non dovrebbe continuare e semmai segnalare?»*. Risposta: sul diario **non si blocca mai** (D-12), e il lucchetto non si disattiva — **si evita di crearlo**, scegliendo la colonna SR (D-1) e il `CHECK` invece della FK (D-9). ⚠️ Non si segnala nemmeno: l'avviso scatterebbe sul caso normale |
| **Q-6** | Quali sorgenti nella vista | ✅ **Quattro** — D-16, con `attivita_fatturabili_log` fuori e il motivo scritto nella vista |

> ⚠️ **Il rilievo di Q-4/Q-5 vale oltre questo cantiere.** «Chi continua a
> scrivere su una riga annullata» è un'anomalia da **presidiare sul documento**,
> non da nascondere spegnendo il suo diario. È materia di
> [analisi-presidi-percorso-storto.md](analisi-presidi-percorso-storto.md), e il
> diario — una volta leggibile — è ciò che permette di **accorgersene**.

---

## 9. Cosa renderebbe necessario un terzo giro

> **Perché questa sezione esiste.** Domanda di Tid, 2026-08-22: *«siamo sicuri
> che sia definitiva? In venti giorni è già la seconda volta sui log»*. È la
> domanda giusta, e la risposta non è una rassicurazione: è l'elenco di ciò che
> ci riporterebbe qui, con accanto cosa lo chiude.

### 9.1 Le due volte in venti giorni sono lo STESSO difetto

Non è sfortuna, ed è nominabile:

> **Una colonna di testo che tutti scrivono e nessuno governa.**

Inizio agosto: 207 codici errore fuori catalogo → seed più tassonomia delle
classi. Oggi: `entity_type` testo libero → catalogo. **Stesso difetto, altra
colonna.** E al 2026-08-22 lo stesso registro ne aveva **altre due** nella stessa
condizione (`domain`, `event_code`): è il motivo per cui la **D-18** le chiude
adesso, invece di aspettare il terzo giro.

### 9.2 Cosa è solido, e non torna

| | Perché non torna |
| --- | --- |
| I sei campi del **lato scrittura** | Sono i non-recuperabili, sono tutti dentro, e 33 asserzioni li presidiano. Era l'unica cosa che *doveva* essere giusta al primo colpo |
| Il **perimetro** (SR + whitelist + policy) | Rispecchia 14 tabelle: se cambia, cambia per tutte, non per questo registro |
| **Append-only contro retention** | Il conflitto è risolto nel merito, non aggirato |
| **D-12** — «il diario non si blocca mai» | È una regola, non un'implementazione: sopravvive a chi la implementa |

### 9.3 Cosa NON è ancora fondamenta, in ordine di probabilità

| # | Rischio | Cosa lo chiude |
| --- | --- | --- |
| **1** | 🔴 ~~`domain` e `event_code` non governati~~ | ✅ **D-18 / L4.** Era il più probabile: stessa forma del difetto che ci ha riportati qui due volte, e `event_code` è l'asse su cui il Passo B raggruppa |
| **2** | 🔴 ~~La vista nasce come union di sole tabelle `vendite`~~ | ✅ **§3.6 rev.** I registri di eventi del progetto sono **sei**: se la cucitura nascesse locale, a rifarsi sarebbe la vista — cioè la cosa che tutti avrebbero già in mano |
| **3** | 🟡 **Il modello non ha ancora incontrato la realtà** | ⛔ **Non si chiude a tavolino.** `event_log` ha **zero righe**: dopo il `TRUNCATE` nessuno ha più scritto, perché il BE non è allineato. «`correlation_id` = un uuid per giro» oggi è un disegno; diventa un fatto quando il runner lo genera. Il modo di non tornare indietro è fare **BE-2/BE-3 presto**, non farli perfetti |
| **4** | 🟡 `FORCE ROW LEVEL SECURITY` | Se arriva l'ondata, `fn_resolve_emittente_sr_id` va rivista — insieme a una dozzina di funzioni gemelle. Dichiarato nel changeSet: **non sarà una ristrutturazione di questo registro** |
| **5** | 🟡 Il **Passo B** poggia sulla qualità dei codici errore | Lo split di `E_PARAMETRO_INVALIDO` (126 funzioni, 7 schemi) ha un brief suo. Non blocca il Passo A |

### 9.4 I due impegni

Sono verificabili, ed è per questo che stanno scritti:

1. ⭐ **L4 è l'ultimo intervento strutturale su `vendite.event_log`** — ✅ **posato
   il 2026-08-22**. Da qui in avanti la tabella si tocca solo per **aggiungere
   righe ai cataloghi**, cioè con un seed, non con una migrazione di schema.
   ⏳ **L'impegno decorre da oggi**: se servisse un'altra colonna, questa sezione
   ha sbagliato qualcosa e va scritto **qui** cosa, con la data.

   > ⏱️ **Primo controllo, 2026-08-22 — l'impegno regge, ma va letto per intero.**
   > Il cantiere del bersaglio aggiungerà **una colonna a `config.tipi_entita`**:
   > la chiave con cui si raggiunge l'entità (`id` oppure `uid`, la convenzione
   > di `config.sorgenti.key_selector`). ⭐ **Non è una violazione** — la promessa
   > è su `event_log`, che non si tocca. ⚠️ Ma vale la pena dirlo qui, perché
   > «da qui solo seed» è vero **della tabella del giornale**, non del catalogo
   > che il giornale usa: quello ha **due padroni**, e il secondo è appena
   > arrivato. Vedi `brief-db-bersaglio-errore` §6, changeSet 63.
2. ⭐ **La vista è la cucitura, e nasce già larga.** Un registro nuovo entra con
   un `UNION ALL`; se un giorno entrasse rinegoziando le colonne, il difetto è
   nella forma normalizzata di §3.6.

⚠️ **E una cosa che non si può promettere**, perché prometterla sarebbe la bugia
più facile: il contatto col backend. Finché `event_log` non ha righe scritte
dalla pipeline vera, questo piano è verificato dai pgTAP e da nient'altro.

---

## 10. Registro

### 2026-08-22 · Nascita

Il brief nasce da due giri con Tid sullo stesso giorno.

- **Primo giro** — riletto lo stato **sul database e sul codice**, non dal §1
  dell'analisi. Cadono tre premesse (la RLS decorativa, il rischio batch, il 67%
  di B1); emergono `tx_id` (B10) e le colonne morte di `request_log` (B11);
  emerge il difetto `severity="WARNING"`. Si stabilisce il criterio d'ordine:
  **lato scrittura contro lato lettura**, su una tabella dove il backfill non
  esiste.
- **Secondo giro** — Tid: *«questo è un ambiente di test, i dati non devono
  essere un limite: scegliamo la strada migliore»*. Cade una **mia** conclusione
  sbagliata (`E_PARAMETRO_INVALIDO` non blocca il Passo B: `function_name` è
  `NOT NULL` e ha 70 valori distinti) ed esce la vista `vw_giornale_entita`,
  perché il Passo A sul solo `event_log` consegnerebbe quattro righe.
- **Le undici decisioni** di §2 sono di Tid, prese lo stesso giorno.

### 2026-08-22 (nono giro) · ✅ L5 — i due scrittori, chiesti dal backend

Il backend, applicati L1+L4+L2, ha misurato su `pg_proc` e ha trovato che **le
colonne del giro c'erano e nessuna funzione le scriveva**. Da lì L5: tre
changeSet (**67-69**), tre codici errore, due file pgTAP — **31 asserzioni verdi
con zero skip**, baseline `vendite` senza regressioni (5 rossi, tutti già noti).

⭐ **Perché ha scavalcato la coda.** In coda c'erano la vista `vw_giornale_entita`
(L3) e la retention dei log gemelli. Sono due cose mie: sbloccano me. Questa
sblocca **BE-2 e BE-3b**, cioè le uniche due consegne ferme *per causa nostra*.
Il criterio non è l'importanza, è **chi resta fermo**.

Tre cose che scrivendo si sono rivelate diverse da come erano nel piano:

1. ⛔ **La premessa della richiesta era falsa, e l'ha detta una misura.** «Con
   `DEFAULT NULL` in coda non serve il `DROP`»: **`CREATE OR REPLACE` con un
   parametro in più non sostituisce, affianca**, e una chiamata a sei argomenti
   soddisfa entrambe le firme (`la funzione non è unica`). Il chiamante che si
   sarebbe rotto è proprio il suo — `pipeline_repository` passa sei argomenti
   posizionali — e si sarebbe rotto **alla prima corsa**, non al migrate.
   ⭐ La regola nota in casa parla di firme che *perdono* parametri: sembra che
   aggiungere sia il caso benigno. **La direzione non c'entra — conta che le
   firme restino due.** Dettaglio in §5-bis.
2. ⭐ **Il difetto che il backend ha trovato non era visibile da nessuno dei due
   lati.** Il changeSet 62 aveva allargato il `CHECK` a quattro stati; la funzione
   che scriveva quella tabella ne ammetteva tre. *Il vincolo non sa chi lo scrive,
   e la funzione non legge il vincolo.* Il presidio nuovo è l'**asserzione 13**
   del pgTAP, che rilegge `pg_get_constraintdef`: è l'unico posto dove i due
   insiemi si guardano in faccia.
3. ⚠️ **Riscrivere un corpo vecchio obbliga a guardarne i messaggi.** I tre guard
   di `fn_start_lotto_task_run` sollevavano `E_PARAMETRO_INVALIDO` con dentro
   «p_lotto_id obbligatorio e > 0». Ne è nato
   **`E_VENDITE_CHIAMATA_NON_VALIDA`**, gemello vendite del codice che
   `pagamenti` ha coniato **il giorno prima** per la stessa ragione. Due cantieri,
   due schemi, stesso criterio: è il segno che il criterio regge.

⏱️ **Controllo del §9.4, e l'impegno regge**: L5 non tocca `vendite.event_log` —
lavora su `fatturazione_lotti_task_runs` e `commesse_push_log`. La promessa era
sulla tabella del giornale, e la tabella del giornale non è stata toccata.

⚠️ **E due misure fatte di passaggio, scritte in §5-bis perché tacerle sarebbe
peggio**: il ruolo batch ha solo `SELECT` su `commesse_push_log` (non potrebbe
aprire un giro), e il trigger del `tx_id` **non è ancora nato** né lì né su
`event_log` — lo genera `ci_apply`, e sul migrate manuale arriva col pgagent.

### 2026-08-22 (ottavo giro) · ✅ L4 e L2 applicati — la fondamenta DB è posata

Applicati, autogen rigenerata, **baseline `vendite`+`rls` senza regressioni**.
I cinque pgTAP adeguati in anticipo sono **33 asserzioni verdi con zero skip** —
verificato leggendo il TAP, perché è l'unica cosa che una baseline non vede: un
file può passare *smettendo di verificare*.

⭐ **E il catalogo guida davvero il trigger**, non solo in teoria. Provato in
transazione:

```
config.tipi_entita     COMMESSA/FATTURA/LOTTO → giornalabili
                       TASK_RUN               → a catalogo, NON giornalabile

fn_log_event('PIPPO',    1, …) → «…di tipo «PIPPO»: sono ammessi COMMESSA, FATTURA, LOTTO»
fn_log_event('TASK_RUN', 1, …) → stesso rifiuto, stesso messaggio
```

Due cose che valgono più della riga verde:

* **l'elenco nel messaggio lo compone il catalogo**, non è più scritto nella
  frase: cresce da solo e non può invecchiare;
* **`TASK_RUN` è rifiutato pur essendo a catalogo**, ed è il disegno che
  funziona: il giornale ammette solo i tipi *con un modo*, il bersaglio tutto il
  catalogo. Le due letture non sono una teoria, sono due `WHERE` diversi sulla
  stessa tabella.

`event_log.domain`: **zero colonne**. La firma è a sei parametri.

⭐ **Cosa significa per §9.4.** L'impegno «L4 è l'ultimo intervento strutturale su
questo registro» **decorre da oggi**. La parte DB della fondamenta è posata: da
qui la tabella si tocca solo con un seed.
⚠️ E resta in piedi, intatto, il rischio 3 del §9.3 — **il modello non ha ancora
incontrato la realtà**. `event_log` ha zero righe perché il backend non è
allineato: nove consegne, zero fatte. Nessuna riga di documentazione può
chiudere quel punto.

### 2026-08-22 (settimo giro) · L4 e L2 scritti, e un `%TYPE` ricascato

L4 (8 changeSet) e L2 (2) scritti, più i **cinque pgTAP adeguati in anticipo**:
applicare L4 li avrebbe resi rossi, e qualcuno li avrebbe attribuiti alla
migrazione. Uno non era meccanico — `test-event-log-deriva-scope` agganciava la
frase `'%sono ammessi LOTTO, COMMESSA e FATTURA%'`, che ora la compone il
catalogo in ordine alfabetico.

Tre cose che il piano dava per buone e che scrivendo si sono rivelate sbagliate:

1. ⛔ **Il cancello dei codici evento non poteva essere il gemello di quello dei
   codici errore.** Quello legge `pg_proc` perché i codici errore li solleva il
   *database*; i codici evento li scrive *Python*. Una vista su `pg_proc`
   sarebbe tornata **vuota per sempre** — il peggior presidio, quello che dice
   sempre «tutto a posto» guardando nel posto sbagliato. Il changeSet 60 ha
   cambiato natura: è una **spia** sulla deriva già avvenuta, dichiarata
   data-dependent, e il cancello vero è **BE-9**.
2. ⛔ **Il changeSet della `fk_index_policy` non serviva, e registrarlo sarebbe
   stato dannoso**: la FK è su `entity_type`, già prima colonna di
   `ix_event_log_entity_time` — coperta *per prefisso* — e il `dll_command`
   avrebbe puntato il `DROP` su un indice **non dedicato**.
3. ⭐ **`entity_id = 0` non era un segnaposto**: la riga di `commesse_push_log`
   nasceva a *fine* giro, quindi era un id **che non esisteva ancora**. Un
   segnaposto è una convenzione da interpretare, un id inesistente è una
   sequenza sbagliata. Correggendola si guadagna anche una cosa non prevista:
   un giro **interrotto** smette di sparire.

⛔ **E un rilievo di Tid già ricevuto il 2026-08-21, ripetuto oggi**: `%TYPE`
mancante in firma e `RETURNS TABLE`. Il meccanismo ha un nome, ed è la ragione
per cui si ripete: **riprodurre il corpo vivo di una funzione porta con sé il
suo debito**, in una forma che sembra corretta perché combacia col database.
Sanato sul changeSet 59 — sette campi della `RETURNS TABLE` e due parametri,
con `pg_get_function_identity_arguments` e `pg_get_function_result` verificati
**byte-identici** al vivo, quindi nessun overload e nessun chiamante rotto.
⚠️ E una trappola dentro la trappola: mentre si ancora **non si riordina** la
`RETURNS TABLE` — cambierebbe l'ordine del result set, e `CREATE OR REPLACE` la
rifiuterebbe comunque.

### 2026-08-22 (settimo giro) · Allineamento post-apply, e un regalo ritirato

Riletto **contro il database** dopo l'apply di L1/L2/L4, e allineato ciò che era
rimasto al disegno:

* **§3.1** — la tabella «dopo» dava ancora `domain` presente e `entity_type` con
  il `CHECK`: oggi la colonna è **rimossa** e il vincolo è la **FK** al catalogo;
* **§3.2** — il blocco col `CASE` scritto a mano è marcato: il trigger legge il
  modo **dal catalogo** (changeSet 58), ed è il guadagno che la D-17 prometteva;
* **§3.5** — verificato l'ordine dei `BEFORE ROW`: i trigger in tabella sono
  **tre**, e ⏱️ **`trg_event_log_gen_tx_id_ins_upd` non è ancora nato** — lo
  genera l'automazione delle 21:00, e finché non c'è `tx_id` resta NULL;
* **§3.8** — il nome della vista: `vw_eventi_non_dichiarati`, non
  `vw_eventi_non_dichiarati`.

⛔ **E il «regalo» del §4-bis è stato ritirato** (rilievo del cantiere gemello):
i due codici di L1 non sono primi adottanti del bersaglio — uno porta per
definizione un tipo fuori catalogo, l'altro punta a un'entità inesistente, e sono
entrambi `TECNICO`. ⭐ **Al loro posto è nata una regola**, che vale più del
regalo: *il bersaglio si mette sugli errori rimediabili, mai sui `TECNICO`*.

### 2026-08-22 (sesto giro) · «È una fondamenta?» — e due scelte corrette

Domanda di Tid: *«siamo sicuri che sia definitiva? In venti giorni è già la
seconda volta sui log»*. Da lì il **§9**, che invece di rassicurare elenca cosa
ci riporterebbe qui — e ha prodotto due allargamenti (`domain`/`event_code`
governati; la vista cucitura cross-schema) più due impegni verificabili.

⭐ **La cosa utile è stata nominare il pattern**: le due volte sono lo **stesso
difetto** — una colonna di testo che tutti scrivono e nessuno governa — e lo
stesso registro ne aveva altre due nella stessa condizione. Chiuderle mentre la
tabella è già aperta è la differenza fra un terzo giro e nessuno.

🔴 **E un richiamo di Tid che ha corretto due scelte già scritte**: *«non abbiamo
produzione, decidiamo sempre la cosa migliore; i log attuali possiamo buttarli
se serve a costruire meglio»*. Avevo lasciato che i dati decidessero, due volte:

1. **`domain` "non si toglie perché l'indice e una funzione la usano"** →
   verificato: il filtro in `fn_list_lotto_segnalazioni` è **ridondante**
   (filtra già `event_code`), l'indice non serve a nessun accesso reale, e il BE
   deve comunque riscrivere le chiamate. ⛔ **La colonna si toglie** — tenerla
   sarebbe stato peggio: una copia derivabile che può dissentire dal catalogo;
2. **un'eccezione alla regola dei CSV** per seminare il catalogo prima della FK,
   *«perché su questo database `event_log` ha righe»* → il registro è **vuoto**,
   e se non lo fosse si azzera (D-4). ⛔ **Eccezione tolta.**

⚠️ Vale la pena tenerlo scritto: in entrambi i casi la misura era corretta e la
**conclusione** no. Un dato di sviluppo può dire cosa c'è, non cosa è giusto.

### 2026-08-22 (quinto giro) · Il catalogo dei tipi arriva qui

`brief-db-bersaglio-errore`, scritto lo stesso giorno da un altro tavolo, aveva
**deciso sulla nostra colonna**: `event_log.entity_type` doveva adottare un
catalogo chiuso (T-1/T-1b). Il suo registro aveva anche previsto il rischio —
*«stessa tabella, stessa funzione di scrittura: un apply solo, e chi arriva
secondo eredita il lavoro del primo»*. Il coordinamento non c'è stato, e **noi
avevamo già applicato la scelta opposta** (D-9, il `CHECK`).

⭐ **La collisione si è sciolta verso il loro disegno, e ha migliorato il nostro.**
La mia obiezione al catalogo era in due parti: la prima **cade** (il lucchetto
`require_attivo` lo genera `config.sorgenti` perché ha `attivo`; un catalogo
nuovo che deprechi con `obsoleto_dal` l'automazione lo salta), la seconda si
risolve **meglio** del `CHECK` — portando il modo di risoluzione nella stessa
riga del tipo, configurazione e trigger non possono più dissentire, e il `CASE`
scritto a mano nel trigger diventa inutile.

⭐ **E la scoperta che ha reso possibile unificare**: i due vocabolari **non sono
lo stesso insieme**. Quello del giornale è selezionato da *«l'emittente
dev'essere derivabile»* — per questo la D-3 ha espulso `TASK_RUN`; quello del
bersaglio da *«il frontend ha una rotta»*, e comprende i task run. Sottoinsieme
proprio, non insiemi diversi: **un catalogo solo, due letture**, distinte dalla
colonna `modo_risoluzione_emittente`.

⚠️ Trovata scrivendo il piano una trappola che nessuno dei due brief aveva:
`80_data` gira **dopo** `00_schema`, quindi la FK arriverebbe prima del seme —
invisibile su un DB ricostruito da zero, fatale su questo. Risolta nel L4.

*Decisione di Tid, 2026-08-22: via **B** (catalogo nuovo, sovrapposizione con
`config.sorgenti` dichiarata e non linkata), e assorbimento evidenziato su
entrambi i brief.*

### 2026-08-22 (quarto giro) · L1 applicato, e due difetti trovati dai test

L1 applicato (8 changeSet, 3 append a CSV) e **33 asserzioni pgTAP verdi con
zero skip**. I test hanno fatto il loro mestiere due volte:

1. ⛔ **Un difetto nel codice appena scritto** — changeSet **47**. Il changeSet
   43 si affidava al `CHECK` sulla colonna per intercettare un `entity_type`
   fuori vocabolario, ma **i `BEFORE ROW` girano prima dei `CHECK`**: il `CASE`
   cadeva a NULL e il risolutore rispondeva *«Parametro non valido: il modo di
   risoluzione dell'emittente «» non esiste»* — codice sbagliato
   (`E_PARAMETRO_INVALIDO`, che AGENTS.md vieta di riusare) e messaggio che
   nomina un concetto interno al database invece del dato passato, per giunta
   vuoto. Misurato in transazione **prima** di scrivere il test, corretto in
   avanti. Adesso dice: *«Il giornale non sa dove collocare un evento di tipo
   «PIPPO»: sono ammessi LOTTO, COMMESSA e FATTURA»*.

2. ⛔ **Due regressioni mie su test preesistenti**, entrambe sanate e **non**
   messe in baseline: `test-event-log-function-v1` chiamava la firma a nove e
   inventava gli `entity_id`; `test-fn-list-lotto-segnalazioni-job` inseriva
   `actor`/`source`. Il secondo, per inciso, contiene già la prova che il
   `correlation_id` è per-lotto e non per-giro (suo test 6) — cioè D-7 misurato
   da qualcun altro prima di noi.

⭐ E un file **non** scritto: quello sul canale batch, che duplicava un presidio
esistente e migliore (§6).

⚠️ **Fuori cantiere, trovato dalla baseline**: `fn_cleanup_fatture_by_ids`
esplodeva con un `23503` grezzo su una figlia di `fatture_righe` che nessuno
sorvegliava. Non c'entra con l'osservabilità e ha un brief suo,
[brief-db-guard-righe-fattura-rettificate.md](brief-db-guard-righe-fattura-rettificate.md).

### 2026-08-22 (terzo giro) · L1 scritto

Sette changeSet e tre append a CSV, elencati in §4. **Due cose che il piano non
aveva previsto**, emerse scrivendo:

1. ⭐ **`fn_log_event` andava rivista comunque** (changeSet 45). Il suo `INSERT`
   elenca `actor` e `source`: il `DROP COLUMN` riesce lo stesso — un corpo
   plpgsql non è tracciato come dipendenza dal DDL — e il difetto si sarebbe
   scoperto **alla prima scrittura**, con un «column does not exist» che non
   dice niente a nessuno. E togliendo parametri serve il **`DROP` esplicito**
   della firma vecchia: due firme con `DEFAULT` rendono ambigua ogni chiamata.
2. ⚠️ **La finestra di applicazione è vincolata.** Dopo il changeSet 40 il ramo
   push scrive `entity_type = 'TASK_RUN'`, che il `CHECK` non ammette: quelle
   scritture **falliscono**. È voluto (D-3 le sposta su `commesse_push_log`), ma
   vuol dire che **L1 e le consegne BE-1/BE-3/BE-4/BE-5/BE-7 vanno applicate
   nella stessa finestra**. Non applicare L1 su un ambiente il cui backend è
   indietro.

Su richiesta di Tid, verificato `%TYPE` in **firma, `RETURNS` e `DECLARE`**:
corretto `p_valore` di `fn_resolve_emittente_sr_id` (era `bigint` nudo) e
`v_auth_user_id` nel trigger. Restano deliberatamente senza `%TYPE` solo
`v_modo` (letterale di dispatch) e `v_ttl_days` (esce da un `jsonb`, non da una
colonna).

### 2026-08-22 (secondo giro) · Le sei domande, e un rilievo che ha rovesciato il disegno

Chiuse Q-1…Q-6 (§8). Cinque risposte hanno confermato il disegno; **una lo ha
cambiato**.

> Tid, sui lucchetti `require_attivo`: *«ma se invece di smettere di scrivere
> continuasse a scrivere segnalando anche l'anomalia? Se qualcuno continua a
> scrivere su una riga annullata c'è un problema, non è così?»*

Il rilievo è giusto e più forte di come era posto: un guard su un **diario** è
autolesionista — il fatto è già accaduto, e rifiutare la riga distrugge l'unica
prova che lo spiegherebbe. Verificando, l'anomalia temuta risulta **già bloccata
a monte** sui documenti, quindi il lucchetto sul diario avrebbe rifiutato **solo
righe legittime**.

Conseguenze, tutte nate da lì:

- nasce **D-12**, la regola in una frase: *il diario rifiuta solo ciò di cui non
  sa dire di chi è*;
- il lucchetto non si può disattivare per tabella (l'automazione gira su
  `*all`/`*all`, l'unico override è per tabella **padre**), quindi **si evita di
  crearlo**: **D-1** passa da `emittente_fiscale_id` a
  `emittente_soggetto_ruolo_id` (il padre non ha `attivo`) e **D-9** dalla FK a
  un `CHECK`;
- il disegno **si semplifica**: due changeSet in meno, `fn_resolve_emittente_fiscale_id`
  non va toccata, e la colonna diventa la stessa che usa tutta la famiglia vendite;
- ⚠️ **non** si segnala l'anomalia sulla riga: scatterebbe sul caso normale. Il
  presidio giusto sta sul documento, ed è di un altro documento.
