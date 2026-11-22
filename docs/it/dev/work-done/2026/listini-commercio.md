# WIP — Listini per dominio commercio: invariante univocità e roadmap evoluzione

> **ARCHIVIATO il 2026-04-22.**
>
> Fase 1 + Fase 2 DB chiuse il 2026-04-09 (EXCLUDE no-overlap + drop `priorita`).
> Tutto il contenuto che era rimasto aperto (backlog v2 — pricing_mode, scaglioni,
> valuta multipla, promotion engine, bundle, fasce orarie utility) è stato
> **assorbito e superato** dal modello v5, dove:
> - `listini_associazioni` è stata **droppata** (F1-DB-26) — sostituita da categoria cliente + contratto
> - `priorita` non esiste più
> - la scontistica commerciale vive in `categorie_clienti_listini` + `contratti` modalità A/B/C
> - le promo sono dominio dedicato (`promo_articoli`, STADIO 0 resolver)
> - scaglioni/formula e valuta multipla restano backlog v6+ (vedi `sviluppo-listini-v6.md`)
>
> **Nuovi sviluppi listini vanno tracciati in** [sviluppo-listini-v5.md](sviluppo-listini-v5) — vedi §14 "Sprint 22-04-2026 — Completamento v5".
>
> Questo documento resta come storico della decisione architetturale "invariante B"
> (univocità per scope con autoclose) che ha preceduto e ispirato v5.
>
> ---
>
> Documento di pianificazione e razionalizzazione del modello listini con focus
> sul dominio commercio.
>
> Data creazione: 2026-04-09
> Stato: **FASE 1 + FASE 2 DB COMPLETATE il 2026-04-09** — backend cleanup richiesto
> (vedi sezione 5.2), fase 3 (estensioni commercio v2) rimandata al backlog
> Branch DB target: `dev/db-tid`
> Branch backend target: `dev/backend-tid`

---

## 1. Contesto e motivazione

### 1.1 Stato del modello listini al 2026-04-09

Il modello `vendite.listini` di ZeroErp è oggi una v1 esplicitamente "minimal":

- **Entità**: `listini` (testata) → `listini_versioni` (finestra temporale) → `listini_righe` (prezzo per articolo+UoM con dimensioni di scope opzionali BA/utility/emittente)
- **Selezione**: `listini_associazioni` decide quali listini sono candidati per un dato contesto operativo
- **Resolver**: [`vendite.fn_resolve_prezzo_listino`](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino) applica un `match_rank` a 7 livelli + tie-break su priorità

Il `pricing_mode` è **dichiaratamente FIXED v1**, con predisposizione mentale (non ancora schema) per `SCAGLIONI` e `FORMULA` in v2 — vedi [gestione-listini.md §282](/guide/gestione-listini).

### 1.2 Il modello attuale è adatto a... cosa?

Domanda affrontata onestamente con Tid il 2026-04-09:

