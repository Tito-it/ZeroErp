## 📘 Documentazione Concettuale – Funzione `vendite.fn_libera_attivita_fatturabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)  
> • [vendite.fn_riporta_attivita_da_emettere](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere)  
> • [vendite.trgfn_attivita_fatturabili_guard_fatturato](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_fatturato)  

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

Rimette in coda di fatturazione un insieme di attività: le **libera** e riporta a
`NON_EMESSA` le righe di commessa che erano passate a `EMESSA` per causa loro.
Restituisce **due contatori separati**.

> **La regola che governa questa pagina.**
> «Questo lavoro torna disponibile» è **un fatto solo**, scritto su **due
> livelli**. Sta qui perché i due non possano divergere.

---

### Perché è una primitiva, e non due `UPDATE` copiate

Se i due livelli divergono, uno torna in coda e l'altro no — **in silenzio**:
nessun errore, nessun contatore fuori posto, e il lavoro esce dal giro.

È la stessa ragione per cui RD-4 aveva messo il ritorno a `NON_EMESSA` **dentro**
la pulizia invece che nei suoi tre chiamanti. Qui il ragionamento sale di un
livello: i consumatori sono **due funzioni diverse**, e la coppia di scritture
diventa un oggetto suo.

| Chi la consuma | Quando |
| --- | --- |
| [`fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) | una fattura viene cancellata: il lavoro che conteneva torna in coda |
| [`fn_riporta_attivita_da_emettere`](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) | un'attività **residua** viene recuperata a mano |

⭐ È nata **insieme** al primo consumatore, non dopo il secondo: farla dopo
avrebbe significato scrivere due volte la stessa coppia e poi rifattorizzare una
funzione appena corretta.

---

### ⛔ Non imposta la GUC di manutenzione, ed è la parte portante

[`trgfn_attivita_fatturabili_guard_fatturato`](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_fatturato)
rifiuta l'`UPDATE` quando `OLD.fattura_riga_id` è valorizzato, salvo GUC
`zeroerp.maintenance_reset_lotto_draft`.

Se **questa** funzione impostasse quella GUC, diventerebbe **il modo di
scollegare una fattura viva**: chiunque la chiamasse su un'attività ancora
agganciata la staccherebbe dal suo documento senza che nulla protesti.

⭐ Impostarla resta quindi una decisione **del chiamante**, e ne ha diritto solo
chi la fattura la sta cancellando:

* `fn_cleanup_fatture_by_ids` la imposta due passi prima — sta cancellando;
* il verbo di recupero **non ce l'ha e non deve**: agisce su attività **orfane**,
  dove `fattura_riga_id` è già `NULL` e il guard lascia passare da sé.

---

### ⛔ L'insieme vuoto non è un errore, qui

Array `NULL` o vuoto: **nessuna scrittura, contatori a zero**. È una primitiva
interna, e la pulizia la chiama legittimamente così — una fattura senza righe non
ha attività da liberare.

⚠️ Il guard sull'array vuoto è un dovere del **verbo** che la consuma, dove un
array vuoto è un errore di chiamante e non deve poter uscire come un dato. Non
della primitiva.

---

### Cosa scrive, e in che ordine

1. **raccoglie** le `commesse_attivita` delle attività indicate — *prima*
   dell'`UPDATE`, che azzera il legame e il lucchetto: dopo, l'insieme non
   sarebbe più ricostruibile;
2. **libera** le attività: `lock_in_fatturazione`, `lock_batch_id`,
   `fattura_riga_id`, `stato_esecuzione`; l'attività che il segno del documento
   aveva fatto nota di credito (`natura_dal_segno`, rev 2026-10-31) riprende la
   natura `FATTURA` e perde la marca: la prossima composizione del lotto decide
   di nuovo ([vendite.fn_lotto_natura_dal_segno](/dbzero/vendite/manual/fn_lotto_natura_dal_segno));
3. **riporta a `NON_EMESSA`** le sole righe di commessa in `EMESSA`.

⚠️ **Solo le `EMESSA`**: le `ANNULLATA` sono state annullate di proposito e non
tornano in coda per una pulizia.

⚠️ **Due statement e due `GET DIAGNOSTICS` distinti**, non una CTE con
`RETURNING`: i due livelli restano **misurabili separatamente**, ed è ciò che
permette a chi chiama di accorgersi se uno dei due non ha fatto niente.

---

### ⛔ Il timbro non si scrive più

Fino al 2026-08-26 la funzione azzerava anche `fatturato`. Dal changeSet
`20260826-33` quella colonna è **generata** su `fattura_riga_id IS NOT NULL`:
nominarla in un `SET` è un errore, non un no-op.

⭐ E il ripristino non ci perde niente — azzerando il puntatore il timbro cade
**da solo**. È il punto della strada B: le due colonne non possono più dire cose
diverse, perché **una sola esiste davvero**, e lo stato «timbrata senza fattura»
smette di essere rappresentabile.

⚠️ **Il lucchetto invece resta scritto a mano, e deve.** Non è un doppione e non
si può generare: è vero legittimamente *durante* il giro, quando la riga di
fattura non esiste ancora. È il motivo per cui togliere il timbro **non basta**,
e per cui il riordino di `fn_cleanup_fatture_by_ids` resta necessario — senza,
cancellare una riga di fattura toglierebbe il timbro da solo e lascerebbe il
lavoro fuori dal giro **per un'altra colonna**.

---

### Esempio d'uso

```sql
-- Il ripristino di una fattura cancellata, dal di dentro della pulizia
SELECT l.updated_attivita, l.riemesse_attivita
  FROM vendite.fn_libera_attivita_fatturabili(v_af_ids) AS l;

-- Insieme vuoto: zero scritture, zero contatori, nessun errore
SELECT * FROM vendite.fn_libera_attivita_fatturabili(ARRAY[]::bigint[]);
-- → (0, 0)
```

---

### Note operative

* **`SECURITY INVOKER`**: `vendite.commesse_attivita` ha la RLS, e lo scope resta
  quello del chiamante. ⚠️ `vendite.attivita_fatturabili` **non** ce l'ha: chi
  compone l'elenco degli id deve aver già risolto il perimetro — è il motivo per
  cui il verbo di recupero risolve le attività **passando per** le righe di
  commessa.
* **Array esplicito** `bigint[]`: `colonna%TYPE[]` non esiste in PostgreSQL. I
  due risultati sono contatori da `ROW_COUNT` e restano `integer`.
* `data_update` / `user_update` / `tx_id` / storico: li mettono i trigger della
  tabella.
* Test: `db/pgtap/vendite/test-fatturazione-reset-lotto-draft.sql` (13..16),
  `test-elimina-fattura-da-lotto-effetti-v1.sql`,
  `test-riporta-attivita-da-emettere-v1.sql`.
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L1 / Q-6.

---

{% include-markdown "signature-core.md" %}
