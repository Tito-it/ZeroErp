## 📘 Documentazione Concettuale – Vista `dbops.vw_radici_di_prova_in_produzione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.credenziali_di_prova](/dbzero/dbops/tabelle/credenziali_di_prova) — le credenziali di prova che la vista elenca
> * [dbops.soggetti_di_prova](/dbzero/dbops/tabelle/soggetti_di_prova) — i soggetti di prova che la vista elenca
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento funzioni:
>
> * [script.fn_ambiente_dichiarato](/dbzero/script/funzioni/fn_ambiente_dichiarato) — l'ambiente, letto senza sollevare
> * [dbops.trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard) — il guard che impedisce alle etichette di nascere in produzione

---

### 🎯 Scopo Principale

**Presidio: dati di prova in un database di produzione.** Elenca le credenziali e i soggetti
di prova quando l'installazione è dichiarata di produzione. **Deve restare vuota.**

---

### ⭐ L'ultima rete

Di norma la vista non può riempirsi: in produzione un'etichetta non nasce, e l'ambiente
dichiarato non cambia. Resta vuota anche in CI, che è un'installazione di sviluppo. Serve per
ciò che i controlli non vedono: una copia di un database di sviluppo ripristinata su un
server di produzione con l'ambiente riscritto a mano, oppure un trigger disattivato.

Funziona perché si etichettano le **radici**: da una credenziale o da un soggetto di prova si
ritrova tutto ciò che vi è legato.

---

### ⚠️ Su un'installazione non dichiarata è vuota

La vista legge l'ambiente col lettore che non solleva, e senza ambiente dichiarato non
elenca niente. Quel caso lo segnala un presidio suo, la vista dell'ambiente non dichiarato.

La vista legge solo tabelle di `dbops`, quindi non dipende dalle tabelle di Django: in CI non
si rompe.

---

### Nel catalogo dei presidi

In [dbops.presidi](/dbzero/dbops/tabelle/presidi) è un presidio a zero, letto ogni giorno,
col conteggio libero dalla sicurezza per riga. Chi agisce è il sistemista: va capito come i
dati di prova sono arrivati e vanno disattivati, senza toccare i dati veri.

---

### Test

* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — in sviluppo è vuota; in produzione
  (costruita) vede le etichette nate prima; con l'ambiente non dichiarato (costruito) è vuota.

---

### Note di migrazione

* 2026-10-18 — nasce con le etichette di prova (`brief-db-processi-accensione-per-ambiente`, R-4).

---

{% include-markdown "signature-core.md" %}
