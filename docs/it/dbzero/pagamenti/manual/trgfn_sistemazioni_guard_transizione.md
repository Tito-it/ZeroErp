## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_sistemazioni_guard_transizione`

### 🎯 Scopo Principale

(rev 2026-08-22)

Il percorso dell'atto, che è cortissimo:

```text
BOZZA ──► CONFERMATA    (l'atto diventa un fatto: genera contabile o fondo)
  └────► ANNULLATA      (la decisione si scarta)
```

Entrambi gli esiti sono **terminali**. Non c'è ritorno da `CONFERMATA` perché a
quel punto **il denaro si è già mosso**: la correzione è una sistemazione
**nuova** — la stessa regola della distinta contabile chiusa.

---

### ⛔ Niente tabella-matrice, e non è una dimenticanza

`vendite_contabili` e le sue righe hanno una matrice di transizioni seminata a
dato. Qui no, di proposito:

* tre stati e **due** passaggi: una matrice sarebbe una tabella di due righe che
  nessuno interroga;
* la matrice esiste anche perché il **frontend** ci legge le azioni con la loro
  etichetta. Qui le azioni **sono i due verbi**, e non c'è una terza via da
  scoprire leggendo una tabella.

⚠️ Chi cerca la regola guardando i dati non la troverà: è **qui**, ed è il motivo
per cui il codice errore la nomina per esteso.

### ⭐ Due regole, due codici — e la differenza conta

| Che cosa si sta facendo | Codice |
| --- | --- |
| cambiare **stato** lungo un passaggio che non esiste | `E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA` |
| toccare **qualunque cosa** di un atto già terminale | `E_SISTEMAZIONE_IMMUTABILE` |

⚠️ Servono entrambi perché dicono due cose diverse a chi legge. *«Non può passare
da CONFERMATA a BOZZA»* è vero; ma se qualcuno prova a correggere l'importo di un
atto già eseguito, quella frase non lo aiuta — il problema non è lo stato, è che
**quel denaro si è già mosso**.

### ⚠️ Su un atto terminale si rifiuta *ogni* update

Non solo quelli che cambiano stato. Un atto confermato ha generato un documento:
se il registro potesse cambiare sotto, racconterebbe una cosa e il documento
un'altra. ⭐ E la conferma stessa non ci inciampa: quella parte da `BOZZA`.

---

{% include-markdown "signature-core.md" %}
