{% include-markdown "it/dbzero/script/manual/trgfn_doc_guard_listino_con_righe.md" %}
# ⚙️ Funzione `trgfn_doc_guard_listino_con_righe`

```sql
CREATE FUNCTION trgfn_doc_guard_listino_con_righe()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_guard_listino_con_righe()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- Scopo: il listino di un contratto o di un'offerta non cambia
--   sotto righe gia' caricate, e non si toglie sotto eccezioni
--   OVERRIDE/ESCLUSIONE (R-DB-4 e D-11 di
--   brief-db-testata-dopo-emissione): solleva il primo motivo di
--   script.fn_check_listino_cambiabile, col campo listino_id. Il
--   predicato sta nella check: qui si solleva soltanto
--   (linee-guida-sql §12.5.2).
-- Uso:   BEFORE UPDATE WHEN il listino cambia, fascia _a10_, su
--        vendite.contratti e vendite.offerte_commerciali. Il nome
--        (guard_listino_con_righe) lo fa parlare prima di
--        guard_listino_documento: se il listino non si puo'
--        cambiare, non serve dire se quello nuovo era buono. Fuori
--        bozza parla prima il lock di testata (_a05_).
-- TG_ARGV[0]: documento (CONTRATTO | OFFERTA_COMMERCIALE), che decide le righe.
DECLARE
    -- Tipo nudo DICHIARATO: un selettore del trigger, nessuna colonna.
    v_documento text := TG_ARGV[0];
    v_motivi    jsonb;
BEGIN
    v_motivi := script.fn_check_listino_cambiabile(
        v_documento, NEW.id, OLD.listino_id, NEW.listino_id);

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        v_motivi,
        v_motivi -> 0 -> 'dettaglio' ->> 'campo',
        NEW.tx_id,
        jsonb_build_object('documento', v_documento,
                           'documento_id', NEW.id,
                           'listino_da', OLD.listino_id,
                           'listino_a', NEW.listino_id));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_guard_listino_con_righe()
IS 'Guard generico (2026-10-11, brief-db-testata-dopo-emissione §11, R-DB-4 e D-11 di Tid; vendite.contratti, vendite.offerte_commerciali): solleva il primo motivo di script.fn_check_listino_cambiabile — E_DOC_LISTINO_CAMBIO_CON_RIGHE (un listino nuovo sotto righe gia'' caricate) o E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI (il listino tolto sotto eccezioni OVERRIDE/ESCLUSIONE) — col campo listino_id (canale COLUMN). TG_ARGV[0] = documento (CONTRATTO | OFFERTA). Montato BEFORE UPDATE WHEN (OLD.listino_id IS DISTINCT FROM NEW.listino_id), fascia _a10_, prima di a10_guard_listino_documento (prima l''immutabilita'', poi la validita'' del valore nuovo); fuori bozza parla prima il lock di testata (_a05_), che il listino lo ferma comunque. Porta a DB le due regole che vivevano solo in contratti_service.update_contratto (E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE, E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI, ritirati) e le estende all''offerta, che ha le stesse righe. ⭐ rev 2026-10-19 (20261019-71, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
