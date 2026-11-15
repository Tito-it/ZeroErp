{% include-markdown "it/dbzero/vendite/manual/fn_get_contratto_attivo.md" %}
# ⚙️ Funzione `fn_get_contratto_attivo`

```sql
CREATE FUNCTION fn_get_contratto_attivo(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
    -- ⭐ rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6c):
    --    in vigore e' lo stato di emissione, la colonna del vocabolario, non
    --    un codice.
    SELECT c.id
      INTO v_contratto_id
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s
        ON s.id = c.stato_doc_contratto_id
     WHERE c.billing_account_id = p_billing_account_id
       AND c.utility_id         = p_utility_id
       AND c.validita          @> p_data_riferimento
       AND s.emissione
     ORDER BY c.id DESC
     LIMIT 1;

    RETURN v_contratto_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_contratto_attivo(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
IS 'Il predicato «contratto in vigore per (billing account, utility, data)», in un posto solo: dato cio'' che un documento porta, dice di quale fornitura si parla, perche'' nessuna testata di documento (bolle, ordini, preventivi, fatture) porta un contratto_id, tutte portano quella terna. La regola: i contratti di quel billing account, per quella utility, con la validita'' che contiene la data, nello stato di emissione (la colonna emissione di config.stati_doc_contratti); se ne resta piu'' di uno, quello con l''id piu'' alto. Piu'' di uno ci puo'' restare davvero, perche'' le finestre di due contratti si sovrappongono quando un rinnovo parte prima che il vecchio scada; «l''id piu'' alto» e'' arbitrario ma scritto, cosi'' il prezzo non cambia da una corsa all''altra. La leggono il risolutore dei prezzi (vendite.fn_resolve_prezzo_listino_v2_esito) e quello IVA (vendite.fn_get_tipo_utenza_fornitura), che da quel contratto arriva al tipo d''uso della fornitura: sceglierne due diversi darebbe prezzo e aliquota della stessa riga da forniture diverse. Ritorna solo l''id; NULL, senza sollevare, quando nessun contratto e'' in vigore, che e'' un caso legittimo (un cliente nuovo). STABLE, sola lettura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
