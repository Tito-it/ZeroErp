## 📘 Documentazione Concettuale – Tabella `documenti.tipi_file_documento`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — ogni file di una stampa dice di che tipo è
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa a cui i file appartengono
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §6, che cosa succede quando si genera un documento

---

### 🎯 Scopo Principale

Il vocabolario dei tipi di file conservati per una stampa: il PDF prodotto dal motore e gli allegati
che l'operatore aggiunge al documento generato. Appartiene alla conservazione della stampa, non al
modello.

---

### I due tipi e chi li usa

* `PDF_FINALE` — il file che il motore produce alla generazione;
* `ALLEGATO` — un file aggiunto dopo, accanto al PDF.

Il backend li cerca per `codice_interno` e si ferma se il tipo manca o è spento. Il `codice_interno` è
bloccato dopo l'inserimento; `codice` e `descrizione` sono le etichette; `meta` non ha lettori.

---

### Spegnere un tipo

`attivo = false` impedisce che un file nuovo nasca con quel tipo. Un tipo non si spegne finché un file
lo nomina. Le modifiche sono storicizzate in `storico.tipi_file_documento`. La tabella è nel lookup
generico e non nel pannello di configurazione.

---

### ⚠️ Che cosa oggi non copre

* **Un tipo già usato non si spegne più.** Il file di una stampa non ha un proprio `attivo`, quindi per
  il controllo ogni file conservato è un figlio vivo: basta un file perché il tipo resti acceso per
  sempre.

---

### Test

* `db/pgtap/documenti/test-documenti-lookup.sql` — la riga `PDF_FINALE`, l'unicità di `codice_interno`,
  il blocco della chiave.
* `db/pgtap/documenti/test-documenti-generati-file.sql` — i file di una stampa, col loro tipo.

---

### Note di migrazione

* 2026-04-29 — nasce con `PDF_FINALE`.
* 2026-05-27 — `ALLEGATO`, per i file aggiunti al documento generato.

---

{% include-markdown "signature-core.md" %}
