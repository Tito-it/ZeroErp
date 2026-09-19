# Brief DB — Osservabilità, tre cose per l'ultimo miglio: il verdetto «lotto fermo» e il suo presidio, R-6, gli indici delle letture trasversali

> **Cos'è.** I prerequisiti DB del piano
> [piano-be-fe-osservabilita-pallino-e-superfici.md](../work-in-progress/piano-be-fe-osservabilita-pallino-e-superfici.md),
> che chiude i residui di [analisi-osservabilita-log.md](../work-in-progress/analisi-osservabilita-log.md)
> dopo il Passo D (18-09). Tre richieste, in ordine di peso:
>
> - **P-1 · il verdetto «lotto fermo» nasce a DB, e da lì il presidio** — è la
>   sorgente che manca al Passo C. Oggi il verdetto vive in Python
>   (`blocks_next_step`): un presidio scritto a DB sarebbe la **seconda sede**
>   dello stesso predicato. Si sposta la sede, non si copia;
> - **P-2 · R-6** — la riga `TASK_RUN` del giornale esce con `quando =
>   COALESCE(ended_at, started_at)`: un task partito il 21 compare col 22.
>   Ancora vero il 18-09 (doc auto-gen);
> - **P-3 · gli indici delle due letture trasversali** — il giornale «per
>   finestra e gravità» e `dbops.error_log` «per area/funzione/codice/tx_id»
>   oggi non hanno un indice da cui partire. È un prerequisito del contratto,
>   non dei volumi di oggi.
>
> **Destinatari:** team DB (`dev/db-tid`). **Chi scrive:** BE/FE
> (`dev/backend-tid`), 2026-09-18.
>
> **Stato:** ~~🔵 scritto il 2026-09-18, in attesa del team DB~~ → ✅ **SCRITTO
> lato DB il 2026-09-19** (§1-bis, §8): sette changeSet `20260919-01 → -07`,
> una riga in `presidi.csv`, un pgTAP nuovo da 21 asserzioni + uno strutturale
> da 10, due pgTAP esistenti riallineati, manuali e guide. Provato con l'SQL
> estratto in transazione con `ROLLBACK` (parità 95/95 con la funzione viva,
> `plpgsql_check` pulito, guardrail statici verdi) e coi pgTAP concatenati
> nella stessa transazione. ✅ **APPLICATO su dbdev da Tid il 19-09 alle 01:34**
> (`databasechangelog`: i sette `EXECUTED`, il mirror dei presidi `RERAN` con
> la riga nuova, `ix_fatturazione_lotti_log_lotto_id` creato dal `90_end`).
> ✅ **pgTAP eseguiti da Tid il 19-09: nessuna regressione.** ✅ **CHIUSO e
> archiviato in `work-done/` il 2026-09-19** (decisione di Tid): la parte DB è
> finita; le consegne BE/FE — V (legge `fermo`), E (`LIKE` con `_` escapato),
> G (`EXPLAIN` sui quattro rami) — stanno in §6 e nel
> [piano BE/FE](../work-in-progress/piano-be-fe-osservabilita-pallino-e-superfici.md),
> che resta in WIP. ⚠️ Finché V non è fatto, il verdetto vive in due posti
> (Python e DB), uguali per costruzione: è la finestra dichiarata in §1-bis.
> Il commit è di Tid.
>
> ⛔ **Niente misure come motivo.** I numeri citati (righe di `error_log`, lotti
> aperti su dev) sono fatti datati per stimare un costo. Nessuna forma dipende
> da essi: un indice si mette perché il contratto dichiara un filtro, non perché
> la tabella è grande.

---

## 0. In una pagina

