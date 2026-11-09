{% include-markdown "it/dbzero/vendite/manual/fn_ddt_riga_componenti_preview.md" %}
# ⚙️ Funzione `fn_ddt_riga_componenti_preview`

```sql
CREATE FUNCTION fn_ddt_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer)
 RETURNS TABLE(articolo_componente_id uuid, componente_id uuid, componente_codice character varying, componente_descrizione character varying, coeff_qta_snapshot numeric, quantita_componente numeric, uom_id bigint, uom_codice character varying, iva_id bigint, prezzo_suggerito numeric, origine_prezzo character varying, resolver_error_reason text, obbligatorio boolean, esposizione_in_fattura character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: preview read-only dei componenti BoM CASO A per il drawer riga DDT
--   (form atomic). Per ogni componente attivo e valido tenta
--   fn_resolve_prezzo_listino_v2; se fallisce ritorna prezzo_suggerito=NULL
--   + motivazione in resolver_error_reason. Nessun side-effect (STABLE).
--   rev 2026-05-13: modello unificato — rimosso filtro esposto_in_fattura=TRUE;
--   obbligatorio e esposto_in_fattura sono ora esposti nella proiezione.
--   rev 2026-10-01: esposizione_in_fattura (NASCOSTO | DESCRITTIVO | VALORIZZATO)
--   al posto del booleano esposto_in_fattura
--   (brief-db-esposizione-componenti-kit-in-fattura).
DECLARE
    v_rec     record;
    v_resolve record;
    v_msg     text;
BEGIN
    FOR v_rec IN
        SELECT ac.id          AS bom_entry_id,
               ac.componente_id,
               ac.coeff_qta,
               ac.obbligatorio,
               ac.esposizione_in_fattura,
               a.codice       AS a_codice,
               a.descrizione  AS a_descrizione,
               a.uom_id       AS a_uom_id,
               a.iva_id       AS a_iva_id,
               um.codice      AS um_codice
          FROM catalogo.fn_distinta_alla_data(p_articolo_id, p_data_riferimento) ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
          LEFT JOIN catalogo.unita_misura um ON um.id = a.uom_id
    LOOP
        articolo_componente_id := v_rec.bom_entry_id;
        componente_id          := v_rec.componente_id;
        componente_codice      := v_rec.a_codice;
        componente_descrizione := v_rec.a_descrizione;
        coeff_qta_snapshot     := v_rec.coeff_qta;
        quantita_componente    := v_rec.coeff_qta * p_quantita_padre;
        uom_id                 := v_rec.a_uom_id;
        uom_codice             := v_rec.um_codice;
        iva_id                 := v_rec.a_iva_id;
        obbligatorio           := v_rec.obbligatorio;
        esposizione_in_fattura := v_rec.esposizione_in_fattura;

        -- ⭐ Si chiama il NUCLEO, non il guscio (2026-08-19, slice C).
        --   Prima qui c'era un BEGIN..EXCEPTION che catturava il P0001 del
        --   resolver e lo trasformava in prezzo_suggerito NULL + motivazione.
        --   Il risultato per il chiamante era gia' quello giusto — questa e'
        --   una preview, non deve fallire — ma il costo era invisibile: il
        --   database SCRIVE la riga di dbops.error_log PRIMA di sollevare, via
        --   dblink fuori transazione, quindi catturare l'eccezione nascondeva
        --   l'errore e lasciava il log. Una riga per componente non risolto, a
        --   ogni apertura del drawer.
        --   Il nucleo non solleva e non logga: riporta l'esito e basta.
        SELECT * INTO v_resolve
          FROM vendite.fn_resolve_prezzo_listino_v2_esito(
              v_rec.componente_id,
              v_rec.a_uom_id,
              p_data_riferimento,
              p_ba_id,
              p_utility_id::integer,
              p_emittente_sr_id,
              p_classe_utenza_id,
              p_articolo_id  -- p_articolo_padre_contesto: attiva STADIO BUNDLE
          );

        IF v_resolve.esito_codice IS NULL THEN
            prezzo_suggerito      := v_resolve.prezzo_finale;
            origine_prezzo        := v_resolve.origine;
            resolver_error_reason := NULL;
        ELSE
            prezzo_suggerito := NULL;
            origine_prezzo   := NULL;

            -- Il testo mostrato resta una FRASE, come prima: il chiamante
            -- e' un drawer e l'operatore legge questo. Il codice
            -- strutturato viaggia in coda, per chi distingue i casi.
            v_msg := script.fn_get_messaggio(v_resolve.esito_codice, NULL, 'it');

            -- ⚠️ I SEGNAPOSTO VANNO SOSTITUITI, e fn_get_messaggio non lo fa:
            --   accetta un valore solo, e questi messaggi ne hanno fino a
            --   cinque. Senza format() l'operatore leggerebbe «Nessuna mappa
            --   categoria %s -> listino per utility %s», che e' peggio di
            --   nessun messaggio: sembra un difetto del programma.
            --   ⛔ E format() con MENO valori dei segnaposto non degrada:
            --   alza 22023. Il ripiego e' lo stesso che
            --   script.fn_log_and_raise_error si e' dato il 2026-08-18 — se la
            --   sostituzione fallisce resta il modello, brutto da leggere ma
            --   innocuo. Una preview non deve rompersi per un messaggio.
            IF array_length(v_resolve.esito_valori, 1) IS NOT NULL THEN
                BEGIN
                    v_msg := format(v_msg, VARIADIC v_resolve.esito_valori);
                EXCEPTION WHEN OTHERS THEN
                    NULL;  -- v_msg resta il modello
                END;
            END IF;

            resolver_error_reason := v_msg || ' [' || v_resolve.esito_codice || ']';
        END IF;

        RETURN NEXT;
    END LOOP;
END;

$function$

COMMENT ON FUNCTION vendite.fn_ddt_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer)
IS 'Preview read-only dei componenti BoM CASO A per il drawer riga DDT. rev 2026-08-19: chiama il NUCLEO fn_resolve_prezzo_listino_v2_esito invece del guscio, e perde il BEGIN..EXCEPTION. Per il chiamante il risultato e'' identico (prezzo_suggerito NULL + resolver_error_reason quando non si risolve); sparisce la riga di dbops.error_log che il DB scriveva comunque, via dblink fuori transazione, PRIMA di sollevare — una per componente non risolto, a ogni apertura del drawer. Brief: brief-ddt-righe-senza-prezzo §9 slice C (C5). rev 2026-10-01: esposto_in_fattura (boolean) diventa esposizione_in_fattura (NASCOSTO | DESCRITTIVO | VALORIZZATO), letta dalla distinta (brief-db-esposizione-componenti-kit-in-fattura).';
```

</div>

---
{% include-markdown "signature-core.md" %}
