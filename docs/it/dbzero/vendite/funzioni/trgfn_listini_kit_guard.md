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
--   BOZZA (INSERT, UPDATE, DELETE), e solo per un articolo composito.
--   Regola completa nell'intestazione del changeSet 20261031-30.
DECLARE
    v_stato       config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_riga_id     vendite.listini_kit.id%TYPE;
    v_versione_id vendite.listini_kit.listino_versione_id%TYPE;
    v_composito   catalogo.articoli.is_composito%TYPE;
    v_codice      catalogo.articoli.codice%TYPE;
BEGIN
    v_riga_id     := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    v_versione_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.listino_versione_id
                          ELSE NEW.listino_versione_id END;

    SELECT s.codice_interno INTO v_stato
      FROM vendite.listini_versioni lv
      JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
     WHERE lv.id = v_versione_id;

    -- 1. Solo in bozza. Una versione che non si legge non e' una bozza.
    IF v_stato IS DISTINCT FROM 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_RIGA_LISTINO_VERSIONE_CHIUSA',
            jsonb_build_object(
                'operazione',          TG_OP,
                'stato_versione',      v_stato,
                'listino_versione_id', v_versione_id,
                'riga_id',             v_riga_id,
                'tabella',             'listini_kit'),
            NULL::uuid,
            TG_OP, COALESCE(v_riga_id::text, 'nuova'), COALESCE(v_stato, 'NULL'));
    END IF;

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
IS 'Guard di vendite.listini_kit: la riga (la periodicita'' di un kit su una versione di listino) si scrive solo in una versione in BOZZA, INSERT UPDATE e DELETE (E_RIGA_LISTINO_VERSIONE_CHIUSA, come i componenti, E-1 di Tid del 2026-10-28), e solo per un articolo composito (E_LISTINO_KIT_NON_COMPOSITO): la periodicita'' di un articolo semplice sta sulla sua riga di listino. L''identita'' la ferma il lucchetto generato. Nasce il 2026-10-31 (20261031-30), brief-db-contratto-righe-periodiche-in-commessa §7.7 (L12, D-2-bis).';
```

</div>

---
{% include-markdown "signature-core.md" %}
