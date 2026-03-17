## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)
> [pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi` definisce i **template degli step di workflow** per ciascun tipo_prestazione. Ogni template descrive un flusso tipo: sequenza di esecuzione, obbligatorieta', direzione, handler automatico opzionale e parametri di configurazione.

---

### Ruolo nel processo

* Quando viene creata una pratica di un dato tipo, i flussi vengono istanziati dai template configurati.
* I template definiscono l'**ordine** (`sequenza`), l'**obbligatorieta'** e la **direzione** del flusso.
* I template con `handler_id NOT NULL` sono automatizzati; quelli con `handler_id NULL` sono manuali.
* I prerequisiti tra template sono definiti nella tabella `template_flussi_prerequisiti` (DAG).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `sequenza` | INTEGER DEFAULT 0. Ordine di esecuzione nel workflow. |
| `obbligatorio` | BOOLEAN DEFAULT false. Se true, il flusso deve essere completato per chiudere la pratica. |
| `direzione` | VARCHAR(10) CHECK (ENTRATA, USCITA, INTERNA) DEFAULT 'INTERNA'. Caratterizza il flusso rispetto all'esterno: ENTRATA = dall'esterno verso il gestionale, USCITA = dal gestionale verso l'esterno, INTERNA = operazione interna. |
| `handler_params` | JSONB DEFAULT '{}'. Parametri operativi passati all'handler Django in fase di esecuzione (es. `{"stampa_foglio": true, "invio_sms_conferma": true}`). Distinto da `meta` che contiene metadati generici. |

---

### Vincoli

* **UQ composito**: `(tipo_prestazione_id, codice)` — codice univoco per tipo_prestazione.
* **CHECK direzione**: solo valori ENTRATA, USCITA, INTERNA.
* **FK handler_id nullable**: NULL = step manuale, NOT NULL = step automatizzato.

---

### Convenzioni

* Trigger standard applicati automaticamente da `dbops.fn_run_automations()`.
* `storicizza = true` per tracciamento modifiche alla configurazione.

---

{% include-markdown "signature-core.md" %}
