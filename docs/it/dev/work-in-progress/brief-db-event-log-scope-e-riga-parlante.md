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
> **Stato:** ✅ **L1 APPLICATO E VERDE (2026-08-22).** Otto changeSet applicati
> (i sette del piano più la correzione `47`), tre append a CSV, **33 asserzioni
> pgTAP verdi con zero skip** su cinque file. Restano **L2** (l'identità del giro)
> e **L3** (la vista), più le otto consegne BE del §5.
>
> **Correlati:**
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md) (il documento madre) ·
> [brief-db-rls-commesse.md](../work-done/brief-db-rls-commesse.md) (il cantiere
> gemello: 3 changeSet + 1 pgTAP) ·
> [brief-db-grant-batch-cleanup-note.md](../work-done/brief-db-grant-batch-cleanup-note.md)
> (il precedente del canale batch, che qui **non** si ripete) ·
> [linee-guida-sql.md](../../linee-guida-sql.md) §10 (RLS) — di cui questo brief
> propone una **precisazione**, §3.3.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Regge, e non si riapre** | Il pattern RLS è in casa e collaudato (`rls_*_ef_whitelist` + `fn_scope_ef_whitelist`) · il dispatcher «di chi è questa riga» **esiste già** (`script.fn_resolve_emittente_fiscale_id`, 5 modi) · il canale batch è già coperto (`BYPASSRLS` + GRANT) | §1.1 |
| 🔴 **Cinque difetti, tutti dello stesso lato** | colonna di perimetro assente · `tx_id` assente · `correlation_id` identifica il **lotto**, non il giro · `entity_id = 0` · `actor` costante | §1.2 |
| ⛔ **Il vincolo che governa tutto** | Append-only per trigger: `UPDATE` **e** `DELETE` vietati ⇒ **nessun backfill, mai**. Unica via: `TRUNCATE` | §1.3 |
| ⛔ **Tre premesse dell'analisi cadute** | La RLS **morde già** (l'app non è owner) · il canale batch non è a rischio · B1 (il 67%) è chiuso | §1.4 |
| ✅ **Decisioni** | **D-1…D-16**, tutte prese con Tid il 2026-08-22 — D-1 e D-9 **riviste** in coda al rilievo sui lucchetti | §2 |
| 🧩 **Il disegno** | Derivazione nel trigger (la firma di `fn_log_event` **non cambia**) · policy a parità di famiglia · retention che convive con l'append-only · `vw_giornale_entita` | §3 |
| 📋 **Il piano** | **L1** la riga parlante — ✅ **APPLICATO E VERDE** (8 changeSet + 3 append a CSV) → **L2** l'identità del giro (2) → **L3** la vista (1, si accende col Passo A) | §4 |
| 🔵 **A carico del BE** | 8 consegne, di cui **BE-1 è un difetto vero e vive già oggi** | §5 |
| 🧪 **Presidio** | ✅ **33 asserzioni verdi, zero skip** su 5 file — 3 nuovi e 2 preesistenti adeguati. Il quarto file previsto **non** è stato scritto: esisteva già | §6 |
| ✅ **Domande aperte** | **Zero.** Le sei del primo giro chiuse il 2026-08-22 | §8 |
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
| **D-9** | ⭐ **`entity_type` con `CHECK`** *(rev. 2026-08-22, era una FK a `config.sorgenti`)*: `CHECK (entity_type IN ('LOTTO','COMMESSA','FATTURA'))`. `entity_id` = **la PK `id` della tabella, sempre** | Un tipo ignoto resta **rifiutato**, che era lo scopo. ⛔ **Perché non la FK:** (a) genererebbe il lucchetto `require_attivo`, e un diario non deve smettere di scrivere (D-12); (b) la FK permetterebbe di **seedare un tipo nuovo in `config.sorgenti` che il trigger non sa risolvere** — una configurazione che dice sì e un trigger che dice no. Col `CHECK`, vocabolario e dispatch cambiano **nello stesso changeSet**. Stessa forma di `chk_event_log_severity`, già sulla tabella. ⚠️ Il `key_selector` (`uid` per preventivi e offerte) serve al **grafo di lineage**, non al giornale |
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
| `domain` | `text` | = | |
| `entity_type` | `text` | **`CHECK`** | `IN ('LOTTO','COMMESSA','FATTURA')` (D-9) |
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

