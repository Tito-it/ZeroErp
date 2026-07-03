# Brief Design — Dashboard Fatturazione (controllo del transito per competenza)

> **Tipo**: brief di design autorevole (modello + piano DB/BE/FE) · **Data**: 2026-07-02
> **Owner**: Tid · **Stato**: 🟢 **Fase 1 DB APPLICATA + TESTATA (2026-07-03)** —
> migrations `20260703-51..57` (20_code/vendite: 5 resolver + union
> `vw_dash_fatturazione_documenti` + aggregata `vw_dash_fatturazione_mensile`) +
> `20260703-58` (90_end: indici `ix_commesse_attivita_segment_key` e
> `ix_commesse_attivita_sorgente_competenza`) + **fix `20260703-59`**
> (is_abortito null-safe, vedi §11) + doc manuale
> `dbzero/vendite/manual/vw_dash_fatturazione_*.md` a standard.
> pgTAP `test-vw-dash-fatturazione-v1.sql` **VERDE 19/19** sul DB di sviluppo.
> Prossimo: Fase 2 BE (§11); EXPLAIN su dati reali da fare quando i volumi crescono.
>
> **Origine**: richiesta Tid 2026-07-02 — "dashboard fondamentale per avere sotto controllo
> la fatturazione": per un dato anno/mese di **competenza**, per ciascuna area che porta
> alla fatturazione (preventivi, ordini, offerte commerciali, contratti, commesse), mostrare
> il **valore totale** e il **valore transitato** verso l'area successiva. Quando
> `totale = transitato` il mese è a posto; la differenza sono gli **elementi fermi**, da
> esplorare col drill-down per area.
>
> **Documenti collegati**:
> [Guida fatturazione](../../guide/fatturazione.md) ·
> [Guida commesse](../../guide/gestione-commesse.md) ·
> [Guida preventivi](../../guide/gestione-preventivi.md) ·
> [Guida ordini](../../guide/gestione-ordini.md) ·
> [Guida offerte](../../guide/gestione-offerte-commerciali.md) ·
> [Guida contratti](../../guide/gestione-contratti.md) ·
> [brief-db-proiezione-stato-dominio](../work-done/brief-db-proiezione-stato-dominio.md) e
> [roll-out 4 domini](../work-done/brief-db-proiezione-stato-dominio-rollout-offerte-ordini-contratti.md)
> (forniscono `script.vw_stato_sorgente` con `fase/esito/terminale`, usata qui per il
> perimetro "documenti vivi").

---

## 1. Problema — il funnel della fatturazione non ha un cruscotto

Tutte le sorgenti di ricavo convergono **obbligatoriamente** sulla commessa prima di
diventare fattura (nessun bypass verso `attivita_fatturabili`):

```text
offerte ──► contratti ─┐
   │                   ├──► commesse ──► attività fatturabili ──► lotti ──► fatture
   └─────► ordini ─────┤        ▲
preventivi ─┬──────────┘        │
            └───────────────────┘   (righe servizio una-tantum)
```

Ogni tratto ha già la sua meccanica di push e il suo tracciamento (§3), ma **non esiste
alcun punto di osservazione aggregato**: per sapere se "tutto il valore di maggio è
arrivato in fattura" oggi bisogna aprire documento per documento. Ricognizione 2026-07-02:
nessuna vista `vw_*totali*`/aggregata di periodo nel DB, nessun endpoint BE di statistiche,
nessuna pagina dashboard FE (solo i 4 placeholder KPI in `HomeView.vue`).

## 2. Principio — proiezione di consultazione, zero nuova logica

La dashboard è una **proiezione read-only** sopra lo stato che il dominio già scrive:

1. **Non introduce stati, flag o colonne sui documenti**: il "transitato" si **deriva** dai
   link che i push scrivono già (FK, tabelle ponte, `segment_key`, `stato_emissione`).
2. **DB-first**: la semantica totale/transitato/fermo vive in viste PostgreSQL; Django
   espone due endpoint sottili; Vue presenta.
