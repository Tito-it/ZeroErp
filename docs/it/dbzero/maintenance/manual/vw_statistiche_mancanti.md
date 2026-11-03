## 📘 Documentazione Concettuale – Vista `maintenance.vw_statistiche_mancanti`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [maintenance.fn_analyze_statistiche](/dbzero/maintenance/funzioni/fn_analyze_statistiche) — la legge subito dopo `ANALYZE`, come autoverifica
> * [maintenance.proc_analyze_statistiche_job](/dbzero/maintenance/funzioni/proc_analyze_statistiche_job) — il job dentro cui la risposta conta

---

### 🎯 Scopo Principale

Le tabelle che, per il ruolo che la interroga, resterebbero senza statistiche dopo un
`ANALYZE`: o perché quel ruolo non può analizzarle, o perché non sono mai state analizzate.

È la prova che `maintenance.fn_analyze_statistiche` usa subito dopo il suo lavoro, e si può
leggere a mano per sapere oggi quali tabelle il pianificatore stima alla cieca.

---

### Due motivi, e il primo vince

Ogni riga porta un motivo:

* **`NON_ANALIZZABILE`** — il ruolo non ha il diritto `MAINTAIN` sulla tabella: `ANALYZE` la
  salterebbe con un avviso. Il diritto ce l'ha il proprietario, un superuser, o chi ha
  `pg_maintain`.
* **`MAI_ANALIZZATA`** — la tabella non ha mai ricevuto né un `ANALYZE` né un `VACUUM`: il
  catalogo la segna con un numero di righe stimato negativo.

Una tabella che è in tutti e due i casi compare come `NON_ANALIZZABILE`: finché manca il diritto,
analizzarla non è possibile, e il rimedio è quello.

⚠️ `MAI_ANALIZZATA` si legge da `pg_class`, che sta nel catalogo e sopravvive a un crash. I
contatori di `pg_stat_*` (come `last_analyze`) no: dopo un riavvio sporco direbbero «mai» di
una tabella che le statistiche le ha.

---

### Il perimetro, per struttura

Tabelle ordinarie e partizionate (le partizioni comprese, che sono tabelle ordinarie),
**tranne**:

* gli schemi di sistema (`pg_catalog`, `information_schema`, quelli di `pg_toast`);
* le tabelle temporanee delle **altre** sessioni: quelle della sessione corrente restano
  dentro, ed è ciò che lascia a un pgTAP costruire il suo caso;
* gli oggetti che appartengono a un'**estensione** (`pgagent`, PostGIS, topology), riconosciuti
  dalla dipendenza registrata nel catalogo, non da un elenco di nomi.

Il perimetro si deriva dal catalogo: una tabella nuova ci entra da sola, senza che nessuno
aggiorni un elenco.

⚠️ **Una tabella partizionata senza partizioni** non ha dati da descrivere e resta senza
statistiche anche dopo `ANALYZE`: per questo il ramo `MAI_ANALIZZATA` la esclude. Il ramo
`NON_ANALIZZABILE` no: se il ruolo non ha il diritto, compare anche lei.

---

### ⚠️ Risponde per il ruolo che sta eseguendo

Il diritto si misura sul **ruolo effettivo** di chi interroga la vista, non su chi si è
collegato. Letta come `zeroerp_app`, **ogni** tabella di progetto risulta `NON_ANALIZZABILE`, ed
è giusto: l'applicazione non analizza.

La risposta che conta è quella data dentro il job: `maintenance.proc_analyze_statistiche_job` è
`SECURITY DEFINER`, quindi lì la vista risponde per il proprietario della procedura,
`zeroerp_owner`, e non per `zeroerp_job`, il ruolo con cui pgAgent si collega. Per rifare a mano
la stessa domanda si legge la vista come `zeroerp_owner`.

---

### Test

`db/pgtap/maintenance/test-fn-analyze-statistiche-v1.sql` — le tabelle temporanee costruite
dal test compaiono come `MAI_ANALIZZATA` prima di `ANALYZE` e spariscono dopo; la partizionata
senza partizioni non c'è; una tabella che il ruolo non può analizzare compare come
`NON_ANALIZZABILE` (caso saltato in modo dichiarato quando il test gira da proprietario o
superuser); nessun oggetto di un'estensione è nel perimetro.

---

### Note di migrazione

* 2026-10-14 — nasce con la funzione e il job notturno
  (`brief-db-statistiche-tabelle-job-notturno`, D15). Il comportamento della partizionata senza
  partizioni è provato su PostgreSQL 18.6.

---

{% include-markdown "signature-core.md" %}
