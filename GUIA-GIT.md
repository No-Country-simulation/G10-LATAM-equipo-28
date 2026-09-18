# Guía Git para el equipo

Instrucciones básicas para subir cambios al repositorio del equipo desde Git Bash.

---

## Cómo hacerlo desde Git Bash

### 1. Abrir Git Bash en la carpeta del repo

Opción rápida: en el Explorador de Windows, entra a la carpeta del proyecto, click derecho → "Open Git Bash here".

O desde una terminal ya abierta:

```bash
cd "/c/Users/racso/Documents/00 - Alura_AI ORACLE/02 - Hackaton NewMind/00 - branch github repositorio/G10-LATAM-equipo-28"
```

(En Git Bash, `C:\` se escribe como `/c/` y se usan `/` no `\`.)

### 2. Ver qué cambió

```bash
git status
```

Te dice qué archivos son nuevos (untracked), cuáles modificaste, y cuáles ya están en el "staging area" listos para commit.

### 3. Añadir archivos al staging

```bash
git add archivo1.py archivo2.md          # archivos específicos (recomendado)
git add .                                # todo lo que hay en la carpeta actual
```

Prefiere nombrar los archivos: evita subir cosas por error (secretos, basura temporal, etc.).

### 4. Crear el commit

```bash
git commit -m "Mensaje descriptivo del cambio"
```

El mensaje debe explicar el *por qué* del cambio, no solo el *qué*.

### 5. Subir al repositorio del equipo

```bash
git push
```

La primera vez en una rama nueva Git te pedirá `git push -u origin nombre-rama` (el `-u` deja esa rama "trackeada" para que después baste con `git push`). Como el `main` ya quedó trackeado, ahora te alcanza con `git push`.

### 6. Bajar cambios de otros compañeros

Antes de empezar a trabajar en el día, o antes de un push si otros están comiteando:

```bash
git pull
```

Esto trae los commits del `main` remoto a tu local.

---

## Flujo típico del día

```bash
git pull                        # traer lo último del equipo
# ...trabajas, editas archivos...
git status                      # revisar qué cambió
git add archivo1 archivo2       # marcar lo que quieres subir
git commit -m "Descripción"     # crear el commit local
git push                        # enviarlo al remoto
```

---

## Recomendaciones importantes para trabajo en equipo

- **Nunca hagas `push --force` sobre `main`** — puede sobrescribir el trabajo de otros.
- **Haz `git pull` antes de `git push`** — si otro compañero subió algo antes, Git te pedirá integrar sus cambios primero.
- **Idealmente, no trabajes directo en `main`.** Crea una rama para cada feature:

  ```bash
  git checkout -b nombre-de-la-feature   # crear y cambiarte a nueva rama
  # trabajas, comiteas normal...
  git push -u origin nombre-de-la-feature
  ```

  Luego abres un Pull Request en GitHub para mergear a `main`. Así el equipo puede revisar antes de que entre al `main`.
- **Revisa qué estás subiendo** con `git status` y `git diff --staged` antes del commit — evita subir archivos `.env` con contraseñas, tokens, etc.
