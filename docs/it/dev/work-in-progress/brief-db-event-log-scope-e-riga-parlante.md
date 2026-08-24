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
> **Stato:** ✅ **PIANO DB FINITO — L1, L4, L2, L5 e L3 applicati e verdi**
> (L1/L4/L2/L5 il 2026-08-22, L3 il **2026-08-23**). Ventidue changeSet,
> cinque CSV (L5 non ne apre di nuovi: appende ai due dei codici errore),
> **76 asserzioni pgTAP con zero skip**, baseline `vendite`+`rls`+`script` senza
> regressioni. ⭐ **La parte DB della fondamenta è posata**: §9.4 dichiarava L4
> come l'ultimo intervento strutturale su questo registro, e da qui in avanti la
> tabella si tocca solo **aggiungendo righe ai cataloghi**.
> ⭐ **L5 è la risposta a una richiesta del backend** (§5-bis): i changeSet 61 e 62
> avevano consegnato le **colonne**, e nessuna funzione le scriveva. Adesso le
> scrivono — ed è ciò che sblocca **BE-2** e **BE-3b**.
> ✅ **L3 — la vista `script.vw_giornale_entita` — è applicata** (changeSet
> **70**, 12 asserzioni verdi come applicazione).
> ✅ **E la domanda «lato DB è completo?» ha aperto un lotto in più: L6**
> (changeSet `20260823-06`, applicato il 2026-08-23, baseline `dbops` verde) —
> *una tabella che rifiuta di essere pulita non fa più morire l'intero giro del
> cleanup*. ⚠️ Resta
> aperta, e giustamente, la **retention dei due log gemelli** (§1.3): quella è
> una decisione di dominio, non un difetto — ma da L6 in poi la decisione di
> qualcun altro non può più rompere il lavoro di tutti.
> 🔵 Restano le sole **consegne BE** del §5. ⭐ E il rischio 3 del §9.3 — «il modello
> non ha ancora incontrato la realtà» — **si è mosso**: `event_log` non è più
> vuoto (12 righe scritte dalla pipeline vera), e quelle righe confermano
> insieme che la scrittura funziona e che **D-7 è ancora aperta**. Vedi il
> registro del 2026-08-23.
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
| 📋 **Il piano** | ✅ **Tutti e cinque i lotti applicati e verdi** — L1 · L4 · L2 · L5 (22/08) · **L3** (23/08), 22 changeSet: il piano DB è **finito** | §4 · §9.4 |
| 🔵 **A carico del BE** | 10 consegne, di cui **BE-1 è un difetto vero e vive già oggi** | §5 |
| ⭐ **La richiesta del backend** | I changeSet 61 e 62 avevano consegnato le **colonne**, e **nessuna funzione le scriveva**. L5 mette i due scrittori — e corregge una premessa della richiesta che era **falsa**, misurandola | §5-bis |
| 🧪 **Presidio** | ✅ **80 asserzioni verdi, zero skip** su 9 file — 5 nuovi/riscritti e 4 preesistenti adeguati. ⭐ E due asserzioni che passavano **dichiarandosi cieche** adesso verificano | §6 |
| ✅ **Passo A CONSEGNATO** | La scheda **«Storia»** del drawer fattura è in servizio: `GET /vendite/fatture/<id>/giornale/`, primo consumatore di `vw_giornale_entita`. ⭐ Il collaudo del perimetro è stato fatto **apposta**, perché i dati non lo avrebbero fatto: la vista da sola risponde «0 righe» dove l'endpoint dice «non la vedi». 🔵 Resta il **lotto**, rinviato: lì il pannello deve prima rispondere a «che cos'è un caso» | §12 |
| 🔵 **Da verificare, fuori cantiere** | Un prezzo **non negoziato sul contratto** dentro un push **riuscito** (ORD0016313): l'errore è in `error_log`, l'attività ha comunque un prezzo bloccato. ⚠️ È la categoria che nessuno controlla — un errore registrato dentro un'operazione andata bene | §11 |
| ✅ **Domande — tutte chiuse** | **La Q-7 è stata decisa il 2026-08-24: il filo è l'AZIONE DELL'OPERATORE**, non la passata. ⭐ A deciderla è stata una misura, non una preferenza: la lettura alternativa si reggeva sul `tx_id` come ripiego, e dentro una sola passata del lotto 6260 i `tx_id` sono **quattro**. 🔴 E la stessa distinzione ha scoperto un difetto **già vivo**: il filtro «Ultimo giro» delle segnalazioni taglia a metà un singolo click | §8 |
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
>
> ⛔ **E il danno era più largo di «quella tabella non si pulisce»** — rilievo di
> Tid, 2026-08-23. ⚠️ **Prima misura sbagliata, corretta**: avevo scritto che a
> ciclare sulle tabelle fosse `dbops.fn_purge_cleanup_expired`; quella funzione
> lavora su **una tabella sola** e il suo `LOOP` è il batch delle righe. Il ciclo
> vero è in **`dbops.fn_run_automations_cleanup`**, e lì il difetto c'era davvero:
> due cicli annidati (tabelle × regole) **senza nessun `EXCEPTION`**. Un solo veto
> e la funzione **muore lì**: le tabelle che venivano dopo, in quel giro, non
> venivano pulite affatto — e nessuno lo sapeva, perché non è un errore che
> qualcuno legge, è una cosa che *smette di succedere*.
>
> ✅ **Risolto il 2026-08-23 (lotto L6, changeSet `20260823-06`)**: una tabella
> che rifiuta viene **saltata**, e il rifiuto lascia una riga `ERROR` in
> `dbops.audit_log` con lo SQLSTATE. ⭐ Resta vero che la **retention** dei due
> gemelli non è decisa qui — quella è una scelta di dominio — ma da oggi la
> decisione di qualcun altro non può più rompere il lavoro di tutti.
> ⚠️ Il guard è `vendite.trgfn_logs_guard_delete` (non `script.`).

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
| **D-11** | La vista **`vw_giornale_entita`** si **disegna qui** e ~~si implementa al Passo A~~ ⏱️ **è stata implementata subito** *(2026-08-23, anticipo deciso da Tid)* | È la vista a decidere se `event_log` deve reggere tutto da solo o solo la sua parte — e quella decisione cambia cosa scriviamo nella riga, che è l'unica cosa non rifacibile. ⭐ L'anticipo regge su una misura: `event_log` ha 12 righe, gli altri tre registri **755** — la vista paga oggi, senza aspettare nessuno |
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

### 3.6 `script.vw_giornale_entita` — il disegno ✅ *(implementato il 2026-08-23, changeSet 70: vedi l'allineamento in coda)*

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

#### ⏱️ Allineamento post-scrittura *(2026-08-23, changeSet 70)*

Il disegno qui sopra regge; **quattro cose sono state decise scrivendo**, e
stanno qui perché il disegno da solo non le conteneva.

| | Cosa cambia rispetto a §3.6 | Perché |
| --- | --- | --- |
| ➕ | **Tre colonne tecniche** oltre ai sette concetti: `registro`, `riga_id`, `riga_key` | I quattro spazi di id **si sovrappongono**: senza la coppia (registro, id) non esiste nessuna chiave stabile per paginare, deduplicare o aprire la riga sorgente. ⭐ È la stessa scelta già fatta da `fn_list_lotto_segnalazioni` (`origine` + `riga_key`); qui la colonna nomina il **registro** e non l'entità, perché l'entità la dice già `entity_type` |
| 🔄 | `quando` del `task_run` = **`COALESCE(ended_at, started_at)`**, non `started_at` | La riga porta lo stato **finale** del tentativo: col solo `started_at`, un task durato tre minuti e finito male comparirebbe **prima** degli eventi che lo spiegano, già marcato `ERRORE`. Un tentativo ancora aperto ha solo l'avvio, e lì compare |
| ⭐ | La mappa della gravità **non ha `ELSE`** | Tre vocabolari chiusi da altrettanti `CHECK` entrano in uno. Un `ELSE 'INFO'` seppellirebbe un valore nuovo fra le righe innocue; senza, esce **NULL** e un'asserzione pgTAP lo vede. È la lezione del **L5** applicata *prima* che il danno accada |
| ⛔ | La vista **non filtra** `disabilitato` né `attivo` — ⚠️ *ma la prima stesura non lo ESPONEVA, ed era sbagliato (corretto il 2026-08-24, changeSet `20260824-13`)* | Un diario dice cosa è **successo**, non cosa è ancora aperto: il **non filtrare** regge. ⛔ Ma «non filtrare» e «non dire» sono due cose diverse, e confonderle lascia il consumatore senza niente in mano — **non si filtra ciò che non si vede**. Misura che l'ha deciso (fattura 19563): due righe con la **stessa frase**, la prima ritirata quando il lotto è stato rifatto ⇒ a video sembrano due errori, ed è uno. Adesso la colonna c'è; il `WHERE` continua a non esserci |

⛔ **E una trappola che vale la pena conoscere prima di toccare la vista**, e che
la doc auto-generata dichiara da sé: `security_invoker` è una **reloption**, non
si vede in `pg_get_viewdef`, e **va ri-specificata in ogni
`CREATE OR REPLACE VIEW`** — altrimenti PostgreSQL la azzera. Chi domani
aggiungesse un ramo copiando il corpo dalla doc auto-generata otterrebbe una
vista che gira come **proprietario**: il perimetro sparirebbe **tutto in una
volta**, senza un errore. ⭐ È il motivo per cui la **prima** asserzione del
pgTAP non collauda un dato ma una *proprietà dell'oggetto*: è l'unica cosa che
rende quella dimenticanza rumorosa.

⚠️ **E una cosa che la vista ha reso visibile senza risolverla: manca un
indice.** L'accesso vero è «la linea del tempo di *questa* entità», e l'`EXPLAIN`
dice due cose opposte: il filtro sul tipo **pota interi rami** (chiedendo un
`LOTTO`, il ramo `fatture_log` non viene nemmeno aperto — è il guadagno gratis
dei letterali), ma su `fatturazione_lotti_log` il filtro `lotto_id` fa un **seq
scan**: la FK è in `dbops.fk_index_policy` a `consentito = false`, ed è il
registro **più scritto** dei quattro (504 righe su 767).

⛔ **Non si crea l'indice a mano e non si ribalta la policy qui.** La policy è
opt-in per disegno, e L3 è la vista — non ancora un consumo. La decisione ha una
sede (il seed della policy) e un momento: il **Passo A**, quando l'endpoint
esisterà e si potrà misurare invece di indovinare. ⚠️ Se il Passo A arriva e
questa riga non è stata riletta, il difetto è qui.

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

### L3 — La vista — ✅ **APPLICATA il 2026-08-23**

> ⚠️ **Il piano diceva «si accende col Passo A, non prima», e la data è stata
> anticipata da Tid** *(2026-08-23)*. La ragione regge: è l'unica cosa in coda
> che **paga senza aspettare nessuno**. `event_log` ha 12 righe, ma gli altri
> tre registri ne hanno **755** — la vista produce qualcosa di leggibile oggi,
> non quando il BE si allineerà.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| ~~50~~ **70** | `create-vw-giornale-entita` | `20_code/script` | §3.6 · `security_invoker` · i quattro rami di D-16 · il `JOIN` alla testata come perimetro · la mappa della gravità **senza `ELSE`** |
| — | `db/pgtap/script/test-vw-giornale-entita.sql` | test | **12 asserzioni**, di cui due canarini (§6) |

⭐ **Cosa la vista mostra il primo giorno**, misurato prima di scriverla:

```text
event_log                        12 righe      ← il diario, appena ripartito
fatturazione_lotti_log          504            ← il racconto per fase
fatturazione_lotti_task_runs    249            ← ogni tentativo di ogni task
fatture_log                       2
                                 ───
                                 767 righe, 4 registri, gravità mai vuota
```

E la linea del tempo del lotto 6260 si legge davvero — la riga che spiega
l'ultima corsa è un `TASK_RUN` in `ERROR`
(`numera_fatture · ERRORE · E_FATTURA_RETTIFICATA_SENZA_NUMERO`), seguita dalle
righe di fase e dai tre eventi della pipeline. **Nessuno dei quattro registri,
da solo, la raccontava.**

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

---

### L6 — «una tabella che rifiuta non ferma il giro» — ✅ **APPLICATO il 2026-08-23**

> ⚠️ **Non era in piano, e non è un ripensamento: è un rilievo di chiusura.**
> Alla domanda «lato DB è completo?» la risposta elencava fra le cose aperte la
> retention dei due log gemelli. Tid ha visto il punto vero: *«bisogna risolvere
> almeno il fatto che le tabelle col lucchetto non blocchino l'intero processo,
> ma siano saltate»*. Ha ragione — e sono due problemi diversi, non uno.

