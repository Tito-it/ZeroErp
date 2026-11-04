## 📘 Documentazione Concettuale – Vista `dbops.vw_credenziali_da_sanare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di una credenziale
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento viste:
>
> * [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) — da cui si legge «nessun accesso»
>
> Approfondimento funzioni:
>
> * [script.fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema) — distingue una veste di macchina da una di persona
> * [anagrafiche.trgfn_identita_digitali_guard_natura_credenziale](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_natura_credenziale) — il guard che oggi rifiuta le credenziali miste
> * [script.fn_elimina_credenziale](/dbzero/script/funzioni/fn_elimina_credenziale) — il gesto che sana una credenziale senza vesti

---

### 🎯 Scopo Principale

**Presidio a zero delle credenziali**: una riga per ogni credenziale da sanare, con il
motivo. Deve restare vuota.

---

### I due motivi

| Motivo | Che cosa vuol dire | Come si sana |
| --- | --- | --- |
| `NESSUNA_VESTE` | la credenziale non ha alcuna veste, nemmeno spenta: non entra da nessuna porta, e la lista degli operatori non la mostra | dandole una veste, o cancellandola. Spegnerla in Django non basta: resta una credenziale senza veste |
| `PERSONA_E_SISTEMA` | sulla stessa credenziale ci sono vesti di persona e vesti di macchina | separando le due nature su due credenziali |

Il guard sulla natura della credenziale oggi rifiuta le credenziali miste: qui escono quelle
nate prima del guard, e quelle prodotte da una gara fra due transazioni.

---

### ⭐ Una credenziale con sole vesti spente non entra

Una credenziale che ha vesti, tutte spente, è una persona disattivata: uno stato legittimo,
non un difetto. Per questo `NESSUNA_VESTE` non si calcola qui: si legge dalla colonna
«nessun accesso» di [vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri), così la
regola che dice quando una credenziale non ha accessi è una sola.

---

### Nel catalogo dei presidi

In [dbops.presidi](/dbzero/dbops/tabelle/presidi) è un presidio a zero, letto ogni
settimana perché non segnala un incidente di oggi, e col conteggio libero dalla sicurezza
per riga: la vista degli accessi attraversa i clienti solo per gli elenchi di clienti
collegati, non per le righe. Chi agisce è l'amministratore.

La vista è `security_invoker`: le tabelle sotto si leggono coi privilegi di chi interroga.

---

### Test

* `db/pgtap/anagrafiche/test-area-accessi-v1.sql` — `NESSUNA_VESTE` per la credenziale senza
  vesti e non per quella con sole vesti spente; `PERSONA_E_SISTEMA` per una credenziale mista
  costruita a guard spento; la vista è `security_invoker`; il presidio è a catalogo.
* `db/pgtap/config/test-elimina-credenziale-v1.sql` — la credenziale senza vesti, cancellata
  dal suo gesto, esce dal presidio.

---

### Note di migrazione

* 2026-10-02 — nasce con l'area accessi (`brief-db-be-fe-area-accessi`, R-DB-2).

---

{% include-markdown "signature-core.md" %}
