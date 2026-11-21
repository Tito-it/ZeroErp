## 📘 Documentazione Concettuale – Tabella `config.formati_file`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati) — i formati che ogni tipo di risorsa ammette
> * [documenti.tipi_file_documento_formati](/dbzero/documenti/tabelle/tipi_file_documento_formati) — i formati che ogni tipo di file della stampa ammette
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_guard_formato_ammesso](/dbzero/documenti/funzioni/trgfn_guard_formato_ammesso) — il controllo alla nascita del file
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §2.4, gli asset

---

### 🎯 Scopo Principale

Il vocabolario dei formati di file che il sistema riconosce: un tipo MIME con la sua estensione (PNG,
JPEG, SVG, WebP, GIF, PDF, foglio di stile CSS). I tipi che accettano un file abbinano qui i formati che
ammettono, invece di tenerne ognuno una lista sua.

---

### Un formato, un tipo MIME

* `mime_type` è unico e minuscolo, nella forma `tipo/sottotipo`: è il valore che il file dichiara e che
  i controlli dei tipi confrontano;
* `estensione` è minuscola e senza punto: quella che si usa quando il nome del file caricato non ne
  ha una.

---

### Un vocabolario si legge, non si configura

Un formato nasce o si ritira con un changeSet. Non ha `attivo`: c'è o non c'è. L'applicazione lo legge
soltanto.

* `codice_interno` è la chiave, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono per chi legge il catalogo; a video l'etichetta viene da
  `etichetta_key` (`config.formati_file.<codice_interno minuscolo>`);
* `ordine` dà l'ordine della tendina.

È la forma dei vocabolari dello schema `documenti`.

---

### ⚠️ Che cosa oggi non copre

* **Gli allegati delle email hanno ancora una lista loro**, nel backend: non sono abbinati a questo
  vocabolario.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma, la sola lettura, i formati
  abbinati ai tipi.

---

### Note di migrazione

* 2026-11-16 — nasce, con i formati che il backend ammetteva per le risorse dei modelli e per i file
  delle stampe.

---

{% include-markdown "signature-core.md" %}