| # | File | Fase | Cosa |
| --- | --- | --- | --- |
| **20260823-06** | `update-fn-run-automations-cleanup-resiliente` | `20_code/dbops` | Una tabella che rifiuta viene **saltata**; il rifiuto lascia una riga `ERROR` in `audit_log` con SQLSTATE e contesto (`skip_reason = BLOCKED_BY_TABLE`) |
| — | `db/pgtap/dbops/test-cleanup-framework.sql` | test | **12 → 16 asserzioni**, col guard **vero** dei log gemelli |

⚠️ **Il numero è `06` e non `03`**: mentre scrivevo, il cantiere del bersaglio
ha preso 03, 04 e 05. Il file è stato rinumerato **prima** dell'apply — id,
`logicalFilePath` e nome del file insieme, che è l'unico modo di farlo senza
lasciare a Liquibase due verità.

**I due problemi, che vanno tenuti separati:**

| | Chi decide | Stato |
| --- | --- | --- |
| *Quanto a lungo deve vivere la storia di una fattura* | il **dominio** (ha implicazioni fiscali) | 🟡 aperto, e giusto che lo sia |
| *Se la scelta di una tabella possa rompere il giro di tutte le altre* | il **framework** | ✅ chiuso da L6 |

⭐ **La cura è il quarto membro di una famiglia che esisteva già.** La funzione
sapeva già saltare una tabella e dirlo — `EXCLUDED`, `NO_CLEANUP_COLUMN`,
`MISSING_TTL_DAYS`, `MISSING_BASE_TS_COLUMN`, ognuno con la sua riga `WARN` in
`audit_log`. Mancava il caso «la tabella si è opposta». Non è un `try/catch`
appiccicato sopra: è il ramo che quella famiglia non aveva. ⭐ E il canale era
già pronto: `fn_audit_log_once` ha da sempre `p_sqlstate` e `p_error_context`, e
qui non li usava nessuno.

**Due scelte dentro il rimedio**, entrambe verificate dal test:

1. **`ERROR` e non `WARN`.** I `WARN` di questa funzione sono salti
   **dichiarati**: cose che qualcuno ha deciso. Questo non è dichiarato — è una
   tabella che si è opposta — e deve distinguersi a colpo d'occhio. In
   `audit_log` le righe `ERROR` oggi sono **zero**: la prima che comparirà vorrà
   dire qualcosa.
2. **`query_canceled` si ri-solleva.** Se qualcuno ferma il job, il job si
   ferma: inghiottire un annullamento trasformerebbe uno stop in un giro che
   finge di lavorare.

⚠️ **Il costo, detto:** ogni regola gira ora in una **sottotransazione** — è ciò
che un blocco `EXCEPTION` implica in PL/pgSQL. Su qualche centinaio di tabelle
non si misura.

🧪 **La controprova, misurata prima e dopo** — perché un test che non sa
fallire non prova niente:

```text
senza questa revisione → not ok 13, 15, 16   (e la 14 VERDE: il veto morde davvero)
con questa revisione   → 16 su 16
```

⭐ **E il test ha trovato un secondo difetto, suo.** Le due asserzioni
sull'orchestratore erano **cieche**: `dbops.automation_scope` elenca per lo
schema `dbops` tre sole tabelle, quindi quella di prova restava fuori e le
asserzioni cadevano nel ramo `ok(true, 'Scope non include tabella test')`.
Verdi **per dichiarazione di cecità**, da sempre: l'orchestratore non era
esercitato mai. Adesso la fixture mette in scope le proprie tabelle — ed è la
stessa classe di difetto del §6 di questo brief, *un file che passa smettendo di
verificare*.

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

> ⏱️ **Stato rimisurato il 2026-08-24** sul codice del backend e sul database,
> non riletto da questa tabella. ⭐ **Otto consegne su undici sono fatte** — il
> BE si è mosso in fretta — e le tre che restano sono tutte piccole.
>
> | | Consegne |
> | --- | --- |
> | ✅ **fatte** | **BE-1** (`severity="WARN"`) · **BE-3** (il repository apre e chiude il giro) · **BE-4** (`entity_type="COMMESSA"`) · **BE-5** (la chiamata è a **sei** parametri) · **BE-6** (il BB unico esiste: `apps/vendite/db/_event_log_repo_mixin.py`) · **BE-7** (il telaio, **12** punti d'uso nei service `vendite`) · **BE-9** (il cancello dei codici evento c'è, e il catalogo è seminato) |
> | 🟡 **scritta, ma mai esercitata** | **BE-2** — l'`uuid` per giro c'è in entrambi i posti giusti (`pipeline_runner.py:671`, `commesse_push_orchestrator.py:213`). ⛔ **Ma `event_log` ha ancora solo le 12 righe del 22/08, con UN filo solo**: dopo l'allineamento **nessuna corsa è stata eseguita**. Il codice c'è, la prova no — e costa una corsa sola |
> | 🟡 **fatta per 21 codici su 22** | **BE-10** — le policy sono state rigenerate, ma **prima** che arrivasse `E_DIAGNOSTICA_NON_REGISTRATA` (987): quel codice manca ancora dal file generato. Si chiude insieme a BE-11, stesso comando |
> | 🔵 **non iniziate** | **BE-11** (la costante è ancora su `E_PIPELINE_MARK_ERROR` — consegnato ieri sera, è normale) · **BE-8** (il `request_id` esiste come contextvar in `request_context_middleware`, ma il formatter di logging non lo raccoglie: nei `settings` non compare) |
>
> ⭐ **La cosa che vale la pena vedere**: le sette fatte sono tutte quelle che
> *si scrivono*. Le due che restano aperte sul giro — BE-2 e il suo esercizio —
> sono quelle che *si dimostrano*, e nessuna riga di codice le chiude al posto
> di una corsa vera. È il rischio 3 del §9.3 nella sua forma finale.

> **Perimetro DB:** questo cantiere non modifica `backend/`. Le richieste si
> scrivono, non si implementano.
>
> ✅ **CHIUSO AL 2026-08-24 — dodici consegne su dodici.** Nessuna riga di
> questa tabella è più aperta. Le due nate misurando e non previste dal piano
> originale (**BE-10**, il registro delle policy; **BE-11**, il codice che aveva
> smesso di dire la verità) sono dentro il conto.
>
> ✅ **E «fatto» vuol dire anche «visto funzionare»**, dal 2026-08-23: quattro
> corse vere di pipeline (lotti 6260 e 7132) hanno scritto **21 righe** con
> perimetro derivato, `auth_user_id`, `tx_id`, `cleanup_at` a 750 giorni e — il
> punto di BE-2 — **un `correlation_id` diverso per corsa**, condiviso coi
> `task_runs`. Il rischio 3 del §9.3 è chiuso.
>
> ⛔ **E il giro vero ha trovato un difetto che i test non vedevano**: sul lotto
> 6260, `set_lotto_job_stato` è stato rifiutato («Transizione non ammessa:
> COMPLETATO → ERRORE») e l'eccezione usciva **prima** che il diario venisse
> tentato — `PIPELINE_ERROR` non veniva scritto. Corretto: marcatura e diario
> sono ora **due passi indipendenti**. Dettaglio in **BE-7**.
>
> ✅ **E il ramo push commesse è stato esercitato anche lui** (2026-08-23,
> 23:27, push di ORD0016313): `commesse_push_log` **1506** nasce e si chiude in
> 75 ms — `stato = COMPLETATO`, non rimasta `IN_ESECUZIONE` — col
> `correlation_id` e il `tx_id` valorizzati. ⭐ Il **perimetro non si è perso**
> togliendo `PUSH_STARTED`: `risultato.perimetro` porta `sorgente_uid = 16824` e
> `source_types = [ORDINE_VENDITA]`. E ⛔ **zero righe in `event_log`**: nessun
> `TASK_RUN` ha provato a entrare nel giornale, che è il difetto da cui il
> cantiere è partito. **Entrambi i rami sono ora verificati sul campo.**
>
> ✅ **Stato al 2026-08-22 (sera), scritto dal backend.** Sette consegne su nove
> fatte in un primo giro — BE-1, BE-3a, BE-4, BE-5, BE-6, BE-7, BE-9 — e le
> ultime due, **BE-2** e **BE-3b**, chiuse appena il team DB ha consegnato i
> due scrittori mancanti (changeSet **67, 68, 69**). ⭐ **Nove su nove.**
> Il prerequisito e la sua richiesta sono in
> [brief-db-scrittori-del-giro-push-e-task-run.md](../work-done/brief-db-scrittori-del-giro-push-e-task-run.md),
> ora in `work-done`.
>
> ⭐ **Il rischio 3 del §9.3 è chiuso a metà**: il registro ha di nuovo delle
> righe scritte dal backend vero — perimetro derivato, `cleanup_at` a 750
> giorni, entrambi verificati contro il DB. Resta aperto il `correlation_id`,
> che è la parte che dipende da BE-2.
>
> ⚠️ **E una consegna che questo §5 non elencava** — la **BE-10** che L5
> nomina: `error_policies_generated.py` va rigenerato dopo ogni seed di codici.
> Fatta due volte, ai due giri. ⭐ Un codice errore nuovo costa **due** cose
> lato BE, non una: la policy generata **e** il messaggio di ripiego senza
> `%s` (`error_messages_fallback.py`) — il secondo verso lo presidia
> `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, ed è quello che si
> dimentica.
>
> ⛔ **Il `tx_id` resta NULL**, riverificato dopo L5: `event_log` e
> `commesse_push_log` non hanno il trigger `..._gen_tx_id_*`. Coerente con
> §3.5 — lo attacca l'automazione in `ci_apply`. **La D-5 è viva come colonna,
> non come dato**, e finché è così `event_log` non si aggancia a `error_log`.
>
> ⚠️ **E il GRANT del canale batch è confermato dal vivo**: aperto un giro di
> push dentro `system_process_context(alias='system_fatturazione')`, il DB
> risponde *«permesso negato per la tabella commesse_push_log»*. Oggi non morde
> — il push gira come `zeroerp_app` — ed è esattamente la misura scritta nel
> §5-bis.

| # | Consegna | Blocca? |
| --- | --- | --- |
| ~~**BE-1**~~ | ✅ **FATTA** *(verificato il 2026-08-23: `commesse_service.py:243` scrive `severity="WARN"`)*. Era il difetto già vivo del §1.2: `EMITTIBILITA_FALLITA` non era mai scrivibile | — |
| ~~**BE-2**~~ | ✅ **FATTA** *(2026-08-24)*. `pipeline_runner` conia un `uuid4()` **a ogni corsa** — non più il `lock_batch_id`, che nasce col lotto e non cambia mai — e lo passa a eventi, `task_runs` (via lo step executor, anche sul ramo di rollback automatico) e `commesse_push_log`. ⭐ Il filo viaggia anche **con l'eccezione**, così il tentativo FALLITO — riscritto fuori transazione — non è l'unico del giro senza. Presidiato da un test che fa **due corse sullo stesso lotto** e le confronta: una corsa sola non distinguerebbe le due implementazioni. ✅ **E la prova sul campo c'è**, 2026-08-23: quattro corse vere, **quattro `correlation_id` distinti** — due sullo stesso lotto 6260 a cinque secondi di distanza, che col `lock_batch_id` sarebbero stati identici. I `task_runs` portano lo stesso filo dei loro eventi (4 tentativi per filo) | ~~~~Sì, dopo L2~~ → **sbloccata**~~ → **chiusa** |
| ~~**BE-3**~~ | ✅ **FATTA** *(2026-08-23/24)*, in due metà. **3a**: `PUSH_STARTED`/`PUSH_COMPLETED` **fuori** da `event_log`; `sorgente_uid`/`righe_ids` non si perdono — scendono in `risultato.perimetro`, che prima vivevano solo nel payload dell'evento. **3b**: `log_push_run` spezzata in `start_push_run` (in testa) e `close_push_run` (in coda). Verificato dal vivo: apertura `IN_ESECUZIONE`, chiusura `PARZIALE`, e i due rifiuti che rispondono come devono. ⚠️ Nel push **singolo** la riga rolla con l'`atomic` esterna: il guadagno «un giro interrotto non sparisce» vale sul **batch** | ~~~~Sì~~ → **sbloccata, e ora è un breaking**~~ → **chiusa** |
| ~~**BE-4**~~ | ✅ **FATTA** *(2026-08-23)*. Una riga per commessa fallita, `entity_type='COMMESSA'`, legata alla commessa di cui parla — invece di un evento aggregato appeso a un giro, con dentro la lista degli id. ⭐ L'aggregato era sbagliato **prima ancora del perimetro**: chi apre la commessa 812 vuole vedere che il suo push è fallito, non pescare il proprio id da una lista che sta altrove | ~~Sì~~ → **chiusa** |
| ~~**BE-5**~~ | ✅ **FATTA** *(2026-08-23)*. Sette call site allineati alla firma a **sei**. ⭐ Un solo adeguamento e non due, perché è viaggiata insieme a **BE-6**: la firma si è riscritta in **un** posto | ~~Sì~~ → **chiusa** |
| ~~**BE-9**~~ | ✅ **FATTA** *(2026-08-23)*, e **più larga del richiesto**. I cinque codici erano già a catalogo; il cancello è `apps/core/tests/test_event_codes_declared_guardrail.py`, che legge il **CSV in git** (non il DB: così gira anche senza database). ⭐ Poi **esteso a `entity_type`** il 2026-08-24: era l'ultima stringa che nessuno guardava, e un refuso passava ogni cancello per fallire a runtime. Il criterio non è «esiste a catalogo» ma «esiste **e ha un modo**» — `TASK_RUN` è a catalogo e viene respinto lo stesso. Verificato che morda su entrambi i casi | ~~No, ma rompe la CI~~ → **chiusa** |
| ~~**BE-6**~~ | ✅ **FATTA** *(2026-08-23)*. `EventLogRepositoryMixin` (`db/_event_log_repo_mixin.py`): le due copie carbone sono sparite. ⭐ Fatta **prima** di BE-5 e non dopo, ed è la ragione per cui la firma a sei si è scritta una volta sola | ~~No, ma è il momento giusto~~ → **chiusa** |
| ~~**BE-7**~~ | ✅ **FATTA** *(2026-08-23/24)*. Tutte e **cinque** le scritture di diario passano dal telaio, ora in `apps/core/services/diagnostica_best_effort.py`. ⛔ **E il telaio da solo non bastava, due volte.** (1) Serviva un **savepoint**: in PostgreSQL ingoiare l'eccezione non recupera una transazione abortita, quindi il `try` spostava solo il punto di rottura. (2) In `_mark_lotto_error` il diario stava **dentro** l'`atomic` della marcatura: una riga rifiutata rollava indietro anche lo stato `ERRORE` del lotto, e il telaio ingoiava — **il diario rotto distruggeva ciò che doveva descrivere**. Trovato rivedendo il codice, corretto, e presidiato da un test che confronta gli **id dei blocchi transazionali** (l'ordine delle chiamate non distingueva le due versioni). ⭐ **(3) E un terzo, trovato da un giro VERO il 2026-08-23** (lotto 6260): `set_lotto_job_stato` rifiutato con «Transizione non ammessa: COMPLETATO → ERRORE» — il lotto era già COMPLETATO da una corsa precedente — e l'eccezione usciva **prima** che il diario venisse tentato. `PIPELINE_ERROR` non veniva scritto: dell'unico giro andato storto non restava traccia nel registro fatto apposta per raccontarlo. È lo **specchio** del (2): là la marcatura moriva per colpa del diario, qui il diario moriva per colpa della marcatura. Ora sono **due passi indipendenti**, e li chiude la stessa regola — la **D-12** | ~~Sì, di fatto~~ → **chiusa** |
| ~~**BE-8**~~ | ✅ **FATTA** *(2026-08-24)*, ed era l'ultima consegna aperta. **(a)** `req=%(request_id)s` è ora nel formatter, messo da un filtro (`apps/core/logging_filters.py`) agganciato a **ogni** handler: la correlazione diventa una proprietà del canale di log, non una disciplina di chi scrive. Fuori da una richiesta vale `-`. ⭐ E l'unico punto che se lo scriveva a mano — `api.exception` — è stato **ripulito**: stampava la stessa informazione due volte. **(b)** `emittente_attivo_id` **si collega**, letto dalla GUC `app.current_emittente_id` dentro la `INSERT`. Verificato dal vivo: senza emittente in sessione → `NULL`, con emittente 7 → `7`. **(c)** ⛔ `tx_id` **non si può collegare da qui** — vedi sotto | No |
| ~~**BE-11**~~ | ✅ **FATTA** *(2026-08-24)*. `CODICE_DIAGNOSTICA_FALLITA` vale **`E_DIAGNOSTICA_NON_REGISTRATA`**, la voce è in `error_messages_fallback.py` e le policy sono rigenerate. Provato dal vivo, non solo in test: `dbops.error_log` → `E_DIAGNOSTICA_NON_REGISTRATA · vendite.commesse_service.pr_run_commesse_push · commessa_id 812`. ⭐ **`E_PIPELINE_MARK_ERROR` (699) non è più sollevato da nessuno**: il suo `obsoleto_dal` si può mettere, ed è l'ultimo passo di §5-ter | — |
| ~~**BE-10**~~ | ✅ **FATTA**, e rifatta a ogni seed *(2026-08-22, 08-23, 08-24)*. `error_policies_generated.py` è allineato: **778 codici, gli stessi del catalogo DB**, zero divergenze e zero classi cambiate — verificato coppia per coppia a ogni rigenero. ⭐ E la consegna ha una **seconda metà** che il §5 non nominava: un codice nuovo vuole la policy **e** il ripiego senza `%s` in `error_messages_fallback.py`. Misurato oggi: **694 codici vivi, 694 ripieghi, zero mancanti**. È il secondo verso che si dimentica, e lo presidia `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | No, ma rompe la CI |

