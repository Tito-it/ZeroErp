{% include-markdown "it/dbzero/script/manual/fn_check_riga_contabile_eliminabile.md" %}
# ⚙️ Funzione `fn_check_riga_contabile_eliminabile`

```sql
CREATE FUNCTION fn_check_riga_contabile_eliminabile(p_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_riga_contabile_eliminabile(p_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di ELIMINARE una riga
--        contabile — cioe' portarla ad attivo = false, o cancellarla.
--        Funzione PURA (fn_check_*): nessuna scrittura, nessun raise
--        di dominio (salvo i due guard di chiamata).
-- Consumatori: pagamenti.trgfn_vendite_contabili_righe_guard_contenuto
--        (solleva il codice del PRIMO motivo, su UPDATE OF attivo e su
--        DELETE) e il backend sul dettaglio di una riga.
-- Ritorna: [] se la riga si puo' eliminare — la distinta e' MANUALE e
--        in BOZZA — altrimenti array ORDINATO di
--        {codice, reason, reason_key, dettaglio, valori}.
-- ⭐ Rev 2026-10-21: i MOTIVI stanno in
--    script.fn_check_riga_contabile_eliminabile_su_distinta, che li
--    giudica sulla testata. Qui resta la LETTURA sotto row security e
--    i due guard di chiamata. Le LISTE chiamano direttamente la meta'
--    con la testata che hanno gia' letto: chiamare questa per riga
--    ricalcolerebbe il perimetro per riga (linee-guida-sql §13.2).
DECLARE
    -- NUDO di proposito: l'array dei motivi non riflette nessuna colonna.
    v_motivi    jsonb := '[]'::jsonb;
    v_contabile pagamenti.vendite_contabili%ROWTYPE;
BEGIN
    -- ⛔ Guard di PARAMETRO, e solleva: un id assente o <= 0 non lo
    --    produce nessuna interfaccia — e' il chiamante a essere rotto.
    --    TECNICO, e non E_PARAMETRO_INVALIDO, che e' un debito e non
    --    una sede (AGENTS.md).
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_riga_contabile_eliminabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_riga_id',
                               'valore',    p_riga_id),
            NULL::uuid,
            'script.fn_check_riga_contabile_eliminabile',
            'identificativo della riga contabile non valido');
    END IF;

    -- La testata della riga, in una lettura sola. ⚠️ Sotto la row
    -- security: chi vede la riga vede la testata per la stessa
    -- catena di scope (via contabile), quindi «non trovata» qui
    -- vuol dire «non esiste» oppure «non e' tua» — e le due risposte
    -- devono restare indistinguibili.
    SELECT c.*
      INTO v_contabile
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili c ON c.id = r.contabile_id
     WHERE r.id = p_riga_id;

    -- ⛔ Non si risponde [] su una riga che non si legge: sarebbe
    --    «si puo' eliminare» detto di una cosa che non si vede, cioe'
    --    un fail-open silenzioso. Stesso codice del mirror del
    --    movimento, stessa frase, classe NON_TROVATO.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_riga_contabile_eliminabile',
            'E_RIGA_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_riga_id', p_riga_id),
            NULL::uuid,
            p_riga_id::text);
    END IF;

    v_motivi := script.fn_check_riga_contabile_eliminabile_su_distinta(v_contabile);

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_riga_contabile_eliminabile(p_riga_id bigint)
IS 'Pure check (§12.5.1): i motivi che impediscono di ELIMINARE una riga contabile — attivo = false, oppure DELETE. Ritorna [] se si puo'' (la distinta e'' MANUALE e in BOZZA), altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. NOMINA i codici e non solleva (salvo i due guard di chiamata). ⭐ Rev 2026-10-21: LEGGE E DELEGA. I motivi — tutti sulla testata — stanno in script.fn_check_riga_contabile_eliminabile_su_distinta, SEDE UNICA del predicato; qui restano la lettura di riga e testata sotto la row security e i due guard di chiamata. pagamenti.trgfn_vendite_contabili_righe_guard_contenuto la CHIAMA su UPDATE OF attivo (true -> false) e su DELETE e solleva il codice del primo motivo con fn_raise_primo_motivo_se_presente; il backend la usa sul dettaglio di una riga. ⛔ Le LISTE non la chiamano per riga: e'' SECURITY INVOKER, ogni chiamata e'' un''istruzione a se'' e ricalcolerebbe il perimetro dell''utente per ogni riga (linee-guida-sql §13.2) — chiamano la meta'' su distinta con la testata che hanno gia'' letto. ⚠️ L''ORDINE dei motivi e'' il contratto: vedi la meta'' su distinta. ⚠️ SECURITY INVOKER e legge sotto la row security: chi vede la riga vede la testata per la stessa catena di scope (via contabile). Riga non leggibile — inesistente o di un altro — solleva E_RIGA_CONTABILE_NON_TROVATA (404, no-leak): rispondere [] sarebbe un fail-open. ⛔ Guard di parametro su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO), non su E_PARAMETRO_INVALIDO. Brief: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §2.2 (D17), §4 P-1; brief-db-righe-distinta-annullata-fuori-dalle-code §4.2, §8.1 (D-2, D-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
