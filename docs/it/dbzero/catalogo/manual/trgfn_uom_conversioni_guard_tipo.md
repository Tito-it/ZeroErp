## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_uom_conversioni_guard_tipo`

> **Ultimo aggiornamento**: 9 novembre 2026
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
> * [catalogo.trgfn_unita_misura_guard_tipo](/dbzero/catalogo/funzioni/trgfn_unita_misura_guard_tipo) — l'altra metà della regola, sul lato delle unità
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

Legge la famiglia delle due unità e rifiuta se sono diverse, con
`E_UOM_CONVERSIONE_TIPO_DIVERSO`: la frase nomina le due unità e le due famiglie. Se una delle
due unità non esiste lascia passare, e la riga la rifiuta subito dopo la chiave verso
`unita_misura`.

---

### ⭐ Al riparo dalla concorrenza

Le due unità si leggono bloccandole in condivisione (`FOR SHARE`). Se un'altra transazione sta
cambiando la famiglia di una delle due, il guard aspetta che finisca e legge la famiglia
nuova; se è la conversione ad arrivare prima, il cambio di famiglia aspetta lei, e poi trova la
conversione e si ferma (`E_UOM_TIPO_IN_USO`, dal guard delle unità). In nessun ordine nasce
una conversione fra famiglie diverse.

---

### Codici errore

* `E_UOM_CONVERSIONE_TIPO_DIVERSO` — le due unità della conversione sono di famiglie diverse. Area
  `catalogo`; in `error_log` col nome della funzione.

---

### Test

* `db/pgtap/catalogo/test-uom-tipi-global-conversioni-v1.sql` — una conversione fra due unità
  della stessa famiglia passa; una fra massa e lunghezza è rifiutata.
* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — il codice della famiglia diversa,
  dalla frase del messaggio.

---

### Note di migrazione

* 2026-04-28 — nasce con le famiglie delle unità.
* 2026-11-09 — un codice registrato al posto di `E_GENERICO`, il nome della funzione nel log,
  le unità lette `FOR SHARE` (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