### ✅ ~~`dbops.request_log.tx_id` non si può riempire, e va tolta~~ — **TOLTA** *(2026-08-24)*

La consegna BE-8 diceva «o si collegano o si tolgono». **`emittente_attivo_id`
si è collegata; `tx_id` no**, e non per pigrizia — dalla sede in cui la riga si
scrive quel valore **non esiste più**:

| | |
| --- | --- |
| Chi scrive la riga | `RequestLogMiddleware._insert_log`, **dopo** che la risposta è partita |
| Quando | la transazione di lavoro ha **già chiuso** |
| Da dove verrebbe il `tx_id` | la GUC `dbops.tx_id` — misurata **vuota** in una sessione applicativa |
| E la tabella | ⛔ **non ha nessun trigger**, quindi `dbops.trgfn_tx_id_managed` non la tocca |

⭐ **Un valore coniato adesso legherebbe la riga a sé stessa e a nient'altro** —
che è la definizione di un filo che non lega, la stessa ragione per cui
`fn_start_commessa_push_run` non genera un `correlation_id` d'ufficio.

➡️ ✅ **Fatto dal team DB il 2026-08-24**, `DROP COLUMN` eseguito. Il backend non ne è stato toccato — l'`INSERT` non nominava quella colonna — ma i commenti che la descrivevano come «da togliere» sono stati allineati, e l'asserzione del test **cambia natura**: non è più una preferenza di disegno, è un presidio sullo **schema** (nominarla adesso farebbe fallire l'INSERT).

⛔ ~~Richiesta al team DB: `ALTER TABLE dbops.request_log DROP COLUMN tx_id`.~~
Zero righe valorizzate su 354.595, quindi non si perde niente. ⚠️ Se invece si
volesse *tenerla*, il collegamento non è un lavoro di backend: la riga andrebbe
scritta **dentro** la transazione di lavoro, cioè da un'altra parte e con un
altro disegno.

### ⭐ E la gemella non era morta — la stava già riempiendo BE-8

⚠️ **Misura da non ripetere male.** Il piano diceva «`emittente_attivo_id` e
`tx_id` sono **due colonne morte** (0 valorizzate su 353.758)», e il team DB ha
rimisurato la prima **dopo** l'apply: **667 valori alle 23, 1.096 alle 2** —
1.099 al controllo successivo. Non è un residuo di un middleware vecchio: è una
colonna che **qualcuno sta scrivendo adesso**, e quel qualcuno è **BE-8**.

⭐ Il «0 su 353.758» fotografava un giorno in cui la colonna era davvero morta.
È la ragione per cui il `DROP` si è deciso sulla misura **di oggi** e solo sulla
gemella: due colonne che sembravano lo stesso caso hanno avuto due esiti opposti
nel giro di poche ore, e a distinguerle è stata una misura ripetuta — non la
riga di un piano.

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
| ⚠️ **Il ruolo batch non può aprire un giro di push** — ⭐ *e non si concede in anticipo (2026-08-24)* | `zeroerp_batch_fatturazione` ha su `commesse_push_log` il solo grado **`r` (SELECT)**, che gli arriva dal `GRANT SELECT ON ALL TABLES` dello schema; su `fatturazione_lotti_task_runs` ha `arw`. Oggi non è un difetto — il push gira come `zeroerp_app` — ma il giorno che passasse sul canale batch, l'apertura fallirebbe sul **GRANT**, non sulla RLS. E un `BYPASSRLS` non aiuta: salta le policy, non i permessi. È lo stesso disallineamento del precedente `vendite.note`. ⛔ **Ma il DML non si aggiunge adesso**, ed è il provisioning script a dirlo: il perimetro di scrittura è per-tabella e graduato (`iud`/`iu`/`i`/`u`/`d`), e *«una tabella nuova non concessa fallisce RUMOROSAMENTE (permission denied): quando la pipeline scrive una nuova tabella, aggiungere la riga nel grado giusto»*. Concedere a chi non scrive spegnerebbe l'unico allarme previsto. Il giorno che il push passa sul canale batch, il grado è **`iu`** — INSERT per l'apertura, UPDATE per la chiusura |
| ✅ **Il `tx_id` è attaccato — ⚠️ ma non alle righe già scritte** | ~~Né `commesse_push_log` né `event_log` hanno il trigger~~ → **rimisurato il 2026-08-23: ci sono entrambi** (`trg_event_log_gen_tx_id_ins_upd`, `trg_commesse_push_log_gen_tx_id_ins_upd`), li ha generati il pgagent come previsto, e una riga **nuova** prende il suo `tx_id`. ⛔ **Le 12 righe già scritte restano NULL per sempre**: la tabella è append-only e il backfill non esiste — è il prezzo dichiarato in §1.3, non un difetto da correggere. Chi guarderà *quelle* righe non troverà il ponte verso `error_log`; se un giorno desse fastidio, l'unica via è quella già usata una volta (azzerare) |
| ⚠️ **La baseline B-7 dei codici errore è indietro, e non la aggiorno io** | Il cancello è **verde** (`accumuli nuovi: 0`), ma `db/baseline-codici-errore-famiglie.tsv` è fermo al cantiere che l'ha creata: rigenerarla oggi farebbe entrare **9 righe di tre cantieri diversi** — le mie due (`E_VENDITE_CHIAMATA_NON_VALIDA` → `PARAMETRO`, `E_COMMESSA_PUSH_RUN_NON_APERTO` → `NOT_FOUND`), quelle di `pagamenti` e quella del pricing. ⭐ Il file dice di sé che aggiornarlo *«è una DECISIONE, non una formalità: ogni riga che cambia dice che un codice ha cambiato significato»*: prendere quella decisione per conto di altri due cantieri sarebbe il modo di svuotarla di senso. Va fatta in **una passata sola e deliberata** |

---

## 5-ter. ⭐ La seconda richiesta del backend — un codice che aveva smesso di dire la verità

> **Cosa chiedeva** *(2026-08-23)*. Il telaio best-effort del BE
> (`diagnostica_best_effort.py`, la D-15 realizzata) marca i propri guasti con
> `CODICE_DIAGNOSTICA_FALLITA = "E_PIPELINE_MARK_ERROR"`. Da quando il telaio
> serve **anche il push commesse**, quel codice mente due volte.

| | Cosa mentiva | |
| --- | --- | --- |
| **il nome** | dice `PIPELINE`, ma raccoglie anche i guasti del diario del **push** | chi cercasse per codice i problemi del push **non li troverebbe** |
| **la classe** | `DATO_ERRATO` → **400** | ma qui non c'è nessun dato sbagliato di nessuna persona: è un guasto interno, e chi ha fatto la richiesta non può farci niente |

✅ **Consegnato: `E_DIAGNOSTICA_NON_REGISTRATA`, classe `TECNICO`** (messaggio
**987**). ⛔ **Nessun changeSet**: i codici errore si aggiungono **solo** in
append ai due CSV, e i mirror `runOnChange` li rileggono a ogni migrate.

⭐ **Perché «non registrata» e non «fallita»** — che sarebbe stato il calco del
nome della costante: *fallita* dice solo che qualcosa non ha funzionato, *non
registrata* dice **che cosa non è successo**. In un log tecnico serve la
seconda. Il legame con la costante del BE è scritto nella `note` del codice, così
chi cerca da una parte trova l'altra.

⭐ **Ed è volutamente UNO SOLO per tutte le sedi.** La tentazione sarebbe un
codice per punto di scrittura; ma ciò che identifica il guasto è il
**`function_name`** — che ogni chiamante passa specifico — più il contesto, dove
la causa vera viaggia nella chiave `mark_error`. Verificato con la chiamata
esatta del telaio (`log_error_only`, VARIADIC vuoto):

```text
backend · vendite.commesse_service._push_una_commessa · E_DIAGNOSTICA_NON_REGISTRATA
   messaggio:  Una scrittura di diagnosi non e' andata a buon fine: il lavoro e' proseguito lo stesso.
   causa vera: chk_event_log_severity violato        ← context->>'mark_error'
```

⚠️ **Il messaggio non ha segnaposto, e non è un caso**: il telaio logga senza
valori, e un `%s` senza qualcosa da metterci dentro è la trappola dell'arità già
registrata (`W_MESSAGGIO_ARITA`).

⛔ **`E_PIPELINE_MARK_ERROR` NON si ritira adesso.** L'`obsoleto_dal` si mette
quando il BE avrà spostato la costante: **un codice ritirato che qualcuno
solleva ancora è peggio di un nome che mente**. È BE-11, e il ritiro è il passo
DB che segue — non lo precede.

---

## 6. Il presidio pgTAP — ✅ **80 asserzioni verdi, zero skip**

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
| `db/pgtap/dbops/test-cleanup-framework.sql` | 16 | *(L6)* **Esteso di quattro** (era 12). ⭐ E le due asserzioni sull'orchestratore erano **cieche**: la tabella di prova restava fuori da `automation_scope` e cadevano nel ramo «ok(true, scope non include tabella test)». Da oggi verificano |
| `db/pgtap/script/test-vw-giornale-entita.sql` | 12 | *(L3)* **Nuovo.** Due asserzioni non collaudano la vista di oggi: sono **canarini** — la gravità mai vuota e l'asse che resta il catalogo. Si accendono il giorno che un `CHECK` si allarga o che un registro cita un tipo che il catalogo non conosce |

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

## 8. Domande — **tutte chiuse**: le sei del primo giro e la Q-7

| # | Era | Come si è chiusa |
| --- | --- | --- |
| **Q-1** | Il `ttl_days` di `event_log` (i 30 giorni della regola `*all` coprivano solo il mese in corso) | ✅ **750 giorni** — D-13. La data si scrive nella riga e non è più modificabile: sbagliare per eccesso è recuperabile, per difetto no |
| **Q-2** | «Chi»: il nome (`user_insert`) o il numero? | ✅ **Tutti e due** — D-14. Il nome si legge senza cercare, il numero regge a un rename |
| **Q-3** | Un difetto del diario può far fallire il lavoro? | ✅ **Fail-loud nel DB, best-effort nel BE** — D-15. E la riga nel log tecnico è la differenza fra «best-effort» e «silenzio» |
| **Q-4 · Q-5** | I lucchetti `require_attivo` verso `config.sorgenti` e `emittenti_fiscali` spegnerebbero il diario | ✅ **Rovesciata da un rilievo di Tid**: *«invece di smettere di scrivere, non dovrebbe continuare e semmai segnalare?»*. Risposta: sul diario **non si blocca mai** (D-12), e il lucchetto non si disattiva — **si evita di crearlo**, scegliendo la colonna SR (D-1) e il `CHECK` invece della FK (D-9). ⚠️ Non si segnala nemmeno: l'avviso scatterebbe sul caso normale |
| **Q-6** | Quali sorgenti nella vista | ✅ **Quattro** — D-16, con `attivita_fatturabili_log` fuori e il motivo scritto nella vista |
| ~~**Q-7**~~ | ✅ **CHIUSA (Tid, 2026-08-24): il filo è l'AZIONE DELL'OPERATORE**, lettura (b) — `run_lotto_pipeline_until_done` conia il `correlation_id` **una volta** e lo passa a tutta la catena; alla domanda *«in quale passata?»* risponde il `task_run`, che quel livello ce l'ha già | ⭐ **La domanda l'hanno posta i dati, non il piano.** Rendendo definitivo LTF-0006586, un **solo** click su «Fattura» ha prodotto **due** giri (`c92b1cf5` alle 23:11:13 e `9084ac2b` alle 23:11:14): `until_done` incatena più corse e ognuna coniava il suo filo — il campo rispondeva a *«in quale passata?»*, **non** a *«cosa ha prodotto il mio click?»*. ⛔ **A decidere è stata una misura, non una preferenza.** La lettura (a) — tenere la grana fine, *«tanto per risalire al click c'è il `tx_id`»* — **non regge**: sul lotto 6260, dentro **una sola passata**, i `tx_id` sono **quattro** (`…0e2a`, `…0f00`, `…9f07`, `…c727`). Il brief sospettava che il `tx_id` tenesse *«per come è caduta la transazione, non per garanzia»*: adesso è misurato che non tiene affatto. Scegliendo la (a), l'azione dell'operatore sarebbe rimasta **senza nessun identificativo** |

### 🔴 La conseguenza della Q-7 è già viva: «Ultimo giro» taglia a metà un click

> **Trovato il 2026-08-24 verificando la Q-7 sui dati**, e non è una previsione:
> è un difetto di ciò che è già in servizio. Sta qui e non altrove perché è la
> stessa cosa che la Q-7 descrive, vista dal lato di chi guarda lo schermo.

Il terzo tab del drawer del lotto ha un filtro **«Ultimo giro»**, e il conteggio
che lo accompagna dice *«+N di corse precedenti»*. L'ancora è l'`event_time`
dell'**ultimo `PIPELINE_STARTED`** (`fn_list_lotto_segnalazioni`) — dichiarata
così di proposito: ⛔ **non** il `correlation_id` (all'epoca era il
`lock_batch_id`, condiviso da due corse), **non** il `tx_id`, **non** il
`tentativo`.

⛔ **Ma «ultimo giro» e «ultima cosa che ho fatto» non sono la stessa cosa**, ed
è esattamente la distinzione della Q-7. Misurato sul lotto **7133**:

```text
01:11:13.970   filo c92b1cf5   tx 01a030e4-7645   ┐ un SOLO click su «Fattura»
01:11:14.160   filo 9084ac2b   tx 01a030e4-7701   ┘
01:18:52.339   filo 93e74f2c   tx 01a030eb-74cf     click diverso
```

Quel click ha scritto **12 righe** in `fatturazione_lotti_log`. L'ancora è il
`PIPELINE_STARTED` più recente, cioè `01:11:14.160`: con «Ultimo giro» attivo
l'operatore ne vede **6** e ne perde **6** — e le sei nascoste sono **la prima
metà di quello che ha appena fatto lui**. Il contatore annuncia *«+6 di corse
precedenti»*, che è **falso**: non è una corsa precedente, è la stessa azione.

⚠️ **E nemmeno il `tx_id` le riunisce** (`…7645` contro `…7701`): prima della
Q-7 non esisteva **niente** che identificasse il click. È lo stesso buco,
osservato da due punti diversi — di qua rende il campo ambiguo, di là rende un
filtro bugiardo.

⭐ **Con la Q-7 decisa il rimedio ha un appiglio che prima non c'era**: se il
filo è l'azione, l'ancora smette di dover indovinare dov'è il confine del giro.
⛔ **Il come non si decide qui**: la funzione è del team DB, e la scelta va fatta
sapendo che la stessa domanda arriverà sui **task runs**, che oggi un filtro
«giro corrente» non ce l'hanno affatto.

⚠️ **Non toccare `fn_get_lotto_segnalazioni_summary`**: quella alimenta
`blocks_next_step` e la regola dell'ultimo giro lì **non vale** — è scritto nel
commento della funzione, e restringerla farebbe avanzare un lotto con una
critica irrisolta.

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
| **3** | ✅ **CHIUSO — il modello ha incontrato la realtà** *(2026-08-23, quattro corse vere)* | ⭐ **Tutti e sei i campi del lato scrittura reggono su dati veri**: perimetro derivato (`72`), `auth_user_id` = 1 con `user_insert` = `tid`, `cleanup_at` a 750 giorni, `entity_id` reale, **`tx_id` ora valorizzato** (il trigger è arrivato: la D-5 è viva come dato, non più solo come colonna) e ⭐ **`correlation_id` diverso a ogni corsa**. La prova che conta è il confronto: le righe del 22 agosto condividono **un solo** filo (`01a0255a…`, il `lock_batch_id`) su più corse; quelle del 23 ne hanno **uno per corsa** — `ba49a824` e `3731cae2` sullo **stesso** lotto 6260, a cinque secondi di distanza — e su LTF-0006586 (lotto 7133) tre corse con tre fili, due delle quali a **un secondo** l'una dall'altra, coi `task_runs` che portano il filo della corsa che li ha generati. ✅ **E il ramo push**: giro 1506 aperto e chiuso, perimetro conservato, giornale intatto. ⛔ **E una correzione onesta**: il 2026-08-24 avevo scritto qui «`event_log` è a zero righe». **Era falso**, ed era un errore di misura mio — la tabella ha la RLS, e contarla senza contesto operatore la fa apparire vuota. È il caso del *conteggio fail-closed che somiglia a un dato*: le righe c'erano tutte |
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

   > ⏱️ **Secondo controllo, 2026-08-23 — entrambi gli impegni reggono.**
   > **(1)** L3 non ha toccato `vendite.event_log`: la vista legge, non scrive, e
   > i due lotti applicati dopo l'impegno (L5 e L3) hanno lavorato su altre
   > tabelle. La promessa era sulla tabella del giornale, e la tabella del
   > giornale non è stata toccata.
   > **(2)** La forma normalizzata **non è stata rinegoziata**: le tre colonne
   > aggiunte scrivendo (`registro`, `riga_id`, `riga_key`) non sono un concetto
   > nuovo del giornale — sono la **chiave della riga**, cioè ciò che rende
   > possibile l'`UNION ALL` stesso. ⚠️ Ma è il primo scostamento dal disegno di
   > §3.6, ed è scritto lì per intero: il prossimo che lo legge deve poter
   > distinguere «ho aggiunto una chiave» da «ho aggiunto una colonna di
   > dominio». La seconda è la cosa che l'impegno vieta.

⚠️ **E una cosa che non si può promettere**, perché prometterla sarebbe la bugia
più facile: il contatto col backend. Finché `event_log` non ha righe scritte
dalla pipeline vera, questo piano è verificato dai pgTAP e da nient'altro.

---

## 10. Registro

### 2026-08-24 sera · Il pannello ordina per gravità, e il lotto ha un perimetro

- 🆕 **La scheda «Storia» ordina per GRAVITÀ** (Tid, dopo la validazione
  in-app): davanti a un documento la prima domanda è «c'è qualcosa che non va?».
  La cronologia resta a un clic — la colonna `quando` è ordinabile.
  ⛔ **Lato server**, perché la lista è paginata: riordinare nel client
  riordinerebbe la sola pagina, e «il più grave» diventerebbe «il più grave fra
  i primi 50». ⚠️ Il rango si calcola in SQL: il vocabolario è testuale, e in
  ordine alfabetico `ERROR` verrebbe **prima** di `INFO` e `WARN`. ⚠️ Il `NULL`
  pesa come un `ERROR`: mandarlo in fondo renderebbe invisibile dalla seconda
  pagina in giù proprio la riga che dichiara un difetto. 6 test nuovi sulla
  clausola, estratta come **funzione pura** — un ordinamento sbagliato non
  solleva niente e a video somiglia a uno giusto.
- ✅ **«Che cos'è un caso» è deciso**: il pannello del lotto mostrerà il lotto
  **più le sue fatture**, righe non-INFO. §12.
- 🔴 **Scritta la richiesta al team DB su R-1** (§13): le quattro colonne di
  orario hanno default `now()`, cioè l'istante della **transazione**. ⭐
  L'argomento nuovo è che quel significato oggi è coperto dal **`tx_id`**, che
  prima non esisteva: l'orario può tornare a dire solo «quando è successo».

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

### 2026-08-24 (ripartenza) · ✅ Ricognizione, **Q-7 decisa**, e il primo pezzo di FE

Il cantiere DB era chiuso; questo giro è servito a **guardare i dati prima di
scrivere l'endpoint**, come il §12 proponeva.

- ✅ **RICOGNIZIONE FATTA** su `script.vw_giornale_entita`, che fino a stamattina
  aveva **zero consumatori**. Sette rilievi, in §12. ⭐ **Tre cambiano il disegno
  invece di confermarlo**: il tempo non ordina (default `now()` = timestamp di
  transazione: 38 righe su 3 istanti), il filo è NULL su due registri su quattro,
  e la storia di un lotto **non contiene** quella delle sue fatture.
- ✅ **Q-7 CHIUSA da Tid: il filo è l'AZIONE DELL'OPERATORE.** ⭐ A deciderla è
  stata una misura, non una preferenza: la lettura alternativa si reggeva sul
  `tx_id` come ripiego, e dentro **una sola passata** del 6260 i `tx_id` sono
  **quattro**. §8.
- 🔴 **E verificando la Q-7 è emerso un difetto già vivo**: il filtro «Ultimo
  giro» delle segnalazioni **taglia a metà un click** — un solo click su
  «Fattura» scrive 12 righe su due corse, e l'ancora (l'ultimo
  `PIPELINE_STARTED`) ne lascia fuori 6 annunciandole come «di corse
  precedenti». §8. ⛔ Non è materia di questo brief risolverlo: è la funzione
  del team DB, e la stessa ancora vive in due liste.
