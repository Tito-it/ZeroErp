## 📘 Documentazione Concettuale – Tabella `anagrafiche.identita_digitali`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo d'impresa a cui la veste appartiene
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto che la veste dell'operatore umano pretende
> * [config.credenziali](/dbzero/config/tabelle/credenziali) — lo stato della password, che è della credenziale e non della veste
> * [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings) — il profilo di accesso legato alla veste
> * [config.identita_scope_bindings](/dbzero/config/tabelle/identita_scope_bindings) — il perimetro dei dati legato alla veste
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — il processo automatico dietro un'identità tecnica
>
> Approfondimento viste:
>
> * [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare) — le credenziali che il modello non ammette
>
> Approfondimento funzioni:
>
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola «la veste vale oggi»
> * [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) — accende o spegne la credenziale secondo le sue vesti
> * [anagrafiche.trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza) — il tipo di veste coerente col ruolo
> * [anagrafiche.trgfn_identita_digitali_guard_natura_credenziale](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_natura_credenziale) — persona o macchina, non tutte e due
> * [anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin) — il sistema non resta senza amministratore
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — crea l'operatore, con la sua veste spenta
> * [anagrafiche.fn_crea_veste_portale](/dbzero/anagrafiche/funzioni/fn_crea_veste_portale) — crea la veste di un portale
> * [anagrafiche.fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste) — accende la veste
> * [anagrafiche.fn_revoca_veste](/dbzero/anagrafiche/funzioni/fn_revoca_veste) — l'amministratore revoca la veste
> * [anagrafiche.fn_togli_revoca_veste](/dbzero/anagrafiche/funzioni/fn_togli_revoca_veste) — il nuovo invito toglie la revoca
> * [anagrafiche.trgfn_identita_digitali_guard_revoca](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_revoca) — una veste revocata non si riaccende
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — crea l'identità tecnica di un processo
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login
> * [Architettura multi-face auth](/guide/architettura-multi-face-auth) — le porte del software e le loro vesti
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto e i suoi ruoli d'impresa

---

### 🎯 Scopo Principale

`anagrafiche.identita_digitali` contiene le **vesti**: ogni riga lega un ruolo d'impresa di un soggetto
(`soggetto_ruolo_id`) a una credenziale Django (`auth_user_id`), e dice con quale porta del software quella
credenziale entra (`ruolo_applicativo`).

Le porte sono cinque: l'operatore interno (`OPERATORE`), il portale dei clienti (`CLIENTE_PORTALE`), il portale dei
fornitori (`FORNITORE_PORTALE`), lo shop (`SHOP_CUSTOMER`) e il sistema esterno integrato (`API_CLIENT`). La veste è
facoltativa: un soggetto che non usa il software non ne ha.

---

### Una credenziale, più vesti

Una credenziale è una persona, o un processo, che si autentica con una password sola; le sue vesti sono le porte in
cui entra. La stessa credenziale può avere la veste dell'operatore e quella del portale, e lo stesso ruolo d'impresa
può avere più vesti, una per porta (un cliente col portale e con lo shop).

I due indici unici valgono fra le vesti **accese** e sono per coppia, non per colonna:

* `uq_identita_digitali_auth_user_ruolo_attivo` — una credenziale ha al più una veste accesa per tipo;
* `uq_identita_digitali_sr_ruolo_attivo` — un ruolo d'impresa ha al più una veste accesa per tipo.

Le vesti spente non hanno limiti: restano, una per ogni volta che la porta è stata chiusa.

---

### ⭐ Una veste si spegne con `attivo = false` e tiene il suo tipo

Spegnere una veste vuol dire `attivo = false`, qualunque sia il tipo, e il tipo resta. `DISABILITATO` è una voce
storica dell'enum, che lo spegnimento dell'operatore scriveva al posto di `OPERATORE`: la tabella la rifiuta (il
CHECK `chk_identita_digitali_ruolo_non_ritirato`, e prima ancora il guard di coerenza), e resta nel tipo solo perché
la porta lo storico.

---

### La veste revocata non si riaccende

Quando la spegne l'amministratore, con `anagrafiche.fn_revoca_veste`, la veste porta il **segno della revoca**:
`revocata_at` (quando) e `revocata_da_user_id` (chi, la credenziale della sessione). Il CHECK
`chk_identita_digitali_revoca_coerente` vuole i due campi insieme, e una veste revocata spenta.

