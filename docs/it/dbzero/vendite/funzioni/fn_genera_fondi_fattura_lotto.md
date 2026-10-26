{% include-markdown "it/dbzero/vendite/manual/fn_genera_fondi_fattura_lotto.md" %}
# ⚙️ Funzione `fn_genera_fondi_fattura_lotto`

```sql
CREATE FUNCTION fn_genera_fondi_fattura_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_fondi_fattura_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
 RETURNS TABLE(fatture_count integer, chiavi_count integer, fondi_creati integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_id vendite.tipi_fondi_fattura.id%TYPE;
    v_fatture INTEGER := 0;
    v_chiavi  INTEGER := 0;
    v_creati  INTEGER := 0;
BEGIN
    -- ===== Guard parametri =====
    -- ⚠️ p_lotto_id lo verifica anche fn_get_scope_fatture_lotto,
    --    ma il tipo di fondo no: senza questo guard un NULL
    --    arriverebbe fino alla generazione, che lo rifiuterebbe
    --    con il nome di un'altra funzione nel log.
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_fondi_fattura_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_tipo_fondo_codice_interno IS NULL OR btrim(p_tipo_fondo_codice_interno) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_fondi_fattura_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_codice_interno', 'valore', p_tipo_fondo_codice_interno),
            NULL::uuid, 'p_tipo_fondo_codice_interno obbligatorio e non vuoto');
    END IF;

    -- ===== Il tipo di fondo: si risolve QUI =====
    -- ⭐ La firma prende il CODICE INTERNO e non l'id perche' e'
    --    cio' che arriva dalla configurazione del task
    --    (`tipo_fondo_codice_interno`, una stringa). Con l'id il
    --    backend dovrebbe fare prima una query di lookup, e
    --    «una SELECT per task» — che e' il senso di R-3 — non si
    --    otterrebbe.
    SELECT t.id INTO v_tipo_id
      FROM vendite.tipi_fondi_fattura t
     WHERE t.codice_interno = p_tipo_fondo_codice_interno
       AND t.attivo IS TRUE
     ORDER BY t.id
     LIMIT 1;

    IF v_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_fondi_fattura_lotto', 'E_TIPO_FONDO_NOT_FOUND',
            jsonb_build_object('codice_interno', p_tipo_fondo_codice_interno),
            NULL::uuid, p_tipo_fondo_codice_interno);
    END IF;

    -- =========================================================
    -- Lo scope si legge UNA volta (la funzione e' STABLE ma
    -- costa un giro sulle tabelle del lotto), e da li' escono
    -- entrambi i conteggi e le chiavi distinte.
    --
    -- ⭐ DISTINCT sulla CHIAVE, senza l'id della fattura: la
    --    generazione lavora per chiave, e ripeterla per ogni
    --    fattura dello stesso emittente/utility/valuta significa
    --    riscandire le stesse sorgenti N volte per crearle una
    --    volta sola.
    -- =========================================================
    WITH scope AS (
        SELECT * FROM vendite.fn_get_scope_fatture_lotto(p_lotto_id)
    ), chiavi AS (
        SELECT DISTINCT
               s.billing_account_id,
               s.utility_id,
               s.tipo_doc_fiscale_id,
               s.emittente_soggetto_ruolo_id,
               s.valuta_id
          FROM scope s
    ), giro AS (
        SELECT vendite.fn_genera_fondi_fattura_source(
                   k.billing_account_id,
                   k.utility_id,
                   k.tipo_doc_fiscale_id,
                   k.emittente_soggetto_ruolo_id,
                   k.valuta_id,
                   v_tipo_id) AS creati
          FROM chiavi k
    )
    SELECT (SELECT count(*)::INTEGER FROM scope),
           (SELECT count(*)::INTEGER FROM chiavi),
           COALESCE((SELECT SUM(g.creati)::INTEGER FROM giro g), 0)
      INTO v_fatture, v_chiavi, v_creati;

    RETURN QUERY SELECT v_fatture, v_chiavi, v_creati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_fondi_fattura_lotto(p_lotto_id bigint, p_tipo_fondo_codice_interno character varying)
IS 'Madre DB del giro di generazione dei fondi per un lotto: risolve il tipo di fondo dal CODICE INTERNO, legge lo scope da vendite.fn_get_scope_fatture_lotto, ne estrae le CHIAVI DISTINTE e chiama fn_genera_fondi_fattura_source una volta per chiave. Ritorna fatture_count, chiavi_count e fondi_creati. ⭐ Prende il codice interno e NON l''id del tipo fondo perche'' e'' cio'' che arriva dalla configurazione del task (una stringa): con l''id il chiamante dovrebbe fare prima una query di lookup, e «una SELECT per task» — il senso di R-3 — non si otterrebbe. Nessun DEFAULT sul codice: il ripiego F_F_ADD_ACC lo risolve gia'' il chiamante, e un DEFAULT qui aprirebbe la strada all''ambiguita'' di overload. ⭐ Il backend passa da uno statement con venti righe di SQL dello scope in Python a una chiamata sola, e smette di conoscere la pseudo-chiave a cinque parametri: due cose di dominio che stavano in un repository. ⭐ E il giro gira una volta per CHIAVE e non per FATTURA — la query Python faceva SELECT DISTINCT con l''id della fattura in proiezione, quindi il DISTINCT non deduplicava nulla e su un lotto di 500 fatture dello stesso emittente la generazione riscandiva le stesse sorgenti 500 volte per crearle una volta (l''atto unico bloccava le altre 499). Non e'' un''ottimizzazione a posteriori: chi itera sulle fatture per passare una chiave sta iterando sull''oggetto sbagliato. ⚠️ Una funzione = uno statement = una transazione: il giro non puo'' restare a meta'' nemmeno se chiamato fuori dalla pipeline. ℹ️ NON decide se una fattura meriti un fondo — quello e'' fn_fondo_fattura_proponibile: questa porta soltanto il lotto fino alla chiave. R-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
