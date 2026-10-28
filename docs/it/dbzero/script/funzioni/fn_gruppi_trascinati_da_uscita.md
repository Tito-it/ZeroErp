{% include-markdown "it/dbzero/script/manual/fn_gruppi_trascinati_da_uscita.md" %}
# ⚙️ Funzione `fn_gruppi_trascinati_da_uscita`

```sql
CREATE FUNCTION fn_gruppi_trascinati_da_uscita(p_lotto_id bigint, p_gruppo_key text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_gruppi_trascinati_da_uscita(p_lotto_id bigint, p_gruppo_key text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: gli ALTRI documenti del lotto che condividono una bozza
--        con p_gruppo_key, e che quindi tornerebbero «da emettere»
--        se quel documento uscisse dal giro.
-- Ritorna: array ORDINATO di gruppo_key, [] se non trascina nessuno.
-- ⚠️ Funzione PURA: nessuna scrittura, nessun raise di dominio.
DECLARE
    v_out jsonb;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_gruppi_trascinati_da_uscita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio (> 0)');
    END IF;

    IF COALESCE(btrim(p_gruppo_key), '') = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_gruppi_trascinati_da_uscita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_gruppo_key', 'valore', p_gruppo_key),
            NULL::uuid, 'p_gruppo_key obbligatorio');
    END IF;

    SELECT COALESCE(jsonb_agg(DISTINCT altri.gruppo_key
                              ORDER BY altri.gruppo_key), '[]'::jsonb)
      INTO v_out
      FROM script.vw_lotto_documento_righe mio
      JOIN script.vw_lotto_documento_righe altri
        ON  altri.lotto_id   = mio.lotto_id
        AND altri.fattura_id = mio.fattura_id
     WHERE mio.lotto_id     = p_lotto_id
       AND mio.gruppo_key   = p_gruppo_key
       AND altri.gruppo_key <> p_gruppo_key;

    RETURN COALESCE(v_out, '[]'::jsonb);
END;
$function$

COMMENT ON FUNCTION script.fn_gruppi_trascinati_da_uscita(p_lotto_id bigint, p_gruppo_key text)
IS 'Gli ALTRI documenti del lotto che condividono una bozza con quello indicato: se lui esce dal giro la bozza viene cancellata, e loro tornano «da emettere» con l''esito riportato a PENDING. Ritorna [] quando l''uscita non trascina nessuno — ed e'' il caso del documento caduto al PULL, che una bozza non l''ha mai avuta. ⭐ SEDE UNICA di tre consumatori: il conteggio sulla riga a video, la frase di conferma, e il reset che fa vendite.fn_escludi_documento_da_giro. Scritta tre volte, il giorno che una cambia l''operatore vede un numero e ne subisce un altro. ⛔ La bozza condivisa NON e'' un motivo di rifiuto (D-2b): rifiutare li'' lascerebbe bloccati anche i documenti di un''ALTRA bozza — il sequestro di partenza in forma piu'' stretta. Legge script.vw_lotto_documento_righe, dove vive la catena. Brief: brief-db-uscita-documento-dal-giro §5.4-bis.';
```

</div>

---
{% include-markdown "signature-core.md" %}
