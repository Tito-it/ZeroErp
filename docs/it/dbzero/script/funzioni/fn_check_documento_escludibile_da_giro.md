{% include-markdown "it/dbzero/script/manual/fn_check_documento_escludibile_da_giro.md" %}
# ⚙️ Funzione `fn_check_documento_escludibile_da_giro`

```sql
CREATE FUNCTION fn_check_documento_escludibile_da_giro(p_lotto_id bigint, p_gruppo_key text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_documento_escludibile_da_giro(p_lotto_id bigint, p_gruppo_key text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di togliere UN documento
--        dal giro di fatturazione. Funzione PURA (fn_check_*):
--        nessun raise di dominio, nessuna scrittura.
-- Consumatori: vendite.fn_escludi_documento_da_giro (solleva il
--        codice del PRIMO motivo) e il frontend, per spiegare
--        invece di far fallire.
-- Ritorna: [] se il documento si puo' togliere; altrimenti array
--        ORDINATO di {codice, reason, reason_key, dettaglio}.
DECLARE
    v_motivi        jsonb := '[]'::jsonb;
    v_lotto_trovato boolean;
    v_lotto_stato   vendite.vw_lotti_fase.stato_codice_interno%TYPE;
    -- ⭐ rev 2026-09-09: il derivato gia' fail-closed della sede unica.
    v_lotto_pre_fiscale vendite.vw_lotti_fase.pre_fiscale%TYPE;
    v_esito         vendite.fatturazione_lotti_esiti.stato_esecuzione%TYPE;
BEGIN
    -- Guard parametri: id assenti o non validi sono errori di
    -- programmazione, non condizioni di dominio.
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_documento_escludibile_da_giro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio (> 0)');
    END IF;

    IF COALESCE(btrim(p_gruppo_key), '') = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_documento_escludibile_da_giro', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_gruppo_key', 'valore', p_gruppo_key),
            NULL::uuid, 'p_gruppo_key obbligatorio');
    END IF;

    -- Stato del LOTTO per codice_interno: la chiave stabile e' quella,
    -- l'id no.
    -- ⭐ rev 2026-09-09 — dalla sede unica vendite.vw_lotti_fase, che fa la
    --   stessa LEFT JOIN di prima: un lotto senza stato risolvibile ha
    --   comunque la sua riga e arriva al confronto, non sparisce.
    -- ⭐ E QUESTA E' LA PORTA D'USCITA: `pre_fiscale` e' lo stesso predicato
    --   con cui vendite.vw_documenti_trattenuti_da_lotto dice «trattenuto».
    --   Trattenuto ⇔ si puo' ancora uscire: se non fossero lo stesso flag, un
    --   documento potrebbe risultare trattenuto senza avere piu' una via
    --   d'uscita — un cancello senza chiave.
    SELECT true, f.stato_codice_interno, f.pre_fiscale
      INTO v_lotto_trovato, v_lotto_stato, v_lotto_pre_fiscale
      FROM vendite.vw_lotti_fase f
     WHERE f.lotto_id = p_lotto_id;

    IF NOT COALESCE(v_lotto_trovato, false) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_documento_escludibile_da_giro', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- MOTIVO 1 — il LOTTO e' oltre il pre-fiscale.
    -- ⚠️ Fail-closed: con lo stato non risolvibile si blocca, come
    --    fa la sorella. Non sapere in che stato e' il giro non e'
    --    un buon motivo per lasciarci mettere le mani.
    -- ⚠️ Il fail-closed non e' sparito: sta dentro `pre_fiscale`, che su uno
    --    stato non risolvibile vale FALSE. Stesso esito di prima.
    IF NOT v_lotto_pre_fiscale THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_LOTTO_NON_PRE_FISCALE',
            'reason',     'STATO_LOTTO_NON_PRE_FISCALE',
            'reason_key', 'vendite.lotti.azione_reason.lotto_non_pre_fiscale',
            'dettaglio',  COALESCE(v_lotto_stato, '-'),
            -- ⭐ «Il lotto e' oltre lo stato pre-fiscale (stato attuale: %s)»:
            --   ci va lo STATO. Fino al 2026-09-09 la madre passava per primo
            --   p_gruppo_key — giusto per i motivi 2-4, che cominciano con «Il
            --   documento %s», e a video usciva il gruppo al posto dello stato.
            --   Arita' giusta, frase falsa: nessun cancello lo vedeva.
            'valori',     jsonb_build_array(COALESCE(v_lotto_stato, '-')));
    END IF;

    SELECT e.stato_esecuzione
      INTO v_esito
      FROM vendite.fatturazione_lotti_esiti e
     WHERE e.lotto_id = p_lotto_id
       AND e.gruppo_key = p_gruppo_key;

    -- MOTIVO 2 — il documento non e' fra gli esiti di questo lotto.
    -- ⚠️ Precede i due seguenti per costruzione: senza la riga non
    --    si puo' parlare del suo stato.
    IF v_esito IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_LOTTO_DOC_SENZA_ESITO',
            'reason',     'SENZA_ESITO',
            'reason_key', 'vendite.lotti.azione_reason.documento_senza_esito',
            'dettaglio',  p_gruppo_key,
            'valori',     jsonb_build_array(p_gruppo_key));

    -- MOTIVO 3 — e' gia' uscito.
    -- ⚠️ PRECEDE il motivo 4, e la precedenza e' portante: un
    --    documento ESCLUSO e' ANCHE «non in errore», quindi senza
    --    questo ramo scatterebbero tutti e due e la madre
    --    solleverebbe quello sbagliato.
    ELSIF v_esito = 'ESCLUSO' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_LOTTO_DOC_GIA_USCITO',
            'reason',     'GIA_USCITO',
            'reason_key', 'vendite.lotti.azione_reason.documento_gia_uscito',
            'dettaglio',  p_gruppo_key,
            'valori',     jsonb_build_array(p_gruppo_key));

    -- MOTIVO 4 — non e' in errore (D-4): dal giro si tolgono solo i
    -- documenti che hanno fallito.
    ELSIF v_esito <> 'ERRORE' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_LOTTO_DOC_NON_IN_ERRORE',
            'reason',     'DOCUMENTO_NON_IN_ERRORE',
            'reason_key', 'vendite.lotti.azione_reason.documento_non_in_errore',
            'dettaglio',  v_esito,
            'valori',     jsonb_build_array(p_gruppo_key, v_esito));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_documento_escludibile_da_giro(p_lotto_id bigint, p_gruppo_key text)
IS 'I motivi che impediscono di togliere UN documento dal giro di fatturazione: [] se si puo'', altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio}. ⭐ SEDE UNICA del predicato: vendite.fn_escludi_documento_da_giro la CHIAMA e solleva il codice del primo motivo, il frontend legge lo stesso elenco per spegnere il pulsante col perche'' — cosi'' tooltip e rifiuto non possono divergere. ⚠️ L''ORDINE e'' il contratto (la madre solleva il primo): lotto, poi assenza di esito, poi «gia'' uscito», poi «non in errore». La terza precede la quarta perche'' un documento ESCLUSO e'' ANCHE non-in-errore, e senza precedenza scatterebbero entrambe. ⭐ Riusa E_LOTTO_NON_PRE_FISCALE e la sua chiave i18n dalla sorella fn_check_fattura_eliminabile_da_lotto: stessa condizione, stesso rimedio, un codice solo. Il confine pre-fiscale arriva dal derivato pre_fiscale di vendite.vw_lotti_fase (rev 2026-09-09, sede unica della fase di un lotto), gia'' fail-closed: mai un elenco di stati scritto a mano, e mai la COALESCE ricopiata qui. ⭐ E'' lo STESSO flag con cui vw_documenti_trattenuti_da_lotto dice «trattenuto»: trattenuto ⇔ si puo'' ancora uscire. ⛔ La bozza CONDIVISA non e'' un motivo: e'' una conseguenza (D-2b), la dichiara script.fn_gruppi_trascinati_da_uscita e la nomina la conferma. Brief: brief-db-uscita-documento-dal-giro §5.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
