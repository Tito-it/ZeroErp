# Brief BE → DB — il registro errori non sa nominare due terzi degli errori

> 🟢 **CHIUSO — 2026-08-04.** Il passo 5 (§9.8), l'ultimo aperto, è fatto lato BE:
> il check anti-ricaduta esiste ed è costruito **sui punti di chiamata** come
> chiedeva il §9.6 — [`test_error_codes_declared_guardrail.py`](../../../../backend/apps/core/tests/test_error_codes_declared_guardrail.py)
> (AST, senza DB, allowlist vuota). Al primo giro ha trovato **28 codici** sfilati:
> 24 dichiarati, un generico `E_NOT_FOUND` corretto in quattro call-site, e
> `E_VALIDAZIONE` (che è vostro) sostituito con `E_ANAG_VALIDAZIONE` in due.
> `E_OFFERTA_XXX` era un **falso positivo**: è il testo di un commento che
> documenta la convenzione `RAISE EXCEPTION USING MESSAGE=...`, non un call-site.
>
> **Il seguito vive altrove:** i 28 codici nuovi vanno a catalogo →
> [brief-db-seed-messaggi-errore-round-2.md](brief-db-seed-messaggi-errore-round-2.md)
> (aperto), che porta anche il vostro gemello del check lato DB.
>
> ---
>
> 🟢 **Stato precedente: ACCOLTO CON MODIFICHE — APPLICATO e verificato il 2026-08-03.**
> Seed a catalogo (595 righe), fix funzione applicato, controprova verde: §9.8.
> La diagnosi è confermata sui dati e i 207 testi sono buoni. **Cambiano quattro cose:**
> il seed viaggia sul CSV Liquibase e non come `INSERT` (§9.2); la lista cresce di
> 14 codici sollevati da funzioni DB vive (§9.3); insieme al seed parte un fix a
> `fn_log_error_only`, senza il quale il buco resta aperto per i client non italiani
> (§9.4); e il ripiego su `MESSAGGIO_NON_DEFINITO` smette di essere distruttivo — il
> §5 lo rimandava, Tid ha deciso di farlo subito (§9.9). Alcune misure del brief
> sono corrette in §9.5.
> **Leggere il §9 prima del resto:** i paragrafi §1–§8 sono il testo originale del BE,
> lasciato integro come richiesta in ingresso, con richiami «⚠️ Errata» dove la
> verifica sul DB ha detto altro.
>
> ---
>
> **Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** `config.messaggi_errore` non contiene **207 dei 360** codici che
> l'applicativo dichiara. Quando uno di quelli viene loggato, `dbops.error_log`
> registra la riga sotto `MESSAGGIO_NON_DEFINITO` e **il codice originale è
> perduto**: resta traccia che è successo qualcosa, non di *cosa*.
> **Cosa chiediamo:** un seed. La proposta SQL è già scritta, validata in
> rollback e idempotente:
> [`backend/scripts/db-proposals/PROPOSTA_seed_messaggi_errore_mancanti.sql`](../../../../backend/scripts/db-proposals/PROPOSTA_seed_messaggi_errore_mancanti.sql).
> **Correlati:** [Messaggi-di-Errore-e-Generazione-Log.md](../../guide/Messaggi-di-Errore-e-Generazione-Log.md) ·
> [analisi-diagnostica-produzione-senza-accesso-db.md](../work-in-progress/analisi-diagnostica-produzione-senza-accesso-db.md) (Fase 0)

---

## 1. Il fatto, misurato

| | |
| --- | --- |
| codici in `config.messaggi_errore` | **373** |
| codici dichiarati in `apps/core/services/error_policies.py` | **360** |
| **dichiarati ma NON a catalogo** | **207** (57%) |
| righe di `dbops.error_log` già degradate a `MESSAGGIO_NON_DEFINITO` | **41.885 su 62.418** (67%) |

I 207 mancanti coprono tutte le famiglie del dominio, non un angolo:
`E_VENDITE` 18 · `E_UI` 16 · `E_PIPELINE` 13 · `E_AI` 8 · `E_PREV` 8 ·
`E_CATALOGO` 7 · `E_COMMESSA` 7 · `E_NOTA` 7 · `E_DOCUMENTI` 6 · `E_ORD` 6 ·
`E_TASK` 6 · `E_ANAG` 5 · `E_DDT` 5 …

