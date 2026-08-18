# Brief DB — `riferimento` costa il 78% della lista gruppi, e non è colpa della ricerca

> **Tipo**: brief al team DB · **Data**: 2026-08-18 · **Richiedente**: perimetro
> BE · **Destinazione**: `dev/db-tid` · **Stato**: 🟡 da valutare — nessuna
> modifica applicata, nessun dato da bonificare
>
> **Origine**: DL-2 di
> [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md)
> §10. Doveva misurare **il costo della ricerca**; la misura ha trovato un costo
> **che la ricerca non c'entra** — si paga a ogni apertura della lista.
>
> ⚠️ **Il titolo è il punto**: `vendite.vw_dash_competenza_gruppi` risolve il
> documento sorgente **una volta per gruppo, a ogni interrogazione**, e quella
> risoluzione è il 78% del tempo. Chi legge il DL-2 pensando «ottimizziamo la
> ricerca» ottimizza il 22%.

---

## 1. La misura

`EXPLAIN (ANALYZE, BUFFERS)` sulla query reale del backend — CTE materializzata
compresa — eseguita come `zeroerp_app` con il contesto operatore
(`app.ruolo_applicativo = 'OPERATORE'`), **competenza giugno 2026, nessun
filtro, nessuna ricerca**.

| Nodo | Tempo | Buffer |
| --- | --- | --- |
| **Totale (45 righe)** | **166 ms** | 35.057 |
| Aggregato base — i 45 gruppi | 11 ms | 2.424 |
| **`LATERAL` documenti** — `loops=45` | **~130 ms** | **28.058** |
| ↳ di cui `Seq Scan on vendite.preventivi` — `loops=34` | **~105 ms** | **22.951** |

**78% del tempo, 80% dei buffer** per risolvere una colonna descrittiva.

⚠️ **45 righe.** Su un perimetro dove nulla dovrebbe essere misurabile.

## 2. La causa, dal piano

```text
Seq Scan on vendite.preventivi p_1  (actual time=1.672..3.088 rows=1.00 loops=34)
  Filter: (current_setting('app.ruolo_applicativo') = 'OPERATORE')
      AND script.fn_check_user_emittente_scope(..., p_1.emittente_fiscale_id)
      AND ((p_1.uid)::text = g_1.sorgente_uid)
      AND ...
  Rows Removed by Filter: 164
```

Per **ogni gruppo** si scandisce l'intera tabella, si scartano 164 righe e se ne
tiene 1. Trentaquattro volte.

⭐ **E il costo non è la scansione: è il predicato RLS su ogni riga scartata.**
`fn_check_user_emittente_scope` viene valutata su tutte e 165 le righe a ogni
giro — **~5.600 chiamate a funzione** per costruire una lista di 45 righe. È da
lì che vengono i 22.951 buffer.

### 2.1 L'indice che eviterebbe tutto questo esiste, e non viene usato

```sql
ix_preventivi_uid_text ON vendite.preventivi USING btree (((uid)::text))
```

Corrisponde **esattamente** al predicato. Con un index lookup si troverebbe
subito la riga giusta e la funzione RLS verrebbe chiamata **una volta invece di
165**.

Perché il planner non lo usi è la prima cosa da capire, ed è probabilmente
l'interazione fra la RLS e i quali dell'utente: con la RLS attiva le condizioni
non-leakproof non possono essere spinte sotto la barriera di sicurezza, e un
percorso parametrizzato può non essere nemmeno considerato. **È un'ipotesi, non
una diagnosi**: va verificata, e va verificata *con* la RLS attiva — un
`EXPLAIN` da owner mostrerebbe un piano che l'applicazione non esegue mai.

### 2.2 🔴 E l'indice c'è **solo** su preventivi

La `LATERAL` unisce **sei rami**. Ecco cosa hanno oggi:

| Ramo | Indice utile a `(uid)::text` |
| --- | --- |
| `preventivi` | ✅ `ix_preventivi_uid_text` — **esiste, ma non viene usato** |
| `ordini` | ❌ solo `uq_ordini_v_uid` su `uid` (uuid) |
| `contratti` | ❌ solo `uq_contratti_uid` su `uid` (uuid) |
| `ddt` | ❌ solo `uq_ddt_vendita_uid` su `uid` (uuid) |
| `offerte`, `commesse` | ❌ nessuno |

Un indice su `uid` (uuid) **non è utilizzabile** attraverso `(uid)::text`.

⚠️ **Conseguenza**: la misura di §1 è quella di un mese i cui gruppi sono
in prevalenza **preventivi**, cioè il ramo *meno* sfavorito — l'unico che un
indice ce l'ha. Su un mese a prevalenza **ordini** o **DDT** il costo è
plausibilmente peggiore. Il campione non è il caso peggiore: è quello fortunato.

### 2.3 L'origine è un'asimmetria di modello

```text
vendite.preventivi.uid            uuid
vendite.ordini.uid                uuid
vendite.commesse_attivita.sorgente_uid   text
```

Il cast `(uid)::text` non è una scelta di stile: è l'unico modo di confrontare
le due colonne. `ix_preventivi_uid_text` è la toppa che qualcuno ha già messo su
**un** ramo — segno che il problema era già stato incontrato, e risolto a metà.

## 3. Come scala

`loops=45` è il numero dei **gruppi del mese**, non delle righe mostrate.

