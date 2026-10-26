{% include-markdown "it/dbzero/script/manual/fn_doc_riga_modificabile.md" %}
# ⚙️ Funzione `fn_doc_riga_modificabile`

```sql
CREATE FUNCTION fn_doc_riga_modificabile(p_tabella regclass, p_stato text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_riga_modificabile(p_tabella regclass, p_stato text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: con il documento in p_stato (codice_interno), una riga
    --   intera di p_tabella si aggiunge, si modifica e si toglie,
    --   oppure i lock «si tocca solo in bozza» la fermano? Dal
    --   montaggio (script.fn_doc_lock_montaggi), con la decisione
    --   del trigger (script.fn_doc_lock_colonna_bloccata) sulla
    --   riga intera (colonne NULL: INSERT e DELETE).
    -- ⚠️ p_stato nudo: e' il codice_interno di sei vocabolari
    --   di stato diversi (polimorfo).
    -- Nessun lock sulla tabella: true, come il database.
    SELECT NOT EXISTS (
             SELECT 1
               FROM script.fn_doc_lock_montaggi(p_tabella) AS m
              WHERE script.fn_doc_lock_colonna_bloccata(
                      m.regola, p_stato, NULL::text[]) IS NOT NULL);
$function$

COMMENT ON FUNCTION script.fn_doc_riga_modificabile(p_tabella regclass, p_stato text)
IS 'Check generica (2026-10-11, brief-db-testata-dopo-emissione §11, R-DB-3): con il documento in p_stato (codice_interno), una riga intera di p_tabella si aggiunge, si modifica e si toglie, o i lock «si tocca solo in bozza» la fermano? Legge il montaggio (script.fn_doc_lock_montaggi) e decide con la funzione del trigger (script.fn_doc_lock_colonna_bloccata, colonne NULL = la riga intera, come INSERT e DELETE): nessuna regola scritta qui, la capability specchia il lock. true se nessun lock ferma la riga; una tabella senza lock risponde true, come il database. Sorella di script.fn_doc_colonna_modificabile (la sola colonna). La usano le capability per i satelliti del documento: can_edit_indirizzi di ordine, DDT, preventivo, offerta e contratto, can_edit_utility dell''offerta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
