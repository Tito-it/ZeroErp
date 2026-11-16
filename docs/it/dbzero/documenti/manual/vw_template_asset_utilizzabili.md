## 📘 Documentazione Concettuale – Vista `documenti.vw_template_asset_utilizzabili`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — gli asset, con `attivo` e la validità
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — la regola gemella, sulle versioni dei modelli
>
> Approfondimento funzioni:
>
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno di oggi nel fuso dell'azienda
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — gli asset nella stampa

---

### 🎯 Scopo Principale

Dice quali asset (loghi, firme, immagini, PDF, fogli di stile) si possono usare oggi: una riga per
asset. È la sede unica della regola «utilizzabile oggi»: chi deve saperlo legge questa vista, invece
di ripeterne le condizioni.

---

### Che cosa vuol dire «utilizzabile oggi»

Un asset è utilizzabile se è acceso e la sua validità comprende la data operativa, il giorno di oggi
nel fuso dell'azienda. Un asset spento, o che vale da una data futura, o la cui validità è chiusa, non
lo è.

La ristampa fedele non passa di qui: usa l'asset di allora anche se oggi è scaduto o spento.

---

### Le colonne

L'id dell'asset e le tre chiavi con cui lo si cerca: l'azienda, il tipo, il codice interno. Il resto
si legge dalla tabella.

---

### Per chi è

* il render di una stampa nuova e dell'anteprima, che cerca l'asset citato dal modello;
* il filtro degli asset utilizzabili della lista.

La vista legge con i permessi di chi la interroga; la tabella degli asset non ha sicurezza di riga.

---

### ⚠️ Che cosa oggi non copre

* **Il backend ripete ancora la condizione** invece di leggere la vista, nel render e nella lista:
  finché non passa alla vista, la regola ha due copie.

---

### Test

* `db/pgtap/documenti/test-documenti-risoluzione-scarto-asset-v1.sql` — utilizzabile l'asset acceso e
  valido oggi, non quello spento né quello che vale da domani.

---

### Note di migrazione

* 2026-11-16 — nasce. Prima la regola era scritta solo nel backend.

---

{% include-markdown "signature-core.md" %}