- ✅ **Decisa la rotta del Passo A: si approda sulla FATTURA.** §12.
- 🔧 **Due correzioni**: la nota di credito del 6260 è la **19205** (non la
  18846, che non esiste); la policy legge **due** GUC, non tre.

⭐ **E un pezzo di frontend è uscito per primo, senza aspettare il Passo A**, dal
rilievo R-7 (segnale/rumore): la scheda **Task** del drawer del lotto mostrava 90
righe di cui **80 annullate**, residui di otto passate, con l'unico errore in
mezzo — e ordinate dal **più vecchio**. Chiesto al team DB *cosa* servisse (non
come); risposto con il changeSet **`20260824-11`**: `p_solo_giro_corrente`,
`p_task_stato` (array) e le colonne `giro_corrente` / `esclusi_count`.
Cablati repository, service, endpoint, export e scheda; **collaudato in-app da
Tid**. Il default esclude gli annullati — **90 → 10 righe** — e la riga «N escluse
dai filtri» è ciò che lo rende onesto.
⛔ **Il filtro «giro corrente» resta disponibile e NON usato come default**: com'è
adesso mostrerebbe **1 riga su 90**, e lo sconsiglia il team DB stesso — è lo
stesso difetto dell'ancora, visto dall'altra lista.
⚠️ **Ordine di merge**: `20260824-11` è applicato sul DB di sviluppo ma non
ancora in git. Il codice BE/FE non deve arrivare a `Tito-dev` prima di quel push
— e la CI **non lo intercetta**, perché i test sono mockati.

