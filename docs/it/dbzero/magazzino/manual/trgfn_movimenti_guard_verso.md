## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_movimenti_guard_verso`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti), [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — dove è montato
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali) — il verso
>
Guide: [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) · brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.9)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**La rete del verso** (M-1): rifiuta un movimento — o un atteso — la cui quantità non ha il
segno della causale (`sign(qta) ≠ causali.segno`), con `E_MAG_MOVIMENTO_VERSO_INCOERENTE`.
È montato `BEFORE INSERT OR UPDATE OF qta, causale_id` su `movimenti` e su
`movimenti_attesi`: una funzione, due trigger.

### È tecnico, di proposito

Il verso non lo digita mai una persona: lo compone l'**operazione** dalla causale. Un
mismatch è quindi un chiamante rotto, non un dato sbagliato — classe `TECNICO`, nessun campo
da accendere nel form. La primitiva di scrittura (Lotto 2) darà il messaggio comprensibile
*prima* di arrivare qui; questo guard è la rete, e chi lo legge è `dbops.error_log`. Il
messaggio nomina la causale, il segno e la quantità.

### Due cose da sapere

* **La quantità zero cade qui**, non nel CHECK `qta <> 0`: un trigger `BEFORE ROW` scatta
  prima dei vincoli di tabella, e `sign(0) = 0` non è mai il segno di una causale. Il CHECK
  resta come seconda rete.
* **Una causale inesistente non è affar suo**: la funzione lascia parlare la FK, invece di
  dire «verso incoerente» su una causa che è un'altra.

Presidio: `db/pgtap/magazzino/test-movimenti-vincoli-v2.sql` (test 7 e 9) e
`test-movimenti-attesi-forma-v1.sql` (test 3 e 4).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
