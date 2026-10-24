## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_smistamento_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
Viste/funzioni collegate:
>
[vw_preventivi_smistamento](vw_preventivi_smistamento.md) (aggregata)
> [vw_preventivi_righe_smistabili_commessa](vw_preventivi_righe_smistabili_commessa.md)
> [vw_preventivi_righe_smistabili_ordine](vw_preventivi_righe_smistabili_ordine.md)

---
### 🎯 Scopo Principale
Fonte dati del **Pannello Smistamento** (brief-db-smistamento-preventivi.md, B):
una riga per ogni riga **attiva** del preventivo, con natura, destinazione e
lo **stato di smistamento autorevole** per la UI. Sostituisce
`vw_preventivi_stato_fatturazione_righe` (rename + rework natura-aware,
2026-06-12): i flag booleani `in_commessa`/`emessa_af`/`fatturata` sono stati
**rimossi** — `stato_smistamento` e' l'unica verita'.

---

### Colonne chiave

| Campo | Significato |
|-------|-------------|
| `natura_vendita_id`, `natura_vendita_codice` | Natura della riga (snapshot di riga; NULL = pregresso pre-trigger) |
| `destinazione_tipo` | Destinazione **effettiva**: `COALESCE(nature_vendita.destinazione_tipo, 'COMMESSA')` — natura NULL trattata COMMESSA, stessa convenzione di `fn_list_preventivi_da_pushare` |
| `ordine_riga_id`, `ordine_id`, `ordine_numero` | Ramo merce: riferimenti all'ordine generato (via `ordini_righe.preventivo_riga_id`, UNIQUE → nessun fan-out) |
| `stato_smistamento` | Stato autorevole: `RESIDUA` / `A_ORDINE` / `IN_COMMESSA` / `EMESSA_AF` / `FATTURATA` |

### Semantica `stato_smistamento`

Valutazione in cascata (vince il primo vero):

1. `FATTURATA` — esiste `attivita_fatturabili` con `fattura_riga_id` valorizzato;
2. `EMESSA_AF` — esiste `attivita_fatturabili` per la riga;
3. `IN_COMMESSA` — il segmento `'PREV:<uid>:R:<riga_id>'` non e' `LIBERA` per `script.fn_get_stato_push_segment`, cioe' la riga e' gia' mandata in commessa (anche non ancora emessa). ⭐ rev 2026-10-12 (`20261012-11`, brief-db-annullo-a-valle-riapre-a-monte D-5): prima contava solo `stato_emissione = 'EMESSA'`, allineato al predicato che la vista smistabili aveva fino al 2026-06-28 e che poi era cambiato; una riga mandata e non emessa risultava `RESIDUA` mentre il push la dava gia' inviata. Una riga `ANNULLATA` (commessa annullata) torna `RESIDUA`;
4. `A_ORDINE` — esiste `ordini_righe.preventivo_riga_id` per la riga;
5. `RESIDUA` — non smistata su alcun ramo.

Gli stati 1–3 sono progressivi sul ramo commessa; `A_ORDINE` e' lo stato
finale del ramo merce (la fatturazione merce segue il ciclo ordine→DDT).

---

### Esempio d'uso

```sql
-- Pannello smistamento: righe del preventivo con stato e destinazione
SELECT riga_id, riga_descrizione, destinazione_tipo, stato_smistamento,
       ordine_numero
  FROM vendite.vw_preventivi_smistamento_righe
 WHERE preventivo_id = 42
 ORDER BY riga_ordine;
```

---

### Note operative

* `security_invoker = on` (policy RLS: la vista eredita i privilegi del chiamante).
* I rami commessa/AF sono valutati con `EXISTS` (niente fan-out da `segment_key` o sorgente duplicati).
* Solo righe `attivo IS TRUE`.
* Test: `db/pgtap/vendite/test-vw-preventivi-smistamento-v1.sql`.
