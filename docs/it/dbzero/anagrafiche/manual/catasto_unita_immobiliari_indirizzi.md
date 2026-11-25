## 📘 Documentazione Concettuale – Tabella `anagrafiche.catasto_unita_immobiliari_indirizzi`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — l'unità catastale
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, da cui nasce la coppia
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo) — chi scrive le righe
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il civico della riga deve essere attivo
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — un civico con un'unità non si spegne
>
> Guide:
>
> * [Il catasto delle istanze](/guide/catasto-delle-istanze) — il flusso intero del catasto

---

### 🎯 Scopo Principale

`anagrafiche.catasto_unita_immobiliari_indirizzi` lega un'unità catastale a un civico. Tiene separato il concetto
catastale (foglio, particella, subalterno) da quello topografico (via, civico, scala, interno): la stessa unità
può stare su più civici, e lo stesso civico può avere più unità.

---

### Una coppia, una volta

Il vincolo unico `uq_catunitaindir` ammette la coppia (unità, civico) una sola volta. È anche il vincolo su cui
`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo` rende idempotente il suo inserimento: la coppia già presente
non si duplica e non dà errore.

---

### ⭐ La coppia nasce dall'istanza

Le righe le scrive il trigger delle istanze: quando un'istanza ha sia l'unità catastale sia il civico, la coppia
(unità dell'istanza, civico dell'istanza) entra qui. Succede alla nascita dell'istanza, a ogni cambio dell'unità o
del civico, e al subentro, quando il clone aggancia all'istanza nuova la copia dell'unità della precedente: il
clone è una riga nuova, quindi anche la coppia è nuova, col civico dell'istanza nuova. L'applicazione può
scrivere anche direttamente (`zeroerp_app` ha il DML), per i casi di un'unità su più civici.

---

### La ponte segue l'istanza

Quando un'istanza cambia civico o unità, la coppia che aveva portato esce, se nessun'altra istanza ha la stessa
coppia, e quella nuova entra. Le coppie scritte a mano con altri civici restano: la ponte è molti a molti. Il
civico lasciato, senza più coppie, si può spegnere. L'unità lasciata che nessuna istanza nomina più si cancella,
e le sue coppie se ne vanno con lei. La regola sta nella guida
[Il catasto delle istanze](/guide/catasto-delle-istanze).

---

### Il civico deve essere attivo, e chi ha un'unità non si spegne

Il legame segue la regola dell'automazione ATTIVO fra un figlio e il suo padre:

* una riga nuova, o una riga che cambia civico, chiede un civico attivo
  (`trg_catasto_unita_immobiliari_indirizzi_a10_indirizzi_de_4328b2`, controllato a fine transazione);
* un civico che ha righe qui non si spegne (`trg_indirizzi_dettaglio_a10_catasto_unita_immobiliari_in_25baf0`):
  la tabella non ha una colonna `attivo`, quindi conta ogni riga.

La riga se ne va con la sua unità o col suo civico, quando l'uno o l'altro si cancella.

---

### Codici errore

* `E_ATTIVO_PADRE_NON_ATTIVO` — la riga nomina un civico spento.
* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — si spegne un civico che ha righe qui.

---

### Test

* `db/pgtap/anagrafiche/test-simula-subentro.sql` — la coppia creata dal trigger per l'unità della prima istanza e
  per il clone del subentro, e il duplicato rifiutato da `uq_catunitaindir`.
* `db/pgtap/anagrafiche/test-catasto-unita-della-sua-istanza-v1.sql` (test 6-10) — il cambio di civico toglie la
  coppia di prima, il civico lasciato si spegne, il cambio di unità porta via le coppie dell'unità lasciata.

---

### Note di migrazione

* 2025-12-10 — nasce al posto della colonna `indirizzo_dettaglio_id` di `catasto_unita_immobiliari`.
* 2026-11-25 — la coppia lasciata da un'istanza che cambia civico o unità esce dalla ponte.

---

{% include-markdown "signature-core.md" %}
