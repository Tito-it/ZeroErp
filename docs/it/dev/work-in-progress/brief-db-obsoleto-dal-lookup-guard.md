# Brief DB — `obsoleto_dal`: filtro selezione nel lookup generico + guard creazione

> **Tipo**: brief DB (cosa serve, non come) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-30
> **Origine**: introdotta la colonna `obsoleto_dal` su `tipi_prestazione`/`template_flussi`
> ([brief-db-deprecabilita-catalogo-vs-istanze.md](brief-db-deprecabilita-catalogo-vs-istanze.md)).
> Resta da far sì che un record **obsoleto** non venga più **offerto per il nuovo** e non
> possa essere **usato per nuove istanze**.
>
> Nota: qui solo il **cosa** e i criteri di accettazione. Il **come** (introspezione,
> firma, trigger) lo decide il team DB.

---

## Contesto in una frase

`obsoleto_dal` separa "riferimento ancora valido" (per le istanze storiche) da
"selezionabile per il nuovo". La parte "storia intatta" è fatta. Manca chiudere il
secondo asse: **nasconderlo nella selezione** e **vietarne l'uso nel nuovo** — e che
valga **per ogni catalogo** che adotta il pattern, non solo per le pratiche.

---

## Obiettivo 1 — La selezione "per il nuovo" non offre i record obsoleti (generico)

Le liste di scelta dei cataloghi sono servite dal **lookup generico** (`rel=`), che già
esclude i record non `attivo`. Serve che **nello stesso punto generico** vengano esclusi
anche i record con `obsoleto_dal` raggiunto, **per qualunque catalogo** che abbia quella
colonna (non una soluzione per-tabella).

**Cosa serve**:
- un record con `obsoleto_dal IS NULL` o `obsoleto_dal > oggi` → **selezionabile**;
- un record con `obsoleto_dal <= oggi` → **non offerto** nella selezione per il nuovo;
- il filtro deve attivarsi **da solo** quando la tabella ha la colonna `obsoleto_dal`
  (come già accade per `attivo`), senza configurazione per-tabella.

**Vincolo importante — serve poter includere gli obsoleti in alcuni contesti**: lo stesso
lookup è usato anche per **filtrare liste/storico** (es. filtrare le pratiche esistenti per
tipo, incluso un tipo ormai obsoleto). In quei contesti gli obsoleti **devono comparire**,
altrimenti non si filtra più lo storico. Serve quindi un **interruttore** (gemello del
"solo attivi" già esistente) che il chiamante usa: default = nascondi obsoleti (selezione
per il nuovo); attivabile = mostra anche obsoleti (filtri/storico).

**Criteri di accettazione**:
- una nuova pratica non offre più `PREVENTIVI_IMMEDIATA/DIFFERITA` (9002/9003, obsoleti) ma
  offre `PREVENTIVI` (9004);
- un filtro "per tipo" su una lista di pratiche esistenti mostra **anche** i tipi obsoleti;
- le **letture storiche** (apertura di una pratica già su un tipo obsoleto) non sono
  influenzate dal filtro.

## Obiettivo 2 — Vietare l'uso di un catalogo obsoleto per nuove istanze (difesa in profondità)

La selezione lo nasconde, ma serve l'ultima linea: impedire via API/forzatura la
**creazione** di una nuova istanza (pratica/flusso, e in generale figli) che referenzia un
catalogo **obsoleto**. È coerente con il pattern guard del progetto ("la UI nasconde, il DB
rifiuta").

**Cosa serve**:
- la creazione di una **nuova** pratica/flusso su un tipo/template con `obsoleto_dal <= oggi`
  è **rifiutata** con errore parlante;
- le istanze **esistenti** su cataloghi obsoleti restano valide (nessun blocco su update di
  lifecycle che non cambiano il riferimento al catalogo).

**Criterio di accettazione**: tentare di creare una pratica sul tipo 9002/9003 (obsoleti)
fallisce con errore semantico; creare sul 9004 riesce; far avanzare una pratica storica su
9002/9003 continua a funzionare.

---

## Fuori scope (BE/FE)

- **Niente filtro lato BE per la selezione**: la lista passa dal lookup generico DB → il
  filtro vive lì. Il BE deve solo, dove serve un contesto "storico/filtro", **chiedere** di
  includere gli obsoleti tramite l'interruttore di cui sopra.
- Messaggistica utente sull'errore di creazione (BE/FE) oltre al codice errore del guard.

## Note

- Pattern `obsoleto_dal` pensato come **riusabile cross-dominio**: entrambi gli obiettivi
  devono valere per qualunque catalogo con la colonna, non solo per le pratiche.
- Coerenza con il guard `prevent_deactivate_if_children` esistente: qui non si tocca
  `attivo`, si lavora sull'asse `obsoleto_dal`.
