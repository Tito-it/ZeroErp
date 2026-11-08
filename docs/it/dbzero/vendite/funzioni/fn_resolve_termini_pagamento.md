{% include-markdown "it/dbzero/vendite/manual/fn_resolve_termini_pagamento.md" %}
# ⚙️ Funzione `fn_resolve_termini_pagamento`

```sql
CREATE FUNCTION fn_resolve_termini_pagamento(p_attivita_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_termini_pagamento(p_attivita_id bigint)
 RETURNS TABLE(termine_pagamento_id bigint, modalita_pagamento_id integer)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: unica implementazione della catena delle condizioni di
--        pagamento (C-13). Risolve per UNA attivita' la coppia che
--        entra nella chiave di aggregazione della fattura (D-7/D-B).
-- Regole: i due campi scendono la catena in modo INDIPENDENTE, perche'
--         la modalita' ha meno livelli del termine (il preventivo non
--         la porta). Assenza totale = TP_1RATA sul termine (D-J) e
--         NULL sulla modalita': `config.modalita_pagamento` non ha una
--         riga «default», e sceglierne una arbitrariamente finirebbe
--         sulla FatturaPA.
-- ⚠️ Ogni livello legge in variabili PROPRIE e la fusione avviene
--    dopo, con COALESCE in codice: un `SELECT ... INTO` che non trova
--    righe mette le variabili a NULL, quindi leggere direttamente
--    dentro `v_termine`/`v_modalita` farebbe CANCELLARE al livello a
--    valle cio' che il livello a monte aveva gia' risolto.
DECLARE
    v_sorgente_codice  config.sorgenti.codice_interno%TYPE;
    -- La chiave del documento d'origine, nelle due specie del modello: l'ordine
    -- e il preventivo sono le sole origini che il livello 1 legge, e hanno uid.
    v_sorgente_id      vendite.commesse_attivita.sorgente_id%TYPE;
    v_sorgente_uid     vendite.ordini.uid%TYPE;
    v_commessa_id      vendite.commesse.id%TYPE;
    v_ba_fattura_id    anagrafiche.billing_account.id%TYPE;
    v_termine          config.termini_pagamento.id%TYPE;
    v_modalita         config.modalita_pagamento.id%TYPE;
    v_liv_termine      config.termini_pagamento.id%TYPE;
    v_liv_modalita     config.modalita_pagamento.id%TYPE;
    v_ca_id            vendite.attivita_fatturabili.commessa_attivita_id%TYPE;
BEGIN
    -- Guard: id numerico obbligatorio e positivo (linee-guida-sql).
    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_resolve_termini_pagamento', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_attivita_id', 'valore', p_attivita_id),
            NULL::uuid, 'p_attivita_id obbligatorio e > 0'
        );
    END IF;

    -- BA della FATTURA = padre se c'e', stessa espressione di
    -- fn_build_fattura_key: le condizioni sono di chi riceve il
    -- documento, non del conto figlio che ha generato la riga.
    SELECT a.commessa_id,
           a.commessa_attivita_id,
           COALESCE(ba.parent_account_id, a.billing_account_id)
      INTO v_commessa_id, v_ca_id, v_ba_fattura_id
      FROM vendite.attivita_fatturabili a
      JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id
     WHERE a.id = p_attivita_id;

    IF v_ba_fattura_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_resolve_termini_pagamento', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id),
            NULL::uuid, concat('attivita non trovata per id ', p_attivita_id)
        );
    END IF;

    -- ── Il documento d'origine ───────────────────────────────────
    -- L'attivita' nasce da una riga di commessa (commessa_attivita_id, FK NOT
    -- NULL), e la riga di commessa dice da quale documento nasce: tipo e chiave
    -- della provenienza. Si leggono solo ordine e preventivo, gli unici
    -- documenti con colonne di pagamento; per loro la chiave si legge nelle due
    -- specie del modello (sorgente_id o sorgente_uid), con la regola d'incontro
    -- del livello 1.
    SELECT s.codice_interno,
           ca.sorgente_id,
           CASE WHEN s.codice_interno IN ('ORDINE_VENDITA', 'PREVENTIVO')
                THEN ca.sorgente_uid::uuid END
      INTO v_sorgente_codice, v_sorgente_id, v_sorgente_uid
      FROM vendite.commesse_attivita ca
      LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
     WHERE ca.id = v_ca_id;

    -- ── Livello 1: documento sorgente ────────────────────────────
    -- L'ordine porta entrambi, il preventivo il solo termine. Nessun
    -- ramo contratto: non ha colonne di pagamento.
    IF v_sorgente_codice = 'ORDINE_VENDITA' THEN
        SELECT o.termine_pagamento_id, o.modalita_pagamento_id
          INTO v_liv_termine, v_liv_modalita
          FROM vendite.ordini o
         WHERE (o.id = v_sorgente_id OR o.uid = v_sorgente_uid);
        v_termine  := COALESCE(v_termine,  v_liv_termine);
        v_modalita := COALESCE(v_modalita, v_liv_modalita);
    ELSIF v_sorgente_codice = 'PREVENTIVO' THEN
        SELECT p.termine_pagamento_id
          INTO v_liv_termine
          FROM vendite.preventivi p
         WHERE (p.id = v_sorgente_id OR p.uid = v_sorgente_uid);
        v_termine := COALESCE(v_termine, v_liv_termine);
    END IF;

    -- ── Livello 2: COMMESSA (D-R) ────────────────────────────────
    -- La commessa POSSIEDE le proprie condizioni: la sorgente gliele
    -- propone alla nascita e sono elemento della sua chiave di
    -- raggruppamento, quindi tutte le attivita' di una commessa
    -- portano lo stesso valore e questo livello non puo' spaccare
    -- una fattura piu' di quanto D-R non abbia gia' spaccato la
    -- commessa. Sta PRIMA del cliente perche' e' piu' specifico e
    -- perche' cambiare le condizioni di un cliente non deve
    -- riscrivere quelle delle commesse gia' aperte.
    IF v_commessa_id IS NOT NULL AND (v_termine IS NULL OR v_modalita IS NULL) THEN
        SELECT c.termine_pagamento_id, c.modalita_pagamento_id
          INTO v_liv_termine, v_liv_modalita
          FROM vendite.commesse c
         WHERE c.id = v_commessa_id;
        v_termine  := COALESCE(v_termine,  v_liv_termine);
        v_modalita := COALESCE(v_modalita, v_liv_modalita);
    END IF;

    -- ── Livello 3: cliente del BA PADRE ──────────────────────────
    -- Costante su tutte le attivita' che aggregano insieme, perche'
    -- il BA padre e' gia' elemento di chiave: questo livello non puo'
    -- spaccare una fattura. Deterministico grazie a
    -- uq_clienti_billing_account: un cliente per BA, una riga sola,
    -- non un LIMIT 1. ⚠️ rev 2026-10-08: fino a quel giorno il cliente
    -- si agganciava per ISTANZA, contando su «un cliente per istanza»;
    -- con piu' BA per istanza (D-5/D-6) avrebbe preso un cliente
    -- qualunque. Si aggancia per BA.
    -- ⚠️ La JOIN e' inner: un BA padre senza riga cliente da ZERO
    -- righe, e leggere qui dentro le variabili di stato le
    -- azzererebbe (vedi nota in testa).
    IF v_termine IS NULL OR v_modalita IS NULL THEN
        SELECT cl.termine_pagamento_id, cl.modalita_pagamento_id
          INTO v_liv_termine, v_liv_modalita
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.clienti cl
            ON cl.billing_account_id = ba.id
         WHERE ba.id = v_ba_fattura_id;
        v_termine  := COALESCE(v_termine,  v_liv_termine);
        v_modalita := COALESCE(v_modalita, v_liv_modalita);
    END IF;

    -- ── Livello 4: default ───────────────────────────────────────
    -- Solo il termine ha un default (D-J). La modalita' resta NULL.
    IF v_termine IS NULL THEN
        SELECT tp.id
          INTO v_termine
          FROM config.termini_pagamento tp
         WHERE tp.codice_interno = 'TP_1RATA'
           AND tp.attivo IS TRUE;
    END IF;

    RETURN QUERY SELECT v_termine, v_modalita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_termini_pagamento(p_attivita_id bigint)
IS 'Catena unica delle condizioni di pagamento di un''attivita'' fatturabile: ritorna la coppia (termine_pagamento_id, modalita_pagamento_id) scendendo documento d''origine -> commessa -> cliente del BA padre -> default TP_1RATA sul solo termine. Il documento d''origine e'' quello da cui nasce la riga di commessa dell''attivita'' (commessa_attivita_id -> commesse_attivita, tipo e chiave della provenienza): l''ordine porta termine e modalita'', il preventivo il solo termine; gli altri documenti non hanno colonne di pagamento. La commessa possiede le proprie condizioni; il cliente si aggancia per BA (uq_clienti_billing_account). I due campi scendono in modo indipendente, ognuno livello per livello in variabili proprie fuse con COALESCE. Solleva E_PARAMETRO_INVALIDO su un id non valido, E_VALORE_MANCANTE su un''attivita'' che non esiste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
