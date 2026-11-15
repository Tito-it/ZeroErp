{% include-markdown "it/dbzero/script/manual/fn_check_famiglia_documento_disattivabile.md" %}
# ⚙️ Funzione `fn_check_famiglia_documento_disattivabile`

```sql
CREATE FUNCTION fn_check_famiglia_documento_disattivabile(p_famiglia_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_famiglia_documento_disattivabile(p_famiglia_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la tabella dei documenti e' la target_table della sorgente
--   (config.fn_sorgente_tabella), non piu' schema_tabella/nome_tabella
--   della famiglia; p_famiglia_id ancorato.
DECLARE
    v_motivi   jsonb := '[]'::jsonb;
    v_fam      record;
    v_relid    pg_catalog.pg_class.oid%TYPE;
    v_schema   pg_catalog.pg_namespace.nspname%TYPE;
    v_nome     pg_catalog.pg_class.relname%TYPE;
    -- due conteggi: nessuna colonna di cui siano il riflesso
    v_registri bigint;
    v_docs     bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di SPEGNERE una
    --   famiglia di documento. Funzione PURA (fn_check_*):
    --   nessuna scrittura, nessun raise di dominio.
    --   Consumatori: il guard che rifiuta l'UPDATE, e la lista
    --   del CRUD, che tiene il cestino spento e dice PERCHE'.
    --
    -- Ritorna: [] se si puo' spegnere; altrimenti array ORDINATO
    --   di {codice, reason, reason_key, dettaglio}
    --   (§12.5.1).
    --
    -- ⛔ PERCHE' ESISTE: anagrafiche.fn_ba_ha_storia_emittente
    --   itera `WHERE fd.attivo`. Spegnere una famiglia la toglie
    --   dal presidio sul cambio emittente del billing account: i
    --   suoi documenti smettono di trattenere il BA dove sono
    --   stati numerati, e nessuno se ne accorge.
    --
    -- ⚠️ SECURITY DEFINER: le cinque tabelle dei documenti hanno
    --   la RLS attiva. Un conteggio invoker tornerebbe zero a chi
    --   non le vede, e zero qui vuol dire «spegnila pure» —
    --   fail-open che non fallisce mai.
    -- =========================================================

    -- Guard di parametro: un id assente o non positivo non esce
    -- da nessuna interfaccia, lo produce un chiamante rotto.
    IF p_famiglia_id IS NULL OR p_famiglia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_famiglia_documento_disattivabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_famiglia_id',
                               'valore', p_famiglia_id),
            NULL::uuid,
            'script.fn_check_famiglia_documento_disattivabile',
            'identificativo della famiglia non valido');
    END IF;

    SELECT f.codice_interno, f.descrizione, f.colonna_numero
      INTO v_fam
      FROM vendite.famiglie_documento f
     WHERE f.id = p_famiglia_id;

    -- ⭐ E non si risponde []: sarebbe «si puo' spegnere», che su
    --   una riga inesistente e' una frase senza senso. Stesso
    --   ramo delle gemelle sui registri.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_famiglia_documento_disattivabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('famiglia_id', p_famiglia_id),
            NULL::uuid,
            'script.fn_check_famiglia_documento_disattivabile',
            concat('famiglia di documento ', p_famiglia_id, ' inesistente'));
    END IF;

    -- ---- MOTIVO 1 — registri ancora accesi ------------------
    -- ⭐ Va per PRIMO perche' e' quello RIMEDIABILE: la madre
    --   solleva il primo motivo, e all'operatore va detta la cosa
    --   che puo' fare, non quella che non puo' fare.
    -- ⚠️ `attivo` e non l'esistenza: un registro spento non
    --   numera piu' niente, e tenerlo in conto vieterebbe per
    --   sempre lo spegnimento di una famiglia gia' ritirata.
    SELECT count(*)
      INTO v_registri
      FROM vendite.registri_fatturazione r
     WHERE r.famiglia_documento = v_fam.codice_interno
       AND r.attivo;

    IF v_registri > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
            'reason',     'HA_REGISTRI_ATTIVI',
            'reason_key', 'amministrazione.famiglie_documento.disattiva_blocco.ha_registri_attivi',
            'dettaglio',  jsonb_build_object('famiglia_id',    p_famiglia_id,
                                             'codice_interno', v_fam.codice_interno,
                                             'registri',       v_registri));
    END IF;

    -- ---- MOTIVO 2 — documenti gia' numerati ----------------
    -- ⚠️ rev 2026-10-20: la tabella e' la target_table della sorgente
    --   (G-5). Se la sorgente non ne dichiara una, nessuna riga: la
    --   check risponde, non esplode.
    SELECT t.relid, t.schema_tabella, t.nome_tabella
      INTO v_relid, v_schema, v_nome
      FROM config.fn_sorgente_tabella(v_fam.codice_interno) t;

    IF v_relid IS NOT NULL THEN
        -- ⭐ Il predicato e' «porta un numero», lo stesso di
        --   anagrafiche.fn_get_storia_emittente_ba: non basta che
        --   la riga esista, deve avere consumato il contatore.
        EXECUTE format(
            'SELECT count(*) FROM %I.%I d'
            || ' WHERE d.%I IS NOT NULL'
            || '   AND btrim(d.%I::text) <> $1',
            v_schema, v_nome,
            v_fam.colonna_numero, v_fam.colonna_numero)
          INTO v_docs
         USING ''::text;

        IF v_docs > 0 THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_ATTIVO_BLOCK_CHILDREN_EXIST',
                'reason',     'HA_DOCUMENTI_NUMERATI',
                'reason_key', 'amministrazione.famiglie_documento.disattiva_blocco.ha_documenti_numerati',
                'dettaglio',  jsonb_build_object('famiglia_id',    p_famiglia_id,
                                                 'codice_interno', v_fam.codice_interno,
                                                 'documenti',      v_docs,
                                                 'tabella',        v_schema || '.' || v_nome));
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_famiglia_documento_disattivabile(p_famiglia_id integer)
IS 'Pure check: i motivi che impediscono di spegnere una famiglia di documento (vendite.famiglie_documento). Ritorna [] se si puo'', altrimenti l''array ordinato dei motivi {codice, reason, reason_key, dettaglio}: prima HA_REGISTRI_ATTIVI (E_ATTIVO_BLOCK_CHILDREN_ACTIVE), poi HA_DOCUMENTI_NUMERATI (E_ATTIVO_BLOCK_CHILDREN_EXIST). Solleva solo E_VENDITE_CHIAMATA_NON_VALIDA, per un identificativo non valido o una famiglia che non esiste. La consumano il guard che rifiuta lo spegnimento (vendite.trgfn_famiglie_documento_guard_disattivazione), che solleva il primo motivo, e la lista del CRUD, che tiene il cestino spento e dice perche''. Esiste perche'' anagrafiche.fn_ba_ha_storia_emittente e anagrafiche.fn_get_storia_emittente_ba leggono solo le famiglie attive: spegnerne una la toglierebbe dal presidio sul cambio emittente del billing account, e i suoi documenti smetterebbero di trattenere il billing account dove sono stati numerati. Il primo motivo e'' quello rimediabile (spegnere i registri); i numeri gia'' usciti non si disfano. La tabella dei documenti e'' la target_table della sorgente della famiglia (config.fn_sorgente_tabella), contata in SQL dinamico sui soli documenti che portano un numero: una famiglia nuova entra nel controllo il giorno che nasce, e una sorgente senza tabella non conta niente. Le frasi dei due codici non hanno valori; il dettaglio porta la famiglia, i registri o i documenti e la tabella. SECURITY DEFINER: le tabelle dei documenti hanno la RLS, e un conteggio sotto RLS risponderebbe zero a chi non le vede, cioe'' «si puo'' spegnere».';
```

</div>

---
{% include-markdown "signature-core.md" %}
