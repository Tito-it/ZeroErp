# ⚙️ Funzione `fn_check_fatture_con_rettifiche`

```sql
CREATE FUNCTION fn_check_fatture_con_rettifiche(p_fatture_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_fatture_con_rettifiche(p_fatture_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire se le righe di queste fatture sono gia' state
--   RETTIFICATE — cioe' se qualcuno ha gia' registrato un
--   accredito su di esse. Funzione PURA (fn_check_*): nessun
--   raise di dominio, nessuna scrittura.
--   Consumatori: le tre porte di reset, via le rispettive
--   fn_check_*, e per loro tramite fn_available_actions_lotto.
-- Ritorna: [] se nessuna riga e' rettificata; altrimenti un
--   array con {codice, reason, reason_key, dettaglio}.
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_righe  integer;
BEGIN
    -- Insieme vuoto: non c'e' niente da controllare, e NON e'
    -- un errore di parametro — i chiamanti passano legittimamente
    -- un lotto senza fatture.
    IF p_fatture_ids IS NULL
       OR array_length(p_fatture_ids, 1) IS NULL THEN
        RETURN v_motivi;
    END IF;

    -- Le QUATTRO figlie NO ACTION di vendite.fatture_righe, in
    -- un colpo solo. Si contano le RIGHE DI FATTURA bloccate,
    -- non i riferimenti: all'operatore serve sapere quante righe
    -- del suo documento sono intoccabili, non quanti puntatori
    -- ci sono sopra.
    SELECT count(*)
      INTO v_righe
      FROM vendite.fatture_righe fr
     WHERE fr.fattura_id = ANY(p_fatture_ids)
       AND (
            EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                     WHERE ca.fattura_riga_rettificata_id = fr.id)
         OR EXISTS (SELECT 1 FROM vendite.attivita_fatturabili af
                     WHERE af.fattura_riga_rettificata_id = fr.id)
         OR EXISTS (SELECT 1 FROM vendite.resi_righe_accrediti ra
                     WHERE ra.fattura_riga_rettificata_id = fr.id)
            -- ⚠️ L'auto-riferimento conta SOLO se la riga che
            --   rettifica sta FUORI dall'insieme che si sta
            --   cancellando: se muoiono insieme, la NO ACTION
            --   e' soddisfatta a fine istruzione e non c'e'
            --   niente da impedire. Senza questa esclusione si
            --   bloccherebbe il caso normale — nota di credito
            --   e fattura nello stesso lotto.
         OR EXISTS (SELECT 1 FROM vendite.fatture_righe fr2
                     WHERE fr2.riga_rettificata_id = fr.id
                       AND NOT (fr2.fattura_id = ANY(p_fatture_ids)))
       );

    IF COALESCE(v_righe, 0) > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_FATTURE_RIGHE_RETTIFICATE',
            'reason',     'RIGHE_RETTIFICATE',
            -- ⚠️ La reason_key e' un debito verso il frontend
            --   finche' non esiste la voce i18n corrispondente.
            'reason_key', 'vendite.lotti.azione_reason.righe_rettificate',
            'dettaglio',  v_righe);
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_fatture_con_rettifiche(p_fatture_ids bigint[])
IS 'Funzione PURA (fn_check_*): dice se le righe di queste fatture sono gia'' state rettificate, cioe'' se qualcuno ha gia'' registrato un accredito su di esse. Ritorna [] oppure un array con {codice, reason, reason_key, dettaglio}. ⭐ Sede UNICA condivisa dalle tre porte di reset — riporta a draft, annulla lotto, elimina fattura — sullo stampo di script.fn_check_lotto_fatture_pre_fiscali: la correttezza di ognuna dipende dal fatto che facciano la stessa cosa. ⚠️ Guarda TUTTE E QUATTRO le figlie NO ACTION di vendite.fatture_righe (commesse_attivita, attivita_fatturabili, resi_righe_accrediti e l''auto-riferimento fatture_righe.riga_rettificata_id), perche'' sono la stessa cosa vista da quattro lati; l''auto-riferimento conta solo se la riga che rettifica sta FUORI dall''insieme cancellato, altrimenti si bloccherebbe il caso normale della nota di credito nello stesso lotto. ⛔ Rifiuta invece di azzerare il legame: quella colonna e'' il SECONDO TETTO dell''accredito (20260818-27 punto 2, «questa riga ha fatturato 10 pezzi, non se ne possono accreditare 11») e il DatiFattureCollegate della TD04 — toglierlo mentre le quantita'' vengono ri-derivate sarebbe il momento peggiore. La via d''uscita per l''operatore e'' vendite.fn_annulla_accredito_riga_reso, poi il reset. rev 2026-08-22.';
```

</div>

---
{% include-markdown "signature-core.md" %}
