## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_attivo_orfani`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_ritira_attivo_orfani](/dbzero/dbops/funzioni/fn_ritira_attivo_orfani) — il ritiro che usa questo elenco
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — legge gli argomenti dei trigger
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica degli argomenti, la stessa delle funzioni trigger
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block sul padre, uno dei due trigger guardati
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il require sul figlio, l'altro
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, gli orfani
> * [Linee guida trigger](/linee-guida-trigger#il-nome-della-funzione-trigger) — chi legge gli argomenti da fuori

---

### 🎯 Scopo Principale

Elenca i trigger ATTIVO che **nominano una tabella o una colonna che non esiste più**, con il
motivo e il dettaglio. È il lettore unico della regola: lo usano il ritiro
`dbops.fn_ritira_attivo_orfani` e il presidio pgTAP.

---

### Perché esistono gli orfani

I trigger del framework ATTIVO legano padre e figlia con una **stringa** negli argomenti, non con
una dipendenza che PostgreSQL conosce. Quando si elimina la figlia, la cancellazione in cascata
toglie la FK ma lascia il block sul padre, e da quel momento ogni disattivazione del padre si ferma
con `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`.

---

### ⛔ Un orfano è un nome morto, non una FK che manca

Alcuni require sono scritti a mano su chiavi **polimorfe** (una colonna che punta a tabelle diverse
secondo il tipo) e non hanno FK: sono legittimi e non compaiono qui. Un trigger è orfano quando
manca una delle cose che il **suo** corpo legge:

| Trigger | Altra tabella | Colonne lette |
| --- | --- | --- |
| block, sul **padre** | la figlia, primo e secondo argomento | sulla figlia la colonna FK (terzo); sul padre la colonna referenziata (quarto) e la colonna attivo (quinto) |
| require, sul **figlio** | il padre, primo e secondo argomento | sul padre la colonna attivo (terzo) e la colonna referenziata (quinto); sul figlio la colonna FK (quarto) |

---

### I motivi

| `motivo` | Quando | `dettaglio` |
| --- | --- | --- |
| `TABELLA_ASSENTE` | l'altra tabella non esiste | la tabella nominata |
| `COLONNA_ASSENTE` | manca una delle tre colonne lette | le colonne che mancano |
| `ARGOMENTI_INVALIDI` | il montaggio è fuori dalla grammatica: un argomento mancante, vuoto o in più (ne servono cinque, tutti) | il perché, come lo dice la grammatica |

Il terzo non è un residuo ma un errore di scrittura: il ritiro non lo tocca.

⭐ Gli argomenti li legge `dbops.fn_trigger_attivo_argomenti`, la stessa grammatica che usano le
funzioni trigger: un montaggio che il trigger rifiuterebbe per gli argomenti è quello che il
lettore riporta, e non ci sono minimi o valori di riserva da tenere allineati.

---

### ⛔ Legge il catalogo, non `information_schema`

Tabelle e colonne si cercano per nome in `pg_class` e `pg_attribute`, con gli argomenti letti da
`dbops.fn_trigger_argomenti` e interpretati da `dbops.fn_trigger_attivo_argomenti`. `information_schema` mostra solo le colonne su cui chi chiede ha un
privilegio, e il job delle automazioni vedrebbe «assente» una colonna valida.

---

### Test

* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — sulla fixture il lettore trova esattamente
  i tre casi attesi col loro motivo, e `COLONNA_ASSENTE` nomina la colonna che manca; un require
  polimorfo senza FK non è orfano. Il test 3 è un presidio sul database: nessun orfano fuori dalla
  fixture (verde in CI per costruzione, rosso su sviluppo finché il job non ha ripulito).

---

### Note di migrazione

* 2026-10-21 — nasce per il ritiro degli orfani (`brief-be-utenti-di-sviluppo` §9.5).
* 2026-11-07 — legge gli argomenti dalla grammatica condivisa; il motivo `ARGOMENTI_INSUFFICIENTI`
  diventa `ARGOMENTI_INVALIDI`, perché gli argomenti sono tutti obbligatori.

---

{% include-markdown "signature-core.md" %}
