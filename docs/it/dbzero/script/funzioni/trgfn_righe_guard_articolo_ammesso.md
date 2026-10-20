{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso.md" %}
# ⚙️ Funzione `trgfn_righe_guard_articolo_ammesso`

```sql
CREATE FUNCTION trgfn_righe_guard_articolo_ammesso()
```

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
    v_riga         jsonb  := to_jsonb(NEW);
    v_documento_id bigint := (to_jsonb(NEW) ->> TG_ARGV[1])::bigint;
    v_porta        text   := COALESCE(current_setting('zeroerp.ddt_riconsegna', true), '');
    v_motivi       jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare una riga il cui articolo il documento non
    --   ammette: solleva il primo motivo di
    --   script.fn_check_articolo_riga. BEFORE INSERT OR UPDATE
    --   OF articolo_id.
    -- =========================================================

    -- La riconsegna (A-6): solo dal verbo, e solo per un articolo
    -- che sta fra le righe del reso che si riconsegna.
    IF v_documento = 'DDT_VENDITA' AND v_porta ~ '^[0-9]+$'
       AND EXISTS (SELECT 1 FROM vendite.resi_righe rr
                    WHERE rr.reso_id = v_porta::bigint
                      AND rr.articolo_id = NEW.articolo_id) THEN
        RETURN NEW;
    END IF;

    -- Natura (preventivo, ordine, bolla) e tipo d'eccezione (offerta,
    -- contratto): ognuna c'e' solo sulle sue tabelle.
    v_motivi := script.fn_check_articolo_riga(
        v_documento, v_documento_id, NEW.articolo_id,
        (v_riga ->> 'natura_vendita_id')::bigint,
        (v_riga ->> 'tipo_eccezione')::vendite.tipo_eccezione_contratto);

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
IS 'BB guard BEFORE INSERT OR UPDATE OF articolo_id sulle righe che scelgono un articolo: vendite.preventivi_righe, vendite.ordini_righe, vendite.ddt_righe; dal 20261013-57 vendite.offerte_commerciali_eccezioni e vendite.contratti_righe; dal 20261013-61 vendite.listini_righe (LISTINO_VERSIONE, anche UPDATE OF listino_versione_id); dal 20261014-05 vendite.promo_articoli (PROMO_ARTICOLO, TG_ARGV[1] = id: la promo non ha un padre). Solleva il primo motivo di script.fn_check_articolo_riga (il predicato sta nella check: linee-guida-sql §12.5.2), passando la natura della riga e il suo tipo d''eccezione, letti da to_jsonb(NEW) (ognuno c''e'' solo sulle sue tabelle). Campo: quello del primo motivo, o articolo_id. TG_ARGV[0]: documento (codice di config.tipi_entita); TG_ARGV[1]: colonna del padre. Su preventivo, ordine e bolla e'' montato DOPO script.trgfn_righe_natura_vendita (_a10_natura_vendita < _a10_regole_articolo); su offerta e contratto PRIMA dei guard di riga (_a10_guard_articolo_ammesso < _a10_guard_erogazione_*): prima i motivi dell''articolo, poi quelli della riga; sulla promo prima del guard delle date (_a10_guard_articolo_ammesso < _a10_guard_data_driven). La riconsegna e'' esente (A-6): con la porta zeroerp.ddt_riconsegna = id del reso, accesa da vendite.fn_genera_ddt_riconsegna, una riga di bolla passa se il suo articolo e'' fra le righe di quel reso; la porta e'' stretta sugli articoli del reso perche'' il verbo e'' SECURITY INVOKER. La distinta ha il suo guard (catalogo.trgfn_articoli_componenti_guard_componente: padre uuid). Il picker catalogo.fn_articoli_ammessi da'' lo stesso motivo prima della scelta. Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, A-6, D-6; §9.3.3, §9.4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
