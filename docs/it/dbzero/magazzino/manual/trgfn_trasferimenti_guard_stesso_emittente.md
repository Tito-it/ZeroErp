## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_trasferimenti_guard_stesso_emittente`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — dove è montato
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'emittente dei due magazzini
>
Guide: [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) · brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Nessuna operazione di magazzino attraversa due emittenti** (M-6). Un trasferimento ha due
magazzini, e il perimetro RLS della tabella poggia su quello di **origine**: questo guard
copre la **destinazione**, rifiutando un trasferimento i cui magazzini appartengono a
emittenti diversi (`E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`). Fra due emittenti sarebbe una
cessione, con un documento, non uno spostamento interno.

### È un dato errato, e il form lo sa

La destinazione la sceglie una persona: classe `DATO_ERRATO`, campo `magazzino_id_to`,
messaggio che nomina i due magazzini. Il frontend accende il campo giusto.

### Sotto RLS, un magazzino che non si vede non è proprio

La funzione legge `magazzini` con i diritti di chi scrive: per un operatore, un magazzino
fuori perimetro **non risolve** (mentre la FK, che la RLS non la vede, passerebbe). Si
rifiuta anche allora, con lo stesso codice — dal punto di vista di chi scrive, un magazzino
che non può vedere non è del suo emittente. È fail-closed.

Presidio: `db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql` (test 9).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