✅ **E nel pomeriggio il Passo A è stato CONSEGNATO** — la scheda «Storia» del
drawer fattura, primo consumatore di `vw_giornale_entita`. Tre cose vale la pena
tenere di quel giro:

- ⭐ **il collaudo del perimetro è stato fatto apposta**, perché i dati non lo
  avrebbero fatto (R-4): senza contesto operatore la vista risponde **0 righe** e
  l'endpoint `E_FATTURA_NON_TROVATA`. È la prova che il cancello sulla testata
  non è ridondante — `security_invoker` da solo trasforma «non la vedi» in «non è
  successo niente»;
- 🔧 **un difetto pagato scrivendolo**: `execute` scarta l'envelope due volte, e
  l'unwrap di troppo produceva *«nessun evento registrato»* su una fattura che ne
  aveva tre — il vuoto positivo prodotto dal flag che esisteva per impedirlo;
- ⭐ **una colonna chiesta al DB e arrivata in giornata** (`disabilitato`,
  changeSet `20260824-14`), chiesta come **colonna e non come filtro**: il diario
  resta completo, a nascondere è il consumatore — che dice anche quante ne
  nasconde.

⚠️ Su richiesta di Tid il pannello è **a schede** (Documento · Storia) e non una
pagina da scorrere, con la segnalazione d'errore **in testa**: chi apre una
fattura in errore la apre proprio per quello, e farglielo cercare in fondo era il
difetto che il pannello esiste per togliere.

📌 Nello stesso giro, sulle due liste del drawer: ordinamento iniziale «Fine»
DESC sui task (era `started_at` **ASC**, il più vecchio in cima) e «Quando» DESC
sulle segnalazioni — dove non cambia l'ordine ma lo **dichiara**: il filtro ha
sempre un livello selezionato, quindi a decidere era già il tiebreak, e mancava
solo la freccia sull'intestazione.

### 2026-08-24 (sera) · ✅ Il modello incontra la realtà — **su entrambi i rami**

Scritto dal **backend**, dopo che Tid ha esercitato l'applicazione vera. È la
verifica che nessun test poteva dare, ed è quella che chiude il **rischio 3**.

| Ramo | Cosa è stato fatto | Cosa dicono le righe |
| --- | --- | --- |
| **Pipeline** | 4 corse sul 6260/7132, poi LTF-0006586 (lotto 7133) reso definitivo | **7 fili distinti su 7 corse**, `task_runs` cuciti col filo della loro corsa, `tx_id` e `auth_user_id` valorizzati, `cleanup_at` a 750 giorni |
| **Push commesse** | push di ORD0016313 | giro **1506** aperto e chiuso in 75 ms, `risultato.perimetro` intatto, **zero** righe nel giornale |

⭐ **La prova che il `correlation_id` funziona sta in un dettaglio di
cronometro**: sul lotto 7133 due corse distano **un secondo** (23:11:13 e
23:11:14) e hanno fili diversi. Col `lock_batch_id` sarebbero stati lo stesso
valore — la S3 non è più una deduzione né una misura su dati vecchi, è il
comportamento nuovo osservato nel caso peggiore.

⛔ **E il giro vero ha trovato due cose che i test non vedevano**, entrambe
corrette lo stesso giorno:

1. **`_mark_lotto_error` moriva prima di scrivere il diario** — la marcatura e
   il diario erano un passo solo, e il rifiuto della prima impediva la seconda.
   Ora sono **indipendenti**. Dettaglio in **BE-7**.
2. **`COMPLETATO -> ERRORE` era vietato** — un lotto già completato e rilanciato
   senza successo non si poteva marcare. Aperto, con la decisione di Tid e il
   perché scritto accanto. Vedi il registro qui sotto.

⚠️ **Una lezione di metodo, e vale oltre questo cantiere**: nel misurare avevo
scritto due volte «`event_log` è a zero righe». **Era falso.** La tabella ha la
RLS, e contarla senza contesto operatore la fa apparire vuota — *un conteggio
fail-closed somiglia in tutto e per tutto a un dato*. Le righe c'erano tutte. Chi
controlla queste tabelle da psql deve impostare il contesto, o leggerà zeri
inventati.

📌 Fuori cantiere, annotato in **§11**: un prezzo **non negoziato sul contratto**
dentro un push **riuscito**.

### 2026-08-24 · ✅ Il backend chiude: **dodici consegne su dodici**

Scritto dal **backend**. Con **BE-8** e **BE-11** finiscono le consegne del §5:
non ne resta nessuna aperta.

- **BE-11** — `CODICE_DIAGNOSTICA_FALLITA` spostata su
  `E_DIAGNOSTICA_NON_REGISTRATA`. ⭐ **Il debito era stato aperto dal backend e
  chiuso da entrambi i lati nell'ordine giusto**: il DB ha coniato il codice
  (TECNICO) e ha lasciato vivo il vecchio scrivendo *«un codice ritirato che
  qualcuno solleva ancora è peggio di un nome che mente»*; ora che nessuno
  solleva più `E_PIPELINE_MARK_ERROR` (699), il suo `obsoleto_dal` si può
  mettere. È l'ultimo passo di §5-ter, ed è a carico del DB.
- **BE-8** — `req=%(request_id)s` su ogni riga di log, e `emittente_attivo_id`
  che smette di essere una colonna morta. Dettaglio nella riga della tabella.

⭐ **Due cose che scrivendo si sono rivelate diverse da come erano nel piano.**

1. **Il `request_id` non andava aggiunto ai messaggi, ma al canale.** Il piano
   diceva «`request_id` nel formatter»; misurando, il progetto lo scriveva già
   a mano — **in un punto solo**, `api.exception`. Cioè la prova che scriverlo
   a mano copre solo dove qualcuno ci ha pensato: è la forma di difetto che
   questo cantiere ha già nominato due volte (*una cosa che tutti scrivono e
   nessuno governa*). Nel filtro la correlazione diventa una **proprietà del
   canale**, e il punto che se la scriveva è stato ripulito perché stampava la
   stessa informazione due volte.
   ⚠️ E il presidio che serviva non era sul filtro: è sulla **configurazione**.
   Il formato cita `%(request_id)s`, quindi un handler aggiunto domani **senza**
   il filtro non stamperebbe una riga sbagliata — la **perderebbe**, perché
   fallisce la formattazione, e proprio mentre si cerca di capire cosa è
   successo. Il test lo verifica sugli handler dichiarati in `settings.LOGGING`.

2. ⛔ **Delle due colonne morte, una sola si poteva collegare.** `tx_id` **no**,
   e la ragione non è di implementazione: la riga di `request_log` si scrive
   *dopo* la risposta, quando la transazione di lavoro ha già chiuso — e la GUC
   `dbops.tx_id` in una sessione applicativa è **vuota** (misurata), mentre la
   tabella **non ha nessun trigger**. Un valore coniato lì legherebbe la riga a
   sé stessa. Richiesta di `DROP COLUMN` scritta sopra, non eseguita qui.

#### ⭐ E il giro vero ha corretto anche una regola di dominio *(decisione di Tid, 2026-08-24)*

Il difetto del lotto 6260 aveva **due** cause, e la seconda non era del diario.
`set_lotto_job_stato` vietava `COMPLETATO -> ERRORE`, quindi un lotto già
completato e **rilanciato senza successo non si poteva marcare**: restava
`COMPLETATO` pur avendo una fattura che non si era numerata.

> *Tid: «non è giusto — se il lotto contiene una riga in errore deve essere
> marcato».*

⚠️ **E il divieto non proteggeva niente**, perché colpiva solo quel caso:
l'avvio del giro scrive `IN_ESECUZIONE` **dentro** la transazione del giro, e un
fallimento la rolla indietro — il marcatore, che gira fuori, ritrova lo stato
precedente. Il lotto era `COMPLETATO` non perché fosse a posto, ma perché il
fallimento aveva cancellato la prova di essere partito.

⛔ **Non si è aperto anche `ERRORE -> COMPLETATO`**, ed è la parte da non
«simmetrizzare» domani: le due transizioni non sono la stessa cosa girata al
contrario. *«È andata bene»* è una **conclusione**, e va guadagnata con un giro —
che passa da `IN_ESECUZIONE` e riporta il lotto a `COMPLETATO` da sé. *«È andata
male»* è un **fatto osservato**: rifiutarne la registrazione non lo rende meno
vero, lo rende solo invisibile. È la stessa regola del diario, la **D-12**, un
piano più in su.

⭐ **E lo spegnimento resta automatico, senza una seconda sede.** A fine di ogni
giro il runner ricalcola con `evaluate_lotto_status` — che conta le segnalazioni
**attuali** — e riporta il lotto a `COMPLETATO` se non ci sono più errori. Tolte
le righe rotte e rilanciato, il segnale si spegne da solo. Verificato sul vivo:
`ERRORE -> IN_ESECUZIONE -> COMPLETATO` passa.
⚠️ Ma **solo dentro un giro**: rimuovere le righe *senza rilanciare* non
sbianca il lotto. Sede unica per scelta, non dimenticanza.

📌 Misurato mentre si correggeva: il lotto 6260 **ha davvero un errore adesso**
(1 segnalazione critica, 1 fattura in `stato_esecuzione = ERRORE`) ed è
`COMPLETATO`. È l'incoerenza che la modifica chiude.

⚠️ **E resta in piedi, intatto, il rischio 3.** `event_log` è di nuovo a **zero
righe** e nessun `task_run` ha il filo del giro: il percorso di scrittura è
verificato dai test e da prove puntuali contro il database, ma **una pipeline
vera non è ancora passata** da quando BE-2 e BE-3b esistono. È l'unica cosa che
nessuna riga di questo documento può dichiarare chiusa — e la prossima mossa
utile non è codice, è **far girare un giro** e guardare le righe.

### 2026-08-24 (dodicesimo giro) · 🟢 La vista dice anche cosa è stato ritirato

Richiesta del backend, e ⭐ **corregge una decisione presa qui**. Il changeSet 70
aveva stabilito che il giornale non filtra le segnalazioni ritirate — e quella
metà regge. L'altra metà no: **non esporre il flag non è la stessa cosa che non
filtrare**, e senza di esso il primo consumatore (il pannello «Storia del
documento» del drawer fattura) non può né marcare né nascondere. *Non si filtra
ciò che non si vede.*

⭐ **La misura vale più dell'argomento**, e sta in tre righe (fattura 19563):

