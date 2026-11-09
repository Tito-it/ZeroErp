## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti_gruppi`

> **Versione**: 2026-07-27 (brief-db-emissione-fattura-per-documento-sorgente
> PARTE A step A2, decisione D-3 · migration `20260727-11`)

> **Vedi anche**
>
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
> [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi)

---

### 🎯 Scopo Principale

Registra il **perimetro di un lotto mirato**: quali gruppi fatturabili quel
lotto ha il permesso di lavorare.

| Contenuto | Significato |
|---|---|
| **righe presenti** per un lotto | lotto **MIRATO**: pull e select lavorano **solo** quei gruppi |
| **nessuna riga** per un lotto | **nessuna restrizione** = esattamente il comportamento odierno |

---

### La convenzione portante: l'assenza di criterio *è* il criterio storico

Non esiste un flag «lotto mirato» da valorizzare. Un lotto senza righe qui si
comporta come si è sempre comportato il giro schedulato — ed è ciò che rende la
slice **retro-compatibile per costruzione**: nessun percorso esistente deve
essere adattato, perché nessun percorso esistente scrive in questa tabella.

---

### ⚠️ Perché una tabella e non un parametro di chiamata

È la ragione per cui questa tabella esiste, e non è ovvia.

Gli step della pipeline ricevono **solo `lotto_id`** e ricostruiscono tutto dal
`LottoContext`, cioè dalla riga del lotto:

- `_handle_pull_attivita_da_commessa_task` chiama `fn_list_commesse_emittibili`
  coi campi del contesto;
- `run_select_attivita_task` passa a `fn_select_attivita_fatturabili` solo
  valori del contesto più i params JSON della pipeline.

**I parametri dell'endpoint non arrivano agli step.** Senza persistenza, il
design non parte proprio.

**Corollario meno ovvio**: i verbi *Rerun step* e *Avanza step* del
`LottoDrawer` ri-eseguono uno step su un lotto **esistente**. Se il perimetro
fosse un parametro di chiamata, un rerun lo perderebbe e **allargherebbe in
silenzio** il lotto mirato a tutto il perimetro. Persistendolo, il rerun
riproduce lo stesso perimetro per costruzione.

---

### Perché non `fatturazione_lotti.meta`

Alternativa valutata e scartata:

- `meta` è già il canale di **configurazione** della pipeline (ci vive
  `fatturazione_immediata`): metterci dati di **perimetro** sovraccarica un
  campo che ha già un ruolo;
- il filtro serve dentro il **SQL dinamico** di
  `fn_select_attivita_fatturabili`, dove un `= ANY(...)` su tabella è naturale e
  indicizzabile mentre un `jsonb` andrebbe destrutturato;
- una tabella porta **audit e `tx_id` veri**: il perimetro di un lotto fiscale è
  un dato da poter ricostruire a distanza di tempo.

---

### Regole principali

- `UNIQUE (lotto_id, gruppo_key)` — idempotenza della selezione: chiedere due
  volte lo stesso gruppo per lo stesso lotto non è un errore da propagare;
- `ON DELETE CASCADE` — il perimetro non ha vita propria: senza il suo lotto non
  significa nulla;
- `CHECK` chiave non vuota — `''` vorrebbe dire «nessun gruppo» e sarebbe
  indistinguibile da «nessuna restrizione», cioè **il contrario** di quello che
  l'operatore ha chiesto;
- `gruppo_key` **non è una FK**: è una chiave di dominio calcolata da
  `fn_build_gruppo_fatturabile_key`, e un gruppo può legittimamente riferirsi a
  un documento che nel frattempo ha cambiato stato. **Non costruirla a mano**:
  usare sempre la funzione.

---

### ⚠️ Nessun indice FK dedicato, e non è una dimenticanza

La `UNIQUE (lotto_id, gruppo_key)` è un btree con `lotto_id` come **prefisso**:
copre già `WHERE lotto_id = ?`, che è l'unico accesso previsto (i filtri leggono
i gruppi di *un* lotto). Un secondo indice sul solo `lotto_id` sarebbe
ridondante e verrebbe segnalato da `dbops.vw_indici_ridondanti_prefisso` (`vw_duplicate_indexes` vede solo i duplicati esatti).

Stessa logica già applicata su `vendite.resi_righe_riconsegne`. La FK è coperta,
quindi la scoperta della politica degli indici (`dbops.fk_index_policy`) non la
registra: non c'è niente da decidere.

---

### Chi la popola

Il **backend**, alla creazione del lotto e **nella stessa transazione** — non
uno step della pipeline. È il punto del contratto BE che va rispettato: non
esiste un modo di passare i gruppi «allo step».

---

{% include-markdown "signature-core.md" %}
