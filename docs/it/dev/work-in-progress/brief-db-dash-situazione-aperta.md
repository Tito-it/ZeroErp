# Brief DB — Situazione aperta (Fase 3 due-lenti): stock documenti senza asse mese

> **Tipo**: brief DB (spec per il team DB, ramo `dev/db-tid`) · **Data**: 2026-07-07 · **Owner**: Tid
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-bis (decisioni DL-9..12, 2026-07-07). **Contesto**: Fase 1 (Competenza) + Fase 2 (Backlog)
> BE+FE mergiate (PR #932); questa è la **Fase 3**, ridefinita da *dismissione* a
> *trasformazione* della dashboard 5-card nella vista **"Situazione aperta"**.
>
> Il team DB possiede la **DDL esatta** (nomi, forma fisica, indici, pgTAP). Questo brief fissa
> **semantica, invarianti e criteri d'accettazione**. Non in produzione: breaking change ammessi,
> nessuna fase di compatibilità.

---

## 0. Scopo in una riga

Fotografare lo **stock di documenti aperti** (Preventivi, Ordini, Offerte, Contratti — **no
Commesse**, coperte dalla Lente 1) raggruppato per **`fase` normalizzata**, **senza asse
temporale**: la 5-card perde l'impianto mensile (che era il pezzo semanticamente sbagliato)
e diventa una vista di consistenza della pipeline, 🟢 fisiologici inclusi (che il Backlog
esclude per costruzione: `classe <> 'FISIOLOGICO'` dentro `vw_dash_backlog_documenti`).

## 1. Contesto (cosa esiste già — non ricrearlo)

Verificato sul DB vivo (doc auto-gen, 2026-07-07):

- `vendite.vw_dash_fatturazione_documenti` (union dei 5 resolver) espone **già** tutto ciò
  che serve al drill-down e alle card: `area, documento_id/uid, codice, emittente_fiscale_id,
  valore_totale, valore_transitato, unita_totali, unita_transitate, is_transitato,
  is_abortito, motivo_fermo, stato_codice_interno, stato_codice, `**`fase`**`,
  cliente_display, data_riferimento`. La **`fase` normalizzata è già lì** (join
  `config.stati_doc_*`) → per la decisione DL-10 **non serve alcun lavoro DB**.
- I resolver escludono già i documenti `esito = NEGATIVO` (regola D-6) e girano
  `security_invoker` (fix `20260706-15`) → scope emittente via RLS gratis.
- La Lente 2 vive sopra la union: `vw_dash_backlog_documenti` = union `WHERE motivo_fermo
  IS NOT NULL AND classe <> 'FISIOLOGICO'` (+ lookup `config.motivi_fermo`);
  `vw_dash_backlog_riepilogo` aggrega per classe/area. **Non vanno toccate** (criterio §3.4).
- `vw_dash_fatturazione_contratti` è **esplosa per mese** (`CROSS JOIN LATERAL
  generate_series(valido_dal … LEAST(valido_al, mese corrente))` + EXISTS canone per mese).
- `vw_dash_fatturazione_mensile` (aggregata `area × competenza_mese`) è consumata **solo**
  dal BE della 5-card (`VenditeRepository.list_dash_fatturazione_mensile`), che questa
  trasformazione ritira.
- Indici già posati: `ix_commesse_attivita_segment_key`, `ix_commesse_attivita_sorgente_competenza`
  (`20260703-58`), `ix_preventivi_uid_text`.

## 2. Deliverable

### SA-1 — Resolver contratti **de-esploso** (1 riga per contratto vivo)

Nella vista stock un contratto deve comparire **una volta sola**, non una riga per mese
coperto. Semantica della riga contratto post-modifica (decisione **DL-12: consistenza pura,
giudizio di transito sospeso** finché non esiste il push ricorrente):

| Colonna | Valore | Perché |
|---|---|---|
| `competenza_mese` | `NULL` | senza periodo non ha significato |
| `data_riferimento` | `valido_dal` | proxy "in essere da" (oggi è il mese esploso) |
| `unita_totali` | `1` | conteggio stock |
| `unita_transitate` / `is_transitato` | `NULL` | giudizio **sospeso**, non falso: senza push ricorrente ogni contratto risulterebbe fermo in eterno (falso-allarme perenne) |
| `motivo_fermo` | `NULL` | `CANONE_NON_GENERATO`/`DOC_BOZZA` spariscono dal resolver contratti (la bozza resta leggibile da `fase`/`stato_codice`) |
| resto (`fase`, `stato_*`, `cliente_display`, `valore_* = NULL`, `is_abortito = false`, filtro esito ≠ NEGATIVO) | invariato | |

**Predisposizione futura** (non ora): quando esisterà il push ricorrente, il predicato
"canone del mese corrente generato" torna su `is_transitato`/`motivo_fermo` e i contratti
entrano anche in Lente 2 — il contratto colonne resta identico, si riempie.

**Impatto a valle — nullo per il Backlog**: i contratti oggi non vi compaiono comunque
(entrambi i motivi sono `FISIOLOGICO`); con `motivo_fermo = NULL` restano esclusi dal
filtro `motivo_fermo IS NOT NULL`. La mensile che aggrega l'esplosione viene dismessa (SA-3).

### SA-2 — Vista riepilogo `area × fase` (per le card)

Aggregata di consultazione sul perimetro **4 aree documento** (`area <> 'COMMESSE'`), grana
`area × fase`, per alimentare le card senza aggregare BE-side (DB-first). Contenuto minimo
per cella: `n_documenti`, `n_aperti` (documenti con `is_transitato IS DISTINCT FROM true` —
per i contratti, giudizio sospeso, coincide col totale), `valore_totale`, `valore_transitato`
(somme; restano `NULL` per le aree a conteggi OFFERTE/CONTRATTI — decisione DL-11, conferma
D-2/D-3/D-4). Nome suggerito `vw_dash_aperto_riepilogo`; forma fisica al team.
`security_invoker` come la famiglia (lo scope emittente deve filtrare anche l'aggregata).

### SA-3 — Drop `vw_dash_fatturazione_mensile` (coordinato col BE)

L'asse mensile per proxy è l'unico artefatto **dismesso davvero**. La vista è letta dal BE
5-card fino alla trasformazione: **changeset di drop separato**, da applicare nello stesso
giro del cutover BE/FE (come pattern cutover `20260706-24`) — il team lo prepari, Tid
coordina il momento. Verificare che nessun altro oggetto vi dipenda.

### SA-4 — Verifica indici (probabilmente nulla da fare)

Al variare del resolver contratti (via l'esplosione, resta l'EXISTS su
`commesse_attivita(sorgente_tipo_id, sorgente_uid, competenza_mese)` solo se/quando tornerà
il giudizio canone): verificare che gli indici esistenti (`20260703-58`) coprano i path
della union e del riepilogo; espressione `((uid::text))` sulle tabelle documento già
verificata per preventivi, controllare le altre solo se i piani lo richiedono.

## 3. Invarianti / criteri d'accettazione (pgTAP)

1. **De-esplosione**: contratto vivo a cavallo di N mesi → **1 riga** nella union (prima N).
2. **Giudizio sospeso**: contratto ATTIVO senza attività → `is_transitato IS NULL`,
   `motivo_fermo IS NULL`, `unita_totali = 1`; contratto DRAFT → idem, con `fase`/stato
   di bozza leggibili.
3. **D-6 invariata**: contratto con esito NEGATIVO assente dalla union.
4. **Regressione Lente 2 = zero**: output di `vw_dash_backlog_documenti` e
   `vw_dash_backlog_riepilogo` **identico** prima/dopo (contratti mai presenti; le altre
   4 aree intatte).
5. **Riepilogo coerente col dettaglio**: somme di `vw_dash_aperto_riepilogo` = aggregazione
   equivalente della union filtrata; solo le 4 aree documento (mai COMMESSE).
6. **Fase valorizzata**: ogni riga delle 4 aree documento ha `fase NOT NULL`.
7. **Scope emittente**: operatore con whitelist ristretta vede nel riepilogo solo i propri
   documenti (invoker + RLS, GUC settata nel test come da pattern `20260706-15`).
8. **Misura**: nel riepilogo `valore_*` valorizzato per PREVENTIVI/ORDINI, `NULL` per
   OFFERTE/CONTRATTI.
9. **Drop pulito**: `vw_dash_fatturazione_mensile` assente, nessuna dipendenza orfana.

## 4. Fuori scope (BE/FE, dopo il DB)

- Ritiro dei 2 endpoint `dashboard-fatturazione/{,fermi/}` e restyle della pagina in
  "Situazione aperta" (card per `fase` + drill-down per stato, riuso `DonutTransito`/
  `dashboardAree.js`) — BE/FE su `dev/backend-tid` **a prerequisiti DB pronti**.
- Ricollocazione i18n `motivo_fermo`/`area_*` dal gruppo `dashboard_fatturazione` a un
  gruppo condiviso (il Backlog li riusa) — FE, prima di cancellare il vecchio vocabolario.
- Push ricorrente contratti e riaccensione del giudizio canone (progetto a sé).

---

*A chiusura: aggiornare §6-bis/§11-Fase 3 del design-of-record e spostare
[brief-design-dashboard-fatturazione.md](brief-design-dashboard-fatturazione.md) in
`work-done` a trasformazione avvenuta.*
