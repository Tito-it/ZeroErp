{% include-markdown "it/dbzero/script/manual/fn_gruppi_di_commessa_nel_lotto.md" %}
# ⚙️ Funzione `fn_gruppi_di_commessa_nel_lotto`

```sql
CREATE FUNCTION fn_gruppi_di_commessa_nel_lotto(p_lotto_id bigint, p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_gruppi_di_commessa_nel_lotto(p_lotto_id bigint, p_commessa_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: quali DOCUMENTI (gruppi fatturabili) di un lotto sono
--        alimentati da una commessa. E' la conversione che serve
--        a chi fallisce avendo in mano la commessa e non il
--        documento, e che finora viveva solo dentro
--        vendite.fn_segna_esito_gruppo_lotto.
-- Ritorna: array ORDINATO di gruppo_key, [] se nessuno.
-- ⚠️ Funzione PURA: nessuna scrittura. Solleva solo sui parametri.
DECLARE
    -- ⚠️ Nessuno dei due riflette una colonna, quindi tipo
    --    esplicito: il primo e' la RISPOSTA a una domanda, il
    --    secondo l'array composto.
    v_ha_perimetro boolean;
    v_out          jsonb;
BEGIN
    -- Guard parametri: un id assente o <= 0 e' un chiamante rotto,
    -- non una condizione di dominio. ⛔ Mai un [] silenzioso: si
    -- confonderebbe con «nessun documento», che ha una conseguenza
    -- opposta (vedi testata).
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_gruppi_di_commessa_nel_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio (> 0)');
    END IF;

    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_gruppi_di_commessa_nel_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id),
            NULL::uuid, 'p_commessa_id obbligatorio (> 0)');
    END IF;

    -- Il lotto dichiara un perimetro? La domanda si fa UNA volta:
    -- serve a restringere, non a decidere se rispondere.
    v_ha_perimetro := EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_gruppi g
         WHERE g.lotto_id = p_lotto_id);

    SELECT COALESCE(jsonb_agg(k.gruppo_key ORDER BY k.gruppo_key),
                    '[]'::jsonb)
      INTO v_out
      FROM (
            -- ⛔ LA CATENA E' QUESTA, e non va spostata: la chiave si
            --   calcola su commesse_attivita, che porta la sorgente
            --   del DOCUMENTO. Su attivita_fatturabili darebbe
            --   COMMESSA:<hash>, che non aggancia niente e non
            --   fallisce. ⭐ La costruisce la funzione che la
            --   costruisce gia' per la dashboard: una sola sede.
            SELECT DISTINCT vendite.fn_gruppo_fatturabile_key_di_attivita(
                       ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id
                   ) AS gruppo_key
              FROM vendite.commesse_attivita ca
             WHERE ca.commessa_id = p_commessa_id
           ) k
     WHERE k.gruppo_key IS NOT NULL
       -- Se il lotto dichiara un perimetro, fuori da quello non
       -- stava lavorando quel documento. Se non lo dichiara, li
       -- stava lavorando tutti.
       AND (NOT v_ha_perimetro
            OR EXISTS (SELECT 1
                         FROM vendite.fatturazione_lotti_gruppi g
                        WHERE g.lotto_id   = p_lotto_id
                          AND g.gruppo_key = k.gruppo_key));

    RETURN COALESCE(v_out, '[]'::jsonb);
END;
$function$

COMMENT ON FUNCTION script.fn_gruppi_di_commessa_nel_lotto(p_lotto_id bigint, p_commessa_id bigint)
IS 'Quali DOCUMENTI (gruppi fatturabili) di un lotto sono alimentati da una commessa: array ORDINATO di gruppo_key, [] se nessuno. ⭐ SEDE UNICA della catena commessa -> vendite.commesse_attivita -> vendite.fn_build_gruppo_fatturabile_key: fino al 2026-09-08 viveva dentro vendite.fn_segna_esito_gruppo_lotto e non era chiamabile, mentre chi fallisce al pull ha in mano la COMMESSA e non il documento. ⛔ La parte fragile non e'' la costruzione della chiave ma DA QUALE TABELLA SI LEGGE: calcolarla su vendite.attivita_fatturabili da'' COMMESSA:<hash del segment_key>, che non aggancia nessun perimetro e non fallisce (misurato il 2026-09-08: zero corrispondenze su quattro documenti noti). Una copia di quella scelta, il giorno che si sposta, produce chiavi mute. ⚠️ E'' 1:N — una commessa puo'' alimentare piu'' documenti — quindi chi scrive una segnalazione ne produce UNA PER DOCUMENTO: sceglierne una sola lascerebbe le altre a bloccare il lotto per sempre e non togliibili. ⭐ Il perimetro e'' parte della domanda: se il lotto ne dichiara uno, fuori da quello non stava lavorando; se non lo dichiara (giri di massa) li stava lavorando tutti. ⚠️ [] vuol dire «questo fallimento non ha un proprietario in questo lotto» ⇒ chi scrive mette UNA segnalazione a gruppo_key NULL, che vuol dire «e'' del GIRO» e blocca — non zero righe. ⚠️ Fail-loud sui parametri (E_PARAMETRO_INVALIDO): la chiama anche il backend, e li'' un id <= 0 e'' un chiamante rotto; un [] sarebbe indistinguibile da «nessun documento». STABLE, SECURITY INVOKER: commesse_attivita ha la RLS e il chiamante vede le commesse dei propri emittenti. Brief: brief-db-uscita-documento-dal-giro §6.1 (richiesta BE §3.2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