3. Nel modello concentrico è un anello di **consultazione** (come la proiezione stato
   dominio): dipende da vendite+config+script, nessuno dipende da lei.

## 3. Cosa esiste già (ricognizione verificata 2026-07-02)

### 3.1 Competenza temporale — dove è nativa e dove va derivata

| Entità | Colonna | Note |
|---|---|---|
| `vendite.preventivi` | `competenza_mese` (date, nullable, testata) | CHECK 1° del mese; scritta all'accettazione |
| `vendite.commesse_attivita` | `competenza_mese` (date NOT NULL, riga) | normalizzata dal trigger; **è la competenza "vera" del funnel** |
| `vendite.attivita_fatturabili` | `competenza_mese` (date NOT NULL) | CHECK 1° del mese |
| `vendite.fatturazione_lotti` | `competenza_mese` (date NOT NULL) | perimetro del lotto |
| `vendite.ordini` | **nessuna** | ha `data` (date) |
| `vendite.offerte_commerciali` | **nessuna** | ha `validita_dal` NOT NULL, `data_emissione`, `data_accettazione` |
| `vendite.contratti` | **nessuna** (periodo) | ha `validita` daterange NOT NULL; `contratti_righe.competenza_canone` è una *modalità* (ANTICIPATA/POSTICIPATA), non una data |

Precedente di derivazione già codificato: `fn_list_preventivi_da_pushare` usa
`COALESCE(validita_dal, competenza_mese, data)`.

### 3.2 Tracciamento del transito — per coppia

| Tratto | Come si riconosce a posteriori |
|---|---|
| preventivo → ordine | `ordini_righe.preventivo_riga_id` + `ordini.documento_origine_tipo='PREVENTIVO'` |
| preventivo → commessa | `commesse_attivita.segment_key = 'PREV:<uid>:R:<riga>'` + `commesse_sorgenti` |
| ordine → commessa | `commesse_sorgenti` / `segment_key`; residuo enumerato da `fn_list_ordini_da_pushare` |
| offerta → contratto | `contratti.offerta_id` (UNIQUE `uq_contratti_offerta_id`) |
| offerta → ordine | `ordini.documento_origine_tipo='OFFERTA'` + UNIQUE parziale `uq_ordini_v_documento_origine_offerta` |
| contratto → commessa (ricorrente) | `commesse_attivita` del mese riconducibili al contratto (sorgente CONTRATTO / `contratto_id` snapshot) |
| commessa → fattura | `commesse_attivita.stato_emissione='EMESSA'`; poi `attivita_fatturabili.fattura_riga_id IS NOT NULL` = fatturata |

Per i **preventivi** esiste già la classificazione canonica riga-livello:
`vw_preventivi_smistamento_righe.stato_smistamento ∈ {FATTURATA, EMESSA_AF, IN_COMMESSA,
A_ORDINE, RESIDUA}` (+ aggregato `vw_preventivi_smistamento`). Le altre aree non hanno
l'equivalente: il deliverable D2 (§11) lo introduce per gli ordini, in simmetria.

### 3.3 Perimetro "documenti vivi" — proiezione stato dominio

`script.vw_stato_sorgente` (union dei 4 resolver `vw_stato_sorgente_{preventivo,offerta,
ordine,contratto}`) espone `fase ∈ {APERTO, IN_CORSO, IN_ATTESA, CHIUSO}`, `esito ∈ {NULL,
POSITIVO, NEGATIVO, PARZIALE}`, `terminale`. Serve qui per la regola-cardine:

> **I documenti chiusi con esito NEGATIVO (annullati, rifiutati, scaduti, superati) sono
> ESCLUSI dal "valore totale".** Non transiteranno mai per definizione: se restassero nel
> totale, `totale = transitato` non tornerebbe mai e la dashboard perderebbe il suo
> significato di semaforo. Il drill-down può mostrarli in un contatore separato
> ("abortiti nel mese"), fuori dal confronto.

### 3.4 Valori — dove sono materializzati

