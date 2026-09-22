# Brief DB — La partita di merce per documento (D14, quarta leva) e la capability a una lettura (seconda leva)

> **Da leggere per primo: §2 — la chiusura di un documento, sul modello — e
> poi §2-bis, la rilettura che corregge quattro cose di §2.1 e §3.**
> Origine: [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> §3 D14, aperta il 2026-09-17. Le prime tre leve sono chiuse e applicate
> (`20260917-01` il 17-09; `20260921-20` il 21-09 alle 12:41 — fino al
> pomeriggio questa riga lo dava «da applicare»): abbassano la **costante**.
> Questo brief è per ciò che resta, e che dà il titolo a D14: *la capability
> di UN DDT paga le partite di TUTTI i DDT*.
>
> ✅ **Stato 2026-09-21: D1–D5 decise da Tid (§6); giro 1 APPLICATO alle
> 14:46 (`20260921-21 → -25`, `EXECUTED`), pgTAP di Tid senza regressioni,
> doc auto-gen rigenerata, committato (`c60f39eaa`, PR #1634).** Misura «dopo»
> come app in §8.6: la partita di UN DDT costa **24 ms** contro i ~120 della
> vista filtrata; capability 290 → **175 ms**.
> ✅ **Giro 2 (D3) APPLICATO da Tid il 21-09 alle 18:43** (`20260921-26 → -31`,
> `EXECUTED`; pgTAP verdi, i due presidi nuovi 12/12 come app) — §9: due
> funzioni `BEGIN ATOMIC` (`fn_situazione_merce_ordine`,
> `fn_resi_da_accreditare`), le due viste come proiezioni, i due verbi dei
> resi sul seme del DDT. Misura come app in §9.7: situazione per ordine
> **187 → 20 ms**, coda per DDT **115 → 36**, il guard dei tetti **→ 1.3**.
> ✅ Committato con la doc auto-gen (`559dbf351`, PR #1635).
> ⚠️ Il censimento dal catalogo ha corretto il brief: i lettori per riga
> erano DUE, non sei (§9.1). Una decisione nuova, **D6** (§6): `vw_contatore_merce`
> non ha più lettori. Richieste BE in §8.4 e §9.4.
> ✅ **Giro 3 (D4, forma B2) APPLICATO da Tid il 21-09 sera, pgTAP senza
> regressioni** — §10, da leggere per primo se si riprende da qui:
> `20260921-32` (la diagnosi rigenerata `BEGIN ATOMIC`, fonte unica, quattro
> colonne in più, seme in `UNION ALL`), `-33` (il lister DERIVA dalla
> diagnosi), `-34` (la capability legge una volta);
> `test-fn-available-actions-ddt-reason-catch-all-v1` riscritto a casi
> costruiti coi builder (8 → 16). Doc auto-gen rigenerata. Misura come app in
> §10.7: capability del DDT **175 → 50 ms**. ⚠️ **E una regressione, sul
> modello, non sui numeri**: il lister SENZA documento (cockpit, lista push)
> **214 → 663 ms**, perché la diagnosi classifica il segmento di OGNI riga e
> il classificatore è una scansione di `commesse_attivita` sotto policy per
> riga — è il pavimento di D5, che ora ha la priorità e un perimetro in più
> (§10.7, **D8**). ⏳ Da committare. Decisioni aperte: D6, D7, D8.

---

## 1. Il difetto, sul modello

`vendite.vw_partite_merce` è **la** sede del conto della merce — una riga per
riga di DDT, read-time, nessun campo memorizzato. È una vista, quindi non ha
un parametro: chi ne vuole una riga la legge intera. Le CTE che la compongono
sono finestre e insiemi sulla **popolazione** (`alloc` è una `sum() OVER
(PARTITION BY ordine_riga_id …)`, `migra` una finestra per `ddt_riga_origine`,
`sospetto` e `articoli_ordinati_per_ddt` sono `MATERIALIZED`), quindi un
`WHERE ddt_id = x` messo fuori **non entra**: il planner calcola tutto e
scarta. È strutturale, non un caso del planner, ed è scritto nel registro dal
17-09.

Chi la legge **per documento** — ed è la lettura che conta, perché è quella
del drawer:

| Lettore | Filtro | Come la raggiunge |
| --- | --- | --- |
| `script.fn_available_actions_ddt` | un DDT | **due volte**: `fn_list_ddt_da_pushare(p_ddt_id)` e `fn_ddt_push_diagnosi(p_ddt_id)`, entrambe in `JOIN` con la vista |
| BE `list_partite_merce` (pannello «Situazione merce», livello 2) | un DDT **o** un ordine | `SELECT … FROM vw_partite_merce WHERE …` |
| BE `list_situazione_merce_ordine` (livello 1) | un ordine | `vw_situazione_merce_ordine`, che aggrega la vista per riga d'ordine |
| `fn_accredita_riga_reso`, `fn_resi_riga_accreditato_partita`, `fn_resi_riga_tetti_accredito`, `fn_chiudi_riconsegna_reso`, `fn_ordine_riga_qta_riconsegna`, `fn_check_accredito_annullabile` | una riga | `vw_contatore_merce` o la vista, per una partita sola |

⛔ Il modello **non ha retention** sui documenti: le partite crescono con la
storia, e con loro il costo di *ogni* apertura di drawer, di ogni accredito
di riga, di ogni pgTAP che itera i DDT. Non è un difetto che si vede a 51
DDT — si vede a cinquantamila, e il modello li ammette.

**Fatti datati** (dbdev, 2026-09-21, 51 DDT / 36 partite, `zeroerp_app` con
contesto operatore; colore, non motivo): vista intera ~90–130 ms, filtrata su
un DDT ~120 ms (uguale: il filtro non entra), `fn_list_ddt_da_pushare(id)`
112 ms, `fn_ddt_push_diagnosi(id)` 93 ms, capability ~290 ms. Con
`20260921-20` la vista scende a ~56 ms, ma resta O(tutti).

## 2. La chiusura di un documento — sul modello, non sui dati

La partita di una riga `r` non dipende da *tutte* le altre: dipende da un
insieme **bounded e nominabile**, e lo dicono le chiavi delle finestre e dei
join della vista stessa. CTE per CTE, cosa legge la riga `r`:

| CTE | Di cosa ha bisogno per `r` | Chiave che delimita |
| --- | --- | --- |
| `riga` (`consegnato`, `in_riconsegna`, `e_riconsegna`, `quota_nuova`) | `ponte(r)`, `migra_origine(r)`, `migra_nuova(r)` | — |
| `ponte` / `ponte_riga` | le **ri-consegne di cui `r` è origine** (quantità, stato emesso, data) | `ddt_riga_origine = r` |
| `acc_origine` | le rettifiche sul segmento DDT di `r` | `riga_id = r` |
| `migra` (finestra) | **tutte le ri-consegne della stessa origine**, ordinate per data: se `r` è una riga nuova, serve la sua origine `o` e le **sorelle** (le altre nuove di `o`) | `PARTITION BY ddt_riga_origine` |
| `orig` | i fulfillment di `r` | `ddt_riga_id = r` |
| `alloc` (finestra) | il `consegnato` di **tutte le righe non-riconsegna della stessa riga d'ordine** (`min(ordine_riga_id)` da `orig`), ordinate per data — cioè la greedy oldest-first | `PARTITION BY ordine_riga_id` |
| `articoli_ordinati_per_ddt`, `sospetto` | le righe **dello stesso DDT** e i loro ordini | `ddt_id` |
| `res` | i resi di `r` | `ddt_riga_id = r` |
| `af` (`fd`, `fr`, `fo`) | il contatore per la riga `r` e per la sua riga d'ordine | `riga_id` |

Ne discende la **chiusura** di un insieme di documenti `X` (DDT), a due salti:

1. **R0** = le righe attive di `X` (su documento `EMESSO`+, non abortito —
   il perimetro di `riga`);
2. **R1** = le righe (stesso perimetro) che condividono con una riga di R0 la
   riga d'ordine di `orig` (`min(ordine_riga_id)`). È una relazione di
   equivalenza: la partizione di `alloc` di una riga di R0 è **tutta** in
   R0 ∪ R1, e la partizione di una riga di R1 è la stessa;
3. **O** = (R0 ∪ R1) ∪ le **origini** di ri-consegna delle righe di R0 ∪ R1.
   `ponte_riga` si restringe a `ddt_riga_origine ∈ O`: per ogni origine
   restano **tutte** le sue nuove, quindi la finestra di `migra` è intera;
   `acc_origine` segue `ponte_riga`;
4. `riga` = R0 ∪ R1; `orig` sulle stesse righe; `articoli_ordinati_per_ddt` e
   `sospetto` su `ddt_id ∈ X`; `res` e `af` restano come sono (per riga: il
   costo di `af` è una scansione di `attivita_fatturabili` che nessun filtro
   per riga evita — è il pavimento, ~15 ms oggi);
5. l'output è `riga` filtrata a `ddt_id ∈ X`.

⭐ **Equivalenza per costruzione**: ogni colonna di una riga di R0 è funzione
delle sole righe di CTE elencate nella tabella, e la chiusura le conserva
tutte — la prova è la chiave di partizione di ciascuna finestra, non un
confronto sui dati. ⚠️ **E la regola che ne discende va scritta in testa alla
funzione**: *chi aggiunge alla vista una finestra o un insieme con una chiave
nuova (per articolo, per cliente, per commessa) deve allargare la chiusura*.
Un pgTAP la pinna costruendo i casi (§3), non contando le righe di oggi.

Vale identico per una chiusura **per ordine** (R0 = le righe che evadono le
righe di quell'ordine) e **per riga** (R0 = quella riga): è lo stesso
algoritmo con un seme diverso.

### 2.1 La forma — una funzione, e la vista ne è la proiezione senza filtro

`vendite.fn_partite_merce(p_ddt_ids bigint[] DEFAULT NULL, p_ordine_ids bigint[]
DEFAULT NULL)` → `RETURNS TABLE` con le **23 colonne** del contratto della vista,
`LANGUAGE sql STABLE`, invoker (la RLS resta di chi legge, come oggi con
`security_invoker=on`). Semi: R0 = righe di `p_ddt_ids` ∪ righe che evadono
`p_ordine_ids`; **entrambi `NULL` = tutte** (nessuna chiusura, la vista di
oggi). Il corpo è **uno**: la vista diventa

```sql
CREATE OR REPLACE VIEW vendite.vw_partite_merce WITH (security_invoker=on) AS
SELECT * FROM vendite.fn_partite_merce(NULL, NULL);
```

> ⚠️ **Il blocco qui sopra è superato in tre punti dalla rilettura del 21-09
> pomeriggio (§2-bis)**, e resta per la storia della decisione: il corpo va
> scritto **`BEGIN ATOMIC`** e non come stringa (§2-bis.3); la vista **non è
> `SELECT *`** — proietta le 23 colonne e casta `consegnato::numeric(18,6)`,
> altrimenti perde la scala in silenzio (§2-bis.1); il predicato `p IS NULL
> OR …` **non si scrive**: i due rami vanno in `UNION ALL` (§2-bis.2).

⛔ Non due corpi (vista e funzione): sarebbero due implementazioni della regola
che dosa la fatturazione, l'errore già corretto il 18-08 sulla diagnosi.
⚠️ Le CTE della chiusura (i semi, R1, O) vanno `MATERIALIZED` come `sospetto`:
il predicato `p IS NULL OR …` si valuta **una volta** lì e non viene spinto
riga per riga (memoria: la forma `p IS NULL OR col = ANY(p)` non si piega in
`LATERAL` — qui la funzione sta in `FROM`, con un letterale, e va comunque
provata con `EXPLAIN` come app). ⚠️ *Provata*: non regge (§2-bis.2). Il
`MATERIALIZED` sui semi resta giusto; è l'`OR` dentro il seme che va spezzato.
⚠️ Le tre viste a valle (`vw_contatore_merce`, `vw_resi_da_accreditare`,
`vw_situazione_merce_ordine`) dipendono dalla vista per `pg_depend`: il
`CREATE OR REPLACE` che ne cambia il corpo senza cambiare le colonne **passa**;
se la funzione nascesse con una colonna in più, sarebbero `DROP` a cascata —
non serve, e non si fa.

### 2.2 Chi passa alla funzione

| Lettore | Chiamata | Note |
| --- | --- | --- |
| `fn_list_ddt_da_pushare(p_ddt_id)` | `fn_partite_merce(CASE WHEN p_ddt_id IS NULL THEN NULL ELSE ARRAY[p_ddt_id] END)` | il ramo `NULL` (lista push, cockpit) resta intero, com'è giusto |
| `fn_ddt_push_diagnosi(p_ddt_id)` | idem | |
| BE `list_partite_merce` | per DDT → `ARRAY[%s]`, per ordine → `(NULL, ARRAY[%s])` | una riga di SQL nel repository, contratto della risposta invariato |
| `vw_situazione_merce_ordine` | ~~resta vista~~ → ✅ giro 2: proiezione di `fn_situazione_merce_ordine(p_ddt_ids, p_ordine_ids)` | l'aggregato per riga d'ordine è letto da `list_situazione_merce_ordine` per ordine **e per DDT**; è la stessa mossa un livello sopra — **decisione D3** |
| ~~le sei funzioni per riga di reso~~ → **due** (`fn_accredita_riga_reso`, `fn_resi_riga_tetti_accredito`), entrambe via `vw_resi_da_accreditare` | ✅ giro 2: `fn_resi_da_accreditare(ARRAY[ddt della riga resa], NULL)` | **decisione D3**. ⚠️ Censimento dal catalogo (§9.1): le altre quattro nominano le viste solo nei commenti, `fn_check_accredito_annullabile` non le tocca |

### 2.3 La seconda leva — la capability a una lettura

Oggi `fn_available_actions_ddt` legge la vista **due volte**: `push_ok` dal
lister (`EXISTS (fn_list_ddt_da_pushare(p_ddt_id))`) e il motivo dalla
diagnosi. Più due `EXISTS` su `fn_get_stato_push_segment` per riga per i rami
`DDT_GIA_INVIATO`/`DDT_GIA_FATTURATO`. La diagnosi risponde già a tutto:
`motivo IS NULL` = eleggibile (equivalenza col lister pinnata dal test 1 di
`test-fn-available-actions-ddt-reason-catch-all-v1`), e in `cand` calcola già
il `segment` — poi lo **butta via** collassandolo in `DDT_ROUTED` (rank 4).

Due cose la rendono una decisione e non una riga:

* **Il contratto di api.md**: *il flag lo produce la STESSA funzione che il
  database usa per agire*. Il push è alimentato dal lister; `push_ok` dal
  lister è vero **per costruzione**, dalla diagnosi è vero **per pgTAP**. ⚠️
  E quel pgTAP (test 1) oggi confronta le **righe vive** — verde per
  sottrazione su un database da zero; i test 2–6 costruiscono i casi di
  motivo, non quello di eleggibilità. Se si sceglie la diagnosi, il test 1 va
  affiancato da un caso **costruito** eleggibile (un DDT `CONSEGNATO` con BA e
  causale fatturabile, differenza > 0, segmento `LIBERA`) confrontato nei due
  versi.
* **La precedenza**: i rami `GIA_INVIATO`/`GIA_FATTURATO` vengono oggi
  **prima** di tutto (un DDT annullato con una riga `ALLOCATA` dice «già
  inviato»); nella diagnosi `DDT_ROUTED` è rank 4, dietro annullato /
  solo-trasporto / senza-BA. Per non cambiare comportamento la diagnosi deve
  **esporre il `segment`** come colonna, e la capability leggere così: esiste
  `motivo IS NULL` → ok; altrimenti esiste `segment = 'ALLOCATA'` → GIA_INVIATO;
  `'EMESSA'` → GIA_FATTURATO; altrimenti `min(rank)` come oggi. Una colonna in
  più su un `RETURNS TABLE` è `DROP FUNCTION` + rigenera (memoria: `CREATE OR
  REPLACE` non cambia `RETURNS TABLE`), con i pgTAP da censire (i due di
  `script/`) e il COMMENT che dichiara la colonna nuova.

⭐ **Raccomandazione: prima la quarta leva, poi si misura, poi si decide la
seconda.** Con la chiusura ogni lettura costa O(chiusura), e leggere due volte
un insieme piccolo non è più il problema; la seconda leva resta una questione
di **contratto** (una fonte per flag e motivo), non di tempo. Se si fa, si fa
nella forma B1 (segment esposto, precedenza invariata) — mai «`push_ok` dalla
diagnosi e il resto com'è», che cambia comportamento sui DDT annullati con
righe instradate.

## 2-bis. Rilettura critica (21-09 pomeriggio) — cosa §2 dava per scontato

Prove fatte su dbdev in `BEGIN … ROLLBACK` come owner: catalogo, piani e
oggetti temporanei; nessun dato scritto, nessun changeSet applicato. Sono
tutte **strutturali** (forma di un piano, contratto di una vista, catalogo),
non misure di popolazione.

1. **`SELECT *` dalla funzione perde la scala di `consegnato`.** La vista ha
   `consegnato numeric(18,6)` (cast esplicito nella CTE `riga`). Un `RETURNS
   TABLE(consegnato numeric(18,6))` viene registrato come **`numeric`**:
   `pg_get_function_result` stampa `TABLE(x numeric, …)`, il typmod cade. E
   `CREATE OR REPLACE VIEW … AS SELECT * FROM fn()` **passa** — PostgreSQL
   ammette di *perdere* un typmod — quindi la vista cambierebbe contratto in
   silenzio; il ritorno con il cast esplicito viene poi **rifiutato** («non è
   possibile cambiare tipo di dato della colonna di vista da numeric a
   numeric(18,6)»): la strada è a senso unico. ⇒ La vista proietta le 23
   colonne per nome e casta `consegnato::numeric(18,6)`; il pgTAP di §3
   pinna i tipi della vista con `col_type_is` (oggi nessun test lo fa).

2. **`p IS NULL OR col = ANY(p)` è la forma che il piano generico non
   piega** — la memoria del 17-09 su `fn_get_saldi_rate`, e qui il chiamante
   è proprio quel caso: il lister è plpgsql e passa un'espressione
   (`CASE WHEN p_ddt_id IS NULL …`), non un letterale; dalla sesta
   esecuzione il piano è generico. Provato con `PREPARE` +
   `plan_cache_mode = force_generic_plan` su `ddt_righe`:

   | Forma del seme | Piano generico |
   | --- | --- |
   | `WHERE $1 IS NULL OR dr.ddt_id = ANY($1)` | `Seq Scan … Filter: (($1 IS NULL) OR (ddt_id = ANY ($1)))` — anche con `enable_seqscan = off` («Disabled: true», nessuna alternativa) |
   | `WHERE dr.ddt_id = ANY($1)` **`UNION ALL`** `WHERE $1 IS NULL` | `Append` → `Bitmap Index Scan uq_ddt_vendita_r_riga_nr (Index Cond: ddt_id = ANY($1))` + `Result / One-Time Filter: ($1 IS NULL)` |

   Nel primo caso la semina scandisce `ddt_righe` intera **sotto la policy di
   riga** — O(tutti) nel posto da cui la chiusura voleva toglierlo. Nel
   secondo il ramo «tutti» ha un predicato senza colonne, che il planner
   solleva a *gating qual*: quando è falso **non esegue nemmeno la
   scansione**. ⇒ Ogni seme è una `UNION ALL` di rami puri: per DDT
   (`= ANY(p_ddt_ids)`), per ordine (via fulfillment, `= ANY(p_ordine_ids)`),
   e «tutti» (`p_ddt_ids IS NULL AND p_ordine_ids IS NULL`). Non serve
   rendere i parametri obbligatori: la memoria vieta l'`OR`, non il
   `NULL = tutti`. E la forma regge anche se un giorno la SRF non venisse
   inlinata (PG 18 mette in plancache anche le funzioni SQL).

3. **Il corpo va scritto `BEGIN ATOMIC`, e non è stile — sono due presidi.**
   (a) Una `LANGUAGE sql` a stringa è validata solo alla creazione, e il
   presidio dei riferimenti morti compila **solo il plpgsql** (memoria del
   20-09: `fn_get_iva_override` morta undici mesi nel catalogo). Con `BEGIN
   ATOMIC` le dipendenze entrano in `pg_depend` (provato: `vendite.ddt_righe`
   come `refobjid` della funzione) e un `DROP`/rinomina a monte viene
   **rifiutato** dal catalogo: si presidia da sola.
   (b) `db/pgtap/rls/test-rls-viste-security-invoker.sql` cammina
   `pg_rewrite → pg_depend → tabelle con RLS` **attraverso le viste**. Con la
   vista ridotta a `SELECT … FROM fn(…)` la catena si spezza sulla funzione:
   la vista **esce dal perimetro del criterio** e il test 1 — che la nomina
   fra le garantite — diventa rosso. Giusto: è il presidio che dice «non ti
   vedo più». ⇒ Nello stesso giro il criterio si allarga di un anello:
   vista → funzione (dalla regola) → dipendenze della funzione in `pg_depend`
   (`classid = 'pg_proc'`), con la condizione che la funzione **non sia
   `SECURITY DEFINER`** — una DEFINER in mezzo spegne la catena come una
   vista senza flag, e il test 3 (caso costruito) va affiancato da un caso
   con una funzione in mezzo. ⚠️ Con un corpo a stringa quell'anello **non
   esiste nel catalogo**: (a) e (b) sono la stessa scelta.
   (c) Il planner inlina anche una SRF `BEGIN ATOMIC` (provato: `CTE Scan on
   semi`, non un `Function Scan`), e con l'array letterale il ramo «tutti»
   sparisce dal piano.
   ⚠️ Da scrivere nel manuale: la vista dipende dalla funzione, quindi una
   colonna nuova nel `RETURNS TABLE` = `DROP FUNCTION` a cascata sulle
   **quattro** viste (`vw_partite_merce` + `vw_contatore_merce`,
   `vw_resi_da_accreditare`, `vw_situazione_merce_ordine`). Oggi una colonna
   nuova costa il drop delle tre a valle; domani ne costa quattro.

4. **Due FK della chiusura non hanno indice**, e sono quelle che la chiusura
   attraversa per salire dalle righe alle ri-consegne: `resi_righe(ddt_riga_id)`
   («di quali righe sono origine le ri-consegne?») e
   `resi_righe_riconsegne(ddt_riga_id)` («questa riga è una ri-consegna?»).
   Stanno in `dbops.fk_index_policy` con `consentito=false` (registrate dal
   job di popolamento, non dal CSV). Senza, `ponte_riga` ristretta a O
   scandisce comunque `resi_righe` intera. ⇒ Due righe in
   `80_data/sql/dbops/fk_index_policy.csv` con `consentito=true`; l'indice lo
   crea `apply_fk_index_policy()` (linee-guida-sql §8: policy opt-in, mai a
   mano). Le altre chiavi sono già servite per prefisso: `ddt_righe(ddt_id)`
   da `uq_ddt_vendita_r_riga_nr`, `ordini_righe_fulfillment(ordine_riga_id)`
   da `uq_ordini_r_ful_v_pair`.

5. **Il «pavimento» di `af` non è un pavimento sul modello.** §2 dice che
   «nessun filtro per riga evita» la scansione di `attivita_fatturabili`.
   Sul modello `vw_af_merce_per_riga` raggruppa per `(corsia, riga_id)`, e
   `riga_id` è una funzione di `commesse_attivita.segment_key`, che **ha un
   indice** (`ix_commesse_attivita_segment_key`): la chiusura conosce le
   chiavi che le servono (`'DDT:'||uid||':R:'||id` per R0 ∪ R1 ∪ O,
   `'ORD:'||uid||':R:'||id` per le loro righe d'ordine) e potrebbe leggere
   `af` per chiave. Due cose lo rendono un passo a sé: i componenti kit hanno
   la chiave con suffisso `#CMP:…`, quindi serve un `LIKE` a prefisso — cioè
   un indice `text_pattern_ops` (memoria: su it_IT un btree normale non
   serve il prefisso, e `_` va escapato); e `attivita_fatturabili` cresce con
   le **fatture**, non con i DDT — è la tabella che nel tempo cresce di più.
   Non è impossibile: è una **decisione** (D5), e va scritta come tale, non
   come un limite.

6. **Il test 6 di §3 è tautologico** se la vista è la proiezione della
   funzione: `fn(NULL, NULL)` e `SELECT … FROM fn(NULL, NULL)` sono la stessa
   query. Vale come pin di **D1** — che nessuno ridia alla vista un corpo suo
   — e allora si scrive sulla **forma**: `pg_get_viewdef` nomina
   `fn_partite_merce` e nessuna tabella. La prova di correttezza sono i casi
   1–5 col numero atteso.

7. **§3.5 vale solo se il filtro d'uscita è sulla colonna proiettata.**
   `ordine_id` della vista è il `min(ordine_riga_id)` di `orig`: una riga
   MULTIPLA (fulfillment su due ordini) esce sotto l'ordine della riga
   minima. Il seme d'ordine è «righe con **un** fulfillment verso l'ordine»
   (superset: giusto per la chiusura), ma l'output si filtra su
   `ordine_id = ANY(p_ordine_ids)` — la stessa colonna che `list_partite_merce`
   filtra (`p.ordine_id = %s`) — non sul seme. Con entrambi i semi
   valorizzati: unione dei semi, output `ddt_id ∈ X OR ordine_id ∈ P`; il BE
   ne passa uno solo, ma il contratto va scritto nel COMMENT.

8. **D4: la forma B1 conserva due implementazioni della stessa regola.**
   `fn_ddt_push_diagnosi` «riproduce i predicati» del lister, e
   l'equivalenza è tenuta da un pgTAP che confronta le **righe vive** (verde
   per sottrazione su un DB da zero). È esattamente ciò che D1 rifiuta per la
   vista. La forma che lo chiude è **B2**: il lister *deriva* dalla diagnosi
   — `… FROM vendite.fn_ddt_push_diagnosi(p) g JOIN testata/riga/BA/src …
   WHERE g.motivo IS NULL AND <filtri competenza/BA> … LIMIT p_limit` — la
   diagnosi espone `segment` e `differenza` (già calcolati in `cand`, oggi
   buttati), e la capability la legge **una volta**: `push_ok` = esiste
   `motivo IS NULL` (per costruzione, perché il push legge la stessa cosa),
   poi la precedenza `ALLOCATA` → `DDT_GIA_INVIATO` / `EMESSA` →
   `DDT_GIA_FATTURATO` sul `segment`, poi `min(rank)` come oggi. Costo:
   `RETURNS TABLE` della diagnosi (DROP + rigenera), lister riscritto sotto
   contratto invariato, `test-fn-list-ddt-da-pushare-contatore-v1` + i due
   pgTAP di `script/`. L'asimmetria con gli altri quattro lister (senza
   diagnosi) esiste già. ⚠️ Tocca il lister che alimenta la pipeline: giro
   **suo**, dopo la quarta leva, non nello stesso.

9. **Fatti datati**: `20260921-20` è applicato su dbdev il 21-09 alle 12:41
   (`databasechangelog`, `EXECUTED`); intestazione e registro D14 lo davano
   «da applicare». Le prove di §5 e la misura «prima/dopo» partono da lì.

## 3. Il presidio — `db/pgtap/vendite/test-fn-partite-merce-chiusura-v1.sql`

Costruisce, non confronta la popolazione. Per ogni caso: `fn_partite_merce(X)`
contro `fn_partite_merce(NULL, NULL)` filtrata a `ddt_id ∈ X`, `EXCEPT ALL` nei
due versi a zero, **e** un'asserzione sul numero atteso (così il test è rosso
anche se la vista intera fosse sbagliata nello stesso modo).

1. **Ordine spedito su tre DDT, fatturato d'ordine parziale**: la greedy di
   `alloc` versa il fatturato nel DDT più vecchio; chiedere il **solo DDT di
   mezzo** deve dare lo stesso `fatturato_da_ordine` della vista intera — è il
   caso in cui R1 è indispensabile (senza, il DDT di mezzo si crederebbe primo);
2. **Catena reso → nota di credito → ri-consegna su DDT diversi**, due
   ri-consegne della stessa origine (riuso della fixture di
   `test-vw-partite-merce-riconsegna-dopo-nc-v1`): chiedere la **sola seconda
   ri-consegna** deve dare la `riconsegna_quota_nuova` giusta — serve l'origine
   **e** la sorella (finestra di `migra`);
3. **Riga aggiunta a mano su DDT misto** con articolo già nell'ordine:
   `sospetto_duplicato_ordine` acceso anche per la chiusura;
4. **DDT senza ordine** e **DDT in bozza** (assente in entrambe);
5. **Seme per ordine**: `fn_partite_merce(NULL, ARRAY[o])` = vista intera
   `WHERE ordine_id = o` sui casi 1–3;
6. ~~**`NULL, NULL` = vista**: `EXCEPT ALL` nei due versi~~ → ⚠️ tautologico
   (§2-bis.6). Al suo posto **due pin di forma**: la vista nomina
   `fn_partite_merce` e nessuna tabella in `pg_get_viewdef` (D1: un corpo), e
   i **tipi** delle 23 colonne della vista con `col_type_is` — `consegnato`
   è `numeric(18,6)`, e il `SELECT *` lo perderebbe in silenzio (§2-bis.1);
7. **Scope**: come app, un DDT di un altro emittente chiesto per id torna
   **zero righe** (la RLS attraversa la funzione);
8. **Seme d'ordine su una riga MULTIPLA**: una riga di DDT che evade due
   ordini esce **solo** sotto l'ordine di `min(ordine_riga_id)` — cioè come
   `list_partite_merce` la filtra oggi (§2-bis.7). È il caso costruito che
   distingue «seme» da «filtro d'uscita».

Presidi trasversali da toccare, e non è un elenco da rileggere a fine giro:

* `rls/test-rls-viste-security-invoker` — **va allargato**, non solo riletto:
  con la vista sopra una funzione la catena `pg_rewrite → pg_depend` si
  spezza e la vista **esce dal criterio** (test 1 rosso, §2-bis.3b). Un
  anello in più (vista → funzione `BEGIN ATOMIC` → sue dipendenze, funzione
  non `SECURITY DEFINER`) e un caso costruito con una funzione in mezzo;
* `dbops/test-riferimenti-morti-v1` — **non la vede** (compila solo il
  plpgsql): con `BEGIN ATOMIC` è il catalogo a presidiarla (§2-bis.3a);
* `script/test-rubinetto-primo-motivo-v1` test 5 — non la conta (non
  chiama l'helper), ma il lister e la diagnosi riscritti restano dove sono;
* `test-vw-partite-merce-v1` (11), `-riconsegna-dopo-nc-v1` (8),
  `test-vw-contatore-merce-v1` (11), `test-fn-list-ddt-da-pushare-contatore-v1`
  (7), `test-fn-available-actions-ddt-reason-catch-all-v1` (8): nella stessa
  transazione dell'SQL estratto, come per la terza leva.

## 4. Documentazione da toccare nello stesso giro

* `docs/it/dbzero/vendite/manual/vw_partite_merce.md`: rev, e la sezione
  «Note operative» dice oggi *«è read-time … vale anche sui documenti vecchi»*
  — resta vero, e va aggiunto che **il lettore per documento chiama la
  funzione**;
* manuale nuovo `docs/it/dbzero/vendite/manual/fn_partite_merce.md`: la
  chiusura (§2) e la **regola per chi aggiunge una chiave** — è il pezzo che
  nessuno rileggerà nello YAML;
* COMMENT di lister e diagnosi (rev);
* `backend/apps/vendite/db/vendite_repository.py`, commento in testa a
  `list_partite_merce` (dice «la vista più costosa del sistema»: dopo non lo
  è più per documento);
* registro D14 (§3, §6, §7) e questo brief.

## 5. Le prove — prima dell'apply, che lo fa Tid

* SQL **estratto** dai changeSet (funzione, vista, lister, diagnosi, in
  quest'ordine) in `BEGIN … ROLLBACK` come owner: `reloptions` della vista,
  `EXCEPT ALL` vista-prima / vista-dopo a zero, i pgTAP di §3 e i cinque del
  17-09 concatenati nella stessa transazione;
* `EXPLAIN (ANALYZE)` come app di `fn_partite_merce(ARRAY[131])`: le CTE della
  chiusura devono comparire **una volta**, e `riga` deve contare le righe della
  chiusura, non 36 — è la prova che il filtro **entra**;
* ⭐ **e la stessa prova nella forma in cui verrà chiamata davvero**
  (memoria: «la forma comoda è quella che mente»): `PREPARE` con l'array a
  parametro e `plan_cache_mode = force_generic_plan`, i semi devono mostrare
  `Index Cond` + `One-Time Filter`, mai un `Filter: (($1 IS NULL) OR …)`
  (§2-bis.2); poi il lister chiamato **sei volte** con lo stesso id, così il
  piano di plpgsql è passato a generico;
* `pg_depend` della funzione non vuoto (`BEGIN ATOMIC` ha preso), e
  `test-rls-viste-security-invoker` allargato **verde con** `vw_partite_merce`
  ancora dentro `_tocca_rls` (§2-bis.3);
* la capability come app su un DDT: il numero è un fatto datato, e va nel
  registro con la data.

## 6. Decisioni aperte per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D1** | La forma: funzione con la vista come proiezione (un corpo), oppure funzione e vista separate | ✅ **Decisa da Tid il 21-09: un corpo.** Due corpi sono due implementazioni della regola che dosa la fatturazione. ⚠️ Con le due precisazioni di §2-bis, che non sono opzioni: corpo **`BEGIN ATOMIC`** (presidio dei riferimenti morti e catena RLS visibili nel catalogo), vista con le 23 colonne **per nome** e `consegnato::numeric(18,6)` |
| **D2** | Due semi (`p_ddt_ids`, `p_ordine_ids`) nella stessa funzione, o solo per DDT | ✅ **Decisa da Tid il 21-09: due semi.** `list_partite_merce` legge già per ordine, e la chiusura per ordine è lo stesso algoritmo. Forma dei semi: rami in `UNION ALL`, mai `p IS NULL OR …` (§2-bis.2); filtro d'uscita sulla colonna proiettata (§2-bis.7) |
| **D3** | Chi passa alla funzione oltre a lister, diagnosi e `list_partite_merce`: `vw_situazione_merce_ordine` (→ funzione per ordine) e le sei funzioni per riga di reso | ✅ **Decisa da Tid il 21-09: non in questo giro, ma è il giro SUBITO DOPO — «prima possibile», non un residuo.** Sono verbi o aggregati letti una volta per gesto, e questo giro vuole restare piccolo per il pgTAP dei casi costruiti; ma restano sette lettori che pagano «tutto». Stessa mossa (una riga per lettore: `fn_partite_merce(ARRAY[ddt_id della riga])` / `(NULL, ARRAY[ordine_id])`), un pgTAP di equivalenza per lettore |
| **D4** | La seconda leva — capability a una lettura. ~~Forma B1 (`segment` esposto, lister invariato)~~ oppure **B2** (§2-bis.8: il lister deriva dalla diagnosi, una sola implementazione dell'eleggibilità) | ✅ **Decisa da Tid il 21-09: B2, in un giro suo, subito dopo la quarta leva.** Non è «dopo la misura»: è una questione di contratto — oggi lister e diagnosi sono due copie della stessa regola tenute uguali da un pgTAP verde per sottrazione, cioè lo stesso difetto che D1 rifiuta per la vista. B1 lo lascerebbe in piedi. Il giro è separato perché tocca il lister della pipeline |
| **D6** | `vendite.vw_contatore_merce` **non ha più lettori** (§9.1: dal `20260921-23` il lister legge `fn_partite_merce`; nessuna funzione, vista, repository o CSV di lista la nomina — solo `test-vw-contatore-merce-v1` e `test-porta-oneri-contatore-cieco-v1`). Ritirarla, o dichiarare chi la leggerà | 🔵 **Da decidere.** Sul modello è la quarta vista a valle della partita e ogni colonna nuova nel `RETURNS TABLE` paga anche il suo `DROP`; il COMMENT dice ancora «dosa la fatturazione», che non è più vero. Se si ritira: `DROP VIEW`, i due pgTAP (il secondo prova la porta degli oneri sul contatore — va riscritto sulla partita o ritirato con motivo), il `manual/` (memoria: oggetto ritirato = cancellare il manual), i COMMENT di `vw_situazione_merce_ordine` e `vw_partite_merce` che la nominano |
| **D7** | `vendite.ddt_righe.attivo` **non ha un guard fuori da `DRAFT`** (letto dal catalogo il 21-09 sera: i soli trigger su `attivo` sono i `block_deact` delle figlie — fulfillment, resi, componenti, note — e una riga standalone già instradata non ne ha). Il modello quindi **ammette** di disattivare una riga che ha un'attività di commessa (`ALLOCATA`/`EMESSA`) su un DDT emesso. È emerso da B2: la capability leggeva la precedenza `GIA_INVIATO`/`GIA_FATTURATO` scandendo `ddt_righe` **senza guardare `attivo`**; ora la legge dalla diagnosi, che guarda le righe attive (lo stesso perimetro della partita e del lister). Nel solo caso «riga instradata poi disattivata» la risposta cambia (da «già inviato» al motivo delle altre righe, o al generico) | 🔵 **Da decidere.** Raccomandazione: un guard `BEFORE UPDATE OF attivo` su `ddt_righe` che rifiuti la disattivazione quando `fn_get_stato_push_segment(segment_key) <> 'LIBERA'` — merce instradata a fatturazione non è una riga che si può far sparire — oppure, più largo, il lock delle righe fuori da `DRAFT` (`can_edit_righe` lo dice già al FE, il DB no). È una regola di dominio, non un ripiego della capability: nessun changeSet in questo giro |
| **D8** | `script.fn_get_stato_push_segment` è un classificatore **per riga**: `WHERE segment_key = k OR LIKE k‖'#CMP:%' OR LIKE k‖'#RET:%'` su `commesse_attivita`. Sotto RLS è una **scansione intera con la policy valutata per prima** (il piano come app: `Seq Scan … Filter: (ruolo = OPERATORE AND fn_scope_ef_whitelist_via_commessa(…) AND (…))`, 2027 buffer per 112 righe): l'`OR` con due `LIKE` non è indicizzabile sul btree normale, e `textlike` **non è leakproof**, quindi non può salire sopra la policy. Fatto datato (21-09 sera, app): 7.6 ms a chiamata. La diagnosi lo chiama per **ogni riga attiva** — deve, perché `segment` serve alla precedenza della capability anche sulle righe escluse dalle altre rank — e da B2 il lister senza documento eredita quel costo (§10.7) | 🔵 **Da decidere, insieme a D5.** Due strade, non alternative: **(a)** l'indice `text_pattern_ops` su `commesse_attivita.segment_key` — lo stesso di D5 — rende indicizzabili tutti e tre i rami (`texteq` e `text_pattern_*` **sono** leakproof: l'`Index Cond` sale sopra la policy, e il `LIKE` residuo ricontrolla solo le righe che l'indice restituisce); **(b)** una forma **set-based** del classificatore, `fn_stati_push_segmenti(p_keys varchar[])`, una scansione per documento invece di una per riga, con la scalare come **proiezione** (D1: un corpo) — la chiamano i cinque lister e le capability, quindi è un BB e le copie si ritirano nello stesso giro. (a) è un changeSet `00_schema` (un indice, non una FK: fuori dalla policy) e toglie il grosso; (b) è il modello giusto per la lista senza documento. Raccomandazione: (a) subito nel giro 4, (b) valutata dopo la misura |
| **D5** | Il «pavimento» di `af` (§2-bis.5): leggere `vw_af_merce_per_riga` per chiave di segmento invece che intera — indice `text_pattern_ops` su `commesse_attivita.segment_key` + `LIKE` a prefisso per i `#CMP` | ✅ **Decisa da Tid il 21-09: DA FARE, passo a sé, dopo D3 e D4.** Non «se serve»: sul modello è l'unico pezzo del conto che dopo la chiusura resta proporzionale alla storia — cresce con le **fatture**, che non si svuotano mai — quindi peggiora da solo col tempo. La misura dopo la quarta leva serve a dargli la priorità, non a decidere se farlo |

## 7. Cosa resta — quattro giri, nell'ordine

**Giro 1 — la quarta leva (D1, D2).** **Quattro changeSet** in `20_code/vendite`
(`fn_partite_merce` nuova `BEGIN ATOMIC`, la vista come proiezione per nome,
lister e diagnosi sulla funzione) + **due righe** nel CSV `fk_index_policy`
(§2-bis.4) + un pgTAP nuovo (§3, otto casi) + la **rev di
`test-rls-viste-security-invoker`** (anello funzione, §2-bis.3b) + una riga
di SQL nel repository BE. Stima: **una giornata e mezza** — la mezza in più è
il criterio del presidio RLS, che senza questo giro diventerebbe cieco
proprio sulla vista che lo ha reso necessario.

**Giro 2 — D3, «prima possibile».** ✅ **Scritto il 21-09 sera (§9).** ~~I
sette lettori restanti~~ → sul catalogo erano **tre**: `vw_situazione_merce_ordine`
(BE per ordine e per DDT) e i due verbi che leggono `vw_resi_da_accreditare`
per una riga. Due funzioni con gli stessi due semi di `fn_partite_merce`, le
due viste come proiezioni, i verbi sul DDT della riga resa; due pgTAP a casi
costruiti (12 + 12). Una richiesta BE (§9.4).

**Giro 3 — D4, forma B2.** ✏️ **Scritto il 21-09 sera (§10).** La diagnosi
espone `segment`, `billing_account_id`, `ordine_riga_id` e `quantita_push`
(`DROP` + rigenera, `BEGIN ATOMIC`), il lister deriva dalla diagnosi, la
capability legge una volta. Contratto del lister invariato verso la pipeline;
i suoi pgTAP a esito identico sopra l'SQL estratto. ⚠️ `differenza` non è fra
le colonne: il lister ha bisogno della **dose** (la differenza cappata alla
quantità della riga), ed esporre la differenza grezza gli avrebbe fatto
ricopiare il cap — la seconda implementazione che B2 vuole togliere.

**Giro 4 — D5 e D8(a), `af` e il classificatore per chiave.** Indice
`text_pattern_ops` su `commesse_attivita.segment_key` — serve a **entrambi**:
`af` letta per le chiavi della chiusura (esatte per le righe, a prefisso per i
`#CMP`) e `fn_get_stato_push_segment` che smette di scandire la tabella sotto
policy a ogni riga (§10.7). ⚠️ Sotto RLS la prova con `EXPLAIN` come app deve
mostrare l'`Index Cond` **sopra** la policy: `texteq` e `text_pattern_*` sono
leakproof, `textlike` no — il `LIKE` resta come recheck sulle righe
dell'indice. La misura dopo il giro 3 gli dà la priorità: il cockpit è
tornato a pagare la diagnosi di tutto. Mezza giornata più la prova.

## 8. Giro 1 — cosa è stato scritto e provato (21-09 sera)

### 8.1 I file

| Cosa | File |
| --- | --- |
| la funzione, `BEGIN ATOMIC` | `20_code/vendite/20260921-21-create-fn-partite-merce` |
| la vista come proiezione per nome | `20_code/vendite/20260921-22-update-vw-partite-merce-proiezione-fn-partite-merce` |
| il lister sul seme | `20_code/vendite/20260921-23-update-fn-list-ddt-da-pushare-partita-per-documento` |
| la diagnosi sul seme | `20_code/vendite/20260921-24-update-fn-ddt-push-diagnosi-partita-per-documento` |
| le due FK a `consentito=true` | `80_data/changelog/20260921-25-upsert-fk-index-policy-partite-merce` + `sql/vendite/fk_index_policy_partite_merce.csv` |
| il presidio della chiusura | `db/pgtap/vendite/test-fn-partite-merce-chiusura-v1.sql` (14) |
| il presidio RLS allargato | `db/pgtap/rls/test-rls-viste-security-invoker.sql` (5 → 7: anello funzione, DEFINER in mezzo) |
| manuali | `vw_partite_merce.md` (rev), **`fn_partite_merce.md`** (nuovo), `fn_list_ddt_da_pushare.md` e `fn_ddt_push_diagnosi.md` (rev) |

### 8.2 La forma finale della funzione, in tre righe

Ogni lettura ristretta è una CTE a **due rami in `UNION ALL`**: quello con la
chiave (`JOIN` sul set della chiusura, predicato `NOT tutti`) e quello «come la
vista» (predicato `tutti`, dove `tutti` = `p_ddt_ids IS NULL AND p_ordine_ids
IS NULL`). I set: `semi` (R0), `r1`, `chiusura` (R0 ∪ R1), `origini` (O),
`dr_in`, `riconsegne_in`, `fulfillment_in`, `resi_in`, `ddt_in`. Da lì in giù
il corpo è la vista del `20260921-20`, ricopiata con le sole sorgenti
sostituite. Uscita: `tutti OR ddt_id = ANY(p_ddt_ids) OR ordine_id = ANY(p_ordine_ids)`.

### 8.3 Le prove (owner, `BEGIN … ROLLBACK`, SQL estratto dai cinque change)

* **Equivalenza sui dati vivi** (colore): `EXCEPT ALL` a zero nei due versi
  fra `fn(NULL,NULL)` e la vista (36 righe); fra `fn(ARRAY[d])` e la vista
  filtrata per **ognuno** dei 29 DDT con partite; fra `fn(NULL, ARRAY[o])` e
  la vista per ognuno dei 16 ordini.
* **Forma del piano in piano generico** (`PREPARE` + `force_generic_plan`, la
  chiamata del lister): `Index Cond` su `uq_ddt_vendita_r_riga_nr` per il seme,
  `One-Time Filter` sui rami «tutti», che risultano `never executed`; le
  stime della chiusura sono giuste (20 stimate, 4 reali). In modo «tutti» le
  scansioni sono **le stesse** della vista (confrontate una per una).
* **Il presidio nuovo**: 13/14 verdi da owner; il **14** (scope) è rosso da
  owner perché l'owner salta la RLS — lo stesso del test 11 gemello di
  `test-vw-situazione-merce-ordine-v1`, verde come app. I casi che contano
  (4: R1; 8: le sorelle; 13: MULTIPLA) sono verdi **per i numeri attesi**, non
  solo per l'uguaglianza con la vista.
* **I sei presidi esistenti** sopra lo stesso SQL: `test-vw-partite-merce-v1`
  11/11, `-riconsegna-dopo-nc-v1` 8/8, `test-vw-contatore-merce-v1` 11/11,
  `test-fn-list-ddt-da-pushare-contatore-v1` 7/7,
  `test-fn-available-actions-ddt-reason-catch-all-v1` 8/8,
  `test-vw-situazione-merce-ordine-v1` 16/17 (l'11 di scope, come sempre da
  owner).
* **Il presidio RLS**: 7/7 con i changeSet e 7/7 senza; e la **controprova**:
  il file di HEAD sopra i changeSet dà `not ok 1 — Unexpected records:
  (vendite.vw_partite_merce)`, cioè la vista che esce dal perimetro (§2-bis.3b
  era un'affermazione, ora è un fatto).
* **Il guardrail dei riferimenti morti** sopra lo stesso SQL: OK (il lister
  plpgsql chiama la funzione nuova e `plpgsql_check` la risolve).
* **I sette cancelli statici** della CI (`run_on_change`, `pgtap_preambolo`,
  `sql_letterali`, `timestamp_senza_fuso`, `precondition_seed`,
  `ddl_su_trigger_automazione`, `grant_ruolo_batch`): tutti OK.
  `liquibase updateSQL` offline del `-21`: rende.
* ⭐ **Il driver, provato col jar di Liquibase** (`tools/liquibase/jdbc/postgresql-42.7.10.jar`,
  un `Statement.execute` in transazione ritirata, come fa Liquibase con
  `splitStatements: false`): pgjdbc esegue un `BEGIN ATOMIC … END;` **solo se
  sta da solo** nel testo — dopo l'`END` non riprende a spezzare, e un
  `COMMENT` accodato nello stesso `sql:` fa rispondere al server «non è
  possibile inserire comandi multipli in una istruzione preparata». Nel `-21`
  il `COMMENT` è un **secondo change** dello stesso changeSet, provato verde.
  È il primo `BEGIN ATOMIC` del repo: la regola sta nell'intestazione del file.
* ⚠️ **Rilettura di Tid (21-09 sera): firme e `RETURNS TABLE` erano a tipi
  nudi** in tutti e tre i changeSet di funzione — la nuova scritta da zero, e
  lister/diagnosi ricopiati dal corpo vivo di `pg_get_functiondef`, che i
  `%TYPE` li scioglie (e il `20260817-10` li aveva già ricopiati sciolti:
  l'ultimo YAML ancorato del lister è il `20260803-02`, della diagnosi il
  `20260818-20`). Corretti: ancorato ciò che proietta una colonna, tipo
  esplicito **con la ragione** per saldi, somme, vocabolari e array
  (`colonna%TYPE[]` non esiste); `SECURITY INVOKER` esplicito; `COMMENT ON
  FUNCTION` con le liste ancorate. Prova: `regtype` delle colonne identico ai
  tipi nudi (sola lettura), poi `pg_get_function_identity_arguments` +
  `pg_get_function_result` + `prosecdef` **byte-identici** al vivo per lister
  e diagnosi, una sola funzione per nome (nessun overload), il `RETURNS` di
  `fn_partite_merce` identico alla stesura precedente; tutti i pgTAP e i
  cancelli ripetuti con lo stesso esito.
* **Tempi da owner** (colore, senza RLS): vista 4.5 ms, fn tutti 4.3, vista
  `WHERE ddt=131` 3.2, fn(ARRAY[131]) 2.4. La misura che conta è come app,
  dopo l'apply.

### 8.4 ✅ Richiesta BE — fatta il 21-09 sera

> ✅ `list_partite_merce` legge `fn_partite_merce` col solo array del documento
> riempito, senza `WHERE`; la scelta dell'array è il BB
> `sorgente_per_documento` (regola del 2: la stessa scelta stava per essere
> scritta in quattro punti — `_coda_documento_filtro.py`, accanto al predicato
> gemello). Un test per punto + la traversata degli otto rami sul DB vero
> (`tests/db/test_lettura_per_documento_dalle_funzioni.py`), provati per
> mutazione (array invertito → rosso, parametri del COUNT invertiti → rosso).
> `apps.vendite` 2093 test verdi. Il commento «la vista più costosa del sistema»
> riscritto. *La richiesta, com'era:*


`backend/apps/vendite/db/vendite_repository.py`, `list_partite_merce`: al
posto di `FROM vendite.vw_partite_merce p … WHERE p.ddt_id = %s` /
`p.ordine_id = %s`, leggere `FROM vendite.fn_partite_merce(ARRAY[%s]::bigint[], NULL) p`
per DDT e `FROM vendite.fn_partite_merce(NULL, ARRAY[%s]::bigint[]) p` per
ordine, **togliendo** il `WHERE` sul documento (la funzione filtra già
l'uscita, sulla stessa colonna proiettata). Contratto della risposta
invariato: stesse 23 colonne, stesse righe (§2-bis.7 e test 13 del pgTAP). E
il commento in testa al metodo, che dice «la vista più costosa del sistema»:
per documento non lo è più. ⚠️ Finché resta sulla vista non c'è niente di
sbagliato, solo il costo di prima.

### 8.5 Cosa resta, nell'ordine

1. ✅ apply dei cinque changeSet — **Tid, 21-09 alle 14:46** (`databasechangelog`,
   tutti `EXECUTED`); `apply_fk_index_policy()` ha creato
   `ix_resi_righe_ddt_riga_id` e `ix_resi_righe_riconsegne_ddt_riga_id`;
   la vista è sulla funzione con `security_invoker=on` e `consegnato`
   `numeric(18,6)`;
2. ✅ pgTAP come app su **dbdev**, corsa di Tid: **nessuna regressione**;
   2-bis. 🔴→✏️ **sullo scratch `zeroerp_ci` il presidio nuovo era rosso**
   (corsa di Tid, 21-09 sera: «Rossi QUI che la CI non conosce», causa
   `ERRORE_FIXTURE`). Non la chiusura: i tre pin di forma passano sul DB da
   zero (funzione `BEGIN ATOMIC` non `DEFINER`, vista sulla funzione senza
   tabelle, 23 colonne con `numeric(18,6)`); moriva la **fixture**, nata per
   copia dai gemelli con il `SELECT … FROM anagrafiche.billing_account …
   LIMIT 1` — su un database ricostruito `billing_account` ha **zero righe**,
   `tmp_refs_ch` resta vuota e `fn_get_or_create_commessa` solleva su
   `p_billing_account_id` NULL. Tre asserzioni su quattordici: copertura
   zero in CI, cioè esattamente il «verde per sottrazione» che §3 dichiara di
   rifiutare, sulla riga sbagliata. È la malattia di D7 (§3 di
   migliorie-generali: *la fixture cerca l'azienda invece di costruirla*) e
   ha già la sua ricetta: **riscritta con i builder** —
   `dbops.fn_pgtap_crea_cliente_ba('pgtap_chiusura')` per la terna
   BA / istanza / soggetto-ruolo (il legame all'emittente lo scrive il
   trigger z90 verso chi agisce, lo stesso emittente che rispondono
   `fn_pgtap_emittente_operatore`/`_sr_operatore`),
   `dbops.fn_pgtap_crea_articolo('PGT-CH-ART', false)` per l'articolo (sul
   DB da zero il catalogo ha **solo** i cinque `ONERE_*`, sourceless: la
   pescata `ORDER BY data_insert DESC` avrebbe preso quelli), e via il
   `SET LOCAL app.current_user_id = '1'` dopo la riga di contesto (l'utente 1
   in CI non esiste; il contesto sceglie o costruisce l'operatore da solo).
   Nessuna asserzione cambia. ⏳ **Da rilanciare da Tid sullo scratch**:
   `PGTAP_ENV_FILE=db/internal.ci.env scripts/testpgtap.sh db/pgtap/vendite/test-fn-partite-merce-chiusura-v1.sql`
   (atteso `14/14`), poi su dbdev per la controprova.
   ⚠️ I sei gemelli della partita (`test-vw-partite-merce-v1`,
   `-riconsegna-dopo-nc-v1`, `test-vw-contatore-merce-v1`, i tre
   `fn-list-ddt-da-pushare-*`) hanno la **stessa** fixture e sono già in
   `baseline-rossi-ci` per la stessa causa: stessa ricetta, un file alla
   volta — cantiere **D7**, non questo brief. Censiti il 21-09: **70 file**
   con quel predicato, 66 rossi in CI;
3. ✅ la misura come app: §8.6;
4. ✅ commit — `c60f39eaa`, PR #1634 (21-09 sera);
5. ✅ giro 2 (D3) **applicato** il 21-09 alle 18:43, misurato (§9.7); poi D4
   (B2), poi D5; D6 da decidere.

### 8.6 La misura «dopo» (dbdev, 21-09 dopo l'apply, `zeroerp_app` con contesto operatore, 51 DDT / 36 partite, media di 5 letture calde — colore, non motivo)

| Lettura | Prima (§1, 21-09 mattina) | Dopo |
| --- | --- | --- |
| vista intera = `fn(NULL, NULL)` | ~90–130 ms | **88 ms** — invariata, com'è giusto: stesse scansioni |
| la partita di UN DDT | ~120 ms (vista filtrata: il filtro non entrava) | **24 ms** (`fn(ARRAY[131])`) |
| `fn_list_ddt_da_pushare(p_ddt_id)` | 112 ms | **52 ms** |
| `fn_ddt_push_diagnosi(p_ddt_id)` | 93 ms | **25 ms** |
| `fn_available_actions_ddt` (il drawer) | ~290 ms | **175 ms** |
| `fn_list_ddt_da_pushare()` senza documento (cockpit) | — | 214 ms (legge tutte, com'era) |

Dentro i 24 ms della partita di un DDT (`EXPLAIN ANALYZE` come app): `af`
— il contatore delle attività fatturabili, letto intero — **~12 ms**, la
CTE `riga` ~12 (le policy di `ddt`/`ddt_righe`/`articoli` sulla chiusura),
tutto il resto sotto i 6. ⭐ Cioè: dopo la chiusura, **metà** del costo di
una lettura per documento è già il pavimento di D5, e cresce con le fatture.
Della capability restano ~100 ms fuori da lister e diagnosi
(`fn_check_ddt_emittibile`, `fn_get_stato_push_segment` per riga, le
transizioni): il giro D4 (B2) toglie una delle due letture della partita
(~25), non quei cento — sono il prossimo bersaglio da misurare, non da
supporre.


## 9. Giro 2 (D3) — cosa è stato scritto e provato (21-09 sera)

### 9.1 Il censimento, prima di scrivere — e cosa ha corretto

Il brief (§1, §2.2, §7) contava **sette** lettori: `vw_situazione_merce_ordine`
e «le sei funzioni per riga di reso». Letto dal catalogo vivo (`pg_proc.prosrc`
senza i commenti, `pg_rewrite`/`pg_depend` per le viste, il backend e i CSV
delle liste), il perimetro è un altro:

| Lettore | Cosa legge davvero | Per |
| --- | --- | --- |
| BE `list_situazione_merce_ordine` | `vw_situazione_merce_ordine` | un ordine **o un DDT** (EXISTS sul fulfillment: «le righe d'ordine che quella spedizione ha toccato», rev BE 2026-08-19) |
| `fn_accredita_riga_reso(p)` | `vw_resi_da_accreditare WHERE resi_riga_id = p` | una riga |
| `fn_resi_riga_tetti_accredito(p, …)` — `SECURITY DEFINER`, chiamata da `trgfn_resi_accrediti_guard` a **ogni riga scritta sul ponte** | idem | una riga |
| BE `list_situazione_merce_accrediti`, `ResiRepository.list_da_accreditare` (con `ddt_id`/`ordine_id`) | `vw_resi_da_accreditare` col BB `filtro_coda_per_documento` | un DDT o un ordine |
| lista configurabile `vendite.resi_da_accreditare` (id 10), `vw_dash_backlog_documenti` | `vw_resi_da_accreditare` | **tutta** — ed è giusto |
| `vw_contatore_merce` | `vw_partite_merce` | **nessuno la legge più** (→ D6) |

Delle «sei funzioni»: `fn_chiudi_riconsegna_reso`, `fn_genera_ddt_riconsegna`,
`fn_ordine_riga_qta_riconsegna`, `fn_resi_riga_accreditato_partita` nominano
le viste **solo nei commenti** (leggono `vw_resi_righe_effettive` o il ponte);
`script.fn_check_accredito_annullabile` non le nomina affatto;
`fn_annulla_accredito_riga_reso` idem. I lettori per riga sono **due**, ed
entrambi passano dalla stessa coda. ⭐ Lezione: un elenco scritto in un brief
si verifica sul catalogo prima di farci un giro sopra — qui avrebbe prodotto
quattro changeSet vuoti.

### 9.2 I file

| Cosa | File |
| --- | --- |
| l'aggregato per riga d'ordine, `BEGIN ATOMIC` | `20_code/vendite/20260921-26-create-fn-situazione-merce-ordine` |
| la vista come proiezione per nome (`ordinato::numeric(18,6)`) | `20_code/vendite/20260921-27-update-vw-situazione-merce-ordine-proiezione-fn` |
| la coda accrediti, `BEGIN ATOMIC` | `20_code/vendite/20260921-28-create-fn-resi-da-accreditare` |
| la vista come proiezione per nome (cinque `varchar` ricastati) | `20_code/vendite/20260921-29-update-vw-resi-da-accreditare-proiezione-fn` |
| il verbo «accredita» sul seme del DDT | `20_code/vendite/20260921-30-update-fn-accredita-riga-reso-partita-per-documento` |
| il guard dei tetti sul seme del DDT (resta `DEFINER`) | `20_code/vendite/20260921-31-update-fn-resi-riga-tetti-accredito-partita-per-documento` |
| i presidi | `db/pgtap/vendite/test-fn-situazione-merce-ordine-chiusura-v1.sql` (12), `test-fn-resi-da-accreditare-chiusura-v1.sql` (12) |
| manuali | **`fn_situazione_merce_ordine.md`**, **`fn_resi_da_accreditare.md`** (nuovi); `vw_situazione_merce_ordine.md`, `vw_resi_da_accreditare.md`, `fn_accredita_riga_reso.md`, `fn_resi_riga_tetti_accredito.md`, `fn_partite_merce.md`, `vw_partite_merce.md` (rev) |

Nessuna riga nuova in `fk_index_policy`: le chiavi che i semi attraversano
sono già servite (`ddt_righe(ddt_id)` e `ordini_righe(ordine_id)` per
prefisso, `ordini_righe_fulfillment(ddt_riga_id)`, `resi_righe(ddt_riga_id)`
dal giro 1).

### 9.3 La forma, e le due cose che non erano nel piano

**Gli stessi due semi, nello stesso ordine.** Entrambe le funzioni prendono
`(p_ddt_ids, p_ordine_ids)` come `fn_partite_merce`; entrambi `NULL` = tutte;
array vuoto = zero righe; entrambi valorizzati = unione. Le viste sono
`fn(NULL, NULL)` con le colonne per nome (D1). Rami in `UNION ALL`, mai
`p IS NULL OR` (§2-bis.2).

1. **Il seme per DDT della situazione ordine non è «la partita di quel DDT»**:
   è la situazione **intera** delle righe d'ordine che quel DDT ha toccato —
   l'ordine spedito in tre volte, chiesto dal DDT di mezzo, risponde
   consegnato 30 e tre partite, non 10 e una. È la semantica che il pannello
   ha dal 19-08 (`vendite_repository`, «due filtri, una lettura»), e il pgTAP
   la costruisce (test 5). Le partite si chiedono a `fn_partite_merce`
   **per ordine** (gli ordini chiesti ∪ gli ordini toccati): l'aggregato di
   una riga d'ordine è completo per costruzione, perché la partita esce sotto
   `ordine_id` della riga minima e l'ordine porta tutte le sue righe.

2. **Il seme per ordine della coda accrediti segue il predicato del backend,
   non quello della partita.** La coda non ha `ordine_id`; il BB
   `filtro_coda_per_documento` la filtra con un `EXISTS` sul fulfillment
   della riga di DDT resa. `fn_partite_merce(NULL, ARRAY[o])` invece esce
   sulla colonna proiettata (`ordine_id` = riga **minima**, §2-bis.7): una
   riga `MULTIPLA` sta nella coda di **entrambi** gli ordini ma nella partita
   di uno solo. Due semantiche «per ordine», diverse perché le due letture lo
   sono; il pgTAP costruisce la riga `MULTIPLA` per distinguerle (test 7:
   coda per B = 1 riga, partita per B = 0). La funzione quindi semina
   `fn_partite_merce` **per DDT** (i DDT delle righe di S, un soprainsieme
   che il `JOIN` con le righe di reso riporta a S) — e le **sorelle** della
   stessa riga di DDT ci sono tutte, quindi la finestra della greedy per
   `resi_riga_id` è intera (test 4 e 5: capienza 3, la prima riga prende 3, la
   seconda 0 — anche dal guard, attraverso la funzione).

3. ⭐ **Il planner non inlina una SRF con un sub-select fra gli argomenti**
   (`inline_set_returning_function`: `contain_subplans` sugli argomenti →
   `Function Scan`). Il seme che le due funzioni passano a `fn_partite_merce`
   è **calcolato** (`array_agg` su una CTE), quindi quel ramo non si inlina.
   Provato: con l'array letterale la chiamata si inlina (`CTE semi …`), con
   `(SELECT array_agg…)` è un `Function Scan`; con `LATERAL … ARRAY[v.id]` si
   inlina ma pianifica di più. La forma scelta: **due rami** sulla lettura
   della partita — il ramo «tutte» chiama `fn_partite_merce(NULL, NULL)` con
   due letterali e resta **inlinato** (la vista di prima: 33 scansioni su 33
   identiche per la situazione; stesse tabelle e stesso numero di accessi per
   la coda), il ramo ristretto è il `Function Scan` col seme calcolato, mai
   eseguito quando `tutti`. `COALESCE(array_agg, '{}')` è obbligatorio: un DDT
   senza fulfillment darebbe `NULL`, e `fn(NULL, NULL)` è «tutte».

4. ⚠️ **Fatto datato sul costo di pianificazione** (dbdev, owner, 21-09 sera —
   cioè **senza RLS**, quindi colore). `fn_partite_merce(ARRAY[d])` con
   letterale costa ~10 ms di *planning* e ~1.5 di esecuzione **a ogni
   istruzione** (una vista o una SRF inlinata si ri-pianificano sempre). Come
   `Function Scan` il piano sta nella plancache della funzione: le prime
   cinque chiamate della sessione usano piani *custom* (~9 ms l'una), dalla
   sesta il **generico** — che è buono proprio perché la forma a One-Time
   Filter regge senza conoscere i parametri — e la chiamata costa **~1.8 ms**
   in tutto (provato con dieci chiamate di seguito e con
   `force_generic_plan`). Quindi, a regime (chiamate 8–10 di 10, media di 3,
   righe valutate intere): situazione per ordine **15 → 8 ms**, per DDT
   **13 → 6**, coda per DDT **9 → 5**; il guard dei tetti 1 → 1 (era già in
   plancache come `DEFINER` SQL, e da owner esegue la coda intera in un
   millisecondo). La vista intera paga **+2–3 ms di planning** (12 → 14, 9 →
   12): le scansioni sono le stesse, il piano ha un ramo in più da preparare.
   ⛔ Nessuno di questi numeri decide niente: il guadagno è sul **modello** —
   O(chiusura) sotto RLS invece di O(tutti) per riga scandita — ed è quello
   che il giro 1 ha misurato come app (120 → 24). La misura che conta è quella,
   dopo l'apply; questa dice solo che la forma non costa niente da owner.

### 9.4 ✅ Richiesta BE — fatta il 21-09 sera

> ✅ `list_situazione_merce_ordine` senza `WHERE`/`EXISTS` (li fa la funzione);
> `_list_coda_su_partite` prende `funzione=` per la coda accrediti e resta sul
> predicato per le ri-consegne; `ResiRepository._list_coda` prende una
> `sorgente` opzionale al posto della vista nel `FROM` — anche nel `COUNT` di
> ripiego, coi parametri della sorgente **prima** dei filtri (è il punto che
> sbaglia senza errore, e ha il suo test) — e `list_da_accreditare` la passa
> quando c'è un documento; senza documento resta sulla vista (`fn(NULL, NULL)`).
> `filtro_coda_per_documento` **non si ritira**: serve alle ri-consegne, come
> previsto. ✅ **22-09 (regola del 2, ok Tid)**: la scelta «quale coda legge la
> funzione e quale la vista» stava in **due** repository col nome della
> funzione ricopiato — ora è `FUNZIONE_PER_CODA` + `lettura_coda_per_documento`
> nello stesso modulo, e `_list_coda`/`_list_coda_su_partite` ricevono la sola
> vista-coda. Quando le ri-consegne avranno la loro funzione: una riga.
> *La richiesta, com'era:*


`backend/apps/vendite/db/vendite_repository.py`:

* `list_situazione_merce_ordine`: `FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[%s]::bigint[]) s`
  per ordine, `FROM vendite.fn_situazione_merce_ordine(ARRAY[%s]::bigint[], NULL) s`
  per DDT, **togliendo** il `WHERE s.ordine_id = %s` e l'`EXISTS` sul
  fulfillment (la funzione incorpora entrambi). Stesse 21 colonne, stesse
  righe (pgTAP test 6). Il commento in testa che dice «NON si passa dalla
  partita» resta vero: la funzione passa da `fn_partite_merce` per ordine,
  che è la partita per chiusura;
* `_list_coda_su_partite` per la coda **accrediti**:
  `FROM vendite.fn_resi_da_accreditare(ARRAY[%s], NULL)` / `(NULL, ARRAY[%s])`
  senza il predicato del BB. ⚠️ La coda **ri-consegne** (`vw_resi_da_riconsegnare`)
  non legge la partita: resta sulla vista col BB, quindi `filtro_coda_per_documento`
  **non si ritira** — serve ancora a lei e a `ResiRepository._list_coda`;
* `ResiRepository.list_da_accreditare` con `ddt_id`/`ordine_id`: idem, se il
  builder condiviso lo permette senza un secondo ramo; altrimenti resta sulla
  vista (paga tutto, come oggi).

### 9.5 Le prove (owner, `BEGIN … ROLLBACK`, SQL estratto dai sei change)

* **Forma**: le due funzioni `BEGIN ATOMIC`, non `DEFINER`, con
  `fn_partite_merce` fra i `refobjid` in `pg_depend` (più
  `fn_ordine_riga_qta_riconsegna`, `fn_resi_riga_accreditato_partita`,
  `fn_resi_riga_residuo_riconsegna`, `fn_check_accredito_annullabile`);
  le viste con `security_invoker=on`, 21 colonne con `ordinato numeric(18,6)`,
  27 colonne coi cinque typmod; `pg_get_function_identity_arguments`,
  `pg_get_function_result` e `prosecdef` dei due verbi identici al vivo.
* **Equivalenza sui dati vivi** (colore): `EXCEPT ALL` a zero nei due versi fra
  `fn(NULL,NULL)` e la vista (121 righe; coda 1 riga); per **ognuno** dei 105
  ordini con righe attive (`fn(NULL, ARRAY[o])` vs `WHERE ordine_id`); per
  ognuno dei 51 DDT (`fn(ARRAY[d])` vs la vista con l'`EXISTS` del BE); per la
  coda, per ogni DDT (`ddt_id`) e per ogni ordine (predicato del BB); i tetti
  identici alla forma di prima per tutte le 21 righe di reso, e 0 su una riga
  inesistente.
* **Forma del piano in piano generico** (`PREPARE` + `force_generic_plan` +
  `enable_seqscan = off`): per ordine, per DDT, coda per DDT e per ordine —
  `Bitmap Index Scan` su `uq_ddt_vendita_r_riga_nr`/`uq_ordrig_riga_nr`,
  `Index Only Scan` su `uq_ordini_r_ful_v_pair`, rami «tutti» `never
  executed` dietro `One-Time Filter: (($1 IS NULL) AND ($2 IS NULL))`, **zero**
  `Filter: (($1 IS NULL) OR …)`; `af` intera (D5). In modo «tutti» le
  scansioni della situazione sono **le stesse** della vista (33/33); per la
  coda stesse tabelle e stesso numero di accessi, con un join che cambia
  metodo (costo, non forma).
* **I presidi nuovi**: 11/12 + 11/12 da owner; i due **12** (scope) sono rossi
  da owner perché l'owner salta la RLS — come il 14 del giro 1 e l'11 di
  `test-vw-situazione-merce-ordine-v1`. I casi che contano — il DDT di mezzo
  (5), la riga `MULTIPLA` (9 e 7), le sorelle (4, 5), il verbo (8) — sono
  verdi **per i numeri attesi**, non solo per l'uguaglianza con la vista.
* **I diciassette presidi esistenti** sopra lo stesso SQL, ciascuno nella
  propria transazione con l'SQL estratto in testa, confrontati con la corsa
  **senza**: esiti identici file per file — `test-vw-situazione-merce-ordine-v1`
  16/17, `test-situazione-merce-ritardo-v1` 11/11,
  `test-vw-resi-da-accreditare-contatore-v1` 10/10, `test-fn-accredita-riga-reso-v1`
  14/14, `test-annulla-accredito-riga-reso-v1` 23/23, `test-accredito-kit-meta-v1`
  8/8, `test-resi-motore-v1` 27/27, `test-rinuncia-gate-accredito-v1` 10/10,
  `test-annulla-reso-gate-accredito-v1` 11/11, `test-resi-rinunce-scenario-v1`
  9/9, `test-vw-dash-backlog-resi-v1` 7/7, `test-vw-contatore-merce-v1` 11/11,
  `test-porta-oneri-contatore-cieco-v1` 5/5, `test-vw-partite-merce-v1` 11/11,
  `test-fn-partite-merce-chiusura-v1` 13/14, `-riconsegna-dopo-nc-v1` 8/8,
  `rls/test-rls-viste-security-invoker` 7/7 — e le cinque viste della partita
  (`vw_partite_merce`, `vw_contatore_merce`, `vw_resi_da_accreditare`,
  `vw_situazione_merce_ordine`, `vw_dash_backlog_documenti`) restano dentro
  `_tocca_rls` con `invoker = true` attraverso le due funzioni annidate.
* **Il guardrail dei riferimenti morti** sopra lo stesso SQL: OK
  (`fn_accredita_riga_reso` chiama la funzione nuova e `plpgsql_check` la
  risolve). **I sette cancelli statici**: tutti OK. `liquibase updateSQL`
  offline dei sei change (copie senza `preConditions`): rendono tutti.
* ⚠️ **Non provato col jar di pgjdbc**: la forma dei due `BEGIN ATOMIC` è
  identica a quella del `-21` (il `COMMENT` in un change suo), provata il
  21-09 pomeriggio.

### 9.6 Cosa resta, nell'ordine

1. ✅ apply dei sei changeSet — **Tid, 21-09 alle 18:43** (`databasechangelog`,
   tutti `EXECUTED`, anche sullo scratch `zeroerp_ci`); pgTAP di Tid verdi;
   i due presidi nuovi **12/12 come app** su dbdev (gli scope si chiudono con
   la RLS attiva). ⚠️ Il solo rosso della corsa sullo scratch —
   `ui/test-lista-definizione-perimetro-emittente-v1` test 6 — non era di
   questo giro: `magazzino.lotti` dichiarata globale dal cantiere BE di
   stamattina (PR #1633) senza il nome nell'elenco del pgTAP, residuo che quel
   piano assegnava al team DB; scritto la sera stessa;
2. ✅ la misura come app: §9.7;
3. ✅ commit con la doc auto-gen rigenerata — `559dbf351`, PR #1635;
4. 🔵 D6 (`vw_contatore_merce`), decisione di Tid;
5. ✏️ giro 3 (D4, B2) **scritto** (§10), ⏳ apply di Tid; poi giro 4 (D5);
   richieste BE §8.4 e §9.4 — ✅ **fatte il 21-09 sera** (BB `sorgente_per_documento`).

### 9.7 La misura «dopo» (dbdev, 21-09 dopo l'apply, `zeroerp_app` con contesto operatore, 121 righe d'ordine / 36 partite / 1 riga in coda, media delle chiamate 8–10 di 10 nella stessa sessione, righe valutate intere — colore, non motivo)

Il «prima» per documento è la vista intera: il filtro non entrava (§1), quindi
la lettura per documento costava quanto la vista.

| Lettura | Prima (= vista intera) | Dopo |
| --- | --- | --- |
| `vw_situazione_merce_ordine` intera | 187 ms | **187 ms** — invariata, com'è giusto |
| situazione per ORDINE (`fn(NULL, ARRAY[o])`) | ~187 | **20 ms** |
| situazione per DDT (`fn(ARRAY[d], NULL)`) | ~187 | **41 ms** |
| `vw_resi_da_accreditare` intera | 115 ms | **115 ms** — invariata |
| coda per DDT | ~115 | **36 ms** |
| coda per ORDINE | ~115 | **16 ms** |
| `fn_resi_riga_tetti_accredito` (il guard, a ogni riga di ponte; `DEFINER`, quindi sopra la RLS) | ~9–14 ms da owner (§9.3.4) | **1.3 ms** |
| controprova giro 1: `vw_partite_merce` intera / partita di UN DDT | 88 / 24 (§8.6) | 96 / 29 |

⭐ Sotto RLS il rapporto è quello del modello, non quello da owner (§9.3.4):
ogni riga scandita paga la sua policy, e la chiusura ne scandisce poche. Il
guard dei tetti, che gira come owner, ci guadagna per un'altra via: il piano
della coda ristretta sta nella plancache della funzione. Il backend, finché
resta sulle viste (§9.4), paga ancora la colonna «prima».

## 10. Giro 3 (D4, forma B2) — cosa è stato scritto e provato (21-09 sera)

### 10.1 Il censimento, prima di scrivere

Dal catalogo vivo (`pg_depend`, `pg_proc.prosrc`, `pg_views`), dal backend e
dai pgTAP:

| Cosa | Esito |
| --- | --- |
| dipendenti di `fn_ddt_push_diagnosi` in `pg_depend` | **nessuno** (nessuna vista sopra): il `DROP` non cascada |
| chi la chiama | solo `script.fn_available_actions_ddt`; il lister la nominava nei commenti |
| chi chiama il lister | la capability, il BE (`count_righe_pushable`, `_SORGENTE_FN_MAP` della pipeline — contratto a 26 colonne condivise + `riga_id`), e due funzioni **nei soli commenti** |
| pgTAP che nominano la diagnosi | uno solo (`reason-catch-all-v1`, test 1 e 8); il lister ne ha sette, la capability sei |
| dominio di `fn_get_stato_push_segment` | esattamente `LIBERA` / `ALLOCATA` / `EMESSA`: `DDT_ROUTED` (rank 4) ⟺ segment ≠ LIBERA |
| `catalogo.articoli` | **senza RLS**, `ddt_righe.articolo_id` NOT NULL: l'`INNER JOIN` del lister non esclude mai |
| `anagrafiche.billing_account` | **con RLS**: l'`INNER JOIN` del lister era un predicato non dichiarato («BA visibile») |
| guard su `ddt_righe.attivo` | solo i `block_deact` delle figlie: **D7** |

### 10.2 I file

| Cosa | File |
| --- | --- |
| la diagnosi, `DROP` + `CREATE … BEGIN ATOMIC`, quattro colonne in più | `20_code/vendite/20260921-32-recreate-fn-ddt-push-diagnosi-fonte-unica-b2` (tre change: DROP, funzione da sola, COMMENT) |
| il lister che deriva dalla diagnosi | `20_code/vendite/20260921-33-update-fn-list-ddt-da-pushare-deriva-dalla-diagnosi` |
| la capability a una lettura | `20_code/script/20260921-34-update-fn-available-actions-ddt-partita-a-una-lettura` (generato dal dump vivo: solo intestazione e blocco del push cambiano) |
| il presidio, riscritto | `db/pgtap/script/test-fn-available-actions-ddt-reason-catch-all-v1.sql` (8 → 16, fixture coi builder) |
| manuali | `fn_ddt_push_diagnosi.md` (riscritto: undici cause, i quattro fatti, chi ne deriva), `fn_list_ddt_da_pushare.md`, `fn_available_actions_ddt.md`, `fn_partite_merce.md` (chiamanti), `fn_get_stato_push_segment.md`, `ddt.md`; guida `gestione-ddt.md` §11 |

### 10.3 La forma, e le tre cose che non erano nel piano

1. **La diagnosi espone quattro colonne, non due.** §2-bis.8 diceva
   «`segment` e `differenza`». Scrivendo il lister derivato è emerso che ogni
   fatto che il lister avrebbe ricalcolato è una seconda copia di una regola
   della diagnosi: il BA (`COALESCE(testata, ordine sorgente)` — e ora letto
   **attraverso** `billing_account`, così la rank 3 copre anche il BA
   invisibile sotto RLS, che prima l'`INNER JOIN` del lister escludeva in
   silenzio), la riga d'ordine sorgente (il «primo fulfillment per id»), la
   **dose** (`GREATEST(0, LEAST(quantita, differenza))`, che la rank 11 già
   giudicava). Quindi `billing_account_id`, `ordine_riga_id`, `segment`,
   `quantita_push`; la differenza grezza non serve a nessuno (la partita per
   riga la dà già `fn_partite_merce`) e avrebbe fatto ricopiare il cap.
2. **Il seme del documento nella diagnosi era un `p IS NULL OR`.** La rev del
   giro 1 aveva lasciato `WHERE (p_ddt_id IS NULL OR d.id = p_ddt_id)` su
   `vendite.ddt`: in piano generico è una scansione intera della tabella
   sotto policy — O(documenti), nel posto da cui la quarta leva li aveva
   tolti. Ora è una CTE `docs` a due rami in `UNION ALL`; provato: `Index
   Cond: (id = $1)` e `One-Time Filter: ($1 IS NULL)` davanti al ramo «tutti».
3. **Il perimetro della precedenza `GIA_*` cambia di un caso, dichiarato.** I
   due `EXISTS` di prima scandivano `ddt_righe` senza guardare `attivo`; la
   diagnosi guarda le righe **attive** — lo stesso perimetro della partita e
   del lister. La differenza si raggiunge solo con una riga instradata e poi
   disattivata su un DDT emesso: il modello lo ammette (D7), e la risposta
   giusta lì è un guard, non una capability che riporta una riga fantasma.
   Il filtro `motivo <> 'DDT_ROUTED'` sul `min(rank)` è caduto: una riga
   ROUTED ha per definizione segment `ALLOCATA` o `EMESSA`, quindi non arriva
   mai al ramo del motivo.

La capability legge la diagnosi con **una** `SELECT` aggregata:
`bool_or(motivo IS NULL)`, `bool_or(segment = 'ALLOCATA')`,
`bool_or(segment = 'EMESSA')`, `(array_agg(motivo ORDER BY motivo_rank) FILTER
(WHERE motivo IS NOT NULL))[1]`. Il resto del corpo è byte-identico al vivo:
il changeSet è generato da uno script che sostituisce solo intestazione e
blocco del push (`gen_34.py` nello scratchpad).

### 10.4 Il presidio riscritto

Il test 1 di prima (`EXCEPT` lister/diagnosi nei due versi sulle righe vive)
con B2 è la stessa query: al suo posto **casi costruiti** — l'eleggibile letto
a tre voci (diagnosi: motivo NULL, dose 10, LIBERA, il BA costruito; lister:
quella riga con 10; capability: `true|-|-`), `ALLOCATA` → `GIA_INVIATO` con il
lister a zero righe, `EMESSA` → `GIA_FATTURATO`, e la **precedenza del
segmento sul documento annullato** (`DDT ANNULLATO` + riga `ALLOCATA` →
`GIA_INVIATO`, l'ordine di prima che B2 deve conservare e che nessun pgTAP
costruiva). Più la coerenza delle quattro colonne con le rank, il pin di
**forma** di D4 (il corpo del lister, senza commenti, nomina la diagnosi e non
`fn_partite_merce` né `fn_get_stato_push_segment`; la capability non nomina il
lister né il classificatore; la diagnosi è `BEGIN ATOMIC` non `DEFINER`) e lo
scope come app. La fixture è coi builder (`fn_pgtap_crea_cliente_ba`,
`fn_pgtap_crea_articolo`, niente `current_user_id = '1'`): il file era in
`baseline-rossi-ci` come `ERRORE_FIXTURE` — se in CI torna verde, la corsa lo
stampa RIENTRATO e `pgtap-baseline-ci-rientrati.sh` lo toglie. ⚠️ Le
attività EMESSA si costruiscono **prima** di quelle ALLOCATA:
`fn_emit_attivita_fatturabili_da_commessa` emette tutto ciò che trova.

### 10.5 Le prove (owner, `BEGIN … ROLLBACK`, SQL estratto dai tre change)

* **Forma nel catalogo**: diagnosi `prosqlbody` non nullo, non `DEFINER`,
  `STABLE`, `RETURNS TABLE(… billing_account_id, ordine_riga_id, segment,
  quantita_push)`; in `pg_depend`: `billing_account, causali_trasporto, ddt,
  ddt_righe, fn_get_stato_push_segment, fn_partite_merce, ordini,
  ordini_righe, ordini_righe_fulfillment, stati_doc_ddt`. Lister e capability:
  `identity_arguments`, `prosecdef`, `provolatile` identici al vivo, `RETURNS`
  del lister identico (md5); una funzione per nome.
* **Equivalenza sui dati vivi** (colore, 51 DDT / 54 righe): lister «tutte»
  4 = 4 e `EXCEPT ALL` a zero nei due versi; lister **per ognuno** dei 51 DDT
  identico; le quattro colonne vecchie della diagnosi identiche riga per riga;
  **il blob della capability identico per tutti i 51 DDT** — e la popolazione
  esercita tutte e sette le reason (`SOLO_TRASPORTO` 20, `FATTURA_DA_ORDINE`
  14, generico 8, eleggibili 3, `MERCE_IN_VIAGGIO` 3, `GIA_FATTURATO` 2,
  `GIA_INVIATO` 1). Coerenza delle colonne nuove: 0 incoerenti.
* **Piano generico** (`PREPARE` + `force_generic_plan` + `enable_seqscan =
  off` sulla diagnosi con parametro): `Index Cond: (id = $1)` sul seme del
  documento, `One-Time Filter: ($1 IS NULL)` davanti alla scansione «tutti»,
  **zero** `Filter: (($1 IS NULL) OR`; dentro, la chiusura di
  `fn_partite_merce` con i suoi One-Time Filter. La diagnosi si **inlina**
  (nessun `Function Scan`, `CTE semi` una volta); lister chiamato sei volte
  con lo stesso id e capability dopo: stessi risultati.
* **I venti presidi esistenti** sopra lo stesso SQL, ciascuno nella propria
  transazione, confrontati con la corsa **senza**: esiti identici —
  `test-fn-list-ddt-da-pushare-contatore-v1` 7/7, `-v1` 12/12, `-v2` 5/5,
  `-orfano-v1` 5/5, `test-ddt-solo-trasporto-causale-v1` 6/6,
  `test-fatturazione-immediata-simmetria-sorgenti-v1` 20/20,
  `test-ddt-read-side-v1` 17/17, `reason-catch-all-v1` **vecchio** 8/8,
  `test-capability-motivi-e-nessuna-azione-v1` 13/13,
  `test-available-actions-requires-righe-v1` 15/15, `-pdf-v1` 5/5,
  `test-capability-annulla-aspetto-e-stato-leggibile-v1` 8/8,
  `test-fn-check-ddt-emittibile-v1` 10/10, `dbops/test-riferimenti-morti-v1`
  9/9, `script/test-rubinetto-primo-motivo-v1` 7/7,
  `test-fn-list-ordini-da-pushare-v3` 10/10,
  `test-ordini-fatturazione-trigger-eredita-v1` 5/5,
  `test-fn-genera-ddt-riconsegna-eredita-v1` 17/17,
  `test-fn-partite-merce-chiusura-v1` 13/14 (il 14 è lo scope, da owner),
  `rls/test-rls-viste-security-invoker` 7/7.
* **Il presidio nuovo**: 15/16 da owner; il **16** (scope) è rosso da owner
  perché l'owner salta la RLS, come il 14 della chiusura. Senza i changeSet il
  file muore (18 errori): legge colonne che non esistono ancora — è il verso
  giusto.
* **I guardrail SQL** della CI sopra lo stesso SQL: `guardrail_riferimenti_morti`
  OK (plpgsql_check risolve la diagnosi nuova nel lister e nella capability),
  `guardrail_codice_errore_strutturato` OK. **I sette cancelli statici**: OK.
  `liquibase updateSQL` offline dei tre (copie senza `preConditions`): rende
  tutti e tre, `DROP` / `CREATE … BEGIN ATOMIC … END;` / `COMMENT` in tre
  istruzioni separate.
* ⚠️ **Non provato col jar di pgjdbc**: il `-32` ha la stessa forma del `-21`
  (funzione `BEGIN ATOMIC` da sola nel suo `sql:`, `COMMENT` in un change suo;
  in più il `DROP` in un change suo), provata il 21-09 pomeriggio.
* ⚠️ **Nessuna misura come app**: `titodb` non è membro di `zeroerp_app` e la
  DDL vuole l'owner, quindi la prova sotto RLS del corpo nuovo non si fa
  prima dell'apply. Il «prima» come app è in §8.6 (capability 175 ms, di cui
  ~50 lister + ~25 diagnosi): la misura «dopo» va presa dopo l'apply e
  scritta qui con la data.

### 10.6 Cosa resta, nell'ordine

1. ✅ apply dei tre changeSet — **Tid, 21-09 sera**;
2. ✅ pgTAP di Tid: **nessuna regressione**; doc auto-gen rigenerata
   (`funzioni/fn_ddt_push_diagnosi.md` mostra il corpo `BEGIN ATOMIC` con le
   otto colonne, il lister e la capability nuovi);
3. ✅ la misura come app: §10.7 — e ha portato **D8**;
4. ⏳ commit;
5. 🔵 D6 (`vw_contatore_merce`), **D7** (`ddt_righe.attivo` senza guard) e
   **D8** (il classificatore del segmento per riga), decisioni di Tid;
6. ⏳ giro 4: D5 **con** D8(a) — l'indice `text_pattern_ops` su
   `commesse_attivita.segment_key` serve a entrambi; ✅ richieste BE §8.4 e
   §9.4 **fatte il 21-09 sera** (nessuna nuova da questo giro: blob della
   capability e contratto del lister invariati).

### 10.7 La misura «dopo» (dbdev, 21-09 sera dopo l'apply, `zeroerp_app` con contesto operatore, 51 DDT / 54 righe attive / 112 attività di commessa, media delle chiamate 6–10 di 10 nella stessa sessione — colore, non motivo)

| Lettura | Prima (§8.6, stesso giorno) | Dopo |
| --- | --- | --- |
| `fn_available_actions_ddt` (il drawer) | 175 ms | **50 ms** |
| `fn_ddt_push_diagnosi(d)` | 25 | 27 |
| `fn_list_ddt_da_pushare(p_ddt_id)` | 52 | 31 |
| `fn_list_ddt_da_pushare()` senza documento (cockpit, lista push) | **214** | **663** ⚠️ |
| `fn_ddt_push_diagnosi()` tutte | — | 348 |
| `fn_get_stato_push_segment` × le 54 righe attive | — | 401 (7.6 a chiamata) |
| `fn_partite_merce(NULL, NULL)` | 88 | 92 |

**La capability paga un terzo.** I ~100 ms «fuori da lister e diagnosi» che
§8.6 dava come prossimo bersaglio erano in gran parte i due `EXISTS` su
`fn_get_stato_push_segment` riga per riga: oggi il segmento lo calcola la
diagnosi una volta.

**La regressione, e da dove viene.** Il lister senza documento è la lista del
push e del cockpit. Prima di B2 la sua `cand` era un'unica `SELECT` con i
predicati nel `WHERE`: il planner valutava per ultimo il classificatore (costo
100) e solo sulle righe sopravvissute a causale, partita e stato — poche.
Ora la diagnosi calcola `segment` come **colonna di `cand`**, per ogni riga
attiva di ogni DDT, e deve: la capability legge il segmento anche sulle righe
escluse da un'altra rank (un DDT annullato con una riga instradata dice «già
inviato», §10.4 test 11). Cinquantaquattro chiamate a 7.6 ms sono 400 dei 663.
⛔ Il numero non decide niente; sul **modello** il fatto è che il classificatore
è O(attività di commessa) **per riga**, sotto una policy che viene valutata
prima del predicato perché `textlike` non è leakproof — cresce con le attività
(cioè con le fatture) e con le righe: è la stessa famiglia del pavimento di
`af` (D5), e la strada è la stessa (D8). Fino a lì il cockpit paga quanto la
diagnosi di tutto.

⚠️ La regressione è **dichiarata, non accettata**: se il giro 4 tardasse, la
lista del push pagherebbe 3× a ogni apertura del cockpit. D8(a) non passa
dalla policy FK (non è una chiave): è un changeSet `00_schema`
(`CREATE INDEX … (segment_key text_pattern_ops)`, naming `ix_<tabella>_<colonna>_tpo`
da verificare su `dbops.vw_duplicate_indexes`), da scrivere nel giro 4 — ed è
lo **stesso** indice di D5.
