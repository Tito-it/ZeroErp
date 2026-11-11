## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_uom_guard_storia`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — la mappatura, una delle due tabelle
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — la conversione generale, l'altra
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_conversione_capability](/dbzero/catalogo/funzioni/fn_uom_conversione_capability) — il giudizio che il guard legge, lo stesso delle viste
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — blocca le colonne della conversione
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — il guard dei listini, a fine transazione
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — la stessa regola, sulla distinta

---

### 🎯 Scopo Principale

Fa sì che una conversione già scritta, la mappatura di un articolo o una conversione generale, non
riscriva i giorni passati. Il fattore di un giorno passato resta quello che era.

---

### Le regole

1. **Spegnere, riaccendere, cancellare** solo una riga senza giorni passati, cioè che comincia oggi
   o dopo: è la riga inserita per errore (`E_UOM_STORIA_IN_VIGORE`).
2. **La fine**: una già passata non si cambia più (`E_UOM_STORIA_CHIUSA`); una nuova non viene
   prima di ieri (`E_UOM_STORIA_CHIUSURA_RETROATTIVA`). Chiudere a ieri lascia la storia com'era e
   permette alla riga nuova di valere da oggi.

Il giudizio lo dà [catalogo.fn_uom_conversione_capability](/dbzero/catalogo/funzioni/fn_uom_conversione_capability),
sulle date di prima. Le viste di dettaglio pubblicano la stessa risposta, quindi l'interfaccia non
offre un'azione che il guard rifiuta.

**Le colonne della conversione** (le unità, l'articolo, il fattore, l'inizio) non si cambiano mai,
ma non le giudica questo guard: le blocca [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns),
dal registro dei lock, col codice `E_UOM_STORIA_IMMUTABILE`. Così il form le trova fra i campi non
modificabili. Le altre colonne della mappatura (passo, decimali, flag d'uso, GTIN) si cambiano.

---

### Come è fatta

Una funzione sola, montata sulle due tabelle, prima di un UPDATE di `attivo` o `valido_al` e prima
di un DELETE; non riceve argomenti. La riga dell'unità base della mappatura non passa di qui: è già
ferma. La cancellazione di un articolo o di un'unità porta via le sue conversioni senza giudizio.

---

### Test

* `db/pgtap/catalogo/test-uom-storia-v1.sql` — le regole sulle due tabelle, il lock delle colonne col suo campo, «chiudi e inserisci», la cancellazione dell'articolo.
* `db/pgtap/catalogo/test-uom-conversione-capability-v1.sql` — il guard e la capability rispondono allo stesso modo, riga per riga.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).
* 2026-11-11 — le colonne della conversione passano al lock di colonna; le regole che restano le giudica `fn_uom_conversione_capability` (brief-db-revisione-catalogo, §15.11).

---

{% include-markdown "signature-core.md" %}
