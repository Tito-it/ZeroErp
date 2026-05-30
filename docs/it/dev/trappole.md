# Trappole: cosa non fare

> Questa pagina raccoglie gli errori che fanno male — le "mine" già pestate almeno una volta.
> Ogni voce dice **cosa non fare**, **perché** e **cosa fare invece**. Leggerla all'inizio
> risparmia ore di lavoro perso e dati da recuperare.
>
> Non è un elenco di regole burocratiche: sono cose che, se sbagliate, rompono qualcosa di
> difficile da rimettere a posto.

---

## Git e Pull Request

### Non lasciare che GitHub cancelli i branch dopo il merge

L'opzione GitHub **"Automatically delete head branches"** cancella il branch di partenza
appena una PR viene unita. Su un branch di integrazione condiviso come `Tito-dev` questo è un
disastro: il branch sparisce per tutti.

- **Perché fa male:** `Tito-dev` non è un branch usa-e-getta, è il punto di integrazione del
  progetto. Cancellarlo blocca il lavoro di tutti.
- **Cosa fare invece:** tieni **disattivata** quell'opzione e proteggi `Tito-dev` e `main`
  nelle impostazioni del repository. Il flusso corretto resta: branch di lavoro
  (`dev/db-tid`, `dev/backend-tid`) → `Tito-dev` → `main`.

---

## Database e migrazioni

### Non toccare i changelog Liquibase già uniti o pubblicati

Una volta che un file di migrazione è stato mergiato o pushato su GitHub, **non si modifica
e non si cancella più**.

- **Perché fa male:** Liquibase calcola un "checksum" di ogni changeset già applicato. Se cambi
  un file vecchio, il checksum non torna più e la sequenza di migrazioni si rompe per tutti gli
  ambienti che l'avevano già applicata.
- **Cosa fare invece:** per aggiornare una funzione o un trigger, crea **sempre un file nuovo**
  con la numerazione successiva (es. `20260225-37-update-...`). Se hai modificato per errore un
  file vecchio, ripristinalo con `git checkout --`.

### Non scrivere a mano i periodi di validità

Le tabelle con validità nel tempo usano una colonna calcolata (tipo `daterange`) che il sistema
popola da solo a partire dalle date di inizio/fine.

- **Perché fa male:** quella colonna è il cuore dei controlli anti-sovrapposizione (es. due
  contratti attivi sullo stesso servizio). Scriverla a mano aggira il controllo e crea dati
  incoerenti. Lato backend la colonna è marcata come non modificabile (`editable=False`).
- **Cosa fare invece:** imposta solo le date di inizio e fine; lascia che il sistema calcoli il
  periodo. Vedi [Migrazione a daterange](/dev/work-done/migrazione-daterange).

### Non creare gli indici sulle chiavi esterne a mano

- **Perché fa male:** gli indici FK sono gestiti da una politica centralizzata
  (`dbops.apply_fk_index_policy()`). Crearne uno a mano genera duplicati e nomi fuori standard.
- **Cosa fare invece:** lascia fare alla policy; se serve un indice particolare, registralo
  secondo le convenzioni invece di crearlo al volo.

### Non scrivere a mano i campi di audit

I campi `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id` sono riempiti
automaticamente dai trigger.

- **Perché fa male:** valorizzarli a mano falsa la tracciabilità e può confliggere con i trigger.
- **Cosa fare invece:** non toccarli; sono gestiti dal database.

### Non usare un codice di errore generico

- **Perché fa male:** un errore "generico" (`E_GENERICO`) non dice nulla a chi legge i log e non
  può essere mappato a un'azione lato interfaccia.
- **Cosa fare invece:** usa un codice di errore **registrato** e specifico. Vedi
  [Messaggi di Errore e Generazione Log](/guide/Messaggi-di-Errore-e-Generazione-Log).

### Attenzione ai controlli "a blocco" sugli aggiornamenti/cancellazioni

Aggiungere un controllo molto restrittivo su un trigger (es. che blocca ogni modifica o
cancellazione) sembra prudente, ma può rompere test e flussi che prima funzionavano.

- **Cosa fare invece:** prima di aggiungere un guard del genere, verifica i test esistenti
  (pgTAP) per non bloccare casi legittimi.

---

## Architettura

### Non spostare la logica di business nel backend "per comodità"

In Zero ERP la logica di business vive nel **database** (funzioni, trigger, regole). Il backend
orchestra ed espone le API; il frontend mostra soltanto.

- **Perché fa male:** spostare una regola in Django "perché è più veloce da scrivere lì" la
  duplica o la sposta nel posto sbagliato. Prima o poi le due versioni divergono e nascono bug
  difficili da spiegare.
- **Cosa fare invece:** se è una regola di business, sta nel database. Se è orchestrazione (più
  passi, transazioni, integrazioni), sta nel backend. Mai la stessa regola in due posti.

### Non duplicare costanti, liste o configurazioni nel frontend

- **Perché fa male:** la stessa cosa scritta in due punti finisce per divergere.
- **Cosa fare invece:** i moduli condivisi stanno in `src/core/` (navigazione, costanti UI).
  Riusa, non ricopiare.

### Non aggiungere la Row-Level Security (RLS) a ogni dominio "per sicurezza"

L'RLS di PostgreSQL **non** è il meccanismo di autorizzazione generale del progetto, e non
va applicata a ogni tabella che sviluppi.

- **Perché è un equivoco:** l'autorizzazione dei documenti gestiti dall'**operatore interno**
  (preventivi, offerte, contratti, listini, commesse…) è data dal modello permessi a due livelli
  (area funzionale TUTTO/LETTURA/BLOCCATO + azioni di processo) con scope per emittente, applicato
  in Django. Mettere RLS dappertutto aggiunge complessità e rischio di filtri silenziosi senza
  aggiungere protezione reale.
- **Quando serve davvero l'RLS:** solo quando le tabelle di quel processo vengono lette
  **direttamente da un'identità esterna** (cliente portale, fornitore portale, shop), che deve
  vedere *soltanto le proprie righe*. È il caso delle policy ownership su `vendite.fatture`,
  `vendite.ordini`, `acquisti.ddt`, `anagrafiche.billing_account`, tabelle `shop`.
- **Cosa fare invece:** per un nuovo dominio interno, proteggilo con permessi area + azioni
  (es. `fn_available_actions_<dominio>`), non con RLS. Aggiungi una policy RLS *ownership* solo se/quando
  esponi quelle tabelle a un portale esterno. La regola: **RLS = confinamento per identità esterna,
  non autorizzazione interna.** Vedi [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
  e [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni).

---

## Dipendenze

### Non aggiungere dipendenze senza conferma

Niente nuove librerie Python (`requirements.in`) o npm (`package.json`) senza accordo preventivo.

- **Perché fa male:** ogni dipendenza è peso da mantenere, aggiornare e mettere in sicurezza.
- **Cosa fare invece:** proponi la dipendenza e attendi conferma prima di aggiungerla.

---

{% include-markdown "signature-core.md" %}
</content>
