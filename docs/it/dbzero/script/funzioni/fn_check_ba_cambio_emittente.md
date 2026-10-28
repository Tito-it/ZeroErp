{% include-markdown "it/dbzero/script/manual/fn_check_ba_cambio_emittente.md" %}
# ⚙️ Funzione `fn_check_ba_cambio_emittente`

```sql
CREATE FUNCTION fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi    jsonb := '[]'::jsonb;
    v_codice_ba anagrafiche.billing_account.codice%TYPE;
    v_codice_ef anagrafiche.emittenti_fiscali.codice%TYPE;
    v_storia    jsonb;
    v_elenco    text;
    v_totale    bigint;
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
    -- ⭐ rev 2026-08-31 (C2-17): la storia non e' piu' «fatture e
    --   commesse», e' «qualunque documento gia' NUMERATO su un
    --   registro», derivata da vendite.famiglie_documento. La
    --   frase deve dire QUALE specie blocca: con cinque famiglie
    --   nominarne due manderebbe a cercare fatture a un cliente
    --   bloccato da un DDT.
    --
    -- ⭐ UNA sola funzione per entrambe le specie di riga (il
    --   mapping specifico e il gestore globale), e non e'
    --   pigrizia: il frontend chiama UNA cosa per riga. Con due
    --   check sarebbe il chiamante a dover dedurre «che tipo di
    --   riga e' questa», cioe' a ricalcolare fuori sede una cosa
    --   che qui e' un IF.
    -- =========================================================

    -- 1) ⭐ LA RIGA DEL GESTORE GLOBALE (billing_account_id NULL).
    --    Quella riga non si toglie MAI: il singleton di
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

    -- 3) ⭐ IL PERCORSO FELICE COSTA UN `EXISTS`.
    --    E' il ramo che la lista dei mapping attraversa a ogni
    --    caricamento, una volta per riga: qui si esce al PRIMO
    --    documento trovato, e i conteggi non si pagano.
    IF NOT anagrafiche.fn_ba_ha_storia_emittente(p_billing_account_id) THEN
        RETURN v_motivi;
    END IF;

    -- ── Da qui in giu' si e' gia' deciso di rifiutare: il
    --    prezzo dei conteggi si paga per comporre la frase.
    SELECT ba.codice INTO v_codice_ba
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;

    -- ⭐ L'emittente si nomina per CODICE: il canale VARIADIC
    --    compone la frase che legge una PERSONA.
    SELECT ef.codice INTO v_codice_ef
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = p_emittente_sr_prima;

    -- ⚠️ WITH ORDINALITY e non un ORDER BY sul codice: l'ordine
    --    e' quello del CATALOGO (la fattura per prima), e senza
    --    ordinalita' l'ordine di un string_agg su una function
    --    scan non e' garantito — la stessa frase cambierebbe di
    --    corsa in corsa.
    -- ⭐ Le parole dell'elenco sono le descrizioni del catalogo,
    --    non etichette ricopiate qui: una famiglia in piu' domani
    --    cambia la frase da se'.
    SELECT jsonb_agg(jsonb_build_object(
               'famiglia',    s.famiglia_documento,
               'descrizione', s.famiglia_descrizione,
               'n',           s.n_documenti) ORDER BY s.ord),
           string_agg(s.famiglia_descrizione || ': ' || s.n_documenti::text,
                      ', ' ORDER BY s.ord),
           sum(s.n_documenti)
      INTO v_storia, v_elenco, v_totale
      FROM anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id)
           WITH ORDINALITY AS s(famiglia_documento, famiglia_descrizione,
                                n_documenti, ord);

    v_motivi := v_motivi || jsonb_build_object(
        'codice',     'E_BA_EMITTENTE_CON_STORIA',
        'reason',     'BA_CON_STORIA',
        'reason_key', 'amministrazione.emittenti_fiscali.ba_blocco.con_storia',
        'dettaglio',  jsonb_build_object(
                          'billing_account_id', p_billing_account_id,
                          'codice',             v_codice_ba,
                          'storia',             COALESCE(v_storia, '[]'::jsonb),
                          'n_documenti',        COALESCE(v_totale, 0),
                          'emittente_sr_prima', p_emittente_sr_prima,
                          'emittente_sr_dopo',  p_emittente_sr_dopo),
        'valori',     jsonb_build_array(
                          COALESCE(v_codice_ba, p_billing_account_id::text),
                          COALESCE(v_codice_ef, p_emittente_sr_prima::text),
                          COALESCE(v_elenco, '')));

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
IS 'Pure check (§12.5.1): elenca i motivi che impediscono di togliere o cambiare una riga di anagrafiche.emittenti_fiscali_billing_account. [] = ammesso; altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva. ⭐ rev 2026-08-31 (brief-db-registri-di-numerazione-emittente-e-trasloco, C2-17): la storia non e'' piu'' «fatture e commesse» ma «qualunque documento gia'' NUMERATO su un registro», derivata da vendite.famiglie_documento — e la frase deve dirlo. ⛔ Con cinque famiglie, una frase che ne nomina due («ha gia'' 3 fatture e 1 commesse») sarebbe PEGGIO di una che non ne nomina nessuna: manderebbe a cercare fatture a un cliente bloccato da un DDT. I valori diventano tre — cliente, emittente, ELENCO — e l''elenco lo compone il DB, che e'' l''unico posto dove il catalogo e'' gia'' aperto. ⭐ Le parole dell''elenco sono le descrizioni del catalogo e non cinque etichette ricopiate qui: una famiglia in piu'' domani cambia la frase da se'', senza toccare questa funzione. ⚠️ WITH ORDINALITY e non un ORDER BY sul codice: l''ordine e'' quello del catalogo (la fattura per prima), e senza ordinalita'' l''ordine di uno string_agg su una function scan non e'' garantito — la stessa frase cambierebbe di corsa in corsa e un test sulla frase diventerebbe instabile. ⭐ EXISTS PRIMA, CONTEGGI DOPO: il ramo «nessuna storia» e'' quello che la lista dei mapping attraversa a ogni caricamento, una volta per riga, e ora costa un anagrafiche.fn_ba_ha_storia_emittente che esce al primo documento trovato; i conteggi per famiglia si pagano solo quando si e'' gia'' deciso di rifiutare. ⚠️ CAMBIA IL `dettaglio`: spariscono n_fatture e n_commesse, arrivano `storia` (array di {famiglia, descrizione, n}) e `n_documenti` (il totale). Il `reason_key` NON cambia, quindi la traduzione del frontend resta agganciata dov''era. ⛔ IL PREDICATO DEL MAPPING SPECIFICO E'' UNA COPPIA: togliere l''aggancio fa ricadere il billing account sul gestore globale, quindi il cambio esiste solo se l''emittente della riga e'' DIVERSO da quello del default — se coincidono non si sposta nessun documento e la rimozione resta ammessa. ⭐ UNA sola funzione per entrambe le specie di riga: il frontend chiama una cosa per riga, e con due check sarebbe il chiamante a dover dedurre in Python «che tipo di riga e'' questa», cioe'' a ricalcolare fuori sede cio'' che qui e'' un IF. ⚠️ La riga del gestore globale (billing_account_id NULL) risponde col singleton, incondizionatamente, e non con la storia. ⚠️ SECURITY DEFINER: la storia si conta su tabelle con la RLS. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-17; e brief-db-motivo-rimozione-mapping-ba, N1 e N7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
