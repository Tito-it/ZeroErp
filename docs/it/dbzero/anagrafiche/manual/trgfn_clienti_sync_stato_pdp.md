## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_sync_stato_pdp()`
>
👀 **Vedi anche**
>
**Approfondimeto tabelle:**
>
• [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)  
> • [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)   
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)   
> • [config.stati_pdp](/dbzero/config/tabelle/stati_pdp)   
>
**Approfondimento funzioni:**   
>
• [`anagrafiche.trgfn_clienti_set_periodo()`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo)    
> • [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)  

---
### 🎯 Scopo Principale
(latest review 09-12-25)
La funzione `anagrafiche.trgfn_clienti_sync_stato_pdp()` è una **trigger function di dominio** che sincronizza lo **stato tecnico del PDP** (`anagrafiche.pdp.stato_pdp_id`) in base al cambio di **stato commerciale** del cliente (`anagrafiche.clienti.stato_cliente_id`).

In sintesi:

* quando un cliente diventa **ATTIVO** → il PDP passa in stato **ATT** (attivo);
* quando un cliente viene **CHIUSO** e non ci sono più clienti attivi su quel PDP (regola estendibile) → il PDP torna in stato **DISP** (disponibile);
* negli altri casi lo stato del PDP **non viene toccato**.

La funzione è pensata per essere richiamata da un trigger `AFTER INSERT OR UPDATE` su `anagrafiche.clienti`.

---

### Contesto e campi interessati

  **Tabella: `anagrafiche.clienti`**

Campi utilizzati direttamente:

* `pdp_id`            → FK verso `anagrafiche.pdp(id)`; se NULL, non viene eseguita alcuna sincronizzazione.
* `stato_cliente_id`  → FK verso `config.stati_cliente(id)`; determina la logica applicata.
* `tx_id`             → identificativo di transazione per logging.

> ☝️ Il legame fra cliente e PDP è mantenuto coerente a monte dalla funzione
> `anagrafiche.trgfn_clienti_sync_pdp()`.

  **Tabella: `config.stati_cliente`**

La funzione legge:

* `codice_interno` → per distinguere gli stati cliente, in particolare:

  * `AT` → cliente attivo;
  * `CH` → cliente chiuso.

  **Tabella: `config.stati_pdp`**

La funzione utilizza i seguenti codici interni:

* `ATT`  → PDP attivo (c’è almeno un cliente commerciale attivo);
* `DISP` → PDP disponibile (nessun cliente commerciale attivo).

Gli ID corrispondenti vengono risolti dinamicamente tramite query su `config.stati_pdp`.

  **Tabella: `anagrafiche.pdp`**

Campi aggiornati:

* `id`            → identificatore del punto di prelievo;
* `stato_pdp_id`  → FK verso `config.stati_pdp`, aggiornato in base allo stato cliente.

---

### Logica di funzionamento

 0️⃣ Nessun PDP collegato

Se `NEW.pdp_id IS NULL`:

```sql
IF NEW.pdp_id IS NULL THEN
    RETURN NEW;
END IF;
```

➡️ La funzione **non effettua alcuna sincronizzazione**. Il cliente non è associato a un punto di prelievo, quindi non esiste uno stato tecnico da aggiornare.

---

 1️⃣ Recupero dello stato cliente

La funzione deriva il codice interno dello stato cliente:

```sql
SELECT sc.codice_interno
INTO v_cd_stato_cliente
FROM config.stati_cliente sc
WHERE sc.id = NEW.stato_cliente_id;

IF v_cd_stato_cliente IS NULL THEN
    RETURN NEW; -- stato non trovato → non interveniamo
END IF;
```

Se lo stato non è trovato (configurazione errata), la funzione **non prosegue** con la sincronizzazione.

---

 2️⃣ Stati cliente rilevanti

Attualmente la funzione considera **solo** due stati cliente:

* `AT` → attivo;
* `CH` → chiuso.

```sql
IF v_cd_stato_cliente NOT IN ('AT', 'CH') THEN
    RETURN NEW;
END IF;
```

Tutti gli altri stati (`AN`, sospeso, voltura tecnica, ecc.) **non modificano** lo stato tecnico del PDP e sono gestiti da processi specifici.

