## 📘 Documentazione Concettuale – Tabella `vendite.listini_versioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
### 🎯 Scopo Principale
La tabella `vendite.listini_versioni` gestisce il versionamento temporale dei listini.
Ogni versione definisce una finestra di validita` e una priorita` operativa.

---

### Regole principali

* univocita` per `listino_id + codice_versione`;
* `stato` ammessi:
  * `BOZZA`
  * `ATTIVA`
  * `CHIUSA`
* `priorita > 0`;
* `valido_al` maggiore di `valido_dal` se valorizzato;
* no overlap temporale **tra versioni `stato = 'ATTIVA'`** dello stesso listino
  (`ex_listini_versioni_no_overlap`). **BOZZE e CHIUSE possono coesistere**
  con un'ATTIVA (e tra loro) anche su intervalli sovrapposti — vedi sezione
  *Workflow clone + publish* qui sotto.

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
* fornire ordinamento secondario in risoluzione prezzi.

---

{% include-markdown "signature-core.md" %}
