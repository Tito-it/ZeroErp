{% include-markdown "it/dbzero/magazzino/manual/fn_documento_interno_blocca.md" %}
# ⚙️ Funzione `fn_documento_interno_blocca`

```sql
CREATE FUNCTION fn_documento_interno_blocca(p_famiglia text, p_documento_id bigint, p_auth_user_id integer, p_porta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_documento_interno_blocca(p_famiglia text, p_documento_id bigint, p_auth_user_id integer, p_porta text)
 RETURNS TABLE(famiglia text, tabella text, tabella_righe text, colonna_fk text, colonna_stato text, colonna_magazzino text, guc_posting text, stato text)
 LANGUAGE plpgsql
 ROWS 1
AS $function$
DECLARE
    v_fam   record;
    v_stato text;   -- lo stato della famiglia: tre colonne, nessuna sola da ancorare
BEGIN
    -- Scopo: la testata del documento p_documento_id della famiglia
    --   p_famiglia, presa FOR UPDATE col predicato della policy sul
    --   suo magazzino. Ritorna la riga del registro e lo stato letto.
    SELECT f.* INTO v_fam FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f;
    IF v_fam.famiglia IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', p_porta, 'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_famiglia', p_famiglia),
            NULL::uuid,
            p_porta,
            'p_famiglia (INVENTARIO | RETTIFICA | TRASFERIMENTO)');
    END IF;

    -- Le GUC della registrazione si spengono: chi arriva qui e' un
    -- verbo DEFINER, cioe' il proprietario, e la GUC accesa dall'app
    -- prima della chiamata aprirebbe le due porte dei trigger (POSTED
    -- e le righe fuori da DRAFT) a un gesto che non registra niente.
    -- Basta quella della famiglia: ogni verbo passa di qui per il
    -- suo documento. La registrazione (fn_posta_*) la accende da
    -- se', dopo.
    PERFORM set_config(v_fam.guc_posting, '', true);

    -- No-leak: inesistente e fuori perimetro rispondono uguale. Lo
    -- stato e' NOT NULL: NULL vuol dire che la riga non c'e'. Nomi
    -- dal registro, quotati: mai da un input.
    IF p_documento_id IS NOT NULL THEN
        EXECUTE format('SELECT t.%I FROM magazzino.%I t
                         WHERE t.id = $1
                           AND script.fn_scope_ef_whitelist_via_magazzino($2, t.%I)
                           FOR UPDATE',
                       v_fam.colonna_stato, v_fam.tabella, v_fam.colonna_magazzino)
           INTO v_stato
          USING p_documento_id, p_auth_user_id;
    END IF;
    IF v_stato IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', p_porta, 'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('famiglia', v_fam.famiglia, 'documento_id', p_documento_id),
            NULL::uuid,
            COALESCE(p_documento_id::text, '(nessuno)'));
    END IF;

    RETURN QUERY SELECT v_fam.famiglia, v_fam.tabella, v_fam.tabella_righe,
                        v_fam.colonna_fk, v_fam.colonna_stato,
                        v_fam.colonna_magazzino, v_fam.guc_posting, v_stato;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_documento_interno_blocca(p_famiglia text, p_documento_id bigint, p_auth_user_id integer, p_porta text)
IS 'Guard: la testata del documento interno p_documento_id della famiglia p_famiglia (INVENTARIO, RETTIFICA, TRASFERIMENTO), presa FOR UPDATE col predicato della policy sul suo magazzino (script.fn_scope_ef_whitelist_via_magazzino; per il trasferimento quello di partenza). Inesistente o fuori perimetro: E_MAG_DOCUMENTO_NON_TROVATO, senza dire quale dei due. Una famiglia che il registro non conosce: E_MAG_CHIAMATA_NON_VALIDA. Ritorna la riga del registro magazzino.fn_documento_interno_famiglia e lo stato della testata, letto sotto il lock. p_porta e'' la funzione che rifiuta: il log e'' suo. La usano i verbi delle righe e i verbi comuni dei documenti interni, dentro i quali la RLS non filtra. Spegne la GUC della registrazione della famiglia (dal registro): dentro un verbo SECURITY DEFINER chi scrive e'' il proprietario, e una GUC accesa dall''applicazione aprirebbe ai trigger la porta POSTED e le righe fuori da DRAFT; la registrazione la accende da se''. Non controlla il permesso e non guarda lo stato: lo stato lo fanno rispettare i guard della tabella. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
