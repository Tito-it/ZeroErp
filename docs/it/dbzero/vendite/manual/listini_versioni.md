## 📘 Documentazione Concettuale – Tabella `vendite.listini_versioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
### 🎯 Scopo Principale
(latest review 09-04-2026)

La tabella `vendite.listini_versioni` gestisce il versionamento temporale dei listini.
Ogni versione definisce una **finestra di validita atomica** dei prezzi: tutte le righe
prezzo (`vendite.listini_righe`) ereditano l'intervallo temporale dalla versione che
le contiene — le righe **non hanno date proprie**.

Per cambiare i prezzi di un listino in un nuovo periodo (es. annuale), si crea una
**nuova versione** con il nuovo intervallo, non si modifica la versione esistente.
Vedi sezione *Workflow clone + publish* qui sotto.

---

### Regole principali

* univocita` per `listino_id + codice_versione`;
* `stato` ammessi:
  * `BOZZA`
  * `ATTIVA`
  * `CHIUSA`
* `valido_al` maggiore di `valido_dal` se valorizzato;
* no overlap temporale **tra versioni `stato = 'ATTIVA'`** dello stesso listino
  (`ex_listini_versioni_no_overlap`, fix `20260409-01`). **BOZZE e CHIUSE possono
  coesistere** con un'ATTIVA (e tra loro) anche su intervalli sovrapposti — vedi
  sezione *Workflow clone + publish* qui sotto.

> 🗑️ **Campo `priorita` RIMOSSO il 2026-04-09 (Fase 2 refactor)**. Con l'invariante
> univocita per versione `ATTIVA` garantita dall'EXCLUDE constraint
> (`ex_listini_versioni_no_overlap`), due versioni `ATTIVA` sovrapposte
> sono impossibili → niente tie-break tra versioni → la priorita non
> discriminava piu nulla. La colonna e il check constraint
> `chk_listini_versioni_priorita` sono stati droppati con la migration
> `20260409-05-drop-priorita-listini-versioni`. Vedi
> [WIP listini-commercio §5](/dev/work-in-progress/listini-commercio).

---

### Workflow clone + publish

Una nuova versione viene tipicamente preparata **in anticipo** rispetto alla data
di entrata in vigore:

1. **Clone**: il backend crea una nuova riga con `stato = 'BOZZA'`,
   `valido_dal` futura (es. oggi+30gg) e `valido_al` NULL. La BOZZA può
   coesistere con la versione `'ATTIVA'` corrente perché il vincolo
   `ex_listini_versioni_no_overlap` filtra solo `attivo IS TRUE AND stato = 'ATTIVA'`.
2. **Edit**: l'utente modifica le righe della BOZZA finché non è pronta.
3. **Publish (D3)**: nella stessa transazione il backend
   * imposta `valido_al = nuova.valido_dal - 1` sulle versioni precedenti `'ATTIVA'`
     (autoclose),
   * cambia `stato = 'ATTIVA'` sulla nuova versione.
   L'invariante "una sola `'ATTIVA'` per listino sull'intervallo" viene
   garantito dall'EXCLUDE alla fine della transazione.

> **Storia del vincolo**: in versioni precedenti il filtro era solo
> `WHERE (attivo IS TRUE)`, e l'INSERT della BOZZA "in anticipo" falliva per
> overlap con la riga ATTIVA. Il fix `20260409-01-fix-listini-versioni-overlap-stato`
> ha ristretto il filtro a `(attivo IS TRUE AND stato = 'ATTIVA')`,
> riallineando il vincolo DB al workflow applicativo e al messaggio del
> translator backend ("Esiste già una versione attiva sovrapposta").

---

### Utilizzo previsto

* garantire coerenza storica prezzi per data di riferimento;
* supportare publish controllata di nuove versioni;
* finestre temporali "atomiche" per i prezzi: ogni versione e una *fotografia*
  immutabile dei prezzi validi nel suo intervallo.

### Asimmetrie del modello (note operative)

* **Le righe non hanno date proprie**: per cambiare un prezzo a meta intervallo
  bisogna creare una nuova versione e ricopiare *tutte* le righe (anche quelle
  invariate). Mitigazione: funzione/endpoint di "clone con override massivo"
  lato backend (TODO).
* **Una versione = una sola valuta**: il modello attuale e implicitamente
  monovaluta (nessuna colonna `valuta_id` su `listini_versioni`). Per supportare
  valuta multipla in futuro andra aggiunta una colonna additiva. Vedi
  [WIP listini-commercio §6.4](/dev/work-in-progress/listini-commercio).
* **`pricing_mode` non ancora esplicito**: il modello v1 e dichiaratamente
  `FIXED` per tutte le righe (prezzo unitario costante). I modi `SCAGLIONI` e
  `FORMULA` previsti per v2 non sono ancora rappresentati nello schema. Vedi
  [WIP listini-commercio §6.6](/dev/work-in-progress/listini-commercio).

---

{% include-markdown "signature-core.md" %}