| Entità | Totali testata | Nota |
|---|---|---|
| preventivi | `totale_imponibile`, `totale_iva`, `totale_documento` | trigger di ricalcolo |
| ordini | `imponibile_tot`, `sconto_tot`, `iva_tot`, `totale_doc` | trigger di ricalcolo |
| offerte | **nessuno** | righe = eccezioni al listino; valore solo via `fn_offerta_righe_espanse` |
| contratti | **nessuno** | valore ricorrente (delta listino), nessun canone mensile totalizzato |
| commesse | **nessuno** in testata | valore = Σ `commesse_attivita.prezzo_snapshot × quantita` |

**Decisione (D-4 §9): la misura è l'IMPONIBILE** (senza IVA), per confrontabilità
cross-area — i valori delle attività di commessa (`prezzo_snapshot × quantita`) sono
imponibili per natura.

## 4. Semantica v1 per area — totale, transitato, fermo

Legenda: 💶 = area con valore in euro; 🔢 = area a conteggi (v1, vedi decisioni D-2/D-3).

| Area | Bucket competenza | Totale | Transitato | Fermo (drill-down) |
|---|---|---|---|---|
| **Preventivi** 💶 | `COALESCE(competenza_mese, date_trunc('month', validita_dal), date_trunc('month', data))` | Σ imponibile righe attive dei preventivi con esito ≠ NEGATIVO | Σ imponibile righe con `stato_smistamento ≠ 'RESIDUA'` | righe RESIDUE (con stato doc: EMESSO in attesa vs ACCETTATO non smistato) |
| **Ordini** 💶 | `date_trunc('month', data)` | Σ `imponibile_tot` ordini con esito ≠ NEGATIVO | Σ imponibile righe già in commessa | ordini DRAFT + righe CONFERMATE non ancora pushate |
| **Offerte** 🔢 | `date_trunc('month', COALESCE(validita_dal, data_emissione))` | n. offerte vive (esito ≠ NEGATIVO) | n. offerte con contratto/ordine generato **e vivo** | ACCETTATE senza figlio; caso speciale "bloccata" (§10.1) |
| **Contratti** 🔢 | mesi M con `validita @> M` (un contratto pesa su ogni mese coperto) | n. contratti ATTIVI nel mese | n. contratti con canone del mese già in `commesse_attivita` | ATTIVI senza attività di competenza M |
| **Commesse** 💶 | `commesse_attivita.competenza_mese` | Σ `prezzo_snapshot × quantita` righe attive (commesse non ANNULLATE) | Σ righe con `stato_emissione = 'EMESSA'` | attività NON_EMESSE, distinte per `stato_approvazione` (BOZZA vs APPROVATA) |

Note di semantica:

