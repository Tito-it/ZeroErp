## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe_stati`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe che portano questi stati
> * [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) — come si passa da uno stato all'altro
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — il catalogo gemello della distinta
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — il movimento che nasce quando la riga è registrata
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) — legge `richiede_abbinamento`
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — legge `is_postabile` per la capienza
> * [script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile) — legge `lavorata` alla validazione
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — gli stati di riga nel modello degli incassi

---

### 🎯 Scopo Principale

La tabella **`pagamenti.vendite_contabili_righe_stati`** è il catalogo degli stati di
lavorazione di una **riga contabile**, con le bandiere che dicono che cosa ogni stato pretende e
permette.

Gli stati a catalogo sono `IMPORTATA`, `DA_ABBINARE`, `ABBINATA`, `SOSPESA`, `SCARTATA`,
`POSTATA` e il ritirato `STORNATA`; `ordine` dà la sequenza di avanzamento.

---

### Le quattro bandiere, e perché sono quattro

| Bandiera | Risponde a |
| --- | --- |
| `is_postabile` | «questa riga è **pronta** da registrare?» (vera solo su `ABBINATA`) |
| `is_final` | «da questo stato si va ancora da qualche parte?» (vera su `POSTATA` e sul ritirato `STORNATA`) |
| `richiede_abbinamento` | «questo stato pretende di sapere **a chi** appartiene la riga?» (vera su `ABBINATA` e `POSTATA`) |
| `lavorata` | «qualcuno ha **guardato** questa riga?» (falsa su `IMPORTATA` e `DA_ABBINARE`, vera sugli altri) |

⭐ Le regole stanno nel catalogo e non dentro i guard che le applicano per la stessa ragione per
cui le transizioni stanno in una tabella: una regola in una tabella si legge e si cambia senza
toccare il codice.

---

### ⚠️ `richiede_abbinamento` non si ricava dalle altre

`ABBINATA` pretende fattura e cliente e **non è finale**: una regola costruita su `is_final`
l'avrebbe mancata del tutto. È la ragione per cui la bandiera esiste.

⚠️ **La rata resta fuori di proposito.** Su `ABBINATA` è facoltativa, perché la riga del fondo
fattura ha fattura sì e rata no: è un saldo per **trasferimento**. La colonna della rata c'è, e
questa bandiera non la comprende.

---

### ⭐ `lavorata` è la bandiera della validazione

`VALIDATA` vuol dire «ho finito di inserire»: entrando in `VALIDATA` una distinta non può avere
righe attive in uno stato non lavorato, perché dopo la registrazione nessuno le guarderebbe più.
La legge [script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile),
chiamata dal guard di validazione ed esposta dal dettaglio.

La **sospesa è stata guardata** (ha un motivo) e con la registrazione tardiva
([fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva)) ha un futuro anche
sotto una distinta chiusa. Il default è `false`: uno stato nuovo non classificato è
fail-closed.

---

### `SCARTATA` non è finale, `STORNATA` è ritirata

* **`SCARTATA` non è finale**: da lì si torna a `SOSPESA` per riprendere in mano una riga
  scartata per errore. Un catalogo che la dichiarasse finale mentre la matrice ammette il
  ritorno insegnerebbe il falso.
* **`STORNATA` è ritirata** (`obsoleto_dal` valorizzata). Non esiste il gesto che ce la
  porterebbe: lo storno non è un tipo di documento, è una contabile a **importi negativi**.
  ⚠️ Ritirata, **non spenta**: `attivo` resta vero, perché spegnerla romperebbe le righe che la
  referenziassero. Chi costruisce una lista di stati filtra `obsoleto_dal`; chi legge uno stato
  già scritto **non** filtra.

---

### ⛔ Gli id di questo catalogo non sono un contratto

Il CSV di seed **non porta la colonna `id`**, e il suo loader usa il `codice` come chiave. Chi
scrive una funzione risolve questi stati **sempre per `codice_interno`**, mai incidendo un id; a
differenza del catalogo gemello della distinta, dove gli id sono nel CSV e sono un contratto.

---

### Test

* `db/pgtap/pagamenti/test-transizioni-stati-contabili.sql` — il grafo seminato, `STORNATA`
  fuori da ogni transizione, `POSTATA` terminale.
* `db/pgtap/pagamenti/test-righe-contabili-guard-dati.sql` — `richiede_abbinamento` su
  `ABBINATA`, e la rata che non serve.
* `db/pgtap/config/test-costanti-catalogo-citate-dal-codice-v1.sql` — i codici di stato citati
  dal codice esistono a catalogo.

---

### Note di migrazione

* 2026-08-21 — arriva `richiede_abbinamento`; `SCARTATA` smette di essere finale (il catalogo
  dichiarava il contrario della matrice); `STORNATA` viene ritirata con `obsoleto_dal`.
* 2026-09-18 — arriva `lavorata`, che il controllo di validazione legge.

---

{% include-markdown "signature-core.md" %}
