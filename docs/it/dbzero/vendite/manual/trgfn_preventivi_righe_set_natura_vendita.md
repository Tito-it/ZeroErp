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

(rev 2026-10-13 — `20261013-10`, brief-db-articoli-ammessi-per-documento A-4)

⚠️ **Dal 2026-10-13 fa una cosa sola, nonostante il nome**: **blocca la ricorrenza sul
preventivo**. Se la natura della riga ha `destinazione_tipo = 'CONTRATTO'`, la riga non può
stare su un preventivo.

La natura della riga non la scrive più: la scrive [`script.trgfn_righe_natura_vendita`](/dbzero/script/manual/trgfn_righe_natura_vendita), montato
`trg_preventivi_righe_a10_natura_vendita_ins_upd`, lo stesso blocco che la scrive sulle righe
d'ordine e di bolla. Viene **prima** di questo trigger nell'ordine dei nomi (`natura` < `set`),
quindi qui la natura è già quella giusta e il guard ne legge la destinazione. Il nome
«set_natura» resta finché il Lotto 3 del brief non ritira questo guard nella check delle righe
di preventivo.

Fino al 2026-10-13 faceva **due cose con una sola lettura** dell'articolo: ereditava la natura
(sovrascrivendo quella del chiamante) e bloccava la ricorrenza.

La regola di dominio vera è il blocco. Un articolo a ricorrenza — un canone — non si vende
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

### Il «nessun override» è vero — ma lo tiene il lock, non questo trigger

L'aggancio è `UPDATE OF articolo_id`: il trigger scatta quando la riga nasce o quando
**cambia articolo**, ed è giusto, perché in quel caso la natura va rieredita. Ma un `UPDATE`
che tocca **solo** `natura_vendita_id` non lo fa scattare:

```sql
UPDATE vendite.preventivi_righe SET natura_vendita_id = :altra WHERE id = :id;
```

A rifiutarlo è `trg_preventivi_righe_a10_lock_columns_upd`
(`script.trgfn_lock_columns('natura_vendita_id', 'E_PREV_RIGA_NATURA_IMMUTABILE')`), generato
dall'automazione `LOCK_COLUMNS`. La dichiarazione «NO override operatore» scritta nel corpo di
questa funzione è quindi vera, ma **non è questa funzione a garantirla**.

⚠️ **Fino al 2026-08-21 non la garantiva nessuno.** L'unico presidio sulla colonna era
`trg_preventivi_righe_a10_nature_vendita_require_attivo_ins_upd`, che verifica soltanto che la
natura scelta sia *attiva* — non che sia quella dell'articolo. La natura poteva quindi essere
staccata dall'articolo con un `UPDATE` diretto, e con essa si aggirava anche il blocco della
ricorrenza: una riga a canone restava su un preventivo invece di andare in offerta.

---

### ⭐ Il lock funziona grazie all'ordine alfabetico, ed è una dipendenza fragile

⚠️ Dal 2026-10-13 i trigger in fila sono tre: `…_a10_lock_columns_upd` (il lock),
`…_a10_natura_vendita_ins_upd` (la scrittura della natura), `…_a10_set_natura_vendita_ins_upd`
(questo guard). Il ragionamento sotto vale identico fra il lock e la scrittura, che è il punto
in cui la natura viene riallineata.

`trg_preventivi_righe_a10_lock_columns_upd` viene **prima** di
`trg_preventivi_righe_a10_set_natura_vendita_ins_upd` in ordine alfabetico, e i `BEFORE ROW`
scattano in quell'ordine. È ciò che rende compatibili le due cose:

* su un `UPDATE` che cambia **solo l'articolo**, il lock legge una natura *non ancora
  riscritta* — `OLD` e `NEW` coincidono — e lascia passare; subito dopo l'ereditarietà la
  riallinea;
* su un `UPDATE` che cambia **la natura**, il lock vede la differenza e rifiuta.

⚠️ Se i due trigger venissero rinominati invertendone l'ordine, il lock bloccherebbe anche il
cambio articolo legittimo — e nessun messaggio direbbe perché. Il presidio di questa
dipendenza è il test 10 di `test-preventivi-righe-guard-natura-ricorrente-v1.sql`, scritto
apposta: è l'unica cosa che se ne accorgerebbe.

---

### ⚠️ Articolo non classificato: la riga passa con natura `NULL`

⚠️ **Sezione storica.** Dal 2026-10-13 la natura non la legge più questa funzione, e
`catalogo.articoli.natura_vendita_id` è `NOT NULL` (default la merce): un articolo senza
natura non esiste. Resta il caso dell'articolo non trovato, che la FK rende irraggiungibile.

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

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` | questa funzione | Articolo con natura a `destinazione_tipo = 'CONTRATTO'` inserito su un preventivo |
| `E_RIGA_NATURA_VENDITA_IMMUTABILE` (1296) | `script.trgfn_lock_columns` | `UPDATE` che cambia a mano `natura_vendita_id` (fino al 2026-10-13 `E_PREV_RIGA_NATURA_IMMUTABILE`, 938, ritirato: la regola vale anche per ordine e bolla) |

Sollevato via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato; il context riporta
`articolo_id`, `articolo_codice`, `natura_vendita_id` e `destinazione_tipo`.

Il nome del codice è già l'istruzione per l'operatore: **usa un'offerta commerciale**.

---

{% include-markdown "signature-core.md" %}
