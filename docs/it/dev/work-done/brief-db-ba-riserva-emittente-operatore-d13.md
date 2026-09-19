# Brief DB — Un billing account non ancora collegato appartiene a chi lo sta creando (D13)

> **Da leggere per primo: §7 — cosa resta.**
> Origine: [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md) §D13
> e [brief-db-fixture-che-costruiscono-d7-d6-d4.md](brief-db-fixture-che-costruiscono-d7-d6-d4.md) §4,
> dove il difetto è stato trovato il 2026-09-12 «strada facendo».
> Decisione di Tid, 2026-09-12: **opzione 1**, nessuna bonifica dei dati.
>
> ✅ **Stato 2026-09-14: CHIUSO — verificato contro repo, dbdev e CI.** I tre
> changeSet (`20260913-01/02/03`) sono `EXECUTED` su dbdev (13-09, 00:22–00:23,
> letto da `databasechangelog`) e mergiati su `Tito-dev` e `main`; le tre
> funzioni toccate sono `STABLE PARALLEL UNSAFE` come dichiarato. **La CI ha
> detto la sua** (14-09, corsa su `Tito-dev` per la PR #1583, verde):
> `test-ba-emittente-risoluzione-v1` e `test-fn-get-emittente-fiscale-pk` sono
> **rientrati** e le loro righe sono uscite da `baseline-rossi-ci.tsv` (commit
> `8454f7cbd`); nel registro resta solo `test-billing-account-auto-link-ef`,
> che è D7 (§6.3). I tre lettori Python delegano dal 13-09 (§6.2). Le due
> decisioni di modello di §3.4 sono **prese** (14-09): da interfaccia il DB
> rifiuta già un BA senza emittente, i percorsi senza sessione sono dati e
> non un caso d'uso — niente presidio, opzione 3 fuori dalla coda. **Non
> resta nulla**: brief archiviato in `work-done/` il 14-09 (§7.6).
>
> Stato 2026-09-13 (storico): applicato e collaudato da Tid; i quattro pgTAP
> (uno nuovo, tre riscritti) erano già verdi in prova **su dbdev come app** e
> **sullo scratch della CI** con i changeSet iniettati in transazione ritirata,
> e il caso di prodotto era **rosso** sullo scratch senza di essi (§5).
> Manuali e guide aggiornati (§6).

---

## 1. Il difetto, in una riga

Come `zeroerp_app`, `INSERT INTO anagrafiche.billing_account … RETURNING id`
moriva con *«la nuova riga viola la regola di sicurezza per riga»* (42501)
ogni volta che l'emittente di chi agiva **non** era quello di default
dell'installazione. La policy di lettura risolve il BA dal legame in
`emittenti_fiscali_billing_account`; il legame lo scrive il trigger **AFTER**
`z90_link_ef`, cioè *dopo* che il `RETURNING` ha chiesto di vedere la riga; in
quell'istante `script.fn_get_ba_emittente_sr_id` ricadeva sul **default** —
un'altra azienda. L'`INSERT` passava (la policy `_ins` chiede solo la veste
`OPERATORE`); era la **rilettura** a negare.

Riprodotto il 2026-09-12 su dbdev con un operatore vero dell'emittente 44
(`EMITEST`). Il backend fa lo stesso `RETURNING`
(`anagrafiche/db/clienti_repository.py`, `create_billing_account`) ⇒ con due
emittenti in esercizio, **gli operatori del secondo non aprivano clienti**.
Sull'emittente di default passava, ed è il motivo per cui nessuno l'ha visto.

---

## 2. Le tre risposte, e la scelta

Alla domanda *«un BA appena scritto, ancora senza legame, di chi è?»*:

| # | Risposta | Cosa costa | Cosa lascia |
| --- | --- | --- | --- |
| **1** | **di chi lo sta creando** — la riserva del resolver passa dal default all'emittente dell'operatore in sessione; default solo senza sessione | un changeSet sul lettore (+ due di coerenza, §4) e i pgTAP | la trappola sparisce per **ogni** scrittore: backend, import, shop, fixture, cantieri futuri |
| 2 | il BE scrive e rilegge dopo, senza `RETURNING` | una riga Python | il DB resta rotto: ogni altro scrittore la ritrova |
| 3 | l'emittente diventa **colonna** del BA, scritta all'`INSERT` | un cambio di modello: la tabella dei legami diventa derivata, i guard e la RLS si riscrivono — giorni | la forma più solida, coerente con «un BA ha esattamente un emittente» |

✅ **Decisione di Tid, 2026-09-12: la 1, subito.** La 3 resta in coda come
**decisione di modello**, non come lavoro. **Nessuna bonifica dei dati**: sono
dati di test — e comunque sulla macchina i 42 BA sono tutti collegati; la
riserva serve solo a quell'istante.

---

## 3. Cosa cambia sul modello

### 3.1 La regola, da due livelli a tre

`script.fn_get_ba_emittente_sr_id(ba)`:

1. **mapping specifico** del BA — invariato, vince sempre (`COALESCE` pigro);
2. ⭐ **riserva in sessione**: l'emittente dell'operatore che sta agendo,
   `script.fn_resolve_emittente_for_user(app.current_user_id)` tradotto in
   `soggetto_ruolo_id`;
3. **riserva senza sessione**: il default dell'installazione — invariato.

⛔ **Il livello 2 usa la STESSA funzione del trigger `z90_link_ef`**, e non è
una scelta di comodo: la riserva deve dire ciò che il trigger *sta per
scrivere*. Con una derivazione «più leggera» — la sola riga 1-a-1 di
`config.user_emittenti_fiscali` — un super admin con emittente attivo
(`app.current_emittente_id`) avrebbe visto la riserva rispondere `NULL` (→
default) mentre il trigger legava all'emittente attivo: lo stesso difetto,
spostato di un caso.

⚠️ **Il guard della delegata**: `fn_resolve_emittente_for_user` **solleva**
(`E_PARAMETRO_INVALIDO`, e scrive nel log via `dblink`) su `NULL` o `<= 0`.
Senza sessione non va nemmeno chiamata: nel corpo la chiamata sta dentro un
`CASE WHEN auth_user_id > 0`, che PostgreSQL valuta pigramente — un `WHERE`
sulla stessa riga lascerebbe al planner la scelta di *quando* valutare la
funzione.

### 3.2 Chi lo segue, senza una riga di modifica

Letti dalla doc auto-gen, i lettori del resolver — e quindi della nuova
regola — sono: `fn_check_ba_visible_for_emittenti` (RLS `via_efba` del BA e
ricerca universale, ramo CL), `fn_search_soggetti_universale` (la colonna
`emittente_ragione_sociale`), `anagrafiche.fn_get_emittente_fiscale_id`
(l'involucro SR: `fn_build_fattura_key`, il guard dell'albero),
`vendite.fn_resolve_registro_documento` (il sezionale), e
`dbops.fn_storico_risolvi_scope` (lo scope congelato di una versione del BA:
una versione scritta in sessione su un BA senza legame porta l'emittente di
chi ha scritto — prima portava il default).

### 3.3 Chi NON lo segue, e va bene così

`anagrafiche.trgfn_efba_guard_storia_emittente` calcola «prima» e «dopo» di un
BA senza legame **esplicitamente sul default**, non con il resolver (il suo
`COMMENT` spiega perché: in un `BEFORE DELETE` il resolver risponderebbe la
riga che si sta cancellando). Con la nuova regola resta **conservativo**: su un
`INSERT` di mapping verso Y da parte di un operatore di Y, la realtà in
sessione direbbe «prima = Y, dopo = Y, nessun movimento», il guard dice «prima
= default, dopo = Y» e, se il BA ha storia, **blocca**. Più stretto del
necessario, mai più largo: non si tocca.

La policy `rls_billing_account_ef_whitelist_ins` (gate-only su
`ruolo = OPERATORE`, «perché `via_efba` rifiuterebbe i BA nuovi») è ora
**ridondante ma innocua**: con il livello 2 `via_efba` accetterebbe il BA nuovo
dell'operatore. Resta com'è — togliere una policy per un'eleganza non è un
lavoro di questo cantiere.

### 3.4 ⚠️ Il prezzo, dichiarato

Un BA che **resta** senza legame — creato senza sessione: un seed, una
migrazione, un'installazione «0 emittenti» — era «del default» e ora è, in
sessione, **di chiunque lo guardi**, ciascuno sotto il proprio emittente: lo
vede, e ci emetterebbe sotto il proprio emittente. Il modello lo ammette (il
trigger lega sempre quando c'è una sessione; l'admin globale non può creare BA
con emittenti presenti — `a10_guard_admin_globale`) e la decisione lo accetta:
è un **dato anomalo**, non un caso d'uso. Due cose ne discendono, entrambe
**decisioni di Tid** e non lavoro di questo cantiere:

- l'opzione 3 (l'emittente come colonna del BA) è ciò che chiuderebbe il caso
  per costruzione: resta in coda come decisione di modello;
