{% include-markdown "it/dbzero/script/manual/fn_arrotonda_importo.md" %}
# ⚙️ Funzione `fn_arrotonda_importo`

```sql
CREATE FUNCTION fn_arrotonda_importo(p_valore numeric, p_decimali integer, p_metodo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_arrotonda_importo(p_valore numeric, p_decimali integer, p_metodo text)
 RETURNS numeric
 LANGUAGE plpgsql
 STRICT
AS $function$
-- Scopo: arrotondare un importo secondo decimali e metodo
--        configurati, in UN punto solo per tutto il database.
-- Vocabolario unico (20260728-07):
--   UP        allontana da zero
--   DOWN      avvicina a zero
--   HALF_UP   sul mezzo allontana da zero
--   HALF_DOWN sul mezzo avvicina a zero
-- brief-fix-importi-riga-fattura-zero §4.1.
DECLARE
    v_scala   numeric;
    v_scalato numeric;
    v_intero  numeric;
BEGIN
    IF p_decimali < 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_arrotonda_importo', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_decimali', 'valore', p_decimali),
            NULL::uuid, 'p_decimali deve essere >= 0'
        );
    END IF;

    v_scala   := power(10::numeric, p_decimali);
    v_scalato := p_valore * v_scala;

    CASE upper(btrim(p_metodo))

        WHEN 'UP' THEN
            v_intero := CASE WHEN v_scalato >= 0
                             THEN  ceil(v_scalato)
                             ELSE -ceil(abs(v_scalato))
                        END;

        WHEN 'DOWN' THEN
            v_intero := CASE WHEN v_scalato >= 0
                             THEN  floor(v_scalato)
                             ELSE -floor(abs(v_scalato))
                        END;

        WHEN 'HALF_UP' THEN
            v_intero := CASE WHEN v_scalato >= 0
                             THEN  floor(v_scalato + 0.5)
                             ELSE -floor(abs(v_scalato) + 0.5)
                        END;

        WHEN 'HALF_DOWN' THEN
            v_intero := CASE WHEN v_scalato >= 0
                             THEN  ceil(v_scalato - 0.5)
                             ELSE -ceil(abs(v_scalato) - 0.5)
                        END;

        ELSE
            -- Un metodo non riconosciuto e' una configurazione
            -- sbagliata, e deve fermarsi qui invece di diventare
            -- un importo sbagliato che nessuno nota.
            PERFORM script.fn_log_and_raise_error(
                'script', 'fn_arrotonda_importo', 'E_PARAMETRO_INVALIDO',
                jsonb_build_object(
                    'parametro', 'p_metodo',
                    'valore',    p_metodo,
                    'ammessi',   'UP,DOWN,HALF_UP,HALF_DOWN'),
                NULL::uuid,
                concat('metodo di arrotondamento non riconosciuto: ', p_metodo)
            );
    END CASE;

    RETURN v_intero / v_scala;
END;
$function$

COMMENT ON FUNCTION script.fn_arrotonda_importo(p_valore numeric, p_decimali integer, p_metodo text)
IS 'Arrotonda un importo secondo decimali e metodo configurati, in UN punto solo per tutto il database. Vocabolario unico del modello (20260728-07): UP = allontana da zero, DOWN = avvicina a zero, HALF_UP = sul mezzo allontana, HALF_DOWN = sul mezzo avvicina. Estratta dal CASE inline di vendite.fn_ricalcola_totali_fattura, di cui conserva esattamente la semantica sui negativi (ceil/floor sull''assoluto col segno riapplicato). ⚠️ Un metodo non riconosciuto SOLLEVA E_PARAMETRO_INVALIDO invece di cadere in un default silenzioso: il CASE inline assorbiva l''ignoto in HALF_UP, e un importo sbagliato che sembra giusto e'' il peggiore dei casi. STRICT: guardare i parametri spetta ai chiamanti, che gia'' lo fanno. VOLATILE perche'' l''errore passa dal canale di log. brief-fix-importi-riga-fattura-zero §4.1, rev 2026-07-28.';
```

</div>

---
{% include-markdown "signature-core.md" %}
