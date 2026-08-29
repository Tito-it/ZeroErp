## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_update_cliente`

> 👀 **Vedi anche**
>
> Tabelle:
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
> Funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-done/analisi-fix-transazioni) (Classe A, finding #1)

### 🎯 Scopo Principale

(latest review 08-07-2026)

La funzione **`anagrafiche.fn_update_cliente`** è la **funzione madre atomica**
per l'aggiornamento di un cliente. Fonde in un'**unica statement** le due
scritture che il service Python eseguiva separatamente:

1. `UPDATE anagrafiche.billing_account` — la **categoria cliente** (Pricing v5:
   la categoria vive sul BA, non sul cliente);
2. `UPDATE anagrafiche.clienti` — i **campi editabili** del cliente (pagamento,
   PA, garanzia, servizio).

In autocommit, farle separate significava che il fallimento della seconda
lasciava la prima committata → due entità reali disallineate. Qui **o entrambe
o rollback totale** (atomicità per costruzione).

---

### Firma

```sql
anagrafiche.fn_update_cliente(
    p_cliente_id              anagrafiche.clienti.id%TYPE,
    p_ba_categoria_cliente_id anagrafiche.billing_account.categoria_cliente_id%TYPE DEFAULT NULL,
    p_cliente_fields          jsonb DEFAULT '{}'::jsonb
) RETURNS TABLE (
    cliente_id           anagrafiche.clienti.id%TYPE,
    categoria_aggiornata boolean,
    campi_aggiornati     boolean
)
```

### Parametri di Input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_cliente_id` | `clienti.id%TYPE` | Cliente da aggiornare (obbligatorio). |
| `p_ba_categoria_cliente_id` | `billing_account.categoria_cliente_id%TYPE` | Categoria da scrivere sul BA. Se `NULL` la categoria non viene toccata; **mai** impostata a NULL (colonna NOT NULL). |
| `p_cliente_fields` | `jsonb` | **Delta** dei campi editabili: solo le chiavi **presenti** vengono aggiornate (chiave presente con valore null ⇒ colonna azzerata; chiave assente ⇒ invariata). Le chiavi non whitelisted sono ignorate. |

**Whitelist campi editabili:** `modalita_pagamento_id`, `termine_pagamento_id`,
`servizio_da_fatturare`, `garanzia_tipo`, `garanzia_importo`.

> ⛔ **rev 2026-08-29 — la whitelist si e' DIMEZZATA, e la doc era gia' indietro.**
>
> Uscite adesso (changeSet `20260829-20`), perche' le colonne non esistono piu' su
> `anagrafiche.clienti` (`20260829-22`):
> `iva_id` — non aveva piu' un lavoro: l'aliquota la decide la merce;
> `cliente_pa` e `split_payment` — sono saliti su
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti), perche' discendono dalla
> partita IVA e non dalla fornitura;
> `codice_cig`, `codice_cup`, `codice_commessa` — sono andati su
> [vendite.contratti](/dbzero/vendite/tabelle/contratti), perche' nominano un contratto.
> Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, I0-B / I8-B.
>
> ⚠️ **`tipo_gg_scadenza_ft` e `nr_giorni_scadenza` erano gia' false**: tolte il
> 2026-07-31 (D-I, piano satelliti 3a.5) e mai aggiornate qui. Un elenco che non ha un
> presidio invecchia in silenzio, e chi lo legge non ha modo di accorgersene.
>
> ⚠️ **Effetto per il chiamante, e va saputo**: una chiave non whitelisted **non fa
> errore, viene ignorata**. Finche' il backend manda ancora `iva_id`, il salvataggio
> riesce e quel valore non va da nessuna parte.

### Ritorno

Una riga: `cliente_id` (echo), `categoria_aggiornata` (TRUE se la categoria BA
è stata scritta), `campi_aggiornati` (TRUE se almeno un campo cliente è stato
scritto). Il caller ricava «modificato = categoria_aggiornata OR
campi_aggiornati»; se entrambi FALSE decide se è un errore di validazione
"nessun campo modificato".

Cliente inesistente ⇒ **`E_CLIENTE_NON_TROVATO`**.

### Note tecniche

* **`SECURITY INVOKER`**: gira come il ruolo chiamante → RLS e scope emittente
  su `billing_account` restano valutati come dal Python.
* **Audit / tx_id / storico** sono gestiti dai trigger esistenti su
  `clienti` e `billing_account`: la funzione fa solo `UPDATE` puri.
* La presenza di una chiave nel delta è verificata con `jsonb_exists()`
  (funzione, non operatore `?`) per evitare l'escaping Liquibase.
* Le validazioni di input (tipo/positività della categoria) restano pre-check
  applicativi del service: non attengono all'atomicità.
