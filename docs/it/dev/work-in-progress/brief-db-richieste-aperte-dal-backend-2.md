# Richieste aperte dal backend — elenco **2**

> **Destinatario:** team DB (`dev/db-tid`). ⭐ **È un ORDINE DI LAVORO, non un
> brief di analisi**: qui c'è *cosa fare*, con lo stato verificato. Il *perché*
> sta nei brief linkati e **non viene ricopiato**.
>
> **Perché un file nuovo e non il precedente riaperto.** Perché lo dice il
> precedente, ed è la regola giusta:
> *«Se arrivano richieste nuove dal backend, NON si riapre questo file: è chiuso
> perché il suo elenco è esaurito, e un ordine di lavoro che si riapre smette di
> dire cosa è finito. Se ne fa uno nuovo, con la stessa forma.»*
> ([elenco 1](../work-done/brief-db-richieste-aperte-dal-backend.md), chiuso il
> 2026-08-31 con tutte e cinque le voci applicate).
>
> **Stato.** 2026-08-31 (4) — ✅ **entrambe le voci sono chiuse e applicate.**
> Le due righe di `task_policy` che mancavano alla voce 1 sono state scritte
> (id 26 e 27) e applicate dal migrate delle 21:47: il cancello BE
> `test_ogni_task_in_pipeline_ha_una_task_policy` è **verde** — 0 task senza
> policy, replicato sul database vivo, e le tre soglie di
> `test_la_misura_non_e_degradata` sono rispettate (27 / 22 / 27 contro 12 / 20 / 20).
>
> ✅ **E il residuo della voce 2, che si è avverato in giornata, è già chiuso**:
> la check copriva 3 figli su 6 per qualche ora — `ordini`, `ddt` e `resi` sono
> arrivati col cantiere della numerazione — e il changeSet `20260831-71` delle
> 22:05 la porta a **sei**, allineata ai trigger montati. ⚠️ In fondo al §2 resta
> scritto **l'errore di metodo** con cui la cosa era stata argomentata: vale più
> del rilievo.
> Verificato sul repo **e sul database**, non ricordato.

---

## 🔎 Cosa resta ATTIVO (verificato sul database, 2026-08-31 notte)

> Le **due voci** dell'ordine di lavoro sono chiuse e applicate. Ciò che resta
> non è più «richiesta del BE»: sono **tre code**, ognuna con un destinatario
> diverso, più una frase di questo file che dichiara aperto ciò che è chiuso.

| # | Cosa | Di chi | Stato verificato |
| --- | --- | --- | --- |
| A | le **sei** `reason_key` di `disattiva_blocco.*` non sono nei locales | **FE** | `it.json` e `en.json`: 0 su 6 |
| B | `automation_fk_exclusions.csv` è un CSV **senza tabella** | DB | tabella assente, CSV presente |
| C | `automation_rules_tbl.params`: 3 chiavi con **zero** consumatori | DB | `pg_proc` → 0, 0, 0 |
| D | §2 dice ancora «la strada giusta è generica, decisione a Tid» | doc | ⛔ **decisa il contrario** in fondo al file |

### A · Il debito i18n è di SEI chiavi, non di tre — e il presidio ne vede solo tre

⛔ **Nessuna** delle sei è nei locales: mancano anche `ha_fatture`,
`ha_progressivi`, `ha_mapping_tipo_doc`, non solo le tre nuove.

⚠️ **E il presidio su cui questo file si appoggia è cieco proprio sulle tre
nuove.** `scripts/check_i18n_keys.py` oggi **fallisce** — `[X] 3 CHIAVI EMESSE
DAL DB e assenti dai locales` — ma le tre che nomina sono le **originali**. Le
tre di `20260831-71` non le vede, perché il guard estrae le chiavi dal **corpo
delle funzioni nella doc auto-gen** (`docs/it/dbzero`, non `pg_proc`), e quella
doc è ferma alle **21:37** mentre il changeSet è delle **22:05**.

⇒ La frase *«vanno aggiunte ai locales, o `check_i18n_keys.py` fallisce»* è vera
a metà: sulle tre nuove il cancello tacerà **finché la doc non viene
rigenerata**. Non è un difetto del guard — è la stessa premessa che salta per
tutti: *la doc auto-gen riflette il vivo solo se è stata rigenerata*.

📌 **Il lavoro è del FE** (locales `it`/`en`), e sta qui come richiesta, non come
compito del DB. Al DB non resta niente su questa voce: i sei `reason_key` sono
già emessi correttamente dalla funzione.

### B · `automation_fk_exclusions.csv` — un seme senza terreno

✅ **Confermato misurando**: `dbops.automation_fk_exclusions` **non esiste**
(droppata da `20260101-01-drop-attivo-legacy-objects`), e
`80_data/sql/dbops/automation_fk_exclusions.csv` **c'è ancora**.

⚠️ Otto changelog lo nominano, ma sono tutti **storici** — compreso il drop
stesso e la `legacy/baseline_v2`. Nessun loader vivo lo legge.

⇒ **Va cancellato il file**: è la stessa regola dell'oggetto ritirato che lascia
la scheda in `manual/` — un moncone resta pubblicizzato, e chi lo trova conclude
che il meccanismo esista. È già successo, in questo stesso brief.

### C · Tre chiavi di `params` che nessuno legge

✅ **Confermato su `pg_proc`**: `block_if_child_no_attivo`, `cascade_children`,
`include_no_action` hanno **zero** consumatori, e **una** riga di
`dbops.automation_rules_tbl` le dichiara.

⇒ O si implementano, o **escono**. Un catalogo che dichiara più di quanto esegue
prima o poi convince qualcuno a sceglierne una — è il difetto di `reset_policy`,
già pagato una volta.

### D · Una frase che dichiara aperto ciò che è chiuso

Il riquadro del §2 chiude ancora con: *«La strada giusta non è per tabella ma
generica … **Decisione a Tid**»*. ⛔ Quella decisione **è stata presa**, ed è
l'opposto: l'elenco delle figlie **resta scritto a mano**, perché un elenco
derivato da `pg_trigger` inventerebbe una `reason_key` che nessuno ha tradotto —
un difetto muto in produzione al posto di un rosso in sviluppo. Ragionamento
completo in fondo al file.

