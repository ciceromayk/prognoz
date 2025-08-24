# prognoz

Projeto para análise de viabilidade imobiliária.

## Migrations e deploy

1. Gerar e commitar migrations sempre que alterar modelos:

```bash
python3 manage.py makemigrations
git add <app>/migrations
git commit -m "Add migration: ..."
```

2. Aplicar migrations no deploy:

```bash
python3 manage.py migrate
```

3. Pipeline CI recomendada:

- `python3 manage.py showmigrations --plan`  # detecta migrations pendentes
- `python3 manage.py migrate --noinput`
- `python3 manage.py test`

4. Arquivos a ignorar no git: `db.sqlite3`, `venv/`, `__pycache__/`, `.env`.

5. Em ambientes com múltiplas instâncias, garantir que migrations rodem antes de trocar tráfego.
