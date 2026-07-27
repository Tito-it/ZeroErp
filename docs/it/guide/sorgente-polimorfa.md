# Sorgente polimorfa — l'aggancio universale ai documenti

> **Cos'è**: il meccanismo con cui, in Zero ERP, una tabella può collegarsi a
> **qualunque** documento/entità (preventivo, ordine, DDT, fattura, commessa…) usando
> **un solo pattern**, invece di una colonna dedicata per ogni tipo.
>
> **Vedi anche**: [config.sorgenti](/dbzero/config/tabelle/sorgenti) ·
> [script.trgfn_guard_sorgente_polimorfa_testuale](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_testuale) ·
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)

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
   - `target_table` = in quale tabella cercare (es. `ORDINE_VENDITA` → `vendite.ordini`);
   - `key_selector` = con quale chiave cercare, **`id`** o **`uid`**.
2. **Le colonne di aggancio** sulla tabella che collega:
   - `sorgente_tipo_id` = *che tipo è* (FK a `config.sorgenti`);
   - `sorgente_uid` = *quale in particolare* (il valore che identifica la riga).
3. **Il guard** — `script.trgfn_guard_sorgente_polimorfa_testuale` (dal 2026-07-18,
   attivo su `pratiche_sorgenti` e `commesse_sorgenti`). Su INSERT/UPDATE apre il
   dizionario, controlla che la chiave sia **nel formato giusto** per il
   `key_selector`, va nella `target_table` giusta e verifica che **quel documento
   esista davvero**; altrimenti **blocca** (niente collegamenti a documenti
   fantasma, niente chiavi nel formato sbagliato che poi «non risolvono» in
   silenzio). Esiste anche la sorella `_tipizzata` per il modello a colonne
   tipizzate (`sorgente_riga` BIGINT / `sorgente_uid` UUID), oggi non agganciata.
   In più, `vendite.fn_link_commessa_sorgente` **normalizza** la chiave alla
   scrittura (traduce l'uuid in `id::text` per i tipi a chiave `id`): i chiamanti
   storici continuano a funzionare e scrivono canonico.

> Analogia: un **adattatore universale**. Non serve una presa diversa per ogni Paese:
> basta l'adattatore + l'indicazione di quale spina usare (`key_selector`).

## 3. Come si usa — esempio

Una **pratica** deve collegarsi all'ordine `ORD0000163`:

```sql
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
VALUES (:pratica_id,
        (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
        '163',          -- key_selector='id' per ORDINE_VENDITA → qui va l'id, non l'uid
        'COLLEGATO');
```

Il guard verifica: esiste `vendite.ordini` con `id = 163`? Sì → ok. Domani lo stesso
meccanismo collega un **DDT** (basta cambiare tipo) senza nuove colonne né nuovo codice.

## 4. La convenzione chiave `id` vs `uid` (trappola da conoscere)

`key_selector` decide se `sorgente_uid` contiene un **id** (bigint::text) o un **uid**
(UUID). Nel modello attuale è **misto ma voluto**:

- **`uid`**: PREVENTIVO, OFFERTA_COMMERCIALE;
- **`id`**: ORDINE, CONTRATTO, DDT, FATTURA, COMMESSA, ATTIVITA, ATTIVITA_CONSUMI.

⚠️ **Non è un errore da "ripulire"**: è portante (lo usano guard e resolver). Mappa
completa + spiegazione dei **due meccanismi** (polimorfo vs colonne tipizzate dirette
come `ddt.sorgente_uid`/`resi.sorgente_uid` che sono `uuid` a sé):
[config.sorgenti — §Convenzione chiave sorgente](/dbzero/config/tabelle/sorgenti).

### 4a. ⚠️ La trappola vera: colonne che *sembrano* polimorfe ma non lo sono

Il punto che fa sbagliare più spesso **non è** `key_selector` in sé — quello è
scritto e chiaro. È che esistono colonne chiamate `sorgente_tipo_id` /
`sorgente_uid` **fuori** da questo meccanismo, che quindi **non sono
normalizzate** e non seguono `key_selector`.

| Dove | Tipo | Cosa contiene davvero | Dentro il meccanismo? |
|---|---|---|---|
| `pratiche.pratiche_sorgenti` | TEXT | chiave **canonica** per `key_selector` | ✅ sì (guard) |
| `vendite.commesse_sorgenti` | TEXT | chiave **canonica** per `key_selector` | ✅ sì (guard + normalizzazione in `fn_link_commessa_sorgente`) |
| `vendite.commesse_attivita` | TEXT | **l'`uid` del documento, sempre** — anche per i tipi a chiave `id` | ❌ no |
| `vendite.attivita_fatturabili` | UUID | `md5(segment_key)`, con tipo `COMMESSA` | ❌ no (idempotenza del pull) |
| `vendite.ddt`, `vendite.resi` | UUID | uid del padre | ❌ no (colonna tipizzata diretta) |

**Come si riconosce chi è dentro**: la Query 1 di §5 (elenco dei trigger guard).
Se una tabella non compare lì, **non dare per scontata la forma della chiave**:
vai a leggere la funzione che fa l'INSERT.

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

Una lista a mano invecchierebbe. Lo stato reale è già nel database: **interrogalo**.

**Chi USA la macchina** (tabelle con il guard) — sempre aggiornato:

```sql
SELECT n.nspname AS schema, c.relname AS tabella, t.tgname AS trigger
FROM pg_trigger t
JOIN pg_class c     ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc p      ON p.oid = t.tgfoid
WHERE p.proname LIKE 'trgfn_guard_sorgente_polimorfa%'
  AND NOT t.tgisinternal
ORDER BY 1, 2;
```

**Quali tipi-sorgente sono ammessi** (il dizionario è già una tabella):

```sql
SELECT id, codice_interno, categoria, target_table, key_selector, attivo
FROM config.sorgenti
ORDER BY id;
```

> Consumatori tipici (a titolo d'esempio, non esaustivo — per l'elenco vivo usa la
> Query 1): `pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti`,
> `vendite.attivita_fatturabili`. Se vuoi comodità, si può incapsulare la Query 1 in
> una vista `vw_sorgenti_consumatori`.

## 6. Per chi costruisce grafi tra documenti (lineage, genealogia, proiezione)

Usa la **chiave nativa polimorfa** `(sorgente_tipo_id, sorgente_uid)` come identità del
nodo (per la commessa → `id::text`, coerente con `key_selector='id'`). Le **colonne
tipizzate dirette** fuori dal meccanismo (`ddt.sorgente_uid`/`resi.sorgente_uid` uuid,
`ordini.documento_origine_id`, `contratti.offerta_id`) vanno **tradotte** su quella
chiave con un join alla tabella target. **Non** canonicalizzare "al volo" a un'unica
chiave: significherebbe rifare guard, resolver e `vw_stato_sorgente_*`.

I resolver di stato pronti da riusare come mattoni:
`vendite.vw_stato_sorgente_{preventivo,offerta,ordine,contratto}` e `script.vw_stato_sorgente`.