⚠️ Va letta come **superata**, non come una domanda ancora aperta: è la forma di
debito documentale che costa di più, perché chi la incontra riapre un cantiere
già deciso.

---

## L'ordine

```text
1. task di pipeline «consuma_plafond_lotto»       ✅ FATTO 31/08 (seed + policy 26/27)
2. fn_check_registro_disattivabile                ✅ FATTO 31/08 (20260831-38)
   └─ ✅ estesa a SEI guard da 20260831-71 (22:05)
```

✅ **La prima è FATTA.** Il task è registrato, ha il suo handler ed è **in
testa** a entrambe le pipeline: `anagrafiche.fn_consuma_plafond_titolo_iva`, che
non aveva **nessun chiamante possibile**, ora ce l'ha.

✅ **E le due righe di `fatturazione_pipeline_task_policy` ci sono** (id 26 e 27,
scritte e applicate il 2026-08-31 sera), con i valori esatti del calco chiesto
qui sotto: `annullabile=false`, `RESUME_TASK`, `meta` con lo `scope`. Il cancello
BE è **verde**.

✅ **La seconda è FATTA** (`script.fn_check_registro_disattivabile`, changeSet
`20260831-38`): forma del §12.5.1, `SECURITY DEFINER`, tre `reason` senza
prefisso `E_`, nessun codice errore nuovo. ⚠️ Con un residuo dichiarato al §2,
che **non blocca** il CRUD: la check elenca i tre figli a mano mentre le madri
sono l'automazione generica, quindi i due elenchi possono divergere.

---

## 1. ✅ Il task di pipeline che consuma il plafond — FATTO

> ✅ **APPLICATA E CHIUSA il 2026-08-31.** Tutto ciò che questa voce
> chiedeva è stato fatto **come chiesto**: il task è **in testa** allo step
> DEFINITIVA su **entrambe** le pipeline (4 e 6), e ⭐ **senza chiave `fn`** —
> nessuna madre SQL, che era il rischio nominato qui sotto. Verificato sul seed
> **e** sul database vivo.
>
> ⛔ **Ciò che questa voce NON chiedeva, e avrebbe dovuto**: le due righe di
> `fatturazione_pipeline_task_policy`. Il cancello BE è rosso, e il difetto è del
> documento — vedi la CORREZIONE qui sotto.
>
> ⇒ Lo smoke che questa voce chiedeva è scritto e verde:
> `backend/scripts/tests/smoke-consuma-plafond-lotto.py`, **21 controlli** —
> compreso il gemello «senza titolo non succede niente» e la prova che la vista
> mostra le due parti come **righe sorelle**.
>
> ⭐ **Il plafond si consuma davvero**: 24 pezzi diventano 12 + 12, l'IVA del
> titolo sulla parte coperta e l'ordinaria sul resto, un movimento nel registro
> e l'accumulatore che lo vede. Il registro costruito in Fase 2 non è più una
> promessa.

📌 **Il ragionamento è già scritto**, e non si ricopia: `P5` e `N3` del
[piano BE/FE di Fase 3](../work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md),
sezione `F3-b2`.

### Il fatto

Il consumo del plafond deve avvenire in un momento preciso, e il piano lo fissa:

```text
per ogni fattura del lotto, ORDER BY data documento, numero   ← P5
   risolvi con l'imponibile VERO
   spezza le righe                      ← fattura ancora EMESSA
   consuma il plafond                   ← fn_consuma_plafond_titolo_iva
   porta a DEFINITIVA                   ← da qui congela
```

⇒ È un **task di pipeline nello step DEFINITIVA**, e va **prima** di
`numera_fatture`: lì la fattura è ancora `EMESSA`, e
`trgfn_fattura_satellite_guard_congelamento` legge lo stato **vivo** al momento
della scrittura — dopo, la spezzatura verrebbe rifiutata.

⛔ **E i task della pipeline sono un SEED, non codice.** Verificato il
2026-08-31 su
`db/changelog/migrations_v2/80_data/sql/vendite/fatturazione_pipeline.csv`: lo
step DEFINITIVA contiene oggi, su **due** pipeline, esattamente

```text
 4  Pipeline massiva (DEFINITIVA)      ['numera_fatture', 'popola_fatture_rettifiche', 'stampa_documenti_lotto']
 6  Pipeline giornaliera (DEFINITIVA)  ['numera_fatture', 'popola_fatture_rettifiche', 'stampa_documenti_lotto']
```

⇒ Il backend può scrivere l'handler, il servizio e i suoi test per intero, ma
**niente lo invocherebbe**.

✅ **E infatti li ha scritti** (2026-08-31, `F3-b2`): `PlafondFatturaService`,
il gestore `consuma_plafond_lotto`, la voce in `ALLOWED_TASK_FUNCTIONS`, i
metodi di repository e **14 test provati per mutazione**. ⛔ Manca **solo** la
riga di configurazione: senza, il task non viene mai chiamato.

⭐ **E una cosa è già in guardia**: `_TASK_ORDER_DEPENDENCIES` dichiara da adesso
`numera_fatture → consuma_plafond_lotto`. Finché il task non è nel seed la riga
non fa nulla (un predecessore assente è una configurazione valida); il giorno
che arriva, se arriva **girata** lo step si ferma **prima** che il primo task
scriva, invece di scoprirsi a documenti già numerati. È la stessa rete che il
codice descrive per `genera_scadenze_lotto`: *«la configurazione la scrive un
altro team»*.

### La richiesta

**Aggiungere il task `consuma_plafond_lotto` in TESTA al `processi` delle
pipeline `4` e `6`**, prima di `numera_fatture`:

```json
{"task":"consuma_plafond_lotto","fase":"Consumo plafond titoli IVA",
 "params":{"implementation_key":"default"}}
```

⚠️ **In testa e non in coda**: dopo `numera_fatture` la fattura è già oltre la
soglia di congelamento, e la spezzatura verrebbe **rifiutata** — non
silenziosamente, ma con un errore che parla d'altro e in un punto dove nessuno
lo cerca.

