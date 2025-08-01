## 📘 Documentazione Concettuale – Funzione `script.fn_get_snapshot_as_of`

> 👀 **Vedi anche**
> Approfondimento Funzioni:
>
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) *(solo logging, non aborta)*
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) *(logging + abort)*

La funzione **`script.fn_get_snapshot_as_of(p_schema TEXT, p_table TEXT, p_id TEXT, p_fk_col TEXT, p_as_of TIMESTAMP)`** restituisce uno **snapshot JSONB** di un record al momento specificato (`p_as_of`), applicando il modello di storicizzazione unificato di Zero ERP:

1. **Ricerca in storico**

   * Verifica l'esistenza della tabella di storico (`storico.<p_table>`) e ne recupera dinamicamente il tipo di chiave esterna.
   * Esegue una query dinamica per estrarre il `snapshot` più recente valido alla data/ora `p_as_of`.
   * Se la query storica fallisce (ad es. tabella non trovata, errori SQL), **logga l'errore e abortisce** chiamando `fn_log_and_raise_error`.
2. **Fallback su tabella operativa**

   * Se non esiste record storico per la data richiesta, serializza la riga corrente di `<p_schema>.<p_table>` in JSONB.
   * Anche in questo passaggio, eventuali errori vengono **loggati e abortiscono** tramite `fn_log_and_raise_error`.

### 🎯 Scopo Principale

* **Recupero storico/flessibile**: ottenere lo stato di un record in un preciso istante, combinando storicizzazione e serializzazione diretta.
* **Robustezza**: ogni errore di query viene tracciato con contesto completo, e l'esecuzione viene interrotta per evitare inconsistenze.

### ⚙️ Flusso Logico

```plpgsql
-- 0) Conversione in timestamptz
v_converted_as_of := p_as_of::timestamptz;

-- 1) Validazione tabella di storico e tipo FK
SELECT format_type(a.atttypid,a.atttypmod) INTO v_pk_type
  FROM pg_attribute a ...
IF v_pk_type IS NULL THEN
  PERFORM script.fn_log_and_raise_error(...);
END IF;

-- 2) Lettura da storico
BEGIN
  EXECUTE format('SELECT snapshot FROM %I.%I WHERE %I = $1::%s ...', ...)
    INTO v_snapshot USING p_id, v_converted_as_of;
EXCEPTION WHEN OTHERS THEN
  PERFORM script.fn_log_and_raise_error(...);
END;
IF v_snapshot IS NOT NULL THEN
  RETURN v_snapshot;
END IF;

-- 3) Fallback: serializzazione corrente
BEGIN
  EXECUTE format('SELECT to_jsonb(t)-%L FROM %I.%I WHERE %I = $1::%s', ...)
    INTO v_snapshot USING p_id;
EXCEPTION WHEN OTHERS THEN
  PERFORM script.fn_log_and_raise_error(...);
END;

RETURN v_snapshot;
```

### 🔒 Gestione degli Errori

* **`fn_log_and_raise_error`** viene invocata per ogni errore imprevisto: registra su `dbops.error_log` e poi **solleva un'eccezione**, interrompendo la chiamata.
* **Per scenari di solo tracking** (log di attività non critiche), utilizzare **`fn_log_error_only`**, che registra l'evento senza bloccare l'esecuzione.

### 💡 Vantaggi Operativi

* **Coerenza**: centralizza la logica di storicizzazione e fallback in un unico punto.
* **Tracciabilità avanzata**: ogni errore è corredato di contesto (`table`, `fk_column`, `id`, `as_of`, `SQLSTATE`).
* **Flessibilità**: scegliere tra `fn_log_error_only` e `fn_log_and_raise_error` in base al livello di criticità.

---

{% include-markdown "signature-core.md" %}
