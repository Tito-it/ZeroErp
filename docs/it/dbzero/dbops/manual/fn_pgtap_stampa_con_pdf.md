## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_stampa_con_pdf`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — il suo PDF principale
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_guard_file_principale](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_file_principale) — il controllo che la fixture fa giudicare
> * [dbops.fn_pgtap_codice_errore](/dbzero/dbops/funzioni/fn_pgtap_codice_errore) — l'altro helper che riceve un'istruzione come testo
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i vincoli differiti nei test

---

### 🎯 Scopo Principale

Fixture pgTAP: registra una stampa col suo PDF principale e ne rende l'`id`. Riceve l'inserimento della stampa
come testo, lo esegue, scrive il PDF (tipo `PDF_FINALE`) e fa giudicare subito il controllo del file principale.
Solo per i pgTAP.

---

### ⭐ Due istruzioni, come il servizio

Una stampa senza PDF principale non si registra, e nei pgTAP i vincoli differiti scattano a fine istruzione.
Stampa e file in un'istruzione sola non si possono scrivere da applicazione: la policy del file ricava l'azienda
dalla stampa, che in quella stessa istruzione non è ancora visibile, e nega.

La fixture fa come il servizio: prima la stampa, poi il file. Apre la finestra differita del solo controllo del file
principale e la richiude subito dopo il file, così il controllo giudica lì e non al rollback del test, che non
giudica niente. Gli altri vincoli restano come il test li ha messi.

Scrive con l'identità di chi chiama, sotto le sue policy.

---

### Test

* La usano i pgTAP che costruiscono stampe: `test-documenti-generati.sql`, `test-documenti-generati-file.sql`,
  `test-documenti-generati-eventi.sql`, `test-documenti-versione-contesto-v1.sql`,
  `test-documenti-template-standard-v1.sql`, `test-sorgente-documenti-generati-v1.sql`,
  `test-documenti-stampa-e-storia-v1.sql` (in `db/pgtap/documenti/`) e `db/pgtap/rls/test-rls-documenti-satelliti.sql`.

---

### Note di migrazione

* 2026-11-15 — nasce col controllo del file principale, al posto della stessa finestra differita ricopiata in ogni
  test.

---

{% include-markdown "signature-core.md" %}
