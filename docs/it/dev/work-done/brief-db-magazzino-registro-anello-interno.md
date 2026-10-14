# Brief DB — il registro di magazzino non conosce i suoi consumatori

> **Destinatario:** team DB (`dev/db-tid`). Nessuna richiesta a BE/FE: le due
> funzioni che si spostano sono interne, il backend non le chiama (letto il
> 2026-10-01: zero riferimenti in `backend/` e `frontend/src`), e la colonna
> tolta da D-3 non la legge nessuno.
>
> **Origine.** La segnalazione sulla [mappa concentrica](../../mappa-concentrica.md):
> con i Lotti 3 e 3-bis la bolla e il reso di `vendite` scaricano e ricaricano la
> merce, e la mappa dice *«mai dipendenze inverse o laterali»*. Discussa e decisa
> da Tid il **2026-10-01** (§2).
>
> **Stato al 2026-10-04:** ✅ **chiuso** — nove changeSet `20261001-18 → -26`
> applicati, le tre sedi della postura, un pgTAP nuovo e due adeguati, la doc
> `manual/`; corsa col runner e doc auto-gen rigenerata (Tid). Verificato il
> 2026-10-04: nessuna ricaduta su BE/FE (§9).
>
> **Perimetro:** spostare in `vendite` i due posting della bolla e del reso,
> togliere la FK dell'asset verso il contratto (D-3), e mettere un presidio che
> impedisca al registro di tornare a nominare un suo consumatore. ⛔ Fuori:
> qualunque cambio di comportamento — movimenti, costi, permessi e porte restano
> identici. Unica differenza visibile, dichiarata in §2.1: il codice del guard di
> parametro dei due posting.

---

## 0. In due parole, senza tecnicismi

Lo schema `magazzino` contiene due cose diverse. Il **registro** dice dove sta la
merce e quanto vale, e ha una sola porta per scriverci. I **documenti di
magazzino** sono gli inventari, le rettifiche e i trasferimenti interni.

Il registro è un servizio, come il motore che stampa i PDF: chi muove merce lo usa,
e lui non deve sapere chi è. Invece due funzioni che stavano nel registro
leggevano le tabelle della bolla e del reso: il registro «conosceva» le vendite. Le
spostiamo dentro le vendite, che è dove servono, e mettiamo un controllo automatico
che lo impedisca in futuro. Il programma fa esattamente le stesse cose di prima.

Il controllo, al primo giro, ha trovato una seconda cosa che nessuno cercava: il
seriale di un bene sapeva sotto quale contratto di vendita stava. Anche quel legame
è stato tolto: se servirà, sarà il contratto a dire quali beni ha.

---

## 1. Il fatto (struttura, letta il 2026-10-01)

Corpi delle funzioni nella doc auto-generata, commenti esclusi; FK e dipendenze dal
catalogo (`pg_depend`).

| Verso | Oggetti | Giudizio |
| --- | --- | --- |
| `vendite` → `magazzino` | `ddt.magazzino_id`, `resi.magazzino_id` (FK); `fn_cambia_stato_ddt`, `fn_conferma_reso`, `fn_annulla_reso`, `fn_ddt_merce_da_movimentare`, `fn_reso_merce_da_rientrare`, `trgfn_ddt_default_magazzino`, `trgfn_ddt_guard_magazzino` | ✅ verso l'interno, dopo D-1 |
| `magazzino` → `vendite` | `magazzino.fn_posta_ddt` (legge `ddt`, `ddt_righe`, `ddt_righe_componenti`, `ddt_righe_prelievi`) e `magazzino.fn_posta_reso` (legge `resi`, `resi_righe`, `resi_righe_rientri`, `ddt_righe`, `ddt_righe_prelievi`, `ddt_righe_componenti`) | 🔴 **verso inverso**: il registro conosce un consumatore |
| `magazzino` → `vendite` | ⚠️ **trovata dal presidio, non dalla prima lettura**: la FK `fk_mag_assets_contratto`, `magazzino.assets.contratto_id` → `vendite.contratti` (nata il 2025-10-01, «FK opzionale verso contratto/noleggio», rimasta nullable col Lotto 1). Nessuna funzione, vista, endpoint o pgTAP la legge o la scrive | 🔴 **verso inverso**, nei dati → D-3 |

