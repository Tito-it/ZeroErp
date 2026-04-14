## 📘 Documentazione Concettuale – Tabella `vendite.contratti`

> 👀 **Vedi anche**
>
**Guide generali:**    
>
• [Generazione di un cliente](/guide/generazione-cliente)    
> • [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility)    
>
**Approfondimento tabelle:**    
>
• [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)    
> • [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto)    
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)    
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)     
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)    
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)    
> • [config.utilities](/dbzero/config/tabelle/utilities)    
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)   
>
**Approfondimento funzioni:**
>
• [`vendite.trgfn_contratti_gen_codice`](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice)
>
### 🎯 Scopo Principale
(Initial version - 19-01-26)
`vendite.contratti` rappresenta la **testata del contratto commerciale**: l’accordo che lega un **billing account** a una **istanza/utility** e ne definisce **ambito**, **periodo di validita** e **stato**. E` la base di aggregazione delle righe (`vendite.contratti_righe`) e il punto di riferimento per la generazione di **attivita fatturabili**.

Obiettivi principali:

* Modellare la **relazione contrattuale** tra cliente (via BA) e fornitura/servizio (istanza utility).
* Delimitare un **periodo di validita** con regole anti‑overlap.
* Tracciare lo **stato del contratto** (bozza, attivo, chiuso, ecc.).
* Stabilire un **contenitore unico** per condizioni, righe e metadati eterogenei.

---

### Collocazione nel flusso operativo

1. **Fase pre‑cliente**: raccolta dati tecnici/commerciali su `anagrafiche.istanze_dati_precontrattuali`.
2. **Creazione contratto**: assegnazione `billing_account_id`, `istanza_utility_id`, `utility_id` e periodo di validita.
3. **Definizione righe**: aggiunta di servizi/beni in `vendite.contratti_righe` con regole di canone/erogazione.
4. **Attivazione**: cambio `stato_doc_contratto_id` e innesco processi di fatturazione.
5. **Rinnovo/chiusura**: gestione del ciclo di vita tramite `valido_al` e `parent_contratto_id`.

---

### Identita contratto & numerazione

* **Numero** (`numero`) generato da `vendite.trgfn_contratti_gen_codice()` se non fornito.
* **UID** (`uid`) per integrazioni esterne e idempotenza applicativa.
* **Blocco modifiche**: `script.trgfn_lock_columns('numero', ...)` impedisce aggiornamenti non autorizzati.
* **Data contratto** (`data`) valorizzata automaticamente alla prima assegnazione di `numero`.


---

### Validita, ambito e anti‑overlap

* **Periodo**: `valido_dal` e `valido_al` (NULL = aperto).
* **Ambito** (`ambito`) separa domini diversi (es. COMMODITY vs servizi extra).
* **Anti‑overlap operativo**: l’indice `ex_contratti_no_overlap` supporta query di controllo per evitare sovrapposizioni sulla stessa combinazione `billing_account_id + istanza_utility_id + utility_id + ambito`.

> Nota: l’anti‑overlap e` tipicamente garantito da logiche applicative o trigger di validazione.

---

### Collegamenti anagrafici

