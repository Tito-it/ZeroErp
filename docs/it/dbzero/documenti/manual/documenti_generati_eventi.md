## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati_eventi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.documenti_generati](/dbzero/documenti/manual/documenti_generati)
> • [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file)
>
**Trigger guard:**
>
• [trgfn_documenti_generati_eventi_block_delete](trgfn_documenti_generati_eventi_block_delete.md)
> • [trgfn_documenti_generati_eventi_block_update](trgfn_documenti_generati_eventi_block_update.md)
>

### 🎯 Scopo Principale
(introdotta 03-05-2026, anticipo Fase B → v1)

`documenti.documenti_generati_eventi` è la **timeline append-only** del ciclo
vita di un documento generato. Registra in ordine cronologico gli eventi
applicativi che riguardano una generazione persistita: emissione, download e
gestione tecnica del file.

---

### Ruolo nel processo

* fornisce audit chi/quando/cosa per ogni evento utente o tecnico associato a
  un PDF persistito;
* rispetta la **Decisione 31** (log evento `SCARICATO` ad ogni download) e la
  **Decisione 30** (no log per anteprime);
* copre il caso `STORAGE_ORPHAN` (Decisione 72) per i file orfani da cleanup
  post-fail commit DB;
* sostituisce, già in v1, il ricorso ad un audit colonnare ad-hoc (`*_at`,
  `*_user_id`) sulla tabella `documenti_generati`.

---

### Campi chiave (semantica)

* **Riferimento documento**: `documento_generato_id` FK
  `documenti.documenti_generati(id)` ON DELETE RESTRICT (anche se il delete è
  bloccato dal trigger A5).
* **Identità evento**: `evento_tipo`, `evento_at`.
* **Operatore**: `user_id` FK condizionale `django.auth_user(id)` (nullable
  per eventi tecnici come `STORAGE_ORPHAN`).
* **Esito**: `esito` ∈ (`OK`, `KO`, `WARN`).
* **Diagnostica**: `messaggio` (testo libero, non vuoto se valorizzato),
  `detail` jsonb (sempre object).
* **Audit standard**: `tx_id`, `data_insert`, `user_insert`,
  `data_update`, `user_update` (questi ultimi due restano valorizzati al solo
  INSERT — la tabella è append-only).

---

### Eventi v1 (set chiuso via CHECK)

| Codice | Quando | `user_id` | `esito` tipico |
|---|---|---|---|
| `GENERATO` | Post commit storage + DB del documento generato | utente API | `OK` |
| `SCARICATO` | Ad ogni download del PDF persistente | utente API | `OK` |
| `STORAGE_ORPHAN` | File orfano dopo fail commit DB (cleanup automatico) | NULL | `KO` |

`ANTEPRIMA`, `INVIATO`, `ARCHIVIATO`, `ANNULLATO`, `RENDER_KO` **non** sono
ammessi in v1. Gli stati workflow tecnici sono governati dal codice
applicativo, non da lookup configurabili (Decisione 18). Estensioni del set
in Fase B richiederanno una migration che modifica il `CHECK`.

---

### Regole principali

* **Append-only**: nessun UPDATE e nessun DELETE sono ammessi (guard
  `trgfn_documenti_generati_eventi_block_update` /
  `trgfn_documenti_generati_eventi_block_delete`). Le correzioni si
  registrano come nuovo evento (es. `esito='WARN'` con riferimento al
  precedente in `detail`).
* **Storico OFF**: la tabella è essa stessa il log; la colonna `storicizza`
  è omessa per impedire il provisioning automatico di
  `storico.documenti_generati_eventi` da parte del framework `dbops`. Stessa
  strategia del changeset 20260501-08 ma applicata ab initio.
* **Detail come object**: `CHECK jsonb_typeof(detail) = 'object'`,
  coerente con Step E della Fase A. No array, no scalari.
* **Messaggio non vuoto**: se valorizzato, `btrim(messaggio) <> ''`. NULL
  resta ammesso (eventi senza messaggio testuale).

---

### Indici

| Indice | Colonne | Uso |
|---|---|---|
| `ix_documenti_generati_eventi_documento_evento_at` | `(documento_generato_id, evento_at DESC)` | Timeline cronologica per documento (uso primario FE). |
| `ix_documenti_generati_eventi_evento_tipo` | `(evento_tipo)` | Analytics/dashboard per tipo evento. |

L'indice composito copre anche la `FK` su `documento_generato_id` (lo prefix
basta per la politica `dbops.fk_index_policy`). L'indice sulla FK `user_id` è
delegato alla politica degli indici delle FK: nel suo CSV non ha una decisione, e
finché resta scoperta la mostra il presidio `dbops.vw_fk_da_decidere`.

---

### Uso tipico nel processo

1. **Genera documento**: il backend, dopo aver salvato `documenti_generati`
   e il file fisico nello storage, registra `('GENERATO', 'OK')` con
   `user_id` dell'API e `detail` minimale (es. `{"size_bytes": ...}`).
2. **Download PDF**: l'endpoint download registra `('SCARICATO', 'OK')` ad
   ogni richiesta — Decisione 31.
3. **Cleanup file orfano**: se il commit DB fallisce dopo un upload riuscito
   in storage, il backend prova un cleanup best-effort e in caso di errore
   registra `('STORAGE_ORPHAN', 'KO')` con `detail` contenente
   `storage_key` per intervento manuale.

---

### Confine v1 / Fase B

In v1 non sono coperti (volutamente):

* eventi `INVIATO` (PEC/email) → richiede pipeline invio;
* eventi `ARCHIVIATO`/`ANNULLATO` → vivono come stato su
  `documenti_generati`, non come evento separato in v1;
* `RENDER_KO` → se il render fallisce, **non si crea** record in
  `documenti_generati` (Decisione 32), quindi nessun evento orfano da
  loggare;
* anteprime PDF → escluse dalla timeline per Decisione 30.

Tutti questi punti rientrano nel piano di estensione Fase B, non richiedono
modifiche strutturali alla tabella ma solo l'aggiornamento del set chiuso
del `CHECK evento_tipo`.

---

{% include-markdown "signature-core.md" %}
