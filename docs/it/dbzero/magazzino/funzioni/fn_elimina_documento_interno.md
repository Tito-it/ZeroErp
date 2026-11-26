{% include-markdown "it/dbzero/magazzino/manual/fn_elimina_documento_interno.md" %}
# ⚙️ Funzione `fn_elimina_documento_interno`

```sql
CREATE FUNCTION fn_elimina_documento_interno(p_famiglia text, p_documento_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_elimina_documento_interno(p_famiglia text, p_documento_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
    v_fam    record;
BEGIN
    -- Scopo: il gesto «elimina il documento» (la bozza). Le
    --   righe vanno con la testata (ON DELETE CASCADE).
    v_utente := script.fn_utente_di_sessione('magazzino.fn_elimina_documento_interno');
    PERFORM script.fn_guard_livello(
        v_utente, 'magazzino',
        (SELECT f.tabella FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f),
        'TUTTO');

    SELECT b.* INTO v_fam
      FROM magazzino.fn_documento_interno_blocca(
               p_famiglia, p_documento_id, v_utente,
               'magazzino.fn_elimina_documento_interno') AS b;

    -- Solo in DRAFT: lo dice trgfn_documento_interno_guard_transizione
    -- (E_MAG_DOCUMENTO_NON_ELIMINABILE), per ogni scrittore.
    EXECUTE format('DELETE FROM magazzino.%I WHERE id = $1', v_fam.tabella)
      USING p_documento_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_elimina_documento_interno(p_famiglia text, p_documento_id bigint)
IS 'VERBO: il gesto «elimina il documento» di un documento interno di magazzino (p_famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO). Passi: script.fn_guard_livello(utente, magazzino, <tabella della testata>, TUTTO) (E_PERMESSO_NEGATO); la testata nel perimetro, presa FOR UPDATE (magazzino.fn_documento_interno_blocca: E_MAG_DOCUMENTO_NON_TROVATO); il DELETE, che il guard della tabella ammette solo in DRAFT (E_MAG_DOCUMENTO_NON_ELIMINABILE). Le righe vanno con la testata (ON DELETE CASCADE); la provenienza di chi nasce da questo documento la difende il suo guard. SECURITY DEFINER del proprietario, search_path bloccato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