⚠️ **Su entrambe le pipeline, non su una.** Una sola sistemata darebbe un
comportamento che dipende dal *tipo di lotto*: il plafond consumato sui lotti
giornalieri e non su quelli massivi, e nessuno se ne accorgerebbe finché i conti
di un esportatore abituale non tornano.

### 🔴 CORREZIONE 2026-08-31 (3) — la riga di `task_policy` È obbligatoria

> ⛔ **Questo brief diceva il falso, e il team DB ha giustamente seguito ciò che
> c'era scritto.** La frase era:
> *«Verificato: `popola_fatture_rettifiche` gira nelle stesse due pipeline e
> **non ne ha una** — quindi non è obbligatoria.»*
> **Rimisurato sul DB: ne ha DUE, attive** — come tutti e tredici i task in
> pipeline. Quel «Verificato» non era stato eseguito.

⛔ **E non è una preferenza: c'è un cancello BE che lo pretende**, preesistente e
oggi **rosso** — `apps/vendite/tests/db/test_pipeline_task_handler_guardrail.py`,
`test_ogni_task_in_pipeline_ha_una_task_policy`:

```text
AssertionError: ['pipeline 4: consuma_plafond_lotto',
                 'pipeline 6: consuma_plafond_lotto'] != []
  task in pipeline senza riga attiva in vendite.fatturazione_pipeline_task_policy:
  girerebbero senza tracing ne' resume
```

⚠️ **Il motivo, scritto nel test stesso**: *«senza policy il task gira CIECO:
niente `task_run`, niente resume — un fallimento non lascia traccia e il
rilancio non riprende»*. Su un giro di documenti fiscali è il difetto peggiore:
non si ferma, non si vede, e non si può riprendere.

✅ **Cosa è già a posto** (verificato sul DB, non sullo YAML): il task è **in
testa** a entrambe le pipeline, `dbops.pipeline_task_registry` id 22 e
`..._registry_impl` id 22 (`default` → `consuma_plafond_lotto_default`) ci sono
e sono attivi.

⛔ **Mancano due righe**, e il calco è `popola_fatture_rettifiche`, che gira
nelle stesse due pipeline nello stesso step:

| `pipeline_id` | `annullabile` | `resume_mode` | `attivo` | `meta` |
| --- | --- | --- | --- | --- |
| **4** | `false` | `RESUME_TASK` | `true` | `{"scope": "DEFINITIVA"}` |
| **6** | `false` | `RESUME_TASK` | `true` | `{"scope": "DEFINITIVA", "tipo_lotto": "GIORNALIERO"}` |

⭐ **`RESUME_TASK` e non `RESUME_LOTTO`**: il consumo del plafond è per fattura e
scrive movimenti: al rilancio si riprende **da quel task**, non si rifà il giro.
È la stessa scelta del vicino, che spezza righe nello stesso step.

⭐ **La lezione, e vale oltre questo caso.** La frase sbagliata è nata
guardando **una** tabella e generalizzando; sarebbe bastato contare le righe
(`13 task, 13 con policy`) o leggere il test che quella regola la presidia da
prima. *Un «Verificato:» scritto senza eseguire la misura è peggio di nessuna
verifica: chi legge smette di controllare.*

### Cosa blocca

`F3-b2`, cioè la **seconda metà di `I4`**: la riga di fattura che si spezza
quando il plafond copre solo una quota, e il consumo che ne segue.

⛔ E con essa l'intero senso di Fase 2: il registro dei titoli IVA, i movimenti,
l'accumulatore e l'annullo delle forzature esistono e sono provati, ma
**nessuna fattura li tocca**. `fn_consuma_plafond_titolo_iva` ha **zero
chiamanti** — verificato.

### ⛔ Il prerequisito che questo brief non aveva: il task va REGISTRATO

> **Trovato il 2026-08-31 eseguendo la voce**, prima di scrivere le due righe.
> ⚠️ È lo stesso schema che il §«Come si decide» racconta, applicato a questo
> file: un artefatto che sembrava uno, ed è **tre**.

⛔ **Le due righe di JSON, da sole, avrebbero fatto morire lo step a runtime.**

L'executor **non prende l'handler dalla lista**: per ogni task chiama
`repository.get_task_handler_code(...)` →
`dbops.fn_get_pipeline_task_implementation(dominio_id, task_code,
implementation_key)`, e solo con il `handler_code` che ne esce cerca nel proprio
`handler_registry` Python
([pipeline_step_executor.py:341](../../../../backend/apps/vendite/services/pipeline_step_executor.py)).

E `consuma_plafond_lotto` **non era a catalogo**. Verificato eseguendo la
funzione com'è oggi:

```text
ERRORE: Task non registrato: consuma_plafond_lotto
```

⇒ Il primo lotto portato a DEFINITIVA si sarebbe fermato sul **primo task**
dello step — cioè prima di numerare, su entrambe le pipeline. Peggio del non
fare niente, perché il difetto sarebbe arrivato su un giro di documenti fiscali
invece che su un `migrate`.

⚠️ **E nessun vincolo lo intercetta**: su `vendite.fatturazione_pipeline` non c'è
nessun trigger che validi i task contro il registry — i cinque che ci sono
guardano altro. `processi` è una `jsonb`: un task non registrato è una stringa
come un'altra, e il `migrate` passa liscio.

⇒ **Le righe sono quattro, non due**: due di catalogo e due di JSON.

| Tabella | Riga | Calco |
| --- | --- | --- |
| `dbops.pipeline_task_registry` | `id 22`, dominio `1`, `consuma_plafond_lotto`, attivo | `popola_fatture_rettifiche` (id 21) |
| `dbops.pipeline_task_registry_impl` | `id 22`, `default` → `consuma_plafond_lotto_default` | idem |

⭐ **Il `handler_code` non è una scelta**: `consuma_plafond_lotto_default` è
letteralmente la chiave del `handler_registry` lato backend. Un valore diverso
darebbe `E_TASK_IMPLEMENTATION_NOT_FOUND` — cioè lo stesso guasto, un gradino
più in là.

