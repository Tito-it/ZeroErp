{% include-markdown "it/dbzero/vendite/manual/fn_prezzi_legame_oltre_la_fine.md" %}
# ⚙️ Funzione `fn_prezzi_legame_oltre_la_fine`

```sql
CREATE FUNCTION fn_prezzi_legame_oltre_la_fine(p_articolo_componente_id uuid, p_valido_al date)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_prezzi_legame_oltre_la_fine(p_articolo_componente_id uuid, p_valido_al date)
 RETURNS TABLE(riga_id bigint, listino_versione_id bigint, listino_id bigint, listino_codice character varying, codice_versione character varying, stato_versione character varying, valido_dal date, valido_al date, prezzo numeric, importo_per_kit numeric, attivo boolean, nel_perimetro boolean, esito text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
BEGIN ATOMIC
 WITH r AS (
          SELECT lrc.id,
             lrc.listino_versione_id,
             lv.listino_id,
             l.codice AS listino_codice,
             lv.codice_versione,
             s.codice_interno AS stato,
             lrc.valido_dal,
             lrc.valido_al,
             lrc.prezzo,
             (lrc.prezzo * ac.coeff_qta) AS importo_per_kit,
             lrc.attivo,
             script.fn_scope_ef_whitelist_via_listino_versione((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer, lrc.listino_versione_id) AS visibile,
                 CASE
                     WHEN (lrc.valido_dal <= fn_prezzi_legame_oltre_la_fine.p_valido_al) THEN 'CHIUDE'::text
                     WHEN ((s.codice_interno)::text = 'BOZZA'::text) THEN 'TOGLIE'::text
                     ELSE 'BLOCCA'::text
                 END AS esito
            FROM ((((vendite.listini_righe_componenti lrc
              JOIN catalogo.articoli_componenti ac ON ((ac.id = lrc.articolo_componente_id)))
              JOIN vendite.listini_versioni lv ON ((lv.id = lrc.listino_versione_id)))
              JOIN vendite.listini l ON ((l.id = lv.listino_id)))
              JOIN config.stati_doc_listino_versioni s ON ((s.id = lv.stato_doc_listino_versione_id)))
           WHERE ((lrc.articolo_componente_id = fn_prezzi_legame_oltre_la_fine.p_articolo_componente_id) AND (fn_prezzi_legame_oltre_la_fine.p_valido_al IS NOT NULL) AND (COALESCE(lrc.valido_al, 'infinity'::date) > fn_prezzi_legame_oltre_la_fine.p_valido_al))
         )
  SELECT
         CASE
             WHEN r.visibile THEN r.id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.listino_versione_id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.listino_id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.listino_codice
             ELSE NULL::character varying
         END AS "case",
         CASE
             WHEN r.visibile THEN r.codice_versione
             ELSE NULL::character varying
         END AS "case",
         CASE
             WHEN r.visibile THEN r.stato
             ELSE NULL::character varying
         END AS "case",
         CASE
             WHEN r.visibile THEN r.valido_dal
             ELSE NULL::date
         END AS "case",
         CASE
             WHEN r.visibile THEN r.valido_al
             ELSE NULL::date
         END AS "case",
         CASE
             WHEN r.visibile THEN r.prezzo
             ELSE NULL::numeric
         END AS "case",
         CASE
             WHEN r.visibile THEN r.importo_per_kit
             ELSE NULL::numeric
         END AS "case",
         CASE
             WHEN r.visibile THEN r.attivo
             ELSE NULL::boolean
         END AS "case",
     COALESCE(r.visibile, false) AS "coalesce",
     r.esito
    FROM r
   ORDER BY COALESCE(r.visibile, false) DESC, r.listino_id, r.listino_versione_id, r.id;
END

COMMENT ON FUNCTION vendite.fn_prezzi_legame_oltre_la_fine(p_articolo_componente_id uuid, p_valido_al date)
IS 'I prezzi bundle di un legame di distinta (vendite.listini_righe_componenti.articolo_componente_id) che vanno oltre la data p_valido_al, cioe'' quelli che una chiusura del legame a quella data tocca: il prezzo deve stare dentro il periodo del legame (FK temporale fk_listrighe_comp_articoli_comp_temporal). Una riga per prezzo, attivi e spenti, in ogni versione e in ogni azienda. esito: CHIUDE (il prezzo comincia entro la fine e ne prende la stessa fine), TOGLIE (comincia dopo, in una versione in BOZZA: si cancella), BLOCCA (comincia dopo, in una versione non in bozza: non si accorcia ne'' si cancella, e la fine del legame deve arrivare almeno al suo inizio). importo_per_kit = prezzo per il coefficiente del legame: quanto il componente pesa sul prezzo di un kit in quella versione, che e'' la somma dei suoi componenti. nel_perimetro: la riga sta nel perimetro di chi chiama (script.fn_scope_ef_whitelist_via_listino_versione, la regola della policy delle righe); fuori perimetro escono solo nel_perimetro = false e l''esito, gli altri campi sono NULL. p_valido_al NULL: nessuna riga. Ordine: prima le righe nel perimetro, poi per listino, versione e riga. Lettori: script.fn_check_legame_distinta_chiudibile, catalogo.trgfn_articoli_componenti_block_modifica_struttura, catalogo.fn_chiudi_legame_distinta, la finestra di conferma. SECURITY DEFINER con search_path bloccato: la distinta e'' comune a tutte le aziende, i listini no. EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
