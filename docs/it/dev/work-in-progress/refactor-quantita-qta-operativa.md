# Refactor `quantita` / `qta_operativa` — simmetria conversione UoM su preventivi, offerte, contratti

> **Stato**: bozza analisi — 2026-05-31
> **Origine**: emerso durante l'analisi "regola del 2" sul FE vendite, indagando
> la differenza `form.quantita` (preventivi) vs `form.qta_operativa` (contratti).
> **Natura**: tocca DB (trigger), BE e FE. Le azioni DB sono passate come brief
> al team DB (non eseguite dall'agente backend).
> **Decisione di modello**: CONFERMATA 2026-05-31 — direzione canonica unica
> (`qta_operativa` = sorgente operatore, `quantita` = base derivata) su tutte e
> tre le entità, allineate ai contratti.

---

## 1. Problema

Le tre entità di vendita che hanno righe con quantità (`preventivi_righe`,
`offerte_commerciali_eccezioni`, `contratti_righe`) gestiscono la coppia
`quantita` / `qta_operativa` in **tre modi diversi e incoerenti**. La conseguenza:

1. **Incoerenza di convenzione** preventivi ↔ contratti: la conversione UoM
   viene fatta in **direzione opposta** (chi è la sorgente e chi il derivato).
2. **Lacuna sulle offerte**: l'offerta ha le colonne ma **non converte affatto**.
3. **Probabile bug al push** offerta→contratto (vedi §4).

La logica di conversione UoM **non è documentata** nella guida
`gestione-preventivi.md` (verificato: nessuna menzione di `qta_operativa` /
`factor_to_base`): la guida descrive solo "articolo + UoM operativa + quantità".
La derivazione vive solo nel codice.

---

## 2. Modello canonico (target)

Il trigger DB `script.trgfn_qta_from_operativa` definisce **un solo** modello,
esplicito nei suoi commenti:

> Sorgente unica: **quantità OPERATIVA**. Su INSERT calcola **sempre** `quantita`
> (base) da `qta_operativa` (operativa) + `uom_operativa_id` + `factor_to_base`.

Quindi la convenzione canonica — già usata da `contratti_righe`, `ddt_righe`,
`ordini_righe` — è:

```text
operatore → qta_operativa (nell'UoM operativa scelta)  [SORGENTE]
sistema   → quantita (UoM base)  = derivata dal trigger  [DERIVATO]
```

`factor_to_base` è lo snapshot del fattore di conversione (quanti pezzi base per
1 unità operativa). La nullabilità di `qta_operativa` è governata, dove esiste,
da `fonte_quantita_attesa` (FISSA ⇒ obbligatoria; altre fonti ⇒ ammessa NULL,
la quantità arriverà da fonte esterna).

**Obiettivo del refactor: portare tutte e tre le entità su questa convenzione.**

---

## 3. Stato attuale per dominio (verificato su codice + dbzero)

| | `preventivi_righe` | `offerte_..._eccezioni` | `contratti_righe` |
|---|---|---|---|
| `fonte_quantita_attesa` | ❌ assente (one-shot, corretto) | ✅ NOT NULL | ✅ NOT NULL |
| `quantita` | numeric NOT NULL | numeric nullable | numeric nullable |
| `qta_operativa` | numeric nullable | numeric nullable | numeric nullable |
| `factor_to_base` | NOT NULL default 1 | NOT NULL default 1 | presente |
| Trigger `trgfn_qta_from_operativa` | ✅ `('true','false')` (target `quantita`, no fonte) | ❌ **ASSENTE** | ✅ `('true','false','quantita','fonte_quantita_attesa')` |
| Derivazione BE | ✅ `_derive_qta_operativa`: **`qta_operativa = quantita × factor`** (direzione INVERSA) | ❌ nessuna (salva raw dal payload) | ❌ nessuna (delega al trigger) |
| Campo compilato dall'operatore (FE) | `form.quantita` | `form.quantita` | `form.qta_operativa` |

### Letture chiave
- **Contratti** = riferimento canonico: operatore inserisce `qta_operativa`, il
  trigger deriva `quantita`.
- **Preventivi** = stessa conversione ma **al contrario**: il FE manda
  `quantita`, il BE (`_derive_qta_operativa`, `preventivi_service.py:1077`)
  calcola `qta_operativa = quantita × factor`. In più sulla tabella c'è
  comunque il trigger che ricalcola `quantita` da `qta_operativa`. **Convivono
  due meccanismi con assunzioni opposte** (vedi §6 — da chiarire con smoke se il
  risultato numerico è corretto o doppiato).
- **Offerte** = ha le colonne ma **nessun meccanismo di derivazione** (né trigger
  né BE): salva `quantita` dal FE, `qta_operativa` resta NULL, `factor_to_base`
  resta al default 1.

---

## 4. Bug al push offerta → contratto

`fn_push_offerta_a_contratto` copia i campi **1:1** dall'eccezione offerta a
`contratti_righe` (incluso `quantita`, `qta_operativa`, `factor_to_base`), senza
rimappare. Ma `contratti_righe` ha il trigger `trgfn_qta_from_operativa` con
governo `fonte_quantita_attesa`.

Caso tipico: eccezione CANONE (default fonte = **FISSA**) → l'offerta ha
`quantita = X`, `qta_operativa = NULL`. Al push entra in `contratti_righe` con
`fonte = FISSA` + `qta_operativa NULL` → il trigger solleva **`E_QTA_MISSING`**.
Per fonti ≠ FISSA non rompe ma crea un contratto con `qta_operativa NULL` e un
valore operatore in `quantita` (colonna che sul contratto è *derivata*):
incoerenza semantica.

> Da confermare con lo smoke §8b: il push FISSA fallisce davvero con E_QTA_MISSING?

---

## 5. DB — logica e motivazione delle modifiche (brief per team DB, NON eseguito qui)

Si fissa la **logica** e il **perché**, non la sintassi DDL. Principio unico:
**la sorgente è sempre `qta_operativa` (UoM operativa scelta dall'operatore); la
colonna `quantita` è la base derivata, calcolata una sola volta dal trigger
`script.trgfn_qta_from_operativa`** (`quantita = qta_operativa × factor_to_base`).

### 5.1 `offerte_commerciali_eccezioni` — aggiungere il trigger di conversione
- **Logica**: installare `trgfn_qta_from_operativa` con la **stessa
  configurazione dei contratti** — sorgente `qta_operativa`, target `quantita`,
  nullabilità di `qta_operativa` governata da `fonte_quantita_attesa` (FISSA ⇒
  obbligatoria; altre fonti ⇒ NULL ammessa, la quantità arriva da fonte esterna).
- **Perché**: oggi l'offerta ha le colonne ma **non deriva nulla** (`qta_operativa`
  resta NULL, `factor_to_base` resta 1). L'offerta è però lo **specchio del
  contratto**: `fn_push_offerta_a_contratto` copia i campi **1:1** in
  `contratti_righe`, che invece **ha** il trigger. Lo smoke §8b dimostra che una
  copia con `fonte=FISSA` + `qta_operativa NULL` viene **rifiutata con
  `E_QTA_MISSING`**. Installando il trigger sull'offerta, `qta_operativa` viene
  valorizzata e `quantita` derivata già a monte: il push copia valori coerenti e
  non rompe. È anche l'unica entità della famiglia "fornitura ricorrente"
  (contratti/ddt/ordini ce l'hanno già) a esserne sprovvista.

### 5.2 `preventivi_righe` — eliminare la doppia derivazione
- **Logica**: il preventivo deve usare **solo** la direzione canonica del trigger
  (`qta_operativa` → `quantita`). Va rimossa la derivazione **inversa** che oggi
  vive nel BE (`quantita` → `qta_operativa`). Poiché il preventivo **non** ha
  `fonte_quantita_attesa`, `qta_operativa` è sempre fornita dall'operatore →
  diventa **NOT NULL**; `quantita` diventa la colonna **derivata**. Il CHECK di
  positività va spostato dalla colonna derivata (`quantita`, oggi
  `chk_prevrighe_quantita_pos`) alla **sorgente `qta_operativa`**. La config del
  trigger resta `('true','false')` (target di default `quantita`, nessuna fonte).
- **Perché**: oggi convivono **due** meccanismi con assunzioni opposte — il BE
  calcola `qta_operativa = quantita × factor`, poi il trigger ricalcola
  `quantita = qta_operativa × factor`. Lo smoke §8a dimostra che si
  **compongono** producendo `quantita = quantita_FE × factor²` (con `factor=6`:
  2 → 72, atteso 12). Lasciando **una sola** derivazione (il trigger) il calcolo
  torna corretto e identico a contratti/offerte. Latente oggi solo perché 0/45
  righe usano `factor ≠ 1`, ma è un bug logico del modello da chiudere prima che
  si venda un articolo in UoM operativa.

### 5.3 Coerenza dei vincoli fra le tre tabelle
- **Logica**: dopo il refactor il **contratto** resta lo schema di riferimento.
  In tutte e tre: sorgente = `qta_operativa`, derivata = `quantita`; il CHECK di
  positività sulla **sorgente**. Uniformare la nullabilità: `quantita` (derivata)
  può diventare nullable dove oggi è NOT NULL (preventivi), `qta_operativa`
  obbligatoria dove la fonte lo impone (preventivi sempre; contratti/offerte se
  fonte FISSA).
- **Perché**: evitare che la stessa colonna abbia semantica/vincoli diversi nelle
  tre tabelle (oggi `quantita` NOT NULL su preventivi, nullable altrove) —
  fonte di confusione e di bug come quelli sopra.

### 5.4 Push `fn_push_offerta_a_contratto`
- **Logica**: nessuna modifica necessaria alla funzione **se** l'offerta, dopo
  §5.1, valorizza già `qta_operativa`. La copia 1:1 diventa corretta e il trigger
  contratti ricalcola `quantita`.
- **Perché**: il problema non è il push in sé ma il dato a monte (offerta senza
  derivazione). Sistemata l'offerta, il push è già corretto.

> Le scelte puntuali su NOT NULL / CHECK / nomi vincoli sono da concordare col
> team DB su `dev/db-tid`: qui è fissata la logica (sorgente `qta_operativa`,
> derivato `quantita`, una sola direzione ovunque) e il perché di ciascuna.

---

## 6. BE — piano operativo aggiornato (DOPO i prerequisiti DB §5)

> **Gate**: nessuna riga di BE parte prima che §5 sia applicato dal team DB
> (trigger sull'offerta + vincoli preventivi). Contratto post-refactor: il FE/BE
> inviano `qta_operativa` + `uom_operativa_id`; `quantita` (base) la calcola
> **solo** il trigger.

1. **`preventivi_service` (`backend/apps/vendite/services/preventivi_service.py`)**
   - **Rimuovere `_derive_qta_operativa`** (la derivazione inversa
     `quantita → qta_operativa`, `:1077`): è la metà del doppio calcolo (smoke §8a).
   - `gestisci_riga` / `aggiorna_riga`: accettare dal payload `qta_operativa` +
     `uom_operativa_id` (+ `factor_to_base` opzionale; se assente, lookup su
     `catalogo.articoli_uom_operativa`). **Non** passare più `quantita` come
     input: è derivata dal trigger.
   - Spostare la guard "quantità > 0" sulla **sorgente `qta_operativa`** (errore
     parlante `E_QTA_MISSING` / `E_PREV_VALIDAZIONE` prima del DB).
   - **Test**: aggiornare i test service (oggi i payload mandano `quantita`);
     aggiungere un caso con `factor ≠ 1` che verifichi `quantita = qta_op × factor`
     (regressione diretta dello smoke §8a).

2. **`offerte_service` (`backend/apps/vendite/services/offerte_service.py`)**
   - Accettare `qta_operativa` + `uom_operativa_id` (+ `factor_to_base`); smettere
     di salvare `quantita` come sorgente raw (oggi whitelist `:243-251`).
   - Validazione simmetrica ai contratti: se `fonte = FISSA` e `qta_operativa`
     mancante ⇒ errore parlante **prima** del trigger.
   - **Test**: aggiornare i test (oggi mandano `quantita`); caso FISSA senza
     `qta_operativa` ⇒ errore; caso push end-to-end senza `E_QTA_MISSING`.

3. **Pricing / letture quantità** — verificare i punti che leggono `quantita`
   (resolver prezzo, riepiloghi IVA, preview componenti) perché usino la **base**
   corretta dopo il cambio di sorgente. In particolare la quantità passata al
   `ComponentiDialog` (oggi `form.quantita` lato preventivi / `form.qta_operativa`
   lato contratti — vedi FE §7).

4. **Push** — nessun cambio di codice atteso (vedi DB §5.4): verificare con
   test + smoke che `fn_push_offerta_a_contratto`, con l'offerta che ora valorizza
   `qta_operativa`, **non** sollevi più `E_QTA_MISSING` e produca `quantita`
   derivata coerente.

**Criteri di accettazione BE**: smoke §8a non riproducibile (preventivo
`factor≠1` salva la base corretta); smoke §8b non riproducibile (push offerta
FISSA va a buon fine); suite test vendite verde.

---

## 7. FE — piano operativo aggiornato (DOPO i prerequisiti DB §5 + BE §6)

> **Gate**: il FE si tocca solo dopo che DB e BE accettano la nuova convenzione.
> **Modello UX confermato**: la quantità si inserisce **nell'UoM operativa
> scelta** → il FE invia `qta_operativa` + `uom_operativa_id`; la base la calcola
> il DB.

1. **`PreventiviRigaForm.vue`** (l'unico con modifica sostanziale)
   - Il campo quantità deve bindare **`form.qta_operativa`** (oggi `form.quantita`,
     `:62/:580`), insieme a `uom_operativa_id` già presente.
   - Payload: inviare `qta_operativa` (+ `uom_operativa_id`), non più `quantita`.
   - `showComponentiDialog`, watch auto-open `[articolo_id, uom_operativa_id]` e
     `:quantita` passata al `ComponentiDialog`: leggere `form.qta_operativa`.
   - `canSave` / validazione riga: guardare `qta_operativa > 0`.

2. **`OffertaEccezioniDrawer.vue`**
   - Stesso allineamento: il campo quantità binda e invia **`qta_operativa`**
     (oggi `form.quantita`, `:278/:301`); populate da `row.qta_operativa`.
   - Coerenza con `fonte_quantita_attesa` già nel form (FISSA ⇒ campo
     obbligatorio, errore se vuoto).

3. **`ContrattoRigheDrawer.vue`** — già su `form.qta_operativa`: **nessuna
   modifica**. Resta il riferimento di simmetria.

4. **i18n** — allineare le etichette quantità nei tre drawer (es. "Quantità (UoM
   operativa)"), evitando label che lascino intendere la quantità base.

5. **Sblocco #3**: una volta che i tre drawer condividono la stessa semantica
   `qta_operativa`, ridiventa praticabile e pulita l'estrazione `useComponentiDialog`
   (#3 del report regola-del-2), oggi rinviata anche a causa di questa asimmetria
   (`form.quantita` vs `form.qta_operativa`).

**Criteri di accettazione FE**: i tre drawer inviano `qta_operativa`; build verde;
verifica manuale di una riga preventivo/offerta con UoM operativa ≠ base che mostri
e salvi i numeri corretti.

---

## 8. Smoke di verifica — ESEGUITI 2026-05-31 (transazioni con ROLLBACK)

### 8a. Preventivo — doppia derivazione → **BUG NUMERICO CONFERMATO**
Riprodotto l'INSERT del BE su articolo `…0101` + UoM operativa `uom_id=2`
(`factor_to_base = 6`), simulando `FE quantita=2` → BE `qta_operativa = 2×6 = 12`.

| campo | valore salvato | atteso corretto |
|---|---|---|
| `quantita` (base) | **72** | **12** |
| `qta_operativa` | 12 | 12 |
| `factor_to_base` | 6 | 6 |

La formula trigger (`script.trgfn_qta_from_operativa` riga 196:
`NEW.quantita := ROUND(NEW.qta_operativa * v_factor_used, 6)`) ricalcola
`quantita = qta_operativa × factor`. Composta con la derivazione BE
(`qta_operativa = quantita_FE × factor`) ⇒ **`quantita = quantita_FE × factor²`**.
Per `factor=6`: 2 → 72 (sbagliato ×6).

**Esposizione**: 0/45 righe preventivo reali hanno `factor_to_base ≠ 1` (esiste
una sola coppia articolo/UoM con factor≠1 a sistema). Il bug è **reale ma
latente**: si manifesta solo appena si vende un articolo in UoM operativa ≠ base.
→ Priorità **alta** (bug logico del modello), ma nessun dato storico da bonificare.

### 8b. Push offerta CANONE/FISSA → contratto — **BUG CONFERMATO**
Riprodotto l'INSERT che `fn_push_offerta_a_contratto` farebbe copiando 1:1 da
un'eccezione offerta CANONE/FISSA (`quantita` valorizzata, `qta_operativa=NULL`):

```text
INSERT contratti_righe (... fonte_quantita_attesa='FISSA', qta_operativa=NULL, quantita=5 ...)
→ ERRORE E_QTA_MISSING: "Quantità nulla o mancante" (column qta_operativa)
```

Il trigger contratti rifiuta `FISSA` + `qta_operativa NULL`. Poiché il FE offerta
valorizza solo `quantita` (lascia `qta_operativa` NULL), **il push di
un'eccezione FISSA fallisce**.

### Conclusione smoke
Entrambi i bug **confermati empiricamente**. Non sono ipotesi: il refactor §5–§7
è necessario, non solo cosmetico.

---

## 9. Punti aperti / decisioni

- [ ] Conferma di Tid sulla direzione canonica unica (`qta_operativa` sorgente
      ovunque) — §2/§7.
- [x] Esito smoke §8a → **bug numerico confermato** (preventivo: `quantita = Q×factor²`); latente (0/45 righe con factor≠1).
- [x] Esito smoke §8b → **bug confermato** (push FISSA → `E_QTA_MISSING`).
- [ ] Decisioni DB su NOT NULL / CHECK colonne (team DB) — §5.
- [ ] Collegamento con `brief-db-offerta-push-successione-contratto-overlap.md`
      (stesso flusso di push).

---

## Riferimenti codice/DB
- `script.trgfn_qta_from_operativa` — docs/it/dbzero/script/manual/trgfn_qta_from_operativa.md
- `preventivi_service._derive_qta_operativa` — backend/apps/vendite/services/preventivi_service.py:1077
- `fn_push_offerta_a_contratto` — docs/it/dbzero/vendite/funzioni/fn_push_offerta_a_contratto.md
- Tabelle: `preventivi_righe`, `offerte_commerciali_eccezioni`, `contratti_righe` (docs/it/dbzero/vendite/tabelle/)
- FE: `PreventiviRigaForm.vue`, `OffertaEccezioniDrawer.vue`, `ContrattoRigheDrawer.vue`
