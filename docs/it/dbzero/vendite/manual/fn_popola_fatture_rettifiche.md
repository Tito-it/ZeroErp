## 📘 Documentazione Concettuale – Funzione `vendite.fn_popola_fatture_rettifiche(...)`

> 👀 **Vedi anche**
>
> [vendite.fatture_rettifiche](/dbzero/vendite/tabelle/fatture_rettifiche) ·
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) ·
> [fn_accredita_riga_reso](fn_accredita_riga_reso.md) ·
> [config.nature_doc_fiscale](/dbzero/config/tabelle/nature_doc_fiscale)
>
> Brief autorevole: `docs/it/dev/work-done/brief-design-note-credito-resi.md` (slice **N10**, §12.6-bis punto 4)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

Proietta sul legame **documento ↔ documento** (`vendite.fatture_rettifiche`)
ciò che le righe già dicono tramite `fatture_righe.riga_rettificata_id`.

**Rev 2026-10-31** (`20261031-48`, brief `brief-db-contratto-righe-periodiche-in-commessa`
§7.9, D-1-ter): sulla **nota di credito** anche le fatture dei pezzi di canone che storna. Il
cammino: la riga di commessa dello storno → `meta.storno_di_attivita_id` → il pezzo addebitato →
la sua attività fatturabile → la sua riga di fattura → la fattura. Le righe dello storno restano
`NORMALE`: non sono rettifiche di riga (quelle prendono prezzo e IVA dalla riga rettificata), e
la citazione è del documento. Un pezzo non ancora fatturato non dà niente da citare: lo storno
si è compensato nella stessa fattura. La nota di credito dal segno è in
[vendite.fn_lotto_natura_dal_segno](/dbzero/vendite/manual/fn_lotto_natura_dal_segno).

---

### La tabella che esisteva e non è mai stata usata

`vendite.fatture_rettifiche (fattura_id, rettificata_id)` esiste dal primo
giorno, aveva **zero righe** e nessuno la scriveva. Il brief la giudicava così:

> *«Non va buttata: serve come legame fra i due documenti, ma da sola non chiude
> nulla.»*

⭐ **Adesso non è più sola.** Con `fatture_righe.riga_rettificata_id` il legame
fra documenti è il `DISTINCT` di quello fra righe:

```text
le righe sono il FATTO   ·   la tabella-ponte è l'INDICE
```

Così non ci sono due verità: c'è una verità e una sua proiezione, che si può
**ricostruire in qualunque momento** senza chiedere niente a nessuno.

---

### ⚠️ Perché una funzione e non un trigger

Un trigger su `fatture_righe` girerebbe **dentro la transazione che genera le
righe**, che è il punto più caldo del giro di fatturazione: un
`INSERT … SELECT DISTINCT` per ogni riga scritta, su una tabella che ne scrive
migliaia per lotto.

La proiezione **non ha bisogno di essere immediata**: serve a chi *legge* il
documento, non a chi lo scrive. Quindi è un **task di pipeline**, invocato dopo
la generazione delle righe.

---

### A cosa serve davvero

Al blocco `DatiFattureCollegate` di una **TD04**, che vuole **numero e data del
documento rettificato**. Senza questo legame il builder XML dovrebbe risalire
riga per riga e poi de-duplicare da solo — cioè rifare qui il lavoro, in un posto
dove un errore diventa **un file trasmesso**.

---

### Garanzie

* **Idempotente**: `ON CONFLICT ON CONSTRAINT uq_fatture_rettifiche_pair DO
  NOTHING`. Si può rieseguire quante volte si vuole, anche su un documento già
  proiettato;
* **una fattura non rettifica se stessa**: la coppia degenere è esclusa dalla
  query, non lasciata alla FK (che l'ammetterebbe);
* ⚠️ **non cancella mai**. Se una riga di nota di credito venisse tolta — cosa
  che l'immutabilità delle righe di fattura già vieta oltre la soglia
  `DRAFT`/`EMESSA` — la coppia resterebbe. È voluto: **una proiezione che
  cancella diventa un secondo scrittore**, ed è quello il momento in cui nascono
  le due verità.

---

### Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `p_fattura_id` | `vendite.fatture.id%TYPE` | la fattura **rettificante** (tipicamente una nota di credito). Obbligatoria (>0) |

### 📦 Output

| Tipo | Descrizione |
|---|---|
| `integer` | numero di coppie effettivamente **aggiunte**. Zero su un documento già proiettato, ed è un successo, non un errore |

---

### Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `fattura_id` `NULL` o `<= 0` |

---

### Esempio d'uso

```sql
-- Dopo la generazione delle righe di una nota di credito
SELECT vendite.fn_popola_fatture_rettifiche(:fattura_id);

-- Quali documenti rettifica una nota di credito, con numero e data
SELECT orig.numero, orig.anno, orig.data
  FROM vendite.fatture_rettifiche fr
  JOIN vendite.fatture orig ON orig.id = fr.rettificata_id
 WHERE fr.fattura_id = :nota_credito_id;
```

---

{% include-markdown "signature-core.md" %}
