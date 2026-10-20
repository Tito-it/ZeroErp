# ⚙️ Funzione `fn_check_ddt_merce`

```sql
CREATE FUNCTION fn_check_ddt_merce(p_ddt vendite.ddt)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ddt_merce(p_ddt vendite.ddt)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: i motivi FISICI che impediscono di emettere una bolla che
--   muove merce. Funzione PURA (fn_check_*): non solleva, non scrive.
-- Consumatori: script.fn_check_ddt_emittibile (la accoda: capability e
--   guard dell'emissione) e vendite.fn_cambia_stato_ddt (solleva il
--   PRIMO motivo con script.fn_raise_primo_motivo_se_presente).
-- Ritorna: [] se la merce puo' uscire (o la bolla non ne muove),
--   altrimenti un array con UN motivo {codice, reason, reason_key,
--   dettaglio, valori}: si esce al primo, gli altri parlerebbero di una
--   bolla che comunque non si emette.
-- Brief: brief-db-magazzino-lotto-3-scarico-da-ddt, sezione 4 (P-6).
DECLARE
    v_causale        config.causali_trasporto.causale_magazzino%TYPE;
    v_stock_negativo magazzino.causali.consente_stock_negativo%TYPE;
    v_voce           record;
    v_pos            record;
    v_motivi_riga    jsonb;
    v_primo          jsonb;
BEGIN
    -- 0. Una bolla che non muove merce non ha motivi fisici.
    IF NOT vendite.fn_ddt_muove_merce(p_ddt) THEN
        RETURN '[]'::jsonb;
    END IF;
    v_causale := vendite.fn_ddt_causale_magazzino(p_ddt);

    -- 1. Il magazzino di partenza.
    IF p_ddt.magazzino_id IS NULL THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_DDT_MAGAZZINO_OBBLIGATORIO',
            'reason',     'MAGAZZINO_MANCANTE',
            'reason_key', 'vendite.ddt.azione_reason.magazzino_mancante',
            'dettaglio',  jsonb_build_object('ddt_id', p_ddt.id, 'quale', 'PARTENZA'),
            -- «La bolla non indica il magazzino %s: ...»
            'valori',     jsonb_build_array('di partenza')));
    END IF;

    -- 2. Il magazzino di arrivo, per la bolla di trasferimento.
    IF v_causale = 'TRASF_OUT' AND p_ddt.magazzino_arrivo_id IS NULL THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_DDT_MAGAZZINO_OBBLIGATORIO',
            'reason',     'MAGAZZINO_ARRIVO_MANCANTE',
            'reason_key', 'vendite.ddt.azione_reason.magazzino_arrivo_mancante',
            'dettaglio',  jsonb_build_object('ddt_id', p_ddt.id, 'quale', 'ARRIVO'),
            'valori',     jsonb_build_array('di arrivo')));
    END IF;

    -- 3. I prelievi coprono la quantita' di ogni voce (o la voce e'
    --    automatica: nessuna scelta da fare, il prelievo lo crea il verbo).
    SELECT m.* INTO v_voce
      FROM vendite.fn_ddt_merce_da_movimentare(p_ddt) m
     WHERE (m.prelevata = 0 AND NOT m.automatico)
        OR (m.prelevata > 0 AND m.prelevata <> m.qta)
     ORDER BY m.riga_nr, m.ddt_riga_id, m.ddt_riga_componente_id NULLS FIRST
     LIMIT 1;
    IF FOUND THEN
        RETURN jsonb_build_array(jsonb_build_object(
            'codice',     'E_DDT_PRELIEVI_INCOMPLETI',
            'reason',     'PRELIEVI_INCOMPLETI',
            'reason_key', 'vendite.ddt.azione_reason.prelievi_incompleti',
            'dettaglio',  jsonb_build_object('ddt_id', p_ddt.id,
                                             'riga_id', v_voce.ddt_riga_id,
                                             'componente_id', v_voce.ddt_riga_componente_id,
                                             'riga_nr', v_voce.riga_nr,
                                             'attesa', v_voce.qta,
                                             'prelevata', v_voce.prelevata),
            -- «Riga %s della bolla: indicati %s pezzi su %s. ...»
            'valori',     jsonb_build_array(v_voce.riga_nr::text,
                                            trim_scale(v_voce.prelevata)::text,
                                            trim_scale(v_voce.qta)::text)));
    END IF;

    -- 4. Ogni prelievo (e ogni voce automatica, a posizione vuota) lo
    --    accetterebbe la primitiva? La STESSA check che lei chiama.
    FOR v_pos IN
        SELECT m.riga_nr, m.ddt_riga_id, m.articolo_id,
               p.id AS prelievo_id, p.lotto_id, p.asset_id, p.ubicazione_id
          FROM vendite.fn_ddt_merce_da_movimentare(p_ddt) m
          LEFT JOIN vendite.ddt_righe_prelievi p
                 ON p.ddt_riga_id = m.ddt_riga_id
                AND p.ddt_riga_componente_id IS NOT DISTINCT FROM m.ddt_riga_componente_id
         ORDER BY m.riga_nr, m.ddt_riga_id, m.ddt_riga_componente_id NULLS FIRST, p.id
    LOOP
        v_motivi_riga := script.fn_check_riga_magazzino(
                             p_ddt.magazzino_id, v_pos.articolo_id,
                             v_pos.lotto_id, v_pos.asset_id, v_pos.ubicazione_id);
        v_primo := v_motivi_riga -> 0;
        IF v_primo IS NOT NULL THEN
            RETURN jsonb_build_array(jsonb_build_object(
                'codice',     v_primo ->> 'codice',
                -- reason e reason_key sono della BOLLA; il dettaglio della
                -- riga resta nel dettaglio, per chi apre i prelievi.
                'reason',     'MERCE_NON_PRELEVABILE',
                'reason_key', 'vendite.ddt.azione_reason.merce_non_prelevabile',
                'dettaglio',  COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
                              || jsonb_build_object('ddt_id', p_ddt.id,
                                                    'riga_id', v_pos.ddt_riga_id,
                                                    'riga_nr', v_pos.riga_nr,
                                                    'prelievo_id', v_pos.prelievo_id,
                                                    'riga_reason', v_primo ->> 'reason',
                                                    'riga_reason_key', v_primo ->> 'reason_key'),
                'valori',     COALESCE(v_primo -> 'valori', '[]'::jsonb)));
        END IF;
    END LOOP;

    -- 5. La merce c'e'? Salvo le causali che ammettono la giacenza
    --    negativa, la stessa check della primitiva, SOMMATA per
    --    (articolo, lotto, seriale).
    SELECT c.consente_stock_negativo INTO v_stock_negativo
      FROM magazzino.causali c
     WHERE c.codice_interno = v_causale;
    IF NOT COALESCE(v_stock_negativo, false) THEN
        FOR v_pos IN
            SELECT m.articolo_id, p.lotto_id, p.asset_id,
                   sum(COALESCE(p.qta, m.qta)) AS qta_uscita
              FROM vendite.fn_ddt_merce_da_movimentare(p_ddt) m
              LEFT JOIN vendite.ddt_righe_prelievi p
                     ON p.ddt_riga_id = m.ddt_riga_id
                    AND p.ddt_riga_componente_id IS NOT DISTINCT FROM m.ddt_riga_componente_id
             GROUP BY m.articolo_id, p.lotto_id, p.asset_id
             ORDER BY m.articolo_id, p.lotto_id NULLS FIRST, p.asset_id NULLS FIRST
        LOOP
            v_motivi_riga := script.fn_check_disponibilita_uscita(
                                 p_ddt.magazzino_id, v_pos.articolo_id, v_pos.qta_uscita,
                                 NULL, NULL, NULL,
                                 v_pos.lotto_id, v_pos.asset_id, false);
            v_primo := v_motivi_riga -> 0;
            IF v_primo IS NOT NULL THEN
                RETURN jsonb_build_array(jsonb_build_object(
                    'codice',     v_primo ->> 'codice',
                    'reason',     'MERCE_NON_DISPONIBILE',
                    'reason_key', 'vendite.ddt.azione_reason.merce_non_disponibile',
                    'dettaglio',  COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
                                  || jsonb_build_object('ddt_id', p_ddt.id,
                                                        'riga_reason', v_primo ->> 'reason',
                                                        'riga_reason_key', v_primo ->> 'reason_key'),
                    'valori',     COALESCE(v_primo -> 'valori', '[]'::jsonb)));
            END IF;
        END LOOP;
    END IF;

    RETURN '[]'::jsonb;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ddt_merce(p_ddt vendite.ddt)
IS 'I motivi FISICI che impediscono di emettere una bolla che muove merce. PURA. In ordine, si esce al primo: magazzino di partenza mancante, magazzino di arrivo mancante su una bolla di trasferimento (E_DDT_MAGAZZINO_OBBLIGATORIO); una voce i cui prelievi non ne coprono la quantita'', o senza prelievi e non automatica (E_DDT_PRELIEVI_INCOMPLETI); un prelievo che la primitiva rifiuterebbe (il codice di script.fn_check_riga_magazzino); merce non disponibile, sommata per articolo/lotto/seriale (il codice di script.fn_check_disponibilita_uscita), salvo causale con giacenza negativa ammessa. Ogni motivo porta i VALORI della frase: la solleva il verbo vendite.fn_cambia_stato_ddt col primo motivo. La accoda script.fn_check_ddt_emittibile (capability «Emetti»). Una bolla che non muove merce torna []. L''ubicazione di arrivo non si controlla qui (si compila fino al CONSEGNATO). Chiavi i18n: vendite.ddt.azione_reason.{magazzino_mancante, magazzino_arrivo_mancante, prelievi_incompleti, merce_non_prelevabile, merce_non_disponibile}. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt (P-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
