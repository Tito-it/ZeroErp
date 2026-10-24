# ⚙️ Funzione `fn_guard_commessa_sorgente_emittente`

```sql
CREATE FUNCTION fn_guard_commessa_sorgente_emittente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_guard_commessa_sorgente_emittente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_codice_commessa vendite.commesse.codice%TYPE;
    v_ef_commessa     vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
    v_codice_sorgente config.sorgenti.codice_interno%TYPE;
    v_ef_sorgente     anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Fail-fast sull'invariante «una commessa non aggrega due
    --   emittenti». La DECISIONE sta nel check: qui si compone
    --   soltanto la frase che una persona legge.
    -- =========================================================
    IF vendite.fn_check_commessa_sorgente_emittente_omogeneo(
           p_commessa_id, p_sorgente_tipo_id, p_sorgente_uid) THEN
        RETURN;
    END IF;

    SELECT c.codice, c.emittente_soggetto_ruolo_id
      INTO v_codice_commessa, v_ef_commessa
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    SELECT s.codice_interno INTO v_codice_sorgente
      FROM config.sorgenti s WHERE s.id = p_sorgente_tipo_id;

    BEGIN
        v_ef_sorgente := script.fn_get_sorgente_emittente_sr_id(
                             p_sorgente_tipo_id, p_sorgente_uid);
    EXCEPTION WHEN OTHERS THEN
        -- ⚠️ Il messaggio non deve MAI mangiarsi il verdetto: se
        --   la risoluzione fallisce qui, l'errore di dominio esce
        --   lo stesso con un «?» al posto dell'emittente.
        v_ef_sorgente := NULL;
    END;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        'fn_guard_commessa_sorgente_emittente',
        'E_COMMESSA_SORGENTE_EMITTENTE_MISTO',
        jsonb_build_object(
            'commessa_id',           p_commessa_id,
            'codice',                v_codice_commessa,
            'sorgente_tipo_id',      p_sorgente_tipo_id,
            'sorgente_codice',       v_codice_sorgente,
            'sorgente_uid',          p_sorgente_uid,
            'emittente_sr_commessa', v_ef_commessa,
            'emittente_sr_sorgente', v_ef_sorgente),
        NULL::uuid,
        COALESCE(v_codice_commessa, p_commessa_id::text),
        concat(COALESCE(v_codice_sorgente, p_sorgente_tipo_id::text), ' ', p_sorgente_uid),
        COALESCE(v_ef_commessa::text, '?'),
        COALESCE(v_ef_sorgente::text, '?'));
END;
$function$

COMMENT ON FUNCTION vendite.fn_guard_commessa_sorgente_emittente(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Guard fail-fast sull''invariante «una commessa non puo'' aggregare diversi emittenti insieme» (H4): la sorgente che si sta collegando deve stare sullo stesso emittente fiscale della commessa. Solleva E_COMMESSA_SORGENTE_EMITTENTE_MISTO nominando la commessa, il documento e i due emittenti. ⭐ La DECISIONE non e'' qui: sta in vendite.fn_check_commessa_sorgente_emittente_omogeneo, e questa funzione compone soltanto la frase — si condivide la funzione, non una copia della sua logica. rev 2026-08-26: l''emittente della commessa si legge dalla sua colonna (NOT NULL) e quello del documento da script.fn_get_sorgente_emittente_sr_id; nessuno dei due passa piu'' dal billing account. ⚠️ SECURITY DEFINER: per comporre il messaggio rilegge vendite.commesse, che ha la RLS. ⚠️ La risoluzione del messaggio e'' avvolta in un blocco EXCEPTION: se fallisce, l''errore di dominio esce lo stesso con un «?» al posto dell''emittente — il messaggio non deve mai mangiarsi il verdetto. ⛔ Nessuna GUC di override e nessuna eccezione per il pregresso. Piano: brief-db-emittente-commessa-invariante, L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
