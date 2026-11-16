## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_guard_formato_ammesso`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — la risorsa dei modelli
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — il file della stampa
> * [documenti.tipi_asset_documento_formati](/dbzero/documenti/tabelle/tipi_asset_documento_formati) — i formati di ogni tipo di risorsa
> * [documenti.tipi_file_documento_formati](/dbzero/documenti/tabelle/tipi_file_documento_formati) — i formati di ogni tipo di file
> * [config.formati_file](/dbzero/config/tabelle/formati_file) — il vocabolario dei formati
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_template_asset_protect_file](/dbzero/documenti/funzioni/trgfn_template_asset_protect_file) — il formato della risorsa non cambia
> * [documenti.trgfn_documenti_generati_file_protect_file](/dbzero/documenti/funzioni/trgfn_documenti_generati_file_protect_file) — tipo e formato del file non cambiano
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function dei due file del modulo, la risorsa di un modello e il file di una stampa: il tipo
MIME dichiarato è un formato che il loro tipo ammette. La regola è la stessa per le due tabelle; cambia
solo l'abbinamento da cui si legge.

---

### Quando scatta

Alla nascita, e quando cambiano il tipo o il formato. Dopo la nascita il formato non cambia, su
entrambe le tabelle, e il tipo del file di una stampa nemmeno; il tipo di una risorsa sì, e allora il
controllo rilegge l'abbinamento del tipo nuovo.

Il trigger viene dopo il `protect_file` della tabella: su un cambio di formato parla prima
l'immutabilità del file.

Il tipo MIME si confronta minuscolo: il vocabolario lo tiene così, e un tipo MIME non distingue le
maiuscole. Un tipo che non esiste lo rifiuta la chiave esterna.

---

### Codici errore

* `E_DOCUMENTI_FORMATO_NON_AMMESSO` (`DATO_ERRATO`) — il formato non è ammesso dal tipo; la frase dice
  il nome del file, il formato e il tipo.
* `E_TRIGGER_ARGOMENTI_INVALIDI` — la funzione montata su una tabella che non ha un abbinamento di
  formati: è un errore di installazione.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — una firma in GIF rifiutata, con la
  frase; un logo in GIF registrato, anche col tipo MIME in maiuscolo; il cambio di tipo della risorsa
  rifiutato; sul cambio di formato parla `protect_file`; un allegato GIF rifiutato, uno PNG registrato.

---

### Note di migrazione

* 2026-11-16 — nasce. Prima che il formato fosse ammesso dal tipo lo controllava solo il backend.

---

{% include-markdown "signature-core.md" %}
