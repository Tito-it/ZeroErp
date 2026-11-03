## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_require_by_args`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — l'unico chiamante, per la strategia di esistenza della regola
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la funzione del trigger che cerca
> * [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args) — la gemella per il block sul padre
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — il controllo per nome, l'altra metà della strategia
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — la lettura degli argomenti che altri lettori usano
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Dice se sulla tabella figlia c'è già un trigger *require* della regola ATTIVO
(`dbops.trgfn_child_requires_active_parent`) con **esattamente** gli argomenti attesi: schema e
tabella del padre, colonna attivo del padre, colonna FK, colonna referenziata.

Serve a `dbops.fn_run_automations_attivo` quando la regola riconosce i trigger per funzione
(`BY_FUNCTION`, o `BOTH` insieme al nome).

---

### ⚠️ Oggi non riconosce nessun trigger

Il confronto si fa sul testo della definizione del trigger (`pg_get_triggerdef`), cercando la
chiamata con gli argomenti separati da una **virgola senza spazio**. PostgreSQL scrive la
definizione con gli argomenti separati da **virgola e spazio**: il testo cercato non compare mai,
e la funzione restituisce sempre falso.

Conseguenze sul motore: con la strategia `BOTH` (quella del seed) decide solo il nome; con
`BY_FUNCTION` ogni giro toglierebbe e ricreerebbe il trigger.

Il confronto è anche `ILIKE`: il trattino basso dei nomi vale come carattere qualsiasi.

---

### Che cosa non fa

Non guarda il nome né gli eventi del trigger, né che sia un constraint trigger differito: solo
funzione e argomenti. È `STABLE` e non tocca niente.

---

{% include-markdown "signature-core.md" %}
