{% include-markdown "it/dbzero/vendite/manual/fn_diagnostica_gruppi_fatturabili.md" %}
# ⚙️ Funzione `fn_diagnostica_gruppi_fatturabili`

```sql
CREATE FUNCTION fn_diagnostica_gruppi_fatturabili(p_gruppi text[], p_competenza_mese date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_diagnostica_gruppi_fatturabili(p_gruppi text[], p_competenza_mese date DEFAULT NULL::date)
 RETURNS TABLE(gruppo_key text, commessa_id bigint, commessa_codice text, commessa_stato_codice_interno text, commessa_stato_descrizione text, commessa_emittibile boolean, n_righe bigint, n_emesse bigint, n_annullate bigint, n_rifiutate bigint, n_non_approvate bigint, n_fuori_competenza bigint, n_pronte bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_bound vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
  -- =========================================================
  -- Scopo: la FOTOGRAFIA di uno o piu' gruppi fatturabili —
  --   quante righe hanno, in che stato sono, e in che stato e'
  --   la testata della commessa. Serve a spiegare all'operatore
  --   perche' un gruppo che aveva chiesto di fatturare non e'
  --   stato servito.
  --   Porta a DB l'SQL che stava in
  --   CommesseRepository.diagnostica_gruppi: era la seconda copia
  --   dei filtri di fn_list_emittibili_lane.
  --   brief-db-emittibilita-visibile-e-sbloccabile §9 F4.
  --
  -- Grana: (gruppo_key, commessa_id). ⚠️ La commessa NON e'
  --   ridondante: gruppo_key per una riga con documento sorgente
  --   vale '<codice_interno>:<uid>' e non la contiene, quindi lo
  --   stesso documento potrebbe in linea di principio alimentare
  --   righe su due commesse. La versione Python aggregava con
  --   min()/bool_or() e in quel caso avrebbe detto «emittibile»
  --   perche' UNA lo era, mancando proprio la diagnosi che serve.
  --   vw_dash_competenza_gruppi la commessa la tiene gia' nel
  --   proprio GROUP BY: qui si fa lo stesso.
  --
  -- rev 2026-08-15: via `n_senza_tipo_doc`. Contava le righe
  --   APPROVATA + NON_EMESSA senza tipo documento, che un guard
  --   di riga e un CHECK rifiutano; il CHECK era pero' NOT VALID,
  --   quindi il vecchio restava ignoto e il ramo «forse» vivo.
  --   Il 20260815-30 ha validato il vincolo: adesso il ramo e'
  --   irraggiungibile per costruzione, e un ramo che sembra
  --   coperto e non lo e' vale meno di zero.
  --
  -- Divisione di competenze: qui i CONTATORI, al BE la PROSA
  --   (classifica_gruppo_non_servito compone le frasi italiane,
  --   con accordo di genere e numero). Il DB dice quanti e in che
  --   stato, il BE dice come si racconta.
  --
  -- Un gruppo richiesto e sconosciuto esce comunque, con
  --   commessa_id NULL e contatori a zero: e' il caso
  --   «chiave ignota», e farlo sparire sarebbe un silenzio.
  --
  -- STABLE, sola lettura. commesse e commesse_attivita hanno la
  --   RLS: la fotografia e' gia' scoped per emittente.
  -- =========================================================

  -- Nessun gruppo chiesto, nessuna diagnosi: e' l'identita', non
  -- un errore. Il chiamante filtra a monte, come gia' faceva.
  IF p_gruppi IS NULL OR cardinality(p_gruppi) = 0 THEN
    RETURN;
  END IF;

  -- Bound di competenza normalizzato al primo del mese, come fa
  -- il chiamante. NULL = nessun limite, e allora la classe
  -- «fuori competenza» resta vuota per costruzione.
  v_bound := CASE
    WHEN p_competenza_mese IS NOT NULL
    THEN date_trunc('month', p_competenza_mese)::date
    ELSE NULL
  END;

  RETURN QUERY
  WITH richiesti AS (
    -- Normalizzazione allineata a fn_build_gruppo_fatturabile_key:
    -- una chiave con spazi in coda non combacerebbe MAI con quella
    -- costruita dal DB, e filtrerebbe zero righe senza dirlo.
    SELECT DISTINCT btrim(k) AS gruppo_key
      FROM unnest(p_gruppi) AS k
     WHERE btrim(COALESCE(k, '')) <> ''
  ),
  righe AS (
    SELECT vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key,
           co.id                                        AS commessa_id,
           co.codice::text                              AS commessa_codice,
           sc.codice_interno::text                      AS commessa_stato_codice_interno,
           -- Descrizione di DISPLAY, stessa forma delle due viste
           -- dashboard: chiude la nota in coda al §8.3, perche'
           -- questo valore finisce NELLA FRASE che l'operatore legge.
           COALESCE(sc.descrizione, sc.codice)::text    AS commessa_stato_descrizione,
           sc.emittibile                                AS commessa_emittibile,
           ca.stato_emissione,
           ca.stato_approvazione,
           ca.tipo_doc_fiscale_id,
           ca.competenza_mese
      FROM vendite.commesse_attivita ca
      JOIN vendite.commesse co       ON co.id = ca.commessa_id
      JOIN vendite.stati_commessa sc ON sc.id = co.stato_commessa_id
     WHERE vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)
           IN (SELECT q.gruppo_key FROM richiesti q)
  )
  SELECT d.gruppo_key,
         x.commessa_id,
         x.commessa_codice,
         x.commessa_stato_codice_interno,
         x.commessa_stato_descrizione,
         x.commessa_emittibile,
         count(x.gruppo_key)::bigint AS n_righe,
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'EMESSA')::bigint AS n_emesse,
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'ANNULLATA')::bigint AS n_annullate,
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'NON_EMESSA'
             AND (x.stato_approvazione)::text = 'RIFIUTATA')::bigint AS n_rifiutate,
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'NON_EMESSA'
             AND (x.stato_approvazione)::text NOT IN ('APPROVATA', 'RIFIUTATA'))::bigint AS n_non_approvate,
         -- Le due classi qui sotto sono i filtri della lane. Il
         -- terzo — tipo documento mancante — non c'e' piu': dopo
         -- il 20260815-30 il CHECK e' validato e quella riga non
         -- puo' esistere.
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'NON_EMESSA'
             AND (x.stato_approvazione)::text = 'APPROVATA'
             AND x.tipo_doc_fiscale_id IS NOT NULL
             AND v_bound IS NOT NULL
             AND x.competenza_mese > v_bound)::bigint AS n_fuori_competenza,
         count(*) FILTER (
           WHERE (x.stato_emissione)::text = 'NON_EMESSA'
             AND (x.stato_approvazione)::text = 'APPROVATA'
             AND x.tipo_doc_fiscale_id IS NOT NULL
             AND (v_bound IS NULL OR x.competenza_mese <= v_bound))::bigint AS n_pronte
    FROM richiesti d
    -- LEFT JOIN: un gruppo senza righe deve uscire lo stesso, con
    -- commessa NULL e contatori a zero.
    LEFT JOIN righe x ON x.gruppo_key = d.gruppo_key
   GROUP BY d.gruppo_key,
            x.commessa_id,
            x.commessa_codice,
            x.commessa_stato_codice_interno,
            x.commessa_stato_descrizione,
            x.commessa_emittibile
   -- Ordine DETERMINISTICO: il chiamante compone una frase con i
   -- primi N, e due chiamate uguali devono dare la stessa frase.
   ORDER BY d.gruppo_key, x.commessa_id NULLS FIRST;
END;
$function$

COMMENT ON FUNCTION vendite.fn_diagnostica_gruppi_fatturabili(p_gruppi text[], p_competenza_mese date)
IS 'FOTOGRAFIA di uno o piu'' gruppi fatturabili: quante righe hanno e in che stato, piu'' la testata della commessa (codice, stato codice interno E descrizione, flag emittibile). Serve a spiegare perche'' un gruppo che l''operatore aveva chiesto di fatturare non e'' stato servito. Porta a DB l''SQL che stava in CommesseRepository.diagnostica_gruppi — ultima copia dei filtri di vendite.fn_list_emittibili_lane rimasta fuori dal database, offerta dal BE il 2026-08-04 (§5.2 di brief-db-emittibilita-visibile-e-sbloccabile) e accolta il 2026-08-15 (§9 F4). ⚠️ Grana (gruppo_key, commessa_id), e la commessa NON e'' ridondante: gruppo_key per una riga con documento sorgente vale ''<codice_interno>:<uid>'' e non la contiene, quindi lo stesso documento potrebbe alimentare righe su due commesse. La versione Python aggregava con min()/bool_or() e in quel caso avrebbe risposto «emittibile» perche'' UNA commessa lo era, perdendo proprio la diagnosi che serve; vw_dash_competenza_gruppi la commessa la tiene gia'' nel proprio GROUP BY. DIVISIONE DI COMPETENZE: qui i contatori, al BE la prosa — classifica_gruppo_non_servito compone le frasi italiane con accordo di genere e numero, ed e'' presentazione. La descrizione dello stato chiude la nota in coda al §8.3: quel valore finisce nella frase che l''operatore legge, e un codice interno dentro una frase e'' il sintomo che la decodifica e'' nel posto sbagliato. n_fuori_competenza e'' la sola classe che dipende da p_competenza_mese (righe pronte con competenza SUCCESSIVA al mese richiesto); NULL = nessun limite e quella classe resta vuota, con le righe in n_pronte. Un gruppo richiesto e sconosciuto esce comunque con commessa_id NULL e contatori a zero: farlo sparire sarebbe un silenzio. Le chiavi si normalizzano con btrim, come fa fn_build_gruppo_fatturabile_key. rev 2026-08-15: TOLTO n_senza_tipo_doc. Contava le righe APPROVATA + NON_EMESSA senza tipo documento, rifiutate da trgfn_commesse_attivita_guard_tipo_doc_emittibile e dal CHECK di tabella; il CHECK era pero'' NOT VALID e le righe preesistenti non erano mai state lette, quindi il ramo restava «forse» vivo. Il 20260815-30 ha validato il vincolo: adesso e'' irraggiungibile per costruzione, e un ramo che sembra coperto e non lo e'' vale meno di zero. ⚠️ Ricaduta BE: MOTIVO_TIPO_DOC_MANCANTE in classifica_gruppo_non_servito diventa morto anche li''. STABLE, sola lettura; commesse e commesse_attivita hanno la RLS, quindi la fotografia e'' gia'' scoped per emittente.';
```

---
{% include-markdown "signature-core.md" %}
