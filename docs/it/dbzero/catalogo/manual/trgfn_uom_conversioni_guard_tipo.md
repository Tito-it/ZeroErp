## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_uom_conversioni_guard_tipo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — la tabella su cui è montata
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le due unità di cui legge la famiglia
> * [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi) — le famiglie
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la sede dei fattori di un solo articolo, che questa regola non tocca
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_unita_misura_guard_tipo_update](/dbzero/catalogo/funzioni/trgfn_unita_misura_guard_tipo_update) — l'altra metà della regola, sul lato delle unità
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

Rifiuta una conversione globale fra due unità di misura di famiglie diverse: in
`catalogo.unita_misura_conversioni` si convertono chilogrammi in grammi, non metri in grammi.

Una conversione fra famiglie diverse non ha un senso valido per tutti gli articoli. I
rapporti che dipendono dal prodotto (il cartone da 12 pezzi, il bancale) stanno in
`articoli_uom_operativa`, dove il fattore è per articolo: questo guard tiene separati i due
posti.

---

### Quando scatta

Prima di ogni inserimento, e degli aggiornamenti che scrivono una delle due unità. Un
aggiornamento del solo fattore o del periodo non tocca la famiglia, e il controllo non gira.

Legge la famiglia delle due unità e rifiuta se sono diverse. Ogni unità ha sempre una
famiglia (la colonna è obbligatoria, con la sua chiave), quindi il ramo che lascia passare
quando una famiglia non si trova scatta solo per un'unità che non esiste, e in quel caso
la riga la rifiuta subito dopo la chiave verso `unita_misura`.

---

### ⚠️ Che cosa oggi non copre

* **L'errore esce come errore tecnico.** Il codice è `E_GENERICO`, con una frase libera come
  messaggio: all'operatore arriva come errore tecnico, e il backend non lo distingue da
  qualunque altro errore generico. In `error_log` la causa si riconosce solo dal contesto
  (le due unità e le due famiglie).
* **In `error_log` c'è il nome del trigger, non quello della funzione**:
  `trg_uom_conversioni_a10_guard_tipo_ins_upd`. Chi cerca dal nome della funzione non trova
  le righe.
* **Non è al riparo dalla concorrenza.** Legge la famiglia delle unità senza bloccarle: se
  un'altra transazione sta cambiando la famiglia di una delle due, il guard vede quella
  vecchia, nessuna delle due transazioni aspetta l'altra, e può nascere una conversione fra
  famiglie diverse.

---

### Codici errore

* `E_GENERICO` — le due unità della conversione sono di famiglie diverse. Area `catalogo`.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — una conversione fra due unità
  della stessa famiglia passa; una fra massa e lunghezza è rifiutata.

---

### Note di migrazione

* 2026-04-28 — nasce con le famiglie delle unità.

---

{% include-markdown "signature-core.md" %}
