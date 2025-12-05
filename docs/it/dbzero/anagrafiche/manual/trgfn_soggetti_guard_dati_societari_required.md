## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_soggetti_guard_dati_societari_required()`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**   
>
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> • [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)   
> • [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)   
>
> **Approfondimento Funzioni/Trigger:**   
>
> • [anagrafiche.trgfn_dati_societari_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_guard_tipo_soggetto)   
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

### 🎯 Scopo Principale
(latest review 03-12-25)
Garantire che, per tutti i **soggetti** la cui tipologia dettagliata prevede una policy **dati societari obbligatoria**, esista **almeno una riga** associata in `anagrafiche.dati_societari`.


La funzione implementa il vincolo di dominio derivato dalla colonna:

```sql
config.tipi_soggetto_dettaglio.dati_societari_policy
```

che può assumere i valori:

| Policy       | Significato                                 | Obbligo su `dati_societari`                                     |
| ------------ | ------------------------------------------- | --------------------------------------------------------------- |
| **NONE**     | Il tipo soggetto NON prevede dati societari | ❌ Devono *non* esistere righe (bloccato da altra guard)         |
| **OPTIONAL** | I dati societari sono facoltativi           | ⚪ Possono esserci 0 o 1 righe                                   |
| **REQUIRED** | I dati societari sono obbligatori           | ✅ **Deve** esistere 1 riga (vincolo gestito da questa funzione) |

> 🔎 **Nota:**
>
> * L’ammissibilità all’inserimento su `anagrafiche.dati_societari` è gestita da:
>   `anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()`.
> * L’obbligatorietà di avere una riga per policy **`REQUIRED`** è invece responsabilità di questa funzione, eseguita tramite **constraint trigger DEFERRABLE** su `anagrafiche.soggetti`.

---

### 🧩 Come Funziona

La funzione `anagrafiche.trgfn_soggetti_guard_dati_societari_required()` è pensata per essere eseguita come **CONSTRAINT TRIGGER**:

* **AFTER INSERT OR UPDATE** su `anagrafiche.soggetti`
* **DEFERRABLE INITIALLY DEFERRED** → il controllo avviene tipicamente a fine transazione

In questo modo è possibile, all’interno della *stessa* transazione:

1. Inserire/aggiornare il soggetto (`anagrafiche.soggetti`)
2. Inserire i relativi dati societari (`anagrafiche.dati_societari`)
3. Fare commit: il constraint trigger verifica la coerenza complessiva.

### Passi logici principali

1. **Verifica presenza tipo_soggetto_dettaglio**

   Se `NEW.tipo_soggetto_dettaglio_id` è `NULL`, la funzione **non applica alcun controllo** e ritorna `NEW`.

   > Questo permette di mantenere una fase di configurazione “soft”; in futuro la regola potrà essere irrigidita se necessario.

2. **Lettura policy dal tipo soggetto dettagliato**

   La funzione legge da `config.tipi_soggetto_dettaglio`:

   * `dati_societari_policy`
   * `codice_interno` (utile per logging applicativo)

   tramite la chiave `NEW.tipo_soggetto_dettaglio_id`.

3. **Tipo non configurato**

   Se non viene trovata alcuna riga o `dati_societari_policy` è `NULL`, viene generato un errore applicativo:

   * **`E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO`**

   perché non è possibile determinare se i dati societari siano richiesti o meno.

4. **Policy diversa da REQUIRED**

   Se `dati_societari_policy` è **`NONE`** o **`OPTIONAL`**, la funzione **non applica alcun controllo aggiuntivo** e ritorna `NEW`.

   > Il divieto di inserire dati societari per policy `NONE` è già gestito da
   > `trgfn_dati_societari_guard_tipo_soggetto()` sul lato tabella `dati_societari`.

