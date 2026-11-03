## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_prevent_deactivate_if_children`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — i nomi della colonna attivo, quando non è `attivo`
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che monta questo trigger, il *block*
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il gemello sul figlio, il *require*
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — riconosce i block rimasti senza figlia
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — il registro senza sollevare, usato per i casi da segnalare
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Il *block* della regola ATTIVO: impedisce di **spegnere un padre** (la sua colonna attivo da vera a
falsa) finché ha figli collegati. Se la figlia ha la colonna attivo bloccano solo i figli attivi;
se non ce l'ha, blocca qualunque figlio.

Lo monta `dbops.fn_run_automations_attivo` sul padre, prima di un `UPDATE` della colonna attivo,
un trigger per ogni FK. Non spegne niente da sé: nessuna cascata sui figli.

---

### Gli argomenti del trigger

In ordine: schema e tabella della figlia, colonna FK della figlia, colonna del padre referenziata
dalla FK, nome della colonna attivo del **padre**. La colonna referenziata può essere una `UNIQUE`
diversa dalla chiave primaria. Gli ultimi due sono facoltativi (`id` e `attivo` se mancano), ma è
una forma deprecata: il generatore li passa sempre, così il nome della colonna attivo del padre
rispetta `automation_overrides_cols`.

---

### Quando blocca

Il controllo si fa solo sul passaggio **da vero a falso** della colonna attivo del padre. Un
aggiornamento che lascia la colonna com'era, o che la riaccende, passa senza guardare i figli.

Allora la funzione cerca nella figlia una riga che punta al padre per la colonna referenziata,
con il valore convertito al tipo della colonna FK:

* figlia **con** colonna attivo (col nome di `automation_overrides_cols`, se c'è): conta solo una
  riga che non sia spenta;
* figlia **senza** colonna attivo: conta qualunque riga.

Se il padre ha la colonna referenziata vuota il controllo si salta, e il salto si scrive nel
registro errori senza sollevare (`E_ATTIVO_BLOCK_REF_NULL`).

---

### ⭐ Due rami, due codici, due rimedi

I due rami non sono due modi di dire la stessa cosa: hanno **rimedi diversi**.

| Figlia | Che cosa blocca | Rimedio | Codice |
| --- | --- | --- | --- |
| con la colonna attivo | le righe attive | spegnerle: prima i figli, poi il padre | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` |
| senza la colonna attivo | qualunque riga | toglierle, perché spegnerle non si può | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |

La funzione sceglie il **codice**, non compone la frase: il testo sta a catalogo e qui viaggiano
solo i dati, nell'ordine che il messaggio consuma — padre, colonna referenziata, suo valore,
figlia — più la colonna FK, passata in più perché arricchire il messaggio non costi una modifica
di codice. ⛔ I due messaggi condividono la stessa lista di valori: devono avere gli stessi
segnaposti nello stesso ordine, altrimenti due nomi di tabella si scambiano in una frase che resta
grammaticalmente perfetta.

---

### ⚠️ Vede i figli con gli occhi di chi spegne

La funzione è `SECURITY INVOKER`: la ricerca dei figli passa dalla row level security di chi fa
l'aggiornamento. Un figlio attivo **fuori dal perimetro** di chi spegne il padre non si vede, e il
padre si spegne.

---

### ⚠️ Il fallback deprecato scrive nel registro errori a ogni aggiornamento

Quando mancano il quarto o il quinto argomento la funzione scrive una riga in `dbops.error_log`
(codice `E_ATTIVO_BLOCK`, senza sollevare) per ogni argomento mancante, **a ogni scatto** del
trigger, anche quando l'aggiornamento non spegne il padre.

---

### Codici errore

* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST` — il rifiuto, secondo il ramo.
* `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` — la colonna FK della figlia non esiste: per esempio un block
  rimasto dopo l'eliminazione della figlia (lo toglie `dbops.fn_ritira_attivo_orfani`).
* `E_ATTIVO_BLOCK_ARGS` — il trigger è montato con meno di tre argomenti.
* `E_ATTIVO_BLOCK_REF_NULL`, `E_ATTIVO_BLOCK` — solo nel registro errori, senza sollevare: il
  controllo saltato per la colonna referenziata vuota, e gli argomenti deprecati.

---

### Test

* `db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql` — il ramo della figlia con
  la colonna attivo (`config.stati_pdp` → `anagrafiche.pdp`): bloccano solo i figli attivi, col
  codice del ramo; il test 13 presidia l'ordine dei valori del messaggio.
* `db/pgtap/config/test-trgfn-prevent-deactivate-if-children-toponomastica.sql` — il ramo della
  figlia senza colonna attivo (`config.toponomastica` → `config.stradario_generale`).
* `db/pgtap/vendite/test-registri-per-emittente-v1.sql` — il ramo senza colonna attivo, col suo
  codice (test 6).
* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — dopo il ritiro degli orfani il padre si
  spegne.

---

### Note di migrazione

* 2026-08-05 — il caso della colonna referenziata vuota si registra con un codice suo e senza
  sollevare; prima la chiamata al registro sollevava e una disattivazione legittima falliva.
* 2026-08-20 — la frase esce dal codice e sta a catalogo, e il rifiuto si divide in due codici,
  uno per ramo. Prima il messaggio era uno, diceva «attive» anche quando la figlia non ha la
  colonna, e non nominava la tabella che bloccava.

---

{% include-markdown "signature-core.md" %}
