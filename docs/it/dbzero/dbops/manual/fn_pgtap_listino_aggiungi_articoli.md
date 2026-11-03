## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_listino_aggiungi_articoli`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — le righe che la fixture scrive
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tipologia di listino che allinea
>
> Approfondimento funzioni:
>
> * [script.fn_check_articolo_riga](/dbzero/script/funzioni/fn_check_articolo_riga) — la regola per cui un'eccezione pretende l'articolo nel listino
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — perché va chiamata prima dell'uso
> * [vendite.trgfn_listini_righe_guard_periodicita_quota_fissa](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_periodicita_quota_fissa) — la periodicità che una quota fissa vorrebbe
> * [dbops.fn_pgtap_crea_listino](/dbzero/dbops/funzioni/fn_pgtap_crea_listino) — la fixture del listino su cui di solito si lavora
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP che **mette degli articoli in una versione di listino**: allinea la tipologia di
listino dell'articolo a quella del listino, se è diversa, poi scrive una riga attiva per
articolo con l'unità di misura base e il prezzo dato (100 se non lo si dà).

---

### ⭐ Perché serve

Una riga di **override** o di **esclusione** su un documento pretende che l'articolo stia nel
listino del documento: fuori dal listino la riga non comparirebbe nel form. Le fixture che
scrivono quelle righe passano da qui per avere l'articolo nel listino giusto. La riga di
listino, a sua volta, pretende che l'articolo abbia la tipologia del listino: per questo la
fixture la allinea prima.

---

### ⚠️ Va chiamata prima di usare l'articolo

La tipologia di listino è una colonna strutturale: su un articolo già usato non cambia più, e
il guard di struttura rifiuta l'allineamento. La fixture va chiamata quando l'articolo è appena
nato.

---

### Che cosa non fa

* scrive le righe anche su una versione **attiva**, non solo in bozza: l'inserimento di una riga
  non è fermato dallo stato della versione;
* non scrive la **periodicità**: la riga di un articolo a quota fissa a canone nasce senza, anche
  su una versione attiva;
* non scrive i componenti di un bundle né le periodicità di un kit;
* una versione che non esiste, o un listino senza tipologia, la fermano con un errore semplice,
  senza codice registrato.

---

### Test

Non ha un test suo: la presidiano i file che la usano, per esempio
`db/pgtap/vendite/test-righe-articolo-ammesso-v1.sql`,
`db/pgtap/catalogo/test-articoli-ammessi-picker-v1.sql` e
`db/pgtap/vendite/test-righe-adesione-v1.sql`.

---

### Note di migrazione

* 2026-10-13 — nasce quando override ed esclusioni cominciano a pretendere l'articolo nel listino
  del documento (`brief-db-articoli-ammessi-per-documento`, Lotto 3b).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
