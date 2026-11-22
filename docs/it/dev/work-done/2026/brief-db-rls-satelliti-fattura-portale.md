# Brief [DB] — RLS mancante sui satelliti fattura letti dal portale

> **Tipo**: brief al **team DB** (`dev/db-tid`) · **Data**: 2026-07-28 ·
> **Owner**: Tid · **Stato**: ✅ **CHIUSO** — applicato dal team DB il
> **2026-07-29** (§8), verificato lato BE, nessuna modifica applicativa
> necessaria ·
> **Priorità**: era 🟠 MEDIA → 🔴 ALTA all'arrivo del portale fatture.
> Chiuso **prima** che il portale nascesse, come chiedeva il brief ·
> **Non ha bloccato**: [brief-be-fe-drawer-fattura](brief-be-fe-drawer-fattura.md)
> (lato operatore il cancello di testata era sufficiente — §4)
>
> **Origine**: domanda di Tid del 2026-07-28 durante l'analisi del drawer
> fattura: *«è corretto che sulle due tabelle non ci sia protezione?»*

---

## 1. La risposta breve

**Sì, è coerente con la regola del progetto.** No, non è completo per il portale.

La regola di casa non è «RLS su tutto»: è **RLS sulle testate**, più i figli che
vengono letti da una veste diversa dall'operatore. Verificato su tutto lo schema
`vendite` il 2026-07-28:

| Gruppo | RLS |
| --- | --- |
| Testate documento (`fatture`, `preventivi`, `ordini`, `contratti`, `offerte_commerciali`, `ddt`, `resi`, `commesse`, `fatturazione_lotti`) | ✅ **tutte** |
| Righe (`preventivi_righe`, `ordini_righe`, `contratti_righe`, `ddt_righe`, `resi_righe`, `fatture_righe`, `listini_righe`) | ❌ **nessuna** |
| Figli protetti — le **due** eccezioni | `fatture_scadenze`, `commesse_attivita` |

Quindi `fatture_righe` e `fatture_riepiloghi_iva` si comportano **esattamente
come tutte le altre righe del progetto**. Non è una svista sulle fatture.

---

## 2. Perché le due eccezioni sono eccezioni

Non è «i figli importanti si proteggono». È più preciso di così, e si legge
nelle policy:

```text
commesse_attivita → rls_commesse_attivita_ef_whitelist
                    ruolo OPERATORE, via fn_scope_ef_whitelist_via_commessa

fatture_scadenze  → rls_fatture_scadenze_ef_whitelist   (OPERATORE, via fattura)
                  → rls_fatture_scadenze_ba_ownership   (CLIENTE_PORTALE, via fattura)
```

`fatture_scadenze` è protetta **perché la legge il portale clienti**: la
policy `ba_ownership` esiste solo dove un cliente finale mette gli occhi. Oggi,
in tutto lo schema `vendite`, le policy `ba_ownership` sono esattamente **due**:

- `vendite.fatture` → `rls_fatture_ba_ownership`
- `vendite.fatture_scadenze` → `rls_fatture_scadenze_ba_ownership`

Cioè: **testata della fattura + piano rate**. Il team DB ha pre-armato la RLS
per il portale sulle due tabelle che si aspettava il portale leggesse.

---

## 3. La lacuna

Gli endpoint portale per le fatture **non esistono ancora** — sono dichiarati
come futuri in `apps/portale/api/views.py`:

> *«(futuri) endpoint MVP (me, billing-account, fatture, scadenze,
> ordini-ricevuti, pagamenti)»*

Il giorno in cui nascono, un cliente vedrà **il dettaglio** della sua fattura:
righe e riepilogo IVA. E quelle due tabelle **non hanno la policy
`ba_ownership`**.

| Tabella | `ef_whitelist` (operatore) | `ba_ownership` (portale) |
| --- | --- | --- |
| `vendite.fatture` | ✅ | ✅ |
| `vendite.fatture_scadenze` | ✅ | ✅ |
| **`vendite.fatture_righe`** | ❌ | ❌ |
| **`vendite.fatture_riepiloghi_iva`** | ❌ | ❌ |

**Perché conta più che lato operatore.** Un buco `ef_whitelist` espone i dati di
un altro **emittente** — colleghi della stessa azienda. Un buco `ba_ownership`
espone i dati di un altro **cliente**: nomi, articoli, prezzi e importi di terzi
a un utente esterno che indovina un intero in un URL. Sono due gravità diverse.

**Prova empirica** (2026-07-28, DB di test, ruolo `zeroerp_app` senza GUC):

| Tabella | Righe reali (`pg_class.reltuples`, non filtrato) | Visibili (`count(*)`, filtrato) |
| --- | --- | --- |
| `vendite.fatture` | 7 | **0** ← la RLS morde |
| `vendite.fatture_righe` | 8 | **8** ← nessuna protezione |
| `vendite.fatture_riepiloghi_iva` | 7 | **7** ← nessuna protezione |

