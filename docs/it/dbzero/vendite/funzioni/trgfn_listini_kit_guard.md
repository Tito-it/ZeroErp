# ⚙️ Funzione `trgfn_listini_kit_guard`

```sql
CREATE FUNCTION trgfn_listini_kit_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_kit_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la riga di vendite.listini_kit si scrive solo in una versione in
--   bozza (INSERT, UPDATE, DELETE), come le righe
--   (script.fn_check_listino_riga_scrivibile, la stessa che dice la
--   superficie della versione), e solo per un articolo composito.
--   Regola completa nell'intestazione dei changeSet 20261031-30 e
--   20261115-70.
DECLARE
    v_composito   catalogo.articoli.is_composito%TYPE;
    v_codice      catalogo.articoli.codice%TYPE;
BEGIN
    -- 1. Solo in bozza.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        script.fn_check_listino_riga_scrivibile(
            CASE WHEN TG_OP = 'INSERT' THEN NEW.listino_versione_id ELSE OLD.listino_versione_id END,
            CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.id END,
            TG_OP),
        NULL,
        NULL::uuid,
        jsonb_build_object('operazione', TG_OP, 'tabella', 'listini_kit'));

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    -- 2. Il kit e' un composito.
    SELECT a.is_composito, a.codice INTO v_composito, v_codice
      FROM catalogo.articoli a
     WHERE a.id = NEW.articolo_padre_id;

    IF v_composito IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_LISTINO_KIT_NON_COMPOSITO',
            jsonb_build_object(
                'campo',               'articolo_padre_id',
                'articolo_padre_id',   NEW.articolo_padre_id,
                'listino_versione_id', NEW.listino_versione_id),
            NULL::uuid,
            COALESCE(v_codice, NEW.articolo_padre_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_kit_guard()
IS 'Guard di vendite.listini_kit: la riga (la periodicita'' di un kit su una versione di listino) si scrive solo in una versione in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, in INSERT, UPDATE e DELETE, come le righe e i prezzi dei componenti: solleva il primo motivo di script.fn_check_listino_riga_scrivibile, la regola che dice anche la superficie vendite.vw_listini_versioni_azioni (periodicita_kit_blocco_*): CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, fuori dalla bozza E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA. E solo per un articolo composito (E_LISTINO_KIT_NON_COMPOSITO): la periodicita'' di un articolo semplice sta sulla sua riga di listino. L''identita'' la ferma il lucchetto generato. E'' il verbo dell''azione PERIODICITA_KIT_LISTINO nel registro config.azioni_riga: il kit si scrive direttamente, e chi rifiuta e'' questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