- un presidio «BA senza legame» (una vista `dbops.vw_billing_account_senza_emittente`
  a catalogo, natura `ZERO`) renderebbe visibile l'anomalia il giorno in cui
  comparisse. Oggi vale zero righe (fatto datato, 2026-09-13: 42 BA, tutti
  collegati); su un database nuovo le anagrafiche non ci sono. Proposto, non
  fatto.

✅ **CHIUSO il 2026-09-14, per decisione di Tid — e per un cancello che c'era
già.** Riverificato sul codice vivo: **nessuna modifica** sull'`INSERT` del BA
dopo il 13-09 (nessun changeSet, `create_billing_account` invariato, i trigger
sono i tre di sempre). Ma il prezzo qui sopra riguarda **solo i percorsi senza
sessione**. Da interfaccia la sessione c'è sempre, e allora:

- `a10_guard_admin_globale` (BEFORE INSERT, rev 2026-08-04) chiama
  `script.fn_check_user_can_create_ba`: passa solo chi **sta dentro un
  emittente** (emittente attivo valido per l'utente, o riga in
  `config.user_emittenti_fiscali`); chi non ne ha uno è ammesso **solo se
  l'istanza ha zero emittenti attivi**, altrimenti `E_BA_ADMIN_GLOBALE_VIETATO`
  e l'`INSERT` muore;
