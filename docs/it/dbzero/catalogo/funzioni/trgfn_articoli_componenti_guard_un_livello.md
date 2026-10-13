{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_un_livello.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_guard_un_livello`

```sql
CREATE FUNCTION trgfn_articoli_componenti_guard_un_livello()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_guard_un_livello()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_is_composito   catalogo.articoli.is_composito%TYPE;
    v_codice_padre   catalogo.articoli.codice%TYPE;
    v_codice_comp    catalogo.articoli.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La distinta base ha un livello solo: il componente di un
    --   legame attivo non e' un articolo composito.
    --   BEFORE INSERT OR UPDATE OF attivo su catalogo.articoli_componenti.
    --   Si giudica il legame che nasce attivo e quello che si
    --   riaccende; un legame spento non e' parte della distinta.
    -- =========================================================
    IF NOT COALESCE(NEW.attivo, FALSE) THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND COALESCE(OLD.attivo, FALSE) THEN
        RETURN NEW;
    END IF;

    SELECT a_comp.is_composito, a_comp.codice, a_padre.codice
      INTO v_is_composito, v_codice_comp, v_codice_padre
      FROM catalogo.articoli a_comp
      LEFT JOIN catalogo.articoli a_padre ON a_padre.id = NEW.prodotto_id
     WHERE a_comp.id = NEW.componente_id;

    -- Componente assente: parla la FK.
    IF COALESCE(v_is_composito, FALSE) THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_BOM_COMPONENTE_COMPOSITO',
            jsonb_build_object(
                'campo',         'componente_id',
                'prodotto_id',   NEW.prodotto_id,
                'componente_id', NEW.componente_id),
            NULL::uuid,
            v_codice_comp,
            COALESCE(v_codice_padre, NEW.prodotto_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_guard_un_livello()
IS 'Guard BEFORE INSERT OR UPDATE OF attivo su catalogo.articoli_componenti: la distinta base ha un livello solo, il componente di un legame attivo non e'' un articolo composito (E_BOM_COMPONENTE_COMPOSITO, campo componente_id). Si giudicano il legame che nasce attivo e quello che si riaccende (componente_id non si cambia: trgfn_articoli_componenti_block_modifica_struttura). Il resto del modello lavora su un livello (le fn_*_riga_componenti_init leggono i figli diretti, le tabelle dei componenti di riga sono piatte, il bundle di listino e'' la somma di un livello) e con un livello solo un ciclo non si costruisce. Il lato articolo (un componente che diventa composito) e'' in catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva. Brief: brief-db-articoli-ammessi-per-documento (§8.4 D-4).';
```

---
{% include-markdown "signature-core.md" %}
