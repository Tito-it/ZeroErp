# ⚙️ Funzione `trgfn_registri_fatturazione_guard_serie_ammessa`

```sql
CREATE FUNCTION trgfn_registri_fatturazione_guard_serie_ammessa()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_registri_fatturazione_guard_serie_ammessa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare un `serie_default` su un registro la cui
    --   famiglia non dichiara una colonna dove il documento possa
    --   registrare la serie.
    --
    -- ⛔ Perche': la serie entra nella chiave del contatore.
    --   Cambiarla apre un secchio nuovo che riparte da 1, e se il
    --   documento non la registra (resi, commesse) quel numero
    --   collide con uno gia' emesso — il documento non si numera
    --   piu'.
    --
    -- ⭐ §12.5.2: QUI NON C'E' IL PREDICATO. Si chiama
    --   script.fn_check_registro_serie_ammessa e si solleva il
    --   codice del primo motivo, cosi' il rifiuto e il tooltip
    --   della maschera non possono divergere.
    -- =========================================================

    -- ⭐ In UPDATE il no-op passa: `UPDATE OF` scatta quando lo
    --   statement NOMINA la colonna, anche a valore invariato — e
    --   il mirror CSV dei registri riscrive serie_default a OGNI
    --   migrate. Senza questo confronto, ogni migrate fallirebbe.
    IF TG_OP = 'UPDATE'
       AND NEW.serie_default      IS NOT DISTINCT FROM OLD.serie_default
       AND NEW.famiglia_documento IS NOT DISTINCT FROM OLD.famiglia_documento THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_registro_serie_ammessa(
                    NEW.famiglia_documento, NEW.serie_default);

    IF v_motivi IS NULL OR jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⚠️ `NULL::uuid` e non NEW.tx_id: questo guard sta su un trigger `_a10_`
    --   che, confrontato per NOME INTERO, precede `..._gen_tx_id_ins_upd`
    --   ('a10' < 'gen'), quindi la transazione non e' ancora assegnata.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'trgfn_registri_fatturazione_guard_serie_ammessa',
        v_motivi,
        'serie_default',
        NULL::uuid);

    -- ⭐ Ora RAGGIUNGIBILE, ed e' il ramo «passa»: l'helper tace quando la
    --   check non ha trovato nessun motivo.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_registri_fatturazione_guard_serie_ammessa()
IS 'Guard `_a10_` su vendite.registri_fatturazione: rifiuta un `serie_default` valorizzato quando la famiglia del registro non dichiara `colonna_serie`, cioe'' quando i suoi documenti non hanno dove registrare la serie. ⛔ PERCHE'': la serie entra nella chiave del contatore, quindi cambiarla apre un secchio nuovo che riparte da 1 — e se il documento non la registra ne'' ce l''ha nel proprio vincolo di unicita'' (resi, commesse) quel numero collide con uno gia'' emesso, il vincolo rifiuta e col rollback torna indietro anche il contatore: il documento non si numera piu''. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: si chiama script.fn_check_registro_serie_ammessa e si solleva il codice del primo motivo, cosi'' il rifiuto e il tooltip della maschera non possono divergere. ⛔ SI RIFIUTA E NON SI IGNORA: lasciar scrivere il valore facendolo poi ignorare al motore sarebbe il difetto appena tolto da config.sistema_codici — un campo editabile dal pannello che l''amministratore cambia senza ottenere niente e senza accorgersene. ⚠️ UN TRIGGER E NON UN CHECK: la condizione attraversa vendite.famiglie_documento, e un CHECK non fa sottoquery. ⛔ INSERT *E* UPDATE, perche'' un registro non deve nemmeno NASCERE con una serie che la sua famiglia non porta; verificato che i sei CHECK della tabella riguardano condizioni diverse, quindi il ramo INSERT non li oscura. ⭐ DUE ACCORGIMENTI TENGONO IN PIEDI IL MIGRATE: in UPDATE si confrontano i VALORI (il mirror CSV 20260127-57 riscrive serie_default a ogni migrate e `UPDATE OF` scatta comunque), e il ramo «famiglia non trovata» della check TACE (su un database ricostruito da zero il mirror dei registri gira prima di quello delle famiglie, perche'' includeAll ordina per nome file). Lo stato finale lo verifica il pgTAP. ⚠️ Il context porta `campo = serie_default`: e'' il canale che diventa error.fields e accende l''input giusto nel form. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima del trigger che lo genera. Piano: brief-db-registri-numerazione-chiave-del-contatore, sezione 5 (S-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
