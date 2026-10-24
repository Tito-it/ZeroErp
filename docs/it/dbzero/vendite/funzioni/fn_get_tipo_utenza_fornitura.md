{% include-markdown "it/dbzero/vendite/manual/fn_get_tipo_utenza_fornitura.md" %}
# ⚙️ Funzione `fn_get_tipo_utenza_fornitura`

```sql
CREATE FUNCTION fn_get_tipo_utenza_fornitura(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_tipo_utenza_fornitura(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire qual e' il TIPO D'USO della fornitura — domestico,
--   altri usi, condominio, pubblico — partendo dalla terna che ogni
--   testata di documento porta. E' il livello di ripiego dello
--   stadio A del risolutore IVA (D11): il gas di casa non paga come
--   il gas di uno stabilimento.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I2 / D11.
-- Ritorna: l'id del tipo utenza, oppure NULL se non c'e' una
--   fornitura attiva a quella data o se il tipo d'uso non e'
--   dichiarato. NON solleva: sono casi legittimi.
DECLARE
    v_contratto_id   vendite.contratti.id%TYPE;
    v_tipo_utenza_id config.tipi_utenze.id%TYPE;
BEGIN
    -- ⭐ Il predicato «contratto attivo» sta in un posto solo, e
    --    questa funzione lo CHIAMA — lo stesso che chiama il nucleo
    --    del pricing. Prezzo e aliquota della stessa riga vengono
    --    cosi' dalla stessa fornitura per costruzione.
    v_contratto_id := vendite.fn_get_contratto_attivo(
                          p_billing_account_id,
                          p_utility_id,
                          p_data_riferimento);

    IF v_contratto_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- ℹ️ Nessun LIMIT: uq_contratti_utilities_contratto_id
    --    garantisce UNA riga per contratto. Un LIMIT 1 qui non
    --    sarebbe una precauzione, sarebbe rumore che nasconde un
    --    vincolo — e senza ORDER BY sarebbe una scommessa.
    SELECT cu.tipo_utenza_id
      INTO v_tipo_utenza_id
      FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = v_contratto_id;

    RETURN v_tipo_utenza_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_tipo_utenza_fornitura(p_billing_account_id bigint, p_utility_id integer, p_data_riferimento date)
IS 'Dato (billing account, utility, data) ritorna il TIPO D''USO della fornitura — domestico, altri usi, condominio, pubblico. E'' il livello di ripiego dello stadio A del risolutore IVA (D11): il gas di casa non paga come il gas di uno stabilimento, e quell''informazione sta in config.tipi_utenze, che si raggiunge solo via vendite.contratti_utilities.contratto_id. ⭐ NON contiene il predicato «contratto attivo»: lo CHIAMA da vendite.fn_get_contratto_attivo, la stessa funzione che usa il nucleo del pricing. La prima stesura lo ricopiava dichiarando il debito; Tid ha scelto di estrarlo, e cosi'' non c''e'' piu'' niente da tenere allineato — prezzo e aliquota della stessa riga vengono dalla stessa fornitura per COSTRUZIONE, non per disciplina. ℹ️ Nessun LIMIT sulla lettura di contratti_utilities: uq_contratti_utilities_contratto_id garantisce una riga per contratto, e un LIMIT senza ORDER BY sarebbe una scommessa che nasconde un vincolo. ⚠️ Ritorna NULL e non solleva: nessun contratto attivo, un contratto senza riga utility o un tipo d''uso non dichiarato sono tutti casi legittimi — un preventivo a un cliente nuovo non ha ancora nessuna fornitura, e nel risolutore «non lo so» significa che il ripiego non si applica e vale quel che dice l''articolo. STABLE, sola lettura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
