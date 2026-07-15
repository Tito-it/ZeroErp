# Sorgente polimorfa — l'aggancio universale ai documenti

> **Cos'è**: il meccanismo con cui, in Zero ERP, una tabella può collegarsi a
> **qualunque** documento/entità (preventivo, ordine, DDT, fattura, commessa…) usando
> **un solo pattern**, invece di una colonna dedicata per ogni tipo.
>
> **Vedi anche**: [config.sorgenti](/dbzero/config/tabelle/sorgenti) ·
> [script.trgfn_guard_sorgente_polimorfa](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa) ·
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
3. **Il guard** — `script.trgfn_guard_sorgente_polimorfa`. Su INSERT/UPDATE apre il
   dizionario, va nella `target_table` giusta, cerca con la chiave giusta e verifica
   che **quel documento esista davvero**; altrimenti **blocca** (niente collegamenti a
   documenti fantasma, niente `key_selector` non gestiti).

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

## 5. Stato attuale di utilizzo — **NON è una lista scritta qui**

Una lista a mano invecchierebbe. Lo stato reale è già nel database: **interrogalo**.

**Chi USA la macchina** (tabelle con il guard) — sempre aggiornato:

```sql
SELECT n.nspname AS schema, c.relname AS tabella, t.tgname AS trigger
FROM pg_trigger t
JOIN pg_class c     ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_proc p      ON p.oid = t.tgfoid
WHERE p.proname = 'trgfn_guard_sorgente_polimorfa'
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
