## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_scadenze_lotto`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) · [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) · [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)
>
> **Funzioni:**
>
> • [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura) — il generatore per fattura, invocato qui
> • [vendite.fn_snapshot_fattura_lotto](/dbzero/vendite/funzioni/fn_snapshot_fattura_lotto) — il **modello** di questo wrapper

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`vendite.fn_genera_scadenze_lotto(p_lotto_id, p_batch_size)` applica il generatore
del piano rate a **tutte le fatture di un lotto**. È il task
`genera_scadenze_lotto` dello step **EMESSA**, in coda a `ricalcola_iva_lotto`.

Restituisce **sei contatori**:

| Contatore | Significato |
|---|---|
| `fatture_count` | fatture esaminate |
| `deleted_rows` / `inserted_rows` | rate cancellate e scritte |
| `skipped_rows` | fatture **oltre la soglia** DRAFT/EMESSA |
| `skipped_errore_rows` | fatture con un critico attivo **di un altro task** |
| `failed_rows` | fatture su cui il generatore ha sollevato |

---

### 🔴 I due `skipped` sono due cose diverse e vanno mostrati diversi

`skipped_rows` = documenti **chiusi**: non hanno lavoro da fare, il loro piano
rate è già quello definitivo.
`skipped_errore_rows` = documenti **rotti** a monte, che uno step a valle non deve
riprovare.

Un contatore unico direbbe «cinque saltate» senza distinguere cinque fatture a
posto da cinque da guardare — che per chi legge il cockpit sono **l'opposto**.
Da qui la scelta di tenerli separati fino all'interfaccia.

---

### 🛟 Il fallimento di UNA non uccide il giro

Ogni fattura è lavorata in un sotto-blocco `BEGIN/EXCEPTION`: se il generatore
solleva, la fattura viene marcata `'C'` su `fatture_log` — che è ciò che le
impedisce di diventare EMESSA — e **le altre proseguono**.

Così i documenti problematici si vedono **tutti in una volta**, invece di uno per
esecuzione.

Si cattura `raise_exception` (P0001), **non** `others`: un guasto di sistema deve
continuare a salire.

---

### ♻️ Il rilancio dello stesso step ripara

Al successo il task **ritira le proprie** segnalazioni critiche sulla fattura.
Quelle di un altro task restano: chi le ha alzate sa quando abbassarle.

È la via d'uscita prevista dal modello — non «annulla il lotto», ma «rilancia lo
stesso step».

---

### ⚠️ La trappola che ha corretto il piano: NON filtrare su `stato_esecuzione`

Il piano prescriveva di saltare le fatture con `stato_esecuzione = 'ERRORE'`.
**Crea uno stallo**, e collaudando è venuto fuori perché.

Quella colonna non dice «rotta a monte»: dice «esiste un log critico attivo», **di
qualunque task** (`fn_resolve_stato_esecuzione` la deriva da `has_critical`).
Quindi lo step che marca una fattura **la esclude da sé stesso per sempre**: la
sua bandiera non può più essere abbassata da chi l'ha alzata, e il rilancio —
l'unica via d'uscita — smette di funzionare.

Il criterio corretto guarda **di chi è** la segnalazione: si salta se c'è un
critico attivo di un **altro** task (`meta->>'task'` diverso dal proprio), le
proprie si riprovano.

> Un critico **senza** `meta->>'task'` conta come altrui: una bandiera che non
> sappiamo chi abbia alzato non è nostra da abbassare.

⚠️ **Due stesure del pgTAP passavano anche col filtro sbagliato** — davano
fiducia falsa, perché lo scenario dello stallo non si formava. La catena vera,
misurata: il log critico porta subito `fatture.critical = true`, ma
`stato_esecuzione` resta **PENDING** finché il runner non risincronizza; e
**nessuna** delle due funzioni di sync serve a forzarlo in un test —
`fn_sync_fatture_log_critical_lotto` allinea il flag e non lo stato di esecuzione,
mentre `fn_sync_lotto_fatture_stato` **non è un ricalcolo**: porta le fatture allo
stato fiscale del *lotto* e in una fixture sbatte contro il guard delle
transizioni. Nel test la condizione si scrive **a mano**.

---

### Ordine nella pipeline

Il task va **dopo** `ricalcola_iva_lotto`: la base di ripartizione è
`totale_a_pagare`, che prima non esiste. Invertirli farebbe sollevare
`E_SCADENZE_BASE_NON_PRONTA` su **ogni** fattura — un giro interamente rosso che
sembra un difetto dei dati mentre è una riga di configurazione girata.

L'ordine è sorvegliato **due volte**, e non è un doppione: `_TASK_ORDER_DEPENDENCIES`
nel backend guarda la configurazione **letta** a runtime, il pgTAP
`test-pipeline-processi-invariante-v1` guarda il **seed** che quella
configurazione la produce. Il primo protegge un giro già avviato, il secondo
impedisce alla config sbagliata di nascere.

---
{% include-markdown "signature-core.md" %}
