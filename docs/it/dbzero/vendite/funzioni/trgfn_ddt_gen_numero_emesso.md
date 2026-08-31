{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso.md" %}
# ⚙️ Funzione `trgfn_ddt_gen_numero_emesso`

```sql
CREATE FUNCTION trgfn_ddt_gen_numero_emesso()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato        config.stati_doc_ddt.codice_interno%TYPE;
    v_prefix       config.sistema_codici.prefisso%TYPE;
    v_sep          config.sistema_codici.separatore%TYPE;
    v_len          config.sistema_codici.lunghezza_numero%TYPE;
    v_emittente_sr vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_registro     vendite.registri_fatturazione.id%TYPE;
    v_serie_reg    vendite.registri_fatturazione.serie_default%TYPE;
    v_serie        text;
    v_anno         vendite.ddt.anno%TYPE;
    v_numero       bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Assegnare ddt.numero alla transizione a EMESSO,
    --   prendendolo dal MOTORE DEI REGISTRI.
    --
    -- ⭐ rev 2026-08-31: cambia SOLO il contatore. Il formato
    --   resta in config.sistema_codici (riga 'ddt'), la
    --   composizione resta qui, il momento resta EMESSO.
    -- =========================================================

    -- Gia' numerato -> no-op (immutabilita' da
    -- trgfn_v_ddt_protect_num).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- Numero solo a EMESSO (no buchi da bozze DRAFT scartate).
    SELECT sdd.codice_interno INTO v_stato
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;
    IF v_stato IS DISTINCT FROM 'EMESSO' THEN
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
    SELECT k.registro_id, k.serie
      INTO v_registro, v_serie_reg
      FROM vendite.fn_get_registro_documento(
               p_famiglia_documento          => 'DDT',
               p_emittente_soggetto_ruolo_id => v_emittente_sr,
               p_utility_id                  => NEW.utility_id) k;

    -- ⚠️ La serie entra nella chiave del contatore E nella
    --   UNIQUE: si risolve una volta e si usa per entrambe.
    v_serie := COALESCE(NEW.serie, v_serie_reg, '');

    -- ⛔ L'anno si ricalcola dalla DATA DEL DOCUMENTO, e oggi non
    --   lo scrive nessuno: trgfn_ddt_normalize lo valorizza solo
    --   nel ramo «INSERT gia' numerato», che dal 2026-07-09 non
    --   si attraversa. Qui si riempie per la prima volta la
    --   colonna che uq_ddt_v_anno_serie_numero pretende.
    v_anno := vendite.fn_get_anno_registro(NEW.data);

    -- ⭐ Il motore: stesso cancello, stesso lock, stesso
    --   contatore delle fatture. `p_competenza_mese` NULL — il
    --   DDT non ha competenza, e il limite di emissione non si
    --   applica alla sua famiglia (20260831-05).
    v_numero := vendite.fn_get_next_progressivo(
                    v_registro, NEW.data, NULL,
                    v_serie, NEW.id, 'DDT');

    -- Formato data-driven dalla riga sistema_codici 'ddt'
    -- (usa_sequenza = false: prefisso, separatore e lunghezza
    -- restano validi, ed e' l'unico ruolo che quel catalogo ha
    -- qui).
    SELECT prefisso, separatore, lunghezza_numero
      INTO v_prefix, v_sep, v_len
      FROM config.sistema_codici
     WHERE codice_interno = 'ddt';

    -- ⚠️ Le quattro colonne si scrivono INSIEME: numero, anno,
    --   serie e registro sono una cosa sola — la chiave del
    --   documento — e scriverne una senza le altre lascia la
    --   riga a raccontare un sezionale che non e' il suo.
    NEW.registro_id := v_registro;
    NEW.anno        := v_anno;
    NEW.serie       := NULLIF(v_serie, '');
    NEW.numero      := COALESCE(v_prefix, 'DDT')
                    || COALESCE(v_sep, '')
                    || lpad(v_numero::text, COALESCE(v_len, 7), '0');

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
IS 'Assegna vendite.ddt.numero alla transizione a EMESSO, prendendolo dal MOTORE DEI REGISTRI. ⭐ rev 2026-08-31 (brief-db-registri-di-numerazione-emittente-e-trasloco, C2-8): CAMBIA UNA RIGA SU TRE. Il generatore faceva tre cose — leggere il FORMATO da config.sistema_codici (riga ''ddt''), prendere il CONTATORE da nextval(vendite.ddt_numero_seq), comporre la stringa — e cambia solo il contatore, che ora e'' vendite.fn_get_next_progressivo sul registro di famiglia DDT dell''emittente. Formato, composizione e MOMENTO (la transizione a EMESSO, «no buchi da bozze DRAFT scartate») restano quelli di prima: e'' la ragione per cui config.sistema_codici non si tocca — resta il catalogo dei FORMATI, che e'' il ruolo che il DDT gli dava gia''. ⛔ L''ANNO si ricalcola qui dalla data del documento, e prima non lo scriveva NESSUNO: misurati il 2026-08-31 ventotto DDT numerati, tutti con anno NULL, perche'' vendite.trgfn_ddt_normalize lo valorizza nel solo ramo «INSERT con numero gia'' presente» e dal 2026-07-09 (20260709-07) il DDT si numera a EMESSO, cioe'' in UPDATE — quel ramo non si attraversa piu''. Non si sta correggendo una divergenza: si riempie per la prima volta una colonna che uq_ddt_v_anno_serie_numero pretende, ed e'' anche il motivo per cui quell''indice non presidiava niente. ⚠️ Anno, serie, registro e numero si scrivono NELLO STESSO statement, come fa vendite.fn_assign_numero_fattura: sono una cosa sola — la chiave del documento — e l''anno del contatore e l''anno della riga devono essere lo STESSO valore, non due che si somigliano. ⚠️ La SERIE si risolve con COALESCE(NEW.serie, serie del registro, '''') e si riscrive con NULLIF: entra nella chiave del contatore e nella UNIQUE, e un documento numerato su serie_default con la riga a NULL risulterebbe di una serie diversa da quella su cui ha preso il numero. ⚠️ L''EMITTENTE va tradotto: vendite.ddt.emittente_fiscale_id e'' un id di anagrafiche.emittenti_fiscali mentre il registro porta il soggetto_ruolo_id — due convenzioni che convivono nel progetto, con traduzione 1:1 garantita da uq_emittenti_fiscali_ruolo. ⛔ Si usa l''INVOLUCRO vendite.fn_get_registro_documento e non il lettore: qui si SCRIVE, e un emittente senza registro DDT deve fermare invece di emettere un documento senza sezionale. ℹ️ p_competenza_mese e'' NULL: il DDT non ha competenza, e il limite di emissione non si applica alla sua famiglia (20260831-05). ℹ️ vendite.ddt_numero_seq resta dov''e'', ferma: e'' la memoria dei numeri gia'' consumati, e cancellarla toglierebbe l''unico modo di sapere fin dove era arrivata la numerazione vecchia. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-8.';
```

---
{% include-markdown "signature-core.md" %}