> `pg_class.reltuples` non passa dalla RLS, `count(*)` sì: il confronto fra i
> due è il modo più rapido per sapere se una policy morde davvero. Tecnica
> riusabile per ogni verifica futura.

---

## 4. Perché NON blocca il drawer fattura

Il drawer di [brief-be-fe-drawer-fattura](brief-be-fe-drawer-fattura.md) è
**lato operatore** e legge sempre passando dalla testata: `vendite.fatture` ha
`ef_whitelist`, quindi una fattura fuori scope dà 0 righe → 404, e i satelliti
non vengono mai raggiunti. Il brief lo impone come regola vincolante
(«testata prima, 404, poi il resto», §5-bis).

Resta però una difesa che dipende dalla **disciplina di ogni chiamante** invece
che dalla struttura — ed è esattamente il motivo di questo brief: quella
disciplina va bene per un endpoint scritto oggi con la regola in testa, non per
i cinque che verranno.

---

## 5. Cosa si propone

Due policy nuove, **simmetriche a quelle già esistenti su `fatture_scadenze`**
(stesso pattern «via fattura», nessuna colonna denormalizzata: una riga fattura
non cambia mai fattura):

| # | Tabella | Policy | Funzione di scope |
| --- | --- | --- | --- |
| **R1** | `vendite.fatture_righe` | `rls_fatture_righe_ef_whitelist` | `fn_scope_ef_whitelist_via_fattura(...)` |
| **R2** | `vendite.fatture_righe` | `rls_fatture_righe_ba_ownership` | `fn_scope_ba_ownership_via_fattura(...)` |
| **R3** | `vendite.fatture_riepiloghi_iva` | `rls_fatture_riepiloghi_iva_ef_whitelist` | `fn_scope_ef_whitelist_via_fattura(...)` |
| **R4** | `vendite.fatture_riepiloghi_iva` | `rls_fatture_riepiloghi_iva_ba_ownership` | `fn_scope_ba_ownership_via_fattura(...)` |

Le due funzioni di scope **esistono già** e sono in uso su `fatture_scadenze`:
non c'è nulla da progettare, si replica il changeset di quella tabella
cambiando il nome della tabella. `ENABLE` senza `FORCE`, per parità di famiglia.

### 5-bis. Punti da verificare prima di applicare

1. **`vw_fattura_righe_esposte`** è `security_invoker=on`: con la policy su
   `fatture_righe` inizierà a filtrare da sola — **desiderato**, ma va
   verificato che il **canale batch** (`system_process_context`, ruolo
   `BYPASSRLS`) e la **generazione PDF** continuino a vedere tutto. Il PDF gira
   nel worker con identità operatore ripristinata (`operator_identity_context`):
   se i GUC ci sono, la policy `ef_whitelist` passa; **da provare**, non da
   dare per buono.
