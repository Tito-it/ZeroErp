{% include-markdown "it/dbzero/anagrafiche/manual/fn_soggetto_id_fiscale_bloccato.md" %}
# ⚙️ Funzione `fn_soggetto_id_fiscale_bloccato`

```sql
CREATE FUNCTION fn_soggetto_id_fiscale_bloccato(p_soggetto_id uuid, p_colonna text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_soggetto_id_fiscale_bloccato(p_soggetto_id uuid, p_colonna text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
  SELECT COALESCE(
           (SELECT anagrafiche.fn_id_fiscale_bloccato(
                     CASE p_colonna
                         WHEN 'codice_fiscale' THEN s.codice_fiscale
                         WHEN 'partita_iva'    THEN s.partita_iva
                         WHEN 'stato_id'       THEN s.stato_id::text
                     END)
              FROM anagrafiche.soggetti s
             WHERE s.id = p_soggetto_id),
           false);
$function$

COMMENT ON FUNCTION anagrafiche.fn_soggetto_id_fiscale_bloccato(p_soggetto_id uuid, p_colonna text)
IS 'La regola di anagrafiche.fn_id_fiscale_bloccato letta sulla riga del soggetto, per la colonna codice_fiscale, partita_iva o stato_id (stato_id dal 2026-11-24, D-T5-3 a di brief-db-revisione-anagrafiche §20). E'' la condizione delle righe di dbops.lock_columns_conditional su anagrafiche.soggetti, che dbops.fn_non_editable_fields valuta per il form: il form spegne esattamente cio'' che il guard rifiuta. Soggetto inesistente o colonna diversa: falso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
