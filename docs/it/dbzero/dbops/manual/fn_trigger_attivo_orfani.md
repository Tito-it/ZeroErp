# fn_trigger_attivo_orfani

### Scopo

Elenca i trigger ATTIVO che **nominano una tabella o una colonna che non esiste
più**. È il lettore unico della regola: lo usano il ritiro
[`dbops.fn_ritira_attivo_orfani`](/dbzero/dbops/manual/fn_ritira_attivo_orfani)
e il presidio `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql`.

## Perché esistono gli orfani

I trigger del framework ATTIVO legano padre e figlia con una **stringa** negli
argomenti, non con una dipendenza che PostgreSQL conosce. Quando si elimina la
figlia, il `DROP TABLE … CASCADE` toglie la FK ma lascia il block sul padre. Da
quel momento ogni disattivazione del padre si ferma con
`E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`.

## Che cosa è un orfano

⛔ **Un nome morto, non una FK che manca.** Alcuni require sono scritti a mano su
chiavi **polimorfe** (una colonna che punta a tabelle diverse secondo il tipo) e
non hanno FK: sono legittimi e restano.

Un trigger è orfano quando manca una delle cose che il **suo** corpo legge:

| Trigger | Funzione | Altra tabella | Colonne lette |
| --- | --- | --- | --- |
| block, sul **padre** | `dbops.trgfn_prevent_deactivate_if_children` | la figlia, argomenti 1-2 | figlia.arg 3 (FK) · padre.arg 4 (default `id`) · padre.arg 5 (default `attivo`) |
| require, sul **figlio** | `dbops.trgfn_child_requires_active_parent` | il padre, argomenti 1-2 | padre.arg 3 (attivo) · figlio.arg 4 (FK) · padre.arg 5 (default `id`) |

## I motivi

| `motivo` | Quando | `dettaglio` |
| --- | --- | --- |
| `TABELLA_ASSENTE` | l'altra tabella non esiste | la tabella nominata |
| `COLONNA_ASSENTE` | manca una delle tre colonne lette | le colonne che mancano |
| `ARGOMENTI_INSUFFICIENTI` | meno argomenti del minimo (3 per il block, 4 per il require) | quanti sono |

Il terzo non è un residuo ma un errore di scrittura: il ritiro non lo tocca, e
lo corregge una persona.

## Come legge

Dal catalogo (`pg_class`, `pg_attribute`) per nome, con gli argomenti letti da
[`dbops.fn_trigger_argomenti`](/dbzero/dbops/manual/fn_trigger_argomenti).
⛔ Non da `information_schema`: mostra solo le colonne su cui chi chiede ha un
privilegio, e il job delle automazioni vedrebbe «assente» una colonna valida.
