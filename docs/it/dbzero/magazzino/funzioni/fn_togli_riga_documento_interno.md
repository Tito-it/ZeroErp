{% include-markdown "it/dbzero/magazzino/manual/fn_togli_riga_documento_interno.md" %}
# ⚙️ Funzione `fn_togli_riga_documento_interno`

```sql
CREATE FUNCTION fn_togli_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_togli_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
    v_fam    record;
    v_c      integer;   -- un conteggio: niente da ancorare
BEGIN
    -- Scopo: il gesto «togli la riga» di un documento interno.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_livello(
        v_utente, 'magazzino',
        (SELECT f.tabella FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f),
        'TUTTO');

    SELECT b.* INTO v_fam
      FROM magazzino.fn_documento_interno_blocca(
               p_famiglia, p_documento_id, v_utente,
               'magazzino.fn_togli_riga_documento_interno') AS b;

    -- La testata in DRAFT la chiede il guard delle righe
    -- (E_MAG_DOCUMENTO_RIGHE_CONGELATE), per ogni scrittore.
    EXECUTE format('DELETE FROM magazzino.%I r WHERE r.id = $1 AND r.%I = $2',
                   v_fam.tabella_righe, v_fam.colonna_fk)
      USING p_riga_id, p_documento_id;
    GET DIAGNOSTICS v_c = ROW_COUNT;
    IF v_c = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', 'magazzino.fn_togli_riga_documento_interno',
            'E_MAG_DOCUMENTO_RIGA_NON_TROVATA',
            jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id,
                               'riga_id', p_riga_id),
            NULL::uuid,
            COALESCE(p_riga_id::text, '(nessuna)'));
    END IF;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_togli_riga_documento_interno(p_famiglia text, p_documento_id bigint, p_riga_id bigint)
IS 'VERBO: il gesto «togli la riga» di un documento interno di magazzino (p_famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO), individuata dentro il suo documento (p_documento_id, p_riga_id). Passi: script.fn_guard_livello(utente, magazzino, <tabella della testata>, TUTTO) (E_PERMESSO_NEGATO); la testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca: E_MAG_DOCUMENTO_NON_TROVATO); il DELETE della riga di quel documento (nessuna riga: E_MAG_DOCUMENTO_RIGA_NON_TROVATA), che il guard delle righe ammette solo con la testata in DRAFT (E_MAG_DOCUMENTO_RIGHE_CONGELATE). SECURITY DEFINER del proprietario, search_path bloccato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
