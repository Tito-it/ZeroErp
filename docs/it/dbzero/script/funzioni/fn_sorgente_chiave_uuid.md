{% include-markdown "it/dbzero/script/manual/fn_sorgente_chiave_uuid.md" %}
# ⚙️ Funzione `fn_sorgente_chiave_uuid`

```sql
CREATE FUNCTION fn_sorgente_chiave_uuid(p_sorgente_uid text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_chiave_uuid(p_sorgente_uid text)
 RETURNS uuid
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
-- Scopo: la chiave di una sorgente polimorfa (forma testuale, come in
--   pratiche_sorgenti.sorgente_uid e script.vw_stato_sorgente.sorgente_uid)
--   nel suo tipo uuid, per cercarla sulla colonna nativa
--   sorgente_chiave_uuid. NULL se il testo non e' un uuid in forma CANONICA.
-- ⭐ Perche' una funzione: sotto RLS un confronto sulla forma testuale non
--   arriva all'indice (uuid_out non e' leakproof); sulla chiave nativa si'.
--   Chi cerca converte il PARAMETRO, non la colonna.
-- ⚠️ Forma CANONICA, cioe' identica a uuid::text: il cast accetta anche
--   maiuscole, graffe, assenza di trattini — chiavi che il confronto testuale
--   non trovava. Il ritorno al testo tiene le due ricerche equivalenti.
-- ⚠️ Mai un errore: pg_input_is_valid prima del cast (22P02 altrimenti). Una
--   chiave che non e' un uuid e' semplicemente «non di questa specie».
-- ⚠️ plpgsql e non sql: una funzione sql si inlinea, e con un argomento
--   costante il planner piega il cast PRIMA del controllo (provato: 22P02 su
--   un uid passato alla gemella _id).
-- STABLE come pg_input_is_valid; NULL in ingresso -> NULL.
DECLARE
    v_chiave script.vw_stato_sorgente.sorgente_chiave_uuid%TYPE;
BEGIN
    IF NOT pg_input_is_valid(p_sorgente_uid, 'uuid') THEN
        RETURN NULL;
    END IF;
    v_chiave := p_sorgente_uid::uuid;
    IF v_chiave::text <> p_sorgente_uid THEN
        RETURN NULL;
    END IF;
    RETURN v_chiave;
END;
$function$

COMMENT ON FUNCTION script.fn_sorgente_chiave_uuid(p_sorgente_uid text)
IS 'La chiave di un documento scritta in testo, nel suo tipo uuid: il lettore della forma canonica per i tipi a key_selector = uid. NULL se il testo non e'' un uuid in forma CANONICA (identica a uuid::text): maiuscole, graffe o trattini mancanti danno NULL, perche'' il confronto sulla forma testuale non li troverebbe e le due strade per cercare la stessa chiave devono rispondere uguale. Mai un errore (pg_input_is_valid prima del cast); NULL in ingresso, NULL in uscita: decide il chiamante. Serve alle chiavi che sono testo per costruzione (i nodi della lineage, la chiave di un gruppo fatturabile, la chiave che riceve il BB che scrive, la riga letta come JSON dal guard unico, le tabelle che hanno la chiave solo in testo): con la gemella script.fn_sorgente_chiave_id e'' il solo posto che decide se quel testo e'' una chiave, e di quale specie. Chi cerca converte il parametro, non la colonna: sotto RLS il confronto sul testo non arriva all''indice (uuid_out non e'' leakproof), quello sull''uuid si''. plpgsql e non sql: una sql si inlinea, e con un argomento costante il cast verrebbe piegato prima del controllo. La leggono script.fn_sorgente_documento_da_chiave, script.fn_sorgente_chiave, script.trgfn_guard_sorgente, dbops.fn_sorgenti_orfane, vendite.fn_documento_lineage_legami, vendite.fn_documento_lineage_sintesi e vendite.fn_riferimento_gruppo_fatturabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
