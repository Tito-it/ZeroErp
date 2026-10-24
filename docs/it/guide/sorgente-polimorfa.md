# Sorgente polimorfa — l'aggancio universale ai documenti

> **Ultimo aggiornamento**: 19 settembre 2026
>
> **Destinatari**: sviluppatori database e backend, analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il dizionario: per ogni tipo agganciabile la `target_table` e la `key_selector`
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — lo stato del documento agganciato, in un vocabolario comune
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — i collegamenti il cui bersaglio è stato cancellato; **deve restare vuota**
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.trgfn_guard_sorgente_polimorfa_testuale](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_testuale) — il guard del modello a chiave unica testuale
> * [script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata) — il guard del modello a colonne tipizzate
> * [script.fn_get_sorgente_emittente_sr_id](/dbzero/script/funzioni/fn_get_sorgente_emittente_sr_id) — chi emette il documento agganciato
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — normalizza la chiave in scrittura
>
> **Vedi anche** — guide correlate:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — dove è iscritto il presidio degli orfani

---

## 1. Il problema che risolve

Molte tabelle devono puntare a «un documento»: **note**, **log**, **attività
fatturabili**, **pratiche**, **commesse**… Ma quel documento può essere di **tipo
diverso** e vivere in **tabelle diverse**. Avere un collegamento fisso per ogni tipo
(una colonna per preventivo, una per ordine, una per DDT…) sarebbe ingestibile.

La soluzione è un **aggancio universale**: invece del tunnel dedicato, si memorizza
**tipo + identificatore**, e un dizionario centrale sa dove e come trovare il bersaglio.

## 2. Come funziona — tre pezzi

1. **Il dizionario** — `config.sorgenti`. Elenca i tipi ammessi; per ognuno dice:
   * `target_table` = in quale tabella cercare (es. `ORDINE_VENDITA` → `vendite.ordini`);
   * `key_selector` = con quale chiave cercare, **`id`** o **`uid`**.
2. **Le colonne di aggancio** sulla tabella che collega:
   * `sorgente_tipo_id` = *che tipo è* (FK a `config.sorgenti`);
   * `sorgente_uid` = *quale in particolare* (il valore che identifica la riga).
