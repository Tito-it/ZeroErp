## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_guard_annullamento()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
>
Approfondimento funzioni:
> • [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile)
> • [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — creata 2026-08-04, brief vie-uscita-operatore §3.1)

**Un preventivo che ha già prodotto qualcosa a valle non si annulla.** Se ne è nato un
ordine, o se è entrato in una commessa, l'annullamento cancellerebbe il capostipite di una
catena che continua a esistere.

La regola non è scritta qui. Vive in `script.fn_check_preventivo_annullabile`, che
restituisce l'**elenco dei motivi** che impediscono l'annullamento — ed è la stessa funzione
letta da `fn_available_actions_preventivo` per decidere se accendere il bottone nella UI.

Questa funzione **solleva soltanto**. È la divisione dei ruoli che tiene allineati bottone e
database: un solo verdetto, due modi di consumarlo. Se un giorno la regola cambia, cambia in
un posto e la UI si adegua da sé.

---

### Aggancio

Trigger `trg_preventivi_a10_guard_annullamento_upd` — fase `_a10_`,
`BEFORE UPDATE OF stato_doc_preventivo_id` su `vendite.preventivi`, `FOR EACH ROW`.

---

### Regole applicate

1. **No-op** se lo stato non cambia davvero.
2. Risolve il `codice_interno` dello stato di destinazione; se **non** è `ANNULLATO`,
   esce senza fare nulla. Il guard è mirato: costa una sola lettura su ogni altra
   transizione.
3. Chiama `script.fn_check_preventivo_annullabile(NEW.id)` e, se l'array dei motivi non è
   vuoto, solleva.

---

### ⭐ Il codice errore è dinamico

```sql
v_motivi -> 0 ->> 'codice'
```

Il codice sollevato è quello del **primo motivo** restituito dalla check, non una costante.
Ne segue che l'errore parla della causa reale — ordine generato, riga in commessa — invece di
un generico «non annullabile».

Due conseguenze da conoscere:

* **L'elenco dei codici possibili non si legge da questa funzione.** Va cercato in
  `script.fn_check_preventivo_annullabile`, che è dove i motivi si costruiscono. Chi
  cataloga i codici errore partendo dai `PERFORM fn_log_and_raise_error` non trova questo
  punto.
* **Se ci sono più motivi, l'utente ne vede uno solo** — il primo. Gli altri restano nel
  `context` JSONB sotto la chiave `motivi`, che riporta l'array completo: risolto il primo
  ostacolo, il secondo tentativo può fallire di nuovo per un motivo diverso.

---

### ⚠️ Il refuso che ha lasciato il segno

Fino alla revisione del 2026-08-04 la funzione citava `NEW.codice` — **una colonna che
`vendite.preventivi` non ha**. L'identificativo leggibile è `numero` (varchar); esistono anche
`uid` (la chiave usata dalle catene documentali) e `rev`.

Il refuso è nato con la funzione, tre changeSet prima, ed è sopravvissuto finché non l'ha
intercettato il controllo sui riferimenti morti. Vale la pena saperlo perché è la forma tipica
del difetto in un trigger: il codice è corretto sintatticamente, la funzione si crea senza
errori, e il problema si manifesta solo sul **ramo di errore** — cioè esattamente quando
serve.

---

### ⚠️ Gira prima del guard di transizione

L'ordine alfabetico dei `BEFORE ROW` mette `guard_annullamento` **prima** di
`guard_transizione`. Su un preventivo con figli a valle, quindi, è questo guard a parlare
per primo: l'utente riceve il codice del motivo di non-annullabilità, mai
`E_PREV_TRANSIZIONE_NON_AMMESSA`.

---

### Codici errore

Variabili: il codice è quello del primo motivo restituito da
`script.fn_check_preventivo_annullabile`. Sollevato via `script.fn_log_and_raise_error`
con `NEW.tx_id` propagato; nel context finiscono `preventivo_id`, `numero`, `stato_a` e
l'**array completo** dei motivi.

---

{% include-markdown "signature-core.md" %}
