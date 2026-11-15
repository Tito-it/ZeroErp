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
    -- La riga come jsonb: una funzione sola su due tabelle.
    v_old      jsonb := to_jsonb(OLD);
    v_new      jsonb;
    -- L'inizio: NULL vuol dire «da sempre» sulla mappatura. Tipo nudo
    -- DICHIARATO: la colonna e' di due tabelle diverse.
    v_dal      date := COALESCE((to_jsonb(OLD) ->> 'valido_dal')::date, '-infinity'::date);
    v_al_old   date := (to_jsonb(OLD) ->> 'valido_al')::date;
    v_al_new   date;
    -- Che cosa si puo' fare sulla riga, dalle sue date di prima: lo stesso
    -- giudizio che le viste di dettaglio pubblicano.
    v_cap      record;
    -- La conversione nei valori dei messaggi, e il contesto.
    v_oggetto  text;
    v_contesto jsonb;
    v_articolo catalogo.articoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: una conversione gia' scritta non riscrive i giorni
    --   passati: si spegne o si cancella solo senza giorni passati, e
    --   la fine si sposta solo in avanti da ieri.
    -- Eventi: UPDATE OF attivo, valido_al; DELETE.
    -- ⛔ Le colonne che fanno la conversione (unita', articolo,
    --   fattore, inizio) non passano di qui: le blocca
    --   script.trgfn_lock_columns (dbops.automation_lock_columns),
    --   che il form legge in dbops.vw_non_editable_fields.
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

    SELECT * INTO v_cap
      FROM catalogo.fn_uom_conversione_capability((v_old ->> 'valido_dal')::date, v_al_old);

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

    -- 1 (DELETE). Solo una riga senza giorni passati.
    IF TG_OP = 'DELETE' THEN
        IF NOT v_cap.puo_eliminarsi THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_IN_VIGORE',
                v_contesto,
                (v_old ->> 'tx_id')::uuid,
                v_oggetto);
        END IF;
        RETURN OLD;
    END IF;

    v_new := to_jsonb(NEW);

    -- 1 (UPDATE). Spegnere o riaccendere: solo senza giorni passati.
    IF (v_new -> 'attivo') IS DISTINCT FROM (v_old -> 'attivo') AND NOT v_cap.puo_cambiare_attivo THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_IN_VIGORE',
            v_contesto || jsonb_build_object('campo', 'attivo'),
            (v_new ->> 'tx_id')::uuid,
            v_oggetto);
    END IF;

    -- 2. La fine. Una fine prima dell'inizio la giudica
    --    script.trgfn_guard_date_validita.
    v_al_new := (v_new ->> 'valido_al')::date;
    IF v_al_new IS DISTINCT FROM v_al_old
       AND (v_al_new IS NULL OR v_al_new >= v_dal) THEN
        IF NOT v_cap.puo_chiudersi THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_CHIUSA',
                v_contesto || jsonb_build_object('campo', 'valido_al', 'valido_al', v_al_old),
                (v_new ->> 'tx_id')::uuid,
                v_oggetto, to_char(v_al_old, 'DD/MM/YYYY'));
        END IF;
        IF v_al_new < v_cap.data_min_chiusura THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_uom_guard_storia', 'E_UOM_STORIA_CHIUSURA_RETROATTIVA',
                v_contesto || jsonb_build_object('campo', 'valido_al', 'valido_al', v_al_new,
                                                 'valido_al_min', v_cap.data_min_chiusura),
                (v_new ->> 'tx_id')::uuid,
                v_oggetto, to_char(v_cap.data_min_chiusura, 'DD/MM/YYYY'));
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_uom_guard_storia()
IS 'Guard della storia delle conversioni, su catalogo.articoli_uom_operativa (la mappatura di un articolo) e catalogo.unita_misura_conversioni (la conversione generale): sono versionate, e una conversione gia'' scritta non riscrive i giorni passati. BEFORE UPDATE OF attivo, valido_al OR DELETE; nessun argomento. Regole, giudicate da catalogo.fn_uom_conversione_capability sulle date di prima (lo stesso giudizio che pubblicano le viste di dettaglio): 1. spegnere o riaccendere (attivo) e cancellare sono ammessi solo se la conversione comincia oggi o dopo (nessun giorno passato, la riga inserita per errore); altrimenti -> E_UOM_STORIA_IN_VIGORE; 2. la fine (valido_al): se e'' gia'' passata (prima di oggi) non si cambia piu'' -> E_UOM_STORIA_CHIUSA; altrimenti la fine nuova e'' vuota o da ieri in avanti -> E_UOM_STORIA_CHIUSURA_RETROATTIVA. Una fine prima dell''inizio la giudica script.trgfn_guard_date_validita. Le colonne che fanno la conversione (le unita'', l''articolo, il fattore, l''inizio) non si cambiano mai: non le giudica questo guard ma script.trgfn_lock_columns, dal registro dbops.automation_lock_columns, col codice E_UOM_STORIA_IMMUTABILE; cosi'' il form le trova in dbops.vw_non_editable_fields. La riga dell''unita'' base di un articolo non passa di qui: e'' ferma per catalogo.trgfn_articoli_uom_operativa_guard_base e per il CHECK chk_articoli_uom_operativa_base_fissa. La cancellazione di un articolo o di un''unita'' porta via le sue conversioni senza giudizio. Valori dei messaggi: la conversione col nome di catalogo.fn_uom_conversione_nome; bersaglio ARTICOLO per la mappatura. Che la chiusura non lasci un listino attivo senza conversione lo giudica catalogo.trgfn_uom_guard_listini_attivi, a fine transazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
