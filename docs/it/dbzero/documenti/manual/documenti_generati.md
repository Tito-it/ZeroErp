## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti)  
> • [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)  
> • [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file)  
> • [documenti.documenti_generati_eventi](documenti_generati_eventi.md) — timeline append-only del ciclo vita documento (anticipata da Fase B a v1)
> • [config.sorgenti](/dbzero/config/manual/sorgenti)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.documenti_generati` è il **registro storico delle generazioni
persistite** del motore documentale. Ogni riga rappresenta un documento
prodotto, con snapshot del contesto, hash di audit e collegamento alla
versione template usata.

---

### Ruolo nel processo

* garantisce tracciabilità del documento effettivamente generato;
* conserva il collegamento alla sorgente applicativa che ha richiesto il
  render;
* disaccoppia lo storico prodotto dalle successive evoluzioni del template.

---

### Campi chiave (semantica)

* **Identita` storica**: `id`, `uid`.
* **Origine**: `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga`,
  `progressivo_sorgente`.
* **Template usato**: `template_documento_id`, `template_versione_id`,
  `tipo_documento_output_id`.
* **Snapshot di audit**: `context_json`, `context_hash`, `template_hash`,
  `pdf_hash`.
* **Tracciamento operativo**: `generato_da_user_id`, `generato_at`, `stato`.

---

### Regole principali

* `uid` è un identificatore esterno stabile e univoco;
* il progressivo è univoco per combinazione
  `sorgente_tipo + sorgente_uid + sorgente_riga + progressivo_sorgente`, con
  `NULLS NOT DISTINCT` per trattare correttamente i casi senza riga sorgente;
* gli hash SHA-256 consentono verifica di integrità e audit del contenuto
  generato;
* lo storico non va interpretato come template "vivo": descrive un fatto già
  accaduto.

---

### Stato documento

* `GENERATO`: documento creato e registrato;
* `ARCHIVIATO`: documento consolidato nel suo ciclo di vita applicativo;
* `ANNULLATO`: storico mantenuto, ma record non più valido per uso operativo.

Nella Fase A lo stato ha semantica leggera; il cuore del valore tabellare è la
tracciabilità del render eseguito.

I cambi di stato (`GENERATO → ARCHIVIATO`/`ANNULLATO`) e gli eventi
applicativi (download, cleanup file orfani) sono tracciati nella timeline
append-only [`documenti_generati_eventi`](documenti_generati_eventi.md),
anticipata da Fase B a v1.

---

### Uso tipico nel processo

1. il backend seleziona template e versione;
2. genera il PDF e il relativo snapshot di contesto;
3. inserisce una riga storica in `documenti.documenti_generati`;
4. collega i file fisici prodotti in `documenti.documenti_generati_file`.

---

{% include-markdown "signature-core.md" %}
