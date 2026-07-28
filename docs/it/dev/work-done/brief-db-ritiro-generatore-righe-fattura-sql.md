# Brief DB — Ritiro del generatore righe fattura SQL (residuo non in esercizio)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-28 · **Owner**: Tid ·
> **Priorità**: 🟠 **MEDIA** — nessun dato a rischio e nessun malfunzionamento in
> corso, ma è la condizione che il 2026-07-28 ha fatto finire **una giornata di
> lavoro DB su codice che non viene eseguito**.
>
> **Stato**: ✅ **CHIUSO lato DB** (2026-07-28) — `DROP` applicato e verificato
> sul DB vivo, entrambi i pgTAP verdi. Spostato in `work-done/`. Restano i due
> passi BE, che per progetto non bloccano.
>
> | Passo | Stato |
> |---|---|
> | 1 — `DROP` delle due funzioni (`20260728-21`) | ✅ **applicato**, verificato: `pg_proc` non le contiene più (0 righe) |
> | 2 — `test-porta-oneri-giro-completo-v1` → `plan(9)` | ✅ **verde a funzioni assenti** — la condizione per cui il taglio è stato fatto |
> | 3 — doc `manual/` dbzero + riferimenti (§5-ter) | ✅ fatto, 11 voci · ⬜ rigenerare l'auto-gen al prossimo `gen` |
> | 4 — `test-articolo-regole-fatturazione` → `plan(6)` + fixture `uom_id` | ✅ **verde**, tolto da `baseline-rossi.tsv` (109 → 108 rossi) |
> | 5 — smoke Python AF → riga di fattura | ⬜ BE, non blocca |
> | 6 — manuali backend | ✅ fatto (riscritti, **non** cancellati: documentano gli entrypoint Python vivi — §5-ter) |
> | 7 — `ALLOWED_TASK_FUNCTIONS` | ⬜ **BE, ora urgente**: due voci del registro puntano a funzioni che non esistono più |
>
> ⚠️ **Da qui in poi il percorso della generazione righe fattura è uno solo**:
> `FattureRigheService`. Non esiste più un oggetto SQL che gli somigli, e questa
> è la garanzia che il difetto d'origine — sviluppare sulla gemella morta — non
> possa ripetersi.
>
> **Origine**: voce **B7** di
> [brief-be-fe-importi-riga-fattura.md](brief-be-fe-importi-riga-fattura.md) §7.
> Il **porting di D4 e D5** nel servizio Python è chiuso e in esercizio (voci
> B0-B4 e B6 di quel brief). ⚠️ Il brief padre **resta aperto**: mancano B5, B8 e
> i casi di integrazione §10.2 **7-8** — cioè proprio lo smoke su DB reale del
> tratto AF → riga di fattura. Vedi §4 sul perché questo **non** è un motivo per
> rinviare il `DROP`.
>
> **Chiude due domande aperte del brief padre**: **P3** (*«`fn_group_attivita_fatturabili`
> SQL: in esercizio o residuo come la gemella?»*, §12 Decisioni aperte) e il dubbio
> sul changeset `-17` (§3-bis, matrice di conservazione). Risposta a entrambe:
> **residuo, zero chiamanti** — §2.3. Vanno spuntate là.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.
>
> **Come leggere**: §1 è la richiesta in breve, §2 i fatti verificati sul DB e sul
> codice vivi, §3 l'**unico effetto collaterale** del `DROP`, §4 le opzioni con la
> raccomandazione, §5 la sequenza (più §5-bis debito di `-18` e §5-ter doc da
> ritirare), §6 cosa NON è in perimetro.

---

## 1. La richiesta, in breve

Due funzioni SQL non sono in esercizio ma sembrano esserlo:

| Funzione | Stato reale | Chiamanti |
|---|---|---|
| `vendite.fn_generate_fatture_righe(bigint, boolean)` | residuo: il task pipeline esegue Python | **nessuno** nel DB |
| `vendite.fn_group_attivita_fatturabili(bigint)` | residuo: il servizio Python usa `_build_group_key` | solo la funzione qui sopra |

