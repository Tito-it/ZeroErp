## 📘 Documentazione Concettuale – Tabella `documenti.tipi_asset_documento_formati`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.tipi_asset_documento](/dbzero/documenti/tabelle/tipi_asset_documento) — il tipo di risorsa
> * [config.formati_file](/dbzero/config/tabelle/formati_file) — il formato
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — la risorsa che nasce in un formato del suo tipo
> * [documenti.tipi_file_documento_formati](/dbzero/documenti/tabelle/tipi_file_documento_formati) — la stessa regola per i file della stampa
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — il controllo che la legge
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §2.4, gli asset

---

### 🎯 Scopo Principale

Quali formati di file ammette ogni tipo di risorsa dei modelli: una riga per coppia (tipo, formato).
Una risorsa nasce solo in un formato abbinato al suo tipo, e il backend legge da qui la lista da
proporre e da controllare sui byte del file.

---

### Chi la legge

* il controllo alla nascita della risorsa,
  [trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso);
* il servizio delle risorse, che controlla anche i byte del file caricato.

Un formato si abbina una volta sola a un tipo. Gli abbinamenti nascono o si ritirano con un changeSet;
l'applicazione li legge soltanto.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — i formati di `LOGO`, `IMMAGINE`,
  `FIRMA`; ogni tipo ne ha almeno uno; la sola lettura.

---

### Note di migrazione

* 2026-11-16 — nasce, con le liste che il backend teneva in codice.

---

{% include-markdown "signature-core.md" %}
