# ⚙️ Funzione `fn_modifica_magazzino`

```sql
CREATE FUNCTION fn_modifica_magazzino(p_id bigint, p_dati jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_modifica_magazzino(p_id bigint, p_dati jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente   config.user_override_oggetti.auth_user_id%TYPE;
    v_ammesse  text[];
    v_estranea text;
    v_riga     jsonb;
BEGIN
    -- Scopo: il gesto «modifica il magazzino» dell'operatore: il
    --   delta p_dati sulle colonne modificabili. Ritorna la riga.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'magazzini', 'TUTTO');

    IF p_dati IS NULL OR jsonb_typeof(p_dati) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_magazzino', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('id', p_id, 'tipo_dati', jsonb_typeof(p_dati)),
            NULL::uuid,
            'magazzino.fn_modifica_magazzino',
            'i dati non sono un oggetto');
    END IF;

    v_ammesse  := magazzino.fn_magazzini_colonne_ammesse('modifica');
    v_estranea := script.fn_prima_chiave_estranea(p_dati, v_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_magazzino', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'id', p_id),
            NULL::uuid,
            v_estranea);
    END IF;

    -- No-leak: fuori perimetro e inesistente rispondono uguale.
    PERFORM 1
       FROM magazzino.magazzini mg
      WHERE mg.id = p_id
        AND script.fn_check_user_emittente_scope(v_utente, mg.emittente_fiscale_id)
        FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_magazzino', 'E_MAG_MAGAZZINO_NON_TROVATO',
            jsonb_build_object('magazzino_id', p_id),
            NULL::uuid,
            COALESCE(p_id::text, '(nessuno)'));
    END IF;

    v_riga := script.fn_scrivi_riga_da_jsonb(
                  'magazzino.magazzini'::regclass, p_dati, jsonb_build_object('id', p_id));

    RETURN (SELECT jsonb_object_agg(e.key, e.value)
              FROM jsonb_each(v_riga) AS e
             WHERE e.key = 'id' OR e.key = ANY (v_ammesse));
END;
$function$

COMMENT ON FUNCTION magazzino.fn_modifica_magazzino(p_id bigint, p_dati jsonb)
IS 'VERBO: il gesto «modifica il magazzino» dell''operatore. p_dati e'' il delta: si scrivono solo le chiavi mandate, una chiave a null scrive NULL, un delta vuoto non scrive niente. Passi: script.fn_guard_livello(utente, magazzino, magazzini, TUTTO) (E_PERMESSO_NEGATO); p_dati oggetto (E_SCRIPT_CHIAMATA_NON_VALIDA) con le sole chiavi della lista modifica di magazzino.fn_magazzini_colonne_ammesse (E_CAMPO_NON_AMMESSO col nome del campo); la riga c''e'' ed e'' nel perimetro dell''operatore (script.fn_check_user_emittente_scope), letta FOR UPDATE, altrimenti E_MAG_MAGAZZINO_NON_TROVATO senza dire quale dei due; la scrittura con script.fn_scrivi_riga_da_jsonb, coi trigger della tabella. Nessun DELETE: si disattiva con attivo. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna la riga: id e colonne modificabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