Si chiede di **rimuoverle**, con la sequenza di §5. Il solo effetto collaterale è
in §3: 3 asserzioni pgTAP che oggi sono verdi su codice non eseguito.

---

## 2. Fatti verificati (DB e codice vivi, 2026-07-28)

### 2.1 Il task della pipeline non esegue la funzione SQL

[`pipeline_step_executor.py:454`](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L454)
chiama `self.fatture_righe_service.generate_fatture_righe(...)`.

Ed è l'**unica** eccezione fra i nove task che hanno una funzione SQL (il
decimo, `close_lotto`, non ne ha: nel registro mappa a `None`). Mappatura
completa, verificata handler per handler:

| Task | Esegue |
|---|---|
| `select_attivita` | `repository.run_select_attivita_task` → SQL |
| **`generate_fatture_righe`** | **`fatture_righe_service.generate_fatture_righe` → Python** ⚠️ |
| `genera_fondi_source_lotto` | `repository.run_genera_fondi_source_lotto_task` → SQL |
| `applica_fondi_lotto` | `repository.run_applica_fondi_lotto_task` → SQL |
| `ricalcola_iva_lotto` | `repository.run_ricalcola_iva_lotto_task` → SQL |
| `prepare_sdi_payload_lotto` | `repository.run_prepare_sdi_payload_lotto_task` → SQL |
| `numera_fatture` | `repository.numera_fattura_opz_emessa` → SQL |
| `reset_lotto_draft` | `repository.reset_lotto_draft` → SQL |
| `pull_attivita_da_commessa` | orchestrazione Python + funzione SQL per commessa |

### 2.2 Non è una deriva: è una decisione documentata

Commit **`ece04a5ff`** (3 febbraio 2026): *«Iniziato sviluppi python — base per
architettura futura. **Riscritto funzioni sql fatturazione in Python**»*.

Il manuale backend
[`docs/it/backend/vendite/manual/fn_generate_fatture_righe.md`](../../backend/vendite/manual/fn_generate_fatture_righe.md):

> *«La logica di `vendite.fn_generate_fatture_righe()` **è stata portata in**
> `apps/vendite/services/fatture_righe_service.py`»*
> *«Stato attuale: **migrazione logica completata lato Python**»*
> *«La funzione SQL **può restare per compatibilità storica/transitoria**»*

**È l'ultima riga il problema.** Quella formula, scritta a febbraio, è il motivo
per cui il 2026-07-28 i changeset `-12` (aggregazione D4) e `-15` (snapshot kit
D5) sono stati scritti, testati e applicati **sulla funzione sbagliata**: il
requisito era corretto, l'oggetto no. Se ne è accorto solo un controllo
incrociato sul codice, perché il difetto non produceva alcun sintomo — il
trigger dell'importo funziona per qualunque scrittore, quindi le fatture
risultavano corrette lo stesso.

### 2.3 Nessun chiamante nel database

- `fn_generate_fatture_righe`: cercata in tutti i `prosrc` dello schema — l'unico
  riscontro è `trgfn_fatture_righe_importo`, che la **nomina in un commento**
  (*«né fn_generate_fatture_righe, né il repository Python…»*), non la chiama.
- `fn_group_attivita_fatturabili`: un solo chiamante reale,
  `fn_generate_fatture_righe`. Ritirata quella, resta a **zero**. (Anche qui
  `trgfn_fatture_righe_importo` la cita solo in un commento sul pattern del
  `LEFT JOIN` con fallback.)

### 2.4 Il registro `ALLOWED_TASK_FUNCTIONS` non protegge nulla

