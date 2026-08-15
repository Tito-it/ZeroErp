## 📘 Documentazione Concettuale – Funzione `vendite.fn_esito_gruppi_giro`

> 👀 **Vedi anche**
>
> **Su cosa è costruita:**
>
> • [vendite.vw_lotti_gruppi_serviti](/dbzero/vendite/views/vw_lotti_gruppi_serviti) — il **fatto**: cosa ciascun lotto ha servito
> • [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi) — il **richiesto**: il perimetro del giro, già persistito
>
> **Cosa non sostituisce:**
>
> • [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) — `gruppi_coperti` resta la diagnosi **prima** dell'esecuzione
> • [vendite.fn_diagnostica_gruppi_fatturabili](/dbzero/vendite/funzioni/fn_diagnostica_gruppi_fatturabili) — il **perché** un gruppo non è candidabile
>
> **Piano:** [brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-done/brief-db-emittibilita-visibile-e-sbloccabile) §8.2 / §9

---

### 🎯 Scopo Principale

(latest review 15-08-2026)

**Che fine ha fatto ogni gruppo di un giro di fatturazione.** Si passano i lotti
del giro e si riceve una riga per gruppo, con un verdetto fra tre:

```text
SERVITO             almeno un'attività del gruppo è finita su una fattura di questi lotti
NON_SERVITO         no, e restano righe non emesse → c'è lavoro fermo, si agisce
FATTURATO_ALTROVE   no, non resta nulla da emettere, e le righe risultano
                    fatturate da lotti DIVERSI da questi
```

---

### ⭐ Perché prende solo i lotti

Sembrerebbe naturale passarle anche l'elenco dei gruppi richiesti. Non serve, e
non doverlo fare **è** il punto.

`pipeline_repository.set_lotto_gruppi` scrive l'intera tupla richiesta su
**ogni** lotto del giro, nella stessa transazione che crea il lotto. Il
richiesto è quindi un dato persistito, non un parametro di chiamata: dai soli
`lotto_id` la funzione ricava richiesti **e** serviti, entrambi *misurati*.

Conseguenza: l'invarianza

```text
richiesti = serviti + non serviti
```

regge **per costruzione**, dentro una sola sede. Un parametro
`p_gruppi_richiesti` avrebbe riaperto la porta a passare la *previsione*
(`gruppi_coperti`) al posto della *misura* — che è esattamente il difetto da cui
questa funzione nasce.

E poiché i lotti sopravvivono al giro, la domanda si può rifare il giorno dopo:
era il secondo vincolo della richiesta.

---

### 🔒 Il cancello di scope, che è la trappola vera

Su questa catena la RLS è **asimmetrica**:

| con RLS | senza RLS |
| --- | --- |
| `commesse`, `commesse_attivita`, `fatture`, `fatture_righe`, `fatturazione_lotti` | `attivita_fatturabili`, `fatturazione_lotti_fatture`, **`fatturazione_lotti_gruppi`** |

Il perimetro **richiesto** è leggibile da chiunque, il **servito** no. Scritta in
modo ingenuo, la funzione risponderebbe `NON_SERVITO` a un operatore fuori scope
su un gruppo fatturato benissimo: un falso allarme con l'aria di un dato. Zero
non è una misura, è fail-closed.

Due presidi, entrambi deliberati:

1. **i lotti si validano prima.** Se anche uno solo non è visibile la funzione
   **solleva** `E_LOTTO_NON_TROVATO`, invece di rispondere su un perimetro
   dimezzato. «Non esiste» e «non lo puoi vedere» danno la stessa risposta di
   proposito: distinguerli sarebbe una fuga di informazione;
2. **il richiesto si legge attraverso `fatturazione_lotti`**, così passa dallo
   stesso cancello del servito.

---

### ⚠️ `n_attivita_residue` non è decorativo

Senza, la classificazione sarebbe sbagliata in modo *plausibile*. Un gruppo con
otto righe fatturate a marzo da un altro lotto e due righe di giugno rimaste
ferme risulterebbe `FATTURATO_ALTROVE` — perché righe fatturate altrove ce ne
sono — mentre le due di giugno sono esattamente il lavoro perso che si sta
cercando.

Il residuo è ciò che distingue *«non c'è più niente da fare»* da *«c'è ancora
tutto da fare»*, e va **misurato**, non dedotto. Per questo **l'ordine dei rami
è la regola**, e non è commutabile:

```text
1. fatturato qui?        → SERVITO
2. resta del non emesso? → NON_SERVITO      ← prima di «altrove», sempre
3. fatturato altrove?    → FATTURATO_ALTROVE
4. altrimenti            → NON_SERVITO
```

Il conteggio guarda le sole righe `NON_EMESSA` e non riapplica i criteri della
lane (approvata, tipo documento, competenza). Non è una semplificazione: il
**perché** una riga non sia candidata lo dice
`fn_diagnostica_gruppi_fatturabili`. Due funzioni per due domande, non due copie
della stessa regola.

---

### ℹ️ Il giro di massa

Un lotto massivo non ha perimetro persistito, quindi «richiesti» è vuoto. La
funzione non torna a mani vuote: restituisce i gruppi **serviti**, con
`richiesto = false`, e l'invarianza degenera in «serviti = serviti», che è vero.

La colonna `richiesto` esiste apposta perché la riga sia leggibile da sola,
senza che il chiamante debba sapere in quale modalità girava il giro.

---

### 🧾 Costo

La chiave di gruppo vale **~5 µs a chiamata** (misurato su 100.000 righe), e la
funzione la valuta una volta per riga dei gruppi in gioco. È una lettura su
richiesta: l'esito di un giro si apre, non si cicla.
