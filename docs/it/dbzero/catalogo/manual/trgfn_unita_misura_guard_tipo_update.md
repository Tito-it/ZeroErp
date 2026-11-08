## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_unita_misura_guard_tipo_update`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — la tabella su cui è montata, al cambio di famiglia
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni che la funzione conta
> * [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi) — le famiglie
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_conversioni_guard_tipo](/dbzero/catalogo/funzioni/trgfn_uom_conversioni_guard_tipo) — l'altra metà della regola, sul lato delle conversioni
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

Impedisce di cambiare la famiglia (`tipo_uom_id`) a un'unità di misura che compare in almeno
una conversione globale. Così una conversione nata fra due unità della stessa famiglia non
diventa, dopo, una conversione fra famiglie diverse.

---

### Le due metà della regola

La regola «una conversione globale collega solo unità della stessa famiglia» ha due porte.
`trgfn_uom_conversioni_guard_tipo` controlla la conversione quando la si scrive; questa
funzione controlla l'unità quando le si cambia la famiglia. Presa da sola, ognuna copre metà
della regola.

La funzione conta le conversioni in cui l'unità compare da una parte o dall'altra, attive o
no, in qualunque periodo: basta una riga. Per cambiare famiglia a un'unità usata si tolgono
prima le sue conversioni; non c'è un percorso che le converta.

---

### ⚠️ Il controllo «la famiglia è cambiata» sta nel trigger, non nella funzione

La funzione non confronta la famiglia vecchia con la nuova: se le conversioni ci sono,
rifiuta. A lasciar passare un aggiornamento che riscrive la stessa famiglia è la condizione
`WHEN` del trigger, che la chiama solo quando il valore cambia davvero. Chi monta la
funzione su un altro trigger deve copiare anche quella condizione, altrimenti ogni
aggiornamento della colonna su un'unità usata viene rifiutato.

---

### ⚠️ Che cosa oggi non copre

* **L'errore esce come errore tecnico.** Il codice è `E_GENERICO`, con una frase libera come
  messaggio: all'operatore arriva come errore tecnico, e il backend non lo distingue da
  qualunque altro errore generico. In `error_log` la causa si riconosce solo dal contesto
  (l'unità, la famiglia vecchia e la nuova, il numero di conversioni).
* **In `error_log` c'è il nome del trigger, non quello della funzione.** Chi cerca le righe
  di questo errore dal nome della funzione non le trova: vanno cercate con il nome del
  trigger, `trg_unita_misura_a10_guard_tipo_uom_upd`.
* **Non è al riparo dalla concorrenza.** Se mentre questa funzione conta zero conversioni
  un'altra transazione ne sta scrivendo una sull'unità, nessuna delle due aspetta l'altra, e
  può nascere una conversione fra famiglie diverse.

---

### Codici errore

* `E_GENERICO` — cambio di `tipo_uom_id` su un'unità che compare in almeno una conversione
  globale. Area `catalogo`.

---

### Test

La funzione non ha un test.

---

### Note di migrazione

* 2026-04-28 — nasce con le famiglie delle unità, insieme al guard sulle conversioni.

---

{% include-markdown "signature-core.md" %}
