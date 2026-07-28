# Brief DB — Ritiro del generatore righe fattura SQL (residuo non in esercizio)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-28 · **Owner**: Tid · **Stato**: 🔴 **APERTO** ·
> **Priorità**: 🟠 **MEDIA** — nessun dato a rischio e nessun malfunzionamento in
> corso, ma è la condizione che il 2026-07-28 ha fatto finire **una giornata di
> lavoro DB su codice che non viene eseguito**.
>
> **Origine**: voce **B7** di
> [brief-be-fe-importi-riga-fattura.md](brief-be-fe-importi-riga-fattura.md) §7.
> Il perimetro BE di quel brief è chiuso: D4 e D5 sono stati portati nel servizio
> Python e sono in esercizio.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.
>
> **Come leggere**: §1 è la richiesta in breve, §2 i fatti verificati sul DB e sul
> codice vivi, §3 **il vincolo** che impedisce un `DROP` immediato, §4 le opzioni
> con la raccomandazione, §5 la sequenza proposta, §6 cosa NON è in perimetro.

---

## 1. La richiesta, in breve

Due funzioni SQL non sono in esercizio ma sembrano esserlo:

| Funzione | Stato reale | Chiamanti |
|---|---|---|
| `vendite.fn_generate_fatture_righe(bigint, boolean)` | residuo: il task pipeline esegue Python | **nessuno** nel DB |
| `vendite.fn_group_attivita_fatturabili(bigint)` | residuo: il servizio Python usa `_build_group_key` | solo la funzione qui sopra |

Si chiede di **dichiararle fuori esercizio** e poi di **rimuoverle**, con la
sequenza di §5 — non subito, per il vincolo di §3.

---

## 2. Fatti verificati (DB e codice vivi, 2026-07-28)

### 2.1 Il task della pipeline non esegue la funzione SQL

[`pipeline_step_executor.py:454`](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L454)
chiama `self.fatture_righe_service.generate_fatture_righe(...)`.

Ed è l'**unica** eccezione su nove task. Mappatura completa, verificata handler
per handler:

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
[`pipeline_repository.py:143`](../../../../backend/apps/vendite/db/pipeline_repository.py#L143),
con un commento che dichiara già l'ambiguità: *«`fn` nei JSON task è mantenuto
come token di compatibilità SQL legacy»*.

Verificato che è **completamente inerte**:

- `SELECT count(*) FROM vendite.fatturazione_pipeline WHERE processi::text LIKE '%"fn"%'`
  → **0**: nessuna configurazione di pipeline contiene la chiave `fn`;
- di conseguenza `_validate_task_function_name` riceve sempre `fn_name = None`, e
  il suo guard è `if fn_name and fn_name != allowed` → non scatta mai.

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

---

## 5. Sequenza proposta

| # | Passo | Chi | Nota |
|---|---|---|---|
| 1 | `DROP FUNCTION vendite.fn_generate_fatture_righe` **e** `vendite.fn_group_attivita_fatturabili` | **team DB** | Un solo changeset |
| 2 | `test-porta-oneri-giro-completo-v1.sql`: `plan(12)` → `plan(9)`, via le righe 158-176 e le voci 10-12 dall'indice; aggiornare l'intestazione (il perimetro diventa «onere → attività fatturabile») | **team DB** | Insieme al passo 1: dopo il `DROP` quel file non gira |
| 3 | Smoke Python sul tratto AF → riga di fattura, che esercita il **percorso reale** (`FattureRigheService`) | BE | **Non blocca** i passi 1-2: costruisce la copertura che non è mai esistita. Caso 7 di §10.2 del brief BE/FE |
| 4 | Manuale backend `fn_generate_fatture_righe.md`: togliere *«la funzione SQL può restare per compatibilità storica/transitoria»* e riscriverlo come «funzione SQL rimossa» | BE | È la frase all'origine dell'equivoco |
| 5 | Rimuovere `ALLOWED_TASK_FUNCTIONS` o renderlo funzionante (§2.4, §6) | BE | Dopo il passo 1, quelle due voci puntano a funzioni inesistenti |

⚠️ **Ordine obbligato dentro il passo 1**: le due funzioni vanno droppate
**insieme**, oppure prima `fn_generate_fatture_righe`. L'inverso fallisce, perché
è l'unica che chiama l'altra.

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

È quindi **debito latente**: il giorno in cui qualcuno risana la fixture — che è
l'obiettivo dichiarato della bonifica baseline — quel caso fallirà, e sembrerà un
difetto nuovo. Conviene rimuoverlo ora che si sa perché (`plan` da adeguare),
mentre il contesto è fresco.

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
- **Il codice di aggregazione D4/D5 scritto nei changeset `-12` e `-15`** non va
  disfatto né riportato indietro: è servito da **specifica eseguibile** per il
  porting Python, ed è la ragione per cui quel porting è stato fedele. Sparirà
  con il `DROP` del passo 1, e va bene così.

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
- **Il codice di aggregazione D4/D5 scritto nei changeset `-12` e `-15`** non va
  disfatto né riportato indietro: è servito da **specifica eseguibile** per il
  porting Python, ed è la ragione per cui quel porting è stato fedele. Sparirà
  con il `DROP` del passo 3, e va bene così.

---

## 7. Registro

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-28 | Rilevata la divergenza durante l'analisi BE post-land | Il task esegue Python; D4/D5 applicati sulla funzione SQL erano inerti |
| 2026-07-28 | Porting D4 + D5 nel servizio Python | Fatto e verificato su DB reale (brief BE/FE §13) |
| 2026-07-28 | Stesura di questo brief | Prima raccomandazione: `COMMENT ON` ora, `DROP` dopo |
| 2026-07-28 | **Revisione su osservazione di Tid** (assenza di produzione) | Raccomandazione **ribaltata a `DROP` diretto**. Ricontate le asserzioni pgTAP a rischio: **3 e non 12** — le altre 9 provano funzioni in esercizio e restano. Aggiunta §5-bis: censita la ricaduta di `-18`, un solo residuo reale (`test-articolo-regole-fatturazione.sql`, caso 4 obsoleto), seed e oggetti DB in chiaro |
