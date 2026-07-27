# Brief DB — Permesso di processo per il cambio stato commessa

> **Tipo**: micro-brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid · **Stato**: ✅ **CHIUSO — riga a
> catalogo (id 30) + BE e FE rilasciati** (2026-07-27) · **Priorità**: 🟠 ALTA
> (fino a ieri l'atto irreversibile era l'unico non protetto).
>
> ⚠️ **Nota di rilascio**: il seed è stato **applicato al DB di test** dal team
> DB via `runOnChange` sul CSV, **non ancora pushato** — sul branch
> `dev/backend-tid` la riga non compare in `azioni_processo.csv`. Il codice BE/FE
> è allineato al catalogo del DB di test: al merge dei due rami tutto combacia,
> ma **su un ambiente senza quella riga il permesso non esiste** e l'endpoint
> risponde 403 a chiunque non sia SUPER_ADMIN.
>
> **Perimetro DB**: **una riga di append** a un CSV di seed. Nessun oggetto nuovo,
> nessun loader nuovo, nessuna funzione toccata.
>
> **Origine**: decisione Tid del 2026-07-27 che chiude lo step **E-BE-4** di
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md),
> segnalato a suo tempo in §8 di
> [brief-db-guard-uscita-commessa-e-capabilities.md](../work-done/brief-db-guard-uscita-commessa-e-capabilities.md).
>
> **BE/FE seguono a valle** ([[feedback_be_fe_attende_prerequisiti_db]]): senza la
> riga a catalogo, `post_permission` punterebbe a un codename inesistente.

---

## 1. Perché

