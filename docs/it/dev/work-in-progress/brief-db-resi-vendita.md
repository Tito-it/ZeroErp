# Brief DB — Slice RESI vendita (motore resi su DDT)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-13 · **Owner**: Tid
> **Contesto**: unica slice di sviluppo DDT rimasta. Riprende la predisposizione
> fissata in `work-done/brief-db-ddt-vendita-evasione-e-stati.md` **§12**
> (invarianti: fulfillment append-only; `fn_ordine_ha_residuo_evasione` già
> reso-aware con addendo `qta_resa_per_riconsegna` oggi = 0; transizioni di
> rientro stato ordine già seedate). Decisione Tid 2026-07-09: il reso è un
> **ibrido** — a credito oppure per ri-consegna.
>
> **Decisioni di design (Tid, 2026-07-13):**
>
> 1. **Entità autonoma con sorgente data-driven** (`sorgente_tipo_id` +
>    `sorgente_uid`, pattern del DDT): in questa slice l'unica sorgente
>    abilitata è `DDT_VENDITA`; in futuro si aggiungerà `FATTURA` senza rework.
> 2. **Tipo reso PER RIGA** (un rientro fisico può mescolare righe a credito e
>    righe da ri-consegnare).
> 3. **Nota di credito: SOLO predisposizione** (coda "da accreditare"
>    interrogabile; il branch NC è slice successiva).
> 4. **Macchina a stati data-driven** mirror DDT: gli effetti valgono solo per
>    i resi CONFERMATI.
> 5. **DDT origine → stato RESO automatico solo se reso totale**; su parziale
>    resta CONSEGNATO (la verità fine sta nelle righe reso).

## 1. Vocabolario `config.tipi_reso`

Tabella codice/descrizione standard (id, codice, codice_interno lockato,
descrizione, `riapre_residuo boolean NOT NULL`, attivo, audit). Seed:

| codice_interno | descrizione | riapre_residuo |
| --- | --- | --- |
| `RESO_A_CREDITO` | Reso a credito (nota di credito) | `false` |
| `RESO_PER_RICONSEGNA` | Reso per ri-consegna | `true` |

Nessun `IF` hardcoded nel motore: si legge il flag (§12 del brief DDT).
Whitelist lookup generico (`core/lookup/codici`) da estendere.

## 2. Stati e transizioni

`config.stati_doc_reso` + `config.transizioni_stati_reso`, stesso impianto
data-driven di `stati_doc_ddt` (fase per le dashboard, `available_actions`
fn dedicata):

- Stati minimi: `DRAFT` (fase APERTO) → `CONFERMATO` (fase CHIUSO) +
  `ANNULLATO` (terminale). Lo stato "ACCREDITATO" arriverà con la slice NC
  (è un seed, non un rework).
- Transizioni: `DRAFT→CONFERMATO`, `DRAFT→ANNULLATO`, `CONFERMATO→ANNULLATO`
  (l'annullo post-conferma deve stornare gli effetti: essendo l'addendo del
  residuo calcolato sui soli resi CONFERMATI, l'esclusione è automatica —
  serve però il ricalcolo/proiezione stato ordine alla transizione, vedi §5).
- `numero` assegnato alla CONFERMA dal trigger (sequenza dedicata, mirror
  `trgfn_ddt_gen_numero_emesso`), NULL in DRAFT.

## 3. Testata `vendite.resi`

Mirror strutturale della testata DDT dove ha senso:

- id BIGINT, uid uuidv7, numero/anno (a conferma), data, meta, audit, tx_id.
- **`sorgente_tipo_id` + `sorgente_uid`** (FK `config.sorgenti`): guard
  data-driven che in questa slice ammette solo `DDT_VENDITA` e richiede il
  DDT in stato `CONSEGNATO` (non si rende ciò che non è stato consegnato).
  N.B. servirà la riga `DDT_VENDITA` in `config.sorgenti` se non già presente
  come sorgente "in ingresso".
- Denormalizzati ereditati dal DDT sorgente via trigger normalize (mirror
  `trgfn_ddt_normalize`): `billing_account_id`, `destinatario_soggetto_ruolo_id`,
  `utility_id`, `valuta_id`.