Il nome della funzione SQL compare in
[`pipeline_repository.py:148`](../../../../backend/apps/vendite/db/pipeline_repository.py#L148),
sotto un commento che dichiara già l'ambiguità: *«`fn` nei JSON task è mantenuto
come token di compatibilità SQL legacy»* (riga 147).

Verificato che è **completamente inerte**, su entrambi i piani:

- **sul DB vivo**:
  `SELECT count(*) FROM vendite.fatturazione_pipeline WHERE processi::text LIKE '%"fn"%'`
  → **0**: nessuna configurazione di pipeline contiene la chiave `fn`;
- **sulla sorgente del seed** — che è ciò che governa un DB ricostruito da zero
  (CI), dove il dato di dev non arriva:
  `80_data/sql/vendite/fatturazione_pipeline.csv` non contiene la chiave `fn`, e
  `80_data/sql/dbops/pipeline_task_registry.csv` / `pipeline_task_registry_impl.csv`
  portano solo codici task e `implementation_key` (`generate_fatture_righe_default`),
  **mai nomi di funzioni SQL**;
- di conseguenza `_validate_task_function_name` riceve sempre `fn_name = None`, e
  il suo guard è `if fn_name and fn_name != allowed` → non scatta mai. In nessun
  ambiente, non solo su dev.

Vale per **tutti** i task, non solo per questo. La pulizia di quel registro è
lavoro **BE**, non del team DB, ed è annotata in §6.

---

## 3. L'unico effetto collaterale: 3 asserzioni pgTAP su codice morto

`db/pgtap/vendite/test-porta-oneri-giro-completo-v1.sql` **invoca davvero** la
funzione, alla riga **159**:

```sql
SELECT vendite.fn_generate_fatture_righe((SELECT lotto_id FROM tmp_lotto)) AS righe;
```

Il file dichiara 12 asserzioni, ma **solo 3 dipendono dalla funzione**.
Verificato riga per riga:

| Asserzioni | Righe | Cosa provano | Dopo il `DROP` |
|---|---|---|---|
| **1-9** | 99-149 | onere creato · commessa con ROOT source · `fn_emit_attivita_fatturabili_da_commessa` · propagazione `tipo_movimento`/qta/prezzo/articolo/approvato/sorgente sull'AF · lotto creato | ✅ **restano** — funzioni **in esercizio**, copertura genuina |
| **10-12** | 161, 169, 175 | riga di fattura generata, qta/prezzo, IVA dell'articolo-onere | ❌ da rimuovere: provano il **residuo** |

Quindi il costo del `DROP` non è «12 asserzioni sul giro completo», ma **3
asserzioni su un percorso che non viene eseguito**. Il file resta valido con
`plan(9)`, e cambia perimetro: da «onere → fattura» a «onere → attività
fatturabile», che è esattamente ciò che quelle 9 asserzioni provano davvero.

⚠️ **Il punto che conta.** Quelle 3 asserzioni sono verdi su **codice morto**: il
commento nel file lo ammette a mezza voce — *«il lock delle AF nel lotto è
emulato a mano … per pilotare `fn_generate_fatture_righe` in puro SQL»*. Non
stiamo perdendo copertura sulla fatturazione: stiamo scoprendo di **non averla
mai avuta** su quel tratto. È la stessa famiglia del difetto d'origine
([brief-fix-importi-riga-fattura-zero](brief-fix-importi-riga-fattura-zero.md)
§2.8): una suite verde che non tocca il percorso di produzione. Tenere in piedi
la funzione per non perdere quelle 3 asserzioni significherebbe conservare il
codice morto **per far contento il test che lo testa**.

La copertura vera del tratto AF → riga di fattura va costruita come smoke sul
percorso Python (§5, passo 3): è lavoro BE e non blocca il `DROP`.

---

## 4. Le opzioni

> **Premessa che cambia il peso**: **non siamo in produzione**
> ([[project_no_produzione_solo_sviluppo]]). Non c'è nessun sistema che si rompe,
> nessuna finestra di indisponibilità, nessuna migrazione dati. Il solo «rischio»
> del `DROP` è la perdita delle 3 asserzioni di §3, che coprono codice morto.

| | Come | Valutazione |
|---|---|---|
| **(a)** `DROP` subito, pgTAP a `plan(9)` *(raccomandata)* | rimuove le due funzioni e le asserzioni 10-12 nello stesso changeset | Chiude la questione in un colpo, senza stati intermedi da ricordare. Il costo è nullo: 3 asserzioni su codice non eseguito |
| **(b)** `COMMENT ON` ora, `DROP` dopo lo smoke Python | due passi, con una fase in cui la funzione esiste ma è dichiarata morta | Prudenza giustificata **solo** in produzione. Qui aggiunge un secondo giro di lavoro e uno stato intermedio che qualcuno deve ricordarsi di chiudere — cioè lo stesso meccanismo per cui la funzione è sopravvissuta da febbraio |
| **(c)** lasciare com'è | — | È lo stato che ha prodotto il problema. La formula *«può restare per compatibilità storica/transitoria»* è già stata messa alla prova e ha fallito |

**Raccomandazione: (a).**

Una prima stesura di questo brief raccomandava **(b)** dopo aver contato 12
asserzioni a rischio invece di 3, e senza pesare l'assenza di produzione. Con
entrambi i dati corretti la prudenza non ha più un oggetto da proteggere: **(b)**
si limiterebbe a rimandare, e i rinvii su questo oggetto hanno già un precedente.

**(b) è dominata, non solo meno conveniente.** Vale la pena dirlo per esteso,
perché è l'argomento che chiude la discussione: anche il `COMMENT ON` richiede un
changeset, quindi (b) costa **due** changeset contro uno e arriva allo stesso
stato finale. E soprattutto: in (b) **nulla lega il `DROP` all'esito dello
smoke** — §5 passo 3 dichiara esplicitamente che lo smoke non blocca. Il "cancello"
che (b) sembra offrire non è collegato a niente: è un rinvio con l'aspetto di una
cautela.

**Il contro-argomento vero, e perché non regge.** Non è il rischio operativo — è
che la SQL D4/D5 è oggi l'unica **specifica eseguibile** delle regole di
aggregazione e di snapshot kit (§6). Dopo il `DROP` resterebbe solo il Python: se
il porting avesse una divergenza, il riferimento con cui accorgersene sparisce.
La risposta è che **la specifica non sparisce affatto**: i changeset `-12`, `-15`
e `-17` sono già committati e pushati (`fc41e80e1`), e per regola di progetto i
changelog pushati **non si rimuovono**. Il corpo SQL con tutte le sue regole resta
leggibile in `db/changelog/migrations_v2/20_code/vendite/` e in git per sempre —
smette solo di essere un oggetto **installato**, che è esattamente ciò che
vogliamo. Il costo residuo è che un DB ricostruito da zero creerà le due funzioni
per poi rimuoverle poche migrazioni dopo: churn innocuo, e il prezzo inevitabile
di non riscrivere la storia.

---

## 5. Sequenza proposta

| # | Passo | Chi | Nota |
|---|---|---|---|
| 1 | `DROP FUNCTION vendite.fn_generate_fatture_righe` **e** `vendite.fn_group_attivita_fatturabili` | **team DB** | Un solo changeset |
| 2 | `test-porta-oneri-giro-completo-v1.sql`: `plan(12)` → `plan(9)`, via le righe 158-176 e le voci 10-12 dall'indice; aggiornare l'intestazione (il perimetro diventa «onere → attività fatturabile») | **team DB** | Insieme al passo 1: dopo il `DROP` quel file non gira |
| 3 | **Doc `manual/` dbzero** — vedi §5-ter: due pagine da ritirare e tre riferimenti da correggere | **team DB** | Sono scritte a mano, l'auto-gen **non** le tocca. Le pagine `funzioni/` spariscono da sole al prossimo `gen` |
| 4 | `test-articolo-regole-fatturazione.sql`: via il caso 4, `plan(7)` → `plan(6)` (§5-bis) | **team DB** | Debito latente di `-18`, non regressione. Chiuderlo ora che il contesto è fresco |
| 5 | Smoke Python sul tratto AF → riga di fattura, che esercita il **percorso reale** (`FattureRigheService`) | BE | **Non blocca** i passi 1-4: costruisce la copertura che non è mai esistita. Caso 7 di §10.2 del brief BE/FE |
| 6 | Manuale backend `fn_generate_fatture_righe.md`: togliere *«la funzione SQL può restare per compatibilità storica/transitoria»* e riscriverlo come «funzione SQL rimossa» | BE | È la frase all'origine dell'equivoco |
| 7 | Rimuovere `ALLOWED_TASK_FUNCTIONS` o renderlo funzionante (§2.4, §6) | BE | Dopo il passo 1, quelle due voci puntano a funzioni inesistenti |

**Le due funzioni nello stesso changeset — ma non per un vincolo del motore.**
Vanno droppate insieme perché non ha senso lasciare uno stato intermedio in cui
la gemella sopravvive senza chiamanti: è lo stesso meccanismo che ha tenuto in
vita il residuo da febbraio.

⚠️ Da non scriverlo come dipendenza: **PostgreSQL non registra le chiamate fra
funzioni `plpgsql`**. Il corpo è una stringa opaca risolta a runtime, non entra
in `pg_depend` — quindi droppare *prima* `fn_group_attivita_fatturabili`
**riuscirebbe** lo stesso, lasciando solo la chiamante rotta a runtime (cosa
irrilevante, visto che nessuno la chiama). Entrambe sono `plpgsql`, verificato in
doc auto-gen. Un `DROP` che fallisce per dipendenza si ha con le viste, o con le
funzioni SQL-standard `BEGIN ATOMIC` — non è questo il caso.

---

## 5-bis. Ricaduta di `-18` non ancora chiusa (`visibilita_componenti`)

Il `DROP` della colonna `vendite.articolo_regole_fatturazione.visibilita_componenti`
(changeset `-18`, applicato il 2026-07-28 alle 16:57) ha lasciato indietro un
riferimento. Censimento completo:

| Dove | Esito |
|---|---|
| BE (`types.py`, `pipeline_repository.py`, `fatture_righe_service.py`) | ✅ ripuliti, e riprovati sul DB reale dopo il `DROP` |
| FE | ✅ nessun riferimento, mai avuti |
| `fn_group_attivita_fatturabili` | ✅ ripulita da `-17`; resta solo una menzione **in un commento** |
| Altri oggetti DB (funzioni, viste) | ✅ nessuno |
| Seed `20260721-10-seed-articolo-regole-onere` | ✅ **falso allarme**: la nomina solo nel commento «PERCHE'», l'`INSERT` dichiara il solo `articolo_id` |
| **`db/pgtap/vendite/test-articolo-regole-fatturazione.sql`** | ⚠️ **da sistemare** |

Quel pgTAP contiene il caso **4) Check `visibilita_componenti`**, che fa
`SET visibilita_componenti = 'non_valido'` per provare il CHECK. Colonna e CHECK
non esistono più: il caso è **obsoleto**.

