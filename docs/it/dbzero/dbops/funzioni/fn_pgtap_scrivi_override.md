{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_scrivi_override.md" %}
# ⚙️ Funzione `fn_pgtap_scrivi_override`

```sql
CREATE FUNCTION fn_pgtap_scrivi_override(p_tabella regclass, p_auth_user_id integer, p_chiave jsonb, p_valori jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_scrivi_override(p_tabella regclass, p_auth_user_id integer, p_chiave jsonb, p_valori jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, cambiare (o togliere) UN override di un utente su una
--   delle tre tabelle, dal verbo vero e lasciando le altre voci.
-- Uso:
--   PERFORM dbops.fn_pgtap_scrivi_override('config.user_override_aree',
--       v_utente, jsonb_build_object('area_id', v_area),
--       jsonb_build_object('livello', 'LETTURA'));
--   PERFORM dbops.fn_pgtap_scrivi_override('config.user_override_azioni',
--       v_utente, jsonb_build_object('azione_id', v_azione), NULL);  -- la toglie
DECLARE
    v_verbo  text;   -- il nome del verbo della tabella: nessuna colonna
    v_righe  jsonb;  -- l'elenco dell'utente com'e': nessuna colonna
    v_prima  jsonb;  -- la voce di prima: nessuna colonna
    v_elenco jsonb;  -- l'elenco da riscrivere: nessuna colonna
    v_ctx    jsonb;  -- il contesto di prima, {utente, ruolo}: nessuna colonna
    c_sistema CONSTANT text[] := ARRAY[  -- le colonne che il verbo non ammette: nomi, nessuna colonna da ancorare
        'id', 'auth_user_id', 'meta', 'data_insert', 'user_insert', 'data_update',
        'user_update', 'storicizza', 'tx_id', 'validita', 'riservato'];
BEGIN
    v_verbo := CASE p_tabella
        WHEN 'config.user_override_aree'::regclass    THEN 'config.fn_imposta_override_aree'
        WHEN 'config.user_override_azioni'::regclass  THEN 'config.fn_imposta_override_azioni'
        WHEN 'config.user_override_oggetti'::regclass THEN 'config.fn_imposta_override_oggetti'
    END;
    IF v_verbo IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_scrivi_override: % non e'' una tabella degli override', p_tabella;
    END IF;
    IF p_auth_user_id IS NULL OR p_chiave IS NULL OR jsonb_typeof(p_chiave) <> 'object' THEN
        RAISE EXCEPTION 'fn_pgtap_scrivi_override: utente e chiave obbligatori';
    END IF;

    EXECUTE format(
        'SELECT COALESCE(jsonb_agg(to_jsonb(o) - $2 ORDER BY o.id), ''[]''::jsonb)
           FROM %s o WHERE o.auth_user_id = $1', p_tabella)
      INTO v_righe
      USING p_auth_user_id, c_sistema;

    SELECT e INTO v_prima
      FROM jsonb_array_elements(v_righe) AS e
     WHERE e @> p_chiave;

    SELECT COALESCE(jsonb_agg(e), '[]'::jsonb) INTO v_elenco
      FROM jsonb_array_elements(v_righe) AS e
     WHERE NOT e @> p_chiave;

    IF p_valori IS NOT NULL THEN
        v_elenco := v_elenco || jsonb_build_array(p_valori || p_chiave);
    END IF;

    v_ctx := dbops.fn_pgtap_entra_come_super_admin('override');
    BEGIN
        EXECUTE format('SELECT %s($1, $2)', v_verbo) USING p_auth_user_id, v_elenco;
    EXCEPTION WHEN OTHERS THEN
        PERFORM dbops.fn_pgtap_rimetti_contesto(v_ctx);
        RAISE;
    END;
    PERFORM dbops.fn_pgtap_rimetti_contesto(v_ctx);

    RETURN v_prima;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_scrivi_override(p_tabella regclass, p_auth_user_id integer, p_chiave jsonb, p_valori jsonb)
IS 'Fixture pgTAP: cambia o toglie UN override di un utente su una delle tre tabelle (config.user_override_aree, config.user_override_azioni, config.user_override_oggetti) lasciando le altre voci. Legge l''elenco dell''utente (le colonne che il verbo ammette), toglie la voce che contiene p_chiave e, se p_valori non è NULL, mette p_chiave || p_valori al suo posto; poi lo riscrive dal verbo vero della tabella (config.fn_imposta_override_aree, _azioni, _oggetti) come SUPER_ADMIN di fixture (dbops.fn_pgtap_entra_come_super_admin), e rimette il contesto anche in errore. Ritorna la voce di prima (NULL se non c''era), da ripassare come p_valori per rimetterla. L''elenco si riscrive intero: gli id delle righe cambiano, e meta si perde. Tabella fuori elenco, utente o chiave nulli -> RAISE; il resto lo rifiuta il verbo. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
