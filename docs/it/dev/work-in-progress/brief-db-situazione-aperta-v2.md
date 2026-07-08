# Brief DB — Situazione aperta v2: serbatoio pre-commessa (viste ridotte agli aperti-non-chiusi)

> **Tipo**: brief DB (spec per il team DB, ramo `dev/db-tid`) · **Data**: 2026-07-08 · **Owner**: Tid
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-ter (decisioni DL-14..18, 2026-07-08). **Contesto**: la Situazione aperta v1
> (`20260707-03..06`, PR #938) è mergiata e validata in-app; alla validazione Tid ne ha
> ridefinito la semantica. Questo brief modifica **solo le 2 viste** `vw_dash_aperto_*`.
> Non in produzione: breaking change ammessi, nessuna fase di compatibilità.

---

## 0. Scopo in una riga

La Situazione aperta diventa il **serbatoio pre-commessa**: mostrare **solo** i documenti
**aperti e non conclusi** (`is_aperto AND fase <> 'CHIUSO'`), eliminando il concetto
**"transitato"** — che in una vista senza asse temporale totalizza *dalla notte dei tempi*
documenti già passati avanti o conclusi, informazione non azionabile. Le viste si
**restringono nel perimetro** e si **snelliscono nelle colonne** (via tutto il transitato).

## 1. Contesto (cosa esiste già — non ricrearlo)

Verificato sul DB vivo (doc auto-gen, 2026-07-08):

- `vendite.vw_dash_aperto_documenti` (v1): union `WHERE area <> 'COMMESSE' AND NOT
  is_abortito`, **tutte le fasi**, espone `is_transitato`, `is_aperto` (derivata),
  `valore_transitato`, `unita_transitate`.
- `vendite.vw_dash_aperto_riepilogo` (v1): `GROUP BY area, fase` con `n_documenti`,
  `n_aperti` (FILTER `is_aperto`), `valore_totale`, `valore_transitato`.
- La union **sorgente** `vw_dash_fatturazione_documenti` **NON va toccata**: continua a
  esporre `is_transitato`/`valore_transitato`/`motivo_fermo` (la Lente 2 Backlog ci vive
  sopra via `vw_dash_backlog_documenti`). Le viste `aperto` sono le **uniche** a cambiare
  → blast radius minimo.
- `data_riferimento` è già nella union (data documento; `valido_dal` per i contratti):
  basta al filtro "oltre N giorni" (che è **BE-side**, vedi §4 — nessun oggetto DB nuovo).
- `security_invoker = on` su entrambe le viste: **da preservare** (attenzione al gotcha
  `CREATE OR REPLACE` che azzera le reloptions — vedi il rework §5 del brief v1;
  ricreare con `WITH (security_invoker = on)`).

## 2. Deliverable

### SA2-1 — `vw_dash_aperto_documenti` ristretta e snellita

Perimetro nuovo (**entrambi** i predicati — DL-15):

```sql
WHERE area <> 'COMMESSE'
  AND NOT is_abortito
  AND (is_transitato IS DISTINCT FROM true)   -- solo aperti (giudizio sospeso contratti = aperto)
  AND fase <> 'CHIUSO'                         -- solo non conclusi
```

Razionale dei due filtri insieme (nessuno dei due basta da solo):
- `is_aperto` da solo lascia i **chiusi-non-transitati** (es. offerta SUPERATA: non
  transitata, non abortita, ma conclusa) → li toglie `fase<>CHIUSO`.
- `fase<>CHIUSO` da solo lascia i **transitati-non-chiusi** (es. preventivo ACCETTATO già
  completamente smistato, resta IN_CORSO) → li toglie `is_aperto`.

Colonne da **rimuovere** (tutte costanti/prive di senso nel nuovo perimetro): `is_transitato`,
`is_aperto` (derivata — ora sempre true), `valore_transitato`, `unita_transitate`. `is_transitato`
resta usato **solo nel WHERE** (dalla union), non più esposto. Colonne che **restano**: `area,
documento_id, documento_uid, codice, emittente_fiscale_id, emittente_soggetto_ruolo_id,
cliente_display, fase, stato_codice_interno, stato_codice, valore_totale, unita_totali,
motivo_fermo, data_riferimento`. (`motivo_fermo` resta come hint informativo di riga; il team
valuti se droppabile — nella v2 il taglio primario è la fase, ma non fa danno tenerlo.)

### SA2-2 — `vw_dash_aperto_riepilogo` snellita

`GROUP BY area, fase` su `n_documenti` (ora = tutti aperti) e `valore_totale`. **Rimuovere**
`n_aperti` (ridondante: coincide con `n_documenti`) e `valore_transitato`. Le fasi presenti
saranno solo APERTO / IN_ATTESA / IN_CORSO (CHIUSO escluso a monte dalla dettaglio); non tutte
le aree hanno tutte le fasi (es. ORDINI/CONTRATTI senza IN_ATTESA) — il completamento a griglia
è a carico del BE come oggi.

### SA2-3 — pgTAP aggiornato

`test-vw-dash-aperto-v1.sql` → v2: il perimetro esclude ora CHIUSO e i transitati; asserire in
particolare i due casi-limite che motivano i due filtri: (a) documento **transitato non chiuso**
(accettato+smistato, IN_CORSO) → **assente**; (b) documento **chiuso non transitato** (offerta
superata) → **assente**; (c) contratto ATTIVO (aperto, IN_CORSO) → **presente**; (d) contratto
CESSATO → **assente**. Più: colonne transitato rimosse dal contratto vista; `n_documenti =
n_aperti` non più (colonna sparita); scope RLS invariato (FORCE + GUC come v1). Regressione Lente
2 Backlog: **zero** (viste backlog non toccate).

### SA2-4 — `security_invoker` e indici

- Ricreare entrambe le viste **`WITH (security_invoker = on)`** (non perderlo col REPLACE).
- Indici: il filtro "oltre N giorni" è BE-side su `data_riferimento` (già nella union); nessun
  indice nuovo richiesto per il pilota. Verificare a volumi reali se serve un indice a
  espressione sulla data-documento delle tabelle sorgente (non pilot-blocking).

## 3. Invarianti / criteri d'accettazione (pgTAP)

1. **Solo aperti-non-chiusi**: ogni riga ha `fase IN ('APERTO','IN_ATTESA','IN_CORSO')` e
   `is_transitato IS DISTINCT FROM true` sulla union sorgente.
2. **Transitato-non-chiuso escluso** (accettato+smistato IN_CORSO) — caso (a) sopra.
3. **Chiuso-non-transitato escluso** (offerta superata) — caso (b) sopra.
4. **Contratti**: ATTIVO presente (IN_CORSO), CESSATO assente, ANNULLATO assente (abortito).
5. **Colonne transitato assenti** dalla dettaglio; `n_aperti`/`valore_transitato` assenti dal
   riepilogo.
6. **Riepilogo = dettaglio**: `n_documenti`/`valore_totale` per (area,fase) coerenti con
   l'aggregazione della dettaglio.
7. **Misura**: `valore_totale` valorizzato per PREVENTIVI/ORDINI, `NULL` per OFFERTE/CONTRATTI.
8. **Scope emittente**: `security_invoker=on` su entrambe (assert su `pg_class.reloptions`,
   come il guard del brief v1); FORCE RLS + GUC → emittente altrui invisibile.
9. **Regressione zero** su `vw_dash_backlog_*` e sulla union `vw_dash_fatturazione_documenti`.

## 4. Fuori scope (BE/FE, dopo il DB) — vedi [brief-be-fe-situazione-aperta-v2.md](brief-be-fe-situazione-aperta-v2.md)

- Filtro **"aperti da oltre N giorni"**: puramente **BE-side** (WHERE `data_riferimento <=
  current_date - N`), **solo sul drill-down** (le card restano la fotografia completa — DL-17).
  Nessun oggetto DB, nessuna colonna nuova.
- Rimozione del parametro/toggle `solo_aperti` (endpoint + FE).
- Donut per fase, `DASH_APERTO_FASI` a 3 fasi, TypedDict snelliti, i18n.

---

*A chiusura: aggiornare la doc manuale `vw_dash_aperto_{documenti,riepilogo}.md` (perimetro
v2, colonne rimosse) e spostare questo brief in `work-done` a viste applicate + pgTAP verdi.*
