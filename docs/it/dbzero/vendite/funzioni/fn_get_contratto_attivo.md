{% include-markdown "it/dbzero/vendite/manual/fn_get_contratto_attivo.md" %}
# ⚙️ Funzione `fn_get_contratto_attivo`

```sql
CREATE FUNCTION fn_get_contratto_attivo(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_contratto_attivo(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dato (billing account, utility, data) dire QUALE contratto
--   e' attivo, cioe' di quale FORNITURA parla un documento. Nessuna
--   testata di documento porta un contratto_id — ddt, ordini,
--   preventivi e fatture portano tutte quella terna — quindi da li'
--   ci si deve arrivare, e la regola va scritta in un posto solo.
--   Consumatori: il nucleo del pricing e il risolutore IVA, che da
--   quel contratto ricava il tipo d'uso della fornitura.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, Fase 3.
-- Ritorna: l'id del contratto, oppure NULL se a quella data non ce
--   n'e' nessuno attivo. NON solleva: e' un caso legittimo.
DECLARE
    v_contratto_id vendite.contratti.id%TYPE;
BEGIN
    IF p_billing_account_id IS NULL
       OR p_utility_id       IS NULL
       OR p_data_riferimento IS NULL THEN
        RETURN NULL;   -- contesto incompleto: niente da cercare
    END IF;

    -- ⚠️ ORDER BY c.id DESC: le finestre di due contratti si
    --    sovrappongono ogni volta che un rinnovo parte prima che il
    --    vecchio scada, quindi piu' di uno ci puo' restare davvero.
    --    «L'id piu' alto» e' arbitrario ma SCRITTO: senza, il
    --    database ne sceglierebbe uno a caso e il prezzo cambierebbe
    --    da una corsa all'altra.
    -- ⚠️ `codice_interno` e non `codice`: il secondo e' modificabile
    --    dall'utente e smetterebbe di agganciarsi in silenzio al
    --    primo rename.
    SELECT c.id
      INTO v_contratto_id
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s
        ON s.id = c.stato_doc_contratto_id
     WHERE c.billing_account_id = p_billing_account_id
       AND c.utility_id         = p_utility_id
       AND c.validita          @> p_data_riferimento
       AND s.codice_interno     = 'ATTIVO'
     ORDER BY c.id DESC
     LIMIT 1;

    RETURN v_contratto_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_contratto_attivo(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
IS 'LA SEDE UNICA del predicato «contratto attivo per (billing account, utility, data)»: dato quel che un documento porta, dice di quale FORNITURA si sta parlando. ⭐ Serve perche'' NESSUNA testata di documento porta un contratto_id — verificato su ddt, ordini, preventivi e fatture, tutte portano invece quella terna. La regola completa e'': i contratti di quel billing account, per quella utility, con la validita'' che contiene la data, in stato ATTIVO; se ne resta piu'' di uno, quello con l''id piu'' alto. ⚠️ L''ultima riga e'' la parte che conta: piu'' di uno ci puo'' restare davvero, perche'' le finestre di due contratti si sovrappongono ogni volta che un rinnovo parte prima che il vecchio scada. «L''id piu'' alto» e'' arbitrario ma SCRITTO — senza, PostgreSQL ne sceglierebbe uno a caso e il prezzo cambierebbe da una corsa all''altra senza che nessuno capisse perche''. 🔴 Estratta il 2026-08-29 da vendite.fn_resolve_prezzo_listino_v2_esito, dove viveva dentro: serve IDENTICA al risolutore IVA, che da quel contratto arriva al tipo d''uso della fornitura (config.tipi_utenze) — se le due funzioni scegliessero contratti diversi sullo stesso overlap, prezzo e aliquota della STESSA riga verrebbero da forniture diverse, e non lo direbbe nessun errore: si vedrebbe solo il giorno che non quadra un totale. ⭐ Decisione di Tid: si estrae invece di ricopiare, e l''argomento che avevo usato per difendere la copia («il nucleo ha molti chiamanti») era sbagliato — estrarre una porzione interna non ne cambia la firma, quindi i chiamanti non vedono nulla. ℹ️ Ritorna SOLO l''id: listino, versione, variazione globale e snapshot categoria sono snapshot del contratto e restano affare del pricing, non del predicato che lo sceglie. ⚠️ Ritorna NULL e non solleva: nessun contratto attivo e'' legittimo — un preventivo a un cliente nuovo non ha ancora nessuna fornitura. STABLE, sola lettura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
