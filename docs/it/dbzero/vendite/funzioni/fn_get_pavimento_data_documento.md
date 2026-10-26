{% include-markdown "it/dbzero/vendite/manual/fn_get_pavimento_data_documento.md" %}
# ⚙️ Funzione `fn_get_pavimento_data_documento`

```sql
CREATE FUNCTION fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
 RETURNS TABLE(pavimento date, origine text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_seq      vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    v_emi      vendite.fatture.data%TYPE;
    v_famiglia vendite.registri_fatturazione.famiglia_documento%TYPE;
    v_presidia vendite.famiglie_documento.presidia_data_documento%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il pavimento EFFETTIVO della data di un documento — il
    --   maggiore fra quello della sequenza e quello del limite
    --   di emissione — e QUALE dei due ha vinto.
    --
    -- Regole:
    --   - una sede sola: nascita, targa e cancello leggono qui;
    --   - `pavimento` e' sempre il maggiore, mai quello di
    --     `origine`;
    --   - il pareggio va a SEQUENZA;
    --   - ⭐ il LIMITE DI EMISSIONE vale sulla sola FATTURA
    --     (20260831-05);
    --   - ⭐ il pavimento di SEQUENZA vale sulle famiglie che
    --     presidiano la data (20260831-12).
    -- =========================================================

    -- ⭐ Famiglia e flag in una lettura sola: la tabella delle
    --   famiglie ha cinque righe e il registro lo si stava gia'
    --   interrogando.
    SELECT r.famiglia_documento, fd.presidia_data_documento
      INTO v_famiglia, v_presidia
      FROM vendite.registri_fatturazione r
      LEFT JOIN vendite.famiglie_documento fd
             ON fd.codice_interno = r.famiglia_documento
     WHERE r.id = p_registro_id;

    -- ⛔ CHI NON PRESIDIA NON HA PAVIMENTO DI SEQUENZA.
    --   L'ordine si numera all'INSERT: il numero esce quando
    --   qualcuno crea la riga, e rifiutare un ordine datato
    --   indietro sarebbe un comportamento nuovo.
    -- ⚠️ COALESCE a TRUE: se la famiglia non fosse a catalogo,
    --   si presidia — il verso prudente e' quello che rifiuta,
    --   non quello che lascia passare.
    IF COALESCE(v_presidia, TRUE) THEN
        v_seq := vendite.fn_get_pavimento_sequenza(p_registro_id, p_serie);
    ELSE
        v_seq := NULL;
    END IF;

    -- ⭐ IL LIMITE DI EMISSIONE VALE SULLA SOLA FATTURA, e non
    --   si spegne da solo: fn_get_pavimento_emissione «torna
    --   SEMPRE una data, mai NULL» e senza override legge i
    --   giorni da config.parameters.
    IF v_famiglia = 'FATTURA' THEN
        v_emi := vendite.fn_get_pavimento_emissione(p_registro_id, p_competenza_mese);
    ELSE
        v_emi := NULL;
    END IF;

    -- ⚠️ GREATEST IGNORA I NULL (torna NULL solo se lo sono
    --    tutti). Nessun COALESCE difensivo.
    RETURN QUERY
    SELECT GREATEST(v_seq, v_emi),
           CASE
               WHEN v_seq IS NOT NULL
                    AND (v_emi IS NULL OR v_seq >= v_emi) THEN 'SEQUENZA'::text
               WHEN v_emi IS NOT NULL                     THEN 'EMISSIONE'::text
               ELSE NULL::text
           END;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
IS 'Il pavimento EFFETTIVO della data di un documento — il maggiore fra il pavimento della SEQUENZA e quello del LIMITE DI EMISSIONE — e quale dei due ha vinto. ⛔ E'' LA SEDE UNICA: la usano la nascita del documento (fn_calcola_data_documento), la targa del dialog (fn_get_pavimento_lotto) e il cancello (fn_get_next_progressivo). ⭐ DUE PERIMETRI, imparati a due giorni di distanza e finiti entrambi QUI per la stessa ragione. (1) rev 2026-08-31 / 20260831-05: il LIMITE DI EMISSIONE vale sulla sola famiglia FATTURA — risponde a «questo documento e'' ancora emettibile?», che e'' una regola della fattura differita, e ⛔ NON si spegne da solo, perche'' vendite.fn_get_pavimento_emissione «torna SEMPRE una data, mai NULL» e senza override sul registro legge i giorni da config.parameters (misurato: su un registro DDT il pavimento era 2026-08-19, attivo). (2) rev 2026-08-31 / 20260831-12: il pavimento di SEQUENZA vale sulle famiglie con vendite.famiglie_documento.presidia_data_documento = true. Non lo e'' l''ORDINE, che si numera all''INSERT: il numero esce quando qualcuno crea la riga, e rifiutare un ordine datato indietro rispetto all''ultimo creato sarebbe un comportamento NUOVO, fuori dal perimetro del cantiere. ℹ️ La COMMESSA si numera anch''essa all''INSERT ma presidia lo stesso, e non e'' una svista: la sua data e'' quella di CREAZIONE, quindi e'' sempre oggi e il pavimento non puo'' morderla — presidiare le costa niente e resta vero se un domani quella data cambiasse natura. ⚠️ Entrambe le distinzioni stanno QUI e non nel cancello proprio perche'' questa e'' la sede unica: scritte nel solo cancello, la nascita e la targa continuerebbero a proporre e a mostrare un pavimento che nessuno applica — tre risposte diverse alla stessa domanda. ⚠️ La FIRMA non e'' cambiata in nessuna delle due revisioni: famiglia e flag si leggono dal registro, che la funzione gia'' identifica con p_registro_id. ⚠️ COALESCE del flag a TRUE: se una famiglia non fosse a catalogo si presidia comunque — il verso prudente e'' quello che rifiuta, non quello che lascia passare. ⭐ `pavimento` e'' SEMPRE quello EFFETTIVO, mai quello di `origine`. ⚠️ Il PAREGGIO VA A SEQUENZA: a parita'' di data la sua frase puo'' portare un BERSAGLIO. ℹ️ GREATEST ignora i NULL, e sulle famiglie senza pavimenti «entrambi NULL» e'' il caso normale. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-4, rivisto da brief-db-registri-di-numerazione-emittente-e-trasloco C2-6 e C2-9.';
```

</div>

---
{% include-markdown "signature-core.md" %}
