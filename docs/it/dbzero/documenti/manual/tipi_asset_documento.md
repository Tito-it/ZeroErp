## 📘 Documentazione Concettuale – Tabella `documenti.tipi_asset_documento`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — ogni risorsa caricata dice di che tipo è
> * [documenti.tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati) — i formati che ogni tipo ammette
> * [config.formati_file](/dbzero/config/tabelle/formati_file) — il vocabolario dei formati di file
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — una risorsa nasce in un formato del suo tipo
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §2.4, gli asset

---

### 🎯 Scopo Principale

Il vocabolario dei tipi di risorsa che un'azienda carica per i suoi modelli: logo, firma, immagine, PDF
di supporto, foglio di stile. Il tipo dice il ruolo della risorsa nel modello, non il file: il file sta
nella risorsa.

---

### Che cosa si può caricare lo dice il tipo

Ogni tipo dichiara i formati di file che ammette, in
[tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati). Una risorsa
nasce solo in uno di quei formati (`E_DOCUMENTI_FORMATO_NON_AMMESSO`), e il backend legge la stessa
lista per proporla e per controllare i byte del file.

* `LOGO` e `IMMAGINE`: PNG, JPEG, SVG, WebP, GIF;
* `FIRMA`: PNG, JPEG, SVG, WebP;
* `PDF`: PDF;
* `CSS`: il foglio di stile.

---

### Un vocabolario si legge, non si configura

Un tipo è ciò che il codice sa usare: nasce o si ritira con un changeSet, insieme ai suoi formati.
Non ha `attivo`: un tipo c'è o non c'è. L'applicazione lo legge soltanto.

* `codice_interno` è la chiave, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono per chi legge il catalogo; a video l'etichetta viene da
  `etichetta_key` (`documenti.tipi_asset_documento.<codice_interno minuscolo>`);
* `ordine` dà l'ordine della tendina.

È la forma dei sette vocabolari dello schema.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma, la sola lettura, i formati
  di ogni tipo, il rifiuto di un formato che il tipo non ammette.
* `db/pgtap/documenti/test-documenti-lookup.sql` — le righe del seed, l'unicità di `codice_interno`, il
  blocco della chiave.

---

### Note di migrazione

* 2026-04-29 — nasce con `LOGO`, `FIRMA`, `IMMAGINE`, `PDF`, `CSS`, `ALTRO`.
* 2026-11-16 — prende la forma dei vocabolari della versione: entrano `etichetta_key` e `ordine`,
  escono `attivo`, `meta` e lo storico. I formati ammessi passano dal backend al database. `ALTRO`,
  che il backend non lasciava caricare, è ritirato.

---

{% include-markdown "signature-core.md" %}
