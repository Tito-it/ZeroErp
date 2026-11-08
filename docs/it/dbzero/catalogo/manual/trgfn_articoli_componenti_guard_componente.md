## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_componenti_guard_componente`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo
> * [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/funzioni/trgfn_righe_guard_articolo_ammesso) — il guard gemello sulle righe dei documenti
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — il lato articolo del livello unico
> * [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_iva_bom_attiva) — il lato articolo dell'IVA

---

### 🎯 Scopo Principale

Il guard di tabella della distinta sul componente: rifiuta un componente che la distinta non ammette, sollevando
il primo motivo di `script.fn_check_articolo_riga` per il documento `ARTICOLO`, con il kit come padre.

Il predicato sta nella check, che vede anche il picker: qui si solleva soltanto.

---

### I motivi, nell'ordine

1. **Il componente è ritirato** (`E_ARTICOLO_OBSOLETO`). Il guard chiama la check sempre come scelta nuova: un legame
   che arriva qui è nuovo, cambiato o riattivato.
2. **Il componente è il kit stesso** (`E_BOM_COMPONENTE_PADRE`). Lo ferma anche il CHECK
   `chk_articoli_componenti_no_selfref`, ma senza codice: parla prima il guard, e il CHECK resta la rete.
3. **Il componente è a sua volta composito** (`E_BOM_COMPONENTE_COMPOSITO`): la distinta ha un livello solo.
4. **Il componente ha un'IVA diversa dal kit** (`E_BOM_IVA_DISCORDANTE`).

---

### Quando giudica

Scatta prima dell'INSERT e dell'UPDATE di `componente_id`, `prodotto_id` o `attivo`. Giudica un legame **attivo**:

* quando nasce;
* quando si riattiva;
* quando cambia il componente o il kit.

Un legame spento non si giudica. Un UPDATE di un legame già attivo che non cambia componente né kit non si
ri-giudica.

Fra i trigger della tabella parla dopo i guard sul padre (composito, solo componente): prima la testata, poi la
riga. Se il padre non è composito, il motivo è quello, anche se il componente ha un altro difetto.

---

### ⭐ Perché un guard suo

Il guard comune delle righe dei documenti legge `articolo_id` e un padre con chiave numerica. Nella distinta
l'articolo è `componente_id` e il padre è `prodotto_id`, con chiave uuid. La regola resta una sola, nella check: i
due guard la chiamano con il proprio documento.

---

### ⚠️ Che cosa oggi non copre

* **La riapertura di un legame chiuso.** Rimettere `valido_al` vuoto non fa scattare il guard. Se nel frattempo il
  componente è diventato composito, è stato ritirato o ha cambiato IVA, il legame torna in vigore senza errore.
* **I cambi dal lato articolo.** Un UPDATE di un legame attivo che non tocca componente né kit non si ri-giudica: se
  il componente cambia nel frattempo, il legame resta com'è. L'IVA la difende il guard sull'articolo; il passaggio
  a composito, il guard sull'articolo lo ferma solo per i legami in vigore o futuri. Un componente ritirato resta
  invece nei legami che già lo contengono, ed è voluto: il ritiro conta solo per le scelte nuove.

---

### Codici errore

* `E_ARTICOLO_OBSOLETO`, `E_BOM_COMPONENTE_PADRE`, `E_BOM_COMPONENTE_COMPOSITO`, `E_BOM_IVA_DISCORDANTE` — il primo
  motivo trovato, nell'ordine sopra. Il campo segnalato è `componente_id`.

---

### Test

* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — un componente composito in un legame attivo
  è rifiutato, anche alla riaccensione; in un legame spento passa; il padre non composito parla prima del
  componente, e il livello prima dell'IVA.
* `db/pgtap/catalogo/test-guard-iva-reactivation-v1.sql` — la riattivazione di un legame con IVA discordante è
  rifiutata.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il guard solleva il primo motivo attraverso il
  rubinetto comune.

Il motivo del componente ritirato e quello del componente uguale al kit, sulla distinta, non hanno un test.

---

### Note di migrazione

* 2026-10-13 — prende il posto di `catalogo.trgfn_articoli_componenti_guard_un_livello` e
  `catalogo.trgfn_articoli_componenti_guard_iva`: le regole sul componente passano alla check comune.

---

{% include-markdown "signature-core.md" %}
