{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_registro_emittente.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_registro_emittente`

```sql
CREATE FUNCTION trgfn_fatture_guard_registro_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_registro_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_emittente_registro vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_codice_registro    vendite.registri_fatturazione.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una fattura si numera sul registro del PROPRIO
    --   emittente. Qui si verifica che i due coincidano.
    --
    -- Regole:
    --   - vale per OGNI scrittore: il vincolo non sa chi lo
    --     scrive, e la risoluzione del registro
    --     (fn_get_registro_id) e' solo uno dei percorsi;
    --   - un registro SENZA emittente non si giudica, finche'
    --     la colonna e' nullable: e' configurazione legittima,
    --     e bloccarla fermerebbe la fatturazione prima della
    --     bonifica;
    --   - registro inesistente: si tace e parla la FK.
    -- =========================================================
    SELECT r.emittente_soggetto_ruolo_id, r.codice
      INTO v_emittente_registro, v_codice_registro
      FROM vendite.registri_fatturazione r
     WHERE r.id = NEW.registro_id;

    -- ⚠️ Due casi in una riga sola, e vanno letti insieme:
    --   1) il registro non c'e' ancora (BEFORE ROW gira prima
    --      della FK) -> lascia parlare fk_fatture_registro;
    --   2) il registro c'e' ma e' generico -> non si giudica.
    --   ⭐ Il secondo sparisce da solo col NOT NULL di C1-2.
    IF v_emittente_registro IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.emittente_soggetto_ruolo_id IS DISTINCT FROM v_emittente_registro THEN
        -- ⛔ TECNICO: niente `campo` (su un 500 non c'e' nessun
        --    campo da accendere) e niente `bersaglio` (nessun
        --    gesto da offrire). Nel VARIADIC vanno i tre valori
        --    che il messaggio nomina, nell'ordine dei %s.
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fatture_guard_registro_emittente',
            'E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE',
            jsonb_build_object(
                'fattura_id',                  NEW.id,
                'numero',                      NEW.numero,
                'registro_id',                 NEW.registro_id,
                'registro_codice',             v_codice_registro,
                'emittente_soggetto_ruolo_id', NEW.emittente_soggetto_ruolo_id,
                'emittente_registro_id',       v_emittente_registro),
            NULL::uuid,
            COALESCE(NEW.numero::text, 'id ' || NEW.id::text),
            v_codice_registro,
            NEW.emittente_soggetto_ruolo_id::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_registro_emittente()
IS 'Guard BEFORE INSERT / UPDATE OF (registro_id, emittente_soggetto_ruolo_id) su vendite.fatture: la fattura deve stare sul registro del PROPRIO emittente. Solleva E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE. ⛔ Chiude un difetto MUTO: fino al 2026-08-30 nulla legava fatture.registro_id a fatture.emittente_soggetto_ruolo_id, e registri_fatturazione.emittente_soggetto_ruolo_id e'' nullable con un quarto livello di fallback in vendite.fn_lookup_registro_id che risolve proprio il registro senza emittente. ⚠️ Un registro condiviso fra due emittenti non produce numeri duplicati — il contatore e'' uno solo, quindi uq_fatture_numero non ha niente da respingere — ma spezza l''ATTRIBUZIONE: due partite IVA pescano dalla stessa serie e nessuna delle due ha una propria numerazione progressiva. Nessun errore e nessuna riga in error_log: e'' la ragione per cui serve un guard e non un vincolo. ⭐ Trigger e non CHECK: un CHECK verrebbe validato sul PREGRESSO e fallirebbe, e le fatture gia'' numerate non si ripuntano (cambiare il registro di una fattura numerata le cambia il sezionale, cioe'' l''identita'' del suo numero); il trigger presidia il futuro e lascia stare la storia. ⛔ Il guard TACE quando il registro non ha emittente, ed e'' voluto: finche'' la colonna e'' nullable quella e'' una configurazione legittima che serve documenti veri, e bloccarla fermerebbe la fatturazione PRIMA che la bonifica abbia separato i registri generici. ⭐ Il giorno in cui la colonna diventa NOT NULL (C1-2) quel ramo diventa irraggiungibile e il guard copre tutto da se'', senza una seconda revisione. ⚠️ UPDATE OF e non UPDATE nudo: con un UPDATE generico ogni passaggio di stato, ogni numerazione e ogni ricalcolo di totali rivaliderebbe la coppia, e una fattura storica su un registro non piu'' coerente diventerebbe non piu'' modificabile con un errore che parla di due colonne che nessuno stava toccando. ⚠️ SECURITY INVOKER e non DEFINER: su vendite.registri_fatturazione la RLS non c''e'', quindi un DEFINER sarebbe privilegio in piu'' senza contropartita. ℹ️ Se il registro non esiste il guard tace e lascia parlare fk_fatture_registro: un BEFORE ROW gira prima che la FK sia verificata, e un guard che diagnostica le FK degli altri produce due messaggi per un difetto solo. ⛔ Il codice e'' TECNICO e non DATO_ERRATO: il registro non lo sceglie una persona in un dialog, lo risolve vendite.fn_get_registro_id dal tipo documento e dalla natura — quindi niente chiave `campo` e niente `bersaglio`. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C1-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
