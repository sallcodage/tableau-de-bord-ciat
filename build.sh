#!/usr/bin/env bash
# Script de build exécuté par Render à chaque déploiement
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Premier déploiement uniquement : jeu de données fictif + comptes de démonstration
# (ne réécrase jamais des données importées ensuite par le CIAT)
python manage.py shell -c "from pilotage.models import Projet; import sys; sys.exit(0 if Projet.objects.exists() else 1)" \
  || python manage.py seed_demo
# À chaque déploiement : mot de passe des comptes de démo = DEMO_PASSWORD (sinon valeur par défaut)
python manage.py shell -c "import os; from accounts.models import User; mdp = (os.getenv('DEMO_PASSWORD') or '').strip() or 'Ciat2026!demo'; comptes = list(User.objects.filter(username__startswith='demo_')); [(u.set_password(mdp), u.save()) for u in comptes]; print('Comptes de demo mis a jour :', len(comptes))"
