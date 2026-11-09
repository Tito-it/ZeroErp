## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_guard_componente`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta su cui opera
>
> Approfondimento funzioni:
>
> * [script.fn_check_articolo_riga](/dbzero/script/funzioni/fn_check_articolo_riga) — la check che chiama, col documento `ARTICOLO`
> * [script.fn_articolo_riga_contesto](/dbzero/script/funzioni/fn_articolo_riga_contesto) — il lato documento della check: rifiuta il padre non composito
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo
> * [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/funzioni/trgfn_righe_guard_articolo_ammesso) — il guard gemello sulle righe dei documenti
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — il lato articolo del livello unico
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — l'immutabilità del legame, che parla prima
> * [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_iva_bom_attiva) — il lato articolo dell'IVA

---

### 🎯 Scopo Principale

Il guard di tabella della distinta: rifiuta una composizione che la distinta non ammette, sollevando il primo
motivo di `script.fn_check_articolo_riga` per il documento `ARTICOLO`, con il kit come padre. Giudica il padre, che
deve essere composito, e il componente.

Il predicato sta nella check, che vede anche il picker: qui si solleva soltanto.

---

### I motivi, nell'ordine

Prima del componente parla il padre: il lato documento della check rifiuta un padre inesistente o non composito
(`E_ARTICOLO_NON_COMPOSITO`, campo `prodotto_id`), perché un articolo che non è un kit non ha una distinta. Un padre
«solo componente» non è un caso a parte: il CHECK di `catalogo.articoli` gli impedisce di essere composito. Poi i
motivi sul componente:

1. **Il componente è ritirato** (`E_ARTICOLO_OBSOLETO`). Il guard chiama la check sempre come scelta nuova: un legame
   che arriva qui è nuovo, cambiato o riattivato.
2. **Il componente è il kit stesso** (`E_BOM_COMPONENTE_PADRE`). Lo ferma anche il CHECK
   `chk_articoli_componenti_no_selfref`, ma senza codice: parla prima il guard, e il CHECK resta la rete.
3. **Il componente è a sua volta composito** (`E_BOM_COMPONENTE_COMPOSITO`): la distinta ha un livello solo.
4. **Il componente ha un'IVA diversa dal kit** (`E_BOM_IVA_DISCORDANTE`).

---

### Quando giudica

Scatta prima dell'INSERT e dell'UPDATE di `componente_id`, `prodotto_id`, `attivo` o `valido_al`. Giudica ogni
**composizione nuova**, cioè un legame attivo:

* quando nasce;
* quando si riattiva;
* quando la sua fine si allontana: `valido_al` tolto o spostato in avanti.

Un legame spento non si giudica. Non si giudica neppure la chiusura, o una fine anticipata: un legame si chiude
sempre, anche se nel frattempo il componente è stato ritirato. Un UPDATE di un legame già attivo che non cambia il
componente né allontana la fine non si ri-giudica. Il componente e il kit sono nell'elenco delle colonne per
prudenza: il loro cambio lo ferma prima l'immutabilità.

Il cambio del componente o del kit, e la riapertura di un legame già finito, non arrivano fin qui: li rifiuta prima il trigger
d'immutabilità (`catalogo.trgfn_articoli_componenti_block_modifica_struttura`), che parla per primo. Qui arriva
soltanto l'allungamento di una fine ancora futura.

---

### ⭐ Perché un guard suo

Il guard comune delle righe dei documenti legge `articolo_id` e un padre con chiave numerica. Nella distinta
l'articolo è `componente_id` e il padre è `prodotto_id`, con chiave uuid. La regola resta una sola, nella check: i
due guard la chiamano con il proprio documento.

---

### ⚠️ Che cosa oggi non copre

* **I cambi dal lato articolo.** Un UPDATE di un legame attivo che non tocca componente né kit non si ri-giudica: se
  il componente cambia nel frattempo, il legame resta com'è. L'IVA la difende il guard sull'articolo; il passaggio
  a composito, il guard sull'articolo lo ferma solo per i legami in vigore o futuri. Un componente ritirato resta
  invece nei legami che già lo contengono, ed è voluto: il ritiro conta solo per le scelte nuove.

---

### Codici errore

* `E_ARTICOLO_NON_COMPOSITO` — il padre non esiste o non è composito. Il campo segnalato è `prodotto_id`.
* `E_ARTICOLO_OBSOLETO`, `E_BOM_COMPONENTE_PADRE`, `E_BOM_COMPONENTE_COMPOSITO`, `E_BOM_IVA_DISCORDANTE` — il primo
  motivo trovato, nell'ordine sopra. Il campo segnalato è `componente_id`.

---

### Test

* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — un componente composito in un legame attivo
  è rifiutato, anche alla riaccensione; in un legame spento passa; il padre non composito parla prima del
  componente, e il livello prima dell'IVA.
* `db/pgtap/catalogo/test-guard-iva-reactivation-v1.sql` — la riattivazione di un legame con IVA discordante è
  rifiutata.
* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — l'allungamento di una fine futura con un componente
  ritirato è rifiutato, la sua chiusura passa; la riattivazione sotto un padre non più composito, e un legame nuovo
  su un padre non composito, sono rifiutati.
* `db/pgtap/catalogo/test-articoli-componenti-solo-componente.sql` — un solo componente come padre è rifiutato;
  come componente è ammesso.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il guard solleva il primo motivo attraverso il
  rubinetto comune.

Il motivo del componente uguale al kit, sulla distinta, non ha un test.

---

### Note di migrazione

* 2026-10-13 — prende il posto di `catalogo.trgfn_articoli_componenti_guard_un_livello` e
  `catalogo.trgfn_articoli_componenti_guard_iva`: le regole sul componente passano alla check comune.
* 2026-11-09 — giudica anche la fine che si allontana, e il padre attraverso la check: si ritirano
  `catalogo.trgfn_articoli_componenti_guard_is_composito` e `catalogo.trgfn_articoli_componenti_guard_solo_componente`,
  che scattavano solo all'inserimento e al cambio del padre (brief-db-revisione-catalogo, giro 1).

---

{% include-markdown "signature-core.md" %}
