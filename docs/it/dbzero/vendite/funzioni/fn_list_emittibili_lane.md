{% include-markdown "it/dbzero/vendite/manual/fn_list_emittibili_lane.md" %}
# ⚙️ Funzione `fn_list_emittibili_lane`

```sql
CREATE FUNCTION fn_list_emittibili_lane(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer, p_gruppi text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_emittibili_lane(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_fatturazione_immediata boolean DEFAULT NULL::boolean, p_limit integer DEFAULT 1000, p_gruppi text[] DEFAULT NULL::text[])
 RETURNS TABLE(emittente_soggetto_ruolo_id bigint, tipo_doc_fiscale_id bigint, utility_id integer, competenza_mese date, total_candidate bigint, gruppi_coperti text[])
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
  v_corsia          record;
  v_n               integer := 0;
BEGIN
  -- =========================================================
  -- Scopo: rispondere al driver batch "quali TERNE distinte
  --   (emittente, tipo_doc, utility) hanno lavoro pronto da
  --   fatturare, e fino a quale competenza creare il lotto".
  -- Criteri:
  --   1. commessa in stato emittibile (stati_commessa.emittibile=true)
  --   2. righe commesse_attivita APPROVATA + NON_EMESSA (allineato pull)
  --   3. tipo_doc_fiscale_id NOT NULL (il lotto lo richiede)
  --   4. competenza CUMULATIVA: competenza_mese <= p_competenza_mese
  --      (coerente con fn_select_attivita_fatturabili); NULL = no limite
  --   5. filtri perimetro BA/utility/emittente; corsia fatturazione_immediata
  --   6. rev 2026-08-15: + gruppi_coperti text[] — QUALI gruppi
  --      fatturabili sono finiti in questa terna. Senza, un'emissione
  --      parziale (3 gruppi chiesti, 2 serviti) non sa dire quale sia
  --      rimasto fuori. ⚠️ E' una PREVISIONE: per il consuntivo di
  --      cio' che un giro ha davvero fatturato usare
  --      vendite.fn_esito_gruppi_giro(lotti).
  --   7. rev 2026-07-27: p_gruppi restringe ai GRUPPI FATTURABILI
  --      richiesti, cosi' l'emissione mirata non fa nascere un lotto
  --      per ogni altra terna del perimetro (lotti vuoti = rumore).
  --      NULL = nessuna restrizione (comportamento storico).
  --   8. rev 2026-08-15 (§9 F7): il TETTO non tronca piu' in
  --      silenzio una richiesta MIRATA. Vedi il blocco qui sotto.
  -- Grana: (emittente, tipo_doc, utility). utility_id e' NOT NULL a monte
  --   (commesse.utility_id) -> in output mai NULL.
  -- Output per terna: competenza_mese = max(...), total_candidate = count(*).
  -- Regole: p_limit max 10000/default 1000; competenza normalizzata al mese;
  --   STABLE (read-only); LIMIT sulle TERNE.
  -- =========================================================
  IF p_limit IS NULL OR p_limit <= 0 THEN
    p_limit := 1000;
  END IF;
  IF p_limit > 10000 THEN
    p_limit := 10000;
  END IF;

  v_competenza_mese := CASE
    WHEN p_competenza_mese IS NOT NULL
    THEN date_trunc('month', p_competenza_mese)::date
    ELSE NULL
  END;

  -- ⚠️ SI LEGGE UNA CORSIA IN PIU' DEL TETTO (LIMIT p_limit + 1).
  -- Alla corsia numero p_limit + 1 si sa che ce n'era dell'altra,
  -- e si puo' distinguere «erano esattamente p_limit» da «sono
  -- state tagliate». Il conto si fa scorrendo il risultato UNA
  -- volta: un secondo SELECT count(*) di controllo sarebbe stata
  -- una seconda copia dei filtri di discovery dentro la stessa
  -- funzione, cioe' l'errore che il §7.1 ha gia' corretto.
  FOR v_corsia IN
    SELECT
      e.emittente_soggetto_ruolo_id  AS emittente_sr,
      e.tipo_doc_fiscale_id          AS tipo_doc,
      e.utility_id                   AS utility,
      max(e.competenza_mese)         AS competenza,
      count(e.commessa_attivita_id)::bigint AS candidate,
      -- I gruppi fatturabili coperti da questa terna.
      -- ⭐ rev 2026-09-09: la chiave arriva GIA' COSTRUITA dal classificatore,
      -- che la calcola una volta per riga dalla sola fonte di verita'
      -- (vendite.fn_build_gruppo_fatturabile_key). Prima era invocata qui, e
      -- l'intestazione spiegava perche' l'ORDER BY dentro l'aggregato non la
      -- valutasse due volte: quel paragrafo non serve piu'.
      -- ⚠️ ORDER BY dentro l'aggregato: l'ordine dev'essere DETERMINISTICO,
      -- altrimenti due chiamate identiche danno array diversi e chi li
      -- confronta (l'esito, un test) vede differenze che non esistono.
      array_agg(DISTINCT e.gruppo_key ORDER BY e.gruppo_key) AS gruppi
    -- ⭐ LA SEDE UNICA DEL CRITERIO (changeSet 20260909-59). Qui non si
    --   scrive PIU' nessuna condizione di ammissibilita': si LEGGE la classe.
    --   La gemella fn_diagnostica_gruppi_fatturabili conta le stesse classi,
    --   quindi le due non possono piu' divergere — ed e' successo davvero, il
    --   2026-09-09: un criterio aggiunto qui e non li'.
    FROM vendite.vw_commesse_attivita_emittibilita e
    -- ⭐ I DUE FATTORI, dichiarati. La lane li pretende ENTRAMBI: la RIGA
    --   dev'essere pronta e la TESTATA emittibile. La diagnostica li tiene
    --   separati apposta, per poter dire «le righe sarebbero pronte, e' la
    --   commessa a essere in BOZZA» — ed e' la differenza che prima era
    --   IMPLICITA, cioe' indistinguibile da una svista.
   WHERE e.classe_emittibilita = 'PRONTA'
     AND e.commessa_emittibile
     -- ⚠️ IL PERIMETRO DELLA DOMANDA resta qui, e non nella vista: dipende da
     --   chi chiede, non dalla riga. La competenza e' CUMULATIVA (<=), ed e'
     --   anche il motivo per cui «fuori competenza» non e' una classe: quella
     --   riga e' PRONTA, solo non per QUESTO mese.
     AND (v_competenza_mese IS NULL OR e.competenza_mese <= v_competenza_mese)
     AND (p_billing_account_id IS NULL OR e.billing_account_id = p_billing_account_id)
     AND (p_utility_id IS NULL OR e.utility_id = p_utility_id)
     AND (p_emittente_soggetto_ruolo_id IS NULL OR e.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
     AND (p_fatturazione_immediata IS NULL OR e.fatturazione_immediata = p_fatturazione_immediata)
     -- EMISSIONE MIRATA (rev 2026-07-27): un gruppo con righe di tipo doc
     -- diverso resta su piu' terne, e vengono restituite tutte (G15).
     AND (p_gruppi IS NULL OR e.gruppo_key = ANY (p_gruppi))
    GROUP BY
      e.emittente_soggetto_ruolo_id,
      e.tipo_doc_fiscale_id,
      e.utility_id
    ORDER BY
      e.emittente_soggetto_ruolo_id,
      e.tipo_doc_fiscale_id,
      e.utility_id
    LIMIT p_limit + 1
  LOOP
    v_n := v_n + 1;

    IF v_n > p_limit THEN
      -- Siamo oltre il tetto: c'era altro lavoro e non entra.
      IF p_gruppi IS NOT NULL THEN
        -- MIRATA: il perimetro e' NOMINALE. Troncare una richiesta
        -- nominale non e' un successo parziale, e' una richiesta
        -- senza risposta — e a valle diventerebbe una diagnosi
        -- FALSA («questi gruppi non sono fatturabili») su gruppi
        -- che erano solo oltre il taglio.
        -- ⚠️ Il RETURN NEXT accumula in un tuplestore: sollevando
        -- qui il chiamante non riceve NESSUNA riga, mai una mezza
        -- risposta accompagnata da un errore.
        PERFORM script.fn_log_and_raise_error(
          'vendite', 'fn_list_emittibili_lane',
          'E_FATTURAZIONE_MIRATA_TRONCATA',
          jsonb_build_object('p_limit', p_limit,
                             'gruppi_richiesti', cardinality(p_gruppi)),
          NULL::uuid, p_limit::text);
      END IF;
      -- MASSA: il tetto e' una valvola di sicurezza, e troncare
      -- e' il comportamento storico. Si esce senza rumore.
      EXIT;
    END IF;

    emittente_soggetto_ruolo_id := v_corsia.emittente_sr;
    tipo_doc_fiscale_id         := v_corsia.tipo_doc;
    utility_id                  := v_corsia.utility;
    competenza_mese             := v_corsia.competenza;
    total_candidate             := v_corsia.candidate;
    gruppi_coperti              := v_corsia.gruppi;
    RETURN NEXT;
  END LOOP;

  RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_emittibili_lane(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer, p_gruppi text[])
IS 'Read-only/STABLE: discovery delle corsie (emittente, tipo_doc_fiscale, utility, competenza_mese) pronte da fatturare per il driver batch. Grana per-utility (il lotto e'' segregato per utility: fn_create pretende utility NOT NULL, fn_select filtra ba.utility_id). utility_id mai NULL (commesse.utility_id NOT NULL); coerenza c.utility_id=ba.utility_id garantita da fn_get_or_create_commessa. Criterio APPROVATA+NON_EMESSA, tipo_doc NOT NULL, competenza cumulativa (<=) con output competenza_mese=max. Filtri perimetro + corsia fatturazione_immediata. fn_list_commesse_emittibili resta separata e invariata. rev 2026-07-27 (brief emissione mirata A5): p_gruppi text[] restringe alle terne dei gruppi richiesti — NULL = nessuna restrizione (G1). Un gruppo con righe di tipo doc fiscale diverso resta su piu'' terne e vengono restituite TUTTE (G15): e'' il motivo per cui l''esito verso il BE e'' una lista di lotto_id. rev 2026-08-15 (brief emittibilita §5): + gruppi_coperti text[], l''elenco DETERMINISTICO dei gruppi fatturabili coperti da ciascuna terna, per il caso dell''emissione PARZIALE che prima era muto. La chiave arriva da vendite.fn_build_gruppo_fatturabile_key, unica fonte di verita'', mai ricostruita qui. ⚠️ gruppi_coperti e'' una PREVISIONE, non un consuntivo: dice quali gruppi la discovery si aspetta di coprire, e fra quel momento e l''esecuzione le righe possono essere prese da un altro giro. Per sapere cosa un giro ha fatturato DAVVERO usare vendite.fn_esito_gruppi_giro(lotti) — brief emittibilita §8.2. ⚠️ Il campo si calcola SEMPRE, anche nel giro di massa, ed e'' deliberato: un campo che a volte vale NULL perche'' «non calcolato» e a volte perche'' «nessun gruppo» e'' il tipo di ambiguita'' che si paga sei mesi dopo. COSTO MISURATO (2026-08-15, 100k righe sintetiche): la chiave vale ~5 µs a chiamata, cioe'' ~0,5 s ogni 100.000 righe candidate — sul cron non morde. ⭐ E la mitigazione «ovvia» NON esiste: sembra che l''ORDER BY dentro l''aggregato valuti la funzione una seconda volta e che basti una LATERAL per dimezzare, ma il parser deduplica l''espressione dell''ORDER BY con quella dell''argomento quando sono identiche — la valutazione e'' gia'' una sola per riga, e le due forme misurano uguale. Scritto perche'' e'' controintuitivo e qualcuno lo riproverebbe. rev 2026-08-15 (§9 F7): il TETTO p_limit non tronca piu'' in silenzio una richiesta MIRATA. Si legge una corsia in piu'' del tetto e, se ce n''era dell''altra: con p_gruppi valorizzato si solleva E_FATTURAZIONE_MIRATA_TRONCATA, perche'' il perimetro mirato e'' NOMINALE e una corsia tagliata porterebbe via i suoi gruppi, che a valle risulterebbero «non fatturabili» pur essendo solo fuori dal taglio — una diagnosi falsa al posto di un errore; sul giro di MASSA il tetto resta una valvola di sicurezza e tronca come prima. Il conteggio si fa scorrendo il risultato UNA volta (RETURN NEXT): un secondo SELECT count(*) sarebbe stato una seconda copia dei filtri di discovery dentro la stessa funzione. ⚠️ RETURN NEXT accumula in un tuplestore, quindi sollevando non esce nessuna riga: mai una mezza risposta piu'' un errore. ⭐ rev 2026-09-09: I CRITERI DI AMMISSIBILITA'' NON SONO PIU'' SCRITTI QUI. Si leggono da vendite.vw_commesse_attivita_emittibilita — questa funzione filtra `classe_emittibilita = PRONTA` piu'' il fattore di TESTATA `commessa_emittibile`, e la gemella fn_diagnostica_gruppi_fatturabili conta le stesse classi: le due non possono piu'' divergere. Il PERIMETRO DELLA DOMANDA (competenza cumulativa, billing account, utility, emittente, corsia, p_gruppi) resta qui, perche'' dipende da chi chiede e non dalla riga. Firma e uscita invariate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
