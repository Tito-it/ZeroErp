{% include-markdown "it/dbzero/vendite/manual/fn_get_data_minima_numerabile_lotto.md" %}
# ⚙️ Funzione `fn_get_data_minima_numerabile_lotto`

```sql
CREATE FUNCTION fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_pavimento vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La sola DATA del pavimento del lotto — la minDate del
    --   dialog. NULL = nessun pavimento.
    --
    -- Regole:
    --   - non decide niente: legge fn_get_pavimento_lotto e ne
    --     butta via l'origine;
    --   - la firma e' un CONTRATTO col backend e non cambia.
    -- =========================================================

    -- ℹ️ I guard (parametro, lotto inesistente o non visibile)
    --    stanno nella funzione che questa legge: qui sarebbero
    --    una seconda copia, e due copie divergono.
    SELECT pl.pavimento
      INTO v_pavimento
      FROM vendite.fn_get_pavimento_lotto(p_lotto_id) pl;

    RETURN v_pavimento;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)
IS 'La sola DATA del pavimento di un lotto: da quale data in poi tutte le sue fatture non numerate possono prendere un numero. NULL = nessun pavimento. ⭐ E'' la TARGA del cancello, non un secondo controllo: serve al frontend per aprire il DatePicker con minDate gia'' giusta, cosi'' il rifiuto diventa l''eccezione invece della norma. Se targa e cancello divergessero, comanda il cancello. ⭐ rev 2026-08-26: e'' diventata una LETTURA SOTTILE su vendite.fn_get_pavimento_lotto, che compone i due pavimenti (sequenza e limite di emissione) e dice anche QUALE ha deciso. Qui l''origine si butta via, e la ragione e'' che questa firma e'' un CONTRATTO: il backend la chiama in tre punti aspettandosi uno scalare e per il frontend e'' la minDate del dialog — cambiarla per aggiungere un''informazione che serve a un solo chiamante avrebbe fatto pagare a tutti il bisogno di uno. ⛔ Chi ha bisogno anche dell''origine (la porta di dichiarazione, per scegliere fra i due codici errore) chiama fn_get_pavimento_lotto direttamente. ℹ️ I guard — parametro non valido, lotto inesistente o non visibile — stanno nella funzione letta: qui sarebbero una seconda copia. ⚠️ Vale anche qui il FAIL-OPEN sotto RLS descritto in fn_get_pavimento_lotto. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
