# ⚙️ Funzione `fn_canone_periodi`

```sql
CREATE FUNCTION fn_canone_periodi(p_valido_dal date, p_valido_al date, p_periodicita character varying, p_mese_partenza smallint, p_generazione character varying, p_data_giro date, p_dal date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_canone_periodi(p_valido_dal date, p_valido_al date, p_periodicita character varying, p_mese_partenza smallint, p_generazione character varying, p_data_giro date, p_dal date DEFAULT NULL::date)
 RETURNS TABLE(periodo_dal date, periodo_al date, competenza_mese date, frazione numeric, periodo_intero_dal date, periodo_intero_al date)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: i pezzi di canone da addebitare per una riga, secondo le
--   decisioni di Tid (G-2, G-3, F-2 … F-7). Regola completa
--   nell'intestazione del changeSet 20261029-25 e nel COMMENT.
-- Sede unica della regola dei periodi: la leggono il lister del push e la
--   dashboard dei canoni non generati, mai una copia.
DECLARE
    v_mesi       config.periodicita.mesi%TYPE;
    v_dal        vendite.commesse_attivita.competenza_dal%TYPE;
    v_comp       vendite.commesse_attivita.competenza_mese%TYPE;
    v_inizio     vendite.commesse_attivita.competenza_dal%TYPE;
    v_fine       vendite.commesse_attivita.competenza_al%TYPE;
    v_s          vendite.commesse_attivita.competenza_dal%TYPE;
    v_e          vendite.commesse_attivita.competenza_al%TYPE;
    v_pezzo_s    vendite.commesse_attivita.competenza_dal%TYPE;
    v_pezzo_e    vendite.commesse_attivita.competenza_al%TYPE;
    v_tot        vendite.commesse_attivita.quantita%TYPE;
    v_acc        vendite.commesse_attivita.quantita%TYPE;
    v_offset     integer;  -- nudo DICHIARATO: mesi fra l'inizio del periodo e il mese del contratto
    v_param      text;     -- nudo DICHIARATO: il parametro incoerente, per il contesto
BEGIN
    -- Guard dei parametri: un valore incoerente e' un errore di chi chiama.
    v_param := CASE
        WHEN p_valido_dal IS NULL THEN 'p_valido_dal'
        WHEN p_data_giro IS NULL THEN 'p_data_giro'
        WHEN p_valido_al < p_valido_dal THEN 'p_valido_al'
        WHEN p_mese_partenza IS NULL OR p_mese_partenza NOT BETWEEN 1 AND 12 THEN 'p_mese_partenza'
        WHEN p_generazione IS NULL
             OR p_generazione NOT IN ('INIZIO_PERIODO', 'FINE_PERIODO') THEN 'p_generazione'
    END;
    IF v_param IS NULL THEN
        SELECT p.mesi INTO v_mesi
          FROM config.periodicita p
         WHERE p.codice = script.fn_codice_normalizzato(p_periodicita);
        IF NOT FOUND THEN
            v_param := 'p_periodicita';
        END IF;
    END IF;
    IF v_param IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_canone_periodi',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'param',         v_param,
                'valido_dal',    p_valido_dal,
                'valido_al',     p_valido_al,
                'periodicita',   p_periodicita,
                'mese_partenza', p_mese_partenza,
                'generazione',   p_generazione,
                'data_giro',     p_data_giro),
            NULL::uuid,
            v_param);
    END IF;

    v_dal  := greatest(p_valido_dal, coalesce(p_dal, p_valido_dal));
    v_comp := date_trunc('month', p_data_giro)::date;

    -- Il periodo del calendario che contiene l'inizio del contratto: il mese
    -- di partenza piu' un multiplo dei mesi della periodicita'.
    v_offset := ((extract(month FROM p_valido_dal)::integer - p_mese_partenza)
                 % v_mesi + v_mesi) % v_mesi;
    v_inizio := (date_trunc('month', p_valido_dal)
                 - make_interval(months => v_offset))::date;

    LOOP
        EXIT WHEN p_valido_al IS NOT NULL AND v_inizio > p_valido_al;

        v_fine := (v_inizio + make_interval(months => v_mesi)
                   - interval '1 day')::date;
        -- Il periodo tagliato sulla validita' del contratto.
        v_s := greatest(v_inizio, p_valido_dal);
        v_e := least(v_fine, coalesce(p_valido_al, v_fine));

        -- Dovuto? Anticipati: appena cominciato; normali: appena finito.
        -- I periodi dopo non lo sono di sicuro: si esce.
        IF p_generazione = 'INIZIO_PERIODO' THEN
            EXIT WHEN v_s > p_data_giro;
        ELSE
            EXIT WHEN v_e >= p_data_giro;
        END IF;

        -- Gia' addebitato fino a prima del «da»: si salta, o si taglia.
        IF v_e >= v_dal THEN
            v_pezzo_s := greatest(v_s, v_dal);

            -- La frazione del tratto da addebitare: mesi interi 1, il mese a
            -- meta' giorni coperti / giorni del mese, diviso i mesi del periodo.
            SELECT round(sum((least(v_e, m.eom) - greatest(v_pezzo_s, m.bom) + 1)::numeric
                             / (m.eom - m.bom + 1)) / v_mesi, 6)
              INTO v_tot
              FROM (SELECT g::date AS bom,
                           (g + interval '1 month' - interval '1 day')::date AS eom
                      FROM generate_series(date_trunc('month', v_pezzo_s),
                                           v_e, interval '1 month') g) m;
            v_acc := 0;

            -- Un pezzo per anno: il periodo che scavalca il 31/12 si spezza.
            WHILE v_pezzo_s <= v_e LOOP
                v_pezzo_e := least(v_e, make_date(extract(year FROM v_pezzo_s)::integer, 12, 31));

                periodo_dal        := v_pezzo_s;
                periodo_al         := v_pezzo_e;
                competenza_mese    := v_comp;
                periodo_intero_dal := v_inizio;
                periodo_intero_al  := v_fine;
                IF v_pezzo_e = v_e THEN
                    -- L'ultimo pezzo prende il resto: la somma e' esatta.
                    frazione := v_tot - v_acc;
                ELSE
                    SELECT round(sum((least(v_pezzo_e, m.eom) - greatest(v_pezzo_s, m.bom) + 1)::numeric
                                     / (m.eom - m.bom + 1)) / v_mesi, 6)
                      INTO frazione
                      FROM (SELECT g::date AS bom,
                                   (g + interval '1 month' - interval '1 day')::date AS eom
                              FROM generate_series(date_trunc('month', v_pezzo_s),
                                                   v_pezzo_e, interval '1 month') g) m;
                    v_acc := v_acc + frazione;
                END IF;
                RETURN NEXT;

                v_pezzo_s := v_pezzo_e + 1;
            END LOOP;
        END IF;

        v_inizio := (v_inizio + make_interval(months => v_mesi))::date;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION vendite.fn_canone_periodi(p_valido_dal date, p_valido_al date, p_periodicita character varying, p_mese_partenza smallint, p_generazione character varying, p_data_giro date, p_dal date)
IS 'Building block, sede unica della regola dei periodi del canone (decisioni di Tid G-2, G-3, F-2 … F-7; brief-db-contratto-righe-periodiche-in-commessa §6.7). Dati validità del contratto (p_valido_dal, p_valido_al; NULL = senza fine), periodicità (codice di config.periodicita), mese di partenza (1-12), generazione che VALE (coalesce(riga, testata): INIZIO_PERIODO = anticipati, FINE_PERIODO = normali), data del giro e, facoltativo, il giorno da cui ripartire (p_dal = il giorno dopo l''ultimo addebito; NULL = inizio contratto), restituisce i pezzi da addebitare: periodo_dal/periodo_al (la competenza della riga di commessa), competenza_mese (il mese del giro: la fattura di quel mese la prende), frazione del periodo intero (6 decimali) e il periodo intero del calendario (periodo_intero_dal/al). Regola: periodi di calendario dal mese di partenza, dal giorno 1; un periodo si addebita appena cominciato (anticipati: inizio <= data del giro) o appena finito (normali: fine < data del giro), con inizio e fine tagliati sulla validità; i periodi arretrati si recuperano tutti; un periodo che scavalca il 31/12 si spezza in un pezzo per anno; frazione = mesi interi 1 + il mese a metà in giorni coperti / giorni del mese, diviso i mesi del periodo, col resto dell''arrotondamento sull''ultimo pezzo del periodo (i pezzi sommano esattamente la frazione del periodo). Parametri incoerenti: E_PARAMETRO_INVALIDO. Legge solo config.periodicita: nessuna scrittura. STABLE, SECURITY INVOKER. Nasce il 2026-10-29 (20261029-25). Rev 2026-11-04 (20261104-39, D-2 di Tid): la periodicita'' si cerca con script.fn_codice_normalizzato(p_periodicita), perche'' config.periodicita salva il codice in maiuscolo (CODICE_MAIUSCOLO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
