{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_iva_bom_attiva`

```sql
CREATE FUNCTION trgfn_articoli_guard_iva_bom_attiva()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_oggi         date := script.fn_data_operativa();
    v_codice       catalogo.articoli.codice%TYPE;
    v_iva          catalogo.articoli.iva_id%TYPE;
    v_iva_pct      text;
    v_codice_altro catalogo.articoli.codice%TYPE;
    v_iva_altro    catalogo.articoli.iva_id%TYPE;
    v_altro_pct    text;
BEGIN
    -- =========================================================
    -- Scopo: un kit e i suoi componenti hanno la stessa IVA, sui
    --   legami attivi da oggi in poi. CONSTRAINT TRIGGER AFTER
    --   UPDATE OF iva_id, differito: si giudica lo stato di fine
    --   transazione, quindi l'IVA di adesso dell'articolo e dei
    --   partner (non NEW, che puo' essere stato superato).
    --   A: l'articolo e' padre -> un componente con IVA diversa.
    --   B: l'articolo e' componente -> un padre con IVA diversa.
    -- =========================================================
    SELECT a.codice, a.iva_id
      INTO v_codice, v_iva
      FROM catalogo.articoli a
     WHERE a.id = NEW.id;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    v_iva_pct := COALESCE((SELECT i.aliquota_iva::text
                             FROM config.iva i WHERE i.id = v_iva), '—');

    -- A: l'articolo e' il padre.
    SELECT a.codice, a.iva_id
      INTO v_codice_altro, v_iva_altro
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli a ON a.id = ac.componente_id
     WHERE ac.prodotto_id = NEW.id
       AND ac.attivo
       AND ac.validita && daterange(v_oggi, NULL, '[]')
       AND a.iva_id IS DISTINCT FROM v_iva
     ORDER BY a.codice
     LIMIT 1;

    IF FOUND THEN
        v_altro_pct := COALESCE((SELECT i.aliquota_iva::text
                                   FROM config.iva i WHERE i.id = v_iva_altro), '—');
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_articoli_guard_iva_bom_attiva', 'E_BOM_IVA_DISCORDANTE',
            jsonb_build_object(
                'campo',           'iva_id',
                'prodotto_id',     NEW.id,
                'iva_padre',       v_iva,
                'iva_padre_pct',   v_iva_pct,
                'codice_figlio',   v_codice_altro,
                'iva_figlio',      v_iva_altro,
                'iva_figlio_pct',  v_altro_pct),
            NEW.tx_id,
            v_codice,
            v_iva_pct,
            v_codice_altro,
            v_altro_pct);
    END IF;

    -- B: l'articolo e' un componente.
    SELECT a.codice, a.iva_id
      INTO v_codice_altro, v_iva_altro
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli a ON a.id = ac.prodotto_id
     WHERE ac.componente_id = NEW.id
       AND ac.attivo
       AND ac.validita && daterange(v_oggi, NULL, '[]')
       AND a.iva_id IS DISTINCT FROM v_iva
     ORDER BY a.codice
     LIMIT 1;

    IF FOUND THEN
        v_altro_pct := COALESCE((SELECT i.aliquota_iva::text
                                   FROM config.iva i WHERE i.id = v_iva_altro), '—');
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_articoli_guard_iva_bom_attiva', 'E_BOM_IVA_DISCORDANTE',
            jsonb_build_object(
                'campo',            'iva_id',
                'componente_id',    NEW.id,
                'iva_figlio',       v_iva,
                'iva_figlio_pct',   v_iva_pct,
                'codice_padre',     v_codice_altro,
                'iva_padre',        v_iva_altro,
                'iva_padre_pct',    v_altro_pct),
            NEW.tx_id,
            v_codice_altro,
            v_altro_pct,
            v_codice,
            v_iva_pct);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_iva_bom_attiva()
IS 'Guard dell''IVA della distinta su catalogo.articoli: un kit e i suoi componenti hanno la stessa IVA, sui legami attivi da oggi in poi (catalogo.articoli_componenti, validita che arriva almeno al giorno aziendale, script.fn_data_operativa). CONSTRAINT TRIGGER AFTER UPDATE OF iva_id, DEFERRABLE INITIALLY DEFERRED, quando l''IVA cambia: si giudica lo stato di fine transazione, con l''IVA di adesso dell''articolo e dei partner, cosi'' l''IVA di un kit e dei suoi componenti si cambia in una transazione, in qualunque ordine. Un legame gia'' finito non blocca. Caso A, l''articolo e'' padre: un componente con IVA diversa; caso B, l''articolo e'' componente: un padre con IVA diversa -> E_BOM_IVA_DISCORDANTE (campo iva_id; valori codice e aliquota del padre, codice e aliquota del componente; aliquota assente: ''—''). Un legame nuovo con IVA diversa lo rifiuta il guard del legame.';
```

</div>

---
{% include-markdown "signature-core.md" %}
