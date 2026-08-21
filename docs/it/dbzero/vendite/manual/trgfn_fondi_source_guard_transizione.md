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
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — → `ANNULLATO` se la distinta contabile è `CHIUSA` (⚠️ dal 21-08-2026 l'atto non eseguito lo **cancella**, non lo riapre)
> • [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — → `ANNULLATO` quando la sorgente non è più capiente
> • `pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito` — `ASSEGNATO` → **`ESEGUITO`**, quando la riga contabile del fondo viene registrata
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-7

---

### 🎯 Scopo Principale
(latest review 22-08-2026)

**Quattro stati, e due da cui non si torna.**

```text
                  ┌──────────────────┐
                  │   DISPONIBILE    │◄────────────┐
                  └────────┬─────────┘             │
                           │  applica              │  disassegna
                           ▼                       │  (nessuno la percorre piu')
                  ┌──────────────────┐             │
                  │    ASSEGNATO     │─────────────┘
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │  la riga contabile
              │                         │  viene REGISTRATA
              ▼                         ▼
        ┌───────────────┐        ┌───────────────┐
        │   ANNULLATO   │        │   ESEGUITO    │
        └───────────────┘        └───────────────┘
           ← terminale              ← terminale
```

Ogni altra transizione è rifiutata con `E_FONDO_STATO_NON_AMMESSO`, e il
messaggio porta **da dove a dove** si stava andando.

---

### ⭐ Perché `ESEGUITO` è terminale (e perché esiste)

Un atto `ESEGUITO` descrive **un fatto già avvenuto**: il trasferimento è stato
registrato in contabilità. Uscire da lì non annullerebbe la registrazione — la
renderebbe soltanto **invisibile all'atto che l'ha prodotta**, cioè lo stesso
denaro contato due volte.

⭐ **Esiste perché `ANNULLATO` diceva tre cose diverse**: «non si deve fare più»,
«non si è più capienti» e «è già stato eseguito». Il terzo caso scriveva un
record che si contraddiceva — annullato, ma con la fattura figlia ancora
agganciata. Adesso ogni fatto ha la sua parola.

⚠️ E il guadagno non è di vocabolario: i tre lettori dei fondi filtrano tutti
sullo **stato**, quindi un atto che passa a `ESEGUITO` esce da tutti e tre senza
che nessuno di loro cambi.

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

### 🔴 ~~Tre stati, non quattro: `REVOCATO` non c'è~~ — il quarto è arrivato, ed è un altro

> ⚠️ **Il titolo qui sotto è rimasto perché la sua lezione vale ancora**, ma la
> conclusione è superata: dal 21-08-2026 gli stati sono **quattro**. Il quarto
> però non è `REVOCATO` e non serve a riemettere niente: è `ESEGUITO`, e
> descrive un fatto che prima non aveva un nome. La differenza è tutta qui —
> uno stato per un meccanismo che non esiste è debito, uno stato per un fatto
> che accade è la parola che mancava.

Il piano nella sua prima stesura aveva un quarto stato, per il meccanismo di
**revoca + riemissione**: si annullava il fondo vecchio e se ne emetteva uno
aggiornato quando l'importo cambiava.

Quel meccanismo è **caduto insieme al ricalcolo**. Da quando una fattura
sorgente `DEFINITIVA` ha un fondo definitivo, non c'è niente da riemettere — e
uno stato che esiste per un meccanismo che non esiste è la forma più costosa di
debito, perché va spiegato a ogni lettura.

---

### ⚠️ `ASSEGNATO` → `DISPONIBILE` resta ammesso, ma non lo percorre più nessuno

Era il **reset tecnico della figlia**: il lotto tornava in bozza, la fattura che
usava il fondo spariva, e il fondo tornava spendibile. Non era una reazione a un
pagamento — nessun incasso apre o chiude un fondo — ed è la ragione per cui la
freccia di ritorno esiste.

> 🔵 **Dal 21-08-2026 quel percorso non lo fa più nessuno**: il reset
> **cancella** l'atto non eseguito invece di riaprirlo, perché riaprirlo
> significava riportarsi dietro l'importo vecchio congelato. La transizione
> resta ammessa come unica strada per disfare l'assegnazione *senza* cancellare
> l'atto — ed è un candidato dichiarato alla rimozione, non una svista. Toglierla
> è una decisione di dominio: si prende, non si fa passando.
>
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
* ⚠️ **Non è un lookup di transizioni.** Sono quattro valori interni, senza
  etichette da tradurre né azioni di UI da abilitare: una tabella di transizioni
  ammesse sarebbe una configurazione che nessuno configura. (Diverso il caso
  delle righe contabili di `pagamenti`, dove la matrice *è* una tabella: là gli
  stati li muove un operatore.)

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