* **Preventivi/Ordini a livello riga, non testata**: un preventivo ACCETTATO può avere
  transito parziale (resta ACCETTATO finché c'è residuo bi-ramo); un ordine resta
  CONFERMATO se il push è parziale. Lo stato testata da solo mentirebbe.
* **Doppio conteggio accettato per design**: lo stesso euro compare in "preventivi"
  e poi in "ordini" e poi in "commesse" — la dashboard misura **ogni tratto del funnel**,
  non il fatturato consolidato (che è la colonna fatture, fuori scope v1, §10.3). Ogni
  card risponde a "quest'area ha spinto avanti tutto il suo mese?".
* **Commesse = tratto finale pre-fattura**: il transitato è l'emissione in
  `attivita_fatturabili`; il drill-down mostra anche il secondo livello (fatturata =
  `fattura_riga_id IS NOT NULL`) come informazione, senza terzo spicchio.

## 5. Architettura DB (Fase 1)

Layering identico alla proiezione stato dominio: **un resolver per area + union +
aggregata**, tutto read-only, schema `vendite` (tutte le sorgenti sono lì).

| Vista | Grana | Colonne (contratto) |
|---|---|---|
| `vw_dash_fatturazione_preventivi` / `_ordini` / `_offerte` / `_contratti` / `_commesse` | 1 riga per **documento × mese** | `area, competenza_mese, documento_id, documento_uid, codice, emittente_soggetto_ruolo_id, valore_totale, valore_transitato, unita_totali, unita_transitate, is_fermo, motivo_fermo, stato_codice, fase` |
| `vw_dash_fatturazione_documenti` | union delle 5 | idem, `area` discriminante |
| `vw_dash_fatturazione_mensile` | `area × competenza_mese` | `valore_totale, valore_transitato, n_documenti, n_transitati, n_fermi, n_abortiti` |

Regole implementative:

* Per le aree 🔢 `valore_*` = NULL e si popolano `unita_*` (conteggi); per le aree 💶
  entrambe (il conteggio serve comunque alla card).
* `motivo_fermo` è un codice interno per il drill-down parlante
  (`RIGA_RESIDUA`, `IN_ATTESA_ACCETTAZIONE`, `ORDINE_DRAFT`, `PUSH_PARZIALE`,
  `SENZA_FIGLIO`, `FIGLIO_ABORTITO`, `CANONE_NON_GENERATO`, `NON_APPROVATA`,
  `NON_EMESSA`, …) — vocabolario chiuso definito in Fase 1, decodifica i18n lato FE.
* Il filtro "vivi" passa da `script.vw_stato_sorgente` (join per `sorgente_tipo_id +
  sorgente_uid` come da `config.sorgenti.key_selector`); le commesse, che non hanno
  resolver, filtrano su `stato_commessa_id ≠ ANNULLATA`.
* **RLS gratis**: le viste girano come invoker → la Row Level Security emittente su
  preventivi/ordini/offerte/contratti (attiva dal 2026-06) filtra automaticamente il
  perimetro dell'operatore. Nessuna logica scope duplicata.
* **Performance**: v1 = viste normali (i volumi attuali lo consentono); l'aggregata è
  pensata per reggere una futura materializzazione (o tabella di snapshot notturno via
  pgAgent) **senza cambiare il contratto verso il BE** — soglia di guardia da misurare
  in Fase 1 con `EXPLAIN` su dati reali. Attenzione nota dal roll-out proiezione: il
  join su `uid::text` può richiedere indici a espressione.
* pgTAP: fixture minime per area (preventivo con riga residua + riga a ordine, offerta
  con/senza contratto, contratto attivo con/senza canone, commessa con attività
  emessa/non emessa) e assert sui totali dell'aggregata.
* Doc: le viste finiscono nell'auto-gen `docs/it/dbzero/vendite/views/`; la semantica
  va in doc manuale (`docs/it/dbzero/vendite/manual/`) + sezione guida (§11 Fase 4).

## 6. Backend (Fase 2)

Due endpoint in `apps/vendite` (pattern `DomainAPIView`, `area_funzionale="vendite"`,
GET-only, livello LETTURA sufficiente):

```text
GET /api/v1/vendite/dashboard-fatturazione/?anno=2026
→ data: { anno, mesi: [ { competenza_mese: "2026-01-01",
           aree: [ { area, valore_totale, valore_transitato,
                     n_documenti, n_transitati, n_fermi, n_abortiti } ×5 ] } ×12 ] }

GET /api/v1/vendite/dashboard-fatturazione/fermi/?competenza_mese=2026-05-01&area=PREVENTIVI&page=1
→ lista paginata standard dal livello documento (codice, valore, motivo_fermo, stato, link)
```

* Il BE **genera sempre i 12 mesi** dell'anno richiesto (LEFT JOIN su
  `generate_series`): i mesi senza dati arrivano al FE con zeri — il contratto API
  incorpora la decisione D-5 (§9), niente logica calendario nel FE.
* `anno` libero (validato `qp_int_strict`, range sensato es. 2000–2100).
* Repository in `vendite_repository.py` (lettura da vista, nessun sottodominio nuovo:
  regola naming `<schema>_repository`); niente service dedicato se resta pura lettura.
* `@extend_schema` inline, test service con mock repository, doc
  `docs/it/backend/vendite/manual/api_dashboard_fatturazione.md` (template standard).

## 7. Frontend (Fase 3)

Nuova rotta `/vendite/dashboard-fatturazione` (meta.domain `vendite`, voce menu in
`core/navigation.js`), vista `vendite/views/DashboardFatturazioneView.vue`.

