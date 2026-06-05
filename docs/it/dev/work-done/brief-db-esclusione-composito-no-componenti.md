# Brief DB — Guard difensivo: ESCLUSIONE composita non inizializza componenti BoM

> **✅ CHIUSO 2026-06-05** — Consegnato dal team DB e mergiato (commit `75054a765`,
> PR #787 → #788). Guard `IF v_tipo_eccezione = 'ESCLUSIONE' THEN RETURN 0`
> aggiunto subito dopo il check `is_composito` in **entrambe** le fn init:
> - `20260605-06-update-fn-offerta-eccezione-componenti-init-guard-esclusione`
> - `20260605-07-update-fn-contratto-riga-componenti-init-guard-esclusione`
>   (incluso fix collaterale operatore jsonb `??` → `?`).
> pgTAP estesi: `test_offerte_eccezioni_componenti.sql`,
> `test-contratti-righe-componenti-v1.sql`. Allineato con BE (commit `879b5193b`)
> e FE. Suite servizi vendite verde (687). Implementazione conforme al brief.
>
> **Origine**: bug riscontrato da Tid il 2026-06-05 caricando su un'**offerta**
> un articolo **composito** con eccezione **ESCLUSIONE**. Errore
> `E_VENDITE_VALIDATION` → violazione `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`.
> OVERRIDE e articoli non compositi funzionano; salta **solo** la combinazione
> «composito + ESCLUSIONE».
>
> **Natura del brief**: descrive **cosa serve e perché** (la logica e la
> motivazione), **non il come**. La strada implementativa (dove leggere il tipo,
> struttura del guard, pgTAP) la sceglie il team DB nel rispetto dei pattern già
> rodati (`feedback_db_actions_passaggio_team`).
>
> **Stato applicativo**: la causa primaria è già stata **chiusa lato BE+FE** (vedi
> §4). Questo brief chiede un **guard difensivo a DB** (single source of truth),
> non sblocca il bug — il bug è già risolto per il flusso reale. È la rete di
> sicurezza che protegge da qualunque altro chiamante delle fn init.

---

## 1. Cosa succede (catena causale)

Un articolo composito è un pacchetto di componenti (BoM CASO A). Sull'eccezione
commerciale (offerte e contratti) il `tipo_eccezione` può essere:

- **OVERRIDE / AGGIUNTA** → l'articolo **ha un prezzo** (il CHECK impone
  `prezzo_unitario NOT NULL`);
- **ESCLUSIONE** → l'articolo è **escluso interamente**, **non ha prezzo** (il
  CHECK impone `prezzo_unitario IS NULL`).

Il bug, passo per passo:

1. Si crea un'eccezione **ESCLUSIONE** su un articolo **composito**.
2. Le funzioni di init dei componenti vengono invocate lo stesso:
   - `vendite.fn_offerta_eccezione_componenti_init`
   - `vendite.fn_contratto_riga_componenti_init`
   Entrambe **non guardano il `tipo_eccezione` del padre**: controllano solo
   `is_composito` e `quantita IS NOT NULL`, poi inseriscono i componenti.
3. L'INSERT nei componenti fa scattare il trigger AFTER
   `_z90_ricalcola_padre` → `script.trgfn_componenti_ricalcola_padre` →
   `script.fn_ricalcola_prezzo_padre_da_componenti`, che esegue
   `UPDATE ...eccezioni SET prezzo_unitario = COALESCE(SUM(figli ...), 0)`
   sulla **riga padre**.
4. Ma la riga padre è **ESCLUSIONE** → il prezzo dovrebbe restare NULL → il
   CHECK `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`
   (rispettivamente `chk_contrighe_prezzo_per_tipo_eccezione`) **rifiuta
   l'UPDATE** → l'intera operazione va in errore.

Perché gli altri casi passano:

- **Articolo non composito**: `..._componenti_init` è no-op (`RETURN 0` su
  `is_composito = FALSE`) → nessun componente, nessun ricalcolo → prezzo resta
  NULL → OK.
