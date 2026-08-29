{% include-markdown "it/dbzero/script/manual/fn_check_ba_cambio_emittente.md" %}
# ⚙️ Funzione `fn_check_ba_cambio_emittente`

```sql
CREATE FUNCTION fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi    jsonb := '[]'::jsonb;
    v_storia    record;
    v_codice_ba anagrafiche.billing_account.codice%TYPE;
    v_codice_ef anagrafiche.emittenti_fiscali.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di togliere o cambiare
    --   una riga di anagrafiche.emittenti_fiscali_billing_account.
    --   Funzione PURA (fn_check_*): nessun raise, nessuna
    --   scrittura. Consumatori: la madre
    --   anagrafiche.fn_guard_ba_cambio_emittente (solleva il
    --   primo motivo) e la lista dei mapping nel drawer
    --   dell'emittente (spegne il cestino di riga).
    --
    -- Ritorna: [] se ammesso; altrimenti array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori} — §12.5.1.
    -- ⚠️ L'ordine e' il contratto: la madre solleva il PRIMO.
    --
    -- ⭐ UNA sola funzione per entrambe le specie di riga (il
    --   mapping specifico e il gestore globale), e non e'
    --   pigrizia: il frontend chiama UNA cosa per riga. Con due
    --   check sarebbe il chiamante a dover dedurre «che tipo di
    --   riga e' questa», cioe' a ricalcolare fuori sede una cosa
    --   che qui e' un IF.
    -- =========================================================

    -- 1) ⭐ LA RIGA DEL GESTORE GLOBALE (billing_account_id NULL).
    --    Prima tornava `[]` — «non e' il mio caso» — e il cestino
    --    restava acceso proprio sulla riga che il repository
    --    tiene IN TESTA (ORDER BY is_default DESC).
    --    ⛔ Quella riga non si toglie MAI: il singleton di
    --    anagrafiche.trgfn_emittenti_fiscali_default_guard
    --    pretende esattamente un default, e cancellarla porta il
    --    conteggio a zero. La risposta e' INCONDIZIONATA — non
    --    dipende dalla storia — ed e' il motivo per cui qui NON
    --    si e' scritta la gemella del guard raggio N: avrebbe
    --    dato un motivo condizionale, suggerendo che senza storia
    --    la riga si potrebbe togliere.
    --    ⚠️ Questo motivo serve alla RIGA, non al raise: a
    --    rifiutare e' il guard singleton, che compone la propria
    --    frase. I `valori` portano il conteggio che RISULTEREBBE.
    IF p_billing_account_id IS NULL THEN
        RETURN v_motivi || jsonb_build_object(
            'codice',     'E_EMITTENTE_DEFAULT_SINGLETON',
            'reason',     'DEFAULT_SINGLETON',
            'reason_key', 'amministrazione.emittenti_fiscali.ba_blocco.default_singleton',
            'dettaglio',  jsonb_build_object(
                              'is_default',         true,
                              'emittente_sr_prima', p_emittente_sr_prima),
            'valori',     jsonb_build_array('0'));
    END IF;

    -- 2) ⛔ LA META' DEL PREDICATO CHE SI DIMENTICA.
    --    Se l'emittente non cambia DAVVERO non c'e' niente da
    --    presidiare: togliere un mapping specifico quando il
    --    gestore globale punta allo stesso emittente non sposta
    --    nessun documento, ed e' manutenzione ordinaria.
    IF p_emittente_sr_prima IS NOT DISTINCT FROM p_emittente_sr_dopo THEN
        RETURN v_motivi;
    END IF;

    SELECT * INTO v_storia
      FROM anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id);

    -- 3) Nessuna storia: la finestra di correzione e' aperta.
    IF COALESCE(v_storia.n_fatture, 0) = 0
       AND COALESCE(v_storia.n_commesse, 0) = 0 THEN
        RETURN v_motivi;
    END IF;

    SELECT ba.codice INTO v_codice_ba
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;

    -- ⭐ L'emittente si nomina per CODICE: il canale VARIADIC
    --    compone la frase che legge una PERSONA.
    SELECT ef.codice INTO v_codice_ef
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = p_emittente_sr_prima;

    v_motivi := v_motivi || jsonb_build_object(
        'codice',     'E_BA_EMITTENTE_CON_STORIA',
        'reason',     'BA_CON_STORIA',
        'reason_key', 'amministrazione.emittenti_fiscali.ba_blocco.con_storia',
        'dettaglio',  jsonb_build_object(
                          'billing_account_id', p_billing_account_id,
                          'codice',             v_codice_ba,
                          'n_fatture',          v_storia.n_fatture,
                          'n_commesse',         v_storia.n_commesse,
                          'emittente_sr_prima', p_emittente_sr_prima,
                          'emittente_sr_dopo',  p_emittente_sr_dopo),
        'valori',     jsonb_build_array(
                          COALESCE(v_codice_ba, p_billing_account_id::text),
                          v_storia.n_fatture::text,
                          v_storia.n_commesse::text,
                          COALESCE(v_codice_ef, p_emittente_sr_prima::text)));

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
IS 'Pure check (§12.5.1): elenca i motivi che impediscono di togliere o cambiare una riga di anagrafiche.emittenti_fiscali_billing_account. [] = ammesso; altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva. ⭐ rev 2026-08-27 (N7): risponde anche per la RIGA DEL GESTORE GLOBALE (billing_account_id NULL), che prima cadeva su un «non e'' il mio caso» e lasciava il cestino ACCESO — proprio sulla riga che il repository tiene in testa (ORDER BY is_default DESC), cioe'' la prima che l''operatore vede. ⛔ E la causa NON e'' il guard raggio N, come sembrava: a rifiutare quella cancellazione e'' prima di tutto anagrafiche.trgfn_emittenti_fiscali_default_guard, che impone il SINGLETON — quella riga non si toglie MAI, con o senza storia. Per questo NON si e'' scritta la gemella fn_check_* del raggio N: avrebbe prodotto un motivo CONDIZIONALE dove la risposta e'' incondizionata, suggerendo che senza storia la riga si potrebbe togliere — e un tooltip che dichiara una condizione inesistente manda a cercare come soddisfarla. ⚠️ Il motivo del singleton serve alla RIGA, non al raise: chi rifiuta davvero e'' il guard singleton, che compone la propria frase; i `valori` portano il conteggio che RISULTEREBBE (0). ⚠️ Il guard raggio N (anagrafiche.fn_guard_ba_gestore_globale_storia) resta necessario e non e'' coperto da qui: presidia il CAMBIO dell''emittente del gestore globale — un UPDATE, o un DELETE seguito da un INSERT — non la cancellazione secca. ⭐ UNA sola funzione per entrambe le specie di riga: il frontend chiama una cosa per riga, e con due check sarebbe il chiamante a dover dedurre in Python «che tipo di riga e'' questa», cioe'' a ricalcolare fuori sede cio'' che qui e'' un IF. ⛔ IL PREDICATO DEL MAPPING SPECIFICO E'' UNA COPPIA: togliere l''aggancio fa ricadere il billing account sul gestore globale, quindi il cambio esiste solo se l''emittente della riga e'' DIVERSO da quello del default — se coincidono non si sposta nessun documento e la rimozione resta ammessa. ⚠️ SECURITY DEFINER: la storia si conta su tabelle con la RLS. ⚠️ Nessun codice errore nuovo. Piano: brief-db-motivo-rimozione-mapping-ba, N1 e N7.';
```

---
{% include-markdown "signature-core.md" %}
