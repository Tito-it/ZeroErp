# Brief DB — Situazione aperta (Fase 3 due-lenti): stock documenti senza asse mese

> **Tipo**: brief DB (spec dal BE al team DB, ramo `dev/db-tid`) · **Data**: 2026-07-07 · **Owner**: Tid
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-bis (decisioni DL-9..13). **Contesto**: Fase 1 (Competenza) + Fase 2 (Backlog) BE+FE
> mergiate (PR #932); questa è la **Fase 3**, ridefinita da *dismissione* a *trasformazione*
> della dashboard 5-card nella vista **"Situazione aperta"**. Non in produzione: breaking
> change ammessi, nessuna fase di compatibilità.
>
> ## Stato: 🟢 DB APPLICATO + pgTAP VERDI (2026-07-07) — migrations `20260707-03..06` EXECUTED (applicate da Tid); test verdi: v1 rimaneggiato 28/28, aperto 10/10 (incluso scope RLS funzionale via FORCE), backlog 14/14 (regressione zero), competenza 15/15. NON committato. Prossimo: BE/FE (§4)
>
> Esito analisi critica DB (2026-07-07, verificata su DB vivo) — 3 correzioni al brief BE:
>
> 1. ⚠️ **Claim D-6 corretto**: i resolver preventivi/ordini/offerte **NON** escludono
>    l'esito NEGATIVO alla fonte (verificato: 18 righe abortite in union, tutte fase
>    CHIUSO) — lo **marcano** (`is_abortito`); escludeva la mensile con `FILTER`. Lo
>    stock lo esclude quindi **in vista** (`vw_dash_aperto_documenti`: `NOT is_abortito`).
> 2. **DL-13 (nuova, Tid 2026-07-07)**: lo stock include **tutte le fasi** (anche
>    CHIUSO, che cresce nel tempo — oggi 46 preventivi CHIUSO non abortiti): la vista è
>    consultazione neutra, **il FE decide quali card mostrare**. In più: vista dettaglio
>    gemella `vw_dash_aperto_documenti` come **perimetro unico** di card e drill-down
>    (il BE non replica filtri).
> 3. **pgTAP esistenti**: il brief non prevedeva il rimaneggiamento di
>    `test-vw-dash-fatturazione-v1.sql` (plan 28), che si rompeva in 6 punti —
>    rimaneggiato 1:1 (test 1 → 6 viste; 12-13 → de-esplosione + giudizio sospeso;
>    17-18 → union al posto della mensile; 20 → solo documenti). Nuovo
>    `test-vw-dash-aperto-v1.sql` (plan 10) con scope RLS via FORCE in-transazione.
>
> **Decisione di sequenza (Tid 2026-07-07)**: niente produzione ⇒ **nessun cutover
> coordinato** — tutte le attività DB subito (drop mensile incluso), il BE si adegua dopo.
>
> Deliverable: `20260707-03` resolver contratti de-esploso · `-04`
> `vw_dash_aperto_documenti` · `-05` `vw_dash_aperto_riepilogo` · `-06` drop
> `vw_dash_fatturazione_mensile` (senza CASCADE, verificato `pg_depend` = zero dipendenze
> DB) · pgTAP (rework + nuovo) · manuali (contratti aggiornato, 2 nuovi, mensile rimosso,
> link sistemati). SA-4: **confermato nulla da fare** (de-esplodendo sparisce l'EXISTS per
> mese; gli indici `20260703-58` restano per gli altri resolver).
>
> *Il testo sotto è il brief BE originale, con le correzioni §1/SA-2 integrate.*

---

## 0. Scopo in una riga

Fotografare lo **stock di documenti aperti** (Preventivi, Ordini, Offerte, Contratti — **no
Commesse**, coperte dalla Lente 1) raggruppato per **`fase` normalizzata**, **senza asse
temporale**: la 5-card perde l'impianto mensile (che era il pezzo semanticamente sbagliato)
e diventa una vista di consistenza della pipeline, 🟢 fisiologici inclusi (che il Backlog
esclude per costruzione: `classe <> 'FISIOLOGICO'` dentro `vw_dash_backlog_documenti`).

## 1. Contesto (cosa esiste già — non ricrearlo)

Verificato sul DB vivo (2026-07-07):

- `vendite.vw_dash_fatturazione_documenti` (union dei 5 resolver) espone **già** tutto ciò
  che serve al drill-down e alle card, inclusa la **`fase` normalizzata** (mai NULL sulle
  4 aree documento) → per la decisione DL-10 nessun lavoro DB.
- ⚠️ **Correzione**: la union **include** i documenti `esito = NEGATIVO` marcandoli
  `is_abortito` (l'esclusione D-6 era applicata dalla mensile via `FILTER`, e dal Backlog
  via `motivo_fermo NULL`); solo il resolver CONTRATTI li esclude alla fonte. Lo stock
  applica `NOT is_abortito` in `vw_dash_aperto_documenti`.
- Le viste girano `security_invoker` (fix `20260706-15`) → scope emittente via RLS.
- La Lente 2 vive sopra la union e **non va toccata** (criterio §3.4).
- `vw_dash_fatturazione_contratti` era **esplosa per mese**; `vw_dash_fatturazione_mensile`
  era consumata **solo** dal BE 5-card, in ritiro.

## 2. Deliverable