- **`emittente_fiscale_id` NOT NULL**: stesso modello deciso il 2026-07-13
  per il DDT (vedi `work-done/brief-db-ddt-emittente-user-e-etichetta-soggetto.md`, CHIUSO) —
  ereditato dal DDT sorgente; trigger `default_emittente` da GUC user come
  fallback + `guard_emittente_ba`; RLS `rls_resi_ef_whitelist` +
  `trgfn_guard_emittente_scope` in scrittura, mirror DDT.
- `stato_doc_reso_id` FK.

## 4. Righe `vendite.resi_righe`

- `reso_id` FK, `ddt_riga_id` FK `vendite.ddt_righe` **NOT NULL** (la riga
  sorgente; quando arriverà la sorgente FATTURA si aggiungerà la colonna
  gemella + CHECK XOR — concentrico, nessun rename).
- `ordine_riga_id` derivato dalla riga DDT/fulfillment (nullable: DDT
  standalone non ha ordine → nessun residuo da riaprire), snapshot per
  alimentare l'addendo del residuo senza JOIN a catena.
- Articolo/UoM: derivati dalla riga DDT (immutabili — il reso non inventa
  articoli), `qta_resa NUMERIC CHECK (> 0)`.
- **`tipo_reso_id` FK `config.tipi_reso` NOT NULL (per riga, decisione 2)**.
- `motivo` testo libero (+ eventuale vocabolario motivi in futuro).
- **Guard quantità**: Σ `qta_resa` dei resi non-ANNULLATI sulla stessa
  `ddt_riga_id` ≤ quantità consegnata di quella riga DDT (guard fail-fast,
  lock coerente su concorrenza).
- Righe modificabili solo con testata in DRAFT (mirror DDT).

## 5. Effetti alla CONFERMA (fn madre, una transazione)

1. **Riapertura residuo**: puntare l'addendo `qta_resa_per_riconsegna` di
   `fn_ordine_ha_residuo_evasione` (oggi 0) alla somma delle righe reso
   CONFERMATE con `tipi_reso.riapre_residuo = true` per `ordine_riga_id`.
   La formula e le transizioni di rientro sono già pronte (§12 invarianti
   1-3): NON toccare `qta_evasa` (append-only).
2. **Proiezione stato ordine**: ricalcolo alla conferma (e all'annullo
   post-conferma) → `EVASO→PARZIALMENTE_EVASO` ecc. via matrice esistente.
3. **Stato DDT origine (decisione 5)**: se le quantità rese cumulate
   (resi CONFERMATI, qualunque tipo) coprono TUTTE le quantità consegnate
   del DDT → transizione automatica `CONSEGNATO→RESO`; altrimenti nessun
   cambio. L'annullo di un reso che aveva causato il flip deve ri-valutare
   (RESO→CONSEGNATO se la matrice lo ammette — da seedare se manca).
4. **Coda "da accreditare" (decisione 3)**: nessuna generazione NC; le righe
   `RESO_A_CREDITO` confermate devono essere interrogabili come coda di
   lavoro (basta una vista `vw_resi_da_accreditare` — riga reso + riferimenti
   DDT/BA/importi; il consumo arriverà con la slice NC).

## 6. Read-side e contorno

- `vw_resi_lista` mirror `vw_ddt_lista` (decodifiche, stato, emittente con
  `emittente_fiscale_descrizione` dal soggetto — allineata al brief etichetta
  del 2026-07-13) + `security_invoker` + RLS su base.
- `script.fn_available_actions_reso` mirror DDT (matrice transizioni).
- Storicizzazione + pgTAP: guard quantità (parziale, cumulato, oltre-soglia),
  effetti conferma/annullo, flip DDT totale/parziale, RLS/scope.

## Fuori perimetro (esplicito)

- Generazione nota di credito (slice successiva; qui solo la vista-coda).
- Movimenti di magazzino (analisi-ddt §1.2: vivono su `magazzino`).
- Sorgente FATTURA (vocabolario predisposto, abilitazione futura).
- BE/FE: partono a DB pronto con brief dedicato (endpoint CRUD+conferma,
  drawer reso da DDT, colonna/lista resi).
