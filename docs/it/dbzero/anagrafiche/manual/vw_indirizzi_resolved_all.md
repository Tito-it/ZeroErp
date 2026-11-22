## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_all`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_base](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base) — la base di cui è la proiezione, dove sta la risoluzione
> * [anagrafiche.vw_indirizzi_resolved_ruolo](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo) — il solo strato dei ruoli
> * [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto) — il solo strato dei soggetti

---

### 🎯 Scopo Principale

`anagrafiche.vw_indirizzi_resolved_all` è `anagrafiche.vw_indirizzi_resolved_base` intera: gli indirizzi dei
ruoli e dei soggetti insieme, già risolti, con `scope` che dice da quale strato viene ogni riga.

---

### Una proiezione, non una seconda risoluzione

La vista espone tutte le righe e tutte le colonne della base, con gli stessi nomi, nello stesso ordine e con
gli stessi tipi, senza filtro: le sue righe sono quelle della proiezione dei ruoli più quelle della proiezione
dei soggetti. Non aggiunge join né regole: come si risolve una riga, che cosa dice ogni colonna e che cosa la
base oggi non copre stanno nella pagina della base, e valgono qui.

Serve a chi vuole tutti gli indirizzi di un soggetto senza sapere dove sono scritti. Come la base, non sceglie
fra i livelli: l'indirizzo da usare per un ruolo, con i suoi ripieghi, lo dice `script.fn_get_indirizzo`.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` — `scope` valorizzato su ogni riga, le righe che sono
  quelle dei due strati insieme.
* `db/pgtap/anagrafiche/test-vw-indirizzi-resolved-derivate-codice-interno-v1.sql` — le colonne della base, il
  codice interno sui due strati, il codice da mostrare non troncato.

---

{% include-markdown "signature-core.md" %}
