## 📘 Documentazione Concettuale – Tabella `documenti.tipi_file_documento`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — ogni file di una stampa dice di che tipo è
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa a cui i file appartengono
> * [documenti.tipi_file_documento_formati](/dbzero/documenti/tabelle/tipi_file_documento_formati) — i formati che ogni tipo ammette
> * [config.formati_file](/dbzero/config/tabelle/formati_file) — il vocabolario dei formati di file
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — un file nasce in un formato del suo tipo
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

Il backend li cerca per `codice_interno`.

---

### I formati che ogni tipo ammette

Ogni tipo dichiara i suoi formati in
[tipi_file_documento_formati](/dbzero/documenti/tabelle/tipi_file_documento_formati), e un file nasce
solo in uno di quelli (`E_DOCUMENTI_FORMATO_NON_AMMESSO`): `PDF_FINALE` è un PDF; un `ALLEGATO` è un
PDF, un JPEG o un PNG. Il backend legge la stessa lista per controllare i byte.

---

### Un vocabolario si legge, non si configura

Un tipo di file nasce o si ritira con un changeSet, insieme ai suoi formati. Non ha `attivo`: c'è o non c'è. L'applicazione lo legge soltanto.

* `codice_interno` è la chiave su cui confronta la logica, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono per chi legge il catalogo; a video l'etichetta viene da
  `etichetta_key` (`documenti.tipi_file_documento.<codice_interno minuscolo>`);
* `ordine` dà l'ordine della tendina.

È la forma dei sette vocabolari dello schema.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma, la sola lettura, i formati
  di ogni tipo, il rifiuto di un allegato in un formato che il tipo non ammette.
* `db/pgtap/documenti/test-documenti-lookup.sql` — la riga `PDF_FINALE`, l'unicità di `codice_interno`,
  il blocco della chiave.
* `db/pgtap/documenti/test-documenti-generati-file.sql` — i file di una stampa, col loro tipo.

---

### Note di migrazione

* 2026-04-29 — nasce con `PDF_FINALE`.
* 2026-05-27 — `ALLEGATO`, per i file aggiunti al documento generato.
* 2026-11-16 — prende la forma dei vocabolari della versione: entrano `etichetta_key` e `ordine`,
  escono `attivo`, `meta` e lo storico. I formati ammessi passano dal backend al database.

---

{% include-markdown "signature-core.md" %}
