{% include-markdown "it/dbzero/vendite/manual/trgfn_fattura_satellite_guard_congelamento.md" %}
# ⚙️ Funzione `trgfn_fattura_satellite_guard_congelamento`

```sql
CREATE FUNCTION trgfn_fattura_satellite_guard_congelamento()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la fattura e' un documento fiscale — superata la soglia
--        DRAFT/EMESSA i suoi SATELLITI (scadenze, indirizzi,
--        riepiloghi) sono uno snapshot e non si toccano piu', ne'
--        in scrittura ne' in cancellazione.
-- Uso:   BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW
--        EXECUTE FUNCTION ...('<colonna_fk_fattura>')
-- Parametrico perche' la stessa regola vale su piu' tabelle:
--   una funzione, N montaggi (piano C-11).
DECLARE
    v_fk_col      text := TG_ARGV[0];
    -- ⭐ Il CODICE ERRORE e' un argomento (D34). Senza, questa funzione
    --    poteva servire solo i satelliti «generici», e chi voleva un errore
    --    piu' preciso doveva scriversi una funzione tutta sua — che e'
    --    esattamente cio' che era successo con le righe di fattura.
    -- ⚠️ TG_ARGV fuori range da' NULL, non un errore: il COALESCE tiene il
    --    comportamento di chi monta il trigger con un argomento solo.
    v_codice      text := COALESCE(NULLIF(btrim(TG_ARGV[1]), ''),
                                  'E_FATTURA_SATELLITE_CONGELATO');
    v_row         jsonb;
    v_fattura_id  vendite.fatture.id%TYPE;
    v_riga_id     bigint;
    v_stato       config.stati_doc_fiscale.codice_interno%TYPE;
    v_congela config.stati_doc_fiscale.congela_fiscale%TYPE;
    v_allow_reset text;
BEGIN
    -- Guard di montaggio: senza la colonna FK il trigger non sa
    -- quale fattura guardare. Errore esplicito, mai silenzio.
    IF v_fk_col IS NULL OR btrim(v_fk_col) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fattura_satellite_guard_congelamento',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'TG_ARGV[0]',
                'tabella',   TG_TABLE_NAME,
                'trigger',   TG_NAME),
            NULL::uuid,
            'TG_ARGV[0] (colonna FK verso vendite.fatture) obbligatorio'
        );
    END IF;

    -- Bypass di manutenzione: stesso contratto degli altri guard
    -- della famiglia. fn_cleanup_fatture_by_ids (reset lotto)
    -- imposta questa GUC per attraversarli.
    v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF COALESCE(lower(v_allow_reset), 'off') IN ('on', 'true', '1') THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END IF;

    -- Riga come jsonb: e' cio' che rende la funzione indipendente
    -- dalla forma della tabella su cui e' montata.
    IF TG_OP = 'DELETE' THEN
        v_row := to_jsonb(OLD);
    ELSE
        v_row := to_jsonb(NEW);
    END IF;

    v_fattura_id := NULLIF(v_row ->> v_fk_col, '')::bigint;
    v_riga_id    := NULLIF(v_row ->> 'id', '')::bigint;

    -- Riga non ancora agganciata a una fattura: non e' questo il
    -- guard che deve occuparsene.
    IF v_fattura_id IS NULL THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END IF;

    -- Stato per codice_interno (immutabile), mai per codice.
    SELECT s.codice_interno, s.congela_fiscale
      INTO v_stato, v_congela
      FROM vendite.fatture f
      JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
     WHERE f.id = v_fattura_id;

    -- Fattura senza stato — o gia' cancellata, che e' il caso
    -- della DELETE in cascata dalla testata: la riga padre non
    -- c'e' piu' quando i figli scattano. Fallire qui darebbe un
    -- errore fuorviante su un problema che sta altrove.
    IF v_stato IS NULL THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END IF;

    -- ⭐ LA SOGLIA E' UN DATO, non una lista scritta qui (D33).
    --    Fino al 2026-08-30 questa funzione portava la propria copia di
    --    `NOT IN ('DRAFT','EMESSA')`. Erano OTTO copie della stessa frase,
    --    e `config.stati_doc_fiscale.congela_fiscale` era nata (I10) proprio
    --    per toglierle: era stata collegata a un solo lettore.
    -- ⚠️ Il comportamento NON cambia: verificato che sui sei stati esistenti
    --    colonna e lista dicono la stessa cosa. Cambia la SEDE, cioe' quante
    --    cose vanno toccate il giorno che il confine si sposta - da otto a una.
    -- ⚠️ E il trattamento dello STATO MANCANTE resta identico a prima: e' una
    --    decisione di questa funzione, non della soglia.
    -- ⚠️ Qui `v_congela` non puo' essere NULL: la colonna e' NOT NULL e il
    --    JOIN e' interno, quindi se lo stato non si risolve `v_stato` e' NULL e
    --    la funzione e' gia' uscita sopra, dal ramo che resta com'era.
    IF v_congela THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fattura_satellite_guard_congelamento',
            v_codice,
            jsonb_build_object(
                'operazione', TG_OP,
                'tabella',    TG_TABLE_NAME,
                'fattura_id', v_fattura_id,
                'riga_id',    v_riga_id,
                'stato',      v_stato,
                'soglia',     'congela_fiscale'),
            NULL::uuid,
            v_fattura_id::text, v_stato, TG_TABLE_NAME
        );
    END IF;

    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento()
IS 'Guard (BEFORE INSERT OR UPDATE OR DELETE) PARAMETRICO per i satelliti della fattura: oltre la soglia DRAFT/EMESSA il documento e'' uno snapshot fiscale e i suoi satelliti non si toccano piu''. La colonna FK verso vendite.fatture si passa in TG_ARGV[0], cosi'' la stessa regola vale su fatture_scadenze, fatture_indirizzi e (quando servira'') fatture_riepiloghi_iva senza copie da tenere allineate. Soglia identica a fn_ricalcola_riepilogo_iva_fattura, per codice_interno. Bypass via GUC zeroerp.maintenance_reset_lotto_draft, che vendite.fn_cleanup_fatture_by_ids imposta per il reset lotto. Esce in testa se la fattura non ha stato: e'' il caso della DELETE in CASCADE dalla testata, in cui la riga padre non esiste piu'' quando i figli scattano. Errore: E_FATTURA_SATELLITE_CONGELATO. Modello: trgfn_fatture_righe_guard_congelamento. piano-db-satelliti-fattura C-11, Fase 1.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
