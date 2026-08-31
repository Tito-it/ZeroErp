## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_sistemazioni_guard_transizione`

### ⭐ rev 31-08-2026 — UN VARCO, E UNO SOLO (D-25)

`CONFERMATA → ANNULLATA` si apre **per il solo ramo `RIPORTO`**.

**Perché proprio quello:** le altre due destinazioni lasciano dietro una
**distinta**, e per una distinta sbagliata il rimedio esiste già — la correzione
guidata. Il `RIPORTO` lascia un **fondo** in `vendite`, e per quello non c'era
niente. *Una sistemazione nuova non è la contropartita di un riporto sbagliato:
la sistemazione pretende un'eccedenza, e quel riporto l'ha già consumata.*

⚠️ **Il varco è chirurgico su TRE assi**, e devono valere tutti insieme:

1. **la transizione** — solo `CONFERMATA → ANNULLATA`;
2. **la destinazione** — solo `RIPORTO`. ⛔ *Due strade per disfare lo stesso
   fatto è il modo in cui due meccanismi cominciano a divergere: la prima volta
   fanno la stessa cosa, alla prima regola nuova no, e nessuno sa più quale sia
   quella giusta;*
3. **le colonne** — su un atto terminale si rifiuta **ogni** modifica, non solo
   quelle di stato. Passano `stato`, `motivo`, `data_esecuzione`,
   `user_esecuzione`, `fondo_source_id`, `meta` e le tecniche di audit.

> ⭐ Il confronto elenca le colonne **ammesse**, non quelle vietate: così una
> colonna nuova sulla tabella nasce **chiusa** invece di diventare modificabile
> in silenzio.

⚠️ `fondo_source_id` deve uscire **azzerato** perché `fk_sistemazioni_fondo_source`
è `NO ACTION`; con lui cadono `data_esecuzione` e `user_esecuzione`, che
`chk_sistemazioni_eseguita` vuole `NULL` fuori da `CONFERMATA`. Sono un dato
**composito**: si sposta intero o non si sposta.

⭐ **E il rifiuto sugli altri due NOMINA L'ALTERNATIVA** — `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO`,
che manda alla correzione guidata sulla distinta. Non è un'idea nuova: è
l'autocritica che questa pagina portava già — *«non può passare da CONFERMATA a
BOZZA» è vero ma non aiuta chi sta provando a correggere un importo già
eseguito.*

---

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
