{% include-markdown "it/dbzero/vendite/manual/fn_get_pavimento_sequenza.md" %}
# ⚙️ Funzione `fn_get_pavimento_sequenza`

```sql
CREATE FUNCTION fn_get_pavimento_sequenza(p_registro_id bigint, p_serie character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pavimento_sequenza(p_registro_id bigint, p_serie character varying)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_serie      vendite.fatture.serie%TYPE;
    v_pavimento  vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Da quale data in poi questo sezionale accetta un numero,
    --   guardando SOLO la sequenza gia' emessa.
    --   NULL = nessun pavimento (non e' ancora uscito niente).
    --
    -- Regole:
    --   - si legge il CONTATORE, non le fatture: il contatore non
    --     ha RLS e la risposta e' sempre completa;
    --   - il massimo si prende ATTRAVERSO GLI ANNI, come fa il
    --     cancello.
    -- =========================================================

    IF p_registro_id IS NULL OR p_registro_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_sequenza',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'registro_id obbligatorio e maggiore di zero',
                'p_registro_id', p_registro_id),
            NULL::uuid,
            'vendite.fn_get_pavimento_sequenza',
            'p_registro_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⭐ Serie NULL = quella del registro. E' la RISOLUZIONE a
    --    essere ammessa, non l'omissione: il parametro non ha
    --    default, cosi' chi chiama deve decidere cosa passare.
    -- ⚠️ La stessa risoluzione, COALESCE(serie, serie_default,''),
    --    la usano chi numera e il backfill del contatore: se una
    --    delle tre divergesse, cercherebbe una riga di contatore
    --    che non esiste e risponderebbe «nessun vincolo».
    SELECT COALESCE(p_serie, r.serie_default, '')
      INTO v_serie
      FROM vendite.registri_fatturazione r
     WHERE r.id = p_registro_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_pavimento_sequenza',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('registro_id', p_registro_id),
            NULL::uuid,
            concat('registro di fatturazione ', p_registro_id, ' inesistente'));
    END IF;

    SELECT max(rp.ultima_data)
      INTO v_pavimento
      FROM vendite.registri_fatturazione_progressivi rp
     WHERE rp.registro_id = p_registro_id
       AND rp.serie       = v_serie;

    RETURN v_pavimento;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_pavimento_sequenza(p_registro_id bigint, p_serie character varying)
IS 'Da quale data in poi questo sezionale (registro + serie) accetta un numero, guardando SOLO LA SEQUENZA gia'' emessa. NULL = nessun pavimento: da quella sequenza non e'' ancora uscito niente, qualunque data va bene. ⛔ NON e'' «la data minima numerabile»: quella e'' la COMPOSIZIONE con il limite di emissione, e la fa vendite.fn_get_pavimento_data_documento. Questa e'' una delle due primitive, e il nome lo dice — fino al 2026-08-26 si chiamava fn_get_data_minima_numerabile, ed era un nome che sarebbe diventato falso nel momento in cui il secondo pavimento e'' nato. ⚠️ LA SERIE SI RISOLVE COME LA RISOLVE CHI NUMERA: COALESCE(p_serie, r.serie_default, ''''). Misurato il 2026-08-25: tutte le fatture non numerate hanno serie NULL e la prendono dal serie_default, quindi un COALESCE(serie,'''') cercherebbe il contatore della serie vuota, non lo troverebbe e risponderebbe NULL — la risposta piu'' permissiva possibile proprio dove il cancello rifiuta. ⛔ p_serie NON ha DEFAULT, al contrario della versione vecchia: da primitiva interna, dimenticare la serie significa leggere il contatore di un''ALTRA sequenza. NULL resta un valore legittimo e significa «la serie di default del registro» — e'' la risoluzione a essere ammessa, non l''omissione. ℹ️ Si legge il CONTATORE e non vendite.fatture: il contatore non ha RLS, quindi la risposta e'' completa per chiunque; e il massimo si prende ATTRAVERSO GLI ANNI, come fa il cancello — altrimenti un documento retrodatato al 31/12 dell''anno scorso passerebbe indisturbato. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
