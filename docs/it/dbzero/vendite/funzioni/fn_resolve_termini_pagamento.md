# ⚙️ Funzione `fn_resolve_termini_pagamento`

```sql
CREATE FUNCTION fn_resolve_termini_pagamento(p_attivita_id bigint)
```

**Definizione completa:**

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
DECLARE
    v_sorgente_codice  config.sorgenti.codice_interno%TYPE;
    v_sorgente_uid     vendite.attivita_fatturabili.sorgente_uid%TYPE;
    v_ba_fattura_id    anagrafiche.billing_account.id%TYPE;
    v_termine          config.termini_pagamento.id%TYPE;
    v_modalita         config.modalita_pagamento.id%TYPE;
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
    SELECT s.codice_interno,
           a.sorgente_uid,
           COALESCE(ba.parent_account_id, a.billing_account_id)
      INTO v_sorgente_codice, v_sorgente_uid, v_ba_fattura_id
      FROM vendite.attivita_fatturabili a
      JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id
      LEFT JOIN config.sorgenti s ON s.id = a.sorgente_tipo_id
     WHERE a.id = p_attivita_id;

    IF v_ba_fattura_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_resolve_termini_pagamento', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id),
            NULL::uuid, concat('attivita non trovata per id ', p_attivita_id)
        );
    END IF;

    -- ── Livello 1: documento sorgente ────────────────────────────
    -- L'ordine porta entrambi, il preventivo il solo termine. Nessun
    -- ramo contratto: non ha colonne di pagamento.
    IF v_sorgente_codice = 'ORDINE_VENDITA' THEN
        SELECT o.termine_pagamento_id, o.modalita_pagamento_id
          INTO v_termine, v_modalita
          FROM vendite.ordini o
         WHERE o.uid = v_sorgente_uid;
    ELSIF v_sorgente_codice = 'PREVENTIVO' THEN
        SELECT p.termine_pagamento_id
          INTO v_termine
          FROM vendite.preventivi p
         WHERE p.uid = v_sorgente_uid;
    END IF;

    -- ── Livello 2: cliente del BA PADRE ──────────────────────────
    -- Costante su tutte le attivita' che aggregano insieme, perche'
    -- il BA padre e' gia' elemento di chiave: questo livello non puo'
    -- spaccare una fattura. Deterministico grazie a
    -- uq_clienti_istanza_utility: una riga sola, non un LIMIT 1.
    -- Si interroga solo per i campi ancora scoperti, cosi' il
    -- livello 1 non viene sovrascritto.
    IF v_termine IS NULL OR v_modalita IS NULL THEN
        SELECT COALESCE(v_termine,  cl.termine_pagamento_id),
               COALESCE(v_modalita, cl.modalita_pagamento_id)
          INTO v_termine, v_modalita
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.clienti cl
            ON cl.istanza_utility_id = ba.istanza_utility_id
         WHERE ba.id = v_ba_fattura_id;
    END IF;

    -- ── Livello 3: default ───────────────────────────────────────
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
IS 'Catena unica condizioni di pagamento per attivita'' (C-13): ritorna la coppia (termine_pagamento_id, modalita_pagamento_id) scendendo documento sorgente -> cliente (per istanza_utility) -> default TP_1RATA sul solo termine. I due campi scendono in modo indipendente: il preventivo porta il termine ma non la modalita''.';
```

---
{% include-markdown "signature-core.md" %}
