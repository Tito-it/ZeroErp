{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_guard_contesto.md" %}
# ⚙️ Funzione `trgfn_pratiche_guard_contesto`

```sql
CREATE FUNCTION trgfn_pratiche_guard_contesto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: validare la coerenza del contesto anagrafico sulla pratica
--        nel modello a DUE RAMI indipendenti dal soggetto:
--            soggetto -> soggetto_ruolo   (pratiche su ruoli)
--            soggetto -> istanza_utility  (pratiche pre-contrattuali)
--        L'istanza puo' essere agganciata senza ruolo sulla pratica.
--        ⚠️ rev 2026-10-08: non e' piu' un «prospect puro» — l'istanza
--        nasce col suo billing account, e il ruolo CLIENTE con lui
--        (brief-db-istanza-nasce-col-ba). Il BA della pratica
--        (billing_account_id, aggancio a grana fine del cliente) e'
--        del ruolo della pratica: regola 5.
--        Tutti i campi sono opzionali (pratica interna = tutti NULL).
-- Regole:
--   1. soggetto_ruolo_id NOT NULL -> soggetto_id obbligatorio
--   2. istanza_utility_id NOT NULL -> soggetto_id obbligatorio
--   3. soggetto_ruolo_id deve appartenere a soggetto_id
--   4. istanza_utility_id deve appartenere a soggetto_id
--   5. billing_account_id deve essere del soggetto_ruolo_id
--      (l'istanza la lega la FK composta, la presenza dell'istanza
--      chk_pratiche_ba_con_istanza)
-- rev 2026-10-19 (D-17b di brief-db-processi-accensione-per-
--   ambiente §6.17.1): le regole 3 e 4 dai BB
--   anagrafiche.fn_ruolo_di_altro_soggetto e
--   fn_istanza_di_altro_soggetto, comuni ai guard di indirizzi,
--   contatti, conti del ruolo e BA. Un ruolo o un'istanza che
--   non esistono li rifiuta la FK, non piu' queste regole.
DECLARE
    v_soggetto_id_ruolo   anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_id_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
    v_ba_ruolo_id         anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_ba_codice           anagrafiche.billing_account.codice%TYPE;
BEGIN
    -- Regola 1: ruolo richiede soggetto (ramo ruolo)
    IF NEW.soggetto_ruolo_id IS NOT NULL AND NEW.soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'E_PRATICHE_RUOLO_SENZA_SOGGETTO',
            jsonb_build_object(
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    -- Regola 2: istanza richiede soggetto (ramo istanza, indipendente
    --           dal ruolo). Sostituisce la vecchia regola istanza=>ruolo.
    IF NEW.istanza_utility_id IS NOT NULL AND NEW.soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'E_PRATICHE_ISTANZA_SENZA_SOGGETTO',
            jsonb_build_object(
                'istanza_utility_id', NEW.istanza_utility_id
            ),
            NULL::uuid,
            NEW.istanza_utility_id::text
        );
    END IF;

    -- Regola 3: ruolo deve appartenere al soggetto
    v_soggetto_id_ruolo := anagrafiche.fn_ruolo_di_altro_soggetto(
        NEW.soggetto_ruolo_id, NEW.soggetto_id);

    IF v_soggetto_id_ruolo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'E_PRATICHE_RUOLO_NON_COERENTE',
            jsonb_build_object(
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                'soggetto_id', NEW.soggetto_id,
                'soggetto_id_ruolo', v_soggetto_id_ruolo
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text,
            NEW.soggetto_id::text
        );
    END IF;

    -- Regola 4: istanza deve appartenere al soggetto
    v_soggetto_id_istanza := anagrafiche.fn_istanza_di_altro_soggetto(
        NEW.istanza_utility_id, NEW.soggetto_id);

    IF v_soggetto_id_istanza IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_contesto',
            'E_PRATICHE_ISTANZA_NON_COERENTE',
            jsonb_build_object(
                'istanza_utility_id', NEW.istanza_utility_id,
                'soggetto_id', NEW.soggetto_id,
                'soggetto_id_istanza', v_soggetto_id_istanza
            ),
            NULL::uuid,
            NEW.istanza_utility_id::text,
            NEW.soggetto_id::text
        );
    END IF;

    -- Regola 5: il BA della pratica e' del ruolo della pratica.
    --   Un ruolo NULL con un BA e' incoerente quanto un ruolo diverso:
    --   il BA dice di quale cliente parla la pratica, il ruolo chi e'.
    IF NEW.billing_account_id IS NOT NULL THEN
        SELECT ba.soggetto_ruolo_id, ba.codice
          INTO v_ba_ruolo_id, v_ba_codice
          FROM anagrafiche.billing_account ba
         WHERE ba.id = NEW.billing_account_id;

        IF v_ba_ruolo_id IS NULL
           OR v_ba_ruolo_id IS DISTINCT FROM NEW.soggetto_ruolo_id THEN
            PERFORM script.fn_log_and_raise_error(
                'pratiche',
                'pratiche.trgfn_pratiche_guard_contesto',
                'E_PRATICHE_BA_NON_COERENTE',
                jsonb_build_object(
                    'campo', 'billing_account_id',
                    'billing_account_id', NEW.billing_account_id,
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                    'soggetto_ruolo_id_ba', v_ba_ruolo_id
                ),
                NULL::uuid,
                COALESCE(v_ba_codice::text, NEW.billing_account_id::text)
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_contesto()
IS 'BEFORE INSERT OR UPDATE su pratiche.pratiche: coerenza del contesto anagrafico (soggetto / soggetto_ruolo / istanza_utility / billing_account). Codici rinominati il 2026-08-05 (20260805-20): E_PRATICHE_RUOLO_SENZA_SOGGETTO (846), E_PRATICHE_RUOLO_NON_COERENTE (847), E_PRATICHE_ISTANZA_NON_COERENTE (848), E_PRATICHE_ISTANZA_SENZA_SOGGETTO (849). I vecchi nomi senza prefisso restano a catalogo, ritirati con obsoleto_dal. rev 2026-10-08 (20261008-66): regola 5, il billing account della pratica e'' del suo ruolo (E_PRATICHE_BA_NON_COERENTE); il trigger scatta anche su billing_account_id. Brief: brief-db-istanza-nasce-col-ba (R-8, D-9). rev 2026-10-19 (20261019-85, D-17b di brief-db-processi-accensione-per-ambiente §6.17.1): regole 3 e 4 dai BB anagrafiche.fn_ruolo_di_altro_soggetto e fn_istanza_di_altro_soggetto (regola del 2); un ruolo o un''istanza che non esistono li rifiuta la FK.';
```

</div>

---
{% include-markdown "signature-core.md" %}