**Non è una regressione di `-18`**, e va detto con precisione: il file è già in
`baseline-rossi.tsv` come `ERRORE_FIXTURE` da prima, e fallisce a monte — sulla
fixture, perché `catalogo.articoli.uom_id` è `NOT NULL` e non viene valorizzato.
Verificato eseguendolo: si ferma alla riga 45, senza arrivare al caso 4.

Era quindi **debito latente**: il giorno in cui qualcuno avesse risanato la
fixture, quel caso sarebbe fallito sembrando un difetto nuovo. Rimosso ora che si
sa perché: **`plan(7)` → `plan(6)`**, via il blocco del caso 4 e la voce 4
dall'indice in testa al file. È il passo 4 di §5.

**E già che c'eravamo, risanata anche la fixture** (Tid ha rilanciato il file il
2026-07-28 e ha visto il rosso di sempre). L'`INSERT` in `catalogo.articoli` non
valorizzava `uom_id`, che è `NOT NULL`: il file esplodeva alla prima riga.
Aggiunta la risoluzione della UoM in `tmp_costanti_arf` — prima unità attiva
ordinata per `id`, lo stesso pattern degli altri pgTAP di `vendite` — perché il
test non dipende da *quale* unità sia: le serve solo soddisfare la FK.

⚠️ **Perché valeva la pena farlo qui.** Non è opportunismo: è la stessa lezione
di §3. Un file che fallisce nel *fixture* non esegue **nessuna** asserzione — la
sua copertura vale **zero, non parziale**, ed è un'area che *sembra* coperta
(6 test dichiarati, 0 eseguiti). Toglierlo da `baseline-rossi.tsv` fa **calare il
registro del debito**, che è l'obiettivo dichiarato della bonifica: la baseline
non è una lista di eccezioni tollerate.