~~📌 **La riga in `fatturazione_pipeline_task_policy` NON è stata messa**, e la
decisione è quella che il brief lasciava al DB: `popola_fatture_rettifiche` gira
nelle stesse due pipeline senza averne una, quindi non è obbligatoria. Il task
non ha bisogno di un `resume_mode` proprio — è idempotente per costruzione,
perché il movimento di plafond lo scrive `fn_consuma_plafond_titolo_iva` sotto
lock. Se servirà, si aggiunge senza toccare nient'altro.~~

### ✅ Chiusura del 2026-08-31, sera — le righe erano SEI, e ora ci sono

> ⭐ **Due squadre hanno trovato lo stesso difetto per due strade diverse**, il
> che è la conferma migliore che si potesse avere. Il BE l'ha visto dal suo
> cancello (`test_ogni_task_in_pipeline_ha_una_task_policy` — la CORREZIONE qui
> sopra); il DB dal pgTAP `test-pipeline-processi-invariante-v1.sql`, caso 7,
> *«ogni (pipeline, task) armato ha la sua task_policy attiva»*: `have: 2,
> want: 0`, rosso **nuovo**, non in baseline.
>
> ⇒ Le due analisi coincidono anche sui **valori**: `annullabile=false`,
> `RESUME_TASK`, `meta` con lo `scope`. Nessuna delle due ha dovuto cedere.

⭐ **Ed è la stessa forma dell'errore che questa voce dichiara di aver corretto**:
poche righe sopra c'è scritto *«le righe erano QUATTRO, non due»*, dopo aver
scoperto che mancava il catalogo. **Erano sei.** Un artefatto che sembrava uno
si è rivelato tre, poi quattro, e alla fine sei — e ogni volta il pezzo
mancante era invisibile perché *nessun vincolo lo intercetta*.

**Cosa costava davvero.** Meno di quanto sembri, e va detto con precisione
invece di drammatizzare:

- ⛔ **NON** faceva morire lo step. L'executor chiama il resolver solo dopo
  `task_policy_exists(...)` ([pipeline_step_executor.py:384](../../../../backend/apps/vendite/services/pipeline_step_executor.py)):
  senza policy, `fn_resolve_lotto_task_execution_mode` non viene invocata e il
  suo `E_CONFIG_MANCANTE` non scatta;
- ⛔ **NON** consumava due volte il plafond. `fn_consuma_plafond_titolo_iva` ha
  una guardia di idempotenza esplicita su (titolo, fattura, riga), con una
  UNIQUE parziale come rete. ⚠️ La conclusione del paragrafo ritirato era
  **giusta**, ma per il motivo sbagliato: il `FOR UPDATE` dà serializzazione,
  non idempotenza — quella la dà la guardia;
- ✅ **Costava la TRACCIA.** Senza policy non si apre nessun `task_run`: il
  task girava **invisibile** nella scheda Task del lotto e nel registro
  `TASK_RUN` di `script.vw_giornale_entita`, e senza `SKIP` rigirava a ogni
  rilancio dello step. Innocuo sui numeri, ma *«eseguito»* e *«mai eseguito»*
  diventavano indistinguibili — su un passo che tocca il plafond fiscale.

**Le due righe messe** (append al CSV, nessun changeSet: il mirror
`20260218-05` è `runOnChange`):

| id | pipeline | `annullabile` | `resume_mode` | `meta` |
| --- | --- | --- | --- | --- |
| 26 | 4 (MASSIVO) | `f` | `RESUME_TASK` | `{"scope":"DEFINITIVA"}` |
| 27 | 6 (GIORNALIERO) | `f` | `RESUME_TASK` | `{"scope":"DEFINITIVA","tipo_lotto":"GIORNALIERO"}` |

⭐ **I due valori non sono una copia, sono un argomento:**

- `annullabile = f` perché annullare il `task_run` **non storna i movimenti** —
  quelli hanno il loro verbo, `anagrafiche.fn_annulla_movimento_titolo_iva`, con
  il suo check e il suo guard. Dichiararlo `t` prometterebbe un annullo che il
  cancel non esegue. È anche l'allineamento con i due compagni di corsia che
  scrivono fatti (`numera_fatture`, `popola_fatture_rettifiche`);
- `resume_mode = RESUME_TASK` perché il task è idempotente e autonomo:
  rilanciare lui solo basta. `RESUME_STEP` serve a `numera_fatture`, dove in
  gioco c'è una **sequenza**, non una riga.

✅ **Applicato** dal migrate delle 21:47 del 2026-08-31 (mirror `RERAN`), e i due
pgTAP sono verdi: `test-pipeline-processi-invariante-v1` **7/7** e
`test-pipeline-consuma-plafond-seed-v1` **6/6** — quest'ultimo non asserisce
nulla sulla policy, quindi l'aggiunta non lo tocca (verificato prima di
scrivere, non dopo).

---

### Presidio atteso

⭐ **Quello che discrimina non è «il task compare nella lista»**: è l'**ordine**.
Un lotto portato a DEFINITIVA su un titolo con capienza parziale deve avere, a
fine giro, **due righe** sulla fattura e **un movimento** nel registro. Con il
task in coda invece che in testa, la stessa prova fallisce con il rifiuto del
guard di congelamento — che è l'esito da vedere **una volta**, per sapere che
la posizione conta.

⚠️ E il gemello: un lotto senza titoli deve passare **identico a oggi**, con
zero movimenti scritti. Senza, un task che «gira sempre» passerebbe il primo.

---

## 2. ✅ La `fn_check_*` che dice perché un registro non si disattiva — FATTA

