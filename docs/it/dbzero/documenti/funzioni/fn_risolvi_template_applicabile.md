{% include-markdown "it/dbzero/documenti/manual/fn_risolvi_template_applicabile.md" %}
# ⚙️ Funzione `fn_risolvi_template_applicabile`

```sql
CREATE FUNCTION fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint, p_template_documento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint DEFAULT NULL::bigint, p_template_documento_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(template_documento_id bigint, livello text, template_versione_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il modello e la versione con cui si stampa un documento
--   della sorgente p_sorgente_tipo_id dell'emittente
--   p_emittente_fiscale_id. La porta unica (rev 20261021-09,
--   brief-db-modelli-documento-standard §10.3 K-2):
--   * senza p_template_documento_id: strada B (§4.1 Q-2), il
--     modello lo sceglie la regola dei due livelli
--     (fn_template_esito_risoluzione);
--   * con p_template_documento_id: il modello indicato si verifica,
--     coerenza col documento (fn_template_motivo_non_coerente) e
--     stampabilita' oggi (vw_template_versioni_stampabili).
--   «Puo' stampare» sta nella vista, una volta sola.
DECLARE
    v_tipo         documenti.template_documenti.tipo_documento_output_id%TYPE;
    -- tipo esplicito: conteggi e motivi, non colonne
    v_n_tipi       integer;
    v_motivo       text;
    v_esito        text;
    v_n_propri     integer;
    v_template_id  documenti.template_documenti.id%TYPE;
    v_versione_id  documenti.template_documenti_versioni.id%TYPE;
    v_attivo       documenti.template_documenti.attivo%TYPE;
    v_codice       documenti.template_documenti.codice%TYPE;
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
    IF p_template_documento_id IS NOT NULL AND p_template_documento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('template_documento_id', p_template_documento_id),
            NULL::uuid,
            'p_template_documento_id (> 0 se indicato)');
    END IF;

    -- A) Il modello indicato: si verifica, non si sceglie.
    IF p_template_documento_id IS NOT NULL THEN
        v_motivo := documenti.fn_template_motivo_non_coerente(
            p_template_documento_id, p_sorgente_tipo_id,
            p_emittente_fiscale_id, p_tipo_documento_output_id);

        IF v_motivo = 'MODELLO_INESISTENTE' THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
                jsonb_build_object('template_documento_id', p_template_documento_id),
                NULL::uuid,
                'p_template_documento_id (non e'' un modello)');
        END IF;

        SELECT t.codice, t.attivo INTO v_codice, v_attivo
          FROM documenti.template_documenti t
         WHERE t.id = p_template_documento_id;

        IF v_motivo IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_NON_COERENTE',
                jsonb_build_object(
                    'template_documento_id',    p_template_documento_id,
                    'motivo',                   v_motivo,
                    'sorgente_tipo_id',         p_sorgente_tipo_id,
                    'tipo_documento_output_id', p_tipo_documento_output_id,
                    'emittente_fiscale_id',     p_emittente_fiscale_id),
                NULL::uuid,
                v_codice::text,
                CASE v_motivo
                  WHEN 'SORGENTE'  THEN 'è per un''altra sorgente'
                  WHEN 'TIPO'      THEN 'produce un altro tipo di documento'
                  WHEN 'EMITTENTE' THEN 'è di un''altra azienda'
                END);
        END IF;

        SELECT s.template_versione_id INTO v_versione_id
          FROM documenti.vw_template_versioni_stampabili s
         WHERE s.template_documento_id = p_template_documento_id;

        IF v_versione_id IS NULL THEN
            v_motivo := CASE WHEN v_attivo THEN 'NESSUNA_VERSIONE_VALIDA'
                             ELSE 'MODELLO_SPENTO' END;
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_NON_STAMPABILE',
                jsonb_build_object(
                    'template_documento_id', p_template_documento_id,
                    'motivo',                v_motivo),
                NULL::uuid,
                v_codice::text,
                CASE v_motivo
                  WHEN 'MODELLO_SPENTO' THEN 'è disattivato'
                  ELSE 'non ha una versione pubblicata valida oggi'
                END);
        END IF;

        template_documento_id := p_template_documento_id;
        livello := 'INDICATO';
        template_versione_id := v_versione_id;
        RETURN NEXT;
        RETURN;
    END IF;

    -- 1) Il tipo di documento. Indicato: vale quello. Non indicato:
    --    si deduce solo se e' uno fra i modelli della sorgente che
    --    questo emittente puo' usare (i suoi e gli standard) e che
    --    possono stampare: una bozza di un altro tipo non conta.
    v_tipo := p_tipo_documento_output_id;
    IF v_tipo IS NULL THEN
        SELECT count(DISTINCT s.tipo_documento_output_id)::integer,
               min(s.tipo_documento_output_id)
          INTO v_n_tipi, v_tipo
          FROM documenti.vw_template_versioni_stampabili s
         WHERE s.sorgente_tipo_id = p_sorgente_tipo_id
           AND (s.emittente_fiscale_id = p_emittente_fiscale_id OR s.standard);

        IF v_n_tipi > 1 THEN
            SELECT so.codice_interno INTO v_sorgente
              FROM config.sorgenti so
             WHERE so.id = p_sorgente_tipo_id;
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

    -- 2) L'esito dei due livelli: la regola e' del BB. Qui si
    --    traducono gli esiti negativi nei loro codici.
    SELECT r.esito, r.template_documento_id, r.template_versione_id, r.modelli_stampabili
      INTO v_esito, v_template_id, v_versione_id, v_n_propri
      FROM documenti.fn_template_esito_risoluzione(
             p_emittente_fiscale_id, v_tipo, p_sorgente_tipo_id) r;

    IF v_esito = 'SENZA_PREDEFINITO' THEN
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

    IF v_esito = 'NON_RISOLTO' THEN
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

    template_documento_id := v_template_id;
    livello := v_esito;
    template_versione_id := v_versione_id;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint, p_template_documento_id bigint)
IS 'La porta unica: il modello e la versione con cui si stampa un documento (2026-10-21, brief-db-modelli-documento-standard §10.3 K-2, D-4 di Tid). Senza p_template_documento_id: strada B (§4.1 Q-2), l''esito di documenti.fn_template_esito_risoluzione; livello EMITTENTE (il suo predefinito stampabile) o STANDARD (il predefinito standard stampabile); E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO se l''emittente ha modelli suoi stampabili ma nessuno predefinito (lo standard non entra), E_DOCUMENTI_TEMPLATE_NON_RISOLTO se non stampa nemmeno lo standard. Tipo di output facoltativo: si deduce solo se fra i modelli stampabili della sorgente utilizzabili dall''emittente ce n''e'' uno solo, altrimenti E_DOCUMENTI_TEMPLATE_AMBIGUO. Con p_template_documento_id: il modello indicato si verifica, livello INDICATO; E_DOCUMENTI_TEMPLATE_NON_COERENTE se non e'' adatto al documento (motivo SORGENTE, TIPO, EMITTENTE: documenti.fn_template_motivo_non_coerente), E_DOCUMENTI_TEMPLATE_NON_STAMPABILE se oggi non puo'' stampare (motivo MODELLO_SPENTO, NESSUNA_VERSIONE_VALIDA). «Puo'' stampare» = documenti.vw_template_versioni_stampabili. Argomenti rotti, o un id che non e'' un modello: E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO. L''emittente e'' quello del documento, gia'' letto sotto RLS dal chiamante: niente scope qui. Restituisce una riga (template_documento_id, livello, template_versione_id).';
```

</div>

---
{% include-markdown "signature-core.md" %}
