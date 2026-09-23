## 📘 Documentazione Concettuale – Funzione `script.fn_check_documento_interno_registrabile()`

> 👀 **Vedi anche**
>
> **Chi la chiama** — quattro, in due mestieri:
>
> • [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) e [magazzino.fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — **sollevano** il codice del primo motivo
> • [script.fn_available_actions_documento_interno](/dbzero/script/funzioni/fn_available_actions_documento_interno) e i suoi due involucri — **spengono** il pulsante «Registra» con la sua `reason_key`
>
> **Su cosa si appoggia:**
>
> • [script.fn_check_riga_magazzino](/dbzero/script/funzioni/fn_check_riga_magazzino) — la stessa check che la primitiva chiama, per il terzo motivo
> • [magazzino.fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) — per l'inventario, la sede che dice quali righe sono postabili
>
> **La regola:** [linee-guida-sql §12.1 e §12.5](/linee-guida-sql)
>
> **Piano:** [brief-db-magazzino-lotto-2-bis-be-fe](/dev/work-in-progress/brief-db-magazzino-lotto-2-bis-be-fe) R-1

---

### 🎯 Scopo Principale
(scritta il 22-09-2026)

Elenca i motivi, **ordinati**, che impediscono di **registrare** un documento
interno di magazzino — un inventario o una rettifica. Risponde `[]` quando si
può.

«Registrare» è il verbo irreversibile del magazzino: scrive i movimenti sul
registro. Per questo la domanda *«si può?»* serve in due momenti diversi — prima,
per accendere o spegnere il pulsante; e nell'istante in cui si preme, per
rifiutare. Le due risposte devono essere **la stessa**, e lo sono perché sono la
stessa funzione.

---

### I tre motivi, nell'ordine che è il contratto

Precedenza dichiarata: **stato → righe → postabilità**. Si esce al primo: gli
altri parlerebbero di un documento che comunque non si registra.

| # | `reason` | Quando | `codice` | `valori` |
| --- | --- | --- | --- | --- |
| 1 | `DOCUMENTO_NON_CONFERMATO` · `DOCUMENTO_GIA_REGISTRATO` · `DOCUMENTO_ANNULLATO` | lo stato non è `CONFIRM` | `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` | `(stato attuale, 'POSTED')` |
| 2 | `DOCUMENTO_SENZA_RIGHE` | nessuna riga | `E_MAG_DOCUMENTO_SENZA_RIGHE` | `(id del documento)` |
| 3 | `RIGHE_NON_POSTABILI` | una riga che la primitiva rifiuterebbe | **quello della riga**: il primo motivo di `fn_check_riga_magazzino` | quelli della riga |

⭐ **Un codice, tre motivi** (riga 1), e non è una svista. Il `codice` sceglie la
frase dell'**errore**, e su tutti e tre gli stati è la stessa cosa: *«il
passaggio a POSTED non è ammesso»*. Il `reason` sceglie il **tooltip del
pulsante**, e lì «il documento non è confermato» detto di un documento **già
registrato** sarebbe falso. Un motivo sbagliato è peggio di nessun motivo
(§12.1). ⚠️ Trovato provando la funzione, non scrivendola: la prima stesura
rispondeva `DOCUMENTO_NON_CONFERMATO` su un `POSTED`.

⭐ **Il terzo motivo tiene il codice della RIGA** (`E_MAG_ARTICOLO_NON_GESTITO`,
`E_MAG_UBICAZIONE_OBBLIGATORIA`, …) e i suoi `valori`: così la frase che
l'operatore legge quando preme «Registra» è **identica** a quella di prima, e i
pgTAP del Lotto 2 che la pinnano non si muovono. Cambia solo il vestito che
serve al pulsante — `reason` e `reason_key` sono del **documento**, perché il
tooltip dice *«ci sono righe da sistemare»*; quale riga e perché sta nel
`dettaglio` (`riga_id`, `riga_reason`, `campo`) e nella lista delle righe.

Le `reason_key` sono `magazzino.documenti_interni.registra_reason.{non_confermato,
gia_registrato, annullato, senza_righe, righe_non_postabili}` — un **debito
verso il frontend**: senza le voci nei locales il pulsante spento mostra un
tooltip vuoto.

---

### ⭐ Dove sta la differenza fra le due famiglie, e dove no

La regola è una sola (D-L2-h), le tabelle sono due. Il terzo motivo è l'unico
punto in cui le due strade divergono, e per una ragione di modello:

* l'**inventario** ha un piano (`fn_inventario_piano`): quali righe siano
  postabili lo dice già lì, e la check legge quella sede invece di rifare il
  conto;
* la **rettifica** non ha un piano — i delta sono un dato, non una differenza da
  calcolare — quindi la check interroga `fn_check_riga_magazzino` riga per riga,
  in ordine di id: la prima che parla vince.

⚠️ Per la rettifica questo **anticipa** un rifiuto che prima arrivava dalla
primitiva a metà ciclo (stesso codice, stessa frase, transazione comunque
annullata). È la simmetria con l'inventario, non una regola nuova.

---

### ⚠️ `SECURITY INVOKER`, e non risponde «si può» su ciò che non vede

Legge sotto la row security: un documento fuori perimetro **non c'è**, e solleva
`E_MAG_DOCUMENTO_NON_TROVATO` — lo stesso codice e la stessa frase della madre,
identici a quelli di un id inesistente (convenzione no-leak). ⛔ Rispondere `[]`
sarebbe *«si può registrare»* detto di una cosa che non si vede: un fail-open
silenzioso.

⇒ Per questo la **capability** guarda la testata **prima** di chiamarla: una
capability non solleva mai, e su un documento che non vede torna `NULL`.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` | `CONFLITTO_STATO` | motivo 1 — riusato, stessi valori di prima |
| `E_MAG_DOCUMENTO_SENZA_RIGHE` | `NON_ESEGUIBILE` | motivo 2 |
| *quello della riga* | — | motivo 3: il codice non lo sceglie questa funzione |
| `E_MAG_DOCUMENTO_NON_TROVATO` | `NON_TROVATO` | il documento non si legge |
| `E_MAG_CHIAMATA_NON_VALIDA` | `TECNICO` | famiglia diversa da `INVENTARIO`/`RETTIFICA`, o id nullo o `<= 0` |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio (salvo i
due guard di chiamata). Ritorna `[]` se l'azione è permessa, altrimenti un array
JSONB **ordinato** di `{codice, reason, reason_key, dettaglio, valori}` — chi
solleva prende il **primo**, con
`script.fn_raise_primo_motivo_se_presente`. ⛔ Il `reason` non porta il prefisso
`E_`.

⚠️ `p_documento_id` è un `bigint` e **non** un `%TYPE`, ed è voluto: la funzione
è parametrica su due tabelle, come il guard di famiglia. Il `%TYPE` di una delle
due direbbe una cosa falsa dell'altra.

Presidio: `db/pgtap/magazzino/test-capability-documenti-interni-v1.sql` (test
10-13), più i pgTAP delle due madri, che pinnano le frasi.

{% include-markdown "signature-core.md" %}
