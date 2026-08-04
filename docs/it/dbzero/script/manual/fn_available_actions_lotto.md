## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_lotto`
### 🎯 Scopo Principale
(latest review 04-08-2026)
Espone le **capability del lotto di fatturazione** per il detail API: quali azioni di
governo sono disponibili sul lotto, quali sono **abilitate** e — quando non lo sono —
**perché**. Ottava della famiglia `fn_available_actions_*` (ordine, DDT, reso, offerta,
preventivo, contratto, commessa): stesso contratto, stessi consumatori frontend.

Nasce per chiudere un difetto concreto: fino al 2026-07-31 il pulsante «Annulla lotto»
era visibile anche da EMESSA in poi, dove la funzione di annullamento rifiuta — un vicolo
cieco trovato in-app. La correzione di allora fu ricopiare la precondizione nel frontend.
Da qui in avanti la precondizione è **una sola** e la UI la legge invece di riscriverla.

---

### Regole applicate

* `available_actions` — i verbi di **stato** sono letti in modo **data-driven** da
  `config.stati_doc_fiscale_transizioni`, dal `meta` (`action_key`, `label_key`,
  `severity`, `icon`, `requires_confirm`, `outlined`, `manuale`):

  | Transizione | `action_key` |
  | --- | --- |
  | `EMESSA → DEFINITIVA` | `numera` |
  | `EMESSA → DRAFT` | `riporta_a_draft` |
  | `DRAFT → ANNULLATA` | `annulla` |

* Il filtro sulla matrice è **lo stesso predicato del guard vivo**
  `vendite.trgfn_fatturazione_lotti_guard_stato`: `ammesso`, `solo_fattura = false`,
  `meta.tipo_lotto` compatibile col tipo del lotto. Se la matrice cambia, cambiano insieme
  il guard e i pulsanti — non ci sono due posti da tenere allineati.
* `ristampa` è **cablata** e non nasce dalla matrice: non è una transizione, perché
  stampare è leggere (I-4). Compare su lotto `DEFINITIVA`, cioè quando le fatture sono
  numerate.
* `enabled` + `reasons` di `annulla` e `riporta_a_draft` arrivano dalle funzioni **pure**
  `script.fn_check_lotto_annullabile` e `script.fn_check_lotto_riportabile_a_draft` — le
  **stesse** che `vendite.fn_annulla_lotto_da_draft` e `vendite.fn_riporta_lotto_a_draft`
  usano per sollevare. Sorgente unica: la UI non può divergere dal DB.
* `can_change_state` è calcolato sulle sole azioni **abilitate** e sulle sole
  **transizioni** (la ristampa non cambia stato). Con le azioni disabilitate presenti in
  lista, un semplice conteggio dell'array sarebbe sempre `true`.
* Fallback sicuro: ritorna `NULL` se il lotto non esiste.

---

### ⚠️ Contratto per i consumatori

> La presenza di un'azione in `available_actions` **non** significa che sia eseguibile.
> Chi consuma deve leggere `enabled` e mostrare `reasons` (tooltip sul pulsante
> disabilitato). È lo stesso contratto dichiarato da `fn_available_actions_commessa`.

---

### 🔴 Cosa NON espone, e perché

`avanza_step` e `rilancia_step` **non sono qui**. Il loro gate è fatto di tre pezzi —
criticità attive, esistenza dello step successivo, e la distinzione fra avanzamento e
rilancio dello stesso step (D-Q p.1) — che oggi vivono per intero in
`LottoPipelineRunner._resolve_steps_for_run` e in `lotto_segnalazioni_service`.
Ricostruirli qui creerebbe la **seconda copia** proprio della regola che questa funzione
serve a de-duplicare. Finché quel gate sta in Python, il DB non finge di possederlo: il
verdetto sull'avanzamento resta di chi lo applica davvero.

Far scendere quel gate nel DB è una decisione a sé, e va presa in un colpo solo — non a
metà. Vedi `risposta-db-azioni-lista-lotto.md` §5.

---

### Output (jsonb)

* `available_actions` — array di
  `{ key, target_state, label_key, severity, icon, requires_confirm, outlined, enabled, reasons }`
* `can_change_state` — bool (solo transizioni abilitate)
* `stato_codice` — `config.stati_doc_fiscale.codice_interno` del lotto
* `tipo_lotto` — `MASSIVO` | `GIORNALIERO`

---

{% include-markdown "signature-core.md" %}
