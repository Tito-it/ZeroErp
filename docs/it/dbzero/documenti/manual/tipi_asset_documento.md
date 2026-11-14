## 📘 Documentazione Concettuale – Tabella `documenti.tipi_asset_documento`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — ogni risorsa caricata dice di che tipo è
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §2.4, gli asset

---

### 🎯 Scopo Principale

Il vocabolario dei tipi di risorsa che un'azienda carica per i suoi modelli: logo, firma, immagine, PDF
di supporto, foglio di stile e «altro». Il tipo dice il ruolo della risorsa nel modello, non il file:
il file sta nella risorsa.

---

### Che cosa si può caricare lo decide il backend

Per ogni tipo il backend ha la lista dei formati di file ammessi, e confronta sul `codice_interno`. Il
vocabolario non porta i formati: `meta` è vuoto e non ha lettori.

* `codice_interno` è la chiave, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono le etichette.

---

### Spegnere un tipo

`attivo = false` impedisce che una risorsa nuova nasca con quel tipo. Un tipo non si spegne finché una
risorsa attiva lo usa. Le modifiche sono storicizzate in `storico.tipi_asset_documento`. La tabella è
nel lookup generico, per le tendine, e non nel pannello di configurazione.

---

### ⚠️ Che cosa oggi non copre

* **`ALTRO` si sceglie ma non si carica.** Il tipo è nel seed ed è attivo, ma il backend non gli
  associa nessun formato e rifiuta ogni caricamento.
* **I formati ammessi stanno solo nel backend.** Un tipo nuovo del seed non ha formati finché il
  backend non lo conosce.

---

### Test

* `db/pgtap/documenti/test-documenti-lookup.sql` — le righe del seed, l'unicità di `codice_interno`, il
  blocco della chiave.

---

### Note di migrazione

* 2026-04-29 — nasce con `LOGO`, `FIRMA`, `IMMAGINE`, `PDF`, `CSS`, `ALTRO`.

---

{% include-markdown "signature-core.md" %}
