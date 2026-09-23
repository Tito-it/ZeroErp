## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_documento_interno()`

> 👀 **Vedi anche**
>
> **I due involucri, che sono ciò che il backend chiama:**
>
> • [script.fn_available_actions_inventario](/dbzero/script/funzioni/fn_available_actions_inventario)
> • [script.fn_available_actions_rettifica](/dbzero/script/funzioni/fn_available_actions_rettifica)
>
> **Da dove prende le sue risposte** — non decide niente da sola:
>
> • [magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni) — quali azioni esistono da questo stato
> • [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile) — se «Registra» è acceso, e se no perché
>
> **Le sorelle:** le otto `fn_available_actions_*` di `vendite` · **la regola:** [linee-guida-sql §12](/linee-guida-sql)
>
> **Piano:** [brief-db-magazzino-lotto-2-bis-be-fe](/dev/work-in-progress/brief-db-magazzino-lotto-2-bis-be-fe) R-1

---

### 🎯 Scopo Principale
(scritta il 22-09-2026)

La capability di un documento interno di magazzino — inventario o rettifica —
per il dettaglio API: **quali azioni proporre, quali spegnere e perché, che cosa
si può ancora modificare**. È ciò che il drawer legge per disegnare la barra dei
pulsanti, senza sapere niente delle regole che ci stanno dietro.

---

### Il blob

| Chiave | Che cosa dice |
| --- | --- |
| `stato_codice` | lo stato corrente |
| `available_actions[]` | una voce per **transizione richiedibile**: `key` (`conferma` · `riapri` · `annulla`), `target_state`, `label_key`, `icon`, `severity`, `requires_confirm`, `enabled`, `reason`, `reason_key`, `manuale` |
| `can_change_state` | c'è almeno un'azione — **anche spenta**: la barra deve comparire proprio per mostrare il pulsante grigio col suo motivo (§12.2 punto 2) |
| `can_edit_testata`, `can_edit_righe`, `can_delete` | lo stato è `DRAFT` — lo **stesso** predicato dei guard che rifiuterebbero |
| `can_registra`, `can_registra_reason`, `can_registra_reason_key` | la terna del verbo irreversibile |
| `stato_info_key` | sugli stati chiusi, la nota che dice che cosa è successo e qual è la strada (`POSTED`, `CANCEL`); `NULL` altrove |

Chiavi i18n emesse — e sono un **debito verso il frontend**, presidiato da
`scripts/check_i18n_keys.py`:

* `magazzino.documenti_interni.azione.{conferma, riapri, annulla}`
* `magazzino.documenti_interni.registra_reason.{non_confermato, gia_registrato,
  annullato, senza_righe, righe_non_postabili}` (le emette la check)
* `magazzino.documenti_interni.stato_info.{posted, cancel}`

---

### ⭐ Non contiene nessuna regola, ed è il suo pregio

Le azioni vengono dalla **matrice** che il guard fa rispettare; la terna di
«Registra» dal **primo motivo** della check che le madri del posting sollevano.
Questa funzione compone, non decide.

> Un pulsante non può promettere ciò che il database rifiuterà. Non perché
> qualcuno tenga allineate due copie: perché la copia è una sola.

È la *terza via* che linee-guida-sql §12.1 vieta — l'azione accesa su qualcosa
che il guard rifiuterà, l'operatore che scopre il vincolo sbagliando — resa
impossibile per costruzione invece che per disciplina.

---

### ⚠️ `POSTED` non è un pulsante

La matrice ammette `CONFIRM → POSTED`, ma quella porta la apre **solo**
l'operazione di registrazione, firmandosi con la sua GUC transazionale: un
bottone «porta a POSTED» prenderebbe `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`.
Perciò `POSTED` esce dalle `available_actions` e rientra come terna
`can_registra` — il verbo irreversibile, che il backend espone su
`.../registra/` con l'azione di processo `registra_magazzino`.

---

### ⚠️ Fuori perimetro: `NULL`, non una capability vuota

`SECURITY INVOKER`: se la testata non si legge — inesistente, o di un altro
emittente — la funzione torna `NULL`, e il **404 lo dà il backend** sulla
testata. È lo stampo delle otto capability di `vendite`.

⭐ Ed è il motivo per cui la testata si guarda **prima** di chiamare la check:
la check su un documento non visibile *solleva*, e una capability non solleva
mai.

---

### Un corpo e due involucri

La regola è la stessa per le due famiglie (D-L2-h: una matrice, un guard, una
check). Due corpi gemelli sarebbero stati due posti dove cambiarla — il difetto
che questo giro viene a chiudere. Gli involucri esistono perché il backend chiama
per **entità** (`fn_available_actions_<entità>`, come negli altri otto domini) e
perché il giorno in cui una delle due avesse una chiave in più si sdoppia
l'involucro, non la regola.

Presidio: `db/pgtap/magazzino/test-capability-documenti-interni-v1.sql` (14
asserzioni; il test 3 confronta la matrice con ciò che il guard lascia
davvero passare).

{% include-markdown "signature-core.md" %}
