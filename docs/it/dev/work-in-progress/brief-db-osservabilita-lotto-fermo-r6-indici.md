# Brief DB — Osservabilità, tre cose per l'ultimo miglio: il verdetto «lotto fermo» e il suo presidio, R-6, gli indici delle letture trasversali

> **Cos'è.** I prerequisiti DB del piano
> [piano-be-fe-osservabilita-pallino-e-superfici.md](piano-be-fe-osservabilita-pallino-e-superfici.md),
> che chiude i residui di [analisi-osservabilita-log.md](analisi-osservabilita-log.md)
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
> **Stato:** 🔵 **scritto il 2026-09-18, in attesa del team DB.** BE e FE
> **attendono** P-1 (per V), P-2 e P-3 (per G ed E); il pezzo P del piano non
> dipende da qui. Nessun changeSet scritto: le forme qui sotto sono **proposte**,
> la scrittura è vostra.
>
> ⛔ **Niente misure come motivo.** I numeri citati (righe di `error_log`, lotti
> aperti su dev) sono fatti datati per stimare un costo. Nessuna forma dipende
> da essi: un indice si mette perché il contratto dichiara un filtro, non perché
> la tabella è grande.

---

## 0. In una pagina

| # | Cosa | Forma proposta | Verifica |
| --- | --- | --- | --- |
| **P-1** ✅ D-1 | Il verdetto «lotto fermo» a DB + presidio `ZERO` a catalogo *(principio deciso da Tid il 18-09)* | (a) i tre addendi del verdetto in **una** sede a DB, esposti al BE come colonna in coda a `fn_get_lotto_segnalazioni_summary`; (b) `dbops.vw_lotti_fermi_da_guardare` sopra la stessa sede, con soglia; (c) riga in `presidi.csv` | pgTAP coi builder: un caso per addendo, `ESCLUSO` non conta, lotto chiuso non conta, soglia |
| **P-2** | R-6: `quando` del `TASK_RUN` | `quando = tr.started_at` in `script.vw_giornale_entita` (`CREATE OR REPLACE` con `security_invoker` **ri-specificato**) | pgTAP: corsa partita il 21 e chiusa il 22 appare al 21; l'ordine della Storia del lotto |
| **P-3** | Indici per le letture trasversali | giornale: tempo (e gravità) sulle quattro sorgenti; `error_log`: `occurred_at`, `(area, function_name, occurred_at)`, `tx_id` | `EXPLAIN` sulle **due** query di §4 con ogni filtro della whitelist |

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

## 6. Cosa fa il BE/FE dopo l'apply (rimando)

Piano completo in
[piano-be-fe-osservabilita-pallino-e-superfici.md](piano-be-fe-osservabilita-pallino-e-superfici.md):
**V** (§5 là) legge `fermo`; **G** (§3) e **E** (§4) partono a indici applicati,
con `EXPLAIN` su ogni filtro prima di consegnare; **P** (§2) non dipende da qui.

---

## 7. Registro

| Quando | Cosa |
| --- | --- |
| 2026-09-18 | Scritto dal BE/FE. Tre richieste; forme proposte, nessun changeSet. In attesa del team DB. |
| 2026-09-18 sera | ✅ **D-1 decisa da Tid** («la regola va a DB»): la sede del verdetto «lotto fermo» è il database, il BE trasporta. La forma di §2.2 resta da scegliere al team DB. |
