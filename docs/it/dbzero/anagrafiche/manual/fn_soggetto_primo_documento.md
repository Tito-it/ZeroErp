## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_soggetto_primo_documento`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il registro dei documenti (categoria `DOCUMENTO`)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli, la prima tabella ponte
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — i billing account dei ruoli
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende dei ruoli
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — le risorse del soggetto o dei suoi ruoli
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — l'unica che la legge
> * [config.fn_sorgente_tabella](/dbzero/config/funzioni/fn_sorgente_tabella) — la tabella di una sorgente
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — la gemella per il billing account

---

### 🎯 Scopo Principale

`anagrafiche.fn_soggetto_primo_documento` dice se un soggetto compare in un documento, in qualunque ruolo:
restituisce il codice del primo tipo di documento in cui lo trova, oppure niente. È la domanda del motivo
`E_CAMBIO_NATURA_CON_DOCUMENTI`, il motivo che non si toglie.

---

### ⭐ Un documento porta l'identità fiscale di quando è nato

Un preventivo, un ordine, un DDT, un contratto, una fattura, una ricevuta sono intestati al soggetto con la
partita IVA che aveva in quel momento. Un cambio di natura che la fa nascere o sparire renderebbe falsi quei
documenti: per questo, quando il soggetto compare in uno solo, quel cambio è chiuso per tutti.

Il soggetto compare in un documento **in qualunque ruolo**: controparte, ma anche emittente, vettore, agente,
reseller, responsabile. Un documento in bozza conta come uno emesso: conta che la riga ci sia.

---

### Quali documenti, e per quale colonna

L'elenco non è scritto nella funzione: lo deriva dal catalogo, e un documento nuovo entra da solo.

* **I documenti** sono le testate delle sorgenti di categoria `DOCUMENTO` di `config.sorgenti`, anche quelle
  spente, con la tabella che `config.fn_sorgente_tabella` dichiara.
* **Le colonne** sono le chiavi esterne a una colonna della testata che puntano a una delle tabelle da cui si
  arriva al soggetto: il soggetto stesso, i suoi ruoli, i billing account e le aziende di quei ruoli, le
  risorse umane del soggetto o dei suoi ruoli.
* **L'ordine** è stabile: per sorgente, poi per posizione della colonna. Il primo trovato è quello che il
  motivo nomina; non è «il più importante», è un esempio.

Una colonna che nomina il soggetto senza chiave esterna, o un riferimento che sta sulle righe e non sulla
testata, non si vede.

---

### ⭐ Sopra la visibilità, ma senza dire niente di più

I documenti sono visibili per azienda, ma che un soggetto compaia in un documento non dipende da chi guarda:
un documento di un'altra azienda deve bloccare come uno proprio. La funzione gira quindi coi privilegi del
proprietario, e per questo risponde il minimo: riceve solo il soggetto (nessun nome di tabella o colonna dal
chiamante) e restituisce solo il codice di un tipo di documento, mai un id o un numero.

---

{% include-markdown "it/dbzero/anagrafiche/_cambio-di-natura.md" %}

---

### ⚠️ Che cosa oggi non copre

* **L'esecuzione è aperta a tutti i ruoli del database.** La funzione legge sopra la visibilità, e il
  permesso di eseguirla non è ristretto all'applicazione: anche `PUBLIC` ce l'ha. Risponde solo il tipo di
  documento, ma a chiunque lo chieda.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato.

Un soggetto che non esiste non è un errore: non compare in niente.

---

### Test

* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — una società in un preventivo (trovata), una
  ditta individuale senza documenti (niente), la funzione privilegiata col percorso di ricerca stretto. Una
  persona fisica dentro un documento non è provata: nessuna fixture crea un cliente persona fisica.

---

### Note di migrazione

* 2026-11-14 — nasce con la regola dei motivi del cambio di natura. Lo stesso giorno la ricevuta dello shop si
  registra fra le sorgenti di categoria `DOCUMENTO`, ed entra nell'elenco senza eccezioni scritte a mano.

---

{% include-markdown "signature-core.md" %}