## 2. Perché è più grave di un messaggio brutto

`script.fn_log_error_only` risolve il codice contro il catalogo; se non lo
trova ripiega su `MESSAGGIO_NON_DEFINITO` — e siccome `error_log` conserva
**`messaggio_errore_id`** (FK) e non il codice in chiaro, **quel ripiego è
distruttivo**: verificato sui dati, il `context` jsonb delle righe degradate
non contiene il codice originale.

```text
context delle righe MESSAGGIO_NON_DEFINITO (ultime 3):
  {"field": "articolo_id", "value": "xxx"}
  {"uom_id": 0}
  {"ba_id": 100, "uom_id": 5, "utility_id": 7, "articolo_id": "019bac81-…"}
```

Non è quindi «il log è meno leggibile»: è che **41.885 errori registrati non
sono più attribuibili**, e nessuna analisi a posteriori potrà recuperarli. Ogni
giorno che passa la quota cresce.

> ⚠️ **Errata (DB, 2026-08-03).** La perdita del codice è confermata (su 42.172
> righe degradate solo **16** portano il codice nel `context`), ma «41.885 errori
> non attribuibili» sovrastima di due ordini di grandezza il danno informativo:
> quelle righe sono **185 combinazioni distinte** di `(area, function_name,
> context)`, ripetute in media 228 volte. E `error_log` ha **retention ~30 giorni**
> (`cleanup_at` + `dbops.fn_purge_cleanup_expired`): 51.175 righe su 63.742 hanno
> già la data di purga fissata. Il registro è una finestra mobile, non un archivio:
> non «cresce ogni giorno», si rinnova. Misure complete in §9.5.

<!-- markdownlint-disable-next-line MD028 -->
> 💡 **Perché lo scopriamo ora.** Cercavamo tutt'altro: uno strumento per
> consultare i log di fatturazione (richiesta di Tid, 2026-08-03). Il primo
> sguardo al contenuto reale di `error_log` ha mostrato che il 67% delle righe
> non sa dire quale errore rappresenta — cioè che **costruire il visualizzatore
> prima di questo seed significherebbe costruire una finestra sul rumore**.

## 3. Cosa chiediamo

**Applicare il seed** dei 207 codici in `config.messaggi_errore`, lingua `it`.

La proposta è già pronta e **non è un elenco di codici da riempire a mano**:
il testo di ogni riga è il `user_message` che `error_policies.py` già
restituisce all'utente per quel codice. Non abbiamo inventato messaggi nuovi —
abbiamo portato nel catalogo quelli che l'API pronuncia da sempre, così che
anche il log possa nominarli. Nessuno dei 207 era privo di `user_message`.

```sql
INSERT INTO config.messaggi_errore (codice, lingua, messaggio) VALUES
    ('E_ADMIN_EMAIL_DUPLICATA', 'it', 'Email gia'' in uso.'),
    ('E_AI_TOOL_DENIED', 'it', 'Non hai i permessi per questo strumento AI.'),
    …  -- 207 righe
ON CONFLICT (codice, lingua) DO NOTHING;
```

✅ **Validato in transazione con rollback** sul DB di sviluppo:
374 → 581 righe (207 inserite), **secondo giro idempotente** (581 → 581),
nessun vincolo violato (`uq_messaggi_errore_codice_lingua` regge).

`causa` e `soluzione` restano **NULL** di proposito: sono campi di diagnosi
che meritano di essere scritti con calma e con la vostra conoscenza del
modello, non dedotti da noi in blocco.

> ⚠️ **Errata (DB).** L'`INSERT` non è il veicolo giusto — il catalogo si semina
> **solo** dal CSV Liquibase, altrimenti i 207 codici esistono su questo DB e su
> nessun altro (§9.2). Nota di dettaglio: nel catalogo `causa`/`soluzione` vuote
> sono **stringa vuota, non NULL** (85 righe, zero NULL); il seed segue la forma
> esistente.

## 4. Due decisioni che lasciamo a voi

