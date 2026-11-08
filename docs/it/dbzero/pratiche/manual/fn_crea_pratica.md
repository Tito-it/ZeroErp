## 📘 Documentazione Concettuale – Funzione `pratiche.fn_crea_pratica`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica che nasce, coi suoi trigger
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — lo stato iniziale `APERTA`
> * [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche) — la priorità predefinita `NORMALE`
>
> Approfondimento funzioni:
>
> * [vendite.fn_genera_pratica_da_preventivo](/dbzero/vendite/funzioni/fn_genera_pratica_da_preventivo) — una madre di dominio che la chiama
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

`pratiche.fn_crea_pratica` è il building block condiviso che crea una pratica e ne ritorna l'id: risolve
lo stato iniziale `APERTA` e, se non è data, la priorità predefinita `NORMALE`, poi inserisce la riga.

La creazione è identica per ogni sorgente (preventivo, ordine, i domini che verranno): ogni funzione
madre di dominio la chiama e aggiunge solo la sua parte specifica, la risoluzione del contesto e il
collegamento al proprio documento. L'atomicità di ogni dominio si ottiene così senza duplicare la
creazione della pratica.

---

### Il significato dei parametri

* Emittente e tipo di prestazione sono obbligatori; soggetto, ruolo del soggetto, istanza della
  utility, priorità, descrizione e metadati sono facoltativi.
* `p_billing_account_id`, in coda e facoltativo, è il cliente di cui parla la pratica, a grana fine.

---

### ⭐ I guard non sono nella funzione: sono sulla tabella

La funzione non ripete nessun controllo: li fanno i trigger di `pratiche.pratiche` all'inserimento, e
valgono per qualunque strada di scrittura. Fra questi la coerenza del contesto, il perimetro
dell'emittente, la definizione del workflow risolta e fissata alla nascita, i riferimenti attivi
(emittente, tipo, stato, priorità, soggetto, unità organizzativa, canale), il tipo di prestazione non
obsoleto, il codice, l'audit, la transazione, la data di apertura e il giornale.

⚠️ Il controllo «tipo di prestazione ammesso prima o dopo l'attivazione del cliente» non sta nel
database: lo fa il servizio del backend, e la funzione non lo ripete. I chiamanti che ne hanno bisogno
lo verificano prima.

---

### Sicurezza

`SECURITY INVOKER`: la RLS su `pratiche.pratiche` si valuta come per chi la chiama.

---

### Codici errore

* `E_CONFIG_MANCANTE` — manca a catalogo lo stato `APERTA` o la priorità `NORMALE`.

---

### Note di migrazione

* 2026-07-08 — nasce come building block comune delle madri di dominio, per chiudere la creazione della
  pratica in una transazione sola col dominio (analisi-fix-transazioni).
* 2026-10-08 — arriva il parametro `p_billing_account_id`, in coda; la firma vecchia è stata tolta,
  perché un overload avrebbe reso ambigue le chiamate per nome (brief-db-istanza-nasce-col-ba).

---

{% include-markdown "signature-core.md" %}
