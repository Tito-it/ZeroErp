# ⚙️ Funzione `fn_modifica_lotto`

```sql
CREATE FUNCTION fn_modifica_lotto(p_id bigint, p_dati jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_modifica_lotto(p_id bigint, p_dati jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_ammesse  text[];
    v_estranea text;
    v_riga     jsonb;
BEGIN
    -- Scopo: il gesto «modifica il lotto» dell'operatore: il delta
    --   p_dati sulle colonne modificabili. Un lotto e'
    --   dell'articolo: nessun perimetro. Ritorna la riga.
    PERFORM script.fn_guard_livello(
        NULLIF(current_setting('app.current_user_id', true), '')::integer,
        'magazzino', 'lotti', 'TUTTO');

    IF p_dati IS NULL OR jsonb_typeof(p_dati) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_lotto', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('id', p_id, 'tipo_dati', jsonb_typeof(p_dati)),
            NULL::uuid,
            'magazzino.fn_modifica_lotto',
            'i dati non sono un oggetto');
    END IF;

    v_ammesse  := magazzino.fn_lotti_colonne_ammesse('modifica');
    v_estranea := script.fn_prima_chiave_estranea(p_dati, v_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_lotto', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'id', p_id),
            NULL::uuid,
            v_estranea);
    END IF;

    PERFORM 1 FROM magazzino.lotti l WHERE l.id = p_id FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_modifica_lotto', 'E_MAG_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_id),
            NULL::uuid,
            COALESCE(p_id::text, '(nessuno)'));
    END IF;

    v_riga := script.fn_scrivi_riga_da_jsonb(
                  'magazzino.lotti'::regclass, p_dati, jsonb_build_object('id', p_id));

    RETURN (SELECT jsonb_object_agg(e.key, e.value)
              FROM jsonb_each(v_riga) AS e
             WHERE e.key = 'id' OR e.key = ANY (v_ammesse));
END;
$function$

COMMENT ON FUNCTION magazzino.fn_modifica_lotto(p_id bigint, p_dati jsonb)
IS 'VERBO: il gesto «modifica il lotto» dell''operatore. p_dati e'' il delta: si scrivono solo le chiavi mandate, una chiave a null scrive NULL, un delta vuoto non scrive niente. Passi: script.fn_guard_livello(utente, magazzino, lotti, TUTTO) (E_PERMESSO_NEGATO); p_dati oggetto (E_SCRIPT_CHIAMATA_NON_VALIDA) con le sole chiavi della lista modifica di magazzino.fn_lotti_colonne_ammesse (E_CAMPO_NON_AMMESSO col nome del campo); il lotto c''e'', letto FOR UPDATE, altrimenti E_MAG_LOTTO_NON_TROVATO; la scrittura con script.fn_scrivi_riga_da_jsonb, coi trigger della tabella. Un lotto e'' dell''articolo, senza perimetro d''emittente. Nessun DELETE: si disattiva con attivo. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna la riga: id e colonne modificabili.';
```

</div>

---
{% include-markdown "signature-core.md" %}