| # | Questione | La nostra opinione |
| --- | --- | --- |
| **4.1** | **Lingua `en`.** Il catalogo ha `it` e `en`; noi proponiamo solo `it`. | Non bloccante: `fn_get_messaggio` fa cascata con fallback `it`. L'`en` può seguire quando serve davvero — meglio 207 righe italiane oggi che 414 righe di cui metà tradotte male |
| **4.2** | **Come evitare che si riapra.** Oggi nulla impedisce di aggiungere un codice a `error_policies.py` e dimenticarlo a catalogo — è così che siamo arrivati a 207. | Un **check CI** che confronti i due insiemi e fallisca sui nuovi disallineati. Lo scriviamo noi lato BE (gira senza DB, stesso stile di `test_transaction_atomicity_guardrail`) se siete d'accordo sul principio. Da valutare se far fallire solo sui codici NUOVI o su tutti (col seed applicato la distinzione sparisce) |

> ⚠️ **Errata (DB) sul 4.1.** La cascata su `it` esiste in `fn_get_messaggio` e in
> `fn_log_and_raise_error`, ma **non** in `fn_log_error_only`, che è proprio la
> funzione di cui parla questo brief. Con `myapp.user_language = 'en'` il log non
> degrada: **sparisce**. Vedi §9.4 — la conclusione «solo `it`» resta giusta, la
> motivazione no.
>
> ⚠️ **Errata (DB) sul 4.2.** Confrontare `error_policies.py` con il catalogo
> lascia fuori i codici passati **direttamente** a `log_error_only` senza
> `ErrorPolicy` (35 casi, fra cui `E_PIPELINE_DRIVER_MAX_ITER`, che degrada oggi) e
> tutto il lato DB. Il check va costruito sui **punti di chiamata**: §9.6.

## 5. Cosa NON chiediamo

| Cosa | Perché no |
| --- | --- |
| Bonificare le 41.885 righe già degradate | Il codice originale **non è recuperabile**: non è nel `context`. Riscriverle significherebbe inventare. Restano come sono, e il seed ferma l'emorragia da qui in avanti |
| ~~(la bonifica è una non-questione)~~ | ⚠️ **Errata (DB):** giusto non farla, ma non perché sia impossibile — perché quelle righe **si cancellano da sole**. Hanno già `cleanup_at` valorizzato (purga entro il 2026-09-01): fra un mese il problema non esiste più, con o senza bonifica |
| Cambiare `fn_log_error_only` perché salvi il codice in chiaro | Sarebbe una modifica di modello sensata (un `codice_originale text` accanto alla FK renderebbe il ripiego non distruttivo), ma è **un'altra discussione**: il seed la rende molto meno urgente, e non vogliamo accoppiare le due cose. Se la ritenete interessante, apriamola separatamente |
| Toccare `error_policies.py` | È il registro applicativo, resta nostro |

## 6. Un difetto nostro che questo seed chiude

`E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA` è nato **oggi** (dashboard
competenza, traccia del fallimento della previsione fatture) e l'abbiamo
registrato in `error_policies.py` **senza accorgerci che il catalogo DB è un
secondo registro da alimentare**. Sarebbe finito anch'esso in
`MESSAGGIO_NON_DEFINITO` al primo guasto — cioè la traccia che avevamo appena
aggiunto per non perdere l'informazione l'avrebbe persa comunque.

È nell'elenco dei 207, ed è anche il motivo per cui proponiamo il check di
§4.2: la disciplina da sola non ha retto 207 volte, non reggerà la 208ª.

## 7. Definizione di «fatto»