⚠️ La prima stesura di questa sezione diceva *«il registro non ha FK verso i
documenti»*: era letto sulle funzioni e sulla prosa, non sul catalogo. Il presidio
(§4), scritto per tenere la regola, l'ha smentita alla prima esecuzione.

Il resto del registro **non** nomina `vendite` nel codice: le menzioni in
`fn_storna_movimenti_sorgente` e su `trasferimenti` sono commenti. Un movimento
nomina la sua origine per tipo e chiave (`config.sorgenti`), che è il punto di
estensione deciso da D-4 / D-7.

ℹ️ Restano, e sono il verso giusto: i `block_deact` che il framework ATTIVO monta
sul padre (`trg_magazzini_a10_ddt_block_deact_upd`, `trg_ubicazioni_a10_resi_righe_rientri_block_deact_upd`,
… sei al 2026-10-01) portano `'vendite', '<tabella>'` come **argomento** di
`dbops.trgfn_prevent_deactivate_if_children`. Sono il riflesso meccanico di una FK
che punta **verso** il registro, generato per pattern su ogni padre: non sono una
dipendenza del registro, e il presidio non li conta (§4).

---

## 2. Le decisioni — Tid, 2026-10-01

### ✅ D-1 — Il registro di magazzino è un servizio dell'anello 2

Lo schema `magazzino` si legge come **due** cose:

* il **registro**, nell'**anello 2** come `documenti` e `pratiche`: magazzini,
  ubicazioni, lotti, seriali, causali, `movimenti`, valore e disponibilità, blocchi,
  la primitiva `fn_scrivi_movimento`, la utility di storno, i verbi del blocco;
* i **documenti di magazzino**, nell'**anello 3**: inventari, rettifiche,
  trasferimenti interni, con i loro verbi di posting.

**La ragione sul modello**: la forma del registro era già quella di un servizio
del centro — una porta sola (M-2), un catalogo delle sorgenti come punto di
estensione (D-4, D-7). Con questa lettura `vendite` → registro è una dipendenza
**verso l'interno**, e la regola «mai laterali» resta intera, senza eccezioni.

⚠️ **Predisposto, non ancora contratto** (`sviluppo-concentrico`, principio 7): i
consumatori esterni sono due documenti dello **stesso** dominio. Il secondo
dominio è `acquisti`, Lotto 4.

**Scartate**: un'**eccezione** «documento ↔ magazzino», che avrebbe coperto proprio
il ciclo da togliere e andrebbe riscritta a ogni dominio che muove merce; un
**punto di estensione a eventi**, perché il carico deve stare nella stessa
transazione del cambio di stato (D-L3-e) e un registro di agganci sincrono con un
solo consumatore sarebbe un meccanismo prima del suo bisogno.

