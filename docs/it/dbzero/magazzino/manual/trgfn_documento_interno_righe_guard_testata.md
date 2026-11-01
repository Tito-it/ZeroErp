## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_documento_interno_righe_guard_testata`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe) — dove è montato
> * [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — dove è montato
> * [magazzino.trasferimenti_righe](/dbzero/magazzino/tabelle/trasferimenti_righe) — dove è montato
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — il gemello sulla testata
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — «chi scrive è un verbo»

---

### 🎯 Scopo Principale

**Le righe dei documenti interni di magazzino seguono lo stato della testata.** Una funzione
per le tre famiglie (inventari, rettifiche, trasferimenti): ogni tabella di righe le passa il
nome della testata, della colonna che la collega, della colonna di stato e dell'impostazione di
registrazione. È montata prima di ogni inserimento, aggiornamento e cancellazione di riga.

---

### Che cosa si può fare, stato per stato

| Testata in… | Le righe… |
| --- | --- |
| `DRAFT` | si scrivono |
| `CONFIRM` | le scrive **solo l'operazione**: la stessa impostazione di registrazione della porta `POSTED` (è lei a fissare `qta_sistema` sull'inventario) **e** chi esegue dev'essere il proprietario, cioè un verbo ([script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella)): l'impostazione l'applicazione può accenderla da sola |
| `POSTED`, `CANCEL` | sono congelate |

Un aggiornamento che sposta una riga su un'altra testata controlla entrambe.

---

### ⭐ Testata assente = passa

Succede in due casi soli: la cascata di una cancellazione della testata (che il guard gemello
ha già ammesso solo in `DRAFT`) e una testata fuori perimetro (che sotto la sicurezza di riga
una riga non raggiunge comunque). Fermarsi qui bloccherebbe la cancellazione legittima di una
bozza.

---

### Codici errore

* `E_MAG_DOCUMENTO_RIGHE_CONGELATE` — scrittura di una riga con la testata non in bozza, fuori
  dall'operazione; la frase nomina lo stato.

---

### Test

`db/pgtap/magazzino/test-documenti-interni-guard-v1.sql` (test 8-13).

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§3 D-L2-h).
* 2026-09-25 — `brief-db-magazzino-verbi-con-permesso` (D-V1): in `CONFIRM` chiede anche che a
  scrivere sia il proprietario. Prima bastava l'impostazione di registrazione.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
