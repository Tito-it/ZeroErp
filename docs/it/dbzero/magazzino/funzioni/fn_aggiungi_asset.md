# ⚙️ Funzione `fn_aggiungi_asset`

```sql
CREATE FUNCTION fn_aggiungi_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
    -- Scopo: il gesto «nuovo seriale» dell'operatore: livello
    --   TUTTO sull'oggetto, poi il BB. L'emittente e' quello della
    --   sessione; il perimetro lo dice il guard della tabella.
    --   Ritorna l'id.
    PERFORM script.fn_guard_livello(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        'magazzino', 'assets', 'TUTTO');

    RETURN magazzino.fn_crea_asset(p_articolo_id, p_seriale, p_stato_id,
                                   p_ownership_id, p_campi);
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_asset(p_articolo_id uuid, p_seriale character varying, p_stato_id bigint, p_ownership_id bigint, p_campi jsonb)
IS 'VERBO: il gesto «nuovo seriale» dell''operatore. Prima riga script.fn_guard_livello(utente, magazzino, assets, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Poi magazzino.fn_crea_asset con l''emittente della sessione: colonne ammesse, perimetro (trgfn_guard_emittente_scope), padri attivi e unicita'' del seriale sono del BB e della tabella. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
