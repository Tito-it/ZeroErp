## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti, da cui viene ogni riga
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_base](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base) — la base di cui è la proiezione, dove sta la risoluzione
> * [anagrafiche.vw_indirizzi_resolved_ruolo](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo) — la proiezione gemella, degli indirizzi dei ruoli
>
> Approfondimento funzioni:
>
> * [script.fn_get_indirizzi_by_soggetto](/dbzero/script/funzioni/fn_get_indirizzi_by_soggetto) — gli indirizzi di un soggetto, letti da qui
> * [script.fn_get_indirizzo_by_soggetto](/dbzero/script/funzioni/fn_get_indirizzo_by_soggetto) — l'indirizzo di un tipo, l'ultimo livello del ripiego
> * [script.fn_snapshot_indirizzo_soggetto](/dbzero/script/funzioni/fn_snapshot_indirizzo_soggetto) — la fotografia dell'indirizzo del soggetto sui documenti

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_resolved_soggetto` è lo strato `SOGGETTO` di `anagrafiche.vw_indirizzi_resolved_base`:
gli indirizzi dei soggetti, già risolti.

---

### Una proiezione, non una seconda risoluzione

La vista prende le righe della base con `scope = 'SOGGETTO'` e ne espone tutte le colonne, con gli stessi nomi,
nello stesso ordine e con gli stessi tipi; ruolo e istanza sono sempre vuoti. Non aggiunge join né regole: come
si risolve una riga, che cosa dice ogni colonna e che cosa la base oggi non copre stanno nella pagina della
base, e valgono qui.

La leggono le funzioni che danno gli indirizzi di un soggetto, compreso l'ultimo livello del ripiego di
`script.fn_get_indirizzo`, e la fotografia dell'indirizzo del soggetto sui documenti.

---

### Test

* `db/pgtap/anagrafiche/test-vw-indirizzi-resolved-derivate-codice-interno-v1.sql` — le colonne della base, il
  codice interno del tipo di ogni riga.
* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` — la lista degli indirizzi del soggetto allineata alla base.

---

{% include-markdown "signature-core.md" %}
