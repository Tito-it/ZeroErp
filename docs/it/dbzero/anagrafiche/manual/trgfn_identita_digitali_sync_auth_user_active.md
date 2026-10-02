## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_identita_digitali_sync_auth_user_active`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La trigger function
**`anagrafiche.trgfn_identita_digitali_sync_auth_user_active()`** sincronizza
`django.auth_user.is_active` in risposta ai cambi sul **nuovo bridge generico**
`anagrafiche.identita_digitali`.

È simmetrica al trigger esistente su `risorse_umane_auth_user`, ma copre
**tutti i ruoli applicativi** del modello multi-face auth (operatore,
portale clienti, portale fornitori, shop customer, api_client, disabilitato).

---

### Regole applicate

* **Eventi**:
  * `AFTER INSERT` — nuova identità creata; sync iniziale di
    `auth_user.is_active`.
  * `AFTER UPDATE OF attivo, valido_dal, valido_al, ruolo_applicativo,
    auth_user_id` — reagisce solo alle colonne che impattano lo stato di
    login (evita scatti inutili su `meta`, audit, ecc.).
* Passa `NEW.auth_user_id` a
  [`fn_sync_auth_user_is_active`](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active).
* La funzione sync gestisce internamente i casi fail-closed (veste
  spenta, finestra scaduta, soggetto disattivato) e l'UPDATE
  idempotente su `auth_user.is_active` (solo se cambia).
* Fase `z90` (final/deferrable, pattern ZeroErp per trigger di propagazione).
* Ritorno `NULL` (trigger AFTER: valore ignorato).

---

### Copertura ruoli

| Ruolo applicativo | Comportamento atteso |
|-------------------|----------------------|
| `OPERATORE` | Doppia verifica: identità + legacy `risorse_umane.attivo` |
| `CLIENTE_PORTALE` | Verifica identità + soggetto attivo |
| `FORNITORE_PORTALE` | Verifica identità + soggetto attivo |
| `SHOP_CUSTOMER` | Verifica identità + soggetto attivo |
| `API_CLIENT` | Verifica identità + soggetto attivo |
| `DISABILITATO` | non esiste più nella tabella viva (dal 2026-10-02, brief `brief-db-be-fe-area-accessi`, R-DB-1): una veste spenta è `attivo = false`, di qualunque tipo |

---

### Scelta DELETE non coperto

Il trigger **non** scatta su `DELETE`. Motivazione: nel modello multi-face
auth la "cancellazione" di un'identità è sconsigliata; la pratica corretta
è disattivare con `attivo = false` (mantenuta la traccia storica). Se in
futuro servirà coprire il DELETE (es. cleanup GDPR), aggiungere un trigger
AFTER DELETE dedicato che passi `OLD.auth_user_id` alla funzione sync.

---

### Ruolo nel processo

È il terzo trigger reattivo della catena sync (insieme a quelli su
`risorse_umane_auth_user` e `risorse_umane`), specifico per il nuovo bridge.
Al cutover §4.6 (quando `risorse_umane_auth_user` diventerà una vista letta
su `identita_digitali`), questo trigger diventerà **l'unico** punto di sync
per gli operatori, eliminando la ridondanza con il trigger legacy.

---

{% include-markdown "signature-core.md" %}
