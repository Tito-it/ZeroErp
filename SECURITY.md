# Politica di sicurezza

ZeroErp è un ERP open source (AGPL-3.0, con doppia licenza commerciale) attualmente in **fase di sviluppo
pre-produzione**: non esistono ancora release stabili con versionamento
semantico. Lo sviluppo avviene sul branch `main` del repository
[Tito-it/ZeroErp](https://github.com/Tito-it/ZeroErp).

## Versioni supportate

Finché non sarà pubblicata la prima release stabile, gli aggiornamenti di
sicurezza sono forniti **solo per l'ultima versione del branch `main`**.

| Versione | Supportata |
| --- | --- |
| `main` (ultimo commit) | ✅ |
| Branch di lavoro / fork / tag pre-release | ❌ |

Quando il progetto raggiungerà release versionate, questa tabella verrà
aggiornata con le versioni effettivamente supportate.

## Segnalare una vulnerabilità

**Non aprire una issue pubblica** per le vulnerabilità di sicurezza: una issue
è visibile a tutti e potrebbe esporre il problema prima che sia corretto.

Usa uno di questi canali privati:

1. **GitHub Security Advisories** (preferito) — dalla scheda **Security** del
   repository, voce *"Report a vulnerability"*
   (`https://github.com/Tito-it/ZeroErp/security/advisories/new`). Permette una
   discussione privata e coordinata con i manutentori.
2. **Email** — [mc.titini@gmail.com](mailto:mc.titini@gmail.com), indicando
   `[SECURITY] ZeroErp` nell'oggetto.

Nella segnalazione includi, per quanto possibile:

- una descrizione della vulnerabilità e del suo impatto;
- i passi per riprodurla (PoC, richieste HTTP, query SQL, configurazione);
- le componenti e i file coinvolti (backend Django, funzioni/trigger
  PostgreSQL, frontend Vue);
- eventuali proposte di mitigazione.

## Cosa aspettarsi

- **Presa in carico**: entro **7 giorni** dalla segnalazione.
- **Valutazione**: aggiornamento sullo stato (accettata / declinata / servono
  più informazioni) di norma entro **30 giorni**.
- **Se accettata**: concordiamo una tempistica di correzione e una
  divulgazione responsabile; la fix viene rilasciata su `main` e la
  segnalazione resa pubblica (con credito a chi l'ha riportata, se gradito)
  solo dopo il rilascio della correzione.
- **Se declinata**: spieghiamo il motivo (es. comportamento atteso, fuori
  perimetro, non riproducibile).

Trattandosi di un progetto a base volontaria, i tempi possono variare:
apprezziamo la **divulgazione coordinata** e chiediamo di non rendere pubblici
i dettagli finché la correzione non è disponibile.
