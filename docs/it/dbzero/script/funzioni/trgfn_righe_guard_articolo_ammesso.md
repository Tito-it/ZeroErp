{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso.md" %}
# ⚙️ Funzione `trgfn_righe_guard_articolo_ammesso`

```sql
CREATE FUNCTION trgfn_righe_guard_articolo_ammesso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_articolo_ammesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: e' il selettore del montaggio (TG_ARGV);
    --   lo valida la check. v_documento_id e' l'id del padre (cinque
    --   testate diverse).
    v_documento    text   := TG_ARGV[0];
    v_col_padre    text   := TG_ARGV[1];
    -- ⚠️ v_col_esenzione nudo: nome di colonna dal montaggio (TG_ARGV[2]).
    v_col_esenzione text  := TG_ARGV[2];
    v_riga         jsonb  := to_jsonb(NEW);
    v_documento_id bigint := (to_jsonb(NEW) ->> TG_ARGV[1])::bigint;
    v_porta        text   := COALESCE(current_setting('zeroerp.ddt_riconsegna', true), '');
    v_scelta_nuova boolean;
    v_motivi       jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare una riga il cui articolo il documento non
    --   ammette: solleva il primo motivo di
    --   script.fn_check_articolo_riga. BEFORE INSERT OR UPDATE
    --   OF articolo_id.
    --   TG_ARGV: [0] documento, [1] colonna del padre,
    --   [2] (opzionale) colonna che, valorizzata all'INSERT,
    --   dice che la riga e' derivata (brief-db-articoli-obsoleto-dal).
    -- =========================================================

    IF v_col_esenzione IS NOT NULL
       AND NOT jsonb_exists(v_riga, v_col_esenzione) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'tgargs', to_jsonb(TG_ARGV)),
            NULL::uuid,
            TG_NAME || ': TG_ARGV[2] nomina una colonna che la riga non ha');
    END IF;

    -- La riconsegna (A-6): solo dal verbo, e solo per un articolo
    -- che sta fra le righe del reso che si riconsegna.
    IF v_documento = 'DDT_VENDITA' AND v_porta ~ '^[0-9]+$'
       AND EXISTS (SELECT 1 FROM vendite.resi_righe rr
                    WHERE rr.reso_id = v_porta::bigint
                      AND rr.articolo_id = NEW.articolo_id) THEN
        RETURN NEW;
    END IF;

    -- Scelta nuova (O-7, O-10): la riga nasce senza provenienza,
    -- oppure l'articolo o il documento cambiano. Riscrivere lo
    -- stesso valore non e' una scelta.
    IF TG_OP = 'INSERT' THEN
        v_scelta_nuova := v_col_esenzione IS NULL
                          OR v_riga ->> v_col_esenzione IS NULL;
    ELSE
        v_scelta_nuova := NEW.articolo_id IS DISTINCT FROM OLD.articolo_id
                          OR v_documento_id IS DISTINCT FROM
                             (to_jsonb(OLD) ->> v_col_padre)::bigint;
    END IF;

    -- Natura (preventivo, ordine, bolla) e tipo d'eccezione (offerta,
    -- contratto): ognuna c'e' solo sulle sue tabelle.
    v_motivi := script.fn_check_articolo_riga(
        v_documento, v_documento_id, NEW.articolo_id,
        (v_riga ->> 'natura_vendita_id')::bigint,
        (v_riga ->> 'tipo_eccezione')::vendite.tipo_eccezione_contratto,
        NULL,
        v_scelta_nuova);

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        v_motivi,
        COALESCE(v_motivi -> 0 -> 'dettaglio' ->> 'campo', 'articolo_id'),
        NEW.tx_id,
        jsonb_build_object('riga_id', NEW.id, v_col_padre, v_documento_id));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_articolo_ammesso()
IS 'BB guard BEFORE INSERT OR UPDATE OF articolo_id sulle righe che scelgono un articolo: vendite.preventivi_righe, vendite.ordini_righe, vendite.ddt_righe, vendite.offerte_commerciali_eccezioni, vendite.contratti_righe, vendite.listini_righe (LISTINO_VERSIONE, anche UPDATE OF listino_versione_id) e vendite.promo_articoli (PROMO_ARTICOLO, TG_ARGV[1] = id: la promo non ha un padre). Solleva il primo motivo di script.fn_check_articolo_riga (il predicato sta nella check), passando la natura della riga e il suo tipo d''eccezione, letti da to_jsonb(NEW) (ognuno c''e'' solo sulle sue tabelle). Campo: quello del primo motivo, o articolo_id. Argomenti: TG_ARGV[0] il documento (codice di config.tipi_entita); TG_ARGV[1] la colonna del padre; TG_ARGV[2], facoltativo, la colonna che, valorizzata all''INSERT, dice che la riga e'' DERIVATA (sulle righe di preventivo, ordine, bolla e contratto: sorgente_tipo_id); una colonna di esenzione che la riga non ha = E_TRIGGER_ARGOMENTI_INVALIDI. Il guard calcola dalla riga la SCELTA NUOVA e la passa alla check (p_scelta_nuova): INSERT senza esenzione, o UPDATE con articolo o documento padre cambiati (riscrivere lo stesso valore non conta). Solo sulla scelta nuova conta il motivo OBSOLETO (E_ARTICOLO_OBSOLETO). Su preventivo, ordine e bolla e'' montato DOPO script.trgfn_righe_natura_vendita (_a10_natura_vendita < _a10_regole_articolo); su offerta e contratto PRIMA dei guard di riga (_a10_guard_articolo_ammesso < _a10_guard_erogazione_*): prima i motivi dell''articolo, poi quelli della riga; sulla promo prima del guard delle date (_a10_guard_articolo_ammesso < _a10_guard_data_driven). La riconsegna e'' esente: con la porta zeroerp.ddt_riconsegna = id del reso, accesa da vendite.fn_genera_ddt_riconsegna, una riga di bolla passa se il suo articolo e'' fra le righe di quel reso; la porta e'' stretta sugli articoli del reso perche'' il verbo e'' SECURITY INVOKER. La distinta ha il suo guard (catalogo.trgfn_articoli_componenti_guard_componente). Il picker catalogo.fn_articoli_ammessi da'' lo stesso motivo prima della scelta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
