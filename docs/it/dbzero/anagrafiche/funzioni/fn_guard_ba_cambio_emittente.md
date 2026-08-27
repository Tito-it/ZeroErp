{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente.md" %}
# ⚙️ Funzione `fn_guard_ba_cambio_emittente`

```sql
CREATE FUNCTION fn_guard_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Fail-fast: un billing account che ha gia' congelato il
    --   proprio emittente da qualche parte non lo cambia piu'.
    --   E' la forma «b» decisa in D-1 — libero finche' non c'e'
    --   storia, vietato dopo.
    --
    -- ⭐ IL PREDICATO NON STA PIU' QUI (§12.5.2): sta in
    --   script.fn_check_ba_cambio_emittente, che e' la STESSA
    --   funzione da cui la lista dei mapping prende il motivo per
    --   spegnere il cestino di riga. Non «coincidono»: sono la
    --   stessa riga di codice, e non possono divergere.
    --
    -- ⚠️ Si solleva il PRIMO motivo dell'array: l'ordine e' il
    --   contratto fra il tooltip e l'errore.
    -- =========================================================
    v_motivi := script.fn_check_ba_cambio_emittente(
                    p_billing_account_id, p_emittente_sr_prima, p_emittente_sr_dopo);

    IF v_motivi IS NULL OR jsonb_array_length(v_motivi) = 0 THEN
        RETURN;
    END IF;

    v_primo := v_motivi -> 0;

    -- ⚠️ Il `context` porta il dettaglio della check piu' il
    --   `reason`: il frontend che riceve il 409 e quello che
    --   legge la riga leggono la stessa parola.
    --   ⛔ Nessuna chiave `campo`: la classe e' CONFLITTO_STATO —
    --   «non c'e' un campo da correggere, e' la situazione che
    --   non lo consente».
    PERFORM script.fn_log_and_raise_error(
        'anagrafiche',
        'fn_guard_ba_cambio_emittente',
        v_primo ->> 'codice',
        COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
            || jsonb_build_object('reason', v_primo ->> 'reason'),
        NULL::uuid,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_ba_cambio_emittente(p_billing_account_id bigint, p_emittente_sr_prima bigint, p_emittente_sr_dopo bigint)
IS 'Guard fail-fast: un billing account che ha gia'' CONGELATO il proprio emittente da qualche parte non lo cambia piu''. Solleva il codice del PRIMO motivo restituito da script.fn_check_ba_cambio_emittente, coi suoi valori. ⭐ rev 2026-08-27 (§12.5.2): il predicato NON sta piu'' qui — la madre CHIAMA la check invece di riscriverla, ed e'' la stessa funzione da cui la lista dei mapping nel drawer dell''emittente prende il motivo per spegnere il cestino di riga. La differenza vale la riga: un test che confrontasse i due esiti proverebbe che OGGI coincidono, cosi'' si prova che NON POSSONO divergere, perche'' la regola sta scritta in un posto solo. Il presidio da scrivere non e'' «gli esiti coincidono», e'' «la madre non contiene piu'' il predicato» — asserzione strutturale su pg_get_functiondef. ⚠️ L''ORDINE dell''array e'' il contratto: si solleva il primo motivo, e un ordine diverso farebbe dire al tooltip del pulsante una cosa e all''errore del rifiuto un''altra, cioe'' il difetto di partenza spostato di un passo. ⭐ Perche'' esiste, nelle parole di Tid: «non puo'' scomparire un cliente che ha gia'' delle fatture con un emittente perche'' e'' andato ad un altro». La fattura NON segue il cliente — congela il proprio emittente — quindi spostare il billing account non riscrive la storia: LA ORFANA. ⭐ Forma «b» (decisione D-1): libero finche'' non c''e'' storia, vietato dopo, perche'' un billing account nasce gia'' agganciato all''emittente di chi lo crea e puo'' nascere sbagliato. La condizione «l''emittente cambia davvero» vive nella check ed e'' cio'' che tiene aperta la manutenzione ordinaria. ⚠️ SECURITY DEFINER: la check lo e'' per contare la storia sotto RLS, e questa lo resta per simmetria e perche'' il contesto dell''errore ne dipende. ⛔ Nessuna GUC di override e nessuna eccezione per il pregresso. ⚠️ Nessun controllo sui figli, ed e'' deliberato: quel caso lo respinge gia'' anagrafiche.fn_guard_albero_ba_emittente con un errore piu'' preciso. Piano: brief-db-motivo-rimozione-mapping-ba, N2.';
```

---
{% include-markdown "signature-core.md" %}
