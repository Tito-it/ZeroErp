{% include-markdown "it/dbzero/vendite/manual/fn_diagnostica_gruppi_fatturabili.md" %}
# ⚙️ Funzione `fn_diagnostica_gruppi_fatturabili`

```sql
CREATE FUNCTION fn_diagnostica_gruppi_fatturabili(p_gruppi text[], p_competenza_mese date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_diagnostica_gruppi_fatturabili(p_gruppi text[], p_competenza_mese date DEFAULT NULL::date)
 RETURNS TABLE(gruppo_key text, commessa_id bigint, commessa_codice text, commessa_stato_codice_interno text, commessa_stato_descrizione text, commessa_emittibile boolean, n_righe bigint, n_emesse bigint, n_annullate bigint, n_rifiutate bigint, n_non_approvate bigint, n_fuori_competenza bigint, n_pronte bigint, terne_pronte jsonb, n_trattenute bigint, lotti_trattenenti jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_bound vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
  -- =========================================================
  -- Scopo: la FOTOGRAFIA di uno o piu' gruppi fatturabili —
  --   quante righe hanno, in che stato sono, in che stato e'
  --   la testata della commessa, e in quale CORSIA ricade il
  --   lavoro ancora pronto. Serve a spiegare all'operatore
  --   perche' un gruppo che aveva chiesto di fatturare non e'
  --   stato servito.
  --   brief-db-emittibilita-visibile-e-sbloccabile §9 F4, §10.6.
  --
  -- Grana: (gruppo_key, commessa_id). ⚠️ La commessa NON e'
  --   ridondante: gruppo_key per una riga con documento sorgente
  --   vale '<codice_interno>:<uid>' e non la contiene, quindi lo
  --   stesso documento potrebbe alimentare righe su due commesse.
  --   La versione Python aggregava con min()/bool_or() e in quel
  --   caso avrebbe detto «emittibile» perche' UNA lo era,
  --   mancando proprio la diagnosi che serve.
  --
  -- rev 2026-08-15 (a): via `n_senza_tipo_doc` — dopo la
  --   validazione del CHECK (20260815-30) e' un ramo
  --   irraggiungibile, e un ramo che sembra coperto e non lo e'
  --   vale meno di zero.
  -- rev 2026-08-15 (b): + `terne_pronte`. La corsia non si
  --   prevede, si MISURA: le righe ancora pronte portano gia' la
  --   terna con se', ed e' quella su cui la lane raggruppa.
  --   Incrociata con le terne FALLITE del giro (che il BE ha
  --   negli esiti, come fatti) distingue «non servito perche' il
  --   perimetro non lo ammetteva» da «non servito perche'
  --   l'esecuzione si e' rotta» — il primo si corregge, il
  --   secondo si riprova.
  --   ⚠️ Sta QUI e non nel consuntivo perche' qui i criteri di
  --   «riga pronta» ci sono gia' (sono quelli di n_pronte):
  --   metterlo in fn_esito_gruppi_giro avrebbe voluto dire
  --   ricopiarli, ed e' la duplicazione che questo cantiere ha
  --   tolto.
  --
  -- Divisione di competenze: qui i CONTATORI e i FATTI, al BE la
  --   PROSA. Il DB dice quanti, in che stato e in quale corsia;
  --   il BE dice come si racconta.
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
    -- ⭐ rev 2026-09-09 — LA SEDE UNICA DEL CRITERIO (changeSet -59).
    --   Questa funzione e' «lo specchio della lane»: i criteri che conta uno
    --   per uno erano gli stessi che la lane filtrava, scritti due volte.
    --   🔴 E si erano gia' rotti: il 20260909-25 ha aggiunto un criterio alla
    --   lane e non qui, e la diagnosi rispondeva «era pronto» su un documento
    --   che la lane non aveva offerto. Ora il criterio non e' scritto in
    --   nessuna delle due: la lane filtra la classe, questa la conta.
    SELECT e.gruppo_key,
           e.commessa_id,
           -- ⚠️ Il `::text` resta VOLUTO su queste tre: sono valori di
           --   DISPLAY che finiscono nella frase composta dal backend, non
           --   specchi di colonna da ancorare con %TYPE.
           e.commessa_codice::text                    AS commessa_codice,
           e.commessa_stato_codice_interno::text      AS commessa_stato_codice_interno,
           e.commessa_stato_descrizione::text         AS commessa_stato_descrizione,
           -- ⭐ IL SECONDO FATTORE, tenuto SEPARATO dalla classe: e' cio' che
           --   permette a questa funzione di dire «le righe sarebbero pronte,
           --   e' la commessa a essere in BOZZA» — la sola cosa che sa dire
           --   meglio della lane, e la ragione per cui i due fattori non si
           --   fondono.
           e.commessa_emittibile,
           e.classe_emittibilita,
           e.competenza_mese,
           e.tipo_doc_fiscale_id,
           e.trattenuta_da_lotti,
           -- La CORSIA della riga: le tre colonne su cui la lane raggruppa.
           e.emittente_soggetto_ruolo_id              AS terna_emittente,
           e.utility_id                               AS terna_utility,
           -- ⚠️ «PRONTA» qui significa «pronta PER QUESTO MESE»: la classe non
           --   conosce il tetto di competenza, che e' perimetro della domanda.
           (e.classe_emittibilita = 'PRONTA'
            AND (v_bound IS NULL OR e.competenza_mese <= v_bound)) AS e_pronta
      FROM vendite.vw_commesse_attivita_emittibilita e
     WHERE e.gruppo_key IN (SELECT q.gruppo_key FROM richiesti q)
  )
  SELECT d.gruppo_key,
         x.commessa_id,
         x.commessa_codice,
         x.commessa_stato_codice_interno,
         x.commessa_stato_descrizione,
         x.commessa_emittibile,
         count(x.gruppo_key)::bigint AS n_righe,
         -- ⭐ Un contatore per CLASSE: i criteri non si riscrivono, si contano.
         count(*) FILTER (WHERE x.classe_emittibilita = 'EMESSA')::bigint    AS n_emesse,
         count(*) FILTER (WHERE x.classe_emittibilita = 'ANNULLATA')::bigint AS n_annullate,
         count(*) FILTER (WHERE x.classe_emittibilita = 'RIFIUTATA')::bigint AS n_rifiutate,
         count(*) FILTER (WHERE x.classe_emittibilita = 'NON_APPROVATA')::bigint AS n_non_approvate,
         -- ⚠️ «Fuori competenza» NON e' una classe: quella riga e' PRONTA,
         --    solo non per QUESTO mese. E' il tetto della domanda, non
         --    l'ammissibilita' della riga — per questo il conto sta qui.
         count(*) FILTER (
           WHERE x.classe_emittibilita = 'PRONTA'
             AND v_bound IS NOT NULL
             AND x.competenza_mese > v_bound)::bigint AS n_fuori_competenza,
         -- n_pronte e terne_pronte guardano lo STESSO predicato
         -- (`e_pronta`): il conteggio e l'elenco delle corsie non
         -- possono raccontare due cose diverse.
         count(*) FILTER (WHERE x.e_pronta)::bigint AS n_pronte,
         -- Le corsie in cui ricade il lavoro ancora pronto.
         -- ⚠️ Array e non tre colonne: un gruppo puo' stare su
         -- piu' corsie, perche' tipo_doc_fiscale_id sta sulla
         -- RIGA (fatto G15). ⚠️ '[]' e mai NULL quando non c'e'
         -- nulla di pronto: «nessuna corsia» e «non calcolato»
         -- devono restare distinguibili.
         -- ⚠️ ORDER BY dentro l'aggregato: l'ordine dev'essere
         -- DETERMINISTICO, o due chiamate identiche danno valori
         -- diversi e chi li confronta vede differenze finte.
         COALESCE(
           jsonb_agg(DISTINCT jsonb_build_object(
                       'emittente_soggetto_ruolo_id', x.terna_emittente,
                       'tipo_doc_fiscale_id',         x.tipo_doc_fiscale_id,
                       'utility_id',                  x.terna_utility)
                     ORDER BY jsonb_build_object(
                       'emittente_soggetto_ruolo_id', x.terna_emittente,
                       'tipo_doc_fiscale_id',         x.tipo_doc_fiscale_id,
                       'utility_id',                  x.terna_utility))
             FILTER (WHERE x.e_pronta),
           '[]'::jsonb) AS terne_pronte,
         -- ⭐⭐ IL CONTATORE CHE MANCAVA, ed e' il difetto che ha aperto il
         --   cantiere: dal 20260909-25 la lane non offre piu' un documento
         --   trattenuto da un lotto in gioco, e questa fotografia continuava a
         --   contarlo fra le righe PRONTE. Il backend ne ricavava «N attivita'
         --   risultano pronte ma il gruppo non e' entrato in nessun lotto:
         --   verificare emittente e utility» — due cose giuste da controllare,
         --   e non una parola sull'unica che contava.
         -- ⚠️ Si conta la CLASSE per intero, senza spezzarla sul tetto di
         --   competenza: il tetto separa il PRONTO, che e' l'unica classe su
         --   cui la domanda «per quale mese?» ha senso.
         count(*) FILTER (WHERE x.classe_emittibilita = 'TRATTENUTA')::bigint AS n_trattenute,
         -- ⭐ E il lotto che trattiene, perche' «trattenuto» senza dire DA COSA
         --   non e' azionabile: il backend ne compone la frase e il frontend
         --   ci disegna il gesto «vai al lotto».
         -- ⚠️ `[]` e mai NULL, come terne_pronte: «nessun lotto» e «non
         --   calcolato» devono restare distinguibili.
         -- ⚠️ DISTINCT + ORDER BY: la stessa coppia (gruppo, commessa) puo'
         --   avere piu' righe tenute dagli stessi lotti, e due chiamate
         --   identiche devono dare lo stesso array.
         COALESCE((
           SELECT jsonb_agg(jsonb_build_object('id', l.id, 'codice', l.codice)
                            ORDER BY l.id)
             FROM (SELECT DISTINCT unnest(y.trattenuta_da_lotti) AS lotto_id
                     FROM righe y
                    WHERE y.gruppo_key = d.gruppo_key
                      AND y.commessa_id IS NOT DISTINCT FROM x.commessa_id
                      AND y.trattenuta_da_lotti IS NOT NULL) u
             JOIN vendite.fatturazione_lotti l ON l.id = u.lotto_id
         ), '[]'::jsonb) AS lotti_trattenenti
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
IS 'FOTOGRAFIA di uno o piu'' gruppi fatturabili: quante righe hanno e in che stato, la testata della commessa (codice, stato codice interno E descrizione, flag emittibile), e in quale CORSIA ricade il lavoro ancora pronto. Serve a spiegare perche'' un gruppo che l''operatore aveva chiesto di fatturare non e'' stato servito. Porta a DB l''SQL che stava in CommesseRepository.diagnostica_gruppi — ultima copia dei filtri di vendite.fn_list_emittibili_lane rimasta fuori dal database (brief-db-emittibilita-visibile-e-sbloccabile §5.2, accolta §9 F4). ⚠️ Grana (gruppo_key, commessa_id), e la commessa NON e'' ridondante: gruppo_key per una riga con documento sorgente vale ''<codice_interno>:<uid>'' e non la contiene. DIVISIONE DI COMPETENZE: qui i contatori e i fatti, al BE la prosa. n_fuori_competenza e'' la sola classe che dipende da p_competenza_mese; NULL = nessun limite e quella classe resta vuota. Un gruppo richiesto e sconosciuto esce comunque con commessa_id NULL e contatori a zero: farlo sparire sarebbe un silenzio. Le chiavi si normalizzano con btrim. rev 2026-08-15 (a): TOLTO n_senza_tipo_doc — dopo il 20260815-30 (CHECK validato) e'' un ramo irraggiungibile. rev 2026-08-15 (b): + terne_pronte jsonb, risposta alla domanda §10.6 del BE. In un giro mirato parziale con una terna FALLITA, i gruppi di quella terna hanno ancora righe da emettere e il consuntivo li dichiara NON_SERVITO — corretto — ma la diagnosi di perimetro a valle attribuisce la causa piu'' prossima che vede («verificare emittente e utility»), mandando l''operatore a controllare una cosa giusta mentre bastava riprovare. terne_pronte da'' la corsia (emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id) delle righe ancora pronte: incrociata con le terne fallite, che il BE ha gia'' negli esiti del giro come FATTI, distingue «non servito perche'' il perimetro non lo ammetteva» da «non servito perche'' l''esecuzione si e'' rotta». ⭐ NON e'' una previsione: la corsia non si stima, si misura sul presente — sono le stesse tre colonne su cui la lane raggruppa. Era il vincolo della domanda: il BE non aveva chiuso il caso da solo per non rimettere in gioco gruppi_coperti, che il §9.7 aveva chiesto di togliere. ⚠️ Sta qui e non in fn_esito_gruppi_giro perche'' qui i criteri di «riga pronta» esistono gia'' (sono quelli di n_pronte, e il predicato e'' scritto una volta sola e condiviso): nel consuntivo avrebbero dovuto essere ricopiati. ⚠️ Array e non tre colonne scalari: un gruppo puo'' stare su piu'' corsie perche'' tipo_doc_fiscale_id sta sulla RIGA (fatto G15). ⚠️ Vale ''[]'' e mai NULL quando non c''e'' nulla di pronto: «nessuna corsia» e «non calcolato» devono restare distinguibili. Ordine deterministico. STABLE, sola lettura; commesse e commesse_attivita hanno la RLS. ⭐ rev 2026-09-09: I CRITERI NON SONO PIU'' SCRITTI QUI. Si legge `classe_emittibilita` da vendite.vw_commesse_attivita_emittibilita, la stessa sede che fn_list_emittibili_lane FILTRA: lo «specchio» non puo'' piu'' divergere, ed era gia'' successo — il 20260909-25 aveva aggiunto un criterio alla lane e non qui, e questa fotografia rispondeva «era pronto» su un documento che la lane non offriva. ⭐ + n_trattenute e lotti_trattenenti (array di {id, codice}, ''[]'' e mai NULL): il contatore che mancava e il lotto da nominare, perche'' «trattenuto» senza dire DA COSA non e'' azionabile. ⚠️ Le righe TRATTENUTE escono da n_pronte — e'' il verso della correzione. ⚠️ Il secondo fattore `commessa_emittibile` resta SEPARATO dalla classe: e'' cio'' che permette di dire «le righe sarebbero pronte, e'' la commessa a essere in BOZZA», la sola cosa che questa funzione sa dire meglio della lane.';
```

</div>

---
{% include-markdown "signature-core.md" %}
