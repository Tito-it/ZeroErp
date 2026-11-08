## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_sistemazioni_guard_transizione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — il registro di cui il guard governa gli stati
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — il fondo che un riporto lascia dietro, e che il varco fa cadere
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione) — il verbo che porta l'atto a `CONFERMATA`
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — il verbo che porta l'atto ad `ANNULLATA`, e che si affida a questo guard per lo stato
> * [pagamenti.fn_crea_distinta_correzione](/dbzero/pagamenti/funzioni/fn_crea_distinta_correzione) — la correzione guidata, il rimedio per un rimborso o una compensazione sbagliati

---

### 🎯 Scopo Principale

Governa il percorso di un atto di sistemazione: nasce in `BOZZA`, va a `CONFERMATA` o ad `ANNULLATA`, e da lì non si muove più, salvo l'annullamento di un riporto confermato.

```text
BOZZA ──► CONFERMATA    (l'atto diventa un fatto: genera distinta o fondo)
  │           └────► ANNULLATA   (solo RIPORTO: il fondo cade con l'atto)
  └────► ANNULLATA      (la decisione si scarta)
```

Non c'è ritorno da `CONFERMATA` perché a quel punto **il denaro si è già mosso**: la
correzione è una sistemazione **nuova**, o la correzione guidata sulla distinta. È la stessa
regola della distinta contabile chiusa.

---

### ⛔ Niente tabella-matrice, e non è una dimenticanza

`vendite_contabili` e le sue righe hanno una matrice di transizioni seminata a dato. Qui no, di
proposito:

* tre stati e pochi passaggi: una matrice sarebbe una tabella di poche righe che nessuno
  interroga;
* la matrice esiste anche perché il **frontend** ci legge le azioni con la loro etichetta. Qui
  le azioni **sono i due verbi**, e non c'è una terza via da scoprire leggendo una tabella.

⚠️ Chi cerca la regola guardando i dati non la troverà: è **qui**, ed è il motivo per cui il
codice errore la nomina per esteso.

---

### ⚠️ Su un atto terminale si rifiuta *ogni* update

Non solo quelli che cambiano stato. Un atto confermato ha generato un documento: se il
registro potesse cambiare sotto, racconterebbe una cosa e il documento un'altra. ⭐ La conferma
non ci inciampa: parte da `BOZZA`.

Le regole sono tre, e ciascuna ha il suo codice, perché dicono cose diverse a chi legge:

| Che cosa si sta facendo | Codice |
| --- | --- |
| far nascere l'atto in uno stato diverso da `BOZZA`, o cambiarne lo stato lungo un passaggio che non esiste | `E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA` |
| annullare un `RIMBORSO` o una `COMPENSAZIONE` già confermati | `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO` |
| toccare **qualunque altra cosa** di un atto già terminale | `E_SISTEMAZIONE_IMMUTABILE` |

⭐ «Non può passare da `CONFERMATA` a `BOZZA`» è vero; ma se qualcuno prova a correggere
l'importo di un atto già eseguito quella frase non lo aiuta: il problema non è lo stato, è
che **quel denaro si è già mosso**. Per la stessa ragione il rifiuto dell'annullamento su rimborso e
compensazione **nomina l'alternativa**, la correzione guidata sulla distinta, invece di dire
soltanto «immutabile».

---

### ⭐ Un varco, e uno solo: l'annullamento del riporto

`CONFERMATA → ANNULLATA` si apre **per il solo `RIPORTO`**. Le altre due destinazioni lasciano
dietro una **distinta**, e per una distinta sbagliata il rimedio esiste già: la correzione
guidata. Il riporto lascia un **fondo** in `vendite`, e per quello non c'era niente. Una
sistemazione nuova non è la contropartita di un riporto sbagliato: la sistemazione pretende
un'eccedenza, e quel riporto l'ha già consumata.

⚠️ **Il varco è chirurgico su tre assi**, e devono valere tutti insieme:

1. **la transizione**: solo `CONFERMATA → ANNULLATA`;
2. **la destinazione**: solo `RIPORTO`. ⛔ Due strade per disfare lo stesso fatto sono il modo
   in cui due meccanismi cominciano a divergere: la prima volta fanno la stessa cosa, alla
   prima regola nuova no, e nessuno sa più quale sia quella giusta;
3. **le colonne**: passano solo `stato`, `motivo`, `data_esecuzione`, `user_esecuzione`,
   `fondo_source_id`, `meta` e le colonne tecniche di audit; ogni altra colonna deve restare
   com'era.

⭐ Il confronto elenca le colonne **ammesse**, non quelle vietate: così una colonna nuova sulla
tabella nasce **chiusa** invece di diventare modificabile in silenzio.

⚠️ `fondo_source_id` deve uscire **azzerato**: `fk_sistemazioni_fondo_source` è `NO ACTION`, e
finché l'atto punta il fondo il fondo non si cancella. Con lui cade `data_esecuzione`, che
`chk_sistemazioni_eseguita` vuole vuota fuori da `CONFERMATA`, e cade `user_esecuzione`, che il
`CHECK` non nomina ma appartiene allo stesso dato composito: si sposta intero o non si sposta.
La memoria dell'esecuzione la conserva `fn_annulla_sistemazione` dentro `meta`.

---

### Codici errore

* `E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA` — l'atto nasce in uno stato diverso da `BOZZA`, o si
  chiede un passaggio di stato che il percorso non prevede.
* `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO` — si annulla un rimborso o una compensazione già
  confermati.
* `E_SISTEMAZIONE_IMMUTABILE` — si modifica un atto già terminale fuori dal varco.

---

### Test

* `db/pgtap/pagamenti/test-sistemazione-annullo-riporto.sql` — i tre assi del varco: l'importo
  resta immutabile da solo e insieme all'annullamento, da `CONFERMATA` non si torna in `BOZZA`,
  l'annullamento del riporto passa, e su una compensazione il rifiuto è quello che nomina
  l'alternativa.
* `db/pgtap/pagamenti/test-sistemazioni-registro.sql` — il test 11: un atto non nasce già
  confermato.
* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il test 8: modificare l'importo di un
  atto eseguito è rifiutato.

---

### Note di migrazione

* 2026-08-22 — nasce con il registro `sistemazioni`: percorso `BOZZA → CONFERMATA | ANNULLATA`,
  entrambi terminali senza eccezioni.
* 2026-08-31 — si apre il varco `CONFERMATA → ANNULLATA` sul solo `RIPORTO`, con il nuovo codice
  `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO` per gli altri due rami.

---

{% include-markdown "signature-core.md" %}
