## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_prevent_deactivate_if_children`

> **Ultimo aggiornamento**: 7 novembre 2026
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
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica degli argomenti
> * [dbops.fn_trigger_figlie_presenti](/dbzero/dbops/funzioni/fn_trigger_figlie_presenti) — cerca i figli, fuori dalla row level security
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il gemello sul figlio, il *require*
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — riconosce i block rimasti senza figlia
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — il registro senza sollevare, usato per la colonna referenziata vuota
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

Cinque, **tutti obbligatori**, nella grammatica di `dbops.fn_trigger_attivo_argomenti`: schema e
tabella della figlia, colonna FK della figlia, colonna del padre referenziata dalla FK, nome della
colonna attivo del **padre** (col nome di `automation_overrides_cols`, se c'è). La colonna
referenziata può essere una `UNIQUE` diversa dalla chiave primaria. Non ci sono ripieghi: un
montaggio con un argomento mancante o vuoto, o che nomina una colonna che il padre non ha, si
rifiuta.

---

### Quando blocca

Il controllo si fa solo sul passaggio **da vero a falso** della colonna attivo del padre. Un
aggiornamento che lascia la colonna com'era, o che la riaccende, passa senza guardare i figli.

Allora si cerca nella figlia una riga che punta al padre per la colonna referenziata:

* figlia **con** colonna attivo (col nome di `automation_overrides_cols`, se c'è): conta solo una
  riga che non sia spenta;
* figlia **senza** colonna attivo: conta qualunque riga.

Se il padre ha la colonna referenziata vuota nessuna figlia può riferirla: il controllo si salta, e
il salto si scrive nel registro errori senza sollevare (`E_ATTIVO_BLOCK_REF_NULL`).

---

### ⭐ I figli si cercano con gli occhi del proprietario

La ricerca la fa `dbops.fn_trigger_figlie_presenti`, fuori dalla row level security: che un padre
sia ancora usato non dipende da chi guarda. Un catalogo visibile a tutti con figli attivi di
un'altra azienda non si spegne, anche se chi lo spegne quei figli non li vede. La ricerca riceve il
trigger, non i nomi delle tabelle, e legge gli argomenti dal suo montaggio.

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

### Codici errore

* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST` — il rifiuto, secondo il ramo.
* `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` — la figlia o la sua colonna FK non esistono: per esempio un
  block rimasto dopo l'eliminazione della figlia (lo toglie `dbops.fn_ritira_attivo_orfani`).
* `E_ATTIVO_BLOCK_ARGS` — il trigger è montato fuori grammatica, o nomina una colonna che il padre
  non ha.
* `E_ATTIVO_BLOCK_REF_NULL` — solo nel registro errori, senza sollevare: il controllo saltato per
  la colonna referenziata vuota.

---

### Test

* `db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql` — il ramo della figlia con
  la colonna attivo (`config.stati_pdp` → `anagrafiche.pdp`): bloccano solo i figli attivi, col
  codice del ramo; il test 13 presidia l'ordine dei valori del messaggio.
* `db/pgtap/config/test-trgfn-prevent-deactivate-if-children-toponomastica.sql` — il ramo della
  figlia senza colonna attivo (`config.toponomastica` → `config.stradario_generale`).
* `db/pgtap/dbops/test-guard-attivo-occhi-del-proprietario-v1.sql` — come applicazione: una
  tipologia di listino usata dal listino di un'altra azienda non si spegne.
* `db/pgtap/dbops/test-guard-attivo-grammatica-e-codici-v1.sql` — il montaggio con quattro
  argomenti si rifiuta.
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
* 2026-11-07 — i figli si cercano fuori dalla row level security (prima, sotto quella di chi
  spegneva il padre, che non vedeva i figli fuori perimetro); quarto e quinto argomento obbligatori
  (prima i ripieghi su `id` e `attivo` scrivevano nel registro errori a ogni scatto).

---

{% include-markdown "signature-core.md" %}
