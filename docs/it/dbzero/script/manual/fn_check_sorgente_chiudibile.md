## 📘 Documentazione Concettuale – Funzione `script.fn_check_sorgente_chiudibile`

> 👀 **Vedi anche**
>
> [vendite.fn_ritira_commessa_attivita_da_sorgente](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente) — l'altra metà della regola
> [vendite.trgfn_doc_guard_chiusura_sorgente](/dbzero/vendite/funzioni/trgfn_doc_guard_chiusura_sorgente) — il guard che la solleva
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile) · [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile) — le due che le delegano

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

Elenca i **motivi che impediscono di chiudere** (annullare) un documento che ha
spinto righe in commessa. Funzione **pura**: non scrive e non solleva errori di
dominio. Ritorna `[]` quando il documento si può chiudere.

⭐ **Oggi il motivo è UNO**: ci sono righe di commessa già `EMESSA`. Quelle sono
in volo verso una fattura, non si ritirano, e finché ci sono la testata non si
chiude.

---

### La regola, divisa per stato

Quando un documento si chiude, ciò che aveva spinto in commessa segue **due
strade diverse** a seconda di dove è arrivato:

| Stato della riga | Cosa succede | Chi lo fa |
| --- | --- | --- |
| `NON_EMESSA` | ⭐ **il documento la ritira** → `ANNULLATA` | [`fn_ritira_commessa_attivita_da_sorgente`](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente) |
| `EMESSA` | ⛔ **la testata NON si chiude** | **questa funzione**, sollevata dal guard |
| `ANNULLATA` | non si tocca | — |

---

### ⭐ E adesso il rifiuto ha una via d'uscita

Prima del verbo
[«Riporta da emettere»](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere)
questo blocco sarebbe stato un **vicolo cieco** — e infatti
`E_PREV_ANNULLA_COMMESSA_EMESSA` lo era: diceva «non puoi» e non nominava nessuna
strada, perché non ce n'era una.

Adesso c'è, ed è la sequenza che il messaggio nomina:

> *«Riporta da emettere» → la riga torna `NON_EMESSA` → chiudi il documento → il
> ritiro la prende insieme alle altre.*

---

### ⛔ La chiave: si guarda `commesse_attivita`, non `commesse_sorgenti`

⚠️ **Non è un dettaglio, ed è la cosa che si sbaglia leggendo in fretta.** Le due
tabelle usano chiavi polimorfe **diverse**, e deliberatamente:

| Tabella | Cosa contiene `sorgente_uid` |
| --- | --- |
| `vendite.commesse_attivita` | **`<testata>.uid::text` per TUTTE le sorgenti** — verificato sul corpo delle cinque `fn_list_*_da_pushare`, che compongono tutte `x.uid::text` |
| `vendite.commesse_sorgenti` | **varia**: `uid` per il preventivo, `id::text` per l'ordine |

⭐ È la ragione per cui `fn_check_preventivo_annullabile` confronta `v_uid::text`
mentre `fn_check_ordine_annullabile` confrontava `p_ordine_id::text`: le due
**non erano in disaccordo**, ognuna seguiva la chiave della propria sorgente.

⛔ Questa funzione lavora sulle **righe**, quindi la chiave è quella uniforme.
Chi la chiama deve passare `<testata>.uid::text`, perché sbagliarla **non
produce un errore**: produce **zero motivi**, cioè un freno che lascia passare
tutto.

---

### Una primitiva sola, non una per documento

La sorgente è polimorfa e la coppia `(sorgente_tipo_id, sorgente_uid)` è già la
chiave che tutto il dominio usa. Sei copie divergerebbero.

⭐ **Una implementazione, due superfici.** La stessa funzione serve:

* il **guard** generico, che ferma la scrittura;
* le `fn_check_*_annullabile` di ordine e preventivo, che accendono o spengono il
  **pulsante** — e che dal 2026-08-26 **delegano** qui invece di ricalcolare.

⚠️ Il preventivo **rietichetta** il motivo col proprio codice
(`E_PREV_ANNULLA_COMMESSA_EMESSA`, che Q-9 ha deciso di tenere): la regola resta
una sola, cambia solo il nome con cui esce. Ed è anche il motivo per cui sui
preventivi **non** si monta il guard generico — uscirebbero due codici diversi
per lo stesso rifiuto.

---

### ℹ️ Cosa non guarda, e perché

* **non** conta le righe già `ANNULLATA`: sono uscite di proposito;
* **non** conta le `NON_EMESSA`: sono proprio quelle che il ritiro porterà via;
* ⚠️ **non raggiunge le righe sourceless** — `ONERE` e `RETTIFICA` — perché non
  hanno sorgente. È corretto, e va detto invece che lasciato dedurre.

---

### Esempio d'uso

```sql
-- Si può chiudere questo ordine?
SELECT jsonb_array_length(
         script.fn_check_sorgente_chiudibile(
             (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
             (SELECT uid::text FROM vendite.ordini WHERE id = 41))) = 0 AS chiudibile;

-- Quante righe lo bloccano?
SELECT script.fn_check_sorgente_chiudibile(6, '…uid…') -> 0 ->> 'dettaglio';
-- → 3
```

---

### Note operative

* **`STABLE`**: è una lettura. Il solo raise è sui parametri
  (`E_RITIRO_SORGENTE_PARAMETRO_MANCANTE`, classe `TECNICO`).
* ⚠️ **Gira sotto ROW SECURITY**: `commesse_attivita` ha la RLS per emittente,
  quindi chi non vede le righe **non viene fermato**. È il comportamento di oggi
  e non un peggioramento — ma qui **non c'è una chiave esterna a fare da rete**,
  quindi va saputo. Il caso resta stretto perché la commessa eredita l'emittente
  dal documento.
* ⭐ Il **valore** nel messaggio è il **conteggio**, non gli id: quanti sono è
  ciò che dice all'operatore quanto lavoro deve recuperare.
* 🔴 La `reason_key` `vendite.sorgenti.azione_reason.righe_commessa_emesse` va
  presente nei locales.
* Test: `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql` (2, 8)
  e `test-ritiro-alla-chiusura-documento-v1.sql` (3).
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L7 / Q-5′ strada A.

---

{% include-markdown "signature-core.md" %}
