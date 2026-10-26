# ⚙️ Funzione `trgfn_vendite_contabili_gen_codice`

```sql
CREATE FUNCTION trgfn_vendite_contabili_gen_codice()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la famiglia di numerazione e' DISTINTA_INCASSO, il codice della
--   sorgente (era DISTINTA).
DECLARE
    v_sigla anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ass   record;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Assegnare vendite_contabili.codice all'INSERT prendendolo
    --   dal MOTORE DEI REGISTRI (famiglia DISTINTA): fino al
    --   2026-09-15 il codice nasceva da un DEFAULT di colonna
    --   (VC_…) e, sulle sistemazioni, da una seconda
    --   composizione (SIS_…). Un'etichetta, non un numero.
    --
    -- ⭐ Il MOMENTO e' la creazione (D2), come ordini e
    --   commessa: il codice e' la maniglia con cui si lavora la
    --   distinta da subito. ⛔ I buchi da bozza annullata restano:
    --   e' la conseguenza dichiarata di quella scelta.
    -- ⭐ La FORMA e' DIS-<sigla>-<anno>-<7 cifre> (D1): la sigla
    --   dell'emittente entra come CORPO, come nella commessa, e
    --   l'anno lo mette il compositore generico perche' il
    --   registro nasce con anno_nel_numero = true.
    --
    -- Uso: BEFORE INSERT FOR EACH ROW — dopo a10_emittente (per
    --      nome), che ha gia' risolto NEW.emittente_soggetto_ruolo_id.
    -- =========================================================

    -- ⭐ Gia' numerato -> no-op: rispetta un codice fornito da
    --   fuori (le fixture dei pgTAP con PGTAP_…) e rende innocua
    --   ogni finestra. ⛔ Non e' una porta per le madri: lo
    --   presidia il test 13 di test-distinta-numerazione-registro-v1.
    IF NEW.codice IS NOT NULL AND btrim(NEW.codice::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Senza data non c'e' anno: si lascia parlare il NOT NULL
    --   di data_contabile (23502), che nomina la colonna giusta.
    IF NEW.data_contabile IS NULL THEN
        RETURN NEW;
    END IF;

    -- La sigla: emittenti_fiscali non ha RLS. Il trigger a10_emittente
    -- ha gia' garantito (livello 0) che il SR sia un emittente,
    -- quindi v_sigla non e' mai NULL.
    SELECT ef.codice INTO v_sigla
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = NEW.emittente_soggetto_ruolo_id;

    -- ⛔ L'involucro, non il lettore: qui si SCRIVE, e un
    --   emittente senza registro DISTINTA deve fermare
    --   (E_CONFIG_MANCANTE da fn_get_registro_documento).
    -- ⭐ I SEI PASSI in una chiamata sola: registro, anno dalla
    --   data del documento, progressivo, formato, composizione.
    --   Il corpo e' la sigla piu' il separatore, come la commessa:
    --   il compositore aggiunge l'anno in coda al corpo.
    SELECT * INTO v_ass
      FROM vendite.fn_assegna_numero_documento(
               p_famiglia_documento          => 'DISTINTA_INCASSO',
               p_emittente_soggetto_ruolo_id => NEW.emittente_soggetto_ruolo_id,
               p_data                        => NEW.data_contabile,
               p_documento_id                => NEW.id,
               p_utility_id                  => NULL,
               p_corpo                       => v_sigla || '-',
               p_serie                       => NULL) v;

    -- ⚠️ INSIEME: registro, anno e codice sono una cosa sola — la
    --   chiave del documento — e scriverne uno senza gli altri
    --   lascerebbe la riga a raccontare un sezionale non suo
    --   (trgfn_ordini_gen_numero).
    NEW.registro_id := v_ass.registro_id;
    NEW.anno        := v_ass.anno;
    NEW.codice      := v_ass.numero;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_gen_codice()
IS 'Assegna il codice alla distinta contabile ALLA CREAZIONE, chiamando vendite.fn_assegna_numero_documento sulla famiglia DISTINTA e sul registro dell''emittente della riga: DIS-<sigla>-<anno>-<7 cifre> (D1/D2 del brief distinta-numerata-sul-registro). ⭐ La sigla dell''emittente entra come CORPO — come la commessa, ed e'' per questo che il compositore ha un p_corpo — perche'' l''identita'' della distinta e'' la STRINGA NUDA (uq_vendite_contabili_codice): con un registro per emittente, due emittenti produrrebbero entrambi DIS-2026-0000001 e il secondo INSERT prenderebbe un 23505 a ogni tentativo (il numeratore piantato della guida §8-bis). L''anno lo mette il compositore generico perche'' il registro nasce con anno_nel_numero = true, e viene da data_contabile: una distinta datata 31/12 e inserita il 2/1 e'' dell''anno vecchio. ⚠️ Scrive INSIEME registro_id, anno e codice: sono la chiave del documento. ⭐ NO-OP su un codice fornito: rispetta le fixture dei pgTAP e rende innocua ogni finestra; ⛔ NON e'' una porta per le madri (nessuna funzione viva passa codice: presidio in test-distinta-numerazione-registro-v1, test 13), ed e'' la ragione per cui il DEFAULT di colonna e'' caduto — con il DEFAULT vivo NEW.codice arriverebbe sempre pieno e il numeratore sarebbe muto per sempre. ⚠️ Presuppone che a10_emittente abbia gia'' risolto l''emittente (precede per NOME) e che l''emittente abbia il registro DISTINTA (20260915-34 per gli esistenti, il trigger z90 di provisioning per i futuri): senza, E_CONFIG_MANCANTE, fail-closed. ⚠️ Il pregresso numerato prima (VC_…, SIS_…) non si rinumera: forma diversa, registro_id e anno NULL, guida §6.6. Rev 2026-09-15. Rev 2026-10-20 (20261020-45, brief-db-grammatica-unica-documenti 2c, G-5): la famiglia di numerazione e'' DISTINTA_INCASSO, il codice della sorgente (era DISTINTA).';
```

</div>

---
{% include-markdown "signature-core.md" %}
