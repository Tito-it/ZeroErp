{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_guard_stato.md" %}
# ⚙️ Funzione `trgfn_listini_righe_guard_stato`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: le righe di listino secondo lo stato della versione (BEFORE
--   INSERT, UPDATE e DELETE). La regola sta in
--   script.fn_check_listino_riga_scrivibile, la stessa che dicono le
--   superfici (la riga nuova in vendite.vw_listini_versioni_azioni, la
--   riga che c'e' in vendite.vw_listini_righe_azioni): qui si solleva
--   soltanto il primo motivo.
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        script.fn_check_listino_riga_scrivibile(
            CASE WHEN TG_OP = 'INSERT' THEN NEW.listino_versione_id ELSE OLD.listino_versione_id END,
            CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.id END,
            TG_OP),
        NULL,
        CASE WHEN TG_OP = 'INSERT' THEN NEW.tx_id ELSE OLD.tx_id END,
        jsonb_build_object('operazione', TG_OP, 'tabella', 'listini_righe'));

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_stato()
IS 'Guard sulle righe di listino (BEFORE INSERT, UPDATE e DELETE, trg_listini_righe_a10_guard_stato_ins_upd_dlt): solleva il primo motivo di script.fn_check_listino_riga_scrivibile, la regola che dicono anche le superfici vendite.vw_listini_versioni_azioni (la riga nuova) e vendite.vw_listini_righe_azioni (la riga che c''e''). In bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, passa tutto; in una versione CHIUSA niente, nemmeno una riga nuova (E_RIGA_LISTINO_VERSIONE_CHIUSA); fuori dalla bozza una riga nuova e'' una rettifica e passa, una riga che c''e'' passa finche'' il suo prezzo non e'' stato usato da un documento (E_RIGA_LISTINO_PROPAGATA). Per cambiare il prezzo di una riga propagata si fa una versione nuova del listino. E'' il verbo delle azioni AGGIUNGI_RIGA_LISTINO e MODIFICA_RIGA_LISTINO nel registro config.azioni_riga: le righe di listino si scrivono direttamente, e chi rifiuta e'' questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
