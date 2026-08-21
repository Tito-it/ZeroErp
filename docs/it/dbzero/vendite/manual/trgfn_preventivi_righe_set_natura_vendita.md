## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_righe_set_natura_vendita()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [config.nature_vendita](/dbzero/config/tabelle/nature_vendita)
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — MODALITÀ A, brief preventivi-ordini D9)

Fa **due cose con una sola lettura** dell'articolo:

1. **eredita e congela** la natura di vendita: `preventivi_righe.natura_vendita_id` viene
   **sempre** presa da `catalogo.articoli.natura_vendita_id`, sovrascrivendo qualunque valore
   fornito dal chiamante. Nessun override dell'operatore;
2. **blocca la ricorrenza sul preventivo**: se la natura dell'articolo ha
   `destinazione_tipo = 'CONTRATTO'`, la riga non può stare su un preventivo.

La seconda è la regola di dominio vera. Un articolo a ricorrenza — un canone — non si vende
con un preventivo: si vende con un'**offerta commerciale**, che è il documento pensato per
generare un contratto. Il blocco è fail-fast all'inserimento della riga, non un controllo
all'emissione: l'errore arriva mentre si costruisce il documento, quando correggerlo costa
poco.

⭐ Il controllo è **data-driven**: guarda `destinazione_tipo`, non il codice della natura.
Aggiungere una natura nuova mappata a `CONTRATTO` la fa bloccare da sé, senza toccare il
trigger.

---

### Aggancio

Trigger `trg_preventivi_righe_a10_set_natura_vendita_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE OF articolo_id` su `vendite.preventivi_righe`, `FOR EACH ROW`.

---

### ⚠️ «Nessun override» vale all'inserimento, non in permanenza

L'aggancio è `UPDATE OF articolo_id`: il trigger scatta quando la riga nasce o quando
**cambia articolo** — ed è giusto, perché in quel caso la natura va rieredidata.

Ma un `UPDATE` che tocca **solo** la natura non lo fa scattare:

```sql
UPDATE vendite.preventivi_righe SET natura_vendita_id = :altra WHERE id = :id;  -- passa
```

Su `vendite.preventivi_righe` **non** esiste un `trgfn_lock_columns` su quella colonna, e
l'unico presidio rimasto è `trg_preventivi_righe_a10_nature_vendita_require_attivo_ins_upd`,
che verifica soltanto che la natura scelta sia **attiva** — non che sia quella dell'articolo.

Conseguenza: la natura può essere staccata dall'articolo con un `UPDATE` diretto, e da quel
momento anche il blocco della ricorrenza è aggirato. Se il congelamento dev'essere davvero
tale, oggi **non è presidiato**.

---

### ⚠️ Articolo non classificato: la riga passa con natura `NULL`

Se l'articolo non ha ancora una natura (`natura_vendita_id IS NULL`, situazione transitoria
pre-backfill), la riga viene salvata con natura nulla e **non è smistabile** finché
l'articolo non viene classificato. È una scelta esplicita: non si blocca l'inserimento per
una classificazione mancante a monte.

⚠️ Lo stesso esito si produce però anche in un caso **diverso**: se il `SELECT ... INTO`
non trova l'articolo, le variabili di destinazione vengono **azzerate** — è il
comportamento di `SELECT INTO` senza righe — quindi `NEW.natura_vendita_id` diventa `NULL`,
`v_destinazione` resta `NULL` e il guard sulla ricorrenza non scatta. Fail-open.

In pratica la FK su `articolo_id` rende il caso irraggiungibile, ma i due esiti restano
indistinguibili guardando la riga risultante: natura nulla può voler dire *«articolo non
classificato»* oppure *«articolo non trovato»*.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` | Articolo con natura a `destinazione_tipo = 'CONTRATTO'` inserito su un preventivo |

Sollevato via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato; il context riporta
`articolo_id`, `articolo_codice`, `natura_vendita_id` e `destinazione_tipo`.

Il nome del codice è già l'istruzione per l'operatore: **usa un'offerta commerciale**.

---

{% include-markdown "signature-core.md" %}