⚠️ **Resta comunque una regola da scrivere**: se un domani qualcuno aggiunge una
FK verso una tabella con `attivo`, l'automazione genererà
`trg_event_log_a10_<padre>_require_attivo_ins_upd`, e i `BEFORE ROW` scattano in
**ordine alfabetico**. `deriva` deve continuare a stare prima, o il lucchetto
troverebbe un `NULL` e si spegnerebbe da solo. **Il nome del trigger è
load-bearing**: rinominarlo `..._a10_scope_deriva_ins` lo manderebbe dopo la `s`
di `sorgenti`, e il difetto non si vedrebbe finché non si disattiva qualcosa.

### 3.6 `vendite.vw_giornale_entita` — il disegno (si implementa al Passo A)

**Il problema che risolve.** Una timeline letta dal solo `event_log` mostra
**quattro** codici per lotto (`PIPELINE_STARTED`, `STEP_COMPLETED`,
`PIPELINE_COMPLETED`, `PIPELINE_ERROR`). Il resto della storia di quel lotto sta
altrove: 426 righe in `fatturazione_lotti_log`, 194 in
`fatturazione_lotti_task_runs`, i log per fattura.

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
| 50 | `create-vw-giornale-entita` | `20_code/vendite` | §3.6, `security_invoker` |

---

## 5. 🔵 A carico del BE — *scritto qui, non toccato da qui*

> **Perimetro DB:** questo cantiere non modifica `backend/`. Le richieste si
> scrivono, non si implementano.

| # | Consegna | Blocca? |
| --- | --- | --- |
| **BE-1** | ⛔ **`severity="WARNING"` → `"WARN"`** in `commesse_service.py:221`, **e il test che asserisce il valore rotto**. È un difetto **già vivo** (§1.2) | No — **e va fatto subito, prima di L1** |
| **BE-2** | `correlation_id` = **un `uuid` nuovo per giro**, generato dal runner e dall'orchestratore push; scritto anche su `task_runs` e `commesse_push_log` (D-7) | Sì, dopo L2 |
| **BE-3** | La riga di `commesse_push_log` nasce **in testa** al giro (`IN_ESECUZIONE`) e si chiude alla fine; `PUSH_STARTED`/`PUSH_COMPLETED` **escono da `event_log`** (D-3) | Sì — senza, quelle scritture falliscono sul `NOT NULL` |
| **BE-4** | `EMITTIBILITA_FALLITA` diventa **per commessa** (`entity_type = 'COMMESSA'`, `entity_id = commessa_id`), una riga per commessa fallita invece di un evento aggregato con dentro una lista di id (D-3) | Sì |
| **BE-5** | Smettere di passare `actor` e `source`: **le colonne non esistono più** (D-6) | Sì |
| **BE-6** | ⚠️ **Estrarre il BB unico di `log_event`.** `pipeline_repository.log_event` e `commesse_repository.log_event` sono **copia carbone**: finché restano due, ogni modifica si scrive due volte | No, ma è il momento giusto |
| **BE-7** | Le scritture di diario passano dal telaio **`_diagnostica_best_effort`** già presente in `pipeline_runner`. ⭐ Dopo L1 una `log_event` **può fallire** (`NOT NULL`, FK, `WITH CHECK`), e un difetto del diario non deve mai diventare il messaggio che legge l'operatore — è **la stessa classe** di BE-1. Vedi **Q-3** | Sì, di fatto |
| **BE-8** | *(Passo 2, indipendente da tutto)* `request_id` nel formatter di logging — esiste già come contextvar. **E già che si è lì**: `dbops.request_log.emittente_attivo_id` e `tx_id` sono **due colonne morte** (0 valorizzate su 353.758) e il valore dell'emittente ce l'ha già il JWT: o si collegano o si tolgono | No |

---

## 6. Il presidio pgTAP — ✅ **33 asserzioni verdi, zero skip**

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

## 9. Registro

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