- `z90_link_ef` (AFTER INSERT) usa lo **stesso** resolver
  (`fn_resolve_emittente_for_user`, stessi due rami): se l'`a10` è passato con
  un emittente, il legame **si scrive sempre**.

⇒ Da interfaccia un BA senza emittente **il DB non lo accetta**. L'unica
eccezione in sessione è l'installazione a **zero emittenti**, dove non c'è
niente a cui legare e il primo emittente creato diventa il default
(`trgfn_emittenti_fiscali_default_bootstrap`) che raccoglie quei BA. I due
rami `RETURN NEW` senza legame di `trgfn_billing_account_link_ef`
(`v_user_id IS NULL`, resolver a `NULL`) servono solo a seed, migrazioni e
manutenzione a mano: **dati, non un caso d'uso** — decisione di Tid, 14-09:
«i dati vecchi non contano». Ne discende che **nessuna delle due voci sopra è
lavoro**: il presidio `ZERO` non si fa (nulla lo alimenterebbe da interfaccia)
e l'opzione 3 esce dalla coda — il cancello all'inserimento rende il caso
irraggiungibile per costruzione, che è ciò che l'opzione 3 avrebbe comprato.
⚠️ Fino a questa nota il brief citava l'`a10` senza tirarne la conseguenza.

---

## 4. Le tre facce del cantiere — i changeSet

Numerazione `20260913-01..03`, tutti `20_code`, corpo dalla doc auto-gen:

| # | File | Che cosa |
| --- | --- | --- |
| 01 | `20_code/script/20260913-01-update-fn-get-ba-emittente-sr-id-riserva-operatore-in-sessione` | **la decisione**: il livello 2. `LANGUAGE sql STABLE`, firma e `RETURNS` con `%TYPE` |
| 02 | `20_code/script/20260913-02-alter-fn-check-ba-visible-for-emittenti-senza-parallel-safe` | **onestà della marcatura**: `ALTER FUNCTION … PARALLEL UNSAFE` + `COMMENT`. Corpo intatto (un `ALTER`, non un `CREATE OR REPLACE` ricopiato) |
| 03 | `20_code/anagrafiche/20260913-03-update-fn-get-emittente-fiscale-pk-delega-al-lettore` | **una regola, un posto**: l'involucro PK delega al lettore invece di tenere la copia |