---

 3️⃣ Risoluzione degli stati tecnici del PDP

La funzione recupera gli ID corrispondenti ai codici:

```sql
SELECT id INTO v_stato_att_id
FROM config.stati_pdp
WHERE codice_interno = 'ATT';

SELECT id INTO v_stato_disp_id
FROM config.stati_pdp
WHERE codice_interno = 'DISP';
```

Se uno dei due non è configurato, viene invocata `script.fn_log_and_raise_error` per segnalare un errore di configurazione:

```sql
IF v_stato_att_id IS NULL OR v_stato_disp_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'database',
        'anagrafiche.trgfn_clienti_sync_stato_pdp',
        'E_CODICE',
        jsonb_build_object(
            'config.stati_pdp: stati tecnici ATT / DISP non configurati correttamente)',
            'att/disp missing'
        ),
        NEW.tx_id,
        'ATT/DISP',
        'config.stati_pdp'
    );
END IF;
```

Questo impedisce aggiornamenti inconsapevoli in presenza di configurazioni incomplete.

---

 4️⃣ Sincronizzazione vera e propria

 Caso A – Cliente **ATTIVO** (`AT`)

Se `v_cd_stato_cliente = 'AT'`:

```sql
UPDATE anagrafiche.pdp p
SET stato_pdp_id = v_stato_att_id
WHERE p.id = NEW.pdp_id
  AND p.stato_pdp_id IS DISTINCT FROM v_stato_att_id;
```

* Il PDP viene portato nello stato tecnico **ATT** (attivo).
* L’UPDATE è condizionato da `IS DISTINCT FROM` per evitare scritture inutili.

> L’ipotesi di dominio è che l’attivazione del cliente implichi un PDP
> tecnicamente attivo, salvo casi particolari (es. dismissione tecnica) gestiti altrove.

---

 Caso B – Cliente **CHIUSO** (`CH`)

Se `v_cd_stato_cliente = 'CH'`:

```sql
UPDATE anagrafiche.pdp p
SET stato_pdp_id = v_stato_disp_id
WHERE p.id = NEW.pdp_id
  AND p.stato_pdp_id IS DISTINCT FROM v_stato_disp_id;
```

* Il PDP viene portato nello stato **DISP** (disponibile), indicando che dal punto di vista commerciale non ci sono più clienti attivi.

> Estensione possibile
> Nella versione corrente la funzione non verifica l’esistenza di altri clienti ATTIVI sullo stesso PDP.
> È però progettata (come da commenti iniziali) per essere estesa in futuro includendo un controllo del tipo:
>
```sql
> SELECT COUNT(*)
> FROM anagrafiche.clienti c
> JOIN config.stati_cliente sc
> ON sc.id = c.stato_cliente_id
> WHERE c.pdp_id = NEW.pdp_id
> AND sc.codice_interno = 'AT'
> AND c.id <> NEW.id;
> ```
>
In tal caso, il passaggio a `DISP` verrebbe effettuato **solo se non esistono altri clienti attivi**.

---

### Trigger associato (schema suggerito)

Esempio di collegamento della funzione:

```sql
CREATE OR REPLACE TRIGGER trg_clienti_a20_sync_stato_pdp_aft_ins_upd
    AFTER INSERT OR UPDATE OF stato_cliente_id, pdp_id
    ON anagrafiche.clienti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp();
```

> ⚠️ La scelta di `AFTER` è importante: consente alla funzione di vedere il record
> già validato da altri trigger (es. `trgfn_clienti_set_periodo`).

---

### Benefici del disegno

* Mantiene **allineati dominio commerciale e dominio tecnico**: lo stato del PDP riflette le condizioni di attivazione/chiusura dei clienti.
* Centralizza le regole di mapping stato cliente → stato PDP in una singola funzione.
* Facilita l’evoluzione futura (es. gestione stati intermedi o multipli clienti) senza toccare la logica applicativa.

In sintesi, `anagrafiche.trgfn_clienti_sync_stato_pdp()` è il punto di coordinamento fra il ciclo di vita del cliente e lo stato tecnico del punto di prelievo, garantendo coerenza fra i diversi livelli del modello Zero ERP.