| Dominio | Adeguatezza v1 attuale | Note |
| --- | --- | --- |
| **Utility commodity** (gas, ee, idrico) | ❌ **Non adatto** | Mancano scaglioni di consumo, componenti additive (materia prima + trasporto + distribuzione + oneri sistema + accise), fasce orarie energia (F1/F2/F3), indicizzazione (PUN/TTF), bonus sociali, mercato tutelato vs libero. **Tutto previsto in v2** ma niente nello schema attuale. |
| **Commercio servizi/B2B semplice** (consulenza, manutenzione standard, fee fisse, abbonamenti software, contratti d'opera) | ✅ **Adatto** | Prezzo unitario per articolo+UoM, sconti riga gestiti a livello documento (preventivi/ordini/fatture), nessuna logica avanzata necessaria. |
| **Commercio retail / e-commerce** | ⚠️ **Parzialmente adatto** | Mancano sconti per volume/quantità, bundle/kit, BOGO, scontistica gerarchica, valuta multipla. Alcuni di questi sono **dominii separati** (catalogo, motore promo), altri richiedono v2. |

**Conclusione architetturale**: il listino v1 è la **base solida** per il commercio servizi/B2B semplice, **non è la soluzione finale** né per utility né per commercio retail. Dovrà essere esteso. Ogni decisione strutturale presa ora deve facilitare l'estensione futura, non bloccarla.

### 1.3 Perché questo WIP

Lavorando sui pricing test smoke (fix `20260409-01-fix-listini-versioni-overlap-stato` su `listini_versioni`) è emerso un secondo problema più subdolo sulle `listini_associazioni`: il vincolo `uq_listini_associazioni_key_attiva` ha due falle che permettono configurazioni contraddittorie con il modello dichiarato in [gestione-listini.md](/guide/gestione-listini).

Il fix richiede di **scegliere un'invariante chiara** — A (multi-listino concorrenti con tie-break) o B (univocità per scope con sostituzione esplicita) — e di documentarla. Questo WIP traccia la decisione e i suoi corollari.

---

## 2. Le due falle del vincolo `uq_listini_associazioni_key_attiva`

Vincolo attuale (definito in [`20260224-01-create-listini-core-mctit.yaml`](https://github.com/Tito-it/ZeroErp/blob/main/db/changelog/migrations_v2/00_schema/vendite/20260224-01-create-listini-core-mctit.yaml)):

```sql
CREATE UNIQUE INDEX uq_listini_associazioni_key_attiva
ON vendite.listini_associazioni (
    listino_id,
    COALESCE(billing_account_id, -1::bigint),
    COALESCE(utility_id, -1),
    COALESCE(emittente_soggetto_ruolo_id, -1::bigint),
    valido_dal
)
WHERE (attivo IS TRUE);
```

### 2.1 Falla 1 — `listino_id` nella key

L'unicità è "**per listino**". Due listini diversi possono avere associazioni attive con lo stesso identico scope dimensionale (BA, utility, emittente) e nello stesso periodo.

Questo è esattamente lo scenario che ha rotto lo step 17 del smoke test pricing: 4 listini SMK-LST-* con scope `(BA=NULL, utility=NULL, emittente=NULL)` tutti attivi → 4 candidati uguali al resolver → tie totale e errore `E_PREZZO_LISTINO_AMBIGUO`.

### 2.2 Falla 2 — `valido_dal` come scalare anziché range

L'unicità usa `valido_dal` come scalare, non come intervallo. Quindi anche togliendo `listino_id` dalla key, queste due righe coesisterebbero comunque:

```text
Associazione A: scope=(NULL,NULL,NULL), valido_dal=2026-01-01, valido_al=NULL
Associazione B: scope=(NULL,NULL,NULL), valido_dal=2026-06-01, valido_al=NULL
```

Il 2026-09-01 entrambe sono attive, l'invariante "una sola attiva per scope sull'intervallo" è violata, l'unique passa perché `valido_dal` differisce.

---

## 3. Decisione architetturale: invariante B (univocità per scope)

### 3.1 Le due opzioni in conflitto

| | **A) Multi-listino concorrenti** (modello attualmente dichiarato in guida) | **B) Univocità stretta per scope** (decisione adottata) |
| --- | --- | --- |
| Più listini con stesso scope contemporaneamente | ✅ ammessi, `priorita` decide il vincitore | ❌ vietati a livello DB |
| Significato di `priorita` su `listini_associazioni`/`listini_versioni` | tie-break reale | codice morto, da rimuovere |
| Cambio promo/listino senza ricreare nulla | semplice (overlay listini concorrenti) | autoclose vecchia + insert nuova in transazione atomica |
| Errore SMK-LST step 17 | è un *misuso operativo*: 4 listini con stessa priorità → tie | è un *bug strutturale*: il DB non doveva consentirlo |
| Resolver `match_rank` | il tie-break ha un ruolo reale | `tie_count > 1` non può mai scattare → guard inutile |
| Coerenza con altri sotto-domini ZeroErp | bassa (asimmetria con `listini_versioni`, `emittenti_fiscali_billing_account`) | alta (allineamento totale) |

### 3.2 Ragionamento della decisione

Analisi completata insieme a Tid in 4 passi (vedi cronologia conversazione 2026-04-09):

1. **6 casi d'uso reali esaminati** (promo temporanea, sostituzione annuale, multi-brand, fasce VIP, override fornitore, A/B test): **solo il caso "promo temporanea" gioca davvero a favore di A**, e il vantaggio è "1 INSERT vs 3 in atomica" — facilmente colmabile da un endpoint backend dedicato. Tutti gli altri 5 casi o funzionano uguale in A e B, o B è migliore, o sono modellazioni sbagliate in entrambi.

2. **Esperienza personale di Tid**: B è il pattern che ha sempre funzionato sui domini critici (gas, ee, idrico) e che vuole portare anche qui.

3. **Coerenza interna ZeroErp**: tutto il resto del modello listini (versioni post-fix `20260409-01`, mapping emittenti-BA post-refactor 2026-04-08, ecc.) usa "univocità per scope con autoclose". Avere `listini_associazioni` come unica eccezione è un'asimmetria strutturale.

4. **Reversibilità asimmetrica**: tornare da B ad A è banale (drop di constraint EXCLUDE). Tornare da A a B richiederebbe sanatoria dati. **B è la scelta minimum-regret.** Senza produzione attuale, il costo del cambio è zero.

5. **Modello mentale unico**: una sola invariante (*"per ogni scope dimensionale, una sola associazione attiva sull'intervallo"*) si spiega in una frase. Il modello A richiede due paragrafi e un esempio per essere capito.

### 3.3 La nuova invariante in formato unico

> **Per ogni triple `(billing_account_id, utility_id, emittente_soggetto_ruolo_id)`** — con `NULL` trattato come valore wildcard discreto — **non possono esistere due righe `attivo IS TRUE` con intervalli temporali sovrapposti su `listini_associazioni`**, indipendentemente dal `listino_id`.
>
> Le sostituzioni avvengono via **autoclose**: si imposta `valido_al = nuova.valido_dal - 1` sulla riga vecchia e si inserisce la nuova nella stessa transazione atomica.

### 3.4 Il caso "promo temporanea" come pattern operativo (non schema)

Per quando in futuro servirà sovrascrivere il listino base di un BA per un periodo limitato (es. promo di marzo), il pattern operativo è:

```text
Per applicare promo temporanea su BA in periodo [Pmin, Pmax]:
1. UPDATE listini_associazioni base: valido_al = Pmin - 1
2. INSERT listini_associazioni promo: scope=(BA), valido_dal=Pmin, valido_al=Pmax
3. INSERT listini_associazioni base ripristino: scope=(BA), valido_dal=Pmax+1, valido_al=NULL
Tutto in transazione atomica.
```

Implementazione: endpoint backend dedicato `apply_temporary_pricing(BA, da, a, listino_id)` (~30 righe Python) che fa le 3 operazioni in `with transaction.atomic()`. Non implementato adesso, va aperto come issue separata se/quando emerge il caso d'uso reale.

---

## 4. Piano operativo Fase 1 (questo commit)

### 4.1 Migration DB

**File**: `db/changelog/migrations_v2/00_schema/vendite/20260409-02-fix-listini-associazioni-no-overlap-mctit.yaml`

Operazioni:

1. DROP `uq_listini_associazioni_key_attiva` (vecchio unique buggato)
2. ADD `ex_listini_associazioni_no_overlap` come `EXCLUDE USING gist` con:
   - `COALESCE(billing_account_id, -1::bigint) WITH =`
   - `COALESCE(utility_id, -1) WITH =`
   - `COALESCE(emittente_soggetto_ruolo_id, -1::bigint) WITH =`
   - `daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]') WITH &&`
   - `WHERE (attivo IS TRUE)`
3. **Pre-condition `sqlCheck`**: 0 righe già in violazione del nuovo constraint (verifica preventiva con self-join). Sul DB di sviluppo dovrebbe essere già 0.
4. **Rollback**: drop nuovo, recreate vecchio unique.

**Dipendenza**: `btree_gist` — già installata, usata da `ex_listini_versioni_no_overlap`.

### 4.2 Aggiornamento documentazione concettuale

| File | Modifica |
| --- | --- |
| [`docs/it/guide/gestione-listini.md`](/guide/gestione-listini) | Riscrittura sezione "Regole multi-listino" → diventa "Una sola associazione attiva per scope". Esempio "Listino A vs Listino B" rimosso. Sezione "Tie-break" semplificata: resta il `match_rank` per specificità BA/utility/emittente, le priorità diventano "campi rimossi/deprecati post 2026-04-09". Aggiunto pattern operativo "promo temporanea" come 3-step in transazione. |
| [`docs/it/dbzero/vendite/manual/listini_associazioni.md`](/dbzero/vendite/tabelle/listini_associazioni) | Nuova invariante 1-per-scope esplicita. Pattern autoclose+insert per sostituzioni. Nota su `priorita` deprecata con riferimento a questo WIP. |
| [`docs/it/dbzero/vendite/manual/listini_versioni.md`](/dbzero/vendite/tabelle/listini_versioni) | Nota analoga sulla deprecazione di `priorita` (era già parzialmente neutralizzata dal fix `20260409-01`). |

### 4.3 Deprecazione `priorita` (passo intermedio safe)

In questo commit: solo `COMMENT ON COLUMN`. Non drop fisico (fase 2).

```sql
COMMENT ON COLUMN vendite.listini_associazioni.priorita IS
  'DEPRECATED 2026-04-09: con l''invariante univocita stretta per scope (ex_listini_associazioni_no_overlap)
   non discrimina piu nulla. Default 100. Sara rimossa in fase 2 (vedi WIP listini-commercio) dopo cleanup
   resolver e backend.';

COMMENT ON COLUMN vendite.listini_versioni.priorita IS
  'DEPRECATED 2026-04-09: con l''invariante univocita stretta per versioni ATTIVA
   (ex_listini_versioni_no_overlap, fix 20260409-01) non discrimina piu nulla. Sara rimossa in fase 2
   (vedi WIP listini-commercio).';
```

### 4.4 Cosa NON facciamo in questa fase

- **Nessuna modifica al resolver `fn_resolve_prezzo_listino`**: l'`ORDER BY associazione_priorita, versione_priorita` resta come no-op safe (codice morto ma non rotto), il guard `tie_count > 1` resta come paranoid check. Cleanup nella fase 2.
- **Nessun drop fisico delle colonne `priorita`**: rotturebbe i consumer Python (vedi fase 2).
- **Nessuna modifica al backend translator** (`listini_service.py`): è compito del backend, fuori scope DB. Loro aggiungeranno l'entry per `ex_listini_associazioni_no_overlap` quando ci passeranno.
- **Nessuna estensione commercio** (sconti volume, bundle, BOGO, valuta multipla, ecc.) — vedi sezione 6 per il backlog v2.

---

## 5. Piano operativo Fase 2 (commit successivo, da coordinare con backend)

> **Attenzione**: la fase 2 è bloccante sul backend. Va aperta solo dopo che il team backend ha confermato di aver:
> 1. Rimosso ogni `INSERT INTO listini_associazioni (..., priorita)` dai service Python
> 2. Rimosso ogni `INSERT INTO listini_versioni (..., priorita)` dai service Python
> 3. Pulito il translator listini in `listini_service.py` (sostituire l'entry vecchia `uq_listini_associazioni_key_attiva` con la nuova `ex_listini_associazioni_no_overlap`)
> 4. Aggiornato eventuali test backend che leggono `priorita`
>
> **Issue/PR backend tracker**: da aprire.

### 5.1 DB

**File**: `00_schema/vendite/AAAAMMGG-NN-drop-listini-priorita-mctit.yaml`

Operazioni:

1. ALTER TABLE `vendite.listini_associazioni` DROP CONSTRAINT `chk_listini_associazioni_priorita`
2. ALTER TABLE `vendite.listini_associazioni` DROP COLUMN `priorita`
3. ALTER TABLE `vendite.listini_versioni` DROP CONSTRAINT `chk_listini_versioni_priorita`
4. ALTER TABLE `vendite.listini_versioni` DROP COLUMN `priorita`
5. **Pre-condition**: nessuna view, materialized view, function, trigger, default che referenzia ancora la colonna (verifica con `pg_depend`).
6. **Rollback**: re-add columns con default 100 + check constraint.

**File**: `20_code/vendite/AAAAMMGG-NN-update-fn-resolve-prezzo-listino-no-priorita-mctit.yaml`

Operazioni:

1. CREATE OR REPLACE FUNCTION `fn_resolve_prezzo_listino` con `runOnChange: true`:
   - Rimuovere `a.priorita`, `v.priorita` dalla CTE `candidati`
   - Rimuovere `c.associazione_priorita`, `c.versione_priorita` dall'`ORDER BY` e dalla `PARTITION BY`
   - Rimuovere/semplificare il guard `tie_count > 1` in `E_PREZZO_LISTINO_AMBIGUO`: se l'invariante DB è rispettata, il tie può scattare solo per duplicati su `valido_dal/valido_al` esatti, scenario che il `match_rank` rende già univoco. Resta come paranoid check con commento esplicito.
2. Test pgTAP da aggiornare (rimuovere riferimenti a priorità nei fixture).

### 5.2 Backend (compito loro)

- Translator: rimuovere entry `uq_listini_associazioni_key_attiva`, lasciare solo `ex_listini_associazioni_no_overlap`
- Repository: rimuovere `priorita` dalle INSERT/UPDATE
- Service: rimuovere setter di `priorita`
- Test: rimuovere fixture su `priorita`
- Eventuale endpoint `apply_temporary_pricing` se la promo temporanea diventa caso d'uso reale

### 5.3 Frontend (compito loro)

- Form di creazione/modifica listino: rimuovere campo `priorita` dall'editor
- Tabelle di visualizzazione: rimuovere colonna `priorita`

---

## 6. Backlog evoluzioni commercio (v2 e oltre)

Le seguenti feature sono state discusse insieme a Tid nel 2026-04-09 ma **NON integrate in fase 1** per evitare di anticipare prematuramente v2 e bloccare il modello attuale. Vanno valutate come progetti separati quando emerge il caso d'uso reale.

### 6.1 Sconti per volume / quantità

> *"Compri 10 = 8% di sconto, compri 50 = 12% di sconto"*

**Modellazione**: scaglioni di prezzo per quantità. È **esattamente** uno dei `pricing_mode` previsti per v2 (`SCAGLIONI`).

**Cosa serve**:
- Aggiungere `quantita_min`, `quantita_max numeric` su `listini_righe` (entrambe nullable, NULL = nessun limite)
- Estendere il vincolo unicità righe per includere `(quantita_min, quantita_max)` o usare un `EXCLUDE` con `numrange`
- Estendere `fn_resolve_prezzo_listino` per accettare `p_quantita` e fare match su scaglioni
- Propagare `quantita` nei consumer (commesse, preventivi, ordini, fatture)

**Costo realistico**: ~2-3 giorni DB pulito, **più** lavoro grosso lato backend (propagazione quantità in tutta la pipeline) e frontend (esporre la cosa).

**Mitigazione v1** (cosa fare nel frattempo): gestire lo sconto volume **a livello documento**. I campi sono già presenti:
- [`vendite.preventivi_righe.sconto_percentuale`](/dbzero/vendite/tabelle/preventivi_righe)
- [`vendite.ordini_righe.sconto_perc`](/dbzero/vendite/tabelle/ordini_righe)
- [`vendite.fatture_righe.sconto_perc`](/dbzero/vendite/tabelle/fatture_righe)

L'operatore (o un service backend di "applica regole sconto") calcola lo sconto in funzione della quantità a livello documento. Il listino contiene il prezzo unitario lordo.

**Decisione per v1**: **mitigare con sconti riga lato documento**. Non anticipare v2.

> ⚠️ **Asimmetria di naming da pulire**: `preventivi_righe.sconto_percentuale` vs `ordini_righe.sconto_perc` vs `fatture_righe.sconto_perc`. Inconsistente. Da uniformare in un futuro cleanup separato (non parte di questo WIP).

### 6.2 Bundle / kit

> *"Compri il kit X (composto da articolo A + B + C) a 50€ invece di 60€"*

**Domain ownership**: il kit è un'**entità di catalogo** (articolo composito), non una regola di prezzo. Il listino assegna un prezzo al kit come fa con qualunque altro articolo. La composizione (`X = 2× A + 1× B + 3× C`) sta nel **catalogo**, non nei listini.

**Cosa serve**: meccanismo di "articolo composito" o "distinta base di vendita" su `catalogo.articoli` o tabella correlata. Probabilmente verrà aperto come progetto separato di catalogo.

**Decisione per v1**: **non riguarda i listini**. Non integrare ora, non bloccare. Va affrontato come feature catalogo se serve.

### 6.3 Promo BOGO (buy one get one)

> *"Acquisti 2 pezzi, il secondo è gratis"*

**Cosa significa**: regola di vendita condizionale che opera al momento del documento (preventivo/ordine), guarda il carrello e applica un'azione (sconto, riga gratis, prezzo modificato). Non è il listino che decide, è un motore separato che decide "quanto costa l'intero carrello".

**Cosa serve**: nuovo dominio "promotion engine" — schema separato (es. `vendite.promozioni`) con regole, condizioni, azioni, applicabilità (cliente/categoria/canale).

**Decisione per v1**: **fuori scope listini**. Da progettare come dominio separato. Bassa priorità per il commercio servizi/B2B; alta priorità solo se ZeroErp dovesse coprire commercio retail/e-commerce.

### 6.4 Valuta multipla

> *"Listini in EUR per clienti italiani, in USD per clienti esteri"*

**Stato attuale**: il modello listini è **monovaluta implicita**. Nessuna colonna `valuta_id` su `listini`, `listini_versioni`, `listini_righe`. Gli altri schemi correlati (`billing_account`, `emittenti_fiscali`, `commesse_attivita`, `fatture`, ecc.) hanno tutti `valuta_id`. Il listino non lo ha.

**Cosa serve**:
- Aggiungere `valuta_id` su `listini_versioni` (non sulle righe, che ereditano dalla versione)
- Validare al momento della creazione che la valuta sia coerente con dominio/emittente
- Decidere comportamento quando un BA in valuta X chiede prezzo da listino in valuta Y (errore? conversione automatica? prompt operatore?)

**Costo realistico**: 1 giornata DB + lavoro backend per gestire conversione/validazione.

**Decisione per v1**: **non integrare**. Utile solo per clienti esteri con prezzi non-EUR. Per il commercio italiano standard è cruft inutile. La modifica futura è additiva (colonna nullable), nessuna penalità nell'attendere.

### 6.5 Scontistica gerarchica

> *"Sconto cliente 5% + sconto promo 10% + sconto pagamento 2% = 17% applicato al netto?"*

**Cosa significa**: sistema di regole di sconto a cascata con priorità, applicabilità per cliente/categoria/canale/condizioni di pagamento, calcolo composito (additivo o moltiplicativo).

**Cosa serve**: stesso del punto 6.3 — è di fatto un'estensione del "promotion engine".

**Decisione per v1**: **fuori scope**. v2/v3, dominio separato.

### 6.6 Pricing mode esplicito (gancio dichiarativo per v2)

**Idea**: aggiungere a `listini_righe` una colonna `pricing_mode varchar NOT NULL DEFAULT 'FIXED' CHECK (pricing_mode IN ('FIXED'))`. Solo `FIXED` ammesso oggi. Quando arriverà v2 il CHECK verrà esteso a `('FIXED', 'SCAGLIONI', 'FORMULA')`.

**Pro**: prepara la strada dichiarativamente, rende esplicito nel modello quello che oggi è solo "predisposto mentalmente" in [gestione-listini.md §282](/guide/gestione-listini).

**Contro**: aggiunge complessità ora per un beneficio futuro non garantito. Se v2 si rivela diversa da come immaginiamo (es. introduce un'altra dimensione invece di pricing_mode), avremo aggiunto una colonna inutile.

**Decisione per v1**: **NON integrare ora**. Lasciare dichiarato solo a livello concettuale in guida. Aggiungere la colonna sarà un mini-task di 1 ora quando si avvierà il progetto v2 effettivo. Aggiungerla adesso senza una v2 in cantiere è ottimizzazione prematura.

### 6.7 Fasce orarie energia, scaglioni utility, formule indicizzate

Tutto il dominio utility commodity (gas, ee, idrico) richiede modellazione **molto** più ricca:

- Scaglioni di consumo (kWh, mc, m³) con prezzi diversi
- Fasce orarie (F1/F2/F3 per energia)
- Componenti additive (materia prima, trasporto, distribuzione, oneri sistema, accise, IVA con aliquote diverse)
- Indicizzazione su indici esterni (PUN, TTF, prezzi medi mese)
- Bonus sociali, agevolazioni regolamentate
- Mercato libero vs tutelato
- Formule parametriche con coefficienti tempo-varianti

**Decisione per v1**: **completamente fuori scope**. Dovrà essere progettato come "modello listini v2 utility" — schema esteso, possibilmente con tabelle dedicate `listini_componenti`, `listini_scaglioni`, `listini_indici`, ecc., e un nuovo resolver `fn_resolve_prezzo_utility` separato dal `fn_resolve_prezzo_listino` di v1.

**Riferimento**: vedere il WIP esistente [Fatturazione modello utilities](/dev/work-in-progress/fatturazione-modello-utilities-gas-ee-idrico) che traccia i requisiti del dominio utility commodity.

---

## 7. Decisioni operative chiuse

### D1 — Invariante = B (univocità per scope)

> Decisione presa il 2026-04-09 dopo analisi approfondita di 6 casi d'uso reali, valutazione dei pro/contro, esperienza personale di Tid sul dominio utility critico, coerenza interna ZeroErp e reversibilità asimmetrica.

### D2 — `priorita` viene rimossa (non solo deprecata)

> Decisione: drop fisico in fase 2 dopo coordinamento con backend. Fase 1 si limita a `COMMENT ON COLUMN ... DEPRECATED` per evitare rotture immediate.

### D3 — Nessuna estensione commercio in questa fase

> Tutte le feature commercio (sconti volume, bundle, BOGO, valuta, gerarchici, pricing_mode esplicito) sono state valutate e rimandate. Lo scope di questa fase è **solo l'invariante univocità**, niente altro. Le estensioni vivranno nei rispettivi capitoli del backlog v2 (sezione 6).

### D4 — Nessuna modifica al resolver in fase 1

> Il resolver `fn_resolve_prezzo_listino` resta invariato in fase 1. L'`ORDER BY associazione_priorita, versione_priorita` diventa codice morto safe. Pulizia in fase 2.

### D5 — Pattern "promo temporanea" documentato ma non implementato

> Il pattern 3-step (autoclose + insert + ripristino in atomica) viene scritto nella guida come riferimento operativo. L'eventuale endpoint backend dedicato verrà aperto come issue separata se/quando emerge il caso d'uso reale. Non parte di questa fase.

---

## 8. Check-list operativa

### Fase 1 — Univocità + deprecazione (`dev/db-tid`)

- [ ] **DB-1.1** Migration `00_schema/vendite/20260409-02-fix-listini-associazioni-no-overlap-mctit.yaml`: drop `uq_listini_associazioni_key_attiva`, add `ex_listini_associazioni_no_overlap` con EXCLUDE GIST + precondition `sqlCheck`
- [ ] **DB-1.2** `COMMENT ON COLUMN` deprecated su `listini_associazioni.priorita` e `listini_versioni.priorita` (changeset nello stesso file o file separato)
- [ ] **DOC-1.3** Aggiornare [`docs/it/guide/gestione-listini.md`](/guide/gestione-listini): riscrittura sezione "Regole multi-listino", semplificazione "Tie-break", aggiunta pattern "promo temporanea"
- [ ] **DOC-1.4** Aggiornare [`docs/it/dbzero/vendite/manual/listini_associazioni.md`](/dbzero/vendite/tabelle/listini_associazioni): nuova invariante 1-per-scope, autoclose pattern, nota deprecation
- [ ] **DOC-1.5** Aggiornare [`docs/it/dbzero/vendite/manual/listini_versioni.md`](/dbzero/vendite/tabelle/listini_versioni): nota deprecation `priorita`
- [ ] **PGTAP-1.6** Eventuale test pgTAP nuovo `test-listini-associazioni-no-overlap.sql` (opzionale: il vincolo EXCLUDE è dichiarativo nativo Postgres, lo testa il motore stesso, ma un test funzionale che verifica i casi vietati può aiutare la regression)

### Fase 2 — Drop fisico colonne (`dev/db-tid` 2026-04-09)

> **Decisione 2026-04-09**: invece di aspettare il prerequisito backend
> (BE-PREREQ originale), si procede al drop DB **immediatamente** sfruttando
> l'assenza di produzione. La rottura dei test backend in CI funge da segnale
> deterministico al team backend per pulire i propri file (`listini_service.py`,
> `listini_repository.py`, `views_listini.py`, `test_listini_service.py`,
> `test_listini_api.py`). Pattern "fail-fast" coerente con la filosofia
> minimum-regret della scelta architetturale B.

- [x] **DB-2.1** Migration `00_schema/vendite/20260409-04-drop-priorita-listini-associazioni-mctit.yaml`: drop check constraint + drop colonna in 2 changeset separati per chiarezza, con rollback completo (recreate column + check)
- [x] **DB-2.2** Migration `00_schema/vendite/20260409-05-drop-priorita-listini-versioni-mctit.yaml`: gemello del precedente per `listini_versioni`
- [x] **DB-2.3** Migration `20_code/vendite/20260409-04-update-fn-resolve-prezzo-listino-no-priorita-mctit.yaml`: nuovo `fn_resolve_prezzo_listino` con `ORDER BY` semplificato (rimossi `associazione_priorita` e `versione_priorita`), guard `tie_count > 1` mantenuto come paranoid check, precondition Liquibase `not columnExists` per garantire ordering corretto rispetto ai drop -04/-05. Pattern `runOnChange: true` come tutte le funzioni `20_code`.
- [x] **PGTAP-2.4** Adattamento `db/pgtap/vendite/test-listini-resolve-prezzo-v1.sql`: rimossi i 3 test originali 11/12/13 (tie-break priorita associazione, tie-break priorita versione, pareggio totale ambiguous) ora strutturalmente impossibili dopo le invarianti univocita. Rimossi tutti gli `INSERT INTO ... priorita` e i listini A25/B25/A24/B24/A23/B23 che creavano overlap vietato. Plan ridotto da 14 a 11 test, indice aggiornato.
- [x] **DOC-2.5** Aggiornati [`gestione-listini.md`](/guide/gestione-listini), [`listini_associazioni.md` manual](/dbzero/vendite/tabelle/listini_associazioni), [`listini_versioni.md` manual](/dbzero/vendite/tabelle/listini_versioni): le note "DEPRECATED" sono diventate "RIMOSSO il 2026-04-09 (Fase 2)" con riferimento esplicito alle migration `20260409-04` e `20260409-05`. La sezione "Storia" del tie-break nella guida e stata aggiornata con la storia completa Fase 1 → Fase 2.
- [ ] **BE-FOLLOW-UP** (compito backend, non bloccante per il merge DB) — da aprire come issue separata sul team backend:
  - Rimuovere `priorita` da `apps/vendite/api/views_listini.py` (serializer DRF)
  - Rimuovere `priorita` da `apps/vendite/db/listini_repository.py` (typing dict, SELECT, ORDER BY)
  - Rimuovere validazione `priorita` da `apps/vendite/services/listini_service.py` (`_extract_nullable_int`, `_validate_payload_create_versione`, `_validate_payload_create_associazione`, whitelist payload `ATTIVA`, translator entries `chk_listini_*_priorita`)
  - Aggiornare `apps/vendite/tests/services/test_listini_service.py` e `apps/vendite/tests/api/test_listini_api.py`
  - **Atteso**: i test backend in CI **falliranno immediatamente** dopo l'applicazione di questo commit DB. E' il segnale per aprire la PR backend.

### Fase 3 — Backlog evoluzioni v2 (futuro lontano, da progettare a sé)

- [ ] **EVO-3.1** Decisione architetturale: pricing_mode esplicito su `listini_righe` come gancio dichiarativo
- [ ] **EVO-3.2** Estensione listini per scaglioni/quantità (commercio retail)
- [ ] **EVO-3.3** Valuta multipla (clienti esteri)
- [ ] **EVO-3.4** Modello listini v2 utility commodity (vedi WIP fatturazione utilities) — schema completamente esteso
- [ ] **EVO-3.5** Promotion engine come dominio separato (BOGO, scontistica gerarchica)
- [ ] **EVO-3.6** Bundle/kit come feature catalogo (non listino)
- [ ] **EVO-3.7** Cleanup naming `sconto_perc` vs `sconto_percentuale` su righe documento

---

## 9. Note di chiusura

- **Branch e PR**: fase 1 = una sola PR atomica su `dev/db-tid` con migration + doc updates. Fase 2 = PR separata in coordinamento col backend. Backlog v2 = progetti dedicati separati.
- **Test pgTAP obbligatori**: solo per DB-2.3 (resolver in fase 2). Fase 1 si appoggia al motore Postgres per il vincolo EXCLUDE.
- **Compatibilità modello v1 ↔ v2**: tutte le decisioni di fase 1 sono **additive** o **subtractive sicure**. Non bloccano nessuna possibile evoluzione futura. Quando arriverà v2 (utility o commercio retail), partirà da una base più pulita.
