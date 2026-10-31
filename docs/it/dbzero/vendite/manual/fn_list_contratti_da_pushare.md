## Documentazione Concettuale – Funzione `vendite.fn_list_contratti_da_pushare(...)`

> **Ultimo aggiornamento**: 31 ottobre 2026

> **Vedi anche**
>
[vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) — la regola: che cosa il contratto addebita a ogni giro
> [vendite.fn_canone_periodi](/dbzero/vendite/funzioni/fn_canone_periodi) — i periodi del canone
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> [Guida dei contratti §4-bis](/guide/gestione-contratti#4-bis-come-il-contratto-si-addebita-una-tantum-e-canoni) — come il contratto si addebita, per chi non sviluppa

---
### 🎯 Scopo Principale

`vendite.fn_list_contratti_da_pushare(...)` è il **lister del push dei contratti**: le righe che
i contratti devono mandare in commessa a questo giro, con il payload completo per l'handler
(una riga per riga di commessa da scrivere con `fn_upsert_commessa_attivita`).

Dal 2026-10-31 (`20261031-03`) la regola non sta qui: la funzione legge
[`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati),
che la condivide con la dashboard dei contratti, e ne tiene le righe **senza scarto**. Qui
restano:

* la sorgente `CONTRATTO` e il suo tipo di documento fiscale, da `config.sorgenti`
  (`E_CODICE` se la riga manca o è spenta);
* le colonne della commessa che non dipendono dalla riga: `pricing_mode = FIXED`,
  `tipo_movimento = NORMALE`, `valuta_id`, `termine_pagamento_id` e `modalita_pagamento_id` NULL;
* l'ordine (contratto, ramo, chiave) e il limite `p_limit`.

Il controllo di `p_contratto_id` (`E_PUSH_SORGENTE_ID_INVALIDO`) e gli stati ATTIVO e CESSATO
(`E_CODICE` se mancano) li fa la funzione della regola.

---

### Che cosa esce (in breve)

| Ramo | Che cosa | Chiave (`segment_key`) |
| --- | --- | --- |
| una tantum | le righe ADESIONE e AGGIUNTA una tantum dei contratti ATTIVO, una volta, competenza = `valido_dal` | `CONTRATTO:<uid>:R:<riga>:M:<AAAA-MM>` |
| canone | i periodi maturati e non ancora addebitati: righe ADESIONE e AGGIUNTA, OVERRIDE su una quota fissa, quote fisse del listino | riga: `CONTRATTO:<uid>:R:<riga>:M:<mese d'inizio del pezzo>`; quota fissa: `CONTRATTO:<uid>:A:<articolo>:M:…` |
| storno | la parte non goduta di un periodo addebitato oltre la fine del contratto, come differenza dal già stornato | `<base del pezzo>#STO`, poi `#STO:2`, `#STO:3` … |

Le regole complete (quali righe, periodi, quantità, prezzo, storni, scarti) sono nella pagina di
[`fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati).

`riga_id` è NULL sulle quote fisse del listino e sugli storni: l'handler non espande i componenti
di un kit su quelle righe.

---

### Parametri

| Parametro | Default | Effetto |
| --- | --- | --- |
| `p_competenza_mese` | NULL | il giro di quel mese: la data del giro è la sua fine; NULL = oggi aziendale |
| `p_billing_account_id` | NULL | solo i contratti di quel billing account |
| `p_limit` | NULL | al più N righe, nell'ordine (contratto, ramo, chiave) |
| `p_contratto_id` | NULL | un contratto solo; `<= 0` → `E_PUSH_SORGENTE_ID_INVALIDO` |

Estensione coordinata con le altre `fn_list_*_da_pushare`: la firma è quella del client Python
`CommesseRepository.fetch_pushable_rows`.

---

### Esempi d'uso

**Giro di un mese (orchestratore):**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(
  p_competenza_mese => DATE '2026-11-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Un contratto solo:**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => 12345);
```

---

### `fatturazione_immediata` e `prezzo_bloccato` (rev 2026-07-27)

Dal changeset `20260727-05` `fatturazione_immediata` è il valore della **colonna reale**
`vendite.contratti.fatturazione_immediata`, non più una costante `FALSE`. Viaggia fino a
`fn_get_or_create_commessa`, dove è **parte della chiave di dedup**: è così che il flag separa le
due corsie (commesse distinte → lotti distinti → `GIORNALIERO` che numera da solo *vs* `MASSIVO`
che si ferma a `EMESSA`).

⚠️ `prezzo_bloccato` dipende dalla **riga** (la riga ha un prezzo suo: OVERRIDE, AGGIUNTA; sugli
storni sempre vero, al prezzo addebitato), **non** dal flag. L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste solo in
`fn_list_preventivi_da_pushare`: copiarlo qui cambierebbe in silenzio il comportamento di pricing.

Presidio a valle: dopo il push il flag non è più modificabile sul documento
([`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)).

---

### Storia

* **2026-10-04** (`20261004-33`): le `ESCLUSIONE` non si listano; l'erogazione viaggia in
  `meta.tipo_erogazione` (dal `20261013-19`, senza ripiego su CANONE).
* **2026-10-13** (`20261013-24`): solo le `UNA_TANTUM`, competenza = giorno di attivazione. Un
  canone partiva una volta sola con la competenza di tutto il contratto.
* **2026-10-30** (`20261030-01`): i tre rami (una tantum, canoni a periodi, storni); l'OVERRIDE non
  si addebita più, l'ADESIONE prende il prezzo del listino.
* **2026-10-31** (`20261031-01`): lo storno è la differenza dal già stornato, quindi segue la fine
  del contratto anche quando si sposta dopo il primo storno.
* **2026-10-31** (`20261031-03`): il corpo passa a `fn_contratti_addebiti_maturati`; qui il filtro.

Brief: `brief-db-contratto-righe-periodiche-in-commessa` (§6.12, §6.13).

Test: `db/pgtap/vendite/test-push-contratto-canoni-v1.sql`,
`test-push-contratto-dalla-madre-v1.sql`, `test-fn-list-contratti-da-pushare-v1.sql` e `-v2`.

{% include-markdown "signature-core.md" %}
