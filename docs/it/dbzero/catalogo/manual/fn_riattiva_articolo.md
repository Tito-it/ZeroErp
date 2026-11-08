## 📘 Documentazione Concettuale – Funzione `catalogo.fn_riattiva_articolo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo che si riaccende
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — un figlio che resta spento
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il trigger che impedisce di spegnere un articolo coi figli attivi
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il trigger che pretende i vocabolari dell'articolo attivi
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore

---

### 🎯 Scopo Principale

Riaccende un articolo spento (`attivo = true`). Tocca solo l'articolo: i figli spenti con lui,
come le unità operative o i legami di distinta, restano spenti.

È la controparte della disattivazione, che invece non ha un verbo: è un UPDATE diretto, e la
proteggono i trigger generati sull'articolo.

---

### ⭐ Prima il padre, poi i figli

La riattivazione non si propaga ai figli. L'articolo era stato spento per una decisione di
dominio, e riaccenderlo non vuol dire che ogni unità operativa, legame di distinta o regola di
fatturazione debba tornare com'era. Chi riattiva un articolo decide figlio per figlio, con
azioni separate. È lo stesso principio delle altre chiusure (versioni di listino, promo,
contratti): ogni passaggio è esplicito.

---

### Che cosa fa

* **Id vuoto o articolo inesistente**: errore `E_ARTICOLO_NOT_FOUND`.
* **Articolo spento**: lo riaccende.
* **Articolo già attivo**: non fa niente, senza errore. L'UPDATE filtra le righe spente, quindi
  su un articolo già attivo non scatta nessun trigger d'audit e `data_update` non cambia.

Audit, `tx_id` e il controllo dei vocabolari li fanno i trigger dell'articolo: la funzione non
li ripete.

---

### Il vocabolario spento ferma la riattivazione al COMMIT

L'articolo pretende attivi i vocabolari che punta: unità, IVA, natura, tipologia, gruppo, voce
di spesa, tipologia di listino, causale, modo di approvvigionamento. Il controllo è un trigger
differito: se uno di loro è spento, la funzione termina senza errore, e la transazione fallisce
al COMMIT con `E_ATTIVO_PADRE_NON_ATTIVO`.

⚠️ Il commento nel corpo della funzione parla di un codice `E_PARENT_*`, che non esiste: il
codice vero è `E_ATTIVO_PADRE_NON_ATTIVO`.

---

### La disattivazione

Spegnere un articolo è un UPDATE diretto di `attivo` a falso. I trigger generati
`block_deact` lo rifiutano finché una tabella figlia ha righe attive che lo puntano, e il
messaggio nomina la tabella figlia. Chi vuole spegnere l'articolo spegne prima i figli.

---

### Codici errore

* `E_ARTICOLO_NOT_FOUND` — l'id è vuoto, o l'articolo non esiste.
* `E_ATTIVO_PADRE_NON_ATTIVO` — non dalla funzione, ma al COMMIT: l'articolo riacceso punta a
  un vocabolario spento.

---

### Test

* `db/pgtap/catalogo/test-fn-riattiva-articolo-v1.sql` — la disattivazione con un figlio attivo è
  rifiutata e il messaggio nomina il figlio; la riattivazione accende l'articolo e lascia spenti
  i figli; un id inesistente dà `E_ARTICOLO_NOT_FOUND`; su un articolo già attivo non succede
  niente.

---

### Note di migrazione

* 2026-04-28 — nasce.

---

{% include-markdown "signature-core.md" %}