> ✅ **CHIUSA il 2026-08-31**, changeSet `20260831-38` applicato. Verificato sul
> database vivo, non sullo YAML: `SECURITY DEFINER` (serve — legge
> `vendite.fatture`, che ha la RLS), tre `reason` **senza prefisso `E_`**
> (`HA_FATTURE`, `HA_PROGRESSIVI`, `HA_MAPPING_TIPO_DOC`), e **nessun codice
> errore nuovo**: nomina i due `E_ATTIVO_BLOCK_CHILDREN_*` già a catalogo.
>
> ✅ **Il residuo dei «due elenchi paralleli» si è manifestato e chiuso in
> giornata** (`20260831-71`, sei guard). Quanto segue resta valido come
> *descrizione del meccanismo*, che non è stato eliminato: la prossima figlia
> registrata riaprirà lo stesso scarto.
>
> ⚠️ **Resta un residuo, e NON blocca il CRUD** — la check funziona e il tooltip
> dirà la cosa giusta. Il presidio del §12.5.2 (*«la madre non contiene più il
> predicato»*) però **non è raggiunto, e non era raggiungibile così**: le tre
> madri non sono guard scritti a mano, sono tre istanze dell'automazione generica
> `dbops.trgfn_prevent_deactivate_if_children`, ognuna col proprio figlio negli
> argomenti del trigger. Una funzione generica che serve 100 tabelle non può
> chiamare una check specifica.
> ⇒ Restano **due elenchi paralleli**: i figli nei trigger montati, e la check
> che li riscrive. Il giorno che si registra un **quarto** figlio, l'automazione
> monta il trigger da sé e la check resta a tre — tooltip che dice «si può» su un
> gesto che fallisce.
>
> ⭐⭐ **E il numero cambia la scala del problema: 100 tabelle, 366 trigger
> montati, UNA sola check di disattivazione** (questa). `catalogo.articoli` ha 29
> figli, `unita_misura` 21: a mano non regge. ⇒ La strada giusta non è per
> tabella ma **generica** — una `script.fn_check_disattivabile(schema, tabella,
> id)` che legge i trigger montati, come `fn_get_storia_emittente_ba` legge il
> catalogo delle famiglie invece di elencarle. ~~**Decisione a Tid**, e vale un
> cantiere suo: non è di questo ordine di lavoro.~~
>
> ⛔ **DECISA, ed è l'opposto** (in fondo al file): l'elenco delle figlie **resta
> scritto a mano**. Un elenco derivato da `pg_trigger` emetterebbe una
> `reason_key` che nessuno ha tradotto — difetto **muto in produzione** invece
> di un rosso in sviluppo. ⭐ È un elenco parallelo **tenuto da un presidio**, che
> è un'altra cosa da un elenco parallelo lasciato a sé stesso.

### ✅ Il residuo si è avverato ed è già stato CHIUSO, nella stessa serata

> ⚠️ **Questa sezione è stata riscritta.** La prima stesura conteneva un
> controesempio **sbagliato**, e il rilievo di Tid l'ha smontato: va tenuto
> scritto, perché l'errore di metodo vale più del rilievo.

**Il fatto.** Il §2 qui sopra prevedeva *«il giorno che si registra un quarto
figlio, l'automazione monta il trigger da sé e la check resta a tre»*. È successo
lo stesso giorno, e i figli nuovi erano **tre**: `ordini`, `ddt` e `resi`,
traslocati sui registri dal cantiere della numerazione. Per qualche ora la check
ne ha coperti **3 su 6**.

✅ **Chiuso alle 22:05** dal changeSet
`20260831-71-update-fn-check-registro-disattivabile-sei-guard`: la check ha ora
sei `reason` — `HA_FATTURE`, `HA_PROGRESSIVI`, `HA_MAPPING_TIPO_DOC`,
`HA_ORDINI`, `HA_DDT`, `HA_RESI` — e **copre tutti e sei i trigger montati**,
verificato incrociando `pg_trigger` con il corpo vivo della funzione.

---

#### ⛔ L'errore di metodo, che è la parte da tenere

**Primo sbaglio — un controesempio NON RAGGIUNGIBILE.** Per mostrare la
divergenza avevo agganciato un ordine a un registro pulito con un `UPDATE` e
concluso *«la check dice si-può, il trigger rifiuta»*. ⛔ **Quello stato
l'applicazione non lo produce**: `trgfn_ordini_gen_numero` — e le gemelle di DDT
e resi — scrivono `NEW.registro_id` e `NEW.numero` **nello stesso blocco**, ed
escono in testa se un numero c'è già. Un documento su un registro **ha sempre**
consumato un progressivo, quindi `HA_PROGRESSIVI` sarebbe scattato comunque.
*Un controesempio costruito fuori dal modello non è un controesempio: è un dato
sporco.*

⭐ **La strada giusta c'era, ed era un'altra** — l'asimmetria fra i due rami del
guard generico:

| Figlio | colonna `attivo` | ramo del guard | la check contava |
| --- | --- | --- | --- |
| `registri_fatturazione_progressivi` | **sì** | `_ACTIVE` — solo le righe attive | solo le attive ✅ |
| `ordini`, `ddt`, `resi`, `fatture` | **no** | `_EXIST` — *«una riga o c'è o non c'è»* | ⛔ non le contava |

⇒ Bastava **spegnere il progressivo** — che è il gesto *«figli prima, padre
poi»* che la check stessa avalla — perché `HA_PROGRESSIVI` smettesse di
scattare mentre l'ordine restava lì a bloccare. Quello sì era raggiungibile,
e non richiedeva nessun `UPDATE` fuori modello.

**Secondo sbaglio — la doc auto-gen letta come «l'oggetto vivo».** I tre
`reason` li avevo contati su
`docs/it/dbzero/script/funzioni/fn_check_registro_disattivabile.md`. Quel file
era stampato alle **21:37**; il changeSet che porta la check a sei è delle
**22:05**. La regola di casa — *«la definizione corrente si prende dalla doc
auto-gen, che riflette l'oggetto vivo»* — **presuppone che la doc sia stata
rigenerata**, e in una giornata con più cantieri che applicano ogni pochi minuti
quella premessa salta.

⚠️ ⇒ **Su un oggetto toccato oggi, la sorgente è `pg_proc`, non il markdown.**
La doc resta giusta per capire *perché*; per sapere *cosa fa adesso* si chiede
al database. Vale come corollario alla regola, non come sua sostituzione.

---

📌 **Il ragionamento è già scritto**, e non si ricopia: §FE-2 del
[brief BE/FE del CRUD dei registri](brief-be-fe-crud-registri-di-numerazione.md).