Il guard `trgfn_identita_digitali_guard_revoca` fa valere il segno su tutta la coppia (credenziale, ruolo anagrafico,
tipo di veste): la veste revocata non si accende, e sulla stessa coppia non nasce né si accende un'altra veste. Il
segno lo scrivono e lo tolgono solo i verbi (la revoca, il nuovo invito con `anagrafiche.fn_togli_revoca_veste`, la
riattivazione di un utente tecnico); una veste revocata non si cancella e non cambia coppia. Il perché e il percorso
completo sono nella guida [Risorse umane e accessi](/guide/risorse-umane-e-accessi#la-revoca).

---

### Le date: dal giorno operativo, aperte in fondo

`valido_dal` è obbligatoria e, se chi scrive non la passa, è il **giorno operativo**, la data di oggi nel fuso
dell'azienda (`script.fn_data_operativa`). `valido_al` è facoltativa: vuota vuol dire senza fine. La fine non viene
prima dell'inizio, e sulle date scatta anche il controllo comune delle finestre di validità.

---

### Accesa non vuol dire utilizzabile

Una veste è **utilizzabile** quando è accesa, oggi sta nelle sue date e il suo soggetto è attivo; la veste
dell'operatore umano pretende in più che il suo rapporto, la risorsa umana dello stesso ruolo, sia acceso e nelle
sue date. La regola ha una sede sola, `script.fn_veste_utilizzabile`.

La credenziale è accesa (`django.auth_user.is_active`) quando **almeno una** delle sue vesti è utilizzabile.
Spegnere una veste, o lasciarla scadere, spegne la credenziale solo se non le resta un'altra veste utilizzabile.
La allinea `anagrafiche.fn_sync_auth_user_is_active`, chiamata dai trigger della tabella e, per le date che
arrivano senza che nessuno scriva, da un passaggio periodico ogni ora: la sua scheda dice chi la chiama e che cosa
nessun trigger copre.

---

### ⭐ Persona o processo: il flag `tecnica`

`tecnica = true` dice che dietro la veste non c'è una persona ma un **processo automatico**. Il processo è un
operatore a tutti gli effetti (`OPERATORE`): attraversa le stesse regole di visibilità e lo stesso perimetro, e un
tipo di veste dedicato avrebbe voluto dire riscriverle una seconda volta.

Il flag non è libero: il guard di coerenza pretende, per l'operatore, un ruolo `PROC_AUTO` se la veste è tecnica e
un ruolo `RIS_UMANA` di una persona fisica pura se non lo è. Marcare tecnica la veste di una persona non passa. Il
default è `false`. Le identità tecniche le crea `script.fn_crea_utente_tecnico`, e il legame col processo sta in
`dbops.processi_identita`.

---

### Il tipo di veste deve essere coerente col ruolo

La veste dell'operatore sta su un ruolo `RIS_UMANA` (di una persona fisica pura) o `PROC_AUTO`; quella del portale
dei clienti e dello shop su un ruolo cliente `CL`; quella del portale dei fornitori su un ruolo `FO`. La veste del
sistema esterno non ha vincoli sul ruolo. Lo controlla, a ogni scrittura,
`anagrafiche.trgfn_identita_digitali_guard_coerenza`.

---

### Una credenziale è di una persona o di una macchina

Tutte le vesti di una credenziale, anche le spente, hanno la stessa natura: di macchina se sono del sistema
esterno o tecniche, di persona altrimenti. Lo impone `anagrafiche.trgfn_identita_digitali_guard_natura_credenziale`.
Su questa regola poggia la categoria di una credenziale (`script.fn_categoria_accesso`), cioè il tab dell'area
«Accessi» in cui sta.

---

### Lo stato della password non è della veste

Tentativi sbagliati, blocco e cambio di password obbligatorio sono della **credenziale**, perché la password è una
sola per tutte le porte: stanno in `config.credenziali`, non qui.

---

### L'amministratore è un profilo legato alla veste

Il passaggio oltre tutti i permessi non è una colonna della veste: è il **profilo** di tipo `SUPER_ADMIN`, legato a
una veste dell'operatore con una riga di `config.profili_accesso_bindings`. Il profilo non ha un id scritto da
nessuna parte: lo risolve `config.fn_profilo_super_admin_id`. Il legame lo scrive, alla creazione dell'operatore,
`anagrafiche.fn_crea_risorsa_umana_v2` (che `fn_crea_operatore_v2` chiama); dopo, lo mettono e lo tolgono
`config.fn_lega_profilo_identita` e `config.fn_slega_profilo_identita`. Chi è amministratore lo dice
`script.fn_is_super_admin`.

La veste dell'operatore nasce **spenta** e la accende l'attivazione dell'invito; i suoi legami coi profili, quello
`SUPER_ADMIN` compreso, nascono invece attivi, perché porta e profili non si legano sull'`attivo`. Una veste spenta
tiene i suoi legami, che servono al reinvito. Che il sistema non resti senza un amministratore lo presidia la
scheda di `trgfn_identita_digitali_guard_ultimo_super_admin`.

---

### Che cosa fanno i trigger della tabella

Oltre ai tre guard sul tipo, sulla natura e sull'ultimo amministratore, i trigger della tabella controllano le date,
impediscono di spegnere una veste che ha ancora un perimetro dei dati attivo in `config.identita_scope_bindings`,
allineano la credenziale dopo ogni scrittura che cambia la validità, e tengono audit, identificativo di transazione
e storico. L'elenco, con l'ordine, sta nella scheda.

---

### La chiave esterna verso Django

`auth_user_id` punta a `django.auth_user`, e una credenziale con delle vesti non si cancella (`ON DELETE RESTRICT`).
La chiave esterna nasce solo dove lo schema Django c'è già quando la migrazione gira: su un database ricostruito da
zero, dove Liquibase gira prima delle migrazioni Django, manca.

---

### ⚠️ Che cosa oggi non copre

* **Il flag `tecnica` su una veste che non è dell'operatore.** Il guard di coerenza legge il flag solo per
  `OPERATORE`: una veste del portale o dello shop con `tecnica = true` passa, e fa della sua credenziale una
  credenziale di macchina.
* **Il profilo `SUPER_ADMIN` su un'identità tecnica.** Un processo non deve passare oltre tutti i permessi, ma nessun
  controllo impedisce di legare quel profilo a una veste con `tecnica = true`.

---

### Codici errore

* `E_RUOLO_APPLICATIVO_RITIRATO` — una veste `DISABILITATO`; il CHECK `chk_identita_digitali_ruolo_non_ritirato` lo
  ripete alla tabella.
* `E_SOGGETTI_RUOLI`, `E_AUTH_USER_SOGGETTO_CON_PIVA`, `E_AUTH_USER_SOGGETTO_SENZA_CF`,
  `E_RUOLO_APPLICATIVO_NON_GESTITO` — il tipo di veste incoerente col ruolo (la scheda del guard di coerenza).
* `E_CREDENZIALE_PERSONA_E_SISTEMA` — una credenziale che mescolerebbe persona e macchina.
* `E_VESTE_REVOCATA` — una veste accesa sulla coppia di una veste revocata.
* `E_VESTE_REVOCA_SOLO_DAL_VERBO` — il segno della revoca scritto o tolto fuori dai verbi, o una veste revocata
  cancellata o spostata.

---

### Test

* `db/pgtap/anagrafiche/test-identita-digitali-unique-multi-veste.sql` — i due indici unici fra le vesti accese, e
  le spente che non contano. È **rosso** in baseline.
* `db/pgtap/anagrafiche/test-veste-operatore-spenta-v1.sql` — la veste dell'operatore si spegne con `attivo = false`
  e tiene il tipo, `DISABILITATO` rifiutato.
* `db/pgtap/anagrafiche/test-identita-tecnica.sql` — il flag `tecnica`, il suo default e i presidi dei processi.
* `db/pgtap/anagrafiche/test-area-accessi-v1.sql` — la natura della credenziale e la categoria.
* `db/pgtap/anagrafiche/test-veste-revocata-v1.sql` — il segno della revoca, il guard, i due verbi col loro permesso,
  lo stato `REVOCATA`.

---

### Note di migrazione

* 2026-04-20 — modello a più vesti: una credenziale può avere più vesti accese, una per tipo. Prende il posto del
  ponte `risorse_umane_auth_user`, che legava la sola risorsa umana alla credenziale e che dal 2026-09-12 non esiste
  più, nemmeno come vista. Il privilegio di amministratore, che era una colonna del ponte, diventa un profilo.
* 2026-09-04 — nasce il flag `tecnica`.
* 2026-09-25 — tentativi sbagliati, blocco e cambio password escono dalla veste e vanno in `config.credenziali`;
  la veste dell'operatore nasce spenta.
* 2026-10-02 — `DISABILITATO` non è più un tipo di veste; nasce la regola «persona o macchina».

---

{% include-markdown "signature-core.md" %}
