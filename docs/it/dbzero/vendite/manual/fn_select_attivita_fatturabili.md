## 📘 Documentazione Concettuale – Funzione `vendite.fn_select_attivita_fatturabili`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività che seleziona e blocca
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa, che dice il gruppo fatturabile
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza utility
> * [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale) — il tipo documento richiesto
>
> Approfondimento funzioni:
>
> * [backend.fn_execute_pipeline_step](/backend/vendite/funzioni/fn_execute_pipeline_step) — il passo di pipeline che la chiama

---

### 🎯 Scopo Principale

La funzione **`vendite.fn_select_attivita_fatturabili()`** seleziona le righe
**eleggibili** per la fatturazione e, se richiesto, le **locka** in modo atomico.

---

### Regole principali

* `competenza_mese` e` obbligatoria e viene normalizzata al primo del mese.
* `tipo_doc_fiscale_id` e` obbligatorio.
* Se `p_lock = true` allora `p_lock_batch_id` e` obbligatorio.
* Vengono escluse righe:
  * gia` fatturate,
  * sospese,
  * non approvate,
  * lockate.
* Rispetta `posticipa_al` e la regola di competenza su `competenza_mese`.
* Con `p_lock = true` usa `FOR UPDATE SKIP LOCKED` e aggiorna
  `lock_in_fatturazione` + `lock_batch_id`.
* `p_lock = false` equivale a una **dry-run**: nessuna scrittura, solo selezione.

---

### Filtri opzionali

* `billing_account_id`
* `utility_id` (da billing_account)
* `valuta_id`
* `emittente_soggetto_ruolo_id` (da mapping BA → emittente)
* `area_geografica_id`
* `p_limit` limita il numero massimo di righe elaborate/lockate.(Accetta null=  no limite)

---

### Output

Ritorna le righe selezionate (o lockate) ordinate per `data_attivita`, `id`.

---

### ⭐ Emissione mirata: `p_gruppi`

Parametro `text[]`, default `NULL`, stessa semantica delle altre funzioni della
catena (`NULL` = nessuna restrizione, `'{}'` = zero righe, chiave inesistente =
zero righe senza errore).

**La falla che chiude.** Questa funzione seleziona e blocca le attività su cui
il lotto costruirà le righe fattura, filtrando per approvato, non fatturato, non
sospesa, non lockata, `posticipa_al`, competenza, tipo doc, BA, utility,
emittente, valuta, area. **Nessuno di questi criteri sa nulla della sorgente.**

Conseguenza senza il filtro: un lotto mirato al gruppo A rastrella qualunque
attività fatturabile **già esistente** e non ancora consumata del gruppo B nello
stesso perimetro. I residui non sono un caso di scuola — nascono da un giro
interrotto fra pull e generazione righe, da un reset a bozza, o dal giro
schedulato che ha fatto pull senza completare.

Il risultato sarebbe una fattura **corretta nella forma e sbagliata nel
perimetro**: l'errore peggiore, perché silenzioso.

#### Come, e perché così

Il legame attività → documento **non è** su `attivita_fatturabili`: l'attività non
porta una provenienza propria, ma punta la riga di commessa con `commessa_attivita_id`,
**NOT NULL**. Il gruppo si ricava con un **JOIN** alla riga di commessa: dal suo tipo
d'origine, dalla sua chiave di segmento e dalla commessa, la stessa chiave del gruppo
fatturabile che calcola il resto della catena.

Da qui la scelta di **non denormalizzare**: nessuna colonna nuova su una tabella
calda, nessun backfill, nessun drift possibile fra valore copiato e sorgente. Il
join si aggiunge **solo** quando `p_gruppi` è valorizzato: il giro schedulato
non paga nulla, né in forma né in piano d'esecuzione.

#### ⚠️ `FOR UPDATE OF a` — invariante da non rompere

Anche in presenza del join, il lock resta ristretto ad `attivita_fatturabili`.
Estenderlo a `commesse_attivita` serializzerebbe il giro di fatturazione con le
operazioni di commessa (approvazioni, oneri): un deadlock che oggi non esiste.

---

### Note di migrazione

* 2026-06-19 — il lock diventa `FOR UPDATE OF a`, ristretto ad `attivita_fatturabili`.
* 2026-07-27 — aggiunto `p_gruppi`, l'emissione mirata per gruppo fatturabile.
* 2026-11-07 — ritirate le colonne di provenienza di `attivita_fatturabili` (che portavano
  l'impronta d'idempotenza del pull e il tipo d'origine): il gruppo si legge solo dalla riga di
  commessa, come già faceva il filtro (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
