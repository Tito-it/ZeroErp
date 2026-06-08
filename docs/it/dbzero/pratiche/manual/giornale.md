## 📘 Documentazione Concettuale – Tabella `pratiche.giornale`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale
La tabella `pratiche.giornale` e' il **giornale di bordo (audit trail)** del modulo pratiche. Registra ogni evento significativo nel ciclo di vita di pratiche e flussi in modo append-only e immutabile.

---

### Ruolo nel processo

* Ogni modifica rilevante a una pratica o flusso genera un record nel giornale tramite trigger business-specific (DB-5).
* Il campo `tx_id` consente la **correlazione cross-tabella**: collegando l'evento del giornale con le modifiche nella stessa transazione su altre tabelle.
* Il giornale e' **append-only**: solo INSERT, mai UPDATE o DELETE. Solo `data_insert/user_insert`.

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `pratica_id` | BIGINT NOT NULL. Sempre presente — ogni evento e' legato a una pratica. |
| `flusso_id` | BIGINT nullable. Presente solo per eventi a livello flusso (NULL = evento pratica). |
| `azione` | VARCHAR(50) NOT NULL. CHECK su lista azioni (vedi sotto). |
| `origine` | VARCHAR(20) DEFAULT 'SISTEMA'. CHECK (SISTEMA, UTENTE, HANDLER, SCHEDULER). Chi ha originato l'evento. |
| `dettaglio` | JSONB DEFAULT '{}'. Dati strutturati dell'evento (es. `{"stato_precedente": "BOZZA", "stato_nuovo": "APERTA"}`). |
| `tx_id` | UUID nullable. Correlazione con il tx_id della transazione per tracciabilita' cross-tabella. |

---

### Azioni registrate

| Azione | Trigger | Evento |
|--------|---------|--------|
| `PRATICA_CREATA` | INSERT su pratiche | Creazione pratica |
| `STATO_CAMBIATO` | UPDATE su pratiche (stato_id cambia) | Cambio stato pratica |
| `ASSEGNAZIONE_CAMBIATA` | UPDATE su pratiche (risorsa/UO cambia) | Cambio assegnazione |
| `PRIORITA_CAMBIATA` | UPDATE su pratiche (priorita_id cambia) | Cambio priorita' |
| `FLUSSO_CREATO` | INSERT su flussi | Creazione flusso |
| `FLUSSO_STATO_CAMBIATO` | UPDATE su flussi (stato_id cambia) | Cambio stato flusso |
| `NOTA_AGGIUNTA` | INSERT su note_pratiche/note_flussi | Aggiunta nota |
| `ALLEGATO_AGGIUNTO` | INSERT su allegati_pratiche/allegati_flussi | Aggiunta allegato |
| `PRATICA_GENERATA` | Generazione cross-pratica | Pratica generata da un flusso |
| `SOSPENSIONE_REGISTRATA` | INSERT su sospensioni | Sospensione registrata |
| `SOSPENSIONE_CHIUSA` | Riattivazione sospensione | Sospensione chiusa |
| `DOMINIO_*` | `pratiche.fn_log_evento_dominio` (origine `HANDLER`) | Evento di dominio applicativo (es. `DOMINIO_COMMESSA_CREATA`, `DOMINIO_PREVENTIVO_EVASO`) |

---

### Eventi di dominio (`DOMINIO_*`) — da 2026-06-08

Oltre agli eventi di **motore** (lista fissa sopra, alimentati dai trigger), il
giornale accetta **eventi di dominio applicativi** con prefisso `DOMINIO_`. Il
CHECK `chk_giornale_azione` ammette:

```sql
azione IN (<11 eventi di motore>) OR azione ~ '^DOMINIO_[A-Z][A-Z0-9_]*$'
```

Gli 11 eventi di motore restano blindati; i `DOMINIO_*` sono liberi (maiuscoli,
nessun nuovo CHECK per evento). L'unico canale di scrittura consentito e' la
funzione [`pratiche.fn_log_evento_dominio`](/dbzero/pratiche/funzioni/fn_log_evento_dominio)
`(p_pratica_id, p_flusso_id, p_tipo_evento, p_meta)`, usata dagli handler
applicativi (es. `vendita.push_preventivo`): mappa `p_tipo_evento -> azione`,
`p_meta -> dettaglio`, forza `origine = 'HANDLER'` e correla via `tx_id` di
sessione. Un nome non conforme (non `DOMINIO_*` e non in lista) viene rifiutato
dal CHECK. Catalogo eventi `DOMINIO_*` in uso: vedi il catalogo building-block
backend (mitigazione refusi; promozione a tabella `config` da rivalutare dopo
3-4 eventi reali).

---

### 📑 Indici espliciti

| Indice | Tipo | Scopo |
|--------|------|-------|
| `ix_pratiche_giornale_data_insert` | BTREE | Query temporali (ultimi N eventi, range date). |
| `ix_pratiche_giornale_azione` | BTREE | Filtro per tipo azione. |

Questi indici sono espliciti (non FK) perche' servono a query frequenti sull'audit trail.

---

### Convenzioni

* PK BIGINT IDENTITY (alto volume).
* Append-only: solo `data_insert/user_insert`, no storicizzazione.
* `tx_id` per correlazione cross-tabella (non gestito da automazione — impostato dal trigger giornale).
* Trigger standard **non** applicati (no audit update, no storico, no lock). I trigger giornale sono business-specific (DB-5).

---

{% include-markdown "signature-core.md" %}