```text
┌──────────┬────────────────────────────────────────────────────────┐
│  ANNO    │  Competenza Maggio 2026          [↻]                   │
│ ◀ 2026 ▶ │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│          │ │Preventivi│ │ Ordini  │ │ Offerte │ │Contratti│ │Commesse │
│ Gen    ✓ │ │  ◔ 82%  │ │  ◕ 95% │ │  12/15  │ │  40/42  │ │  ◑ 60%  │
│ Feb    ✓ │ │ 12.400 € │ │ 9.800 € │ │  (n.)   │ │  (n.)  │ │ 11.300 €│
│ Mar  ⚠ 3 │ └─────────┘ └─────────┘ └─────────┘ └────────┘ └─────────┘
│ Apr    ✓ │  Totale mese: 33.500 €  ·  transitato 29.100 €  ·  fermi 4.400 €
│ ▶Mag ⚠ 7 │ ─────────────────────────────────────────────────────────
│ Giu    · │  Fermi — Preventivi (click su card)                     │
│ …        │  [DataTable: codice · valore · motivo · stato · apri]   │
│ Dic    · │                                                         │
└──────────┴────────────────────────────────────────────────────────┘
```

* **Pannello laterale**: selettore anno **libero** (frecce ◀ ▶ + input) e lista fissa
  dei **12 mesi, sempre tutti presenti** — mesi vuoti con zeri/pallino neutro. Ogni voce
  mostra il semaforo del mese: ✓ se `totale = transitato` su tutte le aree, ⚠ con il
  numero di fermi altrimenti. Così l'anno si legge senza aprire i mesi, e a novembre
  si può già lavorare sull'anno successivo (supera il vecchio schema "mese corrente+1"
  che nascondeva competenze future).
* **Card area**: donut a 2 spicchi (transitato vs fermo) per le aree 💶 con gli importi,
  frazione `n/n` per le aree 🔢; click → pannello fermi sotto (stessa pagina, non drawer:
  il confronto card↔dettaglio deve restare visibile).
* **Grafici**: `chart.js` + componente PrimeVue `<Chart>` (decisione D-1). Wrapper nostro
  `core/components/charts/DonutTransito.vue` (palette da variabili `theme.css`, non colori
  hardcoded) così le view non parlano mai con chart.js direttamente.
* **Drill-down fermi**: DataTable standard (`app-datatable`, paginazione top) con
  `motivo_fermo` decodificato i18n e azione "apri documento" che naviga alla lista area
  con `?search=<codice>` (pattern ricerca-universale già esistente); per le commesse,
  che non hanno una view FE, la riga resta consultiva (niente link, v1).
* Store Pinia `vendite/stores/dashboardFatturazione.js` (anno, mese selezionato, matrice,
  fermi); API client in `vendite/api/`. i18n `it/en` completo. `useApiHandler`/`useNotify`
  standard; refresh via `PageActionsBar`.

## 8. Casi limite (gestiti dal design)

