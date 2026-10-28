{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_gen_numero.md" %}
# ⚙️ Funzione `trgfn_ordini_gen_numero`

```sql
CREATE FUNCTION trgfn_ordini_gen_numero()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_gen_numero()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la famiglia di numerazione e' ORDINE_VENDITA, il codice della
--   sorgente (era ORDINE).
DECLARE
    v_emittente_sr vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_registro     vendite.registri_fatturazione.id%TYPE;
    v_ass          record;
    v_anno         vendite.ordini.anno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Assegnare ordini.numero all'INSERT, prendendolo dal
    --   MOTORE DEI REGISTRI. Fino al 2026-08-31 il numero veniva
    --   dalla sequenza generica del catalogo dei formati, la cui
    --   riga 'ordine' e' uscita col changeSet 20260831-53.
    --
    -- ⭐ Il MOMENTO non cambia: nessuno stato da guardare,
    --   l'ordine nasce numerato. ⛔ E i buchi da bozza scartata
    --   restano: e' la conseguenza dichiarata di quella scelta.
    -- =========================================================

    -- ⭐ Gia' numerato -> no-op. Serve a due cose: rispettare un
    --   numero fornito da fuori, e rendere INNOCUA la finestra in
    --   cui questo trigger convive con quello generico (il CSV
    --   che lo spegne vive in 80_data, che gira dopo 20_code).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Due convenzioni per lo stesso emittente: l'ordine porta
    --   l'id di anagrafiche.emittenti_fiscali, il registro porta
    --   il soggetto_ruolo. Traduzione 1:1, esplicita.
    SELECT ef.soggetto_ruolo_id INTO v_emittente_sr
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = NEW.emittente_fiscale_id;

    -- ⛔ L'involucro, non il lettore: qui si SCRIVE, e un
    --   emittente senza registro ORDINE deve fermare.
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
               p_famiglia_documento          => 'ORDINE_VENDITA',
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

COMMENT ON FUNCTION vendite.trgfn_ordini_gen_numero()
IS 'Assegna il numero all''ordine alla creazione, chiamando vendite.fn_assegna_numero_documento. ⭐ rev 2026-08-31 (brief-db-prefisso-sul-registro-e-allineamento-contatori, P-4): i SEI PASSI della numerazione — risolvere il registro, ricavare l''anno dalla data documento, chiedere il progressivo, leggere il formato, comporre — non stanno piu'' qui. Stavano qui E in altre tre funzioni identiche (DDT, ordini, resi, commessa), verificato il 2026-08-31: gli stessi sei passi, quattro volte. ⚠️ Una correzione alla composizione andava fatta in QUATTRO posti, e chi ne dimenticava uno produceva un difetto MUTO — un documento formattato diverso dagli altri, che nessun vincolo respinge. ⭐ QUI RESTA L''UNICA COSA CHE DISTINGUE DAVVERO QUESTO DOCUMENTO DAGLI ALTRI TRE: il MOMENTO. I guard di uscita anticipata decidono SE e QUANDO numerare, poi la chiamata fa il resto — centralizzare anche il momento avrebbe messo in una funzione comune la sola cosa che comune non e''. ⭐ IL FORMATO VIENE TUTTO DAL REGISTRO — prefisso, suffisso e lunghezza, in una lettura sola — e i DEFAULT con cui un registro nasce stanno in vendite.famiglie_documento. ⛔ config.sistema_codici NON C''ENTRA PIU'': il 20260831-53 ne ha tolto le righe di ddt, ordine, reso e commessa. ⚠️ Fino al 20260831-54 questa descrizione diceva che il catalogo dei formati «conserva la sola LUNGHEZZA»: era vero fino al 53, e nel frattempo la funzione centrale continuava a leggerla da li'' — zero righe, lunghezza NULL, 7 cifre a tutti (giusto per caso qui, sbagliato sulla commessa). Corretto dal 20260831-55. ⚠️ Il separatore non si legge piu'': se serve, si scrive dentro il prefisso. ⚠️ Le colonne della chiave si scrivono INSIEME, perche'' sono una cosa sola: scriverne una senza le altre lascerebbe la riga a raccontare un sezionale che non e'' il suo. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-4 e P-16. Rev 2026-10-20 (20261020-43, brief-db-grammatica-unica-documenti 2c, G-5): la famiglia di numerazione e'' ORDINE_VENDITA, il codice della sorgente (era ORDINE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