| # | Cosa | Forma proposta | Verifica | ✅ Consegnato (19-09) |
| --- | --- | --- | --- | --- |
| **P-1** ✅ D-1 | Il verdetto «lotto fermo» a DB + presidio `ZERO` a catalogo *(principio deciso da Tid il 18-09)* | (a) i tre addendi del verdetto in **una** sede a DB, esposti al BE come colonna in coda a `fn_get_lotto_segnalazioni_summary`; (b) `dbops.vw_lotti_fermi_da_guardare` sopra la stessa sede, con soglia; (c) riga in `presidi.csv` | pgTAP coi builder: un caso per addendo, `ESCLUSO` non conta, lotto chiuso non conta, soglia | `20260919-01` la sede `vendite.vw_lotti_segnalazioni_summary` (dieci conteggi + `fermo`, `fermo_motivo`, `fermo_da`, una riga per lotto); `-02` la funzione diventa **lettore** e porta `fermo` undicesima; `-03` il presidio + riga nel CSV. pgTAP `vendite/test-lotti-fermi-verdetto-a-db-v1.sql` (21) |
| **P-2** | R-6: `quando` del `TASK_RUN` | `quando = tr.started_at` in `script.vw_giornale_entita` (`CREATE OR REPLACE` con `security_invoker` **ri-specificato**) | pgTAP: corsa partita il 21 e chiusa il 22 appare al 21; l'ordine della Storia del lotto | `20260919-04`; il test 10 di `script/test-vw-giornale-entita.sql` **riscritto** (pinnava l'`ended_at` come scelta di disegno) |
| **P-3** | Indici per le letture trasversali | giornale: tempo (e gravità) sulle quattro sorgenti; `error_log`: `occurred_at`, `(area, function_name, occurred_at)`, `tx_id` | `EXPLAIN` sulle **due** query di §4 con ogni filtro della whitelist | `20260919-05` quattro indici per tempo; `-06` **quattro** su `error_log` (il composto è stato **spezzato**, §1-bis); `-07` l'indice FK di `fatturazione_lotti_log(lotto_id)`, che mancava. pgTAP `dbops/test-indici-letture-trasversali-v1.sql` (10) |

---

## 1. Cosa dice il modello, verificato (2026-09-18, doc auto-gen + codice)

**Il verdetto.** `vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id)` torna
dieci conteggi; il BE (`LottoSegnalazioniService.evaluate_lotto_status`) ne
prende tre e decide: `is_error = blocks_next_step = (critiche vive > 0) OR
(fatture con stato_esecuzione ERRORE > 0) OR (esiti ERRORE > 0)`. La `COMMENT`
della funzione lo dichiara: *«blocks_next_step resta in Python e non deve
sapere niente di questi tre: sono per la FRASE, non per la decisione»*. Il
banner FE (`scegliRamoBanner`) è totale su quel verdetto. **Il predicato ha una
sede sola, ed è Python.**

**Il catalogo dei presidi.** `dbops.presidi`: `natura` (`ZERO` = deve restare
vuota), `perimetro` (`LIBERO` / `DEFINER` — «questo conteggio è onesto letto da
un programma senza utente?»: su tabelle in RLS è `DEFINER`, e si conta solo
via `dbops.fn_conta_presidio`), `cadenza`, `nota`. Le soglie **stanno nella
vista**, non nel catalogo (manuale `presidi.md` §«Che cosa NON sta qui»). Come
si aggiunge una riga: vista con `COMMENT` + riga nel CSV, e
`test-catalogo-presidi-v1.sql` fa rosso se manca l'una o l'altra. ⚠️ Il seed è
`runOnChange`: appendere ri-propone tutte le righe ai vincoli.
**Nessuna riga del catalogo parla di lotti** (`grep lotti presidi.csv` → 0).

**Le viste sui lotti che esistono.** `vendite.vw_lotti_fase` — sede unica di
«in che fase è questo lotto?», con `pre_fiscale` (si può ancora agire) e
`in_gioco`; `vendite.vw_lotti_chiusi_con_gruppi_in_errore` — la contraddizione
opposta (lotto **chiuso** con documenti in `ERRORE`), invariante «nessuna riga
non dichiarata». Il presidio nuovo guarda il caso **complementare**: un lotto
**pre-fiscale** che è fermo — e nessuno lo rilancia né lo scioglie.

**Il giornale.** `script.vw_giornale_entita`, `security_invoker`, `UNION ALL`
di `event_log` (`event_time`, `severity`), `fatture_log` (`data_ora`,
`status`), `fatturazione_lotti_log` (`data_ora`, `status`),
`fatturazione_lotti_task_runs` (`started_at`/`ended_at`, `task_stato`). Il ramo
`TASK_RUN`: `COALESCE(tr.ended_at, tr.started_at) AS quando` (R-6). Indici per
tempo: su `event_log` `(entity_type, entity_id, event_time)` e
`(correlation_id, event_time)`; sulle altre tre **nessuno** (letto da
`pg_indexes` il 18-09).

**`dbops.error_log`.** `occurred_at`, `area`, `function_name` (`NOT NULL`),
`messaggio_errore_id` → `config.messaggi_errore` (che ha `codice` →
`config.codici_errore`), `context`, `tx_id` (`NOT NULL`), `cleanup_at`. Indici:
pk, `messaggio_errore_id`, `cleanup_at`. `zeroerp_app`: `SELECT` sì, `DELETE`
no (giusto così — la consultazione legge).

---

## 1-bis. Verifica critica delle premesse, e cosa è cambiato scrivendo *(team DB, 2026-09-19)*

