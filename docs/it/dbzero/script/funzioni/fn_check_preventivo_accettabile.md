{% include-markdown "it/dbzero/script/manual/fn_check_preventivo_accettabile.md" %}
# ⚙️ Funzione `fn_check_preventivo_accettabile`

```sql
CREATE FUNCTION fn_check_preventivo_accettabile(p_preventivo_id bigint, p_validita_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_preventivo_accettabile(p_preventivo_id bigint, p_validita_al date)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ACCETTAZIONE di un
--   preventivo. Funzione PURA (fn_check_*): non solleva, non
--   scrive. Consumatori: vendite.trgfn_preventivi_guard_transizione
--   (che solleva il codice del primo motivo) e
--   script.fn_available_actions_preventivo (che spegne «Accetta»).
--   Gemella di fn_check_preventivo_emettibile. Vedi l'intestazione
--   del changeSet 20261031-62.
-- Ritorna: [] se accettabile; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio, valori}.
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_uid    vendite.preventivi.uid%TYPE;
    v_numero vendite.preventivi.numero%TYPE;
BEGIN
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_preventivo_accettabile', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'preventivo_id', 'valore', p_preventivo_id),
            NULL::uuid, 'preventivo_id obbligatorio (>0)');
    END IF;

    -- `p.numero` serve a COMPORRE la frase, non a decidere.
    SELECT p.uid, p.numero INTO v_uid, v_numero
      FROM vendite.preventivi p
     WHERE p.id = p_preventivo_id;

    IF v_uid IS NULL THEN
        RETURN v_motivi;   -- preventivo inesistente: decide il chiamante
    END IF;

    -- MOTIVO 1 — LA VALIDITA' E' FINITA (E-2 di Tid, 2026-10-31): il
    --   cliente non puo' piu' accettare un'offerta scaduta, anche se il
    --   job delle scadenze non e' ancora passato a portarla a SCADUTO.
    -- ⭐ Il confronto e' quello del job (vendite.fn_chiudi_preventivi_scaduti):
    --   validita_al e' l'ultimo giorno valido, scade dal giorno dopo.
    -- ⚠️ NULL non scade mai: e' un caso del modello, non un'eccezione.
    -- ⛔ Nessuna chiave `campo`: la richiesta e' «accetta», e validita_al
    --   fuori bozza non si corregge. La strada e' la revisione.
    IF p_validita_al IS NOT NULL
       AND p_validita_al < (SELECT script.fn_data_operativa()) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_PREV_VALIDITA_SCADUTA',
            'reason',     'VALIDITA_SCADUTA',
            'reason_key', 'vendite.preventivi.azione_reason.validita_scaduta',
            'dettaglio',  jsonb_build_object('validita_al', p_validita_al),
            'valori',     jsonb_build_array(COALESCE(v_numero, p_preventivo_id::text),
                                            to_char(p_validita_al, 'DD/MM/YYYY')));
    END IF;

    -- MOTIVO 2 — PREZZI NON AUTORIZZATI: un prezzo in attesa o rifiutato
    --   non diventa un impegno ACCETTATO (brief-db-preventivi-congelamento-
    --   pricing, D-1/D-2). Il predicato sta nel building block comune ai
    --   documenti di vendita; prima lo chiamavano guard e capability
    --   ciascuno per se'. Dopo la validita': un prezzo si aspetta, una
    --   validita' finita non torna.
    v_motivi := v_motivi
             || script.fn_check_prezzi_autorizzati('vendite.preventivi'::regclass,
                                                   p_preventivo_id);

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_preventivo_accettabile(p_preventivo_id bigint, p_validita_al date)
IS 'Funzione PURA (fn_check_*): i motivi che impediscono l''ACCETTAZIONE di un preventivo, [] se accettabile; array ordinato di {codice, reason, reason_key, dettaglio, valori}. Motivo 1 (brief-db-scadenza-preventivi, E-2 di Tid 2026-10-31): la validita'' e'' finita, p_validita_al < script.fn_data_operativa() (validita_al e'' l''ultimo giorno valido, lo stesso confronto del job delle scadenze; NULL non scade) -> E_PREV_VALIDITA_SCADUTA, reason VALIDITA_SCADUTA, reason_key vendite.preventivi.azione_reason.validita_scaduta, valori numero e data. Motivo 2: i prezzi non autorizzati, da script.fn_check_prezzi_autorizzati (prima la chiamavano guard e capability ciascuno per se''). ⭐ p_validita_al e'' un PARAMETRO senza default: il guard vendite.trgfn_preventivi_guard_transizione e'' BEFORE ROW sulla testata e passa NEW.validita_al (rileggerla per id leggerebbe la riga di prima); la capability script.fn_available_actions_preventivo passa p.validita_al. Preventivo inesistente: [], decide il chiamante; id NULL o <= 0: E_PARAMETRO_INVALIDO. Gemella di script.fn_check_preventivo_emettibile. Brief: brief-db-scadenza-preventivi §8.1 (D-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
