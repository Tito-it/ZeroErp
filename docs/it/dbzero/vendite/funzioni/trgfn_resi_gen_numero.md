{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_gen_numero.md" %}
# ⚙️ Funzione `trgfn_resi_gen_numero`

```sql
CREATE FUNCTION trgfn_resi_gen_numero()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_gen_numero()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la famiglia di numerazione e' RESO_VENDITA, il codice della
--   sorgente (era RESO).
DECLARE
    v_emissione    config.stati_doc_reso.emissione%TYPE;
    v_emittente_sr vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_registro     vendite.registri_fatturazione.id%TYPE;
    v_ass          record;
    v_anno         vendite.resi.anno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Assegnare resi.numero all'ingresso nello stato di
    --   emissione del reso (config.stati_doc_reso.emissione),
    --   prendendolo dal MOTORE DEI REGISTRI.
    --
    -- ⭐ rev 2026-08-31: cambia SOLO il contatore. Formato,
    --   composizione e momento restano quelli di prima.
    -- =========================================================

    -- Gia' numerato -> no-op (immutabilita' da
    -- trgfn_v_resi_protect_num).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- Numero solo nello stato di emissione (no buchi da bozze
    -- scartate). Lo dice il vocabolario, non il codice.
    SELECT sdr.emissione INTO v_emissione
      FROM config.stati_doc_reso sdr
     WHERE sdr.id = NEW.stato_doc_reso_id;
    IF v_emissione IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Il reso porta l'id di emittenti_fiscali, il registro il
    --   soggetto_ruolo: traduzione 1:1, esplicita.
    SELECT ef.soggetto_ruolo_id INTO v_emittente_sr
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = NEW.emittente_fiscale_id;

    -- ⛔ L'involucro: qui si SCRIVE, e un emittente senza
    --   registro RESO deve fermare.
    -- ⭐ I SEI PASSI IN UNA CHIAMATA SOLA. Stavano qui e in altre tre
    --   funzioni identiche: risolvere il registro, ricavare l'anno,
    --   chiedere il progressivo, leggere il formato, comporre.
    --   ⚠️ Una correzione alla composizione andava fatta in QUATTRO
    --   posti, e chi ne dimenticava uno produceva un documento
    --   formattato diverso dagli altri — che nessun vincolo respinge.
    -- ⭐ Qui resta l'unica cosa che distingue davvero questo documento
    --   dagli altri tre: il MOMENTO, cioe' i guard qui sopra.
    SELECT * INTO v_ass
      FROM vendite.fn_assegna_numero_documento(
               p_famiglia_documento          => 'RESO_VENDITA',
               p_emittente_soggetto_ruolo_id => v_emittente_sr,
               p_data                        => NEW.data,
               p_documento_id                => NEW.id,
               p_utility_id                  => NEW.utility_id,
               p_corpo                       => NULL) v;

    -- ⚠️ Le colonne si scrivono INSIEME: numero, anno e registro
    --   sono una cosa sola — la chiave del documento — e scriverne
    --   una senza le altre lascia la riga a raccontare un sezionale
    --   che non e' il suo.
    NEW.registro_id := v_ass.registro_id;
    NEW.anno        := v_ass.anno;
    NEW.numero      := v_ass.numero;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_gen_numero()
IS 'Assegna il numero al reso quando entra nello stato di emissione del suo vocabolario (config.stati_doc_reso.emissione), chiamando vendite.fn_assegna_numero_documento con la famiglia RESO_VENDITA. Un reso gia'' numerato resta com''e'' (l''immutabilita'' la fa valere vendite.trgfn_v_resi_protect_num); fuori dallo stato di emissione non si numera, cosi'' una bozza scartata non lascia buchi. I passi della numerazione (registro, anno dalla data, progressivo, formato, composizione) stanno in vendite.fn_assegna_numero_documento: qui resta solo il momento. Il formato viene tutto dal registro. Numero, anno e registro si scrivono insieme, perche'' sono la chiave del documento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
