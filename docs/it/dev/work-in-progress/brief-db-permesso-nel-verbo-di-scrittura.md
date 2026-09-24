# Brief DB — Il permesso controllato nel verbo di scrittura

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-24. **A chi:** Tid (decisioni,
> §7), poi team DB e backend.
> **Origine:** approfondimento del §8 di
> [brief-db-area-funzionale-assistente-ai.md](brief-db-area-funzionale-assistente-ai.md).
> **Stato:** ⚠️ **analisi con decisioni aperte — nessun changeSet chiesto**.
>
> **In una riga:** oggi il DB **calcola** i permessi ma non li **applica**:
> qualunque scrittura che il backend autorizza per errore, il DB la esegue. La
> forma che chiude il buco, coerente col DB-first, è **una scrittura = un verbo**:
> una funzione DB che controlla azione o livello di chi agisce, con l'app che
> perde `INSERT`/`UPDATE`/`DELETE` sulle tabelle che il verbo protegge.
>
> ⇒ La proposta è di adottarla come **regola per i domini nuovi** e di portarci
> gli esistenti uno alla volta, **senza data**. Prima servono le decisioni del §7.

---

## 1. Il problema che resta dopo la sola lettura

Il [brief-be-letture-in-transazione-sola-lettura.md](brief-be-letture-in-transazione-sola-lettura.md)
fa garantire al DB che **una lettura non scriva**. Non copre il caso opposto: una
richiesta di **scrittura** che il backend autorizza a chi non dovrebbe, per
esempio un endpoint con il `post_permission` sbagliato, o un tool dell'assistente
legato all'endpoint sbagliato. Lì il DB esegue, perché:

* `zeroerp_app` ha i privilegi di scrittura sulle tabelle;
* nessuna policy RLS e nessuna funzione consulta il livello o l'azione di chi
  agisce.

## 2. Cosa c'è oggi — letto dalla struttura

Fatti datati, letti il 2026-09-24 sul catalogo di dbdev e nel codice. Descrivono
il punto di partenza: **non** decidono né la forma né la priorità.

* **Il DB sa chi agisce.** A ogni richiesta il backend imposta nella sessione
  `app.current_user_id`, `app.ruolo_applicativo`, `app.current_identita_id`,
  `app.current_emittente_id` (`core/api/jwt_audit_authentication.py`). Le policy
  RLS le leggono già.
* **Il DB sa decidere.** `script.fn_resolve_livello_area`,
  `script.fn_resolve_livello_oggetto`, `script.fn_check_azione_processo` sono la
  sede della regola: il backend le chiama, non le riscrive.
* **Il DB non applica.** Nessuna policy cita quelle funzioni: le policy esistenti
  decidono il **perimetro** (emittente, ambito), cioè *quali righe*, non *cosa
  ci si può fare*.
* **La RLS è `ENABLE` senza `FORCE`** (postura del progetto): le funzioni
  `SECURITY DEFINER` del proprietario la scavalcano.
* **Le scritture partono quasi tutte dal backend con SQL diretto** (a quella data
  circa 300 istruzioni `INSERT`/`UPDATE`/`DELETE` in 49 file, più un CRUD
  generico sulle tabelle di configurazione e scritture a tabella costruita a
  runtime). Le funzioni DB che scrivono coprono una parte dei casi.
* ⭐ **La forma «porta» esiste già**: Lotto 2 di magazzino, D-L2-b
  ([brief-db-magazzino-lotto-2-motore.md](brief-db-magazzino-lotto-2-motore.md)).
  `zeroerp_app` ha solo `SELECT` su `magazzino.movimenti`; scrive solo la
  primitiva `fn_scrivi_movimento`, `SECURITY DEFINER` del proprietario; il
  perimetro è rimesso dal guard BB `script.trgfn_guard_emittente_scope`.
* ⛔ **E mostra il pezzo che manca.** Verificato il 2026-09-24:
  `zeroerp_app` ha `EXECUTE` **direttamente** su `fn_scrivi_movimento` (e su
  `fn_ricalcola_valore_giacenza`), non solo sulle operazioni
  `fn_posta_inventario` / `fn_posta_rettifica` che la chiamano. E nessuna delle
  quattro controlla un permesso. La porta decide **da dove** si scrive, non
  **chi** può scrivere.

## 3. Perché non una policy RLS sul livello

È la prima idea, ed è sbagliata per il **modello**, non per il costo:

1. **Una tabella non è un'operazione.** Un operatore in `LETTURA` su `pratiche`
   con l'azione `cambia_stato_pratica` concessa **deve** poter scrivere sulle
   tabelle di `pratiche`. Una policy vede «UPDATE su questa tabella», non quale
   azione lo autorizza: blocca proprio il caso legittimo.
2. **Un'area non è uno schema.** Un'operazione di `vendite` scrive anche in
   `pagamenti`, `dbops`, `config`; aree come `core`, `strumenti`,
   `ai_assistant` non hanno uno schema.
3. **Le DEFINER la scavalcano**: la barriera avrebbe buchi per costruzione.

⇒ Il permesso appartiene all'**operazione**. A DB l'operazione ha un nome solo:
la **funzione** che la esegue.

## 4. Il modello proposto

### 4.1 Una scrittura = un verbo

* Ogni operazione di scrittura di un dominio che adotta il modello è una
  **funzione DB** (il *verbo*): `fn_posta_inventario`, `fn_cambia_stato_pratica`, …