1. `config.messaggi_errore` contiene i 207 codici in lingua `it`;
2. un errore applicativo di un codice prima mancante compare in
   `dbops.error_log` **col proprio codice**, non con `MESSAGGIO_NON_DEFINITO`
   (controprova diretta: sollevare `E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA`
   e rileggere l'ultima riga del registro);
3. la quota di righe degradate **smette di crescere** (le vecchie restano);
4. deciso il §4.2 — con o senza check CI, ma deciso.

---

## 8. Nota operativa

Il seed va **committato** per avere effetto sul logging: `fn_log_error_only`
scrive via `dblink` su una connessione separata, che non vede una transazione
non ancora conclusa. È il motivo per cui la nostra validazione in rollback ha
potuto verificare l'INSERT e l'idempotenza, ma **non** la controprova del
punto 7.2 — quella si fa dopo l'apply, ed è una riga.

---

## 9. Risposta DB — verifica critica e piano di lavorazione

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-03. Da qui in avanti il documento
> è la risposta, non più la richiesta.

### 9.1 Come è stata verificata la richiesta

Niente è stato preso per buono: i conteggi del brief sono stati rifatti sul DB di
sviluppo in sola lettura, e le liste di codici ricostruite dal repository —
`error_policies.py` da un lato, corpi delle funzioni **vive** (documentazione
auto-generata `docs/it/dbzero/`, non gli YAML, che possono essere superati) dall'altro.

Il risultato è che **il cuore del brief regge**:

| Affermazione | Esito |
| --- | --- |
| 374 righe a catalogo, 360 codici dichiarati, 207 assenti | ✅ esatto. Zero collisioni con codici già presenti, nessun messaggio contiene `%` (quindi nessun rischio su `format()`), tutti e 207 hanno una `ErrorPolicy` |
| Il codice originale è perduto nel ripiego | ✅ confermato sui dati: su 42.172 righe degradate solo **16** portano il codice nel `context` |
| Sono errori del backend | ✅ confermato: i venti `function_name` più frequenti fra le righe degradate sono **tutti** `area='backend'` (`pricing_service` 11.718, `commesse_service.*`, `listini_service.*`, `catalogo_service.*`) |

L'estrazione dei 207 da `error_policies.py` è pulita e completa **rispetto a quella
fonte**. I paragrafi che seguono dicono dove quella fonte non basta.

### 9.2 Il seed non può essere un `INSERT`

`config.messaggi_errore` non si popola a mano: è alimentata da un `loadUpdateData`
con `runOnChange: true` sul file
[`80_data/sql/config/messaggi_errore.csv`](../../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv)
(changeSet
[`20260614-08`](../../../../db/changelog/migrations_v2/80_data/changelog/20260614-08-upsert-messaggi-errore-chiusura-flusso-prematuro-mctit.yaml),
`validCheckSums: ANY`, chiave `id`). Oggi il CSV ha 374 righe e la tabella ne ha 374:
il file **è** il catalogo, la tabella ne è la proiezione.

Un `INSERT` diretto crea righe che vivono su questo database e su nessun altro. Su un
ambiente ricostruito da Liquibase — CI, nuova installazione, rebuild locale — i 207
codici tornerebbero mancanti, e la «definizione di fatto» del §7 risulterebbe vera qui
e falsa dappertutto. In più sarebbe la prima divergenza fra CSV e tabella, e da quel
momento il file smetterebbe di essere una fonte affidabile per chiunque.

**Forma adottata:** append delle righe al CSV con `id` espliciti a partire da 577,
nessun changeSet nuovo (il loader `runOnChange` esistente le ripesca al `migrate`
successivo: aggiungerne uno per ogni lotto è ridondanza già deprecata in questo
progetto). Tre dettagli di conversione che l'`INSERT` nasconde:

- l'escape SQL `gia''` deve tornare `gia'` — nel CSV l'apostrofo è un carattere qualsiasi;
- i messaggi che contengono una virgola vanno racchiusi fra doppi apici (circa metà della lista);
- `causa` e `soluzione` vuote nel catalogo sono **stringa vuota**, non NULL (85 righe
  così, zero NULL): il seed replica la forma esistente invece di introdurre la prima
  disomogeneità.

> **Perché l'`INSERT` del BE non è esploso sulla PK.** `id` è
> `GENERATED BY DEFAULT AS IDENTITY` e la sequenza è ferma a 990 mentre il massimo
> in tabella è 576: l'inserimento senza `id` ha pescato numeri liberi. Ha funzionato
> per fortuna, non per costruzione — con la sequenza allineata avrebbe collezionato
> violazioni di chiave primaria, che `ON CONFLICT (codice, lingua)` non intercetta.

### 9.3 La lista dei 207 non è il buco intero

I 207 chiudono il lato backend. Restano **14 codici emessi da funzioni DB vive** e
assenti dal catalogo, che il seed include. Dodici passano da
`fn_log_and_raise_error` e degradano esattamente come quelli del backend; gli ultimi
due (`E_RECONCILE_AMBIGUO`, `E_TASK_RUNTIME`) non passano dal registro errori — sono
scritti come `errcode` in tabelle di log dedicate (`pratiche.reconcile_errori`,
`vendite.attivita_fatturabili_lotti_task_runs`) — ed entrano a catalogo perché siano
leggibili da chi quelle tabelle le consulta, non perché degradino.

| Codice | Emesso da |
| --- | --- |
| `E_VALIDAZIONE` | 10 funzioni (`fn_genera_ddt_da_ordine`, `fn_conferma_reso`, `fn_annulla_reso`, …) |
| `E_COMPETENZA` · `E_COMPETENZA_SUPERATA` · `E_FONTE_QUANTITA_NON_VALIDA` · `E_REGOLA_FATTURAZIONE_MANCANTE` | `trgfn_attivita_fatturabili_guard_fonte` |
| `E_COERENZA_ID` · `E_PARAMETRI_TABELLA` | `trgfn_attivita_fatturabili_guard_ba_coerenza` |
| `E_SCOPE_EMITTENTE` | `trgfn_guard_emittente_scope` |
| `E_RECONCILE_AMBIGUO` | `fn_reconcile_sorgente` |
| `E_LOCK_COLUMNS` | `fn_run_automations_lock_columns`, `fn_run_automations_drop_lock_trg` |
| `E_STORICO_UD` | `fn_run_automations_storico` |
| `E_NOTE_RIGA_MISMATCH` | `trgfn_note_validate_generic` |
| `E_ARTICOLO_SOLO_COMPONENTE` | `trgfn_articoli_componenti_guard_solo_componente` |
| `E_TASK_RUNTIME` | `fn_set_runtime_task_run_esito` (colonna `error_code`, non loggato) |

> **Il numero di `%s` non è a piacere.** In `fn_log_and_raise_error` la `format()`
> **non** è protetta da `EXCEPTION`: un template con più segnaposto dei valori passati
> trasformerebbe l'errore di dominio in un «too few arguments for format()». I
> messaggi di questi 14 sono quindi scritti sull'arità **minima** fra i loro punti di
> chiamata vivi — i valori in eccesso `format()` li ignora, quelli mancanti no —
> e l'arità è stata verificata call site per call site sui corpi vivi (13 siti per
> `E_VALIDAZIONE`, 3 per `E_COMPETENZA`, e così via; `E_ARTICOLO_SOLO_COMPONENTE`
> chiama con `VARIADIC ARRAY[]::text[]` e quindi il suo messaggio non ha segnaposto).

Due codici citati in YAML storici — `E_DOC_COMPONENTE_NON_ESPOSTO` e
`E_RISORSA_UMANA_AUTH_USER_NON_GESTORE` — **non** entrano nel seed: le funzioni vive
non li sollevano più, sono residui di revisioni superate.

> ### Il caso `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`
>
> Il §6 lo legge come una dimenticanza del BE. Non lo è: quel codice (id 441) è stato
> **cancellato deliberatamente** dal catalogo dal changeSet
> [`20260513-01`](../../../../db/changelog/migrations_v2/80_data/changelog/20260513-01-delete-messaggi-errore-deprecati-bom-mctit.yaml),
> con la motivazione «opzione A relaxed mai entrata in produzione».
>
> Solo che `fn_check_ddt_emittibile` e `trgfn_ddt_guard_transizione_approvazione` —
> vive oggi nel DB, e più recenti di quella cancellazione — continuano a sollevarlo.
> È una regressione nostra: il catalogo ha perso un codice che le nostre stesse guard
> usano. Rientra nel seed come **decisione DB consapevole**, e la motivazione del
> 2026-05-13 va considerata superata.

### 9.4 Il seed da solo non basta: `fn_log_error_only` perde le righe non italiane

Il §4.1 dà per buono che la lingua non sia bloccante «perché `fn_get_messaggio` fa
cascata con fallback `it`». Vero per `fn_get_messaggio`, vero per
`fn_log_and_raise_error` — **falso per `fn_log_error_only`**, che è la funzione di cui
parla questo brief. Il suo lookup è secco:

```sql
FROM config.messaggi_errore WHERE codice = p_error_code AND lingua = v_lang
```

`v_lang` viene da `myapp.user_language`, che `UserLanguageMiddleware` valorizza
dall'header `Accept-Language` su ogni richiesta `/api/`. Per un client inglese, quindi:
il codice non si risolve; il ripiego su `MESSAGGIO_NON_DEFINITO` **nemmeno**, perché
quella riga esiste solo in `it` (l'unica riga `en` dell'intero catalogo è
`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`); `v_id` resta NULL e la funzione esce
con un `RAISE WARNING ... log non persistito`.

Il risultato non è un log degradato: **è nessun log**. Un modo di perdere l'errore
peggiore di quello descritto nel brief, e che il seed in `it` non tocca. Il rimedio è
la stessa cascata già usata dalle altre due funzioni
(`WHERE lingua IN (v_lang, 'it') ORDER BY (lingua = v_lang) DESC`) e viaggia insieme al
seed, in un changeSet dedicato.

Conclusione pratica: **il §4.1 resta accolto** — si semina solo `it` — ma perché la
cascata la mettiamo dove manca, non perché ci fosse già.

> **Perché mancava proprio lì.** La cascata è arrivata il 2026-04-23 con il changeSet
> `20260423-02`, che l'ha messa su `fn_get_messaggio` e `fn_log_and_raise_error` e ha
> saltato la terza. Con ogni probabilità non è una svista: quelle due sono di
> `titodb`, `fn_log_error_only` è di `postgres` (è SECURITY DEFINER e scrive via
> dblink), e il migratore non può sostituire una funzione che non possiede. Il muro
> che ha fermato quel fix ha fermato anche il primo tentativo di questo — vedi §9.10.

### 9.5 Errata sulle misure

Le misure del brief sono state rifatte. I numeri veri, al 2026-08-03:

| Misura | Nel brief | Verificato |
| --- | --- | --- |
| righe totali in `error_log` | 62.418 | **63.742** (finestra 2026-07-04 → 2026-08-03) |
| righe degradate | 41.885 (67%) | **42.172** (66%) |
| righe con il codice recuperabile dal `context` | «nessuna» | **16** — la sostanza del brief regge |
| **situazioni** distinte dietro le righe degradate | non misurato | **185** combinazioni `(area, function_name, context)`, ripetute in media 228 volte |
| ritenzione del registro | non citata | **~30 giorni**: 51.175 righe su 63.742 hanno già `cleanup_at`, purga fino al 2026-09-01 |
| codici a catalogo | 373 / 374 | 374 righe, **373 codici** (una sola riga è `en`) |

Due conseguenze sulla lettura del problema, non sulla decisione:

1. **Il danno informativo è più piccolo del numero.** 42.172 righe sono 185 situazioni
   ripetute, in larga parte rumore di suite di test (5.089 righe solo il 3 agosto, su un
   database di sviluppo). Il costo vero è «i prossimi trenta giorni di diagnosi sono
   ciechi», che è comunque un buon motivo per fare il seed subito.
2. **Non c'è emorragia da fermare, c'è una finestra da rendere leggibile.** Il registro
   si rinnova da solo; le righe già degradate spariranno entro il 1° settembre. Il §5
   («non chiediamo la bonifica») è la scelta giusta per la ragione sbagliata.

### 9.6 Palla al BE — 35 codici che nessun catalogo può indovinare

`error_policies.py` non è l'universo dei codici che il backend fa arrivare al log.
Nel codice ci sono **35 codici citati come letterale e mai dichiarati** come
`ErrorPolicy`. Il caso che conta:

```python
# backend/apps/vendite/services/pipeline_runner.py:645
ErrorManager.log_error_only(code="E_PIPELINE_DRIVER_MAX_ITER", ...)
```

Questo codice finisce nel log e degrada **oggi**, non è nei 207, e un check
`error_policies.py` ↔ catalogo lo dichiarerebbe verde. Nella stessa lista compare
`E_OFFERTA_XXX` (`offerte_service.py`), che ha tutta l'aria di un segnaposto rimasto.

Da qui la posizione sul §4.2: **sì al check, ma costruito sui punti di chiamata**
(i letterali passati a `code=` / `error_code`), non sulle dichiarazioni. Serve in due
esemplari simmetrici — uno lato BE sul codice Python, uno lato DB che confronti i
codici sollevati dalle funzioni vive con il CSV — perché i due registri si sfilano
per vie diverse. Sulla domanda «solo i nuovi o tutti»: **tutti**, ma solo dopo che
questo seed è passato, altrimenti nasce rosso il primo giorno.

L'elenco completo dei 35 è ricavabile con una passata sui letterali `E_*` in
`backend/apps/` (esclusi i test) sottratti a catalogo e proposta; qui basta dire che
vanno o dichiarati in `error_policies.py`, o rimossi se sono residui.

### 9.7 Un confine da non superare dopo

Il catalogo DB è un registro di **template**: 324 righe su 374 contengono `%s` e
vengono riempite da `format(..., VARIADIC valori)`. I 207 codici del BE sono frasi
finite senza segnaposto. La convivenza è innocua — `fn_log_error_only` chiama `format`
solo quando riceve valori, e il backend chiama sempre con `VARIADIC ARRAY[]::text[]` —
ma d'ora in poi il catalogo ospita due specie di righe.

Va messo per iscritto adesso: **il messaggio all'utente resta in `error_policies.py`**.
La riga a catalogo serve al log. Oggi il backend non invoca mai `fn_get_messaggio`
(verificato), e deve restare così: se un domani qualcuno «unificasse» i due registri,
il testo mostrato all'utente comincerebbe a dipendere da una GUC di sessione.

### 9.8 Lavorazione e definizione di «fatto» rivista

| # | Passo | Stato |
| --- | --- | --- |
| 1 | **Seed** — 207 codici del BE + 14 del §9.3 appesi a `messaggi_errore.csv`, `id` **577…797**, lingua `it`, `causa`/`soluzione` vuote come le altre (le due voci più opache, `E_VALIDAZIONE` e `E_ARTICOLO_SOLO_COMPONENTE`, hanno causa e soluzione scritte). Nessun changeSet nuovo: il loader `runOnChange` esistente le carica al `migrate` | ✅ scritto — CSV a 595 righe, zero `id` duplicati, zero coppie `(codice, lingua)` duplicate |
| 2 | **Fix `fn_log_error_only`** — [`20260803-11-fix-fn-log-error-only-cascata-lingua`](../../../../db/changelog/migrations_v2/20_code/script/20260803-11-fix-fn-log-error-only-cascata-lingua-mctit.yaml): cascata lingua (§9.4) **e** conservazione del codice originale nel `context` (§9.9) | ✅ scritto — corpo dalla doc auto-gen, l'intero changeSet eseguito in transazione con rollback: prestito owner, `CREATE FUNCTION`, `COMMENT`, restituzione owner a postgres, `SECURITY DEFINER` intatto |
| 3 | **Apply** — `migrate` sul DB di sviluppo | ✅ **applicato 2026-08-03 20:37** — changeSet `20260803-11` EXECUTED, catalogo a **595 righe** (221 nuove), funzione con cascata e `codice_errore_originale`, owner tornato a `postgres` dalla sync `runAlways` di `90_end` alle 20:38 |
| 4 | **Controprova** — §7.2 del brief | ✅ **verde**, tre prove qui sotto |
| 5 | **Check anti-ricaduta** — §9.6, i due esemplari simmetrici | ⏳ prossimo passo |

**La controprova, per esteso.** Tre chiamate a `fn_log_error_only` e una rilettura di
`dbops.error_log` (righe riconoscibili da `function_name = 'brief-seed-*'`):

| Prova | Codice | Prima | Ora |
| --- | --- | --- | --- |
| A | `E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA` (il codice nato oggi, §6) | `MESSAGGIO_NON_DEFINITO` | registrato **col proprio nome** |
| B | `E_VALIDAZIONE` con `myapp.user_language = 'en'` | **nessuna riga** | registrato col proprio nome, via ripiego su `it` |
| C | `E_CODICE_CHE_NON_ESISTE_ANCORA` (inventato) | riga muta | `MESSAGGIO_NON_DEFINITO`, ma con `context->>'codice_errore_originale' = 'E_CODICE_CHE_NON_ESISTE_ANCORA'` |

La C è la più importante delle tre: dimostra che il *prossimo* codice mancante non
sarà più anonimo.

> **Da sapere prima di rifare la prova.** Il §8 ha ragione — `fn_log_error_only`
> scrive su una connessione `dblink` separata — ma la conseguenza vale in entrambi i
> versi: una controprova lanciata dentro una transazione poi rollbackata **lascia
> comunque la riga** in `error_log`. Le tre righe qui sopra sono reali e restano fino
> alla purga automatica.

Verifica già fatta a tavolino sul catalogo reale: con la cascata, un codice presente
solo in `it` si risolve anche per una sessione `en` (id 204 per
`E_PARAMETRO_INVALIDO`), e l'unica riga `en` esistente continua a vincere sulla
propria italiana (id 488). Oggi, senza cascata, la prima delle due query non
restituisce nulla — cioè nessun log.

«Fatto» significa, rispetto al §7 del brief: i 221 codici sono nel **CSV** (non solo
nella tabella di questo DB); un errore di un codice prima mancante compare in
`error_log` col proprio nome; **e** lo stesso vale per una richiesta non italiana.

### 9.9 Il ripiego smette di essere distruttivo — deciso e fatto

Nel ramo di ripiego di `fn_log_error_only` il codice originale veniva **già calcolato**
(`messaggio || ' ' || p_error_code`) e poi buttato via, perché `error_log` conserva
solo la FK. Il BE l'aveva notato e l'aveva messo fra le cose che *non* chiedeva
(§5), proponendo una colonna `codice_originale text` da discutere a parte.

**Decisione di Tid, 2026-08-03: si fa subito**, e senza toccare il modello di
`error_log`. Una riga nel ramo `NOT FOUND`:

```sql
v_ctx := v_ctx || jsonb_build_object('codice_errore_originale', p_error_code);
```

Da qui in avanti una riga degradata dice comunque **quale** errore era. La chiave è
`context->>'codice_errore_originale'` — nome esplicito per non collidere con la chiave
`code` che il `pipeline_error_logger` del BE già scrive nel proprio `meta`.

È la parte del lavoro che vale più del seed stesso: il seed chiude i 221 codici di
oggi, questa riga rende innocuo il **222°**. Perché un altro disallineamento ci sarà —
la disciplina non ha retto 207 volte, e il check di §9.6 nascerà comunque dopo
il prossimo codice, non prima.

### 9.10 Il muro dell'owner, e come lo si attraversa

Il primo tentativo di applicare il changeSet è morto così:

```text
ERRORE: bisogna essere proprietari della funzione fn_log_error_only
```

`script.fn_log_error_only` è una delle quattro funzioni sensibili registrate in
`dbops.sec_functions_owner`: è `SECURITY DEFINER` e deve appartenere a `postgres`,
altrimenti non può scrivere via dblink. Il migratore (`titodb`) non ne è proprietario,
e PostgreSQL rifiuta `CREATE OR REPLACE` su funzione altrui. È, con ogni probabilità,
lo stesso muro che nell'aprile 2026 fece saltare questa funzione dal fix della cascata
lingua — il difetto del §9.4 non è nato da una svista ma da un permesso.

Il progetto ha già il meccanismo: `dbops.fn_sync_functions_owner()` è `SECURITY
DEFINER` posseduta da `postgres`, quindi può riassegnare la proprietà. Il changeSet la
usa in tre tempi, restando dentro Liquibase e senza chiedere una sessione superuser:

1. **prestito** — `required_owner` → utente corrente, `SELECT dbops.fn_sync_functions_owner()`,
   più un guard **fail-loud** che verifica di aver davvero ottenuto la proprietà (la
   funzione di sync degrada a `WARNING` e non solleva: senza il guard il fallimento
   riemergerebbe più avanti come un generico «bisogna essere proprietari»);
2. **sostituzione** — `CREATE OR REPLACE` + `COMMENT`;
3. **restituzione** — `required_owner` → `postgres`, `SELECT dbops.fn_sync_functions_owner()`.

Sotto ci sono due reti già esistenti: il seed `80_data` riscrive comunque
`required_owner = postgres`, e `90_end/20251123-04` rilancia la sync **a ogni update**
(`runAlways: true`). E se il changeSet fallisse a metà, il rollback della transazione
Liquibase annullerebbe anche l'`ALTER FUNCTION ... OWNER TO`, perché in PostgreSQL il
DDL è transazionale. Su database appena creato (CI) il giro è inerte: la tabella è
ancora vuota — si popola in `80_data`, che gira dopo `20_code` — e la funzione
appartiene ancora a chi l'ha appena creata.

> **Nota a margine, da sistemare separatamente.** In
> [`sec_functions_owner.csv`](../../../../db/changelog/migrations_v2/80_data/sql/dbops/sec_functions_owner.csv)
> la riga `id = 5` (`script.fn_log_error_only`) compare **due volte**, identica. Il
> `loadUpdateData` la applica due volte senza danno, ma resta un difetto del seed. E
> `dbops.fn_sync_functions_owner()` è `SECURITY DEFINER` **senza** `SET search_path`:
> non è un problema di oggi, è una superficie da chiudere quando si tocca quella
> funzione.
