{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzo_elemento_dettaglio.md" %}
# ⚙️ Funzione `fn_indirizzo_elemento_dettaglio`

```sql
CREATE FUNCTION fn_indirizzo_elemento_dettaglio(p_el jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzo_elemento_dettaglio(p_el jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'indirizzo normalizzato di un elemento gia' letto da
    --   fn_indirizzo_elemento:
    --     * indirizzo libero: NULL (la riga e' libera);
    --     * indirizzo_dettaglio_id: quello;
    --     * altrimenti la via (stradario_id, oppure
    --       toponomastica + descrizione + comune + CAP) e il
    --       civico, risolti da anagrafiche.fn_create_indirizzo,
    --       idempotente.
    --
    -- Regole:
    --   - non valida i campi di una via nuova: pre-check del
    --     backend, come per fn_create_indirizzo.
    -- =========================================================
    IF NULLIF(btrim(p_el ->> 'indirizzo_libero'), '') IS NOT NULL THEN
        RETURN NULL;
    END IF;

    IF p_el ->> 'indirizzo_dettaglio_id' IS NOT NULL THEN
        RETURN (p_el ->> 'indirizzo_dettaglio_id')::bigint;
    END IF;

    RETURN anagrafiche.fn_create_indirizzo(
        p_stradario_id      := (p_el ->> 'stradario_id')::integer,
        p_toponomastica_id  := (p_el ->> 'toponomastica_id')::integer,
        p_descrizione_via   := p_el ->> 'descrizione_via',
        p_comune_id         := (p_el ->> 'comune_id')::integer,
        p_codice_postale_id := (p_el ->> 'codice_postale_id')::integer,
        p_civico            := (p_el ->> 'civico')::integer,
        p_estensione_civico := NULLIF(btrim(p_el ->> 'estensione_civico'), ''),
        p_palazzina         := NULLIF(btrim(p_el ->> 'palazzina'), ''),
        p_scala             := NULLIF(btrim(p_el ->> 'scala'), ''),
        p_piano             := NULLIF(btrim(p_el ->> 'piano'), ''),
        p_interno           := NULLIF(btrim(p_el ->> 'interno'), ''));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_indirizzo_elemento_dettaglio(p_el jsonb)
IS 'BB (2026-10-18): l''indirizzo normalizzato di un elemento letto da anagrafiche.fn_indirizzo_elemento. Indirizzo libero (indirizzo_libero non vuoto): NULL. indirizzo_dettaglio_id: quello. Altrimenti la via (stradario_id, oppure toponomastica_id + descrizione_via + comune_id + codice_postale_id) e il civico, risolti da anagrafiche.fn_create_indirizzo (idempotente). Non valida i campi di una via nuova (pre-check del backend, come fn_create_indirizzo). Chiamanti: anagrafiche.fn_crea_indirizzi_ruolo e fn_crea_indirizzo_soggetto. D-4 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
