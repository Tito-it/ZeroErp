## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_chiusura_scadenze`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze) — il registro dei bersagli che la funzione legge
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — il lavoro `CHIUSURA_SCADENZE` dentro cui la funzione gira
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove resta la riga di ogni giro
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — la sveglia che accoda un lavoro per azienda
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta che manda una testata al suo verbo di chiusura
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale con cui si confronta la scadenza
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la scrittura dell'audit
>
> Guide:
>
> * [Processi automatici: classe e identità](/guide/processi-automatici-classe-e-identita) — perché la chiusura gira con l'identità di un'azienda
> * [Linee guida SQL — 7c Ciclo stato + finestra di validità](/linee-guida-sql#7c-ciclo-stato-finestra-di-validita) — il modello delle tabelle bersaglio

---

### 🎯 Scopo Principale

Il motore della chiusura per scadenza: per ogni riga attiva di
`dbops.automazione_chiusura_scadenze` porta allo stato «chiuso» le righe ancora «attive» la cui
data di fine validità è passata, e restituisce quante ne ha chiuse per tabella.

La chiama l'handler del lavoro di coda `CHIUSURA_SCADENZE`, un'azienda alla volta. È `SECURITY
INVOKER`: vede e chiude solo ciò che vede l'identità con cui gira.

---

### ⭐ Il perimetro è l'identità, non un parametro

pgAgent non chiama questa funzione: sveglia `dbops.fn_accoda_chiusura_scadenze`, che accoda un
lavoro per ogni azienda con l'identità tecnica di quell'azienda. Il drenatore apre quell'identità e
l'handler chiama la funzione: la row level security dei bersagli fa il resto. Nessun argomento
dice per quale azienda lavorare, perché una seconda sede del perimetro è quella che si dimentica.

Anche «scaduto» è dell'azienda: la scadenza si confronta con `script.fn_data_operativa()`, il
giorno nel fuso dell'azienda, non con la data del server. Una riga con data di fine vuota non
scade mai.

---

### Due strade per chiudere

* **Testata sotto la porta del modello del documento** (`tipo_stato = FK` e la porta
  `script.trgfn_doc_stato_solo_dal_verbo` sulla tabella): la funzione non scrive lo stato, chiama
  il verbo dichiarato in `verbo_chiusura`, e il conteggio è quello che il verbo restituisce. È la
  strada di tutti i bersagli di oggi.
* **Tutte le altre**: un `UPDATE` della colonna di stato dallo stato attivo a quello chiuso, sulle
  righe scadute. Con `tipo_stato = FK` i due codici si traducono prima nei loro id, nella tabella
  di vocabolario dichiarata.

⚠️ La presenza della porta si guarda solo nel ramo `FK`. Una tabella `VARCHAR` sotto la porta non
arriverebbe al verbo: il suo `UPDATE` sarebbe rifiutato dalla porta. E un `verbo_chiusura`
dichiarato su una tabella senza porta non si usa.

Gli identificatori e i valori del registro entrano nello SQL dinamico sempre quotati, anche se il
registro lo scrive solo il seed.

---

### ⛔ Una riga di configurazione rotta ferma il giro

Prima di lavorare una riga la funzione controlla che esistano la tabella, la colonna di stato e
quella della data; per `FK` anche la tabella di vocabolario e i due codici; per una testata sotto
la porta, che il verbo sia dichiarato e sia una funzione viva senza argomenti. Qualunque mancanza
solleva `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`, e il motivo nel contesto dice quale.

Il fallimento non si isola per riga: il giro si ferma e la transazione si annulla, comprese le
tabelle già chiuse prima. È voluto: il lavoro di coda va in errore, si riprova fino ai tentativi
del tipo, e poi resta in `dbops.vw_coda_lavori_da_guardare`. L'isolamento c'è, ma è **per
azienda**, un livello sopra: lo dà la coda.

---

### Che cosa restituisce

Un oggetto con una chiave `schema.tabella` per ogni bersaglio lavorato, col numero di righe chiuse
(anche zero), più il totale (`_total`) e l'istante del giro (`_executed_at`). L'handler lo scrive
nel risultato del lavoro di coda.

Ripetere il giro nello stesso giorno non chiude niente di nuovo: le righe già chiuse non sono più
nello stato attivo.

---

### L'audit di ogni giro

A giro finito la funzione scrive una riga in `dbops.audit_log`, status `OK`, con il riepilogo nei
parametri. La scrittura è **best-effort**: se fallisce, l'errore si inghiotte e il riepilogo arriva
comunque a chi ha chiamato. Lo stesso inghiottimento rende muto un audit che non si scrive:
nessuno se ne accorgerebbe se non contando le righe.

---

### `p_classe`: un filtro che oggi nessuno passa

Con una classe, la funzione lavora solo i bersagli di quella classe; senza (il default), lavora
tutti i bersagli attivi. L'handler della coda chiama senza argomenti.

⚠️ Il filtro non è il cancello: il cancello è il `NOT NULL` su
`automazione_chiusura_scadenze.classe`, che obbliga ogni riga a dichiarare la propria natura. Oggi
tutti i bersagli sono `DOMINIO`, quindi lavorarli tutti e lavorare i `DOMINIO` è la stessa cosa.

---

### Codici errore

* `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` — una riga attiva del registro non è applicabile:
  tabella, colonna o tabella di vocabolario inesistente, codice attivo o chiuso non trovato, testata
  sotto la porta senza verbo o con un verbo che non è una funzione viva senza argomenti, tipo di
  stato non gestito. Il contesto porta l'id della riga, la tabella bersaglio e il motivo.

---

### Test

* `db/pgtap/dbops/test-fn-apply-chiusura-scadenze-v1.sql` — la chiusura col verbo su versione di
  listino e contratto, l'idempotenza, i rifiuti per tabella, colonna o codice inesistenti, la
  testata sotto la porta senza verbo, il verbo che non esiste. ⚠️ Il ramo `UPDATE` diretto non ha
  un bersaglio configurato: lo attraversano solo i controlli preliminari.
* `db/pgtap/dbops/test-chiusura-scadenze-classe.sql` — la chiamata senza argomenti, e con una
  classe senza bersagli attivi non lavora niente.
* `db/pgtap/dbops/test-chiusura-scadenze-audit-v1.sql` — un giro scrive una riga di audit `OK`
  con il riepilogo restituito.
* `db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` — la sveglia che porta qui.
* `db/pgtap/vendite/test-contratto-al-modello-v1.sql`,
  `db/pgtap/vendite/test-contratti-guard-transizione-stato-v1.sql` — la cessazione del contratto
  passando dal motore.

---

### Note di migrazione

* 2026-04-26 — nasce, chiamata ogni notte da pgAgent su tutti i bersagli.
* 2026-09-04 — nasce `p_classe` (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-05 — pgAgent smette di chiamarla: la chiama il lavoro di coda, un'azienda alla volta.
* 2026-10-26 — una testata sotto la porta si chiude col suo verbo; la GUC
  `app.cessazione_automatica` si ritira (`brief-modello-documento-vendita`).
* 2026-10-28 — il verbo si legge da `verbo_chiusura` del registro, non da un caso scritto per il
  contratto.
* 2026-11-03 — l'audit si scrive con status `OK`: fino ad allora era `INFO`, fuori dal vincolo, e
  non si è mai scritto (`brief-db-revisione-maintenance` R5).

---

{% include-markdown "signature-core.md" %}