➡️ **A file verde, va tolta la riga da `db/pgtap/baseline-rossi.tsv`** (o
`scripts/pgtap-baseline.sh --update vendite`). Finché resta lì, un rosso
rientrato viene segnalato come tale a ogni run.

---

## 5-ter. Doc `manual/` che sopravvivono al `DROP` (perimetro DB)

Le pagine `docs/it/dbzero/<schema>/funzioni/*.md` sono **auto-generate**: al
prossimo `gen` quelle delle due funzioni spariscono da sole, non vanno toccate a
mano ([[feedback_no_hand_edit_autogen_docs]]). Le pagine `manual/` invece sono
**scritte a mano** e restano lì a descrivere oggetti inesistenti:

| File | Intervento | Esito |
|---|---|---|
| `dbzero/vendite/manual/fn_generate_fatture_righe.md` | **ritirare** la pagina | ✅ cancellata |
| `dbzero/vendite/manual/fn_group_attivita_fatturabili.md` | **ritirare** la pagina | ✅ cancellata |
| `dbzero/vendite/funzioni/fn_generate_fatture_righe.md` | auto-gen: sparisce al prossimo `gen`, ma intanto è un link rotto | ✅ cancellata |
| `dbzero/vendite/funzioni/fn_group_attivita_fatturabili.md` | idem | ✅ cancellata |
| `dbzero/vendite/index.md` + `index.ci.md` | due voci d'elenco verso le pagine cancellate | ✅ rimosse |
| `dbzero/vendite/manual/fatture_righe.md` (§Popolamento) | attribuiva il popolamento della tabella alla fn SQL: descriveva uno **scrittore inesistente** | ✅ riscritto su `FattureRigheService` |
| `dbzero/anagrafiche/manual/billing_account.md` (catena `dest_billing_account_id`) | i passi 2 e 3 nominavano le due funzioni ritirate | ✅ riscritti sul servizio Python |
| `guide/fatturazione.md` (§Come si aggrega) | *«`fn_generate_fatture_righe` raggruppa…»*: è la guida che un lettore consulta per prima | ✅ riscritto su `FattureRigheService` |
| `backend/vendite/manual/fn_execute_pipeline_step.md` | dichiarava la fn SQL «ammessa se in whitelist» per il task `generate_fatture_righe` | ✅ riscritto: nessuna fn SQL, whitelist inerte |
| `work-done/brief-db-flag-fatturata-lista-attivita.md` | link `[doc:85]` alla pagina auto-gen cancellata | ✅ link rotto sanato, nota storica aggiunta |
| `dbzero/vendite/manual/trgfn_fatture_righe_importo.md` | due citazioni, **una sola** da correggere — vedi sotto | ✅ corretta l'analogia, lasciata la storica |

