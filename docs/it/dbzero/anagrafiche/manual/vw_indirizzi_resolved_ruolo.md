## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, da cui viene ogni riga
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_base](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base) — la base di cui è la proiezione, dove sta la risoluzione
> * [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto) — la proiezione gemella, degli indirizzi dei soggetti
>
> Approfondimento funzioni:
>
> * [script.fn_snapshot_indirizzo](/dbzero/script/funzioni/fn_snapshot_indirizzo) — la fotografia dell'indirizzo sui documenti, che legge da qui

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_resolved_ruolo` è lo strato `RUOLO` di `anagrafiche.vw_indirizzi_resolved_base`: gli
indirizzi dei ruoli, generici e delle istanze, già risolti.

---

### Una proiezione, non una seconda risoluzione

La vista prende le righe della base con `scope = 'RUOLO'` e ne espone tutte le colonne, con gli stessi nomi,
nello stesso ordine e con gli stessi tipi. Non aggiunge join né regole: come si risolve una riga, che cosa
dice ogni colonna e che cosa la base oggi non copre stanno nella pagina della base, e valgono qui.

Come la base, mostra gli indirizzi scritti e non sceglie fra i livelli: un ruolo può avere qui sia l'indirizzo
generico sia quello di un'istanza dello stesso tipo, distinti da `istanza_utility_id`.

La legge `script.fn_snapshot_indirizzo`, che fotografa l'indirizzo sul documento.

---

### Test

* `db/pgtap/anagrafiche/test-vw-indirizzi-resolved-derivate-codice-interno-v1.sql` — le colonne della base, il
  codice interno del tipo di ogni riga.
* `db/pgtap/vendite/test-indirizzi-documenti-simmetria-v1.sql` — la fotografia di un indirizzo del ruolo
  (`script.fn_snapshot_indirizzo`): la sua forma e il ruolo d'origine.

---

{% include-markdown "signature-core.md" %}