5. **Policy REQUIRED: controllo obbligatorietà**

   Se `dati_societari_policy = 'REQUIRED'`, la funzione verifica che esista **almeno una riga** in:

   ```sql
   anagrafiche.dati_societari
   WHERE soggetto_id = NEW.id
   ```

   * Se **nessuna riga è presente**, viene sollevato un errore applicativo:

     * **`E_DATI_SOCIETARI_REQUIRED_MANCANTI`**
   * Se una riga esiste, il controllo è superato e la funzione ritorna `NEW`.

L’unicità di `dati_societari` per soggetto è normalmente garantita dal vincolo `UNIQUE(soggetto_id)` definito sulla tabella.

---

### 🚨 Errori Gestiti

| Codice errore                                       | Quando si verifica                                                                                   |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO** | Il `tipo_soggetto_dettaglio` associato al soggetto non è configurato correttamente (policy mancante) |
| **E_DATI_SOCIETARI_REQUIRED_MANCANTI**              | La policy è `REQUIRED` ma non esiste alcuna riga in `anagrafiche.dati_societari` per il soggetto     |

Entrambi gli errori vengono sollevati tramite:

```sql
script.fn_log_and_raise_error(
    'database',
    'anagrafiche.trgfn_soggetti_guard_dati_societari_required',
    '<CODICE_ERRORE>',
    jsonb_build_object(
        'soggetto_id', NEW.id,
        'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
        'codice_interno', v_cod_int_tipo,
        'dati_societari_policy', v_policy
    ),
    NEW.tx_id,
    NEW.id::text,
    COALESCE(v_cod_int_tipo, '<NULL>')
);
```

---

### 🔗 Relazioni con altri trigger e funzioni

Questa funzione è **complementare** a:

* **`anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()`**

  * valida, lato `dati_societari`, *se* sia lecito inserire una riga per uno specifico soggetto
  * impedisce inserimenti per policy `NONE`.

Insieme i due trigger realizzano la seguente matrice di comportamento:

| Policy       | Su `dati_societari` (guard)            | Su `soggetti` (constraint REQUIRED)                     |
| ------------ | -------------------------------------- | ------------------------------------------------------- |
| **NONE**     | Inserimento vietato (errore immediato) | Nessun controllo specifico (impossibile avere dati)     |
| **OPTIONAL** | Inserimento ammesso                    | Nessun obbligo di presenza                              |
| **REQUIRED** | Inserimento ammesso                    | Obbligo di presenza: errore se manca una riga collegata |

---

### 🧪 Implicazioni sui test e sulla transazionalità

Essendo un **constraint trigger DEFERRABLE**:

* il controllo può essere **posticipato a fine transazione**;
* è possibile creare **nella stessa transazione**:

  * il soggetto con policy `REQUIRED`;
  * il relativo record in `dati_societari`;
  * solo al momento del `COMMIT` (o di un `SET CONSTRAINTS ALL IMMEDIATE`) viene verificata la coerenza.

Nei test automatizzati (es. pgTAP) è consigliato:

* usare `SET CONSTRAINTS ALL IMMEDIATE;` per forzare l’esecuzione del controllo
  all’interno del blocco di test;
* verificare esplicitamente i casi:

  * `REQUIRED` **senza** `dati_societari` → errore atteso;
  * `REQUIRED` **con** `dati_societari` → transazione valida.

---

### 💡 Note Implementative

* La funzione **non introduce logica di business duplicata**: la regola di obbligatorietà
  è derivata esclusivamente dalla configurazione in `config.tipi_soggetto_dettaglio`.
* Il fatto che il trigger sia **DEFERRABLE INITIALLY DEFERRED** lo rende compatibile
  con i flussi applicativi che creano soggetto + dati societari in un unico salvataggio.
* L’aggiunta di nuove policy o la modifica del comportamento potrà avvenire in modo
  centralizzato agendo sulla configurazione, mantenendo la funzione stabile nel tempo.

> 🧠 **"La coerenza sui dati societari è un vincolo di dominio configurabile, non hardcoded: la funzione applica la policy, non la definisce."**