```text
45 gruppi   →  166 ms
450 gruppi  →  ~1,3 s        (stima lineare sui loops)
```

⚠️ **La paginazione non contiene il costo**: la `LATERAL` gira per tutti i gruppi
del perimetro *prima* che si possa impaginare. E le facet, che interrogano lo
stesso perimetro, lo pagano una seconda volta.

## 4. Cosa si chiede

**Il «cosa», non il «come»**: la strada la decide il team DB.

> Che risolvere `riferimento` **non richieda una scansione per gruppo**.

Due direzioni, non alternative in linea di principio:

1. **Rendere utilizzabile l'indice** dove già esiste, e capire perché oggi non lo
   sia. È la correzione più economica e non tocca il modello. Se si sblocca, i
   105 ms del ramo preventivi crollano da soli;
2. **Togliere il cast**, allineando il tipo di `sorgente_uid` a quello degli
   `uid` — oppure aggiungendo l'indice funzionale ai **cinque rami che non ce
   l'hanno**. La prima è la cura, la seconda la toppa estesa.

⚠️ Qualunque strada, **deve valere per tutti e sei i rami**: sistemare i
preventivi lascerebbe il difetto intatto dove è più grave, e la prossima misura
sembrerebbe smentire questa.

## 5. Vincoli da rispettare

1. ⛔ **Nessun cambio a colonne, nomi o semantica** di
   `vw_dash_competenza_gruppi` e `vw_dash_fatturazione_documenti`: le leggono
   l'emissione mirata, l'export, la diagnostica e i cruscotti. Qui si chiede di
   cambiare **come** si risolve `riferimento`, non **cosa** contiene.
2. 🔴 **La grana non deve cambiare**: una riga per `(gruppo, stadio)`. Un
   fan-out moltiplicherebbe conteggio e totali, e il «seleziona tutto» manderebbe
   **doppioni a fatturare**. È già presidiato — `test-vw-dash-competenza-gruppi-cliente-v1`
   test 3 — e quel test va tenuto verde.
3. ⚠️ **`security_invoker=on` va ri-specificata** a ogni `CREATE OR REPLACE`:
   non compare in `pg_get_viewdef` e PostgreSQL la azzera in silenzio → bypass
   RLS.
4. **Nessun allentamento della RLS.** Il costo viene dalle chiamate al predicato
   di sicurezza, ma la soluzione è **chiamarlo meno volte** (una riga invece di
   165), non chiamarlo di meno in senso proprio.

## 6. Cosa NON si chiede

- **Non togliere `riferimento`**: è il dato che l'operatore legge per riconoscere
  il documento. Il problema è come si ottiene, non che ci sia;
- **nessuna materializzata** come primo tentativo: introduce freschezza da
  governare, e qui c'è un indice inutilizzato prima di arrivarci;
- nessun cambio al motore di fatturazione;
- nessuna modifica lato BE: la risoluzione avviene dentro la vista, e nessuna
  strategia di query del repository può aggirarla. *(Era stata valutata una
  «ricerca in due passi» lato backend: risolverebbe un decimo del problema, e
  solo quando si cerca.)*

## 7. Definizione di «fatto»

- [ ] la `LATERAL` dei documenti **non è più il nodo dominante** del piano, per
      tempo e per buffer;
- [ ] nessun `Seq Scan` con `Rows Removed by Filter` a tre cifre **per ogni
      loop** su una tabella di documenti;
- [ ] il miglioramento vale su **tutti e sei i rami**, non solo sui preventivi —
      verificato su un mese a prevalenza ordini/DDT, non solo su quello misurato
      qui;
- [ ] la grana resta `(gruppo, stadio)` e il conteggio righe non cambia
      (`test-vw-dash-competenza-gruppi-cliente-v1` test 3 verde);
- [ ] `security_invoker` ancora attiva (`test-vw-dash-security-invoker` verde);
- [ ] baseline `vendite` senza regressioni.

## 8. Come riprodurre la misura

⚠️ **L'errore facile**: eseguirla come owner. Le viste sono `security_invoker=on`
e sotto c'è la RLS; da owner il piano è diverso e i tempi non sono quelli
dell'applicazione. E con `app.ruolo_applicativo` vuoto la vista è **fail-closed**:
torna zero righe in 0,1 ms e sembra velocissima — il primo tentativo del
2026-08-17 è finito così.

```sql
SET ROLE zeroerp_app;
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', false),
       set_config('app.current_user_id',   '<auth_user_id>', false);
```

Poi la query del backend (CTE `righe AS MATERIALIZED` + `COUNT(*) OVER ()`,
`ORDER BY valore DESC NULLS LAST, gruppo_key ASC, stadio DESC`, `LIMIT 50`) con
`EXPLAIN (ANALYZE, BUFFERS)`. Seconda esecuzione, per non misurare la cache
fredda.

## 9. Riferimenti

| Cosa | Dove |
| --- | --- |
| Vista con la `LATERAL` | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi.md` |
| Union a sei rami dei documenti | `docs/it/dbzero/vendite/views/vw_dash_fatturazione_documenti.md` |
| DL-2 che ha generato la misura | [brief-db-dash-competenza-gruppi-cliente-e-ricerca.md](../work-done/brief-db-dash-competenza-gruppi-cliente-e-ricerca.md) §10 |
| Presidio anti-fan-out | `db/pgtap/vendite/test-vw-dash-competenza-gruppi-cliente-v1.sql` test 3 |
