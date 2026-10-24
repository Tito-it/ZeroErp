{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_pk`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la PK reale (anagrafiche.emittenti_fiscali.id) dell'emittente
--   che fattura un billing account, per chi SCRIVE: solleva se non
--   e' risolvibile. E' l'involucro PK del lettore
--   script.fn_get_ba_emittente_sr_id, come
--   anagrafiche.fn_get_emittente_fiscale_id ne e' l'involucro SR.
-- ⛔ La regola «quale emittente» NON e' scritta qui (rev 20260913-03,
--   D13): fino a quel giorno questa funzione ne teneva una copia a
--   due livelli, e con il terzo livello del lettore (in sessione,
--   l'emittente di chi agisce) le due copie avrebbero risposto cose
--   diverse sullo stesso BA senza legame.
DECLARE
    v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- Guard sul parametro: invariato (codice, frase, contesto).
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_billing_account_id obbligatorio e > 0',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    -- Traduzione soggetto_ruolo -> PK reale. Il filtro ef.attivo
    -- c'era gia' e resta come DIFESA: sul modello un emittente con
    -- una riga di mapping non si puo' disattivare
    -- (trgfn_prevent_deactivate_if_children), quindi il ramo non e'
    -- raggiungibile — se lo fosse, «non risolto» e' la risposta
    -- giusta, non un ripiego silenzioso su un'altra azienda.
    SELECT ef.id
      INTO v_emittente_fiscale_id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id
               = script.fn_get_ba_emittente_sr_id(p_billing_account_id)
       AND ef.attivo = true;

    -- Niente da nessuno dei tre livelli: e' l'installazione che
    -- manca di un emittente, non il chiamante. Invariato.
    IF v_emittente_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_EMITTENTE_DEFAULT_MISSING',
            jsonb_build_object(
                'detail', 'Emittente fiscale di default mancante o disattivato',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            concat('Emittente fiscale di default mancante per billing_account_id ',
                   p_billing_account_id::text)
        );
    END IF;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
IS 'Restituisce anagrafiche.emittenti_fiscali.id (PK numerica reale) per un billing_account, e SOLLEVA se non e'' risolvibile. ⭐ Dal 20260913-03 (D13) non riscrive piu'' la regola: e'' l''involucro PK di script.fn_get_ba_emittente_sr_id — la stessa coppia lettore/involucro di anagrafiche.fn_get_emittente_fiscale_id, che ne e'' l''involucro SR. La regola ha TRE livelli: mapping specifico; altrimenti, in sessione, l''emittente dell''operatore che sta agendo; altrimenti il default. Qui restano il guard sul parametro (E_PARAMETRO_INVALIDO su NULL o <= 0), la traduzione soggetto_ruolo -> PK con il filtro ef.attivo (difesa: sul modello un emittente con una riga di mapping non si disattiva) e E_EMITTENTE_DEFAULT_MISSING quando nessun livello risponde. Fino a quel changeSet teneva una copia a due livelli della regola, e con il terzo livello del lettore le due copie avrebbero risposto cose diverse sullo stesso BA senza legame — la RLS lo mostra, il guard del documento lo rifiuta. Consumatori: trgfn_<doc>_guard_emittente_ba (preventivi, ordini, ddt, resi, contratti, offerte), trgfn_ddt_normalize, trgfn_resi_normalize, fn_lookup_utilities_per_ba, fn_genera_pratica_da_preventivo, il backend. Brief: brief-db-ba-riserva-emittente-operatore-d13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