* Il verbo **dichiara il suo permesso nella prima riga**, con un building block
  unico, e non con un controllo scritto a mano:
  * `script.fn_require_azione(p_permission_codename)`, oppure
  * `script.fn_require_livello(p_area_schema_db, p_tipo_accesso)`.

  Il BB legge `app.current_user_id` e chiama le funzioni di risoluzione che già
  esistono (sede unica della regola). Se il permesso manca, solleva un **codice
  registrato**, famiglia autorizzazione.
* ⭐ Per un'azione di processo il verbo **è** l'azione: `cambia_stato_pratica` il
  codename, `fn_cambia_stato_pratica` il verbo. La coppia rende naturale ciò che
  una policy non sa esprimere (§3.1).

### 4.2 La porta: le tabelle del verbo si chiudono all'app

Stessa forma del Lotto 2 (D-L2-b), resa generale:

* `zeroerp_app` perde `INSERT`/`UPDATE`/`DELETE` sulle tabelle che il verbo
  protegge; la postura si dichiara nel loop dei grant di `ci_apply`
  (`v_tabelle_sola_lettura_app`) e in `provision_db_roles.sql`, come fa il
  Lotto 2 — **non** con un `REVOKE` in un changeSet normale;
* chi scrive su una tabella chiusa gira come **proprietario** (DEFINER), e il
  perimetro lo rimette il guard BB `trgfn_guard_emittente_scope`, come in
  magazzino;
* ⛔ **l'app può eseguire solo i verbi**, non le primitive che i verbi usano: su
  una primitiva `REVOKE EXECUTE … FROM zeroerp_app`. Altrimenti il controllo del
  verbo si aggira chiamando la primitiva (§2, ultimo punto).

### 4.3 Il backend chiede, non decide due volte

Il backend **tiene** il suo controllo sugli endpoint: dà un 403 immediato e un
messaggio utile prima di aprire una transazione. Non è una seconda copia della
regola, perché anche il backend chiama le **stesse** funzioni di risoluzione: la
regola ha una sede sola (il DB), i **punti di applicazione** diventano due. Il
verbo è quello che non si può scavalcare.

### 4.4 Cosa NON protegge — da scrivere, non da scoprire

⛔ **L'identità la dichiara il backend.** Le GUC `app.current_user_id` e
`app.ruolo_applicativo` le imposta la connessione dell'app con `set_config`, e
qualunque codice su quella connessione può impostarle a un altro utente. Quindi il
modello protegge da un backend **che sbaglia** (permesso dichiarato male, tool
legato all'endpoint sbagliato, service che scrive dove non dovrebbe), **non** da un
backend **compromesso**. È lo stesso limite che hanno oggi le policy RLS di
perimetro: va scritto nella guida, non lasciato implicito.

## 5. Il percorso

1. **Il BB del permesso** (`fn_require_azione` / `fn_require_livello`) e i suoi
   codici di errore: un cantiere piccolo, in `script`.
2. **I domini nuovi nascono così**: `magazzino` e `acquisti` sono il prossimo
   cantiere (decisione di Tid del 2026-09-11), e ogni decisione presa lì vale per
   due domini. Il primo passo è **chiudere la porta già aperta del Lotto 2**:
   verbo che controlla il permesso, `EXECUTE` sulla primitiva tolto all'app.
3. **I domini esistenti, uno alla volta, senza data**: quando un cantiere tocca
   le scritture di un dominio, ne porta i verbi al modello nello stesso giro.
   ⚠️ Un dominio **a metà** — alcune tabelle chiuse, altre no — va dichiarato
   come tale nella sua guida, con l'elenco delle tabelle ancora aperte.

## 6. Cosa non si chiede

* ⛔ Nessuna policy RLS di scrittura sul livello (§3).
* ⛔ Nessun `FORCE ROW LEVEL SECURITY`: la postura resta quella del progetto, il
  perimetro dentro le DEFINER lo rimette il guard BB.
* ⛔ Nessuna migrazione in blocco degli esistenti.

## 7. Decisioni aperte — a Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | Adottare il modello (§4) come direzione? | Sì, per i domini nuovi e per gli esistenti al passaggio del loro cantiere |
| **D-2** | Ogni verbo è legato a **un'azione di processo**, o basta il livello d'area per i verbi CRUD semplici? | Due forme, **un BB**: le operazioni di processo usano l'azione, il CRUD semplice il livello (`add`/`change`/`delete` ⇒ `TUTTO`). Così `azioni_processo` non si riempie di azioni che ripetono il livello |
| **D-3** | Il CRUD generico delle tabelle di configurazione (`config_crud_repository`) | Un verbo generico DEFINER, con la stessa whitelist e il controllo di livello sull'area `config` — oppure fuori perimetro finché le tabelle di configurazione restano scrivibili solo da `SUPER_ADMIN`. Da decidere |
| **D-4** | Il Lotto 2 chiude subito la porta aperta (§2, ultimo punto)? | Sì, come primo caso: è piccolo, il dominio è già nella forma giusta, e insegna il modello su un caso vero |
| **D-5** | Gli override per oggetto (`fn_resolve_livello_oggetto`, `area_model_overrides`) | Il BB li onora quando il verbo nomina il proprio oggetto; da verificare sui primi verbi |

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-24 | DB | Brief scritto dall'approfondimento del §8 del brief dell'assistente AI, su decisione di Tid («3 con brief apposito») |
