# ⚙️ Funzione `fn_libera_blocco`

```sql
CREATE FUNCTION fn_libera_blocco(p_blocco_id bigint, p_nota text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_libera_blocco(p_blocco_id bigint, p_nota text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: liberare un blocco manuale con un atto — chi, quando, perche'
--   (M-3: «si libera esplicitamente, non si consuma da se'»).
DECLARE
    v_utente config.user_override_azioni.auth_user_id%TYPE;
    v_stato  magazzino.movimenti_attesi.stato%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_azione(v_utente, 'blocca_merce');

    IF p_blocco_id IS NULL OR p_blocco_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_libera_blocco',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'blocco obbligatorio e maggiore di zero',
                               'p_blocco_id', p_blocco_id),
            NULL::uuid, 'magazzino.fn_libera_blocco', 'p_blocco_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Il blocco, FOR UPDATE, nel perimetro; solo i blocchi manuali (senza sorgente).
    SELECT a.stato INTO v_stato
      FROM magazzino.movimenti_attesi a
     WHERE a.id = p_blocco_id
       AND a.sorgente_tipo_id IS NULL
       AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, a.magazzino_id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_libera_blocco',
            'E_MAG_BLOCCO_NON_TROVATO',
            jsonb_build_object('blocco_id', p_blocco_id),
            NULL::uuid, p_blocco_id::text);
    END IF;
    IF v_stato <> 'APERTA' THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_libera_blocco',
            'E_MAG_BLOCCO_GIA_CHIUSO',
            jsonb_build_object('blocco_id', p_blocco_id, 'stato', v_stato),
            NULL::uuid, p_blocco_id::text);
    END IF;

    UPDATE magazzino.movimenti_attesi a
       SET stato          = 'CHIUSA',
           data_chiusura  = now(),
           meta           = a.meta || jsonb_build_object(
                                'liberato_da',      v_utente,
                                'liberato_il',      now(),
                                'nota_liberazione', NULLIF(btrim(p_nota), ''))
     WHERE a.id = p_blocco_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_libera_blocco(p_blocco_id bigint, p_nota text)
IS 'VERBO: libera un blocco manuale (M-3: si libera con un atto, non si consuma da se''). Prima riga script.fn_guard_azione(utente, ''blocca_merce''). SECURITY DEFINER, blocco nel perimetro del suo magazzino e SENZA sorgente (i blocchi manuali): altrimenti E_MAG_BLOCCO_NON_TROVATO; gia'' CHIUSA -> E_MAG_BLOCCO_GIA_CHIUSO. Porta lo stato a CHIUSA con data_chiusura e scrive in meta liberato_da, liberato_il, nota_liberazione. Non cancella mai. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