3. **Il guard** — apre il dizionario, controlla che la chiave sia **nel formato giusto**
   per il `key_selector`, va nella `target_table` giusta e verifica che **quel documento
   esista davvero**; altrimenti **blocca**. Esiste in **due modelli**, corrispondenti ai
   due modi di scrivere l'aggancio:
   * `script.trgfn_guard_sorgente_polimorfa_testuale` — **modello B**: una sola colonna
     `sorgente_uid` di tipo TEXT, che porta la chiave canonica (`id::text` o `uid::text`).
     È il modello di `pratiche.pratiche_sorgenti` e `vendite.commesse_sorgenti`.
   * `script.trgfn_guard_sorgente_polimorfa_tipizzata` — **modello A**: due colonne
     tipizzate, `sorgente_riga` BIGINT per i tipi a chiave `id` e `sorgente_uid` UUID per
     quelli a chiave `uid`. È il modello delle tabelle di magazzino.

   Quali agganci sono oggi vivi **non si legge qui**: lo dice il database (§5).
   In più, `vendite.fn_link_commessa_sorgente` **normalizza** la chiave alla
   scrittura (traduce l'uuid in `id::text` per i tipi a chiave `id`): i chiamanti
   storici continuano a funzionare e scrivono canonico.

> ⚠️ **Il guard chiude la porta in ingresso, non sorveglia l'uscita.** Verifica che il
> bersaglio esista **quando si scrive il collegamento**: se poi qualcuno cancella il
> documento bersaglio, il collegamento resta orfano e il guard non c'entra più. A
> trovarli, **dopo**, c'è un presidio apposito (vedi sotto).
>
> Analogia: un **adattatore universale**. Non serve una presa diversa per ogni Paese:
> basta l'adattatore + l'indicazione di quale spina usare (`key_selector`).

## 2a. Le quattro domande che il meccanismo sa fare

Un aggancio universale serve a poco se poi, del documento agganciato, non si sa
niente. Oggi il meccanismo risponde a **quattro** domande, e ognuna ha un pezzo suo:

| Domanda                              | Chi risponde                                                                                                                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **esiste?** (al momento di scrivere) | `script.trgfn_guard_sorgente_polimorfa_testuale` / `_tipizzata` — bloccano l'aggancio a un documento che non c'è                                                              |
| **è rimasto orfano?** (dopo)         | [`dbops.vw_sorgenti_orfane`](/dbzero/dbops/views/vw_sorgenti_orfane) — trova i collegamenti il cui bersaglio è stato cancellato dopo; il perimetro si **deriva dal catalogo** |
| **in che stato è?**                  | `script.vw_stato_sorgente` — traduce lo stato nel vocabolario comune                                                                                                          |
| **chi lo emette?**                   | [`script.fn_get_sorgente_emittente_sr_id`](/dbzero/script/funzioni/fn_get_sorgente_emittente_sr_id)                                                                           |

La quarta domanda è nata per un controllo preciso — il guard
`vendite.trgfn_commesse_sorgenti_guard_emittente`, che vieta a una commessa di
aggregare documenti di emittenti diversi — ma la domanda è generale e la risposta
esiste in **un posto solo**.

⛔ **Una trappola che quella funzione ha già pagato**, e che vale per chiunque
scriva un risolutore su questo meccanismo: l'emittente **non** si chiede al
cliente del documento. Su `ordini`, `preventivi`, `ddt` e `resi` il cliente
**può mancare** — è uno stato legittimo — mentre l'emittente c'è sempre. Un
risolutore che passasse dal cliente si fermerebbe su documenti perfettamente
validi, e *un controllo che rifiuta una situazione che il modello ammette non è
severo: è rotto*.

## 3. Come si usa

Una **pratica** deve collegarsi all'ordine `ORD0000163`: si scrive una riga in
`pratiche.pratiche_sorgenti` con il tipo di sorgente (`ORDINE_VENDITA`) e la chiave del
documento ([esempio](#area-tecnica-esempi)). Il guard verifica: esiste `vendite.ordini`
con `id = 163`? Sì → ok. Domani lo stesso meccanismo collega un **DDT** (basta cambiare
tipo) senza nuove colonne né nuovo codice.

## 4. La convenzione chiave `id` vs `uid` (trappola da conoscere)

`key_selector` decide se `sorgente_uid` contiene un **id** (bigint::text) o un **uid**
(UUID). Nel modello attuale è **misto ma voluto**:

* **`uid`**: PREVENTIVO, OFFERTA_COMMERCIALE;
* **`id`**: ORDINE, CONTRATTO, DDT, FATTURA, COMMESSA, ATTIVITA, ATTIVITA_CONSUMI.

⚠️ **Non è un errore da "ripulire"**: è portante (lo usano guard e resolver). Mappa
completa + spiegazione dei **due meccanismi** (polimorfo vs colonne tipizzate dirette
come `ddt.sorgente_uid`/`resi.sorgente_uid` che sono `uuid` a sé):
[config.sorgenti — §Convenzione chiave sorgente](/dbzero/config/tabelle/sorgenti).

⛔ **Decisione definitiva: la chiave non si unifica.** Portare tutto su `id` (o su
`uid`) è un'idea già tornata più volte, e la risposta è sempre no. Non si propone, né
come raccomandazione né come opzione. I motivi:

* **l'`uid` non vive solo qui.** `vendite.commesse_attivita` porta sempre l'`uid` del
  documento (§4a), le chiavi di idempotenza del push lo contengono, `vendite.ddt` e
  `vendite.resi` hanno un `sorgente_uid` di tipo `uuid`, e la proiezione dello stato
  delle pratiche si aggancia al preventivo per `uid`. Cambiarla vuol dire rifare guard,
  resolver, `vw_stato_sorgente_*`, lineage e push, e convertire i dati salvati (§6);
* **far viaggiare l'`id` dai lister è già stato scartato**: rompe il contratto fra
  database e backend, e non porta niente che la normalizzazione nel punto unico di
  scrittura (`fn_link_commessa_sorgente`) non dia già;
* **le due chiavi rispondono a due domande.** `config.sorgenti.key_selector` dice con
  che chiave un documento si **collega**; `config.tipi_entita.key_selector` dice con
  che chiave lo si **apre** a video, e per preventivo e offerta è `id`. Non è una
  divergenza da sanare.

Unificare il **nome del tipo** di documento (un codice solo, quello di
`config.sorgenti`) è un'altra cosa, e si fa.

### 4a. ⚠️ La trappola vera: colonne che *sembrano* polimorfe ma non lo sono

Il punto che fa sbagliare più spesso **non è** `key_selector` in sé — quello è
scritto e chiaro. È che esistono colonne chiamate `sorgente_tipo_id` /
`sorgente_uid` **fuori** da questo meccanismo, che quindi **non sono
normalizzate** e non seguono `key_selector`.

| Dove                           | Tipo | Cosa contiene davvero                                              | Dentro il meccanismo?                                           |
| ------------------------------ | ---- | ------------------------------------------------------------------ | --------------------------------------------------------------- |
| `pratiche.pratiche_sorgenti`   | TEXT | chiave **canonica** per `key_selector`                             | **sì** (guard)                                                  |
| `vendite.commesse_sorgenti`    | TEXT | chiave **canonica** per `key_selector`                             | **sì** (guard + normalizzazione in `fn_link_commessa_sorgente`) |
| `vendite.commesse_attivita`    | TEXT | **l'`uid` del documento, sempre** — anche per i tipi a chiave `id` | no                                                              |
| `vendite.attivita_fatturabili` | UUID | `md5(segment_key)`, con tipo `COMMESSA`                            | no (idempotenza del pull)                                       |
| `vendite.ddt`, `vendite.resi`  | UUID | uid del padre                                                      | no (colonna tipizzata diretta)                                  |

**Come si riconosce chi è dentro**: si interroga il catalogo dei trigger agganciati
([esempio](#area-tecnica-esempi)). Se una tabella non compare lì, **non dare per scontata la
forma della chiave**: vai a leggere la funzione che fa l'INSERT.

**La regola che chiude il dubbio**: la convenzione di `sorgente_uid` la
determina **chi scrive**, non chi chiama. `fn_link_commessa_sorgente` riceve un
uid e scrive `id::text`; `fn_upsert_commessa_attivita` riceve lo stesso uid e lo
scrive tale e quale. Guardare il chiamante (il push, che passa sempre l'uid)
porta a concludere «è sempre l'uid» e a scrivere query che non trovano nulla,
**in silenzio**.

> Caso concreto: `commesse_sorgenti` e `commesse_attivita` sono popolate dallo
> stesso push, hanno colonne omonime, e per lo **stesso ordine** contengono
> valori **diversi** (`id::text` vs `uid::text`). Nessuna delle due è
> sbagliata; sbagliato è dedurre l'una dall'altra.

## 5. Stato attuale di utilizzo — **NON è una lista scritta qui**

Una lista a mano invecchierebbe, e ne abbiamo la prova: le tabelle agganciate, i tipi
ammessi e le colonne che *sembrano* polimorfe senza esserlo sono **stato**, e lo stato
sta nel database. Qui resta la domanda e il modo di farla; le query sono in
[Area tecnica](#area-tecnica-esempi).

Le due domande da fare:

* **chi usa la macchina** — quali tabelle hanno oggi un guard agganciato (il catalogo
  dei trigger dice anche *quale dei due modelli*);
* **quali tipi-sorgente sono ammessi** — il dizionario è già una tabella, `config.sorgenti`.

> Per comodità, la prima si può incapsulare in una vista (`vw_sorgenti_consumatori`),
> così smette di essere una query da ricordare.

## 6. Per chi costruisce grafi tra documenti (lineage, genealogia, proiezione)

Usa la **chiave nativa polimorfa** `(sorgente_tipo_id, sorgente_uid)` come identità del
nodo (per la commessa → `id::text`, coerente con `key_selector='id'`). Le **colonne
tipizzate dirette** fuori dal meccanismo (`ddt.sorgente_uid`/`resi.sorgente_uid` uuid,
`ordini.documento_origine_id`, `contratti.offerta_id`) vanno **tradotte** su quella
chiave con un join alla tabella target. **Non** canonicalizzare "al volo" a un'unica
chiave: significherebbe rifare guard, resolver e `vw_stato_sorgente_*`.

I resolver di stato pronti da riusare come mattoni:
`vendite.vw_stato_sorgente_{preventivo,offerta,ordine,contratto,ddt,reso}` e
[`script.vw_stato_sorgente`](/dbzero/script/views/vw_stato_sorgente).

---

## Area tecnica — esempi

**Agganciare una pratica a un ordine** — `key_selector` di `ORDINE_VENDITA` è `id`,
quindi `sorgente_uid` porta l'`id` del documento, non il suo uid:

```sql
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
VALUES (:pratica_id,
        (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
        '163',          -- key_selector='id' per ORDINE_VENDITA → qui va l'id, non l'uid
        'COLLEGATO');
```

**Quali tabelle hanno oggi un guard agganciato** — e quale dei due modelli:

```sql
SELECT n.nspname AS schema, c.relname AS tabella,
       p.proname AS guard, t.tgname AS trigger
FROM pg_trigger t
JOIN pg_class c     ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc p      ON p.oid = t.tgfoid
WHERE p.proname LIKE 'trgfn_guard_sorgente_polimorfa%'
  AND NOT t.tgisinternal
ORDER BY 1, 2;
```

**Il dizionario dei tipi ammessi** — la mappa che decide la forma della chiave:

```sql
SELECT id, codice_interno, categoria, target_table, key_selector, attivo
FROM config.sorgenti
ORDER BY id;
```

**Gli agganci rimasti orfani** — deve restare vuota:

```sql
SELECT * FROM dbops.vw_sorgenti_orfane;
```

---
{% include-markdown "signature-core.md" %}
