# Preparare ZeroERP all'uso

> **A chi serve**: a chi ha appena ricevuto un'installazione di ZeroERP e deve
> renderla utilizzabile. Non serve essere sviluppatori.
>
> **Che cosa NON copre**: come si installa il programma su una macchina — quello
> è un altro documento ([play-book operativo](dev/backend/play-book-operativo-backend.md),
> di taglio tecnico). Qui si parte da *«il programma è installato e si apre»* e si
> arriva a *«il programma lavora»*. In mezzo ci sono sette cose, e nessuna è
> difficile: sono solo poco visibili.

---

## Perché questo manuale esiste

Fra «installato» e «funzionante» c'è una terra di mezzo fatta di configurazioni
che **nessun errore segnala**. Il programma si apre, le schermate rispondono, i
test sono verdi — e intanto le email non partono, i lavori notturni non girano,
le segnalazioni non arrivano a nessuno.

> **Non è un'ipotesi.** Su questa installazione, nel settembre 2026, mancavano
> **tre** di queste cose contemporaneamente. Nessuna dava errore. Sono state
> scoperte per caso, guardando altro.

⭐ Per questo ogni passo qui sotto finisce con **«come faccio a sapere che è
andata bene»**: è la parte che conta più delle istruzioni.

## Prima di cominciare — che cosa avere sottomano

| Ti serve | Per cosa |
| --- | --- |
| i dati fiscali dell'azienda | partita IVA, codice fiscale, indirizzo, per l'emittente dei documenti |
| un indirizzo email e la sua password | per far uscire la posta dal programma (vedi passo 3: **non** basta la password del tuo account) |
| un indirizzo a cui mandare le segnalazioni | può essere il tuo |
| l'elenco delle persone che useranno il programma | nome, email e che cosa devono poter fare |
| l'accesso alla macchina (o qualcuno che ce l'abbia) | **solo** per il passo 4 |

## I sette passi, in ordine

L'ordine conta: ogni passo dà per fatto il precedente.

| | Passo | Dove si fa | Serve la macchina? |
| --- | --- | --- | --- |
| 1 | L'azienda che emette i documenti | nel programma | no |
| 2 | Le persone e cosa possono fare | nel programma | no |
| 3 | La posta in uscita | nel programma | no |
| 4 | Accendere i lavori automatici | **sulla macchina** | **sì** |
| 5 | Chi riceve le segnalazioni | sulla macchina (un file) | **sì** |
| 6 | I valori predefiniti | nel programma | no |
| 7 | I modelli di stampa | nel programma | no |

---

## Passo 1 — L'azienda che emette i documenti

**Perché**: ogni documento — preventivo, fattura, DDT — è emesso *da qualcuno*.
Senza questo dato il programma non sa intestare niente, e la maggior parte delle
schermate resta vuota.

**Dove**: `Amministrazione software → Emittenti fiscali`.

Si può averne **più di uno** (più aziende sullo stesso programma): in quel caso
ogni operatore vedrà solo i documenti dell'azienda a cui è assegnato — è il
passo 2.

> ✅ **Come so che è andata bene**: l'emittente compare nell'elenco ed è *attivo*.

## Passo 2 — Le persone, e che cosa possono fare

**Perché**: ZeroERP non ha un utente «tuttofare». Ogni persona ha un profilo che
dice a quali aree accede e con quale libertà (vedere, modificare, niente).

**Dove**: `Amministrazione software → Operatori` per le persone,
`Amministrazione software → Permessi` per i profili.

⚠️ **La cosa che si dimentica più spesso**: dopo aver creato una persona, va
**assegnata a un'azienda** (passo 1). Un operatore senza azienda non vede
documenti — e non è un errore, è un elenco vuoto, che si legge come *«non c'è
niente»* invece di *«non ti è stato assegnato niente»*.

> ✅ **Come so che è andata bene**: la schermata degli operatori mostra un avviso
> quando qualcuno è rimasto senza azienda. Se l'avviso non c'è, sono tutti a
> posto.

## Passo 3 — La posta in uscita

**Perché**: il programma manda email — inviti agli utenti, reset delle password,
documenti ai clienti, le segnalazioni del passo 5. Senza questo passo **nessuna
di quelle email parte**.

**Dove**: `Amministrazione software → Email accounts`, account `SISTEMA`.

Servono: indirizzo del server di posta (`smtp_host`), porta, nome utente,
password, e l'indirizzo da cui le email risulteranno spedite.

🔴 **Attenzione, ed è la trappola peggiore di tutto il manuale.** Un'installazione
nuova arriva con un indirizzo **finto**: `smtp.example.com`. Finché resta quello,
il programma **non dice niente**: fa finta di spedire, scrive nel suo registro
che l'email è stata inviata, e non arriva a nessuno. Non c'è nessun errore da
cercare, perché non c'è nessun errore.

⚠️ **Se usi Gmail** (o un altro servizio con verifica in due passaggi) la password
del tuo account **non funziona**: serve una *password per le app*, che si genera
dalle impostazioni di sicurezza del tuo account Google. È un codice di 16
caratteri, e si vede una volta sola.

> ✅ **Come so che è andata bene**: nella stessa schermata c'è il pulsante **«prova
> connessione»**. Deve rispondere verde. ⚠️ Se risponde *«SMTP non configurato»*,
> l'indirizzo finto è ancora lì.

## Passo 4 — Accendere i lavori automatici

