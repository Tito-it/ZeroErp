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
    --   Elencare i motivi che impediscono di cambiare
    --   l'emittente di un billing account. Funzione PURA
    --   (fn_check_*): nessun raise di dominio, nessuna
    --   scrittura. Consumatori: la madre
    --   anagrafiche.fn_guard_ba_cambio_emittente (che solleva il
    --   codice del primo motivo) e la lista dei mapping nel
    --   drawer dell'emittente (che spegne il cestino di riga).
    --
    -- Ritorna: [] se ammesso; altrimenti array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori} — §12.5.1.
    -- ⚠️ L'ordine e' il contratto: la madre solleva il PRIMO.
    -- =========================================================

    -- 1) La riga senza billing account e' quella del GESTORE
    --    GLOBALE: ha un raggio diverso (N clienti, non uno) e la
    --    guarda anagrafiche.fn_guard_ba_gestore_globale_storia.
    IF p_billing_account_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    -- 2) ⛔ LA META' DEL PREDICATO CHE SI DIMENTICA.
    --    Se l'emittente non cambia DAVVERO non c'e' niente da
    --    presidiare: togliere un mapping specifico quando il
    --    gestore globale punta allo stesso emittente non sposta
    --    nessun documento, ed e' manutenzione ordinaria.
    --    Senza questa riga il cestino si spegnerebbe su quasi
    --    tutte le righe di un'installazione a un solo emittente.
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
    --    compone la frase che legge una PERSONA, e un
    --    soggetto_ruolo_id li' dentro e' rumore. La colonna
    --    esiste ed e' NOT NULL; il COALESCE e' la rete.
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
IS 'Pure check (§12.5.1): elenca i motivi che impediscono di cambiare l''emittente di un billing account. [] = ammesso; altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva — sollevare e'' mestiere della madre. ⛔ IL PREDICATO E'' UNA COPPIA, e la meta'' che si dimentica e'' la prima: togliere un mapping specifico fa ricadere il billing account sul GESTORE GLOBALE, quindi il cambio di emittente esiste SOLO SE l''emittente della riga e'' diverso da quello del default — se coincidono non si sposta nessun documento e la rimozione deve restare ammessa, perche'' e'' manutenzione ordinaria. Scrivere solo «il cliente ha storia» spegnerebbe il gesto su quasi tutte le righe di un''installazione a un solo emittente, tutte a torto. ⭐ Sede unica condivisa: anagrafiche.fn_guard_ba_cambio_emittente CHIAMA questa funzione e solleva il codice del PRIMO motivo (§12.5.2), quindi il tooltip del pulsante e l''errore del rifiuto non possono divergere — non «coincidono oggi»: non possono. ⚠️ L''ORDINE dell''array e'' il contratto: la madre solleva il primo, e un ordine diverso farebbe dire al tooltip una cosa e all''errore un''altra. ⚠️ SECURITY DEFINER, come la madre e per la stessa ragione: la storia si conta su vendite.fatture e vendite.commesse, che hanno la RLS accesa, e da SECURITY INVOKER la funzione risponderebbe «nessuna storia» proprio nel caso in cui il pulsante va spento. ⚠️ Nessun codice errore nuovo: E_BA_EMITTENTE_CON_STORIA e'' gia'' a catalogo (20260826-49). ⭐ I `valori` nominano l''emittente per CODICE e non per soggetto_ruolo_id — correzione del messaggio nato col 20260826-47, che diceva «…con l''emittente 72»: il canale VARIADIC compone la frase che legge una persona. Piano: brief-db-motivo-rimozione-mapping-ba, N1.';
```

---
{% include-markdown "signature-core.md" %}