* **Billing Account** (`billing_account_id`) = intestatario economico del contratto.
* **Istanza utility** (`istanza_utility_id`) = punto tecnico/fornitura del servizio.
* **Utility** (`utility_id`) = dominio tecnico (gas, energia, ecc.), coerente con BA e istanza.
* **Cliente**: deriva dalla relazione BA/istanza (`anagrafiche.clienti`), non e` salvato direttamente in `vendite.contratti`.

---

### Integrazione con `anagrafiche.istanze_dati_precontrattuali`

I dati precontrattuali sono **tipici del dominio utilities** e sono riferiti a `istanza_utility_id` e `utility_id`. Il contratto li integra in modo **non invasivo**:

* **Durante la creazione**: i parametri tecnici (potenza, classe utenza, ecc.) possono essere **copiati in `meta`** o usati per valorizzare righe e regole di fatturazione.
* **Durante l’attivazione**: i dati precontrattuali diventano **baseline** per pricing e configurazioni di erogazione.
* **Dopo l’attivazione**: il contratto governa il ciclo commerciale; i precontrattuali restano **storico di raccolta**, utili per audit o riconciliazioni.

Per attivita **non‑utilities** o servizi eterogenei, i dati precontrattuali possono **non essere presenti**: in tal caso le condizioni specifiche risiedono in `vendite.contratti.meta` e in `vendite.contratti_righe.meta`.

---

### Pricing v5 — modalita' A / B / C (14-04-2026)

Il contratto e' il **ponte commerciale** tra billing account e listino (STADIO 1 del resolver prezzi v5). Tre modalita' di pricing coesistono sulla stessa tabella:

| Modalita' | `listino_id` | `tipo_variazione_globale` | Righe `contratti_righe` | Esempio |
| --- | --- | --- | --- | --- |
| **A** — listino + variazione globale | NOT NULL | NOT NULL | vuoto o solo override mirati | "Listino gas 2026 −10%" |
| **B** — listino con override | NOT NULL | NULL o NOT NULL | righe con `prezzo_unitario` per articoli specifici | "Listino gas 2026, art X a €50 fisso" |
| **C** — interamente negoziato | NULL | NULL | tutte le righe attive con `prezzo_unitario` NOT NULL | Grande cliente con condizioni 100% su misura |

Campi introdotti:

| Colonna | Tipo | Nullable | Note |
| --- | --- | --- | --- |
| `listino_id` | bigint | YES | FK a `vendite.listini(id)`. NULL = modalita' C |
| `tipo_variazione_globale` | varchar(16) | YES | `PERCENTUALE` \| `VALORE_FISSO` |
| `valore_variazione_globale` | numeric(10,4) | YES | Coerente con `tipo_variazione_globale` |

Vincoli CHECK:

* `chk_contratti_tipo_variazione_globale`: solo `PERCENTUALE`/`VALORE_FISSO` o NULL.
* `chk_contratti_variazione_globale_coerente`: tipo e valore sono entrambi NULL o entrambi NOT NULL.
* `chk_contratti_modalita_pricing`: se `listino_id IS NULL`, variazione globale = NULL (nessun punto di applicazione).

Vincoli trigger (fail-fast all'attivazione):

* `trg_contratti_a10_guard_modalita_c_activation_ins_upd` -> [`vendite.trgfn_contratti_guard_modalita_c_activation`](/dbzero/vendite/funzioni/trgfn_contratti_guard_modalita_c_activation): scatta sia nella transizione verso stato `codice_interno = 'ATTIVO'` con `listino_id NULL`, sia quando un contratto gia' ATTIVO passa a modalita' C (UPDATE `listino_id` da NOT NULL a NULL). In entrambi i casi blocca se non esiste almeno una riga attiva o se qualche riga attiva ha `prezzo_unitario NULL`.
* `trg_contratti_righe_a10_guard_modalita_c_ins_upd` su `contratti_righe` -> [`vendite.trgfn_contratti_righe_guard_modalita_c`](/dbzero/vendite/funzioni/trgfn_contratti_righe_guard_modalita_c): su contratto gia' ATTIVO in modalita' C, la riga attiva deve avere `prezzo_unitario NOT NULL`.

In stato `DRAFT` le righe incomplete sono ammesse: il contratto modalita' C non e' attivabile finche' le righe non sono complete.

---

### Meta, rinnovi e storicizzazione

* **`meta jsonb`**: contenitore estendibile per condizioni specifiche (SLA, clausole, parametri di calcolo).
* **Rinnovi/collegamenti**: `parent_contratto_id` collega contratti successivi (rinnovi, subentri, varianti).
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update` e `storicizza` per tracciabilita e storico.



---

### Best practice

* Valorizzare sempre `billing_account_id`, `istanza_utility_id` e `utility_id` in modo coerente.
* Gestire `valido_dal`/`valido_al` per evitare sovrapposizioni contrattuali.
* Usare `meta` solo per **estensioni specifiche** del dominio, non per dati core duplicati.
* Collegare i rinnovi via `parent_contratto_id` per ricostruire la **storia contrattuale**.

---

### Ruolo nel sistema

`vendite.contratti` e` il **centro di gravita commerciale** tra istanza tecnica e fatturazione. In ambito utilities consolida i dati precontrattuali e li trasforma in **condizioni operative**, mentre in ambiti eterogenei diventa un contenitore flessibile di servizi e canoni da erogare nel tempo.

{% include-markdown "signature-core.md" %}

---
