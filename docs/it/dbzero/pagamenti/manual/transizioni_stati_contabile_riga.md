## 📘 Documentazione Concettuale – Tabella `pagamenti.transizioni_stati_contabile_riga`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe che percorrono questo grafo
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — gli stati, e le bandiere che dicono che cosa pretendono
> * [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile) — la matrice gemella della distinta
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione) — il guard che legge questa matrice
> * [pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) — le condizioni sui dati di ogni stato
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — le due matrici nel modello degli incassi

---

### 🎯 Scopo Principale

La tabella **`pagamenti.transizioni_stati_contabile_riga`** è la matrice dei passaggi di stato
ammessi per una **riga contabile**, la singola somma di denaro dentro una distinta. La legge
[trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione):
nessuna regola di percorso è scritta nel codice.

⚠️ **Due tabelle e non una**, perché distinta e riga sono **due macchine diverse**, con stati
diversi e cataloghi diversi.

---

### Il percorso della riga

```text
DA_ABBINARE ──────► ABBINATA ──────► POSTATA   (terminale)
     │  ▲              │  ▲
     │  └ ─ ─ ─ ─ ─ ─ ─┘  │        (ABBINATA → DA_ABBINARE: seminata spenta)
     ▼                    │
  SOSPESA ────────────────┘
     │  ▲
     ▼  │
  SCARTATA
```

| Stato | Vuol dire | Si va a |
| --- | --- | --- |
| `IMPORTATA` | arrivata dal flusso, nessuno l'ha guardata | *(nessuna uscita seminata)* |
| `DA_ABBINARE` | va attribuita, non so ancora a chi | `ABBINATA` · `SOSPESA` · `SCARTATA` |
| `ABBINATA` | so dove va, è pronta | `POSTATA` · `SOSPESA` (verso `DA_ABBINARE` spenta) |
| `SOSPESA` | l'ho guardata e c'è un problema | `ABBINATA` · `DA_ABBINARE` · `SCARTATA` |
| `SCARTATA` | non è nostra | `SOSPESA` |
| `POSTATA` | registrata, il movimento esiste | **nessuna: unico terminale** |

⭐ **`SOSPESA → ABBINATA` è diretta**: risolto il problema non si ripassa da `DA_ABBINARE`. La
differenza fra `DA_ABBINARE` e `SOSPESA` è **chi ha guardato**: lavoro non ancora fatto contro
lavoro fatto che ha trovato un ostacolo, due code per due persone diverse.

⭐ **`SCARTATA` non è finale**: da lì si torna a `SOSPESA` per riprendere in mano una riga
scartata per errore.

---

### ⭐ Su una riga abbinata si ri-abbina, non si sgancia

`ABBINATA → DA_ABBINARE` è spenta: su una riga abbinata si **ri-abbina** («Abbina» apre il
dialogo già sulla destinazione che ha). `ABBINATA → SOSPESA` resta: un'abbinata su cui viene un
dubbio prima di registrare si parcheggia con un motivo, e da lì torna `ABBINATA` (diretta) o va
`SCARTATA`.

⚠️ La coppia è **seminata con `attivo = false`, non tolta**: l'upsert del seed non cancella, e
togliere la riga dal seed l'avrebbe lasciata accesa sul database. Il guard la rifiuta e il
backend non la propone fra i «Porta a».

---

### 🔴 `POSTATA` è terminale, e chiude un difetto

È l'unico stato dopo il quale **esiste un fatto**: il movimento contabile. Non se ne esce, e
questo chiude per costruzione un difetto: il giro dei fondi fattura riportava ad `ABBINATA` una
riga il cui movimento esisteva già, facendo **contare lo stesso denaro due volte** su una
fattura che nessuno stava guardando.

⚠️ Se una riga è stata registrata per errore, non si torna indietro cambiandole lo stato: si
registra una contabile nuova con **importi di segno opposto**.

---

### La metà «bagaglio» sta altrove

Questa tabella dice **quando** si può passare. **A quali condizioni sui dati** lo dice
[trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati),
leggendo la bandiera `richiede_abbinamento` del catalogo: gli stati che la portano pretendono
che la riga dica a quale **fattura** e a quale **cliente** appartiene.

⚠️ La **rata** resta facoltativa anche su `ABBINATA`: la riga del fondo fattura ha fattura sì e
rata no, perché è un saldo per **trasferimento**, non denaro arrivato su una scadenza.

---

### ⚠️ Che cosa non è seminato

* Le uscite da `IMPORTATA`: non si seminano finché l'import da flusso non esiste, perché un
  catalogo pieno di righe irraggiungibili insegna cose false (la lezione pagata con
  `STORNATA`).
* Ogni riferimento a `STORNATA`, che è ritirata.

La matrice vale solo sui cambi di stato: l'`INSERT` non è vincolato, e il giro dei fondi crea le
sue righe direttamente in `ABBINATA`.

---

### Test

`db/pgtap/pagamenti/test-transizioni-stati-contabili.sql` — il grafo seminato della riga, le
uscite da `IMPORTATA` assenti, `STORNATA` fuori da ogni transizione, `POSTATA` terminale,
l'`INSERT` non vincolato, `ABBINATA → DA_ABBINARE` seminata ma spenta.

---

### Note di migrazione

* 2026-08-21 — nasce la matrice, gemella di quella della distinta; `SCARTATA` smette di essere
  finale nel catalogo, che dichiarava il contrario di ciò che la matrice permette.
* 2026-09-18 — `ABBINATA → DA_ABBINARE` viene spenta.

---

{% include-markdown "signature-core.md" %}
