## 📘 Documentazione Concettuale – Funzione `vendite.fn_create_contratto`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
>
> Funzioni:
> [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-done/analisi-fix-transazioni) (Classe A, finding #2)

### 🎯 Scopo Principale

(latest review 12-10-2026)

La funzione **`vendite.fn_create_contratto`** è la **funzione madre atomica**
per la creazione di un contratto: genera il numero, crea la testata (stato
`DRAFT`) e l'eventuale riga utility in un'**unica statement**.

Il service Python eseguiva le tre operazioni in transazioni separate:
`generate_numero()` (consuma il contatore) → `INSERT contratti` → `INSERT
contratti_utilities`. In autocommit, se l'INSERT utility veniva rifiutato da un
guard, il contratto restava committato: **contratto orfano senza utility**.
Qui o tutto o rollback totale.

---

### Firma

```sql
vendite.fn_create_contratto(
    p_testata jsonb,
    p_utility jsonb DEFAULT NULL
) RETURNS TABLE (
    contratto_id vendite.contratti.id%TYPE,
    numero       vendite.contratti.numero%TYPE
)
```

### Parametri di Input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_testata` | `jsonb` | Campi della testata contratto. Vengono inseriti **solo i campi whitelisted presenti**; le colonne assenti ereditano default/trigger DB (`ambito`, `valido_dal`, `data`, `emittente_fiscale_id`, `valuta_id`, `meta`…). `numero` e `stato_doc_contratto_id` sono risolti dalla funzione (ignorati se passati). |
| `p_utility` | `jsonb` | Opzionale: la scheda di fornitura scritta dall'operatore. Se `NULL` o `'{}'` resta quella che il contratto riceve dall'anagrafica alla nascita (se il contatore ha dati precontrattuali). Altrimenti le sole chiavi whitelisted presenti **correggono** quella scheda; se il contatore non ha dati, la scheda nasce da queste chiavi. `contratto_id` impostato dalla funzione. |

**Whitelist testata:** `billing_account_id`, `emittente_fiscale_id`,
`istanza_utility_id`, `utility_id`, `ambito`, `valido_dal`, `valido_al`,
`parent_contratto_id`, `data`, `listino_id`, `tipo_variazione_globale`,
`valore_variazione_globale`, `categoria_cliente_id_snapshot`, `valuta_id`,
`meta`.
**Whitelist utility:** `istanza_utility_id`, `utility_id`,
`istanza_dati_precontrattuali_id`, `tipo_utenza_id`, `classe_utenza_id`,
`param_1_num`, `param_2_txt`, `meta`.

Stato iniziale = `DRAFT` (`config.stati_doc_contratti`); se assente ⇒
**`E_CONFIG_MANCANTE`**.

### La scheda di fornitura: anagrafica e operatore

Appena la testata nasce, il trigger
[`trgfn_contratti_snapshot_precontrattuali`](/dbzero/vendite/funzioni/trgfn_contratti_snapshot_precontrattuali)
le dà la scheda di fornitura dai dati precontrattuali del contatore. Poi la
funzione applica `p_utility`:

* **la scheda dall'anagrafica c'è** → un `UPDATE` delle sole chiavi mandate:
  **vince l'operatore**, e le voci che non ha compilato restano quelle
  dell'anagrafica. È la stessa regola del passaggio da offerta a contratto;
* **non c'è** → l'`INSERT` delle chiavi mandate.

Fino al 12-10-2026 il secondo `INSERT` collideva col primo
(`uq_contratti_utilities_contratto_id`): un contratto su un contatore con dati
precontrattuali e la scheda compilata non si creava.

⚠️ Perché l'operatore sappia che cosa sta correggendo, il drawer gli mostra prima
la scheda dell'anagrafica:
[`vendite.fn_get_fornitura_da_anagrafica`](/dbzero/vendite/funzioni/fn_get_fornitura_da_anagrafica)
è la stessa lettura che usa il trigger.

⚠️ `UPDATE` e non `INSERT … ON CONFLICT DO UPDATE`: i trigger `BEFORE INSERT`
giudicano la riga **proposta**, e il guard tipo/classe rifiuterebbe una scheda
parziale (la sola classe, i soli parametri) anche quando la riga finale è
coerente.

### Note tecniche

* **INSERT dinamico** delle sole chiavi presenti, tipizzate via
  `jsonb_populate_record`: rispetta i default/trigger DB delle colonne assenti,
  come faceva l'INSERT dinamico del repository Python.
* **`SECURITY INVOKER`**: RLS + guard emittente-scope su `contratti` valutati
  come dal Python. Audit/tx_id/validita/uid/categoria-snapshot gestiti dai
  trigger esistenti.
* ⚠️ **Numero da sequence.** `fn_generate_codice` usa una `nextval` — le
  sequence **non fanno rollback**: un fallimento lascia un *gap* di numerazione
  (innocuo, già così prima del fix). La funzione elimina il **contratto orfano**,
  non il gap.
