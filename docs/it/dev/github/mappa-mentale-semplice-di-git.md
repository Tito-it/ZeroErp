# 🧠 Mappa Mentale Semplice di Git

---

# 1️⃣ Git ha SOLO 3 cose importanti

## 📂 Working Directory

I file che stai modificando sul tuo computer.

## 🗂️ Local Repository

I commit salvati sul tuo computer.

## ☁️ Remote (origin)

La copia su GitHub.

---

# 2️⃣ Regola d’Oro

GitHub vede SOLO quello che è stato pushato.

Se fai merge locale ma non fai `git push`,
GitHub NON sa nulla.

---

# 3️⃣ I Comandi Fondamentali

## 🔄 Aggiornare dal remoto

```
git fetch origin
```

Scarica informazioni, non modifica i file.

## ⬇️ Portare aggiornamenti nel branch

```
git merge origin/main
```

Oppure

```
git pull
```

## ⬆️ Mandare commit su GitHub

```
git push
```

---

# 4️⃣ Quando una PR dice “This branch has conflicts”

Checklist mentale:

1. Vai sul tuo branch

```
git checkout tuo-branch
```

2. Aggiorna riferimenti

```
git fetch origin
```

3. Porta main dentro

```
git merge origin/main
```

4. Risolvi conflitti

5. Fai push

```
git push
```

6. Refresh PR

Fine.

---

# 5️⃣ Cosa significa “X in uscita” in VS Code

Numero di commit locali NON ancora pushati.

Non sono file modificati.
Sono commit.

---

# 6️⃣ Branch: Come pensarli

Un branch è solo un puntatore a un commit.

Cambiare branch non duplica codice.
Sposta solo dove punta HEAD.

---

# 7️⃣ HEAD (super importante)

HEAD = dove ti trovi adesso.

Controllo veloce:

```
git status
```

---

# 8️⃣ I 3 Problemi Classici

🔴 "Branch diverged"
Significa: locale e remoto hanno commit diversi.

🟡 "This branch has conflicts"
Significa: devi fare merge di main nel tuo branch.

🟢 "Everything up-to-date"
Sei allineato.

---

# 9️⃣ Schema Visuale

main
|
|---- A ---- B ---- C


Tito-dev        D ---- E

Se C cambia le stesse righe di D,
serve un merge manuale.

---

# 🔟 Mentalità Corretta

Git non cancella niente da solo.
Tu scegli cosa tenere nei conflitti.

Se qualcosa va storto:

```
git status
```

È sempre il punto di partenza.

---

# 🧩 Frase che salva la sanità mentale

"Se GitHub dice conflitti, devo fare merge di main nel mio branch e pushare."

---

# ✅ Playbook Anti-Casino (il tuo workflow con Tito-dev come centro)

## 🎯 Struttura

* `dev/db-tid` = lavoro DB
* `dev/backend-tid` = lavoro backend
* `Tito-dev` = integrazione (centro)
* `main` = rilascio

Idea: **le “foglie” non si aggiornano tra loro direttamente**. Passi sempre dal centro.

---

## 🔁 Sequenza quotidiana (inizio giornata / prima di lavorare)

### 1) Aggiorna il tuo branch di lavoro dal remoto

Se lavori su DB:

```
git checkout dev/db-tid
git pull --ff-only origin dev/db-tid
```

Se lavori su backend:

```
git checkout dev/backend-tid
git pull --ff-only origin dev/backend-tid
```

### 2) Porta dentro l’integrazione dal centro (così hai tutto)

DB:

```
git checkout dev/db-tid
git fetch origin
git rebase origin/Tito-dev
git push --force-with-lease
```

Backend:

```
git checkout dev/backend-tid
git fetch origin
git rebase origin/Tito-dev
git push --force-with-lease
```

---

## 🧩 Quando hai finito una feature (portare la foglia nel centro)

### A) Integra DB nel centro

```
git checkout Tito-dev
git fetch origin
git merge origin/dev/db-tid
git push origin Tito-dev
```

### B) Integra backend nel centro

```
git checkout Tito-dev
git fetch origin
git merge origin/dev/backend-tid
git push origin Tito-dev
```

Se ci sono conflitti:

* risolvi nei file
* poi:

```
git add .
git commit
git push origin Tito-dev
```

---

## 🚀 Prima di aprire/chiudere una PR verso `main`

**Sempre** allinea il centro con `main` (così niente conflitti in PR):

```
git checkout Tito-dev
git fetch origin
git merge origin/main
git push origin Tito-dev
```

Poi PR: `Tito-dev → main`.

---

## 🧯 Se GitHub dice “This branch has conflicts”

Significa: il branch della PR non contiene l’ultimo `main` oppure non è stato pushato.

Sul branch della PR:

```
git checkout <branch-della-PR>
git fetch origin
git merge origin/main
# risolvi conflitti
git add .
git commit
git push
```

Refresh PR.

---

## 🔍 Check rapidi (sanity checks)

Dove sono?

```
git status
```

Il mio branch include Tito-dev?

```
git merge-base --is-ancestor origin/Tito-dev HEAD; echo $?
```

`0` = sì.

Cosa mi manca da Tito-dev?

```
git log --oneline HEAD..origin/Tito-dev
```

Cosa ho in più rispetto a Tito-dev?

```
git log --oneline origin/Tito-dev..HEAD
```

---

Fine.

Se rileggi questo prima di PR/merge, eviti quasi tutti i loop mentali.
