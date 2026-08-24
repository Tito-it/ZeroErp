## 📘 Documentazione Concettuale – Funzione `script.fn_check_commessa_pronta_fatturazione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
Approfondimento funzioni:
> • [script.fn_check_commessa_chiudibile](/dbzero/script/funzioni/fn_check_commessa_chiudibile)
> • [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Elenca i motivi che impediscono a una commessa di dichiararsi **`PRONTA_FATTURAZIONE`**.
Due motivi, e non si escludono: possono comparire entrambi.

---

### ⭐ Le condizioni sono quelle della **lane**, non un criterio a parte

Il MOTIVO 1 conta le righe con `APPROVATA` + `NON_EMESSA` + `tipo_doc_fiscale_id IS NOT NULL`:
sono esattamente le tre condizioni di `fn_list_emittibili_lane`.

La ragione è precisa: **dichiarare pronta una commessa che la lane non raccoglierebbe
significa promettere un lavoro che non partirà**. La commessa resterebbe in attesa di un
motore che non la vede, senza errori e senza spiegazioni.

Il MOTIVO 2 guarda `emittente_soggetto_ruolo_id` sulla testata: fa parte della **chiave di
raggruppamento** della lane, e senza di esso il raggruppamento non diventa nessuna fattura.

⚠️ È il motivo per cui questa funzione va riletta ogni volta che cambiano le condizioni della
lane: se le due si separano, la commessa può diventare «pronta» per qualcosa che non accadrà.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_NESSUNA_RIGA_APPROVATA` | Nessuna riga soddisfa le tre condizioni della lane |
| `E_COMMESSA_EMITTENTE_MANCANTE` | Testata senza `emittente_soggetto_ruolo_id` |
| `E_PARAMETRO_INVALIDO` | `commessa_id` nullo o non positivo |

⚠️ Il MOTIVO 2 scatta solo se la commessa **esiste** (`v_trovata`): su un id inesistente
compare il solo MOTIVO 1, perché il conteggio è zero. Distinguere «commessa vuota» da
«commessa inesistente» è compito del chiamante.

---

### Il pattern `fn_check_*` — vale per tutte e cinque

**Funzione pura**: `STABLE`, nessuna scrittura, **nessun raise di dominio**. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}`.

L'ordine è quello di **gravità**: chi solleva prende il **primo**.

⭐ **Sorgente unica per due consumatori diversi.** La stessa funzione è letta da:

* il **guard di transizione**, che solleva il codice del primo motivo;
* `fn_available_actions_*`, che espone l'azione come `disabled` con i suoi `reasons`.

È ciò che rende impossibile la divergenza classica fra UI e database — il bottone acceso su
un'azione che il DB rifiuta. Non è disciplina, è struttura: c'è un solo posto da cambiare.

`reason_key` è la chiave i18n per il frontend; `dettaglio` porta il conteggio, così il
messaggio può dire *quanti*.

⚠️ **Il guard sui parametri è l'unica eccezione alla purezza**: `id` nullo o `<= 0` solleva
`E_PARAMETRO_INVALIDO`. È un errore di programmazione, non una condizione di dominio, e va
detto invece di essere normalizzato in silenzio.

---

{% include-markdown "signature-core.md" %}