1. **Offerta "bloccata"** — l'offerta resta `ACCETTATA` dopo il push (nessuno stato
   post-push) e la XOR contratto/ordine è **permanente**: se il figlio viene annullato
   l'offerta non può rigenerarlo. Non è né "transitata viva" né "ferma rimediabile":
   nel drill-down ha `motivo_fermo = FIGLIO_ABORTITO` con badge dedicato (richiede
   revisione dell'offerta, azione manuale).
2. **Lag della proiezione stato** — `vw_stato_sorgente` proietta lo stato *scritto*: un
   preventivo scaduto-per-data ma non ancora flippato dal job notturno risulta ancora
   vivo. Accettato: coerente con tutto il resto del sistema.
3. **Competenza NULL** — i fallback `COALESCE` (§4) garantiscono che ogni documento cada
   in un mese (le colonne di fallback sono NOT NULL); nessun bucket "senza competenza".
4. **Consumi utility** — entrano in commessa come riga singola (decisione 2026-06-16) e
   quindi nell'area Commesse; nessuna area dedicata in v1.

## 9. Decisioni prese (2026-07-02, Tid)

| # | Decisione | Scelta |
|---|---|---|
| D-1 | Libreria grafici | **chart.js + PrimeVue `<Chart>`** (nuova dipendenza npm approvata da Tid) |
| D-2 | Valore offerte v1 | **Solo conteggi** (n. vive vs n. transitate); € rinviato a v2 |
| D-3 | Valore contratti v1 | **Conteggi attivi vs canone-generato**; "canone atteso" calcolato è un progetto a sé (v2+) |
| D-4 | Misura monetaria | **Imponibile** (senza IVA) su tutte le aree 💶 |
| D-5 | Navigazione periodi | **Anno libero, 12 mesi sempre visibili** (mesi vuoti = zeri) |
| D-6 | Perimetro totale | **Esclusi i documenti con esito NEGATIVO** (contatore separato `n_abortiti`) |

## 10. Non-obiettivi v1

1. **Valore € di offerte e contratti** (D-2/D-3) — richiede rispettivamente totalizzazione
   dell'espansione listino e calcolo del canone atteso.
2. **Riconciliazione con le fatture emesse** — sesta colonna "Fatture del mese"
   (Σ per `data_contabilizzazione` o competenza lotto): candidata naturale per v2,
   chiude il funnel end-to-end. Evoluta in **pagina dedicata** (vedi annotazioni §12).
3. **DDT e consumi come aree autonome**, trend multi-mese (linee), export XLSX del
   drill-down, snapshot storici/materializzazione (predisposta ma non attivata, §5).

## 11. Piano di sviluppo

| Fase | Dove | Deliverable | Stato |
|---|---|---|---|
| 0 — Design | questo brief | semantica per area + decisioni D-1..D-6 | ✅ 2026-07-02 |
| 1 — DB | `dev/db-tid` | 5 viste resolver + union + `vw_dash_fatturazione_mensile`; vocabolario `motivo_fermo`; pgTAP; doc manuale; EXPLAIN su dati reali | ✅ APPLICATA + pgTAP 19/19 VERDE 2026-07-03 (`20260703-51..59`); EXPLAIN rinviato a volumi reali |
| 2 — BE | `dev/backend-tid` | 2 endpoint GET + repository + test + `api_dashboard_fatturazione.md` | ⬜ |
| 3 — FE | `dev/backend-tid` | chart.js, `DonutTransito`, vista+store+rotta+menu+i18n | ⬜ |
| 4 — Guida | docs | sezione "Dashboard fatturazione" nella guida fatturazione (linguaggio non tecnico) | ⬜ |

Domande di Fase 1 — **chiuse in implementazione (2026-07-03)**:

* **`segment_key` ordini**: `'ORD:<uid>:R:<riga_id>'` (verificato in
  `fn_list_ordini_da_pushare`); contratti: `'CONTR:<uid>:R:<riga_id>:M:YYYY-MM'`.
* **Marcatore canone contratti**: colonne `sorgente_tipo_id` (sorgente CONTRATTO per
  `codice_interno`) + `sorgente_uid` + `competenza_mese` su `commesse_attivita`, con
  `stato_emissione='EMESSA'` — future-proof rispetto al push ricorrente. Nota: oggi
  `fn_list_contratti_da_pushare` ancora il canone al **mese di inizio validità**
  (nessuna iterazione mensile): nei mesi successivi i contratti appaiono fermi
  (`CANONE_NON_GENERATO`) — è la realtà operativa finché non esisterà il push
  ricorrente, la dashboard non la maschera.
* **Indici**: niente join su `vw_stato_sorgente` (i resolver joinano direttamente le
  proprie `config.stati_doc_*`, più economico); aggiunti invece
  `ix_commesse_attivita_segment_key` e `ix_commesse_attivita_sorgente_competenza`
  (90_end `20260703-58`) per gli EXISTS di transito.

Decisioni implementative aggiuntive (Fase 1):

* **Predicato canonico EMESSA**: una riga presente in commessa ma `NON_EMESSA` conta
  come ferma in tutte le aree (stesso NOT EXISTS delle `fn_list_*_da_pushare` e della
  vista smistamento, test #6 di `test-vw-preventivi-smistamento-v1.sql`). Conseguenza:
  il valore parcheggiato non-emesso risulta fermo sia nell'area sorgente sia in
  COMMESSE — coerente: non è avanzato.
* **Contratti × mese, cap al mese corrente**: niente righe-mese future (la domanda
  "canone generato?" ha senso solo per mesi non futuri) e niente esplosione per i
  contratti aperti.
* **Contratti abortiti esclusi a monte** dal resolver: `n_abortiti = 0` per l'area
  CONTRATTI in v1 (un annullato per-mese non ha significato).

Diario applicazione + test (2026-07-03, DB sviluppo):

* **Bug scovato dal pgTAP (test 18) → fix `20260703-59`**: nei resolver
  preventivi/ordini/offerte `is_abortito = (esito = 'NEGATIVO')` valeva **NULL**
  per gli stati senza verdetto (esito NULL: BOZZA, DRAFT, EMESSO…) e nella mensile
  quei documenti sparivano sia da `n_documenti` sia da `n_abortiti` (i `FILTER`
  scartano i NULL). Fix: `COALESCE(esito = 'NEGATIVO', false)`; regressione
  bloccata dall'assert #8 (offerta BOZZA → `is_abortito = false`).
* **Fixture pgTAP**: in contesto test la GUC `app.current_user_id` è vuota →
  gli INSERT su `vendite.contratti` devono passare `emittente_fiscale_id`
  esplicito (derivato dal BA via `anagrafiche.fn_get_emittente_fiscale_pk`,
  pattern batch documentato da `E_CONTRATTO_EMITTENTE_NON_RISOLTO`);
  `commesse_attivita.competenza_al` è NOT NULL (niente attività "aperte").
* Esito finale: `test-vw-dash-fatturazione-v1.sql` **19/19 verde**.

## 12. Annotazioni v2 — Dashboard fatturato (idee Tid 2026-07-03, da non perdere)

Durante la validazione grafica del mock FE è emerso che questa dashboard copre il
funnel **fino all'emissione** (commesse → attività fatturabili) ma manca il tratto
finale: **il fatturato**. Decisione: NON si aggiunge una sesta card qui — sarà una
**pagina dashboard dedicata**, da progettare con un brief proprio quando si aprirà
il cantiere. Idee da riprendere in quel brief:

1. **Riconciliazione commesse ↔ fatturato** — per mese di competenza, confronto tra
   il valore presente in commessa (Σ `commesse_attivita`) e il valore effettivamente
   fatturato (`attivita_fatturabili.fattura_riga_id IS NOT NULL` → righe fattura):
   la differenza è il "non ancora fatturato", speculare al totale/transitato di
   questa dashboard ma sull'ultimo tratto del funnel.
2. **Breakdown del fatturato per stato fattura** — il totale fatturato da solo non
   basta: serve la ripartizione per stato del documento fiscale (es. quanto in
   BOZZA/DRAFT, quanto numerato, quanto inviato a SDI, ecc. — stati da
   `config.stati_doc_fiscale`), così si vede quanta parte del fatturato del mese è
   davvero consolidata e quanta è ancora in lavorazione nella pipeline lotti.
3. **Log di fatturazione in dashboard** — pannello/drill-down sugli errori: fatture
   ferme in errore nella pipeline, alimentato da `vendite.fatture_log` (flag
   `critical`) e dai run della pipeline lotti (`fatturazione_lotti_task_runs`).
   Obiettivo: dal cruscotto si vede subito se c'è un lotto/fattura inceppato, senza
   andare a caccia nei log.

Nota di perimetro: il punto 2 e il punto 3 riguardano lo **stato interno** del
processo di fatturazione (pipeline lotti), non il transito per competenza — un
motivo in più per tenerli su una pagina separata con semantica propria. La sesta
colonna "Fatture del mese" citata in §10.2 resta assorbita da questa pagina.