⚠️ **Da NON cancellare, contro l'istinto**: `backend/vendite/manual/fn_generate_fatture_righe.md`
e `backend/vendite/manual/fn_group_attivita_fatturabili.md`. I nomi ingannano —
sembrano le pagine delle due funzioni SQL — ma documentano gli **entrypoint
Python** `pipeline_service.fn_generate_fatture_righe` / `fn_group_attivita_fatturabili`
(righe 484 e 477), che **esistono e girano**. Cancellarle toglierebbe la
documentazione del codice vivo. Sono state invece **riscritte**: intestazione che
avverte del falso amico, e le *Note di migrazione* che dicono «funzione SQL
RIMOSSA» al posto del famigerato «può restare per compatibilità storica».

> 💡 **Debito segnalato, non chiuso qui**: quei due entrypoint Python si chiamano
> `fn_*` come le funzioni SQL che non esistono più. È il nome che ha reso
> possibile l'equivoco d'origine. Rinominarli (e rinominare le due pagine di
> manuale) è lavoro BE, va con il passo 7.

**Sulle due citazioni in `trgfn_fatture_righe_importo`, distinguere:**

- *«né `fn_generate_fatture_righe`, né il repository Python, né un trigger»* (§Il
  difetto che chiude) è **narrazione storica**: descrive chi *non* scriveva
  `imponibile_riga` a febbraio. Resta vera dopo il `DROP` — nominare un oggetto
  poi rimosso, dentro il racconto di un difetto passato, è corretto. **Non
  toccare.**
