## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_uom_guard_storia`

> **Ultimo aggiornamento**: 10 novembre 2026
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
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — il guard dei listini, a fine transazione
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — la stessa regola, sulla distinta

---

### 🎯 Scopo Principale

Fa sì che una conversione già scritta, la mappatura di un articolo o una conversione generale, non
riscriva i giorni passati. Il fattore di un giorno passato resta quello che era.

---

### Le regole

1. **Le colonne della conversione non si cambiano**: le unità, l'articolo, il fattore, l'inizio. Si
   chiude la riga e se ne inserisce una nuova (`E_UOM_STORIA_IMMUTABILE`).
2. **Spegnere, riaccendere, cancellare** solo una riga senza giorni passati, cioè che comincia oggi
   o dopo: è la riga inserita per errore (`E_UOM_STORIA_IN_VIGORE`).
3. **La fine**: una già passata non si cambia più (`E_UOM_STORIA_CHIUSA`); una nuova non viene
   prima di ieri (`E_UOM_STORIA_CHIUSURA_RETROATTIVA`). Chiudere a ieri lascia la storia com'era e
   permette alla riga nuova di valere da oggi.

Le altre colonne della mappatura (passo, decimali, flag d'uso, GTIN) si cambiano.

---

### Come è fatta

Una funzione sola, montata sulle due tabelle (BEFORE UPDATE OR DELETE); le colonne della
conversione arrivano dagli argomenti del trigger. La riga dell'unità base della mappatura non passa
di qui: è già ferma. La cancellazione di un articolo o di un'unità porta via le sue conversioni
senza giudizio.

---

### Test

* `db/pgtap/catalogo/test-uom-storia-v1.sql` — le tre regole sulle due tabelle, «chiudi e inserisci», la cancellazione dell'articolo.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
