{% include-markdown "it/dbzero/magazzino/manual/fn_modifica_magazzino.md" %}
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
    v_ammesse  text[];  -- nomi di colonna: nessuna colonna di cui siano il riflesso
    v_riga     jsonb;
BEGIN
    -- Scopo: il gesto «modifica il magazzino» dell'operatore: il
    --   delta p_dati sulle colonne modificabili. Ritorna la riga.
    v_utente := script.fn_utente_di_sessione('magazzino.fn_modifica_magazzino');
    PERFORM script.fn_guard_livello(v_utente, 'magazzino', 'magazzini', 'TUTTO');

    v_ammesse  := magazzino.fn_magazzini_colonne_ammesse('modifica');
    PERFORM script.fn_guard_campi_ammessi(
        p_dati, v_ammesse,
        'magazzino', 'magazzino.fn_modifica_magazzino',
        jsonb_build_object('id', p_id));

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