- *«È lo stesso pattern di `fn_group_attivita_fatturabili`»* (§Fallback e ordine)
  è invece un'**analogia al presente** con un oggetto che non esisterà più: va
  riscritta.

⚠️ **Verificato, contro l'ipotesi iniziale**: le citazioni nel DB vivo sono
commenti `--` **dentro il corpo** di `trgfn_fatture_righe_importo`, non il suo
`COMMENT ON FUNCTION` (controllato: il `COMMENT` non nomina né l'una né l'altra).
Sono anch'esse narrazione storica, e riscriverle costerebbe un `CREATE OR
REPLACE` della funzione — sproporzionato per un commento che resta vero.
**Nessun changeset per questo.**

---

## 6. Fuori perimetro DB

- **Pulizia di `ALLOWED_TASK_FUNCTIONS`** (§2.4): è codice BE. Il registro mappa
  nomi di funzioni SQL che non vengono mai confrontati con niente, perché nessuna
  configurazione di pipeline valorizza `fn`. Da rivedere lato backend — o si
  rimuove, o si fa in modo che serva davvero a qualcosa.
- **Le altre otto funzioni SQL** della pipeline (§2.1) sono **in esercizio**: non
  toccarle. Questo brief riguarda solo le due nominate in §1.
- **`fn_get_or_create_fattura_header`**: resta in esercizio, la chiama il
  servizio Python via `batch_get_or_create_fattura_headers`.
- **I changeset `-12`, `-15` e `-17`** non vanno disfatti né riportati indietro:
  sono già pushati, e per regola di progetto un changelog pushato **non si
  modifica**. Hanno svolto il ruolo di **specifica eseguibile** del porting
  Python, ed è la ragione per cui quel porting è stato fedele. L'oggetto che
  creano sparisce con il `DROP` del passo 1 — il testo delle regole resta in git,
  ed è tutto ciò che serve (§4).

---

## 7. Registro

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-28 | Rilevata la divergenza durante l'analisi BE post-land | Il task esegue Python; D4/D5 applicati sulla funzione SQL erano inerti |
| 2026-07-28 | Porting D4 + D5 nel servizio Python | Fatto e verificato su DB reale (brief BE/FE §13) |
| 2026-07-28 | Stesura di questo brief | Prima raccomandazione: `COMMENT ON` ora, `DROP` dopo |
| 2026-07-28 | **Revisione su osservazione di Tid** (assenza di produzione) | Raccomandazione **ribaltata a `DROP` diretto**. Ricontate le asserzioni pgTAP a rischio: **3 e non 12** — le altre 9 provano funzioni in esercizio e restano. Aggiunta §5-bis: censita la ricaduta di `-18`, un solo residuo reale (`test-articolo-regole-fatturazione.sql`, caso 4 obsoleto), seed e oggetti DB in chiaro |
| 2026-07-28 | **Esecuzione passi 1-4** | Changeset `20260728-21` scritto (DROP delle due funzioni, precondition di esistenza + guardia di non-uso). pgTAP: `test-porta-oneri-giro-completo-v1` a `plan(9)` con via anche l'emulazione del lock, che era setup del solo consumatore rimosso; `test-articolo-regole-fatturazione` a `plan(6)`. Doc: 4 pagine dbzero cancellate, 2 voci d'indice, 6 riferimenti in prosa riscritti, 1 link rotto sanato (§5-ter). ⚠️ **Nulla applicato sul DB** e nulla committato |
| 2026-07-28 | **Fixture di `test-articolo-regole-fatturazione` risanata** | Tid rilancia il file dopo il taglio del caso 4: rosso di sempre, `uom_id` NOT NULL non valorizzato nell'`INSERT` in `catalogo.articoli` — il file esplodeva nel fixture, **0 asserzioni su 6 dichiarate**. Aggiunta la risoluzione UoM col pattern degli altri pgTAP vendite. A verde, togliere la riga da `baseline-rossi.tsv` (§5-bis) |
| 2026-07-28 | ✅ **BRIEF CHIUSO lato DB** — spostato in `work-done/` | `DROP` applicato al terzo tentativo, col changeset corretto (`HALT`, guardia unica, rollback no-op dichiarato): `pg_proc` non contiene più né `fn_generate_fatture_righe` né `fn_group_attivita_fatturabili` — **0 righe**. La guardia di non-uso è quindi passata su un DB reale, confermando le evidenze di §2.3. **`test-porta-oneri-giro-completo-v1` verde a funzioni assenti**: il `plan(9)` è stato esercitato nella condizione per cui era stato tagliato, non per inerzia. Chiuse nel brief padre **P3** (§12) e la riga `-17` (§3-bis). Restano i soli passi BE 5 e 7 |
| 2026-07-28 | ⚠️ **Il secondo `-21` è stato «applicato» senza fare nulla** | Tid lancia il migrate: nessun errore, e nessun effetto. Causa: `onFail: **MARK_RAN**` sulle preconditions. Quando la guardia non passa, Liquibase fa ciò che gli è stato chiesto — salta le modifiche **e segna il changeset come eseguito**: il `DROP` non parte, non si vede un errore, e la riga finisce in `DATABASECHANGELOG`, così il migrate successivo lo considera già fatto. Un silenzio: esattamente il difetto che questo brief esiste per rimuovere. Corretto in `onFail: HALT`, e **rimosse le due preconditions di esistenza** (`expectedResult: 1`): inutili — il `DROP` è `IF EXISTS` — e dannose, perché con una firma in overload il conteggio fa 2 e la guardia fallisce. Resta la sola guardia che porta informazione. Sanato anche il `rollback: - empty`, che era un'invenzione non valida per lo schema Liquibase: sostituito col no-op dichiarato del precedente `20260415-03`. ➡️ **La riga `20260728-21` va tolta da `DATABASECHANGELOG` prima di rilanciare**, altrimenti il changeset resta saltato |
| 2026-07-28 | ⚠️ **Il primo `-21` è esploso al migrate**: `ERRORE: "array_agg" è una funzione di aggregazione` | La guardia di non-uso scandiva `pg_proc` di tutto lo schema chiamando `pg_get_functiondef()`. **PostgreSQL non garantisce l'ordine di valutazione dei predicati in `WHERE`**: il planner ha letto i corpi *prima* dei filtri su schema e tipo, arrivando su un'aggregata — e su aggregate/window `pg_get_functiondef` solleva. Corretto con **due** presidi: `prokind = 'f'` e `WITH … AS MATERIALIZED` come barriera di ottimizzazione. Il changeset era a `Run: 0`, quindi mai in `DATABASECHANGELOG`: correggibile in place. Il `-18` non ci era incappato perché filtrava un `proname` singolo e selettivo |
| 2026-07-28 | **Revisione critica del brief** (residui della lunga gestazione) | 7 correzioni. **Errore tecnico**: l'«ordine obbligato» del `DROP` era motivato con una dipendenza inesistente — PostgreSQL non traccia le chiamate fra funzioni `plpgsql` (§5). **§6 era duplicata** in due copie divergenti (`passo 1` vs `passo 3`): rimossa quella stale. Header: «perimetro BE chiuso» → è chiuso il **porting D4/D5**, il brief padre resta aperto su B5/B8/§10.2-7-8. §2.4: verifica estesa alla **sorgente del seed** (non solo al DB di dev, che non governa la CI) e riferimento di riga corretto (148, non 143). §4: aggiunta la dominanza di (a) su (b) e dispacciato il contro-argomento «si perde la specifica eseguibile» (i changeset pushati non si rimuovono: resta in git). Nuova **§5-ter**: 5 doc `manual/` dbzero che sopravvivono al `DROP`, perimetro DB, mancavano dalla sequenza. §5-bis: `plan(7)` → `plan(6)`, esplicito |