```text
11:54:21  ritirata=f  Totale a pagare negativo…
11:54:34  ritirata=t  Non si puo' numerare il documento 19563…
11:57:10  ritirata=f  Non si puo' numerare il documento 19563…
```

Le ultime due sono **la stessa identica frase**: la prima è l'errore della corsa
delle 11:54, ritirato quando il lotto è stato rifatto alle 11:57. L'operatore
legge due errori e conclude che sia successo due volte.

Tre cose decise scrivendo:

1. **Il nome è `disabilitato`**, quello della sorgente e quello che espone già
   `fn_list_lotto_segnalazioni` — che risponde alla stessa domanda sulle stesse
   righe. Lo stesso fatto non deve avere due nomi. 📌 Ed è la ragione per cui
   oggi il ritiro si vede sul drawer del **lotto** e non su quello della
   **fattura**: stesso fatto, due strade, una sola arredata.
2. ⚠️ **I due NULL non hanno la stessa ragione**, e la differenza è scritta nella
   vista: su `event_log` il concetto **non esiste** (append-only, un evento non
   si spegne); sui `task_runs` **esiste ma su un altro asse** — `attivo` spegne
   il *record* e lo fa una sola funzione, `disabilitato` ritira un *segnale* e lo
   scrivono **dieci** funzioni. Fonderli sarebbe dire due cose con una parola, e
   oggi la mappatura sarebbe pure inverificabile (0 righe su 299).
3. ⛔ **La colonna nuova va in coda**, perché `CREATE OR REPLACE VIEW` non
   permette di inserirla in mezzo — `disabilitato` finisce dopo `user_insert`,
   non accanto a `cosa` dove si leggerebbe meglio.

⭐ **E la trappola di ieri ha avuto la sua prima occasione**: questo è il primo
`CREATE OR REPLACE` della vista, e `security_invoker` **va ripetuta** o si
azzera. Ripetuta, e verificata sull'oggetto vivo (`reloptions =
{security_invoker=true}`). ⚠️ Da lì anche una conseguenza operativa: il corpo di
una **vista** non si copia dalla doc auto-generata — per le viste quella riporta
`pg_get_viewdef`, cioè l'albero ri-stampato, **senza commenti e senza
reloption**. Il corpo arriva dal changeSet 70, dopo aver verificato che nessun
altro lo tocchi.

🧪 pgTAP da 12 a **15**, e discrimina: senza la colonna il file esegue 12
asserzioni su un piano di 15, che `pg_prove` legge come fallimento.

### 2026-08-23 (undicesimo giro) · 🟢 L6 — il difetto trovato dalla domanda «è completo?»

⭐ **Il lotto che non doveva esistere, e che è il più importante di oggi.** Alla
domanda di Tid «lato DB questo brief è completo?» la risposta elencava fra le
cose aperte la retention dei due log gemelli. Tid ha letto la spiegazione e ha
visto il punto vero, che io avevo trattato come contorno:

> *«ma questa è la parte brutta: bisogna risolvere almeno il fatto che le
> tabelle che hanno il lucchetto non blocchino l'intero processo, ma siano
> saltate».*

Sono **due problemi diversi**, e li avevo impacchettati come uno solo. *Quanto a
lungo vive la storia di una fattura* è una decisione di dominio e può aspettare.
*Se la scelta di una tabella possa fermare il giro di tutte le altre* è un
difetto del framework, e non c'entra niente col dominio. Il secondo si chiude
oggi (§4, lotto L6): la tabella che rifiuta viene **saltata**, e il rifiuto
lascia una riga `ERROR` con lo SQLSTATE.

⚠️ **E una mia misura sbagliata, corretta**: avevo scritto che a ciclare sulle
tabelle fosse `fn_purge_cleanup_expired`. Quella funzione lavora su **una
tabella sola** — il suo `LOOP` è il batch delle righe. Il ciclo vero è in
`fn_run_automations_cleanup`, e il difetto lì c'era davvero. La conclusione
reggeva, la prova no: l'ho rifatta.

⭐ **Tre cose imparate scrivendolo**, e nessuna era nel piano:

1. **La cura era già in casa.** La funzione sapeva già saltare una tabella e
   dirlo (`EXCLUDED`, `NO_CLEANUP_COLUMN`, `MISSING_TTL_DAYS`…): mancava il
   caso «si è opposta». E `fn_audit_log_once` aveva **già** i parametri
   `p_sqlstate` e `p_error_context`, mai usati qui. Il rimedio è stato
   *aggiungere il quarto membro di una famiglia*, non inventare un meccanismo.
2. ⛔ **Il test dell'orchestratore era cieco.** Le due asserzioni esistenti
   cadevano nel ramo «scope non include tabella test» e passavano **dichiarando
   di non verificare**: su questo database l'orchestratore non era esercitato
   *mai*. La fixture ora mette in scope le proprie tabelle. È la stessa classe
   di difetto che il §6 di questo brief nomina da giorni — *un file che passa
   smettendo di verificare* — trovata in casa d'altri.
3. ⚠️ **E sono ricascato in una trappola che avevo già in memoria**: il corpo
   preso dalla doc auto-generata **non ha il `;` dopo `$function$`**, e il primo
   changeSet non compilava. La memoria c'era; l'ho riletta dopo l'errore invece
   che prima.

🧪 La controprova è misurata in entrambi i versi: **senza** la rete `not ok 13,
15, 16` (con la 14 verde — il veto morde davvero), **con** la rete 16 su 16.

### 2026-08-23 (decimo giro) · ✅ L3 — la cucitura, e il modello incontra la realtà

Scritta e **applicata** `script.vw_giornale_entita` (changeSet **70**, applicato
alle 23:18) col suo pgTAP: **12 asserzioni verdi come applicazione, zero skip**,
baseline `script` senza regressioni, doc auto-generata rigenerata.
⭐ **Il piano DB di questo cantiere è finito**: restano solo le consegne BE.

⚠️ Le 12 asserzioni sono state rilette **una per una nel TAP**, e non solo
attraverso la baseline: quella vede un rosso, non un file che passa *smettendo
di verificare*. La prima — «la vista è `security_invoker`» — ha senso solo
girando come applicazione, ed è la precondizione di tutte le altre: senza,
ognuno vedrebbe i documenti degli altri. Verificato anche sull'oggetto vivo:
`reloptions = {security_invoker=true}`.

⭐ **La misura che vale più della vista**: `event_log` **non è più vuoto**. Dodici
righe, scritte dalla pipeline vera sul lotto 6260, e dicono quattro cose insieme:

```text
emittente derivato dal trigger        ✅  1 emittente su 12 righe, nessun rifiuto
auth_user_id (D-14)                   ✅  valorizzato, e user_insert dice «tid»
cleanup_at (D-13)                     ✅  2028-09-10 — i 750 giorni tornano
tx_id (D-5)                           ⏱️  NULL su tutte: il trigger non è ancora nato
correlation_id (D-7)                  ⛔  UNO SOLO per QUATTRO corse
```

⛔ **L'ultima riga è la S3 misurata sul vivo, non più dedotta.** Le quattro corse
delle 18:49 e 18:50 condividono lo stesso `correlation_id`, che è il
`lock_batch_id` del lotto: sulla domanda «in che giro» restano
indistinguibili. Il DB ha fatto la sua parte (changeSet 61 e 67), il runner non
ancora — è **BE-2**, ed è l'unica delle cinque righe che una migrazione non può
chiudere.

⭐ **Il rischio 3 del §9.3 quindi si è mosso di mezzo passo, e va letto così**:
il percorso di scrittura ha incontrato la realtà e ha retto; il *significato* di
un campo no. Era esattamente la distinzione che quel rischio faceva.

Tre cose decise scrivendo la vista, tutte in §3.6 (allineamento):

1. ⭐ **Tre colonne tecniche in più** (`registro`, `riga_id`, `riga_key`): i
   quattro registri hanno spazi di id sovrapposti, e senza la coppia non esiste
   nessuna chiave stabile. Stessa scelta di `fn_list_lotto_segnalazioni`.
2. 🔄 **`quando` di un tentativo = `ended_at` quando c'è**: col solo
   `started_at` un task fallito comparirebbe *prima* degli eventi che lo
   spiegano, già marcato ERRORE.
3. ⭐ **La mappa della gravità non ha `ELSE`**: un valore fuori vocabolario esce
   NULL e il canarino canta. È la lezione del L5 applicata *prima* del danno.

⚠️ **E un difetto che la vista ha reso visibile senza risolverlo**: manca
l'indice su `fatturazione_lotti_log.lotto_id` — la FK è a `consentito = false` in
`fk_index_policy`, e quel registro è il più scritto dei quattro. ⛔ Non si
ribalta la policy qui: L3 è la vista, non ancora un consumo. La sede è il seed,
il momento è il Passo A.

⏱️ **Numerazione**: il file resta `20260822-70` benché scritto il 23 — sta in
coda al lotto di ieri, e i suoi riferimenti (67-69) sono lì. I numeri 63-66
restano prenotati dal cantiere del bersaglio.

#### ⏱️ Rimisura di chiusura — «lato DB è completo?» *(2026-08-23)*

Domanda di Tid. Risposta misurata sul database e sul codice, non riletta da qui.

| | Cosa | Esito |
| --- | --- | --- |
| ✅ | I 22 changeSet del cantiere | tutti applicati |
| ✅ | I sei campi del lato scrittura | perimetro derivato · `auth_user_id` · `cleanup_at` a 750 giorni · `entity_id` reale · `tx_id` **ora scritto** · `correlation_id` **generato dal backend** (BE-2 fatta il 2026-08-24: un `uuid4()` per corsa, non più il `lock_batch_id` del lotto) |
| ✅ | I cataloghi e la retention | 4 tipi · 5 codici evento · regola `CLEANUP_AT` id 15 (750 giorni, attiva) · `fk_index_policy` registrata |
| ✅ | Il presidio | 76 asserzioni verdi, e i quattro percorsi della retention (riga viva, scadenza immutabile, riga scaduta, GUC di manutenzione) sono tutti coperti |
| ✅ | La spia dei codici evento | `dbops.vw_eventi_non_dichiarati` = **0** — e ⭐ **il cancello lato Python esiste già**: `apps/core/tests/test_event_codes_declared_guardrail.py`. **BE-9 risulta fatta** |
| ✅ | ~~**Il BE è rotto adesso su un punto**~~ | ⏱️ **Superato il 2026-08-24, e la misura era su uno snapshot precedente al merge del backend** (PR #1364). `commesse_repository` non chiama più `fn_log_commessa_push_run`: al suo posto ci sono `start_push_run` (in testa) e `close_push_run` (in coda) — **BE-3b è fatta**. Verificato dal vivo: apertura `IN_ESECUZIONE`, chiusura `PARZIALE`, e i due rifiuti della chiusura che rispondono come devono |

⭐ **Quindi: lato DB il cantiere non ha più niente da consegnare.** Restano
**quattro cose aperte, tutte dichiarate e nessuna dimenticata**: l'indice di
`fatturazione_lotti_log` (al Passo A), la retention dei due log gemelli (§1.3,
non di questo cantiere), la baseline B-7 (decisione che attraversa tre
cantieri), e le righe già scritte senza `tx_id` — che append-only rende
definitive, ed è il prezzo che la D-4 aveva già messo in conto.

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

---

## 11. 🔵 Da verificare — trovato collaudando, **fuori cantiere**

> **Perché sta qui e non in un brief suo.** Non è materia di `event_log`: è
> emerso mentre si verificava sul campo il ramo push, e nel registro tecnico si
> vede **solo** perché quel giro è stato guardato riga per riga. Annotato per
> non perderlo — non analizzato, non corretto.

### Un prezzo non negoziato sul contratto, dentro un push riuscito *(2026-08-23)*

Il push di **ORD0016313** (giro `commesse_push_log` **1506**) è andato
`COMPLETATO`, e **nello stesso `tx_id`** ha lasciato una riga in
`dbops.error_log`:

```
23:27:18 · vendite.fn_resolve_prezzo_listino_v2 · E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
context: articolo 019d53f6-58ca-7cb7-b77b-86d201ce9787 · contratto_id 198
         ba_id 155 · utility_id 5 · data_riferimento 2026-08-09
         classe_utenza_id NULL · listino_versione_id_preferito NULL
