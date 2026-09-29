## 📘 Documentazione Concettuale – Tabella `config.auth_totp_device`

> 👀 **Vedi anche**
>
> **La credenziale:** [config.credenziali](/dbzero/config/tabelle/credenziali) — una password, tutte le porte
>
> **Chi deve usarlo:** [fn_totp_obbligatorio](/dbzero/script/funzioni/fn_totp_obbligatorio)
>
> **La lettura:** [fn_get_totp_device](/dbzero/script/funzioni/fn_get_totp_device)
>
> **I verbi:** [fn_totp_registra_device](/dbzero/script/funzioni/fn_totp_registra_device) · [fn_totp_conferma_device](/dbzero/script/funzioni/fn_totp_conferma_device) · [fn_totp_registra_uso](/dbzero/script/funzioni/fn_totp_registra_uso) · [fn_totp_consuma_recovery](/dbzero/script/funzioni/fn_totp_consuma_recovery) · [fn_totp_rigenera_recovery](/dbzero/script/funzioni/fn_totp_rigenera_recovery) · [fn_totp_disabilita_device](/dbzero/script/funzioni/fn_totp_disabilita_device)

---

### 🎯 Scopo Principale
(riscritta il 29-09-2026)

Il **secondo fattore** è il codice di sei cifre che l'app di autenticazione del
telefono cambia ogni trenta secondi: chi entra deve conoscere la password **e**
avere il telefono. Questa tabella tiene il **dispositivo** di una credenziale —
uno solo per persona — e le regole che lo rendono sicuro.

Il segreto da cui il telefono calcola i codici lo **cifra il backend** (con le
chiavi dei dati cifrati, `DJANGO_FIELD_ENCRYPTION_KEYS`): il database non lo vede
mai in chiaro e **non verifica i codici**. Li verifica il backend. Il database
custodisce lo stato e fa rispettare le regole che non devono dipendere dalla
disciplina di chi chiama:

* un codice vale **una volta sola**;
* un codice di recupero vale **una volta sola**;
* il dispositivo di una persona lo tocca **lei** (e, per toglierlo, un
  amministratore).

L'applicazione **legge** la tabella ma **non la scrive**: scrivono solo i verbi
qui sotto.

---

### Il ciclo di vita

| Momento | Chi | Cosa succede |
| --- | --- | --- |
| **Configurazione** | la persona | il backend genera il segreto e i codici di recupero, mostra il QR e i codici **una volta sola**, e registra il dispositivo **da confermare** ([fn_totp_registra_device](/dbzero/script/funzioni/fn_totp_registra_device)). Se si ricomincia prima di confermare, il dispositivo vecchio viene sostituito |
| **Conferma** | la persona | inserisce il primo codice; il backend lo verifica e il dispositivo diventa **attivo** ([fn_totp_conferma_device](/dbzero/script/funzioni/fn_totp_conferma_device)) |
| **Accesso** | nessuno (prima del login) | dopo la password, il backend verifica il codice e il database lo accetta solo se è **nuovo** ([fn_totp_registra_uso](/dbzero/script/funzioni/fn_totp_registra_uso)) |
| **Codice di recupero** | nessuno (prima del login) | senza telefono si entra con uno dei codici di recupero, che dopo non vale più ([fn_totp_consuma_recovery](/dbzero/script/funzioni/fn_totp_consuma_recovery)) |
| **Codici nuovi** | la persona | con un codice valido del telefono si generano codici nuovi, e i vecchi non valgono più ([fn_totp_rigenera_recovery](/dbzero/script/funzioni/fn_totp_rigenera_recovery)) |
| **Disattivazione** | la persona, un SUPER_ADMIN, o chi amministra il database | il dispositivo **viene cancellato**, segreto e codici compresi ([fn_totp_disabilita_device](/dbzero/script/funzioni/fn_totp_disabilita_device)). Chi ha l'obbligo viene riportato alla configurazione al prossimo accesso |

Lo stato si legge con [fn_get_totp_device](/dbzero/script/funzioni/fn_get_totp_device):
`ASSENTE`, `DA_CONFERMARE` o `ATTIVO`.

---

### ⭐ Un codice vale una volta sola

Il telefono calcola il codice dal segreto e dall'**intervallo** di trenta secondi
in cui ci si trova. Lo stesso numero di sei cifre può tornare, per caso, in un
intervallo diverso: confrontare il **testo** del codice non basta. Quello che non
deve succedere è usare di nuovo **lo stesso intervallo**, o uno più vecchio.

Per questo la tabella ricorda il numero dell'**ultimo intervallo accettato**
(`ultimo_passo_usato`) e accetta solo un intervallo **successivo**. Il confronto
e la scrittura avvengono insieme: due accessi simultanei con lo stesso codice
non passano tutti e due.

---

### Chi può toccare il dispositivo

* **Configurare, confermare, generare codici nuovi**: solo la persona stessa.
* **Disattivare**: la persona stessa; oppure un **SUPER_ADMIN**, che deve
  scrivere un **motivo**; oppure, nel caso senza via d'uscita — l'unico
  amministratore ha perso telefono e codici — **chi amministra il database**,
  dal server, sempre con un motivo. L'applicazione non può arrivare a
  quest'ultima strada.

Chi disattiva il dispositivo di un altro, quando e perché resta scritto
nell'audit degli accessi della persona (`dbops.sessioni_utente`): dal
gestionale lo registra il backend; dal server lo registra il database stesso,
nella stessa operazione, perché lì il backend non c'è. La riga del dispositivo
sparisce, e non resta un segreto solo per tenere uno storico.

---

### Limiti da conoscere

* **Il database non verifica i codici**: se il backend accettasse un codice
  sbagliato, il database non se ne accorgerebbe. Il database garantisce il
  monouso, non la correttezza del codice.
* **Un codice sbagliato conta come una password sbagliata**: lo registra il
  backend come tentativo fallito della credenziale (vedi
  [config.credenziali](/dbzero/config/tabelle/credenziali), «Cosa azzera cosa»).
* **Il legame con `django.auth_user`** esiste solo dove Django ha già creato le
  sue tabelle quando gira Liquibase: in CI no. Per questo i verbi controllano da
  sé che l'utente esista.

---

### Storia

* 2026-03-28 — nasce la tabella (`20260328-20`), senza chi la scriva.
* 2026-09-29 — il cantiere «secondo fattore» (`20260929-07` → `-24`): l'anti-replay
  passa dal testo del codice all'intervallo (`ultimo_passo_usato`), esce
  `abilitato` (doppione di `confermato`), nascono i verbi e la tabella si chiude
  in scrittura all'applicazione. Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
