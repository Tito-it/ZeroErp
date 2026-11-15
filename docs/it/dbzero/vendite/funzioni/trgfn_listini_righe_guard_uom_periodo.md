{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_guard_uom_periodo.md" %}
# ⚙️ Funzione `trgfn_listini_righe_guard_uom_periodo`

```sql
CREATE FUNCTION trgfn_listini_righe_guard_uom_periodo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_guard_uom_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_validita vendite.listini_versioni.validita%TYPE;
    v_versione vendite.listini_versioni.codice_versione%TYPE;
    v_primo    date;
    v_articolo catalogo.articoli.codice%TYPE;
    v_uom      catalogo.unita_misura.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: l'unita' di un prezzo si converte per l'articolo in
    --   ogni giorno del periodo della versione.
    -- Eventi: INSERT, UPDATE OF attivo; WHEN NEW.attivo.
    -- =========================================================
    SELECT lv.validita, lv.codice_versione
      INTO v_validita, v_versione
      FROM vendite.listini_versioni lv
     WHERE lv.id = NEW.listino_versione_id;
    -- Versione assente o fuori perimetro: parlano la FK o la RLS.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    v_primo := catalogo.fn_uom_primo_giorno_non_convertibile(NEW.articolo_id, NEW.uom_id, v_validita);
    IF v_primo IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT a.codice INTO v_articolo FROM catalogo.articoli a     WHERE a.id = NEW.articolo_id;
    SELECT u.codice INTO v_uom      FROM catalogo.unita_misura u WHERE u.id = NEW.uom_id;

    PERFORM script.fn_log_and_raise_error(
        'vendite', 'vendite.trgfn_listini_righe_guard_uom_periodo', 'E_LISTINO_UOM_NON_CONVERTIBILE',
        jsonb_build_object(
            'campo',               'uom_id',
            'listino_versione_id', NEW.listino_versione_id,
            'articolo_id',         NEW.articolo_id,
            'uom_id',              NEW.uom_id,
            'primo_giorno',        v_primo,
            'bersaglio',           jsonb_build_array(
                                       jsonb_build_object('tipo', 'LISTINO_VERSIONE',
                                                          'id', NEW.listino_versione_id::text))),
        NEW.tx_id,
        v_versione::text,
        COALESCE(v_uom, '—'),
        COALESCE(v_articolo, '—'),
        to_char(v_primo, 'DD/MM/YYYY'));
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_guard_uom_periodo()
IS 'Guard dell''unita'' delle righe di listino (vendite.listini_righe): l''unita'' di un prezzo si converte per l''articolo in ogni giorno del periodo della versione (catalogo.fn_uom_primo_giorno_non_convertibile sulla validita della versione). BEFORE INSERT e UPDATE OF attivo, per una riga attiva: un prezzo nuovo (in BOZZA, o in ATTIVA come rettifica) e un prezzo riacceso. Articolo, unita'' e versione di una riga non cambiano (E_LISTINO_RIGA_IDENTITA_IMMUTABILE). Scoperto -> E_LISTINO_UOM_NON_CONVERTIBILE (campo uom_id; valori: versione, unita'', articolo, primo giorno scoperto; bersaglio LISTINO_VERSIONE). Gli altri due lati della regola: il periodo della versione (vendite.trgfn_listini_versioni_guard_uom_periodo) e il catalogo che cambia (catalogo.trgfn_uom_guard_listini_attivi); per una BOZZA, l''attivazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
