## 📘 Documentazione Concettuale – Funzione `vendite.fn_af_merce_per_riga(p_segment_keys)`

> 👀 **Vedi anche**
>
> [vendite.vw_af_merce_per_riga](/dbzero/vendite/views/vw_af_merce_per_riga) — la stessa cosa, senza filtro
> [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la chiama con le chiavi della chiusura
> [vendite.fn_situazione_merce_ordine](/dbzero/vendite/funzioni/fn_situazione_merce_ordine) — la chiama con le chiavi delle righe in uscita
> [script.fn_get_stato_push_segment](/dbzero/script/funzioni/fn_get_stato_push_segment) — lo stesso range, per una chiave sola
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la tabella e l'indice `ix_commesse_attivita_segment_key`
> Brief: `docs/it/dev/work-in-progress/brief-db-partita-merce-per-documento.md` §11 (giro 4, D5)

---
### 🎯 Scopo Principale

È il **contatore delle attività fatturabili per riga di documento** — la stessa
domanda di `vw_af_merce_per_riga` (*«di questa riga, quanti pezzi sono entrati
nella corsia di fatturazione?»*) — che risponde **solo per le righe che le si
chiedono**. La vista ne è la proiezione senza filtro: `fn_af_merce_per_riga(NULL)`.
Un corpo solo.

Esiste perché, dopo la chiusura della partita per documento, il contatore era
l'unico pezzo del conto ancora letto **intero** anche chiedendo un solo DDT. E
non è un pezzo qualsiasi: cresce con le **fatture**, che non si svuotano mai.
Ogni lettura di una partita pagava tutta la storia della fatturazione.

---

### Il seme: chiavi di segmento, senza suffisso

Si passano le **chiavi di segmento** delle righe di documento, come le
compongono il push e la chiusura:

```text
DDT:<uid del DDT>:R:<id riga di DDT>
ORD:<uid dell'ordine>:R:<id riga d'ordine>
```

Di ciascuna chiave entrano nel conto la chiave **esatta** e tutte le chiavi che
ne portano un **suffisso**: la rettifica (`#RET:<n>`), il componente di kit
(`#CMP:<id>`), anche combinati (`#RET:1#CMP:<id>`). La regola è una sola: *la
base di una chiave è ciò che precede il primo `#`* — la stessa con cui il conto
ricava `riga_id` e l'istanza di kit.

| Argomento | Risposta |
|---|---|
| `NULL` | tutte le righe: la vista |
| array vuoto `'{}'` | zero righe — vuoto **non** è «tutte» |
| chiavi | il conto delle sole righe di quelle chiavi |

⚠️ Le chiavi sono **normalizzate**: la funzione ne prende la base e le rende
distinte. Una chiave ripetuta, o passata con il suffisso accanto alla sua base,
**non raddoppia** la somma — è successo davvero, provando con le chiavi vive
passate tutte insieme, ed è il test 11 del presidio.

---

### ⛔ La forma del predicato, e perché non è stile

`commesse_attivita` è sotto RLS: ogni lettura passa dalla policy. E sotto una
policy PostgreSQL mette in un indice **solo le clausole di cui si fida** — quelle
i cui operatori sono dichiarati *leakproof* — perché una clausola valutata
prima della policy potrebbe far trapelare, da un errore o da un tempo, righe
che l'operatore non deve vedere.

Il modo naturale di dire «la chiave e i suoi suffissi» è un `LIKE 'k#%'`. Ma
`LIKE` **non è leakproof**: sotto una policy non diventa mai una condizione
d'indice, nemmeno con una costante, e la lettura torna a essere la tabella
intera con la policy valutata riga per riga. Senza policy il planner lo riscrive
in un range e usa l'indice — è per questo che la prova «da owner» mente.

La forma che regge è il **range scritto a mano** con gli operatori del pattern,
che confrontano i byte e sono leakproof:

```text
segment_key = k
OR (segment_key ~>=~ k || '#'  AND  segment_key ~<~ k || '$')
```

`$` è il byte che segue `#`: l'intervallo `[k#, k$)` è **esattamente** «comincia
per `k#`». E `:R:1` non prende `:R:12`, perché la cifra `2` viene dopo `$` — è il
caso costruito dal presidio (test 6). Tre condizioni perché il planner la usi
davvero, tutte provate come applicazione sotto una policy:

* i due bordi (`k || '#'`, `k || '$'`) stanno in una CTE `MATERIALIZED`, come
  colonne — scritti dentro la clausola di join sarebbero una concatenazione, che
  non è leakproof, e la clausola non salirebbe più;
* l'`OR` contiene **solo** operatori leakproof: un `OR` con dentro una funzione
  qualsiasi spegne i percorsi indicizzati per intero;
* l'indice sulla colonna ha l'opclass dei pattern (`varchar_pattern_ops`): con la
  collation `it_IT` del database un btree ordinario non conosce `~>=~`.

> ⚠️ **La prova con il piano generico forzato è pessimista qui.** Con un array
> parametro il planner stima 100 chiavi e, per un range a bordi variabili, lo
> 0,5 % della tabella per chiave: preferisce una scansione. Nella forma in cui la
> funzione viene chiamata davvero — con il seme calcolato, cioè dalla plancache —
> PostgreSQL confronta il piano generico con la media dei piani custom e **tiene
> i custom** finché il generico costa di più (10 chiamate: ~0,4 ms l'una;
> forzando il generico 17 ms). Non è un'ipotesi: è il meccanismo documentato
> della plancache, e cresce a favore dell'indice con la tabella.

---

### Chi la chiama

| Lettore | Chiavi |
|---|---|
| `vw_af_merce_per_riga` | `NULL` — tutte |
| `fn_partite_merce` (giro 4) | `DDT:…` per ogni riga di O (origini di ri-consegna comprese); `ORD:…` per ogni riga d'ordine dei fulfillment della chiusura |
| `fn_situazione_merce_ordine` (giro 4) | `ORD:…` per ogni riga d'ordine in uscita |

In entrambe il ramo «tutte» chiama `fn_af_merce_per_riga(NULL)` col letterale,
che il planner **inlina** (le stesse scansioni della vista di prima); il ramo
ristretto passa il seme calcolato, che resta una chiamata (`Function Scan`) con
il piano nella plancache.

---

### Esempio d'uso

```sql
-- Il conto di una riga di DDT, con le sue rettifiche e i suoi componenti.
SELECT corsia, riga_id, tipo_movimento, quantita, misurabile
  FROM vendite.fn_af_merce_per_riga(ARRAY['DDT:0f3c…:R:17163']::varchar[]);

-- Le chiavi le compone chi ha in mano riga e documento:
SELECT ('DDT:' || d.uid::text || ':R:' || dr.id::text)::varchar
  FROM vendite.ddt_righe dr JOIN vendite.ddt d ON d.id = dr.ddt_id
 WHERE dr.ddt_id = 131;
```

---

### Note operative

* `BEGIN ATOMIC`: le dipendenze stanno in `pg_depend` — una rinomina a monte
  viene rifiutata, e la catena vista → funzione → tabelle con RLS resta leggibile
  dal presidio delle viste `security_invoker`.
* `SECURITY INVOKER`: la RLS resta di chi legge. Chi non vede la commessa non
  vede il conto (zero righe, non conti a zero).
* Il `RETURNS TABLE` perde il typmod di `tipo_movimento` (`varchar(32)`): la
  vista lo ricasta per nome, e il presidio pinna i tipi.
* ⛔ **Niente `LIKE` qui dentro**, per il motivo scritto sopra. Se il predicato
  cambia forma, il piano come applicazione va riletto.
* Presidio: `db/pgtap/vendite/test-fn-af-merce-per-riga-chiusura-v1.sql` — casi
  costruiti: chiave semplice con rettifica, il vicino numerico, kit, le due
  corsie con lo stesso numero, suffisso ignoto, duplicati, vuoto, scope; e i
  pin di forma (proiezione, tipi, opclass dell'indice).

---

{% include-markdown "signature-core.md" %}
