# ⚙️ Funzione `fn_aggiungi_ubicazione`

```sql
CREATE FUNCTION fn_aggiungi_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
BEGIN
    -- Scopo: il gesto «nuova ubicazione» dell'operatore nel
    --   magazzino p_magazzino_id: livello TUTTO sull'oggetto, il
    --   magazzino nel perimetro (no-leak), poi il BB. Ritorna l'id.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'ubicazioni', 'TUTTO');

    -- No-leak: un magazzino fuori perimetro e' come uno che non
    -- esiste. Lo stesso predicato di fn_libera_blocco.
    IF NOT EXISTS (SELECT 1
                     FROM magazzino.magazzini mg
                    WHERE mg.id = p_magazzino_id
                      AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, mg.id)) THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_aggiungi_ubicazione', 'E_MAG_MAGAZZINO_NON_TROVATO',
            jsonb_build_object('magazzino_id', p_magazzino_id),
            NULL::uuid,
            COALESCE(p_magazzino_id::text, '(nessuno)'));
    END IF;

    RETURN magazzino.fn_crea_ubicazione(p_magazzino_id, p_codice, p_tipo_id, p_campi);
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_ubicazione(p_magazzino_id bigint, p_codice character varying, p_tipo_id bigint, p_campi jsonb)
IS 'VERBO: il gesto «nuova ubicazione» dell''operatore nel magazzino p_magazzino_id. Prima riga script.fn_guard_livello(utente, magazzino, ubicazioni, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Un magazzino che non esiste o fuori dal perimetro dell''operatore (script.fn_scope_ef_whitelist_via_magazzino) risponde E_MAG_MAGAZZINO_NON_TROVATO, senza dire quale dei due. Poi magazzino.fn_crea_ubicazione: colonne ammesse, padre, tipo e vincoli sono del BB e della tabella. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