**Perché il 02.** Il `20260818-58` dichiarava *«STABLE PARALLEL SAFE, e la
seconda metà non è decorativa: la chiamante è SAFE e gira dentro la query
dinamica della ricerca; legge solo tabelle, nessuna GUC»*. Ora il resolver
legge una GUC e chiama una plpgsql `UNSAFE` (con `dblink` sul ramo d'errore):
il `SAFE` cade sul resolver e, per la stessa frase, sulla chiamante. È la mossa
già fatta il 18-08 su `fn_search_soggetti_universale` e `fn_get_search_detail`
(*«la catena dello scope è STABLE e basta»*). Costo letto dalla struttura:
~zero — i due consumatori sono già `UNSAFE`, resta la query dinamica interna
della ricerca, paginata, che un piano parallelo non lo ha mai scelto.

**Perché il 03, ed è la parte che non era nel perimetro dichiarato.** Leggendo
i chiamanti del lettore è emersa una **seconda copia** della regola:
`anagrafiche.fn_get_emittente_fiscale_pk` (07-04) riscriveva «mapping,
altrimenti default» con due sottoquery sue, e l'estrazione del 18-08 non l'aveva
toccata. Finché i livelli erano gli stessi non si vedeva; con il terzo le due
copie avrebbero risposto cose **diverse** sullo stesso BA senza legame — la RLS
lo mostra all'operatore Y, il guard di un preventivo
(`trgfn_preventivi_guard_emittente_ba`, che passa dalla `_pk`) lo rifiuta
perché «il BA è del default». Due regole per la stessa domanda, in silenzio:
esattamente ciò che l'estrazione voleva impedire. Il 03 lascia alla `_pk` solo
ciò che è suo (guard sul parametro, traduzione SR → PK con `ef.attivo`, i due
raise, tutti invariati). ⚠️ Il filtro `ef.attivo` stava su *entrambe* le vecchie
sottoquery e un mapping verso un emittente spento ricadeva sul default: sul
modello quel caso **non esiste** (`emittenti_fiscali_billing_account` non ha
`attivo`, quindi `prevent_deactivate_if_children` blocca la disattivazione di un
emittente con una riga di mapping, e `child_requires_active_parent` rifiuta la
riga verso uno spento). Il filtro resta come difesa sull'unico punto in cui si
legge la PK.

⚠️ I tre file sono **applicati** (`databasechangelog`, 2026-09-13 00:22–00:23):
da qui in poi non si rinominano e non si rinumerano.

---

## 5. I presidi — pgTAP

| File | Runner | Cosa |
| --- | --- | --- |
| `rls/test-rls-billing-account-returning-secondo-emittente.sql` — **nuovo** | app | **il caso di prodotto**: due aziende costruite (A, B), contesto di B, la catena sotto il BA come l'helper, poi `INSERT … RETURNING id INTO` a mano — la stessa istruzione di `create_billing_account`. 10 test: precondizione «B non è il default», il RETURNING vive, l'id è la riga e si vede, il legame è verso B, la riserva in sessione è B, come operatore di A il BA **non** si vede, senza sessione la riserva è il default, senza sessione il BA legato risponde B, RLS accesa e non forzata, la policy di lettura è `FOR ALL` |
| `script/test-ba-emittente-risoluzione-v1.sql` — riscritto | app | il test 4 («BA senza mapping → default», pinnato **con** il contesto aperto, verde per coincidenza) si spezza in **4** (in sessione → l'operatore) e **5** (senza sessione → il default); mondo costruito (era nel registro della CI: cercava un mapping esistente). Plan 13 → 14 |
| `anagrafiche/test-fn-get-emittente-fiscale-pk.sql` — riscritto | app | il test 6 si spezza in **6/7**; **9** «la delega è esatta» (PK → SR coincide con il lettore) e **10** anti-ritorno della copia (il corpo nomina il lettore e non `is_default`); i due `throws_ok(…, NULL, NULL)` diventano `throws_like` sulla frase del guard; mondo costruito (era nel registro della CI). Plan 8 → 10 |
| `dbops/test-storico-scope-policy-v1.sql` — test 28 | app | «BA non mappato → default» era pinnato con il contesto aperto: ora **28** (in sessione → l'EF dell'operatore) e **28-bis** (senza sessione → il default, skip dichiarato se manca); due aziende costruite, contesto del preambolo salvato e rimesso. Plan 32 → 33 |

⚠️ Il **non-usare** `dbops.fn_pgtap_crea_cliente_ba` per il caso di prodotto è
voluto: dalla rev `20260912-38` l'helper il `RETURNING` **non lo fa** apposta,
quindi passerebbe anche col difetto vivo. La catena sotto il BA (soggetto, ruolo
CL, istanza, dati precontrattuali come satellite) è quella dell'helper, riga per
riga; il satellite precontrattuale c'è perché la fixture sia completa
**qualunque** sia l'esito del test 1 — senza, prima del changeSet il file
sarebbe morto sul vincolo differito invece di essere rosso sull'asserzione.

⚠️ **Due aziende, e il contesto sulla seconda**, in tutti e quattro i file: sullo
scratch della CI il **primo** emittente creato diventa il default per bootstrap
(`trgfn_emittenti_fiscali_default_bootstrap`), quindi con una sola le due facce
della riserva risponderebbero lo stesso emittente. Le due aziende si creano in
**due istruzioni** (l'ordine è portante, e in una `UNION ALL` è del planner).

**Esiti** (psql `-f`, file in `BEGIN … ROLLBACK`, nessun runner):

| Dove | Come | Esito |
| --- | --- | --- |
| dbdev, `zeroerp_app`, changeSet applicati | i quattro file così come sono | **10/10 · 14/14 · 10/10 · 33/33** |
| scratch `zeroerp_ci`, `zeroerp_app`, **senza** changeSet | il file nuovo | **5 rossi su 10**: il test 1 muore con `42501`, e 2/3/4/7 lo seguono — è il difetto, fabbricato |
| scratch `zeroerp_ci`, owner `zeroerp`, SQL **estratto** dei tre changeSet (preCondition comprese, tutte = 1) + `FORCE ROW LEVEL SECURITY` + il file | i quattro file | tutti verdi tranne l'8 del nuovo, che misura *«non forzata»* ed è rosso per il FORCE della prova |

✅ I due file già nel registro della CI (`test-ba-emittente-risoluzione-v1`,
`test-fn-get-emittente-fiscale-pk`) sono **rientrati**: lo ha detto la CI il
14-09 e le righe sono uscite da `baseline-rossi-ci.tsv` con il commit
`8454f7cbd` (`scripts/pgtap-baseline-ci-rientrati.sh`, che da quel giorno
legge i RIENTRATI dal log della corsa con `gh`). La corsa successiva su
`Tito-dev` (PR #1583, tocca `db/` ⇒ suite completa) è verde. Fino a quel
momento questo paragrafo diceva «dovrebbero rientrare: le righe si tolgono
quando lo dice la CI, non lo scratch» — ed è andata così.

---

## 6. Documentazione e lettori fuori dal DB

### 6.1 Aggiornati

Manuali: `script/manual/fn_get_ba_emittente_sr_id.md` (tre livelli, il perché
del livello 2, il prezzo, la marcatura, i test), `fn_check_ba_visible_for_emittenti.md`,
`anagrafiche/manual/fn_get_emittente_fiscale_pk.md` (involucro PK, delega),
`emittenti_fiscali_billing_account.md` (regole di coerenza), `script/manual/fn_get_search_detail.md`
(la «logica a 3 livelli»), guida `soggetti-e-ruoli-anagrafici.md` (tabella delle
cardinalità). Doc auto-gen rigenerate da Tid.

### 6.2 ✅ Tre copie Python della regola VECCHIA — chiuso dal team BE il 2026-09-13

Il backend tiene **inline** la regola «mapping specifico, altrimenti default se
il BA non ha mapping» in tre query, *«per lasciare al planner il semi-join»*:

- `apps/anagrafiche/db/clienti_repository.py` — `list_clienti` (il commento
  dichiara «semantica identica alla fn canonica», che da oggi non è più vera);
- `apps/anagrafiche/db/soggetti_repository.py` — due volte (righe ~60 e ~185).

Divergono dal DB **solo** su un BA senza legame in sessione — un istante, o un
seed — quindi oggi nessuna lista mente. Ma è la forma in cui due regole si
sfilano in silenzio, e la casa ha già il precedente giusto:
`billing_account_repository.py` e `istanze_utility_repository.py` delegano a
`script.fn_check_ba_visible_for_emittenti` (fix 2026-07-13: *«il vecchio JOIN
inline `… OR is_default = true` era più lasco»*). Da allineare nello stesso
modo; fuori dal perimetro DB di questo brief.

✅ **Fatto il 2026-09-13 (BE).** Le tre copie erano lo stesso frammento
(`_RUOLO_CL_SCOPE_SQL` di `soggetti_repository`, ricopiato con i commenti
dentro la `jsonb_agg` di `list_soggetti`, più `list_clienti`): ora è **un
frammento in tre punti** e `list_clienti` delega direttamente, entrambi con
`fn_check_ba_visible_for_emittenti(<ba>, %s::bigint[])`; i parametri passano
da tre a due per query. Provato sul DB vero, in transazione ritirata: **5
perimetri × 4 query, risultati identici** prima e dopo (sui 42 BA tutti
collegati le due regole coincidono — è la ragione per cui nessuna lista
mentiva). Presidio sulla forma, a registro zero:
`apps/anagrafiche/tests/test_scope_ba_delega_alla_fn.py` — vieta di confrontare
l'emittente **del mapping** con la whitelist `ANY(…)` in una query Python (la
lettura del gestore globale in `parameter_repository` e i registri di
numerazione non sono quella forma, e il test lo dice) e pretende che i quattro
repository nominino ancora la fn. Provato per mutazione nei due versi.
⚠️ Riletto la sera stessa: il frammento condiviso aveva perso il `JOIN
billing_account` — la fn riceve l'id, ma quel JOIN è un cancello RLS che si
somma a quello di `clienti`, e la prova prima/dopo (super admin, perimetro
largo) non poteva vederlo. Rimesso, con il perché in commento. Misurato: la
forma con la fn non è più lenta del semi-join inline (3,6 vs 4,6 ms su
`list_soggetti`, 175 soggetti).

### 6.3 Cose che ora sono storia, e non si toccano

- `dbops.fn_pgtap_crea_cliente_ba` (rev `20260912-38`) non fa `RETURNING` e lo
  spiega col difetto: il commento è ora **storico**, il comportamento resta
  giusto (rilegge dal codice) e non c'è motivo di riaprire l'helper;
- `anagrafiche/test-billing-account-auto-link-ef.sql` fa `RETURNING id INTO`
  nel contesto dell'operatore del preambolo: passava perché quell'operatore è
  del default, ora passa per qualunque operatore. Resta nel registro della CI
  per la sua fixture (cerca un BA esistente) — è D7, non D13.

---

## 7. Cosa resta

1. ✅ **Apply** — fatto da Tid il 13-09 (00:22–00:23), doc auto-gen rigenerate.
2. ✅ **pgTAP col runner e baseline di sviluppo** — fatti da Tid il 13-09:
   **nessuna regressione**. ✅ **CI** — il 14-09 i due file già nel registro
   (`test-ba-emittente-risoluzione-v1`, `test-fn-get-emittente-fiscale-pk`)
   sono rientrati e le righe sono uscite da `baseline-rossi-ci.tsv` (commit
   `8454f7cbd`); corsa su `Tito-dev` per la PR #1583 verde. Nessun file di
   questo brief in nessuna delle due baseline (§5).
3. ✅ **Team BE** — fatto il 13-09: le tre copie inline delegano a
   `fn_check_ba_visible_for_emittenti`, con presidio sulla forma (§6.2,
   `apps/anagrafiche/tests/test_scope_ba_delega_alla_fn.py`).
4. ✅ **Decisioni di Tid, prese il 14-09** (§3.4): da interfaccia il DB
   rifiuta già un BA senza emittente (`a10_guard_admin_globale` +
   `z90_link_ef`); i percorsi senza sessione sono dati, non un caso d'uso.
   **Niente presidio** «BA senza legame» e **l'opzione 3 esce dalla coda**.
5. ✅ La valutazione (`migliorie-generali-da-test-valutazione.md` §D13 e
   checklist) dice CHIUSO il 13-09; la memoria è riallineata il 14-09.
6. ✅ **Chiusura formale** — fatta il 14-09 su richiesta di Tid: brief
   spostato in `work-done/`, riscritti i **tre link per path** che lo
   puntavano (`docs/it/mappa-concentrica.md`,
   `docs/it/dev/mappa-concentrica-changelog.md`,
   `docs/it/dbzero/script/manual/fn_get_ba_emittente_sr_id.md`) e i due link
   relativi di questo file verso `work-in-progress/`. Gli altri lettori (la
   valutazione, il brief D7-D6-D4, i tre YAML, i tre pgTAP, i due repository
   e il test BE) lo citano **per nome** e non si toccano.

*Scritto il 2026-09-13. Nessun test eseguito col runner ufficiale; ogni prova è
un `psql -f` in transazione ritirata, un file alla volta, su dbdev e sullo
scratch della CI. Verificato il 2026-09-14 contro `databasechangelog`, i rami
`origin/Tito-dev` e `origin/main`, le due baseline, `pg_proc` e le corse della
CI: ogni ✅ qui sopra è letto dalla sorgente, non ricopiato.*
