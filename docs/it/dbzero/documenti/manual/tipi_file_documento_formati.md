## 📘 Documentazione Concettuale – Tabella `documenti.tipi_file_documento_formati`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.tipi_file_documento](/dbzero/documenti/tabelle/tipi_file_documento) — il tipo di file della stampa
> * [config.formati_file](/dbzero/config/tabelle/formati_file) — il formato
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — il file che nasce in un formato del suo tipo
> * [documenti.tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati) — la stessa regola per le risorse dei modelli
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — il controllo che la legge
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §6, che cosa succede quando si genera un documento

---

### 🎯 Scopo Principale

Quali formati di file ammette ogni tipo di file di una stampa: una riga per coppia (tipo, formato). Il
PDF principale è un PDF; un allegato è un PDF, un JPEG o un PNG.

---

### Chi la legge

* il controllo alla nascita del file,
  [trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso);
* il servizio di stampa, che controlla anche i byte dell'allegato.

Un formato si abbina una volta sola a un tipo. Gli abbinamenti nascono o si ritirano con un changeSet;
l'applicazione li legge soltanto.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — i formati di `PDF_FINALE` e
  `ALLEGATO`; un allegato GIF rifiutato, uno PNG registrato.

---

### Note di migrazione

* 2026-11-16 — nasce, con le liste che il backend teneva in codice.

---

{% include-markdown "signature-core.md" %}