Il §1 regge riga per riga (riletto su doc auto-gen, `pg_indexes`, `pg_depend`
e il servizio Python). Quattro cose sono cambiate **scrivendo**, e vanno lette
prima delle forme del §2-§4 perché le correggono.

### ⭐ P-1 — la sede non è la funzione né la vista dei fermi: è una terza cosa

La forma (a) del §2.2 — «`vendite.vw_lotti_fermi` con i tre addendi» accanto a
una funzione che tiene le proprie CTE — avrebbe **spostato il doppione dentro il
database** invece di toglierlo: due sedi per lo stesso predicato, una per il
banner e una per il digest, con la stessa divergenza al primo addendo che D-1
chiude. La forma consegnata:

| Oggetto | Ruolo |
| --- | --- |
| `vendite.vw_lotti_segnalazioni_summary` | **la sede**: i dieci conteggi + `fermo` + `fermo_motivo` + `fermo_da`, una riga per **ogni** lotto, set-based (quattro `GROUP BY lotto_id` in `FROM`, con gli stessi filtri delle CTE). Provata in `ROLLBACK`: 95 lotti su 95 con la stessa riga della funzione viva |
| `vendite.fn_get_lotto_segnalazioni_summary` | **lettore per un lotto** (`WHERE lotto_id = $1`, spinto nelle `GROUP BY` — quattro letture per chiave, come le CTE). Undicesima colonna `fermo`; una riga sempre (zeri e `fermo=false` su lotto inesistente o fuori perimetro, com'era). `DROP + CREATE`: la `RETURNS TABLE` cambia; nessun oggetto dipende dalla funzione |
| `dbops.vw_lotti_fermi_da_guardare` | **lettore del presidio**: la sede ⋈ `vw_lotti_fase` `WHERE fermo AND pre_fiscale AND fermo_da < now() - 1h`. **Nessun addendo ricalcolato** |

⚠️ Ne discende che `fermo` è il verdetto su **ogni** lotto, qualunque sia lo
stato fiscale — un `DEFINITIVA` con un esito `ERRORE` è `fermo` nella sede come
lo era per il Python. La **spartizione** con `vw_lotti_chiusi_con_gruppi_in_errore`
sta nel presidio, non nella sede: una sede risponde a una domanda (pgTAP 17).

* `fermo_motivo`: `CRITICHE` › `FATTURE_IN_ERRORE` › `ESITI_IN_ERRORE`, con la
  precedenza del banner. Vocabolario di tre valori nel `COMMENT` (colonna di
  vista: nessun `CHECK` possibile).
* `fermo_da` = il fatto **più recente** che ferma il lotto, come proposto —
  e l'argomento è sul modello: il presidio chiede «da quanto nessuno lo rilancia
  né lo scioglie», e un rilancio che fallisce scrive un fatto nuovo. Sull'esito
  `errore_quando` con `data_update` a ripiego (il `CHECK` «errore parlante»
  pretende codice o messaggio, non l'orario).
* Il BE riceve la sola colonna `fermo` (undicesima); motivo e orologio restano
  nella vista, dove il presidio li legge. Se un giorno il banner li vorrà, si
  allunga la funzione, non si ricalcola.
* ⚠️ Il messaggio `E_PARAMETRO_INVALIDO` del guard è rimasto com'era (nomina il
  parametro): è il debito #14, non di questo cantiere.

### ⭐ P-2 — accettata, con un argomento più forte di R-6

La ricognizione del 24-08 aveva visto il sintomo; il meccanismo, letto sul
modello: `ended_at` lo scrive `fn_set_runtime_task_run_esito`, che
`fn_start_lotto_task_run` chiama per chiudere `ANNULLATO` il tentativo rimasto
aperto — cioè **la corsa successiva**. Fatto datato (dbdev, 19-09): sui 352
`ANNULLATO` la distanza `ended_at − started_at` ha mediana 15 minuti e massimo
quasi due giorni; su `COMPLETATO`/`ERRORE` è sotto il decimo di secondo.

⭐ L'argomento che decide non è «un task partito il 21 compare col 22»: è che
**l'orario di una riga di diario non deve muoversi dopo che la riga è stata
scritta**. `started_at` si scrive una volta; lo stato mostrato è quello corrente,
e non c'è contraddizione. Il test 10 di `test-vw-giornale-entita.sql` pinnava
l'`ended_at` come «scelta di disegno» (24-08): riscritto (memoria: un test che
pinna il sintomo diventa rosso sulla riparazione). Niente `fino_a`: nessun
lettore la chiede, e una colonna senza lettore è un invito a fidarsene.
Corretta nello stesso giro una frase **stantia** della `COMMENT` («gli altri tre
una policy non ce l'hanno» — falsa dal 10-09).

### ⭐ P-3 — quattro indici su `error_log`, non tre; e uno in più che il brief non vedeva

**Giornale**: quattro indici semplici per tempo, **senza** la variante
`(severity, event_time)`: la gravità ha tre valori e la lettura di default
(`ERROR` + `NULL`) non è un'uguaglianza — il filtro si applica scorrendo il
tempo. Verificato con `EXPLAIN` sulla query di §4.1: `Merge Append` sui quattro
rami con l'indice su `event_log`; sugli altri tre il piano su dev sceglie ancora
il seq scan **per costo** (tabelle da centinaia di righe), non per mancanza di
indice — è la cosa da riguardare dal BE sul DB vero dopo l'apply.

**`error_log`**: il composto `(area, function_name, occurred_at)` è stato
**spezzato** in `(area, occurred_at)` + `(function_name text_pattern_ops,
occurred_at)`, più `(occurred_at)` e `(tx_id)`. Due ragioni sul modello:

1. il composto serve `area` da sola e `area + function_name`, **non**
   `function_name` da sola — che è la domanda del tecnico («quale funzione ha
   sollevato»), e la whitelist di §4.2 la ammette;
2. ⛔ **la collation del database è `it_IT.UTF-8`**: su un btree ordinario
   `LIKE 'x%'` **non usa l'indice** (solo con collation C). Il prefisso vuole
   `text_pattern_ops`, che serve `=` e `LIKE 'x%'` — e **mai `ILIKE`**.

⛔ **E c'è una trappola in più, trovata con `EXPLAIN` il 19-09**: `_` è un
**jolly** di `LIKE`, e i nomi di funzione ne sono pieni. `LIKE 'fn_get_lotto%'`
ha come prefisso fisso solo `fn` e il planner torna al seq scan. Il BE deve
**escapare** il prefisso (`fn\_get\_lotto%`) — che è anche l'unica forma
corretta: senza, `fn_get` combacia con `fnXget`. Consegna BE, §6.

**L'indice che il brief non vedeva**: `vendite.fatturazione_lotti_log` aveva la
**sola PK** — nessun indice su `lotto_id`, la colonna da cui entra ogni lettura
del canale lotto (Storia, riepilogo, presidio). La riga di policy c'era a
`consentito=false` dal 25-01 (script di popolamento, «nessuno ha deciso»): ora
è `true` con la ragione (`20260919-07`, CSV dedicato: la riga non sta in nessun
altro CSV, quindi non è il laterale che la regola del 18-09 vieta). L'indice lo
crea `apply_fk_index_policy()` in `90_end`.

### Fatto datato (dbdev, 19-09, sola lettura da proprietario)

38 lotti `fermo` su 95 (37 `CRITICHE`, 1 `ESITI_IN_ERRORE`); **16** pre-fiscali
fermi da 6 a 91 giorni. Il presidio **nasce pieno** su dev: giri di prova
lasciati a metà. Non si esclude il pregresso per farlo partire verde — ed è il
numero che il pallino mostrerà in rosso il primo giorno.

---

## 2. P-1 — il verdetto «lotto fermo» nasce a DB, e da lì il presidio

### 2.1 ✅ D-1 — La regola «lotto fermo» è una regola del DB *(decisa da Tid, 2026-09-18)*

> **Decisione:** *«la regola va a DB»*. Il predicato «quando un lotto è fermo»
> nasce a database come ogni altra regola di dominio; il backend lo **legge**
> (`fermo`) e non lo ricalcola. I tre conteggi restano, per la frase. Ciò che
> segue è il **perché**, e la forma (§2.2) resta una proposta: la scrittura è
> vostra.

#### Perché la sede si sposta e non si copia

La sorgente che manca al Passo C è «lotto fermo in errore da troppo tempo».
Scriverla come vista sopra i tre addendi è **facile** e **sbagliato**: da quel
giorno il predicato avrebbe due sedi — il Python per il banner e il runner, la
vista per il pannello, il digest e il pallino — e le due divergono **al primo
addendo nuovo**: il D2 del 12-09 (gli esiti `ERRORE`) è stato aggiunto in
Python; la vista non l'avrebbe saputo. Il sintomo non è un errore: è il banner
che dice «fermo» e il digest che dice «tutto a posto». *La classe di difetto che
nessun test vede.*

DB-first (PROJECT_CONTEXT §Filosofia, punto 4: *«se è nel DB non va replicata in
Python, e viceversa»*): la decisione va a DB, il BE la **trasporta**. I tre
conteggi restano dove sono, per la frase.

### 2.2 Forma proposta

**(a) La sede.** Un predicato a DB che risponde «questo lotto è fermo?» sui tre
addendi di oggi — critiche vive (`status = 'C'` e `disabilitato = false`, su `fatture_log`
e `fatturazione_lotti_log` del lotto e delle sue fatture),
`fatturazione_lotti_fatture` con `stato_esecuzione = 'ERRORE'`, `fatturazione_lotti_esiti` il cui **ultimo**
esito per `gruppo_key` è `ERRORE` (con `ESCLUSO` che **non** conta: è la via
d'uscita dichiarata). La forma la scegliete voi; due che tornano:

- **una vista `vendite.vw_lotti_fermi`** (`security_invoker`), una riga per
  lotto **pre-fiscale** (`vw_lotti_fase.pre_fiscale`) con i tre addendi, `fermo
  boolean` e `fermo_da timestamptz` (il più recente fra i fatti che lo fermano:
  `data_ora` della critica, `errore_quando` dell'esito, `data_update` della
  riga `ERRORE`) — la vista è ciò che il presidio (b) legge e ciò che la
  funzione (c) interroga per il proprio lotto;
- oppure una **`fn_check_lotto_fermo(p_lotto_id) → boolean`** più la vista che la
  chiama per i soli pre-fiscali. ⚠️ Una `fn_check_*` è la forma giusta se la
  regola deve anche **accendere o spegnere un pulsante** (AGENTS §Guard vs
  Check): qui non lo fa — il banner legge il verdetto, non un motivo — quindi la
  vista basta, ed è una scansione sola.

⭐ **Un lotto non pre-fiscale non è mai «fermo»** in questo senso: un
`DEFINITIVA` con un esito `ERRORE` è la contraddizione di
`vw_lotti_chiusi_con_gruppi_in_errore`, che c'è già. I due presidi si spartiscono
l'asse `pre_fiscale` senza sovrapporsi.

**(b) Il presidio.** `dbops.vw_lotti_fermi_da_guardare`: le righe di (a) con
`fermo AND fermo_da < now() - interval '1 hour'`, colonne parlanti (`lotto_id`,
`lotto_codice`, `emittente`, `motivo` — quale addendo, con la precedenza del
banner: critiche prima degli esiti —, `da_quanto`). Catalogo: `natura = ZERO`,
`perimetro = DEFINER` (`fatturazione_lotti` è in RLS: senza GUC la vista tornerebbe
zero per cecità — il caso per cui `fn_conta_presidio` esiste), `cadenza =
GIORNALIERA`, nota nel CSV: *«DEVE restare vuota. Una riga è un giro di
fatturazione fermo da più di un'ora che nessuno ha rilanciato né sciolto: il
banner lo dice a chi apre il lotto, questa riga lo dice a chi non lo apre.»*

⚠️ **La soglia di un'ora non viene da una misura**: viene dal fatto che il
rilancio è il gesto di una **persona** e che le tre viste delle code usano la
stessa soglia per la stessa ragione — un lotto fallito due minuti fa e già in
rilancio non è un allarme. Se la trovate sbagliata, cambiatela: sta **nella
vista**, come da manuale.

**(c) Il BE legge il verdetto.** Colonna **in coda** a
`fn_get_lotto_segnalazioni_summary`: `fermo boolean` (undicesima — il BE legge la
riga **per posizione**, come la `COMMENT` avverte; il BE allunga il proprio
`TypedDict` nello stesso giro). La `COMMENT` va riscritta: *«blocks_next_step
nasce QUI dal 2026-09-xx; i tre conteggi restano per la frase»*.

### 2.3 Che cosa deve provare il pgTAP *(coi builder, mai iterando sull'esistente)*

Su un lotto pre-fiscale costruito dal test (`dbops.fn_pgtap_crea_emittente_operatore`,
`script.fn_pgtap_registro_fattura` — i builder del 18-09 di Passo D):

1. critica viva su una fattura del lotto → `fermo`; ritirata → non `fermo`;
2. nessuna critica, una riga di `fatturazione_lotti_fatture` in `ERRORE` → `fermo`;
3. nessuna critica, ultimo esito `ERRORE` per un `gruppo_key` → `fermo`; lo
   stesso gruppo con un esito successivo `COMPLETATO` → non `fermo`; con
   `ESCLUSO` → non `fermo`;
4. stesso stato di 1 ma lotto `DEFINITIVA` → **non** in `vw_lotti_fermi`
   (spartizione con `vw_lotti_chiusi_con_gruppi_in_errore`);
5. `fermo` da meno di un'ora → non in `_da_guardare`; `fermo_da` spostato
   indietro di due ore → una riga;
6. `fn_conta_presidio('dbops.vw_lotti_fermi_da_guardare')` da una sessione
   **senza GUC** conta la riga (perimetro `DEFINER` onesto);
7. `test-catalogo-presidi-v1.sql` verde con la riga nuova (e rosso senza: è il
   verso che si vuole).

Preambolo obbligatorio (`BEGIN`, contesto, `SET CONSTRAINTS ALL IMMEDIATE`);
`throws_*` sempre con SQLSTATE.

---

## 3. P-2 — R-6: la riga `TASK_RUN` dice quando è nata

**Il difetto.** `quando = COALESCE(tr.ended_at, tr.started_at)`: la riga del
giornale è **la corsa**, e la corsa nasce a `started_at`; `ended_at` è un
secondo fatto, e la ricognizione del 24-08 ha visto che può essere scritto dalla
corsa **successiva** — un task partito il 21 compare col 22, in mezzo a righe del
22, e la Storia del lotto racconta un ordine che non è successo.

**Proposta.** `quando = tr.started_at`. Un changeSet `20_code/script` di
`CREATE OR REPLACE VIEW script.vw_giornale_entita WITH (security_invoker=true)`
— ⚠️ **ri-specificata**, o PostgreSQL la azzera (doc auto-gen della vista lo
ricorda in testa) — con il corpo preso dalla doc auto-gen, non dallo YAML.
`ended_at` non si perde: se serve al lettore, è una colonna in più della vista
(`fino_a`), non l'orario della riga.

**pgTAP.** Una corsa costruita con `started_at = 21` e `ended_at = 22`, un evento
del 21 sera sulla stessa entità: nella vista la corsa **precede** l'evento.

**Effetto sul BE/FE:** nessun contratto cambia (la colonna si chiama sempre
`quando`); l'ordine della Storia del lotto migliora da solo.

---

## 4. P-3 — gli indici delle due letture trasversali

> ⛔ Il motivo non è il volume: è che il BE dichiarerà una **whitelist di filtri**
> (piano §3.1 e §4.1) e *ciò che il contratto dichiara ammesso va provato per
> intero* — un filtro senza indice è un 500 differito, non una lista lenta.
> I volumi di oggi (fatto datato, 18-09: ~116k righe in `error_log`) servono solo
> a dire che il caso è già osservabile con `EXPLAIN`.

### 4.1 Il giornale per finestra e gravità

La query che il BE scriverà (terzo lettore di `_list_giornale`, senza entità):

```sql
SELECT g.*
  FROM script.vw_giornale_entita g
 WHERE g.quando >= :data_da AND g.quando < :data_a_escl
   AND (g.gravita = ANY(:gravita) OR (:include_null AND g.gravita IS NULL))
   AND (:registro IS NULL OR g.registro = :registro)
   AND (:entity_type IS NULL OR g.entity_type = :entity_type)
   AND (:tx_id IS NULL OR g.tx_id = :tx_id)
   AND (:correlation_id IS NULL OR g.correlation_id = :correlation_id)
   AND (NOT :solo_vive OR g.disabilitato IS DISTINCT FROM true)
 ORDER BY g.quando DESC, g.riga_id DESC
 LIMIT :n OFFSET :o;
```

Proposta di partenza, **da confermare con `EXPLAIN (ANALYZE, BUFFERS)` sul DB
vero e sotto RLS** (con GUC operatore: il piano cambia con la policy):

| Tabella | Indice | Perché |
| --- | --- | --- |
| `vendite.event_log` | `(event_time DESC)` — o `(severity, event_time DESC)` se il piano lo preferisce | oggi solo per entità e per filo |
| `vendite.fatture_log` | `(data_ora DESC)` | nessuno per tempo |
| `vendite.fatturazione_lotti_log` | `(data_ora DESC)` | idem |
| `vendite.fatturazione_lotti_task_runs` | `(started_at DESC)` | idem, e dopo P-2 è la colonna di `quando` |

⚠️ È un `UNION ALL` con `ORDER BY … LIMIT` sopra: PostgreSQL può fare un
`Merge Append` sui quattro rami **solo** se ciascuno ha un indice sull'ordine
richiesto; senza, ordina tutto. È la cosa da guardare nel piano. Se le policy
RLS impediscono il `Merge Append`, ditelo nel registro: il BE può allora
leggere per registro e cucire — ma è una forma peggiore, e va decisa sapendo.

### 4.2 `error_log` per area / funzione / codice / tx_id

```sql
SELECT e.id, e.occurred_at, e.area, e.function_name, m.codice, m.messaggio,
       m.causa, m.soluzione, e.context, e.tx_id
  FROM dbops.error_log e
  JOIN config.messaggi_errore m ON m.id = e.messaggio_errore_id
 WHERE e.occurred_at >= :data_da AND e.occurred_at < :data_a_escl
   AND (:area IS NULL OR e.area = :area)
   AND (:function_name IS NULL OR e.function_name LIKE :function_name || '%')
   AND (:codice IS NULL OR m.codice = :codice)
   AND (:tx_id IS NULL OR e.tx_id = :tx_id)
 ORDER BY e.occurred_at DESC, e.id DESC
 LIMIT :n OFFSET :o;
```

| Indice | Serve a |
| --- | --- |
| `ix_error_log_occurred_at` `(occurred_at DESC)` | la finestra, che è il filtro sempre presente |
| `ix_error_log_area_function_occurred_at` `(area, function_name, occurred_at DESC)` | i due filtri di dominio insieme e separati (prefisso) |
| `ix_error_log_tx_id` `(tx_id)` | il ponte dal giornale (`tx_id` esatto) |

⚠️ `codice` sta sul catalogo, non sul log: il filtro per codice passa
dall'indice già esistente su `messaggio_errore_id` **se** il BE risolve prima
`codice → id` (una lingua per codice: `uq_messaggi_errore_codice_lingua`). Lo
farà così; non serve un indice su `error_log` per questo.

Naming secondo `linee-guida-sql` (`ix_<table>_<column>`); **non** sono FK index,
quindi fuori da `fk_index_policy`. Dove metterli (`00_schema`) e con quale
`preCondition` (`indexExists` → `MARK_RAN`) lo decidete voi.

---

## 5. Cosa NON cambia, e va tenuto fermo

- Il catalogo dei presidi, `fn_conta_presidio`, il digest, il guardiano: la riga
  nuova **entra** in un meccanismo che non si tocca.
- I due endpoint della Storia (`/fatture/<id>/giornale/`, `/lotti/<id>/giornale/`)
  e il loro contratto: P-2 cambia un valore, non una colonna.
- La retention (Passo D): `cleanup_at` e i trigger alla nascita restano; gli
  indici nuovi non li riguardano.
- I tre conteggi del riepilogo lotto: restano, per la frase del banner.

---

## 6. Cosa fa il BE/FE dopo l'apply

Piano completo in
[piano-be-fe-osservabilita-pallino-e-superfici.md](../work-in-progress/piano-be-fe-osservabilita-pallino-e-superfici.md).
⏱️ *19-09, dal team DB* — le consegne, precise:

| Pezzo | Cosa cambia per il BE |
| --- | --- |
| **V** | `fn_get_lotto_segnalazioni_summary` ha l'**undicesima** colonna `fermo boolean`, in coda; la `SELECT` di `pipeline_repository.get_lotto_segnalazioni_summary` la nomina e il `TypedDict` si allunga. `is_error = blocks_next_step = fermo`. I dieci conteggi non cambiano di posto. Su lotto fuori perimetro: zeri e `fermo=false`, com'era. ⚠️ La sede è `vendite.vw_lotti_segnalazioni_summary`: se il banner un giorno vorrà `fermo_motivo`/`fermo_da`, si allunga la funzione — non si ricalcolano |
| **E** | Filtro `function_name` **a prefisso con `LIKE`, non `ILIKE`** (l'indice è `text_pattern_ops`; i nomi sono minuscoli per convenzione — 8 righe su 146k con una maiuscola, chiamanti Python con un nome di classe). ⛔ **Escapare `_` e `%`** nel prefisso (`replace('_', '\\_')`): senza, il prefisso fisso è `fn` e la lettura scandisce la tabella. `area` esatto, `tx_id` esatto, `codice` risolto prima a `messaggio_errore_id`. `EXPLAIN` su ogni filtro dopo l'apply |
| **G** | Nessun cambio di contratto: `quando` del `TASK_RUN` è `started_at`. `EXPLAIN` sulla query di §4.1 dopo l'apply: `Merge Append` con i quattro indici per tempo — se un ramo scandisce, si dice qui nel registro |
| **P** | Il presidio compare da solo nel pannello, nel digest e nel pallino: perimetro `DEFINER`, quindi **niente `prime_righe`** (come le altre sette `DEFINER`); il numero sì |

---

## 8. Consegna DB (19-09)

| File | Cosa |
| --- | --- |
| `20_code/vendite/20260919-01-create-vw-lotti-segnalazioni-summary-sede-del-verdetto` | la sede (`security_invoker`, GRANT app) |
| `20_code/vendite/20260919-02-update-fn-get-lotto-segnalazioni-summary-legge-la-sede-e-porta-fermo` | `DROP + CREATE`, undici colonne, `COMMENT` riscritta (non dice più «blocks_next_step resta in Python») |
| `20_code/dbops/20260919-03-create-vw-lotti-fermi-da-guardare` | il presidio; `80_data/sql/dbops/presidi.csv` +1 riga (`ZERO`, `DEFINER`, `GIORNALIERA`) — il mirror `20260910-08` è `runOnChange` |
| `20_code/script/20260919-04-update-vw-giornale-entita-task-run-quando-started-at` | R-6; `security_invoker` ri-specificato; `COMMENT` corretta |
| `00_schema/vendite/20260919-05-create-ix-registri-giornale-per-tempo` | `ix_event_log_event_time`, `ix_fatture_log_data_ora`, `ix_fatturazione_lotti_log_data_ora`, `ix_fatturazione_lotti_task_runs_started_at` |
| `00_schema/dbops/20260919-06-create-ix-error-log-letture-per-area-funzione-tx` | `ix_error_log_occurred_at`, `_area_occurred_at`, `_function_name_occurred_at` (`text_pattern_ops`), `_tx_id` |
| `80_data/changelog/20260919-07-upsert-fk-index-policy-lotti-log-lotto` + `sql/vendite/fk_index_policy_lotti_log.csv` | `fk_fatturazione_lotti_log_lotto` → `consentito=true` |
| pgTAP | **nuovi** `vendite/test-lotti-fermi-verdetto-a-db-v1.sql` (21), `dbops/test-indici-letture-trasversali-v1.sql` (10); **riallineati** `vendite/test-lotto-segnalazioni-summary-v2.sql` (test 7: l'ultima è `fermo`), `script/test-vw-giornale-entita.sql` (test 10: `started_at`) |
| Doc manuale | `vendite/manual/vw_lotti_segnalazioni_summary.md` (nuovo), `vendite/manual/fn_get_lotto_segnalazioni_summary.md`, `dbops/manual/vw_lotti_fermi_da_guardare.md` (nuovo), `dbops/manual/error_log.md` (§indici + le due trappole del `LIKE`), `script/manual/vw_giornale_entita.md` (R-6, quarta scelta); guide: `processi-automatici-classe-e-identita.md` (tabella dei presidi), `Messaggi-di-Errore-e-Generazione-Log.md` (mappa dei registri) |

⚠️ Dopo l'apply: la doc auto-gen (`gen_db_docs`) e il `COMMENT` vivo diranno
la stessa cosa dei manuali; `test-catalogo-presidi-v1.sql` (runner `owner`,
dal server DB) ha una riga in più da riconoscere.

---

## 7. Registro

| Quando | Cosa |
| --- | --- |
| 2026-09-18 | Scritto dal BE/FE. Tre richieste; forme proposte, nessun changeSet. In attesa del team DB. |
| 2026-09-18 sera | ✅ **D-1 decisa da Tid** («la regola va a DB»): la sede del verdetto «lotto fermo» è il database, il BE trasporta. La forma di §2.2 resta da scegliere al team DB. |
| 2026-09-19 | ✅ **Scritto lato DB** (§1-bis, §8). P-1: sede unica `vendite.vw_lotti_segnalazioni_summary` (non la funzione, non `vw_lotti_fermi`: una vista dei tre addendi accanto alle CTE sarebbe stata il doppione **dentro** il DB), funzione lettrice con `fermo` undicesima, presidio lettore + riga a catalogo. P-2: accettata; argomento più forte (l'orario di una riga di diario non si muove), test 10 riscritto. P-3: quattro indici per tempo sul giornale; su `error_log` **quattro** e non tre — composto spezzato per `function_name` da sola e per la collation `it_IT` (`text_pattern_ops`); trovata la trappola del `_` jolly (consegna BE: escapare); acceso l'indice FK di `fatturazione_lotti_log(lotto_id)`, che mancava. Provato con l'SQL estratto in `ROLLBACK` + pgTAP concatenati (21 nuove: 19 ok come owner, la 18 verde solo come app perché prova la cecità RLS, la 21 provata a parte perché il `CREATE INDEX` su `error_log` nella stessa transazione impicca il dblink di `fn_log_and_raise_error`). Fatto datato: il presidio nasce con 16 righe su dev. ✅ **Applicato da Tid alle 01:34** (sette `EXECUTED`, catalogo e indice FK a posto). |
| 2026-09-19 | ✅ **pgTAP eseguiti da Tid: nessuna regressione** (i due nuovi, i due riallineati, la suite). **Lato DB chiuso**: P-1, P-2, P-3 consegnati e applicati. Passa al BE per V (legge `fermo`), E (`LIKE` con `_` escapato) e G (`EXPLAIN` sui quattro rami). **Archiviato in `work-done/`** lo stesso giorno, su decisione di Tid. |
