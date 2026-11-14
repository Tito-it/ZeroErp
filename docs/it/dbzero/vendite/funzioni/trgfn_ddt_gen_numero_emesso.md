{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso.md" %}
# ⚙️ Funzione `trgfn_ddt_gen_numero_emesso`

```sql
CREATE FUNCTION trgfn_ddt_gen_numero_emesso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la famiglia di numerazione e' DDT_VENDITA, il codice della
--   sorgente (era DDT).
DECLARE
    -- La bolla e' nello stato di emissione? Dal vocabolario.
    v_emissione    config.stati_doc_ddt.emissione%TYPE;
    v_emittente_sr vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_registro     vendite.registri_fatturazione.id%TYPE;
    v_ass          record;
    v_anno         vendite.ddt.anno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Assegnare ddt.numero alla transizione a EMESSO,
    --   prendendolo dal MOTORE DEI REGISTRI.
    --
    -- ⭐ rev 2026-08-31: qui resta il MOMENTO, e basta. Il
    --   formato — prefisso, suffisso, lunghezza — viene TUTTO
    --   dal registro, e la composizione dalla funzione centrale.
    -- ⛔ config.sistema_codici non ha piu' una riga 'ddt': il
    --   20260831-53 l'ha tolta insieme alle altre tre. I DEFAULT
    --   con cui nasce un registro stanno in
    --   vendite.famiglie_documento.
    -- =========================================================

    -- Gia' numerato -> no-op (immutabilita' da
    -- trgfn_v_ddt_protect_num).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- Numero solo a EMESSO (no buchi da bozze DRAFT scartate).
    SELECT sdd.emissione INTO v_emissione
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;
    -- rev 2026-11-14 (giro 6d): lo stato di emissione, la colonna del
    -- vocabolario. Uno stato che non si legge non e' l'emissione.
    IF v_emissione IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Due convenzioni per lo stesso emittente: il DDT porta
    --   l'id di anagrafiche.emittenti_fiscali, il registro porta
    --   il soggetto_ruolo. La traduzione e' 1:1
    --   (uq_emittenti_fiscali_ruolo) e si fa qui, esplicita.
    SELECT ef.soggetto_ruolo_id INTO v_emittente_sr
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = NEW.emittente_fiscale_id;

    -- ⛔ L'INVOLUCRO, non il lettore: qui si SCRIVE, e un
    --   emittente senza registro DDT deve fermare — non emettere
    --   un documento senza sezionale.
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
               p_famiglia_documento          => 'DDT_VENDITA',
               p_emittente_soggetto_ruolo_id => v_emittente_sr,
               p_data                        => NEW.data,
               p_documento_id                => NEW.id,
               p_utility_id                  => NEW.utility_id,
                        p_serie              => NEW.serie,
               p_corpo                       => NULL) v;

    -- ⚠️ Le colonne si scrivono INSIEME: numero, anno, serie e registro
    --   sono una cosa sola — la chiave del documento — e scriverne
    --   una senza le altre lascia la riga a raccontare un sezionale
    --   che non e' il suo.
    NEW.registro_id := v_ass.registro_id;
    NEW.anno        := v_ass.anno;
    NEW.serie       := NULLIF(v_ass.serie, '');
    NEW.numero      := v_ass.numero;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
IS 'Assegna il numero alla bolla quando entra nello stato di emissione (la colonna emissione di config.stati_doc_ddt), chiamando vendite.fn_assegna_numero_documento con la famiglia DDT_VENDITA, il codice della sorgente; un numero gia'' scritto non si tocca. I passi della numerazione (risolvere il registro, ricavare l''anno dalla data documento, chiedere il progressivo, leggere il formato, comporre) stanno nella funzione centrale, comune a bolla, ordine, reso e commessa: qui resta la sola cosa propria del documento, il momento. Il formato viene tutto dal registro (prefisso, suffisso e lunghezza, in una lettura sola), e i default con cui un registro nasce stanno in vendite.famiglie_documento; il separatore, se serve, si scrive dentro il prefisso. Le colonne della chiave si scrivono insieme, perche'' sono una cosa sola: scriverne una senza le altre lascerebbe la riga a raccontare un sezionale che non e'' il suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