### Il fatto — i registri non hanno CRUD, e disattivare è la parte delicata

`vendite.registri_fatturazione` **non ha nessun CRUD** — verificato il
2026-08-31 su cinque superfici: nessuna rotta, nessuna riga in
`ui.lista_definizione`, nessuna voce nel lookup generico, nessun drawer, nessuna
voce di menu. Le 14 righe di oggi nascono da changeSet di seed e dal
provisioning automatico (`fn_provision_registri_emittente`).

Il CRUD si scrive ora, e la sua azione di riga più delicata è **disattiva**,
perché su questa tabella i guard sono **tre**:

```text
trg_registri_fatturazione_a10_fatture_block_deact_upd          → ha fatture
trg_registri_fatturazione_a10_registri_fatturazione_prog_…     → ha progressivi
trg_registri_fatturazione_a10_tipi_doc_fiscale_registri_…      → ha mapping tipo doc
```

⭐ **Il secondo è quello che sorprende**: un registro che ha numerato anche **un
solo** documento ha una riga di contatore viva, quindi non si spegne più. Ne
discende che il cestino è **quasi sempre** indisponibile — e senza un motivo a
video l'operatore lo scopre premendo.

### La richiesta — una `fn_check_*`

```sql
script.fn_check_registro_disattivabile(p_registro_id bigint) RETURNS jsonb
```

Forma del §12.5.1: `[]` se disattivabile, altrimenti array **ordinato** di
`{codice, reason, reason_key, dettaglio, valori}`. Un motivo per guard:

| `reason` | Quando |
| --- | --- |
| `HA_FATTURE` | esistono fatture attive sul registro |
| `HA_PROGRESSIVI` | esiste una riga viva in `registri_fatturazione_progressivi` |
| `HA_MAPPING_TIPO_DOC` | esiste una riga in `tipi_doc_fiscale_registri` |

⭐ **Nessun codice errore nuovo**: la check *nomina* gli `E_ATTIVO_BLOCK_CHILDREN_*`
che sono **già a catalogo con la loro policy** — verificato. §12.5.2 dice che se
servisse un codice nuovo il difetto sarebbe a monte: la madre starebbe
rifiutando senza saper dire perché.

⛔ **I `reason` NON portano il prefisso `E_`.** È la convenzione del §12.5.1, ed
è presidiata solo per caso: il guardrail dei codici errore cerca i letterali
`E_*` nei corpi delle funzioni e un `reason` così prefissato gli arriva come
**codice senza policy**. È costato un changeSet stamattina — `E_UN_ANNULLO` →
`RIGA_DI_ANNULLO`, `20260831-35`.

⚠️ **`SECURITY DEFINER` come le gemelle**: la check legge `vendite.fatture`, che
ha la RLS. Sotto il perimetro di un operatore le fatture di un altro emittente
sono invisibili, e la check concluderebbe «si può disattivare» **proprio nel
caso da bloccare**.

📌 **Dove leggerla, lo decide il BE** e non serve qui: la lista dei registri è
una query del repository, quindi basta una `LEFT JOIN LATERAL` come fa
`EmittentiFiscaliBillingAccountRepository` con `fn_check_ba_cambio_emittente` —
nessuna vista nuova.

### Cosa blocca — niente, ed è il punto

⚠️ **Niente, e va detto.** I passi 1-4 del CRUD (repository, service, mappa
vincoli, lista, drawer) non la toccano. Aspettano solo il passo 5 — il cestino
col motivo — e il 6.

⭐ È chiesta **prima** di scrivere il codice che ne dipende, che è la differenza
con la voce 5 dell'elenco 1: là il prerequisito si scoprì a lavoro fatto.

### Presidio atteso — la madre che CHIAMA

* Un registro **senza** figli: la check risponde `[]`, e la disattivazione passa;
* ⛔ il **gemello negativo**, e senza non si distingue «rifiuta il caso giusto»
  da «rifiuta tutto»: un registro con un progressivo vivo risponde
  `HA_PROGRESSIVI`, e la disattivazione viene rifiutata dal trigger con lo
  stesso codice che la check nomina;
* ⭐ il presidio che vale davvero, §12.5.2: **la madre non contiene più il
  predicato** — cioè il guard di disattivazione chiama la check invece di
  riscriverla. Se restano due predicati, l'invariante è la disciplina e non la
  struttura.

---

## ⛔ Cosa NON è da fare qui — e la prima voce è la più importante

### ⛔ **NON scrivere una madre `fn_consuma_plafond_lotto`**

La richiesta è **due righe di JSON**. Non una funzione.

⚠️ **Il rischio è concreto perché il nome del task suona come una madre per
lotto**, e su questa stessa pipeline è già successo — sta scritto accanto al
codice:

> *«`vendite.fn_generate_fatture_righe` è stata RIMOSSA il 2026-07-28
> (changeset `20260728-21`): l'implementazione in esercizio è
> `FattureRigheService.generate_fatture_righe`. Lasciare qui il nome di una
> funzione inesistente è precisamente ciò che ha fatto scrivere **due requisiti
> di aggregazione su codice non eseguito**.»*

⇒ Il task va dichiarato **senza chiave `fn`**, come `generate_fatture_righe`:
l'implementazione è Python e `ALLOWED_TASK_FUNCTIONS` la registra già a `None`.
⚠️ Un `fn` dichiarato in configurazione per un task a `None` viene **respinto**
con `E_TASK_NOT_ALLOWED` — quindi il presidio c'è, ma è meglio non farlo
scattare.

⭐ **Cosa resta alla madre DB**, e non cambia: `fn_consuma_plafond_titolo_iva`
fa la parte che **deve** stare sotto lock — capienza, movimento, ripartizione.
Il BE ordina le fatture, decide quali righe spezzare e la chiama. La divisione è
quella di sempre: la regola che protegge un invariante concorrente sta nel DB,
l'orchestrazione sta qui.

### Il resto

* ⛔ **L'ordinamento `ORDER BY data documento, numero`** del giro (`P5`,
  `D15-bis`): è **lavoro nostro**, sta nel servizio Python e non nel seed;
