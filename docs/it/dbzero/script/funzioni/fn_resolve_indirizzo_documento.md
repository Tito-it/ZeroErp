{% include-markdown "it/dbzero/script/manual/fn_resolve_indirizzo_documento.md" %}
# ⚙️ Funzione `fn_resolve_indirizzo_documento`

```sql
CREATE FUNCTION fn_resolve_indirizzo_documento(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_codice character varying)
 RETURNS TABLE(snapshot jsonb, origine_indirizzo_id bigint, origine_soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: rispondere alla domanda «da dove prende l'indirizzo di
--        tipo X questo documento», UNA volta sola per tutto il
--        sistema. Due layer, con precedenza all'istanza utility.
-- Uso:   task di snapshot dei documenti + mixin Python (via BE).
DECLARE
    v_tipo_id      config.tipi_indirizzi.id%TYPE;
    v_indirizzo_id anagrafiche.indirizzi.id%TYPE;
    v_soggetto_id  anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_snapshot     jsonb;
    v_origine_sr   anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- ===== Guard parametri =====
    IF p_soggetto_ruolo_id IS NULL OR p_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_resolve_indirizzo_documento', 'E_VALIDAZIONE',
            jsonb_build_object('p_soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid, 'p_soggetto_ruolo_id deve essere > 0');
    END IF;

    -- L'istanza e' OPZIONALE (documenti non legati a una utility),
    -- ma se c'e' deve essere un id valido: zero o negativo e'
    -- un errore del chiamante, non «nessuna istanza».
    IF p_istanza_utility_id IS NOT NULL AND p_istanza_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_resolve_indirizzo_documento', 'E_VALIDAZIONE',
            jsonb_build_object('p_istanza_utility_id', p_istanza_utility_id),
            NULL::uuid, 'p_istanza_utility_id se fornito deve essere > 0');
    END IF;

    IF p_tipo_codice IS NULL OR btrim(p_tipo_codice) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_resolve_indirizzo_documento', 'E_VALIDAZIONE',
            jsonb_build_object('p_tipo_codice', p_tipo_codice),
            NULL::uuid, 'p_tipo_codice obbligatorio');
    END IF;

    -- Tipo per codice_interno (immutabile), mai per codice.
    SELECT t.id INTO v_tipo_id
      FROM config.tipi_indirizzi t
     WHERE t.codice_interno = p_tipo_codice;

    IF v_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_resolve_indirizzo_documento', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', p_tipo_codice),
            NULL::uuid, concat('tipo indirizzo non configurato: ', p_tipo_codice));
    END IF;

    -- ===== Layer 1: RUOLO, con precedenza per ISTANZA =====
    -- I candidati sono al massimo due (le due unique parziali):
    -- quello dell'istanza richiesta e quello generico. L'ORDER BY
    -- su (istanza IS NULL) mette il primo davanti — i booleani
    -- ordinano false prima di true — quindi la scelta e'
    -- deterministica, non un LIMIT 1 lasciato al caso.
    -- Se p_istanza_utility_id e' NULL il confronto non e' mai vero
    -- e resta solo il generico: comportamento corretto per i
    -- documenti che non hanno una utility.
    SELECT i.id INTO v_indirizzo_id
      FROM anagrafiche.indirizzi i
     WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
       AND i.tipo_indirizzo_id = v_tipo_id
       AND (i.istanza_utility_id = p_istanza_utility_id
            OR i.istanza_utility_id IS NULL)
     ORDER BY (i.istanza_utility_id IS NULL)
     LIMIT 1;

    IF v_indirizzo_id IS NOT NULL THEN
        -- Composizione delegata: mai snapshot fatti a mano (D-5).
        -- fn_snapshot_indirizzo solleva se non trova l'id, ma qui
        -- non puo' accadere: l'id arriva da anagrafiche.indirizzi
        -- filtrato per soggetto_ruolo, e la vista che lei legge fa
        -- INNER JOIN proprio su soggetti_ruoli.
        SELECT s.snapshot, s.origine_soggetto_ruolo_id
          INTO v_snapshot, v_origine_sr
          FROM script.fn_snapshot_indirizzo(v_indirizzo_id) s;

        snapshot                  := v_snapshot;
        origine_indirizzo_id      := v_indirizzo_id;
        origine_soggetto_ruolo_id := v_origine_sr;
        RETURN NEXT;
        RETURN;
    END IF;

    -- ===== Layer 2: SOGGETTO (fallback) =====
    SELECT sr.soggetto_id INTO v_soggetto_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF v_soggetto_id IS NOT NULL THEN
        SELECT s.snapshot INTO v_snapshot
          FROM script.fn_snapshot_indirizzo_soggetto(v_soggetto_id, v_tipo_id) s;

        IF v_snapshot IS NOT NULL THEN
            -- origine_indirizzo_id NULL + origine_soggetto_ruolo_id
            -- valorizzato: e' la coppia che dice «viene
            -- dall'anagrafica del soggetto» e lo distingue da un
            -- una-tantum digitato a mano.
            snapshot                  := v_snapshot;
            origine_indirizzo_id      := NULL;
            origine_soggetto_ruolo_id := p_soggetto_ruolo_id;
            RETURN NEXT;
            RETURN;
        END IF;
    END IF;

    -- Nessun layer ha risposto: zero righe. Se quel tipo di
    -- indirizzo sia obbligatorio lo sa il chiamante, non questa.
    RETURN;
END;
$function$

COMMENT ON FUNCTION script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_codice character varying)
IS 'Catena UNICA di risoluzione dell''indirizzo di un documento, condivisa da tutti i domini: layer RUOLO (anagrafiche.indirizzi, con origine_indirizzo_id agganciato) e, come fallback, layer SOGGETTO (anagrafiche.indirizzi_soggetti, origine_indirizzo_id NULL + origine_soggetto_ruolo_id valorizzato — la coppia che distingue «derivato dall''anagrafica del soggetto» da un una-tantum digitato). PRECEDENZA PER ISTANZA UTILITY, poi il generico: un soggetto_ruolo puo'' avere piu'' indirizzi dello stesso tipo (uq_indirizzi_ruolo_istanza_tipo + uq_indirizzi_ruolo_tipo_no_istanza), e in un ERP di utilities la stessa persona con luce, gas e idrico e'' UN ruolo con TRE istanze. Determinismo garantito dalle due unique parziali: i candidati sono al massimo due e l''ORDER BY sceglie fra quelli. Composizione dello snapshot sempre delegata a fn_snapshot_indirizzo / fn_snapshot_indirizzo_soggetto, mai a mano (D-5). Assenza = ZERO RIGHE e non errore: l''obbligatorieta'' di un tipo la conosce il chiamante. STABLE. piano-db-satelliti-fattura C-14b, Fase 2.0-b.';
```

</div>

---
{% include-markdown "signature-core.md" %}
