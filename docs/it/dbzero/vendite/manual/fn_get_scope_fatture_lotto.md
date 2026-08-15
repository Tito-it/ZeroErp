## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_scope_fatture_lotto`

> 👀 **Vedi anche**
>
> **Chi la usa:**
>
> • [vendite.fn_genera_fondi_fattura_lotto](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_lotto) — ne prende le **chiavi distinte**
> • [vendite.fn_applica_fondi_lotto](/dbzero/vendite/funzioni/fn_applica_fondi_lotto) — ne prende le **fatture**
>
> **Tabelle:**
>
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — ⚠️ è lei a portare la RLS
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.3 R-3

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Quali fatture ha questo lotto, e con che chiave.**

Una riga per fattura, ordinata per id, con i cinque elementi che i giri di
fatturazione usano come chiave:

```text
fattura_id · billing_account_id · utility_id
tipo_doc_fiscale_id · emittente_soggetto_ruolo_id · valuta_id
```

---

### ⭐ Perché esiste: era una regola di dominio scritta in Python

Lo scope del lotto viveva in `apps/vendite/db/pipeline_repository.py`
(`_SCOPE_FATTURE_LOTTO_SQL`) e serviva a tre cose — validare i campi, generare i
fondi, applicarli. Con le due madri per lotto i lettori diventano quattro.

*Una regola di dominio con quattro lettori non sta fuori dal database.*

---

### 🔴 La utility è quella della FATTURA, e non è un dettaglio

La versione Python la ricavava da `COALESCE(fl.utility_id, ba.utility_id)` — dal
**lotto** o dal **billing account**. Ma
[fn_genera_fondi_fattura_source](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_source)
filtra su `f.utility_id`, la colonna **della fattura**.

```text
utility passata:   quella del lotto
utility filtrata:  quella della fattura
        divergono → nessun errore, nessun log, NESSUN FONDO
```

Un no-op muto è la forma peggiore di difetto: il task risulta eseguito, il lotto
risulta lavorato, e la fattura esce senza il fondo che le spettava.

> ⚠️ **E il controllo che avrebbe dovuto accorgersene non poteva.** La
> validazione Python guarda il valore **già coalescizzato**, e
> `billing_account.utility_id` è `NOT NULL`: quel ramo non scattava mai. Qui la
> colonna si legge nuda, e il controllo torna a significare qualcosa.

✅ Misurato su dev il 2026-08-15: 12 fatture in lotto, **zero** divergenze e zero
utility mancanti. La correzione è per «può succedere» —
`vendite.fatture.utility_id` è nullable, ed è esattamente il motivo per cui il
Python faceva `COALESCE`.

---

### ⚠️ Perché una `fn_get_*` può sollevare

Due casi, e in entrambi restituire zero righe direbbe una cosa falsa:

| Caso | Errore | Perché non «zero righe» |
| --- | --- | --- |
| lotto **inesistente** | `E_LOTTO_NON_TROVATO` | «vuoto» e «inesistente» sono risposte diverse: la prima è legittima, la seconda è un errore del chiamante, e zero righe non le distingue |
| **scope incompleto** | `E_PIPELINE_SCOPE_INCOMPLETE` | lo scope di un documento rotto non è vuoto: **non esiste**. Il contesto porta gli id delle fatture colpevoli |

⚠️ **Cambio di comportamento** rispetto a prima: una fattura di lotto senza
`utility_id` adesso **ferma il giro**, mentre il `COALESCE` la faceva proseguire
a vuoto. È fail-closed di proposito — *una fattura emessa senza il fondo che le
spettava non se ne accorge nessuno, un task rosso sì.*

ℹ️ Si controllano le **tre colonne nullable** della chiave (`utility_id`,
`tipo_doc_fiscale_id`, `valuta_id`). Billing account ed emittente sono `NOT NULL`
a schema: aggiungerli sarebbe una riga che non può scattare, e una riga che non
può scattare insegna a chi legge una cosa falsa sul modello.

---

### ⚠️ RLS: il perimetro è quello del chiamante

`SECURITY INVOKER` (il default): `vendite.fatture` ha la RLS operatori, quindi un
lotto che contiene fatture di un altro emittente ne mostra solo la parte
visibile. È corretto — è quella che il chiamante può lavorare.

---

### Esempio d'uso

```sql
-- Le chiavi distinte di un lotto: quante volte gira davvero la generazione.
SELECT DISTINCT billing_account_id, utility_id, tipo_doc_fiscale_id,
       emittente_soggetto_ruolo_id, valuta_id
  FROM vendite.fn_get_scope_fatture_lotto(1234);
```

---

{% include-markdown "signature-core.md" %}