* ⛔ **La spezzatura della riga**: colonna, FK, guard e vista sono **già
  applicati** (voce 5 dell'elenco 1, `20260831-30..33`);
* 📌 **Il generatore XML FatturaPA**: non esiste, e non è di questo cantiere.

---

## ⭐ Come si decide se una voce è DB o BE — la prova, non l'impressione

> Scritto il 2026-08-31 dopo una domanda di Tid: *«siamo sicuri che stiamo
> gestendo bene la pipeline e non abbiamo spostato al DB richieste non
> necessarie, che poi magari duplichiamo?»*. ⛔ La domanda era giusta: la prima
> versione di questa voce diceva che il consumo del plafond «non è scrivibile»
> lato BE, ed **era falso** — handler, servizio e test erano scrivibili, e sono
> stati scritti.

**La prova è una sola, e si esegue sul repo**: *esiste un percorso di scrittura
BE su quell'artefatto?*

| Artefatto | Percorso di scrittura BE | Chi |
| --- | --- | --- |
| `vendite.fatturazione_pipeline` (i task di uno step) | **nessuno** — verificato: il BE la legge via `fn_list_fatturazione_pipeline_steps` e `fn_resolve_fatturazione_pipeline_step`, non esiste `INSERT`/`UPDATE`, nessuna rotta, nessuna schermata | **DB** |
| L'**handler** di un task, il servizio, i test | è codice Python | **BE** |
| `config.parameters` (riga base: codice e valore) | **nessuno** — il `ParameterService` scrive solo `parameter_overrides`, che è un'altra tabella | **DB** |
| `config.codici_errore` / `messaggi_errore` | **nessuno** — il generatore delle policy **legge** e produce un file Python | **DB** |
| Corpo di una funzione SQL, DDL, trigger, viste | — | **DB** |

⚠️ **Il caso che inganna è proprio il primo**, e va nominato: «il task di
pipeline» non è un artefatto solo. È **due**: il codice che lo esegue (BE) e la
riga che dice quando eseguirlo (DB). Chiamarlo con un nome solo fa sbagliare
l'instradamento in entrambi i versi — chiedere al DB ciò che si può scrivere, o
scrivere qui ciò che non prenderebbe mai effetto.

⭐ **E il verso pericoloso è quello della duplicazione**: il codice lo dice già,
sulla stessa pipeline — `fn_generate_fatture_righe` fu scritta a DB **mentre**
l'implementazione viva era in Python, e *«ha fatto scrivere due requisiti di
aggregazione su codice non eseguito»*.

---

## Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 (4) | 🔨 **Voce 1 FATTA** (la 2 no, per richiesta di Tid). ⛔ **E le righe erano QUATTRO, non due**: trovato eseguendo che l'executor risolve l'handler dal **registry DB** (`fn_get_pipeline_task_implementation`), non dalla lista dei processi — e `consuma_plafond_lotto` non era a catalogo. Le sole due righe di JSON avrebbero fatto morire lo step DEFINITIVA sul primo task, su entrambe le pipeline, con «Task non registrato»: un guasto su un giro di documenti fiscali invece che su un migrate. ⚠️ Nessun vincolo lo intercetta — `processi` è una `jsonb` e il migrate passa liscio. Presidio: `db/pgtap/vendite/test-pipeline-consuma-plafond-seed-v1.sql`, 6 casi, tre mutazioni che cadono ognuna sul caso suo. ⭐ E il test ha corretto **me**: il criterio «ogni step che congela» era sbagliato, perché congela anche INVIATA — quello giusto è il **primo** stato che congela, cioè il passaggio in cui il congelamento avviene. ⛔ Nessuna madre `fn_consuma_plafond_lotto`, nessuna chiave `fn`: il divieto del §«Cosa NON è da fare» è rispettato, e il caso 6 del pgTAP lo presidia |
| 2026-08-31 (3) | ➕ **Voce 2**: `fn_check_registro_disattivabile`, dal cantiere del CRUD dei registri. ⭐ **Non blocca** — i primi quattro passi di quel brief partono senza — ed è chiesta *prima* di scrivere il codice che ne dipende. ⚠️ La strada alternativa (derivare `can_remove` in Python) è stata **scartata da Tid**: è il grado ⛔ del §12.5 e sarebbe il difetto che il mapping BA ha appena finito di chiudere, per giunta su **tre** guard invece di uno. ⛔ E i `reason` non portano il prefisso `E_`: la regola è costata un changeSet stamattina (`E_UN_ANNULLO` → `RIGA_DI_ANNULLO`, `20260831-35`) |
| 2026-08-31 (2) | ⛔ **Corretta una frase sbagliata di questo stesso file**, su segnalazione di Tid: diceva che il consumo del plafond non era scrivibile lato BE. Era falso — handler, servizio, repository e 14 test sono BE, e sono stati scritti. Al DB resta **solo** la configurazione. Aggiunta la regola di instradamento (§«Come si decide») e il divieto esplicito di scrivere una madre `fn_consuma_plafond_lotto`, che è la duplicazione che questo cantiere ha già pagato una volta |
| 2026-08-31 | Elenco nato chiudendo `F3-b1` (la riga di fattura che chiede l'IVA al risolutore) e verificando **dove** possa vivere il consumo del plafond. ⚠️ **È lo stesso schema della voce 5 dell'elenco 1**: un lavoro che sembrava «solo BE» fermo su un prerequisito che nessuno aveva chiesto — lì una colonna, qui due righe di seed. ⭐ La differenza è che stavolta è stato trovato **prima** di scrivere il codice che ne dipende |

---

## ⚠️ Voce 2 — aggiornamento del 2026-08-31 (sera): i guard erano diventati SEI

`script.fn_check_registro_disattivabile` copriva **tre** figlie; ne sono comparse
altre tre. Allineata dal changeSet `20_code/script/20260831-71`.

### Come si è visto

⭐ L'ha trovato **il presidio, da solo**. Il test 6 del suo pgTAP era scritto con
questa frase: *«il giorno che ne compare una quarta, diventa rosso»*. È diventato
rosso, e ne erano comparse tre.

```
have: ddt, fatture, ordini, registri_fatturazione_progressivi, resi, tipi_doc_fiscale_registri
want: fatture, registri_fatturazione_progressivi, tipi_doc_fiscale_registri
```

⛔ **Nessuno le ha scritte.** Col trasloco della numerazione `vendite.ddt`,
`ordini` e `resi` hanno guadagnato `registro_id`, e l'automazione monta il guard
di disattivazione **da sola** a partire dalla FK — al `migrate`, senza annunciarlo.

### ⭐ Cosa cambiava davvero, misurato

Sul registro `DDT-72`, che ha numerato documenti veri:

| | la check diceva | il rifiuto dice |
| --- | --- | --- |
| **prima** | `HA_PROGRESSIVI` | *«…righe collegate in `vendite.ddt`»* |
| **dopo** | `HA_DDT \| HA_PROGRESSIVI` | *«…righe collegate in `vendite.ddt`»* |

⇒ Il tooltip e l'errore nominavano **figlie diverse** sullo stesso registro. Ora
no, e non per caso: i motivi sono ordinati per **nome della tabella figlia**, che
è l'ordine alfabetico in cui i `BEFORE ROW` scattano davvero. Il primo motivo è
quello che il rifiuto nominerebbe.

### ⚠️ Debito verso il FE — tre `reason_key` NUOVE

```
amministrazione.registri_fatturazione.disattiva_blocco.ha_ddt
amministrazione.registri_fatturazione.disattiva_blocco.ha_ordini
amministrazione.registri_fatturazione.disattiva_blocco.ha_resi
```

Vanno aggiunte ai locales, o `scripts/check_i18n_keys.py` fallisce. ⭐ Ed è il
motivo per cui l'elenco delle figlie **resta scritto a mano** invece di essere
derivato da `pg_trigger`: un elenco derivato inventerebbe una chiave che nessuno
ha tradotto, e la superficie mostrerebbe la chiave nuda — un difetto **muto in
produzione** al posto di un rosso in sviluppo. È un elenco parallelo *tenuto da un
presidio*, che è un'altra cosa da un elenco parallelo lasciato a sé stesso.

### ✅ La domanda aperta è stata DECISA — Tid, 2026-08-31 sera

I tre guard nuovi sono `_EXIST`: bloccano sull'**esistenza** dei documenti, perché
`ddt`, `ordini` e `resi` non hanno la colonna `attivo`. ⇒ Un registro che ha
numerato anche un solo documento non si può più disattivare.

**Decisione: si accetta il blocco.** La check copre tutti e sei i guard
(`20260831-71`), e a essere corretta è la documentazione, non il vincolo.

#### ⭐ Perché è la scelta giusta sul MODELLO

⚠️ Il primo argomento che avevo portato — *«costruire l'esclusione costa, tocca
un'automazione condivisa»* — è stato **ritirato dal ragionamento su richiesta di
Tid**: è un argomento sullo stato dello sviluppo, e non deve decidere la forma.
La scelta regge senza, su tre fatti strutturali:

| | |
| --- | --- |
| lo slot `UNIQUE` resta occupato anche da spento | non se ne può creare uno sostitutivo |
| `fn_lookup_registro_documento` pretende `attivo IS TRUE` | il documento non nasce più |
| `fn_provision_registri_emittente` non crea dove una riga esiste | nessun rimedio automatico |

⇒ Spegnere un registro non fiscale **non è un ritiro: è un blocco senza uscita**.
L'azienda smette di emettere quel documento e non c'è modo di tornare indietro.
Un guard che lo impedisce non toglie una capacità utile: **impedisce un autogol**.

⭐ **E il bisogno vero dietro «ritiro e rifaccio» era cambiare la forma del
numero.** Da ieri sera `prefisso`, `suffisso` e `lunghezza_numero` sono colonne
del registro e si modificano: la strada che sembrava chiusa era già stata riaperta
altrove.

#### ⛔ Perché la strada B è stata SCARTATA

Escludere le tre coppie dall'automazione avrebbe riaperto la possibilità di
compiere quell'azione. ⇒ Si costruisce un meccanismo **per riabilitare un'azione
che porta a uno stato irrecuperabile**: è la definizione di un foot-gun.

⚠️ E si sarebbe dovuto costruirlo davvero — vedi la correzione qui sotto.

#### ⛔ CORREZIONE — «il meccanismo esiste già ed è vuoto» era FALSO

Avevo proposto la strada B dicendo che bastava riempire
`80_data/sql/dbops/automation_fk_exclusions.csv`. ⛔ **Dedotto dall'esistenza del
file, senza guardare la tabella:** `dbops.automation_fk_exclusions` **non esiste**
— l'ha droppata `20260101-01-drop-attivo-legacy-objects`. Quel CSV è un file
morto, un seme senza terreno.

⭐ È la stessa lezione del `20260831-55`, applicata all'incontrario: là avevo
cancellato una fonte senza censire chi la legge, qui ho creduto viva una fonte
senza chiedere se esistesse. **In entrambi i casi la verifica costava una query.**

#### ⚠️ Due residui trovati mentre si cercava il meccanismo (non corretti)

1. **`automation_fk_exclusions.csv` è un CSV senza tabella.** Chi lo trova
   conclude — come ho fatto io — che il meccanismo esista. ⛔ Va **cancellato**,
   ed è la stessa regola dell'oggetto ritirato che lascia il file in `manual/`:
   un moncone resta pubblicizzato.
2. **`dbops.automation_rules_tbl.params` dichiara tre chiavi che nessuno legge** —
   `block_if_child_no_attivo`, `cascade_children`, `include_no_action`. Verificato
   su `pg_proc.prosrc` il 2026-08-31: zero consumatori. ⚠️ È lo stesso difetto di
   `reset_policy`, che prometteva tre comportamenti e ne faceva uno: un catalogo
   che dichiara più di quanto esegue prima o poi convince qualcuno a sceglierne
   una. ⇒ O si implementano, o **escono**.

⚠️ Entrambi sono fuori dal perimetro di questa richiesta: sono scritti qui perché
non vadano persi.