- **OVERRIDE composito**: il prezzo NOT NULL è ammesso (anzi richiesto), quindi
  il ricalcolo a `SUM(figli)` è legittimo → OK.

> Nota: l'`fn_ricalcola_prezzo_padre_da_componenti` è un **helper generico**
> condiviso da 5 tabelle `*_righe_componenti`. **Non va toccato**: accoppiarlo al
> modello eccezioni romperebbe la sua genericità. Il guard va messo a monte,
> nelle due fn init (vedi §3).

## 2. Decisione di modello (ratificata da Tid, 2026-06-05)

> **ESCLUSIONE = articolo escluso interamente → nessun prezzo, nessun componente
> BoM.** Non ha senso negoziare i prezzi dei pezzi di qualcosa che stai togliendo.

È la soluzione sul merito, non un tampone (`feedback_no_quick_fix_soluzione_assoluta`).

## 3. Cosa serve a DB (il guard difensivo)

In **entrambe** le funzioni di init dei componenti:

- `vendite.fn_offerta_eccezione_componenti_init`
- `vendite.fn_contratto_riga_componenti_init`

aggiungere un **early-return no-op** (coerente con i `RETURN 0` già presenti per
non-composito e quantità NULL): **se il `tipo_eccezione` della riga padre è
`ESCLUSIONE`, non inizializzare alcun componente e ritornare 0**.

- Le funzioni leggono già la riga padre per ricavare `articolo_id`, `uom`,
  `quantita`, `offerta_id`/`riga_contratto_id`: basta includere `tipo_eccezione`
  nello stesso SELECT e aggiungere il guard subito dopo il controllo
  `is_composito` (prima del loop di INSERT).
- Resta **idempotente** e non altera il comportamento di OVERRIDE/AGGIUNTA.

> **Perché a DB anche se BE/FE già filtrano**: single source of truth. Il bug
> nasce da un invariante di modello («ESCLUSIONE non ha componenti») che oggi non
> è protetto a livello DB ma solo dai chiamati applicativi. Il guard rende la fn
> sicura **per qualunque chiamante** (script, fix dati, futuri servizi), in linea
> con la filosofia DB-first del progetto.

## 4. Cosa è già stato fatto lato applicativo (non a carico DB)

La causa primaria è già chiusa, in modo **simmetrico su offerte e contratti**,
su tutti gli strati applicativi (sviluppo concentrico, difesa multi-livello):

- **BE** — l'auto-init dei componenti viene saltato per le ESCLUSIONI:
  - `offerte_service.crea_eccezione`: `if is_composito and tipo_eccezione != "ESCLUSIONE"`
  - `contratti_service.create_riga`: gate analogo prima di `init_componenti_riga`
- **FE** — la `ComponentiDialog` non si apre e i `componenti_overrides` non
  vengono inviati per le ESCLUSIONI:
  - `OffertaEccezioniDrawer.vue` e `ContrattoRigheDrawer.vue`: i getter
    `isComposito`/`isPadreComposito` escludono `tipo_eccezione === ESCLUSIONE`
  - `useComponentiDialog.js`: auto-chiusura + scarto payload quando la dialog
    non è più pertinente (watch su `showComponentiDialog`).
- **Test**: suite servizi vendite verde (687) + build FE verde.

## 5. Test DB attesi (pgTAP)

A scelta del team DB, ma il caso da coprire è chiaro, per entrambe le fn:

- articolo **composito** + padre **ESCLUSIONE** → la fn ritorna 0, **nessuna**
  riga in `*_eccezioni_componenti` / `*_righe_componenti`, e la riga padre
  conserva `prezzo_unitario IS NULL` (nessuna violazione del CHECK);
- regressione: articolo composito + **OVERRIDE** → componenti inseriti e prezzo
  padre ricalcolato come prima (comportamento invariato).
