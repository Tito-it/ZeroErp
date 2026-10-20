{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_documento.md" %}
# ⚙️ Funzione `fn_get_registro_documento`

```sql
CREATE FUNCTION fn_get_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer DEFAULT NULL::integer)
 RETURNS TABLE(registro_id bigint, serie character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_registro vendite.registri_fatturazione.id%TYPE;
    v_serie    vendite.registri_fatturazione.serie_default%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il registro su cui numerare un documento di questa
    --   famiglia — e SOLLEVA se non e' risolvibile.
    --   E' l'involucro di vendite.fn_lookup_registro_documento:
    --   qui passa chi SCRIVE.
    -- =========================================================

    -- ⛔ LA FATTURA NON SI RISOLVE DI QUI.
    --   Il suo registro dipende da (tipo documento, natura) e lo
    --   sceglie vendite.fn_get_registro_id. Rispondere qui
    --   darebbe il PRIMO registro di fatturazione
    --   dell'emittente: plausibile, e sbagliato per una nota di
    --   credito — in silenzio.
    -- ⚠️ TECNICO e non DATO_ERRATO: a questa chiamata non arriva
    --   nessuna persona in un form, ci arriva un chiamante
    --   scritto male. Niente `campo` nel contesto: su un 500 non
    --   c'e' nessun campo da accendere.
    IF p_famiglia_documento = 'FATTURA' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_registro_documento',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'la famiglia FATTURA si risolve con vendite.fn_get_registro_id (tipo documento + natura)',
                'p_famiglia_documento', p_famiglia_documento),
            NULL::uuid,
            'vendite.fn_get_registro_documento',
            'p_famiglia_documento (FATTURA non si risolve di qui)');
    END IF;

    -- Guard di parametro: un emittente nullo non esce da nessuna
    -- interfaccia — lo produce solo un chiamante rotto.
    IF p_emittente_soggetto_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_registro_documento',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'emittente obbligatorio',
                'p_famiglia_documento', p_famiglia_documento),
            NULL::uuid,
            'vendite.fn_get_registro_documento',
            'p_emittente_soggetto_ruolo_id (obbligatorio)');
    END IF;

    SELECT k.registro_id, k.serie
      INTO v_registro, v_serie
      FROM vendite.fn_lookup_registro_documento(
               p_famiglia_documento          => p_famiglia_documento,
               p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
               p_utility_id                  => p_utility_id) k;

    -- ⚠️ FAIL-CLOSED, ed e' nuovo: prima del trasloco il
    --   documento nasceva comunque, su un registro qualsiasi.
    --   Meglio fermarsi che numerare sul sezionale di un altro.
    IF v_registro IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_registro_documento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'famiglia_documento',           p_famiglia_documento,
                'emittente_soggetto_ruolo_id',  p_emittente_soggetto_ruolo_id,
                'utility_id',                   p_utility_id),
            NULL::uuid,
            concat('registro di numerazione non configurato per la famiglia ',
                   p_famiglia_documento, ' di questo emittente'));
    END IF;

    RETURN QUERY SELECT v_registro, v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'Il registro su cui numerare un documento di una data FAMIGLIA (DDT, ORDINE, COMMESSA, RESO) — e SOLLEVA se non e'' risolvibile. E'' l''INVOLUCRO di vendite.fn_lookup_registro_documento, ed e'' la stessa coppia, con la stessa ragione, di vendite.fn_lookup_registro_id / vendite.fn_get_registro_id: chi LEGGE (viste, previsioni) consuma il lettore, che risponde NULL e non fa morire la lista che decora; chi SCRIVE consuma questo, dove un buco di configurazione DEVE fermare — altrimenti il documento nasce senza numero e il difetto si scopre a valle. ⛔ RIFIUTA la famiglia FATTURA, ed e'' la riga che vale: il registro della fattura dipende da (tipo documento, natura) e lo sceglie vendite.fn_get_registro_id attraverso vendite.tipi_doc_fiscale_registri. Rispondere qui darebbe il PRIMO registro di fatturazione dell''emittente — una risposta plausibile e sbagliata, che per una nota di credito e'' il sezionale sbagliato, in silenzio. ⚠️ Il codice e'' TECNICO (E_VENDITE_CHIAMATA_NON_VALIDA) e non DATO_ERRATO: a questa chiamata non arriva nessuna persona in un form, ci arriva un chiamante scritto male — quindi niente chiave `campo` nel contesto, perche'' su un 500 non c''e'' nessun campo da accendere. ⚠️ IL FAIL-CLOSED E'' NUOVO e va saputo: da qui in poi un emittente senza registro per la sua famiglia NON EMETTE quel documento, mentre prima del trasloco il documento nasceva comunque su un registro qualsiasi. E'' il verso giusto, ma il passo C2-12 del piano — una riga di registro per emittente e famiglia — va fatto PRIMA di accendere i generatori nuovi. ℹ️ Nessun codice errore nuovo: E_CONFIG_MANCANTE e E_VENDITE_CHIAMATA_NON_VALIDA sono gia'' a catalogo e sono esattamente i due che fn_get_registro_id usa per gli stessi due casi — un codice nuovo qui sarebbe un sinonimo, e i sinonimi si cercano due volte nei log. ℹ️ VOLATILE per il log dell''errore, a differenza del lettore che e'' STABLE. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
