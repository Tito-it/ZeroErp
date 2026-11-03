## 📘 Documentazione Concettuale – Funzione `dbops.fn_fix_triggers_event_tokens`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fix_triggers_events_noorder](/dbzero/dbops/funzioni/fn_fix_triggers_events_noorder) — la versione che il repository crea ed esegue
> * [dbops.fn_rename_triggers_by_order](/dbzero/dbops/funzioni/fn_rename_triggers_by_order) — la rinomina per fase, da cui questa copia la composizione del nome
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger#il-nome-del-trigger) — la regola dei nomi di oggi

---

### 🎯 Scopo Principale

Utility **una tantum** della campagna di rinomina dei trigger del settembre 2025, mai usata:
doveva riscrivere gli eventi nel nome dei trigger, con una fase di ripiego per i nomi che non ne
hanno una. È una **candidata al ritiro**.

⚠️ **Nessun changeSet del repository la crea.** Il file del primo albero che ne porta il nome
crea `dbops.fn_fix_triggers_events_noorder`. Questa funzione esiste sul database da cui è
generata la documentazione, non su un database costruito da zero né in CI.

---

### ⛔ Non funziona: il controllo d'ingresso rifiuta ogni fase

Il parametro della fase di ripiego vale `a10` di default, e il messaggio d'errore chiede una
fase nella forma `aNN` o `zNN`. Il controllo però accetta **solo** `ins`, `upd` e `dlt`. Così
la chiamata col default, o con una fase vera, solleva sempre l'errore. Con `ins`, `upd` o `dlt`
passa, e quel valore finisce nel nome al posto della fase.

L'errore è un `RAISE EXCEPTION` senza codice di progetto, fuori dal contratto di
`script.fn_log_and_raise_error`.

---

### Che cosa farebbe

Se il controllo la lasciasse passare, la funzione prenderebbe i trigger utente il cui nome
comincia con `trg_ins`, `trg_upd`, `trg_del` o `trg_dlt`, oppure con `trg_` senza un evento nel
nome, in tutti gli schemi tranne `public` e `topology`. Poi li rinominerebbe in
`trg_<tabella>_<fase>_<eventi>[_of_<colonna>][_aft]_<scopo>`, con un suffisso numerico in caso
di collisione, troncando a 63 caratteri, in anteprima (il default) o eseguendo. Valgono le
stesse ragioni per non rilanciarla di `fn_fix_triggers_events_noorder`.

---

{% include-markdown "signature-core.md" %}
