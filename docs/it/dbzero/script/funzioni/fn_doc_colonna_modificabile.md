{% include-markdown "it/dbzero/script/manual/fn_doc_colonna_modificabile.md" %}
# ⚙️ Funzione `fn_doc_colonna_modificabile`

```sql
CREATE FUNCTION fn_doc_colonna_modificabile(p_tabella regclass, p_colonna name, p_stato text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_colonna_modificabile(p_tabella regclass, p_colonna name, p_stato text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: con il documento in p_stato (codice_interno), un
    --   UPDATE che cambia SOLO p_colonna passa i lock «si tocca
    --   solo in bozza» di p_tabella? Dal montaggio
    --   (script.fn_doc_lock_montaggi), con la decisione del
    --   trigger (script.fn_doc_lock_colonna_bloccata).
    -- ⚠️ p_stato nudo: e' il codice_interno di sei vocabolari
    --   di stato diversi (polimorfo).
    -- Nessun lock sulla tabella: true, come il database.
    SELECT NOT EXISTS (
             SELECT 1
               FROM script.fn_doc_lock_montaggi(p_tabella) AS m
              WHERE script.fn_doc_lock_colonna_bloccata(
                      m.regola, p_stato, ARRAY[p_colonna::text]) IS NOT NULL);
$function$

COMMENT ON FUNCTION script.fn_doc_colonna_modificabile(p_tabella regclass, p_colonna name, p_stato text)
IS 'Check generica (2026-10-10, brief-db-testata-dopo-emissione fase 1, R-1): con il documento in p_stato (codice_interno; per un nipote a livello RIGA lo stato della testata), un UPDATE che cambia SOLO p_colonna passa i lock «si tocca solo in bozza» di p_tabella? Legge il montaggio (script.fn_doc_lock_montaggi) e decide con la funzione del trigger (script.fn_doc_lock_colonna_bloccata): nessuna regola scritta qui, la capability specchia il lock. true se nessun lock ferma la colonna; una tabella senza lock risponde true, come il database. La usa script.fn_check_ordine_data_consegna_confermata (la promessa di consegna dopo la conferma); servira'' ai prelievi della bolla e alla testata della fase 2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
