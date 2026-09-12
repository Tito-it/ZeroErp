## 📘 Documentazione Concettuale – Funzione `vendite.fn_classe_emittibilita_per_giro`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[vendite.vw_commesse_attivita_emittibilita](/dbzero/vendite/manual/vw_commesse_attivita_emittibilita) ·
[vendite.vw_documenti_trattenuti_da_lotto](/dbzero/vendite/manual/vw_documenti_trattenuti_da_lotto)
>
Approfondimenti funzioni:
>
[vendite.fn_lotto_da_emit_batch](/dbzero/vendite/manual/fn_lotto_da_emit_batch) ·
[vendite.fn_list_commesse_emittibili](/dbzero/vendite/manual/fn_list_commesse_emittibili) ·
[vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(latest review 12-09-2026)

Risponde a una domanda che la vista delle classi **non può** fare: *«questa riga,
per il giro che la sta chiedendo, si può prendere?»*.

La **classe** di una riga (`PRONTA`, `TRATTENUTA`, `NON_APPROVATA`…) è una
proprietà della riga e vive nella vista
`vw_commesse_attivita_emittibilita`, che giustamente non sa chi chiede. Ma
**«trattenuta»** dipende da chi guarda: una riga trattenuta da un **altro**
lotto in gioco è fuori; una riga trattenuta **soltanto dal mio** lotto è il mio
documento di un tentativo precedente, e al rilancio va ripresa. Questa funzione
restituisce la classe **vista dal giro**: `TRATTENUTA` soltanto dal lotto
corrente diventa `PRONTA`; ogni altra classe torna com'è.

> ⭐ **È la sede unica dell'auto-esclusione del proprio lotto.** Fino al
> 12-09-2026 quella regola stava scritta nell'emit e **mancava** nella discovery:
> al rilancio di un pull fallito la discovery scartava le proprie commesse, il
> pull visitava zero commesse e il lotto usciva `COMPLETATO` senza aver emesso
> niente. Due copie di una regola si sfilano; una sede no.

---

### La regola, e le sue tre righe

| Ingresso | Uscita | Perché |
| --- | --- | --- |
| `TRATTENUTA`, tenuta **solo** dal lotto corrente | `PRONTA` | è il mio documento, da riprendere |
| `TRATTENUTA`, tenuta dal mio lotto **e** da un altro in gioco | `TRATTENUTA` | `<@` e non `= ANY`: si libera solo se **tutti** quelli che la tengono sono il mio |
| `TRATTENUTA`, lotto corrente `NULL` | `TRATTENUTA` | chiamante fuori pipeline (backfill, riconciliazione): nessuna auto-esclusione, la risposta prudente |
| qualunque altra classe | **invariata** | `PRONTA`, `NON_APPROVATA`, `RIFIUTATA`, `EMESSA`, `ANNULLATA` non dipendono da chi chiede |

⚠️ **«Per il mio giro è PRONTA» poggia sull'ordine del `CASE` della vista**:
`RIFIUTATA` e `NON_APPROVATA` vengono **prima** di `TRATTENUTA`, quindi una riga
trattenuta è per costruzione approvata e non emessa. Se la vista cambiasse
ordine, questa funzione promuoverebbe a `PRONTA` una riga non approvata: il test
10 di `db/pgtap/vendite/test-pull-non-prende-trattenuti-v1.sql` lo asserisce su
un caso costruito (una riga in `BOZZA` tenuta da un lotto → `NON_APPROVATA`).

---

### Chi la chiama, e con che cosa sopra

I due cancelli del pull la leggono entrambi, e **ognuno tiene la propria
whitelist** — non sono uguali, e non devono diventarlo:

| Cancello | Whitelist sopra la classe vista dal giro |
| --- | --- |
| `fn_list_commesse_emittibili` (quali **commesse** visitare) | `PRONTA`, `RIFIUTATA`, `NON_APPROVATA` — sempre |
| `fn_emit_attivita_fatturabili_da_commessa` (quali **righe** emettere) | `PRONTA`; `NON_APPROVATA`/`RIFIUTATA` solo con `p_only_approved = false` |

Il lotto corrente lo risolvono da `p_emit_batch_id` con
[fn_lotto_da_emit_batch](/dbzero/vendite/manual/fn_lotto_da_emit_batch).

---

### Perché è `LANGUAGE sql IMMUTABLE`

Perché il planner la **inlina**: nel piano della discovery non compare nessuna
chiamata di funzione, il `CASE` è espanso dentro la query. Una sede unica che
costasse una chiamata per riga sarebbe stata un argomento contro la sede unica;
così è gratis. ⛔ Niente `STRICT`: bloccherebbe l'inlining, e un `NULL` in
ingresso ha già la sua risposta nel `CASE`.

---

### Esempio d'uso

```sql
-- Le righe della commessa 34137 come le vede il lotto 13338
SELECT e.commessa_attivita_id, e.classe_emittibilita,
       vendite.fn_classe_emittibilita_per_giro(e.classe_emittibilita, e.trattenuta_da_lotti, 13338) AS per_il_giro
  FROM vendite.vw_commesse_attivita_emittibilita e
 WHERE e.commessa_id = 34137;
```

Origine: `docs/it/dev/work-in-progress/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md` (D1);
changeSet `20260912-12`.

---

{% include-markdown "signature-core.md" %}
