## 🔍 Documentazione Concettuale – Vista `vendite.vw_fattura_righe_esposte`

> **Versione**: 2026-07-28 (brief-fix-importi-riga-fattura-zero §4.7-bis, D5 ·
> migration `20260728-16`)

> **Vedi anche**
>
[vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — il dettaglio da cui deriva
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — il livello sotto la riga
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — `esposto_in_fattura`, la regola
> [guida fatturazione](/guide/fatturazione) — §La riga di fattura: aggregazione, importo, esposizione

---

### 🎯 Scopo Principale

Produce **come il documento va rappresentato**, a partire dalle righe che lo
compongono.

⚠️ **Non è «la vista di stampa».** Deve essere letta da **ogni uscita verso
l'esterno**: PDF, XML SDI, portale. Se il PDF mostrasse il kit raggruppato e
l'XML trasmettesse i componenti, avremmo due uscite dello stesso documento che
raccontano dettagli diversi — totali uguali, quindi niente di irregolare, ma una
divergenza che nessuno ha deciso. Chiamarla «di stampa» significherebbe
costruirla già divergente.

Il principio che la governa: **`vendite.fatture_righe` resta il dettaglio** —
tutte le componenti, con articolo, quantità e prezzo propri — e questa vista
produce la **sintesi**. Non esiste un secondo dato da tenere allineato.

---

### Perché una vista e non una tabella

Una tabella materializzata porterebbe tre domande: quando la generi, cosa succede
se la stampa viene rilanciata, cosa se qualcuno tocca le righe dopo. Con la vista
spariscono tutte — fonte unica, nessun momento di generazione, nessuna
idempotenza da garantire. Se un domani il costo lo richiedesse, materializzarla è
banale: la definizione è già qui.

---

### Le tre regole

| Caso | Cosa produce |
|---|---|
| riga **non** di kit (`kit_key IS NULL`) | passa così com'è |
| riga di **kit** | **una riga padre** che porta il totale del kit |
| componenti con `kit_esposto_in_fattura = TRUE` | righe **descrittive** sotto il padre, **senza importo** |

I componenti con il flag a `false` **non compaiono**: il loro valore è già dentro
il totale del padre. Da cui la proprietà che conta: **il totale del documento non
cambia mai al variare dell'esposizione**.

---

### Convenzioni

* **Quantità della riga padre** = **media** delle quantità dei componenti. In un
  kit da 2 pezzi tutti i componenti portano 2 e il padre porta 2: la media dà 2.
  ⚠️ Regge finché `coeff_qta_snapshot` vale 1 — vero su tutte le righe di
  `ordini_righe_componenti` alla data. Con un coefficiente diverso la media
  diventerebbe un numero che non corrisponde a nulla (un kit da 2 con un
  componente a coefficiente 3 darebbe la media di `{2, 6, 6}`). Il rimedio, se
  servirà, è congelare la quantità del padre alla generazione.
* **`riga_nr` della riga padre** = quello del **primo** dei suoi componenti.
* **Importo della riga padre** = **somma** dei componenti.
* **Prezzo unitario del padre** = derivato, `importo / quantità`. È il prezzo
  *implicito* della riga mostrata, non una lettura dal catalogo: quella può
  essere cambiata dopo l'emissione.
* **Importo delle righe descrittive** = `NULL`, non zero. `NULL` dice «questa
  riga non porta importo», zero direbbe «vale zero». Chi somma ottiene comunque
  il totale corretto, perché `SUM` ignora i `NULL`.

---

### Colonne di servizio

| Colonna | A cosa serve |
|---|---|
| `tipo_riga` | `NORMALE` · `KIT_PADRE` · `KIT_COMPONENTE` |
| `ordinamento` | il `riga_nr` del capogruppo: tiene i componenti insieme al proprio padre |
| `livello` | `0` padre o riga normale, `1` componente descrittivo |
| `fatture_righe_id` | la riga sottostante; **`NULL`** sulla riga padre, che è sintetizzata e non esiste come record |

Ordinamento canonico: `ORDER BY ordinamento, livello, riga_nr`.

---

### ⚠️ Raggruppamento per IVA

La riga padre è costruita per **(fattura, kit, IVA, billing account
destinatario)** e non per solo (fattura, kit). Se un kit avesse componenti con
aliquote diverse, una riga padre sola non potrebbe rappresentarle e falserebbe il
riepilogo IVA: così se ne ottengono due, che è l'esito corretto. Alla data il
caso non si presenta.

Stessa logica per articolo e descrizione del padre: stanno nel `GROUP BY` e non
in un aggregato. Se per qualche ragione divergessero si otterrebbero due righe
padre invece di una fusione silenziosa — degradazione sicura.

---

### Ruolo nel sistema

È il **contratto verso l'esterno** del documento. Chi produce un'uscita — stampa,
tracciato fiscale, portale cliente — legge questa vista e non `fatture_righe`:
leggere le righe direttamente significa ignorare l'esposizione dei kit e
produrre un documento diverso da quello che gli altri canali mostrano.
