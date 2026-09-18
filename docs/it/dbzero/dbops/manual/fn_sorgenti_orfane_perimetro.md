## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane_perimetro`

> 👀 **Vedi anche**
>
> • [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane), [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane)
> • [script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata) — il contratto
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.7, §6-ter C16)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Le tabelle che il presidio degli orfani esamina**, rese visibili: quelle con una chiave
esterna verso `config.sorgenti` su una colonna sola, le due colonne di chiave
(`sorgente_riga`, `sorgente_uid`) **e il guard tipizzato montato**. È il guard il contratto
del «modello A» (tipo ⇒ esattamente una chiave verso il bersaglio dichiarato): le tabelle di
vendite con la stessa chiave esterna e le stesse colonne hanno un'altra semantica (la riga è
la riga del documento, l'uid è il documento) e senza questo filtro davano 112 falsi orfani
(misurato il 18-09). Entreranno quando prenderanno il guard.

⭐ Esiste perché un presidio che esamina zero tabelle è verde e muto: il pgTAP asserisce che
le sei di magazzino ci sono. Derivato dal catalogo, non da un elenco — una tabella nuova con
quella forma entra da sola.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-25`).

---

{% include-markdown "signature-core.md" %}