```

⭐ **E il push non si è fermato**: l'attività nata dal giro
(`commesse_attivita` **44883**, commessa **25092**) ha
`prezzo_snapshot = 17.00`, `prezzo_bloccato = true`, `pricing_mode = FIXED` —
cioè il prezzo **è arrivato lo stesso**, verosimilmente bloccato dalla riga
d'ordine invece che risolto dal contratto.

**La domanda da porsi, quando si riprende:**

1. **17,00 è il prezzo giusto?** Se viene dall'ordine e il contratto 198 avrebbe
   dovuto negoziarne un altro, il documento nasce con un prezzo che nessuno ha
   deciso — ed è il tipo di cosa che si scopre in fattura.
2. **Il ripiego è voluto o è una tolleranza?** Un `prezzo_bloccato` che copre un
   articolo *non negoziato sul contratto* può essere il disegno (il prezzo del
   documento vince) oppure il modo in cui un buco di configurazione passa
   inosservato. Le due cose si distinguono solo leggendo la regola, non il dato.
3. **Quante volte capita?** Una riga di `error_log` su un push riuscito non la
   guarda nessuno: se il caso è frequente, il registro lo sa già —
   `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` per `function_name` e periodo.

⚠️ **Non è un difetto accertato.** È un errore *registrato dentro
un'operazione riuscita*, che è esattamente la categoria che nessuno controlla —
e per questo vale la pena riprenderla a mente fresca invece di archiviarla come
rumore.

---

### ✅ CHIUSO — il dubbio su `competenza_mese` *(2026-08-24)*

> **Era una domanda aperta di questo brief**, nata collaudando: un documento di
> **competenza giugno** confermato **ad agosto** finisce nel lotto di *giugno*,
> il dato fiscale è corretto (la fattura ha data agosto), ma `competenza_mese`
> sembrava fare **due mestieri** — tetto della raccolta *e* etichetta di
> archiviazione — senza che esistesse un `periodo_fatturazione`.

⭐ **Il modello non ha il difetto che sospettavamo.** Misurato: la regola di
raccolta è `a.competenza_mese <= X` e il documento prende la data del giorno di
emissione — entrambe corrette. Il caso nasce da una scelta legittima
dell'operatore: lanciare *«fattura competenza giugno»* in agosto.

⛔ **Il difetto era di VISIBILITÀ, non di modello**: chi lavora sul mese di
agosto quel documento non lo trova, perché lo cerca — con ragione — per la
**data del documento** e non per la competenza della commessa. Non serviva un
`periodo_fatturazione`: serviva un posto dove guardare.

✅ **Risposto** con una scheda **«Recuperi del mese»** sulla lista lotti — i
lotti di competenza precedente che hanno emesso documenti nel mese filtrato.
Sulla lista di agosto risponde `LTF-0006585` e `LTF-0006586`.

📌 Il caso, le due sbagliate che ho preso per strada e le cose che restano stanno
nel §6-bis di
[brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md) —
qui basta sapere che **la domanda non è più aperta**.

⚠️ **E ne è uscito un buco più grande, che resta aperto**: la **fattura è
l'unico documento del ciclo attivo senza la sua lista**. Misurato — `preventivi`,
`offerte`, `ordini`, `contratti`, `ddt`, `resi` hanno la loro
`ui.lista_definizione`; `fatture` no, e nel frontend non esiste nessuna rotta
verso di loro. Oggi un documento fiscale si raggiunge **solo** passando da un
lotto, da un cruscotto o da un collegamento. È la ragione per cui la prima idea
era stata una scheda dentro il drawer del lotto: non c'era altro posto.

---

## 12. ✅ Il Passo A — **CONSEGNATO** sulla fattura *(2026-08-24)*

> **Perché sta in questo brief e non in quello del Passo A.** Il Passo A non è
> materia di questo cantiere — è il §498 di
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md). Ma **questo**
> cantiere è ciò che lo ha reso possibile, e chi riparte lo fa da qui: la nota
> serve a non dover ricostruire il ragionamento da capo.

### ✅ I tre prerequisiti sono soddisfatti, e nessuno per deduzione

| Prerequisito | Come si è chiuso |
| --- | --- |
| La riga di `event_log` è **parlante** | perimetro derivato · `auth_user_id` · `tx_id` · `cleanup_at` · `correlation_id` per corsa — verificati su **7 giri veri** (§10, voce del 2026-08-24 sera) |
| `event_log` è sotto **RLS** | L1, changeSet 46. È ciò che permette a un endpoint di lettura di non mostrare gli eventi di altri emittenti: era il rischio **B9** dell'analisi, ed è il motivo per cui il Passo 0 veniva prima |
| La **cucitura** esiste | `script.vw_giornale_entita`, lotto L3 — ⚠️ nata con **zero consumatori**; il primo l'ha interrogata il 2026-08-24, ed è la ricognizione qui sotto |

⭐ **E c'è la condizione che mancava fino a ieri: dati veri da mostrare.** Con il
registro vuoto una timeline non si poteva collaudare — si sarebbe consegnata una
pagina che «funziona» perché non mostra niente.

### Cosa è, in una riga

*«Dammi la storia di questa entità, in ordine di tempo.»* Filtri `entity_type` +
`entity_id`, e `correlation_id`. Read-only, `DomainAPIView`, envelope e
paginazione standard ([api.md](../api.md)). ⛔ Nessun aggregato, nessuna finestra
temporale, nessun cruscotto: quelli sono il Passo B, e hanno prerequisiti loro.

✅ **Approda nel drawer della FATTURA** (decisione del 2026-08-24, motivi al
punto 2 qui sotto), come sezione accanto a «Collegamenti» e «Situazione merce»:
si apre il documento e lì dentro c'è anche la sua storia. Il **lotto** viene
dopo. ⭐ È **il primo pezzo di questo filone con un lato FE vero** — finora non
ce n'era nessuno, ed è la ragione per cui il cantiere è stato tutto backend.

📌 La query che serve è quella per cui la tabella è **già indicizzata**
(`ix_event_log_entity_time`): non c'è niente da ottimizzare, e non è un caso —
§1.1 la registrava fra le cose che reggevano già.

### ✅ Le tre cose da decidere prima di scrivere codice — **decise**

1. 🔴 **Il primo consumatore di `vw_giornale_entita` ne è anche il collaudo** — e
   la ricognizione ha dato la risposta peggiore fra quelle possibili. Non «regge»
   né «non regge»: **il perimetro non è mai stato messo alla prova**. Vedi R-4.
2. ✅ **Approda sulla FATTURA** *(Tid, 2026-08-24)*. La domanda del primo giro era
   *«lotto o fattura, a chi serve prima?»*; a deciderla è stato **R-3**, che l'ha
   cambiata: la storia di un lotto **non contiene** quella delle sue fatture, e
   sul caso sporco la frase leggibile sta solo di là. Le ragioni, in ordine:
   il drawer della fattura oggi **non mostra nessuna storia** (cliente, documento,
   righe, riepilogo IVA — e basta), mentre il lotto ha già tre schede che rendono
   gli stessi tre registri; la storia di una fattura è **corta** (due righe che
   contano contro 213); e non obbliga a decidere adesso come si cuce un «caso»,
   che è una domanda di modello e non di schermata.
   ⛔ **Il lotto non è rinviato per poco interesse**: è rinviato perché lì il
   pannello dovrebbe prima rispondere a *«che cos'è un caso»*, e quella risposta
   si scrive meglio dopo aver visto funzionare la forma semplice.
3. ✅ **La Q-7 è stata risposta** *(2026-08-24)*, e la timeline non deve più
   aspettarla: il `correlation_id` identifica **l'azione dell'operatore**. La
   colonna del filo si può disegnare — e mostra ciò che l'operatore riconosce
   come «quello che ho fatto io», non una passata interna della catena. §8.

### ✅ La RICOGNIZIONE è stata fatta *(2026-08-24)* — sette rilievi

> ⚠️ **Il contesto della misura, dichiarato** (lezione del 2026-08-24, §10):
> connessione **`zeroerp_app`** — non owner, non `BYPASSRLS` — con
> `app.ruolo_applicativo = 'OPERATORE'` e `app.current_user_id = 1` (utente
> `tid`, che è **SUPER_ADMIN**), salvo dove indicato. Senza queste due GUC la
> vista torna **zero righe**, e uno zero fail-closed somiglia in tutto a un dato.
>
> ⛔ **Nessuna scrittura**: solo `SELECT`. Casi: lotto **6260** (sporco, errore
> vivo) e **7133** / LTF-0006586 (pulito, tre corse, fattura numerata).

**Quello che blocca il disegno**

| # | Rilievo | La misura |
| --- | --- | --- |
| **R-1** | 🔴 **Il tempo non ordina.** `event_time` e `data_ora` hanno default `now()`, che in PostgreSQL è il timestamp di **transazione**, non `clock_timestamp()` | Le **38 righe** del lotto 7133 stanno su **3 istanti** distinti — uno per corsa, identico al microsecondo su tutti e tre i registri. L'ordine che si vede è quello di `riga_id`, che è **per registro**: la timeline esce raggruppata per sorgente, non per accadimento. ⛔ Una schermata «in ordine di tempo» costruita su quella colonna racconta una sequenza che non è quella vera |
| **R-2** | 🔴 **Il filo non copre tutto, e non copre la parte leggibile.** `LOTTO_LOG` e `FATTURA_LOG` hanno `correlation_id` **NULL per costruzione della vista** (`NULL::uuid`) | Filtrare per filo tiene `event_log` + `task_run` — `PIPELINE_STARTED`, `select_attivita · COMPLETATO` — e butta via «Numerazione fatture», «Chiusura lotto eseguita da flag chiude_lotto», che sono le uniche righe scritte per una persona |
| **R-3** | 🔴 **La storia di un lotto non contiene le sue fatture**, ed è ciò che ha deciso dove approda il Passo A | Filtrando `entity_type = 'LOTTO'` il ramo `FATTURA_LOG` non compare **mai**: la sua entità è la fattura. Sul 6260 le 213 righe del lotto dicono **otto volte** «Esito fatture lotto · WARN», e la frase che serve non c'è — sta sulla fattura **19205**: *«Non si può numerare il documento 19205: la fattura che rettifica non è ancora numerata (documento 835). Numera prima quella.»* |

**Quello che va saputo prima di scrivere l'endpoint**

| # | Rilievo | La misura |
| --- | --- | --- |
| **R-4** | 🔴 **Il perimetro non è mai stato esercitato**, su nessuno dei quattro rami | `event_log` ha **un solo** `emittente_soggetto_ruolo_id` (**72**), e così `fatturazione_lotti` (48 lotti) e `fatture` (17). Esiste un secondo emittente (`ef_pk 44` / `sr 159`) che `fara` e `pochi` **non** hanno in whitelist — ma nessuna riga gli appartiene. ✅ Il **fail-closed** funziona (senza `app.ruolo_applicativo` la vista torna **0**); ⛔ la **discriminazione** non è mai avvenuta su dati veri. È il rischio del punto 1 qui sopra, adesso **misurato invece che temuto** |
| **R-5** | ⚠️ **In `event_log` convivono due generazioni di righe** | 12 righe (corse del 22/08) hanno `tx_id` **NULL** e `correlation_id` = `01a0255a-0de9-…`, cioè il `lock_batch_id` del lotto — il difetto **S3** di prima di BE-2. Le righe dal 24/08 hanno tx valorizzato e un filo per corsa. ⛔ A video le due sono **indistinguibili**: la colonna «filo» mostrerebbe il lotto per le vecchie e il giro per le nuove |
| **R-6** | ⚠️ **La riga `TASK_RUN` è incoerente con sé stessa** | `quando` è `COALESCE(ended_at, started_at)`, e `ended_at` viene scritto quando la corsa **successiva** annulla i task rimasti aperti. Il task 1182 è partito il **21/08 19:24** e appare in timeline il **22/08 11:37**, col `tx_id` della sera prima: **timestamp di un giro, transazione di un altro** |
| **R-7** | ⚠️ **Il rapporto fra segnale e rumore, misurato** | Lotto 6260: **213 righe**, di cui 82 non-INFO — e 81 sono la stessa storia ripetuta **otto volte** (`task_code · ANNULLATO` per otto corse). L'errore vero è **una riga**. Sul 7133 (pulito) 38 righe, e `STEP_COMPLETED` / `task · COMPLETATO` / «Generazione righe fattura» raccontano **la stessa cosa tre volte** |

**Due correzioni a questo documento**, trovate misurando:

- 🔧 **La nota di credito del lotto 6260 è la 19205, non la 18846** (che non
  esiste). Rettifica la **835**. Il numero sbagliato era qui e nel registro.
- 🔧 **La policy legge DUE GUC, non tre.** `rls_event_log_ef_whitelist` usa
  `app.ruolo_applicativo` e `app.current_user_id`; `app.current_emittente_id`
  **non compare in nessuna delle quattro**. L'avvertenza sulla trappola resta
  giusta, l'elenco no.

### ⭐ Cosa la ricognizione ha comprato, in una riga

Il disegno dell'endpoint **non parte più da zero**: si sa che l'ordinamento non
può appoggiarsi al tempo (R-1), che il filo non è un filtro sufficiente (R-2),
che la chiave `(entity_type, entity_id)` risponde a una domanda più stretta di
quella dell'operatore (R-3) e che il perimetro va collaudato **apposta**, perché
i dati non lo faranno (R-4). ⭐ Erano esattamente le cose che il §12 diceva di
*«non scoprire a metà»*.

### ✅ Consegnato — la scheda «Storia» del drawer fattura

`GET /api/v1/vendite/fatture/<id>/giornale/` → scheda **Storia** accanto a
**Documento**, più una **segnalazione in testa** quando il documento porta un
errore. Doc:
[api_fattura_giornale.md](../../backend/vendite/manual/api_fattura_giornale.md).

⭐ **La vista ha finalmente un consumatore**, e il collaudo che il §12 metteva in
conto è stato fatto davvero:

| Contesto | La vista da sola | L'endpoint |
| --- | --- | --- |
| con contesto operatore | 3 righe | 3 righe |
| **senza contesto** (fail-closed) | **0 righe** | **`E_FATTURA_NON_TROVATA`** |

⛔ **È la prova che il cancello sulla testata non è ridondante**: `security_invoker`
da solo trasforma «non la vedi» in «non è successo niente». Presidiato da
`test_giornale_non_letto_se_testata_none` — senza, la regressione sarebbe
silenziosa, perché la risposta sbagliata è un `200` con un elenco vuoto.

**Come i rilievi hanno cambiato il codice, uno per uno:**

| Rilievo | Cosa ne è uscito |
| --- | --- |
| **R-1** il tempo non ordina | `ORDER BY quando DESC, riga_id DESC`, col motivo scritto accanto: dentro l'istante a ordinare è il tiebreak, ed è la sequenza vera **finché il registro è uno solo** |
| **R-2** il filo non copre due registri | nessun filtro per filo nel pannello: sarebbe un filtro che nasconde metà del contenuto |
| **R-3** il lotto non contiene le sue fatture | ha deciso **dove** approdare |
| **R-4** il perimetro mai esercitato | il collaudo qui sopra, fatto apposta perché i dati non lo avrebbero fatto |
| **R-7** segnale contro rumore | le **ritirate** si nascondono, e `ritirate_count` dichiara quante |

### 🔧 Un difetto pagato scrivendolo, e vale oltre questo pannello

`useApiHandler.execute` **scarta già l'envelope due volte** (ritorna
`response.data.data`). Il pannello leggeva `res.data?.data?.results`, cioè
`undefined` — e il flag «ho caricato» andava comunque a `true`.

⛔ **Il risultato era un vuoto positivo**: *«Nessun evento registrato per questo
documento»* su una fattura che ne aveva tre. Cioè **esattamente ciò che quel
flag esisteva per impedire, prodotto dal flag stesso.**

⚠️ La causa è che due funzioni adiacenti nello stesso file hanno **contratti
diversi**: `loadDettaglio` passa da `loadDetailOrClose`, che la response axios la
restituisce intera; `loadGiornale` passa da `execute`, che la scarta. Copiare la
forma del vicino era la mossa naturale ed era sbagliata. Scritto nel codice.

### ⭐ E una colonna chiesta al DB e arrivata in giornata

`disabilitato` — la segnalazione **ritirata** — non c'era sulla vista, e senza
non si poteva né marcarla né nasconderla: **non si filtra ciò che non si vede**.
Chiesta come colonna e **non** come filtro (il diario deve restare completo: a
filtrare è il consumatore), è arrivata col changeSet `20260824-14`.

Decisione di Tid: **si nascondono**. Sul caso misurato la ritirata è
*letteralmente la stessa frase* di quella viva, e mostrarle entrambe fa credere
che sia successo due volte.

⚠️ Con la condizione che vale in tutto questo cantiere: **dire quante se ne
nascondono**. È la terza volta in un giorno che lo stesso difetto si presenta —
il filtro dei task che mostrava 1 riga su 90, l'«Ultimo giro» che ne taglia 6
chiamandole «di corse precedenti», e qui. Un elenco filtrato e un elenco vuoto
si leggono uguali.

### ✅ «Che cos'è un caso» — **DECISO da Tid il 2026-08-24**

Era la domanda che teneva fermo il pannello del **lotto**, e non era una scelta
di schermata: cambia il filtro dell'endpoint, il contratto e su cosa pagina.

➡️ **Decisione: il lotto PIÙ le sue fatture, limitato alle righe non-INFO.**
Cioè *«cosa è andato storto in questo giro, ovunque sia successo»*.

⭐ **Il numero che l'ha decisa**, misurato sul 6260: filtrando `entity_type =
'LOTTO'` tornano **213 righe** che dicono otto volte *«Esito fatture lotto ·
WARN»* e **non contengono il motivo** — che sta sulla fattura 19205, perché la
sua entità è la fattura (**R-3**). Un pannello onesto ma limitato al lotto
sarebbe un pannello che nel giorno in cui serve **non contiene la risposta**.

⚠️ **«Non-INFO» non è `gravita IN ('WARN','ERROR')`.** È *tutto ciò che non è
`INFO`*, **NULL compreso**: una gravità nulla significa «un vincolo si è
allargato e la mappa è rimasta indietro» (§3.6), ed è esattamente la riga da non
perdere. Un filtro scritto per elencazione la butterebbe via **in silenzio** — e
sarebbe la terza volta che questo cantiere incontra lo stesso difetto. ⭐ È anche
coerente con l'ordinamento appena consegnato sulla fattura, dove il `NULL` pesa
come un `ERROR`.

⛔ **E vale la regola di casa: dire quante se ne nascondono.** Un elenco filtrato
e un elenco completo si leggono uguali; il pannello dichiara quante righe `INFO`
ha tolto, come già fa con le ritirate.

⚠️ **Cosa questa decisione NON risolve, e va saputo prima di scrivere**: il
filtro non-INFO da solo non basta contro il rumore. Sempre sul 6260, delle 82
righe non-INFO **81 sono la stessa storia ripetuta otto volte** (`task_code ·
ANNULLATO`, una per corsa) e l'errore vero è **una riga sola** — è il rilievo
**R-7**. Il nascondere le ritirate ne toglie una parte; il resto è una domanda
aperta di **de-duplicazione**, da guardare col pannello davanti e non prima.

### 🔵 Cosa resta del Passo A

- **Il lotto**, che ora ha il suo perimetro (qui sopra) ma aspetta **R-1**: la
  richiesta al team DB è il **§13**. Senza orario vero quella timeline mostra
  una sequenza mai avvenuta, e sul lotto i registri sono **tre**.
- ⚠️ **Il secondo registro.** Oggi per una fattura risponde solo `fatture_log`
  (`event_log` non ha righe di entità `FATTURA`). Quando ne arriverà un secondo,
  il tiebreak di R-1 smette di essere la sequenza vera.

### Cosa NON fare partendo

| Non fare | Perché |
| --- | --- |
| Aggregati, conteggi, «quanti errori questo mese» | È il **Passo B**, e su questo ambiente sarebbe illeggibile (§Passo B dell'analisi). Una vista aggregata costruita adesso porta chi la guarda a conclusioni sbagliate |
| Una seconda vista «più comoda» accanto a `vw_giornale_entita` | La forma normalizzata a sette colonne è una **decisione** (§3.6), presa perché i registri di eventi del progetto sono **sei** e non uno. Una vista comoda per il primo consumatore è il seme della terza ristrutturazione |
| Allargare la vista con colonne nuove | Un registro che non sa riempire la forma lascia `NULL`, **non allarga**. È scritto nel §3.6 ed è l'impegno §9.4 n.2 |

---

## 13. 🔴 Il passaggio al team DB — **R-1: l'orario di transazione non ordina** *(scritto dal BE il 2026-08-24)*

> **Cos'è.** Il prossimo pezzo del Passo A è la **storia di un lotto**, e non è
> scrivibile finché l'orario delle righe non è quello vero. ⛔ **Perimetro: è del
> team DB** — sono i `DEFAULT` di quattro colonne su quattro tabelle. Il BE qui
> misura e chiede, non scrive.
>
> ⚠️ **Sulla FATTURA il difetto non morde**, ed è la ragione per cui il pannello
> consegnato oggi funziona: un registro solo, poche righe, e dentro l'istante
> ordina l'ordine di scrittura di *quel* registro. Sul **lotto** i registri
> diventano **tre**, e i loro contatori di scrittura non sono confrontabili fra
> loro.

### La misura — 2026-08-24, sui dati veri

`now()` in PostgreSQL è l'istante in cui è cominciata la **transazione**, non
quello della scrittura. Tutte le righe scritte dentro la stessa transazione
escono quindi con lo **stesso identico timestamp**, al microsecondo.

```text
lotto 7133 (pulito, tre corse)   38 righe  →  3 istanti distinti, uno per corsa
lotto 6260 (sporco)             213 righe  →  stesso fenomeno
```

Le quattro colonne, dalla doc auto-generata:

| Tabella | Colonna | Default oggi |
| --- | --- | --- |
| `vendite.event_log` | `event_time` | `now()` |
| `vendite.fatture_log` | `data_ora` | `now()` |
| `vendite.fatturazione_lotti_log` | `data_ora` | `now()` |
| `vendite.fatturazione_lotti_task_runs` | `started_at` | `now()` |

⛔ **E non c'è una colonna di ripiego**: `data_insert` è `now()` anche lei, su
tutte e quattro. Non esiste, oggi, un modo di sapere in che ordine due righe di
registri diversi siano state scritte dentro la stessa transazione.

### 🔵 La domanda — posta come domanda

**Le quattro colonne passano a `clock_timestamp()`?**

⭐ **L'argomento a favore, che è nuovo e non c'era quando quei default sono
stati scelti**: l'orario di transazione oggi non serve più a niente che non sia
già coperto. Da questo cantiere ogni riga porta il **`tx_id`**, quindi «quali
righe appartengono alla stessa transazione» ha una **chiave sua** — non è più
una domanda a cui deve rispondere il timestamp. Prima del `tx_id` quei due
significati erano sovrapposti su una colonna sola; adesso sono separabili, e
l'orario può tornare a dire una cosa sola: **quando è successo**.

⚠️ **Se la risposta fosse no**, la richiesta alternativa è una **sequenza
ordinabile fra registri diversi** — perché il problema da risolvere non è il
timestamp: è che una timeline di tre registri, oggi, **non è ordinabile**.

### ⛔ La dipendenza da verificare — una sola, e va guardata

`vendite.fn_list_lotto_segnalazioni` àncora il «job corrente» a
`max(event_time)` dei `PIPELINE_STARTED` e tiene le righe da lì in avanti.

⚠️ **Con l'orario vero il comportamento cambia**, e va deciso se in meglio: oggi
le righe scritte nella **stessa transazione** del `PIPELINE_STARTED` — anche
quelle scritte *prima* — hanno il suo identico timestamp e finiscono **dentro**
il giro corrente. Con `clock_timestamp()` quelle precedenti cadrebbero **fuori**.
⭐ A occhio è la lettura giusta, ma è un cambio di perimetro su una funzione in
servizio: **lo dica un test, non questa frase.**

### ⛔ Cosa il BE NON chiede

* **Nessun backfill.** Le righe già scritte restano come sono: `event_log` è
  append-only per trigger (niente `UPDATE`, niente `DELETE`) e un orario
  ricostruito a posteriori sarebbe **inventato**. La convivenza fra due
  generazioni di righe è già un fatto noto (rilievo **R-5**), e il pannello deve
  reggerla comunque;
* **Nessun tocco ai campi di audit** `data_insert` / `data_update`: lì l'orario
  di transazione è la convenzione della casa (806 colonne) e non c'entra con
  l'ordinamento di una timeline. ⚠️ Va detto perché la tentazione di
  «uniformare tutto» trasformerebbe una richiesta da quattro colonne in una
  passata su mezzo database;
* **Nessuna modifica alle viste né agli indici.** `ix_event_log_entity_time` è
  su `event_time DESC` e continua a servire: cambia il **valore** che ci finisce,
  non la colonna;
* **Nessun rimedio in Python.** Ordinare nel backend ciò che il database non sa
  ordinare vorrebbe dire leggere tutte le righe per ordinarne una pagina — e la
  lista è paginata.

### 📌 Cosa fa il BE nel frattempo

Niente che vada disfatto: il pannello **fattura** è consegnato e regge (un
registro solo), e il pannello **lotto** non si scrive finché questa risposta non
c'è. ⛔ Scriverlo prima significherebbe consegnare una schermata che mostra una
sequenza **mai avvenuta**, e nessuno se ne accorgerebbe guardandola: è un elenco
plausibile: la trappola è esattamente che non sembra rotto.
