# ⚙️ Funzione `trgfn_listini_righe_guard_tipologia`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_tipologia()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_tipologia()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_articolo_tipologia_id catalogo.articoli.listino_tipologia_id%TYPE;
    v_listino_tipologia_id  vendite.listini.tipologia_id%TYPE;
BEGIN
    -- Recupera in una sola query articolo.tipologia e listino.tipologia
    -- risalendo versione -> listino.
    SELECT a.listino_tipologia_id, l.tipologia_id
      INTO v_articolo_tipologia_id, v_listino_tipologia_id
      FROM catalogo.articoli a
      JOIN vendite.listini_versioni lv
        ON lv.id = NEW.listino_versione_id
      JOIN vendite.listini l
        ON l.id = lv.listino_id
     WHERE a.id = NEW.articolo_id;

    -- Articolo senza tipologia: non puo' entrare in listino tipizzato.
    IF v_articolo_tipologia_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME,
            'E_ARTICOLO_TIPOLOGIA_MANCANTE',
            jsonb_build_object(
                'detail', 'articolo privo di listino_tipologia_id: mappare l''articolo prima di inserirlo in un listino',
                'articolo_id', NEW.articolo_id,
                'listino_versione_id', NEW.listino_versione_id,
                'listino_tipologia_id', v_listino_tipologia_id
            ),
            NULL::uuid,
            'Articolo senza listino_tipologia_id: non ammesso in listino tipizzato'
        );
    END IF;

    -- Incompatibilita' tra tipologia articolo e tipologia listino.
    IF v_articolo_tipologia_id IS DISTINCT FROM v_listino_tipologia_id THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME,
            'E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE',
            jsonb_build_object(
                'detail', 'articolo.listino_tipologia_id diverso da listino.tipologia_id',
                'articolo_id', NEW.articolo_id,
                'articolo_tipologia_id', v_articolo_tipologia_id,
                'listino_versione_id', NEW.listino_versione_id,
                'listino_tipologia_id', v_listino_tipologia_id
            ),
            NULL::uuid,
            'Tipologia articolo incompatibile con tipologia listino'
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_tipologia()
IS 'Guard BEFORE INS/UPD su vendite.listini_righe: articolo.listino_tipologia_id deve coincidere con listino.tipologia_id. Pricing v5.';
```

---
{% include-markdown "signature-core.md" %}