*Applicata*: la mappa concentrica è aggiornata (diagramma, anello 2, dipendenze
dell'anello 3, nota sotto la matrice), e la decisione aperta è chiusa nel
[changelog della mappa](../mappa-concentrica-changelog.md) (1 ottobre 2026).

### ✅ D-2 — Il posting sta nel dominio che muove la merce

**Chi scrive merce scrive il proprio posting nel proprio schema** e chiama la
primitiva; il registro non legge mai le tabelle di un documento.
`magazzino.fn_posta_ddt` → `vendite.fn_posta_ddt`, `magazzino.fn_posta_reso` →
`vendite.fn_posta_reso`. Per `acquisti` il posting nascerà in `acquisti`.

⭐ **I documenti di magazzino non cambiano**: `fn_posta_inventario`,
`fn_posta_rettifica`, `fn_posta_trasferimento` leggono tabelle di `magazzino` e
stanno dove devono.

**Il nome**: lo stesso, nello schema nuovo. Il posting è «della bolla» e «del
reso»; lo schema dice già chi lo possiede.

### ✅ D-3 — L'asset non sa sotto quale contratto sta (Tid, 2026-10-01, sera)

Emersa dal presidio (§1, terza riga). Tre strade proposte: togliere la FK nello
stesso giro, dichiararla come debito nel presidio, escludere le FK dal presidio.
**Tid: si toglie, nello stesso giro.**

**La ragione sul modello**: è D-2 applicata ai dati — chi usa il legame lo porta.
Se un contratto dovrà sapere quali asset ha in carico, il legame nascerà in
`vendite` (sulla riga di contratto o in una tabella del contratto) e punterà
all'asset: verso l'interno. Il presidio nasce a **zero**, senza eccezioni scritte.

### 2.1 Scostamento dichiarato, emerso scrivendo — il codice del guard di parametro

I due posting sollevavano `E_MAG_CHIAMATA_NON_VALIDA` sul guard di parametro (un
id ≤ 0, una fase che non esiste). Nello schema nuovo sollevano
**`E_VENDITE_CHIAMATA_NON_VALIDA`**: il catalogo dei codici lo definisce *«guard di
parametro delle funzioni di vendite»*, e il codice nomina la famiglia della
funzione che lo solleva. Stessa classe (`TECNICO`), stesso testo (*«Chiamata non
valida a %s: %s.»*), stessi due valori: per il backend e per l'operatore nessuna
differenza, ed è un ramo che nessuna interfaccia raggiunge. Cambiano anche area e
nome nel log (`'vendite'`, `'vendite.fn_posta_ddt'`). ⚠️ Non è una decisione di Tid:
se la preferisce identica, è una sostituzione per changeSet (`-18`, `-19`) finché
non sono applicati.

---

## 3. Il lavoro, pezzo per pezzo — scritto il 2026-10-01

> Corpi di partenza: la **doc auto-generata**, confrontata con l'ultimo YAML e col
> `prosrc` vivo (md5 identico, i quattro corpi). Le firme non vengono dal blocco
> auto-gen: sono scritte ancorate con `%TYPE` (firma, `RETURNS TABLE`, `COMMENT`,
> `DROP`, `REVOKE`), e i `DECLARE` erano già ancorati. Il corpo è generato da uno
> script che dichiara le sostituzioni, ciascuna col numero atteso di occorrenze.

| # | File | Che cosa | Discende da |
| --- | --- | --- | --- |
| **P-1** | `20_code/vendite/20261001-18-create-fn-posta-ddt-in-vendite` | `vendite.fn_posta_ddt(vendite.ddt.id%TYPE, text)`: corpo identico a `magazzino.fn_posta_ddt` salvo area/funzione nel log e il codice di §2.1; DEFINER, `search_path` bloccato; COMMENT con la sede e la ragione | D-2 |
| **P-2** | `20_code/vendite/20261001-19-create-fn-posta-reso-in-vendite` | `vendite.fn_posta_reso(vendite.resi.id%TYPE)`: idem da `magazzino.fn_posta_reso`. La lettura di `magazzino.movimenti` (il costo dell'uscita) resta: è un consumatore che legge il registro | D-2 |
| **P-3** | `20_code/vendite/20261001-20-update-fn-cambia-stato-ddt-posting-in-vendite`, `-21-update-fn-conferma-reso-posting-in-vendite` | i due verbi chiamano lo schema nuovo (due chiamate in `fn_cambia_stato_ddt`, una in `fn_conferma_reso`); nel COMMENT cambia solo il nome. Firme invariate. `fn_annulla_reso` non si tocca: storna con la utility del registro | D-2 |
| **D-3** | `00_schema/magazzino/20261001-22-alter-assets-drop-contratto` | `DROP COLUMN magazzino.assets.contratto_id` (la FK cade con la colonna); COMMENT della tabella. preCondition `expectedResult: 0` sulle righe con un contratto: un legame scritto a mano non si butta in silenzio | D-3 |
| **D-3** | `80_data/changelog/20261001-25-delete-fk-index-policy-assets-contratto` | `DELETE` della riga di `fk_mag_assets_contratto` da `dbops.fk_index_policy`. Il CSV base è dormiente e non si tocca (forma di `20260915-12`) | D-3 |
| **P-6** | `20_code/dbops/20261001-23-create-vw-magazzino-dipendenze-inverse` | il presidio (§4) | D-1 |
| **P-6** | `90_end/20261001-26-grant-vw-magazzino-dipendenze-inverse-app` | `GRANT SELECT` all'app per dev (in CI lo dà il loop) | — |
| **P-6** | `80_data/sql/dbops/presidi.csv` | la riga a catalogo, natura **CANCELLO** (§4) | — |
| **P-4 + P-5** | `90_end/20261001-24-ritira-posting-dal-registro-e-postura` | `DROP` di `magazzino.fn_posta_ddt` e `fn_posta_reso`; `REVOKE EXECUTE … FROM PUBLIC, zeroerp_app` sulle due di `vendite`. ⛔ In `90_end` e non in `20_code`: `90_end/20260928-83` e `-98` pretendono le funzioni del registro esistenti (`onFail: HALT`), e su un database da zero `90_end` gira dopo `20_code`. Il nome viene dopo `20260928-98` in `includeAll` | D-2, permesso D-4 |
| **P-5** | `90_end/ci_apply/20260205-41` (loop, `runOnChange`) e `scripts/sql/provision_db_roles.sql` | le altre due sedi: in `v_fn_riservate` e nel blocco «LA PORTA SULLE FUNZIONI» le voci passano da `magazzino.fn_posta_*` a `vendite.fn_posta_*`; il blocco del provisioning ora filtra per `(schema, funzione)` | permesso D-4 |
| **P-7** | `db/pgtap/magazzino/` | §5 | — |
| **P-8** | doc | `manual/`: pagina nuova `dbops/vw_magazzino_dipendenze_inverse`, `magazzino/assets` (il contratto esce); mappa concentrica e suo changelog; una riga nei registri dei Lotti 3 e 3-bis (che restano come sono: sono storia). Nessuna pagina `manual/` da cancellare: i due posting non ne avevano. Le pagine auto-generate si rigenerano | — |

---

## 4. Il presidio — la regola diventa un controllo

La matrice delle dipendenze era **scritta**, e nessun test la controllava: il verso
inverso è entrato senza che niente diventasse rosso — **due volte**, come ha
mostrato il presidio stesso. Ora la regola si legge sul codice vivo:

> **nessun oggetto dello schema `magazzino` nomina uno schema di processo**
> (`vendite`, `acquisti`, `pagamenti`).

`dbops.vw_magazzino_dipendenze_inverse` (`security_invoker`, legge solo il
catalogo, ~75 ms su `zeroerp_ci`). Colonne: `oggetto`, `tipo_oggetto`, `come`,
`schema_nominato`, `nominati`. **Due lenti**:

| Lente | Che cosa vede |
| --- | --- |
| `CATALOGO` — `pg_depend` | ogni dipendenza registrata da un oggetto di `magazzino` verso una tabella, vista, sequenza, funzione o tipo di uno schema di processo: FK, viste, default, policy, trigger (la funzione eseguita), tipi nella firma di una funzione, corpi SQL standard. Esatta: non legge testo |
| `CORPO` — `prosrc` | le funzioni di cui il catalogo non registra le dipendenze (plpgsql e sql a stringa), con i commenti di riga `--` tolti (lezione del rubinetto del primo motivo). Cerca `<schema>.` a inizio parola. I `COMMENT ON` non stanno in `prosrc`: i rimandi restano liberi |

**Scostamenti dalla prima stesura, dichiarati:**

* ⭐ **viste e FK dal catalogo, non dal testo** (`pg_get_viewdef` era la proposta):
  `pg_depend` è esatto, e copre in un colpo anche trigger, policy, default e firme;
* ⭐ **natura `CANCELLO`, non `ZERO`** (`cadenza MAI`, `presidiato_da` il pgTAP): la
  regola è sul **codice**, e il controllo che la tiene è il pgTAP in CI, che ferma
  la build. È la natura della vista gemella `vw_audit_log_scrittori_fuori_perimetro`;
  ripeterla nel digest sarebbe rumore (manuale di `dbops.presidi`);
* 🔴 **trovato provando** (2026-10-01): `pg_identify_object` restituisce lo schema
  **NULL** per regole (cioè viste), trigger, policy e default. Alla prima stesura la
  lente `CATALOGO` era cieca sulle viste: l'ha detto il testimone della vista, rosso
  alla prima corsa. Corretto: quei quattro tipi prendono lo schema della tabella che
  li porta (`ev_class`, `tgrelid`, `polrelid`, `adrelid`), e ognuno ha il suo
  testimone.

**Il caso si costruisce** (Regola zero): il pgTAP crea in transazione **sei
testimoni** in `magazzino` — una funzione plpgsql che legge `vendite.ddt` (CORPO),
una vista su `acquisti.ordini`, una FK verso `pagamenti.enti_incasso`, un trigger che
esegue una funzione di `vendite`, una policy e un default che nominano `vendite.ddt`
(CATALOGO) — e il gemello negativo: una funzione che nomina `vendite.ddt` **solo**
in un commento non compare.

**Zero**, non una soglia: dopo P-1 … P-4 e D-3 il conteggio è zero, e una soglia
lascerebbe crescere il buco.

⚠️ **Il perimetro è dichiarato, non dedotto**: l'elenco degli schemi di processo sta
nella vista, e uno schema di processo nuovo si aggiunge lì, con un changeSet.
`contabilita` non c'è (vuoto, fuori perimetro).

**Che cosa non vede, dichiarato** (anche nell'intestazione del changeSet): gli
**argomenti** dei trigger (i `block_deact` di §1, il verso giusto) e un nome di
schema composto a runtime o fra virgolette doppie — nessuna funzione di magazzino lo
fa.

---

## 5. Il censimento dei pgTAP — rifatto il 2026-10-01 sui file

| File | Che cosa nomina | Fatto |
| --- | --- | --- |
| `magazzino/test-registro-non-nomina-i-consumatori-v1` | **nuovo**, 14 test: la vista vuota, il gemello «esiste» (le FK di `vendite` verso il registro ci sono, e il catalogo le registra), il perimetro dichiarato, i sei testimoni e il negativo, i posting fuori dal registro e in `vendite` DEFINER, `assets` senza `contratto_id`, la riga a catalogo. `pgtap-runner: owner` col motivo scritto: fa DDL in `magazzino` | ✅ |
| `magazzino/test-blocco-manuale-e-porta-lotto3-v1` (test 12 e 14) | `('magazzino', 'fn_posta_ddt')` | → `('vendite', 'fn_posta_ddt')`; nel 14 anche l'ordine del testo atteso (`vendite.fn_posta_ddt` in coda) |
| `magazzino/test-reso-carico-v1` (test 24) | `has_function_privilege(…, 'magazzino.fn_posta_reso(bigint)', …)` | → `vendite.fn_posta_reso(bigint)` |
| i pgTAP che emettono, consegnano o annullano bolle e confermano resi (scarico, trasferimento, reso, kit) | **niente**: chiamano i verbi | nessuno, ed è la prova che lo spostamento non cambia il comportamento (§7.2) |

Presidi trasversali che un giro di funzioni plpgsql accende sempre:
`dbops/test-riferimenti-morti-v1` (`plpgsql_check` su ogni funzione),
`script/test-rubinetto-primo-motivo-v1` (i due posting non chiamano l'helper;
`fn_cambia_stato_ddt` lo chiamava e lo chiama: il conteggio non si sposta),
`dbops/test-catalogo-presidi-v1` (la vista nuova è in `dbops`: dev'essere a
catalogo, e lo è), `script/test-catalogo-messaggi-errore-completo` e
`dbops/test-vw-codici-errore-motivo-nominato` (§2.1 cambia il codice sollevato da due
funzioni). Tutti provati in §7.2.

---

## 6. Che cosa NON entra

| Cosa | Perché |
| --- | --- |
| spostare fisicamente il registro in uno schema suo | è la stessa decisione scritta due volte: lo schema `magazzino` resta, la mappa dice che cosa è anello 2. Si riconsidera solo se un secondo dominio lo chiedesse |
| le funzioni di `script` che nominano tabelle di `vendite` (`fn_check_ddt_merce`, `fn_check_reso_merce`, …) | `script` è la sede delle check condivise e chiama già i domini da prima del magazzino: è un'altra domanda, non questo debito |
| il legame contratto → asset in `vendite` | D-3 lo toglie dal registro e basta: nascerà quando un contratto dovrà davvero sapere quali beni ha, con il suo consumatore |
| il posting di `acquisti` | Lotto 4: nasce in `acquisti` per D-2 |
| l'apply, i pgTAP col runner, il commit, la rigenerazione della doc | Tid |

---

## 7. La prova pre-apply — 2026-10-01

### 7.1 Come

Su **`zeroerp_ci`** (il database ricostruito da zero) come migratore `zeroerp`, in
una transazione annullata: l'SQL **estratto** dai nove changeSet
(`changes[].sql.sql` con `yaml.safe_load`, `COMMENT` e `DO` compresi) nell'ordine del
master — `00_schema`/`20_code`, `80_data`, `90_end` — con le `sqlCheck` delle
preCondition eseguite e confrontate col valore atteso, più la riga nuova di
`presidi.csv` (⚠️ seed **simulato** con un `INSERT`: il loader vero lo prova solo
l'apply). Poi ogni pgTAP, ciascuno nella sua sessione, sopra la stessa
transazione.

### 7.2 Esito

| Che cosa | Esito |
| --- | --- |
| preCondition | tutte all'atteso (`0`, `2`, `1`, `2`, `1`, `2`) |
| firme | `pg_get_function_identity_arguments` e `pg_get_function_result` **byte-identici** a quelli delle funzioni d'origine; una funzione per nome; tutte `prosecdef = t` col `search_path` bloccato |
| postura | `vendite.fn_posta_ddt` / `fn_posta_reso`: niente `EXECUTE` all'app né a PUBLIC; la vista leggibile dall'app |
| la vista | **zero righe** dopo i changeSet; **tre** prima (i due posting e la FK dell'asset) |
| `test-registro-non-nomina-i-consumatori-v1` | 14/14 (🔴 alla prima corsa, ancora a 11 test, 10/11: la vista cieca, §4) |
| `test-reso-carico-v1` | 25/25 |
| `test-blocco-manuale-e-porta-lotto3-v1` | 13/14 — il test 8 (*«come app, `UPDATE … WHERE false` risponde 42501»*) è rosso **da migratore per costruzione**, identico sul file intatto senza i changeSet; come app è verde |
| `test-catalogo-presidi-v1` · `test-riferimenti-morti-v1` · `test-rubinetto-primo-motivo-v1` | 11/11 · 9/9 · 7/7 |
| `test-catalogo-messaggi-errore-completo` · `test-vw-codici-errore-motivo-nominato` · `test-storico-scope-policy-v1` | 7/7 · 8/8 · 33/33, identici prima e dopo |
| comportamento: i 25 pgTAP che chiamano `fn_cambia_stato_ddt`, `fn_conferma_reso` o `fn_annulla_reso` | **identici prima e dopo**, file per file. `magazzino/test-ddt-scarico-v1` 16/16, `test-ddt-trasferimento-v1` 13/13, `test-reso-carico-kit-seriali-v1` 14/14. Quelli di `vendite` si fermano da migratore nella fixture (scope emittente, billing account) allo **stesso** punto prima e dopo: non dicono niente su questo cantiere, lo dirà il runner come app |

### 7.3 Che cosa la prova non copre — a Tid

* **l'apply** su dbdev (e il loader vero di `presidi.csv`, che si sveglia: i due
  mirror `20260910-08`/`-35` rileggono il file intero);
* la **corsa col runner come app**: i tre file di §5, i presidi trasversali di §5, e
  i pgTAP di `vendite` che emettono bolle e confermano resi (§7.2, ultima riga);
* su dbdev il `DELETE` di `-25` trova la riga (1 al 2026-10-01); su `zeroerp_ci` non
  c'era già (0): innocuo in entrambi i casi;
* la rigenerazione della doc auto-gen (le due funzioni nuove in `vendite`, le due
  sparite da `magazzino`, la vista nuova, la colonna sparita da `assets`).

---

## 8. Riferimenti

- [Mappa concentrica](../../mappa-concentrica.md) — la regola degli anelli (§1), l'anello 2, la matrice.
- [Lotto 3](brief-db-magazzino-lotto-3-scarico-da-ddt.md) (P-7, `fn_posta_ddt`) ·
  [Lotto 3-bis](brief-db-magazzino-lotto-3-bis-carico-da-reso.md) (P-7, `fn_posta_reso`).
- [Analisi carico e scarico](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md) — M-2 (la primitiva), §6 (l'identità e le sorgenti).
- Vista gemella del cancello: `dbops.vw_audit_log_scrittori_fuori_perimetro` (`20_code/dbops/20260911-32`).
- [linee-guida-sql §11.8](../../linee-guida-sql.md) — le tre sedi della postura.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-01 | Prima stesura, dalla segnalazione sulla mappa. Misurato sulla struttura: il verso `magazzino` → `vendite` sono **solo** i due posting. ✅ **Tid**: D-1 (il registro è un servizio dell'anello 2, predisposto finché `acquisti` non è il secondo dominio) e D-2 (il posting sta nel dominio che muove la merce). Mappa aggiornata nello stesso giro. ⚠️ Emerso scrivendo: il DROP delle due funzioni va in `90_end`, perché due `preConditions` di `90_end` le pretendono esistenti |
| 2026-10-01 (sera) | 🔴 **Il presidio smentisce §1 alla prima esecuzione**: oltre ai due posting c'è la FK `magazzino.assets.contratto_id` → `vendite.contratti`, mai letta né scritta. La prima lettura guardava funzioni e prosa, non `pg_depend`. ✅ **Tid, D-3: si toglie nello stesso giro.** |
| 2026-10-01 (sera) | ✅ **Scritto, non applicato**: nove changeSet `20261001-18 → -26`, le tre sedi della postura, un pgTAP nuovo (14 test) e due adeguati, `manual/` di `assets` e della vista, mappa e changelog. Scostamenti dichiarati: il codice del guard di parametro (§2.1), il presidio dal catalogo e di natura `CANCELLO` (§4). 🔴 **Trovato provando**: `pg_identify_object` dà schema NULL a viste, trigger, policy e default — la lente era cieca sulle viste, l'ha detto il testimone; corretta, e tre testimoni in più. ✅ Prova pre-apply su `zeroerp_ci` (§7) |
| 2026-10-04 | ✅ **Chiuso**: apply, corsa col runner come app e doc auto-gen rigenerata (Tid; la doc mostra i due posting in `vendite`, spariti da `magazzino`, la vista nuova, `assets` senza contratto). Riletto il codice: nessuna ricaduta su BE/FE — `backend/` e `frontend/src` non nominano i due posting né la vista, l'unica query su `magazzino.assets` (`lookup_assets`) non legge `contratto_id`, e `E_VENDITE_CHIAMATA_NON_VALIDA` ha già policy e ripiego. Spostato in `work-done/` |
