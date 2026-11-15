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
--   INSERT, UPDATE e DELETE). Si scrivono solo in bozza
--   (script.fn_check_listino_riga_scrivibile, la stessa che dicono le
--   superfici). L'unica eccezione e' la rettifica del prezzo, dalla
--   porta del verbo vendite.fn_rettifica_riga_listino: li' risponde
--   script.fn_check_listino_riga_rettificabile. Qui si solleva soltanto
--   il primo motivo.
DECLARE
    -- Nomi di colonna della tabella: la rettifica cambia prezzo e meta,
    --   le altre tre le scrivono i trigger generati.
    v_rettifica text[] := ARRAY['prezzo', 'meta', 'data_update', 'user_update', 'tx_id'];
BEGIN
    -- La porta della rettifica: per QUESTA riga, dal proprietario della
    -- tabella (il verbo e' SECURITY DEFINER), e solo prezzo e meta.
    IF TG_OP = 'UPDATE'
       AND COALESCE(current_setting('zeroerp.listino_riga_rettifica', true), '') = OLD.id::text
       AND script.fn_is_proprietario_tabella(TG_RELID)
       AND (to_jsonb(NEW) - v_rettifica) = (to_jsonb(OLD) - v_rettifica) THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', TG_NAME::text,
            script.fn_check_listino_riga_rettificabile(OLD.id),
            'prezzo',
            OLD.tx_id,
            jsonb_build_object('operazione', 'RETTIFICA', 'tabella', 'listini_righe'));
        RETURN NEW;
    END IF;

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
IS 'Guard sulle righe di listino (BEFORE INSERT, UPDATE e DELETE, trg_listini_righe_a10_guard_stato_ins_upd_dlt): le righe si scrivono solo in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni. Solleva il primo motivo di script.fn_check_listino_riga_scrivibile, la regola che dicono anche le superfici vendite.vw_listini_versioni_azioni (la riga nuova, la variazione) e vendite.vw_listini_righe_azioni (la riga che c''e''): CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, fuori dalla bozza E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA. Una sola eccezione, la rettifica: con la GUC transazionale zeroerp.listino_riga_rettifica = id della riga e il proprietario della tabella (script.fn_is_proprietario_tabella), un UPDATE che cambia il solo prezzo e meta solleva invece il primo motivo di script.fn_check_listino_riga_rettificabile (in bozza, CHIUSA, non in vigore, propagata). La porta l''apre solo il verbo vendite.fn_rettifica_riga_listino, che chiede il motivo e scrive la traccia. E'' il verbo delle azioni AGGIUNGI_RIGA_LISTINO, MODIFICA_RIGA_LISTINO e VARIA_PREZZI_LISTINO nel registro config.azioni_riga: quelle scritture sono dirette, e chi rifiuta e'' questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