**Perché**: alcune cose il programma le fa da solo — spedire la posta in coda,
stampare i documenti, chiudere quello che è scaduto, mandarti le segnalazioni.
Questi lavori sono **descritti** nell'installazione, ma vanno **accesi** una
volta sola sulla macchina.

**Dove**: sulla macchina, con un comando solo:

```bash
sudo /percorso/di/ZeroErp/backend/bin/install-timers.sh
```

Il comando legge l'elenco dei lavori dalla configurazione e accende quelli
previsti. È **ripetibile**: lanciarlo due volte non fa danni.

🔴 **Perché è il passo più facile da saltare**: se non lo si esegue, tutto il
resto sembra funzionare. Le schermate rispondono, i documenti si creano — solo
che di notte non succede niente e la posta resta ferma in coda.

> ✅ **Come so che è andata bene**: il comando stampa un elenco con scritto
> `ACCENDI` accanto ai lavori previsti. Per ricontrollare più tardi:
> `systemctl list-timers 'zeroerp-*'`.

## Passo 5 — Chi riceve le segnalazioni

**Perché**: ZeroERP tiene sotto controllo sé stesso e, quando qualcosa non torna,
manda un riassunto per email. Ma deve sapere **a chi**.

**Dove**: sulla macchina, nel file `backend/.env.systemd`, una riga:

```
ZEROERP_PRESIDI_DIGEST_DESTINATARIO=tuo.indirizzo@esempio.it
```

Più indirizzi si separano con una virgola: il primo è il destinatario, gli altri
ricevono in copia.

⚠️ Lasciarlo vuoto **non spegne** le segnalazioni: il programma le prepara lo
stesso e poi dichiara di non avere nessuno a cui mandarle. È voluto — così
l'assenza si vede invece di passare per silenzio.

> ✅ **Come so che è andata bene**: la mattina dopo arriva un'email con oggetto
> `[ZeroERP] Presidi …`. Se non vuoi aspettare, chi ha accesso alla macchina può
> chiederla subito.

## Passo 6 — I valori predefiniti

**Perché**: molte schermate propongono valori già compilati — l'IVA, i termini di
pagamento, la valuta. Sono **53** impostazioni, quasi tutte già sensate: si
toccano solo quelle che nella tua azienda funzionano diversamente.

**Dove**: `Configurazione → Impostazioni`.

⭐ **Non serve guardarle tutte adesso.** Il modo più efficiente è partire, e
correggere quando una schermata propone un valore che non è il tuo: ogni
impostazione dice a chi si applica (tutti, un'azienda, una persona).

> ✅ **Come so che è andata bene**: creando un documento di prova, i valori
> proposti sono quelli giusti.

## Passo 7 — I modelli di stampa

**Perché**: i documenti che escono in PDF seguono un modello. Il programma ne
porta alcuni pronti; se l'azienda ha una sua carta intestata, si sostituiscono.

⚠️ È il passo meno urgente: si può cominciare a lavorare e sistemarlo dopo. Ma
finché non è fatto, i documenti stampati avranno l'aspetto predefinito.

> ✅ **Come so che è andata bene**: genera un documento di prova e guarda il PDF.

---

## La verifica finale

Quando hai finito, questi cinque controlli dicono se il sistema è davvero pronto:

| Controllo | Come si fa | Esito atteso |
| --- | --- | --- |
| l'azienda c'è | `Amm. software → Emittenti fiscali` | almeno uno, attivo |
| nessuno è rimasto senza azienda | `Amm. software → Operatori` | nessun avviso in cima |
| la posta esce | `Email accounts` → «prova connessione» | verde |
| i lavori girano | `systemctl list-timers 'zeroerp-*'` | l'elenco non è vuoto |
| le segnalazioni arrivano | la posta, la mattina dopo | un'email `[ZeroERP] Presidi …` |

⭐ **Il quinto controllo vale per tutti gli altri**: se quell'email arriva, vuol
dire che la posta esce, che i lavori girano e che il programma si sta guardando
allo specchio. È il collaudo dell'intera catena, in una riga sola.

## Quando qualcosa non va — i tre casi veri

Questi tre non sono esempi inventati: sono capitati su questa installazione, e
ognuno era **muto**.

| Sintomo | Causa quasi certa | Passo |
| --- | --- | --- |
| «tutto sembra a posto ma **non arriva nessuna email**» | l'indirizzo di posta è ancora quello finto | 3 |
| «di notte **non succede niente**», la coda si riempie | i lavori automatici non sono stati accesi | 4 |
| «il programma dice di aver mandato il riassunto, **non lo riceve nessuno**» | manca il destinatario | 5 |

⭐ **Il filo comune, e vale la pena averlo in mente**: in tutti e tre i casi il
programma *non sbagliava*. Faceva esattamente quello che gli era stato detto di
fare, e nessuno gli aveva detto niente. **Un pezzo che manca non fa rumore** — ed
è la ragione per cui esiste la verifica finale qui sopra.

## Che cosa questo manuale non dice ancora

* **come si installa il programma su una macchina nuova**: è un documento a
  parte, oggi incompleto — la scelta fra i due modi di installare non è ancora
  stata presa;
* **i salvataggi (backup) e come si rimette in piedi** un'installazione: manca, ed
  è la cosa più importante fra quelle che mancano;
* **la messa in sicurezza** (certificati, accessi dall'esterno): oggi vive nel
  play-book tecnico e andrebbe raccontata anche qui;
* **il passaggio dei dati** da un altro gestionale.

*Prima versione: 11 settembre 2026. Nasce da un'installazione vera in cui tre di
questi sette passi mancavano, e nessuno se n'era accorto.*
