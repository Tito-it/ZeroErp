## 📘 Documentazione Concettuale – Funzione `vendite.fn_cleanup_fatture_by_ids`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft)  
> • [vendite.fn_elimina_fattura_da_lotto](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto)  
> • [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft)  
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)  

---

### 🎯 Scopo Principale
(latest review 03-08-2026)  

La funzione **`vendite.fn_cleanup_fatture_by_ids()`** è il **proprietario unico**
del ripristino: cancella le fatture indicate e riporta indietro **tutto** ciò che
avevano consumato.

> **La regola che governa questa pagina.**
> **Cosa si ripulisce** sta qui e **solo** qui. **Come resta il documento** —
> annullato, riaperto, o intatto — appartiene all'operazione che chiama.
> I chiamanti non contengono nessuna riga di pulizia.

---

### I tre chiamanti, e perché la divisione conta

| chiamante | come lascia il lotto |
|---|---|
| [`fn_annulla_lotto_da_draft`](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) | → **ANNULLATA**: il lotto si chiude |
| [`fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) | → **DRAFT**: il lotto resta vivo e riparte |
| [`fn_elimina_fattura_da_lotto`](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto) | **non lo tocca**: agisce su una fattura sola |

Sono tre operazioni diverse che condividono **la stessa** pulizia. È il motivo per
cui la pulizia non può stare dentro nessuna delle tre: la correttezza di ognuna
dipende dal fatto che facciano esattamente la stessa cosa.

⚠️ **Lezione pagata il 03-08-2026.** Il ritorno a DRAFT era nato con un passo in
più scritto **dentro di sé** — il ripristino delle `commesse_attivita`. Risultato:
la stessa pulizia esisteva in due versioni, completa in una funzione e incompleta
nelle altre due. Le altre due cancellavano le fatture lasciando le attività
marcate come **emesse**, cioè righe di commessa **senza fattura e irrecuperabili**:
la selezione di ciò che è da emettere le scartava per sempre. Nessuna orfana si era
ancora formata — il difetto era **latente** e si sarebbe armato al primo
annullamento.

---

### Cosa ripristina

* **Elimina**: note (dal padre partizionato `vendite.note`), riepiloghi IVA,
  righe, log, collegamento lotto-fattura, testate.
* **Storna** dall'ambito di compensazione l'arrotondamento delle fatture
  cancellate, **prima** di toccarle — in testa alla funzione, così resta corretto
  qualunque passo venga aggiunto dopo.
* **Azzera i fondi** via [`fn_reset_fondi_fattura`](/dbzero/vendite/funzioni/fn_reset_fondi_fattura).
  ⚠️ Quella funzione **non cancella** `fatture_fondi_fattura_source`: ne azzera
  `fattura_figlia_id` e rimette il fondo `DISPONIBILE`. È il trattamento giusto —
  un credito deve **sopravvivere** alla fattura che lo consumava. In caso di
  movimenti già contabilizzati non elimina i dati e registra un warning in
  `fatture_log`.
* **Sblocca** le `attivita_fatturabili` (lock, flag `fatturato`, legame alla riga,
  `stato_esecuzione` a NULL).
* **Riporta le `commesse_attivita` a `NON_EMESSA`** (dal 03-08-2026). Senza questo
  passo il ripristino è **inutile**: `fn_emit_attivita_fatturabili_da_commessa`
  filtra su `stato_emissione = 'EMESSA'` e non le riprenderebbe mai più. Lo stesso
  campo decide come il cruscotto competenza classifica la riga.
  Le attività **ANNULLATE** non si toccano: sono state annullate di proposito.
* Usa la GUC `zeroerp.maintenance_reset_lotto_draft` per bypassare il guard
  «fatturato».

⚠️ **Le due popolazioni devono restare una sola.** Le `commesse_attivita` da
rimettere in coda si raccolgono con il **predicato identico** a quello della
`UPDATE` su `attivita_fatturabili`, e **subito prima** di essa: quella `UPDATE`
azzera `fattura_riga_id`, cioè distrugge il legame. Se i due filtri divergessero,
si sbloccherebbe un insieme di attività e se ne rimetterebbe in coda un altro —
in silenzio.

⚠️ **Il ramo su `p_lock_batch_id`** prende **tutte** le attività del batch: è
corretto nel reset globale (libera anche quelle agganciate al lotto che non sono
mai diventate riga) ed è il motivo per cui il reset **per-fattura** deve passare
`NULL`.

---

### 🔴 Se aggiungi una tabella figlia di `vendite.fatture`

**O la gestisci qui, o la motivi nel test.** Non c'è una terza strada, e non è una
raccomandazione: c'è un invariante che lo verifica —
`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql`.

Quel test legge da `pg_constraint` **ogni** figlia di `vendite.fatture` e pretende
che sia classificata in una di quattro categorie, con la motivazione scritta:
`GESTITA`, `CASCADE_DB`, `BLOCCO_VOLUTO`, `SCOPERTA_NOTA`. Una tabella nuova lo fa
diventare **rosso, col proprio nome dentro il messaggio**.

Il motivo per cui serve: senza, una figlia nuova fallisce in **due modi opposti** e
nessuno dei due è «continua a funzionare» —

| la figlia nasce con… | cosa succede |
|---|---|
| `ON DELETE CASCADE` | viene cancellata **in silenzio**, anche se doveva sopravvivere |
| `NO ACTION` | la `DELETE` **esplode** con una violazione di FK grezza, davanti all'operatore |

⚠️ **Un rosso non si spegne aggiungendo la voce all'inventario.** Si decide a quale
categoria appartiene la tabella. Il rosso non è il problema: è la domanda.

---

### Output

Ritorna una riga con **quattro** contatori, separati di proposito: un numero unico
direbbe «dieci cose fatte» senza distinguere attività **sbloccate** da attività
**rimesse in coda**, che sono fatti diversi e possono divergere.

* `deleted_fatture`
* `deleted_righe`
* `updated_attivita` — `attivita_fatturabili` sbloccate
* `riemesse_attivita` — `commesse_attivita` tornate emittibili

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_cleanup_fatture_by_ids(
  p_fatture_ids   => ARRAY[1001, 1002],
  p_lock_batch_id => NULL
);
```

Nota: il cleanup delle note avviene su `vendite.note` (partizione `note_fatture`).

---

{% include-markdown "signature-core.md" %}
