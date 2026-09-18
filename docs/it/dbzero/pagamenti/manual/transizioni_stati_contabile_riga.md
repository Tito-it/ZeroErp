## 📘 Documentazione Concettuale – Tabella `pagamenti.transizioni_stati_contabile_riga`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)
> • [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile)

### 🎯 Scopo Principale

(rev 2026-08-21)

La **matrice delle transizioni ammesse** fra gli stati della **riga contabile** —
la singola somma di denaro dentro una distinta. È il grafo che
`pagamenti.trgfn_vendite_contabili_righe_guard_transizione` legge: nessuna regola
è scritta nel codice.

⚠️ **Due tabelle e non una**, perché testata e riga sono **due macchine diverse**,
con stati diversi e cataloghi diversi.

---

### Il percorso della riga

```text
DA_ABBINARE ──────► ABBINATA ──────► POSTATA   (terminale)
     │  ▲              │  ▲
     │  └ ─ ─ ─ ─ ─ ─ ─┘  │        (ABBINATA → DA_ABBINARE: SPENTA dal 18-09, D20-e)
     ▼                    │
  SOSPESA ────────────────┘
     │  ▲
     ▼  │
  SCARTATA
```

| Stato | Vuol dire | Si va a |
| --- | --- | --- |
| `IMPORTATA` | arrivata dal flusso, nessuno l'ha guardata | *(non ancora seminato)* |
| `DA_ABBINARE` | va attribuita, non so ancora a chi | `ABBINATA` · `SOSPESA` · `SCARTATA` |
| `ABBINATA` | so dove va, è pronta | `POSTATA` · `SOSPESA` — ~~`DA_ABBINARE`~~ *spenta* |
| `SOSPESA` | l'ho guardata e c'è un problema | `ABBINATA` · `DA_ABBINARE` · `SCARTATA` |
| `SCARTATA` | non è nostra | `SOSPESA` |
| `POSTATA` | registrata, il movimento esiste | **∅ (unico terminale)** |

⭐ **`SOSPESA → ABBINATA` è diretta**: risolto il problema non si ripassa da
`DA_ABBINARE`. E la differenza fra `DA_ABBINARE` e `SOSPESA` è **chi ha
guardato** — lavoro non ancora fatto contro lavoro fatto che ha trovato un
ostacolo: due code per due persone diverse.

⭐ **`ABBINATA → DA_ABBINARE` è spenta dal 18-09-2026** (D20-e, strada b —
decisione di Tid): su una riga abbinata si **ri-abbina** («Abbina» apre il
dialogo già sulla destinazione che ha), non si «sgancia». `ABBINATA → SOSPESA`
**resta**: una abbinata su cui viene un dubbio prima di registrare si parcheggia
con un motivo, e da lì torna `ABBINATA` (diretta) o va `SCARTATA`. ⚠️ La coppia
è **seminata con `attivo = false`, non tolta**: l'upsert del seed
(`20260821-31`) non cancella, e togliere la riga dal `VALUES` l'avrebbe lasciata
accesa sul database. Il guard la rifiuta (`E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA`)
e il backend non la propone fra i «Porta a».

⭐ **`SCARTATA` non è finale**, e da lì si torna a `SOSPESA` per riprendere in
mano una riga scartata per errore. Il catalogo la marcava finale fino al
2026-08-21, e **dichiarava il contrario di ciò che la matrice permette**.

---

### 🔴 `POSTATA` è terminale, e chiude un difetto

È l'unico stato dopo il quale **esiste un fatto**: il movimento contabile. Non se
ne esce, e questo chiude per costruzione un difetto misurato — il giro dei fondi
fattura riportava ad `ABBINATA` una riga il cui movimento esisteva già, facendo
**contare lo stesso denaro due volte** su una fattura che nessuno stava
guardando.

⚠️ Se una riga è stata registrata per errore, non si torna indietro cambiandole
lo stato: si registra una contabile nuova con **importi di segno opposto**.

---

### La metà «bagaglio» sta altrove

Questa tabella dice **quando** si può passare. **A quali condizioni sui dati** lo
dice `pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati`, leggendo la
bandiera `richiede_abbinamento` del catalogo: gli stati che la portano pretendono
che la riga dica a quale **fattura** e a quale **cliente** appartiene.

⚠️ La **rata** resta facoltativa anche su `ABBINATA`: la riga del fondo fattura ha
fattura sì e rata no, perché è un saldo per **trasferimento**, non denaro arrivato
su una scadenza.

---

### ⚠️ Che cosa non è seminato

Le uscite da `IMPORTATA` e ogni riferimento a `STORNATA` (ritirato). Vedi la
gemella della testata per la ragione.

{% include-markdown "signature-core.md" %}