### SA-1 — Resolver contratti **de-esploso** (1 riga per contratto vivo) — `20260707-03`

Decisione **DL-12: consistenza pura, giudizio di transito sospeso** finché non esiste il
push ricorrente:

| Colonna | Valore | Perché |
|---|---|---|
| `competenza_mese` | `NULL` | senza periodo non ha significato |
| `data_riferimento` | `valido_dal` | "in essere da" (prima: mese esploso) |
| `unita_totali` | `1` | conteggio stock |
| `unita_transitate` / `is_transitato` | `NULL` | giudizio **sospeso**, non falso (falso-allarme perenne altrimenti) |
| `motivo_fermo` | `NULL` | `CANONE_NON_GENERATO`/`DOC_BOZZA` spariscono dal resolver (bozza leggibile da `fase`/`stato_codice_interno`); il seed `config.motivi_fermo` NON cambia (predisposizione riaccensione) |
| resto | invariato | filtro esito ≠ NEGATIVO, fase/stato, cliente_display, valori NULL |

La union **non va ricreata** (stesse colonne, NULL tipizzati). Impatto Backlog: zero
(contratti già esclusi prima, esclusi dopo).

### SA-2 — Stock: dettaglio + riepilogo — `20260707-04` / `-05`

- **`vw_dash_aperto_documenti`** (dettaglio, perimetro unico): union
  `WHERE area <> 'COMMESSE' AND NOT is_abortito`, **tutte le fasi** (DL-13), colonna
  derivata `is_aperto = is_transitato IS DISTINCT FROM true` (il sospeso conta aperto).
- **`vw_dash_aperto_riepilogo`** (card): `area × fase` → `n_documenti`, `n_aperti`,
  `valore_totale`/`valore_transitato` in `SUM` **senza COALESCE** (restano `NULL` per
  OFFERTE/CONTRATTI — DL-11, conferma D-2/D-3/D-4).
- Entrambe `security_invoker = on`.

### SA-3 — Drop `vw_dash_fatturazione_mensile` — `20260707-06`

Unico artefatto dismesso davvero. Verificato: **zero dipendenze DB** (`pg_depend`);
consumer solo BE (`VenditeRepository.list_dash_fatturazione_mensile` + `types.py`), che si
adegua dopo. `DROP` **senza CASCADE** (fail-fast su dipendenze inattese). Doc della vista
rimossa (manuale + auto-gen), link degli altri manuali reindirizzati.

### SA-4 — Verifica indici — ✅ nulla da fare

De-esplodendo sparisce l'EXISTS per mese dal resolver contratti; `20260703-58` resta a
servizio degli altri resolver. Riverifica con `EXPLAIN` solo a volumi reali.

## 3. Invarianti / criteri d'accettazione (pgTAP)

Coperti da `test-vw-dash-fatturazione-v1.sql` (rework, plan 28) e
`test-vw-dash-aperto-v1.sql` (nuovo, plan 10):

1. **De-esplosione**: contratto vivo a cavallo di 3 mesi → **1 riga** nella union (v1 #12).
2. **Giudizio sospeso**: `is_transitato/motivo_fermo NULL`, `unita_totali 1`,
   `competenza NULL`, `data_riferimento = valido_dal`; **resta sospeso anche con canone
   EMESSO in commessa** (v1 #12-13).
3. **D-6**: contratto NEGATIVO assente dalla union (v1 #14); **abortiti fuori dallo
   stock** pur presenti in union (aperto #4).
4. **Regressione Lente 2 = zero**: viste backlog non toccate da alcuna migration;
   contratti esclusi prima e dopo (`test-vw-dash-backlog-v1.sql` resta verde, test 10).
5. **Riepilogo = dettaglio**: somme coerenti; solo 4 aree, mai COMMESSE (aperto #3, #7).
6. **Fase valorizzata**: nessuna riga stock con `fase NULL` (aperto #8).
7. **Scope emittente**: FORCE RLS in-transazione + GUC operatore → emittente B invisibile
   (aperto #9, skip-conditional a singolo emittente).
8. **Misura**: `valore_*` per PREVENTIVI/ORDINI, `NULL` per OFFERTE/CONTRATTI (aperto #7).
9. **Drop pulito**: mensile assente, drop senza CASCADE (v1 #1).

## 4. Fuori scope (BE/FE, dopo il DB)

- Ritiro dei 2 endpoint `dashboard-fatturazione/{,fermi/}` e restyle della pagina in
  "Situazione aperta" (card per `fase` + drill-down per stato, riuso `DonutTransito`/
  `dashboardAree.js`) — BE/FE su `dev/backend-tid`, **prerequisiti DB pronti**. Nota BE:
  leggere `vw_dash_aperto_{riepilogo,documenti}` (perimetro già filtrato, niente
  `NOT is_abortito` applicativo).
- Ricollocazione i18n `motivo_fermo`/`area_*` in gruppo condiviso (il Backlog li riusa).
- Push ricorrente contratti e riaccensione del giudizio canone (progetto a sé;
  `CANONE_NON_GENERATO` resta seedato in `config.motivi_fermo` apposta).

---

*A chiusura: aggiornato §6-bis/§11-Fase 3 del design-of-record;
[brief-design-dashboard-fatturazione.md](brief-design-dashboard-fatturazione.md) si sposta
in `work-done` a trasformazione BE/FE avvenuta.*
