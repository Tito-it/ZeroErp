# Brief DB — Le funzioni che ripianificano a ogni chiamata

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Nessuno: chiuso e archiviato il 2026-10-18.** D-1…D-6 e D-3b (D-3b-1, D-3b-2, D-3b-3) applicate,
pgTAP verdi, misurate. Il debito residuo vive in
[brief-db-perimetro-una-volta-famiglie-residue](brief-db-perimetro-una-volta-famiglie-residue.md)
(D36). Fuori dal brief, a Tid: ricostruire lo scratch `zeroerp_ruoli` (le fixture committate
dall'incidente del 2026-10-18, §5quinquies) prima della prossima baseline. Lavoro del 2026-10-18
**da committare** (changeSet `20261018-15`…`-29`, `-31`…`-33`, `-48`…`-52`, pgTAP, pagine `manual/`,
linee-guida-sql, registro, PROJECT_CONTEXT, questo brief e quello del residuo).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid.
> **Origine:** il debito residuo di
> [brief-db-segment-base-commesse-attivita](brief-db-segment-base-commesse-attivita.md)
> (§8), archiviato il 2026-10-10. Voce nel registro: **D26-2** di
> [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).
> **Stato: ✅ chiuso e archiviato il 2026-10-18** (§7). Storia:
> **(2026-10-10):** 🔎 censimento e misura del §2.1 fatti (§4). **D-4**: primo
> passo `20261010-44` ✅ applicato da Tid, pgTAP `vendite` rilanciati, misurato (§5.2).
> D-6 e D-5 passate al brief figlio `brief-db-lineage-seminata-per-chiave`, ✅ chiuso il
> 2026-10-11 (`work-done/`): tutte e due risolte. **2026-10-11**: D-3
> misurata (§5bis), **D-3a** `20261011-42` ✅ applicato. **D-2** ✅ chiusa (`20261012-03` applicato, §5ter). Aperta solo **D-3b**, profilata il 2026-10-18 (§5quater); **D-3b-1**
> ✅ applicata (`20261018-15`, 2026-10-18), pgTAP verde. Aperte D-3b-2 e D-3b-3. **Cosa resta: §6.**
> **Ricadute BE/FE:** nessuna prevista.

## 1. Cosa ha insegnato il cantiere da cui nasce

Una funzione plpgsql che chiama con un **parametro** una funzione SQL che si
incorpora (`fn_ddt_push_diagnosi` → `fn_partite_merce` → `fn_af_merce_per_riga`)
esegue una query enorme. In modo `auto` la plancache confronta i costi
**stimati**: il piano generico, col parametro sconosciuto, le sembra più caro, e
lei ripianifica a ogni chiamata — ~13-15 ms di sola pianificazione, con piani
personalizzati spesso anche più lenti da eseguire.

La cura applicata lì: `ALTER FUNCTION … SET plan_cache_mode = force_generic_plan`
sulla funzione plpgsql chiamante (`20261010-83` capability del DDT, `-84` lister
dei DDT da spingere), presidiata dal pgTAP
`script/test-fn-available-actions-ddt-piano-generico-v1`. Fatti datati
(2026-10-10, dbdev come app, 56 DDT): capability 1,42 → ~0,6 s; lister per DDT
1,30 → ~0,48 s.

## 2. I due punti aperti

### 2.1 Le altre funzioni con la stessa forma

Il censimento non è stato fatto: le due funzioni curate sono le sole misurate.
Candidate per costruzione: le funzioni plpgsql che chiamano con un parametro una
funzione `LANGUAGE sql` `BEGIN ATOMIC` grande (diagnosi, partite merce,
situazione merce dell'ordine, le capability degli altri documenti, le altre
`fn_list_*_da_pushare`).
Il metodo, già provato: per ciascuna, un ciclo plpgsql di N chiamate come app in
`auto` e con `force_generic_plan` di sessione — se il generico costa molto meno,
la clausola sulla funzione è la cura; se costa uguale, non serve.
⛔ La clausola non si mette «per igiene»: si mette dove la misura mostra il
difetto, e il presidio la pretende solo lì.

### 2.2 Il lister dei DDT senza filtri

`vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, NULL)` costa ~1,1 s (dbdev
come app, 2026-10-10), uguale in `auto` e in generico: è la diagnosi di tutti i
DDT in una chiamata, non un problema di plancache. Va profilata come query
(`EXPLAIN ANALYZE` del ramo «tutti») prima di dire se e dove si può migliorare.

## 3. Decisioni attese

* **D-1** — fare il censimento del §2.1, e con che perimetro (tutte le capability
  e i lister, o solo le funzioni che il backend chiama in un ciclo).
* **D-2** — profilare il §2.2 ora, o quando il volume dei DDT lo renderà
  visibile.

## 4. Censimento e misura (2026-10-10, dbdev come app)

### 4.1 Il censimento

Funzioni plpgsql che nominano una funzione `LANGUAGE sql` o una **vista** (le
viste sono macro: stessa forma) il cui corpo, sommato a quello delle SQL e viste
annidate, supera ~4.000 caratteri: **43**. Censimento per testo, quindi largo (una
menzione in un commento conta): il criterio vero è la misura.

### 4.2 La misura

Per ciascuna candidata **di sola lettura**: un ciclo plpgsql di N chiamate (max
50) su argomenti veri, seconda corsa, in `auto` e con `force_generic_plan` di
sessione. Le funzioni che scrivono e i trigger non si misurano così su dbdev.

| Funzione | ms/chiamata `auto` | ms/chiamata generico | Rapporto |
| --- | --- | --- | --- |
| `vendite.fn_resi_da_accreditare` (per DDT) | 22,5 | 5,6 | **4,0** |
| `vendite.fn_resi_riga_tetti_accredito` (per riga di reso) | 6,0 | 1,5 | **4,1** |
| `vendite.fn_get_lotto_segnalazioni_summary` | 3,3 | 2,6 | 1,3 |
| `script.fn_check_accredito_annullabile` | 0,63 | 0,51 | 1,2 |
| `pratiche.fn_stato_sorgente` | 0,49 | 0,42 | 1,2 |
| altre 14 (capability preventivo, prezzi autorizzati, saldi, permessi, operatore, totp, sorgenti, indirizzi, commessa, riconsegna ordine…) | 0,1-1,3 | uguale | 1,0 |
| `vendite.fn_documento_lineage` (preventivo / ordine / DDT) | **~600-780** | uguale | 1,0 |
| `vendite.vw_offerte_commerciali_lista` filtrata per un id | **~390** | uguale | 1,0 |

### 4.3 Cosa dice

* **Il difetto di plancache c'è solo sui resi**: le due funzioni SQL della coda
  accrediti, 4× fra `auto` e generico. I chiamanti plpgsql sono
  `vendite.fn_accredita_riga_reso` (chiama `fn_resi_da_accreditare`) e il trigger
  `vendite.trgfn_resi_accrediti_guard` (chiama `fn_resi_riga_tetti_accredito`);
  la vista `vw_resi_da_accreditare` è letta da `fn_annulla_accredito_riga_reso`,
  `fn_chiudi_riconsegna_reso`, `fn_check_accredito_annullabile`. Tutti scrivono
  (o sono trigger): il guadagno reale si misura su un ciclo di accrediti
  costruito, in transazione annullata.
* **Due funzioni lente in sé, non per la plancache** — e sono le più importanti
  trovate: `fn_documento_lineage` (il pannello «Passaggi», ~0,6-0,8 s a
  chiamata) e `vw_offerte_commerciali_lista` letta per un id (~0,4 s: il filtro
  per id non scende dentro la vista). Vanno profilate come query: è un altro
  difetto, e un altro cantiere.
* Le altre 16 misurate non hanno il difetto: la plancache sceglie bene.

### 4.4 Decisioni attese sulla lista

* **D-3** — resi: misurare il ciclo di accredito costruito e, se il 4× regge,
  la clausola `plan_cache_mode` sui chiamanti plpgsql (come `20261010-83/-84`).
* **D-4** — aprire un cantiere sul **pannello «Passaggi»** (`fn_documento_lineage`).
* **D-5** — aprire un cantiere sulla **lista offerte letta per id**
  (`vw_offerte_commerciali_lista`; la legge anche il trigger della revisione).

## 5. D-4 — il pannello «Passaggi» (`vendite.fn_documento_lineage`)

Avviata da Tid il 2026-10-10.

### 5.1 La causa

`vendite.vw_documento_lineage_archi` costruisce **l'intero grafo** decorato: 13
rami in `UNION ALL` per gli archi, e una CTE `MATERIALIZED` con i nodi di tutti i
documenti. La funzione la nominava nel passo iniziale e nel termine ricorsivo,
con un join a `OR` fra le due direzioni: la vista si rivalutava a ogni livello,
e il recinto `MATERIALIZED` impedisce a qualunque filtro di scendere nei rami.

| Fatto datato, dbdev come app | Tempo |
| --- | --- |
| archi grezzi dell'intero grafo (231) | ~125-140 ms |
| nodi di tutti i documenti (474) | ~41 ms |
| vista intera | ~190 ms |
| vista filtrata su un nodo | ~351 ms (peggio dell'intera) |
| funzione, anche su un nodo senza archi | ~0,6-0,8 s |

### 5.2 Primo passo — `20_code/vendite/20261010-44-update-fn-documento-lineage-grafo-una-volta`

La vista si legge una volta in una CTE `MATERIALIZED` `archi` dentro la
funzione, e la ricorsione attraversa la copia. Nient'altro cambia: firma,
`RETURNS TABLE` con i suoi `%TYPE`, controlli dei parametri, guardia dei cicli,
ordinamento. Numero preso nel buco (`-44`): la coda del giorno la usa un'altra
sessione.

Prove (2026-10-10):

* **equivalenza su dbdev come app**, copia `pg_temp` della funzione: tutti i
  **339** casi del grafo (ogni nodo con archi, nelle due direzioni), righe
  identiche — 708 per parte, `EXCEPT ALL` a zero nei due versi; tempo
  **283 s → 60 s** (~836 → ~177 ms a chiamata). Il corpo del changeSet è
  identico (normalizzato) a quello provato;
* il corpo di partenza (`20260829-02`) verificato uguale al corpo vivo;
* **scratch**, SQL estratto: i 5 pgTAP che toccano la lineage identici prima e
  dopo, tutti verdi (`test-documento-lineage-v1` 47/47 sui grafi che costruisce);
  avanti e indietro: definizione identica (md5), `GRANT` all'app conservato.

**Dopo l'apply** (2026-10-10, dbdev come app, sulla funzione vera): nodo senza
archi **~0,8 → ~0,19 s**; 40 nodi con archi 6,7 s, cioè ~0,17 s a chiamata.

### 5.3 Secondo passo, da decidere

~0,18 s è il costo di costruire **l'intero** grafo una volta. Per scendere ai
millisecondi la funzione deve costruire solo gli archi del nodo chiesto: archi
**seminati per chiave** (la forma della partita merce), un cantiere vero —
la vista degli archi è letta anche dalle liste (`vw_documento_lineage`, la
colonna della lineage nelle liste). Decisione attesa: **D-6**.

➡️ **D-6 è diventata un brief suo** (2026-10-10, su richiesta di Tid):
[brief-db-lineage-seminata-per-chiave](brief-db-lineage-seminata-per-chiave.md).
Il censimento ha mostrato che lo stesso costo lo paga **ogni pagina di sette
liste** (~0,42 s), e che la **D-5** di questo brief (lista offerte letta per id)
è lo stesso difetto: anche D-5 passa di là.

## 5bis. D-3 — la misura del ciclo di accredito (2026-10-11, dbdev come app)

Metodo: N chiamate di `vendite.fn_accredita_riga_reso` sulla sola riga in coda
(15922, una riga di ponte per chiamata), ciascuna in sottotransazione annullata;
la plancache della sessione sopravvive al rollback. Script nello scratchpad della
sessione (`misura-d3-*.sql`), tutto in `BEGIN … ROLLBACK`.

| Cosa, ms/chiamata | `auto` | generico | Nota |
| --- | --- | --- | --- |
| guard da solo, `fn_resi_riga_tetti_accredito` | 7,1 | 1,5 | 4,8× |
| la coda letta **come la legge il verbo** (stessa forma plpgsql) | 27 | 12 | 2,2× |
| copia `pg_temp` del guard: la clausola **sulla funzione SQL DEFINER**, sessione in `auto` | 30 | 15,6 | in PG18 la clausola su una SQL non incorporata funziona (la copia gira come app, sotto RLS: conta il rapporto, non il valore) |
| **verbo intero**, generico di sessione (= la clausola sul verbo) | 119-126 | 115-120 | ~5% |

Copia `pg_temp` del verbo (INVOKER, risultato identico alla vera), col generico
acceso **solo** attorno a una istruzione, due corse in ordine mescolato:

| Variante | ms/chiamata |
| --- | --- |
| tutto `auto` | 123-126 |
| generico solo sulla lettura della coda | 117-118,5 |
| generico solo sull'`INSERT` del ponte (guard e trigger della tabella) | **132-137** — peggio |
| generico su coda + `INSERT` | 117-120 |
| tutto generico | 118-119 |

Cosa dice:

* il difetto c'è **su entrambe le istruzioni** prese da sole: nel guard e
  nella lettura della coda;
* il verbo costa ~115 ms **altrove**, non nella pianificazione: le due cure
  insieme ne tolgono ~5-7;
* il generico acceso su tutta la finestra dell'`INSERT` del ponte **peggiora**
  il verbo: qualche istruzione di quel percorso (guard, trigger della tabella)
  sta meglio coi piani personalizzati. ⇒ La clausola non va sul **trigger**.
  La clausola su `fn_resi_riga_tetti_accredito` invece si applica solo alle
  query di quella funzione (il GUC torna com'era all'uscita), e lì il difetto
  è misurato.

**D-3a** ✅ **decisa da Tid (2026-10-11)**: la clausola va **solo** su
`fn_resi_riga_tetti_accredito`, nel changeSet `20261011-42`; sul verbo no.

**D-3a scritta (2026-10-11)**: `20_code/vendite/20261011-42-alter-fn-resi-riga-tetti-accredito-piano-generico`
(`ALTER FUNCTION … SET plan_cache_mode`; rollback `RESET plan_cache_mode`).
Presidio unico `db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql` (plan 5:
le tre funzioni, più il contratto della capability e il fail-closed dei tetti);
`test-fn-available-actions-ddt-piano-generico-v1` è **ritirato** (i commenti di
`-83/-84`, già applicati, lo nominano ancora: l'intestazione del nuovo dice che lo
sostituisce). Nota nelle pagine `manual/` delle tre funzioni.
Prova sullo scratch `zeroerp_ci`, da owner, SQL estratto: precondition 1; presidio
**senza** il `-42` 4/5 (rosso solo il 4, cioè vede il difetto), **con** il `-42` 5/5;
andata e ritorno: definizione identica (md5), `GRANT` conservati. ✅ **Applicato** da Tid
(2026-10-11, `EXECUTED` nel `databasechangelog` di dbdev). Dopo l'apply, su dbdev come app:
presidio 5/5; la funzione vera in sessione `auto` 1,9 ms a chiamata (prima 7,1). Sul verbo toglierebbe i ~6 ms
della coda, ma imporrebbe il generico a **tutto** il verbo, compresa la finestra
dell'`INSERT` dove la misura lo mostra peggiore: nasconderebbe quel peggioramento
invece di mostrarlo.
**D-3b** (decisione attesa): dove vanno i ~115 ms del verbo, da profilare come
query (nessun `auto_explain` come app: si fa per istruzione, a mano).

## 5ter. D-2 — il lister dei DDT senza filtri (2026-10-11) — ✅ chiusa

**Profilo** (dbdev come app): `fn_list_ddt_da_pushare(NULL, NULL, NULL, NULL)`
~1,17 s, ed è tutta la diagnosi (`fn_ddt_push_diagnosi(NULL)` ~1,18 s). Ma la
stessa diagnosi fatta DDT per DDT e sommata costa ~0,38 s: il ramo «tutti» non
faceva più lavoro, era pianificato male.

**Causa.** La CTE `src` della diagnosi (la riga d'ordine sorgente di ogni riga di
DDT: il primo fulfillment, `LATERAL … LIMIT 1`) non era `MATERIALIZED`. `cand` la
incorporava come sottoquery in `LEFT JOIN src s ON s.dr_id = r.dr_id` e, non
potendole passare la chiave, la ricalcolava intera per ogni riga esterna: il
`LATERAL` girava righe² volte, con tre policy a giro (58 righe: 3364 giri, ~1,05 s
su 1,18). Cresce col **quadrato** delle righe di DDT del sistema.

**Cura**: `20_code/vendite/20261012-03-update-fn-ddt-push-diagnosi-src-materialized`.
`src AS MATERIALIZED`, corpo preso dal vivo `20261009-83` coi suoi `%TYPE`,
COMMENT conservato con la revisione davanti.

**Prove** (copia `pg_temp`, dbdev come app): diagnosi e lister identici ai vivi nel
ramo «tutti» e DDT per DDT; stessa firma. Tempi: diagnosi di tutti 1178 → 169 ms,
lister senza filtri 1135 → 154 ms, per DDT invariato (~410 ms per 62 chiamate).
Sullo scratch, SQL estratto: i 6 pgTAP che toccano diagnosi, lister e capability
identici prima e dopo.

**Presidio** (decisione di Tid, 2026-10-11): `script/test-fn-available-actions-ddt-reason-catch-all-v1`
test **18** (plan 17 → 18), pin di forma: nella diagnosi la CTE `src` è
`MATERIALIZED`, letto da `pg_get_function_sqlbody` (il corpo è `BEGIN ATOMIC`).
Senza la parola i risultati restano giusti e solo il tempo se ne accorge. Provato:
rosso senza il `-03`, verde con.

✅ **Applicato** da Tid (2026-10-11): `20261012-03`, pgTAP verdi.

## 5quater. D-3b — dove vanno i ~115 ms del verbo (2026-10-18, dbdev come app)

**Metodo.** Da superuser: `SET track_functions = 'all'`, `LOAD 'auto_explain'` con
`log_nested_statements` e `log_triggers` e `log_level = notice`, poi `SET ROLE zeroerp_app`
col contesto di `tid` (identità 19, OPERATORE, emittente 32). Tutto in `BEGIN … ROLLBACK`,
riga di reso 15922 (ancora in coda, 3 pezzi). Script nello scratchpad della sessione
(`profilo-d3b.sql`). Contatori da `pg_stat_xact_user_functions`; piani da `auto_explain`.

**Tempi puliti** (senza `auto_explain`): 257 ms a freddo, poi **146 e 130 ms**.
Con `auto_explain` e `log_analyze`, una corsa calda: 442 ms e **7.376 istruzioni** annidate.

**Dove vanno.** Tre istruzioni del verbo pesano 317 ms su 442 (72%):

| Istruzione del verbo (corpo vivo `20261003-05`) | ms | Piano |
| --- | --- | --- |
| progressivo `#RET:` — `WHERE ca.segment_key LIKE v_seg_ddt \|\| '#RET:%'` | 127,6 | `Seq Scan` su `commesse_attivita`: la policy gira su **tutte** le 330 righe, il `LIKE` dopo |
| gruppi da accreditare (`FOR v_grp`) — `segment_key = … OR segment_key LIKE …` | 94,5 | entra da `attivita_fatturabili` in `Seq Scan` (63 righe, policy su ognuna), poi `commesse_attivita` per id con la policy di nuovo |
| righe del gruppo (`FOR v_cmp`) — `split_part(ca.segment_key, '#CMP:', 1) = v_grp.kit_key` | 94,8 | stesso piano del precedente |

**Causa.** È la regola di `linee-guida-sql.md` §8.5-bis («Sotto una policy RLS entra
nell'indice solo una clausola leakproof»): sotto una policy RLS il planner
promuove a condizione d'indice solo le clausole **leakproof**. `LIKE` e `split_part` non lo
sono: restano filtri **sopra** la policy, e la policy si valuta su ogni riga della tabella
prima che il filtro selettivo possa scartarla. L'indice `ix_commesse_attivita_segment_key`
(`varchar_pattern_ops`) c'è, ma sotto RLS non entra. Il verbo è del 2026-10-03; la cura del
2026-10-10 (`segment_base`, colonna generata `split_part(segment_key, '#', 1)` con il suo
btree, `20261010-80…-82`) non lo ha raggiunto. Il costo è **per costruzione** lineare nel
numero di righe di commessa di tutto il sistema, a ogni accredito.

**Il prezzo di una riga sotto policy.** Ogni valutazione di
`fn_scope_ef_whitelist_via_commessa` costa ~0,38 ms (127,6 ms / 330 righe): risale a
`fn_scope_ef_whitelist_via_sr` → `fn_check_user_emittente_scope` → `fn_is_super_admin_account`
(una query sui binding con dentro `fn_veste_utilizzabile`) → `fn_veste_utilizzabile`
(due `fn_data_operativa`, ciascuna con `fn_fuso_operativo` che rilegge `SYSTEM_FUSO_ORARIO`).
Contatori su 3 corse del verbo: `fn_veste_utilizzabile` 2.748 chiamate, `fn_fuso_operativo`
5.499, `fn_check_user_emittente_scope` 3.936. Tutto ricalcolato da capo per riga, con la
stessa risposta: in una richiesta il perimetro dell'utente non cambia.

**Il resto** (corsa con `auto_explain`): lettura della coda `fn_resi_da_accreditare` 64 ms
(partite merce, la forma già curata in `20261010-80…-82`); `INSERT` del ponte 17 ms col guard
dei tetti 13 ms; `fn_upsert_commessa_attivita` 24 ms; il `tx_id` della transazione via
`dblink` ~18 ms (`dbops.fn_get_or_create_session_tx_id`, una volta per transazione).

**Censimento** (dbdev, `pg_proc`, 2026-10-18): fra le funzioni vive, filtri `LIKE`/`split_part`
su `segment_key` in `WHERE` li ha **solo** `fn_accredita_riga_reso` (8 punti).
`fn_aggiungi_onere_commessa` usa `split_part` solo nel `SELECT`, dopo
`commessa_id = p_commessa_id`: entra dall'uguaglianza, non ha il difetto.

**Decisioni attese.**

* **D-3b-1** — riscrivere le tre istruzioni del verbo con l'**uguaglianza su
  `segment_base`** come condizione d'ingresso e il `LIKE` come residuo:
  `ca.segment_base = v_seg_ddt` (le chiavi `…#RET:n` e `…#CMP:x` hanno per base proprio
  `v_seg_ddt`), e `ca.segment_base IN (v_seg_ddt, v_seg_ord)` per i gruppi; per le righe del
  gruppo, `segment_base` della chiave di kit. Corpo dal vivo `20261003-05` coi suoi `%TYPE`.
  Prova: copia `pg_temp` come app, risultato identico al vivo, piano con `Index Cond` su
  `segment_base`; presidio di forma come il test 18 della D-2 (nessun `LIKE` su
  `segment_key` nel `WHERE` del verbo).
* **D-3b-2** — il prezzo per riga della catena di perimetro (~0,4 ms) riguarda **ogni**
  tabella con policy, non questo verbo: un cantiere a parte (un brief), da aprire o no.
* **D-3b-3** — il `tx_id` via `dblink` a ogni transazione (~18 ms): guardarlo nel brief
  che possiede `dbops.fn_get_or_create_session_tx_id`, non qui.

### D-3b-1 — ✅ applicata (2026-10-18, via di Tid)

**ChangeSet** `20_code/vendite/20261018-15-update-fn-accredita-riga-reso-segment-base`.
Le tre letture entrano da `ca.segment_base = v_seg_ddt`, `ca.segment_base IN (v_seg_ddt,
v_seg_ord)` e `ca.segment_base = v_grp.kit_key`; il filtro di prima resta come residuo.
Righe identiche **per costruzione**: i segmenti della partita non contengono `#`, quindi
ogni chiave accettata dal filtro di prima ha per base il segmento stesso (argomento per
esteso nell'intestazione del changeSet). Numero `-15`: il primo libero dopo `-14`
(`90_end`, di un'altra sessione).

⚠️ **Corpo di partenza**: il vivo è quello di `20261009-50` (il giorno operativo,
`v_data := script.fn_data_operativa()`), **non** quello di `20261003-05`, che è l'ultimo
YAML dedicato al verbo ma è più vecchio. `prosrc` di dbdev confrontato col blocco del
`-50`: 534 righe identiche. Rollback: quel corpo per intero, e il COMMENT ripulito della
revisione.

**Presidio**: `db/pgtap/vendite/test-fn-accredita-riga-reso-v1.sql`, plan 14 → 16.

* test **15**: la **corsia ORD** costruita (fattura sul segmento dell'ordine, reso sulla
  spedizione, rettifica col prezzo della riga d'ordine). Nessun pgTAP del verbo la
  attraversava, ed è il ramo `v_seg_ord` che il changeSet tocca. Verde anche senza il
  changeSet: è copertura, non rivelatore;
* test **16**: pin di forma, `FROM vendite.commesse_attivita ca` e `ca.segment_base =|IN`
  contati nel `prosrc` senza commenti, `3|3`. Sul corpo di prima `3|0`.

**Prove** (2026-10-18):

* **dbdev come app**, copia `pg_temp`, riga 15922 (corsia ORD): righe scritte identiche
  (segmento, quantità, prezzo, meta, ponte); verbo **113-121 → 61-70 ms** a chiamata, quattro
  corse alternate. Piani delle tre letture col **generico forzato**: tutte in `Index Cond`
  su `ix_commesse_attivita_segment_base` — 127,6 → 0,1 ms, 94,5 → 6,7 ms, 94,8 → 1,7 ms;
* **scratch `zeroerp_ruoli`**, SQL estratto, da owner: il file del verbo **senza** il
  changeSet 15/16 (rosso solo il 16), **con** 16/16; gli altri 11 pgTAP che chiamano il
  verbo hanno esiti identici senza e con. I rossi presenti in entrambe le corse sono
  già noti: `test-rettifica-non-annullabile-e-prezzo-immutabile-v1` è `ERRORE_FIXTURE` in
  baseline; il 14 di `test-fn-partite-merce-chiusura-v1` e il 12 di
  `test-fn-resi-da-accreditare-chiusura-v1` sono test di perimetro, rossi da owner per
  costruzione;
* **andata e ritorno**: definizione, COMMENT, GRANT e attributi identici (md5) dopo il
  rollback; preCondition verificate a parte (colonna `segment_base` presente, funzione
  presente).

Nota nella pagina `manual/fn_accredita_riga_reso.md` (rev 2026-10-18).

✅ **Applicato** da Tid (2026-10-18 11:33, `EXECUTED` nel `databasechangelog` di dbdev);
pgTAP `vendite/test-fn-accredita-riga-reso-v1` verde (Tid). Dopo l'apply, su dbdev come
app, la funzione vera sulla riga 15922 in transazioni annullate: 131 ms a freddo, poi
**60-64 ms** (prima 113-146). Pin di forma sul corpo vivo: 3 ingressi da `segment_base`.
Il resto dei ~65 ms è la lettura della coda (partite merce), l'upsert e il `tx_id`: D-3b-2 e
D-3b-3, non questo changeSet.

## 5quinquies. D-3b-2 — il perimetro dell'operatore si calcola per riga (2026-10-18)

Tid, 2026-10-18: D-3b-2 e D-3b-3 si chiudono **in questo brief**.

### Il difetto, sul modello

Una policy ef_whitelist chiede «l'operatore della sessione vede l'emittente di questa
riga?». Tutte le forme arrivano alla canonica `script.fn_check_user_emittente_scope(utente,
emittente)` (plpgsql): direttamente (`fn_scope_ef_whitelist`, 77 policy) o attraverso un
adattatore `fn_scope_ef_whitelist_via_<x>` che **risolve** l'emittente della riga (commessa →
ruolo emittente → emittente, ~45 adattatori, ~230 policy; 310 policy su 176 tabelle in
tutto, comprese le famiglie cliente/shop/fornitore/note che non passano di qui).

La canonica fa due cose di natura diversa:

| Parte | Dipende da | Cosa fa |
| --- | --- | --- |
| il **perimetro dell'utente** | sessione (`app.current_user_id`, `app.ruolo_applicativo`, `app.current_emittente_id`) | emittente attivo, super admin (binding + veste utilizzabile + giorno operativo + fuso), veste OPERATORE utilizzabile, whitelist |
| l'**appartenenza** | la riga | l'emittente della riga sta nel perimetro? |

La prima non dipende dalla riga, ma si ricalcola **a ogni riga**: una plpgsql è opaca, e
gli adattatori SQL non si incorporano (hanno una sottoquery nel corpo: `inline_function`
rifiuta `hasSubLinks`). È un costo per costruzione **righe lette × catena**, su ogni
tabella con policy. Il manuale di `fn_scope_ef_whitelist` dice «inlineable, valutata una
volta» (§2-bis.7 di `sviluppo-multi-face-da-completare`): era l'intento, non è il fatto.

Fatto datato (§5quater, 3 corse del verbo): della catena, l'80% del tempo proprio è la
parte dell'utente (`fn_veste_utilizzabile`, `fn_fuso_operativo`, `fn_is_super_admin_account`,
`fn_data_operativa`).

### La prova di concetto (2026-10-18, dbdev, sola lettura)

Script `prova-perimetro-una-volta.sql` (scratchpad della sessione). Da owner, cioè senza
RLS, `count(*)` di `vendite.commesse_attivita` (330 righe) filtrato in due modi: con la
funzione della policy chiamata per riga (`fn_scope_ef_whitelist_via_commessa`), e con il
perimetro dell'utente calcolato **una volta** (regole della canonica in forma di insieme)
e l'emittente della riga confrontato con `= ANY`.

| Utente | Emittente attivo | Per riga | Una volta | Righe (uguali) |
| --- | --- | --- | --- | --- |
| tid (super admin) | 32 | 33 ms | 6 ms | 132 |
| tid (super admin) | — | 53 ms | 2 ms | 330 |
| terenzi | — | 62 ms | 6 ms | 132 |
| pochi | 32 | 34 ms | 4 ms | 132 |

### La forma proposta

1. **Un BB, una regola in due forme** (regola del 2): `script.fn_perimetro_ef(p_auth_user_id)`
   restituisce gli emittenti visibili come `bigint[]`, **NULL = tutti** (super admin senza
   emittente attivo), `'{}'` = nessuno. Le sei regole della canonica, in forma di insieme.
   La canonica diventa `fn_perimetro_ef(u) IS NULL OR e = ANY (fn_perimetro_ef(u))`: i
   guard di scrittura che la chiamano non cambiano.
2. **Le policy** chiamano il perimetro in una **sottoquery scalare non correlata**, che
   PostgreSQL valuta una volta per istruzione (InitPlan):
   `(SELECT script.fn_perimetro_ef_sessione()) IS NULL OR <emittente della riga> = ANY ((SELECT script.fn_perimetro_ef_sessione()))`.
   Dove la tabella ha la colonna emittente, il confronto è sulla colonna: `int8eq` è
   leakproof, quindi la policy può anche **entrare nell'indice** (§8.5-bis). Dove serve
   l'adattatore, l'adattatore si riduce a **risolutore** (riga → emittente): resta per
   riga, ma è una lettura per chiave.
3. **Equivalenza per costruzione**: le funzioni della catena sono STABLE, cioè vedono già
   una fotografia per istruzione; calcolare il perimetro una volta per istruzione non
   cambia cosa si vede, cambia quante volte lo si calcola.

### Decisioni attese

* **D-3b-2a** — la forma: BB del perimetro + canonica riscritta su di lui + policy con la
  sottoquery scalare + adattatori ridotti a risolutori.
* **D-3b-2b** — il perimetro del lavoro: tutte le policy ef_whitelist in un giro, o **a
  ondate** per famiglia (come l'accensione della RLS), cominciando dalle 77 dirette e dai
  risolutori di `vendite`. Le famiglie cliente/shop/fornitore/note hanno la stessa forma
  e restano fuori, a debito dichiarato, se non si decide altrimenti.

✅ **Decise da Tid il 2026-10-18**: la forma (D-3b-2a) e le ondate (D-3b-2b). Prima ondata
in due giri: **1a** le policy dirette, **1b** gli adattatori di `vendite`.

### Giro 1a — ✅ applicato (2026-10-18); correzione `-22`/`-23` da applicare

**Due correzioni alla forma, trovate scrivendo:**

* **§10.3 è tassativa**: la policy chiama una `fn_scope_*`, niente logica in linea; §10.4:
  i GUC li passa la policy. La forma diventa
  `script.fn_scope_ef_perimetro((SELECT … IS NULL), (SELECT …), emittente)`: una funzione
  di scope **pura e incorporabile**, a cui la policy passa il perimetro in due sottoquery
  non correlate. Ogni parametro una volta sola nel corpo, o PostgreSQL rifiuta
  l'incorporazione (argomento-sottoquery usato due volte).
* **Il perimetro come insieme esisteva già**: `script.fn_get_emittenti_scope_pk_ids`
  (`NULL` = tutti, `'{}'` = nessuno, whitelist ∩ emittente attivo), usata dal backend. Il
  `fn_perimetro_ef` che avevo scritto era un doppione (regola del 2): ritirato prima di
  qualunque apply. E la regola era già scritta **due** volte, nella canonica e in
  `_pk_ids` (ordine diverso fra veste e super admin, stesso esito: il super admin richiede
  una veste OPERATORE utilizzabile). Ora una: la canonica chiede a `_pk_ids`.

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261018-16-create-fn-scope-ef-perimetro` | la funzione di scope pura (`IMMUTABLE`, incorporata) |
| `20_code/script/20261018-17-alter-fn-get-emittenti-scope-pk-ids-cost` | `COST 5000` (era 100: legge tabelle, ora la nominano le policy) |
| `20_code/script/20261018-18-update-fn-check-user-emittente-scope-su-perimetro` | la canonica chiede a `_pk_ids` e interroga con `fn_scope_ef_perimetro`; firma ancorata `%TYPE` |
| `00_schema/vendite/20261018-19-alter-policy-ef-whitelist-dirette-perimetro` | le 13 policy scritte a mano (5 schemi), `USING` e `WITH CHECK`, generate dal testo vivo (identico su dbdev e scratch) |
| `20_code/dbops/20261018-20-update-fn-storico-arma-scope-perimetro` | il generatore delle policy dello storico scrive la forma nuova |
| `00_schema/storico/20261018-21-alter-policy-storico-ef-whitelist-perimetro` | riallinea le 51 policy di lettura dello storico già armate (il generatore crea solo se manca); nessuna preCondition sul numero (§11.4) |

**Presidi.** Nuovo `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (plan 4:
derivazione non cieca; nessuna policy con `fn_scope_ef_whitelist(`; perimetro sempre in
sottoquery; **dal piano** di ogni tabella con RLS accesa: perimetro in `InitPlan`, nessuna
funzione della catena nel `Filter`). `script/test-policy-funzioni-cost-v1`: l'elenco delle
economiche misurate vale anche per il test 2, con `fn_scope_ef_perimetro` (<0,001 ms a
chiamata, incorporata). `storico/test-storico-scope-congelato-v1` test 6: la forma nuova.

**Prove** (scratch `zeroerp_ruoli`, SQL estratto, da owner; 2026-10-18):

* piano di `vendite.ddt` sotto policy: `((InitPlan 1).col1 OR COALESCE((emittente_fiscale_id = ANY ((InitPlan 2).col1)), false))`;
* presidio nuovo: **senza** 2/4 (rossi 1 e 2), **con** 4/4 su 64 tabelle;
* 56 pgTAP (canonica, parità `_pk_ids`, permessi, titoli IVA, storico, costo, tutti
  `rls/`): esiti identici senza e con, salvo i due rossi attesi senza (presidio nuovo,
  storico 6). I rossi presenti in entrambe le corse sono preesistenti dello scratch;
* andata e ritorno dei sei: funzioni (definizione, COMMENT, `COST`, GRANT) e testi di tutte
  le 310 policy identici (md5) dopo il rollback, e uguali a dbdev.

⚠️ **Incidente sullo scratch (2026-10-18, mio).** Nella prima tornata inserivo l'SQL
estratto dopo la prima occorrenza di `BEGIN;`: sei file hanno `-- BEGIN; + ROLLBACK a fine
file` in testa, l'SQL è finito nel commento e quei file sono girati **in autocommit**.
Committati su `zeroerp_ruoli`: i sei changeSet (non registrati nel `databasechangelog`), le
fixture di sei test (due corse ciascuno) e `vendite.preventivi DISABLE ROW LEVEL SECURITY`
(riga 181 di `rls/test-rls-preventivi-ef-whitelist-write`). Lo ha visto
`rls/test-rls-perimetro-scoperto` (POLICY_INERTE `NON_DICHIARATO`). **Rimediato**: rollback
dei sei committato, RLS di `vendite.preventivi` riaccesa, md5 di funzioni e policy uguale a
dbdev, `test-rls-perimetro-scoperto` di nuovo 8/8, tutte le prove rifatte su scratch pulito.
**Restano** le righe di fixture committate (operatori, emittenti, whitelist, documenti di
prova): da togliere con la ricostruzione dello scratch (`ci-local.sh --fresh --ci-apply`)
prima della prossima baseline. Su dbdev l'SQL estratto non è mai stato lanciato.

**Doc**: linee-guida-sql §10.3 (la forma, e perché) e §10.9; pagine `manual/` di
`fn_scope_ef_perimetro` (nuova), `fn_get_emittenti_scope_pk_ids`,
`fn_check_user_emittente_scope`, `fn_scope_ef_whitelist` (correggevano tre affermazioni
false: «valutata una volta sola dal planner», «utente NULL → true», «whitelist vuota →
nessuna restrizione»).

**Non fatto in 1a**: gli adattatori `via_*` (~230 policy) → giro 1b; le famiglie
cliente/shop/fornitore/note → fuori, a debito dichiarato.

✅ **Applicato** da Tid (2026-10-18 12:12, `-16…-21` `EXECUTED` su dbdev e sullo scratch),
pgTAP verdi, nessuna regressione nei test. Dopo l'apply, dbdev come app: 64 policy nella
forma nuova; `count(*)` di `vendite.ddt`, `ordini`, `preventivi` 2-3 ms.

### ⛔ La regressione che i test non vedono, e la correzione (`-22`, `-23`)

Misurato dopo l'apply (dbdev come app, riga 15922, 8 corse): il verbo dell'accredito
**60-64 → 80-86 ms**. Le risposte sono giuste, quindi nessun pgTAP diventa rosso: è solo
tempo. Il verbo attraversa tabelle protette da adattatori `via_*`, che chiamano la
canonica **per riga**, e la canonica di `-18` costa di più a chiamata:

* **uscita anticipata persa**: la canonica di prima, con un emittente attivo, rispondeva
  `false` subito per un emittente diverso; quella di `-18` calcola sempre il perimetro;
* **veste verificata due volte**: `_pk_ids` chiedeva la veste OPERATORE e poi il super
  admin, che la riverifica dentro `fn_is_super_admin_account`.

Copie `pg_temp`, 300 chiamate, ms a chiamata (dbdev come app, 2026-10-18):

| Utente | Emittente attivo | Prima di oggi | `-18` | Con `-22`/`-23` |
| --- | --- | --- | --- | --- |
| tid (super admin) | 32 | 0,024 | 0,109 | 0,021 |
| tid (super admin) | — | 0,061 | 0,115 | 0,059 |
| pochi | 32 | 0,025 | 0,077 | 0,025 |
| pochi | — | 0,079 | 0,076 | 0,077 |

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261018-22-update-fn-get-emittenti-scope-pk-ids-super-admin-prima` | il super admin si chiede prima della veste (stesso esito: il super admin richiede una veste OPERATORE utilizzabile); firma `%TYPE`, `COST 5000` ripetuto |
| `20_code/script/20261018-23-update-fn-check-user-emittente-scope-uscita-emittente-attivo` | con un emittente attivo, per un emittente diverso `false` senza calcolare il perimetro: conseguenza della regola (il perimetro è al più `{attivo}`), non una seconda copia; la parità la tiene il test di parità |

**Prove** (2026-10-18): scratch, SQL estratto, 12 pgTAP (canonica, parità, impersonazione,
permessi, titoli IVA, presidio nuovo, costo, quattro `rls/…-write`/functional, accredito)
tutti verdi; andata e ritorno identico (md5). Equivalenza su dbdev come app, copie
`pg_temp`, vecchia canonica contro corretta: **0 differenze** su 368 casi della canonica e
92 del perimetro (23 utenti, 4 emittenti compresi `NULL` e inesistente, 4 stati
dell'emittente attivo) — colore: come app gli emittenti visibili sono pochi; la prova è
la costruzione e i test costruiti.

⚠️ La lezione per il giro 1b: un cambio di una funzione chiamata **per riga** si misura
anche nel **costo a chiamata**, non solo nelle risposte.

✅ **Applicato** da Tid (`-22`, `-23` alle 12:23), pgTAP verdi (baseline `script`, accredito).
Baseline dello scratch (`baseline-rossi-scratch.tsv`, 12:20): quattro file escono dai rossi;
`vendite/test-guard-uscita-commessa-v1` resta rosso e cambia tipo (`ERRORE_FIXTURE` →
`ASSERZIONE`), non nasce da questi changeSet: da guardare a parte.

### Il costo fisso per istruzione (2026-10-18, dbdev come app)

Verbo dopo `-22`/`-23`: **68-77 ms** (prima del giro 1a 60-64, dopo 80-86). La differenza
che resta è della forma a **due** sottoquery: ogni istruzione su una tabella protetta
calcola il perimetro due volte, anche quando legge una riga per chiave.

| Misura (300 ripetizioni) | ms |
| --- | --- |
| `fn_get_emittenti_scope_pk_ids(1)`, una chiamata | 0,058-0,067 |
| canonica, una chiamata | 0,056-0,061 |
| lettura per chiave di `vendite.ddt` sotto policy (due perimetri) | 0,125-0,130 |
| lettura per chiave di `vendite.resi_righe` (adattatore `via_reso`, per riga) | 0,191-0,199 |

| Forma, su 20.000 righe di prova | ms |
| --- | --- |
| due sottoquery, funzione di scope incorporata (quella applicata) | 1,8-2,9 |
| **una** sottoquery, funzione di scope non incorporata (il perimetro le serve due volte) | 26-32 |

Per istruzione: la forma applicata costa 2 × 0,058 ms fissi e ~0,0001 ms a riga; quella a
una sottoquery 0,058 ms fissi e ~0,0015 ms a riga. Pari a ~40 righe lette. Prima di oggi:
0,02-0,08 ms **a riga**.

**Decisione attesa — D-3b-2c**: passare alla forma a una sottoquery
(`fn_scope_ef_perimetro(perimetro, emittente)`, stessa convenzione NULL = tutti di
`_pk_ids`) per riportare le letture di una riga al costo di prima, accettando ~1,5 µs a riga
sulle scansioni; oppure tenere la forma applicata. Una terza via (una sottoquery e
funzione incorporata) esiste solo con un valore sentinella per l'emittente NULL
(`coalesce(emittente, 0)` + `CHECK (id > 0)` sugli emittenti): scartata, un numero magico in
una regola di sicurezza.

✅ **D-3b-2c decisa da Tid (2026-10-18): una sottoquery.**

### D-3b-2c — scritta e provata (2026-10-18), da applicare

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261018-24-create-fn-scope-ef-perimetro-un-argomento-perimetro` | `fn_scope_ef_perimetro(perimetro bigint[], emittente)`: NULL = tutti, la convenzione di `_pk_ids` |
| `20_code/script/20261018-25-update-fn-check-user-emittente-scope-scope-un-argomento` | la canonica chiama la firma nuova (corpo vivo dopo `-23`, `%TYPE`, `COST 5000`) |
| `00_schema/vendite/20261018-26-alter-policy-ef-whitelist-dirette-una-sottoquery` | le 13 policy, perimetro in una sottoquery (dal testo vivo; il catalogo stampa l'alias `AS fn_get_emittenti_scope_pk_ids` nella seconda sottoquery, la regex lo sa) |
| `20_code/dbops/20261018-27-update-fn-storico-arma-scope-una-sottoquery` | il generatore dello storico |
| `00_schema/storico/20261018-28-alter-policy-storico-ef-whitelist-una-sottoquery` | riallinea le policy dello storico già armate |
| `20_code/script/20261018-29-drop-fn-scope-ef-perimetro-tre-argomenti` | ritira la firma a tre argomenti (preCondition: nessuna dipendenza in `pg_depend`); rollback: la ricrea come in `-16` |

**Presidi**: `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` — test 3 rifiuta
la forma a due sottoquery, test 4 ammette `fn_scope_ef_perimetro` nel `Filter` (ora è la
chiamata per riga voluta) e vieta la catena. ⚠️ Nel piano il perimetro può comparire più
volte, una per policy applicata: `soggetti_titoli_iva_ambiti`/`_movimenti` fanno un
`EXISTS` sul titolo padre, che ha la sua policy (la prima stesura del test 4 lo contava
come difetto). `script/test-policy-funzioni-cost-v1`: la misura dell'economica aggiornata.

**Prove** (scratch `zeroerp_ruoli`, SQL estratto, inserimento dopo la riga `BEGIN;`):

* lettura per chiave di `vendite.preventivi` sotto policy, stessa sessione, operatore di
  fixture: due sottoquery **0,24-0,27 ms**, una **0,084-0,088 ms**; un solo `InitPlan`;
* presidio: senza 3/4 (vede la forma a due), con 4/4 su 64 tabelle;
* 51 pgTAP (canonica, parità, impersonazione, permessi, titoli IVA, storico, costo,
  accredito, tutti `rls/`): esiti identici senza e con;
* andata e ritorno dei sei: funzioni (con la firma a tre argomenti e il suo COMMENT) e
  testi delle 310 policy identici (md5); scratch invariato dopo ogni corsa.

Doc: `manual/fn_scope_ef_perimetro` riscritta, linee-guida-sql §10.3 (una sottoquery, e
perché non due) e §10.9, note in `fn_get_emittenti_scope_pk_ids` e `fn_scope_ef_whitelist`.

✅ **Applicato** da Tid su dbdev (2026-10-18 12:39, `-24…-29` `EXECUTED`): resta solo
`fn_scope_ef_perimetro(bigint[],bigint)`, nessuna policy nella forma a due sottoquery. Dopo
l'apply, dbdev come app, verbo dell'accredito sulla riga 15922, 8 corse: 133 ms a freddo,
poi **64-69 ms** (una corsa a 91). Il percorso: 60-64 prima del giro 1a, 80-86 dopo, 68-77
con `-22`/`-23`, 64-69 con la forma a una sottoquery. Quello che resta al verbo sono gli
adattatori `via_*` per riga (giro 1b), la coda e il `tx_id` (D-3b-3).

### Giro 1b — gli adattatori di `vendite`: censimento e proposta (2026-10-18)

**Censimento** (dbdev, `pg_policies`): 22 adattatori `fn_scope_ef_whitelist_via_*` toccano
tabelle di `vendite` (12 altri stanno in `magazzino`, `pratiche`, `pagamenti`, `documenti`,
`anagrafiche`: ondata 2). Tutti `LANGUAGE sql`, `INVOKER`, `COST 5000`, nella stessa forma:
`canonica(utente, (SELECT emittente FROM <padre> WHERE id = chiave))`, spesso a catena (riga →
documento → emittente; commessa/fattura/lotto/listino → ruolo emittente → emittente via
`via_sr`). Uno (`via_efba`) è plpgsql e ragiona sul billing account.

**Il difetto che il giro 1a non tocca.** La sottoquery di risoluzione gira **sotto la RLS del
padre** (l'adattatore è INVOKER): ogni chiamata per riga esegue la policy del padre — che
ora calcola il suo perimetro, un `InitPlan` **per chiamata** — e poi la canonica. Lettura per
chiave di `vendite.resi_righe` (adattatore `via_reso_riga` → `via_reso`): **0,19 ms**.
Un risolutore INVOKER non lo cura: la policy del padre resterebbe dentro, a ogni riga.

**La proposta (D-3b-2d).** Risolutori `SECURITY DEFINER` del migratore, che leggono
l'emittente del padre **oltre la RLS** (il pattern di §10.5: `fn_resolve_*`), uno per chiave,
con la catena in una sola lettura per chiave:

```sql
-- per riga: una lettura per chiave, nessuna policy annidata
script.fn_scope_ef_perimetro(
    (SELECT script.fn_get_emittenti_scope_pk_ids(<utente>)),   -- una volta per istruzione
    script.fn_emittente_di_reso_riga(resi_riga_id))            -- per riga
```

Stesso esito: per l'operatore il padre è invisibile esattamente quando il suo emittente è
fuori perimetro (la policy del padre è la stessa regola), e il gate della veste OPERATORE
resta nella policy figlia. Prova di costo (dbdev come app, 20.000 righe, padre per chiave):
risolutore **~3,3-3,6 µs a riga**, INVOKER o DEFINER, con o senza `SET search_path`.

⚠️ **Il prezzo, ed è una decisione di sicurezza**: un risolutore DEFINER risponde «di che
emittente è il documento N» anche per un documento che chi chiama non vede. L'applicazione
deve poterlo eseguire (le policy girano col suo ruolo). Si saprebbe l'id dell'azienda
proprietaria di un id di documento, non il documento. Precedente: `fn_resolve_emittente_fiscale_id`
(DEFINER, nelle economiche misurate del presidio sul costo).

**Il lavoro**: ~22 risolutori, ~60 policy di `vendite` (e le 13 di `pagamenti` che usano
`via_fattura`/`via_sr`), i pin strutturali dei test satelliti che nominano gli adattatori
nel testo delle policy (`rls/test-rls-*-satelliti`, `test-rls-arrotondamenti-scope`,
`test-rls-vendite-contabili-lotti`), il presidio esteso agli adattatori. Gli adattatori
restano per chi chiede su un emittente fuori dalle policy, se qualcuno li chiama; altrimenti
si ritirano nello stesso giro.

**Decisione attesa — D-3b-2d**: risolutori DEFINER (con quel prezzo), o INVOKER (nessuna
lettura oltre la RLS, ma la policy del padre resta per riga e il guadagno del giro 1b si
riduce alla sola canonica).

✅ **D-3b-2d decisa da Tid (2026-10-18): DEFINER.**

### Giro 1b — ✅ applicato (2026-10-18 14:26) e misurato

**Il risolutore c'era già** (regola del 2): `script.fn_resolve_emittente_fiscale_id(modo,
valore)`, DEFINER con `search_path` bloccato, la domanda di FATTO («di chi è questa riga»)
separata da quella di permesso, usata dai guard di scrittura. Aveva 7 modi; ne servivano
18. Niente risolutori nuovi.

**Gli adattatori non si ritirano**: li chiamano i verbi di vendite (`fn_annulla_*`,
`fn_cambia_stato_ddt`, `fn_conferma_reso`, `fn_ddt_riga_correggi_qta_evasa`),
`fn_scope_note_ef_whitelist`, il backend (`vendite_service`, `pagamenti_repository`) e 12
pgTAP. Per non lasciare la strada documento → emittente in due posti, si riscrivono sul
risolutore.

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261018-31-update-fn-resolve-emittente-fiscale-id-documenti-vendita` | 18 modi: `ddt`, `ddt_riga`, `ordine`, `ordine_riga`, `preventivo`, `preventivo_riga`, `offerta`, `offerta_eccezione`, `contratto`, `contratto_riga`, `reso`, `reso_riga`, `commessa`, `commessa_attivita`, `attivita_fatturabile`, `lotto`, `fattura_sdi`, `listino_versione`; corretto il commento del modo `listino` (il valore è l'id del listino) |
| `20_code/script/20261018-32-update-fn-scope-ef-whitelist-via-su-risolutore` | i 21 adattatori di vendite = `canonica(utente, fn_resolve_emittente_fiscale_id('<modo>', chiave))`; firme `%TYPE`, `COST 5000`; senza sottoquery ora si incorporano |
| `00_schema/vendite/20261018-33-alter-policy-ef-whitelist-via-risolutore` | 69 policy (140 sostituzioni): `fn_scope_ef_perimetro((SELECT perimetro), fn_resolve_emittente_fiscale_id('<modo>', chiave))`; comprese le 2 con `via_contabile` — una lo combinava in `OR` con un adattatore del giro, e lasciato per riga riportava la canonica nel piano |

`-30` è dell'altra sessione (`create-fn-crea-fornitore`). `via_efba` resta: ragiona sul billing
account, non su un emittente.

**Presidi**: presidio nuovo, **test 5**: nessuna policy chiama un adattatore `via_*` fuori
dal debito dichiarato dell'ondata 2 (12 adattatori elencati per nome: magazzino, pratiche,
documenti, anagrafiche, `via_efba`). Pin di forma aggiornati alla stessa rotta, letta nel
modo del risolutore invece che nel nome dell'adattatore: `rls/test-rls-arrotondamenti-scope`
3, `test-rls-commesse-satelliti` 3, `test-rls-fatture-stampa-coda` 3,
`test-rls-listini-satelliti` 3, `test-rls-lotti-satelliti` 3, `test-rls-policies-structure` 8,
`test-rls-vendite-contabili-lotti` 4; la canarina di `script/test-policy-funzioni-cost-v1`
è ora `fn_scope_ef_perimetro`.

**Prove** (scratch `zeroerp_ruoli`, SQL estratto, 2026-10-18):

* piano di `vendite.resi_righe` sotto policy: per riga
  `fn_scope_ef_perimetro((InitPlan 1).col1, fn_resolve_emittente_fiscale_id('reso', reso_id))`;
* 84 pgTAP (presidio, costo, storico, canonica, parità, impersonazione, permessi, titoli
  IVA, billing account, accredito, i pgTAP dei verbi che usano gli adattatori, tutti
  `rls/`): **con** il giro esiti identici a prima; **senza** rossi solo gli 8 pin aggiornati
  e il test 5 del presidio;
* andata e ritorno: 35 funzioni (risolutore e adattatori, con COMMENT e configurazione) e
  310 policy identiche (md5); scratch invariato dopo ogni corsa.

Doc: `manual/fn_resolve_emittente_fiscale_id` (i modi, il prezzo DEFINER), note in
`fn_scope_ef_whitelist_via_{commessa,fattura,listino,sr}`, linee-guida-sql §10.3.

**Resta**: misurare dopo l'apply (verbo dell'accredito, una lista di righe); ondata 2 (gli
adattatori di magazzino, pratiche, documenti, anagrafiche), che con il risolutore è la
stessa forma.

✅ **Applicato** da Tid su dbdev (2026-10-18 14:26, `-31…-33` `EXECUTED`), pgTAP verdi.

**Misura dopo l'apply** (dbdev come app, contesto di `tid`, emittente attivo 32):

| Cosa | Prima di D-3b-2 | Dopo il giro 1a (`-29`) | Dopo il giro 1b |
| --- | --- | --- | --- |
| verbo dell'accredito, riga 15922 | 60-64 ms | 64-69 ms | **mediana 56-59 ms** (2 × 20 corse, min 51, max 78) |
| lettura per chiave di `vendite.resi_righe` (adattatore → risolutore) | — | 0,19 ms | **0,076-0,106 ms** |
| lettura per chiave di `vendite.ddt_righe` | — | — | 0,15 ms |
| `count(*)` di `vendite.commesse_attivita` (132 righe) | 33-62 ms (stesso filtro per riga, da owner, §5quinquies) | — | **4,2-6,0 ms** |
| `count(*)` di `vendite.attivita_fatturabili` (63 righe) | — | — | 0,8-1,5 ms |

Fatti datati, non motivi: la forma si è decisa sul modello (il perimetro non dipende dalla
riga). Il verbo è rumoroso — le singole corse vanno da 51 a 78 ms — ma la mediana sta sotto
il punto di partenza. Quello che gli resta sono la coda (`fn_resi_da_accreditare`, partite
merce), l'upsert della commessa e il `tx_id` via `dblink` (D-3b-3).

### Ondata 2 — scritta e provata (2026-10-18), da applicare

Decisa da Tid il 2026-10-18 («3b-2 ora»). Numeri dopo l'ultimo del giorno (`-47`, di altre
sessioni).

**Due specie di adattatori.** Dieci a emittente singolo (`asset`, `documento_generato`,
`evento_asset`, `flusso`, `inventario`, `magazzino`, `movimento`, `pratica`, `rettifica`,
`trasferimento`): la cura del giro 1b. E il **billing account** (`via_efba`): un BA ha un
emittente, ma quale lo dice `script.fn_get_ba_emittente_sr_id` — legame esplicito,
altrimenti l'emittente **dell'utente in sessione**, altrimenti il default — cioè non un
fatto della riga, quindi non un modo del risolutore (la domanda di FATTO). Lì il perimetro
va in convenzione soggetto_ruolo: `fn_scope_ef_perimetro((SELECT
fn_get_emittenti_scope_sr_ids(u)), fn_get_ba_emittente_sr_id(ba))`. Stesse risposte di
`via_efba` (NULL = tutti, `'{}'` = nessuno, BA senza emittente = false).

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261018-48-update-fn-resolve-emittente-fiscale-id-magazzino-pratiche` | 9 modi: `asset`, `evento_asset`, `inventario`, `movimento`, `rettifica`, `trasferimento` (magazzino di partenza, come l'adattatore), `pratica`, `flusso`, `documento_generato` |
| `20_code/script/20261018-49-update-fn-scope-ef-whitelist-via-ondata-2` | i 10 adattatori sul risolutore; `via_efba` da plpgsql a sql, la composizione delle sue policy |
| `00_schema/vendite/20261018-50-alter-policy-ef-whitelist-via-ondata-2` | 34 policy (68 sostituzioni): magazzino, pratiche, documenti, billing account / clienti / attività di consumo |
| `20_code/script/20261018-51-alter-fn-scope-sr-ids-e-ba-emittente-cost` | `COST 5000` a `fn_get_emittenti_scope_sr_ids` e `fn_get_ba_emittente_sr_id`, ora nominate dalle policy (erano 100) |

**Resta, dichiarato**: `via_coppia` (`istanze_dati_precontrattuali`): la chiave è una coppia
di colonne (istanza, utility) e il risolutore prende un valore solo. È l'unico nome
nell'elenco del debito del presidio (test 5). Chiama `via_efba`, già nella forma nuova.

**Un errore mio trovato prima dell'apply**: nella preCondition di `-50` la regex era finita
`\\(` invece di `\(` — conteggio 0, l'apply si sarebbe fermato in HALT. Corretta e
verificata sullo scratch (34). Le preCondition di tutti e quattro sono state eseguite a
mano (`read -r`: senza, la shell mangia la barra e il controllo mente).

**Presidi**: test 5 del presidio nuovo — il debito si riduce a `via_coppia`; test 4 vieta
nel `Filter` anche `fn_get_emittenti_scope_sr_ids`. Pin di forma aggiornati alla stessa
rotta: `rls/test-rls-pratiche-satelliti` 3 (modi `pratica`/`flusso`),
`test-rls-documenti-satelliti` 3 (`documento_generato`), `test-rls-commesse-satelliti` 3 (la
riga di `attivita_consumi`: `fn_get_ba_emittente_sr_id`).

**Prove** (scratch `zeroerp_ruoli`, SQL estratto, 2026-10-18): 115 pgTAP (presidi, canonica,
parità, impersonazione, permessi, billing account, accredito, tutti `rls/`, magazzino,
pratiche, documenti): **con** esiti identici a prima; **senza** rossi solo i pin aggiornati e
il test 5 del presidio. Andata e ritorno: 37 funzioni e 310 policy identiche (md5); scratch
invariato.

Doc: `manual/fn_resolve_emittente_fiscale_id` (i 9 modi), note negli adattatori di
magazzino, `via_efba`, `via_coppia` (il perché del debito), linee-guida-sql §10.3 (il BA in
convenzione SR).

✅ **Applicato** da Tid su dbdev (2026-10-18 14:45, `-48…-51` `EXECUTED`), pgTAP verdi. Nelle
policy resta un solo adattatore (`via_coppia`, dichiarato).

Misura dopo l'apply (dbdev come app, contesto di `tid`, emittente attivo 32): `count(*)` sotto
policy di `pratiche.flussi` (204 righe) 3,1 ms, `documenti.documenti_generati` (225) 0,8 ms,
`anagrafiche.billing_account` (41) 2,9 ms, `anagrafiche.clienti` (20) 2,2 ms,
`pratiche.pratiche` (102) 0,4 ms. Prima dell'ondata 2 queste tabelle non sono state misurate:
nessun confronto, solo il fatto datato. Verbo dell'accredito (fuori da questa ondata):
mediana 57-61 ms su 2 × 20 corse, come dopo il giro 1b.

**D-3b-2 chiusa** (2026-10-18): il perimetro dell'operatore si calcola una volta per
istruzione in tutte le policy ef_whitelist, salvo `via_coppia` (debito dichiarato nel
presidio, con il motivo). Famiglie cliente/shop/fornitore/note fuori perimetro, come deciso.

## 5sexies. D-3b-3 — il `tx_id` via `dblink` (2026-10-18)

**Il modello** (guida `tx_id_implementation_guide`, linee-guida-sql §9): alla prima scrittura
di ogni transazione `dbops.trgfn_tx_id_managed` chiama `dbops.fn_get_or_create_session_tx_id()`
(DEFINER di `postgres`), che registra un id in `dbops.transaction_ids` **via `dblink`** —
su una connessione separata, perché la registrazione deve **sopravvivere al rollback** della
transazione principale — e lo pubblica nella GUC `dbops.tx_id` per il resto della transazione.
È una proprietà voluta, non un incidente. Il backend la chiama anche in
`apps/core/services/idempotency_store.py`.

**Fatti datati** (2026-10-18, dbdev come app):

* prima chiamata di ogni transazione **~12-13 ms** (27 ms alla prima della sessione, con la
  connessione), le successive ~0 (GUC già pubblicata);
* commit locale con XID, `synchronous_commit = on`, `fdatasync`: **0,05 ms** — il disco non
  è il collo di bottiglia;
* `dbops.transaction_ids`: 564.010 righe, 93 MB, solo la PK, nessun trigger in inserimento,
  nessuna FK che la referenzi; l'`INSERT` remoto dovrebbe costare frazioni di ms;
* stamattina `script.fn_log_error_only`, anch'esso via `dblink`, costava ~4 ms: il giro
  `dblink` da solo non spiega 12 ms.

**Da misurare da superuser** (la connessione è `service=zeroerp_log`, ruolo e parametri nel
`pg_service.conf` del server): connessione, `dblink` con `SELECT 1`, con un commit remoto
senza dati, con `fn_generate_tx_id` sincrono e asincrono, ed esecuzione remota. Script
`d3b3-pgadmin.sql` (scratchpad della sessione), da lanciare in pgAdmin come superuser: scrive
20 righe di misura nel registro (immutabile, restano come per ogni transazione vera).

Decisione attesa dopo la misura — **D-3b-3**: dipende da dove stanno i 12 ms (configurazione
della sessione di log, o forma del percorso).

**La misura da superuser** (Tid, pgAdmin, dbdev, 2026-10-18), connessione `misura_d3b3` aperta
una volta e riusata:

| Cosa | ms |
| --- | --- |
| aprire la connessione (`service=zeroerp_log`, ruolo remoto `zeroerp_log`, `synchronous_commit=on`) | **25,9** |
| `dblink` `SELECT 1` | 0,18 a chiamata |
| `dblink` con XID e commit remoto, nessun dato | 0,12 |
| `dblink` `fn_generate_tx_id`, commit sincrono | **1,29** |
| idem con `synchronous_commit = off` | 0,23 |
| esecuzione remota di `fn_generate_tx_id` | 0,067 |

**La causa — un difetto di forma, non di configurazione.** Il passo 1 di
`fn_get_or_create_session_tx_id` apre (o trova aperta) la connessione persistente `'logconn'`
(`script.fn_ensure_logconn`), ma il passo 3 chiamava `dblink(v_dblink_conn, …)` con la
**stringa** di connessione: `dblink` apriva e chiudeva una connessione nuova a ogni chiamata,
cioè alla prima scrittura di ogni transazione, e `'logconn'` restava inutilizzata. Sul modello:
il costo di una connessione pagato per ogni transazione che scrive.

**La cura — `20_code/dbops/20261018-52-update-fn-get-or-create-session-tx-id-logconn-persistente`**:
`dblink('logconn', …)` quando è aperta; la stringa resta il ripiego se `'logconn'` non c'è (il
passo 1 può non aprirla: `too_many_connections`) e se la chiamata sulla persistente fallisce
(connessione caduta: la si chiude e si riprova una volta da una nuova, come faceva sempre la
versione di prima). Sentinella, GUC locale alla transazione, autonomia della registrazione:
invariati. La funzione è di `postgres`: il rito del prestito di proprietà di `20260912-40`,
nelle modifiche e nel rollback. Corpo vivo = `-40` (90 righe, verificato).

Il commit asincrono della sessione di log (1,29 → 0,23 ms) **non** è nella cura: è una scelta
di durabilità del registro (un crash potrebbe perdere le ultime registrazioni), da decidere a
parte se mai servisse.

**Prove sullo scratch** (lì `myapp.dblink_log_connection` è vuoto: il ramo `dblink` non si
attiva; si provano il rito, la sintassi, l'andata e ritorno): dopo il changeSet la funzione
torna di `postgres` e il registro dice `postgres`; il corpo nuovo usa `dblink('logconn', …)`;
andata e ritorno identico (md5 di definizione, COMMENT, owner, GRANT, configurazione);
`dbops/test-tx-id-coerenza-non-registrato` 11/11 e `dbops/test-security-definer-search-path-v1`
5/5, senza e con.

**Prova del ramo vero, su dbdev prima dell'apply** (da superuser, in pgAdmin, transazione
annullata): script `d3b3-prova-52-pgadmin.sql` (scratchpad della sessione) — 10 generazioni
con la funzione di oggi, 10 con la nuova, 10 dopo aver chiuso `'logconn'` a mano (il passo 1
la deve riaprire); per ciascuna: ms a generazione, quante registrate davvero in
`dbops.transaction_ids`, se `'logconn'` è aperta.

✅ **Applicato** da Tid su dbdev (2026-10-18 14:57, `-52` `EXECUTED`; la prova in pgAdmin non è
stata lanciata, lo script resta per chi volesse rifarla). Dopo l'apply: la funzione è di
`postgres`, il registro dice `postgres`, il corpo usa `dblink('logconn', …)`.

**Misura dopo l'apply** (dbdev come app, 2026-10-18):

| Cosa | Prima di `-52` | Dopo |
| --- | --- | --- |
| prima chiamata di `fn_get_or_create_session_tx_id()` in una transazione | 12-13 ms | **1,3-2,2 ms** (15 ms la prima della sessione: apre `'logconn'`) |
| tx_id generati e registrati in `dbops.transaction_ids` | — | sì (13 registrazioni nuove nelle corse di verifica) |
| verbo dell'accredito, riga 15922, mediana su 19 corse | 56-61 ms | **50,6 ms** (min 43,2, max 70,3; la prima a freddo 123) |

**D-3b-3 chiusa** (2026-10-18). Fuori dalla cura, da decidere solo se servisse: il commit
asincrono della sessione di log (1,46 → 0,32 ms, a prezzo della durabilità del registro).

### D-3b — il percorso del verbo dell'accredito, riga 15922 (dbdev come app)

| Passo | Mediana del verbo |
| --- | --- |
| partenza (2026-10-11, §5bis) | ~115-120 ms |
| D-3b-1, `segment_base` (`-15`) | 60-64 ms |
| D-3b-2 giro 1a (`-16…-29`, con le correzioni `-22`/`-23` e la forma a una sottoquery) | 64-69 ms |
| D-3b-2 giro 1b (`-31…-33`) | 56-59 ms |
| D-3b-3, `logconn` persistente (`-52`) | **50,6 ms** |

Fatti datati, non motivi: ogni cura si è decisa sul modello (un filtro che non arriva
all'indice, un perimetro che non dipende dalla riga, una connessione aperta e non usata).
Quello che resta al verbo è il suo lavoro: la coda (partite merce), l'upsert della commessa
e le scritture con i loro trigger. (aggiornato al 2026-10-11)

| Voce | Cosa | Stato | Dove |
| --- | --- | --- | --- |
| D-1 | censimento delle funzioni che ripianificano | ✅ fatto | §4 |
| D-2 | il lister dei DDT **senza filtri** (diagnosi di tutti i DDT in una chiamata) | ✅ **chiusa**: la CTE `src` si ricalcolava per ogni riga (righe² giri sotto RLS); `20261012-03` applicato, 1135 → 154 ms, presidio di forma (test 18) | §2.2, §5ter |
| **D-3** | resi: misurare un ciclo di accredito **costruito** (in transazione annullata) e, clausola `plan_cache_mode` **solo** su `fn_resi_riga_tetti_accredito` (D-3a: non sul verbo né sul trigger, §5bis). Un solo changeSet, **numero riservato `20261011-42`** (in `20_code/vendite/`). Presidio: il pgTAP `test-fn-available-actions-ddt-piano-generico-v1` diventa `test-plan-cache-mode-piano-generico-v1` con le tre funzioni, e il vecchio si ritira nello stesso giro (decisione di Tid, 2026-10-11) | **D-3a** ✅ `20261011-42` applicato, presidio 5/5 su dbdev · **D-3b** 🔎 profilata il 2026-10-18: 72% in tre filtri `LIKE`/`split_part` su `segment_key` che sotto RLS non entrano nell'indice · **D-3b-1** ✅ `20261018-15` applicato, pgTAP verde, verbo ~120 → ~62 ms · **D-3b-2** giro 1a ✅ `20261018-16…-29`, giro 1b ✅ `-31…-33` applicati e misurati (verbo mediana 56-59 ms, `count(*)` di 132 righe 33-62 → 4-6 ms); ondata 2 ✅ `-48…-51` applicata — **D-3b-2 chiusa** (resta solo `via_coppia`, dichiarato) · **D-3b-3** ✅ `20261018-52` applicato: `tx_id` 12-13 → 1,3-2,2 ms a transazione, verbo mediana 50,6 ms · **D-3b-3** ⬜ | §4.3, §4.4, §5bis, §5quater |
| D-4 | pannello «Passaggi», primo passo | ✅ `20261010-44` applicato e misurato | §5.2 |
| **D-5 + D-6** | lista offerte per id e lineage seminata (ogni pagina di sette liste paga il grafo intero) | ✅ **chiuse nel brief figlio** (2026-10-11): grafo seminato per chiave, liste ed export dalla sintesi dopo la paginazione, `vw_documento_lineage` ritirata | [brief-db-lineage-seminata-per-chiave](brief-db-lineage-seminata-per-chiave.md) §8 |

Il padre si archivia quando D-2 e D-3 sono chiuse; il figlio vive per conto suo.

## 7. Archiviazione (2026-10-18)

Chiuso tutto ciò che il brief aveva aperto:

* **D-1** censimento; **D-2** lister dei DDT senza filtri (`20261012-03`); **D-3a** resi col piano
  generico (`20261011-42`); **D-4** pannello «Passaggi» (`20261010-44`); **D-5/D-6** nel brief figlio
  `brief-db-lineage-seminata-per-chiave`.
* **D-3b** il verbo dell'accredito, riga 15922, ~115-120 → **50,6 ms** di mediana (dbdev come app):
  D-3b-1 `segment_base` (`20261018-15`); D-3b-2 il perimetro dell'operatore una volta per istruzione
  in tutte le policy ef_whitelist (`20261018-16…-33`, `-48…-51`; D-3b-2a/b/c/d decise da Tid); D-3b-3
  il `tx_id` sulla connessione di log persistente (`20261018-52`).
* Regole nuove o riscritte: linee-guida-sql §10.3 (il perimetro una volta per istruzione, una
  sottoquery e non due, il risolutore DEFINER, il billing account in convenzione SR) e §10.9.
  Presidio nuovo `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (testo e piano).

**Residuo → brief nuovo** [brief-db-perimetro-una-volta-famiglie-residue](brief-db-perimetro-una-volta-famiglie-residue.md)
(D36 nel registro): le famiglie che restano per riga (cliente portale, cliente, shop, fornitore,
email, note) e tre policy dell'operatore — `fn_scope_note_ef_whitelist` e
`fn_scope_note_magazzino_ef_whitelist`, che il test 5 del presidio non vede (non sono `via_*`), e
`via_coppia`, dichiarata.

**Non è debito, e resta qui come opzione:** il commit asincrono della sessione di log
(`fn_generate_tx_id` 1,46 → 0,32 ms) a prezzo della durabilità del registro `transaction_ids`
(§5sexies). Si decide solo se servisse.

**Lezioni scritte in memoria:** il numero changeSet è il massimo del giorno + 1, cercato su tutti i
livelli (anche `90_end`); l'SQL estratto in un pgTAP si inserisce dopo la **riga** `BEGIN;`, mai dopo
la prima occorrenza (un commento `-- BEGIN; + ROLLBACK` ha fatto girare sei file in autocommit sullo
scratch, §5quinquies).
