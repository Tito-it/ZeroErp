{% include-markdown "it/dbzero/documenti/manual/fn_risolvi_template_applicabile.md" %}
# ⚙️ Funzione `fn_risolvi_template_applicabile`

```sql
CREATE FUNCTION fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(template_documento_id bigint, livello text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il modello che stampa un documento della sorgente
--   p_sorgente_tipo_id dell'emittente p_emittente_fiscale_id.
--   Strada B (brief-db-modelli-documento-standard §4.1 Q-2): se
--   l'emittente ha modelli che possono stampare per (tipo,
--   sorgente) vale il suo predefinito, e senza predefinito
--   stampabile e' un errore; se non ne ha, vale il predefinito
--   standard.
--   «Puo' stampare» = attivo, con una versione PUBBLICATA, attiva
--   e valida alla data operativa: gli stessi filtri con cui chi
--   stampa carica la versione (rev 20261020-26).
DECLARE
    -- tipo esplicito: la data operativa, non una colonna
    v_oggi         date;
    v_tipo         documenti.template_documenti.tipo_documento_output_id%TYPE;
    -- tipo esplicito: dei conteggi, non colonne
    v_n_tipi       integer;
    v_n_propri     integer;
    v_template_id  documenti.template_documenti.id%TYPE;
    v_standard_id  documenti.template_documenti.id%TYPE;
    v_tipo_nome    documenti.tipi_documento_output.descrizione%TYPE;
    v_sorgente     config.sorgenti.codice_interno%TYPE;
BEGIN
    -- 0) Argomenti: solo un chiamante rotto li manda male.
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid,
            'p_sorgente_tipo_id (obbligatorio, > 0)');
    END IF;
    IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('emittente_fiscale_id', p_emittente_fiscale_id),
            NULL::uuid,
            'p_emittente_fiscale_id (obbligatorio, > 0: l''emittente del documento)');
    END IF;
    IF p_tipo_documento_output_id IS NOT NULL AND p_tipo_documento_output_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('tipo_documento_output_id', p_tipo_documento_output_id),
            NULL::uuid,
            'p_tipo_documento_output_id (> 0 se indicato)');
    END IF;

    v_oggi := script.fn_data_operativa();

    -- 1) Il tipo di documento. Indicato: vale quello. Non indicato:
    --    si deduce solo se e' uno fra i modelli della sorgente che
    --    questo emittente puo' usare (i suoi e gli standard) e che
    --    possono stampare: una bozza di un altro tipo non conta.
    v_tipo := p_tipo_documento_output_id;
    IF v_tipo IS NULL THEN
        SELECT count(DISTINCT t.tipo_documento_output_id)::integer,
               min(t.tipo_documento_output_id)
          INTO v_n_tipi, v_tipo
          FROM documenti.template_documenti t
         WHERE t.sorgente_tipo_id = p_sorgente_tipo_id
           AND t.attivo
           AND (t.emittente_fiscale_id = p_emittente_fiscale_id OR t.standard)
           AND EXISTS (
                 SELECT 1
                   FROM documenti.template_documenti_versioni v
                  WHERE v.template_documento_id = t.id
                    AND v.stato = 'PUBBLICATA'
                    AND v.attivo
                    AND v.validita @> v_oggi);

        IF v_n_tipi > 1 THEN
            SELECT s.codice_interno INTO v_sorgente
              FROM config.sorgenti s
             WHERE s.id = p_sorgente_tipo_id;
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_AMBIGUO',
                jsonb_build_object(
                    'sorgente_tipo_id',     p_sorgente_tipo_id,
                    'emittente_fiscale_id', p_emittente_fiscale_id,
                    'tipi_candidati',       v_n_tipi),
                NULL::uuid,
                coalesce(v_sorgente::text, p_sorgente_tipo_id::text));
        END IF;
    END IF;

    IF v_tipo IS NOT NULL THEN
        SELECT o.descrizione INTO v_tipo_nome
          FROM documenti.tipi_documento_output o
         WHERE o.id = v_tipo;
    END IF;

    -- 2) I candidati della terna, in una lettura: quelli
    --    dell'emittente (contati, e il suo predefinito) e il
    --    predefinito standard. Candidato = puo' stampare.
    --    uq_template_documenti_default_attivo (NULLS NOT DISTINCT):
    --    al massimo un predefinito attivo per lato, quindi max() non
    --    sceglie fra due.
    SELECT count(*) FILTER (WHERE NOT t.standard)::integer,
           max(t.id) FILTER (WHERE NOT t.standard AND t.is_default),
           max(t.id) FILTER (WHERE t.standard AND t.is_default)
      INTO v_n_propri, v_template_id, v_standard_id
      FROM documenti.template_documenti t
     WHERE t.tipo_documento_output_id = v_tipo
       AND t.sorgente_tipo_id = p_sorgente_tipo_id
       AND (t.emittente_fiscale_id = p_emittente_fiscale_id OR t.standard)
       AND t.attivo
       AND EXISTS (
             SELECT 1
               FROM documenti.template_documenti_versioni v
              WHERE v.template_documento_id = t.id
                AND v.stato = 'PUBBLICATA'
                AND v.attivo
                AND v.validita @> v_oggi);

    -- 2a) Livello EMITTENTE: decide la presenza di modelli suoi che
    --     possono stampare, non il predefinito (strada B).
    IF v_n_propri > 0 THEN
        IF v_template_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO',
                jsonb_build_object(
                    'tipo_documento_output_id', v_tipo,
                    'sorgente_tipo_id',         p_sorgente_tipo_id,
                    'emittente_fiscale_id',     p_emittente_fiscale_id,
                    'modelli_stampabili',       v_n_propri),
                NULL::uuid,
                coalesce(v_tipo_nome::text, '?'));
        END IF;

        template_documento_id := v_template_id;
        livello := 'EMITTENTE';
        RETURN NEXT;
        RETURN;
    END IF;

    -- 2b) Livello STANDARD.
    IF v_standard_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_TEMPLATE_NON_RISOLTO',
            jsonb_build_object(
                'tipo_documento_output_id', v_tipo,
                'sorgente_tipo_id',         p_sorgente_tipo_id,
                'emittente_fiscale_id',     p_emittente_fiscale_id),
            NULL::uuid,
            coalesce(v_tipo_nome::text, '?'));
    END IF;

    template_documento_id := v_standard_id;
    livello := 'STANDARD';
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
IS 'Il modello che stampa un documento (2026-10-20, brief-db-modelli-documento-standard §4.1 Q-2, strada B di Tid). Conta solo un modello che PUO'' STAMPARE: attivo, con una versione PUBBLICATA, attiva e valida alla data operativa (rev 20261020-26: un modello attivo con la sola bozza non toglie lo standard). Livello EMITTENTE se l''emittente del documento ha modelli stampabili per (tipo, sorgente): vale il suo predefinito, se stampabile; altrimenti E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO (lo standard non entra). Livello STANDARD se non ne ha: il predefinito standard stampabile, altrimenti E_DOCUMENTI_TEMPLATE_NON_RISOLTO. Tipo di output facoltativo: si deduce solo se fra i modelli stampabili della sorgente utilizzabili dall''emittente ce n''e'' uno solo, altrimenti E_DOCUMENTI_TEMPLATE_AMBIGUO. Argomenti rotti: E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO. L''emittente e'' quello del documento, gia'' letto sotto RLS dal chiamante: niente scope qui. Restituisce una riga (template_documento_id, livello).';
```

---
{% include-markdown "signature-core.md" %}
