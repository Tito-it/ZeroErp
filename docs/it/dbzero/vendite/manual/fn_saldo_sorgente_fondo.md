## 📘 Documentazione Concettuale – Funzione `vendite.fn_saldo_sorgente_fondo`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) · [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)
>
> **Funzioni:**
>
> • [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) · [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili)
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) · [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — i due chiamanti
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-3

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

Risponde a una domanda sola: **«quanto regge ancora questa fattura sorgente,
tolto ciò che questo fondo le ha già dato?»**

```text
saldo(movimenti)  −  ( saldo contabile postabile  −  quota di QUESTO fondo )
```

---

### ⭐ Il terzo termine è tutto il punto

I primi due sono i due saldi che il progetto usa da sempre: il residuo per
**movimenti** e quanto è già **in lavorazione**. Il terzo è quello che rende la
domanda sensata.

Quando un fondo viene applicato, `fn_sync_contabili_fondo_fattura` scrive una
**riga contabile sulla fattura sorgente**: è il modo in cui la sorgente risulta
saldata per trasferimento. Quella riga entra nel secondo termine — quindi, senza
scorporarla, chiedere al fondo di «coprire» il residuo significherebbe
chiedergli di coprire **una cosa che copre lui**. Al primo passaggio il termine
vale zero e non si nota; al rerun di un lotto sì, ed è il momento in cui una
formula scritta a metà smette di funzionare.

`p_source_id` assente = **nessun contributo proprio da scorporare**. Non è un
ripiego: è la stessa domanda posta *prima* che il fondo esista come riga
contabile.

---

### Regole principali

* `p_fattura_sorgente_id` obbligatorio e `> 0`; `p_source_id` opzionale ma, se
  fornito, `> 0`. Guard espliciti con `E_PARAMETRO_INVALIDO`: un id nullo è un
  errore del chiamante, non un caso da normalizzare in silenzio.
* La quota propria conta solo le righe contabili **attive**, in stato
  **postabile**, il cui `fondo_source_id` è l'atto indicato (⭐ **colonna** dal
  21-08-2026; prima erano due chiavi dentro il `meta`, e il filtro su `origine`
  è caduto perché diceva la stessa cosa in un secondo modo).
* Ritorna un `NUMERIC` che **può essere negativo**: su una fattura a credito il
  residuo lo è, ed è normale.

> ⚠️ **L'assunzione su cui regge lo scorporo, scritta perché non si perda.** La
> quota propria somma le sole righe **postabili**, quindi vale **finché la riga
> del fondo è in lavorazione**. Su un fondo il cui trasferimento è già stato
> *registrato* quella riga non sarebbe più contata — `POSTATA` non è postabile —
> lo scorporo verrebbe a zero e il residuo risulterebbe **più basso del vero**:
> il fondo sembrerebbe non più capiente.
>
> ✅ **Non capita, e non per fortuna**: un trasferimento registrato porta l'atto
> a `ESEGUITO`, e tutti e tre i chiamanti filtrano `ASSEGNATO` o `DISPONIBILE`.
> Nessuno arriva qui con un fondo eseguito.
>
> ⛔ **Chi aggiungesse un quarto chiamante deve rispettare questa condizione.**
> È l'invariante presidiata da `db/pgtap/vendite/test-fondo-fattura-eseguito.sql`
> — *nessun fondo `ASSEGNATO` ha una riga già registrata* — e un'assunzione non
> presidiata è la prossima trappola.

---

### ⚠️ Perché NON è dichiarata `STABLE`

Non scrive niente, quindi la tentazione c'è. Ma chiama
`pagamenti.fn_get_saldo_fattura` e `fn_get_saldo_fattura_contabili`, entrambe
`plpgsql` **senza marcatore di volatilità**, cioè `VOLATILE`.

Dichiarare `STABLE` una funzione che ne chiama di volatili è una **promessa che
il planner può prendere sul serio** — cache del risultato, inline in un piano —
su un valore che stabile non è. Il costo di non dichiararla è un piano meno
aggressivo; il beneficio è non mentire.

ℹ️ Il giorno in cui le due funzioni di `pagamenti` verranno dichiarate `STABLE`,
questa potrà seguirle. Non prima.

---

### ⚠️ Il primo termine oggi è inerte, e la formula è scritta per domani

**Nessuna funzione del database scrive `pagamenti.vendite_movimenti`**: il
*posting* non è ancora implementato (slice 1 del
[cantiere incassi](/dev/work-in-progress/brief-incassi-riconciliazione-rate-promemoria)).
Quindi `fn_get_saldo_fattura` restituisce oggi, per costruzione, l'intero
`totale_a_pagare`.

Non è un difetto di questa funzione: è il motivo per cui la formula nomina
comunque quel termine. Il giorno in cui il posting esisterà, il conto sarà già
giusto senza toccare niente.

---

### Chi la usa, e perché è una funzione e non tre copie

| Chiamante | A cosa serve |
| --- | --- |
| `vendite.fn_applica_fondi_fattura` | **guard di capienza**: prima di muovere denaro rilegge se la sorgente regge ancora l'importo del fondo |
| `vendite.fn_sync_contabili_fondo_fattura` | decide se la source è ormai coperta (saldo effettivo zero) |
| *(Fase C del piano)* | la **proposta derivata**, il numero che l'elenco «fondi da decidere» mostrerà senza conservarlo |

La formula esisteva già, scritta inline dentro la sync. È stata estratta il
2026-08-15 con la **regola del 2**, prima che le copie divergessero: due
versioni della regola che decide se un fondo è ancora dovuto darebbero, prima o
poi, due risposte diverse alla stessa domanda — una in applicazione e una in
sincronizzazione.

---

### Esempio d’uso

```sql
-- Quanto regge la sorgente 123, al netto di quello che il fondo 45 le ha dato
SELECT vendite.fn_saldo_sorgente_fondo(123, 45);

-- Prima che il fondo esista come riga contabile (nessun contributo proprio)
SELECT vendite.fn_saldo_sorgente_fondo(123);
```

⚠️ **Come si confronta il risultato**: su segno **e** valore assoluto, mai con un
`>=` nudo. Su una sorgente a credito il residuo è negativo, e un confronto
diretto direbbe sempre di no:

```sql
sign(vendite.fn_saldo_sorgente_fondo(s.fattura_sorgente_id, s.id)) = sign(s.importo)
AND abs(vendite.fn_saldo_sorgente_fondo(s.fattura_sorgente_id, s.id)) >= abs(s.importo)
```

---

{% include-markdown "signature-core.md" %}
