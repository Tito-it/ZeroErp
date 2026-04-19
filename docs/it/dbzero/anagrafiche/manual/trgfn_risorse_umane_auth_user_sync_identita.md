## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_auth_user_sync_identita`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
**Approfondimento funzioni:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La trigger function
**`anagrafiche.trgfn_risorse_umane_auth_user_sync_identita()`** è un
**trigger-ponte temporaneo** (§4.6.D.4 WIP multi-face-auth) che propaga
gli `INSERT`/`UPDATE` sul bridge legacy `risorse_umane_auth_user` verso
il nuovo bridge `identita_digitali` (identità `OPERATORE`) e mantiene
sincronizzato il binding `SUPER_ADMIN` con la colonna `ruolo_sistema`.

Serve durante la transizione **expand-align-contract** per:

1. **Mantenere funzionanti i test pgTAP esistenti** che usano `INSERT`
   / `UPDATE` diretti su `risorse_umane_auth_user` come fixture.
2. **Mantenere coerente il backend Python legacy** (
   `amm_software_repository` scrive ancora su RUA) tra merge della
   **PR1 DB** e merge della **PR2 backend**.

È progettato per essere **rimosso** al cutover §4.6.H.3 quando il bridge
legacy viene eliminato.

---

### Eventi gestiti

* `AFTER INSERT`
* `AFTER UPDATE OF attivo, ruolo_sistema, tentativi_falliti,
   bloccato_fino_a, deve_cambiare_password, invito_inviato_at,
   totp_obbligatorio, storicizza, risorsa_umana_id, auth_user_id`

`UPDATE OF` mirato per evitare scatti inutili su modifiche di campi non
rilevanti (audit, meta, ecc.).

Fase `z80` (post-guard, pre-sync auth_user `z90`).

---

### Logica applicata

#### 1. UPSERT identità OPERATORE

Per ogni riga INSERT/UPDATE su `risorse_umane_auth_user`:

* Risolve `soggetto_ruolo_id` e finestra temporale (`valido_dal`,
  `valido_al`) dalla `risorse_umane` parent (`ru.id = NEW.risorsa_umana_id`).
* Esegue `INSERT ... ON CONFLICT (auth_user_id) DO UPDATE` con:
  * `ruolo_applicativo = 'OPERATORE'` (fisso)
  * `attivo = NEW.attivo AND NEW.ruolo_sistema <> 'DISABILITATO'`
    (DISABILITATO legacy → soft-off sull'identità)
  * Campi stateful copiati: `deve_cambiare_password`, `invito_inviato_at`,
    `tentativi_falliti`, `bloccato_fino_a`, `totp_obbligatorio`, `storicizza`

#### 2. Sync binding SUPER_ADMIN

In base a `NEW.ruolo_sistema`:

| `ruolo_sistema` legacy | Azione sul binding `(profilo_id = 9100, identita)` |
|------------------------|----------------------------------------------------|
| `'ADMIN'`              | INSERT se mancante; UPDATE `attivo = true` se esistente-inattivo |
| `'OPERATIVO'`          | DELETE binding (l'utente non è più super admin) |
| `'DISABILITATO'`       | DELETE binding (doppia sicurezza) |

Il `INSERT` usa pattern `WHERE NOT EXISTS` anziché `ON CONFLICT` per
gestire correttamente l'**indice parziale UNIQUE**
`uq_profili_accesso_bindings_identita` (che è su
`(identita_digitale_id) WHERE identita_digitale_id IS NOT NULL`).

---

### Interazione con trigger adiacenti

Il trigger-ponte in fase `z80` **precede** il trigger esistente `z90`
`trgfn_risorse_umane_auth_user_sync_active` (che sincronizza
`auth_user.is_active` via `fn_sync_auth_user_is_active`). A sua volta,
l'UPSERT su `identita_digitali` scatena il trigger `z90`
`trgfn_identita_digitali_sync_auth_user_active` (gemello sul nuovo bridge).

Risultato: ogni INSERT/UPDATE su RUA comporta **due chiamate** a
`fn_sync_auth_user_is_active` (una via trigger legacy, una via trigger
identita). Ridondanza accettata perché la funzione sync è **idempotente**
(aggiorna `auth_user.is_active` solo se cambia).

---

### Ruolo `DISABILITATO` legacy

La traduzione `ruolo_sistema = 'DISABILITATO'` → `identita.attivo = false`
è intenzionale: nel nuovo modello il gate "utente disabilitato" è
espresso come **assenza di identità attiva** (verificabile via
`fn_has_identita_attiva`), non come valore speciale del `ruolo_applicativo`
(che resta `OPERATORE` per coerenza del tipo di identità).

---

### Ordine disattivazione (caveat per writer)

Il trigger `dbops.trgfn_prevent_deactivate_if_children` installato su
`identita_digitali` **blocca** la disattivazione di un'identità se esistono
bindings figli attivi. Il trigger-ponte gestisce correttamente questo
caso eseguendo prima il DELETE del binding SUPER_ADMIN (quando
`ruolo_sistema` passa a DISABILITATO) e poi disattivando l'identità via
UPSERT con `attivo = false`. Un writer esterno che tentasse di disattivare
direttamente un'identità con binding attivo incapperebbe invece
nell'errore del trigger — pattern corretto: disattivare prima i binding,
poi l'identità.

---

### Rimozione al cutover

Al cutover §4.6.H.3 questo trigger sarà droppato insieme al bridge
legacy `risorse_umane_auth_user` (che verrà sostituito dalla vista di
compatibilità). A quel punto `amm_software_repository` e tutti gli altri
writer Python scriveranno direttamente su `identita_digitali`, rendendo
il trigger-ponte superfluo.

---

{% include-markdown "signature-core.md" %}