2. **`fn_generate_fatture_righe`** e la pipeline di fatturazione scrivono su
   `fatture_righe`: verificare che le policy `FOR ALL` (o l'assenza di `WITH
   CHECK` restrittivo) non blocchino le scritture del giro.
3. **pgTAP**: i test esistenti sulle righe fattura girano come owner e **non**
   esercitano la RLS (limite noto, cfr. `brief-db-emissione-fattura-per-documento-sorgente`
   §RLS). La verifica vera è applicativa.
4. **Altri figli fattura**: `fatture_riepiloghi_iva` e `fatture_righe` sono i due
   che il portale leggerà. `fatture_indirizzi`, `fatture_fondi_fattura`,
   `fatture_sdi`, `fatture_log` restano fuori da questo brief — vanno valutati
   quando (e se) il portale li espone.

---

## 6. Cosa NON è in questo brief

- **Le righe degli altri documenti** (`ordini_righe`, `preventivi_righe`, …):
  stessa situazione, ma nessuna veste non-operatore le legge oggi. Sono
  un'ondata a sé, da fare quando il portale/shop cresce — non un rattoppo qui.
- **`FORCE ROW LEVEL SECURITY`**: resta l'ondata coordinata futura, fuori
  perimetro (cfr. `brief-db-rls-commesse` §2).
- **`attivita_fatturabili`**: senza RLS, ma è tabella di lavorazione interna mai
  esposta a vesti esterne.

---

## 7. Registro

### 2026-07-28 · Analisi

Emerso rispondendo alla domanda di Tid sul brief del drawer fattura. La verifica
ha smentito la lettura iniziale («le due tabelle sono scoperte, è un buco»): il
progetto ha una regola coerente — RLS sulle testate, figli solo se letti da una
veste non-operatore — e le righe fattura la rispettano.

La lacuna vera è più stretta e più precisa: **il pre-armamento per il portale è
a metà**. `fatture` e `fatture_scadenze` hanno `ba_ownership`, `fatture_righe` e
`fatture_riepiloghi_iva` no — e sono esattamente il **contenuto** della fattura
che un portale mostrerebbe.

Va chiuso **prima** che nascano gli endpoint portale, non dopo: a quel punto
sarebbe una correzione di sicurezza su codice vivo invece di un prerequisito.

---

## 8. Esecuzione — team DB, 2026-07-29 ✅

Applicato (DB di test; push in arrivo). **Quattro policy**, come proposto in §5:

| Tabella | Policy operatore | Policy portale |
| --- | --- | --- |
| `vendite.fatture_righe` | `rls_fatture_righe_ef_whitelist` (`FOR ALL`) | `rls_fatture_righe_ba_ownership` (`FOR SELECT`) |
| `vendite.fatture_riepiloghi_iva` | `rls_fatture_riepiloghi_iva_ef_whitelist` (`FOR ALL`) | `rls_fatture_riepiloghi_iva_ba_ownership` (`FOR SELECT`) |

Il team DB ha aggiunto una distinzione che il brief non aveva chiesto e che è
**più stretta** della proposta: il portale è `FOR SELECT`, non `FOR ALL`. Un
cliente legge il contenuto della propria fattura e non può scriverlo — giusto
per un documento fiscale, e da non «correggere» scrivendo endpoint portale che
presuppongano il contrario.

### 8a. La regola da non violare (parole del team DB)

> Le policy sui satelliti devono continuare a usare le funzioni di scope della
> **testata** (`fn_scope_ef_whitelist_via_fattura`,
> `fn_scope_ba_ownership_via_fattura`). È quello che rende il filtro
> **tutto-o-niente per fattura**, e tiene completi il `count` di
> `fn_assign_numero_fattura` e la `SUM` di `fn_ricalcola_riepilogo_iva_fattura`.
> Un criterio proprio o una colonna denormalizzata renderebbero possibili le
> **somme parziali** — e un riepilogo IVA parziale non solleva errori, si
> scrive e basta.

È il punto più importante dell'intero brief, e vale la pena riformularlo: il
rischio di una policy «furba» sui satelliti non è vedere meno righe, è
**numerare una fattura contando solo le righe visibili** o **ricalcolare l'IVA
sommandone un sottoinsieme**. Nessuna delle due cosa fallisce rumorosamente: la
prima assegna un progressivo fiscale a un documento incompleto, la seconda
scrive un totale sbagliato e basta.

**Kill-switch** se qualcosa si comportasse in modo inatteso:
`ALTER TABLE vendite.fatture_righe DISABLE ROW LEVEL SECURITY;` — riporta al
comportamento precedente senza toccare le policy.

### 8b. Verifica lato BE (2026-07-29)

Nessuna modifica applicativa necessaria, come previsto dal team DB. Verificato:

| Controllo | Esito |
| --- | --- |
| Le policy mordono (`reltuples` non filtrato vs `count(*)`) | ✅ `fatture_righe` 8 reali → **0** visibili senza GUC (prima 8/8); `riepiloghi_iva` 7 → **0** (prima 7/7) |
| **Il drawer operatore legge ancora** | ✅ risultati **identici** al pre-RLS su tutte e 7 le fatture (righe 0/0/0/1/5/1/1, riepilogo 1 ciascuna) |
| Suite Django | ✅ verde |

> Il secondo controllo era il vero rischio, ed è di quelli che **non fanno
> rumore**: una policy che non passa non solleva un errore, restituisce
> semplicemente **zero righe**. Il drawer avrebbe mostrato una fattura vuota,
> perfettamente formata e perfettamente falsa. Il confronto con i valori
> pre-RLS è l'unico modo per accorgersene.

### 8c. Cosa resta scoperto (fuori dal perimetro di questo brief)

`vendite.note_fatture` **non** ha RLS — come nessuna delle 6 partizioni note del
ciclo attivo. Non è una dimenticanza di questo brief (§6 lo escludeva
esplicitamente), ma è ora l'ultimo satellite fattura senza policy, ed è
raggiungibile dagli endpoint note cablati il 2026-07-28.

Dettaglio: nel BB `PartitionedNoteService` il gate sul padre
(`_ensure_parent_exists`, che interroga `vendite.fatture` ed è quindi
RLS-protetto) è applicato su **`list_note` e `crea_nota`**, ma **non** su
`get_nota` / `aggiorna_nota` / `elimina_nota`. Chi conoscesse la coppia
(`fattura_id`, `note_id`) di un altro emittente potrebbe leggere o cancellare
quella nota. Vale per tutti e 6 i domini, non solo fatture.

Due rimedi possibili, da decidere: **BE** (aggiungere `_ensure_parent_exists`
ai tre metodi del BB — chiude tutti i domini in un colpo) oppure **DB** (RLS
sulle partizioni note). Da valutare a parte.