`ApiCommessaStato` ([views.py:684](../../../../backend/apps/vendite/api/views.py#L684))
dichiara `area_funzionale = "vendite"` ma **non ha `post_permission`**: è protetto
dal solo controllo d'area. Chiunque acceda all'area vendite — anche chi ci sta per
fare preventivi — può portare una commessa a `CHIUSA` o `ANNULLATA`.

Sono **stati terminali irreversibili**: nessun arco uscente in matrice, entrambi
`emittibile = false` → la commessa esce per sempre dal giro di fatturazione e
nessuna via applicativa la riporta indietro (§0 del brief guard-uscita).

L'asimmetria che chiude la questione (criterio di Tid): **se serve
un'autorizzazione per modificare un prezzo, a maggior ragione serve per eliminare
la commessa.** Oggi nella stessa entità:

| Azione | Reversibile? | Permesso |
| --- | --- | --- |
| Modifica manuale prezzo riga | sì | `prezzo_override_manuale` |
| Carica onere manuale | sì | `carica_voce_manuale` |
| Approva attività | sì | `approva_attivita_commessa` |
| **Chiudi / Annulla commessa** | **NO** | **nessuno** ← |

I guard usciti col brief precedente (Regola 3 del trigger) coprono un asse
diverso: impediscono la chiusura **sbagliata** (con righe pendenti), non
stabiliscono **chi** ha l'autorità di chiudere quando la chiusura è lecita.

---

## 2. Cosa fare — append di **una riga**

**File**: `db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv`
— **solo append**. Verificato: il loader
[20260228-18-upsert-config-azioni-processo](../../../../db/changelog/migrations_v2/80_data/changelog/20260228-18-upsert-config-azioni-processo-mctit.yaml)
è `loadUpdateData` + `runOnChange: true` + `primaryKey: id` → **nessun changeset
nuovo, nessun numero consumato**. Ultimo id occupato: **29**.

| Colonna | Valore |
| --- | --- |
| `id` | `30` |
| `area_id` | `2` (vendite) |
| `permission_codename` | **`cambia_stato_commessa`** |
| `descrizione` | `Cambia stato commessa (chiudi/riapri/annulla)` |
| `pericolosa` | **`t`** |
| `attivo` | `t` |
| `meta` | `{}` |

### Perché `pericolosa = t`

La colonna è letta dall'editor profili
([RepartoProfiloEditor.vue](../../../../frontend/src/amministrazione/components/RepartoProfiloEditor.vue)):
marca l'azione a chi la sta assegnando. Coerente con le altre irreversibili già a
catalogo (`numera_fatture_lotti`, `reset_lotto_draft`, `genera_fatture_lotti`).

### Perché UN codename per tre transizioni

`post_permission` gatta **l'endpoint**, non la singola `action_key`: lo stesso
permesso coprirà `chiudi`, `annulla` **e** `riapri`. È deliberato, e ha già un
precedente identico a catalogo: `cambia_stato_preventivi` — *«Cambia stato
preventivo (emetti/accetta/rifiuta/annulla)»* (id 11). Il permesso significa
**«governa il ciclo di vita della commessa»**.

Nota su `riapri`: di per sé è reversibile, ma non è innocuo — riporta la commessa
in `IN_ESECUZIONE`, che **non è emittibile**, cioè la toglie dal giro di
fatturazione. Sta bene sotto lo stesso permesso. Se un domani servisse separare i
tre verbi, servirebbe un gate per `action_key` **dentro il service**, non un
secondo `post_permission`: è un'estensione, non una correzione di questa scelta.

---

## 3. Effetto operativo il giorno dell'applicazione — da sapere prima

L'aggiunta del permesso **non è neutra per gli operatori**:

- **SUPER_ADMIN**: nessun effetto, ha il bypass totale sia FE
  (`auth.isActionAllowed` → `if (isSuperAdmin) return true`) sia BE
  (`permissions_resolver`). Nessun rischio di auto-lockout.
- **Operatori normali**: il gate è **fail-closed**. Finché l'azione non è
  assegnata, i pulsanti «Chiudi»/«Riapri»/«Annulla» **spariscono** dal drawer
  commessa. È l'effetto voluto — prima non filtravano nessuno — ma va **deciso a
  chi darla** contestualmente, altrimenti arriva la segnalazione «è sparito il
  pulsante» ed è indistinguibile da un guasto.

L'assegnazione è **configurazione runtime, non seed**: si fa dalla UI
amministrazione (profilo → azioni, tabella `config.profili_accesso_azioni`; per il
singolo utente `config.user_override_azioni`). Nessuna riga di seed da scrivere.

---

## 4. A valle — BE e FE ✅ **fatti (2026-07-27)**

| Dove | Cosa | Esito |
| --- | --- | --- |
| **BE** | `post_permission = "cambia_stato_commessa"` su `ApiCommessaStato` | ✅ una riga + 2 test (`test_commessa_stato_post_permission_allowed`/`_denied`: il *denied* verifica anche che il service **non** venga invocato). Il **GET** di lettura stato resta libero nell'area: `post_permission` gatta il solo POST |
| **FE** | Gate sulle azioni di stato del `CommessaGestioneDrawer` | ✅ via il BB `mapAvailableActionsToDrawerActions`, esteso con il parametro opzionale **`permission`**: stampa `action: <codename>` su ogni azione mappata e il filtro di `DrawerActionsBar` (`auth.isActionAllowed`) fa il resto. Un solo punto invece di un gate per pulsante — ed è pronto per gli altri domini (i preventivi hanno già `cambia_stato_preventivi` lato BE, oggi senza gate FE) |

Suite BE **1970 test verdi**; eslint + build + i18n guard FE verdi.

Le capability DB (`enabled`/`reasons` da `fn_available_actions_commessa`) restano
**ortogonali**: dicono *se l'azione è eseguibile adesso*, il permesso dice *se
quell'operatore può eseguirla*. I due gate si sommano, non si sostituiscono.

---

## 5. Verifica

Nessun pgTAP dedicato: è un dato di configurazione, non logica. Controlli:

1. `SELECT id, permission_codename, pericolosa, attivo FROM config.azioni_processo WHERE permission_codename = 'cambia_stato_commessa';` → 1 riga, `pericolosa = t`, `attivo = t` — ✅ confermato dal team DB sul DB di test;
2. l'azione compare nell'editor profili dell'area vendite, marcata pericolosa;
3. **da validare in app** (l'unica cosa che resta): operatore **senza** l'azione → nessun pulsante di stato sul drawer commessa e `403` chiamando l'endpoint direttamente; operatore **con** l'azione → comportamento invariato. I due test BE coprono il gate lato server, non la resa a schermo.

### Prima di dare per chiuso il rilascio

**Assegnare `cambia_stato_commessa` ai profili che devono averlo** (UI
amministrazione → profilo → azioni). Finché non lo fai, per gli operatori i
pulsanti Chiudi/Riapri/Annulla **non ci sono più** — vedi §3. Tu come
SUPER_ADMIN non te ne accorgi.

---

## 6. Riferimenti

- Segnalazione originale: §8 di [brief-db-guard-uscita-commessa-e-capabilities.md](../work-done/brief-db-guard-uscita-commessa-e-capabilities.md)
- Decisione e contesto di fase: **E-BE-4** in [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
- Precedente di naming: `cambia_stato_preventivi` (id 11) in [azioni_processo.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv)
- Tabella: [config.azioni_processo](../../dbzero/config/tabelle/azioni_processo.md) · raccordi: [profili_accesso_azioni](../../dbzero/config/tabelle/profili_accesso_azioni.md) · [user_override_azioni](../../dbzero/config/tabelle/user_override_azioni.md)
