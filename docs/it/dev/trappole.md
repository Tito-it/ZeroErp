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

> Ogni voce dice in breve **che cosa** e **perché**; la regola intera sta nella sua sede,
> linkata. Se una voce qui e la sua sede dicono cose diverse, vale la sede.

### Non toccare i changelog Liquibase già uniti o pubblicati

Liquibase tiene il checksum di ogni changeSet applicato: un file vecchio cambiato rompe la
catena per tutti gli ambienti. Per cambiare una funzione o un trigger si scrive un file **nuovo**
con la numerazione successiva, partendo dal corpo della **doc auto-generata**, non da uno YAML
vecchio. Gli altri divieti che passano su dev e muoiono in CI (`runOnChange`, `preCondition` sui
seed, privilegi a mano…) sono in [Linee Guida SQL](/linee-guida-sql) §11, ognuno col suo
guardrail.

### Non scrivere a mano i periodi di validità, i campi di audit, gli indici delle FK

Sono calcolati o generati: la colonna `daterange` dalle date di inizio e fine (è lei che regge
l'anti-sovrapposizione), `data_insert`/`user_*`/`tx_id` dai trigger, gli indici FK dalla policy
centralizzata. Scriverli a mano aggira il controllo o crea duplicati. Sedi:
[Linee Guida SQL](/linee-guida-sql) §7 (audit), §7b (validità), §8.7 (indici FK, «Mai a mano»).

### Non usare un codice di errore generico

`E_GENERICO` non dice niente a chi legge i log e non si traduce in un'azione a video. Si usa un
codice **registrato** e specifico, sollevato da una delle due funzioni previste:
[Linee Guida SQL](/linee-guida-sql) §5 «Due funzioni per sollevare» e
[Messaggi di Errore e Generazione Log](/guide/Messaggi-di-Errore-e-Generazione-Log).

### Non aggiungere un guard restrittivo senza cercare chi lo attraversa

Un guard che blocca un UPDATE o una DELETE sembra prudente, ma rompe i flussi e i test che
passavano di lì. Prima di scriverlo si cercano nei pgTAP e nelle funzioni madri le scritture che
lo attraversano.

### Non spegnere un blocco con una GUC

Un blocco che si spegne con `SET zeroerp.qualcosa = on` non è un cancello: le GUC personalizzate
le imposta anche il ruolo applicativo, quindi l'immutabilità diventa una disciplina del backend.
Un bypass, quando serve, si lega al **ruolo** (`fn_is_proprietario_tabella`, come fa
`zeroerp.ddt_cambio_stato`). ⚠️ Le GUC di bypass esistenti sono ancora slegate: la decisione
è aperta (D17 Q-2 della
[valutazione DB](/dev/work-in-progress/migliorie-generali-da-test-valutazione)). Non se ne
aggiungono di nuove.

### Non contare su `UPDATE OF colonna` per dire «quando la colonna cambia»

Scatta se la colonna è nel `SET`, a prescindere dal valore, e **non** scatta se la colonna la
cambia un altro trigger `BEFORE`. Un guard o una propagazione scritti su quell'equivoco si
aggirano da soli: è successo con le quantità dei componenti del kit e con la catena delle
istanze. Sede: [Linee Guida Trigger](/linee-guida-trigger), «Cosa fa davvero `UPDATE OF`».

### Non dare a una `SECURITY DEFINER` un `search_path` «prudente» uguale per tutte

`pg_temp` va sempre elencato e per ultimo. Ma `pg_catalog, pg_temp` toglie di vista le
estensioni, che stanno in `public` (`dblink`, `unaccent`…): dentro un `EXCEPTION WHEN OTHERS`
la funzione non dà errore, smette di funzionare in silenzio. Si decide **per funzione**: o si
qualifica la chiamata (`public.dblink(...)`), o `public` resta nell'elenco. Presidio:
`db/pgtap/dbops/test-security-definer-search-path-v1.sql`, con due soglie che possono solo
calare.

### Non far nascere una tabella fuori dal perimetro dei dati

Una tabella nuova con una FK verso una tabella protetta dalla RLS è dentro il perimetro, anche
se nessuno la elenca: o porta la sua policy, o va dichiarata con la ragione in
`dbops.rls_perimetro_debito`. Il presidio (`vw_rls_perimetro_scoperto`) la vede da solo e fa
rosso il pgTAP. Lo storico invece non si scrive a mano: la policy della shadow la genera il
framework. Sede: [Linee Guida SQL](/linee-guida-sql) §10 (checklist §10.9).

---

## Test pgTAP

### Non cercare il mondo: costruiscilo

Una fixture che pesca «il primo cliente che c'è» passa sul database di sviluppo e, su un
database ricostruito da zero (la CI), non trova niente: salta, e un test saltato conta verde.
Il mondo si costruisce con i builder di `dbops` (`fn_pgtap_crea_*`), prima della riga di
contesto. Sede: [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test), «Le
fixture».

### Non scrivere una data a mano, e non usare `CURRENT_DATE`

Una data letterale che passa da una regola temporale (finestra di emissione, scadenze,
congelamenti) fa un test verde il giorno in cui nasce e rosso qualche settimana dopo, senza che
nessuno abbia toccato niente. E `CURRENT_DATE` è il giorno della sessione, non quello
dell'azienda. Si scrive relativo a `script.fn_data_operativa()`. Sede: la guida pgTAP,
«“Oggi” è il giorno dell'azienda».

### Non asserire «un errore qualunque»

`throws_ok(sql, NULL, NULL)` accetta anche l'errore sbagliato: due volte un test è risultato
verde per un errore che non era quello della regola. Si asserisce il codice. Sede: la guida
pgTAP, «Un errore si asserisce, non si spera»; il debito che resta ha una soglia in
`scripts/guardrail_pgtap_preambolo.py`.

### Non provare da owner ciò che gira come applicazione

L'owner non vede la RLS e ha privilegi che l'applicazione non ha: un test o una misura presi da
owner provano un altro sistema. Si gira come `zeroerp_app`; l'eccezione si dichiara nel file
con `pgtap-runner: owner` e il motivo. Sede: la guida pgTAP, «Quando il test non può girare
come l'applicazione».

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

### Non lasciare il perimetro dei dati al backend

La RLS **è** il perimetro dei dati per tutte le vesti, operatore interno compreso: un
operatore vede solo le righe degli emittenti della sua whitelist, e il filtro lo applica la
policy, non una `WHERE` scritta in Django. Dal settembre 2026 il perimetro copre l'intero
dominio documento, righe e satelliti compresi, e le versioni di storico.

- **Perché fa male:** un filtro scritto a mano nel backend vale solo per le strade che lo
  attraversano. Una vista, una funzione o un endpoint nuovi lo saltano, e senza un errore.
- **Ma non dappertutto:** le tabelle senza uno scope (configurazione, lookup, `dbops`, log) non
  vanno in RLS. Una policy «preventiva» dà falsa sicurezza e costa manutenzione.
- **Cosa fare invece:** per decidere se una tabella sta dentro, si guarda il suo legame con una
  tabella protetta (vedi «Non far nascere una tabella fuori dal perimetro dei dati», qui sopra).
  Il permesso di **fare** un'azione (area TUTTO/LETTURA/BLOCCATO, azioni di processo) è un'altra
  cosa e resta nel modello dei permessi. Sedi: [Linee Guida SQL](/linee-guida-sql) §10 e
  [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni#63-ambito-dati-whitelist-ef-per-operatori-rls-per-portaleshop).

---

## Dipendenze

### Non aggiungere dipendenze senza conferma

Niente nuove librerie Python (`requirements.in`) o npm (`package.json`) senza accordo preventivo.

- **Perché fa male:** ogni dipendenza è peso da mantenere, aggiornare e mettere in sicurezza.
- **Cosa fare invece:** proponi la dipendenza e attendi conferma prima di aggiungerla.

---

{% include-markdown "signature-core.md" %}
</content>
