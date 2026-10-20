{% include-markdown "it/dbzero/script/manual/trgfn_righe_natura_vendita.md" %}
# ⚙️ Funzione `trgfn_righe_natura_vendita`

```sql
CREATE FUNCTION trgfn_righe_natura_vendita()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_natura_vendita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_modo nudo: e' il selettore del montaggio (TG_ARGV), con
    --   due valori dichiarati qui sotto.
    v_modo     text := TG_ARGV[0];
    v_natura   catalogo.articoli.natura_vendita_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La natura di vendita di una riga di documento: alla
    --   nascita e al cambio di articolo, poi congelata.
    --   BEFORE INSERT OR UPDATE OF articolo_id, natura_vendita_id.
    -- =========================================================
    IF v_modo IS NULL OR v_modo NOT IN ('ARTICOLO', 'CHIAMANTE') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'tgargs', to_jsonb(TG_ARGV)),
            NULL::uuid,
            TG_NAME || ': TG_ARGV[0] deve essere ARTICOLO o CHIAMANTE');
    END IF;

    IF TG_OP = 'UPDATE'
       AND NEW.articolo_id IS NOT DISTINCT FROM OLD.articolo_id THEN
        -- Stesso articolo: qui non si decide niente. Una natura
        -- scritta a mano l'ha gia' giudicata il lock di colonna,
        -- che parla prima (ordine dei nomi) ed e' la sede unica
        -- della regola, porta di manutenzione compresa
        -- (zeroerp.allow_lock_columns_override).
        -- ⛔ rev 2026-10-13 (20261013-14): niente piu'
        --    NEW := OLD «per difesa». Era una seconda copia del
        --    lock, e gia' diversa: richiudeva in silenzio la
        --    porta che il lock prevede apposta.
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' AND v_modo = 'CHIAMANTE'
       AND NEW.natura_vendita_id IS NOT NULL THEN
        -- La porta il verbo che copia la riga dall'origine.
        RETURN NEW;
    END IF;

    SELECT a.natura_vendita_id
      INTO v_natura
      FROM catalogo.articoli a
     WHERE a.id = NEW.articolo_id;

    -- Articolo assente: parla la FK della riga.
    NEW.natura_vendita_id := v_natura;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_natura_vendita()
IS 'BB trigger BEFORE INSERT OR UPDATE OF articolo_id, natura_vendita_id sulle righe di documento che portano la natura di vendita (vendite.preventivi_righe, vendite.ordini_righe, vendite.ddt_righe). La natura e'' quella con cui la riga e'' stata venduta: si scrive alla nascita (dall''articolo; in modo CHIAMANTE quella portata dal verbo che copia la riga dal documento d''origine, se la porta) e quando cambia l''articolo (dal nuovo articolo), poi resta, anche se l''articolo cambia natura in anagrafica. TG_ARGV[0]: ARTICOLO | CHIAMANTE (altrimenti E_TRIGGER_ARGOMENTI_INVALIDI). Scriverla a mano lo rifiuta il lock di colonna (dbops.automation_lock_columns, E_RIGA_NATURA_VENDITA_IMMUTABILE), che parla prima di questo trigger nell''ordine dei nomi; a parita'' di articolo questo trigger non tocca la colonna: la regola e la sua porta di manutenzione (zeroerp.allow_lock_columns_override) stanno solo nel lock. rev 2026-10-13 (20261013-14): tolta la riassegnazione a OLD «per difesa», che richiudeva in silenzio quella porta. Estratto alla terza copia: prima la scriveva vendite.trgfn_preventivi_righe_set_natura_vendita, che da 20261013-10 e'' solo il guard della ricorrenza. Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
