## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fondi_source_guard_transizione`

> 👀 **Vedi anche**
>
> **Tabella sorvegliata:**
>
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — trigger `trg_fatture_fondi_fattura_source_a10_guard_transizione_upd`
>
> **Gli altri due presidi della stessa tabella:**
>
> • [vendite.trgfn_fondi_source_guard_importo](/dbzero/vendite/funzioni/trgfn_fondi_source_guard_importo) — il fondo assomiglia alla sua sorgente
> • `trg_fatture_fondi_fattura_source_a10_lock_atto_upd` — le colonne dell'atto non si riscrivono (`script.trgfn_lock_columns`)
>
> **Chi muove gli stati:**
>
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) — `DISPONIBILE` → `ASSEGNATO`
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — `ASSEGNATO` → `DISPONIBILE`, e → `ANNULLATO` se la contabile è `CHIUSA`
> • [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — → `ANNULLATO` quando la sorgente non è più capiente
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-7

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Tre stati, e uno solo da cui non si torna.**

```text
                  ┌──────────────────┐
                  │   DISPONIBILE    │◄────────────┐
                  └────────┬─────────┘             │
                           │  applica              │  reset TECNICO
                           ▼                       │  (la figlia torna in bozza)
                  ┌──────────────────┐             │
                  │    ASSEGNATO     │─────────────┘
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌───────────────────────────────────┐
        │           ANNULLATO               │   ← terminale
        └───────────────────────────────────┘
```

Ogni altra transizione è rifiutata con `E_FONDO_STATO_NON_AMMESSO`, e il
messaggio porta **da dove a dove** si stava andando.

---

### ⭐ Perché `ANNULLATO` è terminale

Un fondo annullato è **denaro che qualcuno ha tolto dal tavolo** — una regola
(la sorgente non è più capiente) o una persona (il processo rimborsi). Riaprirlo
con un `UPDATE` rimetterebbe in gioco quella cifra **senza che nessuno l'abbia
deciso una seconda volta**, e senza lasciare traccia della prima decisione.

Se quel fondo serve di nuovo, si compie un **atto nuovo**: è la stessa regola per
cui un atto non si modifica ma si annulla con un altro atto. La differenza si
vede quando si va a leggere: due righe raccontano che è successo due volte, una
riga riscritta racconta che non è mai successo.

---

### 🔴 Tre stati, non quattro: `REVOCATO` non c'è

Il piano nella sua prima stesura aveva un quarto stato, per il meccanismo di
**revoca + riemissione**: si annullava il fondo vecchio e se ne emetteva uno
aggiornato quando l'importo cambiava.

Quel meccanismo è **caduto insieme al ricalcolo**. Da quando una fattura
sorgente `DEFINITIVA` ha un fondo definitivo, non c'è niente da riemettere — e
uno stato che esiste per un meccanismo che non esiste è la forma più costosa di
debito, perché va spiegato a ogni lettura.

---

### ⚠️ `ASSEGNATO` → `DISPONIBILE` resta ammesso, e non è un ripensamento

È il **reset tecnico della figlia**: il lotto torna in bozza, la fattura che
usava il fondo sparisce, e il fondo torna a essere spendibile. Non è una
reazione a un pagamento — nessun incasso apre o chiude un fondo — ed è la
ragione per cui la freccia di ritorno esiste.

> Chi cerca «cosa succede al fondo se la sorgente viene pagata dopo» trova la
> risposta in [fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura),
> che lo dichiara nel proprio `COMMENT`: **niente**.

---

### Regole principali

* Montato `BEFORE UPDATE OF stato FOR EACH ROW`: gli aggiornamenti che non
  toccano lo stato non pagano nulla.
* **Esce in testa** se `NEW.stato` non è distinto da `OLD.stato` — un `UPDATE`
  che riscrive lo stesso valore non è una transizione.
* Uno stato di partenza **fuori vocabolario** cade nel ramo `ELSE FALSE`: il
  guard è fail-closed anche verso i dati che non dovrebbero esistere. Il
  vocabolario in sé lo presidia il `CHECK chk_fondi_source_stato`.
* ⚠️ **Non è un lookup di transizioni.** Sono tre valori interni, senza etichette
  da tradurre né azioni di UI da abilitare: una tabella di transizioni ammesse
  sarebbe una configurazione che nessuno configura.

---

### ⚠️ Non confondere con il lock delle colonne

Sono due presidi diversi montati sulla stessa fase e sulla stessa tabella:

| | Che cosa difende | Errore |
| --- | --- | --- |
| **questo guard** | il **cammino** fra gli stati | `E_FONDO_STATO_NON_AMMESSO` |
| `..._a10_lock_atto_upd` | l'**identità** dell'atto (`importo`, sorgente, tipo, `origine`) | `E_FONDO_ATTO_IMMUTABILE` |

Il primo dice «da qui non si va lì», il secondo dice «questo non si tocca, mai».
Insieme rendono la riga un **atto**: una cosa che si compie e si annulla, non un
valore che si aggiorna.

---

{% include-markdown "signature-core.md" %}
