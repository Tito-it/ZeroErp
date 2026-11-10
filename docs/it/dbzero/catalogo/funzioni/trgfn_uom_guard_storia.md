{% include-markdown "it/dbzero/catalogo/manual/trgfn_uom_guard_storia.md" %}
# ⚙️ Funzione `trgfn_uom_guard_storia`

```sql
CREATE FUNCTION trgfn_uom_guard_storia()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_uom_guard_storia()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_oggi     date := script.fn_data_operativa();
    -- La riga come jsonb: una funzione sola su due tabelle.
    v_old      jsonb := to_jsonb(OLD);
    v_new      jsonb;
    -- L'inizio: NULL vuol dire «da sempre» sulla mappatura.
    v_dal      date := COALESCE((to_jsonb(OLD) ->> 'valido_dal')::date, '-infinity'::date);
    v_al_old   date := (to_jsonb(OLD) ->> 'valido_al')::date;
    v_al_new   date;
    v_min_al   date := script.fn_data_operativa() - 1;
    -- Nomi di colonna (TG_ARGV): nessuna colonna di cui siano il riflesso.
    v_campo    text;
    -- La conversione nei valori dei messaggi, e il contesto.
    v_oggetto  text;
    v_contesto jsonb;
    v_articolo catalogo.articoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: una conversione gia' scritta non riscrive i giorni
    --   passati: si chiude e se ne apre una nuova.
    -- Eventi: UPDATE, DELETE. TG_ARGV: le colonne della conversione.
    -- =========================================================

    -- La riga base della mappatura e' ferma altrove.
    IF TG_TABLE_NAME = 'articoli_uom_operativa' AND (v_old ->> 'is_base')::boolean THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- La conversione, per le frasi; e se l'articolo o l'unita' non c'e'
    -- piu', e' la sua cancellazione che porta via la riga.
    IF TG_TABLE_NAME = 'articoli_uom_operativa' THEN
        v_articolo := (v_old ->> 'articolo_id')::uuid;
        v_oggetto  := catalogo.fn_uom_conversione_nome(v_articolo, (v_old ->> 'uom_id')::bigint, NULL);
    ELSE
        v_oggetto  := catalogo.fn_uom_conversione_nome(NULL, (v_old ->> 'uom_from_id')::bigint,
                                                       (v_old ->> 'uom_to_id')::bigint);
    END IF;
    IF v_oggetto IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    v_contesto := jsonb_build_object(
        'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'riga_id', v_old -> 'id',
        'operazione', TG_OP);
    IF v_articolo IS NOT NULL THEN
        v_contesto := v_contesto
            || jsonb_build_object('articolo_id', v_articolo,
                                  'bersaglio', jsonb_build_array(
                                      jsonb_build_object('tipo', 'ARTICOLO', 'id', v_articolo::text)));
    END IF;

    -- 2 (DELETE). Solo una riga senza giorni passati.
    IF TG_OP = 'DELETE' THEN
        IF v_dal < v_oggi THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_IN_VIGORE',
                v_contesto,
                (v_old ->> 'tx_id')::uuid,
                v_oggetto);
        END IF;
        RETURN OLD;
    END IF;

    v_new := to_jsonb(NEW);

    -- 1. Le colonne della conversione non si cambiano.
    FOR v_i IN 0 .. TG_NARGS - 1 LOOP
        v_campo := TG_ARGV[v_i];
        IF (v_new -> v_campo) IS DISTINCT FROM (v_old -> v_campo) THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_IMMUTABILE',
                v_contesto || jsonb_build_object('campo', v_campo),
                (v_new ->> 'tx_id')::uuid,
                v_oggetto);
        END IF;
    END LOOP;

    -- 2 (UPDATE). Spegnere o riaccendere: solo senza giorni passati.
    IF (v_new -> 'attivo') IS DISTINCT FROM (v_old -> 'attivo') AND v_dal < v_oggi THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_IN_VIGORE',
            v_contesto || jsonb_build_object('campo', 'attivo'),
            (v_new ->> 'tx_id')::uuid,
            v_oggetto);
    END IF;

    -- 3. La fine.
    v_al_new := (v_new ->> 'valido_al')::date;
    IF v_al_new IS DISTINCT FROM v_al_old
       AND (v_al_new IS NULL OR v_al_new >= v_dal) THEN
        IF v_al_old < v_oggi THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_CHIUSA',
                v_contesto || jsonb_build_object('campo', 'valido_al', 'valido_al', v_al_old),
                (v_new ->> 'tx_id')::uuid,
                v_oggetto, to_char(v_al_old, 'DD/MM/YYYY'));
        END IF;
        IF v_al_new < v_min_al THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_CHIUSURA_RETROATTIVA',
                v_contesto || jsonb_build_object('campo', 'valido_al', 'valido_al', v_al_new,
                                                 'valido_al_min', v_min_al),
                (v_new ->> 'tx_id')::uuid,
                v_oggetto, to_char(v_min_al, 'DD/MM/YYYY'));
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_uom_guard_storia()
IS 'Guard della storia delle conversioni, su catalogo.articoli_uom_operativa (la mappatura di un articolo) e catalogo.unita_misura_conversioni (la conversione generale): sono versionate, e una conversione gia'' scritta non riscrive i giorni passati. BEFORE UPDATE OR DELETE. TG_ARGV: le colonne che fanno la conversione (le unita'', l''articolo, il fattore, l''inizio). Regole: 1. una di quelle colonne cambiata -> E_UOM_STORIA_IMMUTABILE (campo: la colonna): la conversione si chiude e se ne apre una nuova; 2. spegnere o riaccendere (attivo) e cancellare sono ammessi solo se la conversione comincia oggi o dopo (nessun giorno passato, la riga inserita per errore); altrimenti -> E_UOM_STORIA_IN_VIGORE; 3. la fine (valido_al): se e'' gia'' passata (prima di oggi) non si cambia piu'' -> E_UOM_STORIA_CHIUSA; altrimenti la fine nuova e'' vuota o da ieri in avanti -> E_UOM_STORIA_CHIUSURA_RETROATTIVA. Una fine prima dell''inizio la giudica script.trgfn_guard_date_validita. Il giorno e'' script.fn_data_operativa. La riga dell''unita'' base di un articolo non passa di qui: e'' ferma per catalogo.trgfn_articoli_uom_operativa_guard_base e per il CHECK chk_articoli_uom_operativa_base_fissa. La cancellazione di un articolo o di un''unita'' porta via le sue conversioni senza giudizio. Valori dei messaggi: la conversione col nome di catalogo.fn_uom_conversione_nome; bersaglio ARTICOLO per la mappatura. Che la chiusura non lasci un listino attivo senza conversione lo giudica catalogo.trgfn_uom_guard_listini_attivi, a fine transazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
